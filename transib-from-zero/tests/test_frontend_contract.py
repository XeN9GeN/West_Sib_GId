import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FrontendTaxonomyContractTests(unittest.TestCase):
    def setUp(self):
        self.app_js = (ROOT / "frontend" / "app.js").read_text(
            encoding="utf-8"
        )
        self.index_html = (ROOT / "frontend" / "index.html").read_text(
            encoding="utf-8"
        )
        self.readme = (ROOT / "README.md").read_text(
            encoding="utf-8"
        )

    def test_frontend_loads_zoom_and_cancels_stale_place_requests(self):
        self.assertIn("zoom: String(map.getZoom())", self.app_js)
        self.assertIn("new AbortController()", self.app_js)
        self.assertIn("setTimeout(loadPlaces, 250)", self.app_js)
        self.assertIn("map.on('moveend', schedulePlaceLoad)", self.app_js)
        self.assertIn("map.on('zoomend', loadRailway)", self.app_js)

    def test_frontend_has_no_legacy_taxonomy_dictionaries(self):
        for legacy_name in (
            "type1Labels",
            "type2Labels",
            "type2DescriptionLabels",
        ):
            self.assertNotIn(legacy_name, self.app_js)
        self.assertIn("fetch('/api/taxonomy')", self.app_js)
        self.assertIn("hiddenTypes.category", self.app_js)
        self.assertIn("hiddenTypes.object_class", self.app_js)

    def test_card_uses_effective_description_and_taxonomy_labels(self):
        self.assertIn("place.effective_description", self.app_js)
        self.assertIn(
            "place.effective_description_source !== 'ai_summary'",
            self.app_js,
        )
        self.assertIn("Демонстрационный объект", self.app_js)
        self.assertIn("getSubcategoryLabel", self.app_js)
        self.assertIn("getObjectClassLabel", self.app_js)

    def test_frontend_reports_errors_and_truncated_results(self):
        self.assertIn("X-Truncated", self.app_js)
        self.assertIn("Показана неполная выборка объектов.", self.app_js)
        self.assertIn("Ошибка загрузки легенды:", self.app_js)

    def test_legend_headings_and_search_limitation_contract(self):
        self.assertIn("<h4>Класс</h4>", self.index_html)
        self.assertIn("<h4>Категория</h4>", self.index_html)
        self.assertNotIn("Тип 1 (Nature/Artificial)", self.index_html)
        self.assertNotIn("Тип 2 (Categories)", self.index_html)
        self.assertIn("текущего bbox и zoom", self.readme)


if __name__ == "__main__":
    unittest.main()
