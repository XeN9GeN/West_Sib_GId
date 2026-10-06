from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class MarkerStyle(BaseModel):
    color: str
    icon: str
    shape: str


class CulturePlaceOut(BaseModel):
    id: int
    name: str
    type1: str
    type2: str
    lat: float
    lon: float
    size_priority: float
    short_description: str
    history: Optional[str] = None
    sources: Optional[List[str]] = None
    creation_date: Optional[date] = None
    rarity: Optional[str] = None
    photo_url: Optional[str] = None
    marker: MarkerStyle
    train_coord_id: Optional[int] = None


class TrainCoordOut(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    search_radius_m: float