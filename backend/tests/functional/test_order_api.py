"""
Функциональные HTTP тесты для Order API
Тестируют полный flow создания заказов из корзины
"""
import pytest
import json
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tests.conftest import (
    UserFactory,
    ProductFactory,
    CategoryFactory,
    BrandFactory,
    CartFactory,
    CartItemFactory,
    OrderFactory,
)
from apps.orders.models import Order, OrderItem
from apps.cart.models import Cart, CartItem


@pytest.fixture
def api_client():
    """API клиент для тестов"""
    return APIClient()


@pytest.fixture
def authenticated_user():
    """Авторизованный пользователь"""
    return UserFactory.create(role="retail")


@pytest.fixture
def b2b_user():
    """B2B пользователь"""
    return UserFactory.create(role="wholesale_level1")


@pytest.fixture
def test_product():
    """Тестовый продукт"""
    category = CategoryFactory.create()
    brand = BrandFactory.create()
    return ProductFactory.create(
        category=category,
        brand=brand,
        retail_price=Decimal("1000.00"),
        opt1_price=Decimal("900.00"),
        stock_quantity=10,
        min_order_quantity=1,
        is_active=True,
    )


@pytest.fixture
def cart_with_items(authenticated_user, test_product):
    """Корзина с товарами"""
    cart = CartFactory.create(user=authenticated_user)
    cart_item = CartItemFactory.create(cart=cart, product=test_product, quantity=2)
    return cart


