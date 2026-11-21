from typing import List, Optional
from fastapi import FastAPI, Depends, Query
from sqlalchemy import func, select, cast, text
from sqlalchemy.orm import Session
from geoalchemy2 import Geometry
from fastapi.middleware.cors import CORSMiddleware
import json

from .database import SessionLocal, engine, Base
from . import models, schemas
from .migrations import ensure_osm_enrichment_schema


with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
Base.metadata.create_all(bind=engine)
ensure_osm_enrichment_schema(engine)

app = FastAPI(title="TransSib Culture API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/culture_places", response_model=List[schemas.CulturePlaceOut])
def culture_places( 
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    type1: Optional[List[str]] = Query(None, description="Фильтр по типу 1 (human, nature)"),
    type2: Optional[List[str]] = Query(None, description="Фильтр по типу 2 "), db: Session = Depends(get_db),):
    result = []
    
    geom_as_geom = cast(models.CulturePlace.geom, Geometry(geometry_type="POINT", srid=4326))
    stmt = select(models.CulturePlace)

    if bbox:
        min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        stmt = stmt.where(func.ST_Within(geom_as_geom, envelope))

    rows = db.execute(stmt).scalars().all()

    for r in rows:
        lon, lat = db.execute(
            select(func.ST_X(geom_as_geom), func.ST_Y(geom_as_geom)).where(models.CulturePlace.id == r.id)
        ).first()

        result.append(schemas.CulturePlaceOut(
            id=r.id, name=r.name, type1=r.type1.value, type2=r.type2.value,
            lat=lat, lon=lon, size_priority=r.size_priority,
            short_description=r.short_description, history=r.history,
            ai_summary=r.ai_summary,
            ai_summary_sources=r.ai_summary_sources or [],
            photo_url=r.photo_url, photo_attribution=r.photo_attribution,
            sources=r.sources or [], creation_date=r.creation_date,
            osm_type=r.osm_type, osm_id=r.osm_id, wikidata_id=r.wikidata_id,
            marker=schemas.MarkerStyle(**r.marker)
        ))
        
    return result

@app.get("/api/railway")
def get_railway(zoom: int = Query(6, ge=0, le=22), db: Session = Depends(get_db)):
    detail_level = max(4, min(18, (zoom // 2) * 2))
    stmt = select(
        models.RailwayDetail.zoom_level,
        func.ST_AsGeoJSON(models.RailwayDetail.geom),
    ).where(models.RailwayDetail.zoom_level == detail_level)
    row = db.execute(stmt).first()

    if row and row[1]:
        return {"geometry": json.loads(row[1]), "detail_level": row[0]}

    stmt = select(func.ST_AsGeoJSON(models.Railway.geom)).order_by(models.Railway.id).limit(1)
    row = db.execute(stmt).first()

    if row and row[0]:
        return {"geometry": json.loads(row[0]), "detail_level": None}
    return {"geometry": None, "detail_level": None}


from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")#"/"- index.hlml, "app.js" - app.js ; отдаёт файлы из директории