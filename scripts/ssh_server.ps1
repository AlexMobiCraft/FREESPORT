# Скрипт для быстрого SSH-подключения к серверу разработки FREESPORT
# Использование:
#   pwsh .\scripts\ssh_server.ps1
#   pwsh .\scripts\ssh_server.ps1 -User другой_пользователь -IP 192.168.1.130

param(
    [string]$User = "alex",
    [string]$IP = "192.168.0.129"
)

# Функция подключается по SSH к удалённому серверу разработки
function Connect-FreesportServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost
    )

    Start-Service ssh-agent -ErrorAction SilentlyContinue | Out-Null
    ssh-add "$HOME\.ssh\id_ed25519" | Out-Null
    ssh "$ConnectionUser@$ConnectionHost"
}

Connect-FreesportServer -ConnectionUser $User -ConnectionHost $IP
