import unittest

from app.description_quality import assess_description, pick_effective_description
from app.taxonomy import load_taxonomy


class DescriptionQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_taxonomy()["settings"]
        cls.description_config = cls.config["description"]

    def test_empty_placeholders_name_and_thresholds(self):
        cases = [
            (None, "Объект", "empty"),
            ("   ", "Объект", "empty"),
            ("Музей в Омске", "Объект", "placeholder"),
            ("Церковь", "Церковь", "same_as_name"),
            (            "Короткое описание!!!", "Объект", "too_short"),
            (
                "Историко-культурное описание достопримечательности региона",
                "Объект",
                "too_few_words",
            ),
            (
                "This is a sufficiently long English description without Russian text.",
                "Place",
                "not_russian",
            ),
        ]
        for text, name, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(
                    assess_description(text, name, self.description_config),
                    expected,
                )

    def test_sufficient_russian_description_and_trusted_manual_description(self):
        description = (
            "Это содержательное описание достопримечательности, "
            "в котором подробно рассказана история здания и его значение."
        )
        self.assertEqual(
            assess_description(description, "Музей", self.description_config),
            "ok",
        )
        self.assertEqual(
            assess_description("Короткое ручное описание.", "Музей", self.description_config, trusted=True),
            "ok_manual",
        )

    def test_effective_description_uses_order_quality_and_manual_source(self):
        history = (
            "Это содержательное описание истории объекта, его создания, "
            "архитектуры и значения для города."
        )
        short_description = (
            "Краткое, но достаточно содержательное описание музея, "
            "рассказывающее о его коллекции и истории."
        )
        result = pick_effective_description(
            {"history": history, "short_description": short_description},
            "Музей",
            self.config,
        )
        self.assertEqual(result.effective_description_source, "history")
        self.assertEqual(result.description_quality, "ok")

        result = pick_effective_description(
            {
                "history": "Церковь",
                "short_description": "Ручной текст.",
                "description_source": "manual",
            },
            "Церковь",
            self.config,
        )
        self.assertEqual(result.effective_description_source, "short_description")
        self.assertEqual(result.description_quality, "ok_manual")

    def test_ai_summary_requires_switches_valid_sources_and_never_replaces_short_text(self):
        summary = (
            "Это содержательная исследованная сводка об объекте, "
            "его истории, архитектуре и культурном значении."
        )
        source = {
            "url": "https://example.org/object",
            "title": "Источник",
            "publisher": "Издатель",
            "accessed_at": "2026-01-01",
        }
        candidates = {
            "history": "Церковь",
            "short_description": "Также слишком короткий текст.",
            "ai_summary": summary,
            "ai_summary_sources": [source],
        }
        result = pick_effective_description(candidates, "Церковь", self.config)
        self.assertEqual(result.effective_description, summary)
        self.assertEqual(result.effective_description_source, "ai_summary")
        self.assertNotIn("short_description", result.effective_description)

        without_sources = dict(candidates, ai_summary_sources=[])
        result = pick_effective_description(without_sources, "Церковь", self.config)
        self.assertIsNone(result.effective_description)
        self.assertEqual(result.description_quality, "same_as_name")

        disabled = dict(self.config)
        disabled["description"] = dict(self.config["description"], accept_ai_summary=False)
        result = pick_effective_description(candidates, "Церковь", disabled)
        self.assertIsNone(result.effective_description)

    def test_ai_sources_reject_credentials_wrong_scheme_and_extra_fields(self):
        summary = (
            "Это содержательная исследованная сводка об объекте, "
            "его истории, архитектуре и культурном значении."
        )
        source = {
            "url": "https://user:pass@example.org/object",
            "title": "Источник",
            "publisher": "Издатель",
            "accessed_at": "2026-01-01",
        }
        result = pick_effective_description(
            {
                "history": "Церковь",
                "ai_summary": summary,
                "ai_summary_sources": [source],
            },
            "Церковь",
            self.config,
        )
        self.assertIsNone(result.effective_description)

        source["url"] = "http://example.org/object"
        result = pick_effective_description(
            {
                "history": "Церковь",
                "ai_summary": summary,
                "ai_summary_sources": [source],
            },
            "Церковь",
            self.config,
        )
        self.assertIsNone(result.effective_description)

        source["url"] = "https://example.org/object"
        source["extra"] = "not allowed"
        result = pick_effective_description(
            {
                "history": "Церковь",
                "ai_summary": summary,
                "ai_summary_sources": [source],
            },
            "Церковь",
            self.config,
        )
        self.assertIsNone(result.effective_description)

    def test_all_bad_candidates_return_first_nonempty_rejection(self):
        result = pick_effective_description(
            {"history": "Церковь", "short_description": "Музей"},
            "Объект",
            self.config,
        )
        self.assertIsNone(result.effective_description)
        self.assertEqual(result.effective_description_source, None)
        self.assertEqual(result.description_quality, "placeholder")


if __name__ == "__main__":
    unittest.main()
