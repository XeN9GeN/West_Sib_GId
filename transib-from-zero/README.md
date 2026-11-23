# TransSib Culture

## Полный запуск на Windows

1. Запустите Docker Desktop.
2. Поместите `row_trailway_points.xml` в `data/`.
3. Из PowerShell выполните:

   ```powershell
   .\start_project.ps1
   ```

Перед изменениями существующей базы данных создайте резервную копию. Если
контейнер БД остановлен, сначала запустите его командой
`docker compose up -d db`. Для первой установки без существующей базы этот
шаг пропустите:

```powershell
docker compose exec db pg_dump -U transsib transsib > backup_before_taxonomy.sql
```

Скрипт собирает и запускает PostGIS/backend, ждёт готовности БД, затем
последовательно загружает точки железной дороги, импортирует OSM, отбирает
объекты в радиусе 2500 м, обогащает их через Wikidata, переносит подходящие
объекты в `culture_place` и запускает классификацию. Классификация обязательна:
до её завершения карта не показывает строки, для которых ещё не рассчитаны
расстояние и решение таксономии.

По умолчанию радиус берётся из `config/taxonomy.yaml` (2500 м). Ненулевое
значение `-RadiusMeters` временно переопределяет его для эксперимента:

```powershell
.\start_project.ps1 -RadiusMeters 3000
```

Чтобы использовать радиус из конфигурации, запускайте без параметра или
укажите `-RadiusMeters 0`. Значение радиуса не отменяет обязательное
ограничение показа объектов классификатором.

Если импорт уже выполнен, но классификатор ещё не запускался, сначала
просмотрите отчёт на заранее подготовленной копии базы данных `transsib_test`.
Передайте URL копии для команды dry-run:

```powershell
docker compose up -d --build backend
docker compose exec -e DATABASE_URL=postgresql://transsib:transsib@db:5432/transsib_test backend python -m scripts.classify_places --dry-run --report
```

После проверки отчёта и согласования решений запустите классификацию рабочей
базы:

```powershell
docker compose exec backend python -m scripts.classify_places
```

После импорта исследовательских материалов из `archive/` пересчитайте
эффективные описания:

```powershell
docker compose exec backend python -m scripts.classify_places --recompute-descriptions
```

Полный `start_project.ps1` запускает классификатор автоматически после импорта.
Перед его первым запуском должны быть проверены решения в режиме `--dry-run`
на копии базы данных и создана резервная копия. Не запускайте команду dry-run
без параметра `-e DATABASE_URL=...`: тогда она подключится к рабочей базе.

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
- `archive/` — архивные скрипты, тесты и материалы исследования Новосибирска.
- `data/` — внешний XML-файл исходных точек ЖД (не хранится в Git).
- `tests/` — тесты импорта и обогащения.
- `start_project.ps1` — полный локальный запуск и импорт данных.

Backend доступен по адресу `http://localhost:8000`, документация API —
`http://localhost:8000/docs`.
