"""Enrich selected OSM places with Wikidata and promote them to culture_place."""

import argparse
import difflib
import html
import json
import math
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, unquote
from urllib.request import Request, urlopen

from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, case, func, or_, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert

from app import models
from app.database import Base, SessionLocal, engine
from app.migrations import ensure_osm_enrichment_schema, ensure_taxonomy_schema
from app.taxonomy import classify, load_taxonomy


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
REQUEST_TIMEOUT_SECONDS = 60
COORDINATE_MATCH_RADIUS_KM = 0.1
DIRECT_QUERY_BATCH_SIZE = 100
COORDINATE_QUERY_BATCH_SIZE = 20
COMMONS_QUERY_BATCH_SIZE = 50
WIKI_ARTICLE_QUERY_BATCH_SIZE = 20
WIKIDATA_ENTITY_BATCH_SIZE = 50
WIKI_ARTICLE_EXTRACT_MAX_CHARS = 800
BATCH_SIZE = 500
WIKIMEDIA_MIN_REQUEST_INTERVAL_SECONDS = 1.0
WIKIMEDIA_MAX_RETRIES = 5
WIKIMEDIA_RETRY_DELAY_SECONDS = 5
WIKIMEDIA_DEFAULT_429_DELAY_SECONDS = 60
WIKIMEDIA_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
USER_AGENT = (
    "West-Sib-GId/1.0 (OSM/Wikidata importer; "
    "https://github.com/XeN9GeN/West_Sib_GId)"
)
_last_wikimedia_request_at = None


@dataclass
class SelectedPOI:
    id: int
    osm_type: str
    osm_id: int
    name: str
    tags: dict
    lon: float
    lat: float
    wikidata_id: str = None
    wikidata_description: str = None
    wikipedia_extract: str = None
    wikivoyage_extract: str = None
    wikivoyage_url: str = None


def _wait_for_wikimedia_request_slot():
    global _last_wikimedia_request_at
    now = time.monotonic()
    if _last_wikimedia_request_at is not None:
        elapsed = now - _last_wikimedia_request_at
        delay = WIKIMEDIA_MIN_REQUEST_INTERVAL_SECONDS - elapsed
        if delay > 0:
            time.sleep(delay)
    _last_wikimedia_request_at = time.monotonic()


def _retry_after_seconds(value):
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _request_json(url, data=None, accept="application/json"):
    last_error = None
    retry_after = None

    for attempt in range(WIKIMEDIA_MAX_RETRIES + 1):
        request = Request(
            url,
            data=data,
            headers={"User-Agent": USER_AGENT, "Accept": accept},
            method="POST" if data is not None else "GET",
        )
        _wait_for_wikimedia_request_slot()
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in WIKIMEDIA_RETRYABLE_STATUS_CODES:
                raise RuntimeError(
                    f"HTTP {exc.code} при запросе к {url}: {exc.reason}"
                ) from exc
            last_error = exc
            retry_after = _retry_after_seconds(exc.headers.get("Retry-After"))
            exc.close()
        except (URLError, TimeoutError) as exc:
            last_error = exc
            retry_after = None
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Сервис вернул некорректный JSON: {url}") from exc

        if attempt >= WIKIMEDIA_MAX_RETRIES:
            break

        if retry_after is not None:
            delay = retry_after
        elif isinstance(last_error, HTTPError) and last_error.code == 429:
            delay = WIKIMEDIA_DEFAULT_429_DELAY_SECONDS
        else:
            delay = WIKIMEDIA_RETRY_DELAY_SECONDS * (2 ** attempt)

        print(
            f"Внешний сервис ограничил или прервал запрос к {url}; "
            f"повтор через {delay:.0f} сек. "
            f"({attempt + 1}/{WIKIMEDIA_MAX_RETRIES})."
        )
        time.sleep(delay)

    raise RuntimeError(
        f"Не удалось выполнить запрос к {url} после "
        f"{WIKIMEDIA_MAX_RETRIES} повторов. Последняя ошибка: {last_error}"
    ) from last_error


