@echo off
:: Скрипт для запуска тестов FREESPORT Platform в Docker (Windows)
echo ===============================================
echo FREESPORT Platform - Запуск тестов в Docker
echo ===============================================

:: Проверка наличия Docker
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Docker не найден. Установите Docker Desktop.
    pause
    exit /b 1
)

:: Проверка наличия Docker Compose
where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Docker Compose не найден.
    pause
    exit /b 1
)

:: Переход в корневую директорию проекта
cd /d "%~dp0\.."

echo [INFO] Остановка и удаление предыдущих тестовых контейнеров...
docker-compose -f docker-compose.test.yml down --remove-orphans --volumes

echo [INFO] Сборка тестовых образов...
docker-compose -f docker-compose.test.yml build --no-cache

echo [INFO] Запуск тестовой среды...
docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from backend

:: Сохранение кода выхода
set TEST_EXIT_CODE=%errorlevel%

echo [INFO] Остановка тестовых контейнеров...
docker-compose -f docker-compose.test.yml down

:: Копирование отчетов о покрытии кода (если существуют)
if exist htmlcov rmdir /s /q htmlcov
docker run --rm -v freesport_test_coverage:/coverage -v "%cd%":/host alpine cp -r /coverage/. /host/htmlcov/ 2>nul

echo ===============================================
if %TEST_EXIT_CODE% equ 0 (
    echo [УСПЕХ] Все тесты прошли успешно!
    echo [INFO] Отчет о покрытии кода: htmlcov/index.html
) else (
    echo [ОШИБКА] Тесты завершились с ошибками (код: %TEST_EXIT_CODE%)
)
echo ===============================================

pause
exit /b %TEST_EXIT_CODE%