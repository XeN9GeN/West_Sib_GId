"""Persistence and railway-selection helpers for OSM points of interest."""

import argparse
import math

from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app import models
from app.database import SessionLocal, engine
from app.taxonomy import load_taxonomy


IMPORT_RADIUS_METERS = load_taxonomy()["settings"]["railway_radius_meters"]
BATCH_SIZE = 1000


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
        description="Пространственный отбор импортированных OSM POI рядом с ЖД."
    )
    parser.add_argument(
        "--select-near-railway",
        action="store_true",
        required=True,
        help="Отобрать уже импортированные объекты OSM рядом с точками ЖД.",
    )
    parser.add_argument(
        "--radius-m",
        type=float,
        default=IMPORT_RADIUS_METERS,
        help=f"Радиус пространственного отбора в метрах (по умолчанию {IMPORT_RADIUS_METERS}).",
    )
    args = parser.parse_args()

    select_osm_pois_near_railway(args.radius_m)


if __name__ == "__main__":
    main()
