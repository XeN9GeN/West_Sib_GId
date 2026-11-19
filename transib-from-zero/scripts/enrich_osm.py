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
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from app import models
from app.database import Base, SessionLocal, engine
from app.migrations import ensure_osm_enrichment_schema


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
REQUEST_TIMEOUT_SECONDS = 60
COORDINATE_MATCH_RADIUS_KM = 0.1
DIRECT_QUERY_BATCH_SIZE = 100
COORDINATE_QUERY_BATCH_SIZE = 20
COMMONS_QUERY_BATCH_SIZE = 50
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
    direct_qids = [
        _qid_from_tags(poi.tags) or poi.wikidata_id
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

    for poi_id, values in updates.items():
        db.execute(
            update(models.OSMPOI)
            .where(models.OSMPOI.id == poi_id)
            .values(**values)
        )
    db.commit()
    print(
        f"Обогащено объектом Wikidata {len(updates)} из {len(pois)} выбранных OSM-объектов."
    )


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


def _wikipedia_tag_url(value):
    if not value or ":" not in value:
        return None
    language, title = value.split(":", 1)
    if not re.fullmatch(r"[a-z-]+", language) or not title:
        return None
    return f"https://{language}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


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
    if metadata.get("image_page_url"):
        sources.append(metadata["image_page_url"])
    return list(dict.fromkeys(sources))


def _culture_place_row(poi, lon, lat):
    tags = poi.tags or {}
    name = (
        tags.get("name:ru")
        or tags.get("name")
        or poi.wikidata_label
    )
    if not name:
        return None

    description = (
        poi.wikidata_description
        or tags.get("description:ru")
        or tags.get("description")
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
        "history": None,
        "sources": _source_urls(poi, {
            "wikidata_id": poi.wikidata_id,
            "wikipedia_url": poi.wikipedia_url,
            "image_page_url": poi.image_page_url,
        }),
        "creation_date": _parse_creation_date(tags),
        "photo_url": poi.image_url,
        "photo_attribution": poi.image_attribution,
        "size_priority": 1.0,
        "geom": WKTElement(f"POINT({lon} {lat})", srid=4326),
    }


def promote_selected_pois(db):
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

    rows = []
    for poi, lon, lat in selected_rows:
        row = _culture_place_row(poi, float(lon), float(lat))
        if not row:
            continue
        rows.append(row)

    with db.no_autoflush:
        for offset in range(0, len(rows), BATCH_SIZE):
            batch = rows[offset:offset + BATCH_SIZE]
            statement = insert(models.CulturePlace).values(batch)
            statement = statement.on_conflict_do_update(
                index_elements=["osm_type", "osm_id"],
                index_where=text("osm_type IS NOT NULL AND osm_id IS NOT NULL"),
                set_={
                    "wikidata_id": statement.excluded.wikidata_id,
                    "name": statement.excluded.name,
                    "type1": statement.excluded.type1,
                    "type2": statement.excluded.type2,
                    "short_description": func.coalesce(
                        statement.excluded.short_description,
                        models.CulturePlace.short_description,
                    ),
                    "sources": statement.excluded.sources,
                    "creation_date": func.coalesce(
                        statement.excluded.creation_date,
                        models.CulturePlace.creation_date,
                    ),
                    "photo_url": func.coalesce(
                        statement.excluded.photo_url,
                        models.CulturePlace.photo_url,
                    ),
                    "photo_attribution": func.coalesce(
                        statement.excluded.photo_attribution,
                        models.CulturePlace.photo_attribution,
                    ),
                    "geom": statement.excluded.geom,
                },
            )
            db.execute(statement)
    db.commit()
    print(
        f"В culture_place перенесено/обновлено объектов OSM: {len(rows)} "
        f"(без названия пропущено: {len(selected_rows) - len(rows)})."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Обогащение выбранных OSM-объектов Wikidata и перенос в culture_place."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enrich-only", action="store_true")
    mode.add_argument("--promote-only", action="store_true")
    args = parser.parse_args()

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    ensure_osm_enrichment_schema(engine)
    db = SessionLocal()
    try:
        if not args.promote_only:
            enrich_selected_pois(db)
        if not args.enrich_only:
            promote_selected_pois(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
