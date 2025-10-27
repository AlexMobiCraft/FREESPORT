# Скрипт запускает тесты Story 3.1.2 (команда import_catalog_from_1c)
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AdditionalPytestArgs = @()
)

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $scriptDirectory "run-tests-docker-local.ps1"

if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "Не найден основной скрипт запуска: $runnerPath"
}

$defaultPytestArgs = @(
    "tests/integration/test_management_commands/test_import_catalog_from_1c.py",
    "-v",
    "--migrations"
)

$pytestArgs = @($defaultPytestArgs + $AdditionalPytestArgs)

& $runnerPath -ComposeFile "docker/docker-compose.test.yml" -SkipBuild:$false -DockerContext "default" -KeepContainers:$false -ServiceName "backend" -PytestArgs $pytestArgs
