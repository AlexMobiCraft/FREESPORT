# Основной скрипт миграции на унифицированное виртуальное окружение
# Выполняет полный переход от некорректного venv к стандартной структуре

param(
    [switch]$SkipBackup,
    [switch]$SkipDocker,
    [switch]$Force
)

Write-Host "=== Миграция на унифицированное виртуальное окружение ===" -ForegroundColor Cyan
Write-Host

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка предварительных условий
Write-Host "Проверка предварительных условий..." -ForegroundColor Yellow

# Проверка Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python недоступен" -ForegroundColor Red
    exit 1
}

# Проверка Docker (если не пропущен)
if (-not $SkipDocker) {
    try {
        docker info > $null 2>&1
        Write-Host "  ✓ Docker доступен" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Docker недоступен (используйте -SkipDocker для пропуска)" -ForegroundColor Red
        exit 1
    }
}

# Проверка структуры проекта
if (-not (Test-Path -Path "backend")) {
    Write-Host "  ✗ Директория backend не найдена" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -Path "backend/requirements.txt")) {
    Write-Host "  ✗ backend/requirements.txt не найден" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Предварительные условия выполнены" -ForegroundColor Green
Write-Host

# Этап 1: Резервное копирование
if (-not $SkipBackup) {
    Write-Host "=== Этап 1: Резервное копирование ===" -ForegroundColor Cyan
    & $PSScriptRoot/backup-current-env.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Резервное копирование завершилось с ошибкой" -ForegroundColor Red
        if (-not $Force) {
            exit 1
        }
        Write-Host "⚠ Продолжение принудительно (-Force)" -ForegroundColor Yellow
    }
    Write-Host "✓ Этап 1 завершен" -ForegroundColor Green
    Write-Host
} else {
    Write-Host "⚠ Этап 1 пропущен (-SkipBackup)" -ForegroundColor Yellow
    Write-Host
}

