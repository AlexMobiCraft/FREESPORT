<<<<<<< HEAD

from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem
from apps.products.serializers import ProductListSerializer
from apps.cart.models import Cart

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "quantity",
            "unit_price",
            "total_price",
            "product_name",
            "product_sku",
        )

class OrderListSerializer(serializers.ModelSerializer):
    customer_display_name = serializers.CharField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "user",
            "customer_display_name",
            "status",
            "total_amount",
            "total_items",
            "created_at",
        )

class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_display_name = serializers.CharField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = (
=======
"""
Сериализаторы для заказов FREESPORT
Поддерживает создание заказов из корзины с транзакционной логикой
"""
from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Order, OrderItem
from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from apps.users.models import Address

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор для элементов заказа"""

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "unit_price",
            "total_price",
        ]
        read_only_fields = ["id", "product_name", "product_sku", "total_price"]


class OrderDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор заказа"""

    items = OrderItemSerializer(many=True, read_only=True)
    customer_display_name = serializers.CharField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    calculated_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    can_be_cancelled = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
            "id",
            "order_number",
            "user",
            "customer_display_name",
<<<<<<< HEAD
=======
            "customer_name",
            "customer_email",
            "customer_phone",
>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
            "status",
            "total_amount",
            "discount_amount",
            "delivery_cost",
<<<<<<< HEAD
            "subtotal",
            "total_items",
=======
>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
            "delivery_address",
            "delivery_method",
            "delivery_date",
            "tracking_number",
            "payment_method",
            "payment_status",
<<<<<<< HEAD
=======
            "payment_id",
>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
            "notes",
            "created_at",
            "updated_at",
            "items",
<<<<<<< HEAD
        )

class OrderCreateSerializer(serializers.Serializer):
    delivery_address = serializers.CharField(max_length=500)
    delivery_method = serializers.ChoiceField(choices=Order.DELIVERY_METHODS)
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHODS)
    delivery_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Пользователь должен быть авторизован")
            
        user = request.user
        
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Корзина не найдена")
            
        if not cart.items.exists():
            raise serializers.ValidationError("Корзина пуста")
            
        for cart_item in cart.items.all():
            if cart_item.product.stock_quantity < cart_item.quantity:
                raise serializers.ValidationError(
                    f"Недостаточно товара '{cart_item.product.name}' на складе. "
                    f"Доступно: {cart_item.product.stock_quantity}, требуется: {cart_item.quantity}"
                )
        
        # Валидация минимальных количеств для B2B пользователей
        if user.role in ['wholesale_level1', 'wholesale_level2', 'wholesale_level3']:
            for cart_item in cart.items.all():
                min_quantity = getattr(cart_item.product, 'min_order_quantity', 1)
                if cart_item.quantity < min_quantity:
                    raise serializers.ValidationError(
                        f"Минимальное количество для заказа товара '{cart_item.product.name}': {min_quantity}"
                    )
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        cart = Cart.objects.get(user=user)
        
        # Вычисляем общую стоимость
        subtotal = sum(
            item.quantity * item.product.get_price_for_user(user)
            for item in cart.items.select_related('product').all()
        )
        
        # Расчет стоимости доставки (пока статичная логика)
        delivery_cost = self._calculate_delivery_cost(validated_data['delivery_method'])
        total_amount = subtotal + delivery_cost
        
        # Создаем заказ
        order = Order.objects.create(
            user=user,
            total_amount=total_amount,
            delivery_cost=delivery_cost,
            **validated_data
        )
        
        # Переносим товары из корзины в заказ
        for cart_item in cart.items.select_related('product').all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.get_price_for_user(user),
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
            )
        
        # Очищаем корзину
        cart.items.all().delete()
        
        return order
    
    def _calculate_delivery_cost(self, delivery_method):
        """Расчет стоимости доставки"""
        delivery_costs = {
            'pickup': 0,
            'courier': 500,
            'post': 300,
            'transport': 1000,
        }
        return delivery_costs.get(delivery_method, 0)


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']
<<<<<<< HEAD
        
    def validate_status(self, value):
        """Валидация переходов статусов заказа"""
        if not self.instance:
            return value
            
        current_status = self.instance.status
        
        # Не позволяем откатывать статус назад или перескакивать статусы
        status_order = {
            'pending': 0,
            'confirmed': 1, 
            'processing': 2,
            'shipped': 3,
            'delivered': 4,
            'cancelled': 5,
            'refunded': 6
        }
        
        current_order = status_order.get(current_status, 0)
        new_order = status_order.get(value, 0)
        
        # Запрещаем переход с конечных статусов
        if current_status in ['delivered', 'cancelled', 'refunded']:
            if value != current_status:
                raise serializers.ValidationError(
                    f'Невозможно изменить статус с "{current_status}" на "{value}"'
                )
        
        # Запрещаем откат статуса или большие скачки (кроме отмены)
        if value != 'cancelled':
            if new_order < current_order:
                raise serializers.ValidationError(
                    f'Невозможно откатить статус с "{current_status}" на "{value}"'
                )
            # Запрещаем пропуск статусов (можно только на следующий)
            if new_order > current_order + 1:
                raise serializers.ValidationError(
                    f'Невозможно перейти с "{current_status}" на "{value}". Переходы должны быть последовательными.'
                )
            
        return value
