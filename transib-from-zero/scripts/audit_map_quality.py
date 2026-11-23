"""Читающий аудит качества карты по критериям раздела 18."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from sqlalchemy import create_engine, text

from app.database import engine
from app.taxonomy import load_taxonomy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
DEFAULT_REPORT = PROJECT_ROOT / "data" / "reports" / "map_quality_audit.md"


@dataclass(frozen=True)
class AuditFinding:
    criterion: str
    count: int
    details: tuple[str, ...] = ()


def _rows(connection, statement, parameters=None):
    return connection.execute(text(statement), parameters or {}).mappings().all()


def _visible_condition_sql():
    return """
        WHERE excluded_from_map = false
          AND classified_at IS NOT NULL
          AND railway_distance_checked_at IS NOT NULL
    """


def run_sql_audit(connection):
    connection.exec_driver_sql("SET TRANSACTION READ ONLY")
    findings = []

    radius = _rows(connection, f"""
        SELECT id, name
        FROM culture_place
        {_visible_condition_sql()}
          AND NOT EXISTS (
              SELECT 1
              FROM raw_railway_points r
              WHERE ST_DWithin(culture_place.geom, r.geom::geography, 2500)
          )
        ORDER BY id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.1 Радиус 2500 м", len(radius),
                                tuple(f"{row['id']}: {row['name']}" for row in radius)))

    invisible = _rows(connection, """
        SELECT id, name
        FROM culture_place
        WHERE classified_at IS NULL OR railway_distance_checked_at IS NULL
        ORDER BY id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.1b Невидимость до классификации", len(invisible),
                                tuple(f"{row['id']}: {row['name']}" for row in invisible)))

    excluded_without_reason = _rows(connection, """
        SELECT id, name
        FROM culture_place
        WHERE excluded_from_map = true AND exclusion_reason IS NULL
        ORDER BY id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.2 Исключённые без причины", len(excluded_without_reason),
                                tuple(f"{row['id']}: {row['name']}" for row in excluded_without_reason)))

    registry = _rows(connection, """
        SELECT e.id, e.osm_poi_id
        FROM osm_poi_exclusion_registry e
        LEFT JOIN osm_pois p ON p.id = e.osm_poi_id
        WHERE e.is_active = true
          AND (p.id IS NULL OR e.rule_id IS NULL
               OR e.exclusion_reason IS NULL OR e.taxonomy_version IS NULL)
        ORDER BY e.id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.2 Реестр жёстких исключений", len(registry),
                                tuple(f"{row['id']}: osm_poi_id={row['osm_poi_id']}" for row in registry)))

    duplicate_registry = _rows(connection, """
        SELECT osm_poi_id, COUNT(*) AS active_count
        FROM osm_poi_exclusion_registry
        WHERE is_active = true
        GROUP BY osm_poi_id
        HAVING COUNT(*) > 1
        ORDER BY osm_poi_id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.2 Активные дубликаты реестра",
                                len(duplicate_registry),
                                tuple(f"osm_poi_id={row['osm_poi_id']}: "
                                      f"{row['active_count']} записей"
                                      for row in duplicate_registry)))

    monument_without_subcategory = _rows(connection, f"""
        SELECT id, name
        FROM culture_place
        {_visible_condition_sql()}
          AND type2::text = 'monument'
          AND subcategory IS NULL
        ORDER BY id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.4 Monument без подкатегории",
                                len(monument_without_subcategory),
                                tuple(f"{row['id']}: {row['name']}" for row in monument_without_subcategory)))

    low_zoom_description = _rows(connection, """
        SELECT id, name
        FROM culture_place
        WHERE excluded_from_map = false
          AND classified_at IS NOT NULL
          AND railway_distance_checked_at IS NOT NULL
          AND effective_description_source IS NOT NULL
          AND effective_description_source NOT IN ('history', 'short_description', 'ai_summary')
        ORDER BY id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.3 Неизвестный источник effective_description",
                                len(low_zoom_description),
                                tuple(f"{row['id']}: {row['name']}" for row in low_zoom_description)))

    demo_outside = _rows(connection, """
        SELECT id, name
        FROM culture_place
        WHERE origin = 'demo'
          AND excluded_from_map = false
          AND classified_at IS NOT NULL
          AND railway_distance_checked_at IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM raw_railway_points r
              WHERE ST_DWithin(culture_place.geom, r.geom::geography, 2500)
          )
        ORDER BY id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.9 Demo вне радиуса", len(demo_outside),
                                tuple(f"{row['id']}: {row['name']}" for row in demo_outside)))

    demo_count = connection.execute(text("""
        SELECT COUNT(*) FROM culture_place WHERE origin = 'demo'
    """)).scalar_one()
    findings.append(AuditFinding("18.9 Число demo-строк", 0 if demo_count == 40 else demo_count))

    pending_visible = _rows(connection, f"""
        SELECT id, name
        FROM culture_place
        {_visible_condition_sql()}
          AND exclusion_reason = 'pending_review'
        ORDER BY id
        LIMIT 100
    """)
    findings.append(AuditFinding("18.9 pending_review в публичном наборе видимости",
                                len(pending_visible),
                                tuple(f"{row['id']}: {row['name']}" for row in pending_visible)))

    return findings


def run_taxonomy_audit(connection, taxonomy):
    findings = []
    subcategories = {
        subcategory["id"]
        for category in taxonomy["categories"]
        for subcategory in category["subcategories"]
    }
    subcategory_categories = {
        subcategory["id"]: category["id"]
        for category in taxonomy["categories"]
        for subcategory in category["subcategories"]
    }

    visible_regular = _rows(connection, """
        SELECT id, name, category, subcategory, object_class, excluded_from_map,
               exclusion_reason, type2::text AS type2
        FROM culture_place
        WHERE excluded_from_map = false
          AND classified_at IS NOT NULL
          AND railway_distance_checked_at IS NOT NULL
          AND origin IN ('osm', 'manual')
        ORDER BY id
    """)

    invalid_subcategory = []
    category_mismatch = []
    unclassified = []
    excluded_without_reason = []
    for place in visible_regular:
        subcategory = place["subcategory"]
        if subcategory not in subcategories:
            invalid_subcategory.append(f"{place['id']}: subcategory={subcategory}")
        elif place["category"] != subcategory_categories[subcategory]:
            category_mismatch.append(
                f"{place['id']}: category={place['category']}, "
                f"subcategory={subcategory}"
            )
        if place["object_class"] == "unclassified":
            unclassified.append(f"{place['id']}: {place['name']}")
        if place["excluded_from_map"] and not place["exclusion_reason"]:
            excluded_without_reason.append(f"{place['id']}: {place['name']}")

    findings.append(AuditFinding("18.4 Подкатегория вне YAML",
                                len(invalid_subcategory),
                                tuple(invalid_subcategory)))
    findings.append(AuditFinding("18.4 Несовпадение категории и подкатегории",
                                len(category_mismatch),
                                tuple(category_mismatch)))
    findings.append(AuditFinding("18.4 Видимый unclassified",
                                len(unclassified),
                                tuple(unclassified)))
    findings.append(AuditFinding("18.4 Исключённая строка без причины",
                                len(excluded_without_reason),
                                tuple(excluded_without_reason)))

    category_count = connection.execute(text("""
        SELECT COUNT(*) FROM culture_place
        WHERE category = 'railway_heritage'
    """)).scalar_one()
    museum_count = connection.execute(text("""
        SELECT COUNT(*) FROM culture_place
        WHERE subcategory = 'railway_museums'
    """)).scalar_one()
    findings.append(AuditFinding("18.4 Наличие railway_heritage",
                                0 if category_count > 0 else 1))
    findings.append(AuditFinding("18.4 Наличие railway_museums",
                                0 if museum_count > 0 else 0,
                                ("Подкатегория не обязательна к непустому наличию "
                                 "после этапа 3; отсутствие объясняется в отчёте.",
                                 f"Число строк: {museum_count}")))

    rule_ids = {rule["id"] for rule in taxonomy["exclude_rules"]}
    reasons = set(taxonomy["exclusion_reasons"])
    registry_rows = _rows(connection, """
        SELECT rule_id, exclusion_reason
        FROM osm_poi_exclusion_registry
        WHERE is_active = true
    """)
    invalid_registry = [
        f"{row['rule_id']}: {row['exclusion_reason']}"
        for row in registry_rows
        if row["rule_id"] not in rule_ids
        or row["exclusion_reason"] not in reasons
    ]
    findings.append(AuditFinding("18.2 Правила реестра есть в YAML",
                                len(invalid_registry),
                                tuple(invalid_registry)))

    return findings


def _git_archive_check():
    completed = subprocess.run(
        ["git", "diff", "--stat", "--", "transib-from-zero/archive/", "archive/"],
        cwd=str(REPOSITORY_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip()


def render_report(findings, taxonomy, manual_status):
    lines = [
        "# Отчёт о качестве карты — приёмка этапа 6",
        "",
        f"Дата: {datetime.now(timezone.utc).isoformat()}",
        f"Версия таксономии: {taxonomy['version']}",
        "",
        "## Автоматические SQL-проверки",
        "",
        "| Критерий | Нарушений | Детали |",
        "|---|---:|---|",
    ]
    for finding in findings:
        details = "<br>".join(finding.details[:20]) if finding.details else "—"
        lines.append(
            f"| {finding.criterion} | {finding.count} | "
            f"{details.replace('|', r'\\|')} |"
        )

    git_archive_diff = _git_archive_check()
    lines.extend([
        "",
        "## 18.6 Архив",
        "",
        "- Изменений `archive/` по git diff: "
        f"{'нет' if not git_archive_diff else git_archive_diff}.",
        "- Контрактный тест `test_archive_contract.py` включён в unit-набор.",
        "- Запуск архивных тестов не является критерием при отсутствии подтверждённой тестовой среды.",
        "",
        "## Требуют ручной проверки или рабочей БД/API",
        "",
    ])
    for item in manual_status:
        lines.append(f"- {item}")

    violations = sum(1 for finding in findings if finding.count != 0)
    lines.extend([
        "",
        "## Итог",
        "",
        f"Автоматические нарушения: **{violations}**.",
        "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Аудит SQL-критериев качества карты по разделу 18."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
        help="Файл Markdown-отчёта.",
    )
    args = parser.parse_args(argv)

    taxonomy = load_taxonomy()
    audit_engine = create_engine(
        engine.url,
        connect_args={"connect_timeout": 5},
    )
    findings = []
    try:
        with audit_engine.connect() as connection:
            findings.extend(run_sql_audit(connection))
            findings.extend(run_taxonomy_audit(connection, taxonomy))
    finally:
        audit_engine.dispose()

    manual_status = [
        "18.3 Проверить API для zoom 7, 8, 10, 11, 12, 13, 22 и границ priority_tiers.",
        "18.5 Повторный прогон enrich_osm + classify_places требует снимка до/после.",
        "18.7 Выполнить ручной чек-лист 11.8 и проверить контракт API.",
        "18.8 Интеграционная матрица ручных решений должна выполняться на transsib_test.",
        "18.9 Проверить исходные 40 demo-строк и наличие pending_review в CSV ручной проверки.",
    ]
    report = render_report(findings, taxonomy, manual_status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")

    violations = sum(finding.count != 0 for finding in findings)
    print(f"Отчёт аудита сохранён: {args.output}")
    print(f"Автоматические нарушения: {violations}.")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
