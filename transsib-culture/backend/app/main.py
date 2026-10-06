from typing import List, Optional
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_MakeEnvelope, ST_Within, ST_DWithin, ST_Distance

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

    # порог size_priority в зависимости от зума (требование 4)
    threshold = {
        0: 3.0, 1: 3.0, 2: 3.0, 3: 2.5, 4: 2.5, 5: 2.0,
        6: 2.0, 7: 1.5, 8: 1.5, 9: 1.0, 10: 1.0, 11: 0.8,
    }.get(zoom, 0.5)

    stmt = select(models.CulturePlace).where(
        models.CulturePlace.size_priority >= threshold,
        ST_Within(
            models.CulturePlace.geom,
            ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326),
        ),
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
    lon, lat = db.execute(
        select(func.ST_X(r.geom), func.ST_Y(r.geom))
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