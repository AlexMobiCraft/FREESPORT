# Скрипт с полезными командами для управления средой разработки FREESPORT Platform
# Использование: .\scripts\dev\dev-commands.ps1 [command]

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "logs", "status", "migrate", "shell", "test", "clean")]
    [string]$Command
)

# Поддержка параметров с дефисом для совместимости
if ($args.Count -gt 0 -and -not $Command) {
    $Command = $args[0].TrimStart('-')
}

$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot

function Show-Usage {
    Write-Host "Использование: .\scripts\dev\dev-commands.ps1 [command]" -ForegroundColor Cyan
    Write-Host
    Write-Host "Доступные команды:" -ForegroundColor Yellow
    Write-Host "  start    - Запустить все сервисы разработки" -ForegroundColor White
    Write-Host "  stop     - Остановить все сервисы разработки" -ForegroundColor White
    Write-Host "  restart  - Перезапустить все сервисы разработки" -ForegroundColor White
    Write-Host "  logs     - Показать логи всех сервисов" -ForegroundColor White
    Write-Host "  status   - Показать статус контейнеров" -ForegroundColor White
    Write-Host "  migrate  - Выполнить миграции базы данных" -ForegroundColor White
    Write-Host "  shell    - Открыть Django shell" -ForegroundColor White
    Write-Host "  test     - Запустить тесты в интерактивном режиме" -ForegroundColor White
    Write-Host "  clean    - Очистить Docker образы и контейнеры" -ForegroundColor White
}

function Invoke-Start {
    Write-Host "Запуск всех сервисов разработки..." -ForegroundColor Yellow
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Сервисы успешно запущены" -ForegroundColor Green
        Write-Host "Backend: http://localhost:8001/api/v1" -ForegroundColor Cyan
        Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
    }
    else {
        Write-Host "✗ Ошибка при запуске сервисов" -ForegroundColor Red
    }
}

function Invoke-Stop {
    Write-Host "Остановка всех сервисов разработки..." -ForegroundColor Yellow
    docker-compose down
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Сервисы успешно остановлены" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Ошибка при остановке сервисов" -ForegroundColor Red
    }
}

function Invoke-Restart {
    Write-Host "Перезапуск всех сервисов разработки..." -ForegroundColor Yellow
    docker-compose restart
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Сервисы успешно перезапущены" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Ошибка при перезапуске сервисов" -ForegroundColor Red
    }
}

function Invoke-Logs {
    Write-Host "Показ логов всех сервисов (Ctrl+C для выхода)..." -ForegroundColor Yellow
    docker-compose logs -f
}

function Invoke-Status {
    Write-Host "Статус контейнеров:" -ForegroundColor Yellow
    docker-compose ps
}

function Invoke-Migrate {
    Write-Host "Выполнение миграций базы данных..." -ForegroundColor Yellow
    docker-compose exec backend python manage.py migrate
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Миграции успешно выполнены" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Ошибка при выполнении миграций" -ForegroundColor Red
    }
}

function Invoke-Shell {
    Write-Host "Открытие Django shell..." -ForegroundColor Yellow
    docker-compose exec backend python manage.py shell
}

function Invoke-Test {
    Write-Host "Запуск тестов в интерактивном режиме..." -ForegroundColor Yellow
    & "$PSScriptRoot\..\tests\run-tests-interactive.ps1"
}

function Invoke-Clean {
    Write-Host "Очистка Docker образов и контейнеров..." -ForegroundColor Yellow
    Write-Host "Это удалит все контейнеры, образы и тома проекта. Продолжить? (y/n)" -ForegroundColor Red
    $answer = Read-Host
    if ($answer.ToLower() -eq "y") {
        Write-Host "Остановка и удаление контейнеров..." -ForegroundColor Cyan
        docker-compose down -v --remove-orphans
        
        Write-Host "Остановка и удаление тестовых контейнеров..." -ForegroundColor Cyan
        docker-compose -f docker-compose.test.yml down -v --remove-orphans
        
        Write-Host "Удаление неиспользуемых образов..." -ForegroundColor Cyan
        docker image prune -f
        
        Write-Host "Удаление неиспользуемых томов..." -ForegroundColor Cyan
        docker volume prune -f
        
        Write-Host "✓ Очистка завершена" -ForegroundColor Green
    }
    else {
        Write-Host "Отменено" -ForegroundColor Yellow
    }
}

# Основная логика
if (-not $Command) {
    Show-Usage
    exit 0
}

switch ($Command.ToLower()) {
    "start" { Invoke-Start }
    "stop" { Invoke-Stop }
    "restart" { Invoke-Restart }
    "logs" { Invoke-Logs }
    "status" { Invoke-Status }
    "migrate" { Invoke-Migrate }
    "shell" { Invoke-Shell }
    "test" { Invoke-Test }
    "clean" { Invoke-Clean }
    default {
        Write-Host "Неизвестная команда: $Command" -ForegroundColor Red
        Show-Usage
        exit 1
    }
}