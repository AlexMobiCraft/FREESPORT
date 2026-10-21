# Скрипт создания самоподписанных SSL сертификатов для OPTISPORT (Windows версия)
# Используется для временного HTTPS доступа к серверу по IP адресу
# ВАЖНО: Этот скрипт необходимо запускать из корневой директории проекта!

Write-Host "🔐 Создание самоподписанных SSL сертификатов для OPTISPORT..."

# Определяем директорию для сертификатов относительно корня проекта
$CERT_DIR = "docker\nginx\ssl"

# Создаем директорию, если она не существует
if (-not (Test-Path $CERT_DIR)) {
    New-Item -ItemType Directory -Path $CERT_DIR -Force
}

# Пути к файлам
$KEY_PATH = "$CERT_DIR\key.pem"
$CERT_PATH = "$CERT_DIR\cert.pem"

# Проверяем, существуют ли уже сертификаты
if ((Test-Path $CERT_PATH) -and (Test-Path $KEY_PATH)) {
    Write-Host "✅ Сертификаты уже существуют в $CERT_DIR. Пропускаем создание."
} else {
    # Проверяем, доступен ли OpenSSL
    try {
        $null = openssl version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "OpenSSL не найден"
        }
    } catch {
        Write-Host "❌ Ошибка: OpenSSL не найден в системе."
        Write-Host "Пожалуйста, установите OpenSSL:"
        Write-Host "1. Скачайте с https://slproweb.com/products/Win32OpenSSL.html"
        Write-Host "2. Или установите через Git for Windows (включает OpenSSL)"
        Write-Host "3. Или используйте WSL (Windows Subsystem for Linux)"
        exit 1
    }

    # Создаем приватный ключ
    Write-Host "🔑 Создание приватного ключа..."
    openssl genrsa -out "$KEY_PATH" 2048
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка при создании приватного ключа"
        exit 1
    }

    # Создаем самоподписанный сертификат
    Write-Host "📜 Создание самоподписанного сертификата..."
    openssl req -new -x509 -key "$KEY_PATH" -out "$CERT_PATH" -days 365 -subj "/C=RU/ST=Moscow/L=Moscow/O=FREESPORT/OU=IT/CN=localhost"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка при создании сертификата"
        exit 1
    }

    Write-Host "✅ Сертификаты успешно созданы в директории $CERT_DIR"
    Write-Host "   - $KEY_PATH (приватный ключ)"
    Write-Host "   - $CERT_PATH (сертификат)"
}

Write-Host ""
Write-Host "📋 Инструкции по использованию:"
Write-Host "1. Убедитесь, что вы обновили код на сервере (включая этот скрипт и docker-compose.yml)."
Write-Host "2. Перезапустите контейнеры из корневой директории проекта:"
Write-Host "   docker-compose down && docker-compose up -d"

Write-Host ""
Write-Host "⚠️  ВАЖНО:"
Write-Host "- Эти сертификаты самоподписанные, и браузеры будут показывать предупреждение о безопасности."
Write-Host "- Для доступа к сайту https://localhost вам нужно будет принять риски и добавить исключение безопасности в браузере."
Write-Host "- Для реальной эксплуатации (production) используйте сертификаты от Let's Encrypt или другого доверенного центра."

Write-Host ""
Write-Host "🌐 Доступ к сервисам после запуска:"
Write-Host "- Frontend: http://localhost:3000"
Write-Host "- Backend API: http://localhost:8001/api/v1"
Write-Host "- Nginx (HTTPS): https://localhost (с самоподписанным сертификатом)"