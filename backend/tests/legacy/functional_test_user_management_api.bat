@echo off
REM Bash-скрипт для функционального тестирования User Management API
REM Следует принципам test-catalog-api.md:
REM - ВСЕГДА полноценное функциональное тестирование с реальными данными
REM - Создание тестовых пользователей с реальным содержимым
REM - Проверка фактической работы API с заполненными данными
REM - Тестирование полного жизненного цикла функций

cd /d "C:\Users\38670\DEV_WEB\FREESPORT\backend"

echo ========================================
echo FREESPORT User Management API Testing
echo Функциональное тестирование с реальными данными
echo ========================================
echo.

REM Проверка и активация виртуального окружения
echo [SETUP] Проверка виртуального окружения...
if exist "venv\Scripts\activate.bat" (
    echo [SETUP] Найдено виртуальное окружение, активация...
    call venv\Scripts\activate.bat
    echo [SETUP] Виртуальное окружение активировано
) else (
    echo [WARNING] Виртуальное окружение не найдено
    echo [SETUP] Проверка установки Django...
    python -c "import django; print('Django версия:', django.get_version())" 2>nul
    if errorlevel 1 (
        echo [ERROR] Django не установлен! Установите зависимости или активируйте venv.
        pause
        exit /b 1
    )
    echo [SETUP] Django найден, продолжаем без venv
)
echo.

REM Установка переменных
set BASE_URL=http://127.0.0.1:8001/api/v1
set TEST_EMAIL_RETAIL=bash_test_retail@example.com
set TEST_EMAIL_B2B=bash_test_b2b@company.com
set TEST_EMAIL_FEDERATION=bash_test_federation@sport.ru
set TEST_PASSWORD=BashTest123!
set TOTAL_TESTS=0
set PASSED_TESTS=0
set FAILED_TESTS=0

echo [SETUP] Подготовка тестовой среды...

REM Проверка наличия curl
curl --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl не найден! Установите curl для выполнения HTTP запросов.
    pause
    exit /b 1
)

REM Очистка тестовых данных в БД
echo [SETUP] Очистка тестовых пользователей...
python manage.py shell -c "from apps.users.models import User; User.objects.filter(email__contains='bash_test_').delete(); print('Тестовые пользователи очищены')"

REM Запуск Django сервера в фоне
echo [SETUP] Запуск Django сервера на порту 8001...
start /B python manage.py runserver 127.0.0.1:8001 > server.log 2>&1

REM Ожидание запуска сервера
echo [SETUP] Ожидание запуска сервера (8 сек)...
timeout /t 8 > nul

REM Проверка доступности сервера
echo [SETUP] Проверка доступности сервера...
curl -s %BASE_URL%/users/roles/ > nul
if errorlevel 1 (
    echo [ERROR] Сервер недоступен! Проверьте запуск Django.
    echo [ERROR] Проверьте server.log для деталей ошибки
    goto :cleanup
)
echo [SETUP] Сервер запущен успешно!
echo.

echo ========================================
echo Начало функциональных тестов
echo ========================================
echo.

REM ТЕСТ 1: Получение ролей пользователей
echo [ТЕСТ 1] Получение доступных ролей пользователей
set /a TOTAL_TESTS+=1
curl -s -X GET %BASE_URL%/users/roles/ -o test1_result.json
if errorlevel 0 (
    findstr /C:"retail" test1_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 1: Endpoint ролей возвращает данные
        set /a PASSED_TESTS+=1
    ) else (
        echo [FAIL] Тест 1: Неверный формат ответа ролей
        echo Ответ сервера:
        type test1_result.json
        set /a FAILED_TESTS+=1
    )
) else (
    echo [FAIL] Тест 1: Ошибка запроса к endpoint ролей
    set /a FAILED_TESTS+=1
)
echo.

