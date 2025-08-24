@echo off
:: Скрипт для запуска только unit-тестов FREESPORT Platform в Docker
cd /d "%~dp0\.."

echo [INFO] Запуск только unit-тестов...

docker-compose -f docker-compose.test.yml down --remove-orphans
docker-compose -f docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing
docker-compose -f docker-compose.test.yml down

pause