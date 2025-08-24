@echo off
chcp 65001 >nul

echo Тестирование извлечения токена из JSON...
echo.

REM Создаем тестовый JSON файл
echo {"access":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1NTQ0MjAwLCJpYXQiOjE3NTU1NDA2MDAsImp0aSI6ImRjYjM3ODVjYzk3NTQyZmU4ZmJhMDk4ZjE2YjgxOTVhIiwidXNlcl9pZCI6NTB9.SAmV-VphrzNM-8cC1tlxZvad65sRgLY5zTV6-fS_PiU","refresh":"..."} > test_token.json

echo Содержимое тестового файла:
type test_token.json
echo.

echo === СТАРЫЙ МЕТОД (НЕПРАВИЛЬНЫЙ) ===
for /f "tokens=2 delims=:" %%a in ('findstr /C:"access" test_token.json') do (
    set OLD_TOKEN=%%a
)
set OLD_TOKEN=%OLD_TOKEN:"=%
set OLD_TOKEN=%OLD_TOKEN:,=%
set OLD_TOKEN=%OLD_TOKEN: =%
echo Извлеченный токен (старый метод): %OLD_TOKEN%
echo Длина токена: 
echo %OLD_TOKEN% | find /c /v ""
echo.

echo === НОВЫЙ МЕТОД (ПРАВИЛЬНЫЙ) ===
REM Используем PowerShell для корректного парсинга JSON
for /f "usebackq delims=" %%a in (`powershell -command "(Get-Content test_token.json | ConvertFrom-Json).access"`) do set NEW_TOKEN=%%a
echo Извлеченный токен (новый метод): %NEW_TOKEN%
echo.

echo === АЛЬТЕРНАТИВНЫЙ МЕТОД (jq) ===
REM Если есть jq
jq -r .access test_token.json > token_only.txt 2>nul
if exist token_only.txt (
    set /p JQ_TOKEN=<token_only.txt
    echo Извлеченный токен (jq): !JQ_TOKEN!
    del token_only.txt
) else (
    echo jq не найден, пропускаем этот метод
)

echo.
echo === ПРОВЕРКА ТОКЕНА ===
echo Правильный токен должен иметь 3 части, разделенные точками
echo %NEW_TOKEN% | find /c "."

del test_token.json
pause
