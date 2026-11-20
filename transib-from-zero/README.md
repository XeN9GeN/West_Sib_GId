# TransSib Culture

## Полный запуск на Windows

1. Запустите Docker Desktop.
2. Поместите `row_trailway_points.xml` в `data/`.
3. Из PowerShell выполните:

   ```powershell
   .\start_project.ps1
   ```

Скрипт собирает и запускает PostGIS/backend, ждёт готовности БД, затем
последовательно загружает точки железной дороги, импортирует OSM, отбирает
объекты в радиусе 5 км, обогащает их через Wikidata и переносит в
`culture_place`. Радиус можно изменить:

```powershell
.\start_project.ps1 -RadiusMeters 3000
```

Для повторной загрузки больших наборов OSM/Wikidata учитывайте лимиты внешних
сервисов. OSM импортируется локально из выгрузок Geofabrik для Уральского и
Сибирского федеральных округов (около 942 МБ суммарно). PBF-файлы сохраняются
в `data/osm/` и используются повторно; после сетевого обрыва загрузчик
автоматически переподключается с последнего сохранённого байта, а при
исчерпании повторов загрузку можно продолжить перезапуском.
Для фильтрации в Docker устанавливается `osmium-tool`. Wikidata/Commons
запрашиваются не чаще раза в секунду; на HTTP 429 загрузчик учитывает
`Retry-After` и повторяет запрос с задержкой. Скрипт не удаляет Docker volume
с базой данных.

Для объектов с тегом OSM `wikipedia=язык:Название` загрузчик получает краткое
вступление статьи через MediaWiki API, сохраняет его как запасное описание и
оставляет ссылку на статью в источниках для атрибуции. Условия повторного
использования определяются лицензией конкретной статьи. Чтобы выполнить этот
этап на уже загруженных объектах без поиска Wikidata по координатам:

```powershell
docker compose up -d --build backend
docker compose exec backend python -m scripts.enrich_osm --wikipedia-only
```

Для WikiVoyage используются только прямые ссылки из OSM-тега `wikivoyage` или
из sitelink Wikidata самого объекта; ближайшая статья города не принимается за
описание достопримечательности. Повторить только этот этап на уже загруженных
данных можно так:

```powershell
docker compose up -d --build backend
docker compose exec backend python -m scripts.enrich_osm --wikivoyage-only
```

Данные © OpenStreetMap contributors, лицензия ODbL:
https://www.openstreetmap.org/copyright.

## Структура

- `app/` — FastAPI, модели, схемы и миграции.
- `frontend/` — веб-карта.
- `scripts/` — импорт железной дороги, OSM и Wikidata.
- `data/` — внешний XML-файл исходных точек ЖД (не хранится в Git).
- `tests/` — тесты импорта и обогащения.
- `start_project.ps1` — полный локальный запуск и импорт данных.

Backend доступен по адресу `http://localhost:8000`, документация API —
`http://localhost:8000/docs`.
