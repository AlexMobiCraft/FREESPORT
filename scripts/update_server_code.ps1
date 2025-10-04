# Скрипт для актуализации кода проекта FREESPORT на сервере 192.168.1.130
# Использование (по умолчанию работает с текущей веткой):
#   pwsh .\scripts\update_server_code.ps1
#   pwsh .\scripts\update_server_code.ps1 -Branch feature/x -EnvFileLocal "backend/.env.test"
# Перед запуском убедитесь, что локальные изменения закоммичены и при необходимости запушены в origin.

param(
    [string]$User = "alex",
    [string]$ServerHost = "192.168.1.130",
    [string]$ProjectPathRemote = "~/FREESPORT",
    [string]$DockerContext = "freesport-remote",
    [string]$ComposeFile = "docker-compose.test.yml",
    [string]$EnvFileLocal = "backend/.env",
    [string]$EnvFileRemote = "~/FREESPORT/backend/.env",
    [string]$SshKeyPath = "C:\\Users\\38670\\.ssh\\id_ed25519",
    [string]$Branch
)

# Функция запускает ssh-agent и добавляет указанный приватный ключ
function Start-SshAgentIfNeeded {
    param(
        [string]$KeyPath
    )

    if (-not (Test-Path -Path $KeyPath)) {
        throw "SSH-ключ не найден: $KeyPath"
    }

    Start-Service ssh-agent -ErrorAction SilentlyContinue | Out-Null
    ssh-add $KeyPath | Out-Null
}

# Функция определяет текущую ветку git в указанной директории
function Get-CurrentGitBranch {
    param(
        [string]$WorkingDirectory
    )

    $branch = (git -C $WorkingDirectory rev-parse --abbrev-ref HEAD).Trim()
    if ([string]::IsNullOrWhiteSpace($branch)) {
        throw "Не удалось определить текущую ветку git"
    }

    return $branch
}

# Функция выполняет git fetch/pull на сервере по SSH
function Invoke-RemoteGitUpdate {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$RemotePath,
        [string]$BranchName
    )

    $remoteCommand = "cd $RemotePath && git fetch origin && git checkout $BranchName && git pull --ff-only origin $BranchName && git status"
    ssh "$ConnectionUser@$ConnectionHost" "bash -lc \"$remoteCommand\""
}

# Функция копирует локальный .env файл на сервер через SCP
function Copy-EnvFileToServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$LocalPath,
        [string]$RemotePath
    )

    if (-not (Test-Path -Path $LocalPath)) {
        throw "Локальный файл не найден: $LocalPath"
    }

    scp $LocalPath ([string]::Format("{0}@{1}:{2}", $ConnectionUser, $ConnectionHost, $RemotePath))
}

# Функция перезапускает тестовые контейнеры через docker compose в удалённом контексте
function Restart-RemoteCompose {
    param(
        [string]$Context,
        [string]$ComposeFilePath
    )

    & docker --context $Context compose -f $ComposeFilePath down -v
    & docker --context $Context compose -f $ComposeFilePath up -d
}

$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$projectRoot = Split-Path -Path $scriptDirectory -Parent

Push-Location $projectRoot

try {
    Write-Host "=== Актуализация кода на сервере ===" -ForegroundColor Cyan

    Start-SshAgentIfNeeded -KeyPath $SshKeyPath

    if (-not $Branch) {
        $Branch = Get-CurrentGitBranch -WorkingDirectory $projectRoot
    }
    Write-Host "Используемая ветка: $Branch" -ForegroundColor Yellow

    Write-Host "Обновление кода на сервере..." -ForegroundColor Yellow
    Invoke-RemoteGitUpdate -ConnectionUser $User -ConnectionHost $ServerHost -RemotePath $ProjectPathRemote -BranchName $Branch

    $absoluteEnvPath = if ([System.IO.Path]::IsPathRooted($EnvFileLocal)) { $EnvFileLocal } else { Join-Path -Path $projectRoot -ChildPath $EnvFileLocal }
    Write-Host "Синхронизация .env файла..." -ForegroundColor Yellow
    Copy-EnvFileToServer -ConnectionUser $User -ConnectionHost $ServerHost -LocalPath $absoluteEnvPath -RemotePath $EnvFileRemote

    Write-Host "Перезапуск docker compose в контексте '$DockerContext'..." -ForegroundColor Yellow
    Restart-RemoteCompose -Context $DockerContext -ComposeFilePath $ComposeFile

    Write-Host "✓ Актуализация завершена" -ForegroundColor Green
}
catch {
    Write-Host "✗ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
finally {
    Pop-Location
}
