# Тестирование в Docker для FREESPORT Platform

## Обзор

⚠️ **КРИТИЧЕСКИ ВАЖНО**: Тестирование выполняется ТОЛЬКО с PostgreSQL через Docker Compose!

Данное руководство описывает настройку и использование Docker-based тестирования для FREESPORT Platform, включая unit, integration и end-to-end тесты.

## Важные изменения

## Архитектура тестирования

### Тестовая среда vs Среда разработки

| Аспект | Разработка | Тестирование |
|--------|------------|-------------|
| **Порты** | 5432, 6379, 8001 | 5433, 6380 |
| **Сеть** | freesport-network | freesport-test-network |
| **БД** | PostgreSQL persistent | PostgreSQL tmpfs |
| **Redis** | Persistent, AOF | In-memory, no persistence |
| **Образ** | Dockerfile | Dockerfile.test |
| **Команда** | gunicorn | pytest |

### Тестовые контейнеры

```
┌─────────────────────────────────────────────────────────────────┐
│                    Тестовая изоляция                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌─────────────────┐   ┌────────────────┐   │
│  │ backend-test │───►│ test-db:5432    │   │ test-redis:6379│   │
│  │ (pytest)    │    │ (PostgreSQL)    │   │ (Redis)        │   │
│  │              │    │ tmpfs:/tmp      │   │ tmpfs:/data    │   │
│  └──────────────┘    └─────────────────┘   └────────────────┘   │
│                                                                 │
│  Volumes: test_postgres_data, test_coverage                     │
│  Network: freesport-test-network (изолированная)               │
└─────────────────────────────────────────────────────────────────┘
```

## Быстрый старт

### Запуск всех тестов

```bash
# Рекомендуемый способ - через Make
make test

# Или напрямую через Docker Compose
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Windows скрипт
scripts\test.bat

# Linux/macOS скрипт  
./scripts/test.sh
```

### Запуск конкретных типов тестов

```bash
# Только unit тесты
make test-unit

# Только integration тесты  
make test-integration

# Быстрые тесты (без пересборки)
make test-fast
```

## Конфигурация тестовых сервисов

### PostgreSQL тестовая БД

```yaml
# docker-compose.test.yml
db:
  image: postgres:15-alpine
  container_name: freesport-test-db
  environment:
    POSTGRES_DB: freesport_test
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: password123
  ports:
    - "5433:5432"  # Избегаем конфликта с основной БД
  tmpfs:
    - /tmp         # Ускоряем временные операции
  shm_size: 256mb  # Больше памяти для PostgreSQL
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres -d freesport_test"]
    interval: 10s  # Быстрее проверки
    timeout: 5s
    retries: 5
```

### Redis тестовый кеш

```yaml
redis:
  image: redis:7-alpine
  container_name: freesport-test-redis
  command: redis-server --appendonly no --save "" --requirepass redis123
  ports:
    - "6380:6379"  # Избегаем конфликта с основным Redis
  tmpfs:
    - /data        # Всё в памяти для скорости
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "redis123", "ping"]
    interval: 10s
    timeout: 3s
    retries: 5
```

### Backend тестовый контейнер

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile.test
  container_name: freesport-backend-test
  environment:
    - DJANGO_SETTINGS_MODULE=freesport.settings.test
    - SECRET_KEY=test-secret-key-for-testing-only
    - DB_HOST=db
    - DB_NAME=freesport_test
    - REDIS_URL=redis://:redis123@redis:6379/1
    - PYTEST_CURRENT_TEST=1
    - PYTHONUNBUFFERED=1
  command: ["pytest", "-v", "--cov=apps", "--cov-report=html", "--cov-report=term"]
  volumes:
    - ./backend:/app
    - test_coverage:/app/htmlcov
```

## Dockerfile.test оптимизации

### Базовые оптимизации

```dockerfile
# backend/Dockerfile.test
FROM python:3.12-slim

# Системные зависимости включая инструменты отладки
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    gettext \
    git \
    curl \
    # Инструменты для отладки в тестовой среде
    procps \
    vim-tiny

# Дополнительные тестовые инструменты
RUN pip install --no-cache-dir \
    pytest-xdist \      # Параллельные тесты
    pytest-mock \       # Улучшенные моки  
    pytest-env \        # Environment variables
    pytest-sugar \      # Красивый вывод
    pytest-clarity      # Лучшие assert diff'ы

