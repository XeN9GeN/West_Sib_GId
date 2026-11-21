"""Validate and import researched summaries for Novosibirsk culture places."""

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import text

from app.database import SessionLocal, engine
from app.migrations import ensure_osm_enrichment_schema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "agent_research_novosibirsk"
DEFAULT_INPUT_PATH = DATA_DIR / "novosibirsk_places_input.jsonl"
DEFAULT_RESULT_PATH = DATA_DIR / "novosibirsk_place_research (1).jsonl"
BOUNDARY_PATH = DATA_DIR / "novosibirsk_city_boundary.geojson"
ALLOWED_STATUSES = {"ready", "no_reliable_sources", "ambiguous"}
ALLOWED_RESULT_FIELDS = {
    "schema_version",
    "osm_type",
    "osm_id",
    "status",
    "summary_ru",
    "sources",
    "note",
}
ALLOWED_SOURCE_FIELDS = {"url", "title", "publisher", "accessed_at"}

PLACE_QUERY = text("""
    SELECT
        cp.short_description,
        cp.history,
        cp.ai_summary,
        cp.ai_summary_sources
    FROM culture_place AS cp
    WHERE cp.osm_type = :osm_type
      AND cp.osm_id = :osm_id
      AND ST_Covers(
            ST_SetSRID(ST_GeomFromGeoJSON(:boundary_geojson), 4326),
            cp.geom::geometry
      )
""")

UPDATE_QUERY = text("""
    UPDATE culture_place
    SET ai_summary = :summary,
        ai_summary_sources = CAST(:sources AS JSON)
    WHERE osm_type = :osm_type
      AND osm_id = :osm_id
      AND ai_summary IS NULL
""")


def _read_jsonl(path):
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise RuntimeError(f"Не удалось прочитать файл: {path}") from exc

    records = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise RuntimeError(f"Пустая строка в JSONL, строка {line_number}.")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Некорректный JSON в строке {line_number}: {exc.msg}."
            ) from exc
        if not isinstance(record, dict):
            raise RuntimeError(f"Строка {line_number} должна содержать JSON-объект.")
        records.append((line_number, record))
    return records


def _validate_sources(sources, line_number):
    if not isinstance(sources, list):
        raise RuntimeError(f"В строке {line_number} sources должен быть списком.")
    for source_index, source in enumerate(sources, start=1):
        label = f"строка {line_number}, источник {source_index}"
        if not isinstance(source, dict) or set(source) != ALLOWED_SOURCE_FIELDS:
            raise RuntimeError(f"{label}: неожиданные поля источника.")
        url = source.get("url")
        parsed_url = urlsplit(url) if isinstance(url, str) else None
        if (
            not parsed_url
            or parsed_url.scheme != "https"
            or not parsed_url.netloc
            or parsed_url.username
            or parsed_url.password
        ):
            raise RuntimeError(f"{label}: ожидается корректная HTTPS-ссылка.")
        for field in ("title", "publisher", "accessed_at"):
            value = source.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(f"{label}: поле {field} не должно быть пустым.")
        try:
            parsed_date = date.fromisoformat(source["accessed_at"])
        except ValueError as exc:
            raise RuntimeError(f"{label}: accessed_at должен иметь формат YYYY-MM-DD.") from exc
        if parsed_date.isoformat() != source["accessed_at"]:
            raise RuntimeError(f"{label}: accessed_at должен иметь формат YYYY-MM-DD.")


