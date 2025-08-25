"""
Django Unit Tests для Orders App
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderDetailSerializer
from apps.products.models import Product, Category, Brand
from apps.cart.models import Cart, CartItem

User = get_user_model()


class OrderSerializerTest(TestCase):
    """Тесты сериализаторов заказов"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", role="retail"
        )

        self.category = Category.objects.create(
            name="Test Category", slug="test-category"
        )
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")

        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            category=self.category,
            brand=self.brand,
            sku="TEST001",
            retail_price=1000,
            stock_quantity=10,
            min_order_quantity=1,
            is_active=True,
        )

    def test_order_detail_serializer(self):
        """Тест OrderDetailSerializer"""
        order = Order.objects.create(
            user=self.user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=1000,
        )

        serializer = OrderDetailSerializer(order)
        data = serializer.data

        self.assertEqual(data["id"], order.id)
        self.assertEqual(data["order_number"], order.order_number)
        self.assertEqual(data["status"], "pending")
        self.assertTrue(data["can_be_cancelled"])

    def test_order_create_serializer_validation(self):
        """Тест валидации OrderCreateSerializer"""

        # Создаем mock request
        class MockRequest:
            def __init__(self, user):
                self.user = user

        request = MockRequest(self.user)

        # Создаем корзину с товаром
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        data = {
            "delivery_address": "Test Address",
            "delivery_method": "courier",
            "payment_method": "card",
        }

        serializer = OrderCreateSerializer(data=data, context={"request": request})
        self.assertTrue(serializer.is_valid())


class OrderModelTest(TestCase):
    """Простые тесты модели Order"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_order_creation(self):
        """Тест создания заказа"""
        order = Order.objects.create(
            user=self.user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=1000,
        )

        self.assertTrue(order.order_number)
        self.assertTrue(order.order_number.startswith("FS-"))
        self.assertEqual(str(order), f"Заказ #{order.order_number}")

    def test_order_properties(self):
        """Тест computed properties"""
        order = Order.objects.create(
            user=self.user,
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
            total_amount=1000,
            status="pending",
        )

        self.assertTrue(order.can_be_cancelled)
        self.assertEqual(order.customer_display_name, self.user.email)
