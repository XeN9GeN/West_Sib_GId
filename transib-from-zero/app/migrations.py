from sqlalchemy import text


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
