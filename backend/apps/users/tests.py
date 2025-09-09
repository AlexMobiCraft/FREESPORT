"""
Unit тесты для приложения users
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .models import Address, Favorite

User = get_user_model()


class UserModelTest(TestCase):
    """Тестирование модели User"""

    def test_create_user_with_email(self):
        """Создание пользователя с email"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.role, "retail")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_verified)

    def test_create_b2b_user(self):
        """Создание B2B пользователя"""
        user = User.objects.create_user(
            email="b2b@example.com",
            password="testpass123",
            role="wholesale_level1",
            company_name="Test Company",
            tax_id="1234567890",
        )
        self.assertEqual(user.role, "wholesale_level1")
        self.assertEqual(user.company_name, "Test Company")
        self.assertEqual(user.tax_id, "1234567890")

    def test_email_unique_constraint(self):
        """Email должен быть уникальным"""
        User.objects.create_user(email="test@example.com", password="testpass123")

        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="test@example.com", password="anotherpass")

    def test_user_str_representation(self):
        """Строковое представление пользователя"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(str(user), "test@example.com")


class AddressModelTest(TestCase):
    """Тестирование модели Address"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_create_address(self):
        """Создание адреса"""
        address = Address.objects.create(
            user=self.user,
            address_type="shipping",
            full_name="Test User",
            address_line1="123 Test St",
            city="Test City",
            postal_code="123456",
            country="RU",
        )
        self.assertEqual(address.user, self.user)
        self.assertEqual(address.address_type, "shipping")
        self.assertFalse(address.is_default)

    def test_default_address_logic(self):
        """Логика адреса по умолчанию"""
        # Первый адрес автоматически становится основным
        address1 = Address.objects.create(
            user=self.user,
            address_type="shipping",
            full_name="Test User",
            address_line1="123 Test St",
            city="Test City",
            postal_code="123456",
            country="RU",
            is_default=True,
        )
        self.assertTrue(address1.is_default)

        # Второй адрес не должен быть основным по умолчанию
        address2 = Address.objects.create(
            user=self.user,
            address_type="shipping",
            full_name="Test User",
            address_line1="456 Another St",
            city="Test City",
            postal_code="654321",
            country="RU",
        )
        self.assertFalse(address2.is_default)

    def test_address_str_representation(self):
        """Строковое представление адреса"""
        address = Address.objects.create(
            user=self.user,
            address_type="shipping",
            full_name="Test User",
            address_line1="123 Test St",
            city="Test City",
            postal_code="123456",
            country="RU",
        )
        expected = f"Test User - 123 Test St, Test City"
        self.assertEqual(str(address), expected)


class FavoriteModelTest(TestCase):
    """Тестирование модели Favorite"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        # Создаем минимальную структуру для товара
        from apps.products.models import Brand, Category, Product

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
        )

    def test_create_favorite(self):
        """Создание записи в избранном"""
        favorite = Favorite.objects.create(user=self.user, product=self.product)
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.product, self.product)

    def test_favorite_unique_constraint(self):
        """Уникальность записи user-product"""
        Favorite.objects.create(user=self.user, product=self.product)

        with self.assertRaises(IntegrityError):
            Favorite.objects.create(user=self.user, product=self.product)

    def test_favorite_str_representation(self):
        """Строковое представление избранного"""
        favorite = Favorite.objects.create(user=self.user, product=self.product)
        expected = f"{self.user.email} - {self.product.name}"
        self.assertEqual(str(favorite), expected)
