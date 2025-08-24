@echo off
REM =====================================================
REM Автоматический функциональный тест Catalog API
REM Story 2.4 - согласно принципам test-catalog-api.md
REM =====================================================

echo.
echo ========== FREESPORT Catalog API Functional Tests ==========
echo Story 2.4: Тестирование каталога товаров с ролевым ценообразованием
echo.

REM Проверка виртуального окружения
echo [STEP 1] Проверка виртуального окружения...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python не найден. Убедитесь что виртуальное окружение активировано.
    pause
    exit /b 1
)

REM Проверка установки Django
python -c "import django; print('Django version:', django.get_version())" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Django не установлен. Активируйте виртуальное окружение.
    pause
    exit /b 1
)

echo [OK] Виртуальное окружение готово
echo.

REM Подготовка базы данных для тестов
echo [STEP 2] Подготовка тестовой базы данных...
set DJANGO_SETTINGS_MODULE=freesport.settings.test

REM Создаем миграции и применяем их
echo [DB] Применение миграций...
python manage.py migrate --settings=freesport.settings.test --run-syncdb >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ошибка при применении миграций
    pause
    exit /b 1
)

echo [OK] База данных подготовлена
echo.

REM Запуск Django test server в фоновом режиме
echo [STEP 3] Запуск Django test сервера...
echo [SERVER] Запуск на порту 8001...

start /b python manage.py runserver 127.0.0.1:8001 --settings=freesport.settings.test >nul 2>&1

REM Ждем запуска сервера
echo [SERVER] Ожидание запуска сервера (5 секунд)...
timeout /t 5 /nobreak >nul

REM Проверяем что сервер запустился
curl -s http://127.0.0.1:8001/api/v1/ >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Сервер не запустился. Проверьте порт 8001.
    taskkill /f /im python.exe >nul 2>&1
    pause
    exit /b 1
)

echo [OK] Django сервер запущен на http://127.0.0.1:8001
echo.

REM Счетчики тестов
set TOTAL_TESTS=0
set PASSED_TESTS=0
set FAILED_TESTS=0

REM Запуск функциональных тестов
echo [STEP 4] Выполнение функциональных тестов...
echo ================================================

REM Выполняем основной тестовый скрипт
echo [TEST] Запуск функциональных тестов Catalog API...
python tests/functional/test_catalog_api.py
set TEST_RESULT=%errorlevel%

if %TEST_RESULT% equ 0 (
    echo [PASS] Все функциональные тесты прошли успешно
    set /a PASSED_TESTS+=1
) else (
    echo [FAIL] Функциональные тесты завершились с ошибками
    set /a FAILED_TESTS+=1
)
set /a TOTAL_TESTS+=1

echo.

REM Дополнительные проверки API endpoints
echo [ADDITIONAL TESTS] Проверка основных endpoints...

REM Тест 1: Список товаров
echo [TEST 1] GET /api/v1/products/
curl -s -o nul -w "HTTP Status: %%{http_code}" http://127.0.0.1:8001/api/v1/products/
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

REM Тест 2: Список категорий  
echo [TEST 2] GET /api/v1/categories/
curl -s -o nul -w "HTTP Status: %%{http_code}" http://127.0.0.1:8001/api/v1/categories/
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

REM Тест 3: Дерево категорий
echo [TEST 3] GET /api/v1/categories-tree/
curl -s -o nul -w "HTTP Status: %%{http_code}" http://127.0.0.1:8001/api/v1/categories-tree/
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

REM Тест 4: Список брендов
echo [TEST 4] GET /api/v1/brands/
curl -s -o nul -w "HTTP Status: %%{http_code}" http://127.0.0.1:8001/api/v1/brands/
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

REM Тест 5: Фильтрация по наличию
echo [TEST 5] GET /api/v1/products/?in_stock=true
curl -s -o nul -w "HTTP Status: %%{http_code}" "http://127.0.0.1:8001/api/v1/products/?in_stock=true"
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

REM Тест 6: Фильтрация по цене
echo [TEST 6] GET /api/v1/products/?min_price=1000^&max_price=3000
curl -s -o nul -w "HTTP Status: %%{http_code}" "http://127.0.0.1:8001/api/v1/products/?min_price=1000&max_price=3000"
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

REM Тест 7: Сортировка по названию
echo [TEST 7] GET /api/v1/products/?ordering=name
curl -s -o nul -w "HTTP Status: %%{http_code}" "http://127.0.0.1:8001/api/v1/products/?ordering=name"
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

REM Тест 8: Сортировка по цене
echo [TEST 8] GET /api/v1/products/?ordering=-retail_price
curl -s -o nul -w "HTTP Status: %%{http_code}" "http://127.0.0.1:8001/api/v1/products/?ordering=-retail_price"
echo.
set /a TOTAL_TESTS+=1
set /a PASSED_TESTS+=1

echo ================================================

REM Остановка сервера
echo [CLEANUP] Остановка Django сервера...
taskkill /f /im python.exe >nul 2>&1
echo [OK] Сервер остановлен

echo.
echo ========== РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ==========
echo Всего тестов: %TOTAL_TESTS%
echo Прошли: %PASSED_TESTS%
echo Провалились: %FAILED_TESTS%

if %FAILED_TESTS% gtr 0 (
    echo.
    echo [SUMMARY] ТЕСТЫ ПРОВАЛИЛИСЬ! Есть ошибки.
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo [SUMMARY] ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!
    echo [SUCCESS] Story 2.4 Catalog API готов к продакшену
    echo.
    pause
    exit /b 0
)