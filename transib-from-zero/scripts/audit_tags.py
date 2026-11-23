"""Аудит OSM-тегов и расстояний между точками ЖД без изменения данных."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

from app.database import engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = PROJECT_ROOT / "data" / "reports" / "tag_audit.md"
TAG_SOURCES = {
    "osm_pois": "FROM osm_pois AS p",
    "osm_pois_near_railway": (
        "FROM osm_pois_near_railway AS n "
        "JOIN osm_pois AS p ON p.id = n.osm_poi_id"
    ),
}
RAILWAY_NAME_PATTERN = (
    r"железнодорож|железной[[:space:]]+дороги|паровоз|локомотив|ж/д|railway|"
    r"вокзал|станц|депо|рельс|(^|[^[:alnum:]_])жд([^[:alnum:]_]|$)"
)


def _read_audit_data(connection):
    results = {}
    connection.exec_driver_sql("SET TRANSACTION READ ONLY")

    for source, relation in TAG_SOURCES.items():
        results[source] = {
            "counts": connection.execute(
                text(f"SELECT COUNT(*) {relation}")
            ).scalar_one(),
            "tags": connection.execute(
                text(f"""
                    SELECT tag.key, tag.value, COUNT(*) AS object_count
                    {relation}
                    CROSS JOIN LATERAL json_each_text(p.tags) AS tag
                    WHERE tag.key IN (
                        'historic', 'memorial', 'tourism', 'amenity', 'building',
                        'railway', 'museum', 'religion', 'denomination',
                        'attraction', 'theatre:genre'
                    )
                       OR tag.key LIKE 'heritage%'
                       OR tag.key LIKE 'ref:%'
                    GROUP BY tag.key, tag.value
                    ORDER BY tag.key, object_count DESC, tag.value
                """)
            ).all(),
            "railway_names": connection.execute(
                text(f"""
                    SELECT COALESCE(p.tags ->> 'name:ru', p.tags ->> 'name') AS name,
                           COUNT(*) AS object_count
                    {relation}
                    WHERE COALESCE(
                              p.tags ->> 'name:ru',
                              p.tags ->> 'name'
                          ) ~* :pattern
                    GROUP BY COALESCE(
                        p.tags ->> 'name:ru',
                        p.tags ->> 'name'
                    )
                    ORDER BY object_count DESC, name
                    LIMIT 50
                """),
                {"pattern": RAILWAY_NAME_PATTERN},
            ).all(),
        }

    results["radius_counts"] = connection.execute(text("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (
                   WHERE EXISTS (
                       SELECT 1
                       FROM raw_railway_points AS r
                       WHERE ST_DWithin(
                           p.geom::geography,
                           r.geom::geography,
                           2500
                       )
                   )
               ) AS within_2500_m,
               COUNT(*) FILTER (
                   WHERE EXISTS (
                       SELECT 1
                       FROM raw_railway_points AS r
                       WHERE ST_DWithin(
                           p.geom::geography,
                           r.geom::geography,
                           5000
                       )
                   )
               ) AS within_5000_m
        FROM osm_pois AS p
    """)).one()

    results["railway_spacing"] = connection.execute(text("""
        WITH adjacent_points AS (
            SELECT track_id,
                   ST_Distance(
                       geom::geography,
                       LAG(geom::geography) OVER (
                           PARTITION BY track_id
                           ORDER BY km, measure
                       )
                   ) AS gap_m
            FROM raw_railway_points
        )
        SELECT COUNT(gap_m) AS gap_count,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY gap_m) AS median_m,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY gap_m) AS p95_m,
               MAX(gap_m) AS max_m,
               COUNT(*) FILTER (WHERE gap_m > 500) AS gaps_over_500_m
        FROM adjacent_points
        WHERE gap_m IS NOT NULL
    """)).one()

    results["railway_order_ties"] = connection.execute(text("""
        WITH ordering_keys AS (
            SELECT track_id, km, measure, COUNT(*) AS point_count
            FROM raw_railway_points
            GROUP BY track_id, km, measure
        )
        SELECT COUNT(*) AS distinct_order_keys,
               SUM(point_count) AS point_count,
               SUM(point_count - 1) AS repeated_order_rows,
               COUNT(*) FILTER (WHERE point_count > 1) AS tied_keys,
               MAX(point_count) AS largest_tie_group
        FROM ordering_keys
    """)).one()

    results["railway_spacing_stable"] = connection.execute(text("""
        WITH adjacent_points AS (
            SELECT track_id,
                   ST_Distance(
                       geom::geography,
                       LAG(geom::geography) OVER (
                           PARTITION BY track_id
                           ORDER BY km, measure, id
                       )
                   ) AS gap_m
            FROM raw_railway_points
        )
        SELECT COUNT(gap_m) AS gap_count,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY gap_m) AS median_m,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY gap_m) AS p95_m,
               MAX(gap_m) AS max_m,
               COUNT(*) FILTER (WHERE gap_m > 500) AS gaps_over_500_m
        FROM adjacent_points
        WHERE gap_m IS NOT NULL
    """)).one()

    return results


