param(
    [string]$ComposeFile = "docker-compose.test.yml",
    [string]$DataDir = "/app/data/import_1c"
)

Write-Host "Запуск сервисов (PostgreSQL, Redis)..."
docker compose -f $ComposeFile up -d --wait --remove-orphans

Write-Host "Применение миграций Django..."
docker compose -f $ComposeFile run --rm backend python manage.py migrate

Write-Host "Запуск полного импорта каталога из 1С..."
docker compose -f $ComposeFile run --rm backend python manage.py import_catalog_from_1c --data-dir $DataDir

Write-Host "Импорт завершён."
