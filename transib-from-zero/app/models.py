import enum
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    ARRAY,
    UniqueConstraint,
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

    @property
    def marker(self):
        return MARKER_STYLE.get(self.type2, {"color": "#555", "icon": "fa-circle", "shape": "pin"})