def validate_result(input_path, result_path):
    input_records = _read_jsonl(input_path)
    result_records = _read_jsonl(result_path)
    if len(input_records) != len(result_records):
        raise RuntimeError(
            f"Число записей не совпадает: вход {len(input_records)}, "
            f"результат {len(result_records)}."
        )

    statuses = {"ready": 0, "no_reliable_sources": 0, "ambiguous": 0}
    ready_records = []
    seen_keys = set()
    for (input_line, input_record), (line_number, record) in zip(
        input_records, result_records
    ):
        osm_type = input_record.get("osm_type")
        osm_id = input_record.get("osm_id")
        expected_key = (osm_type, osm_id)
        if (
            record.get("osm_type") != osm_type
            or type(record.get("osm_id")) is not int
            or expected_key != (record.get("osm_type"), record.get("osm_id"))
        ):
            raise RuntimeError(
                f"OSM ID в строке {line_number} не совпадает с "
                f"входной строкой {input_line}."
            )
        if expected_key in seen_keys:
            raise RuntimeError(f"Повтор OSM ID {osm_type}/{osm_id}.")
        seen_keys.add(expected_key)

        if set(record) - ALLOWED_RESULT_FIELDS:
            raise RuntimeError(
                f"Неожиданные поля результата в строке {line_number}: "
                f"{sorted(set(record) - ALLOWED_RESULT_FIELDS)}."
            )
        if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
            raise RuntimeError(f"Неподдерживаемая schema_version в строке {line_number}.")
        status = record.get("status")
        if status not in ALLOWED_STATUSES:
            raise RuntimeError(f"Неизвестный status в строке {line_number}: {status!r}.")
        statuses[status] += 1
        if "note" in record and not isinstance(record["note"], str):
            raise RuntimeError(f"Поле note в строке {line_number} должно быть строкой.")

        summary = record.get("summary_ru")
        sources = record.get("sources")
        _validate_sources(sources, line_number)
        if status == "ready":
            if not isinstance(summary, str) or not summary.strip():
                raise RuntimeError(f"Для ready в строке {line_number} нужна сводка.")
            if len(summary) > 500:
                raise RuntimeError(f"Сводка в строке {line_number} длиннее 500 символов.")
            if not sources:
                raise RuntimeError(f"Для ready в строке {line_number} нужны источники.")
            ready_records.append(record)
        else:
            if summary is not None:
                raise RuntimeError(
                    f"Для {status} в строке {line_number} summary_ru должен быть null."
                )
            if status == "no_reliable_sources" and sources:
                raise RuntimeError(
                    f"Для no_reliable_sources в строке {line_number} "
                    "sources должен быть пустым."
                )
    return ready_records, statuses


def _read_boundary():
    try:
        boundary = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RuntimeError(f"Не удалось прочитать границу города: {BOUNDARY_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Некорректный GeoJSON границы Новосибирска.") from exc
    if boundary.get("type") not in {"Polygon", "MultiPolygon"}:
        raise RuntimeError("Ожидалась граница GeoJSON Polygon или MultiPolygon.")
    return json.dumps(boundary, separators=(",", ":"))


def import_result(input_path, result_path, apply=False):
    ready_records, statuses = validate_result(input_path, result_path)
    boundary_geojson = _read_boundary()
    inserted = 0
    already_imported = 0

    with SessionLocal() as db:
        try:
            for record in ready_records:
                identity = f"{record['osm_type']}/{record['osm_id']}"
                row = db.execute(
                    PLACE_QUERY,
                    {
                        "osm_type": record["osm_type"],
                        "osm_id": record["osm_id"],
                        "boundary_geojson": boundary_geojson,
                    },
                ).mappings().one_or_none()
                if row is None:
                    raise RuntimeError(
                        f"Объект {identity} не найден в culture_place "
                        "внутри границы Новосибирска."
                    )
                if any(
                    isinstance(value, str) and value.strip()
                    for value in (row["short_description"], row["history"])
                ):
                    raise RuntimeError(
                        f"У объекта {identity} уже есть обычное описание или история; "
                        "импорт остановлен, существующие данные не изменены."
                    )

                sources_json = json.dumps(
                    record["sources"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                if row["ai_summary"] is not None:
                    existing_sources = row["ai_summary_sources"] or []
                    if (
                        row["ai_summary"] != record["summary_ru"]
                        or existing_sources != record["sources"]
                    ):
                        raise RuntimeError(
                            f"У объекта {identity} уже есть другая ИИ-сводка; "
                            "перезапись запрещена."
                        )
                    already_imported += 1
                    continue

                if apply:
                    result = db.execute(
                        UPDATE_QUERY,
                        {
                            "summary": record["summary_ru"],
                            "sources": sources_json,
                            "osm_type": record["osm_type"],
                            "osm_id": record["osm_id"],
                        },
                    )
                    if result.rowcount != 1:
                        raise RuntimeError(
                            f"Не удалось записать сводку для {identity}; "
                            "транзакция будет отменена."
                        )
                inserted += 1

            if apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise

    return statuses, inserted, already_imported


def main():
    parser = argparse.ArgumentParser(
        description="Проверить и импортировать ИИ-сводки объектов Новосибирска."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT_PATH)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Записать проверенные сводки в БД; без флага выполняется dry-run.",
    )
    args = parser.parse_args()

    ensure_osm_enrichment_schema(engine)
    statuses, inserted, already_imported = import_result(
        args.input,
        args.result,
        apply=args.apply,
    )
    mode = "Импорт завершён" if args.apply else "Проверка пройдена (dry-run)"
    print(
        f"{mode}: готовых {statuses['ready']}, "
        f"без надёжных источников {statuses['no_reliable_sources']}, "
        f"неоднозначных {statuses['ambiguous']}; "
        f"{'записано' if args.apply else 'будет записано'} {inserted}, "
        f"уже импортировано {already_imported}."
    )


if __name__ == "__main__":
    main()
