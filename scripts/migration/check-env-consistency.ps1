# Скрипт проверки согласованности виртуальных окружений
# Сравнивает версии пакетов в локальном venv и Docker

Write-Host "=== Проверка согласованности виртуальных окружений ===" -ForegroundColor Cyan
Write-Host

# Переход в корень проекта
$projectRoot = (Split-Path -Path $PSScriptRoot -Parent) | Split-Path -Parent
Set-Location -Path $projectRoot
Write-Host "Рабочая директория: $projectRoot" -ForegroundColor Yellow
Write-Host

# Проверка наличия окружений
$localVenvExists = Test-Path -Path "backend/venv"
$dockerAvailable = $false

try {
    docker info > $null 2>&1
    $dockerAvailable = $true
} catch {
    Write-Host "⚠ Docker недоступен, проверка только локального окружения" -ForegroundColor Yellow
}

Write-Host "Доступные окружения:" -ForegroundColor Cyan
if ($localVenvExists) {
    Write-Host "  ✓ Локальное venv: backend/venv" -ForegroundColor Green
} else {
    Write-Host "  ✗ Локальное venv: не найден" -ForegroundColor Red
}

if ($dockerAvailable) {
    Write-Host "  ✓ Docker: доступен" -ForegroundColor Green
} else {
    Write-Host "  ✗ Docker: недоступен" -ForegroundColor Red
}

Write-Host

# Ключевые пакеты для проверки
$packages = @(
    @{ name = "black"; expected = "23.11.0" },
    @{ name = "isort"; expected = "5.12.0" },
    @{ name = "flake8"; expected = "6.1.0" },
    @{ name = "mypy"; expected = "1.7.1" },
    @{ name = "pytest"; expected = "7.4.3" }
)

# Проверка локального окружения
if ($localVenvExists) {
    Write-Host "=== Проверка локального виртуального окружения ===" -ForegroundColor Cyan
    
    $localIssues = 0
    foreach ($pkg in $packages) {
        $pkgPath = "backend/venv/Scripts/$($pkg.name).exe"
        if (Test-Path -Path $pkgPath) {
            try {
                $version = & $pkgPath --version 2>&1
                if ($version -match $pkg.expected) {
                    Write-Host "  ✓ $($pkg.name): $version" -ForegroundColor Green
                } else {
                    Write-Host "  ⚠ $($pkg.name): $version (ожидается $($pkg.expected))" -ForegroundColor Yellow
                    $localIssues++
                }
            } catch {
                Write-Host "  ✗ $($pkg.name): ошибка получения версии" -ForegroundColor Red
                $localIssues++
            }
        } else {
            Write-Host "  ✗ $($pkg.name): не установлен" -ForegroundColor Red
            $localIssues++
        }
    }
    
    if ($localIssues -eq 0) {
        Write-Host "✓ Локальное окружение корректно" -ForegroundColor Green
    } else {
        Write-Host "⚠ Локальное окружение имеет $localIssues проблем" -ForegroundColor Yellow
    }
    Write-Host
}

# Проверка Docker окружения
if ($dockerAvailable) {
    Write-Host "=== Проверка Docker окружения ===" -ForegroundColor Cyan
    
    # Проверка наличия образа
    $imageExists = $false
    try {
        $imageInfo = docker images freesport-dev-tools --format "table {{.Repository}}:{{.Tag}}" 2>&1
        if ($imageInfo -match "freesport-dev-tools") {
            $imageExists = $true
            Write-Host "  ✓ Образ freesport-dev-tools найден" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Образ freesport-dev-tools не найден" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ✗ Ошибка проверки Docker образа" -ForegroundColor Red
    }
    
    if ($imageExists) {
        $dockerIssues = 0
        foreach ($pkg in $packages) {
            try {
                $version = docker run --rm freesport-dev-tools $pkg.name --version 2>&1
                if ($version -match $pkg.expected) {
                    Write-Host "  ✓ $($pkg.name): $version" -ForegroundColor Green
                } else {
                    Write-Host "  ⚠ $($pkg.name): $version (ожидается $($pkg.expected))" -ForegroundColor Yellow
                    $dockerIssues++
                }
            } catch {
                Write-Host "  ✗ $($pkg.name): ошибка получения версии" -ForegroundColor Red
                $dockerIssues++
            }
        }
        
        if ($dockerIssues -eq 0) {
            Write-Host "✓ Docker окружение корректно" -ForegroundColor Green
        } else {
            Write-Host "⚠ Docker окружение имеет $dockerIssues проблем" -ForegroundColor Yellow
        }
    }
    Write-Host
}

# Сравнение с requirements.txt
Write-Host "=== Проверка соответствия requirements.txt ===" -ForegroundColor Cyan

if (Test-Path -Path "backend/requirements.txt") {
    $requirementsContent = Get-Content -Path "backend/requirements.txt"
    $reqIssues = 0
    
    foreach ($pkg in $packages) {
        $reqLine = $requirementsContent | Where-Object { $_ -match "^$($pkg.name)==" }
        if ($reqLine) {
            if ($reqLine -match "==$($pkg.expected)") {
                Write-Host "  ✓ $($pkg.name): $($pkg.expected) в requirements.txt" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ $($pkg.name): версия в requirements.txt отличается" -ForegroundColor Yellow
                $reqIssues++
            }
        } else {
            Write-Host "  ✗ $($pkg.name): не найден в requirements.txt" -ForegroundColor Red
            $reqIssues++
        }
    }
    
    if ($reqIssues -eq 0) {
        Write-Host "✓ requirements.txt корректен" -ForegroundColor Green
    } else {
        Write-Host "⚠ requirements.txt имеет $reqIssues проблем" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ requirements.txt не найден" -ForegroundColor Red
}

Write-Host

# Рекомендации
Write-Host "=== Рекомендации ===" -ForegroundColor Cyan

if (-not $localVenvExists) {
    Write-Host "• Создайте локальное виртуальное окружение:" -ForegroundColor Yellow
    Write-Host "  cd backend && python -m venv venv" -ForegroundColor Gray
    Write-Host "  venv\Scripts\activate && pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host
}

if ($dockerAvailable -and -not $imageExists) {
    Write-Host "• Соберите Docker образ для утилит:" -ForegroundColor Yellow
    Write-Host "  docker build -f docker/Dockerfile.dev-tools -t freesport-dev-tools ./backend" -ForegroundColor Gray
    Write-Host
}

if ($localIssues -gt 0 -or $dockerIssues -gt 0 -or $reqIssues -gt 0) {
    Write-Host "• Для исправления версий выполните:" -ForegroundColor Yellow
    Write-Host "  # Локальное окружение" -ForegroundColor Gray
    Write-Host "  cd backend && venv\Scripts\activate" -ForegroundColor Gray
    Write-Host "  pip install black==23.11.0 isort==5.12.0 flake8==6.1.0 mypy==1.7.1 pytest==7.4.3" -ForegroundColor Gray
    Write-Host
    Write-Host "  # Docker окружение" -ForegroundColor Gray
    Write-Host "  docker build -f docker/Dockerfile.dev-tools -t freesport-dev-tools ./backend" -ForegroundColor Gray
    Write-Host
}

Write-Host "=== Проверка завершена ===" -ForegroundColor Green