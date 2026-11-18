import datetime as dt
import re
from pathlib import Path
from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from app.database import engine, SessionLocal, Base
import xml.etree.ElementTree as ET
from sqlalchemy import text
from app import models

TRAIN_COORDS = [
    ("Омск",              73.3242, 54.9885, 18000),
    ("Калачинск",         74.5833, 55.0500, 14000),
    ("Татарск",           75.9667, 55.2167, 14000),
    ("Барабинск",         78.3500, 55.3500, 16000),
    ("Каргат",            80.2833, 55.2000, 14000),
    ("Новосибирск",       82.9357, 55.0084, 20000),
]

PLACES = [
    # Омск и рядом (10)
    ("Омская крепость", "human", "architecture", 54.9915, 73.3715, "Историческая крепость XVIII века.", "Основана в 1716 году отрядом И. Бухгольца как острог.", ["https://omk-museum.ru", "https://ru.wikipedia.org/wiki/Омская_крепость"], dt.date(1716,1,1), 2.5),
    ("Омский драматический театр", "human", "theater", 54.9900, 73.3680, "Один из старейших театров Сибири.", "Основан в 1874 году.", ["https://omskdrama.ru"], dt.date(1874,1,1), 1.8),
    ("Успенский собор", "human", "temple", 54.9905, 73.3650, "Главный православный храм Омска.", "Построен в 1891–1898 гг.", ["https://omsk-eparhia.ru"], dt.date(1898,1,1), 1.5),
    ("Омский краеведческий музей", "human", "museum", 54.9840, 73.3720, "Крупнейший музей Омска.", "Основан в 1878 году.", ["https://omsk-museum.ru"], dt.date(1878,1,1), 1.6),
    ("Памятник Достоевскому", "human", "monument", 54.9880, 73.3700, "Памятник писателю, отбывавшему ссылку в Омске.", "Установлен в 2000 году.", ["https://omsk.ru"], dt.date(2000,1,1), 1.0),
    ("Омский зоопарк", "human", "museum", 54.9700, 73.3900, "Один из крупнейших зоопарков Сибири.", "Открыт в 1927 году.", ["https://omskzoo.ru"], dt.date(1927,1,1), 1.0),
    ("Набережная Тухачевского", "human", "architecture", 54.9930, 73.3760, "Главная набережная Омска.", "Реконструирована в 2010-х.", ["https://omsk.ru"], None, 0.9),
    ("Соборная мечеть Омска", "human", "temple", 54.9870, 73.3660, "Старейшая мечеть города.", "Построена в 1828 году.", ["https://omsk-muslim.ru"], dt.date(1828,1,1), 1.3),
    ("Птичья гавань", "nature", "lake", 54.9700, 73.3500, "Природный парк в черте города.", "Особо охраняемая территория с 1994 года.", ["https://oopt.aari.ru"], dt.date(1994,1,1), 1.4),
    ("Омский академический театр", "human", "theater", 54.9902, 73.3720, "Академический театр драмы.", "Основан в 1874 году.", ["https://omskdrama.ru"], dt.date(1874,1,1), 1.2),

    # Между Омском и Татарском (10)
    ("Калачинский краеведческий музей", "human", "museum", 55.0500, 74.5833, "Музей истории Калачинска.", "Открыт в 1975 году.", ["https://kalachinsk-museum.ru"], dt.date(1975,1,1), 0.9),
    ("Озеро Ик", "nature", "lake", 55.1000, 74.8000, "Крупное озеро в Омской области.", "Памятник природы.", ["https://oopt.aari.ru"], None, 1.6),
    ("Свято-Никольский храм Калачинска", "human", "temple", 55.0480, 74.5850, "Православный храм.", "Построен в 1900-х.", ["https://omsk-eparhia.ru"], dt.date(1905,1,1), 1.0),
    ("Памятник воинам-калачинцам", "human", "monument", 55.0510, 74.5800, "Мемориал ВОВ.", "Установлен в 1985 году.", ["https://kalachinsk.ru"], dt.date(1985,1,1), 0.9),
    ("Татарский краеведческий музей", "human", "museum", 55.2167, 75.9667, "Музей истории Татарска.", "Основан в 1986 году.", ["https://tatarsk-museum.ru"], dt.date(1986,1,1), 0.9),
    ("Озеро Чаны (западный берег)", "nature", "lake", 55.0000, 76.5000, "Крупнейшее озеро Западной Сибири.", "Памятник природы федерального значения.", ["https://oopt.aari.ru", "https://ru.wikipedia.org/wiki/Чаны_(озеро)"], None, 2.8),
    ("Татарский Свято-Успенский храм", "human", "temple", 55.2150, 75.9700, "Старинный храм.", "Построен в 1890-х.", ["https://omsk-eparhia.ru"], dt.date(1895,1,1), 1.0),
    ("Памятник Чапаеву в Татарске", "human", "monument", 55.2180, 75.9650, "Памятник герою Гражданской войны.", "Установлен в 1960-х.", ["https://tatarsk.ru"], dt.date(1965,1,1), 0.9),
    ("Барабинская степь", "nature", "reserve", 55.3000, 77.5000, "Типичная лесостепь Барабы.", "Заказник регионального значения.", ["https://oopt.aari.ru"], dt.date(1990,1,1), 1.5),
    ("Озеро Тандово", "nature", "lake", 55.3500, 77.8000, "Живописное озеро Барабы.", "Памятник природы.", ["https://oopt.aari.ru"], None, 1.2),

    # Барабинск (10)
    ("Барабинский краеведческий музей", "human", "museum", 55.3500, 78.3500, "Музей истории Барабинска.", "Основан в 1975 году.", ["https://barabinsk-museum.ru"], dt.date(1975,1,1), 0.9),
    ("Собор в честь Иверской иконы Божией Матери", "human", "temple", 55.3480, 78.3520, "Главный храм Барабинска.", "Построен в 1990-х.", ["https://nsk-eparhia.ru"], dt.date(1995,1,1), 1.0),
    ("Озеро Убинское", "nature", "lake", 55.5000, 79.5000, "Крупное озеро Новосибирской области.", "Памятник природы.", ["https://oopt.aari.ru"], None, 1.7),
    ("Барабинский вокзал", "human", "architecture", 55.3510, 78.3480, "Историческое здание вокзала.", "Построен в 1890-х.", ["https://rzd.ru"], dt.date(1896,1,1), 1.4),
    ("Памятник Ленину в Барабинске", "human", "monument", 55.3490, 78.3510, "Типовой советский памятник.", "Установлен в 1950-х.", ["https://barabinsk.ru"], dt.date(1955,1,1), 0.8),
    ("Озеро Сартлан", "nature", "lake", 55.0000, 78.5000, "Второе по величине озеро НСО.", "Памятник природы.", ["https://oopt.aari.ru"], None, 2.4),
    ("Барабинский парк культуры", "human", "architecture", 55.3470, 78.3550, "Городской парк.", "Заложен в 1930-х.", ["https://barabinsk.ru"], dt.date(1935,1,1), 0.8),
    ("Река Омь", "nature", "river", 55.4000, 78.0000, "Приток Иртыша.", "Длина 1091 км.", ["https://ru.wikipedia.org/wiki/Омь"], None, 1.3),
    ("Барабинский лесхоз", "nature", "forest", 55.3600, 78.3000, "Лесной массив вокруг города.", "Основан в 1930-х.", ["https://oopt.aari.ru"], dt.date(1936,1,1), 1.0),
    ("Мемориал Славы Барабинска", "human", "monument", 55.3500, 78.3450, "Мемориал ВОВ.", "Открыт в 1975 году.", ["https://barabinsk.ru"], dt.date(1975,1,1), 0.9),

    # Каргат и до Новосибирска (10)
    ("Каргатский краеведческий музей", "human", "museum", 55.2000, 80.2833, "Музей истории Каргата.", "Основан в 1980 году.", ["https://kargat-museum.ru"], dt.date(1980,1,1), 0.9),
    ("Озеро Карган", "nature", "lake", 55.2200, 80.3000, "Озеро рядом с Каргатом.", "Памятник природы.", ["https://oopt.aari.ru"], None, 1.1),
    ("Каргатский храм", "human", "temple", 55.1980, 80.2850, "Православный храм.", "Построен в 1900-х.", ["https://nsk-eparhia.ru"], dt.date(1902,1,1), 1.0),
    ("Памятник каргатцам-героям", "human", "monument", 55.2010, 80.2800, "Мемориал ВОВ.", "Установлен в 1980 году.", ["https://kargat.ru"], dt.date(1980,1,1), 0.8),
    ("Река Каргат", "nature", "river", 55.2000, 80.0000, "Приток Чулыма.", "Длина 387 км.", ["https://ru.wikipedia.org/wiki/Каргат_(река)"], None, 1.0),
    ("Новосибирский оперный театр", "human", "theater", 55.0300, 82.9200, "Крупнейший оперный театр России.", "Открыт в 1945 году.", ["https://novat.nsk.ru", "https://ru.wikipedia.org/wiki/Новосибирский_театр_оперы_и_балета"], dt.date(1945,5,12), 3.0),
    ("Новосибирский зоопарк", "human", "museum", 55.0500, 82.8800, "Один из крупнейших зоопарков мира.", "Основан в 1947 году.", ["https://zoo.nsk.ru"], dt.date(1947,1,1), 2.5),
    ("Часовня Святого Николая", "human", "temple", 55.0280, 82.9210, "Символ Новосибирска.", "Построена в 1915, восстановлена в 1993.", ["https://nsk-eparhia.ru"], dt.date(1915,1,1), 1.7),
    ("Новосибирский краеведческий музей", "human", "museum", 55.0290, 82.9180, "Один из старейших музеев города.", "Основан в 1920 году.", ["https://museum.nsk.ru"], dt.date(1920,1,1), 1.6),
    ("Ботанический сад СО РАН", "nature", "reserve", 54.9800, 83.0000, "Крупнейший ботанический сад Сибири.", "Основан в 1946 году.", ["https://csbg.nsc.ru"], dt.date(1946,1,1), 2.2),
]