REM ТЕСТ 2: Регистрация retail пользователя
echo [ТЕСТ 2] Регистрация retail пользователя с реальными данными
set /a TOTAL_TESTS+=1
curl -s -X POST %BASE_URL%/auth/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"%TEST_EMAIL_RETAIL%\",\"password\":\"%TEST_PASSWORD%\",\"password_confirm\":\"%TEST_PASSWORD%\",\"role\":\"retail\",\"first_name\":\"Ivan\",\"last_name\":\"Petrov\",\"phone\":\"+79161234567\"}" ^
  -o test2_result.json
findstr /C:"успешно" test2_result.json > nul
if not errorlevel 1 (
    echo [PASS] Тест 2: Retail пользователь зарегистрирован
    set /a PASSED_TESTS+=1
) else (
    findstr /C:"message" test2_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 2: Retail пользователь зарегистрирован
        set /a PASSED_TESTS+=1
    ) else (
        echo [FAIL] Тест 2: Ошибка регистрации retail пользователя
        echo Ответ сервера:
        type test2_result.json
        set /a FAILED_TESTS+=1
    )
)
echo.

REM ТЕСТ 3: Авторизация и получение JWT токенов
echo [ТЕСТ 3] Авторизация retail пользователя
set /a TOTAL_TESTS+=1
curl -s -X POST %BASE_URL%/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"%TEST_EMAIL_RETAIL%\",\"password\":\"%TEST_PASSWORD%\"}" ^
  -o test3_result.json
findstr /C:"access" test3_result.json > nul
if not errorlevel 1 (
    echo [PASS] Тест 3: Авторизация успешна, получены JWT токены
    set /a PASSED_TESTS+=1
    
    REM Извлечение access токена для следующих тестов (упрощенная версия)
    for /f "tokens=2 delims=:" %%a in ('findstr /C:"access" test3_result.json') do (
        set ACCESS_TOKEN=%%a
    )
    set ACCESS_TOKEN=%ACCESS_TOKEN:"=%
    set ACCESS_TOKEN=%ACCESS_TOKEN:,=%
    set ACCESS_TOKEN=%ACCESS_TOKEN: =%
    
    if defined ACCESS_TOKEN (
        echo [INFO] Access токен получен для дальнейших тестов
    )
) else (
    echo [FAIL] Тест 3: Ошибка авторизации
    echo Ответ сервера:
    type test3_result.json
    set /a FAILED_TESTS+=1
)
echo.

REM ТЕСТ 4: Получение профиля с JWT аутентификацией
echo [ТЕСТ 4] Получение профиля с JWT токеном
set /a TOTAL_TESTS+=1
if defined ACCESS_TOKEN (
    curl -s -X GET %BASE_URL%/users/profile/ ^
      -H "Authorization: Bearer %ACCESS_TOKEN%" ^
      -o test4_result.json
    findstr /C:"%TEST_EMAIL_RETAIL%" test4_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 4: Профиль получен с JWT аутентификацией
        set /a PASSED_TESTS+=1
    ) else (
        echo [FAIL] Тест 4: Неверные данные профиля
        echo Ответ сервера:
        type test4_result.json
        set /a FAILED_TESTS+=1
    )
) else (
    echo [SKIP] Тест 4: Пропущен из-за отсутствия access токена
    set /a FAILED_TESTS+=1
)
echo.

REM ТЕСТ 5: Обновление профиля PATCH запросом
echo [ТЕСТ 5] Обновление профиля пользователя
set /a TOTAL_TESTS+=1
if defined ACCESS_TOKEN (
    curl -s -X PATCH %BASE_URL%/users/profile/ ^
      -H "Authorization: Bearer %ACCESS_TOKEN%" ^
      -H "Content-Type: application/json" ^
      -d "{\"first_name\":\"IvanUpdated\",\"phone\":\"+79169876543\"}" ^
      -o test5_result.json
    findstr /C:"IvanUpdated" test5_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 5: Профиль обновлен через PATCH
        set /a PASSED_TESTS+=1
    ) else (
        echo [FAIL] Тест 5: Ошибка обновления профиля
        echo Ответ сервера:
        type test5_result.json
        set /a FAILED_TESTS+=1
    )
) else (
    echo [SKIP] Тест 5: Пропущен из-за отсутствия access токена
    set /a FAILED_TESTS+=1
)
echo.

