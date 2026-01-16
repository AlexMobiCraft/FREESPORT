# Script to update FREESPORT project code on server 5.35.124.149
# Usage (works with current branch by default):
#   pwsh .\scripts\update_server_code.ps1
#   pwsh .\scripts\update_server_code.ps1 -Branch feature/x -EnvFileLocal "backend/.env.test"
#   pwsh .\scripts\update_server_code.ps1 -User alex -IP 5.35.124.149
# Before running, make sure local changes are committed and pushed to origin if necessary.

param(
    [string]$User = "root",
    [string]$IP = "5.35.124.149",
    [string]$ProjectPathRemote = "/home/freesport/freesport",
    [string]$DockerContext = "freesport-remote",
    [string]$ComposeFile = "docker/docker-compose.prod.yml",
    [string]$EnvFileLocal = "backend/.env",
    [string]$EnvFileRemote = "/home/freesport/freesport/backend/.env",
    [string]$SshKeyPath = "backend\\.ssh\\id_ed25519",
    [string]$Branch,
    [switch]$UseTestCompose
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

# Function to start ssh-agent and add the specified private key
function Start-SshAgentIfNeeded {
    param(
        [string]$KeyPath
    )

    if (-not (Test-Path -Path $KeyPath)) {
        throw "SSH key not found: $KeyPath"
    }

    Start-Service ssh-agent -ErrorAction SilentlyContinue | Out-Null
    ssh-add $KeyPath | Out-Null
}

# Function to determine the current git branch in the specified directory
function Get-CurrentGitBranch {
    param(
        [string]$WorkingDirectory
    )

    $branch = (git -C $WorkingDirectory rev-parse --abbrev-ref HEAD).Trim()
    if ([string]::IsNullOrWhiteSpace($branch)) {
        throw 'Could not determine the current git branch'
    }

    return $branch
}

# Function to perform git fetch/pull on the server via SSH
function Invoke-RemoteGitUpdate {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$RemotePath,
        [string]$BranchName
    )

    $remoteCommand = "cd $RemotePath; git fetch origin; git checkout $BranchName; git pull --ff-only origin $BranchName; git status"
    # Добавляем -o BatchMode=yes чтобы отключить интерактивные запросы пароля
    ssh -o BatchMode=yes "$ConnectionUser@$ConnectionHost" $remoteCommand
}

# Function to copy a local .env file to the server via SCP
function Copy-EnvFileToServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$LocalPath,
        [string]$RemotePath
    )

    if (-not (Test-Path -Path $LocalPath)) {
        throw "Local file not found: $LocalPath"
    }

    # Добавляем -B для пакетного режима
    scp -B $LocalPath ([string]::Format('{0}@{1}:{2}', $ConnectionUser, $ConnectionHost, $RemotePath));
}

# Function to check and create Docker context if it doesn't exist
function Ensure-DockerContext {
    param(
        [string]$ContextName,
        [string]$ContextUser,
        [string]$ContextHost
    )

    try {
        $contexts = docker context ls --format "{{.Name}}"
        $contextExists = $contexts -split "`n" | Where-Object { $_.Trim() -eq $ContextName }

        if (-not $contextExists) {
            Write-Host "Создание Docker контекста '$ContextName'..." -ForegroundColor Yellow
            # Явно передаем путь к сокету ssh-agent в docker context
            $SshAgentSocket = $env:SSH_AUTH_SOCK
            if ([string]::IsNullOrEmpty($SshAgentSocket)) {
                # Попытка найти сокет, если переменная не установлена
                $SshAgentSocket = "npipe:////./pipe/openssh-ssh-agent"
            }
            Write-Host "Используется сокет SSH агента: $SshAgentSocket" -ForegroundColor Gray
            docker context create $ContextName --docker "host=ssh://$($ContextUser)@$($ContextHost),ssh-agent-socket=$SshAgentSocket" | Out-Null
        }

        Write-Host "Проверка Docker контекста '$ContextName'..." -ForegroundColor Yellow
        docker --context $ContextName ps | Out-Null

        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Не удалось подключиться к Docker контексту '$ContextName'." -ForegroundColor Red
            throw "Docker недоступен в контексте '$ContextName'"
        }

        Write-Host "✓ Docker контекст '$ContextName' доступен" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Ошибка при работе с Docker контекстом '$ContextName': $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

# Function to build, recreate and restart containers on the remote server
function Restart-RemoteCompose {
    param(
        [string]$Context,
        [string]$ComposeBuildFile,
        [string]$ComposeUpFile,
        [string]$ProjectDirectory,
        [string]$ConnectionUser,
        [string]$ConnectionHost
    )

    Write-Host "1. Сборка новых образов НАПРЯМУЮ на сервере (используя $ComposeBuildFile)..." -ForegroundColor Yellow
    $remoteBuildCommand = "cd $ProjectDirectory; docker compose -f $ComposeBuildFile build --no-cache"
    ssh -o BatchMode=yes "$ConnectionUser@$ConnectionHost" $remoteBuildCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Ошибка при сборке образов напрямую на сервере"
    }
    Write-Host "✓ Сборка образов завершена" -ForegroundColor Green

    Write-Host "2. Остановка старых контейнеров (используя $ComposeUpFile)..." -ForegroundColor Yellow
    & docker --context $Context compose -f $ComposeUpFile --project-directory $ProjectDirectory down -v
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Предупреждение: не удалось остановить контейнеры, но продолжаем..." -ForegroundColor Yellow
    }

    Write-Host "3. Запуск новых контейнеров (используя $ComposeUpFile)..." -ForegroundColor Yellow
    # Флаг --force-recreate здесь не нужен, т.к. мы используем разные образы
    & docker --context $Context compose -f $ComposeUpFile --project-directory $ProjectDirectory up -d
    
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось запустить контейнеры"
    }
    
    Write-Host "✓ Контейнеры перезапущены" -ForegroundColor Green
}

