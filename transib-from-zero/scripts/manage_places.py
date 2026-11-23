"""Ручное управление решениями классификатора и аудит действий владельца."""

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, engine
from app.description_quality import pick_effective_description
from app.migrations import ensure_taxonomy_schema
from app.taxonomy import classify, load_taxonomy, valid_ai_summary_sources


def list_pending(db: Session, limit: int = 100) -> list[models.CulturePlace]:
    if limit <= 0:
        raise ValueError("Лимит должен быть положительным числом.")
    return list(
        db.execute(
            select(models.CulturePlace)
            .where(models.CulturePlace.exclusion_reason == "pending_review")
            .order_by(models.CulturePlace.size_priority.desc(), models.CulturePlace.id)
            .limit(limit)
        ).scalars()
    )


def apply_manual_decision(
    db: Session,
    taxonomy: dict[str, Any],
    action: str,
    osm_type: str,
    osm_id: int,
    *,
    reason: str | None = None,
    subcategory_id: str | None = None,
    note: str | None = None,
    description: str | None = None,
) -> models.CulturePlace:
    place = _find_place(db, osm_type, osm_id)
    old_value = _snapshot(place)
    audit_action = action
    if action == "include":
        _require_note(note)
        subcategory = _find_subcategory(taxonomy, subcategory_id)
        _require_in_radius(place)
        _check_hard_exclusion(db, place, osm_type, osm_id, subcategory_id, taxonomy)
        place.category = _category_for(taxonomy, subcategory_id)
        place.subcategory = subcategory_id
        place.object_class = subcategory["default_class"]
        place.type1 = models.Type1(subcategory["legacy_type1"])
        place.type2 = models.Type2(subcategory["legacy_type2"])
        place.size_priority = subcategory["base_priority"]
        place.excluded_from_map = False
        place.exclusion_reason = None
        place.classification_evidence = [{
            "rule": "manual_include",
            "fact": note.strip(),
            "source": "manual",
        }]
        place.taxonomy_version = str(taxonomy["version"])
        place.classified_at = datetime.now(timezone.utc)
        place.classification_locked = True
        audit_action = "manual_include"
    elif action == "exclude":
        _require_note(note, optional=True)
        reason = reason or "manual_exclusion"
        if reason == "outside_railway_radius":
            raise ValueError("Причину outside_railway_radius задаёт только расчёт расстояния.")
        if reason not in taxonomy["exclusion_reasons"]:
            raise ValueError(f"Неизвестная причина исключения: {reason}")
        place.excluded_from_map = True
        place.exclusion_reason = reason
        place.classification_locked = True
        place.classification_evidence = [{
            "rule": "manual_exclusion",
            "fact": note.strip() if note else reason,
            "source": "manual",
        }]
        audit_action = "manual_exclude"
    elif action == "set-category":
        _require_note(note, optional=True)
        subcategory = _find_subcategory(taxonomy, subcategory_id)
        _require_in_radius(place)
        place.category = _category_for(taxonomy, subcategory_id)
        place.subcategory = subcategory_id
        place.object_class = subcategory["default_class"]
        place.type1 = models.Type1(subcategory["legacy_type1"])
        place.type2 = models.Type2(subcategory["legacy_type2"])
        place.size_priority = subcategory["base_priority"]
        place.classification_evidence = [{
            "rule": "manual_set_category",
            "fact": note.strip() if note else subcategory_id,
            "source": "manual",
        }]
        place.taxonomy_version = str(taxonomy["version"])
        place.classified_at = datetime.now(timezone.utc)
        place.classification_locked = True
        audit_action = "manual_set_category"
    elif action == "set-description":
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Ручное описание не должно быть пустым.")
        place.short_description = description.strip()
        place.description_source = "manual"
        effective = pick_effective_description(
            _description_candidates(place),
            place.name,
            taxonomy["settings"],
        )
        place.effective_description_source = effective.effective_description_source
        place.description_quality = effective.description_quality
        place.description_checked_at = datetime.now(timezone.utc)
        place.classification_locked = True
        audit_action = "manual_set_description"
    elif action in {"verify-ai-significance", "unverify-ai-significance"}:
        _require_note(note)
        if action == "verify-ai-significance":
            if not place.ai_summary or not valid_ai_summary_sources(place.ai_summary_sources):
                raise ValueError("Для подтверждения нужны ai_summary и корректные HTTPS-источники.")
            place.ai_summary_significance_verified = True
            audit_action = "manual_verify_ai_significance"
        else:
            place.ai_summary_significance_verified = False
            audit_action = "manual_unverify_ai_significance"
        place.classification_locked = True
    elif action == "unlock":
        place.classification_locked = False
        audit_action = "manual_unlock"
    else:
        raise ValueError(f"Неизвестное ручное действие: {action}")

    db.add(models.ClassificationAuditLog(
        culture_place_id=place.id,
        osm_type=place.osm_type,
        osm_id=place.osm_id,
        action=audit_action,
        actor="manual",
        old_value=old_value,
        new_value=_snapshot(place),
        note=note,
    ))
    return place


