# Скрипт резервного копирования текущего виртуального окружения
# Создает бэкап перед миграцией на новую структуру

Write-Host "=== Резервное копирование текущего виртуального окружения ===" -ForegroundColor Cyan
Write-Host

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка существования venv
if (-not (Test-Path -Path "backend/venv")) {
    Write-Host "⚠ Виртуальное окружение backend/venv не найдено" -ForegroundColor Yellow
    exit 0
}

# Создание резервной копии
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = "backend/venv.backup.$timestamp"

Write-Host "Создание резервной копии..." -ForegroundColor Yellow
if (Test-Path -Path $backupPath) {
    Remove-Item -Path $backupPath -Recurse -Force
}

Copy-Item -Path "backend/venv" -Destination $backupPath -Recurse
Write-Host "✓ Резервная копия создана: $backupPath" -ForegroundColor Green

# Фиксация текущих версий пакетов
$requirementsBackup = "requirements.backup.$timestamp.txt"
if (Test-Path -Path "backend/venv/Script/pip.exe") {
    Write-Host "Фиксация версий пакетов..." -ForegroundColor Yellow
    & backend/venv/Script/pip.exe freeze > $requirementsBackup
    Write-Host "✓ Версии пакетов сохранены: $requirementsBackup" -ForegroundColor Green
} else {
    Write-Host "⚠ pip.exe не найден в текущем venv" -ForegroundColor Yellow
}

# Анализ структуры текущего окружения
Write-Host
Write-Host "Анализ структуры текущего окружения:" -ForegroundColor Cyan

if (Test-Path -Path "backend/venv/Scripts") {
    Write-Host "  ✓ Найден стандартный каталог Scripts" -ForegroundColor Green
} elseif (Test-Path -Path "backend/venv/Script") {
    Write-Host "  ⚠ Найден нестандартный каталог Script" -ForegroundColor Yellow
} else {
    Write-Host "  ✗ Каталог Scripts/Script не найден" -ForegroundColor Red
}

# Проверка ключевых утилит
$utilities = @("black.exe", "isort.exe", "flake8.exe", "mypy.exe", "pytest.exe")
Write-Host "Проверка установленных утилит:" -ForegroundColor Cyan

foreach ($util in $utilities) {
    $utilPath = "backend/venv/Script/$util"
    if (Test-Path -Path $utilPath) {
        Write-Host "  ✓ $util" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $util не найден" -ForegroundColor Red
    }
}

Write-Host
Write-Host "=== Резервное копирование завершено ===" -ForegroundColor Green
Write-Host "Для восстановления используйте: Move-Item '$backupPath' 'backend/venv' -Force" -ForegroundColor Gray