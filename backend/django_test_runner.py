#!/usr/bin/env python
"""
Альтернативный запуск тестов через Django без pytest
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def setup_django():
    """Настройка Django для тестов"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.test')
    django.setup()

def run_django_tests(test_labels=None):
    """Запуск тестов через Django TestRunner"""
    setup_django()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
    
    if not test_labels:
        test_labels = ['tests.unit.test_serializers']
    
    print(f"🧪 Запуск тестов: {', '.join(test_labels)}")
    print("=" * 60)
    
    failures = test_runner.run_tests(test_labels)
    
    print("=" * 60)
    if failures:
        print(f"❌ Тесты завершились с {failures} ошибками")
        return False
    else:
        print("✅ Все тесты прошли успешно!")
        return True

def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        # Если переданы аргументы, используем их как test_labels
        test_labels = sys.argv[1:]
    else:
        # По умолчанию запускаем все тесты сериализаторов
        test_labels = ['tests.unit.test_serializers']
    
    try:
        success = run_django_tests(test_labels)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Ошибка при запуске тестов: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
