@echo off
cd /d "c:\Users\38670\DEV_WEB\FREESPORT\backend"
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo.
echo Запуск тестов Django сериализаторов...
echo ================================================

if "%1"=="" (
    echo Запуск всех тестов сериализаторов...
    python -m pytest tests/unit/test_serializers/ -v
) else (
    echo Запуск тестов: %1
    python -m pytest %1 -v
)

echo.
echo ================================================
echo Тесты завершены
pause
