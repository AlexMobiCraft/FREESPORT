# Docker Configuration для FREESPORT Platform

## Обзор

Данная документация описывает Docker конфигурацию FREESPORT Platform, включая настройки разработки, тестирования и развертывания.

## Архитектура контейнеров

### Основные сервисы (docker-compose.yml)

```text
┌─────────────────────────────────────────────────────────────────┐
│                      FREESPORT Platform                        │
├─────────────────────────────────────────────────────────────────┤
│  nginx:80,443 ──┬─► backend:8000 (Django API)                  │
│                 └─► frontend:3000 (Next.js)                    │
│                                                                 │
│  backend:8001 ──► db:5432 (PostgreSQL)                        │
│              └──► redis:6379 (Кеш и сессии)                   │
└─────────────────────────────────────────────────────────────────┘
```

**Сервисы:**

- **nginx** - Reverse proxy, статические файлы, load balancing
- **backend** - Django REST API (порт 8001 → 8000)
- **frontend** - Next.js SSR/SSG приложение (порт 3000)
- **db** - PostgreSQL 15 база данных (порт 5432)
- **redis** - Redis кеш и очереди (порт 6379)

### Тестовые сервисы (docker-compose.test.yml)

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Тестовая среда                               │
├─────────────────────────────────────────────────────────────────┤
│  backend-test ──► test-db:5432 (PostgreSQL тесты)             │
│               └──► test-redis:6379 (Redis тесты)              │
│                                                                 │
│  Отдельная сеть: freesport-test-network                       │
│  Отдельные порты: 5433, 6380                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Ключевые особенности:**

- Изолированная тестовая среда
- Отдельные порты для предотвращения конфликтов
- Оптимизированные настройки для быстрых тестов
- Временные тома (tmpfs) для ускорения

## Файловая структура Docker

```text
freesport/
├── docker-compose.yml          # Основная среда разработки
├── docker-compose.test.yml     # Тестовая среда
├── Makefile                    # Команды автоматизации
├── backend/
│   ├── Dockerfile              # Production образ Django
│   ├── Dockerfile.test         # Тестовый образ Django
│   └── .dockerignore          # Игнорируемые файлы
├── docker/
│   └── nginx/
│       ├── nginx.conf         # Главная конфигурация Nginx
│       └── conf.d/
│           └── default.conf   # Виртуальный хост
└── scripts/
    ├── test.sh               # Скрипт тестирования Unix
    └── test.bat              # Скрипт тестирования Windows
```

## Основные исправления (23.08.2025)

### 🔴 Решенные критические проблемы

#### 1. Унификация настроек БД

**Проблема:** Тестовая среда не соответствовала production-конфигурации

**Решение:** Во всех окружениях используется PostgreSQL с параметрами из `.env`

#### 2. Отсутствующие сервисы в тестовой среде

**Проблема:** docker-compose.test.yml не содержал db и redis сервисы

**Решение:** Добавлена полная тестовая среда с:

- PostgreSQL с оптимизацией для тестов (tmpfs, shm_size)
- Redis без персистентности (tmpfs)
- Изолированная сеть freesport-test-network
- Отдельные порты (5433, 6380)

#### 3. Отсутствующая nginx конфигурация

**Проблема:** Ссылки на несуществующие файлы nginx

**Решение:** Созданы полные конфигурации:

- `docker/nginx/nginx.conf` - основная конфигурация
- `docker/nginx/conf.d/default.conf` - виртуальный хост

#### 4. Конфликт портов 8000

**Проблема:** Конфликт с другими службами на порту 8000

**Решение:** Django сервер теперь доступен на порту 8001:

- Обновлены все docker-compose файлы
- Исправлены frontend конфигурации
- Обновлена документация и CI/CD

## Конфигурация портов

### Основная среда

| Сервис   | Внутренний | Внешний | Описание         |
| -------- | ---------- | ------- | ---------------- |
| nginx    | 80, 443    | 80, 443 | HTTP/HTTPS proxy |
| backend  | 8000       | 8001    | Django API       |
| frontend | 3000       | 3000    | Next.js app      |
| db       | 5432       | 5432    | PostgreSQL       |
| redis    | 6379       | 6379    | Redis cache      |

### Тестовая среда

| Сервис     | Внутренний | Внешний | Описание         |
| ---------- | ---------- | ------- | ---------------- |
| test-db    | 5432       | 5433    | PostgreSQL тесты |
| test-redis | 6379       | 6380    | Redis тесты      |

## Команды использования

### Make команды

```bash
# Разработка
make build          # Собрать образы
make up             # Запустить среду разработки
make down           # Остановить среду
make logs           # Показать логи
make clean          # Очистить volumes и образы

# Тестирование
make test           # Все тесты в Docker
make test-unit      # Unit тесты
make test-integration # Интеграционные тесты
make test-fast      # Быстрые тесты без сборки

# Отладка
make shell          # Shell в backend контейнере
make db-shell       # Подключение к БД

# Разработка
make format         # Форматирование кода
make lint           # Проверка кода
make migrate        # Миграции БД
```

