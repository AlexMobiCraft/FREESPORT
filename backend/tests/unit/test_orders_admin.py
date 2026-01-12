"""
Unit тесты для Django Admin конфигурации Orders.
Тестирование OrderAdmin и OrderItemInline.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO
from typing import TYPE_CHECKING

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from apps.orders.admin import OrderAdmin, OrderItemInline
from apps.orders.models import Order, OrderItem
from apps.products.models import Brand, Category, Product
from apps.users.models import User

if TYPE_CHECKING:
    from django.http import HttpRequest

pytestmark = pytest.mark.django_db


class TestOrderItemInline:
    """Тесты для OrderItemInline конфигурации."""

    def setup_method(self) -> None:
        """Настройка тестовых данных."""
        self.site = AdminSite()
        self.inline = OrderItemInline(OrderItem, self.site)
        self.factory = RequestFactory()

    def test_inline_model(self) -> None:
        """Тест что inline использует правильную модель."""
        assert self.inline.model == OrderItem

    def test_inline_fields(self) -> None:
        """Тест что поля inline настроены правильно."""
        expected_fields = [
            "product_name",
            "product_sku",
            "quantity",
            "unit_price",
            "total_price",
        ]
        assert self.inline.fields == expected_fields

    def test_readonly_fields(self) -> None:
        """Тест что total_price - readonly."""
        assert "total_price" in self.inline.readonly_fields

    def test_has_add_permission_returns_false(self) -> None:
        """Тест что добавление позиций через admin запрещено."""
        request = self.factory.get("/")
        assert self.inline.has_add_permission(request) is False


class TestOrderAdmin:
    """Тесты для OrderAdmin конфигурации."""

    def setup_method(self) -> None:
        """Настройка тестовых данных."""
        self.site = AdminSite()
        self.admin = OrderAdmin(Order, self.site)
        self.factory = RequestFactory()

    def test_list_display_fields(self) -> None:
        """Тест что list_display содержит правильные поля."""
        expected = [
            "order_number",
            "customer_display",
            "status",
            "payment_status_display",
            "items_count",
            "total_amount",
            "created_at",
        ]
        assert self.admin.list_display == expected

    def test_list_select_related(self) -> None:
        """Тест оптимизации select_related."""
        assert self.admin.list_select_related == ["user"]

    def test_list_filter_fields(self) -> None:
        """Тест фильтров в list view."""
        expected = ["status", "payment_status", "delivery_method", "created_at"]
        assert self.admin.list_filter == expected

    def test_search_fields(self) -> None:
        """Тест полей поиска."""
        expected = [
            "order_number",
            "user__email",
            "customer_email",
            "tracking_number",
        ]
        assert self.admin.search_fields == expected

    def test_readonly_fields(self) -> None:
        """Тест readonly полей."""
        expected = ["order_number", "created_at", "updated_at", "payment_id"]
        assert self.admin.readonly_fields == expected

    def test_inlines_configuration(self) -> None:
        """Тест что OrderItemInline подключен."""
        assert OrderItemInline in self.admin.inlines

    def test_actions_configuration(self) -> None:
        """Тест что export_to_csv action настроен."""
        assert "export_to_csv" in self.admin.actions

    def test_fieldsets_structure(self) -> None:
        """Тест структуры fieldsets."""
        assert len(self.admin.fieldsets) == 6
        # Проверяем названия секций
        sections = [fs[0] for fs in self.admin.fieldsets]
        assert "Основная информация" in sections
        assert "Информация о клиенте" in sections
        assert "Суммы" in sections
        assert "Доставка" in sections
        assert "Оплата" in sections
        assert "Дополнительная информация" in sections


class TestOrderAdminMethods:
    """Тесты для custom методов OrderAdmin."""

    def setup_method(self) -> None:
        """Настройка тестовых данных."""
        self.site = AdminSite()
        self.admin = OrderAdmin(Order, self.site)
        self.factory = RequestFactory()

    def test_customer_display_with_registered_user(self) -> None:
        """Тест customer_display для зарегистрированного пользователя."""
        user = User.objects.create_user(
            email=f"test{User.objects.count()}@example.com", password="testpass123"
        )
        order = Order.objects.create(
            user=user,
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        assert self.admin.customer_display(order) == user.email

    def test_customer_display_with_guest_email(self) -> None:
        """Тест customer_display для гостевого заказа с email."""
        order = Order.objects.create(
            customer_email="guest@example.com",
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        assert self.admin.customer_display(order) == "guest@example.com"

    def test_customer_display_with_guest_name(self) -> None:
        """Тест customer_display для гостевого заказа с именем."""
        order = Order.objects.create(
            customer_name="John Doe",
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        assert self.admin.customer_display(order) == "John Doe"

    def test_customer_display_empty(self) -> None:
        """Тест customer_display для пустого заказа."""
        order = Order.objects.create(
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        assert self.admin.customer_display(order) == "-"

    def test_items_count(self) -> None:
        """Тест подсчета количества позиций в заказе."""
        order = Order.objects.create(
            total_amount=Decimal("300.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        brand = Brand.objects.create(name=f"Test Brand {Brand.objects.count()}")
        category = Category.objects.create(
            name=f"Test Category {Category.objects.count()}",
            slug=f"test-category-{Category.objects.count()}",
        )
        # Создаем 3 позиции с разными продуктами
        for i in range(3):
            product = Product.objects.create(
                name=f"Test Product {i}",
                sku=f"TEST-00{i}",
                brand=brand,
                category=category,
                retail_price=Decimal("100.00"),
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1,
                unit_price=Decimal("100.00"),
                product_name=product.name,
                product_sku=product.sku,
            )

        assert self.admin.items_count(order) == 3

    def test_total_items_quantity(self) -> None:
        """Тест подсчета общего количества товаров."""
        order = Order.objects.create(
            total_amount=Decimal("300.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        brand = Brand.objects.create(name=f"Test Brand {Brand.objects.count()}")
        category = Category.objects.create(
            name=f"Test Category {Category.objects.count()}",
            slug=f"test-category-{Category.objects.count()}",
        )
        # Создаем 2 позиции с разными продуктами
        product1 = Product.objects.create(
            name="Test Product 1",
            sku="TEST-001",
            brand=brand,
            category=category,
            retail_price=Decimal("100.00"),
        )
        product2 = Product.objects.create(
            name="Test Product 2",
            sku="TEST-002",
            brand=brand,
            category=category,
            retail_price=Decimal("100.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=product1,
            quantity=5,
            unit_price=Decimal("100.00"),
            product_name=product1.name,
            product_sku=product1.sku,
        )
        OrderItem.objects.create(
            order=order,
            product=product2,
            quantity=3,
            unit_price=Decimal("100.00"),
            product_name=product2.name,
            product_sku=product2.sku,
        )

        assert self.admin.total_items_quantity(order) == 8

    def test_payment_status_display_paid(self) -> None:
        """Тест отображения статуса 'paid'."""
        order = Order.objects.create(
            payment_status="paid",
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        result = self.admin.payment_status_display(order)
        assert "💳" in result
        assert "Оплачен" in result
        assert "green" in result

    def test_payment_status_display_pending(self) -> None:
        """Тест отображения статуса 'pending'."""
        order = Order.objects.create(
            payment_status="pending",
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        result = self.admin.payment_status_display(order)
        assert "⏳" in result
        assert "Ожидает оплаты" in result
        assert "orange" in result

    def test_payment_status_display_failed(self) -> None:
        """Тест отображения статуса 'failed'."""
        order = Order.objects.create(
            payment_status="failed",
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        result = self.admin.payment_status_display(order)
        assert "❌" in result
        assert "Ошибка оплаты" in result
        assert "red" in result

    def test_payment_status_display_refunded(self) -> None:
        """Тест отображения статуса 'refunded'."""
        order = Order.objects.create(
            payment_status="refunded",
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        result = self.admin.payment_status_display(order)
        assert "🔄" in result
        assert "Возвращен" in result
        assert "blue" in result


class TestOrderAdminExportCSV:
    """Тесты для экспорта заказов в CSV."""

    def setup_method(self) -> None:
        """Настройка тестовых данных."""
        self.site = AdminSite()
        self.admin = OrderAdmin(Order, self.site)
        self.factory = RequestFactory()

    def test_export_to_csv_response_type(self) -> None:
        """Тест типа ответа CSV export."""
        order = Order.objects.create(
            order_number="TEST-123",
            customer_email="test@example.com",
            status="pending",
            payment_status="paid",
            total_amount=Decimal("100.00"),
            delivery_address="Test Address",
            delivery_method="courier",
            payment_method="card",
        )
        request = self.factory.get("/")
        queryset = Order.objects.filter(pk=order.pk)
        response = self.admin.export_to_csv(request, queryset)

        assert response["Content-Type"] == "text/csv; charset=utf-8"
        assert "attachment" in response["Content-Disposition"]
        assert "orders_export.csv" in response["Content-Disposition"]

    def test_export_to_csv_content(self) -> None:
        """Тест содержимого CSV файла."""
        order = Order.objects.create(
            order_number="TEST-456",
            customer_name="John Doe",
            customer_email="john@example.com",
            status="confirmed",
            payment_status="paid",
            total_amount=Decimal("250.50"),
            delivery_address="Test Address",
            delivery_method="post",
            payment_method="card",
        )
        request = self.factory.get("/")
        queryset = Order.objects.filter(pk=order.pk)
        response = self.admin.export_to_csv(request, queryset)

        # Декодируем содержимое
        content = response.content.decode("utf-8")
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Проверяем заголовки
        assert rows[0] == [
            "Order Number",
            "Customer",
            "Status",
            "Payment Status",
            "Total Amount",
            "Delivery Method",
            "Created At",
        ]

        # Проверяем данные
        assert rows[1][0] == "TEST-456"
        assert "John Doe" in rows[1][1] or "john@example.com" in rows[1][1]
        assert "250.50" in rows[1][4]

    def test_export_to_csv_multiple_orders(self) -> None:
        """Тест экспорта нескольких заказов."""
        for i in range(3):
            Order.objects.create(
                order_number=f"TEST-{i}",
                customer_email=f"test{i}@example.com",
                status="pending",
                payment_status="paid",
                total_amount=Decimal("100.00"),
                delivery_address="Test Address",
                delivery_method="courier",
                payment_method="card",
            )

        request = self.factory.get("/")
        queryset = Order.objects.all()
        response = self.admin.export_to_csv(request, queryset)

        content = response.content.decode("utf-8")
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Заголовок + 3 строки данных
        assert len(rows) == 4


class TestOrderAdminQuerysetOptimization:
    """Тесты производительности и оптимизации N+1 queries."""

    def setup_method(self) -> None:
        """Настройка тестовых данных."""
        self.site = AdminSite()
        self.admin = OrderAdmin(Order, self.site)
        self.factory = RequestFactory()

    def test_get_queryset_uses_select_related(self) -> None:
        """Тест что queryset использует select_related."""
        request = self.factory.get("/")
        qs = self.admin.get_queryset(request)

        # Проверяем что select_related применен
        assert "user" in str(qs.query).lower()

    def test_get_queryset_uses_prefetch_related(self) -> None:
        """Тест что queryset использует prefetch_related."""
        request = self.factory.get("/")
        qs = self.admin.get_queryset(request)

        # Проверяем что prefetch_related применен для items
        assert hasattr(qs, "_prefetch_related_lookups")
        assert "items" in qs._prefetch_related_lookups

    @pytest.mark.django_db
    def test_n_plus_one_queries_prevention(self, django_assert_max_num_queries) -> None:
        """Тест отсутствия N+1 queries при отображении списка заказов."""
        # Создаем тестовые данные
        user = User.objects.create_user(
            email=f"user{User.objects.count()}@example.com", password="testpass123"
        )
        brand = Brand.objects.create(name=f"Test Brand {Brand.objects.count()}")
        category = Category.objects.create(
            name=f"Test Category {Category.objects.count()}",
            slug=f"test-category-{Category.objects.count()}",
        )
        product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            brand=brand,
            category=category,
            retail_price=Decimal("100.00"),
        )

        # Создаем 10 заказов с items
        for i in range(10):
            order = Order.objects.create(
                user=user,
                total_amount=Decimal("100.00"),
                delivery_address="Test Address",
                delivery_method="courier",
                payment_method="card",
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1,
                unit_price=Decimal("100.00"),
                product_name=product.name,
                product_sku=product.sku,
            )

        request = self.factory.get("/")

        # Должно быть максимум 5-7 запросов независимо от количества заказов
        with django_assert_max_num_queries(7):
            qs = self.admin.get_queryset(request)
            # Force evaluation
            list(qs)
            # Обращение к items для каждого заказа не должно создавать новые queries
            for order in qs:
                _ = order.items.count()
