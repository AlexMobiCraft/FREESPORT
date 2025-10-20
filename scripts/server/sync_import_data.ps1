# Скрипт для копирования данных импорта 1С на сервер разработки FREESPORT

param(
    [string]$User = "alex",
    [string]$IP = "192.168.1.130",
    [string]$LocalDataPath = "data/import_1c",
    [string]$RemoteDataPath = "~/FREESPORT/data/import_1c",
    [string]$SshKeyPath = "C:\\Users\\38670\\.ssh\\id_ed25519"
)

$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$projectRoot = Split-Path -Path $scriptDirectory -Parent

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

# Функция преобразует путь на сервере в абсолютный вид
function Resolve-RemotePath {
    param(
        [string]$RemotePath,
        [string]$RemoteUser
    )

    if ($RemotePath -eq "~") {
        return "/home/$RemoteUser"
    }

    if ($RemotePath.StartsWith("~/")) {
        return "/home/$RemoteUser/" + $RemotePath.Substring(2)
    }

    return $RemotePath
}

# Функция создаёт директорию на удалённом сервере, если она отсутствует
function Ensure-RemoteDirectory {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$RemotePath
    )

    $escapedPath = $RemotePath.Replace("'", "'""'")
    $command = "mkdir -p '$escapedPath'"
    ssh "$ConnectionUser@$ConnectionHost" "bash -lc \"$command\"" | Out-Null
}

# Функция копирует каталог данных на сервер через SCP
function Copy-DirectoryToServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$LocalPath,
        [string]$RemotePath
    )

    if (-not (Test-Path -Path $LocalPath)) {
        throw "Локальный каталог не найден: $LocalPath"
    }

    $sourcePath = Join-Path -Path $LocalPath -ChildPath "."
    $destination = [string]::Format("{0}@{1}:{2}", $ConnectionUser, $ConnectionHost, $RemotePath)
    $scpArgs = @("-r", "-C", $sourcePath, $destination)
    & scp @scpArgs
}

Push-Location $projectRoot

try {
    Write-Host "=== Копирование файлов 1С на сервер ===" -ForegroundColor Cyan
    Start-SshAgentIfNeeded -KeyPath $SshKeyPath

    $absoluteLocalPath = if ([System.IO.Path]::IsPathRooted($LocalDataPath)) {
        $LocalDataPath
    } else {
        Join-Path -Path $projectRoot -ChildPath $LocalDataPath
    }

    $resolvedRemotePath = Resolve-RemotePath -RemotePath $RemoteDataPath -RemoteUser $User

    Write-Host "Подготовка директории на сервере..." -ForegroundColor Yellow
    Ensure-RemoteDirectory -ConnectionUser $User -ConnectionHost $IP -RemotePath $resolvedRemotePath

    Write-Host "Копирование файлов из '$absoluteLocalPath'..." -ForegroundColor Yellow
    Copy-DirectoryToServer -ConnectionUser $User -ConnectionHost $IP -LocalPath $absoluteLocalPath -RemotePath $resolvedRemotePath

    Write-Host "✓ Копирование завершено" -ForegroundColor Green
}
catch {
    Write-Host "✗ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
finally {
    Pop-Location
}