# Директории для тестовых артефактов
RUN mkdir -p /app/test-reports /app/htmlcov /app/test-logs
```

### Команды по умолчанию

```dockerfile
# Команда с оптимальными параметрами
CMD ["pytest", 
     "-v",                          # Verbose вывод
     "--tb=short",                  # Краткие traceback'и  
     "--cov=apps",                  # Покрытие кода
     "--cov-report=html",           # HTML отчет
     "--cov-report=term-missing",   # Terminal отчет
     "--cov-fail-under=70"]         # Минимальное покрытие
```

## Настройки Django для тестов

### Адаптивные настройки БД

```python
# backend/freesport/settings/test.py
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'freesport_test'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password123'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'TEST': {
            'NAME': 'test_' + os.environ.get('DB_NAME', 'freesport_test'),
        },
    }
}
```

### Адаптивные настройки кеша

```python
if os.environ.get('REDIS_URL'):
    # Redis кеш для Docker тестов
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'freesport_test'
        }
    }
else:
    # Локальный кеш в памяти
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
```

## Продвинутые возможности тестирования

### Параллельные тесты с pytest-xdist

```bash
# В Dockerfile.test или локально
pytest -n auto  # Авто-определение количества процессов
pytest -n 4     # 4 параллельных процесса
```

### Категорированные тесты

```python
# pytest.ini
[tool:pytest]
markers =
    unit: Unit tests (isolated, fast)
    integration: Integration tests (database, external services)
    slow: Slow tests (long-running operations)
    api: API endpoint tests
    models: Django model tests
```

```bash
# Запуск по категориям
pytest -m unit                    # Только unit тесты
pytest -m "integration and not slow"  # Интеграционные, но не медленные
pytest -m "not slow"             # Всё кроме медленных тестов
```

### Покрытие кода

```bash
# Генерация отчетов покрытия
pytest --cov=apps --cov-report=html --cov-report=term-missing

# Проверка минимального покрытия
pytest --cov=apps --cov-fail-under=80

# Покрытие с исключениями
pytest --cov=apps --cov-report=term-missing --cov-config=.coveragerc
```

## Скрипты автоматизации

### Windows скрипт (scripts/test.bat)

```batch
@echo off
echo [INFO] Запуск тестов FREESPORT Platform в Docker...

:: Остановка предыдущих контейнеров
docker-compose -f docker-compose.test.yml down --remove-orphans --volumes

:: Сборка тестовых образов
docker-compose -f docker-compose.test.yml build --no-cache

:: Запуск тестов
docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from backend

:: Сохранение кода выхода
set TEST_EXIT_CODE=%errorlevel%

:: Остановка контейнеров
docker-compose -f docker-compose.test.yml down

:: Копирование отчетов
docker run --rm -v freesport_test_coverage:/coverage -v "%cd%":/host alpine cp -r /coverage/. /host/htmlcov/ 2>nul

if %TEST_EXIT_CODE% equ 0 (
    echo [УСПЕХ] Все тесты прошли успешно!
) else (
    echo [ОШИБКА] Тесты завершились с ошибками
)

exit /b %TEST_EXIT_CODE%
```

### Linux/macOS скрипт (scripts/test.sh)

```bash
#!/bin/bash
set -e

echo "[INFO] Запуск тестов FREESPORT Platform в Docker..."

# Переход в корневую директорию
cd "$(dirname "$0")/.."

# Остановка предыдущих контейнеров
docker-compose -f docker-compose.test.yml down --remove-orphans --volumes

# Сборка и запуск тестов
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend

TEST_EXIT_CODE=$?

# Очистка
docker-compose -f docker-compose.test.yml down

# Копирование отчетов
docker run --rm -v freesport_test_coverage:/coverage -v "$(pwd)":/host alpine sh -c "cp -r /coverage/. /host/htmlcov/ 2>/dev/null || true"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "[УСПЕХ] Все тесты прошли успешно!"
    echo "[INFO] Отчет о покрытии: htmlcov/index.html"
else
    echo "[ОШИБКА] Тесты завершились с ошибками"
fi

exit $TEST_EXIT_CODE
```

## Makefile команды

```makefile
# Все тесты
test:
	docker-compose -f docker-compose.test.yml down --remove-orphans --volumes
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend
	docker-compose -f docker-compose.test.yml down

# Unit тесты
test-unit:
	docker-compose -f docker-compose.test.yml down --remove-orphans
	docker-compose -f docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing
	docker-compose -f docker-compose.test.yml down

# Интеграционные тесты
test-integration:
	docker-compose -f docker-compose.test.yml down --remove-orphans
	docker-compose -f docker-compose.test.yml run --rm backend pytest -v -m integration --cov=apps --cov-report=term-missing
	docker-compose -f docker-compose.test.yml down