@pytest.mark.django_db
class TestOrderAPI:
    """Тесты Order API"""

    def test_create_order_unauthorized(self, api_client):
        """GET /orders/ - неавторизованный доступ"""
        url = reverse("orders:order-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_create_order_empty_cart(self, api_client, authenticated_user):
        """POST /orders/ - создание заказа с пустой корзиной"""
        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "Test Address, 123",
            "delivery_method": "courier",
            "payment_method": "card",
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Корзина пуста" in str(response.data)

    def test_create_order_success(
        self, api_client, authenticated_user, cart_with_items, test_product
    ):
        """POST /orders/ - успешное создание заказа"""
        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "Москва, ул. Тестовая, д. 123, кв. 45",
            "delivery_method": "courier",
            "payment_method": "card",
            "notes": "Тестовый заказ",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert "order_number" in response.data
        assert response.data["delivery_address"] == data["delivery_address"]
        assert response.data["delivery_method"] == data["delivery_method"]
        assert response.data["payment_method"] == data["payment_method"]
        assert response.data["notes"] == data["notes"]
        assert response.data["total_amount"] == "2500.00"  # 2 * 1000 + 500 доставка
        assert response.data["status"] == "pending"
        assert len(response.data["items"]) == 1

        # Проверяем создание в БД
        order = Order.objects.get(id=response.data["id"])
        assert order.user == authenticated_user
        assert order.items.count() == 1

        order_item = order.items.first()
        assert order_item.product == test_product
        assert order_item.quantity == 2
        assert order_item.unit_price == Decimal("1000.00")
        assert order_item.total_price == Decimal("2000.00")

        # Проверяем, что корзина очистилась
        cart_with_items.refresh_from_db()
        assert cart_with_items.items.count() == 0

    def test_create_order_insufficient_stock(
        self, api_client, authenticated_user, test_product
    ):
        """POST /orders/ - недостаток товара на складе"""
        # Создаем корзину с количеством больше остатка
        cart = CartFactory.create(user=authenticated_user)
        CartItemFactory.create(
            cart=cart, product=test_product, quantity=15  # больше чем stock_quantity=10
        )

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "Test Address",
            "delivery_method": "courier",
            "payment_method": "card",
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Недостаточно товара" in str(response.data)

    def test_create_order_b2b_payment_validation(
        self, api_client, b2b_user, test_product
    ):
        """POST /orders/ - валидация способов оплаты для B2B"""
        # Создаем корзину для B2B пользователя
        cart = CartFactory.create(user=b2b_user)
        CartItemFactory.create(cart=cart, product=test_product, quantity=1)

        api_client.force_authenticate(user=b2b_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "B2B Address",
            "delivery_method": "courier",
            "payment_method": "card",  # Недопустимо для B2B
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "банковский перевод" in str(response.data)

    def test_create_order_b2b_success(self, api_client, b2b_user, test_product):
        """POST /orders/ - успешное создание B2B заказа"""
        cart = CartFactory.create(user=b2b_user)
        CartItemFactory.create(cart=cart, product=test_product, quantity=1)

        api_client.force_authenticate(user=b2b_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "B2B Company Address",
            "delivery_method": "transport",
            "payment_method": "bank_transfer",
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert (
            response.data["total_amount"] == "1900.00"
        )  # 900 (B2B цена) + 1000 (транспорт)

    def test_get_order_detail(self, api_client, authenticated_user, test_product):
        """GET /orders/{id}/ - получение деталей заказа"""
        order = OrderFactory.create(user=authenticated_user)

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-detail", kwargs={"pk": order.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == order.id
        assert response.data["order_number"] == order.order_number
        assert response.data["status"] == order.status

    def test_get_order_detail_forbidden(self, api_client, authenticated_user):
        """GET /orders/{id}/ - доступ к чужому заказу"""
        other_user = UserFactory.create()
        order = OrderFactory.create(user=other_user)

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-detail", kwargs={"pk": order.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_orders_list(self, api_client, authenticated_user):
        """GET /orders/ - список заказов пользователя"""
        # Создаем заказы для текущего пользователя
        order1 = OrderFactory.create(user=authenticated_user)
        order2 = OrderFactory.create(user=authenticated_user)

        # Создаем заказ для другого пользователя
        other_user = UserFactory.create()
        OrderFactory.create(user=other_user)

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

        order_ids = [order["id"] for order in response.data]
        assert order1.id in order_ids
        assert order2.id in order_ids

    def test_cancel_order_success(self, api_client, authenticated_user):
        """PATCH /orders/{id}/cancel/ - отмена заказа"""
        order = OrderFactory.create(user=authenticated_user, status="pending")

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-cancel", kwargs={"pk": order.id})
        response = api_client.patch(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "cancelled"

        order.refresh_from_db()
        assert order.status == "cancelled"

    def test_cancel_order_forbidden(self, api_client, authenticated_user):
        """PATCH /orders/{id}/cancel/ - отмена чужого заказа"""
        other_user = UserFactory.create()
        order = OrderFactory.create(user=other_user, status="pending")

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-cancel", kwargs={"pk": order.id})
        response = api_client.patch(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_order_invalid_status(self, api_client, authenticated_user):
        """PATCH /orders/{id}/cancel/ - отмена заказа в невалидном статусе"""
        order = OrderFactory.create(user=authenticated_user, status="delivered")

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-cancel", kwargs={"pk": order.id})
        response = api_client.patch(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "не может быть отменен" in str(response.data)

    def test_delivery_cost_calculation(
        self, api_client, authenticated_user, test_product
    ):
        """POST /orders/ - расчет стоимости доставки"""
        cart = CartFactory.create(user=authenticated_user)
        CartItemFactory.create(cart=cart, product=test_product, quantity=1)

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")

        # Тест разных способов доставки
        delivery_tests = [
            ("pickup", "1000.00"),  # 1000 + 0
            ("courier", "1500.00"),  # 1000 + 500
            ("post", "1300.00"),  # 1000 + 300
            ("transport", "2000.00"),  # 1000 + 1000
        ]

        for delivery_method, expected_total in delivery_tests:
            data = {
                "delivery_address": "Test Address",
                "delivery_method": delivery_method,
                "payment_method": "card",
            }

            response = api_client.post(url, data, format="json")
            assert response.status_code == status.HTTP_201_CREATED
            assert response.data["total_amount"] == expected_total

            # Очищаем заказ и восстанавливаем корзину для следующего теста
            Order.objects.get(id=response.data["id"]).delete()
            CartItemFactory.create(cart=cart, product=test_product, quantity=1)

    def test_order_response_structure(
        self, api_client, authenticated_user, cart_with_items
    ):
        """Проверка структуры ответа API"""
        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "Test Address",
            "delivery_method": "courier",
            "payment_method": "card",
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # Проверяем обязательные поля в ответе
        required_fields = [
            "id",
            "order_number",
            "customer_display_name",
            "status",
            "total_amount",
            "delivery_cost",
            "delivery_address",
            "delivery_method",
            "payment_method",
            "payment_status",
            "created_at",
            "updated_at",
            "items",
            "subtotal",
            "total_items",
            "calculated_total",
            "can_be_cancelled",
        ]

        for field in required_fields:
            assert field in response.data, f"Поле '{field}' отсутствует в ответе"

        # Проверяем структуру элементов заказа
        assert len(response.data["items"]) > 0
        item = response.data["items"][0]
        item_fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "unit_price",
            "total_price",
        ]

        for field in item_fields:
            assert field in item, f"Поле '{field}' отсутствует в элементе заказа"


@pytest.mark.django_db
class TestOrderAPIEdgeCases:
    """Тесты граничных случаев Order API"""

    def test_create_order_inactive_product(self, api_client, authenticated_user):
        """POST /orders/ - заказ с неактивным товаром"""
        category = CategoryFactory.create()
        brand = BrandFactory.create()
        inactive_product = ProductFactory.create(
            category=category, brand=brand, is_active=False, stock_quantity=10
        )

        cart = CartFactory.create(user=authenticated_user)
        CartItemFactory.create(cart=cart, product=inactive_product, quantity=1)

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "Test Address",
            "delivery_method": "courier",
            "payment_method": "card",
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "больше недоступен" in str(response.data)

    def test_create_order_min_quantity_validation(self, api_client, authenticated_user):
        """POST /orders/ - валидация минимального количества"""
        category = CategoryFactory.create()
        brand = BrandFactory.create()
        product = ProductFactory.create(
            category=category, brand=brand, min_order_quantity=5, stock_quantity=10
        )

        cart = CartFactory.create(user=authenticated_user)
        CartItemFactory.create(
            cart=cart, product=product, quantity=2
        )  # меньше min_order_quantity

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "Test Address",
            "delivery_method": "courier",
            "payment_method": "card",
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Минимальное количество заказа" in str(response.data)

    def test_order_with_multiple_products(self, api_client, authenticated_user):
        """POST /orders/ - заказ с несколькими товарами"""
        category = CategoryFactory.create()
        brand = BrandFactory.create()

        product1 = ProductFactory.create(
            category=category,
            brand=brand,
            retail_price=Decimal("1000.00"),
            stock_quantity=10,
        )
        product2 = ProductFactory.create(
            category=category,
            brand=brand,
            retail_price=Decimal("2000.00"),
            stock_quantity=5,
        )

        cart = CartFactory.create(user=authenticated_user)
        CartItemFactory.create(cart=cart, product=product1, quantity=2)
        CartItemFactory.create(cart=cart, product=product2, quantity=1)

        api_client.force_authenticate(user=authenticated_user)

        url = reverse("orders:order-list")
        data = {
            "delivery_address": "Test Address",
            "delivery_method": "courier",
            "payment_method": "card",
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["total_amount"] == "4500.00"  # (2*1000 + 1*2000) + 500
        assert len(response.data["items"]) == 2
        assert response.data["total_items"] == 3
