"""
Интеграционные тесты для Orders API
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.orders.models import Order, OrderItem
from apps.products.models import Product, Brand, Category
from apps.cart.models import Cart, CartItem

User = get_user_model()

@pytest.mark.integration
@pytest.mark.django_db
class TestOrderAPI:
    """Интеграционные тесты для Orders API"""

    def setup_method(self):
        """Настройка данных для тестов"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass',
            first_name='John',
            last_name='Doe',
            role='retail'
        )
        self.brand = Brand.objects.create(name='Test Brand', slug='test-brand')
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            brand=self.brand,
            category=self.category,
            sku='TEST001',
            retail_price=Decimal('100.00'),
            stock_quantity=10
        )

    def test_create_order_from_cart_success(self, db):
        """Тест успешного создания заказа из корзины"""
        # Авторизуемся
        self.client.force_authenticate(user=self.user)
        
        # Создаем корзину с товаром
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        
        # Данные для создания заказа
        order_data = {
            'delivery_address': 'г. Москва, ул. Тестовая, д. 1',
            'delivery_method': 'courier',
            'payment_method': 'card',
            'notes': 'Тестовый заказ'
        }
        
        url = reverse('orders:order-list')
        response = self.client.post(url, order_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'order_number' in response.data
        
        # Проверяем, что заказ создался
        order = Order.objects.get(order_number=response.data['order_number'])
        assert order.user == self.user
        assert order.status == 'pending'
        assert order.total_amount == Decimal('700.00')  # 2 * 100 + 500 доставка
        assert order.delivery_cost == Decimal('500.00')
        
        # Проверяем, что создались OrderItem
        assert order.items.count() == 1
        order_item = order.items.first()
        assert order_item.product == self.product
        assert order_item.quantity == 2
        assert order_item.unit_price == Decimal('100.00')
        assert order_item.product_name == 'Test Product'
        assert order_item.product_sku == 'TEST001'
        
        # Проверяем, что корзина очистилась
        assert not cart.items.exists()

    def test_create_order_empty_cart_failure(self, db):
        """Тест создания заказа с пустой корзиной"""
        self.client.force_authenticate(user=self.user)
        
        # Создаем пустую корзину
        Cart.objects.create(user=self.user)
        
        order_data = {
            'delivery_address': 'г. Москва, ул. Тестовая, д. 1',
            'delivery_method': 'courier',
            'payment_method': 'card'
        }
        
        url = reverse('orders:order-list')
        response = self.client.post(url, order_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Корзина пуста' in str(response.data)

    def test_create_order_insufficient_stock_failure(self, db):
        """Тест создания заказа при недостатке товара"""
        self.client.force_authenticate(user=self.user)
        
        # Создаем корзину с количеством больше чем на складе
        cart = Cart.objects.create(user=self.user)
        # Временно увеличим stock для создания CartItem
        original_stock = self.product.stock_quantity
        self.product.stock_quantity = 20
        self.product.save()
        CartItem.objects.create(cart=cart, product=self.product, quantity=15)
        # Вернем исходный stock для теста
        self.product.stock_quantity = original_stock
        self.product.save()
        
        order_data = {
            'delivery_address': 'г. Москва, ул. Тестовая, д. 1',
            'delivery_method': 'courier',
            'payment_method': 'card'
        }
        
        url = reverse('orders:order-list')
        response = self.client.post(url, order_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Недостаточно товара' in str(response.data)

    def test_create_order_unauthenticated_failure(self, db):
        """Тест создания заказа неавторизованным пользователем"""
        order_data = {
            'delivery_address': 'г. Москва, ул. Тестовая, д. 1',
            'delivery_method': 'courier',
            'payment_method': 'card'
        }
        
        url = reverse('orders:order-list')
        response = self.client.post(url, order_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_order_detail_success(self, db):
        """Тест получения детальной информации о заказе"""
        self.client.force_authenticate(user=self.user)
        
        # Создаем заказ
        order = Order.objects.create(
            user=self.user,
            delivery_address='г. Москва, ул. Тестовая, д. 1',
            delivery_method='courier',
            payment_method='card',
            total_amount=Decimal('600.00'),
            delivery_cost=Decimal('500.00')
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            unit_price=Decimal('100.00'),
            product_name=self.product.name,
            product_sku=self.product.sku
        )
        
        url = reverse('orders:order-detail', kwargs={'pk': order.pk})
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['order_number'] == order.order_number
        assert response.data['customer_display_name'] == 'John Doe'
        assert len(response.data['items']) == 1
        assert response.data['items'][0]['product_name'] == 'Test Product'

    def test_get_order_detail_access_denied(self, db):
        """Тест доступа к чужому заказу"""
        # Создаем другого пользователя
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass'
        )
        
        # Создаем заказ от имени другого пользователя
        order = Order.objects.create(
            user=other_user,
            delivery_address='г. Москва, ул. Тестовая, д. 1',
            delivery_method='courier',
            payment_method='card',
            total_amount=Decimal('600.00')
        )
        
        # Пытаемся получить доступ к заказу
        self.client.force_authenticate(user=self.user)
        url = reverse('orders:order-detail', kwargs={'pk': order.pk})
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_user_orders(self, db):
        """Тест получения списка заказов пользователя"""
        self.client.force_authenticate(user=self.user)
        
        # Создаем несколько заказов с разными временными метками
        import time
        order1 = Order.objects.create(
            user=self.user,
            delivery_address='Адрес 1',
            delivery_method='courier',
            payment_method='card',
            total_amount=Decimal('600.00')
        )
        time.sleep(0.01)  # Небольшая пауза для различия времени создания
        order2 = Order.objects.create(
            user=self.user,
            delivery_address='Адрес 2',
            delivery_method='pickup',
            payment_method='cash',
            total_amount=Decimal('300.00')
        )
        
        url = reverse('orders:order-list')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        # Проверяем сортировку по дате создания (новые первые)
        # order2 создан позже, поэтому должен быть первым
        orders_ids = [order['id'] for order in response.data['results']]
        assert order2.id in orders_ids
        assert order1.id in orders_ids
        assert orders_ids[0] == order2.id

    def test_delivery_cost_calculation(self, db):
        """Тест расчета стоимости доставки для разных способов"""
        self.client.force_authenticate(user=self.user)
        
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        
        delivery_methods = [
            ('pickup', Decimal('0')),
            ('courier', Decimal('500')),
            ('post', Decimal('300')),
            ('transport', Decimal('1000'))
        ]
        
        for method, expected_cost in delivery_methods:
            order_data = {
                'delivery_address': 'г. Москва, ул. Тестовая, д. 1',
                'delivery_method': method,
                'payment_method': 'card'
            }
            
            url = reverse('orders:order-list')
            response = self.client.post(url, order_data)
            
            assert response.status_code == status.HTTP_201_CREATED
            
            order = Order.objects.get(order_number=response.data['order_number'])
            assert order.delivery_cost == expected_cost
            assert order.total_amount == Decimal('100.00') + expected_cost
            
            # Удаляем заказ для следующей итерации
            order.delete()
            
            # Воссоздаем товар в корзине
            CartItem.objects.create(cart=cart, product=self.product, quantity=1)

    def test_b2b_minimum_quantity_validation(self, db):
        """Тест валидации минимального количества для B2B пользователей"""
        # Создаем B2B пользователя
        b2b_user = User.objects.create_user(
            email='b2b@example.com',
            password='testpass',
            role='wholesale_level1'
        )
        self.client.force_authenticate(user=b2b_user)
        
        # Устанавливаем минимальное количество для заказа
        self.product.min_order_quantity = 5
        self.product.save()
        
        # Создаем корзину с количеством меньше минимального
        cart = Cart.objects.create(user=b2b_user)
        # Временно сбросим минимальное количество для создания CartItem
        self.product.min_order_quantity = 1
        self.product.save()
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        # Теперь установим реальное минимальное количество
        self.product.min_order_quantity = 5
        self.product.save()
        
        order_data = {
            'delivery_address': 'г. Москва, ул. Тестовая, д. 1',
            'delivery_method': 'courier',
            'payment_method': 'bank_transfer'
        }
        
        url = reverse('orders:order-list')
        response = self.client.post(url, order_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Минимальное количество для заказа' in str(response.data)