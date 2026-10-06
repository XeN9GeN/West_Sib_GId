import enum
from sqlalchemy import (
    Column, Integer, String, Float, Enum, ForeignKey, Text, Date, ARRAY
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography, Geometry
from .database import Base


class Type1(str, enum.Enum):
    human = "human"
    nature = "nature"


class Type2(str, enum.Enum):
    # human-made
    museum = "museum"
    monument = "monument"
    architecture = "architecture"
    theater = "theater"
    temple = "temple"
    # natural
    lake = "lake"
    river = "river"
    mountain = "mountain"
    reserve = "reserve"
    forest = "forest"
    # historical-natural
    historic_nature = "historic_nature"


# цвет + иконка (Font Awesome) + форма для каждого типа
MARKER_STYLE = {
    Type2.museum:         {"color": "#8e44ad", "icon": "fa-landmark",       "shape": "pin"},
    Type2.monument:       {"color": "#c0392b", "icon": "fa-monument",       "shape": "pin"},
    Type2.architecture:   {"color": "#2980b9", "icon": "fa-building",       "shape": "pin"},
    Type2.theater:        {"color": "#e67e22", "icon": "fa-masks-theater",  "shape": "pin"},
    Type2.temple:         {"color": "#d4af37", "icon": "fa-church",         "shape": "pin"},
    Type2.lake:           {"color": "#1abc9c", "icon": "fa-water",          "shape": "circle"},
    Type2.river:          {"color": "#16a085", "icon": "fa-water",          "shape": "circle"},
    Type2.mountain:       {"color": "#7f8c8d", "icon": "fa-mountain",       "shape": "triangle"},
    Type2.reserve:        {"color": "#27ae60", "icon": "fa-tree",           "shape": "circle"},
    Type2.forest:         {"color": "#2ecc71", "icon": "fa-tree",           "shape": "circle"},
    Type2.historic_nature:{"color": "#f39c12", "icon": "fa-scroll",         "shape": "star"},
}


class TrainCoord(Base):
    __tablename__ = "train_coord"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    search_radius_m = Column(Float, nullable=False, default=15000)

    culture_places = relationship("CulturePlace", back_populates="train_coord")


class Railway(Base):
    __tablename__ = "railway"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=False)


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
    rarity = Column(String(32), nullable=True)  # common/rare/epic/legendary

    photo_url = Column(String(512), nullable=True)

    size_priority = Column(Float, nullable=False, default=1.0)  # 0.5 .. 3.0
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    train_coord_id = Column(Integer, ForeignKey("train_coord.id"), nullable=True)
    train_coord = relationship("TrainCoord", back_populates="culture_places")

    @property
    def marker(self):
        return MARKER_STYLE.get(self.type2, {"color": "#555", "icon": "fa-circle", "shape": "pin"})