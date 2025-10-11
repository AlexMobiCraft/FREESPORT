# Скрипт запускает тесты в локальном Docker окружении FREESPORT Platform

param(
    [string]$ComposeFile = "docker-compose.test.yml",
    [switch]$SkipBuild,
    [string]$DockerContext = "default",
    [switch]$KeepContainers,
    [string]$LogsDirectory = "logs/test-runs"
)

$script:TestExitCode = 1
$script:LogsSavedPath = $null

# Функция проверяет доступность Docker Engine на локальной машине.
function Test-DockerAvailability {
    param(
        [string]$Context
    )

    try {
        docker --context $Context info > $null 2>&1
    }
    catch {
        throw "Docker недоступен или не запущен."
    }
}

# Функция переключает активный Docker контекст на указанный.
function Set-DockerContext {
    param(
        [string]$Context
    )

    docker context inspect $Context > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker контекст '$Context' не найден."
    }

    docker context use $Context > $null 2>&1
}

# Функция возвращает абсолютный путь к файлу docker-compose.
function Resolve-ComposePath {
    param(
        [string]$PathValue,
        [string]$ProjectRoot
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        if (-not (Test-Path -LiteralPath $PathValue)) {
            throw "Файл compose не найден: $PathValue"
        }

        return (Resolve-Path -LiteralPath $PathValue).Path
    }

    $resolved = Join-Path -Path $ProjectRoot -ChildPath $PathValue

    if (-not (Test-Path -LiteralPath $resolved)) {
        throw "Файл compose не найден: $resolved"
    }

    return (Resolve-Path -LiteralPath $resolved).Path
}

# Функция останавливает и очищает предыдущие тестовые контейнеры.
function Clear-TestEnvironment {
    param(
        [string]$ComposePath,
        [string]$Context
    )

    & docker --context $Context compose -f $ComposePath down -v --remove-orphans > $null 2>&1
}

# Функция запускает docker compose и сохраняет код возврата тестового сервиса backend.
function Invoke-DockerComposeTests {
    param(
        [string]$ComposePath,
        [switch]$SkipBuild,
        [string]$Context
    )

    $arguments = @(
        "compose",
        "-f", $ComposePath,
        "up",
        "--abort-on-container-exit",
        "--exit-code-from", "backend"
    )

    if (-not $SkipBuild) {
        $arguments += "--build"
    }

    & docker --context $Context @arguments
    $script:TestExitCode = [int]$LASTEXITCODE
}

# Функция выгружает логи backend контейнера в указанный файл.
function Save-BackendLogs {
    param(
        [string]$ComposePath,
        [string]$Context,
        [string]$OutputFile
    )

    $destinationDirectory = Split-Path -Path $OutputFile -Parent
    if (-not (Test-Path -LiteralPath $destinationDirectory)) {
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    }

    docker --context $Context compose -f $ComposePath logs backend | Out-File -FilePath $OutputFile -Encoding UTF8
}

Write-Host "=== FREESPORT Local Docker Test Runner ===" -ForegroundColor Cyan
Write-Host

$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$projectRoot = Split-Path -Path $scriptDirectory -Parent
Push-Location -Path $projectRoot

$composePath = $null
try {
    Set-DockerContext -Context $DockerContext
    Test-DockerAvailability -Context $DockerContext
    $composePath = Resolve-ComposePath -PathValue $ComposeFile -ProjectRoot $projectRoot

    Clear-TestEnvironment -ComposePath $composePath -Context $DockerContext

    Write-Host "Запуск тестов. Это может занять несколько минут." -ForegroundColor Yellow
    Invoke-DockerComposeTests -ComposePath $composePath -SkipBuild:$SkipBuild -Context $DockerContext
}
catch {
    Write-Host "✗ Ошибка при выполнении: $($_.Exception.Message)" -ForegroundColor Red
    $script:TestExitCode = 1
}
finally {
    if ($composePath -and $script:TestExitCode -ne 0) {
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $logFileName = "backend-$timestamp.log"
        $logPath = Join-Path -Path $projectRoot -ChildPath (Join-Path -Path $LogsDirectory -ChildPath $logFileName)

        try {
            Save-BackendLogs -ComposePath $composePath -Context $DockerContext -OutputFile $logPath
            $script:LogsSavedPath = $logPath
        }
        catch {
            Write-Host "Failed to save backend logs before cleanup: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    if ($composePath -and (-not $KeepContainers)) {
        Clear-TestEnvironment -ComposePath $composePath -Context $DockerContext
    }
    Pop-Location
}

Write-Host
if ($script:TestExitCode -eq 0) {
    Write-Host "=== TESTS PASSED SUCCESSFULLY ===" -ForegroundColor Green
}
else {
    Write-Host "=== TESTS FAILED ===" -ForegroundColor Red

    if ($script:LogsSavedPath) {
        Write-Host "Backend logs saved to $script:LogsSavedPath" -ForegroundColor Yellow
    }
    else {
        Write-Host "Backend logs were not saved. Use -KeepContainers to investigate manually." -ForegroundColor Yellow
    }

    if ($KeepContainers) {
        Write-Host "Containers are still running for investigation." -ForegroundColor Yellow
    }
    elseif ($composePath) {
        Write-Host "Containers have been removed after log collection." -ForegroundColor Yellow
    }
}

exit $script:TestExitCode
