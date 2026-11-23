"""Пересчёт расстояний, таксономии и качества описаний culture_place."""

import argparse
import csv
from difflib import SequenceMatcher
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any

from sqlalchemy import and_, bindparam, cast, func, select, text
from sqlalchemy.orm import Session
from geoalchemy2 import Geometry

from app import models
from app.database import SessionLocal, engine
from app.description_quality import EffectiveDescription, pick_effective_description
from app.migrations import ensure_taxonomy_schema
from app.taxonomy import Classification, classify, load_taxonomy, normalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
BATCH_SIZE = 1000
EARTH_RADIUS_METERS = 6_371_008.8


def classify_places(
    db: Session,
    taxonomy: dict[str, Any],
    *,
    dry_run: bool = True,
    backfill_origin: bool = False,
    recompute_descriptions: bool = False,
    reports_dir: Path = REPORTS_DIR,
    place_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Выполняет классификацию в переданной сессии, не обращаясь к глобальной БД."""
    origin_backfill = _backfill_origin(db, dry_run) if backfill_origin else {
        "osm": 0,
        "demo": 0,
    }
    radius = taxonomy["settings"]["railway_radius_meters"]
    distance_updates = _update_railway_distances(db, radius, dry_run, place_ids)
    if dry_run:
        distance_by_id = _calculate_railway_distances(db, radius, place_ids)
    else:
        distance_query = select(models.CulturePlace.id, models.CulturePlace.railway_distance_m)
        if place_ids is not None:
            distance_query = distance_query.where(models.CulturePlace.id.in_(place_ids))
        distance_by_id = dict(db.execute(distance_query).all())

    demo_places = _load_demo_places()
    summary: dict[str, Any] = {
        "dry_run": dry_run,
        "origin_backfill": origin_backfill,
        "distance_updates": distance_updates,
        "classification_updates": 0,
        "description_updates": 0,
        "decisions": {"include": 0, "pending_review": 0, "excluded": 0},
        "by_subcategory": {},
        "priority_histogram": {},
        "demo_priority_histogram": {},
        "pending": [],
        "unidentified": [],
        "demos": [],
        "osm_places": [],
    }
    offset = 0
    while True:
        geometry = cast(models.CulturePlace.geom, Geometry(geometry_type="POINT", srid=4326))
        place_query = (
            select(
                models.CulturePlace,
                models.OSMPOI,
                func.ST_X(geometry),
                func.ST_Y(geometry),
            )
            .outerjoin(
                models.OSMPOI,
                and_(
                    models.OSMPOI.osm_type == models.CulturePlace.osm_type,
                    models.OSMPOI.osm_id == models.CulturePlace.osm_id,
                ),
            )
            .order_by(models.CulturePlace.id)
            .limit(BATCH_SIZE)
            .offset(offset)
        )
        if place_ids is not None:
            place_query = place_query.where(models.CulturePlace.id.in_(place_ids))
        rows = db.execute(place_query).all()
        if not rows:
            break
        offset += len(rows)

        for place, poi, lon, lat in rows:
            distance = distance_by_id.get(place.id)
            inferred_origin = _infer_origin(place, float(lon), float(lat), demo_places)
            origin = place.origin or inferred_origin
            effective = _effective_description(
                place,
                taxonomy["settings"],
                force=recompute_descriptions,
            )
            is_demo = origin == "demo"
            if origin == "demo":
                summary["demos"].append({
                    "id": place.id,
                    "name": place.name,
                    "lon": float(lon),
                    "lat": float(lat),
                    "distance": distance,
                    "size_priority": place.size_priority,
                    "wikidata_id": place.wikidata_id,
                })
                decision = (
                    _locked_result(place, taxonomy)
                    if place.classification_locked
                    else _classify_demo(place, distance, taxonomy)
                )
            elif place.classification_locked:
                decision = _locked_result(place, taxonomy)
            elif origin in (None, "manual") or (origin == "osm" and poi is None):
                summary["unidentified"].append(_unidentified_row(place, origin))
                decision = _pending_result(taxonomy, "unidentified_osm_or_manual_record")
            elif distance is None:
                decision = _outside_radius_result(taxonomy)
            else:
                decision = _classify_osm_place(place, poi, taxonomy, effective)

            if distance is None:
                decision = _outside_radius_result(taxonomy, previous=decision)
            elif (
                place.classification_locked
                and place.exclusion_reason == "outside_railway_radius"
            ):
                previous_state = _radius_restore_state(db, place.id)
                decision = _restore_locked_result(
                    place,
                    taxonomy,
                    previous_state=previous_state,
                )

            changed, description_changed = _apply_result(
                db,
                place,
                decision,
                distance,
                taxonomy,
                effective,
                is_demo=is_demo,
                dry_run=dry_run,
            )
            if changed:
                summary["classification_updates"] += 1
            if description_changed:
                summary["description_updates"] += 1
            if decision.decision in summary["decisions"]:
                summary["decisions"][decision.decision] += 1
            subcategory_id = decision.subcategory or "(нет)"
            if subcategory_id not in summary["by_subcategory"]:
                summary["by_subcategory"][subcategory_id] = {
                    "include": 0,
                    "pending_review": 0,
                    "excluded": 0,
                }
            summary["by_subcategory"][subcategory_id][decision.decision] += 1
            priority = decision.size_priority
            _increment_priority_histogram(
                summary["demo_priority_histogram"] if origin == "demo"
                else summary["priority_histogram"],
                priority,
            )
            if decision.exclusion_reason == "pending_review":
                summary["pending"].append(_pending_row(place, decision))
            if origin == "osm":
                summary["osm_places"].append({
                    "id": place.id,
                    "osm_type": place.osm_type,
                    "osm_id": place.osm_id,
                    "name": place.name,
                    "lon": float(lon),
                    "lat": float(lat),
                    "wikidata_id": poi.wikidata_id if poi else place.wikidata_id,
                })

        if not dry_run:
            db.flush()
            db.expunge_all()

    registry_counts = db.execute(
        select(
            func.count(models.OSMPOIExclusionRegistry.id).filter(
                models.OSMPOIExclusionRegistry.is_active.is_(True)
            ),
            func.count(models.OSMPOIExclusionRegistry.id).filter(
                models.OSMPOIExclusionRegistry.is_active.is_(False)
            ),
        )
    ).one()
    summary["registry_active"] = registry_counts[0]
    summary["registry_resolved"] = registry_counts[1]
    summary["demo_duplicates"] = _find_demo_duplicates(
        summary["demos"],
        summary["osm_places"],
    )
    if not dry_run:
        db.commit()
    if reports_dir is not None:
        _write_reports(summary, reports_dir)
    return summary


def _update_railway_distances(
    db: Session,
    radius: int,
    dry_run: bool,
    place_ids: list[int] | None,
) -> int:
    id_filter = "AND cp.id IN :place_ids" if place_ids is not None else ""
    if dry_run:
        statement = text(f"""
                SELECT COUNT(*)
                FROM (
                    SELECT cp.railway_distance_checked_at,
                           cp.railway_distance_m,
                           (
                               SELECT MIN(ST_Distance(cp.geom, r.geom::geography))
                               FROM raw_railway_points AS r
                               WHERE ST_DWithin(cp.geom, r.geom::geography, :radius_m)
                           ) AS distance_m
                    FROM culture_place AS cp
                    WHERE true {id_filter}
                ) AS distances
                WHERE railway_distance_checked_at IS NULL
                   OR railway_distance_m IS DISTINCT FROM distance_m
            """)
        if place_ids is not None:
            statement = statement.bindparams(bindparam("place_ids", expanding=True))
        params = {"radius_m": radius}
        if place_ids is not None:
            params["place_ids"] = place_ids
        changed = db.execute(statement, params).scalar_one()
        return int(changed)

    statement = text(f"""
            UPDATE culture_place AS cp
            SET railway_distance_m = distances.distance_m,
                railway_distance_checked_at = now()
            FROM (
                SELECT candidate.id,
                       (
                           SELECT MIN(ST_Distance(candidate.geom, r.geom::geography))
                           FROM raw_railway_points AS r
                           WHERE ST_DWithin(candidate.geom, r.geom::geography, :radius_m)
                       ) AS distance_m
                FROM culture_place AS candidate
                WHERE true {id_filter.replace("cp.", "candidate.")}
            ) AS distances
            WHERE distances.id = cp.id
              AND (
                  cp.railway_distance_checked_at IS NULL
                  OR cp.railway_distance_m IS DISTINCT FROM distances.distance_m
              )
        """)
    if place_ids is not None:
        statement = statement.bindparams(bindparam("place_ids", expanding=True))
    params = {"radius_m": radius}
    if place_ids is not None:
        params["place_ids"] = place_ids
    result = db.execute(statement, params)
    return max(0, result.rowcount or 0)


def _calculate_railway_distances(
    db: Session,
    radius: int,
    place_ids: list[int] | None,
) -> dict[int, float | None]:
    distances: dict[int, float | None] = {}
    offset = 0
    id_filter = "AND cp.id IN :place_ids" if place_ids is not None else ""
    statement = text(f"""
                SELECT cp.id,
                       (
                           SELECT MIN(ST_Distance(cp.geom, r.geom::geography))
                           FROM raw_railway_points AS r
                           WHERE ST_DWithin(cp.geom, r.geom::geography, :radius_m)
                       ) AS distance_m
                FROM culture_place AS cp
                WHERE true {id_filter}
                ORDER BY cp.id
                LIMIT :limit OFFSET :offset
            """)
    if place_ids is not None:
        statement = statement.bindparams(bindparam("place_ids", expanding=True))
    while True:
        params = {"radius_m": radius, "limit": BATCH_SIZE, "offset": offset}
        if place_ids is not None:
            params["place_ids"] = place_ids
        rows = db.execute(statement, params).all()
        if not rows:
            break
        distances.update((row.id, row.distance_m) for row in rows)
        offset += len(rows)
    return distances


def _backfill_origin(db: Session, dry_run: bool) -> dict[str, int]:
    demo_places = _load_demo_places()
    if dry_run:
        osm_count = db.execute(
            select(func.count(models.CulturePlace.id)).where(
                models.CulturePlace.origin.is_(None),
                models.CulturePlace.osm_id.is_not(None),
            )
        ).scalar_one()
        demo_count = sum(
            1
            for place, lon, lat in db.execute(
                select(
                    models.CulturePlace,
                    func.ST_X(cast(models.CulturePlace.geom, Geometry(geometry_type="POINT", srid=4326))),
                    func.ST_Y(cast(models.CulturePlace.geom, Geometry(geometry_type="POINT", srid=4326))),
                ).where(
                    models.CulturePlace.origin.is_(None),
                    models.CulturePlace.osm_id.is_(None),
                )
            ).all()
            if _infer_demo_origin(place, float(lon), float(lat), demo_places)
        )
        return {"osm": int(osm_count), "demo": demo_count}

    osm_result = db.execute(
        text("""
            UPDATE culture_place
            SET origin = 'osm'
            WHERE origin IS NULL AND osm_id IS NOT NULL
        """)
    )
    demo_result = 0
    for demo in demo_places:
        result = db.execute(
            text("""
                UPDATE culture_place
                SET origin = 'demo'
                WHERE origin IS NULL
                  AND osm_id IS NULL
                  AND name = :name
                  AND ST_DWithin(
                      geom,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                      1
                  )
            """),
            demo,
        )
        demo_result += max(0, result.rowcount or 0)
    return {"osm": max(0, osm_result.rowcount or 0), "demo": demo_result}


def _load_demo_places() -> list[dict[str, Any]]:
    from scripts.init_data import PLACES

    return [
        {"name": place[0], "lat": float(place[3]), "lon": float(place[4])}
        for place in PLACES
    ]


def _infer_origin(
    place: models.CulturePlace,
    lon: float,
    lat: float,
    demo_places: list[dict[str, Any]],
) -> str | None:
    if place.origin:
        return place.origin
    if place.osm_id is not None:
        return "osm"
    if _infer_demo_origin(place, lon, lat, demo_places):
        return "demo"
    return None


def _infer_demo_origin(
    place: models.CulturePlace,
    lon: float,
    lat: float,
    demo_places: list[dict[str, Any]],
) -> bool:
    for demo in demo_places:
        if place.name == demo["name"] and _distance_meters(lon, lat, demo["lon"], demo["lat"]) <= 1:
            return True
    return False


def _classify_osm_place(
    place: models.CulturePlace,
    poi: models.OSMPOI,
    taxonomy: dict[str, Any],
    effective: Any,
) -> Classification:
    tags = poi.tags or {}
    facts = {
        "name": place.name,
        "tags": tags,
        "wikidata_id": poi.wikidata_id or place.wikidata_id,
        "wikidata_description": poi.wikidata_description,
        "wikipedia_extract": poi.wikipedia_extract,
        "wikipedia_url": poi.wikipedia_url,
        "wikivoyage_extract": poi.wikivoyage_extract,
        "wikipedia_article_verified": bool(poi.wikipedia_extract and poi.wikipedia_url),
        "wikivoyage_verified": bool(poi.wikivoyage_extract and poi.wikivoyage_url),
        "ai_summary": place.ai_summary,
        "ai_summary_sources": place.ai_summary_sources,
        "ai_summary_significance_verified": place.ai_summary_significance_verified,
        "quality_description": effective.description_quality
        if effective.effective_description_source
        else None,
    }
    return classify(facts, taxonomy)


def _classify_demo(
    place: models.CulturePlace,
    distance: float | None,
    taxonomy: dict[str, Any],
) -> Classification:
    if distance is None:
        return _outside_radius_result(taxonomy)
    return Classification(
        category=None,
        subcategory=None,
        object_class="unclassified",
        decision="include",
        exclusion_reason=None,
        size_priority=place.size_priority,
        legacy_type1=None,
        legacy_type2=None,
        evidence=(),
        taxonomy_version=str(taxonomy["version"]),
    )


def _effective_description(
    place: models.CulturePlace,
    settings: dict[str, Any],
    *,
    force: bool,
) -> Any:
    if not force and place.description_checked_at is not None:
        return EffectiveDescription(
            effective_description=None,
            effective_description_source=place.effective_description_source,
            description_quality=place.description_quality or "empty",
        )
    return pick_effective_description(
        {
            "history": place.history,
            "short_description": place.short_description,
            "description_source": place.description_source,
            "ai_summary": place.ai_summary,
            "ai_summary_sources": place.ai_summary_sources,
        },
        place.name,
        settings,
    )


def _pending_result(taxonomy: dict[str, Any], reason: str) -> Classification:
    return Classification(
        category=None,
        subcategory=None,
        object_class="unclassified",
        decision="pending_review",
        exclusion_reason="pending_review",
        size_priority=0.0,
        legacy_type1=None,
        legacy_type2=None,
        evidence=({"rule": reason, "fact": reason, "source": "automatic"},),
        taxonomy_version=str(taxonomy["version"]),
    )


def _outside_radius_result(
    taxonomy: dict[str, Any],
    *,
    previous: Classification | None = None,
) -> Classification:
    return Classification(
        category=previous.category if previous else None,
        subcategory=previous.subcategory if previous else None,
        object_class=previous.object_class if previous else "unclassified",
        decision="excluded",
        exclusion_reason="outside_railway_radius",
        size_priority=previous.size_priority if previous else 0.0,
        legacy_type1=previous.legacy_type1 if previous else None,
        legacy_type2=previous.legacy_type2 if previous else None,
        evidence=previous.evidence if previous else ({
            "rule": "R-001",
            "fact": "outside_railway_radius",
            "source": "railway_distance",
        },),
        taxonomy_version=str(taxonomy["version"]),
    )


def _locked_result(place: models.CulturePlace, taxonomy: dict[str, Any]) -> Classification:
    if place.exclusion_reason == "pending_review":
        decision = "pending_review"
    elif place.excluded_from_map:
        decision = "excluded"
    else:
        decision = "include"
    return Classification(
        category=place.category,
        subcategory=place.subcategory,
        object_class=place.object_class,
        decision=decision,
        exclusion_reason=place.exclusion_reason,
        size_priority=place.size_priority,
        legacy_type1=place.type1.value,
        legacy_type2=place.type2.value,
        evidence=tuple(place.classification_evidence or ()),
        taxonomy_version=place.taxonomy_version or str(taxonomy["version"]),
    )


def _restore_locked_result(
    place: models.CulturePlace,
    taxonomy: dict[str, Any],
    *,
    previous_state: dict[str, Any] | None = None,
) -> Classification:
    result = _locked_result(place, taxonomy)
    manual_exclusion = any(
        item.get("rule") == "manual_exclusion"
        for item in (place.classification_evidence or ())
        if isinstance(item, dict)
    )
    manual_inclusion = any(
        item.get("rule") == "manual_include"
        for item in (place.classification_evidence or ())
        if isinstance(item, dict)
    )
    if manual_exclusion:
        decision = "excluded"
        exclusion_reason = (
            previous_state.get("exclusion_reason")
            if previous_state
            and previous_state.get("excluded_from_map")
            and previous_state.get("exclusion_reason") != "outside_railway_radius"
            else "manual_exclusion"
        )
    elif previous_state is not None:
        was_excluded = previous_state.get("excluded_from_map", False)
        exclusion_reason = previous_state.get("exclusion_reason") if was_excluded else None
        if not was_excluded:
            decision = "include"
        elif exclusion_reason == "pending_review":
            decision = "pending_review"
        else:
            decision = "excluded"
    elif manual_inclusion:
        decision = "include"
        exclusion_reason = None
    else:
        decision = "pending_review"
        exclusion_reason = "pending_review"
    return Classification(
        category=result.category,
        subcategory=result.subcategory,
        object_class=result.object_class,
        decision=decision,
        exclusion_reason=exclusion_reason,
        size_priority=result.size_priority,
        legacy_type1=result.legacy_type1,
        legacy_type2=result.legacy_type2,
        evidence=result.evidence,
        taxonomy_version=result.taxonomy_version or str(taxonomy["version"]),
    )


def _radius_restore_state(db: Session, place_id: int) -> dict[str, Any] | None:
    return db.execute(
        select(models.ClassificationAuditLog.old_value)
        .where(
            models.ClassificationAuditLog.culture_place_id == place_id,
            models.ClassificationAuditLog.action == "auto_radius_flip",
            models.ClassificationAuditLog.new_value["exclusion_reason"].as_string()
            == "outside_railway_radius",
        )
        .order_by(models.ClassificationAuditLog.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _apply_result(
    db: Session,
    place: models.CulturePlace,
    result: Classification,
    distance: float | None,
    taxonomy: dict[str, Any],
    effective: Any,
    *,
    is_demo: bool,
    dry_run: bool,
) -> tuple[bool, bool]:
    now = datetime.now(timezone.utc)
    old = _classification_snapshot(place)
    current_distance = place.railway_distance_m
    distance_changed = distance != current_distance or place.railway_distance_checked_at is None
    desired = {
        "category": None if is_demo else result.category,
        "subcategory": None if is_demo else result.subcategory,
        "object_class": "unclassified" if is_demo else result.object_class,
        "excluded_from_map": result.decision != "include",
        "exclusion_reason": result.exclusion_reason,
        "size_priority": result.size_priority,
        "classification_evidence": list(result.evidence),
    }
    result_fields = tuple(desired)
    classification_changed = any(
        getattr(place, field) != desired[field]
        for field in result_fields
        if field not in {"taxonomy_version"}
    )
    first_classification = place.classified_at is None
    force_radius = result.exclusion_reason == "outside_railway_radius"
    restore_radius = (
        place.classification_locked
        and place.exclusion_reason == "outside_railway_radius"
        and distance is not None
    )
    allow_classification_update = not place.classification_locked or force_radius or restore_radius
    classification_applied = allow_classification_update and (
        classification_changed or first_classification
    )
    if allow_classification_update:
        if not dry_run and (
            not place.classification_locked or force_radius or restore_radius
        ):
            for field, value in desired.items():
                if (
                    field in {
                        "category",
                        "subcategory",
                        "object_class",
                        "size_priority",
                        "classification_evidence",
                    }
                    and force_radius
                ):
                    continue
                setattr(place, field, value)
        if not dry_run and (classification_changed or first_classification):
            place.classified_at = now
            if not place.classification_locked:
                place.taxonomy_version = result.taxonomy_version
    if not dry_run and not place.classification_locked and result.legacy_type1:
        place.type1 = models.Type1(result.legacy_type1)
    if not dry_run and not place.classification_locked and result.legacy_type2:
        place.type2 = models.Type2(result.legacy_type2)

    if effective is not None:
        description_changed = (
            place.effective_description_source != effective.effective_description_source
            or place.description_quality != effective.description_quality
        )
        description_changed = description_changed or place.description_checked_at is None
        if description_changed and not dry_run:
            place.effective_description_source = effective.effective_description_source
            place.description_quality = effective.description_quality
            place.description_checked_at = now
    else:
        description_changed = False

    new = dict(old)
    new.update(desired)
    if classification_changed or first_classification:
        new["taxonomy_version"] = result.taxonomy_version
        new["classified_at"] = now
    if effective is not None and description_changed:
        new["effective_description_source"] = effective.effective_description_source
        new["description_quality"] = effective.description_quality
    if distance_changed:
        new["railway_distance_m"] = distance
    changed = classification_applied
    if old["classified_at"] is not None and _audit_relevant_change(old, new) and not dry_run:
        db_log = models.ClassificationAuditLog(
            culture_place_id=place.id,
            osm_type=place.osm_type,
            osm_id=place.osm_id,
            action="auto_radius_flip"
            if old["exclusion_reason"] == "outside_railway_radius"
            or new["exclusion_reason"] == "outside_railway_radius"
            else "auto_reclassify",
            actor="classify",
            old_value=_json_snapshot(old),
            new_value=_json_snapshot(new),
        )
        db.add(db_log)
    if dry_run:
        return changed, bool(effective is not None and description_changed)
    if distance_changed:
        place.railway_distance_m = distance
        place.railway_distance_checked_at = now
    return changed, bool(effective is not None and description_changed)


def _classification_snapshot(place: models.CulturePlace) -> dict[str, Any]:
    return {
        "category": place.category,
        "subcategory": place.subcategory,
        "object_class": place.object_class,
        "excluded_from_map": place.excluded_from_map,
        "exclusion_reason": place.exclusion_reason,
        "size_priority": place.size_priority,
        "classification_evidence": place.classification_evidence,
        "classified_at": place.classified_at,
        "taxonomy_version": place.taxonomy_version,
        "effective_description_source": place.effective_description_source,
        "description_quality": place.description_quality,
        "railway_distance_m": place.railway_distance_m,
    }


def _json_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = dict(snapshot)
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def _audit_relevant_change(old: dict[str, Any], new: dict[str, Any]) -> bool:
    fields = ("subcategory", "excluded_from_map", "exclusion_reason")
    return any(old[field] != new[field] for field in fields)


def _unidentified_row(place: models.CulturePlace, origin: str | None) -> dict[str, Any]:
    return {
        "culture_place_id": place.id,
        "name": place.name,
        "osm_type": place.osm_type or "",
        "osm_id": place.osm_id or "",
        "origin": origin or "",
        "review_status": "pending_review",
    }


def _pending_row(place: models.CulturePlace, result: Classification) -> dict[str, Any]:
    return {
        "culture_place_id": place.id,
        "name": place.name,
        "osm_type": place.osm_type or "",
        "osm_id": place.osm_id or "",
        "action": "",
        "category": result.category or "",
        "subcategory": result.subcategory or "",
        "object_class": result.object_class,
        "size_priority": result.size_priority,
        "exclusion_reason": result.exclusion_reason or "",
        "note": "",
    }


def _increment_priority_histogram(histogram: dict[str, int], priority: float) -> None:
    lower = math.floor(float(priority))
    key = f"{lower:.1f}-{lower + 1:.1f}"
    histogram[key] = histogram.get(key, 0) + 1


def _find_demo_duplicates(
    demos: list[dict[str, Any]],
    osm_places: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    duplicates = []
    for demo in demos:
        demo_name = normalize_name(demo["name"])
        for osm in osm_places:
            distance = _distance_meters(demo["lon"], demo["lat"], osm["lon"], osm["lat"])
            similarity = SequenceMatcher(
                None,
                demo_name,
                normalize_name(osm["name"]),
            ).ratio()
            same_wikidata = bool(
                demo.get("wikidata_id")
                and demo["wikidata_id"] == osm.get("wikidata_id")
            )
            if same_wikidata or (distance <= 300 and similarity >= 0.8):
                duplicates.append({
                    "demo_name": demo["name"],
                    "osm_name": osm["name"],
                    "osm_type": osm["osm_type"],
                    "osm_id": osm["osm_id"],
                    "distance_m": round(distance, 1),
                    "name_similarity": round(similarity, 3),
                    "wikidata_match": same_wikidata,
                })
    return duplicates


def _distance_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = lat2_rad - lat1_rad
    delta_lon = math.radians(lon2 - lon1)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(haversine)))


def _write_reports(summary: dict[str, Any], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        reports_dir / "classification_review.csv",
        sorted(
            summary["pending"],
            key=lambda row: (
                -row["size_priority"],
                row["culture_place_id"],
            ),
        ),
        [
            "culture_place_id",
            "name",
            "osm_type",
            "osm_id",
            "action",
            "category",
            "subcategory",
            "object_class",
            "size_priority",
            "exclusion_reason",
            "note",
        ],
    )
    _write_csv(
        reports_dir / "unidentified_rows.csv",
        summary["unidentified"],
        ["culture_place_id", "name", "osm_type", "osm_id", "origin", "review_status"],
    )
    print("Сводка решений:")
    for decision, count in summary["decisions"].items():
        print(f"  {decision}: {count}")
    print("Подкатегория × решение:")
    for subcategory, decisions in sorted(summary["by_subcategory"].items()):
        print(f"  {subcategory}: {decisions}")
    print(f"Гистограмма size_priority: {summary['priority_histogram']}")
    print(f"Гистограмма size_priority demo: {summary['demo_priority_histogram']}")
    print(
        "Исключения OSM-кандидатов: "
        f"активных {summary['registry_active']}, снятых {summary['registry_resolved']}"
    )
    print(f"Неопознанных строк: {len(summary['unidentified'])}")
    print(f"Возможных пар demo ↔ OSM: {len(summary['demo_duplicates'])}")
    for duplicate in summary["demo_duplicates"]:
        print(
            f"  {duplicate['demo_name']} ↔ {duplicate['osm_name']} "
            f"({duplicate['distance_m']} м, сходство {duplicate['name_similarity']})"
        )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Классификация объектов и проверка расстояния до точек железной дороги."
    )
    parser.add_argument("--dry-run", action="store_true", help="Не сохранять изменения в БД.")
    parser.add_argument("--report", action="store_true", help="Создать CSV-отчёты и сводку.")
    parser.add_argument(
        "--recompute-descriptions",
        action="store_true",
        help="Повторно проверить эффективное описание для всех объектов.",
    )
    parser.add_argument(
        "--backfill-origin",
        action="store_true",
        help="Определить происхождение существующих строк без перезаписи неизвестных.",
    )
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    ensure_taxonomy_schema(engine)
    db = SessionLocal()
    try:
        summary = classify_places(
            db,
            taxonomy,
            dry_run=args.dry_run,
            backfill_origin=args.backfill_origin,
            recompute_descriptions=args.recompute_descriptions,
            reports_dir=REPORTS_DIR if args.report else None,
        )
        print(
            f"{'Сухой прогон' if args.dry_run else 'Классификация завершена'}: "
            f"изменений классификации {summary['classification_updates']}, "
            f"описаний {summary['description_updates']}, "
            f"расстояний {summary['distance_updates']}."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