def _query_wikidata(query):
    payload = _request_json(
        WIKIDATA_SPARQL_URL,
        data=urlencode({"query": query, "format": "json"}).encode("utf-8"),
        accept="application/sparql-results+json",
    )
    try:
        return payload["results"]["bindings"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Wikidata вернул ответ неожиданного формата.") from exc


def _metadata_query(pattern, group_by):
    return f"""
        PREFIX bd: <http://www.bigdata.com/rdf#>
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX p: <http://www.wikidata.org/prop/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wikibase: <http://wikiba.se/ontology#>
        PREFIX wd: <http://www.wikidata.org/entity/>
        SELECT {group_by}
               (SAMPLE(?labelRu) AS ?labelRuValue)
               (SAMPLE(?labelEn) AS ?labelEnValue)
               (SAMPLE(?descriptionRu) AS ?descriptionRuValue)
               (SAMPLE(?descriptionEn) AS ?descriptionEnValue)
               (SAMPLE(STR(?image)) AS ?imageValue)
               (SAMPLE(STR(?wikipedia)) AS ?wikipediaValue)
               (SAMPLE(STR(?coordinates)) AS ?coordinatesValue)
        WHERE {{
            {pattern}
            OPTIONAL {{ ?item rdfs:label ?labelRu . FILTER(LANG(?labelRu) = "ru") }}
            OPTIONAL {{ ?item rdfs:label ?labelEn . FILTER(LANG(?labelEn) = "en") }}
            OPTIONAL {{
                ?item schema:description ?descriptionRu .
                FILTER(LANG(?descriptionRu) = "ru")
            }}
            OPTIONAL {{
                ?item schema:description ?descriptionEn .
                FILTER(LANG(?descriptionEn) = "en")
            }}
            OPTIONAL {{ ?item wdt:P18 ?image }}
            OPTIONAL {{
                ?wikipedia schema:about ?item ;
                           schema:isPartOf <https://ru.wikipedia.org/> .
            }}
            OPTIONAL {{ ?item wdt:P625 ?coordinates }}
        }}
        GROUP BY {group_by}
    """


def query_wikidata_ids(qids):
    results = {}
    unique_qids = list(dict.fromkeys(qid for qid in qids if qid))
    batch_count = math.ceil(len(unique_qids) / DIRECT_QUERY_BATCH_SIZE)
    for offset in range(0, len(unique_qids), DIRECT_QUERY_BATCH_SIZE):
        batch = unique_qids[offset:offset + DIRECT_QUERY_BATCH_SIZE]
        print(
            f"Wikidata ID: пакет {offset // DIRECT_QUERY_BATCH_SIZE + 1}/"
            f"{batch_count} ({len(batch)} ID)."
        )
        values = " ".join(f"wd:{qid}" for qid in batch)
        query = _metadata_query(
            f"VALUES ?item {{ {values} }}",
            "?item",
        )
        for binding in _query_wikidata(query):
            item_uri = binding.get("item", {}).get("value", "")
            qid_match = re.search(r"/(Q[1-9][0-9]*)$", item_uri)
            if qid_match:
                results[qid_match.group(1)] = binding
    return results


def _point_wkt(lon, lat):
    return f'"Point({lon} {lat})"^^geo:wktLiteral'


def query_wikidata_nearby(pois):
    results = {}
    batch_count = math.ceil(len(pois) / COORDINATE_QUERY_BATCH_SIZE)
    for offset in range(0, len(pois), COORDINATE_QUERY_BATCH_SIZE):
        batch = pois[offset:offset + COORDINATE_QUERY_BATCH_SIZE]
        print(
            f"Wikidata по координатам: пакет "
            f"{offset // COORDINATE_QUERY_BATCH_SIZE + 1}/{batch_count} "
            f"({len(batch)} объектов)."
        )
        branches = []
        for index, poi in enumerate(batch):
            branches.append(f"""
                {{
                    BIND({index} AS ?osmIndex)
                    SERVICE wikibase:around {{
                        ?item wdt:P625 ?coordinates .
                        bd:serviceParam wikibase:center {_point_wkt(poi.lon, poi.lat)} ;
                                        wikibase:radius "{COORDINATE_MATCH_RADIUS_KM}" .
                    }}
                }}
            """)
        query = _metadata_query(
            " UNION ".join(branches),
            "?osmIndex ?item",
        )
        for binding in _query_wikidata(query):
            try:
                local_index = int(binding["osmIndex"]["value"])
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError("Wikidata вернул некорректный индекс координат.") from exc
            results.setdefault(offset + local_index, []).append(binding)
    return results


def _binding_value(binding, name):
    value = binding.get(name)
    return value.get("value") if value else None


def _parse_wkt_point(value):
    if not value:
        return None
    match = re.search(
        r"Point\s*\(\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
        r"\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*\)",
        value,
    )
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _normalized_name(name):
    normalized = unicodedata.normalize("NFKC", name or "").casefold()
    return "".join(character for character in normalized if character.isalnum())


def _distance_meters(lon1, lat1, lon2, lat2):
    earth_radius_m = 6_371_000
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_m * math.asin(math.sqrt(min(1, haversine)))


def _match_nearby_binding(poi, bindings):
    poi_name = _normalized_name(poi.name)
    if not poi_name:
        return None

    candidates = []
    for binding in bindings:
        label = _binding_value(binding, "labelRuValue") or _binding_value(
            binding, "labelEnValue"
        )
        wikidata_name = _normalized_name(label)
        if not wikidata_name:
            continue
        similarity = difflib.SequenceMatcher(None, poi_name, wikidata_name).ratio()
        if similarity < 0.8:
            continue

        coordinates = _parse_wkt_point(_binding_value(binding, "coordinatesValue"))
        if not coordinates:
            continue
        distance = _distance_meters(poi.lon, poi.lat, coordinates[0], coordinates[1])
        if distance <= COORDINATE_MATCH_RADIUS_KM * 1000:
            candidates.append((distance, -similarity, binding))

    if not candidates:
        return None
    candidates.sort(key=lambda result: (result[0], result[1]))
    return candidates[0][2]


def _commons_filename(image_value):
    if not image_value:
        return None
    path = urlsplit(image_value).path
    marker = "/Special:FilePath/"
    if marker not in path:
        return None
    filename = unquote(path.split(marker, 1)[1]).strip("/")
    return filename or None


def _plain_text(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value or ""))).strip()


