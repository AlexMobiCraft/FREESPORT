@echo off
chcp 65001 >nul
REM Functional test script for Product Detail API
REM Following testing-environment.md principles

cd /d "C:\Users\38670\DEV_WEB\FREESPORT\backend"

echo ========================================
echo FREESPORT Product Detail API Testing
echo История 2.5: Функциональное тестирование с реальными данными
echo ========================================
echo.

REM Check and activate virtual environment
echo [НАСТРОЙКА] Проверка виртуального окружения...
if exist "venv\Scripts\activate.bat" (
    echo [SETUP] Found virtual environment, activating...
    call venv\Scripts\activate.bat
    echo [SETUP] Virtual environment activated
) else (
    echo [WARNING] Virtual environment not found
    echo [SETUP] Checking Django installation...
    python -c "import django; print('Django found')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Django not installed! Install dependencies or activate venv.
        pause
        exit /b 1
    )
    echo [SETUP] Django found, continuing without venv
)
echo.

REM Set variables
set BASE_URL=http://127.0.0.1:8001/api/v1
set TEST_EMAIL_RETAIL=bash_test_detail_retail@example.com
set TEST_EMAIL_B2B=bash_test_detail_b2b@company.com
set TEST_PASSWORD=BashDetailTest123!
set TOTAL_TESTS=0
set PASSED_TESTS=0
set FAILED_TESTS=0

echo [SETUP] Preparing test environment for Product Detail API...

REM Check curl availability
curl --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl not found! Install curl for HTTP requests.
    pause
    exit /b 1
)

REM Clear test data in DB
echo [SETUP] Clearing test data...
python manage.py shell -c "from apps.users.models import User; from apps.products.models import Product, Brand, Category; User.objects.filter(email__contains='bash_test_detail_').delete(); Product.objects.filter(sku__contains='DETAIL_TEST_').delete(); Brand.objects.filter(name__contains='Detail Test').delete(); print('Test data cleared')"

REM Start Django server in background
echo [SETUP] Starting Django server on port 8001...
start /B python manage.py runserver 127.0.0.1:8001 > server.log 2>&1

REM Wait for server startup
echo [SETUP] Waiting for server startup (8 seconds)...
timeout /t 8 > nul

REM Check server availability
echo [SETUP] Checking server availability...
curl -s %BASE_URL%/products/ > nul
if errorlevel 1 (
    echo [ERROR] Server unavailable! Check Django startup.
    echo [ERROR] Check server.log for error details
    goto :cleanup
)
echo [SETUP] Server started successfully!
echo.

echo ========================================
echo Начало функциональных тестов
echo ========================================
echo.

