import unittest
from datetime import datetime, timezone

from app import models
from scripts.manage_places import _snapshot


class ManagePlacesTests(unittest.TestCase):
    def test_audit_snapshot_serializes_all_changed_manual_fields(self):
        classified_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        place = models.CulturePlace(
            category="heritage",
            subcategory="monuments_memorials",
            object_class="heritage",
            type1=models.Type1.human,
            type2=models.Type2.monument,
            excluded_from_map=True,
            exclusion_reason="manual_exclusion",
            classification_locked=True,
            size_priority=1.2,
            classification_evidence=[{"rule": "manual_exclusion"}],
            taxonomy_version="2.2",
            classified_at=classified_at,
            short_description="Ручное описание",
            description_source="manual",
            effective_description_source="short_description",
            description_quality="ok_manual",
            description_checked_at=classified_at,
            ai_summary_significance_verified=True,
        )
        snapshot = _snapshot(place)
        self.assertEqual(snapshot["type1"], "human")
        self.assertEqual(snapshot["type2"], "monument")
        self.assertEqual(snapshot["classified_at"], classified_at.isoformat())
        self.assertEqual(snapshot["short_description"], "Ручное описание")
        self.assertTrue(snapshot["ai_summary_significance_verified"])


if __name__ == "__main__":
    unittest.main()
