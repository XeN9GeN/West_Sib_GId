from sqlalchemy import text

from . import models


def ensure_taxonomy_schema(engine):
    with engine.begin() as connection:
        for column, definition in (
            ("category", "VARCHAR(48)"),
            ("subcategory", "VARCHAR(64)"),
            ("object_class", "VARCHAR(16) DEFAULT 'unclassified' NOT NULL"),
            ("excluded_from_map", "BOOLEAN DEFAULT false NOT NULL"),
            ("exclusion_reason", "VARCHAR(48)"),
            ("classification_locked", "BOOLEAN DEFAULT false NOT NULL"),
            ("classified_at", "TIMESTAMPTZ"),
            ("taxonomy_version", "VARCHAR(16)"),
            ("classification_evidence", "JSON"),
            ("ai_summary_significance_verified", "BOOLEAN DEFAULT false NOT NULL"),
            ("railway_distance_m", "DOUBLE PRECISION"),
            ("railway_distance_checked_at", "TIMESTAMPTZ"),
            ("description_source", "VARCHAR(32)"),
            ("effective_description_source", "VARCHAR(32)"),
            ("description_quality", "VARCHAR(24)"),
            ("description_checked_at", "TIMESTAMPTZ"),
            ("origin", "VARCHAR(16)"),
        ):
            connection.execute(text(
                f"ALTER TABLE culture_place ADD COLUMN IF NOT EXISTS {column} {definition}"
            ))

        connection.execute(text(
            "ALTER TABLE culture_place ALTER COLUMN origin SET DEFAULT 'osm'"
        ))

        models.ClassificationAuditLog.__table__.create(
            bind=connection,
            checkfirst=True,
        )
        models.OSMPOIExclusionRegistry.__table__.create(
            bind=connection,
            checkfirst=True,
        )

        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_culture_place_geom_geometry
            ON culture_place USING GIST ((geom::geometry))
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_culture_place_visible
            ON culture_place (size_priority)
            WHERE excluded_from_map = false
              AND classified_at IS NOT NULL
              AND railway_distance_m IS NOT NULL
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_osm_poi_exclusion_registry_active
            ON osm_poi_exclusion_registry (is_active)
            WHERE is_active = true
        """))


def ensure_osm_enrichment_schema(engine):
    with engine.begin() as connection:
        for column, definition in (
            ("wikidata_id", "VARCHAR(32)"),
            ("wikidata_label", "VARCHAR(512)"),
            ("wikidata_description", "TEXT"),
            ("wikipedia_extract", "TEXT"),
            ("wikipedia_url", "VARCHAR(1024)"),
            ("wikivoyage_extract", "TEXT"),
            ("wikivoyage_url", "VARCHAR(1024)"),
            ("image_url", "VARCHAR(1024)"),
            ("image_page_url", "VARCHAR(1024)"),
            ("image_attribution", "TEXT"),
        ):
            connection.execute(text(
                f"ALTER TABLE osm_pois ADD COLUMN IF NOT EXISTS {column} {definition}"
            ))

        for column, definition in (
            ("osm_type", "VARCHAR(16)"),
            ("osm_id", "BIGINT"),
            ("wikidata_id", "VARCHAR(32)"),
            ("photo_attribution", "TEXT"),
            ("ai_summary", "TEXT"),
            ("ai_summary_sources", "JSON"),
        ):
            connection.execute(text(
                f"ALTER TABLE culture_place ADD COLUMN IF NOT EXISTS {column} {definition}"
            ))

        connection.execute(text(
            "ALTER TABLE culture_place ALTER COLUMN short_description DROP NOT NULL"
        ))
        connection.execute(text(
            "ALTER TABLE culture_place ALTER COLUMN photo_url TYPE VARCHAR(1024)"
        ))
        connection.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_culture_place_osm_identity
            ON culture_place (osm_type, osm_id)
            WHERE osm_type IS NOT NULL AND osm_id IS NOT NULL
        """))
