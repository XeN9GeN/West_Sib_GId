import os
import unittest
import uuid

from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app.database import Base
from app.migrations import ensure_osm_enrichment_schema, ensure_taxonomy_schema
from app.taxonomy import load_taxonomy
from scripts.enrich_osm import _classify_promotion_candidate, promote_selected_pois
from scripts.import_osm import to_poi_row
from scripts.import_osm_pbf import feature_to_osm_element


class OSMPromotionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database_url = os.getenv("TEST_DATABASE_URL")
        if not database_url:
            raise unittest.SkipTest("TEST_DATABASE_URL не задан.")
        if not make_url(database_url).database.endswith("_test"):
            raise unittest.SkipTest("Интеграционные тесты разрешены только на *_test.")

        cls.engine = create_engine(database_url, pool_pre_ping=True)
        try:
            with cls.engine.connect() as connection:
                connection.execute(text("SELECT postgis_version()"))
            Base.metadata.create_all(bind=cls.engine)
            ensure_osm_enrichment_schema(cls.engine)
            ensure_taxonomy_schema(cls.engine)
        except SQLAlchemyError as error:
            cls.engine.dispose()
            raise unittest.SkipTest(f"Тестовая БД недоступна: {error}") from error
        cls.taxonomy = load_taxonomy()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "engine"):
            cls.engine.dispose()

    def setUp(self):
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection)
        self.osm_id = int(uuid.uuid4().int % 2_000_000_000) + 1

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def test_target_objects_flow_from_pbf_feature_through_promotion(self):
        examples = (
            (
                "way",
                {"railway": "museum", "name": "Железнодорожный музей"},
                "railway_museums",
            ),
            (
                "way",
                {"building": "train_station", "name": "Исторический вокзал"},
                "railway_stations_historic",
            ),
            (
                "relation",
                {"boundary": "protected_area", "name": "Охраняемая территория"},
                "protected_areas",
            ),
        )

        for index, (osm_type, tags, expected_subcategory) in enumerate(examples):
            with self.subTest(osm_type=osm_type, tags=tags):
                osm_id = self.osm_id + index
                feature = {
                    "type": "Feature",
                    "properties": {
                        "@type": osm_type,
                        "@id": osm_id,
                        **tags,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [10.0, 10.0],
                    },
                }
                element = feature_to_osm_element(feature)
                poi = models.OSMPOI(**to_poi_row(element))
                self.db.add(poi)
                self.db.flush()
                self.db.add(models.OSMPOINearRailway(osm_poi_id=poi.id))
                self.db.flush()

                promote_selected_pois(self.db, self.taxonomy)
                self.db.flush()

                place = self.db.execute(
                    select(models.CulturePlace).where(
                        models.CulturePlace.osm_type == osm_type,
                        models.CulturePlace.osm_id == osm_id,
                    )
                ).scalar_one()
                self.assertIsNone(place.subcategory)
                self.assertEqual(place.name, tags["name"])
                self.assertEqual(
                    _classify_promotion_candidate(poi, self.taxonomy).subcategory,
                    expected_subcategory,
                )
                self.assertIsNone(place.classified_at)

        count = self.db.execute(
            select(models.CulturePlace.id).where(
                models.CulturePlace.osm_id.in_(
                    [self.osm_id, self.osm_id + 1, self.osm_id + 2]
                )
            )
        ).scalars().all()
        self.assertEqual(len(count), 3)

    def test_repeated_hard_exclusion_is_idempotent_and_resolves_in_place(self):
        feature = {
            "type": "Feature",
            "properties": {
                "@type": "way",
                "@id": self.osm_id,
                "highway": "footway",
                "name": "Пешеходная дорожка",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [10.0, 10.0],
            },
        }
        poi = models.OSMPOI(**to_poi_row(feature_to_osm_element(feature)))
        self.db.add(poi)
        self.db.flush()
        self.db.add(models.OSMPOINearRailway(osm_poi_id=poi.id))
        self.db.flush()

        promote_selected_pois(self.db, self.taxonomy)
        self.db.flush()
        registry = self.db.execute(
            select(models.OSMPOIExclusionRegistry).where(
                models.OSMPOIExclusionRegistry.osm_poi_id == poi.id
            )
        ).scalar_one()
        first_evaluated_at = registry.last_evaluated_at
        first_log_count = self.db.execute(
            select(models.ClassificationAuditLog.id).where(
                models.ClassificationAuditLog.osm_id == self.osm_id
            )
        ).scalars().all()

        promote_selected_pois(self.db, self.taxonomy)
        self.db.flush()
        self.assertEqual(registry.last_evaluated_at, first_evaluated_at)
        self.assertEqual(
            len(self.db.execute(
                select(models.ClassificationAuditLog.id).where(
                    models.ClassificationAuditLog.osm_id == self.osm_id
                )
            ).scalars().all()),
            len(first_log_count),
        )

        poi.tags = {"tourism": "museum", "name": "Музей"}
        self.db.flush()
        promote_selected_pois(self.db, self.taxonomy)
        self.db.flush()

        self.assertFalse(registry.is_active)
        self.assertIsNotNone(registry.resolved_at)
        place = self.db.execute(
            select(models.CulturePlace).where(
                models.CulturePlace.osm_id == self.osm_id
            )
        ).scalar_one()
        self.assertEqual(place.name, "Музей")
        actions = self.db.execute(
            select(models.ClassificationAuditLog.action)
            .where(models.ClassificationAuditLog.osm_id == self.osm_id)
            .order_by(models.ClassificationAuditLog.id)
        ).scalars().all()
        self.assertEqual(
            actions,
            ["auto_exclude_candidate", "auto_resolve_candidate_exclusion"],
        )

    def test_manual_category_and_description_survive_promote(self):
        poi = models.OSMPOI(
            osm_type="node",
            osm_id=self.osm_id,
            tags={"tourism": "museum", "name": "OSM name"},
            geom=WKTElement("POINT(10 10)", srid=4326),
        )
        self.db.add(poi)
        self.db.flush()
        place = models.CulturePlace(
            osm_type="node",
            osm_id=self.osm_id,
            name="Ручное название",
            type1=models.Type1.human,
            type2=models.Type2.theater,
            subcategory="railway_museums",
            classification_locked=True,
            short_description="Ручное описание.",
            description_source="manual",
            geom=WKTElement("POINT(10 10)", srid=4326),
        )
        self.db.add(place)
        self.db.add(models.OSMPOINearRailway(osm_poi_id=poi.id))
        self.db.flush()

        promote_selected_pois(self.db, self.taxonomy)
        self.db.flush()
        self.db.refresh(place)

        self.assertEqual(place.name, "Ручное название")
        self.assertEqual(place.type2, models.Type2.theater)
        self.assertEqual(place.subcategory, "railway_museums")
        self.assertEqual(place.short_description, "Ручное описание.")
        self.assertEqual(place.description_source, "manual")

    def test_unchanged_promote_does_not_update_existing_place(self):
        poi = models.OSMPOI(
            osm_type="node",
            osm_id=self.osm_id,
            tags={"railway": "museum", "name": "Железнодорожный музей"},
            geom=WKTElement("POINT(10 10)", srid=4326),
        )
        self.db.add(poi)
        self.db.flush()
        self.db.add(models.OSMPOINearRailway(osm_poi_id=poi.id))
        self.db.flush()

        promote_selected_pois(self.db, self.taxonomy)
        self.db.flush()
        first_ctid = self.db.execute(
            text("SELECT ctid::text FROM culture_place WHERE osm_id = :osm_id"),
            {"osm_id": self.osm_id},
        ).scalar_one()

        promote_selected_pois(self.db, self.taxonomy)
        self.db.flush()
        second_ctid = self.db.execute(
            text("SELECT ctid::text FROM culture_place WHERE osm_id = :osm_id"),
            {"osm_id": self.osm_id},
        ).scalar_one()

        self.assertEqual(first_ctid, second_ctid)


if __name__ == "__main__":
    unittest.main()