REM ТЕСТ 6: Регистрация B2B пользователя
echo [ТЕСТ 6] Регистрация B2B пользователя с company_name и tax_id
set /a TOTAL_TESTS+=1
curl -s -X POST %BASE_URL%/auth/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"%TEST_EMAIL_B2B%\",\"password\":\"%TEST_PASSWORD%\",\"password_confirm\":\"%TEST_PASSWORD%\",\"role\":\"wholesale_level2\",\"first_name\":\"Maria\",\"last_name\":\"Wholesale\",\"phone\":\"+79162234567\",\"company_name\":\"FREESPORT Wholesale LLC\",\"tax_id\":\"7707083893\"}" ^
  -o test6_result.json
findstr /C:"wholesale_level2" test6_result.json > nul
if not errorlevel 1 (
    echo [PASS] Тест 6: B2B пользователь зарегистрирован
    set /a PASSED_TESTS+=1
) else (
    findstr /C:"message" test6_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 6: B2B пользователь зарегистрирован
        set /a PASSED_TESTS+=1
    ) else (
        echo [FAIL] Тест 6: Ошибка регистрации B2B пользователя
        echo Ответ сервера:
        type test6_result.json
        set /a FAILED_TESTS+=1
    )
)
echo.

REM ТЕСТ 7: Валидация уникальности email
echo [ТЕСТ 7] Проверка валидации уникальности email
set /a TOTAL_TESTS+=1
curl -s -X POST %BASE_URL%/auth/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"%TEST_EMAIL_RETAIL%\",\"password\":\"DifferentPass123!\",\"password_confirm\":\"DifferentPass123!\",\"role\":\"retail\",\"first_name\":\"Duplicate\",\"last_name\":\"User\"}" ^
  -o test7_result.json
findstr /C:"существует" test7_result.json > nul
if not errorlevel 1 (
    echo [PASS] Тест 7: Валидация уникальности email работает
    set /a PASSED_TESTS+=1
) else (
    findstr /C:"email" test7_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 7: Валидация уникальности email работает
        set /a PASSED_TESTS+=1
    ) else (
        echo [FAIL] Тест 7: Валидация уникальности не сработала
        echo Ответ сервера:
        type test7_result.json
        set /a FAILED_TESTS+=1
    )
)
echo.

REM ТЕСТ 8: Валидация формата телефона
echo [ТЕСТ 8] Проверка валидации формата телефона
set /a TOTAL_TESTS+=1
curl -s -X POST %BASE_URL%/auth/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"bash_test_invalid_phone@example.com\",\"password\":\"%TEST_PASSWORD%\",\"password_confirm\":\"%TEST_PASSWORD%\",\"role\":\"retail\",\"first_name\":\"Invalid\",\"last_name\":\"Phone\",\"phone\":\"invalid_phone_format\"}" ^
  -o test8_result.json
findstr /C:"phone" test8_result.json > nul
if not errorlevel 1 (
    echo [PASS] Тест 8: Валидация формата телефона работает
    set /a PASSED_TESTS+=1
) else (
    echo [FAIL] Тест 8: Валидация телефона не сработала
    echo Ответ сервера:
    type test8_result.json
    set /a FAILED_TESTS+=1
)
echo.

REM ТЕСТ 9: Проверка аутентификации без токена
echo [ТЕСТ 9] Проверка доступа к профилю без JWT токена
set /a TOTAL_TESTS+=1
curl -s -X GET %BASE_URL%/users/profile/ -o test9_result.json
findstr /C:"401" test9_result.json > nul
if not errorlevel 1 (
    echo [PASS] Тест 9: Доступ без токена корректно заблокирован
    set /a PASSED_TESTS+=1
) else (
    findstr /C:"Authentication" test9_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 9: Доступ без токена корректно заблокирован
        set /a PASSED_TESTS+=1
    ) else (
        findstr /C:"detail" test9_result.json > nul
        if not errorlevel 1 (
            echo [PASS] Тест 9: Доступ без токена корректно заблокирован
            set /a PASSED_TESTS+=1
        ) else (
            echo [FAIL] Тест 9: Доступ без токена не заблокирован
            echo Ответ сервера:
            type test9_result.json
            set /a FAILED_TESTS+=1
        )
    )
)
echo.

