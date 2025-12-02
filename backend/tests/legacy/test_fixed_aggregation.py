#!/usr/bin/env python
"""
Тест исправленной агрегации с новыми именами
"""
import os
import sys

import django

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.test")
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Sum

from apps.orders.models import Order

User = get_user_model()


def test_fixed_aggregation():
    """Тест исправленной агрегации"""
    print("🧪 Тестируем исправленную агрегацию...")

    try:
        # Создаем тестового пользователя
        user = User.objects.create_user(
            email="test@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        print(f"✅ Пользователь создан: {user}")

        # Создаем заказы
        order1 = Order.objects.create(
            user=user,
            order_number="TEST-001",
            status="pending",
            total_amount=1000.00,
            delivery_address="Test Address 1",
            delivery_method="courier",
            payment_method="card",
        )

        order2 = Order.objects.create(
            user=user,
            order_number="TEST-002",
            status="delivered",
            total_amount=2000.00,
            delivery_address="Test Address 2",
            delivery_method="courier",
            payment_method="card",
        )
        print(f"✅ Заказы созданы: {Order.objects.filter(user=user).count()}")

        # Тестируем новую агрегацию с другими именами
        user_orders = Order.objects.filter(user=user)
        stats = user_orders.aggregate(
            orders_count=Count("id"),
            total_sum=Sum("total_amount"),
            average_amount=Avg("total_amount"),
        )
        print(f"✅ Агрегация с новыми именами: {stats}")

        # Тестируем наш метод
        from apps.users.views.personal_cabinet import UserDashboardView

        view = UserDashboardView()
        result = view._get_order_statistics(user)
        print(f"✅ Метод _get_order_statistics: {result}")

        # Проверяем результаты
        assert result["count"] == 2
        assert result["total_amount"] == 3000.0
        assert result["avg_amount"] == 1500.0

        # Очистка
        order1.delete()
        order2.delete()
        user.delete()

        print("\n🎉 Исправленная агрегация работает отлично!")
        return True

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_fixed_aggregation()
    sys.exit(0 if success else 1)
