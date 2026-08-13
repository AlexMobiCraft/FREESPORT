---
name: docker-test-run
description: >-
  Запускай backend-тесты FREESPORT в Docker-контейнере с PostgreSQL и Redis.
  Активируй при запросах "запусти тесты в докере", "docker test", "pytest через docker",
  "unit-тесты в контейнере", "интеграционные тесты docker".
---

# Docker Test Run Skill

Навык для запуска backend-тестов FREESPORT через Docker с полным окружением (PostgreSQL, Redis).

> **`--env-file` для `docker-compose.test.yml` не указывается.** Файла `docker/.env` в репозитории
> нет (`.env` лежит в корне), и с ним команды падают на `couldn't find env file`. Он и не нужен:
> в `docker-compose.test.yml` нет ни одной подстановки переменных — имя проекта, пароли и порты
> 5433/6380 зашиты литералами. Побочная выгода: команды работают в worktree, где `.env` нет.
> Канонический вид всех команд — `Makefile`, цели `test*`.

## Быстрый старт

### Все тесты (с пересборкой)
```powershell
cd docker
docker compose -p freesport-test -f docker-compose.test.yml down --remove-orphans --volumes
docker compose -p freesport-test -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend
docker compose -p freesport-test -f docker-compose.test.yml down
```

### Unit-тесты
```powershell
cd docker
docker compose -p freesport-test -f docker-compose.test.yml down --remove-orphans
docker compose -p freesport-test -f docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing
docker compose -p freesport-test -f docker-compose.test.yml down
```

### Интеграционные тесты
```powershell
cd docker
docker compose -p freesport-test -f docker-compose.test.yml down --remove-orphans
docker compose -p freesport-test -f docker-compose.test.yml run --rm backend pytest -v -m integration --cov=apps --cov-report=term-missing
docker compose -p freesport-test -f docker-compose.test.yml down
```

### Перф- и медленные тесты
```powershell
cd docker
docker compose -p freesport-test -f docker-compose.test.yml run --rm backend pytest -v -m performance
docker compose -p freesport-test -f docker-compose.test.yml run --rm backend pytest -v -m slow
docker compose -p freesport-test -f docker-compose.test.yml down
```

### Быстрый запуск (без пересборки образов)
```powershell
cd docker
docker compose -p freesport-test -f docker-compose.test.yml run --rm backend pytest -v --tb=short
```

### Запуск конкретного теста / файла
```powershell
cd docker
docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest apps/orders/tests/test_views.py -v --tb=short
```

## Pytest-маркеры проекта

**`unit` / `integration` / `performance` проставляются автоматически по каталогу теста** — руками
писать не нужно. Разметку делает хук `pytest_collection_modifyitems` в `backend/conftest.py`;
явный маркер в файле побеждает автоматический. `data_dependent` и `slow` ортогональны и ставятся
вручную. Подробности и таблица соответствия — `backend/docs/testing-standards.md`.

| Маркер | Назначение | Команда |
|--------|-----------|---------|
| `unit` | Модульные тесты приложения (`unit/` в пути либо всё под `apps/`) | `pytest -m unit` |
| `integration` | Интеграционные (`integration/`, `functional/`, `regression/`) | `pytest -m integration` |
| `performance` | Перф-тесты (`performance/`), выведены из PR-гейтов в nightly | `pytest -m performance` |
| `slow` | Таймингозависимые, ставится вручную; выведены из PR-гейтов в nightly | `pytest -m slow` |
| `data_dependent` | Тесты на реальных выгрузках 1С из `data/import_1c/` | `pytest -m "not data_dependent"` |

> ⚠️ `performance` и `slow` исключены из всех PR-гейтов и исполняются только в nightly
> `performance-tests.yml`. Падение nightly поднимает issue с меткой `nightly-failure`.

## Типичный рабочий процесс

1. **Перед PR**: запустить все тесты через `make test` (или Docker-команды выше)
2. **Разработка фичи**: запустить только unit-тесты `make test-unit`
3. **Проверка интеграции**: запустить `make test-integration`
4. **Быстрая проверка**: `make test-fast` (без пересборки)
5. **Перед правкой таймингозависимого кода**: `make test-performance` / `make test-slow` — в PR-гейтах их нет

## Альтернатива: Makefile

Если `make` доступен, используй короткие команды из корня проекта:

```powershell
make test              # Все тесты с пересборкой
make test-unit         # Только unit
make test-integration  # Только интеграционные
make test-performance  # Только перф-тесты
make test-slow         # Только медленные (маркер slow)
make test-fast         # Быстрый запуск без пересборки
```

## Важные нюансы для Windows

- **PowerShell chaining**: используй `;` вместо `&&` для объединения команд
- **Проектный контейнер**: команды должны выполняться из директории `docker/`
- **Переменные окружения**: `--env-file` тестовому compose не нужен (см. врезку выше). Настройки
  бэкенда приходят из `../backend/.env.test`, который `docker-compose.test.yml` читает сам
- **Очистка**: всегда выполняй `down` после тестов, чтобы освободить порты и volumes
- **`run --rm`, а не `exec`**: у сервиса `backend` в `docker-compose.test.yml` команда по умолчанию —
  `pytest`, контейнер отрабатывает и выходит. После любой test-команды подключаться `exec` не к чему

## Тестирование через Docker exec (если dev-среда уже запущена)

```powershell
# Запустить тесты в уже поднятом backend-контейнере dev-среды.
# Здесь exec уместен: контейнер работает постоянно, и --env-file нужен —
# в docker-compose.yml подстановки переменных есть.
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest <путь_к_тесту> -v
```

> [!WARNING]
> Не путай `docker-compose.test.yml` (изолированная тестовая среда, `run --rm`, без `--env-file`)
> и `docker-compose.yml` (dev-среда, `exec`, с `--env-file .env`).
> Для чистоты результатов CI-style тестирования используй `docker-compose.test.yml`.