Base.metadata.create_all(bind=engine)


def load_railway_points(db):
    file_path = Path(__file__).with_name("row_trailway_points.xml")

    lat_pattern = re.compile(r'LAT="([\d\.]+)"')
    lon_pattern = re.compile(r'LON="([\d\.]+)"')
    track_pattern = re.compile(r'TRACK="(\d+),[^"]+"')
    km_pattern = re.compile(r'KM="(\d+)"')
    measure_pattern = re.compile(r'M="([\d\.]+)"')

    with file_path.open(mode='r', encoding='utf-8') as f:
        batch = []
        batch_size = 10000
        point_count = 0

        for line_number, line in enumerate(f, start=1):
            lat_match = lat_pattern.search(line)
            lon_match = lon_pattern.search(line)

            if lat_match and lon_match:
                track_match = track_pattern.search(line)
                km_match = km_pattern.search(line)
                measure_match = measure_pattern.search(line)
                if not track_match or not km_match or not measure_match:
                    raise ValueError(
                        f"В XML не хватает данных пути для точки в строке {line_number}"
                    )

                lat = float(lat_match.group(1))
                lon = float(lon_match.group(1))
                batch.append(models.RawRailwayPoint(
                    geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
                    track_id=track_match.group(1),
                    km=int(km_match.group(1)),
                    measure=float(measure_match.group(1)),
                ))
                point_count += 1

            if len(batch) >= batch_size:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []

        if batch:
            db.bulk_save_objects(batch)
            db.commit()

    print(f"Точки ЖД успешно загружены из XML-файла: {point_count}.")


