"""Import raw OSM points of interest around the railway corridor."""

import argparse
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app import models
from app.database import SessionLocal, engine


OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
REQUEST_TIMEOUT_SECONDS = 240
OVERPASS_ATTEMPTS_PER_ENDPOINT = 2
OVERPASS_RETRY_DELAY_SECONDS = 2
OVERPASS_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
OVERPASS_UNAVAILABLE_SPLIT_DEPTH = 1
IMPORT_RADIUS_METERS = 5000
BATCH_SIZE = 1000
OVERPASS_TILE_WIDTH_DEGREES = 2.0
OVERPASS_TILE_HEIGHT_DEGREES = 1.0
OVERPASS_TILE_DELAY_SECONDS = 1
MAX_TIMEOUT_SPLIT_DEPTH = 3
MIN_TILE_SPAN_DEGREES = 0.05


class OverpassQueryTimeout(RuntimeError):
    pass


class OverpassTileUnavailable(RuntimeError):
    pass


def get_route_bbox(db, radius_m=IMPORT_RADIUS_METERS):
    bounds = db.execute(text("""
        SELECT
            ST_XMin(ST_3DExtent(geom)),
            ST_YMin(ST_3DExtent(geom)),
            ST_XMax(ST_3DExtent(geom)),
            ST_YMax(ST_3DExtent(geom))
        FROM railway
    """)).one()

    if any(value is None for value in bounds):
        raise RuntimeError(
            "Таблица railway пуста: сначала загрузите и постройте линию ЖД."
        )

    min_lon, min_lat, max_lon, max_lat = map(float, bounds)
    lat_padding = radius_m / 111_320
    middle_latitude = math.radians((min_lat + max_lat) / 2)
    longitude_scale = max(abs(math.cos(middle_latitude)), 0.01)
    lon_padding = radius_m / (111_320 * longitude_scale)

    return (
        min_lon - lon_padding,
        min_lat - lat_padding,
        max_lon + lon_padding,
        max_lat + lat_padding,
    )


def _axis_tiles(start, end, max_span):
    count = max(1, math.ceil((end - start) / max_span))
    span = (end - start) / count
    return [
        (start + index * span, end if index == count - 1 else start + (index + 1) * span)
        for index in range(count)
    ]


def split_bbox_into_tiles(bbox, max_width=OVERPASS_TILE_WIDTH_DEGREES,
                          max_height=OVERPASS_TILE_HEIGHT_DEGREES):
    min_lon, min_lat, max_lon, max_lat = bbox
    lon_tiles = _axis_tiles(min_lon, max_lon, max_width)
    lat_tiles = _axis_tiles(min_lat, max_lat, max_height)
    return [
        (tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat)
        for tile_min_lat, tile_max_lat in lat_tiles
        for tile_min_lon, tile_max_lon in lon_tiles
    ]


