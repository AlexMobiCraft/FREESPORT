# Скрипт исправления существующего виртуального окружения
# Работает с текущим venv и исправляет структуру Script/Scripts

Write-Host "=== Исправление существующего виртуального окружения ===" -ForegroundColor Cyan
Write-Host

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка наличия venv
$venvPath = "backend/venv"
$backupVenvPath = "backend/venv.backup.20251027-114659"

if (-not (Test-Path -Path $venvPath)) {
    Write-Host "✗ Виртуальное окружение не найдено: $venvPath" -ForegroundColor Red
    Write-Host "ℹ Найден backup: $backupVenvPath" -ForegroundColor Yellow
    
    if (Test-Path -Path $backupVenvPath) {
        Write-Host "Восстановление из backup..." -ForegroundColor Yellow
        Move-Item -Path $backupVenvPath -Destination $venvPath -Force
        Write-Host "✓ Виртуальное окружение восстановлено из backup" -ForegroundColor Green
    } else {
        Write-Host "✗ Backup также не найден" -ForegroundColor Red
        exit 1
    }
}

# Проверка структуры
Write-Host "Анализ структуры виртуального окружения..." -ForegroundColor Cyan

$scriptPath = "$venvPath/Script"
$scriptsPath = "$venvPath/Scripts"

$hasScript = Test-Path -Path $scriptPath
$hasScripts = Test-Path -Path $scriptsPath

Write-Host "  Каталог Script: $(if ($hasScript) { 'найден' } else { 'не найден' })" -ForegroundColor $(if ($hasScript) { "Green" } else { "Red" })
Write-Host "  Каталог Scripts: $(if ($hasScripts) { 'найден' } else { 'не найден' })" -ForegroundColor $(if ($hasScripts) { "Green" } else { "Red" })

if ($hasScript -and -not $hasScripts) {
    Write-Host "✓ Обнаружена проблема: есть Script, но нет Scripts" -ForegroundColor Yellow
    Write-Host "Исправление структуры..." -ForegroundColor Yellow
    
    try {
        # Переименование Script в Scripts
        Rename-Item -Path $scriptPath -NewName $scriptsPath -Force
        Write-Host "✓ Script переименован в Scripts" -ForegroundColor Green
        
        # Проверка наличия black.exe
        $blackPath = "$scriptsPath/black.exe"
        if (Test-Path -Path $blackPath) {
            Write-Host "✓ black.exe найден: $blackPath" -ForegroundColor Green
            
            # Тестирование работы black
            try {
                $version = & $blackPath --version 2>&1
                Write-Host "✓ black работает: $version" -ForegroundColor Green
            } catch {
                Write-Host "⚠ black не работает: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "✗ black.exe не найден после переименования" -ForegroundColor Red
        }
    } catch {
        Write-Host "✗ Ошибка при переименовании: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
} elseif ($hasScripts -and -not $hasScript) {
    Write-Host "✓ Структура уже корректна: есть Scripts, нет Script" -ForegroundColor Green
} elseif ($hasScript -and $hasScripts) {
    Write-Host "⚠ Обнаружены оба каталога: Script и Scripts" -ForegroundColor Yellow
    Write-Host "Рекомендуется удалить Script и оставить Scripts" -ForegroundColor Yellow
} else {
    Write-Host "✗ Ни Script, ни Scripts не найдены" -ForegroundColor Red
    exit 1
}

Write-Host

# Создание bat файла для удобства
Write-Host "Создание bat файла для удобства..." -ForegroundColor Yellow

$batContent = @"
@echo off
REM Исправленный запуск black
backend\venv\Scripts\black.exe %*
"@

$batPath = "scripts/black-fixed.bat"
$batContent | Out-File -FilePath $batPath -Encoding ASCII
Write-Host "✓ Создан bat файл: $batPath" -ForegroundColor Green

Write-Host
Write-Host "=== Исправление завершено ===" -ForegroundColor Green
Write-Host
Write-Host "Способы использования black:" -ForegroundColor Cyan
Write-Host "  1. Через bat файл:" -ForegroundColor White
Write-Host "     scripts\black-fixed.bat ." -ForegroundColor Gray
Write-Host
Write-Host "  2. Прямой вызов:" -ForegroundColor White
Write-Host "     backend\venv\Scripts\black.exe ." -ForegroundColor Gray
Write-Host
Write-Host "  3. Через python -m:" -ForegroundColor White
Write-Host "     backend\venv\Scripts\python.exe -m black ." -ForegroundColor Gray
Write-Host
Write-Host "  4. Активация окружения:" -ForegroundColor White
Write-Host "     cd backend"
Write-Host "     venv\Scripts\activate"
Write-Host "     black ." -ForegroundColor Gray
Write-Host