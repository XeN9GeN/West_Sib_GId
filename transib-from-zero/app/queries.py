"""Общие условия видимости и запросы карты."""

import math
from collections.abc import Mapping, Sequence
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import and_, case, cast, func, or_, select, text

from . import models
from .taxonomy import load_taxonomy


VISIBLE_CONDITION = """
excluded_from_map = false
AND classified_at IS NOT NULL
AND railway_distance_checked_at IS NOT NULL
AND railway_distance_m IS NOT NULL
""".strip()

_DESCRIPTION_QUALITIES = ("ok", "ok_ai_summary", "ok_manual")
_OBJECT_CLASS_LABELS = {
    "heritage": "Наследие",
    "tourism": "Туризм",
    "both": "Наследие и туризм",
    "unclassified": "Не классифицировано",
}


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    """Проверяет bbox в формате minLon,minLat,maxLon,maxLat."""
    try:
        coordinates = tuple(float(part.strip()) for part in bbox.split(","))
    except (AttributeError, ValueError) as error:
        raise ValueError(
            "bbox должен содержать четыре координаты: minLon,minLat,maxLon,maxLat."
        ) from error
    if len(coordinates) != 4 or not all(math.isfinite(value) for value in coordinates):
        raise ValueError(
            "bbox должен содержать четыре конечные координаты: minLon,minLat,maxLon,maxLat."
        )

    min_lon, min_lat, max_lon, max_lat = coordinates
    if not (-180 <= min_lon < max_lon <= 180):
        raise ValueError("Долготы bbox должны быть в диапазоне -180..180 и minLon < maxLon.")
    if not (-90 <= min_lat < max_lat <= 90):
        raise ValueError("Широты bbox должны быть в диапазоне -90..90 и minLat < maxLat.")
    return coordinates


def min_priority_for_zoom(zoom: int, taxonomy: Mapping[str, Any]) -> float:
    if type(zoom) is not int or not 0 <= zoom <= 22:
        raise ValueError("zoom должен быть целым числом от 0 до 22.")
    for tier in taxonomy["settings"]["zoom"]["priority_tiers"]:
        if zoom <= tier["max_zoom"]:
            return float(tier["min_priority"])
    raise ValueError(f"В taxonomy.yaml нет яруса приоритета для zoom={zoom}.")


def effective_description_expression():
    place = models.CulturePlace
    return case(
        (place.effective_description_source == "history", place.history),
        (
            place.effective_description_source == "short_description",
            place.short_description,
        ),
        (place.effective_description_source == "ai_summary", place.ai_summary),
        else_=None,
    )


def build_marker(
    taxonomy: Mapping[str, Any],
    subcategory: str | None,
    legacy_marker: Mapping[str, str],
) -> dict[str, str]:
    if subcategory:
        for category in taxonomy["categories"]:
            for item in category["subcategories"]:
                if item["id"] == subcategory:
                    return dict(item["marker"])
    return dict(legacy_marker)


def build_taxonomy_response(taxonomy: Mapping[str, Any]) -> dict[str, Any]:
    categories = []
    for category in taxonomy["categories"]:
        subcategories = [
            {
                "id": item["id"],
                "label": item["label"],
                "marker": dict(item["marker"]),
            }
            for item in category["subcategories"]
        ]
        # Стиль категории берётся из первого маркера подкатегории в YAML.
        category_marker = category["subcategories"][0]["marker"]
        categories.append({
            "id": category["id"],
            "label": category["label"],
            "color": category_marker["color"],
            "icon": category_marker["icon"],
            "subcategories": subcategories,
        })

    settings = taxonomy["settings"]
    return {
        "version": taxonomy["version"],
        "description_required_from_zoom": (
            settings["zoom"]["description_required_from_zoom"]
        ),
        "priority_tiers": [
            dict(tier) for tier in settings["zoom"]["priority_tiers"]
        ],
        "object_classes": [
            {
                "id": object_class,
                "label": _OBJECT_CLASS_LABELS[object_class],
            }
            for object_class in taxonomy["object_classes"]
        ],
        "categories": categories,
        "demo": dict(settings["demo"]),
    }


def build_result_count_headers(total_count: int, returned_count: int) -> dict[str, str]:
    return {
        "X-Truncated": str(total_count > returned_count).lower(),
        "X-Total-Count": str(total_count),
        "X-Returned-Count": str(returned_count),
    }


