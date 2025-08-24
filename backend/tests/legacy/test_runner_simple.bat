@echo off
chcp 65001 >nul 2>&1
cd /d "C:\Users\38670\DEV_WEB\FREESPORT\backend"

echo [SETUP] Starting simple test...
python -c "print('Python works')"
echo [SETUP] Python test complete

echo [SETUP] Testing Django...
python manage.py check
echo [SETUP] Django check complete

echo [TEST] Testing API endpoint...
python -c "import requests; print('requests available')" 2>nul || echo No requests module

echo [CLEANUP] Simple test complete
pause