# Быстрые тесты (без пересборки)
test-fast:
	docker-compose -f docker-compose.test.yml run --rm backend pytest -v --tb=short
```

## Мониторинг и отладка тестов

### Логи и вывод

```bash
# Просмотр логов тестов
docker-compose -f docker-compose.test.yml logs backend

# Запуск с подробными логами
docker-compose -f docker-compose.test.yml up --build

# Отладка конкретного теста
docker-compose -f docker-compose.test.yml run --rm backend pytest -v -s tests/test_specific.py::test_function
```

### Отладка в интерактивном режиме

```bash
# Shell в тестовом контейнере
docker-compose -f docker-compose.test.yml run --rm backend bash

# Подключение к тестовой БД
docker-compose -f docker-compose.test.yml exec db psql -U postgres -d freesport_test

# Проверка Redis
docker-compose -f docker-compose.test.yml exec redis redis-cli -a redis123
```

### Производительность тестов

```bash
# Профилирование тестов
pytest --durations=10         # 10 самых медленных тестов
pytest --durations=0          # Все тесты с временем

# Параллельное выполнение
pytest -n auto               # Автоматически по количеству CPU
pytest -n 4                  # 4 процесса

# Остановка на первой ошибке
pytest -x                    # Stop on first failure
pytest --maxfail=3           # Stop after 3 failures
```

## Интеграция с CI/CD

### GitHub Actions

```yaml
# .github/workflows/backend-tests.yml
- name: Запуск тестов в Docker
  run: |
    make test
    
- name: Загрузка отчетов покрытия
  uses: actions/upload-artifact@v4
  with:
    name: coverage-reports
    path: htmlcov/
```

### Отчеты покрытия кода

```bash
# Генерация отчетов для CI
pytest --cov=apps --cov-report=xml --cov-report=html

# Отправка в Codecov
codecov -f coverage.xml
```

## Решение проблем

### Частые проблемы

**1. Контейнеры не останавливаются**
```bash
# Принудительная остановка
docker-compose -f docker-compose.test.yml down --remove-orphans --volumes
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
```

**2. Проблемы с портами**
```bash
# Проверка занятых портов
netstat -tulpn | grep :5433
lsof -i :5433

# Использование других портов
# Отредактируйте docker-compose.test.yml
```

**3. Ошибки БД подключения**
```bash
# Проверка health check
docker-compose -f docker-compose.test.yml ps

# Логи БД
docker-compose -f docker-compose.test.yml logs db

# Ручная проверка подключения
docker-compose -f docker-compose.test.yml exec db pg_isready -U postgres -d freesport_test
```

**4. Медленные тесты**
```bash
# Профилирование
pytest --durations=10

# Использование tmpfs
# Уже настроено в docker-compose.test.yml

# Параллельные тесты
pytest -n auto
```

**5. Проблемы с покрытием кода**
```bash
# Проверка конфигурации покрытия
cat .coveragerc

# Исключение файлов
pytest --cov=apps --cov-report=term-missing --cov-config=.coveragerc
```

## Лучшие практики

### Структура тестов

```
backend/tests/
├── unit/                  # Быстрые изолированные тесты
│   ├── test_models.py    # Тесты моделей
│   ├── test_serializers.py
│   └── test_utils.py
├── integration/           # Тесты с БД и внешними сервисами
│   ├── test_api_views.py
│   ├── test_database.py
│   └── test_cache.py
└── legacy/               # Устаревшие тесты для рефакторинга
```

### Маркировка тестов

```python
import pytest

@pytest.mark.unit
def test_model_creation():
    """Быстрый unit тест."""
    pass

@pytest.mark.integration
@pytest.mark.django_db
def test_api_endpoint():
    """Интеграционный тест с БД."""
    pass

@pytest.mark.slow
def test_complex_calculation():
    """Медленный тест."""
    pass
```

### Factory Boy для тестовых данных

```python
# tests/factories.py
import factory
from apps.users.models import User

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.LazyAttribute(lambda obj: obj.email.split('@')[0])
    is_active = True

# Использование в тестах
def test_user_creation():
    user = UserFactory()
    assert user.email is not None
```

## Заключение

Docker-based тестирование для FREESPORT Platform обеспечивает:

- ✅ **Изоляцию** - отдельная среда для тестов
- ✅ **Консистентность** - одинаковая среда везде  
- ✅ **Скорость** - оптимизация с tmpfs и параллелизм
- ✅ **Покрытие** - автоматические отчеты покрытия кода
- ✅ **CI/CD Ready** - готова для автоматизации

Используйте `make test` для ежедневной разработки и специализированные команды для конкретных задач.