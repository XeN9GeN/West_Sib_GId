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
    marker: MarkerStyle