"""
Тесты для Order Serializers - Story 2.7 Order Management API
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.orders.serializers import (
    OrderItemSerializer,
    OrderCreateSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderStatusUpdateSerializer
)
from apps.users.serializers import AddressSerializer as DeliveryAddressSerializer

User = get_user_model()


@pytest.mark.django_db
class TestOrderDetailSerializer:
    """Тесты детального сериализатора заказов"""

    def test_order_serialization(self, user_factory, address_factory,
                                order_factory):
        """Тест сериализации заказа"""
        user = user_factory.create()
        address = address_factory.create(user=user)
        order = order_factory.create(
            user=user,
            delivery_address=address,
            status='pending'
        )

        serializer = OrderDetailSerializer(order)
        data = serializer.data

        assert data['status'] == 'pending'
        assert 'user' in data
        assert 'delivery_address' in data

    def test_order_with_items_serialization(self, user_factory, order_factory,
                                           product_factory, order_item_factory):
        """Тест сериализации заказа с товарами"""
        user = user_factory.create()
        order = order_factory.create(user=user)

        product1 = product_factory.create(
            name='Товар 1', retail_price=Decimal('1000.00'))
        product2 = product_factory.create(
            name='Товар 2', retail_price=Decimal('1500.00'))

        order_item_factory.create(
            order=order, product=product1, quantity=2,
            unit_price=product1.retail_price
        )

        order_item_factory.create(
            order=order, product=product2, quantity=1,
            unit_price=product2.retail_price
        )

        serializer = OrderDetailSerializer(order)
        data = serializer.data

        assert 'items' in data
        assert len(data['items']) == 2

    def test_order_total_calculation(self, order_factory):
        """Тест расчета общей суммы заказа"""
        order = order_factory.create(
            total_amount=Decimal('5000.00')
        )

        serializer = OrderDetailSerializer(order)
        data = serializer.data

        assert data['total_amount'] == '5000.00'


@pytest.mark.django_db
class TestOrderItemSerializer:
    """Тесты сериализатора элементов заказа"""

    def test_order_item_serialization(self, user_factory, order_factory,
                                     product_factory, order_item_factory):
        """Тест сериализации элемента заказа"""
        user = user_factory.create()
        order = order_factory.create(user=user)
        product = product_factory.create(
            name='Тестовый товар',
            retail_price=Decimal('1500.00')
        )

        order_item = order_item_factory.create(
            order=order, product=product, quantity=3,
            unit_price=product.retail_price
        )

        serializer = OrderItemSerializer(order_item)
        data = serializer.data

        assert data['product']['name'] == 'Тестовый товар'
        assert data['quantity'] == 3
        assert data['unit_price'] == '1500.00'

    def test_order_item_total_calculation(self, order_item_factory):
        """Тест расчета суммы элемента заказа"""
        order_item = order_item_factory.create(
            quantity=4,
            unit_price=Decimal('250.00')
        )

        serializer = OrderItemSerializer(order_item)
        data = serializer.data

        expected_total = Decimal('250.00') * 4
        assert Decimal(data['total_price']) == expected_total

    def test_order_item_with_discount(self, product_factory,
                                     order_item_factory):
        """Тест элемента заказа со скидкой"""
        product = product_factory.create(
            retail_price=Decimal('1000.00')
        )

        order_item = order_item_factory.create(
            product=product, quantity=1,
            unit_price=Decimal('500.00')
        )

        serializer = OrderItemSerializer(order_item)
        data = serializer.data

        assert data['unit_price'] == '500.00'
        assert data['total_price'] == '500.00'


@pytest.mark.django_db
class TestOrderCreateSerializer:
    """Тесты сериализатора создания заказа"""

    def test_order_creation_validation(self, user_factory, address_factory, 
                                       cart_factory, product_factory, cart_item_factory):
        """Тест валидации создания заказа"""
        user = user_factory.create()
        address = address_factory.create(user=user)
        
        # Создаем корзину с товарами
        cart = cart_factory.create(user=user)
        product = product_factory.create(stock_quantity=10)
        cart_item_factory.create(cart=cart, product=product, quantity=2)

        data = {
            'user': user.id,
            'delivery_address': address.id,
            'payment_method': 'card',
            'delivery_method': 'courier'
        }

        serializer = OrderCreateSerializer(data=data, context={'user': user})
        assert serializer.is_valid(), serializer.errors

        order = serializer.save()
        assert order.user == user

    def test_order_creation_with_b2b_user(self, user_factory, address_factory,
                                         cart_factory, product_factory, cart_item_factory):
        """Тест создания заказа B2B пользователем"""
        b2b_user = user_factory.create(role='wholesale_level1')
        company_address = address_factory.create(user=b2b_user)
        
        # Создаем корзину с товарами
        cart = cart_factory.create(user=b2b_user)
        product = product_factory.create(stock_quantity=10)
        cart_item_factory.create(cart=cart, product=product, quantity=2)

        data = {
            'delivery_address': company_address.full_address,
            'payment_method': 'bank_transfer',
            'delivery_method': 'pickup'
        }

        serializer = OrderCreateSerializer(data=data, context={'user': b2b_user})
        assert serializer.is_valid(), serializer.errors

        order = serializer.save()
        assert order.user.role == 'wholesale_level1'

    def test_order_creation_validation_errors(self, user_factory,
                                             address_factory):
        """Тест ошибок валидации при создании заказа"""
        user = user_factory.create()
        address = address_factory.create(user=user)

        data = {
            'user': user.id,
            'delivery_address': address.id,
            'payment_method': 'invalid_method',
            'delivery_method': 'courier'
        }

        serializer = OrderCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'payment_method' in serializer.errors

    def test_order_from_cart_creation(self, user_factory, address_factory,
                                     cart_factory, product_factory,
                                     cart_item_factory):
        """Тест создания заказа из корзины"""
        user = user_factory.create()
        address = address_factory.create(user=user)
        cart = cart_factory.create(user=user)

        product1 = product_factory.create(retail_price=Decimal('100.00'))
        product2 = product_factory.create(retail_price=Decimal('200.00'))

        cart_item_factory.create(cart=cart, product=product1, quantity=2)
        cart_item_factory.create(cart=cart, product=product2, quantity=1)

        data = {
            'user': user.id,
            'delivery_address': address.id,
            'payment_method': 'card',
            'delivery_method': 'courier',
            'cart': cart.id
        }

        serializer = OrderCreateSerializer(data=data, context={'user': user})
        assert serializer.is_valid(), serializer.errors

        order = serializer.save()
        assert order.items.count() == 2

    def test_order_creation_without_address(self, user_factory,
                                           address_factory):
        """Тест создания заказа без адреса доставки"""
        user = user_factory.create()

        data = {
            'user': user.id,
            'payment_method': 'card',
            'delivery_method': 'pickup'
        }

        serializer = OrderCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'delivery_address' in serializer.errors


@pytest.mark.django_db
class TestOrderStatusUpdateSerializer:
    """Тесты сериализатора обновления статуса заказа"""

    def test_status_update(self, order_factory):
        """Тест обновления статуса заказа"""
        order = order_factory.create(status='pending')

        data = {'status': 'confirmed'}

        serializer = OrderStatusUpdateSerializer(
            order, data=data, partial=True
        )
        assert serializer.is_valid(), serializer.errors

        updated_order = serializer.save()
        assert updated_order.status == 'confirmed'

    def test_invalid_status_update(self, order_factory):
        """Тест некорректного обновления статуса"""
        order = order_factory.create(status='delivered')

        data = {'status': 'pending'}

        serializer = OrderStatusUpdateSerializer(
            order, data=data, partial=True
        )
        assert not serializer.is_valid()
        assert 'status' in serializer.errors

    def test_status_transition_validation(self, order_factory):
        """Тест валидации переходов статусов"""
        order = order_factory.create(status='pending')

        # Корректный переход
        data = {'status': 'confirmed'}
        serializer = OrderStatusUpdateSerializer(
            order, data=data, partial=True
        )
        assert serializer.is_valid()

        # Некорректный переход (пропуск статусов)
        data = {'status': 'delivered'}
        serializer = OrderStatusUpdateSerializer(
            order, data=data, partial=True
        )
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestOrderListSerializer:
    """Тесты сериализатора списка заказов"""

    def test_order_list_serialization(self, user_factory, order_factory):
        """Тест сериализации списка заказов"""
        user = user_factory.create()
        order1 = order_factory.create(
            user=user,
            status='pending',
            total_amount=Decimal('1000.00')
        )
        order2 = order_factory.create(
            user=user,
            status='confirmed',
            total_amount=Decimal('2000.00')
        )

        orders = [order1, order2]
        serializer = OrderListSerializer(orders, many=True)
        data = serializer.data

        assert len(data) == 2
        assert data[0]['status'] in ['pending', 'confirmed']
        assert data[1]['status'] in ['pending', 'confirmed']

    def test_order_list_user_filtering(self, user_factory, order_factory):
        """Тест фильтрации заказов по пользователю"""
        user1 = user_factory.create()
        user2 = user_factory.create()
        order1 = order_factory.create(user=user1, status='pending')
        order2 = order_factory.create(user=user2, status='shipped')

        # Сериализация заказов первого пользователя
        user1_orders = [order1]
        serializer = OrderListSerializer(user1_orders, many=True)
        data = serializer.data

        assert len(data) == 1
        assert data[0]['user'] == user1.id


@pytest.mark.django_db
class TestOrderDetailSerializer:
    """Тесты детального сериализатора заказа"""

    def test_order_detail_serialization(self, user_factory, address_factory,
                                       order_factory, product_factory,
                                       order_item_factory):
        """Тест детальной сериализации заказа"""
        user = user_factory.create()
        address = address_factory.create(user=user)
        order = order_factory.create(
            user=user,
            delivery_address=address,
            status='confirmed',
            payment_method='card',
            delivery_method='courier'
        )

        product = product_factory.create(name='Детальный товар')
        order_item_factory.create(
            order=order, product=product, quantity=3
        )

        serializer = OrderDetailSerializer(order)
        data = serializer.data

        assert 'items' in data
        assert 'delivery_address' in data
        assert 'payment_method' in data
        assert 'delivery_method' in data
        assert len(data['items']) == 1


    def test_order_detail_performance(self, user_factory, order_factory,
                                     product_factory, order_item_factory):
        """Тест производительности детального сериализатора"""
        user = user_factory.create()
        order = order_factory.create(user=user)

        # Создаем заказ с множеством товаров
        products = product_factory.create_batch(5)
        for product in products:
            order_item_factory.create(order=order, product=product)

        serializer = OrderDetailSerializer(order)
        data = serializer.data

        assert len(data['items']) == 5
        assert 'total_amount' in data



@pytest.mark.django_db
class TestOrderIntegration:
    """Интеграционные тесты заказов"""

    def test_full_order_workflow(self, user_factory, address_factory,
                                cart_factory, product_factory,
                                cart_item_factory):
        """Тест полного рабочего процесса заказа"""
        user = user_factory.create()
        address = address_factory.create(user=user)
        cart = cart_factory.create(user=user)

        product = product_factory.create(retail_price=Decimal('500.00'))
        cart_item_factory.create(cart=cart, product=product, quantity=2)

        # Создание заказа
        create_data = {
            'user': user.id,
            'delivery_address': address.id,
            'payment_method': 'card',
            'delivery_method': 'courier',
            'cart': cart.id
        }

        create_serializer = OrderCreateSerializer(data=create_data, context={'user': user})
        assert create_serializer.is_valid()
        order = create_serializer.save()

        # Обновление статуса
        status_data = {'status': 'confirmed'}
        status_serializer = OrderStatusUpdateSerializer(
            order, data=status_data, partial=True
        )
        assert status_serializer.is_valid()
        updated_order = status_serializer.save()

        # Проверка детальной информации
        detail_serializer = OrderDetailSerializer(updated_order)
        detail_data = detail_serializer.data

        assert detail_data['status'] == 'confirmed'
        assert len(detail_data['items']) == 1

    def test_order_performance_with_many_items(self, user_factory,
                                              order_factory, product_factory,
                                              order_item_factory):
        """Тест производительности заказа с множеством товаров"""
        user = user_factory.create()
        order = order_factory.create(user=user)

        # Создаем множество элементов заказа с разными товарами
        products = product_factory.create_batch(10)
        for i, product in enumerate(products):
            order_item_factory.create(order=order, product=product,
                                     quantity=i+1)

        serializer = OrderDetailSerializer(order)
        data = serializer.data

        assert len(data['items']) == 10
        assert 'total_amount' in data

    def test_b2b_order_workflow(self, user_factory, address_factory,
                               order_factory, order_item_factory):
        """Тест рабочего процесса B2B заказа"""
        b2b_user = user_factory.create(role='b2b')
        orders = order_factory.create_batch(3, user=b2b_user)

        for order in orders:
            order_item_factory.create(order=order)

        serializer = OrderListSerializer(orders, many=True)
        data = serializer.data

        assert len(data) == 3
        for order_data in data:
            assert order_data['user'] == b2b_user.id
