"""
Тесты для Cart API
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from django.contrib.sessions.models import Session
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

from apps.cart.models import Cart, CartItem
from apps.products.models import Product, Category, Brand
from apps.users.models import User


class CartAPITestCase(TestCase):
    """Тесты для Cart API"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()

        # Создаем бренд и категорию
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(
            name="Test Category", slug="test-category"
        )

        # Создаем товары
        self.product1 = Product.objects.create(
            name="Product 1",
            slug="product-1",
            sku="TEST-001",
            brand=self.brand,
            category=self.category,
            description="Test product 1",
            retail_price=Decimal("1000.00"),
            opt1_price=Decimal("800.00"),
            stock_quantity=10,
            min_order_quantity=1,
        )

        self.product2 = Product.objects.create(
            name="Product 2",
            slug="product-2",
            sku="TEST-002",
            brand=self.brand,
            category=self.category,
            description="Test product 2",
            retail_price=Decimal("500.00"),
            stock_quantity=5,
            min_order_quantity=2,
        )

        # Создаем пользователей
        self.retail_user = User.objects.create_user(
            email="retail@test.com", password="testpass123", role="retail"
        )

        self.wholesale_user = User.objects.create_user(
            email="wholesale@test.com", password="testpass123", role="wholesale_level1"
        )

    def test_get_empty_cart_authenticated(self):
        """Тест получения пустой корзины для авторизованного пользователя"""
        self.client.force_authenticate(user=self.retail_user)
        response = self.client.get("/api/v1/cart/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(float(response.data["total_amount"]), 0.0)
        self.assertEqual(len(response.data["items"]), 0)

    def test_get_empty_cart_guest(self):
        """Тест получения пустой корзины для гостя"""
        response = self.client.get("/api/v1/cart/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(float(response.data["total_amount"]), 0.0)
        self.assertEqual(len(response.data["items"]), 0)

    @patch("apps.products.models.Product.main_image")
    def test_add_item_to_cart_authenticated(self, mock_main_image):
        """Тест добавления товара в корзину авторизованного пользователя"""
        mock_main_image.url = "http://example.com/test.jpg"

        self.client.force_authenticate(user=self.retail_user)

        data = {"product": self.product1.id, "quantity": 2}
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quantity"], 2)
        self.assertEqual(response.data["product"], self.product1.id)

        # Проверяем что товар добавился в корзину
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(cart_response.data["total_items"], 2)
        self.assertEqual(float(cart_response.data["total_amount"]), 2000.0)  # 2 * 1000

    @patch("apps.products.models.Product.main_image")
    def test_add_item_merge_same_product(self, mock_main_image):
        """Тест объединения одинаковых товаров в корзине"""
        mock_main_image.url = "http://example.com/test.jpg"

        self.client.force_authenticate(user=self.retail_user)

        # Добавляем товар первый раз
        data = {"product": self.product1.id, "quantity": 2}
        self.client.post("/api/v1/cart/items/", data)

        # Добавляем тот же товар еще раз
        data = {"product": self.product1.id, "quantity": 3}
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quantity"], 5)  # 2 + 3 = 5

        # Проверяем корзину - должен быть только один элемент
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(len(cart_response.data["items"]), 1)
        self.assertEqual(cart_response.data["total_items"], 5)

    @patch("apps.products.models.Product.main_image")
    def test_add_item_insufficient_stock(self, mock_main_image):
        """Тест добавления товара при недостаточном количестве на складе"""
        mock_main_image.url = "http://example.com/test.jpg"

        self.client.force_authenticate(user=self.retail_user)

        data = {"product": self.product2.id, "quantity": 10}  # На складе только 5
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Недостаточно товара на складе", str(response.data))

    @patch("apps.products.models.Product.main_image")
    def test_add_item_below_minimum_quantity(self, mock_main_image):
        """Тест добавления товара ниже минимального количества"""
        mock_main_image.url = "http://example.com/test.jpg"

        self.client.force_authenticate(user=self.retail_user)

        data = {"product": self.product2.id, "quantity": 1}  # Минимум 2
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Минимальное количество заказа", str(response.data))

    @patch("apps.products.models.Product.main_image")
    def test_update_cart_item_quantity(self, mock_main_image):
        """Тест обновления количества товара в корзине"""
        mock_main_image.url = "http://example.com/test.jpg"

        self.client.force_authenticate(user=self.retail_user)

        # Добавляем товар
        data = {"product": self.product1.id, "quantity": 2}
        response = self.client.post("/api/v1/cart/items/", data)
        item_id = response.data["id"]

        # Обновляем количество
        update_data = {"quantity": 5}
        response = self.client.patch(f"/api/v1/cart/items/{item_id}/", update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["quantity"], 5)

    @patch("apps.products.models.Product.main_image")
    def test_delete_cart_item(self, mock_main_image):
        """Тест удаления товара из корзины"""
        mock_main_image.url = "http://example.com/test.jpg"

        self.client.force_authenticate(user=self.retail_user)

        # Добавляем товар
        data = {"product": self.product1.id, "quantity": 2}
        response = self.client.post("/api/v1/cart/items/", data)
        item_id = response.data["id"]

        # Удаляем товар
        response = self.client.delete(f"/api/v1/cart/items/{item_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверяем что корзина пуста
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(cart_response.data["total_items"], 0)

    @patch("apps.products.models.Product.main_image")
    def test_clear_cart(self, mock_main_image):
        """Тест очистки корзины"""
        mock_main_image.url = "http://example.com/test.jpg"

        self.client.force_authenticate(user=self.retail_user)

        # Добавляем несколько товаров
        self.client.post(
            "/api/v1/cart/items/", {"product": self.product1.id, "quantity": 2}
        )
        self.client.post(
            "/api/v1/cart/items/", {"product": self.product2.id, "quantity": 3}
        )

        # Очищаем корзину
        response = self.client.delete("/api/v1/cart/clear/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверяем что корзина пуста
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(cart_response.data["total_items"], 0)

    @patch("apps.products.models.Product.main_image")
    def test_pricing_by_user_role(self, mock_main_image):
        """Тест ценообразования в зависимости от роли пользователя"""
        mock_main_image.url = "http://example.com/test.jpg"

        # Тест для розничного пользователя
        self.client.force_authenticate(user=self.retail_user)
        self.client.post(
            "/api/v1/cart/items/", {"product": self.product1.id, "quantity": 1}
        )
        response = self.client.get("/api/v1/cart/")
        self.assertEqual(float(response.data["total_amount"]), 1000.0)  # Розничная цена

        # Тест для оптового пользователя
        self.client.force_authenticate(user=self.wholesale_user)
        self.client.post(
            "/api/v1/cart/items/", {"product": self.product1.id, "quantity": 1}
        )
        response = self.client.get("/api/v1/cart/")
        self.assertEqual(float(response.data["total_amount"]), 800.0)  # Оптовая цена

    @patch("apps.products.models.Product.main_image")
    def test_guest_cart_functionality(self, mock_main_image):
        """Тест функциональности гостевой корзины"""
        mock_main_image.url = "http://example.com/test.jpg"

        # Не аутентифицируемся, работаем как гость
        response = self.client.post(
            "/api/v1/cart/items/", {"product": self.product1.id, "quantity": 2}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверяем что корзина сохраняется для гостя
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(cart_response.data["total_items"], 2)
        self.assertEqual(
            float(cart_response.data["total_amount"]), 2000.0
        )  # Розничная цена для гостей


class CartIntegrationTestCase(TestCase):
    """Интеграционные тесты для Cart API с реальными изображениями"""

    def setUp(self):
        """Настройка тестовых данных с реальными изображениями"""
        self.client = APIClient()

        # Создаем бренд и категорию
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(
            name="Test Category", slug="test-category"
        )

        # Создаем тестовое изображение
        self.test_image = self._create_test_image()

        # Создаем товар с изображением
        self.product = Product.objects.create(
            name="Product with Image",
            slug="product-with-image",
            sku="TEST-IMG-001",
            brand=self.brand,
            category=self.category,
            description="Test product with image",
            retail_price=Decimal("1000.00"),
            stock_quantity=10,
            min_order_quantity=1,
            main_image=self.test_image,
        )

        # Создаем пользователя
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", role="retail"
        )

    def _create_test_image(self):
        """Создать тестовое изображение"""
        # Создаем изображение 100x100 пикселей
        image = Image.new("RGB", (100, 100), color="red")
        image_io = io.BytesIO()
        image.save(image_io, format="JPEG")
        image_io.seek(0)

        return SimpleUploadedFile(
            "test_product.jpg", image_io.getvalue(), content_type="image/jpeg"
        )

    def test_cart_with_real_images(self):
        """Тест корзины с реальными изображениями товаров"""
        self.client.force_authenticate(user=self.user)

        # Добавляем товар в корзину
        data = {"product": self.product.id, "quantity": 2}
        response = self.client.post("/api/v1/cart/items/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quantity"], 2)
        self.assertEqual(response.data["product"], self.product.id)

        # Проверяем что изображение товара присутствует в ответе
        self.assertIsNotNone(response.data.get("product_image"))
        self.assertIn("test_product", response.data["product_image"])

        # Проверяем корзину
        cart_response = self.client.get("/api/v1/cart/")
        self.assertEqual(cart_response.data["total_items"], 2)

        # Проверяем что в корзине есть информация об изображении
        cart_item = cart_response.data["items"][0]
        self.assertIsNotNone(cart_item.get("product_image"))
        self.assertIn("test_product", cart_item["product_image"])

    def test_cart_without_image_handling(self):
        """Тест обработки товаров без изображения"""
        # Создаем товар без изображения
        product_no_image = Product.objects.create(
            name="Product No Image",
            slug="product-no-image",
            sku="TEST-NO-IMG-001",
            brand=self.brand,
            category=self.category,
            description="Test product without image",
            retail_price=Decimal("500.00"),
            stock_quantity=5,
            min_order_quantity=1
            # main_image не указано
        )

        self.client.force_authenticate(user=self.user)

        # Добавляем товар без изображения - должна быть ошибка
        data = {"product": product_no_image.id, "quantity": 1}
        response = self.client.post("/api/v1/cart/items/", data)

        # Ожидаем ошибку из-за отсутствия изображения
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
