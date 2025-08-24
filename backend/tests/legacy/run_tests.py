#!/usr/bin/env python
"""
Скрипт для запуска тестов с корректным выводом в PowerShell
"""
import os
import sys
import subprocess

def run_tests(test_path=None, verbose=True):
    """Запуск тестов с корректным выводом"""
    
    # Устанавливаем переменные окружения
    env = os.environ.copy()
    env['DJANGO_SETTINGS_MODULE'] = 'freesport.settings.test'
    env['PYTHONPATH'] = os.getcwd()
    
    # Формируем команду
    if test_path:
        cmd = ['python', '-m', 'pytest', test_path]
    else:
        cmd = ['python', '-m', 'pytest', 'tests/unit/test_serializers/']
    
    if verbose:
        cmd.extend(['-v', '-s'])
    
    print(f"Запуск команды: {' '.join(cmd)}")
    print("=" * 50)
    
    try:
        # Запускаем тесты
        result = subprocess.run(
            cmd,
            env=env,
            cwd=os.getcwd(),
            capture_output=False,
            text=True
        )
        
        print("=" * 50)
        print(f"Код завершения: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Ошибка запуска тестов: {e}")
        return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    test_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("🧪 Запуск тестов Django сериализаторов")
    print("=" * 50)
    
    success = run_tests(test_path)
    
    if success:
        print("✅ Тесты завершены")
    else:
        print("❌ Тесты завершились с ошибками")
        sys.exit(1)
