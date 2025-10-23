# Скрипт для импорта XML-файлов в базу данных напрямую на сервере

param(
    [string]$ServerIP = "5.35.124.149",
    [string]$User = "root",
    [string]$RemoteDataPath = "/home/freesport/freesport/data/import_1c",
    [string]$RemoteProjectPath = "/home/freesport/freesport",
    [string]$SshKeyPath = "C:\\Users\\38670\\.ssh\\id_ed25519",
    [int]$ChunkSize = 500,
    [switch]$SkipBackup = $false,
    [switch]$SkipMigrate = $false,
    [switch]$DryRun = $false,
    [string]$BackupPath = ""
)

$ErrorActionPreference = "Stop"

# Функция запускает ssh-agent и добавляет указанный приватный ключ
function Start-SshAgentIfNeeded {
    param(
        [string]$KeyPath
    )

    if (-not (Test-Path -Path $KeyPath)) {
        throw "SSH-ключ не найден: $KeyPath"
    }

    Start-Service ssh-agent -ErrorAction SilentlyContinue | Out-Null
    ssh-add $KeyPath | Out-Null
}

# Функция выполнения команды на удалённом сервере
function Invoke-RemoteCommand {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$Command,
        [string]$ErrorMessage
    )

    Write-Host "🔧 Выполнение команды на сервере: $Command" -ForegroundColor Gray
    
    $result = ssh "$ConnectionUser@$ConnectionHost" $Command 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        throw "$ErrorMessage. Результат: $result"
    }
    
    return $result
}

# Функция проверки существования файлов на сервере
function Test-RemoteFiles {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$RemotePath
    )
    
    Write-Host "📋 Проверка наличия XML-файлов на сервере..." -ForegroundColor Yellow
    
    $command = "find '$RemotePath' -name '*.xml' -type f | wc -l"
    $fileCount = Invoke-RemoteCommand -ConnectionUser $ConnectionUser -ConnectionHost $ConnectionHost -Command $command -ErrorMessage "Не удалось проверить файлы на сервере"
    
    $fileCount = [int]$fileCount.Trim()
    Write-Host "  Найдено XML-файлов: $fileCount" -ForegroundColor Gray
    
    if ($fileCount -eq 0) {
        throw "❌ В директории $RemotePath не найдено XML-файлов"
    }
    
    # Показываем несколько примеров файлов
    $command = "find '$RemotePath' -name '*.xml' -type f | head -5"
    $sampleFiles = Invoke-RemoteCommand -ConnectionUser $ConnectionUser -ConnectionHost $ConnectionHost -Command $command -ErrorMessage "Не удалось получить примеры файлов"
    
    Write-Host "  Примеры файлов:" -ForegroundColor Gray
    foreach ($file in $sampleFiles -split "`n") {
        if ($file.Trim()) {
            Write-Host "    - $file" -ForegroundColor Gray
        }
    }
    
    return $fileCount
}

# Функция создания резервной копии на сервере
function Backup-RemoteDatabase {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$ProjectPath,
        [string]$CustomBackupPath
    )
    
    Write-Host "💾 Создание резервной копии базы данных на сервере..." -ForegroundColor Yellow
    
    $backupCommand = "cd '$ProjectPath' && python manage.py backup_db"
    
    if ($CustomBackupPath) {
        $backupCommand += " --output '$CustomBackupPath'"
    }
    
    $result = Invoke-RemoteCommand -ConnectionUser $ConnectionUser -ConnectionHost $ConnectionHost -Command $backupCommand -ErrorMessage "Не удалось создать резервную копию"
    
    Write-Host "  ✅ Резервная копия создана: $result" -ForegroundColor Green
}

# Функция применения миграций на сервере
function Invoke-RemoteMigrations {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$ProjectPath
    )
    
    Write-Host "📦 Применение миграций на сервере..." -ForegroundColor Yellow
    
    $migrateCommand = "cd '$ProjectPath' && python manage.py migrate"
    Invoke-RemoteCommand -ConnectionUser $ConnectionUser -ConnectionHost $ConnectionHost -Command $migrateCommand -ErrorMessage "Миграции завершились с ошибкой"
    
    Write-Host "  ✅ Миграции применены" -ForegroundColor Green
}

