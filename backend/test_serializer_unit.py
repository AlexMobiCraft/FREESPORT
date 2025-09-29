#!/usr/bin/env python
"""
Unit тест для OrderHistorySerializer без подключения к БД
"""
import os
import sys
import django
from unittest.mock import Mock

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.development")
django.setup()

from apps.users.serializers import OrderHistorySerializer
from apps.orders.models import Order


def test_serializer_fields():
    """Тест полей сериализатора"""
    print("🧪 Тестируем поля OrderHistorySerializer...")

    # Создаем mock объект заказа
    mock_order = Mock(spec=Order)
    mock_order.id = 1
    mock_order.order_number = "TEST-001"
    mock_order.status = "delivered"
    mock_order.get_status_display.return_value = "Доставлен"
    mock_order.payment_status = "paid"
    mock_order.get_payment_status_display.return_value = "Оплачен"
    mock_order.total_amount = 15000.00
    mock_order.discount_amount = 500.00
    mock_order.delivery_cost = 300.00
    mock_order.customer_display_name = "Иван Петров"
    mock_order.created_at = "2025-09-29T10:00:00Z"
    mock_order.updated_at = "2025-09-29T10:00:00Z"
    mock_order.total_items = 3  # Для метода get_items_count

    # Тестируем сериализатор
    serializer = OrderHistorySerializer(mock_order)
    data = serializer.data

    print(f"📋 Данные сериализатора: {data}")

    # Проверяем основные поля
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
        assert field in data, f"Поле {field} отсутствует в данных"
        print(f"  ✅ {field}: {data[field]}")

    # Проверяем конкретные значения
    assert data["order_number"] == "TEST-001"
    assert data["status"] == "delivered"
    assert data["status_display"] == "Доставлен"
    assert data["payment_status"] == "paid"
    assert data["payment_status_display"] == "Оплачен"
    assert float(data["total_amount"]) == 15000.00
    assert float(data["discount_amount"]) == 500.00
    assert float(data["delivery_cost"]) == 300.00
    assert data["items_count"] == 3
    assert data["customer_display_name"] == "Иван Петров"

    print("✅ Все поля корректно сериализуются!")
    return True


def test_serializer_method_fields():
    """Тест SerializerMethodField"""
    print("\n🧪 Тестируем SerializerMethodField...")

    mock_order = Mock(spec=Order)
    mock_order.total_items = 5

    serializer = OrderHistorySerializer(mock_order)

    # Тестируем метод get_items_count
    items_count = serializer.get_items_count(mock_order)
    assert items_count == 5, f"Ожидали 5, получили {items_count}"

    print("✅ SerializerMethodField работает корректно!")
    return True


def test_readonly_fields():
    """Тест что все поля только для чтения"""
    print("\n🧪 Тестируем readonly поля...")

    serializer = OrderHistorySerializer()
    readonly_fields = serializer.Meta.read_only_fields
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

    assert set(readonly_fields) == set(expected_fields), "Неправильные readonly поля"
    print("✅ Все поля корректно помечены как readonly!")
    return True


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск unit тестов для OrderHistorySerializer\n")

    try:
        test_serializer_fields()
        test_serializer_method_fields()
        test_readonly_fields()

        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("OrderHistorySerializer полностью готов к использованию!")

    except Exception as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
