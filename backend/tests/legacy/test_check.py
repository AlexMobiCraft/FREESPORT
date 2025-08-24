#!/usr/bin/env python
"""
Скрипт для проверки работоспособности тестов
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.test')
django.setup()

def check_imports():
    """Проверка импортов тестов"""
    try:
        # Проверяем импорты сериализаторов
        from apps.users.serializers import (
            UserRegistrationSerializer,
            UserLoginSerializer,
            AddressSerializer
        )
        print("✓ Импорт user serializers успешен")
        
        from apps.orders.serializers import (
            OrderSerializer,
            OrderItemSerializer,
            OrderCreateSerializer
        )
        print("✓ Импорт order serializers успешен")
        
        # Проверяем импорты тестов
        from tests.unit.test_serializers import test_user_serializers
        print("✓ Импорт test_user_serializers успешен")
        
        from tests.unit.test_serializers import test_order_serializers
        print("✓ Импорт test_order_serializers успешен")
        
        from tests.unit.test_serializers import test_common_serializers
        print("✓ Импорт test_common_serializers успешен")
        
        from tests.unit.test_serializers import test_simple_address
        print("✓ Импорт test_simple_address успешен")
        
        return True
        
    except ImportError as e:
        print(f"✗ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return False

def check_fixtures():
    """Проверка доступности fixtures"""
    try:
        from tests.conftest import (
            user_factory,
            address_factory,
            product_factory,
            cart_factory,
            order_factory
        )
        print("✓ Все pytest fixtures доступны")
        return True
    except ImportError as e:
        print(f"✗ Ошибка импорта fixtures: {e}")
        return False

if __name__ == "__main__":
    print("Проверка работоспособности тестов...")
    print("=" * 50)
    
    imports_ok = check_imports()
    fixtures_ok = check_fixtures()
    
    print("=" * 50)
    if imports_ok and fixtures_ok:
        print("✓ Все проверки пройдены успешно!")
        sys.exit(0)
    else:
        print("✗ Обнаружены проблемы")
        sys.exit(1)
