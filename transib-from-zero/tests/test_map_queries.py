import copy
import unittest

from sqlalchemy.dialects import postgresql

from app.queries import (
    build_culture_places_count_query,
    build_culture_places_query,
    build_marker,
    build_result_count_headers,
    build_taxonomy_response,
    effective_description_expression,
    min_priority_for_zoom,
    parse_bbox,
)
from app.schemas import CulturePlaceOut, MarkerStyle
from app.taxonomy import load_taxonomy


class MapQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy()

    def test_bbox_is_validated_and_normalized(self):
        self.assertEqual(parse_bbox(" 10, 20, 30, 40 "), (10.0, 20.0, 30.0, 40.0))
        invalid_values = (
            "",
            "1,2,3",
            "1,2,3,4,5",
            "nan,2,3,4",
            "1,2,inf,4",
            "181,2,190,4",
            "1,-91,3,4",
            "3,2,1,4",
            "1,4,3,2",
        )
        for value in invalid_values:
            with self.subTest(bbox=value), self.assertRaises(ValueError):
                parse_bbox(value)

    def test_priority_tier_boundaries_are_inclusive(self):
        expected = {
            7: 2.5,
            8: 1.8,
            10: 1.8,
            11: 1.2,
            12: 1.2,
            13: 0.0,
            22: 0.0,
        }
        for zoom, threshold in expected.items():
            with self.subTest(zoom=zoom):
                self.assertEqual(
                    min_priority_for_zoom(zoom, self.taxonomy),
                    threshold,
                )

    def test_query_includes_visibility_bbox_filters_zoom_and_ordering(self):
        query = build_culture_places_query(
            "-10,-20,30,40",
            zoom=11,
            category=["railway_heritage"],
            subcategory=["railway_museums"],
            object_class=["both"],
            type1=["human"],
            type2=["museum"],
            taxonomy=self.taxonomy,
        )
        sql = str(query.compile(dialect=postgresql.dialect()))

        self.assertIn("excluded_from_map = false", sql)
        self.assertIn("railway_distance_checked_at IS NOT NULL", sql)
        self.assertIn("ST_Within", sql)
        self.assertIn("culture_place.origin = ", sql)
        self.assertIn("culture_place.category IS NOT NULL", sql)
        self.assertIn("culture_place.object_class !=", sql)
        self.assertIn("category IN", sql)
        self.assertIn("subcategory IN", sql)
        self.assertIn("object_class IN", sql)
        self.assertIn("type1 IN", sql)
        self.assertIn("type2 IN", sql)
        self.assertIn("effective_description_source IS NOT NULL", sql)
        self.assertIn("description_quality IN", sql)
        self.assertIn("ORDER BY culture_place.size_priority DESC, culture_place.id ASC", sql)

    def test_zoom_below_description_threshold_keeps_description_filter_off(self):
        query = build_culture_places_query(
            "-10,-20,30,40",
            zoom=10,
            taxonomy=self.taxonomy,
        )
        sql = str(query.compile(dialect=postgresql.dialect()))

        self.assertIn("size_priority >=", sql)
        self.assertNotIn("effective_description_source IS NOT NULL", sql)
        self.assertNotIn("description_quality IN", sql)

    def test_demo_priority_cap_is_applied_only_when_configured(self):
        taxonomy = copy.deepcopy(self.taxonomy)
        taxonomy["settings"]["demo"]["priority_cap"] = 1.5

        query = build_culture_places_query(
            "-10,-20,30,40",
            zoom=6,
            taxonomy=taxonomy,
        )
        sql = str(query.compile(dialect=postgresql.dialect())).lower()

        self.assertIn("least(culture_place.size_priority", sql)
        self.assertIn("culture_place.origin = ", sql)

    def test_count_query_uses_the_same_filters(self):
        query = build_culture_places_count_query(
            "-10,-20,30,40",
            zoom=8,
            category=["railway_heritage"],
            taxonomy=self.taxonomy,
        )
        sql = str(query.compile(dialect=postgresql.dialect()))

        self.assertIn("count(*)", sql.lower())
        self.assertIn("category IN", sql)
        self.assertIn("ST_Within", sql)
        self.assertIn("excluded_from_map = false", sql)

    def test_effective_description_is_selected_from_its_declared_source(self):
        sql = str(
            effective_description_expression().compile(
                dialect=postgresql.dialect()
            )
        )

        self.assertIn("CASE", sql)
        self.assertIn("effective_description_source", sql)
        self.assertIn("WHEN", sql)
        self.assertIn("history", sql)
        self.assertIn("short_description", sql)
        self.assertIn("ai_summary", sql)

    def test_taxonomy_response_contains_yaml_categories_and_subcategories(self):
        payload = build_taxonomy_response(self.taxonomy)
        expected_subcategories = {
            item["id"]
            for category in self.taxonomy["categories"]
            for item in category["subcategories"]
        }
        returned_subcategories = {
            item["id"]
            for category in payload["categories"]
            for item in category["subcategories"]
        }

        self.assertEqual(payload["version"], self.taxonomy["version"])
        self.assertEqual(
            payload["description_required_from_zoom"],
            self.taxonomy["settings"]["zoom"]["description_required_from_zoom"],
        )
        self.assertEqual(expected_subcategories, returned_subcategories)
        self.assertEqual(
            {item["id"] for item in payload["object_classes"]},
            set(self.taxonomy["object_classes"]),
        )
        for category, source in zip(payload["categories"], self.taxonomy["categories"]):
            marker = source["subcategories"][0]["marker"]
            self.assertEqual(category["color"], marker["color"])
            self.assertEqual(category["icon"], marker["icon"])
            self.assertEqual(category["subcategories"][0]["marker"], marker)
        self.assertEqual(payload["demo"], self.taxonomy["settings"]["demo"])

    def test_marker_uses_yaml_and_falls_back_to_legacy(self):
        legacy = {"color": "#000000", "icon": "fa-circle", "shape": "pin"}

        self.assertEqual(
            build_marker(self.taxonomy, "railway_museums", legacy),
            {
                "color": "#6c3483",
                "icon": "fa-train-subway",
                "shape": "pin",
            },
        )
        self.assertEqual(build_marker(self.taxonomy, None, legacy), legacy)
        self.assertEqual(build_marker(self.taxonomy, "unknown", legacy), legacy)

    def test_response_schema_additions_are_optional_and_legacy_fields_remain(self):
        place = CulturePlaceOut(
            id=1,
            name="Тест",
            type1="human",
            type2="museum",
            lat=10,
            lon=20,
            size_priority=1,
            marker=MarkerStyle(color="#000000", icon="fa-circle", shape="pin"),
        )

        self.assertIsNone(place.category)
        self.assertIsNone(place.subcategory)
        self.assertIsNone(place.object_class)
        self.assertIsNone(place.description_source)
        self.assertIsNone(place.effective_description)
        self.assertIsNone(place.effective_description_source)
        self.assertIsNone(place.origin)
        self.assertEqual(place.type1, "human")
        self.assertEqual(place.type2, "museum")
        self.assertEqual(place.marker.shape, "pin")

    def test_count_headers_report_truncation_and_returned_count(self):
        self.assertEqual(
            build_result_count_headers(120, 50),
            {
                "X-Truncated": "true",
                "X-Total-Count": "120",
                "X-Returned-Count": "50",
            },
        )
        self.assertEqual(
            build_result_count_headers(50, 50)["X-Truncated"],
            "false",
        )

    def test_invalid_filter_values_are_rejected(self):
        with self.assertRaises(ValueError):
            build_culture_places_query(
                "-10,-20,30,40",
                category=["not-a-category"],
                taxonomy=self.taxonomy,
            )
        with self.assertRaises(ValueError):
            build_culture_places_query(
                "-10,-20,30,40",
                type2=["not-an-enum-value"],
                taxonomy=self.taxonomy,
            )


if __name__ == "__main__":
    unittest.main()