# Этап 2: Создание нового виртуального окружения
Write-Host "=== Этап 2: Создание нового виртуального окружения ===" -ForegroundColor Cyan
& $PSScriptRoot/create-new-venv.ps1
$venvExitCode = $LASTEXITCODE
if ($venvExitCode -ne 0) {
    Write-Host "✗ Создание виртуального окружения завершилось с ошибкой (код: $venvExitCode)" -ForegroundColor Red
    if (-not $Force) {
        Write-Host "  Для продолжения используйте параметр -Force" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "⚠ Продолжение принудительно (-Force)" -ForegroundColor Yellow
} else {
    Write-Host "✓ Этап 2 завершен" -ForegroundColor Green
}
Write-Host

# Этап 3: Оптимизация Docker
if (-not $SkipDocker) {
    Write-Host "=== Этап 3: Оптимизация Docker для быстрых утилит ===" -ForegroundColor Cyan
    
    # Проверка наличия Dockerfile.dev-tools
    if (Test-Path -Path "docker/Dockerfile.dev-tools") {
        Write-Host "  ✓ Dockerfile.dev-tools найден" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Dockerfile.dev-tools не найден" -ForegroundColor Red
        exit 1
    }
    
    # Сборка lightweight образа
    Write-Host "  Сборка lightweight Docker образа..." -ForegroundColor Yellow
    docker build -f docker/Dockerfile.dev-tools -t freesport-dev-tools ./backend
    $dockerExitCode = $LASTEXITCODE
    if ($dockerExitCode -ne 0) {
        Write-Host "  ✗ Ошибка при сборке Docker образа (код: $dockerExitCode)" -ForegroundColor Red
        if (-not $Force) {
            Write-Host "  Для продолжения используйте параметр -Force" -ForegroundColor Yellow
            exit 1
        }
        Write-Host "  ⚠ Продолжение принудительно (-Force)" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ Docker образ успешно собран" -ForegroundColor Green
    }
    
    Write-Host "✓ Этап 3 завершен" -ForegroundColor Green
    Write-Host
} else {
    Write-Host "⚠ Этап 3 пропущен (-SkipDocker)" -ForegroundColor Yellow
    Write-Host
}

# Этап 4: Валидация
Write-Host "=== Этап 4: Валидация и тестирование ===" -ForegroundColor Cyan

# Тест локальных утилит
Write-Host "  Тест локальных утилит..." -ForegroundColor Yellow
$localTests = @(
    @{ name = "black"; command = "backend/venv/Scripts/black.exe --version" },
    @{ name = "isort"; command = "backend/venv/Scripts/isort.exe --version" },
    @{ name = "flake8"; command = "backend/venv/Scripts/flake8.exe --version" },
    @{ name = "mypy"; command = "backend/venv/Scripts/mypy.exe --version" },
    @{ name = "pytest"; command = "backend/venv/Scripts/pytest.exe --version" }
)

$localTestsPassed = 0
foreach ($test in $localTests) {
    try {
        $result = Invoke-Expression $test.command 2>&1
        Write-Host "    ✓ $($test.name): $result" -ForegroundColor Green
        $localTestsPassed++
    } catch {
        Write-Host "    ✗ $($test.name): ошибка" -ForegroundColor Red
    }
}

# Тест Docker утилит (если не пропущен)
$dockerTestsPassed = 0
if (-not $SkipDocker) {
    Write-Host "  Тест Docker утилит..." -ForegroundColor Yellow
    $dockerTests = @(
        @{ name = "black"; command = "docker run --rm -v `$(PWD)/backend:/app` freesport-dev-tools black --version" },
        @{ name = "isort"; command = "docker run --rm -v `$(PWD)/backend:/app` freesport-dev-tools isort --version" },
        @{ name = "flake8"; command = "docker run --rm -v `$(PWD)/backend:/app` freesport-dev-tools flake8 --version" }
    )
    
    foreach ($test in $dockerTests) {
        try {
            $result = Invoke-Expression $test.command 2>&1
            Write-Host "    ✓ $($test.name): $result" -ForegroundColor Green
            $dockerTestsPassed++
        } catch {
            Write-Host "    ✗ $($test.name): ошибка" -ForegroundColor Red
        }
    }
}

# Итоги валидации
Write-Host "  Результаты валидации:" -ForegroundColor Cyan
Write-Host "    Локальные утилиты: $localTestsPassed/5 пройдено" -ForegroundColor $(if ($localTestsPassed -eq 5) { "Green" } else { "Yellow" })
if (-not $SkipDocker) {
    Write-Host "    Docker утилиты: $dockerTestsPassed/3 пройдено" -ForegroundColor $(if ($dockerTestsPassed -eq 3) { "Green" } else { "Yellow" })
}

if ($localTestsPassed -eq 5 -and ($SkipDocker -or $dockerTestsPassed -eq 3)) {
    Write-Host "✓ Этап 4 завершен успешно" -ForegroundColor Green
} else {
    Write-Host "⚠ Этап 4 завершен с предупреждениями" -ForegroundColor Yellow
    if (-not $Force) {
        exit 1
    }
    Write-Host "⚠ Продолжение принудительно (-Force)" -ForegroundColor Yellow
}
Write-Host

# Этап 5: Создание документации
Write-Host "=== Этап 5: Создание документации ===" -ForegroundColor Cyan

# Создание инструкции для разработчиков
$devGuide = @"
# Установка окружения разработки FREESPORT Platform

## Обзор
Проект использует гибридный подход:
- **Docker** для основной разработки и тестирования
- **Локальное venv** для быстрых утилит форматирования и линтинга

## Вариант 1: Docker (рекомендуется)
\`\`\`bash
make up              # Запустить все сервисы
make shell            # Shell в backend контейнере
make format           # Форматирование через Docker
make lint             # Линтинг через Docker
make test             # Полное тестирование
\`\`\`

## Вариант 2: Быстрые Docker утилиты
\`\`\`bash
make format-fast       # Быстрое форматирование через lightweight Docker
make lint-fast        # Быстрый линтинг через lightweight Docker
make test-fast-tools  # Быстрые тесты через lightweight Docker
\`\`\`

## Вариант 3: Локальные утилиты
\`\`\`bash
cd backend
python -m venv venv                    # Создать окружение (если еще не создано)
venv\Scripts\activate                   # Активировать
pip install -r requirements.txt          # Установить зависимости

# Использование утилит
venv\Scripts\black.exe .               # Форматирование
venv\Scripts\isort.exe .              # Сортировка импортов
venv\Scripts\flake8.exe .              # Линтинг
venv\Scripts\mypy.exe .               # Type checking
venv\Scripts\pytest.exe -v             # Тестирование
\`\`\`

## Структура виртуального окружения
- \`backend/venv/\` - Стандартное виртуальное окружение Python
- \`backend/venv/Scripts/\` - Исполняемые файлы Windows
- \`backend/venv/ENV_INFO.txt\` - Информация об окружении

## Устранение неполадок

### Проблема: "black не найден"
\`\`\`bash
# Решение 1: Через python -m
backend/venv/Scripts/python.exe -m black .

# Решение 2: Прямой вызов
backend/venv/Scripts/black.exe .

# Решение 3: Активация окружения
cd backend
venv\Scripts\activate
black .
\`\`\`

### Проблема: Docker утилиты не работают
\`\`\`bash
# Пересборка образа
docker build -f docker/Dockerfile.dev-tools -t freesport-dev-tools ./backend

# Проверка образа
docker run --rm freesport-dev-tools --version
\`\`\`

## Синхронизация окружений
Для проверки согласованности версий:
\`\`\`bash
# Сравнить локальные и Docker версии
make check-env-consistency
\`\`\`
"@

$devGuide | Out-File -FilePath "docs/development-environment.md" -Encoding UTF8
Write-Host "  ✓ Документация создана: docs/development-environment.md" -ForegroundColor Green

Write-Host "✓ Этап 5 завершен" -ForegroundColor Green
Write-Host

# Итоги миграции
Write-Host "=== Миграция завершена ===" -ForegroundColor Green
Write-Host
Write-Host "Что было сделано:" -ForegroundColor Cyan
Write-Host "  ✓ Создано резервное копирование старого окружения" -ForegroundColor Gray
Write-Host "  ✓ Создано новое стандартное виртуальное окружение" -ForegroundColor Gray
Write-Host "  ✓ Оптимизирован Docker для быстрых утилит" -ForegroundColor Gray
Write-Host "  ✓ Обновлен Makefile с новыми командами" -ForegroundColor Gray
Write-Host "  ✓ Создана документация для разработчиков" -ForegroundColor Gray
Write-Host
Write-Host "Доступные команды:" -ForegroundColor Cyan
Write-Host "  make format-fast    # Быстрое форматирование через Docker" -ForegroundColor White
Write-Host "  make format-local   # Локальное форматирование" -ForegroundColor White
Write-Host "  make lint-fast      # Быстрый линтинг через Docker" -ForegroundColor White
Write-Host "  make lint-local     # Локальный линтинг" -ForegroundColor White
Write-Host "  make test-local     # Локальное тестирование" -ForegroundColor White
Write-Host
Write-Host "Для восстановления старого окружения:" -ForegroundColor Yellow
Write-Host "  Move-Item 'backend/venv.backup.*' 'backend/venv' -Force" -ForegroundColor Gray
Write-Host