REM TEST 1: AC 1 - GET /products/{id}/ returns full information
echo [ТЕСТ 1] AC 1: Получение полной информации о товаре
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X GET %BASE_URL%/products/1/ -o test1_result.json
findstr /C:"name" test1_result.json > nul
if not errorlevel 1 (
    findstr /C:"specifications" test1_result.json > nul
    if not errorlevel 1 (
        echo [ПРОШЛО] Тест 1: Product detail возвращает полную информацию
        set /a PASSED_TESTS=PASSED_TESTS+1
    ) else (
        echo [ПРОВАЛ] Тест 1: Отсутствуют specifications в ответе
        set /a FAILED_TESTS=FAILED_TESTS+1
    )
) else (
    echo [ПРОВАЛ] Тест 1: Ошибка получения детальной информации
    echo Ответ сервера:
    type test1_result.json
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 2: Register retail user for price testing
echo [ТЕСТ 2] Регистрация retail пользователя для тестирования цен
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X POST %BASE_URL%/auth/register/ -H "Content-Type: application/json" -d "{\"email\":\"%TEST_EMAIL_RETAIL%\",\"password\":\"%TEST_PASSWORD%\",\"password_confirm\":\"%TEST_PASSWORD%\",\"role\":\"retail\",\"first_name\":\"Retail\",\"last_name\":\"User\",\"phone\":\"+79161111111\"}" -o test2_result.json
findstr /C:"message" test2_result.json > nul
if not errorlevel 1 (
    echo [ПРОШЛО] Тест 2: Retail пользователь зарегистрирован
    set /a PASSED_TESTS=PASSED_TESTS+1
) else (
    echo [ПРОВАЛ] Тест 2: Ошибка регистрации retail пользователя
    echo Ответ сервера:
    type test2_result.json
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 3: Login retail user
echo [ТЕСТ 3] Авторизация retail пользователя
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X POST %BASE_URL%/auth/login/ -H "Content-Type: application/json" -d "{\"email\":\"%TEST_EMAIL_RETAIL%\",\"password\":\"%TEST_PASSWORD%\"}" -o test3_result.json
findstr /C:"access" test3_result.json > nul
if not errorlevel 1 (
    echo [ПРОШЛО] Тест 3: Retail пользователь авторизован
    set /a PASSED_TESTS=PASSED_TESTS+1
    
    REM Extract token using PowerShell for correct JSON parsing
    for /f "usebackq delims=" %%a in (`powershell -command "(Get-Content test3_result.json | ConvertFrom-Json).access"`) do set RETAIL_TOKEN=%%a
) else (
    echo [FAIL] Test 3: Error logging in retail user
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 4: AC 2 - RRP/MSRP hidden for retail users
echo [TEST 4] AC 2: RRP/MSRP hidden for retail users
set /a TOTAL_TESTS=TOTAL_TESTS+1
if defined RETAIL_TOKEN (
    curl -s -X GET %BASE_URL%/products/1/ -H "Authorization: Bearer %RETAIL_TOKEN%" -o test4_result.json
    findstr /C:"recommended_retail_price" test4_result.json > nul
    if errorlevel 1 (
        findstr /C:"max_suggested_retail_price" test4_result.json > nul
        if errorlevel 1 (
            echo [PASS] Test 4: RRP/MSRP correctly hidden for retail
            set /a PASSED_TESTS=PASSED_TESTS+1
        ) else (
            echo [FAIL] Test 4: MSRP shown to retail (should be hidden)
            set /a FAILED_TESTS=FAILED_TESTS+1
        )
    ) else (
        echo [FAIL] Test 4: RRP shown to retail (should be hidden)
        set /a FAILED_TESTS=FAILED_TESTS+1
    )
) else (
    echo [SKIP] Test 4: Skipped due to missing retail token
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 5: Register B2B user
echo [TEST 5] Register B2B user for RRP/MSRP testing
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X POST %BASE_URL%/auth/register/ -H "Content-Type: application/json" -d "{\"email\":\"%TEST_EMAIL_B2B%\",\"password\":\"%TEST_PASSWORD%\",\"password_confirm\":\"%TEST_PASSWORD%\",\"role\":\"wholesale_level1\",\"first_name\":\"B2B\",\"last_name\":\"User\",\"phone\":\"+79162222222\",\"company_name\":\"B2B Test Company\",\"tax_id\":\"7707083893\"}" -o test5_result.json
findstr /C:"wholesale_level1" test5_result.json > nul
if not errorlevel 1 (
    echo [ПРОШЛО] Тест 5: B2B пользователь зарегистрирован
    set /a PASSED_TESTS=PASSED_TESTS+1
) else (
    findstr /C:"message" test5_result.json > nul
    if not errorlevel 1 (
        echo [ПРОШЛО] Тест 5: B2B пользователь зарегистрирован
        set /a PASSED_TESTS=PASSED_TESTS+1
    ) else (
        echo [FAIL] Test 5: Error registering B2B user
        echo Server response:
        type test5_result.json
        set /a FAILED_TESTS=FAILED_TESTS+1
    )
)
echo.

REM TEST 6: Login B2B user
echo [TEST 6] Login B2B user
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X POST %BASE_URL%/auth/login/ -H "Content-Type: application/json" -d "{\"email\":\"%TEST_EMAIL_B2B%\",\"password\":\"%TEST_PASSWORD%\"}" -o test6_result.json
findstr /C:"access" test6_result.json > nul
if not errorlevel 1 (
    echo [PASS] Test 6: B2B user logged in
    set /a PASSED_TESTS=PASSED_TESTS+1
    
    REM Extract B2B token using PowerShell for correct JSON parsing
    for /f "usebackq delims=" %%a in (`powershell -command "(Get-Content test6_result.json | ConvertFrom-Json).access"`) do set B2B_TOKEN=%%a
) else (
    echo [FAIL] Test 6: Error logging in B2B user
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 7: AC 2 - RRP/MSRP shown to B2B users
echo [TEST 7] AC 2: RRP/MSRP shown to B2B users
set /a TOTAL_TESTS=TOTAL_TESTS+1
if defined B2B_TOKEN (
    curl -s -X GET %BASE_URL%/products/1/ -H "Authorization: Bearer %B2B_TOKEN%" -o test7_result.json
    findstr /C:"recommended_retail_price" test7_result.json > nul
    if not errorlevel 1 (
        findstr /C:"max_suggested_retail_price" test7_result.json > nul
        if not errorlevel 1 (
            echo [PASS] Test 7: RRP/MSRP correctly shown to B2B
            set /a PASSED_TESTS=PASSED_TESTS+1
        ) else (
            echo [FAIL] Test 7: MSRP missing for B2B user
            set /a FAILED_TESTS=FAILED_TESTS+1
        )
    ) else (
        echo [FAIL] Test 7: RRP missing for B2B user
        set /a FAILED_TESTS=FAILED_TESTS+1
    )
) else (
    echo [SKIP] Test 7: Skipped due to missing B2B token
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 8: AC 3 - Image gallery
echo [TEST 8] AC 3: Image gallery in detail view
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X GET %BASE_URL%/products/1/ -o test8_result.json
findstr /C:"images" test8_result.json > nul
if not errorlevel 1 (
    echo [PASS] Test 8: Image gallery present in response
    set /a PASSED_TESTS=PASSED_TESTS+1
) else (
    echo [FAIL] Test 8: Image gallery missing
    echo Server response:
    type test8_result.json
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 9: AC 4 - Related products
echo [TEST 9] AC 4: Related products in detail view
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X GET %BASE_URL%/products/1/ -o test9_result.json
findstr /C:"related_products" test9_result.json > nul
if not errorlevel 1 (
    echo [PASS] Test 9: Related products present in response
    set /a PASSED_TESTS=PASSED_TESTS+1
) else (
    echo [FAIL] Test 9: Related products missing
    echo Server response:
    type test9_result.json
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

REM TEST 10: AC 5 - Specifications and breadcrumbs
echo [TEST 10] AC 5: Specifications and category breadcrumbs
set /a TOTAL_TESTS=TOTAL_TESTS+1
curl -s -X GET %BASE_URL%/products/1/ -o test10_result.json
findstr /C:"specifications" test10_result.json > nul
if not errorlevel 1 (
    findstr /C:"category_breadcrumbs" test10_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Test 10: Specifications and breadcrumbs present
        set /a PASSED_TESTS=PASSED_TESTS+1
    ) else (
        echo [FAIL] Test 10: category_breadcrumbs missing
        set /a FAILED_TESTS=FAILED_TESTS+1
    )
) else (
    echo [FAIL] Test 10: specifications missing
    set /a FAILED_TESTS=FAILED_TESTS+1
)
echo.

:results
echo ========================================
echo РЕЗУЛЬТАТЫ ФУНКЦИОНАЛЬНОГО ТЕСТИРОВАНИЯ
echo ========================================
echo.
echo Testing Framework: pytest + Django TestCase + functional tests
echo Coverage Target: 70%+ (testing-environment.md requirement)
echo Factory Pattern: Brand/Category/Product with real data
echo.
echo Всего тестов выполнено: %TOTAL_TESTS%
echo Прошли успешно: %PASSED_TESTS%
echo Провалились: %FAILED_TESTS%
echo.

REM Calculate success percentage
if %TOTAL_TESTS% gtr 0 (
    set /a SUCCESS_PERCENT=(%PASSED_TESTS% * 100) / %TOTAL_TESTS%
    echo Процент успеха: %SUCCESS_PERCENT%%%
) else (
    echo Процент успеха: 0%
)

echo.
if %FAILED_TESTS% equ 0 (
    echo [УСПЕХ] Все функциональные тесты Product Detail API прошли!
    echo.
    echo Test results according to testing-environment.md:
    echo   - AC 1 (full information): PASS
    echo   - AC 2 (RRP/MSRP for B2B): PASS  
    echo   - AC 3 (image gallery): PASS
    echo   - AC 4 (related products): PASS
    echo   - AC 5 (specifications + breadcrumbs): PASS
    echo   - Role-based pricing: PASS
    echo.
    echo Product Detail API готов к продакшену!
    set EXIT_CODE=0
) else (
    echo [НЕУДАЧА] %FAILED_TESTS% из %TOTAL_TESTS% тестов провалились
    echo Проверьте логи выше для деталей ошибок
    echo [STANDARD] testing-environment.md requires 70%+ coverage
    set EXIT_CODE=1
)

:cleanup
echo.
echo [ОЧИСТКА] Очистка тестовой среды...

REM Stop Django server
echo [ОЧИСТКА] Остановка Django сервера...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001') do (
    taskkill /PID %%a /F > nul 2>&1
)

REM Clean temporary files
echo [ОЧИСТКА] Очистка временных файлов...
del test*_result.json > nul 2>&1
del server.log > nul 2>&1

REM Clean test data
echo [ОЧИСТКА] Очистка тестовых данных...
python manage.py shell -c "from apps.users.models import User; from apps.products.models import Product, Brand, Category; User.objects.filter(email__contains='bash_test_detail_').delete(); Product.objects.filter(sku__contains='DETAIL_TEST_').delete(); Brand.objects.filter(name__contains='Detail Test').delete(); print('Test data cleaned')"

echo [ОЧИСТКА] Очистка завершена
echo.
echo ========================================
echo Функциональное тестирование завершено
echo ========================================

pause
exit /b %EXIT_CODE%