def split_bbox_in_half(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    lon_span = max_lon - min_lon
    lat_span = max_lat - min_lat
    lon_mid = (min_lon + max_lon) / 2
    lat_mid = (min_lat + max_lat) / 2

    lon_parts = (
        [(min_lon, lon_mid), (lon_mid, max_lon)]
        if lon_span > MIN_TILE_SPAN_DEGREES
        else [(min_lon, max_lon)]
    )
    lat_parts = (
        [(min_lat, lat_mid), (lat_mid, max_lat)]
        if lat_span > MIN_TILE_SPAN_DEGREES
        else [(min_lat, max_lat)]
    )
    return [
        (tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat)
        for tile_min_lat, tile_max_lat in lat_parts
        for tile_min_lon, tile_max_lon in lon_parts
    ]


def build_overpass_query(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    bbox_text = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    return f"""
        [out:json][timeout:180];
        (
          nwr["tourism"~"^(museum|attraction|gallery|zoo)$"]({bbox_text});
          nwr["historic"]({bbox_text});
          nwr["heritage"]({bbox_text});
          nwr["amenity"~"^(theatre|place_of_worship|arts_centre)$"]({bbox_text});
          nwr["building"~"^(church|chapel|mosque|synagogue|temple)$"]({bbox_text});
          nwr["memorial"]({bbox_text});
        );
        out center tags;
    """


def fetch_osm_elements(query):
    request_data = urlencode({"data": query}).encode("utf-8")
    last_error = None
    endpoint_errors = []
    received_gateway_timeout = False
    received_bad_gateway = False
    received_read_timeout = False

    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(OVERPASS_ATTEMPTS_PER_ENDPOINT):
            request = Request(
                endpoint,
                data=request_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "West-Sib-GId OSM POI importer",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    payload = json.load(response)
            except HTTPError as exc:
                error_message = (
                    f"Overpass API {endpoint} вернул HTTP {exc.code}: {exc.reason}"
                )
                if exc.code not in OVERPASS_RETRYABLE_STATUS_CODES:
                    exc.close()
                    raise RuntimeError(error_message) from exc
                last_error = exc
                endpoint_errors.append(
                    f"{endpoint}: HTTP {exc.code}: {exc.reason}"
                )
                received_gateway_timeout = received_gateway_timeout or exc.code == 504
                received_bad_gateway = received_bad_gateway or exc.code == 502
                exc.close()
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                endpoint_errors.append(f"{endpoint}: {exc}")
                reason = getattr(exc, "reason", None)
                if isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError):
                    received_read_timeout = True
                    break
            else:
                if not isinstance(payload, dict):
                    raise RuntimeError(
                        f"Overpass API {endpoint} вернул ответ в неожиданном формате."
                    )
                if payload.get("remark"):
                    remark = payload["remark"]
                    if any(
                        phrase in remark.lower()
                        for phrase in ("timed out", "out of memory")
                    ):
                        raise OverpassQueryTimeout(
                            f"Overpass API {endpoint} превысил лимит времени: "
                            f"{remark}"
                        )
                    raise RuntimeError(
                        f"Overpass API {endpoint} не выполнил запрос: {remark}"
                    )

                elements = payload.get("elements")
                if not isinstance(elements, list):
                    if isinstance(last_error, HTTPError) and last_error.code == 504:
                        raise OverpassQueryTimeout(
                            "Все серверы Overpass завершили запрос по HTTP 504."
                        ) from last_error

                    raise RuntimeError(
                        f"В ответе Overpass API {endpoint} отсутствует список elements."
                    )
                return elements

            if attempt + 1 < OVERPASS_ATTEMPTS_PER_ENDPOINT:
                time.sleep(OVERPASS_RETRY_DELAY_SECONDS * (2 ** attempt))

    if received_gateway_timeout:
        raise OverpassQueryTimeout(
            "Все серверы Overpass завершили запрос по HTTP 504. "
            f"Подробности: {'; '.join(endpoint_errors)}"
        ) from last_error

    if received_bad_gateway or received_read_timeout:
        raise OverpassTileUnavailable(
            "Overpass вернул HTTP 502 или не ответил вовремя. "
            f"Подробности: {'; '.join(endpoint_errors)}"
        ) from last_error

    raise RuntimeError(
        "Все серверы Overpass временно недоступны после "
        f"{len(OVERPASS_ENDPOINTS) * OVERPASS_ATTEMPTS_PER_ENDPOINT} попыток. "
        f"Ошибки: {'; '.join(endpoint_errors)}"
    ) from last_error


def import_osm_tile(db, bbox, depth=0):
    try:
        elements = fetch_osm_elements(build_overpass_query(bbox))
    except (OverpassQueryTimeout, OverpassTileUnavailable) as exc:
        max_split_depth = (
            OVERPASS_UNAVAILABLE_SPLIT_DEPTH
            if isinstance(exc, OverpassTileUnavailable)
            else MAX_TIMEOUT_SPLIT_DEPTH
        )
        smaller_tiles = split_bbox_in_half(bbox)
        if depth >= max_split_depth or len(smaller_tiles) < 2:
            raise RuntimeError(
                f"Overpass не обработал тайл {bbox} "
                f"после {depth} делений."
            ) from exc

        print(
            f"Тайл {bbox} не обработан Overpass; делю его на "
            f"{len(smaller_tiles)} меньших тайла."
        )
        return sum(
            import_osm_tile(db, tile, depth + 1)
            for tile in smaller_tiles
        )

    return save_osm_elements(db, elements)


def to_poi_row(element):
    position = element if element.get("type") == "node" else element.get("center")
    if not position or "lat" not in position or "lon" not in position:
        raise ValueError(
            f"У OSM-объекта {element.get('type')}/{element.get('id')} нет координат."
        )

    tags = element.get("tags", {})
    if not isinstance(tags, dict):
        raise ValueError(
            f"У OSM-объекта {element.get('type')}/{element.get('id')} некорректные теги."
        )

    lon = float(position["lon"])
    lat = float(position["lat"])
    return {
        "osm_type": element["type"],
        "osm_id": int(element["id"]),
        "name": tags.get("name"),
        "tags": tags,
        "geom": WKTElement(f"POINT({lon} {lat})", srid=4326),
    }


def save_osm_elements(db, elements):
    unique_elements = {
        (element["type"], element["id"]): element
        for element in elements
    }
    rows = [to_poi_row(element) for element in unique_elements.values()]

    for offset in range(0, len(rows), BATCH_SIZE):
        batch = rows[offset:offset + BATCH_SIZE]
        statement = insert(models.OSMPOI).values(batch)
        statement = statement.on_conflict_do_update(
            index_elements=["osm_type", "osm_id"],
            set_={
                "name": statement.excluded.name,
                "tags": statement.excluded.tags,
                "geom": statement.excluded.geom,
            },
        )
        db.execute(statement)

    db.commit()
    return len(rows)


def import_osm():
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    models.OSMPOI.__table__.create(bind=engine, checkfirst=True)

    db = SessionLocal()
    try:
        tiles = split_bbox_into_tiles(get_route_bbox(db))
        imported_count = 0
        for index, tile in enumerate(tiles, start=1):
            if index > 1:
                time.sleep(OVERPASS_TILE_DELAY_SECONDS)
            print(f"Загрузка тайла OSM {index}/{len(tiles)}: {tile}")
            imported_count += import_osm_tile(db, tile)
        print(
            f"В таблицу osm_pois загружено/обновлено объектов OSM: "
            f"{imported_count} (тайлов: {len(tiles)})."
        )
    finally:
        db.close()


def select_osm_pois_near_railway(radius_m=IMPORT_RADIUS_METERS):
    if not math.isfinite(radius_m) or radius_m <= 0:
        raise ValueError("Радиус поиска должен быть положительным числом в метрах.")

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    models.OSMPOINearRailway.__table__.create(bind=engine, checkfirst=True)

    with engine.begin() as connection:
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_raw_railway_points_geography
            ON raw_railway_points USING GIST ((geom::geography))
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_osm_pois_geography
            ON osm_pois USING GIST ((geom::geography))
        """))
        connection.execute(text("DELETE FROM osm_pois_near_railway"))
        result = connection.execute(
            text("""
                INSERT INTO osm_pois_near_railway (osm_poi_id)
                SELECT p.id
                FROM osm_pois AS p
                WHERE EXISTS (
                    SELECT 1
                    FROM raw_railway_points AS r
                    WHERE ST_DWithin(
                        p.geom::geography,
                        r.geom::geography,
                        :radius_m
                    )
                )
            """),
            {"radius_m": radius_m},
        )

    print(
        f"В радиусе {radius_m:g} м от точек ЖД найдено объектов OSM: "
        f"{result.rowcount}."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Импорт OSM POI и пространственный отбор рядом с точками ЖД."
    )
    parser.add_argument(
        "--select-near-railway",
        action="store_true",
        help="Отобрать уже импортированные объекты OSM рядом с точками ЖД.",
    )
    parser.add_argument(
        "--radius-m",
        type=float,
        default=IMPORT_RADIUS_METERS,
        help="Радиус пространственного отбора в метрах (по умолчанию 5000).",
    )
    args = parser.parse_args()

    if args.select_near_railway:
        select_osm_pois_near_railway(args.radius_m)
    else:
        import_osm()


if __name__ == "__main__":
    main()
