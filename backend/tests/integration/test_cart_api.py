<<<<<<< HEAD:backend/tests/integration/test_cart_api.py
import pytest
from django.urls import reverse
from rest_framework import status
from apps.products.models import Product
from apps.cart.models import Cart, CartItem
from tests.conftest import UserFactory, ProductFactory, sample_image

pytestmark = pytest.mark.django_db

@pytest.fixture
def product(sample_image):
    """Fixture to create a product for cart tests."""
    return ProductFactory.create(stock_quantity=10, main_image=sample_image)

@pytest.fixture
def authenticated_client(db, api_client):
    user = UserFactory.create()
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client

# AC 1: Get Cart
def test_get_cart_for_authenticated_user(authenticated_client):
    """Test getting the cart for an authenticated user."""
    url = reverse("cart:cart-list")
    response = authenticated_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_items"] == 0

def test_get_cart_for_guest(api_client):
    """Test getting the cart for a guest user."""
    url = reverse("cart:cart-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_items"] == 0

# AC 2: Add Item
def test_add_item_to_cart(authenticated_client, product):
    """Test adding an item to the cart."""
    url = reverse("cart:cart-items-list")
    data = {"product": product.id, "quantity": 2}
    response = authenticated_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert CartItem.objects.count() == 1
    cart = Cart.objects.get(user=authenticated_client.user)
    assert cart.total_items == 2

def test_add_same_item_merges_quantity(authenticated_client, product):
    """Test that adding the same item merges the quantity."""
    url = reverse("cart:cart-items-list")
    # Add first time
    authenticated_client.post(url, {"product": product.id, "quantity": 1}, format="json")
    # Add second time
    response = authenticated_client.post(url, {"product": product.id, "quantity": 2}, format="json")
    assert response.status_code == status.HTTP_201_CREATED # Merging returns 201
    assert CartItem.objects.count() == 1
    cart = Cart.objects.get(user=authenticated_client.user)
    assert cart.items.first().quantity == 3

# AC 3: Update Item
def test_update_item_quantity(authenticated_client, product):
    """Test updating the quantity of a cart item."""
    # Add item first
    add_url = reverse("cart:cart-items-list")
    authenticated_client.post(add_url, {"product": product.id, "quantity": 1}, format="json")
    cart_item = CartItem.objects.first()

    update_url = reverse("cart:cart-items-detail", kwargs={"pk": cart_item.pk})
    response = authenticated_client.patch(update_url, {"quantity": 5}, format="json")
    assert response.status_code == status.HTTP_200_OK
    cart_item.refresh_from_db()
    assert cart_item.quantity == 5

# AC 4: Delete Item
def test_delete_item_from_cart(authenticated_client, product):
    """Test deleting an item from the cart."""
    add_url = reverse("cart:cart-items-list")
    authenticated_client.post(add_url, {"product": product.id, "quantity": 1}, format="json")
    cart_item = CartItem.objects.first()

    delete_url = reverse("cart:cart-items-detail", kwargs={"pk": cart_item.pk})
    response = authenticated_client.delete(delete_url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert CartItem.objects.count() == 0

# AC 5: Guest Cart
def test_guest_cart_persistence(api_client, product):
    """Test that a guest cart persists across requests."""
    url = reverse("cart:cart-items-list")
    response = api_client.post(url, {"product": product.id, "quantity": 1}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    session_key = api_client.session.session_key
    assert Cart.objects.filter(session_key=session_key).exists()

    # Make another request to ensure the cart is retrieved
    cart_url = reverse("cart:cart-list")
    response = api_client.get(cart_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_items"] == 1
=======
"""
Functional тесты Cart API (Story 2.6)
"""
import pytest
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.products.models import Category, Brand, Product
from apps.cart.models import Cart, CartItem

User = get_user_model()


class CartAPITest(APITestCase):
    """Тестирование Cart API endpoints"""

    def setUp(self):
        # Создаем тестового пользователя
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", role="retail"
        )

        # Создаем тестовую структуру товаров
        self.category = Category.objects.create(
            name="Test Category", slug="test-category"
        )
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            category=self.category,
            brand=self.brand,
            retail_price=100.00,
            stock_quantity=10,
            is_active=True,
        )

    def test_get_empty_cart_anonymous(self):
        """Получение пустой корзины анонимным пользователем"""
        response = self.client.get("/api/v1/cart/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(response.data["total_amount"], "0.00")
        self.assertEqual(len(response.data["items"]), 0)

    def test_get_empty_cart_authenticated(self):
        """Получение пустой корзины авторизованным пользователем"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/cart/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(response.data["total_amount"], "0.00")

    def test_add_item_to_cart(self):
        """Добавление товара в корзину"""
        self.client.force_authenticate(user=self.user)

        data = {"product": self.product.id, "quantity": 2}
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["product"], self.product.id)
        self.assertEqual(response.data["quantity"], 2)

    def test_update_cart_item_quantity(self):
        """Обновление количества товара в корзине"""
        self.client.force_authenticate(user=self.user)

        # Добавляем товар
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        # Обновляем количество
        data = {"quantity": 3}
        response = self.client.patch(f"/api/v1/cart/items/{cart_item.id}/", data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["quantity"], 3)

    def test_remove_item_from_cart(self):
        """Удаление товара из корзины"""
        self.client.force_authenticate(user=self.user)

        # Добавляем товар
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        # Удаляем товар
        response = self.client.delete(f"/api/v1/cart/items/{cart_item.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_clear_cart(self):
        """Очистка корзины"""
        self.client.force_authenticate(user=self.user)

        # Добавляем товар
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        # Очищаем корзину
        response = self.client.delete("/api/v1/cart/clear/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cart_item_merge_functionality(self):
        """Тестирование объединения одинаковых товаров (FR6.1)"""
        self.client.force_authenticate(user=self.user)

        # Добавляем товар первый раз
        data = {"product": self.product.id, "quantity": 2}
        self.client.post("/api/v1/cart/items/", data)

        # Добавляем тот же товар снова
        data = {"product": self.product.id, "quantity": 3}
        response = self.client.post("/api/v1/cart/items/", data)

        # Проверяем, что количество увеличилось
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(len(cart_response.data["items"]), 1)
        self.assertEqual(cart_response.data["items"][0]["quantity"], 5)

    def test_cart_validation_out_of_stock(self):
        """Валидация остатков товара"""
        self.client.force_authenticate(user=self.user)

        # Пытаемся добавить больше, чем есть на складе
        data = {
            "product": self.product.id,
            "quantity": 15,  # больше чем stock_quantity=10
        }
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_cart_functionality(self):
        """Тестирование гостевой корзины"""
        # Не авторизуемся
        data = {"product": self.product.id, "quantity": 1}
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверяем, что корзина создалась
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(cart_response.data["total_items"], 1)
>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f:backend/tests/functional/test_cart_api.py
