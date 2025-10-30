# Быстрое исправление проблемы с black без полной миграции
# Создает символическую ссылку для исправления пути Script/Scripts

Write-Host "=== Быстрое исправление проблемы с black ===" -ForegroundColor Cyan
Write-Host

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка текущей структуры
$scriptPath = "backend/venv/Script"
$scriptsPath = "backend/venv/Scripts"

Write-Host "Анализ текущей структуры..." -ForegroundColor Cyan

if (Test-Path -Path $scriptPath) {
    Write-Host "  ✓ Найден каталог: $scriptPath" -ForegroundColor Green
} else {
    Write-Host "  ✗ Каталог не найден: $scriptPath" -ForegroundColor Red
    exit 1
}

if (Test-Path -Path $scriptsPath) {
    Write-Host "  ✓ Найден каталог: $scriptsPath" -ForegroundColor Green
    Write-Host "  ℹ Стандартная структура уже существует" -ForegroundColor Gray
    Write-Host "  ✗ Проблема не в структуре каталогов" -ForegroundColor Red
    exit 1
} else {
    Write-Host "  ⚠ Стандартный каталог не найден: $scriptsPath" -ForegroundColor Yellow
}

Write-Host

# Проверка наличия black.exe
$blackPath = "$scriptPath/black.exe"
if (Test-Path -Path $blackPath) {
    Write-Host "  ✓ Найден black.exe: $blackPath" -ForegroundColor Green
} else {
    Write-Host "  ✗ black.exe не найден: $blackPath" -ForegroundColor Red
    exit 1
}

Write-Host

# Решение 1: Создание символической ссылки
Write-Host "=== Решение 1: Создание символической ссылки ===" -ForegroundColor Cyan

try {
    New-Item -ItemType SymbolicLink -Path $scriptsPath -Target $scriptPath -Force
    Write-Host "✓ Символическая ссылка создана: $scriptsPath → $scriptPath" -ForegroundColor Green
} catch {
    Write-Host "✗ Ошибка при создании символической ссылки: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Попробуйте запустить от имени администратора" -ForegroundColor Yellow
    exit 1
}

# Проверка работы
Write-Host
Write-Host "=== Проверка работы ===" -ForegroundColor Cyan

try {
    $result = & "$scriptsPath/black.exe" --version 2>&1
    Write-Host "✓ black работает: $result" -ForegroundColor Green
} catch {
    Write-Host "✗ black не работает через символическую ссылку" -ForegroundColor Red
    Write-Host "  Ошибка: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host

# Решение 2: Создание bat файла для удобства
Write-Host "=== Решение 2: Создание bat файла ===" -ForegroundColor Cyan

$batContent = @"
@echo off
REM Быстрый запуск black с исправленным путем
backend\venv\Scripts\black.exe %*
"@

$batPath = "scripts/black.bat"
$batContent | Out-File -FilePath $batPath -Encoding ASCII
Write-Host "✓ Создан bat файл: $batPath" -ForegroundColor Green

Write-Host
Write-Host "=== Использование ===" -ForegroundColor Cyan
Write-Host "Теперь можно использовать следующие команды:" -ForegroundColor Yellow
Write-Host
Write-Host "  1. Через символическую ссылку:" -ForegroundColor White
Write-Host "     backend\venv\Scripts\black.exe ." -ForegroundColor Gray
Write-Host
Write-Host "  2. Через bat файл:" -ForegroundColor White
Write-Host "     scripts\black.bat ." -ForegroundColor Gray
Write-Host
Write-Host "  3. Через python -m (всегда работает):" -ForegroundColor White
Write-Host "     backend\venv\Scripts\python.exe -m black ." -ForegroundColor Gray
Write-Host
Write-Host "  4. Активация окружения:" -ForegroundColor White
Write-Host "     cd backend"
Write-Host "     venv\Scripts\activate"
Write-Host "     black ." -ForegroundColor Gray
Write-Host

Write-Host "=== Рекомендация ===" -ForegroundColor Cyan
Write-Host "Для полного решения проблемы рекомендуется выполнить полную миграцию:" -ForegroundColor Yellow
Write-Host "powershell -ExecutionPolicy Bypass -File scripts/migration/migrate-to-unified-env.ps1" -ForegroundColor Gray
Write-Host
Write-Host "Это создаст стандартное виртуальное окружение и устранит все проблемы." -ForegroundColor Gray