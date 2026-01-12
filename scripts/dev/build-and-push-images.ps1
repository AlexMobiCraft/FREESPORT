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
    [string]$TagsJsonFile = "scripts/dev/last-release-tags.json",
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

function Load-TagsFromFile {
    param([string]$FilePath)
    if (-not (Test-Path $FilePath -PathType Leaf)) {
        throw "Файл с тегами '$FilePath' не найден. Невозможно продолжить."
    }
    Write-Log "Загрузка тегов из $FilePath..."
    $data = Get-Content -Raw -Path $FilePath | ConvertFrom-Json
    
    if ($null -ne $data.tag) {
        $env:BACKEND_TAG = $data.tag
        $env:FRONTEND_TAG = $data.tag
        Write-Log "Тег $($data.tag) загружен в переменные окружения."
    }
    else {
        throw "Не удалось найти 'tag' в файле $FilePath."
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
}
else {
    Write-Log "Пропуск генерации тегов. Проверка переменных..."
    if ([string]::IsNullOrWhiteSpace($env:BACKEND_TAG) -or [string]::IsNullOrWhiteSpace($env:FRONTEND_TAG)) {
        Write-Log "Одна или несколько переменных тегов не установлены. Загрузка из файла..."
        Load-TagsFromFile -FilePath $TagsJsonFile
    }
    else {
        Write-Log "Используются переменные из текущей сессии."
    }
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
