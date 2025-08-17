#!/usr/bin/env python
"""
Скрипт для запуска тестов с корректной кодировкой UTF-8 на Windows
"""
import os
import sys
import subprocess

# Настройка кодировки для Windows
if sys.platform == 'win32':
    # Установка переменной окружения для UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Попытка изменить кодировку консоли
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except Exception:
        pass

def run_functional_tests():
    """Запуск функциональных тестов HTTP API с корректной кодировкой"""
    
    # Функциональные тесты HTTP API  
    functional_tests = [
        # User Management API (Story 2.2)
        ('functional/test_user_management_api.py', 'User Management API (Story 2.2)'),
        
        # Personal Cabinet API (Story 2.3)
        ('functional/test_personal_cabinet_api.py', 'Personal Cabinet API (Story 2.3)'),
        
        # Catalog API (Story 2.4)
        ('functional/test_catalog_api.py', 'Catalog API (Story 2.4)'),
        
        # Product Detail API (Story 2.5)
        ('functional/test_product_detail_api.py', 'Product Detail API (Story 2.5)'),
    ]
    
    print("=" * 80)
    print("ЗАПУСК ФУНКЦИОНАЛЬНЫХ ТЕСТОВ FREESPORT с кодировкой UTF-8")
    print("=" * 80)
    
    for i, (test_file, description) in enumerate(functional_tests, 1):
        print(f"\n[{i}/{len(functional_tests)}] {description}")
        print("-" * 50)
        
        try:
            # Запуск функционального теста с правильной кодировкой
            result = subprocess.run(
                ['python', f'tests/{test_file}'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if result.returncode == 0:
                print("✅ Тест прошел успешно")
                # Выводим результат с правильной кодировкой
                print(result.stdout)
            else:
                print("❌ Тест завершился с ошибкой")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except Exception as e:
            print(f"❌ Ошибка при запуске теста: {e}")

def run_unit_tests():
    """Запуск unit тестов Django с корректной кодировкой"""
    
    # Команды для запуска тестов
    test_commands = [
        # Products API тесты
        ['python', 'manage.py', 'test', 'apps.products.tests', '--verbosity=2'],
        
        # Cart API тесты (unit)
        ['python', 'manage.py', 'test', 'apps.cart.tests.CartAPITestCase', '--verbosity=2'],
        
        # Cart API тесты (integration) 
        ['python', 'manage.py', 'test', 'apps.cart.tests.CartIntegrationTestCase', '--verbosity=2'],
        
        # Users API тесты 
        ['python', 'manage.py', 'test', 'tests.test_users', '--verbosity=2'],
        
        # Common API тесты (пропускаем из-за pytest конфликта)
        # ['python', 'manage.py', 'test', 'tests.test_common', '--verbosity=2'],
    ]
    
    print("=" * 80)
    print("ЗАПУСК UNIT ТЕСТОВ FREESPORT с кодировкой UTF-8")
    print("=" * 80)
    
    for i, command in enumerate(test_commands, 1):
        app_name = command[3].split('.')[1]
        test_type = 'ALL' if len(command[3].split('.')) == 2 else command[3].split('.')[2]
        
        print(f"\n[{i}/{len(test_commands)}] Тестирование {app_name.upper()} API ({test_type})")
        print("-" * 50)
        
        try:
            # Запуск команды с корректной кодировкой
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if result.returncode == 0:
                print(f"✅ {app_name.upper()} тесты прошли успешно")
                # Показываем только краткую сводку
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Ran' in line and 'test' in line:
                        print(f"📊 {line}")
                    elif 'OK' in line and len(line.strip()) <= 10:
                        print(f"✅ {line}")
            else:
                print(f"❌ {app_name.upper()} тесты упали")
                print("STDOUT:", result.stdout[-500:])  # Последние 500 символов
                print("STDERR:", result.stderr[-500:])
                
        except FileNotFoundError:
            print(f"❌ Тесты для {app_name} не найдены")
        except Exception as e:
            print(f"❌ Ошибка при запуске тестов {app_name}: {e}")
    
    print("\n" + "=" * 80)
    print("UNIT ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)

def main():
    """Главная функция с выбором типа тестов"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--functional':
            run_functional_tests()
        elif sys.argv[1] == '--unit':
            run_unit_tests()
        else:
            print("Использование:")
            print("  python run_tests_utf8.py --functional  # Функциональные тесты HTTP API")
            print("  python run_tests_utf8.py --unit        # Unit тесты Django")
            print("  python run_tests_utf8.py               # Все тесты")
    else:
        # Запускаем все тесты
        run_functional_tests()
        print("\n")
        run_unit_tests()

if __name__ == '__main__':
    main()