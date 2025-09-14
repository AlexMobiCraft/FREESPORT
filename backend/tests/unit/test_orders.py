"""
Unit тесты для приложения orders
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.test import APIClient
from typing import Dict, Any

"""
Unit тесты для приложения orders
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.test import APIClient
from typing import (
    Dict,
    Any,
)  # Добавил сюда, чтобы избежать конфликтов с другими импортами

from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.orders.serializers import OrderCreateSerializer, OrderDetailSerializer
from apps.products.models import Brand, Category, Product

User = get_user_model()

# ВНИМАНИЕ: файл устарел и сохранен только для обратной совместимости.
# Тесты для моделей перенесены в: backend/tests/unit/test_models/test_order_models.py
# Тесты сериализаторов перенесены в: backend/tests/unit/test_serializers/test_order_serializers.py
# Чтобы избежать дублирования, модуль пропускается целиком.
# pytest.skip(
#     "Тесты orders разделены по файлам (models/serializers). Этот модуль больше не используется в CI.",
#     allow_module_level=True,
# )


@pytest.mark.unit
class TestOrderModel:
    """Тесты модели Order"""

    def test_generate_order_number_format(self):
        """Тест формата генерируемого номера заказа"""
        order_number = Order.generate_order_number()

        assert order_number.startswith("FS-")
        assert len(order_number) == 15  # FS-YYMMDD-XXXXX
        assert order_number[3:9].isdigit()  # YYMMDD часть
        assert order_number[10:].isalnum()  # XXXXX часть содержит только буквы и цифры
        assert (
            order_number[10:] == order_number[10:].upper()
        )  # XXXXX часть в верхнем регистре

    def test_order_number_auto_generation(self, db):
        """Тест автогенерации номера заказа при создании"""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        order = Order.objects.create(
            user=user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("1000.00"),
        )

        assert order.order_number is not None
        assert order.order_number.startswith("FS-")

    def test_customer_display_name_with_user(self, db):
        """Тест отображаемого имени для авторизованного пользователя"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass",
            first_name="John",
            last_name="Doe",
        )
        order = Order.objects.create(
            user=user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("1000.00"),
        )

        assert order.customer_display_name == "John Doe"

    def test_customer_display_name_guest_order(self, db):
        """Тест отображаемого имени для гостевого заказа"""
        order = Order.objects.create(
            customer_name="Jane Smith",
            customer_email="jane@example.com",
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("1000.00"),
        )

        assert order.customer_display_name == "Jane Smith"

    def test_can_be_cancelled_statuses(self, db):
        """Тест определения возможности отмены заказа"""
        user = User.objects.create_user(email="test@example.com", password="testpass")

        # Заказ в статусе pending - можно отменить
        order_pending = Order.objects.create(
            user=user,
            status="pending",
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("1000.00"),
        )
        assert order_pending.can_be_cancelled is True

        # Заказ в статусе confirmed - можно отменить
        order_confirmed = Order.objects.create(
            user=user,
            status="confirmed",
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("1000.00"),
        )
        assert order_confirmed.can_be_cancelled is True

        # Заказ в статусе shipped - нельзя отменить
        order_shipped = Order.objects.create(
            user=user,
            status="shipped",
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("1000.00"),
        )
        assert order_shipped.can_be_cancelled is False


@pytest.mark.unit
class TestOrderItemModel:
    """Тесты модели OrderItem"""

    def test_total_price_calculation(self, db):
        """Тест автоматического расчета общей стоимости"""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        category = Category.objects.create(name="Test Category", slug="test-category")
        product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            brand=brand,
            category=category,
            sku="TEST001",
            retail_price=Decimal("100.00"),
            stock_quantity=10,
        )
        order = Order.objects.create(
            user=user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("500.00"),
        )

        order_item = OrderItem.objects.create(
            order=order, product=product, quantity=3, unit_price=Decimal("100.00")
        )

        assert order_item.total_price == Decimal("300.00")

    def test_product_snapshot_data(self, db):
        """Тест сохранения снимка данных товара"""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        category = Category.objects.create(name="Test Category", slug="test-category")
        product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            brand=brand,
            category=category,
            sku="TEST001",
            retail_price=Decimal("100.00"),
            stock_quantity=10,
        )
        order = Order.objects.create(
            user=user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("100.00"),
        )

        order_item = OrderItem.objects.create(
            order=order, product=product, quantity=1, unit_price=Decimal("100.00")
        )

        assert order_item.product_name == "Test Product"
        assert order_item.product_sku == "TEST001"


@pytest.mark.unit
class TestOrderCreateSerializer:
    """Тесты сериализатора создания заказа"""

    def test_validate_empty_cart(self, db):
        """Тест валидации пустой корзины"""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        cart = Cart.objects.create(user=user)

        # Мокаем request объект
        class MockRequest:
            def __init__(self, user):
                self.user = user

        serializer = OrderCreateSerializer(context={"request": MockRequest(user)})

        with pytest.raises(serializers.ValidationError, match="Корзина пуста"):
            serializer.validate(
                {
                    "delivery_address": "Test Address",
                    "delivery_method": "courier",
                    "payment_method": "card",
                }
            )

    def test_delivery_cost_calculation(self, db):
        """Тест расчета стоимости доставки"""
        serializer = OrderCreateSerializer()  # type: ignore

        assert serializer.calculate_delivery_cost("pickup") == 0
        assert serializer.calculate_delivery_cost("courier") == 500
        assert serializer.calculate_delivery_cost("post") == 300
        assert serializer.calculate_delivery_cost("transport") == 1000


@pytest.mark.unit
class TestOrderDetailSerializer:
    """Тесты сериализатора деталей заказа"""

    def test_serializer_fields(self, db):
        """Тест корректности полей сериализатора"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass",
            first_name="John",
            last_name="Doe",
        )
        order = Order.objects.create(
            user=user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=Decimal("1000.00"),
            delivery_cost=Decimal("500.00"),
        )

        serializer = OrderDetailSerializer(order)
        data = serializer.data  # type: ignore

        assert "order_number" in data
        assert "customer_display_name" in data
        assert "total_amount" in data
        assert "delivery_cost" in data
        assert "items" in data
        assert data["customer_display_name"] == "John Doe"
