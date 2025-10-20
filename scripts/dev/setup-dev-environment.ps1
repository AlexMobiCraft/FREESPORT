# Скрипт первоначальной настройки Docker-среды разработки FREESPORT Platform
# Создает и запускает все необходимые контейнеры для разработки

Write-Host "=== FREESPORT Dev Environment Setup ===" -ForegroundColor Cyan
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

# Создание необходимых директорий
Write-Host "Создание необходимых директорий..." -ForegroundColor Yellow
$directories = @(
    "data",
    "data/import_1c",
    "logs",
    "docker/nginx/conf.d"
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

# Проверка наличия файлов конфигурации
Write-Host "Проверка файлов конфигурации..." -ForegroundColor Yellow

if (-not (Test-Path -Path "docker/nginx/nginx.conf")) {
    Write-Host "  ⚠ Внимание: docker/nginx/nginx.conf не найден" -ForegroundColor Yellow
    Write-Host "    Вам может потребоваться создать конфигурацию Nginx" -ForegroundColor Yellow
}

if (-not (Test-Path -Path "docker/init-db.sql")) {
    Write-Host "  ⚠ Внимание: docker/init-db.sql не найден" -ForegroundColor Yellow
    Write-Host "    Вам может потребоваться создать скрипт инициализации БД" -ForegroundColor Yellow
}

Write-Host

# Создание .env файла для локальной разработки, если он не существует
$envFilePath = ".env"
if (-not (Test-Path -Path $envFilePath)) {
    Write-Host "Создание файла .env для локальной разработки..." -ForegroundColor Yellow
    $envContent = @"
# Django настройки
DJANGO_SETTINGS_MODULE=freesport.settings.development
SECRET_KEY=development-secret-key-change-in-production
DEBUG=1

# База данных
DB_NAME=freesport
DB_USER=postgres
DB_PASSWORD=password123
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://:redis123@redis:6379/0

# Дополнительные настройки
PYTHONUTF8=1
PYTHONUNBUFFERED=1
"@
    $envContent | Out-File -FilePath $envFilePath -Encoding UTF8
    Write-Host "  ✓ Файл .env создан" -ForegroundColor Green
}
else {
    Write-Host "  ✓ Файл .env уже существует" -ForegroundColor Gray
}

Write-Host

# Сборка и запуск контейнеров
Write-Host "Сборка и запуск Docker-контейнеров..." -ForegroundColor Yellow
Write-Host "Это может занять несколько минут при первом запуске." -ForegroundColor Gray
Write-Host

try {
    # Сборка образов
    Write-Host "Сборка Docker-образов..." -ForegroundColor Cyan
    docker-compose build
    if ($LASTEXITCODE -ne 0) {
        throw "Ошибка при сборке Docker-образов"
    }
    Write-Host "✓ Образы успешно собраны" -ForegroundColor Green
    Write-Host

    # Запуск контейнеров в фоновом режиме
    Write-Host "Запуск контейнеров..." -ForegroundColor Cyan
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) {
        throw "Ошибка при запуске контейнеров"
    }
    Write-Host "✓ Контейнеры успешно запущены" -ForegroundColor Green
    Write-Host

    # Ожидание запуска сервисов
    Write-Host "Ожидание запуска сервисов..." -ForegroundColor Cyan
    Start-Sleep -Seconds 10

    # Проверка статуса контейнеров
    Write-Host "Проверка статуса контейнеров:" -ForegroundColor Cyan
    docker-compose ps
    Write-Host

    # Выполнение миграций базы данных
    Write-Host "Выполнение миграций базы данных..." -ForegroundColor Cyan
    docker-compose exec backend python manage.py migrate
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Предупреждение: Возникли проблемы при выполнении миграций" -ForegroundColor Yellow
    }
    else {
        Write-Host "✓ Миграции успешно выполнены" -ForegroundColor Green
    }
    Write-Host

    # Создание суперпользователя (опционально)
    $createSuperuser = Read-Host "Создать суперпользователя Django? (y/n)"
    if ($createSuperuser.ToLower() -eq "y") {
        Write-Host "Создание суперпользователя..." -ForegroundColor Cyan
        docker-compose exec backend python manage.py createsuperuser
    }

    Write-Host
    Write-Host "=== Среда разработки успешно настроена! ===" -ForegroundColor Green
    Write-Host
    Write-Host "Доступные сервисы:" -ForegroundColor Cyan
    Write-Host "  • Backend API: http://localhost:8001/api/v1" -ForegroundColor White
    Write-Host "  • Frontend: http://localhost:3000" -ForegroundColor White
    Write-Host "  • Nginx: http://localhost" -ForegroundColor White
    Write-Host "  • PostgreSQL: localhost:5432" -ForegroundColor White
    Write-Host "  • Redis: localhost:6379" -ForegroundColor White
    Write-Host
    Write-Host "Полезные команды:" -ForegroundColor Cyan
    Write-Host "  • Просмотр логов: docker-compose logs -f [service]" -ForegroundColor White
    Write-Host "  • Остановка: docker-compose down" -ForegroundColor White
    Write-Host "  • Перезапуск: docker-compose restart [service]" -ForegroundColor White
    Write-Host "  • Выполнение команд в backend: docker-compose exec backend [command]" -ForegroundColor White
    Write-Host
}
catch {
    Write-Host "✗ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host
    Write-Host "Проверьте:" -ForegroundColor Yellow
    Write-Host "  • Docker запущен и доступен" -ForegroundColor White
    Write-Host "  • Файлы docker-compose.yml и Dockerfile существуют" -ForegroundColor White
    Write-Host "  • Порты 5432, 6379, 8001, 3000, 80 не заняты" -ForegroundColor White
    exit 1
}