#!/usr/bin/env python
"""
Простой тест для проверки OrderHistorySerializer
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.development")
django.setup()

from apps.users.serializers import OrderHistorySerializer
from apps.orders.models import Order
from django.contrib.auth import get_user_model

User = get_user_model()


def test_serializer():
    """Простой тест сериализатора"""
    print("Тестируем OrderHistorySerializer...")

    # Создаем пользователя
    user = User.objects.create_user(
        email="test@test.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )

    # Создаем заказ
    order = Order.objects.create(
        user=user,
        order_number="TEST-001",
        status="pending",
        total_amount=1000.00,
        delivery_address="Test Address",
        delivery_method="courier",
        payment_method="card",
    )

    # Тестируем сериализатор
    serializer = OrderHistorySerializer(order)
    data = serializer.data

    print(f"Данные сериализатора: {data}")

    # Проверяем основные поля
    assert data["order_number"] == "TEST-001"
    assert data["status"] == "pending"
    assert float(data["total_amount"]) == 1000.00
    assert data["items_count"] == 0  # Нет товаров

    print("✅ Тест прошел успешно!")

    # Очистка
    order.delete()
    user.delete()


if __name__ == "__main__":
    test_serializer()
