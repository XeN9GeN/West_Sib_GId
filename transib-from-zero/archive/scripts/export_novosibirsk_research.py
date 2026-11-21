"""Export undocumented Novosibirsk OSM places for external research."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import text

from app.database import SessionLocal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = (
    PROJECT_ROOT
    / "agent_research_novosibirsk"
    / "novosibirsk_city_boundary.geojson"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "agent_research_novosibirsk"
    / "novosibirsk_places_input.jsonl"
)

EXPORT_QUERY = text("""
    WITH boundary AS (
        SELECT ST_SetSRID(ST_GeomFromGeoJSON(:boundary_geojson), 4326) AS geom
    )
    SELECT
        cp.osm_type,
        cp.osm_id,
        cp.name,
        cp.type1::text AS type1,
        cp.type2::text AS type2,
        ST_Y(op.geom) AS lat,
        ST_X(op.geom) AS lon,
        op.tags::text AS tags_json,
        COALESCE(
            NULLIF(BTRIM(op.tags->>'wikidata'), ''),
            NULLIF(BTRIM(op.wikidata_id), ''),
            NULLIF(BTRIM(cp.wikidata_id), '')
        ) AS wikidata_id,
        op.wikipedia_url,
        op.wikivoyage_url,
        op.image_page_url,
        cp.sources
    FROM culture_place AS cp
    JOIN osm_pois AS op
      ON op.osm_type = cp.osm_type
     AND op.osm_id = cp.osm_id
    CROSS JOIN boundary
    WHERE cp.osm_type IN ('node', 'way', 'relation')
      AND cp.osm_id IS NOT NULL
      AND ST_Covers(boundary.geom, op.geom)
      AND NULLIF(BTRIM(cp.short_description), '') IS NULL
      AND NULLIF(BTRIM(cp.history), '') IS NULL
      AND NULLIF(BTRIM(op.tags->>'description:ru'), '') IS NULL
      AND NULLIF(BTRIM(op.tags->>'description'), '') IS NULL
      AND NULLIF(BTRIM(op.wikidata_description), '') IS NULL
      AND NULLIF(BTRIM(op.wikipedia_extract), '') IS NULL
      AND NULLIF(BTRIM(op.wikivoyage_extract), '') IS NULL
    ORDER BY cp.osm_type, cp.osm_id
""")


def _read_boundary(path):
    try:
        geometry = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RuntimeError(f"Не удалось прочитать границу города: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Файл границы не содержит корректный GeoJSON: {path}") from exc

    if not isinstance(geometry, dict) or geometry.get("type") not in {
        "Polygon",
        "MultiPolygon",
    }:
        raise RuntimeError(
            "Граница Новосибирска должна быть GeoJSON Polygon или MultiPolygon."
        )
    return geometry


def _source_urls(row, tags):
    urls = [
        f"https://www.openstreetmap.org/{row['osm_type']}/{row['osm_id']}",
        row.get("wikipedia_url"),
        row.get("wikivoyage_url"),
        row.get("image_page_url"),
    ]
    wikidata_id = row.get("wikidata_id")
    if isinstance(wikidata_id, str) and re.fullmatch(r"Q[1-9][0-9]*", wikidata_id):
        urls.append(f"https://www.wikidata.org/wiki/{wikidata_id}")

    for key, project in (("wikipedia", "wikipedia"), ("wikivoyage", "wikivoyage")):
        value = tags.get(key)
        if not isinstance(value, str) or ":" not in value:
            continue
        language, title = value.split(":", 1)
        if re.fullmatch(r"[a-z][a-z0-9-]{0,20}", language) and title.strip():
            urls.append(
                f"https://{language}.{project}.org/wiki/"
                f"{quote(title.strip().replace(' ', '_'), safe='')}"
            )

    urls.extend(row.get("sources") or [])
    return list(dict.fromkeys(url for url in urls if isinstance(url, str) and url))


def _input_record(row):
    tags = json.loads(row["tags_json"]) if row.get("tags_json") else {}
    if not isinstance(tags, dict):
        raise RuntimeError(
            f"Теги OSM {row['osm_type']}/{row['osm_id']} имеют неожиданный формат."
        )

    return {
        "osm_type": row["osm_type"],
        "osm_id": int(row["osm_id"]),
        "name": row["name"],
        "type1": row["type1"],
        "type2": row["type2"],
        "lat": round(float(row["lat"]), 7),
        "lon": round(float(row["lon"]), 7),
        "tags": tags,
        "wikidata_id": row.get("wikidata_id"),
        "existing_sources": _source_urls(row, tags),
    }


def export_places(output_path=DEFAULT_OUTPUT_PATH, boundary_path=BOUNDARY_PATH):
    boundary = _read_boundary(Path(boundary_path))
    with SessionLocal() as db:
        rows = db.execute(
            EXPORT_QUERY,
            {"boundary_geojson": json.dumps(boundary, separators=(",", ":"))},
        ).mappings().all()

    records = [_input_record(row) for row in rows]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return len(records)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Экспорт мест без описаний внутри границы Новосибирска "
            "для подготовки справок."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Путь к JSONL (по умолчанию: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--boundary",
        type=Path,
        default=BOUNDARY_PATH,
        help=f"GeoJSON границы (по умолчанию: {BOUNDARY_PATH})",
    )
    args = parser.parse_args()

    count = export_places(args.output, args.boundary)
    print(f"Экспортировано объектов без описания: {count}.")
    print(f"Файл для передачи агенту: {args.output.resolve()}")


if __name__ == "__main__":
    main()
