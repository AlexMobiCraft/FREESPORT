# PowerShell скрипт для запуска integration тестов с правильными переменными окружения
# Использование: .\run_integration_tests.ps1

Write-Host "🧪 Запуск integration тестов для Story 3.1.3..." -ForegroundColor Cyan

# Устанавливаем переменные окружения для тестов
$env:DB_NAME = "freesport_test"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "postgres"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DJANGO_SETTINGS_MODULE = "freesport.settings.test"

# Проверяем что PostgreSQL запущен
Write-Host "📊 Проверка подключения к PostgreSQL..." -ForegroundColor Yellow
$pgCheck = docker ps --filter "name=freesport-db" --filter "status=running" --format "{{.Names}}"

if (-not $pgCheck) {
    Write-Host "⚠️  PostgreSQL не запущен. Запускаем..." -ForegroundColor Yellow
    docker-compose up -d db
    Start-Sleep -Seconds 3
    Write-Host "✅ PostgreSQL запущен" -ForegroundColor Green
} else {
    Write-Host "✅ PostgreSQL уже запущен" -ForegroundColor Green
}

# Активируем venv если он существует
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    Write-Host "📦 Активация venv..." -ForegroundColor Yellow
    & "..\venv\Scripts\Activate.ps1"
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Активация venv..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

# Запускаем тесты
Write-Host "`n🚀 Запуск тестов..." -ForegroundColor Cyan
python -m pytest tests/integration/test_real_catalog_import.py -v --tb=short

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "`n✅ Тесты завершены успешно!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Тесты завершились с ошибками (код: $exitCode)" -ForegroundColor Red
}

exit $exitCode
