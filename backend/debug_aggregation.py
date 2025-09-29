#!/usr/bin/env python
"""
Отладка проблемы с агрегацией Order модели
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.development")
django.setup()

from django.db.models import Avg, Count, Sum
from apps.orders.models import Order
from django.contrib.auth import get_user_model

User = get_user_model()


def test_aggregation():
    """Тест агрегации заказов"""
    print("🧪 Тестируем агрегацию Order модели...")

    try:
        # Создаем тестового пользователя
        user = User.objects.create_user(
            email="test@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        print(f"✅ Пользователь создан: {user}")

        # Создаем несколько заказов
        order1 = Order.objects.create(
            user=user,
            order_number="TEST-001",
            status="pending",
            total_amount=1000.00,
            delivery_address="Test Address 1",
            delivery_method="courier",
            payment_method="card",
        )
        print(f"✅ Заказ 1 создан: {order1}")

        order2 = Order.objects.create(
            user=user,
            order_number="TEST-002",
            status="delivered",
            total_amount=2000.00,
            delivery_address="Test Address 2",
            delivery_method="courier",
            payment_method="card",
        )
        print(f"✅ Заказ 2 создан: {order2}")

        # Тестируем агрегацию
        print("\n🔍 Тестируем агрегацию...")

        # Простой QuerySet
        user_orders = Order.objects.filter(user=user)
        print(f"✅ QuerySet создан: {user_orders.count()} заказов")

        # Тестируем каждую агрегацию отдельно
        count_result = user_orders.aggregate(count=Count("id"))
        print(f"✅ Count агрегация: {count_result}")

        sum_result = user_orders.aggregate(total=Sum("total_amount"))
        print(f"✅ Sum агрегация: {sum_result}")

        avg_result = user_orders.aggregate(avg=Avg("total_amount"))
        print(f"✅ Avg агрегация: {avg_result}")

        # Тестируем комбинированную агрегацию
        combined_result = user_orders.aggregate(
            count=Count("id"),
            total_amount=Sum("total_amount"),
            avg_amount=Avg("total_amount"),
        )
        print(f"✅ Комбинированная агрегация: {combined_result}")

        # Очистка
        order1.delete()
        order2.delete()
        user.delete()

        print("\n🎉 Все тесты агрегации прошли успешно!")
        return True

    except Exception as e:
        print(f"\n❌ ОШИБКА агрегации: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_aggregation()
    sys.exit(0 if success else 1)
