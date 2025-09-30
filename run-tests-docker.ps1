# Скрипт для запуска тестов через Docker Compose
# FREESPORT Platform - Test Runner

Write-Host "=== FREESPORT Test Runner ===" -ForegroundColor Cyan
Write-Host ""

# Проверка Docker
Write-Host "Проверка Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✓ Docker запущен" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker не запущен. Запустите Docker Desktop и повторите попытку." -ForegroundColor Red
    exit 1
}

# Остановка и очистка предыдущих контейнеров
Write-Host ""
Write-Host "Очистка предыдущих тестовых контейнеров..." -ForegroundColor Yellow
docker-compose -f docker-compose.test.yml down -v 2>$null

# Запуск тестов
Write-Host ""
Write-Host "Запуск тестов..." -ForegroundColor Yellow
Write-Host "Это может занять несколько минут при первом запуске (сборка образа)" -ForegroundColor Gray
Write-Host ""

docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

$exitCode = $LASTEXITCODE

# Очистка после тестов
Write-Host ""
Write-Host "Очистка тестовых контейнеров..." -ForegroundColor Yellow
docker-compose -f docker-compose.test.yml down -v

# Результат
Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "=== ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО ===" -ForegroundColor Green
} else {
    Write-Host "=== ТЕСТЫ ЗАВЕРШИЛИСЬ С ОШИБКАМИ ===" -ForegroundColor Red
}

exit $exitCode
