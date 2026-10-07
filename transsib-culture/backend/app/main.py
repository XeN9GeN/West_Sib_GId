from typing import List, Optional
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, cast
from sqlalchemy.orm import Session
from geoalchemy2 import Geometry

from .database import SessionLocal
from . import models, schemas

app = FastAPI(title="TransSib Culture API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- эндпоинты ----------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/culture_places", response_model=List[schemas.CulturePlaceOut])
def culture_places(
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    zoom: int = Query(6, ge=1, le=20),
    type1: Optional[str] = None,
    type2: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))

    envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)

    # Ключевая правка: geography → geometry
    geom_as_geom = cast(
        models.CulturePlace.geom,
        Geometry(geometry_type="POINT", srid=4326),
    )

    stmt = select(models.CulturePlace).where(
        func.ST_Within(geom_as_geom, envelope)
    )
    if type1:
        stmt = stmt.where(models.CulturePlace.type1 == type1)
    if type2:
        stmt = stmt.where(models.CulturePlace.type2 == type2)
    if q:
        stmt = stmt.where(models.CulturePlace.name.ilike(f"%{q}%"))

    rows = db.execute(stmt).scalars().all()
    return [_to_out(r, db) for r in rows]


@app.get("/api/train_coords", response_model=List[schemas.TrainCoordOut])
def train_coords(db: Session = Depends(get_db)):
    rows = db.query(models.TrainCoord).all()
    out = []
    for r in rows:
        lon, lat = db.execute(
            select(func.ST_X(r.geom), func.ST_Y(r.geom))
        ).first()
        out.append(schemas.TrainCoordOut(
            id=r.id, name=r.name, lat=lat, lon=lon,
            search_radius_m=r.search_radius_m,
        ))
    return out


@app.get("/api/railway")
def railway(db: Session = Depends(get_db)):
    rows = db.query(models.Railway).all()
    result = []
    for r in rows:
        coords = db.execute(
            select(func.ST_AsGeoJSON(r.geom))
        ).scalar()
        import json
        result.append({"name": r.name, "geojson": json.loads(coords)})
    return result


@app.get("/api/culture_places/{place_id}", response_model=schemas.CulturePlaceOut)
def place_detail(place_id: int, db: Session = Depends(get_db)):
    r = db.get(models.CulturePlace, place_id)
    if not r:
        from fastapi import HTTPException
        raise HTTPException(404, "Not found")
    return _to_out(r, db)


# ---------- helpers ----------

def _to_out(r: models.CulturePlace, db: Session) -> schemas.CulturePlaceOut:
    geom_as_geom = cast(
        r.geom,
        Geometry(geometry_type="POINT", srid=4326),
    )
    lon, lat = db.execute(
        select(func.ST_X(geom_as_geom), func.ST_Y(geom_as_geom))
    ).first()
    return schemas.CulturePlaceOut(
        id=r.id, name=r.name, type1=r.type1.value, type2=r.type2.value,
        lat=lat, lon=lon,
        size_priority=r.size_priority,
        short_description=r.short_description,
        history=r.history, sources=r.sources or [],
        creation_date=r.creation_date, rarity=r.rarity,
        photo_url=r.photo_url,
        marker=schemas.MarkerStyle(**r.marker),
        train_coord_id=r.train_coord_id,
    )


# статика фронтенда
app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")