### Скрипты автоматизации

**Windows:**

```cmd
scripts\test.bat
scripts\test-unit.bat
scripts\test-integration.bat
```

**Linux/macOS:**

```bash
./scripts/test.sh
```

## Особенности тестовой среды

### Dockerfile.test оптимизации

```dockerfile
# Дополнительные тестовые инструменты
RUN pip install --no-cache-dir \
    pytest-xdist \
    pytest-mock \
    pytest-env \
    pytest-sugar \
    pytest-clarity

# Директории для тестовых артефактов
RUN mkdir -p /app/test-reports /app/htmlcov /app/test-logs

# Команда по умолчанию с покрытием кода
CMD ["pytest", "-v", "--tb=short", "--cov=apps",
     "--cov-report=html", "--cov-report=term-missing",
     "--cov-fail-under=70"]
```

### PostgreSQL тестовые оптимизации

```yaml
# docker-compose.test.yml
db:
  tmpfs:
    - /tmp
  shm_size: 256mb
  healthcheck:
    interval: 10s # Быстрее чем в основной среде
    timeout: 5s
    retries: 5
```

### Redis тестовые настройки

```yaml
redis:
  command: redis-server --appendonly no --save "" --requirepass redis123
  tmpfs:
    - /data # В памяти для скорости
```

## Переменные окружения

### Основная среда

> Значения ниже — dev-дефолты. На production пароли задаются через `.env.prod` (см. `.env.prod.example`).

```env
# Backend
DJANGO_SETTINGS_MODULE=freesport.settings.development
SECRET_KEY=development-secret-key
DB_HOST=db
DB_NAME=freesport
REDIS_URL=redis://:redis123@redis:6379/0

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
NODE_ENV=development
```

### Тестовая среда

```env
# Backend
DJANGO_SETTINGS_MODULE=freesport.settings.test
SECRET_KEY=test-secret-key-for-testing-only
DB_HOST=db
DB_NAME=freesport_test
REDIS_URL=redis://:redis123@redis:6379/1
PYTEST_CURRENT_TEST=1
```

## Мониторинг и отладка

### Health Checks

Все сервисы имеют health check'и:

- **PostgreSQL:** `pg_isready`
- **Redis:** `redis-cli ping`
- **Django:** `python manage.py check`
- **Next.js:** HTTP проверка `/api/health`

### Логи и отладка

```bash
# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f backend

# Shell в контейнере
docker compose exec backend bash

# Подключение к БД
docker compose exec db psql -U postgres -d freesport
```

### Volumes и данные

```bash
# Просмотр volumes
docker volume ls | grep freesport

# Очистка тестовых данных
docker compose --env-file .env -f docker-compose.test.yml down --volumes

# Бэкап БД (для разработки)
docker compose exec db pg_dump -U postgres freesport > backup.sql
```

## Производительность и оптимизация

### .dockerignore для быстрой сборки

```gitignore
# backend/.dockerignore
.pytest_cache
__pycache__
*.pyc
.coverage
htmlcov/
node_modules/
.git
```

### Кеширование слоев Docker

```dockerfile
# Копируем зависимости сначала для кеширования
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем код потом
COPY . .
```

### Многостадийная сборка

```dockerfile
# Стадия сборки зависимостей
FROM python:3.12-slim as builder
RUN python -m venv /opt/venv
COPY --from=builder /opt/venv /opt/venv

# Продакшен стадия
FROM python:3.12-slim as production
COPY --from=builder /opt/venv /opt/venv
```

## Безопасность

### Пользователи контейнеров

```dockerfile
# Создание непривилегированного пользователя
RUN groupadd -r freesport && useradd -r -g freesport freesport
USER freesport
```

### Настройки Nginx

```nginx
# Базовые заголовки безопасности
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header X-Content-Type-Options "nosniff" always;
```

## Решение проблем

### Частые проблемы и решения

**1. Порты заняты**

```bash
# Найти процессы на портах
netstat -tulpn | grep :8001
lsof -i :8001

# Остановить все Docker контейнеры
docker-compose down
docker stop $(docker ps -aq)
```

**2. Ошибки разрешений**

```bash
# Исправить права на папки
sudo chown -R $USER:$USER .
chmod -R 755 scripts/
```

**3. Проблемы с БД подключением**

```bash
# Проверить health check БД
docker compose ps
docker compose exec db pg_isready -U postgres
```

**4. Проблемы с Redis**

```bash
# Проверить Redis подключение
docker compose exec redis redis-cli -a redis123 ping
```

## Дополнительные ресурсы

- [Docker Compose официальная документация](https://docs.docker.com/compose/)
- [Django в Docker best practices](https://docs.docker.com/samples/django/)
- [Next.js Docker deployment](https://nextjs.org/docs/deployment#docker-image)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Redis Docker](https://hub.docker.com/_/redis)
