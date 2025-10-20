param(
    [string]$ComposeFile = "docker-compose.test.yml",
    [string]$DataDir = "/app/data/import_1c",
    [int]$ChunkSize = 500,
    [switch]$SkipMigrate,
    [switch]$SkipBackup,
    [switch]$SkipImport,
    [string]$BackupOutput,
    [string[]]$ImportArgs = @()
)

$ErrorActionPreference = "Stop"

# Функция-обёртка для выполнения docker-команд с проверкой кода возврата
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
    Write-Host "⚙️ Используем compose-файл: $ComposeFile"
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
        Write-Host "⏭️ Пропуск применения миграций (флаг --SkipMigrate)."
    }

    if (-not $SkipBackup) {
        $backupCommand = @("docker", "compose", "-f", $ComposeFile, "run", "--rm", "backend", "python", "manage.py", "backup_db")
        if ($BackupOutput) {
            $backupCommand += @("--output", $BackupOutput)
        }

        Invoke-DockerCommand `
            -Message "💾 Создание резервной копии базы данных..." `
            -ErrorMessage "Резервное копирование завершилось с ошибкой." `
            -Command $backupCommand
    }
    else {
        Write-Host "⏭️ Пропуск резервного копирования (флаг --SkipBackup)."
    }

    if (-not $SkipImport) {
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
            -Message "⬇️ Запуск полного импорта каталога из 1С..." `
            -ErrorMessage "Импорт каталога завершился с ошибкой." `
            -Command $importCommand
    }
    else {
        Write-Host "⏭️ Пропуск импорта (флаг --SkipImport)."
    }

    Write-Host "✅ Импорт завершён."
}
catch {
    Write-Error "❌ $($_.Exception.Message)"
    exit 1
}
