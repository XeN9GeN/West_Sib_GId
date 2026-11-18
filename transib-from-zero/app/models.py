import enum
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, Text, Date, ARRAY
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
    short_description = Column(Text, nullable=False)
    history = Column(Text, nullable=True)
    sources = Column(ARRAY(String), nullable=True)
    creation_date = Column(Date, nullable=True)
    photo_url = Column(String(512), nullable=True)
    size_priority = Column(Float, nullable=False, default=1.0)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    train_coord_id = Column(Integer, ForeignKey("train_coord.id"), nullable=True)

    @property
    def marker(self):
        return MARKER_STYLE.get(self.type2, {"color": "#555", "icon": "fa-circle", "shape": "pin"})