def _parse_wiki_tag(value):
    if not isinstance(value, str) or ":" not in value:
        return None
    language, title = value.split(":", 1)
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,20}", language):
        return None
    title = title.strip().replace("_", " ")
    if not title:
        return None
    return language, title


def _normalized_wiki_title(title):
    return " ".join((title or "").replace("_", " ").split()).casefold()


def _short_wiki_extract(value):
    extract = _plain_text(value)
    if len(extract) <= WIKI_ARTICLE_EXTRACT_MAX_CHARS:
        return extract
    boundary = max(
        extract.rfind(mark, 0, WIKI_ARTICLE_EXTRACT_MAX_CHARS)
        for mark in (".", "!", "?")
    )
    if boundary >= WIKI_ARTICLE_EXTRACT_MAX_CHARS // 2:
        return extract[:boundary + 1].strip()
    return extract[:WIKI_ARTICLE_EXTRACT_MAX_CHARS - 3].rstrip() + "..."


def _fetch_mediawiki_extracts(requested, project):
    results = {}
    for language, titles_by_name in requested.items():
        titles = list(titles_by_name)
        batch_count = math.ceil(len(titles) / WIKI_ARTICLE_QUERY_BATCH_SIZE)
        for offset in range(0, len(titles), WIKI_ARTICLE_QUERY_BATCH_SIZE):
            batch = titles[offset:offset + WIKI_ARTICLE_QUERY_BATCH_SIZE]
            print(
                f"{project.capitalize()} ({language}): пакет "
                f"{offset // WIKI_ARTICLE_QUERY_BATCH_SIZE + 1}/{batch_count} "
                f"({len(batch)} статей)."
            )
            query = urlencode({
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "extracts|pageprops",
                "exintro": "1",
                "explaintext": "1",
                "exchars": str(WIKI_ARTICLE_EXTRACT_MAX_CHARS),
                "redirects": "1",
                "titles": "|".join(batch),
            })
            payload = _request_json(
                f"https://{language}.{project}.org/w/api.php?{query}"
            )
            try:
                response = payload["query"]
                pages = response["pages"]
            except (KeyError, TypeError) as exc:
                raise RuntimeError(
                    f"{project.capitalize()} ({language}) вернула ответ "
                    "неожиданного формата."
                ) from exc

            mappings = (response.get("normalized") or []) + (
                response.get("redirects") or []
            )
            for page in pages:
                pageprops = page.get("pageprops") or {}
                if page.get("missing") or "disambiguation" in pageprops:
                    continue
                extract = _short_wiki_extract(page.get("extract"))
                if not extract:
                    continue

                page_title = page.get("title", "")
                aliases = {_normalized_wiki_title(page_title)}
                changed = True
                while changed:
                    changed = False
                    for mapping in mappings:
                        source = _normalized_wiki_title(mapping.get("from"))
                        target = _normalized_wiki_title(mapping.get("to"))
                        if target in aliases and source not in aliases:
                            aliases.add(source)
                            changed = True

                wikidata_id = pageprops.get("wikibase_item")
                if not isinstance(wikidata_id, str) or not re.fullmatch(
                    r"Q[1-9][0-9]*", wikidata_id
                ):
                    wikidata_id = None
                canonical_title = page_title.replace(" ", "_")
                article_url = (
                    f"https://{language}.{project}.org/wiki/"
                    f"{quote(canonical_title, safe='')}"
                )
                for requested_title in titles_by_name:
                    normalized_title = _normalized_wiki_title(requested_title)
                    if normalized_title not in aliases:
                        continue
                    results[(language, normalized_title)] = {
                        "extract": extract,
                        "wikidata_id": wikidata_id,
                        "url": article_url,
                    }
    return results


def fetch_wikipedia_extracts(pois):
    requested = {}
    for poi in pois:
        if poi.wikipedia_extract:
            continue
        parsed = _parse_wiki_tag((poi.tags or {}).get("wikipedia"))
        if parsed:
            language, title = parsed
            requested.setdefault(language, {}).setdefault(title, []).append(poi.id)

    articles = _fetch_mediawiki_extracts(requested, "wikipedia")
    results = {}
    for language, titles_by_name in requested.items():
        for title, poi_ids in titles_by_name.items():
            article = articles.get((language, _normalized_wiki_title(title)))
            if not article:
                continue
            for poi_id in poi_ids:
                results[poi_id] = {
                    "wikipedia_extract": article["extract"],
                    "wikidata_id": article["wikidata_id"],
                    "wikipedia_url": article["url"],
                }
    return results


