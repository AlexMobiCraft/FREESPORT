# Проверка работоспособности окружения FREESPORT Platform

Эта инструкция описывает процедуры проверки работоспособности всех компонентов платформы после развертывания.

## Общая проверка

### 1. Проверка статуса контейнеров

```bash
# Проверка статуса всех контейнеров
docker compose -f docker-compose.prod.yml ps

# Ожидаемый результат: все контейнеры в статусе "Up" или "running"
```

### 2. Проверка логов на наличие ошибок

```bash
# Просмотр логов всех сервисов
docker compose -f docker-compose.prod.yml logs

# Проверка логов конкретного сервиса
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs db
docker compose -f docker-compose.prod.yml logs nginx
```

## Проверка компонентов

### 1. База данных PostgreSQL

```bash
# Проверка подключения к базе данных
docker compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# Проверка списка таблиц
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d freesport -c "\dt"

# Проверка соединения из backend
docker compose -f docker-compose.prod.yml exec backend python manage.py dbshell --command "SELECT version();"
```

### 2. Redis

```bash
# Проверка подключения к Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# Проверка аутентификации
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Проверка информации о сервере
docker compose -f docker-compose.prod.yml exec redis redis-cli info server
```

### 3. Django Backend

```bash
# Проверка здоровья Django
docker compose -f docker-compose.prod.yml exec backend python manage.py check --deploy

# Проверка доступности API
curl -f -s http://localhost:8001/api/v1/health/ || echo "API недоступен"

# Проверка миграций
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# Проверка сбора статических файлов
docker compose -f docker-compose.prod.yml exec backend python manage.py findstatic --verbosity 2 admin/css/base.css
```

### 4. Next.js Frontend

```bash
# Проверка здоровья frontend
curl -f -s http://localhost:3000/api/health || echo "Frontend недоступен"

# Проверка логов сборки
docker compose -f docker-compose.prod.yml logs frontend
```

### 5. Nginx

```bash
# Проверка конфигурации Nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# Проверка доступности сайта через Nginx
curl -I http://localhost/

# Проверка SSL (если настроен)
curl -I https://freesport.ru/
```

### 6. Celery Worker

```bash
# Проверка статуса Celery worker
docker compose -f docker-compose.prod.yml exec celery celery -A freesport inspect active

# Проверка доступности очередей
docker compose -f docker-compose.prod.yml exec celery celery -A freesport inspect reserved
```

### 7. Celery Beat

```bash
# Проверка статуса Celery beat
docker compose -f docker-compose.prod.yml logs celery-beat

# Проверка расписания задач
docker compose -f docker-compose.prod.yml exec celery celery -A freesport beat schedule
```

## Функциональное тестирование

### 1. Тестирование API endpoints

```bash
# Тестирование основного API
curl -X GET http://localhost:8001/api/v1/health/

# Тестирование каталога товаров
curl -X GET http://localhost:8001/api/v1/products/

# Тестирование аутентификации
curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### 2. Тестирование работы с базой данных

```bash
# Создание тестовой записи
docker compose -f docker-compose.prod.yml exec backend python manage.py shell << EOF
from apps.users.models import User
User.objects.create_user('testuser', 'test@example.com', 'testpass')
print("Test user created")
EOF

# Проверка записи
docker compose -f docker-compose.prod.yml exec backend python manage.py shell << EOF
from apps.users.models import User
print(f"Users count: {User.objects.count()}")
EOF
```

### 3. Тестирование загрузки файлов

```bash
# Проверка загрузки медиа файлов
docker compose -f docker-compose.prod.yml exec backend python manage.py shell << EOF
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage

test_file = SimpleUploadedFile("test.txt", b"test content", content_type="text/plain")
saved_path = default_storage.save('test/test.txt', test_file)
print(f"File saved to: {saved_path}")
EOF
```

## Мониторинг производительности

### 1. Проверка использования ресурсов

```bash
# Статистика Docker контейнеров
docker stats

# Использование диска
df -h

