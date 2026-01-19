#!/bin/bash

# Скрипт диагностики проблем подключения к серверу FREESPORT
# IP: 5.35.124.149

SERVER_IP="5.35.124.149"
echo "🔍 Диагностика сервера FREESPORT ($SERVER_IP)"
echo "=================================================="
echo ""

# Функция для проверки статуса сервисов
check_services() {
    echo "📊 Статус Docker сервисов:"
    if docker-compose -f docker/docker-compose.prod.yml ps --services --filter "status=running" 2>/dev/null; then
        echo "✅ Сервисы работают"
    else
        echo "❌ Проблема с сервисами"
    fi
    echo ""
}

# Проверка портов
check_ports() {
    echo "🔌 Проверка портов на сервере:"
    
    # HTTP (80)
    if timeout 5 bash -c "echo >/dev/tcp/$SERVER_IP/80" 2>/dev/null; then
        echo "✅ Порт 80 (HTTP) доступен"
    else
        echo "❌ Порт 80 (HTTP) недоступен"
    fi
    
    # HTTPS (443)
    if timeout 5 bash -c "echo >/dev/tcp/$SERVER_IP/443" 2>/dev/null; then
        echo "✅ Порт 443 (HTTPS) доступен"
    else
        echo "❌ Порт 443 (HTTPS) недоступен"
    fi
    
    # Backend (8000)
    if timeout 5 bash -c "echo >/dev/tcp/$SERVER_IP/8000" 2>/dev/null; then
        echo "✅ Порт 8000 (Backend) доступен"
    else
        echo "❌ Порт 8000 (Backend) недоступен"
    fi
    echo ""
}

# Проверка Nginx конфигурации
check_nginx() {
    echo "🌐 Проверка конфигурации Nginx:"
    
    # Проверка синтаксиса конфигурации
    if docker-compose -f docker/docker-compose.prod.yml exec -T nginx nginx -t 2>/dev/null; then
        echo "✅ Конфигурация Nginx корректна"
    else
        echo "❌ Ошибка в конфигурации Nginx"
    fi
    
    # Проверка доступности конфигурационных файлов
    if docker-compose -f docker/docker-compose.prod.yml exec -T ls -la /etc/nginx/conf.d/default.conf 2>/dev/null; then
        echo "✅ Конфигурационный файл найден"
    else
        echo "❌ Конфигурационный файл отсутствует"
    fi
    echo ""
}

# Проверка логов
check_logs() {
    echo "📜 Последние логи Nginx (последние 10 строк):"
    docker-compose -f docker/docker-compose.prod.yml logs --tail=10 nginx 2>/dev/null || echo "Не удалось получить логи"
    echo ""
}

# Локальная проверка
local_checks() {
    echo "🏠 Локальные проверки (на сервере):"
    
    # Проверка доступности локально
    echo -n "HTTP (127.0.0.1:80): "
    if timeout 3 curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/health || echo "FAILED"; then
        echo "✅"
    else
        echo "❌"
    fi
    
    echo -n "HTTPS (127.0.0.1:443): "
    if timeout 3 curl -k -s -o /dev/null -w "%{http_code}" https://127.0.0.1/health 2>/dev/null || echo "FAILED"; then
        echo "✅"
    else
        echo "❌"
    fi
    
    # Проверка Django Admin локально
    echo -n "Django Admin (127.0.0.1:80/admin): "
    if timeout 3 curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/admin 2>/dev/null | grep -q "302\|200\|301"; then
        echo "✅"
    else
        echo "❌"
    fi
    echo ""
}

# Проверка файервола
check_firewall() {
    echo "🔥 Проверка файервола:"
    
    # iptables
    if command -v iptables >/dev/null 2>&1; then
        echo "📋 Правила iptables:"
        sudo iptables -L INPUT -n | grep -E "ACCEPT|REJECT|DROP" | head -5
    fi
    
    # ufw
    if command -v ufw >/dev/null 2>&1; then
        echo "📋 Статус UFW:"
        sudo ufw status numbered | head -10
    fi
    
    # nftables
    if command -v nft >/dev/null 2>&1; then
        echo "📋 Правила nftables:"
        sudo nft list ruleset | head -10
    fi
    echo ""
}

# Рекомендации
recommendations() {
    echo "💡 Рекомендации по устранению проблем:"
    echo "1. Проверьте, что контейнеры запущены: docker-compose -f docker/docker-compose.prod.yml ps"
    echo "2. Проверьте логи: docker-compose -f docker/docker-compose.prod.yml logs nginx"
    echo "3. Убедитесь, что порты 80 и 443 открыты в файерволе"
    echo "4. Создайте SSL сертификаты: ./scripts/server/create-ssl-certs.sh"
    echo "5. Перезапустите Nginx: docker-compose -f docker/docker-compose.prod.yml restart nginx"
    echo "6. Проверьте Django settings: ALLOWED_HOSTS должен включать $SERVER_IP"
    echo ""
}

# Выполняем все проверки
check_services
check_ports
check_nginx
check_logs
local_checks
check_firewall
recommendations

echo "🏁 Диагностика завершена"