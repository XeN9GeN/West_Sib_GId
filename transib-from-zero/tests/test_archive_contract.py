import inspect
import unittest

from app import models
from app import migrations
from app.database import SessionLocal, engine
from scripts.enrich_osm import map_osm_tags


class ArchiveContractTests(unittest.TestCase):
    def test_database_exports_and_migration_signature_remain_compatible(self):
        self.assertIsNotNone(SessionLocal)
        self.assertIsNotNone(engine)
        self.assertEqual(
            list(inspect.signature(migrations.ensure_osm_enrichment_schema).parameters),
            ["engine"],
        )

    def test_culture_place_keeps_archive_fields(self):
        expected = {
            "ai_summary",
            "ai_summary_sources",
            "geom",
            "osm_type",
            "osm_id",
            "short_description",
            "history",
        }
        self.assertTrue(expected.issubset(set(models.CulturePlace.__table__.columns.keys())))
        self.assertEqual(str(models.CulturePlace.__table__.columns["ai_summary"].type), "TEXT")
        self.assertEqual(str(models.CulturePlace.__table__.columns["ai_summary_sources"].type), "JSON")

    def test_legacy_osm_tag_mapper_is_still_available(self):
        self.assertTrue(callable(map_osm_tags))


if __name__ == "__main__":
    unittest.main()
