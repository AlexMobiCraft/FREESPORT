# Скрипт для копирования данных импорта 1С на сервер разработки FREESPORT

param(
    [string]$User = "root",
    [string]$IP = "5.35.124.149",
    [string]$LocalDataPath = "data/import_1c",
    [string]$RemoteDataPath = "/home/freesport/freesport/data/import_1c",
    [string]$SshKeyPath = "C:\\Users\\38670\\.ssh\\id_ed25519",
    [switch]$SkipVerification = $false,
    [switch]$ForceCopy = $false
)

$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
# Исправляем определение корня проекта - поднимаемся на два уровня вверх от scripts/server/
$projectRoot = Split-Path -Path (Split-Path -Path $scriptDirectory -Parent) -Parent

Write-Host "Отладка определения путей:" -ForegroundColor Cyan
Write-Host "  Директория скрипта: $scriptDirectory" -ForegroundColor Gray
Write-Host "  Определённый корень проекта: $projectRoot" -ForegroundColor Gray
Write-Host "  Текущая рабочая директория: $(Get-Location)" -ForegroundColor Gray

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

# Функция преобразует путь на сервере в абсолютный вид
function Resolve-RemotePath {
    param(
        [string]$RemotePath,
        [string]$RemoteUser
    )

    if ($RemotePath -eq "~") {
        return "/home/$RemoteUser"
    }

    if ($RemotePath.StartsWith("~/")) {
        return "/home/$RemoteUser/" + $RemotePath.Substring(2)
    }

    return $RemotePath
}

# Функция создаёт директорию на удалённом сервере, если она отсутствует
function Ensure-RemoteDirectory {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$RemotePath
    )

    Write-Host "  Отладка Ensure-RemoteDirectory:" -ForegroundColor Gray
    Write-Host "    Исходный путь: $RemotePath" -ForegroundColor Gray
    
    # Проверяем, что путь не пустой
    if ([string]::IsNullOrWhiteSpace($RemotePath)) {
        throw "Удалённый путь не может быть пустым"
    }
    
    # Более надёжное экранирование пути для SSH
    # Используем двойные кавычки для пути, чтобы избежать проблем с экранированием
    $escapedPath = $RemotePath.Replace('"', '\"')
    $command = "mkdir -p ""$escapedPath"""
    
    Write-Host "    Экранированный путь: $escapedPath" -ForegroundColor Gray
    Write-Host "    Команда для выполнения: $command" -ForegroundColor Gray
    Write-Host "    Полная SSH команда: bash -lc \"$command\"" -ForegroundColor Gray
    
    try {
        # Добавляем проверку соединения перед выполнением команды
        $testResult = ssh "$ConnectionUser@$ConnectionHost" "echo 'Connection test'" 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Не удалось установить SSH соединение: $testResult"
        }
        
        # Пробуем более простой подход - выполняем mkdir напрямую через bash
        $simpleCommand = "mkdir -p $escapedPath"
        Write-Host "    Упрощённая команда: $simpleCommand" -ForegroundColor Gray
        
        $result = ssh "$ConnectionUser@$ConnectionHost" $simpleCommand 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    Ошибка выполнения mkdir: $result" -ForegroundColor Red
            Write-Host "    Код выхода: $LASTEXITCODE" -ForegroundColor Red
             
            # Если простой подход не сработал, пробуем альтернативный
            Write-Host "    Пробуем альтернативный подход..." -ForegroundColor Yellow
            $altCommand = "mkdir -p '$RemotePath'"
            Write-Host "    Альтернативная команда: $altCommand" -ForegroundColor Gray
            $result2 = ssh "$ConnectionUser@$ConnectionHost" $altCommand 2>&1
             
            if ($LASTEXITCODE -ne 0) {
                throw "Не удалось создать директорию на сервере: $result2"
            } else {
                Write-Host "    Директория успешно создана (альтернативным методом)" -ForegroundColor Green
            }
        } else {
            Write-Host "    Директория успешно создана" -ForegroundColor Green
        }
    } catch {
        Write-Host "    Исключение при выполнении mkdir: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

# Функция проверяет, какие файлы уже существуют на сервере
function Get-ExistingFilesOnServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$RemotePath
    )
    
    Write-Host "Проверка существующих файлов на сервере..." -ForegroundColor Yellow
    
    # Получаем список файлов с их размерами и хешами на сервере
    $command = "find '$RemotePath' -type f -exec sha256sum {} \; 2>/dev/null | sed 's|$RemotePath/||'"
    $result = ssh "$ConnectionUser@$ConnectionHost" $command 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Не удалось получить список файлов на сервере, возможно, директория пуста" -ForegroundColor Gray
        return @{}
    }
    
    $existingFiles = @{}
    foreach ($line in $result -split "`n") {
        if ($line.Trim() -match "^([a-f0-9]+)\s+(.+)$") {
            $hash = $matches[1]
            $relativePath = $matches[2]
            $existingFiles[$relativePath] = $hash
        }
    }
    
    Write-Host "  Найдено существующих файлов: $($existingFiles.Count)" -ForegroundColor Gray
    return $existingFiles
}

