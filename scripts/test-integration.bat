@echo off
:: Скрипт для запуска интеграционных тестов FREESPORT Platform в Docker
cd /d "%~dp0\.."

echo [INFO] Запуск интеграционных тестов...

docker-compose -f docker-compose.test.yml down --remove-orphans
docker-compose -f docker-compose.test.yml run --rm backend pytest -v -m integration --cov=apps --cov-report=term-missing
docker-compose -f docker-compose.test.yml down

pause