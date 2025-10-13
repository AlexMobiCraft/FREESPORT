# Makefile для FREESPORT Platform

.PHONY: help build up down test test-unit test-integration clean logs shell \
         format lint migrate createsuperuser collectstatic \
         docs-validate docs-search-obsolete docs-check-links docs-check-api docs-update-index

# По умолчанию показываем help
help:
	@echo "FREESPORT Platform - Доступные команды:"
	@echo ""
	@echo "Разработка:"
	@echo "  build          - Собрать все Docker образы"
	@echo "  up             - Запустить среду разработки"
	@echo "  down           - Остановить среду разработки"
	@echo "  logs           - Показать логи всех сервисов"
	@echo "  clean          - Очистить Docker volumes и образы"
	@echo ""
	@echo "Тестирование (PostgreSQL + Redis через Docker):"
	@echo "  test           - Запустить все тесты в Docker с PostgreSQL"
	@echo "  test-unit      - Запустить только unit-тесты"
	@echo "  test-integration - Запустить интеграционные тесты"
	@echo "  test-fast      - Быстрые тесты (без пересборки образов)"
	@echo ""
	@echo "Документация:"
	@echo "  docs-validate      - Полная валидация документации"
	@echo "  docs-search-obsolete - Поиск устаревших терминов"
	@echo "  docs-check-links   - Проверка кросс-ссылок"
	@echo "  docs-check-api     - Проверка покрытия API"
	@echo "  docs-update-index  - Обновление индекса документации"
	@echo "  docs-sync-api      - Сверка API (код ↔ docs)"
	@echo "  docs-sync-decisions - Сверка решений (docs ↔ код)"
	@echo "  docs-sync-all      - Выполнить все синхронизации"
	@echo "  docs-update-index-apply - Обновить индексы с записью"
	@echo ""
	@echo "Отладка:"
	@echo "  shell          - Открыть shell в backend контейнере"
	@echo "  db-shell       - Подключиться к базе данных"

# Сборка образов
build:
	docker-compose build

# Запуск среды разработки
up:
	docker-compose up -d

# Остановка среды разработки
down:
	docker-compose down

# Все тесты
test:
	@echo "Запуск всех тестов..."
	docker-compose -f docker-compose.test.yml down --remove-orphans --volumes
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend
	docker-compose -f docker-compose.test.yml down

# Unit-тесты
test-unit:
	@echo "Запуск unit-тестов..."
	docker-compose -f docker-compose.test.yml down --remove-orphans
	docker-compose -f docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing
	docker-compose -f docker-compose.test.yml down

# Интеграционные тесты
test-integration:
	@echo "Запуск интеграционных тестов..."
	docker-compose -f docker-compose.test.yml down --remove-orphans
	docker-compose -f docker-compose.test.yml run --rm backend pytest -v -m integration --cov=apps --cov-report=term-missing
	docker-compose -f docker-compose.test.yml down

# Быстрые тесты (без сборки образов)
test-fast:
	@echo "Быстрый запуск тестов (без пересборки)..."
	docker-compose -f docker-compose.test.yml run --rm backend pytest -v --tb=short

# Логи всех сервисов
logs:
	docker-compose logs -f

# Shell в backend контейнере
shell:
	docker-compose exec backend bash

# Подключение к БД
db-shell:
	docker-compose exec db psql -U freesport_user -d freesport

# Очистка Docker volumes и неиспользуемых образов
clean:
	@echo "Очистка Docker volumes и образов..."
	docker-compose down --volumes --remove-orphans
	docker-compose -f docker-compose.test.yml down --volumes --remove-orphans
	docker system prune -f
	docker volume prune -f

# Форматирование кода
format:
	docker-compose exec backend black .
	docker-compose exec backend isort .

# Линтинг кода
lint:
	docker-compose exec backend flake8 .
	docker-compose exec backend mypy .

# Миграции БД
migrate:
# Создание суперпользователя
createsuperuser:
	docker-compose exec backend python manage.py createsuperuser

# Сбор статических файлов
collectstatic:
	docker-compose exec backend python manage.py collectstatic --noinput

# Валидация документации
docs-validate:
	@echo "Валидация документации..."
	python scripts/docs_validator.py validate

# Поиск устаревших терминов
docs-search-obsolete:
	@echo "Поиск устаревших терминов..."
	python scripts/docs_validator.py obsolete

# Проверка кросс-ссылок
docs-check-links:
	@echo "Проверка кросс-ссылок..."
	python scripts/docs_validator.py cross-links

# Проверка покрытия API
docs-check-api:
	@echo "Проверка покрытия API..."
	python scripts/docs_validator.py api-coverage

# Обновление индекса документации
docs-update-index:
	@echo "Обновление индекса документации..."
	python scripts/docs_index_generator.py

# Синхронизация документации: API ↔ Views
docs-sync-api:
	@echo "Синхронизация API (код ↔ документация)..."
	python scripts/docs_sync.py api-sync

# Синхронизация документации: Decisions ↔ Код
docs-sync-decisions:
	@echo "Синхронизация решений (docs ↔ код)..."
	python scripts/docs_sync.py decisions-sync

# Синхронизация: все шаги
docs-sync-all:
	@echo "Полная синхронизация документации..."
	python scripts/docs_sync.py all

# Обновление индексов с применением изменений
docs-update-index-apply:
	@echo "Обновление индексов документации (apply)..."
	python scripts/docs_sync.py update-index --apply