# Использование памяти
free -h

# Нагрузка на CPU
top
```

### 2. Проверка сетевых соединений

```bash
# Проверка прослушиваемых портов
netstat -tlnp

# Проверка соединений между контейнерами
docker network ls
docker network inspect freesport-prod-network
```

## Автоматическая проверка

### Скрипт комплексной проверки

```bash
#!/bin/bash
# scripts/health-check.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

check_service() {
    local service=$1
    local command=$2
    
    echo -n "Проверка $service... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        ERRORS=$((ERRORS + 1))
    fi
}

echo "Комплексная проверка работоспособности FREESPORT Platform"
echo "========================================================"

# Проверка контейнеров
check_service "Статус контейнеров" "docker compose -f docker-compose.prod.yml ps | grep -q 'Up'"

# Проверка базы данных
check_service "PostgreSQL" "docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres"

# Проверка Redis
check_service "Redis" "docker compose -f docker-compose.prod.yml exec -T redis redis-cli ping"

# Проверка Django
check_service "Django Backend" "docker compose -f docker-compose.prod.yml exec -T backend python manage.py check --deploy"

# Проверка API
check_service "API Endpoint" "curl -f -s http://localhost:8001/api/v1/health/"

# Проверка Frontend
check_service "Frontend" "curl -f -s http://localhost:3000/api/health"

# Проверка Nginx
check_service "Nginx" "docker compose -f docker-compose.prod.yml exec -T nginx nginx -t"

echo "========================================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}Все проверки пройдены успешно!${NC}"
    exit 0
else
    echo -e "${RED}Обнаружено $ERRORS ошибок${NC}"
    exit 1
fi
```

### Регулярная проверка через cron

```bash
# Добавление в cron для проверки каждые 5 минут
echo "*/5 * * * * /path/to/freesport/scripts/health-check.sh" | crontab -
```

## Логирование и отчетность

### 1. Настройка логирования

```bash
# Создание директории для логов проверки
mkdir -p logs/health-check

# Модификация скрипта для записи логов
# Добавьте в начало скрипта:
LOG_FILE="logs/health-check/health-$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE")
exec 2>&1
```

### 2. Настройка оповещений

```bash
# Добавление функции отправки email уведомлений
send_alert() {
    local subject=$1
    local message=$2
    
    echo "$message" | mail -s "$subject" admin@yourdomain.com
}

# Использование в скрипте:
if [ $ERRORS -gt 0 ]; then
    send_alert "FREESPORT Health Check Failed" "Обнаружено $ERRORS ошибок при проверке работоспособности"
fi
```

## Решение типичных проблем

### Проблема: Контейнер не запускается

```bash
# Проверка логов контейнера
docker compose -f docker-compose.prod.yml logs [service_name]

# Проверка конфигурации
docker compose -f docker-compose.prod.yml config

# Пересборка образа
docker compose -f docker-compose.prod.yml build [service_name]
```

### Проблема: Нет подключения к базе данных

```bash
# Проверка статуса контейнера БД
docker compose -f docker-compose.prod.yml ps db

# Проверка настроек подключения
docker compose -f docker-compose.prod.yml exec backend python manage.py dbshell --command "SELECT version();"

# Перезапуск контейнера БД
docker compose -f docker-compose.prod.yml restart db
```

### Проблема: Недоступен API

```bash
# Проверка работы Django
docker compose -f docker-compose.prod.yml exec backend python manage.py check --deploy

# Проверка портов
docker compose -f docker-compose.prod.yml port backend 8000

# Проверка Nginx конфигурации
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

## Заключение

Регулярное выполнение этих проверок поможет убедиться в стабильной работе платформы и своевременно выявлять проблемы. Рекомендуется автоматизировать эти проверки и настроить оповещения о сбоях.

Для дополнительной информации обратитесь к:
- [Полной документации по развертыванию](docker-server-setup.md)
- [Инструкции по быстрому развертыванию](quick-deployment.md)
- [Документации проекта](README.md)