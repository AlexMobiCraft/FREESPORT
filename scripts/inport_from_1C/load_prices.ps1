param(
    [string]$ComposeFile = "docker-compose.test.yml",
    [string]$DataDir = "/app/data/import_1c",
    [int]$ChunkSize = 500,
    [switch]$SkipMigrate,
    [string[]]$ImportArgs = @(),
    [string]$ServerIP = "5.35.124.149",
    [string]$RemoteDataPath = "/home/freesport/freesport/data/import_1c",
    [string]$SshKeyPath = "C:\\Users\\38670\\.ssh\\id_ed25519",
    [switch]$SkipSync,
    [switch]$UseLocalData
)

$ErrorActionPreference = "Stop"

# Функция запускает docker-команды и валидирует код возврата.
function Invoke-DockerCommand {
    param(
        [string]$Message,
        [string]$ErrorMessage,
        [string[]]$Command
    )

    Write-Host $Message

    if (-not $Command -or $Command.Length -eq 0) {
        throw "Команда для выполнения не задана"
    }

    $executable = $Command[0]
    $arguments = @()
    if ($Command.Length -gt 1) {
        $arguments = $Command[1..($Command.Length - 1)]
    }

    & $executable @arguments

    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

# Функция синхронизирует локальные данные с сервером 1С.
function Sync-DataFromServer {
    param(
        [string]$ServerIP,
        [string]$RemoteDataPath,
        [string]$LocalDataPath,
        [string]$SshKeyPath
    )

    Write-Host "🔄 Синхронизация данных с сервера $ServerIP..." -ForegroundColor Cyan

    $syncScriptPath = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) "..\server\sync_import_data.ps1"

    if (-not (Test-Path $syncScriptPath)) {
        throw "Скрипт синхронизации не найден: $syncScriptPath"
    }

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
    $projectRoot = Split-Path (Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent) -Parent
    $localDataPath = Join-Path $projectRoot "data\import_1c"

    Write-Host "📁 Локальная директория данных: $localDataPath" -ForegroundColor Gray
    Write-Host "🖥️  Директория в контейнере: $DataDir" -ForegroundColor Gray

    if (-not $SkipSync -and -not $UseLocalData) {
        Sync-DataFromServer -ServerIP $ServerIP -RemoteDataPath $RemoteDataPath -LocalDataPath $localDataPath -SshKeyPath $SshKeyPath
    }
    elseif ($UseLocalData) {
        Write-Host "⚠️ Используем локальные данные без синхронизации" -ForegroundColor Yellow
    }
    else {
        Write-Host "⏭️ Пропуск синхронизации данных (флаг -SkipSync)" -ForegroundColor Yellow
    }

    if (-not (Test-Path $localDataPath)) {
        throw "❌ Локальная директория данных не найдена: $localDataPath"
    }

    Invoke-DockerCommand `
        -Message "🚀 Запуск сервисов (PostgreSQL, Redis)..." `
        -ErrorMessage "Не удалось запустить сервисы docker-compose." `
        -Command @("docker", "compose", "-f", $ComposeFile, "up", "-d", "--wait", "--remove-orphans")

    if (-not $SkipMigrate) {
        Invoke-DockerCommand `
            -Message "📦 Применение миграций Django..." `
            -ErrorMessage "Миграции завершились с ошибкой." `
            -Command @("docker", "compose", "-f", $ComposeFile, "run", "--rm", "backend", "python", "manage.py", "migrate")
    }
    else {
        Write-Host "⏭️ Пропуск применения миграций (флаг -SkipMigrate)."
    }

    $importCommand = @(
        "docker", "compose", "-f", $ComposeFile, "run", "--rm", "backend",
        "python", "manage.py", "import_products_from_1c",
        "--data-dir", $DataDir,
        "--chunk-size", $ChunkSize,
        "--file-type", "prices",
        "--skip-backup"
    )

    if ($ImportArgs -and $ImportArgs.Length -gt 0) {
        $importCommand += $ImportArgs
    }

    Invoke-DockerCommand `
        -Message "💰 Обновление цен и типов цен..." `
        -ErrorMessage "Обновление цен завершилось с ошибкой." `
        -Command $importCommand

    Write-Host "✅ Загрузка цен завершена."
}
catch {
    Write-Error "❌ $($_.Exception.Message)"
    exit 1
}
