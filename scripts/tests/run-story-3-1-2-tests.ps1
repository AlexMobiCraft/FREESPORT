# Скрипт запускает тесты Epic 27 (VariantImportProcessor / import_products_from_1c)
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
    "tests/integration/test_variant_import.py",
    "-v",
    "--migrations"
)

$pytestArgs = @($defaultPytestArgs + $AdditionalPytestArgs)

& $runnerPath -ComposeFile "docker/docker-compose.test.yml" -SkipBuild:$false -DockerContext "default" -KeepContainers:$false -ServiceName "backend" -PytestArgs $pytestArgs
