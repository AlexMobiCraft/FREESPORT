# Скрипт для запуска тестов через Docker Compose
# FREESPORT Platform - Test Runner

param(
    [string]$DockerContext = "freesport-remote",
    [string]$ComposeFile = "docker-compose.test.yml"
)

$script:TestRunExitCode = 1

# Функция проверяет доступность Docker в указанном контексте
function Test-DockerConnection {
    param(
        [string]$Context
    )

    Write-Host "Проверка Docker (контекст '$Context')..." -ForegroundColor Yellow
    docker --context $Context ps | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Не удалось подключиться к Docker контексту '$Context'." -ForegroundColor Red
        throw "Docker недоступен"
    }

    Write-Host "✓ Docker доступен" -ForegroundColor Green
}

# Функция останавливает и удаляет предыдущие тестовые контейнеры
function Cleanup-PreviousRun {
    param(
        [string]$Context,
        [string]$ComposeFile
    )
    Write-Host ""
    Write-Host "Очистка предыдущих тестовых контейнеров..." -ForegroundColor Yellow
    & docker --context $Context compose -f $ComposeFile down -v --remove-orphans 2>$null
}

# Функция запускает docker compose и возвращает код возврата тестов
function Run-Tests {
    param(
        [string]$Context,
        [string]$ComposeFile
    )

    Write-Host "Запуск тестов..." -ForegroundColor Yellow
    Write-Host "Это может занять несколько минут при первом запуске (сборка образа)" -ForegroundColor Gray
    Write-Host ""

    & docker --context $Context compose -f $ComposeFile up --build --abort-on-container-exit
    $script:TestRunExitCode = [int]$LASTEXITCODE
}

# Функция выполняет финальную очистку тестовых контейнеров
function Finalize-Cleanup {
    param(
        [string]$Context,
        [string]$ComposeFile
    )

    Write-Host ""
    Write-Host "Очистка тестовых контейнеров..." -ForegroundColor Yellow
    & docker --context $Context compose -f $ComposeFile down -v --remove-orphans | Out-Null
}

Write-Host "=== FREESPORT Test Runner ===" -ForegroundColor Cyan
Write-Host ""

$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
Push-Location $scriptDirectory

try {
    $exitCode = 1

    Test-DockerConnection -Context $DockerContext
    Cleanup-PreviousRun -Context $DockerContext -ComposeFile $ComposeFile
    Run-Tests -Context $DockerContext -ComposeFile $ComposeFile
    $exitCode = [int]$script:TestRunExitCode
}
catch {
    Write-Host "✗ Ошибка при выполнении тестов: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}
finally {
    Finalize-Cleanup -Context $DockerContext -ComposeFile $ComposeFile
    Pop-Location
}

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "=== ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО ===" -ForegroundColor Green
} else {
    Write-Host "=== ТЕСТЫ ЗАВЕРШИЛИСЬ С ОШИБКАМИ ===" -ForegroundColor Red
}

exit $exitCode
