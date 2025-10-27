# Скрипт безопасного удаления виртуального окружения
# Создает резервную копию перед удалением

param(
    [switch]$Force,
    [switch]$SkipBackup
)

Write-Host "=== Удаление виртуального окружения ===" -ForegroundColor Cyan
Write-Host

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка наличия venv
$venvPath = "backend/venv"
if (-not (Test-Path -Path $venvPath)) {
    Write-Host "ℹ Виртуальное окружение не найдено: $venvPath" -ForegroundColor Gray
    Write-Host "✓ Удаление не требуется" -ForegroundColor Green
    exit 0
}

Write-Host "⚠ Найдено виртуальное окружение: $venvPath" -ForegroundColor Yellow
Write-Host

# Резервное копирование (если не пропущено)
if (-not $SkipBackup) {
    Write-Host "Создание резервной копии..." -ForegroundColor Yellow
    
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = "backend/venv.backup.$timestamp"
    
    if (Test-Path -Path $backupPath) {
        Write-Host "⚠ Резервная копия уже существует: $backupPath" -ForegroundColor Yellow
        if (-not $Force) {
            Write-Host "Для перезаписи используйте параметр -Force" -ForegroundColor Red
            exit 1
        }
    }
    
    try {
        Copy-Item -Path $venvPath -Destination $backupPath -Recurse -Force
        Write-Host "✓ Резервная копия создана: $backupPath" -ForegroundColor Green
    } catch {
        Write-Host "✗ Ошибка при создании резервной копии: $($_.Exception.Message)" -ForegroundColor Red
        if (-not $Force) {
            exit 1
        }
        Write-Host "⚠ Продолжение принудительно (-Force)" -ForegroundColor Yellow
    }
} else {
    Write-Host "ℹ Пропущено резервное копирование (-SkipBackup)" -ForegroundColor Gray
}

Write-Host

# Удаление виртуального окружения
Write-Host "Удаление виртуального окружения..." -ForegroundColor Yellow

try {
    Remove-Item -Path $venvPath -Recurse -Force
    Write-Host "✓ Виртуальное окружение удалено: $venvPath" -ForegroundColor Green
} catch {
    Write-Host "✗ Ошибка при удалении виртуального окружения: $($_.Exception.Message)" -ForegroundColor Red
    if (-not $Force) {
        exit 1
    }
    Write-Host "⚠ Продолжение принудительно (-Force)" -ForegroundColor Yellow
}

Write-Host

# Проверка результата
if (Test-Path -Path $venvPath) {
    Write-Host "✗ Виртуальное окружение все еще существует" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✓ Виртуальное окружение успешно удалено" -ForegroundColor Green
}

Write-Host

# Рекомендации
Write-Host "=== Рекомендации ===" -ForegroundColor Cyan
Write-Host "Для создания нового виртуального окружения:" -ForegroundColor Yellow
Write-Host "  cd backend"
Write-Host "  python -m venv venv"
Write-Host "  venv\Scripts\activate"
Write-Host "  pip install -r requirements.txt"
Write-Host
Write-Host "Для восстановления из резервной копии:" -ForegroundColor Yellow
if (-not $SkipBackup) {
    Write-Host "  Move-Item '$backupPath' 'backend/venv' -Force" -ForegroundColor Gray
}
Write-Host
Write-Host "=== Удаление завершено ===" -ForegroundColor Green