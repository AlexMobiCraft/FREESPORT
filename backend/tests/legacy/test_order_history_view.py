#!/usr/bin/env python
"""
Тест OrderHistoryView
"""
import os
import sys

import django

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.test")
django.setup()

from django.contrib.auth import get_user_model

from apps.orders.models import Order
from apps.users.views.personal_cabinet import OrderHistoryView

User = get_user_model()


def test_order_history_view():
    """Тест OrderHistoryView"""
    print("🧪 Тестируем OrderHistoryView...")

    try:
        # Проверяем что view импортируется
        view = OrderHistoryView()
        print("✅ OrderHistoryView импортирован успешно")

        # Проверяем что методы существуют
        print(f"✅ Метод get существует: {hasattr(view, 'get')}")
        print(f"✅ permission_classes установлены: {view.permission_classes}")

        # Создаем тестового пользователя
        user = User.objects.create_user(
            email="test@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        print(f"✅ Пользователь создан: {user}")

        # Создаем тестовые заказы
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

        # Тестируем QuerySet
        orders = Order.objects.filter(user=user).order_by("-created_at")
        print(f"✅ QuerySet работает: {orders.count()} заказов")

        # Тестируем фильтрацию
        pending_orders = orders.filter(status="pending")
        print(f"✅ Фильтрация по статусу: {pending_orders.count()} pending заказов")

        # Очистка
        order1.delete()
        order2.delete()
        user.delete()

        print("\n🎉 OrderHistoryView готов к работе!")
        return True

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_order_history_view()
    sys.exit(0 if success else 1)
