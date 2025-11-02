<#
.SYNOPSIS
    Универсальная сборка и публикация Docker-образов FREESPORT.
.DESCRIPTION
    Скрипт вызывает generate-image-tags.ps1 для получения тега версии,
    затем собирает и пушит образы backend и frontend или конкретного сервиса.
#>

param(
    [ValidateSet("backend", "frontend", "all")]
    [string]$Target = "all",
    [string]$Registry = "ghcr.io",
    [string]$RepositoryPrefix = "alexmobicraft/freesport",
    [string]$TagsScript = "scripts/dev/generate-image-tags.ps1",
    [switch]$SkipTagGeneration
)

function Write-Log {
    param([string]$Message)
    Write-Host "[build-images] $Message"
}

function Invoke-TagScript {
    param([string]$ScriptPath)
    if (-not (Test-Path $ScriptPath -PathType Leaf)) {
        throw "Скрипт генерации тегов не найден: $ScriptPath"
    }

    Write-Log "Запуск $ScriptPath для генерации тегов..."
    & $ScriptPath
}

function Ensure-Tag {
    param([string]$TagValue, [string]$Name)
    if ([string]::IsNullOrWhiteSpace($TagValue)) {
        throw "Переменная окружения $Name не установлена. Запустите генерацию тегов."
    }
}

function Build-And-PushBackend {
    Ensure-Tag -TagValue $env:BACKEND_TAG -Name "BACKEND_TAG"
    $image = "${Registry}/${RepositoryPrefix}/backend:${env:BACKEND_TAG}"
    Write-Log "Сборка backend из backend/Dockerfile"
    docker build --platform linux/amd64 -t $image -f backend/Dockerfile backend
    Write-Log "Publish backend -> $image"
    docker push $image
}

function Build-And-PushFrontend {
    Ensure-Tag -TagValue $env:FRONTEND_TAG -Name "FRONTEND_TAG"
    $image = "${Registry}/${RepositoryPrefix}/frontend:${env:FRONTEND_TAG}"
    Write-Log "Сборка frontend из frontend/Dockerfile"
    docker build --platform linux/amd64 -t $image -f frontend/Dockerfile frontend
    Write-Log "Publish frontend -> $image"
    docker push $image
}

if (-not $SkipTagGeneration) {
    Invoke-TagScript -ScriptPath $TagsScript
} else {
    Write-Log "Пропуск генерации тегов (используем текущие переменные)."
}

switch ($Target) {
    "backend" {
        Build-And-PushBackend
    }
    "frontend" {
        Build-And-PushFrontend
    }
    default {
        Build-And-PushBackend
        Build-And-PushFrontend
    }
}

Write-Log "Сборка и публикация завершены."
