import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from app import models
from scripts import enrich_osm
from scripts.enrich_osm import (
    SelectedPOI,
    _culture_place_row,
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

    def test_wikipedia_tag_fetches_intro_and_linked_wikidata_id(self):
        poi = SelectedPOI(
            id=5,
            osm_type="way",
            osm_id=22,
            name="Музей",
            tags={"wikipedia": "ru:Старая_страница"},
            lon=73.37,
            lat=54.99,
        )
        response = {
            "query": {
                "redirects": [
                    {"from": "Старая страница", "to": "Статья музея"},
                ],
                "pages": [{
                    "title": "Статья музея",
                    "extract": "Краткое описание музея.",
                    "pageprops": {"wikibase_item": "Q42"},
                }],
            },
        }

        with patch.object(enrich_osm, "_request_json", return_value=response):
            extracts = enrich_osm.fetch_wikipedia_extracts([poi])

        self.assertEqual(
            extracts[5],
            {
                "wikipedia_extract": "Краткое описание музея.",
                "wikidata_id": "Q42",
                "wikipedia_url": (
                    "https://ru.wikipedia.org/wiki/"
                    "%D0%A1%D1%82%D0%B0%D1%82%D1%8C%D1%8F_%D0%BC%D1%83%D0%B7%D0%B5%D1%8F"
                ),
            },
        )

    def test_wikipedia_extract_is_limited_to_short_intro(self):
        long_text = ("А" * 300 + ". ") * 4

        extract = enrich_osm._short_wiki_extract(long_text)

        self.assertLessEqual(len(extract), enrich_osm.WIKI_ARTICLE_EXTRACT_MAX_CHARS)
        self.assertTrue(extract.endswith("."))

    def test_wikipedia_extract_is_used_as_description_and_has_source_link(self):
        poi = models.OSMPOI(
            osm_type="way",
            osm_id=22,
            tags={"name": "Музей", "wikipedia": "ru:Статья_музея"},
            wikipedia_extract="Краткое описание из статьи.",
            wikipedia_url="https://ru.wikipedia.org/wiki/Статья_музея",
        )

        row = _culture_place_row(poi, 73.37, 54.99)

        self.assertEqual(row["short_description"], "Краткое описание из статьи.")
        self.assertIn(
            "https://ru.wikipedia.org/wiki/Статья_музея",
            row["sources"],
        )

    def test_wikivoyage_extract_uses_exact_wikidata_sitelink(self):
        poi = SelectedPOI(
            id=9,
            osm_type="node",
            osm_id=27,
            name="Музей",
            tags={},
            lon=73.37,
            lat=54.99,
            wikidata_id="Q42",
        )
        responses = [
            {
                "entities": {
                    "Q42": {
                        "sitelinks": {
                            "ruwikivoyage": {"title": "Омск/Достопримечательности"},
                        },
                    },
                },
            },
            {
                "query": {
                    "pages": [{
                        "title": "Омск/Достопримечательности",
                        "extract": "Путеводная статья об объекте.",
                        "pageprops": {"wikibase_item": "Q42"},
                    }],
                },
            },
        ]

        with patch.object(
            enrich_osm,
            "_request_json",
            side_effect=responses,
        ) as request_mock:
            extracts = enrich_osm.fetch_wikivoyage_extracts([poi])

        self.assertEqual(
            extracts[9],
            {
                "wikivoyage_extract": "Путеводная статья об объекте.",
                "wikivoyage_url": (
                    "https://ru.wikivoyage.org/wiki/"
                    "%D0%9E%D0%BC%D1%81%D0%BA%2F%D0%94%D0%BE%D1%81%D1%82"
                    "%D0%BE%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%87%D0%B0%D1%82"
                    "%D0%B5%D0%BB%D1%8C%D0%BD%D0%BE%D1%81%D1%82%D0%B8"
                ),
            },
        )
        self.assertEqual(request_mock.call_count, 2)

    def test_wikivoyage_osm_tag_fetches_article_without_wikidata(self):
        poi = SelectedPOI(
            id=11,
            osm_type="node",
            osm_id=30,
            name="Музей",
            tags={"wikivoyage": "ru:Музей_в_Омске"},
            lon=73.37,
            lat=54.99,
        )
        response = {
            "query": {
                "pages": [{
                    "title": "Музей в Омске",
                    "extract": "Описание по прямой ссылке из OSM.",
                    "pageprops": {},
                }],
            },
        }

        with patch.object(enrich_osm, "_request_json", return_value=response):
            extracts = enrich_osm.fetch_wikivoyage_extracts([poi])

        self.assertEqual(
            extracts[11]["wikivoyage_extract"],
            "Описание по прямой ссылке из OSM.",
        )
        self.assertEqual(
            extracts[11]["wikivoyage_url"],
            "https://ru.wikivoyage.org/wiki/%D0%9C%D1%83%D0%B7%D0%B5%D0%B9_"
            "%D0%B2_%D0%9E%D0%BC%D1%81%D0%BA%D0%B5",
        )

    def test_wikivoyage_is_skipped_when_object_already_has_description(self):
        poi = SelectedPOI(
            id=10,
            osm_type="node",
            osm_id=28,
            name="Музей",
            tags={"description": "Описание уже есть."},
            lon=73.37,
            lat=54.99,
            wikidata_id="Q42",
        )

        with patch.object(enrich_osm, "_request_json") as request_mock:
            extracts = enrich_osm.fetch_wikivoyage_extracts([poi])

        self.assertEqual(extracts, {})
        request_mock.assert_not_called()

    def test_wikivoyage_extract_is_promoted_as_last_description_fallback(self):
        poi = models.OSMPOI(
            osm_type="way",
            osm_id=29,
            tags={"name": "Музей"},
            wikivoyage_extract="Текст из путеводителя.",
            wikivoyage_url="https://ru.wikivoyage.org/wiki/Омск",
        )

        row = _culture_place_row(poi, 73.37, 54.99)

        self.assertEqual(row["short_description"], "Текст из путеводителя.")
        self.assertIn("https://ru.wikivoyage.org/wiki/Омск", row["sources"])


if __name__ == "__main__":
    unittest.main()
