import os
import unittest
import uuid

from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url

from app import models
from app.database import Base
from app.migrations import ensure_taxonomy_schema
from app.taxonomy import load_taxonomy
from scripts.classify_places import classify_places


class TaxonomyIntegrationTests(unittest.TestCase):
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
        self.prefix = "taxonomy-test-" + uuid.uuid4().hex[:12]

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def test_radius_includes_2499_and_excludes_2501_meters(self):
        near = self._add_demo("near", 2499)
        far = self._add_demo("far", 2501)

        summary = classify_places(
            self.db,
            self.taxonomy,
            dry_run=False,
            reports_dir=None,
            place_ids=[near.id, far.id],
        )

        near_result = self.db.execute(
            select(models.CulturePlace).where(models.CulturePlace.id == near.id)
        ).scalar_one()
        far_result = self.db.execute(
            select(models.CulturePlace).where(models.CulturePlace.id == far.id)
        ).scalar_one()
        self.assertIsNotNone(near_result.railway_distance_m)
        self.assertLessEqual(near_result.railway_distance_m, 2500)
        self.assertFalse(near_result.excluded_from_map)
        self.assertIsNone(far_result.railway_distance_m)
        self.assertTrue(far_result.excluded_from_map)
        self.assertEqual(far_result.exclusion_reason, "outside_railway_radius")
        self.assertEqual(summary["classification_updates"], 2)

    def test_repeated_classification_does_not_update_checked_timestamps(self):
        place = self._add_demo("repeat", 100)
        classify_places(
            self.db,
            self.taxonomy,
            dry_run=False,
            reports_dir=None,
            place_ids=[place.id],
        )
        persisted = self.db.execute(
            select(models.CulturePlace).where(models.CulturePlace.id == place.id)
        ).scalar_one()
        classified_at = persisted.classified_at
        checked_at = persisted.railway_distance_checked_at

        summary = classify_places(
            self.db,
            self.taxonomy,
            dry_run=False,
            reports_dir=None,
            place_ids=[place.id],
        )
        persisted = self.db.execute(
            select(models.CulturePlace).where(models.CulturePlace.id == place.id)
        ).scalar_one()
        self.assertEqual(summary["classification_updates"], 0)
        self.assertEqual(summary["distance_updates"], 0)
        self.assertEqual(persisted.classified_at, classified_at)
        self.assertEqual(persisted.railway_distance_checked_at, checked_at)

    def test_dry_run_does_not_mutate_classification_or_distance(self):
        place = self._add_demo("dry", 100)
        summary = classify_places(
            self.db,
            self.taxonomy,
            dry_run=True,
            reports_dir=None,
            place_ids=[place.id],
        )
        persisted = self.db.execute(
            select(models.CulturePlace).where(models.CulturePlace.id == place.id)
        ).scalar_one()
        self.assertGreaterEqual(summary["classification_updates"], 1)
        self.assertIsNone(persisted.classified_at)
        self.assertIsNone(persisted.railway_distance_checked_at)

    def _add_demo(self, suffix, distance_m):
        name = f"{self.prefix}-{suffix}"
        geom_wkt = self.db.execute(
            text("""
                SELECT ST_AsText(
                    ST_Project(
                        ST_SetSRID(ST_Point(10, 10), 4326)::geography,
                        :distance_m,
                        pi() / 2
                    )::geometry
                )
            """),
            {"distance_m": distance_m},
        ).scalar_one()
        railway = models.RawRailwayPoint(
            geom=WKTElement("POINT(10 10)", srid=4326),
            track_id=uuid.uuid4().hex[:32],
            km=1,
            measure=0.0,
        )
        place = models.CulturePlace(
            name=name,
            type1=models.Type1.human,
            type2=models.Type2.monument,
            origin="demo",
            size_priority=1.0,
            geom=WKTElement(geom_wkt, srid=4326),
        )
        self.db.add_all([railway, place])
        self.db.flush()
        return place


if __name__ == "__main__":
    unittest.main()
