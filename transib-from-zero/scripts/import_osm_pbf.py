"""Import cultural OSM objects from Geofabrik regional PBF extracts."""

import argparse
import http.client
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from shapely.geometry import shape
from sqlalchemy import text

from app import models
from app.database import SessionLocal, engine
from scripts.import_osm import BATCH_SIZE, save_osm_elements


PBF_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "osm"
PBF_DOWNLOADS = (
    (
        "ural-fed-district",
        "https://download.geofabrik.de/russia/ural-fed-district-latest.osm.pbf",
    ),
    (
        "siberian-fed-district",
        "https://download.geofabrik.de/russia/siberian-fed-district-latest.osm.pbf",
    ),
)
DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
DOWNLOAD_PROGRESS_STEP_BYTES = 50 * 1024 * 1024
DOWNLOAD_RETRY_LIMIT = 8
DOWNLOAD_RETRY_DELAY_SECONDS = 5
DOWNLOAD_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
OSM_TAG_FILTERS = (
    "nwr/tourism=museum,attraction,gallery,zoo",
    "nwr/historic",
    "nwr/heritage",
    "nwr/amenity=theatre,place_of_worship,arts_centre",
    "nwr/building=church,chapel,mosque,synagogue,temple",
    "nwr/memorial",
)


def download_extract(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        print(f"Используется сохранённая выгрузка: {destination.name}")
        return destination

    partial_path = destination.with_suffix(destination.suffix + ".part")
    consecutive_failures = 0

    while True:
        offset = partial_path.stat().st_size if partial_path.exists() else 0
        headers = {"User-Agent": "West-Sib-GId OSM POI importer"}
        if offset:
            headers["Range"] = f"bytes={offset}-"

        request = Request(url, headers=headers)
        try:
            response_context = urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS)
        except HTTPError as exc:
            if offset and exc.code == 416:
                partial_path.unlink(missing_ok=True)
                continue
            if exc.code not in DOWNLOAD_RETRYABLE_STATUS_CODES:
                raise RuntimeError(
                    f"Не удалось скачать OSM-выгрузку {url}: HTTP {exc.code}"
                ) from exc
            last_error = exc
            exc.close()
            bytes_received = 0
        except (URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            bytes_received = 0
        else:
            with response_context as response:
                status = getattr(response, "status", None) or response.getcode()
                append = bool(offset and status == 206)
                if offset and status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    expected_prefix = f"bytes {offset}-"
                    if not content_range.startswith(expected_prefix):
                        raise RuntimeError(
                            f"Сервер вернул некорректный Content-Range для {url}: "
                            f"{content_range!r}."
                        )
                    total_text = content_range.partition("/")[2]
                    expected_size = (
                        int(total_text)
                        if total_text.isdigit()
                        else None
                    )
                else:
                    append = False
                    expected_length = response.headers.get("Content-Length")
                    expected_size = (
                        int(expected_length)
                        if expected_length is not None
                        else None
                    )

                downloaded = offset if append else 0
                bytes_received = 0
                last_reported = downloaded // DOWNLOAD_PROGRESS_STEP_BYTES
                mode = "ab" if append else "wb"
                read_error = None
                with partial_path.open(mode) as output:
                    while True:
                        try:
                            chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        except http.client.IncompleteRead as exc:
                            chunk = exc.partial
                            read_error = exc
                        except (URLError, TimeoutError, ConnectionError) as exc:
                            chunk = b""
                            read_error = exc

                        if chunk:
                            output.write(chunk)
                            downloaded += len(chunk)
                            bytes_received += len(chunk)
                            progress = downloaded // DOWNLOAD_PROGRESS_STEP_BYTES
                            if progress > last_reported:
                                print(
                                    f"Загружено {downloaded // (1024 * 1024)} МБ "
                                    f"из {destination.name}."
                                )
                                last_reported = progress
                        if read_error or not chunk:
                            break

            if read_error is not None:
                last_error = read_error
            elif expected_size is None or downloaded == expected_size:
                break
            elif downloaded > expected_size:
                raise RuntimeError(
                    f"Загрузка {url} превысила ожидаемый размер: "
                    f"{downloaded} > {expected_size} байт."
                )
            elif bytes_received:
                consecutive_failures = 0
                continue
            else:
                last_error = RuntimeError(
                    f"Сервер завершил ответ раньше ожидаемого размера: "
                    f"{downloaded} из {expected_size} байт."
                )

        consecutive_failures += 1
        if consecutive_failures > DOWNLOAD_RETRY_LIMIT:
            raise RuntimeError(
                f"Не удалось завершить загрузку {url} после "
                f"{DOWNLOAD_RETRY_LIMIT} повторов. Получено "
                f"{partial_path.stat().st_size if partial_path.exists() else 0} байт. "
                f"Частичный файл сохранён: {partial_path.name}. Последняя ошибка: "
                f"{last_error}"
            ) from last_error

        delay = min(
            DOWNLOAD_RETRY_DELAY_SECONDS * (2 ** (consecutive_failures - 1)),
            60,
        )
        print(
            f"Обрыв загрузки {destination.name}; продолжу с "
            f"{partial_path.stat().st_size if partial_path.exists() else 0} байт "
            f"через {delay} сек. ({consecutive_failures}/{DOWNLOAD_RETRY_LIMIT})."
        )
        time.sleep(delay)

    downloaded = partial_path.stat().st_size if partial_path.exists() else 0
    if downloaded == 0:
        raise RuntimeError(f"Сервер вернул пустую OSM-выгрузку: {url}")

    os.replace(partial_path, destination)
    print(f"Выгрузка сохранена: {destination.name}")
    return destination


def feature_to_osm_element(feature):
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise ValueError("Osmium export вернул объект не в формате GeoJSON Feature.")

    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        raise ValueError("В GeoJSON Feature отсутствуют properties или geometry.")

    osm_type = properties.get("@type")
    if osm_type not in {"node", "way", "relation"}:
        raise ValueError(f"В GeoJSON Feature указан неизвестный OSM type: {osm_type}")
    try:
        osm_id = int(properties["@id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("В GeoJSON Feature отсутствует корректный OSM ID.") from exc

    try:
        point = shape(geometry).representative_point()
        if point.is_empty:
            raise ValueError("Пустая геометрия.")
        center = {"lon": point.x, "lat": point.y}
    except (TypeError, ValueError) as exc:
        center = get_coordinate_bounds_center(geometry)
        if center is None:
            raise ValueError(
                f"У OSM-объекта {osm_type}/{osm_id} нет корректной геометрии."
            ) from exc
        print(
            f"Предупреждение: геометрия OSM {osm_type}/{osm_id} не разобрана "
            f"Shapely; использован центр координатной рамки. Причина: {exc}"
        )

    tags = {
        key: value
        for key, value in properties.items()
        if key not in {"@type", "@id"}
    }
    element = {
        "type": osm_type,
        "id": osm_id,
        "tags": tags,
    }
    if osm_type == "node":
        element.update({"lon": center["lon"], "lat": center["lat"]})
    else:
        element["center"] = center
    return element


def iter_positions(coordinates):
    if not isinstance(coordinates, (list, tuple)):
        return
    if (
        len(coordinates) >= 2
        and isinstance(coordinates[0], (int, float))
        and isinstance(coordinates[1], (int, float))
    ):
        yield float(coordinates[0]), float(coordinates[1])
        return
    for child in coordinates:
        yield from iter_positions(child)


def get_coordinate_bounds_center(geometry):
    positions = list(iter_positions(geometry.get("coordinates")))
    if geometry.get("type") == "GeometryCollection":
        positions = [
            position
            for item in geometry.get("geometries", [])
            if isinstance(item, dict)
            for position in iter_positions(item.get("coordinates"))
        ]
    if not positions:
        return None

    longitudes, latitudes = zip(*positions)
    return {
        "lon": (min(longitudes) + max(longitudes)) / 2,
        "lat": (min(latitudes) + max(latitudes)) / 2,
    }


def iter_geojsonseq(pbf_path):
    command = [
        "osmium",
        "export",
        "--output-format=geojsonseq",
        "--attributes=type,id",
        str(pbf_path),
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if process.stdout is None:
        raise RuntimeError("Не удалось открыть поток вывода команды osmium export.")

    completed = False
    try:
        for line in process.stdout:
            record = line.strip()
            if record:
                yield json.loads(record.lstrip("\x1e"))
        completed = True
    finally:
        process.stdout.close()
        if not completed and process.poll() is None:
            process.terminate()
        process.wait()

    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command)


def import_filtered_pbf(db, pbf_path):
    batch = []
    imported_count = 0
    for feature in iter_geojsonseq(pbf_path):
        batch.append(feature_to_osm_element(feature))
        if len(batch) >= BATCH_SIZE:
            imported_count += save_osm_elements(db, batch)
            batch.clear()
    if batch:
        imported_count += save_osm_elements(db, batch)
    return imported_count


def import_extract(db, name, pbf_path, data_dir):
    filtered_path = data_dir / f"{name}.poi.osm.pbf"
    command = [
        "osmium",
        "tags-filter",
        "--remove-tags",
        "--output",
        str(filtered_path),
        "--overwrite",
        str(pbf_path),
        *OSM_TAG_FILTERS,
    ]
    try:
        subprocess.run(command, check=True)
        return import_filtered_pbf(db, filtered_path)
    finally:
        filtered_path.unlink(missing_ok=True)


def import_osm_from_pbf(data_dir=PBF_DATA_DIR):
    data_dir.mkdir(parents=True, exist_ok=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    models.OSMPOI.__table__.create(bind=engine, checkfirst=True)

    db = SessionLocal()
    try:
        imported_count = 0
        for name, url in PBF_DOWNLOADS:
            print(f"Подготовка региональной OSM-выгрузки: {name}.")
            pbf_path = download_extract(url, data_dir / f"{name}-latest.osm.pbf")
            print(f"Отбор культурных объектов из {pbf_path.name}.")
            imported_count += import_extract(db, name, pbf_path, data_dir)
        print(
            f"Из региональных PBF загружено/обновлено объектов OSM: "
            f"{imported_count}."
        )
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Импорт культурных объектов OSM из региональных PBF."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=PBF_DATA_DIR,
        help="Каталог для сохранения PBF-выгрузок.",
    )
    args = parser.parse_args(argv)
    import_osm_from_pbf(args.data_dir)


if __name__ == "__main__":
    main()
