#!/usr/bin/env python
"""
Скрипт для запуска функциональных тестов User Management API
Автоматически проверяет окружение и запускает тесты
"""
import os
import sys
import subprocess
import django
from pathlib import Path

# Настройка окружения Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.test")
django.setup()

from django.test.utils import get_runner
from django.conf import settings


def check_virtual_environment():
    """Быстрая проверка виртуального окружения"""
    if not os.environ.get('VIRTUAL_ENV'):
        print("❌ Виртуальное окружение не активировано!")
        print("   Активируйте виртуальное окружение:")
        print("   Windows: .\\venv\\Scripts\\activate")
        print("   Linux/Mac: source venv/bin/activate")
        return False
    return True


def check_environment():
    """Проверяет готовность тестового окружения"""
    print("🔍 Проверка тестового окружения...")
    
    # Сначала быстро проверяем виртуальное окружение
    if not check_virtual_environment():
        return False
    
    # Запускаем полную проверку окружения
    try:
        result = subprocess.run([sys.executable, 'setup_test_environment.py'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Окружение готово")
            return True
        else:
            print("❌ Проблемы с окружением:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки окружения: {e}")
        return False


def run_functional_tests():
    """Запуск функциональных тестов User Management API"""
    print("\n Запуск функциональных тестов User Management API")
    print("Следует принципам test-catalog-api.md:")
    print("   - Полноценное функциональное тестирование с реальными данными")
    print("   - Автоматическая очистка кэша перед каждым тестом")
    print("   - Создание тестовых пользователей с реальным содержимым")
    print("   - Проверка фактической работы API с заполненными данными")
    print("   - Тестирование полного жизненного цикла функций")
    print("-" * 60)
    
    # Получение Django test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False)
    
    # Запуск тестов
    test_labels = ['tests.functional.test_user_management_api']
    failures = test_runner.run_tests(test_labels)
    
    if failures:
        print(f"\n [FAIL] {failures} тест(ов) провалились")
        return False
    else:
        print("\n [PASS] Все функциональные тесты User Management API прошли успешно!")
        print("\nРезультаты тестирования:")
        print("   Регистрация пользователей")
        print("   Аутентификация и авторизация") 
        print("   Управление профилями")
        print("   Валидация данных")
        print("   Обработка ошибок")
        print("   Автоматическая очистка кэша")
        return True


def main():
    """Основная функция"""
    print(" FREESPORT - Функциональные тесты User Management API")
    print("=" * 60)
    
    # Проверяем окружение
    if not check_environment():
        print("\n Не удалось подготовить окружение для тестов")
        sys.exit(1)
    
    # Запускаем тесты
if __name__ == "__main__":
    success = run_functional_tests()
    sys.exit(0 if success else 1)