# =============================================================================
# FREESPORT: Полный импорт данных из 1С (локальный Docker на Windows)
# =============================================================================
# Использование:
#   .\full_import_local.ps1                    # Полный импорт
#   .\full_import_local.ps1 -DryRun            # Тестовый запуск
#   .\full_import_local.ps1 -SkipBackup        # Без backup
#   .\full_import_local.ps1 -SkipImages        # Без изображений
# =============================================================================

param(
    [switch]$DryRun,
    [switch]$SkipBackup,
    [switch]$SkipImages,
    [switch]$SkipCustomers,
    [switch]$ClearExisting,
    [string]$ComposeFile = "docker/docker-compose.yml",
    [string]$DataDir = "/app/data/import_1c",
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# =============================================================================
# Справка
# =============================================================================

if ($Help) {
    Write-Host @"
=== FREESPORT: Локальный импорт данных из 1С ===

Использование: .\full_import_local.ps1 [опции]

Опции:
  -DryRun         Тестовый запуск без записи в БД
  -SkipBackup     Пропустить создание backup
  -SkipImages     Пропустить импорт изображений
  -SkipCustomers  Пропустить импорт клиентов
  -ClearExisting  Очистить данные перед импортом (ОСТОРОЖНО!)
  -ComposeFile    Путь к docker-compose файлу (по умолчанию: docker/docker-compose.yml)
  -DataDir        Путь к данным внутри контейнера (по умолчанию: /app/data/import_1c)
  -Help           Показать эту справку

Примеры:
  .\full_import_local.ps1                              # Полный импорт
  .\full_import_local.ps1 -DryRun                      # Тестовый прогон
  .\full_import_local.ps1 -SkipBackup -SkipImages      # Быстрый импорт
"@
    exit 0
}

# =============================================================================
# Вспомогательные функции
# =============================================================================

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Success($msg) { Write-Host "[SUCCESS] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARNING] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

function Invoke-DockerCommand {
    param([string]$Command)
    Write-Info "Выполнение: $Command"
    
    $fullCommand = "docker compose -f $ComposeFile exec -T backend $Command"
    Invoke-Expression $fullCommand
    
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Команда завершилась с ошибкой: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

function Invoke-DjangoCommand {
    param([string]$ManageCommand)
    Invoke-DockerCommand "python manage.py $ManageCommand"
}

# =============================================================================
# Определение корня проекта
# =============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# Переходим в корень проекта
Push-Location $ProjectRoot

try {
    # =============================================================================
    # Начало скрипта
    # =============================================================================

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  FREESPORT: Полный импорт данных из 1С (Local Docker)" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # Формирование аргументов
    $DryRunArg = if ($DryRun) { "--dry-run" } else { "" }
    $SkipBackupArg = if ($SkipBackup) { "--skip-backup" } else { "" }
    $SkipImagesArg = if ($SkipImages) { "--skip-images" } else { "" }
    $ClearExistingArg = if ($ClearExisting) { "--clear-existing" } else { "" }

    # Вывод параметров
    Write-Info "Параметры импорта:"
    Write-Host "   - Compose файл: $ComposeFile"
    Write-Host "   - Директория данных: $DataDir"
    Write-Host "   - Dry run: $($DryRun.ToString())"
    Write-Host "   - Skip backup: $($SkipBackup.ToString())"
    Write-Host "   - Skip images: $($SkipImages.ToString())"
    Write-Host "   - Skip customers: $($SkipCustomers.ToString())"
    Write-Host "   - Clear existing: $($ClearExisting.ToString())"
    Write-Host ""

    # Подтверждение для реального импорта
    if (-not $DryRun) {
        Write-Warn "Это РЕАЛЬНЫЙ импорт! Данные будут изменены."
        $confirm = Read-Host "Продолжить? (yes/no)"
        if ($confirm -ne "yes") {
            Write-Info "Импорт отменён"
            exit 0
        }
    }

    $StartTime = Get-Date

    # =============================================================================
    # Проверка Docker
    # =============================================================================

    Write-Info "Проверка Docker..."

    # Проверяем наличие docker
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        Write-Err "Docker не найден в PATH"
        Write-Info "Установите Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    }

    # Проверяем, запущен ли Docker daemon
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Docker daemon не запущен"
        Write-Info "Запустите Docker Desktop и дождитесь инициализации"
        exit 1
    }
    Write-Success "Docker работает"

    # Проверка compose файла
    if (-not (Test-Path $ComposeFile)) {
        Write-Err "Compose файл не найден: $ComposeFile"
        exit 1
    }
    Write-Success "Compose файл найден: $ComposeFile"

    # Проверка Docker контейнеров
    Write-Info "Проверка Docker контейнеров..."
    $backendContainer = docker compose -f $ComposeFile ps --format "{{.Name}}" 2>&1 | Where-Object { $_ -match "backend" }
    
    if (-not $backendContainer) {
        Write-Warn "Backend контейнер не запущен. Запускаем..."
        docker compose -f $ComposeFile up -d --wait
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Не удалось запустить контейнеры"
            exit 1
        }
        Write-Success "Контейнеры запущены"
    } else {
        Write-Success "Backend контейнер работает: $backendContainer"
    }

    # =============================================================================
    # ШАГ 1: Импорт атрибутов
    # =============================================================================

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Info "ШАГ 1/3: Импорт атрибутов товаров..."
    Write-Host "============================================================" -ForegroundColor Cyan

    $AttrArgs = "--data-dir $DataDir $DryRunArg".Trim() -replace '\s+', ' '
    Invoke-DjangoCommand "import_attributes $AttrArgs"
    Write-Success "Атрибуты импортированы"

    # =============================================================================
    # ШАГ 2: Импорт каталога
    # =============================================================================

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Info "ШАГ 2/3: Импорт каталога товаров..."
    Write-Host "============================================================" -ForegroundColor Cyan

    $CatalogArgs = "--data-dir $DataDir $DryRunArg $SkipBackupArg $SkipImagesArg $ClearExistingArg".Trim() -replace '\s+', ' '
    Invoke-DjangoCommand "import_products_from_1c $CatalogArgs"
    Write-Success "Каталог импортирован"

    # =============================================================================
    # ШАГ 3: Импорт клиентов
    # =============================================================================

    if (-not $SkipCustomers) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Info "ШАГ 3/3: Импорт клиентов..."
        Write-Host "============================================================" -ForegroundColor Cyan
        
        $CustomerArgs = "--data-dir $DataDir $DryRunArg".Trim() -replace '\s+', ' '
        Invoke-DjangoCommand "import_customers_from_1c $CustomerArgs"
        Write-Success "Клиенты импортированы"
    } else {
        Write-Info "ШАГ 3/3: Импорт клиентов пропущен (-SkipCustomers)"
    }

    # =============================================================================
    # Завершение
    # =============================================================================

    $EndTime = Get-Date
    $Duration = $EndTime - $StartTime
    $Minutes = [math]::Floor($Duration.TotalMinutes)
    $Seconds = $Duration.Seconds

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Success "ИМПОРТ ЗАВЕРШЁН УСПЕШНО!"
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Время выполнения: ${Minutes}м ${Seconds}с"
    Write-Host ""

    if ($DryRun) {
        Write-Warn "Это был тестовый запуск. Данные НЕ были изменены."
        Write-Info "Для реального импорта запустите без -DryRun"
    }

    Write-Host ""

} finally {
    # Возвращаемся в исходную директорию
    Pop-Location
}