def _wikivoyage_titles_by_qid(qids):
    unique_qids = list(dict.fromkeys(
        qid for qid in qids
        if isinstance(qid, str) and re.fullmatch(r"Q[1-9][0-9]*", qid)
    ))
    titles = {}
    batch_count = math.ceil(len(unique_qids) / WIKIDATA_ENTITY_BATCH_SIZE)
    for offset in range(0, len(unique_qids), WIKIDATA_ENTITY_BATCH_SIZE):
        batch = unique_qids[offset:offset + WIKIDATA_ENTITY_BATCH_SIZE]
        print(
            f"Ссылки Wikidata на Wikivoyage: пакет "
            f"{offset // WIKIDATA_ENTITY_BATCH_SIZE + 1}/{batch_count} "
            f"({len(batch)} ID)."
        )
        query = urlencode({
            "action": "wbgetentities",
            "format": "json",
            "props": "sitelinks",
            "sitefilter": "ruwikivoyage",
            "ids": "|".join(batch),
        })
        payload = _request_json(f"{WIKIDATA_API_URL}?{query}")
        try:
            entities = payload["entities"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError(
                "Wikidata вернула ответ со ссылками WikiVoyage неожиданного формата."
            ) from exc
        for qid, entity in entities.items():
            sitelink = (entity.get("sitelinks") or {}).get("ruwikivoyage")
            title = sitelink.get("title") if sitelink else None
            if title:
                titles[qid] = title
    return titles


def fetch_wikivoyage_extracts(pois):
    requested = {}
    article_by_poi = {}
    eligible = [
        poi for poi in pois
        if not poi.wikivoyage_extract
        and not any(
            isinstance(value, str) and value.strip()
            for value in (
                (poi.tags or {}).get("description:ru"),
                (poi.tags or {}).get("description"),
                poi.wikipedia_extract,
                poi.wikidata_description,
            )
        )
    ]

    qid_by_poi = {}
    qids_without_direct_article = []
    for poi in eligible:
        parsed = _parse_wiki_tag((poi.tags or {}).get("wikivoyage"))
        if parsed:
            article_by_poi[poi.id] = parsed
            continue
        qid = _qid_from_tags(poi.tags) or poi.wikidata_id
        if qid and re.fullmatch(r"Q[1-9][0-9]*", qid):
            qid_by_poi[poi.id] = qid
            qids_without_direct_article.append(qid)

    title_by_qid = _wikivoyage_titles_by_qid(qids_without_direct_article)
    for poi_id, qid in qid_by_poi.items():
        title = title_by_qid.get(qid)
        if title:
            article_by_poi[poi_id] = ("ru", title)

    for poi_id, (language, title) in article_by_poi.items():
        requested.setdefault(language, {}).setdefault(title, [])
        requested[language][title].append(poi_id)

    articles = _fetch_mediawiki_extracts(requested, "wikivoyage")
    results = {}
    for poi_id, (language, title) in article_by_poi.items():
        article = articles.get((language, _normalized_wiki_title(title)))
        if article:
            results[poi_id] = {
                "wikivoyage_extract": article["extract"],
                "wikivoyage_url": article["url"],
            }
    return results


def fetch_commons_metadata(image_values):
    filenames = list(dict.fromkeys(
        filename for filename in (_commons_filename(value) for value in image_values)
        if filename
    ))
    results = {}
    batch_count = math.ceil(len(filenames) / COMMONS_QUERY_BATCH_SIZE)
    for offset in range(0, len(filenames), COMMONS_QUERY_BATCH_SIZE):
        batch = filenames[offset:offset + COMMONS_QUERY_BATCH_SIZE]
        print(
            f"Wikimedia Commons: пакет "
            f"{offset // COMMONS_QUERY_BATCH_SIZE + 1}/{batch_count} "
            f"({len(batch)} изображений)."
        )
        query = urlencode({
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "titles": "|".join(f"File:{filename}" for filename in batch),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": "1200",
        })
        payload = _request_json(f"{COMMONS_API_URL}?{query}")
        try:
            pages = payload["query"]["pages"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Wikimedia Commons вернул ответ неожиданного формата.") from exc

        for page in pages:
            if not page.get("imageinfo"):
                continue
            info = page["imageinfo"][0]
            metadata = info.get("extmetadata", {})
            artist = _plain_text(metadata.get("Artist", {}).get("value"))
            license_name = _plain_text(metadata.get("LicenseShortName", {}).get("value"))
            license_url = metadata.get("LicenseUrl", {}).get("value")
            attribution_parts = [value for value in (artist, license_name) if value]
            if license_url and license_url.startswith(("https://", "http://")):
                attribution_parts.append(license_url)
            results[page.get("title", "").removeprefix("File:")] = {
                "image_url": info.get("thumburl") or info.get("url"),
                "image_page_url": info.get("descriptionurl"),
                "image_attribution": " — ".join(attribution_parts) or None,
            }
    return results


def _metadata_from_binding(qid, binding, commons_by_filename):
    image_value = _binding_value(binding, "imageValue")
    filename = _commons_filename(image_value)
    commons = commons_by_filename.get(filename, {}) if filename else {}
    return {
        "wikidata_id": qid,
        "wikidata_label": (
            _binding_value(binding, "labelRuValue")
            or _binding_value(binding, "labelEnValue")
        ),
        "wikidata_description": (
            _binding_value(binding, "descriptionRuValue")
            or _binding_value(binding, "descriptionEnValue")
        ),
        "wikipedia_url": _binding_value(binding, "wikipediaValue"),
        "image_url": commons.get("image_url"),
        "image_page_url": commons.get("image_page_url"),
        "image_attribution": commons.get("image_attribution"),
    }


def _selected_pois(db):
    geom = models.OSMPOI.geom
    rows = db.execute(
        select(
            models.OSMPOI.id,
            models.OSMPOI.osm_type,
            models.OSMPOI.osm_id,
            models.OSMPOI.name,
            models.OSMPOI.tags,
            func.ST_X(geom),
            func.ST_Y(geom),
            models.OSMPOI.wikidata_id,
            models.OSMPOI.wikidata_description,
            models.OSMPOI.wikipedia_extract,
            models.OSMPOI.wikivoyage_extract,
            models.OSMPOI.wikivoyage_url,
        ).join(
            models.OSMPOINearRailway,
            models.OSMPOINearRailway.osm_poi_id == models.OSMPOI.id,
        )
    ).all()
    return [
        SelectedPOI(
            id=row[0],
            osm_type=row[1],
            osm_id=row[2],
            name=row[3],
            tags=row[4] or {},
            lon=float(row[5]),
            lat=float(row[6]),
            wikidata_id=row[7],
            wikidata_description=row[8],
            wikipedia_extract=row[9],
            wikivoyage_extract=row[10],
            wikivoyage_url=row[11],
        )
        for row in rows
    ]


def _qid_from_tags(tags):
    qid = tags.get("wikidata")
    if isinstance(qid, str) and re.fullmatch(r"Q[1-9][0-9]*", qid.strip()):
        return qid.strip()
    return None


def enrich_selected_pois(db):
    pois = _selected_pois(db)
    wikipedia = fetch_wikipedia_extracts(pois)
    direct_qids = [
        _qid_from_tags(poi.tags)
        or poi.wikidata_id
        or wikipedia.get(poi.id, {}).get("wikidata_id")
        for poi in pois
    ]
    direct_metadata = query_wikidata_ids(direct_qids)

    unmatched_indexes = [
        index for index, qid in enumerate(direct_qids)
        if not qid or qid not in direct_metadata
    ]
    nearby = query_wikidata_nearby([pois[index] for index in unmatched_indexes])

    matches = {}
    for index, qid in enumerate(direct_qids):
        if qid and qid in direct_metadata:
            matches[index] = (qid, direct_metadata[qid])

    for local_index, poi_index in enumerate(unmatched_indexes):
        binding = _match_nearby_binding(
            pois[poi_index],
            nearby.get(local_index, []),
        )
        if binding:
            item_uri = _binding_value(binding, "item")
            qid_match = re.search(r"/(Q[1-9][0-9]*)$", item_uri or "")
            if qid_match:
                matches[poi_index] = (qid_match.group(1), binding)

    item_bindings = [binding for _, binding in matches.values()]
    image_values = [_binding_value(binding, "imageValue") for binding in item_bindings]
    commons = fetch_commons_metadata(image_values)

    updates = {}
    for index, (qid, binding) in matches.items():
        updates[pois[index].id] = _metadata_from_binding(qid, binding, commons)

    for poi in pois:
        article = wikipedia.get(poi.id)
        if not article:
            continue
        values = updates.setdefault(poi.id, {})
        values["wikipedia_extract"] = article["wikipedia_extract"]
        values["wikipedia_url"] = article["wikipedia_url"]
        article_qid = article.get("wikidata_id")
        if article_qid and not _qid_from_tags(poi.tags) and not poi.wikidata_id:
            values.setdefault("wikidata_id", article_qid)

    for poi_id, values in updates.items():
        db.execute(
            update(models.OSMPOI)
            .where(models.OSMPOI.id == poi_id)
            .values(**values)
        )
    db.commit()
    print(
        f"Обновлено данными Wikidata/Wikipedia объектов: {len(updates)} "
        f"из {len(pois)} выбранных OSM-объектов."
    )
    enrich_wikivoyage_tagged_pois(db)


def enrich_wikivoyage_tagged_pois(db):
    extracts = fetch_wikivoyage_extracts(_selected_pois(db))
    if not extracts:
        print("Подходящих статей Wikivoyage для объектов без описания не найдено.")
        return

    for poi_id, values in extracts.items():
        db.execute(
            update(models.OSMPOI)
            .where(models.OSMPOI.id == poi_id)
            .values(**values)
        )
    db.commit()
    print(f"Загружены описания Wikivoyage для объектов: {len(extracts)}.")


def enrich_wikipedia_tagged_pois(db):
    pois = _selected_pois(db)
    wikipedia = fetch_wikipedia_extracts(pois)
    if not wikipedia:
        print("Новых статей Wikipedia для загрузки нет.")
        return

    qid_by_poi = {}
    for poi in pois:
        article = wikipedia.get(poi.id, {})
        qid = article.get("wikidata_id")
        if qid and not _qid_from_tags(poi.tags) and not poi.wikidata_id:
            qid_by_poi[poi.id] = qid

    metadata_by_qid = query_wikidata_ids(qid_by_poi.values())
    bindings = [
        metadata_by_qid[qid]
        for qid in dict.fromkeys(qid_by_poi.values())
        if qid in metadata_by_qid
    ]
    image_values = [_binding_value(binding, "imageValue") for binding in bindings]
    commons = fetch_commons_metadata(image_values)

    pois_by_id = {poi.id: poi for poi in pois}
    for poi_id, article in wikipedia.items():
        poi = pois_by_id[poi_id]
        values = {
            "wikipedia_extract": article["wikipedia_extract"],
            "wikipedia_url": article["wikipedia_url"],
        }
        qid = qid_by_poi.get(poi_id)
        if qid:
            binding = metadata_by_qid.get(qid)
            if binding:
                values.update(_metadata_from_binding(qid, binding, commons))
            else:
                values["wikidata_id"] = qid
            values["wikipedia_extract"] = article["wikipedia_extract"]
            values["wikipedia_url"] = article["wikipedia_url"]
        db.execute(
            update(models.OSMPOI)
            .where(models.OSMPOI.id == poi_id)
            .values(**values)
        )
    db.commit()
    print(f"Загружены описания Wikipedia для объектов: {len(wikipedia)}.")


def map_osm_tags(tags):
    tourism = tags.get("tourism", "")
    amenity = tags.get("amenity", "")
    building = tags.get("building", "")
    natural = tags.get("natural", "")
    water = tags.get("water", "")
    historic = tags.get("historic", "")
    leisure = tags.get("leisure", "")

    if tourism == "nature_reserve" or leisure == "nature_reserve":
        return models.Type1.nature, models.Type2.reserve
    if water == "river" or tags.get("waterway"):
        return models.Type1.nature, models.Type2.river
    if natural in ("lake", "water") or water == "lake":
        return models.Type1.nature, models.Type2.lake
    if natural in ("wood", "forest"):
        return models.Type1.nature, models.Type2.forest
    if tourism in ("museum", "gallery", "zoo") or amenity == "arts_centre":
        return models.Type1.human, models.Type2.museum
    if amenity == "theatre":
        return models.Type1.human, models.Type2.theater
    if amenity == "place_of_worship" or building in (
        "church", "chapel", "mosque", "synagogue", "temple",
    ):
        return models.Type1.human, models.Type2.temple
    if historic in ("castle", "ruins", "archaeological_site", "building"):
        return models.Type1.human, models.Type2.architecture
    if historic or tags.get("memorial") or tags.get("heritage") or tourism == "attraction":
        return models.Type1.human, models.Type2.monument
    return models.Type1.human, models.Type2.architecture


def _parse_creation_date(tags):
    value = tags.get("start_date") or tags.get("opening_date")
    if not value:
        return None
    match = re.match(r"^\s*(\d{4})(?:-(\d{2})-(\d{2}))?\s*$", value)
    if not match:
        return None
    year, month, day = match.groups()
    try:
        from datetime import date
        return date(int(year), int(month or 1), int(day or 1))
    except ValueError:
        return None


def _wiki_tag_url(value, project):
    parsed = _parse_wiki_tag(value)
    if not parsed:
        return None
    language, title = parsed
    return (
        f"https://{language}.{project}.org/wiki/"
        f"{quote(title.replace(' ', '_'), safe='')}"
    )


def _wikipedia_tag_url(value):
    return _wiki_tag_url(value, "wikipedia")


def _source_urls(poi, metadata):
    osm_url = f"https://www.openstreetmap.org/{poi.osm_type}/{poi.osm_id}"
    sources = [osm_url]
    if metadata.get("wikidata_id"):
        sources.append(f"https://www.wikidata.org/wiki/{metadata['wikidata_id']}")
    wikipedia_url = metadata.get("wikipedia_url") or _wikipedia_tag_url(
        (poi.tags or {}).get("wikipedia")
    )
    if wikipedia_url:
        sources.append(wikipedia_url)
    wikivoyage_url = metadata.get("wikivoyage_url") or _wiki_tag_url(
        (poi.tags or {}).get("wikivoyage"),
        "wikivoyage",
    )
    if wikivoyage_url:
        sources.append(wikivoyage_url)
    if metadata.get("image_page_url"):
        sources.append(metadata["image_page_url"])
    return list(dict.fromkeys(sources))


def _classify_promotion_candidate(poi, taxonomy):
    tags = poi.tags or {}
    name = tags.get("name:ru") or tags.get("name") or poi.wikidata_label or ""
    return classify(
        {
            "name": name,
            "tags": tags,
            "wikidata_id": poi.wikidata_id or tags.get("wikidata"),
            "wikidata_description": poi.wikidata_description,
            "wikipedia_extract": poi.wikipedia_extract,
            "wikipedia_url": poi.wikipedia_url,
            "wikivoyage_extract": poi.wikivoyage_extract,
            "wikivoyage_url": poi.wikivoyage_url,
            "wikipedia_article_verified": bool(
                poi.wikipedia_extract and poi.wikipedia_url
            ),
            "wikivoyage_verified": bool(
                poi.wikivoyage_extract and poi.wikivoyage_url
            ),
        },
        taxonomy,
    )


def _culture_place_row(poi, lon, lat):
    tags = poi.tags or {}
    name = (
        tags.get("name:ru")
        or tags.get("name")
        or poi.wikidata_label
    )
    if not name:
        return None

    description_candidates = (
        (tags.get("description:ru"), "osm_description_ru"),
        (poi.wikipedia_extract, "wikipedia"),
        (poi.wikidata_description, "wikidata"),
        (tags.get("description"), "osm_description"),
        (poi.wikivoyage_extract, "wikivoyage"),
    )
    description, description_source = next(
        (
            (value, source)
            for value, source in description_candidates
            if value
        ),
        (None, None),
    )
    type1, type2 = map_osm_tags(tags)
    return {
        "osm_type": poi.osm_type,
        "osm_id": poi.osm_id,
        "wikidata_id": poi.wikidata_id,
        "name": name[:255],
        "type1": type1,
        "type2": type2,
        "short_description": description,
        "description_source": description_source,
        "history": None,
        "sources": _source_urls(poi, {
            "wikidata_id": poi.wikidata_id,
            "wikipedia_url": poi.wikipedia_url,
            "wikivoyage_url": poi.wikivoyage_url,
            "image_page_url": poi.image_page_url,
        }),
        "creation_date": _parse_creation_date(tags),
        "photo_url": poi.image_url,
        "photo_attribution": poi.image_attribution,
        "size_priority": 1.0,
        "geom": WKTElement(f"POINT({lon} {lat})", srid=4326),
    }


_HARD_EXCLUSION_REASONS = {
    "unsupported_object_type",
    "technical_infrastructure",
    "individual_zoo_animal_or_enclosure",
    "duplicate_or_component",
    "invalid_or_incomplete_data",
}


def _record_candidate_exclusion(db, poi, result, registry_by_poi_id):
    registry = registry_by_poi_id.get(poi.id)
    if result is None and (registry is None or not registry.is_active):
        return
    if result is not None and (
        registry is not None
        and registry.is_active
        and registry.rule_id == result.evidence[0]["rule"]
        and registry.exclusion_reason == result.exclusion_reason
        and registry.taxonomy_version == result.taxonomy_version
    ):
        return

    now = datetime.now(timezone.utc)
    if result is None:
        old_value = {
            "rule_id": registry.rule_id,
            "exclusion_reason": registry.exclusion_reason,
            "taxonomy_version": registry.taxonomy_version,
            "is_active": True,
        }
        registry.is_active = False
        registry.last_evaluated_at = now
        registry.resolved_at = now
        action = "auto_resolve_candidate_exclusion"
        new_value = dict(old_value, is_active=False)
    else:
        new_value = {
            "rule_id": result.evidence[0]["rule"],
            "exclusion_reason": result.exclusion_reason,
            "taxonomy_version": result.taxonomy_version,
            "is_active": True,
        }
        old_value = None
        if registry is None:
            registry = models.OSMPOIExclusionRegistry(
                osm_poi_id=poi.id,
                first_seen_at=now,
            )
            db.add(registry)
            registry_by_poi_id[poi.id] = registry
        else:
            old_value = {
                "rule_id": registry.rule_id,
                "exclusion_reason": registry.exclusion_reason,
                "taxonomy_version": registry.taxonomy_version,
                "is_active": registry.is_active,
            }
        registry.rule_id = new_value["rule_id"]
        registry.exclusion_reason = new_value["exclusion_reason"]
        registry.taxonomy_version = new_value["taxonomy_version"]
        registry.is_active = True
        registry.last_evaluated_at = now
        registry.resolved_at = None
        action = "auto_exclude_candidate"

    db.add(models.ClassificationAuditLog(
        osm_type=poi.osm_type,
        osm_id=poi.osm_id,
        action=action,
        actor="import",
        old_value=old_value,
        new_value=new_value,
    ))


def promote_selected_pois(db, taxonomy=None):
    taxonomy = taxonomy or load_taxonomy()
    selected_rows = db.execute(
        select(
            models.OSMPOI,
            func.ST_X(models.OSMPOI.geom),
            func.ST_Y(models.OSMPOI.geom),
        ).join(
            models.OSMPOINearRailway,
            models.OSMPOINearRailway.osm_poi_id == models.OSMPOI.id,
        )
    ).all()

    if not selected_rows:
        print("В радиусе отбора нет OSM-объектов для переноса.")
        return

    pois = [row[0] for row in selected_rows]
    poi_ids = [poi.id for poi in pois]
    identities = [(poi.osm_type, poi.osm_id) for poi in pois]
    existing_identities = set()
    registry_by_poi_id = {}
    for offset in range(0, len(poi_ids), BATCH_SIZE):
        batch_ids = poi_ids[offset:offset + BATCH_SIZE]
        registry_by_poi_id.update({
            registry.osm_poi_id: registry
            for registry in db.execute(
                select(models.OSMPOIExclusionRegistry).where(
                    models.OSMPOIExclusionRegistry.osm_poi_id.in_(batch_ids)
                )
            ).scalars()
        })
    for offset in range(0, len(identities), BATCH_SIZE):
        batch = identities[offset:offset + BATCH_SIZE]
        existing_identities.update(
            (row[0], row[1])
            for row in db.execute(
                select(
                    models.CulturePlace.osm_type,
                    models.CulturePlace.osm_id,
                ).where(
                    tuple_(
                        models.CulturePlace.osm_type,
                        models.CulturePlace.osm_id,
                    ).in_(batch)
                )
            ).all()
        )

    rows = []
    hard_excluded = 0
    for poi, lon, lat in selected_rows:
        result = _classify_promotion_candidate(poi, taxonomy)
        identity = (poi.osm_type, poi.osm_id)
        new_candidate = identity not in existing_identities
        hard_exclusion = result.exclusion_reason in _HARD_EXCLUSION_REASONS
        if new_candidate and hard_exclusion:
            _record_candidate_exclusion(
                db,
                poi,
                result,
                registry_by_poi_id,
            )
            hard_excluded += 1
            continue

        _record_candidate_exclusion(db, poi, None, registry_by_poi_id)
        row = _culture_place_row(poi, float(lon), float(lat))
        if not row:
            continue
        rows.append(row)

    with db.no_autoflush:
        for offset in range(0, len(rows), BATCH_SIZE):
            batch = rows[offset:offset + BATCH_SIZE]
            statement = insert(models.CulturePlace).values(batch)
            excluded = statement.excluded
            place = models.CulturePlace
            can_update_type = and_(
                place.classification_locked.is_(False),
                place.subcategory.is_(None),
            )
            can_update_description = and_(
                excluded.short_description.is_not(None),
                func.btrim(excluded.short_description) != "",
                func.coalesce(place.description_source, "") != "manual",
            )
            wikidata_id = func.coalesce(excluded.wikidata_id, place.wikidata_id)
            creation_date = func.coalesce(excluded.creation_date, place.creation_date)
            photo_url = func.coalesce(excluded.photo_url, place.photo_url)
            photo_attribution = func.coalesce(
                excluded.photo_attribution,
                place.photo_attribution,
            )
            statement = statement.on_conflict_do_update(
                index_elements=["osm_type", "osm_id"],
                index_where=text("osm_type IS NOT NULL AND osm_id IS NOT NULL"),
                set_={
                    "wikidata_id": wikidata_id,
                    "name": case(
                        (
                            place.classification_locked.is_(False),
                            excluded.name,
                        ),
                        else_=place.name,
                    ),
                    "type1": case(
                        (
                            can_update_type,
                            excluded.type1,
                        ),
                        else_=place.type1,
                    ),
                    "type2": case(
                        (
                            can_update_type,
                            excluded.type2,
                        ),
                        else_=place.type2,
                    ),
                    "short_description": case(
                        (
                            can_update_description,
                            excluded.short_description,
                        ),
                        else_=place.short_description,
                    ),
                    "description_source": case(
                        (
                            can_update_description,
                            excluded.description_source,
                        ),
                        else_=place.description_source,
                    ),
                    "sources": excluded.sources,
                    "creation_date": creation_date,
                    "photo_url": photo_url,
                    "photo_attribution": photo_attribution,
                    "geom": excluded.geom,
                },
                where=or_(
                    place.wikidata_id.is_distinct_from(wikidata_id),
                    and_(
                        place.classification_locked.is_(False),
                        place.name.is_distinct_from(excluded.name),
                    ),
                    and_(
                        can_update_type,
                        place.type1.is_distinct_from(excluded.type1),
                    ),
                    and_(
                        can_update_type,
                        place.type2.is_distinct_from(excluded.type2),
                    ),
                    and_(
                        can_update_description,
                        place.short_description.is_distinct_from(
                            excluded.short_description
                        ),
                    ),
                    and_(
                        can_update_description,
                        place.description_source.is_distinct_from(
                            excluded.description_source
                        ),
                    ),
                    place.sources.is_distinct_from(excluded.sources),
                    place.creation_date.is_distinct_from(creation_date),
                    place.photo_url.is_distinct_from(photo_url),
                    place.photo_attribution.is_distinct_from(photo_attribution),
                    place.geom.is_distinct_from(excluded.geom),
                ),
            )
            db.execute(statement)
    print(
        f"В culture_place перенесено/обновлено объектов OSM: {len(rows)} "
        f"(жёстко исключено: {hard_excluded}; "
        f"без названия пропущено: {len(selected_rows) - len(rows) - hard_excluded})."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Обогащение выбранных OSM-объектов Wikidata и перенос в culture_place."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enrich-only", action="store_true")
    mode.add_argument("--promote-only", action="store_true")
    mode.add_argument(
        "--wikipedia-only",
        action="store_true",
        help="Загрузить тексты по тегам wikipedia без поиска по координатам.",
    )
    mode.add_argument(
        "--wikivoyage-only",
        action="store_true",
        help="Загрузить точные статьи Wikivoyage по тегам или Wikidata ID.",
    )
    args = parser.parse_args()

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    ensure_osm_enrichment_schema(engine)
    ensure_taxonomy_schema(engine)
    db = SessionLocal()
    try:
        if not args.promote_only:
            if args.wikipedia_only:
                enrich_wikipedia_tagged_pois(db)
            elif args.wikivoyage_only:
                enrich_wikivoyage_tagged_pois(db)
            else:
                enrich_selected_pois(db)
        if not args.enrich_only:
            promote_selected_pois(db)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
