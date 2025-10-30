# Скрипт создания нового стандартного виртуального окружения
# Заменяет некорректное venv на стандартное

Write-Host "=== Создание нового стандартного виртуального окружения ===" -ForegroundColor Cyan
Write-Host

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка наличия Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python доступен: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python недоступен. Установите Python 3.11+" -ForegroundColor Red
    exit 1
}

# Удаление старого виртуального окружения
if (Test-Path -Path "backend/venv") {
    Write-Host "Удаление старого виртуального окружения..." -ForegroundColor Yellow
    Remove-Item -Path "backend/venv" -Recurse -Force
    Write-Host "✓ Старое окружение удалено" -ForegroundColor Green
} else {
    Write-Host "✓ Старое окружение не найдено" -ForegroundColor Gray
}

# Создание нового виртуального окружения
Write-Host "Создание нового виртуального окружения..." -ForegroundColor Yellow
Set-Location -Path "backend"

try {
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        throw "Ошибка при создании venv"
    }
    Write-Host "✓ Виртуальное окружение создано" -ForegroundColor Green
} catch {
    Write-Host "✗ Ошибка при создании виртуального окружения: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Проверка структуры
Write-Host "Проверка структуры виртуального окружения..." -ForegroundColor Cyan

if (Test-Path -Path "venv/Scripts") {
    Write-Host "  ✓ Стандартный каталог Scripts создан" -ForegroundColor Green
} else {
    Write-Host "  ✗ Стандартный каталог Scripts не найден" -ForegroundColor Red
    exit 1
}

if (Test-Path -Path "venv/Scripts/python.exe") {
    Write-Host "  ✓ Python executable найден" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python executable не найден" -ForegroundColor Red
    exit 1
}

if (Test-Path -Path "venv/Scripts/pip.exe") {
    Write-Host "  ✓ Pip executable найден" -ForegroundColor Green
} else {
    Write-Host "  ✗ Pip executable не найден" -ForegroundColor Red
    exit 1
}

# Активация и обновление pip
Write-Host "Активация и обновление pip..." -ForegroundColor Yellow
try {
    # Попытка обновления pip с обработкой ошибок
    $pipUpgradeResult = & venv/Scripts/pip.exe install --upgrade pip 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Предупреждение: pip не удалось обновить, продолжаем с текущей версией" -ForegroundColor Yellow
        Write-Host "  Код ошибки: $LASTEXITCODE" -ForegroundColor Gray
        Write-Host "  Вывод: $pipUpgradeResult" -ForegroundColor Gray
    } else {
        Write-Host "✓ Pip обновлен" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ Предупреждение: pip не удалось обновить, продолжаем с текущей версией" -ForegroundColor Yellow
    Write-Host "  Ошибка: $($_.Exception.Message)" -ForegroundColor Gray
}

# Установка утилит разработки
Write-Host "Установка утилит разработки..." -ForegroundColor Yellow

$devTools = @(
    "black==23.11.0",
    "isort==5.12.0", 
    "flake8==6.1.0",
    "mypy==1.7.1",
    "pytest==7.4.3",
    "pytest-cov==4.1.0",
    "pytest-django==4.7.0"
)

foreach ($tool in $devTools) {
    Write-Host "  Установка $tool..." -ForegroundColor Gray
    & venv/Scripts/pip.exe install $tool
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Ошибка при установке $tool" -ForegroundColor Red
    } else {
        Write-Host "  ✓ $tool установлен" -ForegroundColor Green
    }
}

# Проверка установленных утилит
Write-Host
Write-Host "Проверка установленных утилит:" -ForegroundColor Cyan

$utilities = @("black", "isort", "flake8", "mypy", "pytest")
foreach ($util in $utilities) {
    $utilPath = "venv/Scripts/$util.exe"
    if (Test-Path -Path $utilPath) {
        Write-Host "  ✓ $util.exe" -ForegroundColor Green
        
        # Проверка версии
        try {
            $version = & $utilPath --version 2>&1
            Write-Host "    Версия: $version" -ForegroundColor Gray
        } catch {
            Write-Host "    Версия: недоступна" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ✗ $util.exe не найден" -ForegroundColor Red
    }
}

# Создание файла с информацией об окружении
$envInfo = @"
# Информация о виртуальном окружении
Создано: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Python: $(python --version 2>&1)
Pip: $(venv/Scripts/pip.exe --version 2>&1)

# Установленные утилиты разработки
- black: $(venv/Scripts/black.exe --version 2>&1)
- isort: $(venv/Scripts/isort.exe --version 2>&1)
- flake8: $(venv/Scripts/flake8.exe --version 2>&1)
- mypy: $(venv/Scripts/mypy.exe --version 2>&1)
- pytest: $(venv/Scripts/pytest.exe --version 2>&1)
"@

$envInfo | Out-File -FilePath "venv/ENV_INFO.txt" -Encoding UTF8
Write-Host "✓ Информация об окружении сохранена в venv/ENV_INFO.txt" -ForegroundColor Green

Write-Host
Write-Host "=== Новое виртуальное окружение успешно создано ===" -ForegroundColor Green
Write-Host
Write-Host "Для активации используйте:" -ForegroundColor Cyan
Write-Host "  cd backend"
Write-Host "  venv\Scripts\activate"
Write-Host
Write-Host "Для использования утилит:" -ForegroundColor Cyan
Write-Host "  venv\Scripts\black.exe ."
Write-Host "  venv\Scripts\isort.exe ."
Write-Host "  venv\Scripts\flake8.exe ."
Write-Host "  venv\Scripts\mypy.exe ."
Write-Host "  venv\Scripts\pytest.exe"