def apply_decisions_csv(
    db: Session,
    taxonomy: dict[str, Any],
    csv_path: Path,
    *,
    dry_run: bool,
) -> int:
    """Проверяет CSV целиком; при ошибке транзакция должна быть откачена вызывающим кодом."""
    required = {"osm_type", "osm_id", "action", "subcategory", "note"}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV должен содержать osm_type, osm_id, action, subcategory, note.")
        rows = list(reader)

    for row_number, row in enumerate(rows, start=2):
        try:
            osm_id = int(row["osm_id"])
            action = row["action"]
            if action not in {"include", "exclude", "set-category"}:
                raise ValueError(f"Недопустимое действие: {action}")
            apply_manual_decision(
                db,
                taxonomy,
                action,
                row["osm_type"],
                osm_id,
                reason=row.get("reason"),
                subcategory_id=row.get("subcategory") or None,
                note=row.get("note"),
            )
        except (ValueError, KeyError) as error:
            raise ValueError(f"Ошибка CSV в строке {row_number}: {error}") from error
    if dry_run:
        db.rollback()
    return len(rows)


def _find_place(db: Session, osm_type: str, osm_id: int) -> models.CulturePlace:
    place = db.execute(
        select(models.CulturePlace).where(
            models.CulturePlace.osm_type == osm_type,
            models.CulturePlace.osm_id == osm_id,
        )
    ).scalar_one_or_none()
    if place is None:
        raise ValueError(f"Объект {osm_type}/{osm_id} отсутствует в culture_place.")
    return place


def _find_subcategory(
    taxonomy: dict[str, Any],
    subcategory_id: str | None,
) -> dict[str, Any]:
    if not subcategory_id:
        raise ValueError("Не указана подкатегория.")
    for category in taxonomy["categories"]:
        for subcategory in category["subcategories"]:
            if subcategory["id"] == subcategory_id:
                return subcategory
    raise ValueError(f"Неизвестная подкатегория: {subcategory_id}")


def _category_for(taxonomy: dict[str, Any], subcategory_id: str) -> str:
    return next(
        category["id"]
        for category in taxonomy["categories"]
        if any(subcategory["id"] == subcategory_id for subcategory in category["subcategories"])
    )


def _require_in_radius(place: models.CulturePlace) -> None:
    if place.railway_distance_checked_at is None:
        raise ValueError("Расстояние до железной дороги ещё не проверено.")
    if place.railway_distance_m is None:
        raise ValueError("Объект за пределами радиуса 2500 м; включение запрещено.")


