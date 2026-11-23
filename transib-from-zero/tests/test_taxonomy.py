import ast
from copy import deepcopy
from pathlib import Path
import unittest

from app.taxonomy import (
    LEGACY_TYPE1_VALUES,
    LEGACY_TYPE2_VALUES,
    classify,
    load_taxonomy,
    normalize_name,
    validate_taxonomy,
)


class TaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy()

    def test_normalize_name_uses_nfkc_casefold_yo_and_whitespace(self):
        self.assertEqual(normalize_name("  ЁЛКА\u00a0  Cafe  "), "елка cafe")

    def test_match_language_supports_presence_values_negation_and_names(self):
        facts = {
            "name": "МУЗЕЙ Западно-Сибирской железной дороги",
            "tags": {"tourism": "museum", "museum": "railway"},
        }
        result = classify(facts, self.taxonomy)
        self.assertEqual(result.subcategory, "railway_museums")

        self.assertEqual(
            classify({"name": "Вождь", "tags": {"tourism": "museum"}}, self.taxonomy).subcategory,
            "specialized_museums",
        )
        self.assertEqual(
            classify(
                {"name": "Музей Железнодорожного района", "tags": {"tourism": "museum"}},
                self.taxonomy,
            ).subcategory,
            "historical_museums",
        )

    def test_short_name_token_without_word_boundaries_is_rejected(self):
        taxonomy = deepcopy(self.taxonomy)
        taxonomy["categories"][1]["subcategories"][1]["match"][2]["name_regex"] = "жд"
        with self.assertRaisesRegex(ValueError, "границ"):
            validate_taxonomy(taxonomy)

    def test_unknown_root_key_is_rejected(self):
        taxonomy = deepcopy(self.taxonomy)
        taxonomy["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "Неизвестные ключи"):
            validate_taxonomy(taxonomy)

    def test_duplicate_subcategory_id_and_match_order_are_rejected(self):
        taxonomy = deepcopy(self.taxonomy)
        taxonomy["categories"][1]["subcategories"][0]["id"] = "railway_museums"
        with self.assertRaisesRegex(ValueError, "Повтор id подкатегории"):
            validate_taxonomy(taxonomy)

        taxonomy = deepcopy(self.taxonomy)
        taxonomy["categories"][1]["subcategories"][1]["match_order"] = 10
        with self.assertRaisesRegex(ValueError, "Повтор match_order"):
            validate_taxonomy(taxonomy)

    def test_significance_flag_has_to_be_boolean_and_defaults_to_false(self):
        railway_museum = self._subcategory("railway_museums")
        self.assertFalse(railway_museum.get("trust_ai_summary_as_evidence", False))

        taxonomy = deepcopy(self.taxonomy)
        taxonomy["categories"][1]["subcategories"][1]["trust_ai_summary_as_evidence"] = "true"
        with self.assertRaisesRegex(ValueError, "должен быть boolean"):
            validate_taxonomy(taxonomy)

    def test_must_precede_order_and_legacy_enum_values_are_validated(self):
        taxonomy = deepcopy(self.taxonomy)
        taxonomy["categories"][2]["subcategories"][4]["match_order"] = 34
        with self.assertRaisesRegex(ValueError, "match_order нарушен"):
            validate_taxonomy(taxonomy)

        taxonomy = deepcopy(self.taxonomy)
        taxonomy["categories"][0]["subcategories"][0]["legacy_type2"] = "not_a_type"
        with self.assertRaisesRegex(ValueError, "legacy_type2"):
            validate_taxonomy(taxonomy)

        self.assertIn("human", LEGACY_TYPE1_VALUES)
        self.assertIn("monument", LEGACY_TYPE2_VALUES)

    def test_exclusion_reason_marker_shape_and_overridable_are_required(self):
        taxonomy = deepcopy(self.taxonomy)
        taxonomy["categories"][0]["subcategories"][0]["marker"].pop("shape")
        with self.assertRaisesRegex(ValueError, "marker.*shape"):
            validate_taxonomy(taxonomy)

        taxonomy = deepcopy(self.taxonomy)
        taxonomy["exclude_rules"][0].pop("overridable")
        with self.assertRaisesRegex(ValueError, "overridable"):
            validate_taxonomy(taxonomy)

        taxonomy = deepcopy(self.taxonomy)
        taxonomy["exclude_rules"][0]["reason"] = "not_registered"
        with self.assertRaisesRegex(ValueError, "Неизвестная причина"):
            validate_taxonomy(taxonomy)

    def test_classification_separates_type_name_and_significance(self):
        locomotive = classify(
            {"name": "Паровоз Проворный", "tags": {"historic": "memorial"}},
            self.taxonomy,
        )
        self.assertEqual(locomotive.subcategory, "locomotives_rolling_stock")
        self.assertEqual(locomotive.decision, "pending_review")
        self.assertEqual(locomotive.object_class, "both")

        station = classify(
            {"name": "Станция", "tags": {"building": "train_station"}},
            self.taxonomy,
        )
        self.assertEqual(station.subcategory, "railway_stations_historic")
        self.assertEqual(station.decision, "excluded")
        self.assertEqual(station.exclusion_reason, "insufficient_cultural_significance")

        memorial = classify(
            {"name": "Памятник", "tags": {"historic": "memorial", "heritage": "98"}},
            self.taxonomy,
        )
        self.assertEqual(memorial.decision, "pending_review")

        protected = classify(
            {"name": "Охраняемый вокзал", "tags": {"building": "train_station", "heritage": "4"}},
            self.taxonomy,
        )
        self.assertEqual(protected.decision, "include")
        self.assertEqual(protected.object_class, "both")
        self.assertEqual(protected.evidence[0]["rule"], "heritage_status")

    def test_name_wikidata_id_and_description_do_not_prove_significance(self):
        result = classify(
            {
                "name": "Известное место",
                "wikidata_id": "Q123",
                "quality_description": "ok",
                "tags": {"historic": "memorial"},
            },
            self.taxonomy,
        )
        self.assertEqual(result.decision, "pending_review")
        self.assertEqual(result.evidence, ())

    def test_ai_summary_significance_requires_all_three_permission_levels(self):
        taxonomy = deepcopy(self.taxonomy)
        railway_museum = next(
            subcategory
            for category in taxonomy["categories"]
            for subcategory in category["subcategories"]
            if subcategory["id"] == "railway_museums"
        )
        railway_museum["trust_ai_summary_as_evidence"] = True
        facts = {
            "name": "Железнодорожный музей",
            "tags": {"tourism": "museum", "museum": "railway"},
            "ai_summary": "Подтверждённое владельцем описание",
            "ai_summary_sources": [{
                "url": "https://example.org/railway-museum",
                "title": "Источник",
                "publisher": "Издатель",
                "accessed_at": "2026-01-01",
            }],
            "ai_summary_significance_verified": True,
        }
        result = classify(facts, taxonomy)
        self.assertEqual(result.decision, "include")
        self.assertEqual(result.evidence[0]["rule"], "researched_ai_summary")

        facts["ai_summary_significance_verified"] = False
        result = classify(facts, taxonomy)
        self.assertEqual(result.decision, "pending_review")

    def test_mkrf_is_weak_and_only_applies_to_cultural_institutions(self):
        museum = classify(
            {
                "name": "Музей",
                "tags": {
                    "tourism": "museum",
                    "website": "https://museum.example",
                    "ref:mkrf_museums": "123",
                },
            },
            self.taxonomy,
        )
        self.assertEqual(museum.decision, "include")
        self.assertIn("mkrf_registry", {item["rule"] for item in museum.evidence})

        memorial = classify(
            {
                "name": "Памятник",
                "tags": {
                    "historic": "memorial",
                    "website": "https://museum.example",
                    "ref:mkrf_museums": "123",
                },
            },
            self.taxonomy,
        )
        self.assertEqual(memorial.decision, "pending_review")
        self.assertNotIn("mkrf_registry", {item["rule"] for item in memorial.evidence})

    def test_religious_tag_does_not_assign_heritage_class(self):
        mosque = classify(
            {"name": "Мечеть", "tags": {"amenity": "place_of_worship", "religion": "muslim"}},
            self.taxonomy,
        )
        self.assertEqual(mosque.subcategory, "mosques")
        self.assertEqual(mosque.object_class, "unclassified")
        self.assertEqual(mosque.decision, "pending_review")

    def test_only_selected_exclusion_rules_can_be_overridden(self):
        result = classify(
            {"name": "Тигр", "tags": {"attraction": "animal"}},
            self.taxonomy,
        )
        self.assertEqual(result.exclusion_reason, "individual_zoo_animal_or_enclosure")
        self.assertFalse(self._rule("zoo_animal_or_enclosure")["overridable"])
        self.assertTrue(self._rule("auditorium")["overridable"])

    def test_taxonomy_module_does_not_import_models(self):
        source = Path(__file__).parents[1] / "app" / "taxonomy.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertNotIn("app.models", imports)
        self.assertNotIn("models", imports)

    def _subcategory(self, subcategory_id):
        return next(
            subcategory
            for category in self.taxonomy["categories"]
            for subcategory in category["subcategories"]
            if subcategory["id"] == subcategory_id
        )

    def _rule(self, rule_id):
        return next(rule for rule in self.taxonomy["exclude_rules"] if rule["id"] == rule_id)


if __name__ == "__main__":
    unittest.main()
