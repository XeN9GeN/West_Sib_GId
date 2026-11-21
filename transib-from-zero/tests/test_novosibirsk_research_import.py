import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_novosibirsk_research import validate_result


class NovosibirskResearchImportTests(unittest.TestCase):
    def _write_jsonl(self, path, records):
        path.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )

    def test_validates_research_rows_and_keeps_duplicate_source_entries(self):
        source = {
            "url": "https://example.org/place",
            "title": "Страница объекта",
            "publisher": "Источник",
            "accessed_at": "2026-11-21",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.jsonl"
            result_path = Path(temp_dir) / "result.jsonl"
            self._write_jsonl(input_path, [
                {"osm_type": "way", "osm_id": 42},
                {"osm_type": "node", "osm_id": 43},
            ])
            self._write_jsonl(result_path, [
                {
                    "schema_version": 1,
                    "osm_type": "way",
                    "osm_id": 42,
                    "status": "ready",
                    "summary_ru": "Проверенная справка.",
                    "sources": [source, source],
                },
                {
                    "schema_version": 1,
                    "osm_type": "node",
                    "osm_id": 43,
                    "status": "no_reliable_sources",
                    "summary_ru": None,
                    "sources": [],
                },
            ])

            ready, statuses = validate_result(input_path, result_path)

        self.assertEqual(statuses, {
            "ready": 1,
            "no_reliable_sources": 1,
            "ambiguous": 0,
        })
        self.assertEqual(ready[0]["sources"], [source, source])

    def test_rejects_research_result_with_mismatched_osm_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.jsonl"
            result_path = Path(temp_dir) / "result.jsonl"
            self._write_jsonl(input_path, [{"osm_type": "way", "osm_id": 42}])
            self._write_jsonl(result_path, [{
                "schema_version": 1,
                "osm_type": "way",
                "osm_id": 99,
                "status": "no_reliable_sources",
                "summary_ru": None,
                "sources": [],
            }])

            with self.assertRaisesRegex(RuntimeError, "не совпадает"):
                validate_result(input_path, result_path)


if __name__ == "__main__":
    unittest.main()