def create_railway_line_from_points(db):
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_raw_railway_geom ON raw_railway_points USING GIST (geom);"))
    db.commit()

    query = text("""
        WITH track_lines AS (
            SELECT track_id, ST_MakeLine(geom ORDER BY km, measure) AS geom
            FROM raw_railway_points
            GROUP BY track_id
        )
        SELECT ST_Multi(ST_Collect(geom))
        FROM track_lines;
    """)
    result = db.execute(query).scalar()

    if result:
        db.query(models.Railway).delete()
        db.add(models.Railway(name="Транссиб (реальный маршрут)", geom=result))
        db.commit()
        print("Пути ЖД успешно сгенерированы и сохранены для карты.")
    else:
        print("Не удалось сгенерировать линию: нет точек в БД.")


def create_railway_detail_levels(db):
    # Geometry is stored in EPSG:4326, so simplification tolerances are in degrees.
    levels = [
        (4, 0.06),
        (6, 0.015),
        (8, 0.004),
        (10, 0.001),
        (12, 0.00025),
        (14, 0.00006),
        (16, 0.000015),
        (18, 0.000004),
    ]

    db.query(models.RailwayDetail).delete()
    db.flush()

    for zoom_level, tolerance in levels:
        db.execute(
            text("""
                INSERT INTO railway_detail (zoom_level, geom)
                SELECT :zoom_level,
                       ST_Simplify(geom, :tolerance)
                FROM railway
                ORDER BY id
                LIMIT 1
            """),
            {"zoom_level": zoom_level, "tolerance": tolerance},
        )

    db.commit()
    print("Уровни детализации ЖД линии успешно сохранены.")