=======
=======
            "subtotal",
            "total_items",
            "calculated_total",
            "can_be_cancelled",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "user",
            "customer_display_name",
            "created_at",
            "updated_at",
            "items",
            "subtotal",
            "total_items",
            "calculated_total",
            "can_be_cancelled",
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания заказа из корзины"""

    class Meta:
        model = Order
        fields = [
            "delivery_address",
            "delivery_method",
            "delivery_date",
            "payment_method",
            "notes",
        ]

    def validate(self, attrs):
        """Валидация данных заказа"""
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Контекст запроса обязателен")

        user = request.user if request.user.is_authenticated else None

        # Получаем корзину
        cart = self._get_user_cart(request, user)
        if not cart or not cart.items.exists():
            raise serializers.ValidationError("Корзина пуста")

        # Проверяем наличие товаров
        for item in cart.items.select_related("product"):
            product = item.product
            if not product.is_active:
                raise serializers.ValidationError(
                    f"Товар '{product.name}' больше недоступен"
                )
            if item.quantity > product.stock_quantity:
                raise serializers.ValidationError(
                    f"Недостаточно товара '{product.name}' на складе. "
                    f"Доступно: {product.stock_quantity}, запрошено: {item.quantity}"
                )
            if item.quantity < product.min_order_quantity:
                raise serializers.ValidationError(
                    f"Минимальное количество заказа для '{product.name}': {product.min_order_quantity}"
                )

        # Валидация способов доставки и оплаты
        delivery_method = attrs.get("delivery_method")
        payment_method = attrs.get("payment_method")

        # Проверка совместимости для B2B/B2C
        if user and hasattr(user, "role"):
            if user.role.startswith("wholesale") and payment_method not in [
                "bank_transfer",
                "payment_on_delivery",
            ]:
                raise serializers.ValidationError(
                    "Для оптовых покупателей доступны только банковский перевод и оплата при получении"
                )

        attrs["_cart"] = cart
        return attrs

    def _get_user_cart(self, request, user):
        """Получение корзины пользователя"""
        if user:
            return getattr(user, "cart", None)
        else:
            # Гостевая корзина по session
            session_key = request.session.session_key
            if session_key:
                try:
                    return Cart.objects.get(session_key=session_key, user__isnull=True)
                except Cart.DoesNotExist:
                    pass
        return None

    @transaction.atomic
    def create(self, validated_data):
        """Создание заказа из корзины с транзакционной логикой"""
        cart = validated_data.pop("_cart")
        request = self.context.get("request")
        user = request.user if request.user.is_authenticated else None

        # Расчет стоимости доставки (пока статичная)
        delivery_cost = self._calculate_delivery_cost(validated_data["delivery_method"])

        # Создаем заказ
        order_data = {"user": user, "delivery_cost": delivery_cost, **validated_data}

        # Для гостевых заказов сохраняем контактные данные
        if not user:
            order_data.update(
                {
                    "customer_name": request.data.get("customer_name", ""),
                    "customer_email": request.data.get("customer_email", ""),
                    "customer_phone": request.data.get("customer_phone", ""),
                }
            )

        order = Order(**order_data)

        # Рассчитываем общую сумму заказа
        total_amount = 0
        order_items = []

        for cart_item in cart.items.select_related("product"):
            product = cart_item.product
            user_price = product.get_price_for_user(user)
            item_total = user_price * cart_item.quantity
            total_amount += item_total

            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    quantity=cart_item.quantity,
                    unit_price=user_price,
                    total_price=item_total,
                    product_name=product.name,
                    product_sku=product.sku,
                )
            )

        order.total_amount = total_amount + delivery_cost
        order.save()

        # Создаем элементы заказа
        OrderItem.objects.bulk_create(order_items)

        # Очищаем корзину
        cart.clear()

        return order

    def _calculate_delivery_cost(self, delivery_method):
        """Расчет стоимости доставки"""
        delivery_costs = {
            "pickup": 0,
            "courier": 500,
            "post": 300,
            "transport": 1000,
        }
        return delivery_costs.get(delivery_method, 0)

    def to_representation(self, instance):
        """Возвращаем детальный вид созданного заказа"""
        return OrderDetailSerializer(instance, context=self.context).data


class OrderListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка заказов"""

    customer_display_name = serializers.CharField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer_display_name",
            "status",
            "total_amount",
            "delivery_method",
            "payment_method",
            "payment_status",
            "created_at",
            "total_items",
        ]
        read_only_fields = fields
>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
>>>>>>> b9cb5403e397f615917fa522c8bf3e0f81cc0fcf
