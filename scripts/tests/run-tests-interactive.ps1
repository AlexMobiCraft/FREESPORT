# Интерактивный запуск тестовых сценариев FREESPORT Platform
# Скрипт предоставляет меню для выбора набора тестов и параметров pytest.
# Работает поверх run-tests-docker-local.ps1

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $scriptDirectory "run-tests-docker-local.ps1"

if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "Не найден основной скрипт запуска: $runnerPath"
}

$scenarios = @(
    [pscustomobject]@{
        Id = 1
        Title = "Story 3.1.3 — real catalog (8 тестов)"
        Description = "tests/integration/test_real_catalog_import.py"
        PytestArgs = @(
            "tests/integration/test_real_catalog_import.py",
            "-v",
            "--migrations"
        )
    },
    [pscustomobject]@{
        Id = 2
        Title = "Story 3.1.2 — import_catalog_from_1c"
        Description = "tests/integration/test_management_commands/test_import_catalog_from_1c.py"
        PytestArgs = @(
            "tests/integration/test_management_commands/test_import_catalog_from_1c.py",
            "-v",
            "--migrations"
        )
    },
    [pscustomobject]@{
        Id = 3
        Title = "Все backend тесты (pytest tests)"
        Description = "Полный прогон pytest по каталогу tests/"
        PytestArgs = @(
            "tests",
            "-v",
            "--migrations"
        )
    },
    [pscustomobject]@{
        Id = 4
        Title = "Произвольный путь/тест"
        Description = "Ручной ввод пути и дополнительных аргументов"
        PytestArgs = @()
    }
)

function Show-Menu {
    param(
        [pscustomobject[]]$Items
    )

    Write-Host "=== FREESPORT Test Runner ===" -ForegroundColor Cyan
    Write-Host "Выберите сценарий:" -ForegroundColor Yellow

    foreach ($item in $Items) {
        Write-Host ("{0}. {1}" -f $item.Id, $item.Title)
        if ($item.Description) {
            Write-Host ("   {0}" -f $item.Description) -ForegroundColor DarkGray
        }
    }

    Write-Host "0. Выход"
    Write-Host
}

function Read-ScenarioSelection {
    param(
        [pscustomobject[]]$Items
    )

    while ($true) {
        $inputValue = Read-Host "Введите номер сценария"
        if ($inputValue -eq "0") {
            return $null
        }

        if ($inputValue -as [int]) {
            $selected = $Items | Where-Object { $_.Id -eq [int]$inputValue }
            if ($selected) {
                return $selected
            }
        }

        Write-Host "Некорректный ввод. Попробуйте снова." -ForegroundColor Red
    }
}

function Read-CustomScenarioArgs {
    $path = Read-Host "Введите путь к тесту или директории (pytest target)"
    if (-not $path) {
        Write-Host "Путь обязателен." -ForegroundColor Red
        return Read-CustomScenarioArgs
    }

    $additional = Read-Host "Дополнительные аргументы pytest (через запятую или оставьте пустым)"

    $args = @($path)
    if ($additional) {
        $additional.Split(",") | ForEach-Object {
            $trimmed = $_.Trim()
            if ($trimmed) {
                $args += $trimmed
            }
        }
    }

    return $args
}

function Read-ExtraPytestArgs {
    $raw = Read-Host "Введите дополнительные аргументы pytest (через запятую) или оставьте пустым"
    $result = @()

    if ($raw) {
        $raw.Split(",") | ForEach-Object {
            $trimmed = $_.Trim()
            if ($trimmed) {
                $result += $trimmed
            }
        }
    }

    return $result
}

function Confirm-Run {
    param(
        [string[]]$SelectedArgs
    )

    Write-Host "Будут запущены pytest аргументы:" -ForegroundColor Yellow
    foreach ($arg in $SelectedArgs) {
        Write-Host " - $arg"
    }

    while ($true) {
        $answer = Read-Host "Продолжить? (y/n)"
        switch ($answer.ToLower()) {
            "y" { return $true }
            "n" { return $false }
            default { Write-Host "Введите 'y' или 'n'." -ForegroundColor Red }
        }
    }
}

function Invoke-TestScenario {
    param(
        [string[]]$PytestArgs
    )

    & $runnerPath -ComposeFile "docker/docker-compose.test.yml" -SkipBuild:$false -DockerContext "default" -KeepContainers:$false -ServiceName "backend" -PytestArgs $PytestArgs
}

while ($true) {
    Clear-Host
    Show-Menu -Items $scenarios
    $scenario = Read-ScenarioSelection -Items $scenarios

    if (-not $scenario) {
        Write-Host "Выход." -ForegroundColor Cyan
        break
    }

    $pytestArgs = @($scenario.PytestArgs)

    if ($scenario.Id -eq 4) {
        $pytestArgs = Read-CustomScenarioArgs
    }

    $extraArgs = Read-ExtraPytestArgs
    if ($extraArgs.Count -gt 0) {
        $pytestArgs = @($pytestArgs + $extraArgs)
    }

    if (-not $pytestArgs -or $pytestArgs.Count -eq 0) {
        Write-Host "Нечего запускать, возвращаемся в меню." -ForegroundColor Red
        Start-Sleep -Seconds 2
        continue
    }

    if (-not (Confirm-Run -SelectedArgs $pytestArgs)) {
        Write-Host "Отменено пользователем." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        continue
    }

    try {
        Invoke-TestScenario -PytestArgs $pytestArgs
    }
    catch {
        Write-Host "Ошибка выполнения: $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host
    Write-Host "Нажмите Enter для возврата в меню..." -ForegroundColor Yellow
    [void][System.Console]::ReadKey($true)
}
