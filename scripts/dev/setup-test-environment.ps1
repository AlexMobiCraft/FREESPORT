# Скрипт первоначальной настройки Docker-среды для тестирования FREESPORT Platform
# Создает и подготавливает все необходимые контейнеры для запуска тестов

Write-Host "=== FREESPORT Test Environment Setup ===" -ForegroundColor Cyan
Write-Host

# Проверка доступности Docker
try {
    docker info > $null 2>&1
    Write-Host "✓ Docker доступен" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker недоступен. Убедитесь, что Docker запущен." -ForegroundColor Red
    exit 1
}

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка наличия файла docker-compose.test.yml
if (-not (Test-Path -Path "docker-compose.test.yml")) {
    Write-Host "✗ Файл docker-compose.test.yml не найден в корне проекта" -ForegroundColor Red
    exit 1
}

# Создание необходимых директорий для тестов
Write-Host "Создание необходимых директорий для тестов..." -ForegroundColor Yellow
$directories = @(
    "data",
    "data/import_1c",
    "logs/test-runs"
)

foreach ($dir in $directories) {
    if (-not (Test-Path -Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✓ Создана директория: $dir" -ForegroundColor Green
    }
    else {
        Write-Host "  ✓ Директория уже существует: $dir" -ForegroundColor Gray
    }
}

Write-Host

# Установка переменной окружения для пути к проекту (используется в docker-compose.test.yml)
$env:FREESPORT_PROJECT_ROOT = $projectRoot
Write-Host "Установлена переменная окружения FREESPORT_PROJECT_ROOT = $projectRoot" -ForegroundColor Green
Write-Host

# Сборка и запуск тестовых контейнеров
Write-Host "Сборка и запуск тестовых Docker-контейнеров..." -ForegroundColor Yellow
Write-Host "Это может занять несколько минут при первом запуске." -ForegroundColor Gray
Write-Host

try {
    # Сборка тестовых образов
    Write-Host "Сборка тестовых Docker-образов..." -ForegroundColor Cyan
    docker-compose -f docker-compose.test.yml build
    if ($LASTEXITCODE -ne 0) {
        throw "Ошибка при сборке тестовых Docker-образов"
    }
    Write-Host "✓ Тестовые образы успешно собраны" -ForegroundColor Green
    Write-Host

    # Запуск тестовых сервисов в фоновом режиме
    Write-Host "Запуск тестовых сервисов (db, redis)..." -ForegroundColor Cyan
    docker-compose -f docker-compose.test.yml up -d db redis
    if ($LASTEXITCODE -ne 0) {
        throw "Ошибка при запуске тестовых сервисов"
    }
    Write-Host "✓ Тестовые сервисы запущены" -ForegroundColor Green
    Write-Host

    # Ожидание запуска сервисов
    Write-Host "Ожидание запуска тестовых сервисов..." -ForegroundColor Cyan
    Start-Sleep -Seconds 15

    # Проверка статуса контейнеров
    Write-Host "Проверка статуса тестовых контейнеров:" -ForegroundColor Cyan
    docker-compose -f docker-compose.test.yml ps
    Write-Host

    # Проверка доступности тестовой базы данных
    Write-Host "Проверка доступности тестовой базы данных..." -ForegroundColor Cyan
    $dbCheck = docker-compose -f docker-compose.test.yml exec -T db pg_isready -U postgres -d freesport_test
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Тестовая база данных доступна" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ Тестовая база данных еще не готова" -ForegroundColor Yellow
    }

    # Проверка доступности Redis
    Write-Host "Проверка доступности Redis..." -ForegroundColor Cyan
    $redisCheck = docker-compose -f docker-compose.test.yml exec -T redis redis-cli -a redis123 ping
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Redis доступен" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ Redis еще не готов" -ForegroundColor Yellow
    }

    Write-Host
    Write-Host "=== Тестовая среда успешно настроена! ===" -ForegroundColor Green
    Write-Host
    Write-Host "Теперь вы можете запускать тесты с помощью:" -ForegroundColor Cyan
    Write-Host "  • Интерактивный запуск: .\scripts\..\tests\run-tests-interactive.ps1" -ForegroundColor White
    Write-Host "  • Прямой запуск: .\scripts\..\tests\run-tests-docker-local.ps1" -ForegroundColor White
    Write-Host
    Write-Host "Полезные команды для тестовой среды:" -ForegroundColor Cyan
    Write-Host "  • Просмотр логов: docker-compose -f docker-compose.test.yml logs -f [service]" -ForegroundColor White
    Write-Host "  • Остановка тестовой среды: docker-compose -f docker-compose.test.yml down" -ForegroundColor White
    Write-Host "  • Перезапуск сервисов: docker-compose -f docker-compose.test.yml restart [service]" -ForegroundColor White
    Write-Host "  • Выполнение команд в тестовом backend: docker-compose -f docker-compose.test.yml exec backend [command]" -ForegroundColor White
    Write-Host
}
catch {
    Write-Host "✗ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host
    Write-Host "Проверьте:" -ForegroundColor Yellow
    Write-Host "  • Docker запущен и доступен" -ForegroundColor White
    Write-Host "  • Файл docker-compose.test.yml существует" -ForegroundColor White
    Write-Host "  • Порты 5433, 6380 не заняты (для тестовой среды)" -ForegroundColor White
    exit 1
}