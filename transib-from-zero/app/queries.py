"""Общие условия видимости объектов карты."""

VISIBLE_CONDITION = """
excluded_from_map = false
AND classified_at IS NOT NULL
AND railway_distance_checked_at IS NOT NULL
AND railway_distance_m IS NOT NULL
""".strip()