def _markdown_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        cells = [str(value).replace("|", r"\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_report(results):
    lines = [
        "# Аудит OSM-тегов и шага точек ЖД",
        "",
        f"Дата аудита: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Все запросы к БД выполняются в транзакции `READ ONLY`.",
        "",
        "## Объекты и теги",
        "",
    ]
    for source, data in results.items():
        if source in {
            "radius_counts",
            "railway_spacing",
            "railway_order_ties",
            "railway_spacing_stable",
        }:
            continue
        lines.extend([
            f"### `{source}`",
            "",
            f"Всего объектов: **{data['counts']}**.",
            "",
            _markdown_table(
                ["Ключ", "Значение", "Число объектов"],
                data["tags"],
            ),
            "",
            "Топ-50 имён железнодорожной тематики "
            "(имя и число совпавших объектов):",
            "",
            _markdown_table(["Имя", "Число объектов"], data["railway_names"]),
            "",
        ])

    radius = results["radius_counts"]
    lines.extend([
        "## Радиусы от точек ЖД",
        "",
        _markdown_table(
            ["Все osm_pois", "≤ 2500 м", "≤ 5000 м"],
            [[radius.total, radius.within_2500_m, radius.within_5000_m]],
        ),
        "",
        "## Расстояния между соседними точками ЖД",
        "",
        _markdown_table(
            ["Соседних пар", "Медиана, м", "p95, м", "Максимум, м", "> 500 м"],
            [[
                results["railway_spacing"].gap_count,
                results["railway_spacing"].median_m,
                results["railway_spacing"].p95_m,
                results["railway_spacing"].max_m,
                results["railway_spacing"].gaps_over_500_m,
            ]],
        ),
        "",
        "### Неоднозначность порядка и стабильная диагностика",
        "",
        "Основная статистика выше использует нормативный порядок `(track_id, km, measure)`. "
        "При повторяющихся ключах соседство не детерминировано. Таблица ниже показывает "
        "число совпадающих ключей и диагностический пересчёт с `id` как последним "
        "tie-breaker; это не меняет нормативный запрос.",
        "",
        _markdown_table(
            [
                "Уникальных ключей",
                "Точек",
                "Строк сверх первой в группе",
                "Ключей с повторами",
                "Максимальный размер группы",
            ],
            [[
                results["railway_order_ties"].distinct_order_keys,
                results["railway_order_ties"].point_count,
                results["railway_order_ties"].repeated_order_rows,
                results["railway_order_ties"].tied_keys,
                results["railway_order_ties"].largest_tie_group,
            ]],
        ),
        "",
        _markdown_table(
            ["Порядок", "Соседних пар", "Медиана, м", "p95, м", "Максимум, м", "> 500 м"],
            [[
                "(track_id, km, measure, id)",
                results["railway_spacing_stable"].gap_count,
                results["railway_spacing_stable"].median_m,
                results["railway_spacing_stable"].p95_m,
                results["railway_spacing_stable"].max_m,
                results["railway_spacing_stable"].gaps_over_500_m,
            ]],
        ),
        "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Только чтение: аудит тегов osm_pois и расстояний между точками ЖД."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
        help="Файл Markdown-отчёта (по умолчанию data/reports/tag_audit.md).",
    )
    args = parser.parse_args(argv)

    audit_engine = create_engine(
        engine.url,
        connect_args={"connect_timeout": 5},
    )
    try:
        with audit_engine.connect() as connection:
            results = _read_audit_data(connection)
    finally:
        audit_engine.dispose()

    report = render_report(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Отчёт аудита сохранён: {args.output}")


if __name__ == "__main__":
    main()
