# Makefile для FREESPORT Platform

.PHONY: help build up down test test-unit test-integration clean logs shell

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
	@echo "Тестирование:"
	@echo "  test           - Запустить все тесты в Docker"
	@echo "  test-unit      - Запустить только unit-тесты"
	@echo "  test-integration - Запустить интеграционные тесты"
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
	docker-compose exec backend python manage.py migrate

# Создание суперпользователя
createsuperuser:
	docker-compose exec backend python manage.py createsuperuser

# Сбор статических файлов
collectstatic:
	docker-compose exec backend python manage.py collectstatic --noinput