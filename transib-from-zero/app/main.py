from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import json

from .database import SessionLocal, engine, Base
from . import models, schemas
from .migrations import ensure_osm_enrichment_schema, ensure_taxonomy_schema
from .queries import (
    build_culture_places_count_query,
    build_culture_places_query,
    build_marker,
    build_result_count_headers,
    build_taxonomy_response,
)
from .taxonomy import load_taxonomy


with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
Base.metadata.create_all(bind=engine)
ensure_osm_enrichment_schema(engine)
ensure_taxonomy_schema(engine)

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
    response: Response,
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    zoom: Optional[int] = Query(None, ge=0, le=22),
    category: Optional[List[str]] = Query(None),
    subcategory: Optional[List[str]] = Query(None),
    object_class: Optional[List[str]] = Query(None),
    type1: Optional[List[str]] = Query(None),
    type2: Optional[List[str]] = Query(None),
    limit: int = Query(5000, ge=1),
    db: Session = Depends(get_db),
):
    taxonomy = load_taxonomy()
    query_args = {
        "bbox": bbox,
        "zoom": zoom,
        "category": category,
        "subcategory": subcategory,
        "object_class": object_class,
        "type1": type1,
        "type2": type2,
        "taxonomy": taxonomy,
    }
    try:
        count_query = build_culture_places_count_query(**query_args)
        place_query = build_culture_places_query(**query_args).limit(limit)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    total_count = db.execute(count_query).scalar_one()
    rows = db.execute(place_query).all()
    response.headers.update(
        build_result_count_headers(total_count, len(rows))
    )
    result = []
    for place, lon, lat, effective_description in rows:
        result.append(schemas.CulturePlaceOut(
            id=place.id,
            name=place.name,
            type1=place.type1.value,
            type2=place.type2.value,
            lat=lat,
            lon=lon,
            size_priority=place.size_priority,
            short_description=place.short_description,
            history=place.history,
            ai_summary=place.ai_summary,
            ai_summary_sources=place.ai_summary_sources or [],
            photo_url=place.photo_url,
            photo_attribution=place.photo_attribution,
            sources=place.sources or [],
            creation_date=place.creation_date,
            osm_type=place.osm_type,
            osm_id=place.osm_id,
            wikidata_id=place.wikidata_id,
            marker=schemas.MarkerStyle(**build_marker(
                taxonomy,
                place.subcategory,
                place.marker,
            )),
            category=place.category,
            subcategory=place.subcategory,
            object_class=place.object_class,
            description_source=place.description_source,
            effective_description=effective_description,
            effective_description_source=place.effective_description_source,
            origin=place.origin,
        ))
    return result


@app.get("/api/taxonomy")
def get_taxonomy():
    return build_taxonomy_response(load_taxonomy())


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