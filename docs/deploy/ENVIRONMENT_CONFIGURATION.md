# Конфигурация окружений FREESPORT Platform

## Обзор

Проект FREESPORT использует две основные конфигурации окружений:
- **Локальная разработка** - для разработки на локальной машине
- **Продакшен** - для развертывания на сервере 5.35.124.149

## Структура конфигурационных файлов

### Локальная разработка
- **Переменные окружения:** `.env`
- **Docker Compose:** `docker/docker-compose.yml`
- **Настройки Django:** `backend/freesport/settings/development.py`

### Продакшен
- **Переменные окружения:** `.env.prod` (только образы)
- **Docker Compose:** `docker/docker-compose.prod.yml`
- **Настройки Django:** `backend/freesport/settings/production.py`
- **Основные переменные:** передаются через серверные переменные окружения

## Переменные окружения

### Обязательные переменные для локальной разработки (.env)

```bash
# === ОБЩИЕ НАСТРОЙКИ ===
DJANGO_ENVIRONMENT=development
SECRET_KEY=your-secret-key-here

# === НАСТРОЙКИ БАЗЫ ДАННЫХ ===
DB_NAME=freesport
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=db
DB_PORT=5432

# === REDIS CACHE ===
REDIS_PASSWORD=your-redis-password

# === CELERY SETTINGS ===
CELERY_BROKER_URL=redis://:your-redis-password@redis:6379/0

# === НАСТРОЙКИ ДОМЕНОВ ===
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# === НАСТРОЙКИ БЕЗОПАСНОСТИ ===
DEBUG=True
SECURE_SSL_REDIRECT=False
```

### Переменные для продакшена

Продакшен использует переменные окружения сервера. Основные переменные:

```bash
# === ОБЩИЕ НАСТРОЙКИ ===
DJANGO_SETTINGS_MODULE=freesport.settings.production
SECRET_KEY=production-secret-key

# === НАСТРОЙКИ БАЗЫ ДАННЫХ ===
DB_NAME=freesport
DB_USER=postgres
DB_PASSWORD=production-db-password
DB_HOST=db
DB_PORT=5432
DB_SSLMODE=prefer

# === REDIS CACHE ===
REDIS_PASSWORD=production-redis-password

# === НАСТРОЙКИ ДОМЕНОВ ===
ALLOWED_HOSTS=freesport.ru,www.freesport.ru,5.35.124.149
CORS_ALLOWED_ORIGINS=https://freesport.ru,https://www.freesport.ru

# === НАСТРОЙКИ БЕЗОПАСНОСТИ ===
DEBUG=False
SECURE_SSL_REDIRECT=True
```

## Использование конфигураций

### Локальная разработка

1. **Настройка .env файла:**
```bash
# Копирование шаблона
cp .env.example .env

# Редактирование
nano .env
```

2. **Запуск контейнеров:**
```bash
docker compose -f docker/docker-compose.yml up -d
```

3. **Проверка статуса:**
```bash
docker compose -f docker/docker-compose.yml ps
```

### Продакшен развертывание

1. **Настройка серверных переменных окружения:**
```bash
# На сервере 5.35.124.149
export DB_NAME=freesport
export DB_PASSWORD=production-db-password
export REDIS_PASSWORD=production-redis-password
# ... другие переменные
```

2. **Использование .env.prod:**
```bash
# .env.prod содержит только образы
BACKEND_IMAGE=ghcr.io/alexmobicraft/freesport/backend:v20251102-1542
FRONTEND_IMAGE=ghcr.io/alexmobicraft/freesport/frontend:v20251102-1542
```

3. **Запуск продакшен контейнеров:**
```bash
docker compose -f docker/docker-compose.prod.yml --env-file .env.prod up -d
```

## Важные замечания

### Безопасность
- Никогда не храните продакшен пароли в Git
- Используйте разные пароли для разработки и продакшена
- Регулярно меняйте SECRET_KEY в продакшене

### Совместимость
- Убедитесь, что версии образов в .env.prod соответствуют актуальным
- Проверяйте совместимость версий PostgreSQL и Redis
- Тестируйте изменения в локальной среде перед продакшеном

### Мониторинг
- Используйте `docker compose logs` для отладки
- Проверяйте health check статусы
- Мониторьте использование ресурсов

## Решение проблем

### Ошибки аутентификации
```bash
# Проверьте переменные окружения
docker compose exec backend env | grep -E "(DB_|REDIS_)"

# Проверьте подключение к БД
docker compose exec db psql -U postgres -d freesport
```

### Ошибки сети
```bash
# Проверьте сеть Docker
docker network ls | grep freesport

# Проверьте разрешение имен
docker compose exec backend ping db
docker compose exec backend ping redis
```

### Проблемы с переменными
```bash
# Показать все переменные контейнера
docker compose exec backend env

# Проверить конкретные переменные
docker compose exec backend printenv | grep DB_PASSWORD
```

## Автоматизация

### Скрипты для локальной разработки
```bash
# Полная перезагрузка с очисткой
make clean && make up

# Запуск тестов
make test

# Форматирование кода
make format
```

### Скрипты для продакшена
Используйте скрипты из `scripts/server/`:
- `update_server_code.ps1` - обновление кода на сервере
- `deploy_production.ps1` - развертывание продакшена

## Дополнительная информация

- [Docker Configuration](docker-configuration.md)
- [Local Docker Setup](LOCAL_DOCKER_SETUP.md)
- [Docker Context Troubleshooting](docker-context-troubleshooting.md)