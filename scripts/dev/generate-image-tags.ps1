<#
.SYNOPSIS
    Генерация и сохранение Docker-тегов для backend и frontend.
.DESCRIPTION
    Скрипт формирует теги в формате vYYYYMMDD-HHmm (или пользовательский),
    сохраняет их в локальный файл и экспортирует переменные окружения текущей сессии.
#>

param(
    [string]$Prefix = "v",
    [string]$CustomTag,
    [string]$OutputFile = "scripts\\dev\\last-release-tags.json",
    [string]$EnvFile = ".env.prod",
    [string]$ChangeLogFile = "docs\\ci-cd\\change-log.md",
    [switch]$Overwrite
)

# Логгирование сообщений в консоль
function Write-Log {
    param([string]$Message)
    Write-Host "[generate-tags] $Message"
}

# Обновление (или добавление) значения переменной в .env файле
function Set-EnvVariable {
    param(
        [string]$FilePath,
        [string]$Key,
        [string]$Value
    )

    if (-not (Test-Path $FilePath -PathType Leaf)) {
        Write-Log "Файл $FilePath не найден. Создаю новый."
        New-Item -ItemType File -Path $FilePath -Force | Out-Null
    }

    $lines = Get-Content -Path $FilePath
    $pattern = "^{0}=" -f [regex]::Escape($Key)
    $replaced = $false

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$Value"
            $replaced = $true
            break
        }
    }

    if (-not $replaced) {
        $lines += "$Key=$Value"
    }

    Set-Content -Path $FilePath -Value $lines -Encoding UTF8
}

# Добавление записи в markdown-журнал изменений CI/CD
function Append-ChangeLogEntry {
    param(
        [string]$FilePath,
        [string]$Tag,
        [string]$BackendImage,
        [string]$FrontendImage
    )

    $directory = Split-Path $FilePath -Parent
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    if (-not (Test-Path $FilePath -PathType Leaf)) {
        "# CI/CD Change Log`n" | Set-Content -Path $FilePath -Encoding UTF8
    }

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $entry = "`n## $timestamp`n- TAG=$Tag`n- BACKEND_IMAGE=$BackendImage`n- FRONTEND_IMAGE=$FrontendImage`n"
    Add-Content -Path $FilePath -Value $entry -Encoding UTF8
}

# Формирование метки
if ($CustomTag) {
    $tag = $CustomTag
    Write-Log "Используется пользовательский тег: $tag"
} else {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmm'
    $tag = "$Prefix$timestamp"
    Write-Log "Сгенерирован тег: $tag"
}

$backendTag = "ghcr.io/alexmobicraft/freesport/backend:$tag"
$frontendTag = "ghcr.io/alexmobicraft/freesport/frontend:$tag"

Write-Log "Backend tag:  $backendTag"
Write-Log "Frontend tag: $frontendTag"

# Экспорт переменных для текущей сессии
$env:BACKEND_TAG = $tag
$env:FRONTEND_TAG = $tag
$env:BACKEND_IMAGE = $backendTag
$env:FRONTEND_IMAGE = $frontendTag

Write-Log "Переменные окружения BACKEND_TAG/FRONTEND_TAG обновлены"

# Подготовка данных для файла
$data = [ordered]@{
    generated_at = (Get-Date).ToString('s')
    tag = $tag
    backend_image = $backendTag
    frontend_image = $frontendTag
}

if (Test-Path $OutputFile -PathType Leaf -and -not $Overwrite) {
    Write-Log "Файл $OutputFile уже существует. Для перезаписи используйте -Overwrite"
} else {
    $directory = Split-Path $OutputFile -Parent
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $data | ConvertTo-Json -Depth 2 | Set-Content -Path $OutputFile -Encoding UTF8
    Write-Log "Теги сохранены в $OutputFile"
}

Set-EnvVariable -FilePath $EnvFile -Key "BACKEND_IMAGE" -Value $backendTag
Set-EnvVariable -FilePath $EnvFile -Key "FRONTEND_IMAGE" -Value $frontendTag
Write-Log "Обновлён файл $EnvFile значениями образов."

Append-ChangeLogEntry -FilePath $ChangeLogFile -Tag $tag -BackendImage $backendTag -FrontendImage $frontendTag
Write-Log "Запись о релизе добавлена в $ChangeLogFile."

Write-Log "Готово. Используйте переменные BACKEND_IMAGE и FRONTEND_IMAGE при сборке."
