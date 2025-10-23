param(
    [string]$ComposeFile = "docker-compose.test.yml",
    [string]$DataDir = "/app/data/import_1c",
    [string]$ServerIP = "5.35.124.149",
    [string]$RemoteDataPath = "/home/freesport/freesport/data/import_1c",
    [string]$SshKeyPath = "C:\\Users\\38670\\.ssh\\id_ed25519",
    [switch]$SkipSync = $false,
    [switch]$UseLocalData = $false
)

$ErrorActionPreference = "Stop"

# Функция для синхронизации данных с сервера
function Sync-DataFromServer {
    param(
        [string]$ServerIP,
        [string]$RemoteDataPath,
        [string]$LocalDataPath,
        [string]$SshKeyPath
    )
    
    Write-Host "🔄 Синхронизация данных с сервера $ServerIP..." -ForegroundColor Cyan
    
    # Проверяем существование скрипта синхронизации
    $syncScriptPath = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) "..\server\sync_import_data.ps1"
    
    if (-not (Test-Path $syncScriptPath)) {
        throw "Скрипт синхронизации не найден: $syncScriptPath"
    }
    
    # Запускаем синхронизацию с параметром ForceCopy для получения свежих данных
    $syncArgs = @{
        IP = $ServerIP
        RemoteDataPath = $RemoteDataPath
        SshKeyPath = $SshKeyPath
        ForceCopy = $true
        SkipVerification = $false
    }
    
    try {
        & $syncScriptPath @syncArgs
        Write-Host "✅ Синхронизация завершена успешно" -ForegroundColor Green
    }
    catch {
        throw "❌ Ошибка синхронизации данных: $($_.Exception.Message)"
    }
}

try {
    # Определяем путь к локальной директории данных
    $projectRoot = Split-Path (Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent) -Parent
    $localDataPath = Join-Path $projectRoot "data\import_1c"
    
    Write-Host "📁 Локальная директория данных: $localDataPath" -ForegroundColor Gray
    Write-Host "🖥️  Директория в контейнере: $DataDir" -ForegroundColor Gray
    
    # Синхронизируем данные с сервера, если не пропущено
    if (-not $SkipSync -and -not $UseLocalData) {
        Sync-DataFromServer -ServerIP $ServerIP -RemoteDataPath $RemoteDataPath -LocalDataPath $localDataPath -SshKeyPath $SshKeyPath
    }
    elseif ($UseLocalData) {
        Write-Host "⚠️ Используем локальные данные без синхронизации" -ForegroundColor Yellow
    }
    else {
        Write-Host "⏭️ Пропуск синхронизации данных (флаг -SkipSync)" -ForegroundColor Yellow
    }
    
    # Проверяем существование локальных данных
    if (-not (Test-Path $localDataPath)) {
        throw "❌ Локальная директория данных не найдена: $localDataPath"
    }
    
    Write-Host "🚀 Запуск сервисов (PostgreSQL, Redis)..." -ForegroundColor Cyan
    docker compose -f $ComposeFile up -d --wait --remove-orphans

    Write-Host "📦 Применение миграций Django..." -ForegroundColor Cyan
    docker compose -f $ComposeFile run --rm backend python manage.py migrate

    Write-Host "⬇️ Запуск полного импорта каталога из 1С..." -ForegroundColor Cyan
    docker compose -f $ComposeFile run --rm backend python manage.py import_catalog_from_1c --data-dir $DataDir

    Write-Host "✅ Импорт завершён." -ForegroundColor Green
}
catch {
    Write-Error "❌ $($_.Exception.Message)"
    exit 1
}