# Функция копирует только новые или измененные файлы на сервер
function Copy-ChangedFilesToServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$LocalPath,
        [string]$RemotePath,
        [hashtable]$ExistingFiles
    )

    if (-not (Test-Path -Path $LocalPath)) {
        throw "Локальный каталог не найден: $LocalPath"
    }

    Write-Host "Анализ локальных файлов..." -ForegroundColor Yellow
    $localFiles = Get-ChildItem -Path $LocalPath -Recurse -File
    $filesToCopy = @()
    $skippedFiles = 0
    
    foreach ($file in $localFiles) {
        $relativePath = $file.FullName.Replace((Resolve-Path $LocalPath).Path, "").TrimStart("\").Replace("\", "/")
        
        # Вычисляем хеш локального файла
        $localHash = (Get-FileHash -Path $file.FullName -Algorithm SHA256).Hash.ToLower()
        
        # Проверяем, существует ли файл на сервере и совпадает ли хеш
        if ($ExistingFiles.ContainsKey($relativePath) -and $ExistingFiles[$relativePath] -eq $localHash) {
            $skippedFiles++
            Write-Host "  Пропуск: $relativePath (уже существует)" -ForegroundColor Gray
        } else {
            $filesToCopy += $file
            if ($ExistingFiles.ContainsKey($relativePath)) {
                Write-Host "  Копирование: $relativePath (изменён)" -ForegroundColor Cyan
            } else {
                Write-Host "  Копирование: $relativePath (новый)" -ForegroundColor Green
            }
        }
    }
    
    Write-Host "Итого: $($filesToCopy.Count) файлов для копирования, $skippedFiles файлов пропущено" -ForegroundColor Yellow
    
    if ($filesToCopy.Count -eq 0) {
        Write-Host "✓ Все файлы уже актуальны, копирование не требуется" -ForegroundColor Green
        return
    }
    
    # Копируем файлы по одному для детального контроля
    foreach ($file in $filesToCopy) {
        $relativePath = $file.FullName.Replace((Resolve-Path $LocalPath).Path, "").TrimStart("\").Replace("\", "/")
        $remoteDir = "$RemotePath/$($relativePath.Substring(0, $relativePath.LastIndexOf('/')))"
        $remoteFilePath = "$RemotePath/$relativePath"
        
        # Создаем директорию на сервере, если нужно
        if ($relativePath.Contains('/')) {
            $mkdirCommand = "mkdir -p '$remoteDir'"
            ssh "$ConnectionUser@$ConnectionHost" $mkdirCommand 2>&1 | Out-Null
        }
        
        # Копируем файл
        $destination = [string]::Format("{0}@{1}:{2}", $ConnectionUser, $ConnectionHost, $remoteFilePath)
        $scpArgs = @("-C", $file.FullName, $destination)
        & scp @scpArgs
        
        if ($LASTEXITCODE -ne 0) {
            throw "Ошибка при копировании файла: $($file.FullName)"
        }
    }
}

# Функция копирует каталог данных на сервер через SCP (резервный вариант)
function Copy-DirectoryToServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$LocalPath,
        [string]$RemotePath
    )

    if (-not (Test-Path -Path $LocalPath)) {
        throw "Локальный каталог не найден: $LocalPath"
    }

    $sourcePath = Join-Path -Path $LocalPath -ChildPath "."
    $destination = [string]::Format("{0}@{1}:{2}", $ConnectionUser, $ConnectionHost, $RemotePath)
    $scpArgs = @("-r", "-C", $sourcePath, $destination)
    & scp @scpArgs
}

