# Проверка работоспособности окружения FREESPORT Platform

Эта инструкция описывает процедуры проверки работоспособности всех компонентов платформы после развертывания.

## Общая проверка

### 1. Проверка статуса контейнеров

```bash
# Проверка статуса всех контейнеров
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml ps

# Ожидаемый результат: все контейнеры в статусе "Up" или "running"
```

### 2. Проверка логов на наличие ошибок

```bash
# Просмотр логов всех сервисов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs

# Проверка логов конкретного сервиса
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs db
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs nginx
```

## Проверка компонентов

### 1. База данных PostgreSQL

```bash
# Проверка подключения к базе данных
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec db pg_isready -U postgres

# Проверка списка таблиц
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec db psql -U postgres -d freesport -c "\dt"

# Проверка соединения из backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py dbshell --command "SELECT version();"
```

### 2. Redis

```bash
# Проверка подключения к Redis
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec redis redis-cli ping

# Проверка аутентификации
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Проверка информации о сервере
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec redis redis-cli info server
```

### 3. Django Backend

```bash
# Проверка здоровья Django
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py check --deploy

# Проверка доступности API
curl -f -s http://localhost:8001/api/v1/health/ || echo "API недоступен"

# Проверка миграций
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py showmigrations

# Проверка сбора статических файлов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py findstatic --verbosity 2 admin/css/base.css
```

### 4. Next.js Frontend

```bash
# Проверка здоровья frontend
curl -f -s http://localhost:3000/api/health || echo "Frontend недоступен"

# Проверка логов сборки
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs frontend
```

### 5. Nginx

```bash
# Проверка конфигурации Nginx
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec nginx nginx -t

# Проверка доступности сайта через Nginx
curl -I http://localhost/

# Проверка SSL (если настроен)
curl -I https://freesport.ru/
```

### 6. Celery Worker

```bash
# Проверка статуса Celery worker
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec celery celery -A freesport inspect active

# Проверка доступности очередей
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec celery celery -A freesport inspect reserved
```

### 7. Celery Beat

```bash
# Проверка статуса Celery beat
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs celery-beat

# Проверка расписания задач
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec celery celery -A freesport beat schedule
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
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py shell << EOF
from apps.users.models import User
User.objects.create_user('testuser', 'test@example.com', 'testpass')
print("Test user created")
EOF

# Проверка записи
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py shell << EOF
from apps.users.models import User
print(f"Users count: {User.objects.count()}")
EOF
```

### 3. Тестирование загрузки файлов

```bash
# Проверка загрузки медиа файлов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py shell << EOF
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

Используйте встроенный скрипт проверки:

```bash
# Запуск полной проверки
./scripts/deploy/health-check.sh

# Проверка с записью в лог
./scripts/deploy/health-check.sh > logs/health-check.log 2>&1
```

### Регулярная проверка через cron

```bash
# Добавление в cron для проверки каждые 5 минут
echo "*/5 * * * * /path/to/freesport/scripts/deploy/health-check.sh" | crontab -
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
    
    echo "$message" | mail -s "$subject" admin@freesport.ru
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
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs [service_name]

# Проверка конфигурации
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml config

# Пересборка образа
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml build --no-cache [service_name]
```

### Проблема: Нет подключения к базе данных

```bash
# Проверка статуса контейнера БД
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml ps db

# Проверка настроек подключения
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py dbshell --command "SELECT version();"

# Перезапуск контейнера БД
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart db
```

### Проблема: Недоступен API

```bash
# Проверка работы Django
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py check --deploy

# Проверка портов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml port backend 8000

# Проверка Nginx конфигурации
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec nginx nginx -t
```

### Проблема: Недостаточно ресурсов

```bash
# Проверка использования памяти
free -h

# Проверка дискового пространства
df -h

# Очистка Docker
docker system prune -a
docker volume prune
```

## Мониторинг в production

### 1. Настройка мониторинга

Рекомендуется использовать следующие инструменты для мониторинга:

- **Prometheus + Grafana** для сбора метрик
- **ELK Stack** для централизованного логирования
- **Sentry** для отслеживания ошибок

### 2. Ключевые метрики для мониторинга

- Время ответа API
- Количество активных пользователей
- Использование CPU и памяти
- Дисковое пространство
- Количество запросов к базе данных
- Ошибки в логах

### 3. Настройка алертов

Настройте оповещения для следующих ситуаций:

- Сайт недоступен (> 5 минут)
- Время ответа API > 5 секунд
- Использование CPU > 80%
- Использование памяти > 80%
- Дисковое пространство < 10%
- Количество ошибок > 10 в минуту

## Заключение

Регулярное выполнение этих проверок поможет убедиться в стабильной работе платформы и своевременно выявлять проблемы. Рекомендуется автоматизировать эти проверки и настроить оповещения о сбоях.

Для дополнительной информации обратитесь к:
- [Полной документации по развертыванию](docker-server-setup.md)
- [Инструкции по быстрому развертыванию](quick-deployment.md)
- [Документации проекта](../../README.md)