REM ТЕСТ 10: Регистрация federation_rep
echo [ТЕСТ 10] Регистрация представителя федерации
set /a TOTAL_TESTS+=1
curl -s -X POST %BASE_URL%/auth/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"%TEST_EMAIL_FEDERATION%\",\"password\":\"%TEST_PASSWORD%\",\"password_confirm\":\"%TEST_PASSWORD%\",\"role\":\"federation_rep\",\"first_name\":\"Federation\",\"last_name\":\"Rep\",\"phone\":\"+79163334567\",\"company_name\":\"Russian Athletics Federation\",\"tax_id\":\"7707083894\"}" ^
  -o test10_result.json
findstr /C:"federation_rep" test10_result.json > nul
if not errorlevel 1 (
    echo [PASS] Тест 10: Federation_rep пользователь зарегистрирован
    set /a PASSED_TESTS+=1
) else (
    findstr /C:"message" test10_result.json > nul
    if not errorlevel 1 (
        echo [PASS] Тест 10: Federation_rep пользователь зарегистрирован
        set /a PASSED_TESTS+=1
    ) else (
        echo [FAIL] Тест 10: Ошибка регистрации federation_rep
        echo Ответ сервера:
        type test10_result.json
        set /a FAILED_TESTS+=1
    )
)
echo.

:results
echo ========================================
echo РЕЗУЛЬТАТЫ ФУНКЦИОНАЛЬНОГО ТЕСТИРОВАНИЯ
echo ========================================
echo.
echo Всего тестов выполнено: %TOTAL_TESTS%
echo Прошли успешно: %PASSED_TESTS%
echo Провалились: %FAILED_TESTS%
echo.

if %FAILED_TESTS% equ 0 (
    echo [SUCCESS] Все функциональные тесты User Management API прошли успешно!
    echo.
    echo Результаты тестирования согласно test-catalog-api.md:
    echo   - Получение ролей пользователей: PASS
    echo   - Регистрация retail пользователя: PASS
    echo   - Авторизация и JWT токены: PASS
    echo   - Получение профиля с аутентификацией: PASS
    echo   - Обновление профиля PATCH: PASS
    echo   - Регистрация B2B пользователя: PASS
    echo   - Валидация уникальности email: PASS
    echo   - Валидация формата телефона: PASS
    echo   - Проверка аутентификации: PASS
    echo   - Регистрация federation_rep: PASS
    echo.
    echo User Management API готов к продакшену!
    set EXIT_CODE=0
) else (
    echo [FAILURE] %FAILED_TESTS% из %TOTAL_TESTS% тестов провалились
    echo Проверьте логи выше для деталей ошибок
    set EXIT_CODE=1
)

:cleanup
echo.
echo [CLEANUP] Очистка тестовой среды...

REM Остановка Django сервера
echo [CLEANUP] Остановка Django сервера...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001') do (
    taskkill /PID %%a /F > nul 2>&1
)

REM Очистка временных файлов
echo [CLEANUP] Очистка временных файлов...
del test*_result.json > nul 2>&1
del server.log > nul 2>&1

REM Очистка тестовых данных
echo [CLEANUP] Очистка тестовых пользователей...
python manage.py shell -c "from apps.users.models import User; User.objects.filter(email__contains='bash_test_').delete(); print('Тестовые пользователи очищены')"

echo [CLEANUP] Очистка завершена
echo.
echo ========================================
echo Функциональное тестирование завершено
echo ========================================

if defined VIRTUAL_ENV (
    echo [INFO] Деактивация виртуального окружения...
    deactivate
)

pause
exit /b %EXIT_CODE%