def _validate_filter_values(
    values: Sequence[str] | None,
    allowed: set[str],
    name: str,
) -> None:
    if values is None:
        return
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(
            f"Недопустимые значения фильтра {name}: {', '.join(sorted(unknown))}."
        )


def _culture_place_conditions(
    bbox: str,
    zoom: int | None,
    category: Sequence[str] | None,
    subcategory: Sequence[str] | None,
    object_class: Sequence[str] | None,
    type1: Sequence[str] | None,
    type2: Sequence[str] | None,
    taxonomy: Mapping[str, Any],
):
    coordinates = parse_bbox(bbox)
    categories = {
        item["id"] for item in taxonomy["categories"]
    }
    subcategories = {
        subcategory["id"]
        for item in taxonomy["categories"]
        for subcategory in item["subcategories"]
    }
    _validate_filter_values(category, categories, "category")
    _validate_filter_values(subcategory, subcategories, "subcategory")
    _validate_filter_values(object_class, set(taxonomy["object_classes"]), "object_class")
    _validate_filter_values(
        type1,
        {item.value for item in models.Type1},
        "type1",
    )
    _validate_filter_values(
        type2,
        {item.value for item in models.Type2},
        "type2",
    )

    place = models.CulturePlace
    geom_as_geometry = cast(place.geom, Geometry)
    envelope = func.ST_MakeEnvelope(*coordinates, 4326)
    conditions = [
        text(VISIBLE_CONDITION),
        func.ST_Within(geom_as_geometry, envelope),
        or_(
            place.origin == "demo",
            and_(
                place.category.is_not(None),
                place.subcategory.is_not(None),
                place.object_class != "unclassified",
            ),
        ),
    ]
    for field, values in (
        (place.category, category),
        (place.subcategory, subcategory),
        (place.object_class, object_class),
        (place.type1, type1),
        (place.type2, type2),
    ):
        if values is not None:
            conditions.append(field.in_(values))

    if zoom is not None:
        min_priority = min_priority_for_zoom(zoom, taxonomy)
        priority = place.size_priority
        priority_cap = taxonomy["settings"]["demo"]["priority_cap"]
        if priority_cap is not None:
            priority = case(
                (
                    place.origin == "demo",
                    func.least(place.size_priority, priority_cap),
                ),
                else_=place.size_priority,
            )
        conditions.append(priority >= min_priority)

        description_required_from_zoom = (
            taxonomy["settings"]["zoom"]["description_required_from_zoom"]
        )
        if zoom >= description_required_from_zoom:
            conditions.extend((
                place.effective_description_source.is_not(None),
                place.description_quality.in_(_DESCRIPTION_QUALITIES),
            ))
    return conditions, geom_as_geometry


def build_culture_places_query(
    bbox: str,
    *,
    zoom: int | None = None,
    category: Sequence[str] | None = None,
    subcategory: Sequence[str] | None = None,
    object_class: Sequence[str] | None = None,
    type1: Sequence[str] | None = None,
    type2: Sequence[str] | None = None,
    taxonomy: Mapping[str, Any] | None = None,
):
    config = taxonomy if taxonomy is not None else load_taxonomy()
    conditions, geom_as_geometry = _culture_place_conditions(
        bbox,
        zoom,
        category,
        subcategory,
        object_class,
        type1,
        type2,
        config,
    )
    place = models.CulturePlace
    return (
        select(
            place,
            func.ST_X(geom_as_geometry),
            func.ST_Y(geom_as_geometry),
            effective_description_expression(),
        )
        .where(*conditions)
        .order_by(place.size_priority.desc(), place.id.asc())
    )


def build_culture_places_count_query(
    bbox: str,
    *,
    zoom: int | None = None,
    category: Sequence[str] | None = None,
    subcategory: Sequence[str] | None = None,
    object_class: Sequence[str] | None = None,
    type1: Sequence[str] | None = None,
    type2: Sequence[str] | None = None,
    taxonomy: Mapping[str, Any] | None = None,
):
    config = taxonomy if taxonomy is not None else load_taxonomy()
    conditions, _ = _culture_place_conditions(
        bbox,
        zoom,
        category,
        subcategory,
        object_class,
        type1,
        type2,
        config,
    )
    return select(func.count()).select_from(models.CulturePlace).where(*conditions)
