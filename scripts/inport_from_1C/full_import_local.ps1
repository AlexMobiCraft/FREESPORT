# =============================================================================
# FREESPORT: Full Import from 1C (Local Docker on Windows)
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

if ($Help) {
    Write-Host "=== FREESPORT: Local Import from 1C ==="
    Write-Host ""
    Write-Host "Usage: .\full_import_local.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -DryRun         Test run without DB changes"
    Write-Host "  -SkipBackup     Skip creating backup"
    Write-Host "  -SkipImages     Skip importing images"
    Write-Host "  -SkipCustomers  Skip importing customers"
    Write-Host "  -ClearExisting  Clear data before import (WARNING!)"
    Write-Host "  -ComposeFile    Path to docker-compose file (default: docker/docker-compose.yml)"
    Write-Host "  -DataDir        Path to data inside container (default: /app/data/import_1c)"
    Write-Host "  -Help           Show this help"
    exit 0
}

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Success($msg) { Write-Host "[SUCCESS] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARNING] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

function Invoke-DockerCommand {
    param([string]$Command)
    Write-Info "Executing: $Command"
    
    $fullCommand = "docker compose -f $ComposeFile exec -T backend $Command"
    Invoke-Expression $fullCommand
    
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Command failed with error code: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

function Invoke-DjangoCommand {
    param([string]$ManageCommand)
    Invoke-DockerCommand "python manage.py $ManageCommand"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

Push-Location $ProjectRoot

# =============================================================================
# Script Start
# =============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  FREESPORT: Full Import from 1C (Local Docker)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Arg construction
$DryRunArg = ""
if ($DryRun) { $DryRunArg = "--dry-run" }

$SkipBackupArg = ""
if ($SkipBackup) { $SkipBackupArg = "--skip-backup" }

$SkipImagesArg = ""
if ($SkipImages) { $SkipImagesArg = "--skip-images" }

$ClearExistingArg = ""
if ($ClearExisting) { $ClearExistingArg = "--clear-existing" }

# Print parameters
Write-Info "Import Parameters:"
Write-Host "   - Compose file: $ComposeFile"
Write-Host "   - Data directory: $DataDir"
Write-Host "   - Dry run: $DryRun"
Write-Host "   - Skip backup: $SkipBackup"
Write-Host "   - Skip images: $SkipImages"
Write-Host "   - Skip customers: $SkipCustomers"
Write-Host "   - Clear existing: $ClearExisting"
Write-Host ""

# Confirmation for real import
if ($DryRun -eq $false) {
    Write-Warn "This is a REAL import! Data will be changed."
    $confirm = Read-Host "Continue? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Info "Import cancelled"
        Pop-Location
        exit 0
    }
}

$StartTime = Get-Date

# =============================================================================
# Check Docker
# =============================================================================

Write-Info "Checking Docker..."

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Err "Docker not found in PATH"
    exit 1
}

    # Temporarily allow stderr for docker info warnings
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue" 
    $dockerInfo = docker info 2>&1
    $ErrorActionPreference = $oldPreference

    if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker daemon is not running"
    exit 1
}
Write-Success "Docker is running"

if (-not (Test-Path $ComposeFile)) {
    Write-Err "Compose file not found: $ComposeFile"
    exit 1
}
Write-Success "Compose file found: $ComposeFile"

Write-Info "Checking Docker containers..."
$backendContainer = docker compose -f $ComposeFile ps --format '{{.Name}}' 2>&1 | Where-Object { $_ -match "backend" }

if (-not $backendContainer) {
    Write-Warn "Backend container not running. Starting..."
    docker compose -f $ComposeFile up -d --wait
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to start containers"
        exit 1
    }
    Write-Success "Containers started"
} else {
    Write-Success "Backend container is running: $backendContainer"
}

# =============================================================================
# STEP 1: Import Attributes
# =============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Info "STEP 1/3: Importing product attributes..."
Write-Host "============================================================" -ForegroundColor Cyan

$AttrArgs = "--data-dir $DataDir $DryRunArg".Trim() -replace '\s+', ' '
Invoke-DjangoCommand "import_attributes $AttrArgs"
Write-Success "Attributes imported"

# =============================================================================
# STEP 2: Import Catalog
# =============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Info "STEP 2/3: Importing product catalog..."
Write-Host "============================================================" -ForegroundColor Cyan

$CatalogArgs = "--data-dir $DataDir $DryRunArg $SkipBackupArg $SkipImagesArg $ClearExistingArg".Trim() -replace '\s+', ' '
Invoke-DjangoCommand "import_products_from_1c $CatalogArgs"
Write-Success "Catalog imported"

# =============================================================================
# STEP 3: Import Customers
# =============================================================================

if ($SkipCustomers -eq $false) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Info "STEP 3/3: Importing customers..."
    Write-Host "============================================================" -ForegroundColor Cyan
    
    $CustomerArgs = "--data-dir $DataDir $DryRunArg".Trim() -replace '\s+', ' '
    Invoke-DjangoCommand "import_customers_from_1c $CustomerArgs"
    Write-Success "Customers imported"
} else {
    Write-Info "STEP 3/3: Customer import skipped (-SkipCustomers)"
}

# =============================================================================
# Completion
# =============================================================================

$EndTime = Get-Date
$Duration = $EndTime - $StartTime
$Minutes = [math]::Floor($Duration.TotalMinutes)
$Seconds = $Duration.Seconds

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Success "IMPORT COMPLETED SUCCESSFULLY!"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Execution time: ${Minutes}m ${Seconds}s"
Write-Host ""

if ($DryRun) {
    Write-Warn "This was a DRY RUN. Data was NOT changed."
    Write-Info "For real import, run without -DryRun"
}

Write-Host ""

Pop-Location
