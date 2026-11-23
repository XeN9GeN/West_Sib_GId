param(
    [ValidateRange(0, 100000)]
    [int]$RadiusMeters = 0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RailwayPointsFile = Join-Path $ProjectRoot "data\row_trailway_points.xml"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI не найден. Установите Docker Desktop и повторите запуск."
}

if (-not (Test-Path -LiteralPath $RailwayPointsFile -PathType Leaf)) {
    throw "Не найден файл точек ЖД: $RailwayPointsFile. Поместите row_trailway_points.xml в папку data."
}

Push-Location $ProjectRoot
try {
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Engine недоступен. Запустите Docker Desktop и повторите попытку."
    }

    Write-Host "1/8: сборка и запуск PostGIS и backend..."
    & docker compose up --build --detach
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось запустить docker compose."
    }

    Write-Host "2/8: ожидание готовности PostGIS..."
    $databaseReady = $false
    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        & docker compose exec -T db pg_isready -U transsib -d transsib *> $null
        if ($LASTEXITCODE -eq 0) {
            $databaseReady = $true
            break
        }
        Start-Sleep -Seconds 3
    }
    if (-not $databaseReady) {
        throw "PostGIS не стал готов за 3 минуты. Проверьте: docker compose logs db"
    }

    Write-Host "3/8: импорт точек ЖД и подготовка базовых данных..."
    & docker compose exec -T backend python -m scripts.init_data
    if ($LASTEXITCODE -ne 0) {
        throw "Импорт точек ЖД завершился ошибкой."
    }

    Write-Host "4/8: загрузка региональных OSM-выгрузок и импорт объектов..."
    & docker compose exec -T backend python -m scripts.import_osm_pbf
    if ($LASTEXITCODE -ne 0) {
        throw "Импорт OSM завершился ошибкой."
    }

    Write-Host "5/8: отбор объектов рядом с железной дорогой..."
    $selectionArgs = @("--select-near-railway")
    if ($RadiusMeters -ne 0) {
        $selectionArgs += @("--radius-m", "$RadiusMeters")
    }
    & docker compose exec -T backend python -m scripts.import_osm @selectionArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Пространственный отбор объектов завершился ошибкой."
    }

    Write-Host "6/8: обогащение Wikidata и перенос в culture_place..."
    & docker compose exec -T backend python -m scripts.enrich_osm
    if ($LASTEXITCODE -ne 0) {
        throw "Обогащение или перенос данных завершились ошибкой."
    }

    Write-Host "7/8: классификация объектов и проверка расстояния..."
    & docker compose exec -T backend python -m scripts.classify_places
    if ($LASTEXITCODE -ne 0) {
        throw "Классификация объектов завершилась ошибкой."
    }

    Write-Host "8/8: проверка доступности API..."
    $apiReady = $false
    $deadline = (Get-Date).AddMinutes(2)
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-WebRequest -UseBasicParsing `
                -Uri "http://localhost:8000/openapi.json" -TimeoutSec 5
            $apiReady = $true
            break
        }
        catch {
            Start-Sleep -Seconds 3
        }
    }
    if (-not $apiReady) {
        throw "API не ответил на http://localhost:8000. Проверьте: docker compose logs backend"
    }

    Write-Host "Готово. Карта: http://localhost:8000"
}
finally {
    Pop-Location
}
