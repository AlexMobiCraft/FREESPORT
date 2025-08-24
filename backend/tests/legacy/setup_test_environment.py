#!/usr/bin/env python
"""
Простой скрипт для проверки и запуска необходимых сервисов перед тестами
"""
import os
import sys
import time
import subprocess
import requests
import redis


def check_docker():
    """Проверяет и запускает Docker если нужно"""
    print("🐳 Проверка Docker...")
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("   ✅ Docker работает")
            return True
        else:
            print("   ❌ Docker не запущен. Запустите Docker Desktop вручную")
            return False
    except:
        print("   ❌ Docker не найден. Установите Docker Desktop")
        return False


def check_redis():
    """Проверяет и запускает Redis контейнер если нужно"""
    print("🔴 Проверка Redis...")
    
    # Проверяем существующий контейнер
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=redis-test', '--format', '{{.Names}}'], 
                              capture_output=True, text=True, timeout=10)
        if 'redis-test' in result.stdout:
            print("   ✅ Redis контейнер уже запущен")
            return check_redis_connection()
    except:
        pass
    
    # Запускаем Redis контейнер
    print("   Запуск Redis контейнера...")
    try:
        # Останавливаем старый если есть
        subprocess.run(['docker', 'stop', 'redis-test'], capture_output=True, timeout=10)
        subprocess.run(['docker', 'rm', 'redis-test'], capture_output=True, timeout=10)
        
        # Запускаем новый
        result = subprocess.run([
            'docker', 'run', '-d', '-p', '6379:6379', '--name', 'redis-test', 'redis:alpine'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            time.sleep(2)  # Ждем запуска
            if check_redis_connection():
                print("   ✅ Redis контейнер запущен")
                return True
        
        print(f"   ❌ Ошибка запуска Redis: {result.stderr}")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def check_redis_connection():
    """Проверяет подключение к Redis"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=1)
        r.ping()
        return True
    except:
        return False


def check_virtual_environment():
    """Проверяет активировано ли виртуальное окружение"""
    print("🐍 Проверка виртуального окружения...")
    
    # Проверяем переменную VIRTUAL_ENV
    if os.environ.get('VIRTUAL_ENV'):
        venv_path = os.environ.get('VIRTUAL_ENV')
        print(f"   ✅ Виртуальное окружение активно: {venv_path}")
        return True
    
    # Проверяем наличие папки venv в текущей директории
    if os.path.exists('venv'):
        print("   ⚠️ Найдена папка venv, но окружение не активировано")
        print("   Активируйте виртуальное окружение:")
        print("   Windows: .\\venv\\Scripts\\activate")
        print("   Linux/Mac: source venv/bin/activate")
        return False
    
    print("   ❌ Виртуальное окружение не найдено")
    print("   Создайте и активируйте виртуальное окружение:")
    print("   python -m venv venv")
    print("   Windows: .\\venv\\Scripts\\activate")
    print("   Linux/Mac: source venv/bin/activate")
    return False


def main():
    """Основная функция проверки окружения"""
    print("🚀 Проверка тестового окружения FREESPORT")
    print("=" * 50)
    
    all_ok = True
    
    # Проверяем виртуальное окружение
    if not check_virtual_environment():
        all_ok = False
    
    # Проверяем Docker
    if not check_docker():
        all_ok = False
    
    # Проверяем Redis
    if not check_redis():
        all_ok = False
    
    print("=" * 50)
    if all_ok:
        print("✅ Окружение готово для запуска тестов!")
        print("\nТеперь можно запускать:")
        print("  python run_functional_tests_user_management.py")
        print("  или любые другие функциональные тесты")
    else:
        print("❌ Есть проблемы с окружением. Исправьте их перед запуском тестов.")
        sys.exit(1)


if __name__ == "__main__":
    main()
