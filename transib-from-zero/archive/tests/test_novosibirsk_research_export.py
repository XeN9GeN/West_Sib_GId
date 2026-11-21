import json
import unittest

from scripts.export_novosibirsk_research import _input_record


class NovosibirskResearchExportTests(unittest.TestCase):
    def test_input_record_keeps_osm_identity_and_source_links(self):
        record = _input_record({
            "osm_type": "way",
            "osm_id": 123,
            "name": "Музей",
            "type1": "human",
            "type2": "museum",
            "lat": 55.00000001,
            "lon": 82.90000001,
            "tags_json": json.dumps({"wikipedia": "ru:Тестовая_статья"}),
            "wikidata_id": "Q42",
            "wikipedia_url": None,
            "wikivoyage_url": None,
            "image_page_url": None,
            "sources": ["https://example.org/source"],
        })

        self.assertEqual((record["osm_type"], record["osm_id"]), ("way", 123))
        self.assertEqual((record["lat"], record["lon"]), (55.0, 82.9))
        self.assertIn("https://www.openstreetmap.org/way/123", record["existing_sources"])
        self.assertIn("https://www.wikidata.org/wiki/Q42", record["existing_sources"])
        self.assertIn(
            "https://ru.wikipedia.org/wiki/"
            "%D0%A2%D0%B5%D1%81%D1%82%D0%BE%D0%B2%D0%B0%D1%8F_"
            "%D1%81%D1%82%D0%B0%D1%82%D1%8C%D1%8F",
            record["existing_sources"],
        )
        self.assertIn("https://example.org/source", record["existing_sources"])


if __name__ == "__main__":
    unittest.main()