# Функция проверяет, что все файлы успешно скопированы на сервер
function Verify-CopiedFiles {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$LocalPath,
        [string]$RemotePath
    )

    Write-Host "Проверка скопированных файлов..." -ForegroundColor Yellow
    
    # Получаем информацию о локальных файлах
    $localFiles = Get-ChildItem -Path $LocalPath -Recurse -File
    $localCount = $localFiles.Count
    $localSize = ($localFiles | Measure-Object -Property Length -Sum).Sum
    
    Write-Host "  Локальные файлы: $localCount шт., размер: $([math]::Round($localSize / 1MB, 2)) МБ" -ForegroundColor Gray
    
    # Получаем информацию о файлах на сервере
    $remoteCommand = "find '$RemotePath' -type f | wc -l && du -sb '$RemotePath' | cut -f1"
    $remoteInfo = ssh "$ConnectionUser@$ConnectionHost" $remoteCommand 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Не удалось получить информацию о файлах на сервере: $remoteInfo" -ForegroundColor Red
        return $false
    }
    
    $remoteLines = $remoteInfo -split "`n"
    $remoteCount = [int]$remoteLines[0].Trim()
    $remoteSize = [long]$remoteLines[1].Trim()
    
    Write-Host "  Файлы на сервере: $remoteCount шт., размер: $([math]::Round($remoteSize / 1MB, 2)) МБ" -ForegroundColor Gray
    
    # Сравниваем количество файлов
    if ($localCount -eq $remoteCount) {
        Write-Host "  ✓ Количество файлов совпадает: $localCount" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Количество файлов не совпадает: локально $localCount, на сервере $remoteCount" -ForegroundColor Red
        return $false
    }
    
    # Сравниваем размеры (с небольшим допуском из-за особенностей файловых систем)
    $sizeDiff = [math]::Abs($localSize - $remoteSize)
    $sizeDiffPercent = if ($localSize -gt 0) { $sizeDiff / $localSize * 100 } else { 0 }
    
    if ($sizeDiffPercent -lt 1) {  # Допуск 1%
        Write-Host "  ✓ Размеры файлов совпадают (разница: $([math]::Round($sizeDiffPercent, 2))%)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ✗ Размеры файлов значительно отличаются: локально $([math]::Round($localSize / 1MB, 2)) МБ, на сервере $([math]::Round($remoteSize / 1MB, 2)) МБ" -ForegroundColor Red
        return $false
    }
}

Push-Location $projectRoot

try {
    Write-Host "=== Копирование файлов 1С на сервер ===" -ForegroundColor Cyan
    Start-SshAgentIfNeeded -KeyPath $SshKeyPath

    $absoluteLocalPath = if ([System.IO.Path]::IsPathRooted($LocalDataPath)) {
        $LocalDataPath
    } else {
        Join-Path -Path $projectRoot -ChildPath $LocalDataPath
    }

    $resolvedRemotePath = Resolve-RemotePath -RemotePath $RemoteDataPath -RemoteUser $User

    Write-Host "Отладочная информация:" -ForegroundColor Cyan
    Write-Host "  Корень проекта: $projectRoot" -ForegroundColor Gray
    Write-Host "  Локальный путь (относительный): $LocalDataPath" -ForegroundColor Gray
    Write-Host "  Локальный путь (абсолютный): $absoluteLocalPath" -ForegroundColor Gray
    Write-Host "  Проверка существования локальной директории: $(Test-Path -Path $absoluteLocalPath)" -ForegroundColor Gray
    Write-Host "  Удалённый путь (до преобразования): $RemoteDataPath" -ForegroundColor Gray
    Write-Host "  Удалённый путь (после преобразования): $resolvedRemotePath" -ForegroundColor Gray

    Write-Host "Подготовка директории на сервере..." -ForegroundColor Yellow
    Ensure-RemoteDirectory -ConnectionUser $User -ConnectionHost $IP -RemotePath $resolvedRemotePath

    if ($ForceCopy) {
        Write-Host "Копирование файлов из '$absoluteLocalPath' (полное копирование)..." -ForegroundColor Yellow
        Copy-DirectoryToServer -ConnectionUser $User -ConnectionHost $IP -LocalPath $absoluteLocalPath -RemotePath $resolvedRemotePath
    } else {
        Write-Host "Инкрементальное копирование файлов из '$absoluteLocalPath'..." -ForegroundColor Yellow
        $existingFiles = Get-ExistingFilesOnServer -ConnectionUser $User -ConnectionHost $IP -RemotePath $resolvedRemotePath
        Copy-ChangedFilesToServer -ConnectionUser $User -ConnectionHost $IP -LocalPath $absoluteLocalPath -RemotePath $resolvedRemotePath -ExistingFiles $existingFiles
    }

    Write-Host "✓ Копирование завершено" -ForegroundColor Green
    
    # Проверяем, что все файлы успешно скопированы (если не отключено)
    if (-not $SkipVerification) {
        $verificationResult = Verify-CopiedFiles -ConnectionUser $User -ConnectionHost $IP -LocalPath $absoluteLocalPath -RemotePath $resolvedRemotePath
        
        if ($verificationResult) {
            Write-Host "✓ Проверка завершена успешно - все файлы скопированы корректно" -ForegroundColor Green
        } else {
            Write-Host "✗ Проверка выявила несоответствия - возможно, не все файлы скопированы" -ForegroundColor Red
            throw "Проверка копирования файлов не пройдена"
        }
    } else {
        Write-Host "⚠ Проверка копирования пропущена (использован параметр -SkipVerification)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "✗ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
finally {
    Pop-Location
}
