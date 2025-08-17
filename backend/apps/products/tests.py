from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from .models import Product, Category, Brand
from apps.users.models import User


class ProductDetailAPITestCase(TestCase):
    """Тесты для Product Detail API"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        
        # Создаем бренд
        self.brand = Brand.objects.create(
            name="Test Brand",
            slug="test-brand"
        )
        
        # Создаем категорию
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )
        
        # Создаем товар
        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            sku="TEST-001",
            brand=self.brand,
            category=self.category,
            description="Полное описание товара",
            short_description="Краткое описание",
            retail_price=Decimal('1000.00'),
            trainer_price=Decimal('700.00'),
            recommended_retail_price=Decimal('1200.00'),
            stock_quantity=10,
            specifications={
                "weight": "1.5kg",
                "color": "Red"
            }
        )
        
        # Создаем пользователя-тренера
        self.trainer_user = User.objects.create_user(
            email="trainer@test.com",
            password="testpass123",
            role="trainer"
        )
    
    def test_product_detail_basic_fields(self):
        """Тест основных полей в Product Detail API"""
        response = self.client.get(f'/api/v1/products/{self.product.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Проверяем основные поля
        self.assertEqual(data['id'], self.product.id)
        self.assertEqual(data['name'], self.product.name)
        self.assertEqual(data['sku'], self.product.sku)
        self.assertEqual(data['description'], self.product.description)
        self.assertEqual(data['stock_quantity'], self.product.stock_quantity)
        
    def test_product_detail_specifications(self):
        """Тест отображения specifications"""
        response = self.client.get(f'/api/v1/products/{self.product.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        specs = data['specifications']
        self.assertEqual(specs['weight'], "1.5kg")
        self.assertEqual(specs['color'], "Red")
    
    def test_product_detail_trainer_pricing(self):
        """Тест ролевого ценообразования для тренера"""
        self.client.force_authenticate(user=self.trainer_user)
        response = self.client.get(f'/api/v1/products/{self.product.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['current_price'], str(self.product.trainer_price))
        self.assertEqual(data['price_type'], 'trainer')
    
    def test_discount_calculation(self):
        """Тест расчета скидки для тренера"""
        self.client.force_authenticate(user=self.trainer_user)
        response = self.client.get(f'/api/v1/products/{self.product.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Скидка тренера: (1000-700)/1000 * 100 = 30%
        trainer_price = float(self.product.trainer_price)
        retail_price = float(self.product.retail_price)
        expected_discount = round(((retail_price - trainer_price) / retail_price) * 100, 1)
        
        self.assertEqual(data['discount_percent'], expected_discount)
