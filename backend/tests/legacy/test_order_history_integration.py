#!/usr/bin/env python
"""
Интеграционный тест для OrderHistoryView
"""
import os
import sys

import django

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.test")


from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402
from rest_framework_simplejwt.tokens import \
    RefreshToken as JWTRefreshToken  # noqa: E402

from apps.orders.models import Order  # noqa: E402

django.setup()

User = get_user_model()


def test_order_history_api():
    """Интеграционный тест API истории заказов"""
    print("🧪 Тестируем Order History API...")

    try:
        # Создаем тестового пользователя
        import time

        unique_email = f"test{int(time.time())}@test.com"
        user = User.objects.create_user(
            username=unique_email,
            email=unique_email,
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        print(f"✅ Пользователь создан: {user}")

        # Создаем JWT токен
        refresh = JWTRefreshToken.for_user(user)
        access_token = str(refresh)

        # Создаем API клиент
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        print("✅ API клиент настроен с JWT токеном")

        # Тест 1: Пустая история заказов
        response = client.get("/api/v1/users/orders/")
        print(f"📋 Ответ API: статус {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Ошибка API: {response.content}")
            print(f"❌ Заголовки: {response.headers}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []

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

        # Тест 2: История с заказами
        response = client.get("/api/v1/users/orders/")
        print(f"✅ Тест истории с заказами: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

        # Проверяем структуру данных
        order_data = data["results"][0]  # Первый заказ (самый новый)
        expected_fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "payment_status",
            "payment_status_display",
            "total_amount",
            "discount_amount",
            "delivery_cost",
            "items_count",
            "customer_display_name",
            "created_at",
            "updated_at",
        ]
        for field in expected_fields:
            assert field in order_data, f"Поле {field} отсутствует"
        print("✅ Структура данных корректна")

        # Тест 3: Фильтрация по статусу
        response = client.get("/api/v1/users/orders/?status=pending")
        print(f"✅ Тест фильтрации: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["status"] == "pending"

        # Очистка
        order1.delete()
        order2.delete()
        user.delete()

        print("\n🎉 Все интеграционные тесты прошли успешно!")
        return True

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_order_history_api()
    sys.exit(0 if success else 1)
