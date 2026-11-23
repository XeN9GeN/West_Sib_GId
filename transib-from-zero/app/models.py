import enum
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    ARRAY,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography, Geometry
from .database import Base

class Type1(str, enum.Enum):
    human = "human"
    nature = "nature"

class Type2(str, enum.Enum):
    museum = "museum"
    monument = "monument"
    architecture = "architecture"
    theater = "theater"
    temple = "temple"
    lake = "lake"
    river = "river"
    reserve = "reserve"
    forest = "forest"
    historic_nature = "historic_nature"

MARKER_STYLE = {
    Type2.museum: {"color": "#8e44ad", "icon": "fa-landmark", "shape": "pin"},
    Type2.monument: {"color": "#c0392b", "icon": "fa-monument", "shape": "pin"},
    Type2.architecture: {"color": "#2980b9", "icon": "fa-building", "shape": "pin"},
    Type2.theater: {"color": "#e67e22", "icon": "fa-masks-theater", "shape": "pin"},
    Type2.temple: {"color": "#d4af37", "icon": "fa-church", "shape": "pin"},
    Type2.lake: {"color": "#1abc9c", "icon": "fa-water", "shape": "circle"},
    Type2.river: {"color": "#16a085", "icon": "fa-water", "shape": "circle"},
    Type2.reserve: {"color": "#27ae60", "icon": "fa-tree", "shape": "circle"},
    Type2.forest: {"color": "#2ecc71", "icon": "fa-tree", "shape": "circle"},
    Type2.historic_nature: {"color": "#f39c12", "icon": "fa-scroll", "shape": "star"},
}

class TrainCoord(Base):
    __tablename__ = "train_coord"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    search_radius_m = Column(Float, nullable=False, default=15000)

class RawRailwayPoint(Base):
    __tablename__ = "raw_railway_points"
    id = Column(Integer, primary_key = True)
    geom = Column(Geometry(geometry_type="Point", srid=4326), nullable = False)
    track_id = Column(String(32), nullable=False)
    km = Column(Integer, nullable=False)
    measure = Column(Float, nullable=False)

class OSMPOI(Base):
    __tablename__ = "osm_pois"
    id = Column(Integer, primary_key=True)
    osm_type = Column(String(16), nullable=False)
    osm_id = Column(BigInteger, nullable=False)
    name = Column(String(512), nullable=True)
    tags = Column(JSON, nullable=False)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    wikidata_id = Column(String(32), nullable=True)
    wikidata_label = Column(String(512), nullable=True)
    wikidata_description = Column(Text, nullable=True)
    wikipedia_extract = Column(Text, nullable=True)
    wikipedia_url = Column(String(1024), nullable=True)
    wikivoyage_extract = Column(Text, nullable=True)
    wikivoyage_url = Column(String(1024), nullable=True)
    image_url = Column(String(1024), nullable=True)
    image_page_url = Column(String(1024), nullable=True)
    image_attribution = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("osm_type", "osm_id", name="uq_osm_pois_osm_identity"),
    )

class OSMPOINearRailway(Base):
    __tablename__ = "osm_pois_near_railway"
    osm_poi_id = Column(
        Integer,
        ForeignKey("osm_pois.id", ondelete="CASCADE"),
        primary_key=True,
    )

class Railway(Base):#ready lines
    __tablename__ = "railway"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    geom = Column(Geometry(geometry_type="MULTILINESTRING", srid=4326), nullable=False)

class RailwayDetail(Base):
    __tablename__ = "railway_detail"
    zoom_level = Column(Integer, primary_key=True)
    geom = Column(Geometry(geometry_type="MULTILINESTRING", srid=4326), nullable=False)

class CulturePlace(Base):
    __tablename__ = "culture_place"
    __table_args__ = (
        Index(
            "idx_culture_place_visible",
            "size_priority",
            postgresql_where=text(
                "excluded_from_map = false AND classified_at IS NOT NULL "
                "AND railway_distance_m IS NOT NULL"
            ),
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    type1 = Column(Enum(Type1), nullable=False)
    type2 = Column(Enum(Type2), nullable=False, index=True)
    short_description = Column(Text, nullable=True)
    history = Column(Text, nullable=True)
    sources = Column(ARRAY(String), nullable=True)
    ai_summary = Column(Text, nullable=True)
    ai_summary_sources = Column(JSON, nullable=True)
    creation_date = Column(Date, nullable=True)
    photo_url = Column(String(1024), nullable=True)
    photo_attribution = Column(Text, nullable=True)
    osm_type = Column(String(16), nullable=True)
    osm_id = Column(BigInteger, nullable=True)
    wikidata_id = Column(String(32), nullable=True)
    size_priority = Column(Float, nullable=False, default=1.0)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    train_coord_id = Column(Integer, ForeignKey("train_coord.id"), nullable=True)
    category = Column(String(48), nullable=True)
    subcategory = Column(String(64), nullable=True)
    object_class = Column(String(16), nullable=False, default="unclassified", server_default="unclassified")
    excluded_from_map = Column(Boolean, nullable=False, default=False, server_default="false")
    exclusion_reason = Column(String(48), nullable=True)
    classification_locked = Column(Boolean, nullable=False, default=False, server_default="false")
    classified_at = Column(DateTime(timezone=True), nullable=True)
    taxonomy_version = Column(String(16), nullable=True)
    classification_evidence = Column(JSON, nullable=True)
    ai_summary_significance_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    railway_distance_m = Column(Float, nullable=True)
    railway_distance_checked_at = Column(DateTime(timezone=True), nullable=True)
    description_source = Column(String(32), nullable=True)
    effective_description_source = Column(String(32), nullable=True)
    description_quality = Column(String(24), nullable=True)
    description_checked_at = Column(DateTime(timezone=True), nullable=True)
    origin = Column(String(16), nullable=True, default="osm", server_default="osm")

    @property
    def marker(self):
        return MARKER_STYLE.get(self.type2, {"color": "#555", "icon": "fa-circle", "shape": "pin"})


class ClassificationAuditLog(Base):
    __tablename__ = "classification_audit_log"

    id = Column(Integer, primary_key=True)
    culture_place_id = Column(Integer, nullable=True)
    osm_type = Column(String(16), nullable=True)
    osm_id = Column(BigInteger, nullable=True)
    action = Column(String(40), nullable=False)
    actor = Column(String(16), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class OSMPOIExclusionRegistry(Base):
    __tablename__ = "osm_poi_exclusion_registry"

    id = Column(Integer, primary_key=True)
    osm_poi_id = Column(
        Integer,
        ForeignKey("osm_pois.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    rule_id = Column(String(64), nullable=False)
    exclusion_reason = Column(String(48), nullable=False)
    taxonomy_version = Column(String(16), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_evaluated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "idx_osm_poi_exclusion_registry_active",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
    )