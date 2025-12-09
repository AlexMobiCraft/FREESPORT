# =============================================================================
# FREESPORT: Полный импорт данных из 1С (через SSH на production)
# =============================================================================
# Использование:
#   .\full_import_remote.ps1                    # Полный импорт
#   .\full_import_remote.ps1 -DryRun            # Тестовый запуск
#   .\full_import_remote.ps1 -SkipBackup        # Без backup
#   .\full_import_remote.ps1 -SkipImages        # Без изображений
# =============================================================================

param(
    [switch]$DryRun,
    [switch]$SkipBackup,
    [switch]$SkipImages,
    [switch]$SkipCustomers,
    [switch]$ClearExisting,
    [switch]$Help
)

# Конфигурация SSH
$SSH_HOST = "freesport-server"
$SSH_USER = "root"
$PROJECT_PATH = "/home/freesport/freesport"
$DATA_DIR = "/app/data/import_1c"

if ($Help) {
    Write-Host @"
Использование: .\full_import_remote.ps1 [опции]

Опции:
  -DryRun         Тестовый запуск без записи в БД
  -SkipBackup     Пропустить создание backup
  -SkipImages     Пропустить импорт изображений
  -SkipCustomers  Пропустить импорт клиентов
  -ClearExisting  Очистить данные перед импортом (ОСТОРОЖНО!)
  -Help           Показать эту справку
"@
    exit 0
}

# Функции
function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Success($msg) { Write-Host "[SUCCESS] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARNING] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

function Invoke-RemoteCommand {
    param([string]$Command)
    Write-Info "Выполнение: $Command"
    ssh "${SSH_USER}@${SSH_HOST}" "cd $PROJECT_PATH && $Command"
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Команда завершилась с ошибкой: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

function Invoke-DjangoCommand {
    param([string]$ManageCommand)
    $dockerCmd = "docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T backend python manage.py $ManageCommand"
    Invoke-RemoteCommand $dockerCmd
}

# =============================================================================
# Начало скрипта
# =============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  FREESPORT: Полный импорт данных из 1С (Remote)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Формирование аргументов
$DryRunArg = if ($DryRun) { "--dry-run" } else { "" }
$SkipBackupArg = if ($SkipBackup) { "--skip-backup" } else { "" }
$SkipImagesArg = if ($SkipImages) { "--skip-images" } else { "" }
$ClearExistingArg = if ($ClearExisting) { "--clear-existing" } else { "" }

# Вывод параметров
Write-Info "Параметры импорта:"
Write-Host "   - Сервер: ${SSH_USER}@${SSH_HOST}"
Write-Host "   - Директория данных: $DATA_DIR"
Write-Host "   - Dry run: $($DryRun.ToString())"
Write-Host "   - Skip backup: $($SkipBackup.ToString())"
Write-Host "   - Skip images: $($SkipImages.ToString())"
Write-Host "   - Skip customers: $($SkipCustomers.ToString())"
Write-Host "   - Clear existing: $($ClearExisting.ToString())"
Write-Host ""

if (-not $DryRun) {
    Write-Warn "Это РЕАЛЬНЫЙ импорт! Данные будут изменены."
    $confirm = Read-Host "Продолжить? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Info "Импорт отменён"
        exit 0
    }
}

$StartTime = Get-Date

# Проверка SSH подключения
Write-Info "Проверка SSH подключения..."
try {
    ssh -o ConnectTimeout=5 "${SSH_USER}@${SSH_HOST}" "echo 'SSH OK'" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "SSH failed" }
    Write-Success "SSH подключение успешно"
} catch {
    Write-Err "Не удалось подключиться к серверу"
    Write-Info "Проверьте настройки SSH в ~/.ssh/config или запустите scripts/server/setup_ssh.ps1"
    exit 1
}

# Проверка Docker контейнеров
Write-Info "Проверка Docker контейнеров на сервере..."
Invoke-RemoteCommand "docker compose --env-file .env.prod -f docker/docker-compose.prod.yml ps | grep backend"

# =============================================================================
# ШАГ 1: Импорт атрибутов
# =============================================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Info "ШАГ 1/3: Импорт атрибутов товаров..."
Write-Host "============================================================" -ForegroundColor Cyan

Invoke-DjangoCommand "import_attributes --data-dir $DATA_DIR $DryRunArg"
Write-Success "Атрибуты импортированы"

# =============================================================================
# ШАГ 2: Импорт каталога
# =============================================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Info "ШАГ 2/3: Импорт каталога товаров..."
Write-Host "============================================================" -ForegroundColor Cyan

$CatalogArgs = "--data-dir $DATA_DIR $DryRunArg $SkipBackupArg $SkipImagesArg $ClearExistingArg".Trim() -replace '\s+', ' '
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
    
    Invoke-DjangoCommand "import_customers_from_1c --data-dir $DATA_DIR $DryRunArg"
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