def _check_hard_exclusion(
    db: Session,
    place: models.CulturePlace,
    osm_type: str,
    osm_id: int,
    subcategory_id: str,
    taxonomy: dict[str, Any],
) -> None:
    poi = db.execute(
        select(models.OSMPOI).where(
            models.OSMPOI.osm_type == osm_type,
            models.OSMPOI.osm_id == osm_id,
        )
    ).scalar_one_or_none()
    if poi is None:
        return
    result = classify(
        {
            "name": place.name,
            "tags": poi.tags or {},
            "wikidata_id": poi.wikidata_id or place.wikidata_id,
        },
        taxonomy,
    )
    if result.exclusion_reason is None:
        return
    rule = next(
        (
            rule
            for rule in taxonomy["exclude_rules"]
            if rule["reason"] == result.exclusion_reason
            and any(
                evidence.get("rule") == rule["id"]
                for evidence in result.evidence
            )
        ),
        None,
    )
    if rule is None:
        return
    if not rule["overridable"]:
        raise ValueError(
            f"Включение запрещено жёстким правилом {rule['id']} "
            f"(подкатегория {subcategory_id})."
        )


def _require_note(note: str | None, *, optional: bool = False) -> None:
    if not optional and (not isinstance(note, str) or not note.strip()):
        raise ValueError("Для решения требуется непустое основание в --note.")


def _description_candidates(place: models.CulturePlace) -> dict[str, Any]:
    return {
        "history": place.history,
        "short_description": place.short_description,
        "description_source": place.description_source,
        "ai_summary": place.ai_summary,
        "ai_summary_sources": place.ai_summary_sources,
    }


def _snapshot(place: models.CulturePlace) -> dict[str, Any]:
    fields = (
        "category",
        "subcategory",
        "object_class",
        "type1",
        "type2",
        "excluded_from_map",
        "exclusion_reason",
        "classification_locked",
        "size_priority",
        "classification_evidence",
        "taxonomy_version",
        "classified_at",
        "short_description",
        "description_source",
        "effective_description_source",
        "description_quality",
        "description_checked_at",
        "ai_summary_significance_verified",
    )
    snapshot = {}
    for field in fields:
        value = getattr(place, field)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, (models.Type1, models.Type2)):
            value = value.value
        snapshot[field] = value
    return snapshot


def _print_place(place: models.CulturePlace) -> None:
    print(
        f"{place.osm_type}/{place.osm_id}: {place.name}; "
        f"{place.category or '-'} / {place.subcategory or '-'}; "
        f"{place.exclusion_reason or 'включён'}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ручное управление классификацией объектов.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pending = subparsers.add_parser("list-pending")
    pending.add_argument("--limit", type=int, default=100)

    for command in ("exclude", "include", "set-category", "set-description",
                    "verify-ai-significance", "unverify-ai-significance", "unlock"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("osm_type")
        command_parser.add_argument("osm_id", type=int)
        if command in {"exclude", "include", "set-category"}:
            if command == "exclude":
                command_parser.add_argument("--reason")
            if command in {"include", "set-category"}:
                command_parser.add_argument("--subcategory", required=True)
            command_parser.add_argument("--note")
        elif command == "set-description":
            command_parser.add_argument("description")
        elif command in {"verify-ai-significance", "unverify-ai-significance"}:
            command_parser.add_argument("--note", required=True)

    apply_parser = subparsers.add_parser("apply-decisions")
    apply_parser.add_argument("file", type=Path)
    apply_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    ensure_taxonomy_schema(engine)
    db = SessionLocal()
    try:
        if args.command == "list-pending":
            for place in list_pending(db, args.limit):
                _print_place(place)
            return
        if args.command == "apply-decisions":
            count = apply_decisions_csv(db, taxonomy, args.file, dry_run=args.dry_run)
            if not args.dry_run:
                db.commit()
            print(f"Обработано решений: {count}.")
            return
        action = args.command
        place = apply_manual_decision(
            db,
            taxonomy,
            action,
            args.osm_type,
            args.osm_id,
            reason=getattr(args, "reason", None),
            subcategory_id=getattr(args, "subcategory", None),
            note=getattr(args, "note", None),
            description=getattr(args, "description", None),
        )
        db.commit()
        _print_place(place)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
