import unittest

from app import models
from app.taxonomy import load_taxonomy
from scripts import import_osm_pbf
from scripts.enrich_osm import (
    _classify_promotion_candidate,
    _culture_place_row,
)


class ImportTaxonomyTests(unittest.TestCase):
    def test_pbf_filters_include_target_objects_without_all_stations(self):
        expected = {
            "nwr/building=train_station",
            "nwr/railway=museum",
            "nwr/leisure=nature_reserve",
            "nwr/boundary=protected_area",
            "nwr/boundary=national_park",
        }

        self.assertTrue(expected.issubset(import_osm_pbf.OSM_TAG_FILTERS))
        self.assertNotIn("nwr/railway=station", import_osm_pbf.OSM_TAG_FILTERS)

    def test_description_source_preserves_existing_precedence(self):
        cases = (
            ({"description:ru": "Из OSM"}, None, None, None, "osm_description_ru"),
            ({}, "Из Википедии", "Из Wikidata", "Из Wikivoyage", "wikipedia"),
            ({}, None, "Из Wikidata", "Из Wikivoyage", "wikidata"),
            ({"description": "Из OSM"}, None, None, "Из Wikivoyage", "osm_description"),
            ({}, None, None, "Из Wikivoyage", "wikivoyage"),
        )

        for tags, wikipedia, wikidata, wikivoyage, expected_source in cases:
            with self.subTest(expected_source=expected_source):
                poi = models.OSMPOI(
                    osm_type="node",
                    osm_id=1,
                    tags={"name": "Объект", **tags},
                    wikipedia_extract=wikipedia,
                    wikidata_description=wikidata,
                    wikivoyage_extract=wikivoyage,
                )

                row = _culture_place_row(poi, 73.37, 54.99)

                self.assertEqual(row["description_source"], expected_source)

    def test_promotion_classifies_hard_exclusions_from_taxonomy(self):
        poi = models.OSMPOI(
            osm_type="way",
            osm_id=2,
            tags={"highway": "footway", "name": "Пешеходная дорожка"},
        )

        result = _classify_promotion_candidate(poi, load_taxonomy())

        self.assertEqual(result.exclusion_reason, "unsupported_object_type")
        self.assertEqual(result.evidence[0]["rule"], "path_or_road")


if __name__ == "__main__":
    unittest.main()
