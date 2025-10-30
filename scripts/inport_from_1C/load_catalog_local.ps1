param(
    [string]$ComposeFile = "docker-compose.yml",
    [string]$LocalDataPath,
    [string]$DataDir = "/app/data/import_1c",
    [int]$ChunkSize = 500,
    [switch]$SkipMigrate,
    [switch]$SkipBackup,
    [string[]]$ImportArgs = @()
)

$ErrorActionPreference = "Stop"

# Функция выполняет docker-команду и проверяет успешность выполнения.
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

try {
    $scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
    $projectRoot = Split-Path (Split-Path $scriptDir -Parent) -Parent

    if (-not $env:FREESPORT_PROJECT_ROOT -or [string]::IsNullOrWhiteSpace($env:FREESPORT_PROJECT_ROOT)) {
        $env:FREESPORT_PROJECT_ROOT = $projectRoot
    }

    if ([string]::IsNullOrWhiteSpace($LocalDataPath)) {
        $LocalDataPath = Join-Path $projectRoot "data\import_1c"
    }
    else {
        $LocalDataPath = (Resolve-Path $LocalDataPath).Path
    }

    if (-not (Test-Path $LocalDataPath)) {
        throw "❌ Локальная директория данных не найдена: $LocalDataPath"
    }

    Write-Host "📁 Локальная директория данных: $LocalDataPath" -ForegroundColor Gray
    Write-Host "🖥️  Директория в контейнере: $DataDir" -ForegroundColor Gray

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

    if (-not $SkipBackup) {
        $backupCommand = @("docker", "compose", "-f", $ComposeFile, "run", "--rm", "backend", "python", "manage.py", "backup_db")

        Invoke-DockerCommand `
            -Message "💾 Создание резервной копии базы данных..." `
            -ErrorMessage "Резервное копирование завершилось с ошибкой." `
            -Command $backupCommand
    }
    else {
        Write-Host "⏭️ Пропуск резервного копирования (флаг -SkipBackup)."
    }

    $importCommand = @(
        "docker", "compose", "-f", $ComposeFile, "run", "--rm", "backend",
        "python", "manage.py", "import_catalog_from_1c",
        "--data-dir", $DataDir,
        "--chunk-size", $ChunkSize,
        "--skip-backup"
    )

    if ($ImportArgs -and $ImportArgs.Length -gt 0) {
        $importCommand += $ImportArgs
    }

    Invoke-DockerCommand `
        -Message "⬇️ Запуск импорта каталога (товары, категории, бренды)..." `
        -ErrorMessage "Импорт каталога завершился с ошибкой." `
        -Command $importCommand

    Write-Host "✅ Импорт каталога завершён."
}
catch {
    Write-Error "❌ $($_.Exception.Message)"
    exit 1
}