# Function to run Django migrations on the remote server
function Invoke-RemoteMigrations {
    param(
        [string]$Context,
        [string]$ComposeFilePath,
        [string]$ProjectDirectory,
        [string]$ServiceName = "backend"
    )

    Write-Host "Выполнение миграций базы данных для сервиса '$ServiceName'..." -ForegroundColor Yellow
    # The -T flag disables pseudo-tty allocation, which is necessary for non-interactive exec.
    & docker --context $Context compose -f $ComposeFilePath --project-directory $ProjectDirectory exec -T $ServiceName python manage.py migrate --no-input
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Предупреждение: Не удалось выполнить миграции" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Миграции выполнены" -ForegroundColor Green
    }
}

$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$projectRoot = (Resolve-Path (Join-Path $scriptDirectory '..\..')).Path

Push-Location $projectRoot

try {
    Write-Host '=== Updating code on the server ===' -ForegroundColor Cyan

    # Используем test compose файл если указан флаг
    # Этот скрипт теперь всегда использует docker-compose.prod.yml
    # Для тестов используется отдельный скрипт run-tests-docker.ps1
    Write-Host "Используется compose-файл для production: $ComposeFile" -ForegroundColor Yellow

    $absoluteSshKeyPath = if ([System.IO.Path]::IsPathRooted($SshKeyPath)) { $SshKeyPath } else { Join-Path -Path $projectRoot -ChildPath $SshKeyPath }
    Start-SshAgentIfNeeded -KeyPath $absoluteSshKeyPath

    if (-not $Branch) {
        $Branch = Get-CurrentGitBranch -WorkingDirectory $projectRoot
    }
    Write-Host "Using branch: $Branch" -ForegroundColor Yellow

    Write-Host 'Updating code on the server...' -ForegroundColor Yellow
    Invoke-RemoteGitUpdate -ConnectionUser $User -ConnectionHost $IP -RemotePath $ProjectPathRemote -BranchName $Branch

    $absoluteEnvPath = if ([System.IO.Path]::IsPathRooted($EnvFileLocal)) { $EnvFileLocal } else { Join-Path -Path $projectRoot -ChildPath $EnvFileLocal }
    Write-Host 'Syncing .env file...' -ForegroundColor Yellow
    Copy-EnvFileToServer -ConnectionUser $User -ConnectionHost $IP -LocalPath $absoluteEnvPath -RemotePath $EnvFileRemote

    Write-Host "Проверка Docker контекста '$DockerContext'..." -ForegroundColor Yellow
    Ensure-DockerContext -ContextName $DockerContext -ContextUser $User -ContextHost $IP

    Write-Host "Restarting docker compose in context '$DockerContext'..." -ForegroundColor Yellow
    
    try {
        $ComposeBuildFile = "docker/docker-compose.build.yml"
        Restart-RemoteCompose -Context $DockerContext -ComposeBuildFile $ComposeBuildFile -ComposeUpFile $ComposeFile -ProjectDirectory $ProjectPathRemote -ConnectionUser $User -ConnectionHost $IP
        Invoke-RemoteMigrations -Context $DockerContext -ComposeFilePath $ComposeFile -ProjectDirectory $ProjectPathRemote
    }
    finally {
        # Код очистки больше не нужен
    }

    Write-Host '✓ Update complete' -ForegroundColor Green
}
catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
finally {
    Pop-Location
}
