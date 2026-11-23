import unittest

from geoalchemy2.elements import WKTElement

from app import models
from app.description_quality import EffectiveDescription
from app.taxonomy import Classification, load_taxonomy
from scripts.classify_places import (
    _apply_result,
    _distance_meters,
    _find_demo_duplicates,
    _locked_result,
    _pending_result,
    _restore_locked_result,
)


class _DBStub:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)


class ClassifyPlacesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy()

    def test_dry_run_counts_changes_without_mutating_the_row(self):
        place = self._place()
        before = (
            place.category,
            place.subcategory,
            place.excluded_from_map,
            place.exclusion_reason,
            place.classified_at,
            place.railway_distance_m,
        )
        changed, description_changed = _apply_result(
            _DBStub(),
            place,
            _pending_result(self.taxonomy, "test"),
            100.0,
            self.taxonomy,
            EffectiveDescription(None, None, "empty"),
            is_demo=False,
            dry_run=True,
        )
        after = (
            place.category,
            place.subcategory,
            place.excluded_from_map,
            place.exclusion_reason,
            place.classified_at,
            place.railway_distance_m,
        )
        self.assertTrue(changed)
        self.assertTrue(description_changed)
        self.assertEqual(after, before)

    def test_live_apply_updates_classification_and_distance_fields(self):
        place = self._place()
        result = Classification(
            category="heritage",
            subcategory="monuments_memorials",
            object_class="heritage",
            decision="pending_review",
            exclusion_reason="pending_review",
            size_priority=1.2,
            legacy_type1="human",
            legacy_type2="monument",
            evidence=({"rule": "name_only", "fact": "name", "source": "test"},),
            taxonomy_version="1.0",
        )
        changed, _ = _apply_result(
            _DBStub(),
            place,
            result,
            100.0,
            self.taxonomy,
            EffectiveDescription(None, None, "empty"),
            is_demo=False,
            dry_run=False,
        )
        self.assertTrue(changed)
        self.assertEqual(place.category, "heritage")
        self.assertEqual(place.subcategory, "monuments_memorials")
        self.assertEqual(place.exclusion_reason, "pending_review")
        self.assertEqual(place.railway_distance_m, 100.0)
        self.assertIsNotNone(place.railway_distance_checked_at)

    def test_demo_duplicate_matching_uses_distance_name_or_wikidata(self):
        demo = {
            "name": "Новосибирский зоопарк",
            "lon": 82.88,
            "lat": 55.05,
            "wikidata_id": None,
        }
        near_osm = {
            "name": "Новосибирский зоопарк",
            "lon": 82.881,
            "lat": 55.05,
            "osm_type": "way",
            "osm_id": 10,
            "wikidata_id": None,
        }
        wikidata_osm = {
            "name": "Другое название",
            "lon": 90.0,
            "lat": 60.0,
            "osm_type": "relation",
            "osm_id": 11,
            "wikidata_id": "Q123",
        }
        wikidata_demo = dict(demo, wikidata_id="Q123")
        nearby_duplicates = _find_demo_duplicates([demo], [near_osm])
        self.assertEqual(len(nearby_duplicates), 1)
        wikidata_duplicates = _find_demo_duplicates([wikidata_demo], [wikidata_osm])
        self.assertEqual(len(wikidata_duplicates), 1)
        self.assertTrue(wikidata_duplicates[0]["wikidata_match"])

    def test_radius_restore_preserves_locked_pending_decision(self):
        place = self._place()
        place.classification_locked = True
        place.excluded_from_map = True
        place.exclusion_reason = "outside_railway_radius"
        place.classification_evidence = [{"rule": "manual_set_description"}]
        result = _restore_locked_result(
            place,
            self.taxonomy,
            previous_state={
                "excluded_from_map": True,
                "exclusion_reason": "pending_review",
            },
        )
        self.assertEqual(result.decision, "pending_review")
        self.assertEqual(result.exclusion_reason, "pending_review")

    def test_locked_pending_review_remains_pending_in_reports(self):
        place = self._place()
        place.classification_locked = True
        place.excluded_from_map = True
        place.exclusion_reason = "pending_review"
        result = _locked_result(place, self.taxonomy)
        self.assertEqual(result.decision, "pending_review")

    def test_radius_restore_keeps_manual_exclusion(self):
        place = self._place()
        place.classification_locked = True
        place.excluded_from_map = True
        place.exclusion_reason = "outside_railway_radius"
        place.classification_evidence = [{"rule": "manual_exclusion"}]
        result = _restore_locked_result(
            place,
            self.taxonomy,
            previous_state={"excluded_from_map": False, "exclusion_reason": None},
        )
        self.assertEqual(result.decision, "excluded")
        self.assertEqual(result.exclusion_reason, "manual_exclusion")

    def test_radius_restore_keeps_custom_manual_exclusion_reason(self):
        place = self._place()
        place.classification_locked = True
        place.excluded_from_map = True
        place.exclusion_reason = "outside_railway_radius"
        place.classification_evidence = [{"rule": "manual_exclusion"}]
        result = _restore_locked_result(
            place,
            self.taxonomy,
            previous_state={
                "excluded_from_map": True,
                "exclusion_reason": "technical_infrastructure",
            },
        )
        self.assertEqual(result.decision, "excluded")
        self.assertEqual(result.exclusion_reason, "technical_infrastructure")

    def test_distance_helper_uses_geographic_distance(self):
        self.assertAlmostEqual(_distance_meters(10, 10, 10, 10), 0.0)
        self.assertGreater(_distance_meters(10, 10, 10.01, 10), 1000)

    def _place(self):
        return models.CulturePlace(
            id=5,
            name="Тестовый объект",
            type1=models.Type1.human,
            type2=models.Type2.monument,
            geom=WKTElement("POINT(10 10)", srid=4326),
            size_priority=1.0,
            category=None,
            subcategory=None,
            object_class="unclassified",
            excluded_from_map=False,
            exclusion_reason=None,
            classification_locked=False,
            classified_at=None,
            taxonomy_version=None,
            classification_evidence=None,
            railway_distance_m=None,
            railway_distance_checked_at=None,
            effective_description_source=None,
            description_quality=None,
            description_checked_at=None,
        )


if __name__ == "__main__":
    unittest.main()
