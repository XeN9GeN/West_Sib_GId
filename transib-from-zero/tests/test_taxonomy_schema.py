import inspect
import unittest

from sqlalchemy import Boolean, DateTime, Float, JSON, String
from sqlalchemy.schema import CreateIndex

from app import models
from app.migrations import ensure_taxonomy_schema
from app.queries import VISIBLE_CONDITION
from app.taxonomy import load_taxonomy
from scripts.import_osm import IMPORT_RADIUS_METERS


class TaxonomySchemaTests(unittest.TestCase):
    def test_existing_enum_is_unchanged_and_taxonomy_fields_are_additive(self):
        self.assertEqual(
            {item.value for item in models.Type2},
            {
                "museum",
                "monument",
                "architecture",
                "theater",
                "temple",
                "lake",
                "river",
                "reserve",
                "forest",
                "historic_nature",
            },
        )
        columns = models.CulturePlace.__table__.columns
        expected = {
            "category",
            "subcategory",
            "object_class",
            "excluded_from_map",
            "exclusion_reason",
            "classification_locked",
            "classified_at",
            "taxonomy_version",
            "classification_evidence",
            "ai_summary_significance_verified",
            "railway_distance_m",
            "railway_distance_checked_at",
            "description_source",
            "effective_description_source",
            "description_quality",
            "description_checked_at",
            "origin",
        }
        self.assertTrue(expected.issubset(set(columns.keys())))
        self.assertTrue(columns["origin"].nullable)
        self.assertEqual(str(columns["origin"].server_default.arg), "osm")

    def test_audit_and_exclusion_registry_keep_required_constraints(self):
        audit = models.ClassificationAuditLog.__table__
        self.assertEqual(
            set(audit.columns.keys()),
            {
                "id",
                "culture_place_id",
                "osm_type",
                "osm_id",
                "action",
                "actor",
                "old_value",
                "new_value",
                "note",
                "created_at",
            },
        )
        registry = models.OSMPOIExclusionRegistry.__table__
        self.assertTrue(registry.columns["osm_poi_id"].unique)
        fk = next(iter(registry.columns["osm_poi_id"].foreign_keys))
        self.assertEqual(fk.target_fullname, "osm_pois.id")
        self.assertEqual(fk.ondelete, "RESTRICT")
        self.assertTrue(any(index.name == "idx_osm_poi_exclusion_registry_active" for index in registry.indexes))

    def test_column_types_are_compatible_with_taxonomy_contract(self):
        columns = models.CulturePlace.__table__.columns
        self.assertIsInstance(columns["category"].type, String)
        self.assertEqual(columns["category"].type.length, 48)
        self.assertEqual(columns["subcategory"].type.length, 64)
        self.assertIsInstance(columns["object_class"].type, String)
        self.assertIsInstance(columns["classification_evidence"].type, JSON)
        self.assertIsInstance(columns["excluded_from_map"].type, Boolean)
        self.assertIsInstance(columns["railway_distance_m"].type, Float)
        self.assertTrue(columns["classified_at"].type.timezone)
        self.assertIsInstance(columns["classified_at"].type, DateTime)

    def test_partial_visibility_index_and_single_shared_predicate(self):
        index = next(
            index
            for index in models.CulturePlace.__table__.indexes
            if index.name == "idx_culture_place_visible"
        )
        predicate = str(index.dialect_options["postgresql"]["where"])
        self.assertIn("excluded_from_map = false", predicate)
        self.assertIn("classified_at IS NOT NULL", predicate)
        self.assertIn("railway_distance_m IS NOT NULL", predicate)
        self.assertEqual(
            VISIBLE_CONDITION.split(),
            [
                "excluded_from_map", "=", "false", "AND", "classified_at", "IS",
                "NOT", "NULL", "AND", "railway_distance_checked_at", "IS", "NOT",
                "NULL", "AND", "railway_distance_m", "IS", "NOT", "NULL",
            ],
        )
        self.assertEqual(
            list(inspect.signature(ensure_taxonomy_schema).parameters),
            ["engine"],
        )

    def test_import_default_radius_comes_from_taxonomy_config(self):
        self.assertEqual(
            IMPORT_RADIUS_METERS,
            load_taxonomy()["settings"]["railway_radius_meters"],
        )


if __name__ == "__main__":
    unittest.main()
