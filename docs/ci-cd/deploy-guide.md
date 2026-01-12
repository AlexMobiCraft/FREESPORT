# 🚀 Руководство по деплою

## Обзор

Деплой FREESPORT Platform осуществляется через GitHub Actions workflow `deploy.yml`. В текущей конфигурации используется **одно production-окружение**; запуск workflow выполняется **вручную** через GitHub Actions или CLI.

## Архитектура деплоя

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Manual Trigger  │────▶│  Build Images   │────▶│  Deploy Server  │
│ (workflow run)  │     │  (GHCR)         │     │  (SSH)          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Health Check   │
                                               └─────────────────┘
```

## Требования

### GitHub Secrets

Для работы деплоя необходимо настроить следующие секреты в репозитории:

#### Репозиторий

| Secret | Описание |
|--------|----------|
| `SSH_PRIVATE_KEY` | Приватный ключ, которым GitHub Actions подключается по SSH |
| `NEXT_PUBLIC_API_URL` | URL API для frontend (
  например, `https://freesport.ru/api/v1`) |
| `CODECOV_TOKEN` | Токен Codecov (опционально) |

#### Production

| Secret | Описание |
|--------|----------|
| `PRODUCTION_SERVER_HOST` | IP или hostname production сервера |
| `PRODUCTION_SERVER_USER` | Пользователь SSH на production |
| `PRODUCTION_DEPLOY_PATH` | Путь к проекту на production |
| `PRODUCTION_URL` | URL production окружения (например, `https://freesport.ru`) |

### GitHub Environments

Используется environment **production** (можно добавить обязательное ручное подтверждение перед запуском).

## Способы запуска деплоя

### 1. Ручной через GitHub CLI

```bash
# Деплой на production
gh workflow run deploy.yml

# Hotfix без тестов (только для критических исправлений)
gh workflow run deploy.yml -f skip_tests=true
```

### 2. Через GitHub UI

1. Перейдите в **Actions** → **Deploy to Server**
2. Нажмите **Run workflow**
3. (Опционально) отметьте `skip_tests`
4. Нажмите **Run workflow**

## Процесс деплоя

Процесс един для production окружения:

1. **Тестирование** — полный набор тестов
2. **Сборка образов** — Docker images с тегом `production`
3. **Backup** — резервное копирование базы данных
4. **Деплой** — zero-downtime обновление контейнеров
5. **Health check** — расширенная проверка работоспособности
6. **Уведомление** — создание issue при ошибках

## Конфигурации Nginx

Проект использует **две различные конфигурации Nginx**:

| Файл | Окружение | Особенности |
|------|-----------|-------------|
| `docker/nginx/conf.d/local.conf` | Development | HTTP only, localhost |
| `docker/nginx/conf.d/default.conf` | Production | HTTPS, SSL (LetsEncrypt), freesport.ru |

### Монтирование в Docker Compose

- **`docker-compose.yml`** (dev):
  ```yaml
  volumes:
    - ./nginx/conf.d/local.conf:/etc/nginx/conf.d/default.conf:ro
  ```

- **`docker-compose.prod.yml`** (prod):
  ```yaml
  volumes:
    - ./nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
  ```

> ⚠️ **Важно**: Workflow всегда использует `docker-compose.prod.yml`, поэтому убедитесь, что все production-конфигурации актуальны.

## Структура на сервере

```
/opt/freesport/
├── backend/
├── frontend/
├── docker/
│   ├── docker-compose.prod.yml
│   └── nginx/
│       ├── nginx.conf
│       └── conf.d/
│           ├── default.conf    # Production (HTTPS)
│           └── local.conf      # Development (HTTP)
├── data/
│   └── prod/
│       ├── static/
│       └── media/
├── backups/
│   └── backup_YYYYMMDD_HHMMSS.sql
├── .env.prod
└── logs/
```

## Файл окружения (.env.prod)

```bash
# Database
DB_NAME=freesport
DB_USER=postgres
DB_PASSWORD=<secure_password>

# Redis
REDIS_PASSWORD=<secure_password>

# Django
SECRET_KEY=<secure_key>
CORS_ALLOWED_ORIGINS=https://freesport.ru,https://www.freesport.ru

# Frontend
NEXT_PUBLIC_API_URL=https://freesport.ru/api/v1

# Docker images
BACKEND_IMAGE=ghcr.io/alexmobicraft/freesport/backend:production
FRONTEND_IMAGE=ghcr.io/alexmobicraft/freesport/frontend:production

# 1C Integration
ONEC_DATA_DIR=/opt/freesport/data/import_1c
```

## Откат (Rollback)

### Быстрый откат

```bash
# SSH на сервер
ssh user@server

# Откат к предыдущему образу
cd /opt/freesport
docker compose -f docker/docker-compose.prod.yml down
export BACKEND_IMAGE=ghcr.io/alexmobicraft/freesport/backend:<previous_tag>
export FRONTEND_IMAGE=ghcr.io/alexmobicraft/freesport/frontend:<previous_tag>
docker compose -f docker/docker-compose.prod.yml up -d
```

### Восстановление базы данных

```bash
# Список бэкапов
ls -la /home/freesport/freesport/backups/

# Восстановление
docker compose -f docker/docker-compose.prod.yml exec -T db \
  psql -U postgres -d freesport < backups/backup_YYYYMMDD_HHMMSS.sql
```

## Мониторинг

### Проверка статуса контейнеров

```bash
docker compose -f docker/docker-compose.prod.yml ps
```

### Просмотр логов

```bash
# Все сервисы
docker compose -f docker/docker-compose.prod.yml logs -f

# Конкретный сервис
docker compose -f docker/docker-compose.prod.yml logs -f backend
```

### Health check скрипт

```bash
./scripts/deploy/health-check.sh
```

## Устранение неполадок

### Деплой завершился с ошибкой

1. Проверьте логи в GitHub Actions
2. Проверьте SSH подключение к серверу
3. Проверьте наличие всех секретов
4. Проверьте статус контейнеров на сервере

### Контейнер не запускается

```bash
# Проверка логов
docker compose -f docker/docker-compose.prod.yml logs backend

# Проверка конфигурации
docker compose -f docker/docker-compose.prod.yml config
```

### База данных недоступна

```bash
# Проверка статуса PostgreSQL
docker compose -f docker/docker-compose.prod.yml exec db pg_isready

# Перезапуск
docker compose -f docker/docker-compose.prod.yml restart db
```

---

*Последнее обновление: 2024-11-28*