def main():
    db = SessionLocal()
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        db.commit()

        db.execute(text("""
            ALTER TABLE raw_railway_points
                ADD COLUMN IF NOT EXISTS track_id VARCHAR(32),
                ADD COLUMN IF NOT EXISTS km INTEGER,
                ADD COLUMN IF NOT EXISTS measure DOUBLE PRECISION
        """))
        db.execute(text("""
            ALTER TABLE railway
                ALTER COLUMN geom TYPE geometry(MultiLineString, 4326)
                USING ST_Multi(geom)
        """))
        db.execute(text("""
            ALTER TABLE railway_detail
                ALTER COLUMN geom TYPE geometry(MultiLineString, 4326)
                USING ST_Multi(geom)
        """))
        db.commit()

        if db.query(models.TrainCoord).count() == 0:
            for name, lon, lat, radius in TRAIN_COORDS:
                db.add(models.TrainCoord(
                    name=name, 
                    geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
                    search_radius_m=radius
                ))
            db.commit()

        if db.query(models.CulturePlace).count() == 0:
            for (name, t1, t2, lat, lon, short, hist, src, date, prio) in PLACES:
                place = models.CulturePlace(
                    name=name, type1=models.Type1(t1), type2=models.Type2(t2),
                    short_description=short, history=hist, sources=src or [],
                    creation_date=date, size_priority=prio,
                    geom=WKTElement(f"POINT({lon} {lat})", srid=4326)
                )
                db.add(place)
            db.commit()
            print("База успешно заполнена 50 местами!")

        points_need_reload = db.query(models.RawRailwayPoint).filter(
            (models.RawRailwayPoint.track_id.is_(None))
            | (models.RawRailwayPoint.km.is_(None))
            | (models.RawRailwayPoint.measure.is_(None))
        ).first() is not None
        if db.query(models.RawRailwayPoint).count() == 0 or points_need_reload:
            file_path = Path(__file__).with_name("row_trailway_points.xml")
            if not file_path.is_file():
                raise FileNotFoundError(f"Файл {file_path} не найден")
            db.query(models.RawRailwayPoint).delete(synchronize_session=False)
            db.commit()
            load_railway_points(db)
            points_need_reload = True

        if points_need_reload or db.query(models.Railway).count() == 0:
            create_railway_line_from_points(db)

        if points_need_reload or db.query(models.RailwayDetail).count() == 0:
            create_railway_detail_levels(db)

    finally:
        db.close()




if __name__ == "__main__":
    main()