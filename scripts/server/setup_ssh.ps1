# Скрипт для настройки SSH окружения для работы с сервером FREESPORT
# Запускается один раз для каждой новой сессии терминала.

param(
    [string]$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519"
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

function Write-ColorMessage {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

Write-ColorMessage "=== Настройка SSH окружения для FREESPORT ===" "Cyan"
Write-Host ""

# 1. Проверка SSH ключа
Write-ColorMessage "1. Проверка SSH ключа..." "Yellow"
if (-not (Test-Path -Path $KeyPath)) {
    Write-ColorMessage "   ✗ SSH ключ не найден: $KeyPath" "Red"
    exit 1
}
Write-ColorMessage "   ✓ SSH ключ найден: $KeyPath" "Green"
Write-Host ""

# 2. Запуск SSH агента и настройка окружения
Write-ColorMessage "2. Проверка и запуск SSH агента..." "Yellow"
$agentRunning = Get-Process -Name ssh-agent -ErrorAction SilentlyContinue

if ($agentRunning) {
    Write-ColorMessage "   ✓ ssh-agent уже запущен." "Green"
} else {
    Write-ColorMessage "   ssh-agent не запущен. Пытаемся запустить..." "Cyan"
    
    # Проверяем, не отключена ли служба
    $service = Get-Service -Name ssh-agent -ErrorAction SilentlyContinue
    if ($service -and $service.StartType -eq 'Disabled') {
        Write-ColorMessage "   ✗ КРИТИЧЕСКАЯ ОШИБКА: Служба 'OpenSSH Authentication Agent' отключена." "Red"
        Write-ColorMessage "   Скрипт не может ее запустить. Пожалуйста, включите службу вручную." "Yellow"
        Write-ColorMessage "   Подробная инструкция здесь: docs/deploy/FIX_SSH_AGENT_SERVICE.md" "Cyan"
        exit 1
    }

    try {
        # Ищем ssh-agent.exe в стандартной директории, если его нет в PATH
        $sshAgentPath = "ssh-agent"
        if (-not (Get-Command $sshAgentPath -ErrorAction SilentlyContinue)) {
            Write-ColorMessage "   ssh-agent.exe не найден в PATH. Ищем в стандартной директории..." "Yellow"
            $openSshPath = "$env:SystemRoot\System32\OpenSSH\ssh-agent.exe"
            if (Test-Path $openSshPath) {
                Write-ColorMessage "   ✓ ssh-agent.exe найден: $openSshPath" "Green"
                $sshAgentPath = $openSshPath
            } else {
                throw "Не удалось найти ssh-agent.exe ни в PATH, ни в $openSshPath."
            }
        }

        # Самый надежный способ: запустить агент и выполнить его вывод
        # Это установит переменные SSH_AUTH_SOCK и SSH_AGENT_PID
        $agentOutput = & $sshAgentPath
        if ($LASTEXITCODE -ne 0 -or -not $agentOutput) {
             throw "Не удалось получить вывод от ssh-agent.exe."
        }
        
        $agentOutput | ForEach-Object {
            $cmd, $val = $_ -split '=', 2;
            if ($cmd -and $val) {
                $var, $null = $cmd -split ' ';
                Set-Item "env:$var" $val.Split(';')[0]
            }
        }
        $agentRunning = Get-Process -Name ssh-agent -ErrorAction SilentlyContinue
        if ($agentRunning) {
             Write-ColorMessage "   ✓ ssh-agent успешно запущен (PID: $($agentRunning.Id))" "Green"
        } else {
            throw "Не удалось запустить ssh-agent после выполнения команды."
        }
    }
    catch {
        Write-ColorMessage "   ✗ Не удалось запустить ssh-agent: $($_.Exception.Message)" "Red"
        Write-ColorMessage "   См. инструкцию: docs/deploy/FIX_SSH_AGENT_SERVICE.md" "Cyan"
        exit 1
    }
}
Write-Host ""

# 3. Добавление ключа в агент
Write-ColorMessage "3. Добавление ключа в SSH агент..." "Yellow"
$keyAlreadyAdded = $false
try {
    $addedKeys = ssh-add -l 2>&1
    if ($addedKeys -is [array]) {
        foreach ($key in $addedKeys) {
            if ($key -match [regex]::Escape((Get-Item $KeyPath).Name)) {
                $keyAlreadyAdded = $true
                break
            }
        }
    } elseif ($addedKeys -match [regex]::Escape((Get-Item $KeyPath).Name)) {
        $keyAlreadyAdded = $true
    }
}
catch {
    # ssh-add вернет ошибку, если агент пуст, это нормально
}


if ($keyAlreadyAdded) {
    Write-ColorMessage "   ✓ Ключ уже добавлен в агент." "Green"
} else {
    Write-ColorMessage "   Ключ не найден в агенте. Добавляем..." "Cyan"
    Write-ColorMessage "   Если ключ защищен, введите пароль сейчас:" "Cyan"
    try {
        ssh-add $KeyPath
        if ($LASTEXITCODE -eq 0) {
            Write-ColorMessage "   ✓ Ключ успешно добавлен в агент." "Green"
        } else {
            Write-ColorMessage "   ✗ Не удалось добавить ключ в агент." "Red"
            exit 1
        }
    }
    catch {
        Write-ColorMessage "   ✗ Ошибка при добавлении ключа: $($_.Exception.Message)" "Red"
        exit 1
    }
}
Write-Host ""

# 4. Проверка подключения
Write-ColorMessage "4. Тестирование SSH подключения..." "Yellow"
try {
    ssh -o ConnectTimeout=10 -o BatchMode=yes root@5.35.124.149 "echo 'SSH connection test successful'"
    if ($LASTEXITCODE -eq 0) {
        Write-ColorMessage "   ✓ Тест подключения успешен. Аутентификация по ключу работает." "Green"
    } else {
        Write-ColorMessage "   ✗ Тест подключения не удался. Проверьте авторизацию ключа на сервере." "Red"
    }
}
catch {
    Write-ColorMessage "   ✗ Ошибка при тесте подключения: $($_.Exception.Message)" "Red"
}
Write-Host ""

Write-ColorMessage "=== Настройка SSH завершена ===" "Cyan"
Write-ColorMessage "Окружение для текущей сессии терминала настроено."
Write-ColorMessage "Теперь можно запускать другие скрипты." "Green"