# Функция импорта каталога на сервере
function Import-RemoteCatalog {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$ProjectPath,
        [string]$DataPath,
        [int]$ChunkSize,
        [bool]$DryRun
    )
    
    Write-Host "⬇️ Запуск импорта каталога на сервере..." -ForegroundColor Yellow
    
    $importCommand = "cd '$ProjectPath' && python manage.py import_catalog_from_1c --data-dir '$DataPath' --chunk-size $ChunkSize"
    
    if ($DryRun) {
        $importCommand += " --dry-run"
        Write-Host "  🧪 Режим тестового запуска (без изменений в базе)" -ForegroundColor Cyan
    }
    
    $importCommand += " --skip-backup"  # Пропускаем бэкап, так как делаем его отдельно
    
    try {
        # Запускаем импорт с выводом прогресса
        $fullCommand = "echo 'Начало импорта...' && $importCommand && echo 'Импорт завершён.'"
        $result = Invoke-RemoteCommand -ConnectionUser $ConnectionUser -ConnectionHost $ConnectionHost -Command $fullCommand -ErrorMessage "Импорт каталога завершился с ошибкой"
        
        Write-Host "  ✅ Импорт успешно завершён" -ForegroundColor Green
        return $result
    }
    catch {
        Write-Host "  ❌ Ошибка импорта: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

try {
    Write-Host "🚀 Импорт каталога напрямую на сервере $ServerIP" -ForegroundColor Cyan
    Write-Host "📁 Директория данных: $RemoteDataPath" -ForegroundColor Gray
    Write-Host "📂 Проект: $RemoteProjectPath" -ForegroundColor Gray
    
    # Запускаем SSH агент
    Start-SshAgentIfNeeded -KeyPath $SshKeyPath
    
    # Проверяем соединение с сервером
    Write-Host "🔍 Проверка соединения с сервером..." -ForegroundColor Yellow
    Invoke-RemoteCommand -ConnectionUser $User -ConnectionHost $ServerIP -Command "echo 'Соединение установлено'" -ErrorMessage "Не удалось установить соединение с сервером"
    
    # Проверяем наличие файлов
    $fileCount = Test-RemoteFiles -ConnectionUser $User -ConnectionHost $ServerIP -RemotePath $RemoteDataPath
    
    # Проверяем наличие проекта на сервере
    Write-Host "🔍 Проверка наличия проекта на сервере..." -ForegroundColor Yellow
    Invoke-RemoteCommand -ConnectionUser $User -ConnectionHost $ServerIP -Command "test -d '$RemoteProjectPath'" -ErrorMessage "Проект не найден на сервере: $RemoteProjectPath"
    
    # Создаём резервную копию (если не пропущено)
    if (-not $SkipBackup) {
        Backup-RemoteDatabase -ConnectionUser $User -ConnectionHost $ServerIP -ProjectPath $RemoteProjectPath -CustomBackupPath $BackupPath
    } else {
        Write-Host "⏭️ Пропуск резервного копирования (флаг -SkipBackup)" -ForegroundColor Yellow
    }
    
    # Применяем миграции (если не пропущено)
    if (-not $SkipMigrate) {
        Invoke-RemoteMigrations -ConnectionUser $User -ConnectionHost $ServerIP -ProjectPath $RemoteProjectPath
    } else {
        Write-Host "⏭️ Пропуск миграций (флаг -SkipMigrate)" -ForegroundColor Yellow
    }
    
    # Выполняем импорт
    $importResult = Import-RemoteCatalog -ConnectionUser $User -ConnectionHost $ServerIP -ProjectPath $RemoteProjectPath -DataPath $RemoteDataPath -ChunkSize $ChunkSize -DryRun $DryRun
    
    Write-Host "🎉 Операция завершена успешно!" -ForegroundColor Green
    Write-Host "📊 Обработано файлов: $fileCount" -ForegroundColor Gray
}
catch {
    Write-Host "❌ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}