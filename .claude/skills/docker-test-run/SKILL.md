---
name: docker-test-run
description: >-
  Запускай backend-тесты FREESPORT в Docker-контейнере с PostgreSQL и Redis.
  Активируй при запросах "запусти тесты в докере", "docker test", "pytest через docker",
  "unit-тесты в контейнере", "интеграционные тесты docker".
---

# Docker Test Run Skill

Навык для запуска backend-тестов FREESPORT через Docker с полным окружением (PostgreSQL, Redis).

## Быстрый старт

### Все тесты (с пересборкой)
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down --remove-orphans --volumes
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down
```

### Unit-тесты
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down --remove-orphans
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down
```

### Интеграционные тесты
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down --remove-orphans
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest -v -m integration --cov=apps --cov-report=term-missing
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down
```

### Быстрый запуск (без пересборки образов)
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest -v --tb=short
```

### Запуск конкретного теста / файла
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest apps/orders/tests/test_views.py -v --tb=short
```

## Pytest-маркеры проекта

| Маркер | Назначение | Команда |
|--------|-----------|---------|
| `unit` | Юнит-тесты (модульные) | `pytest -m unit` |
| `integration` | Интеграционные тесты | `pytest -m integration` |
| `data_dependent` | Тесты с внешними данными | `pytest -m "not data_dependent"` |

## Типичный рабочий процесс

1. **Перед PR**: запустить все тесты через `make test` (или Docker-команды выше)
2. **Разработка фичи**: запустить только unit-тесты `make test-unit`
3. **Проверка интеграции**: запустить `make test-integration`
4. **Быстрая проверка**: `make test-fast` (без пересборки)

## Альтернатива: Makefile

Если `make` доступен, используй короткие команды из корня проекта:

```powershell
make test           # Все тесты с пересборкой
make test-unit      # Только unit
make test-integration # Только интеграционные
make test-fast      # Быстрый запуск
```

## Важные нюансы для Windows

- **PowerShell chaining**: используй `;` вместо `&&` для объединения команд
- **Проектный контейнер**: команды должны выполняться из директории `docker/`
- **Переменные окружения**: файл `.env` должен быть в корне проекта (docker-compose.test.yml читает `../backend/.env.test`)
- **Очистка**: всегда выполняй `down` после тестов, чтобы освободить порты и volumes

## Тестирование через Docker exec (если среда уже запущена)

```powershell
# Запустить тесты в уже поднятом backend-контейнере (dev-среда)
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest <путь_к_тесту> -v
```

> [!WARNING]
> Не путай `docker-compose.test.yml` (изолированная тестовая среда) и `docker-compose.yml` (dev-среда).
> Для чистоты результатов CI-style тестирования используй `docker-compose.test.yml`.
