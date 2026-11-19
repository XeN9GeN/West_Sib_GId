import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from app import models
from scripts import enrich_osm
from scripts.enrich_osm import (
    SelectedPOI,
    _match_nearby_binding,
    _parse_creation_date,
    _source_urls,
    map_osm_tags,
)


class OSMEnrichmentTests(unittest.TestCase):
    def test_wikimedia_requests_are_spaced_by_minimum_interval(self):
        with patch.object(
            enrich_osm,
            "_last_wikimedia_request_at",
            100.0,
        ), patch.object(
            enrich_osm.time,
            "monotonic",
            side_effect=[100.2, 100.3],
        ), patch.object(enrich_osm.time, "sleep") as sleep_mock:
            enrich_osm._wait_for_wikimedia_request_slot()

        sleep_mock.assert_called_once()
        self.assertAlmostEqual(sleep_mock.call_args.args[0], 0.8)

    def test_wikidata_429_retries_after_server_delay(self):
        error = HTTPError(
            enrich_osm.WIKIDATA_SPARQL_URL,
            429,
            "Too Many Requests",
            {"Retry-After": "7"},
            io.BytesIO(),
        )
        response = io.BytesIO(json.dumps({"results": {"bindings": []}}).encode())

        with patch.object(
            enrich_osm,
            "urlopen",
            side_effect=[error, response],
        ) as urlopen_mock, patch.object(
            enrich_osm,
            "_wait_for_wikimedia_request_slot",
        ), patch.object(enrich_osm.time, "sleep") as sleep_mock:
            payload = enrich_osm._request_json(enrich_osm.WIKIDATA_SPARQL_URL)

        self.assertEqual(payload, {"results": {"bindings": []}})
        self.assertEqual(urlopen_mock.call_count, 2)
        sleep_mock.assert_called_once_with(7.0)

    def test_osm_tags_map_to_existing_culture_categories(self):
        self.assertEqual(
            map_osm_tags({"tourism": "museum"}),
            (models.Type1.human, models.Type2.museum),
        )
        self.assertEqual(
            map_osm_tags({"natural": "lake"}),
            (models.Type1.nature, models.Type2.lake),
        )
        self.assertEqual(
            map_osm_tags({"natural": "water", "water": "river"}),
            (models.Type1.nature, models.Type2.river),
        )

    def test_coordinate_fallback_requires_close_matching_name(self):
        poi = SelectedPOI(
            id=1,
            osm_type="node",
            osm_id=22,
            name="Омский музей",
            tags={},
            lon=73.37,
            lat=54.99,
        )
        match = {
            "item": {"value": "http://www.wikidata.org/entity/Q42"},
            "labelRuValue": {"value": "Омский музей"},
            "coordinatesValue": {"value": "Point(73.3701 54.9901)"},
        }

        self.assertIs(_match_nearby_binding(poi, [match]), match)
        unrelated = {
            **match,
            "labelRuValue": {"value": "Совсем другой объект"},
        }
        self.assertIsNone(_match_nearby_binding(poi, [unrelated]))

    def test_date_and_source_links_are_preserved(self):
        self.assertEqual(
            _parse_creation_date({"start_date": "1901"}).isoformat(),
            "1901-01-01",
        )
        poi = SelectedPOI(
            id=1,
            osm_type="way",
            osm_id=22,
            name="Музей",
            tags={"wikipedia": "ru:Омский_музей"},
            lon=73.37,
            lat=54.99,
        )

        self.assertEqual(
            _source_urls(poi, {
                "wikidata_id": "Q42",
                "image_page_url": "https://commons.wikimedia.org/wiki/File:Photo.jpg",
            }),
            [
                "https://www.openstreetmap.org/way/22",
                "https://www.wikidata.org/wiki/Q42",
                "https://ru.wikipedia.org/wiki/"
                "%D0%9E%D0%BC%D1%81%D0%BA%D0%B8%D0%B9_%D0%BC%D1%83%D0%B7%D0%B5%D0%B9",
                "https://commons.wikimedia.org/wiki/File:Photo.jpg",
            ],
        )


if __name__ == "__main__":
    unittest.main()
