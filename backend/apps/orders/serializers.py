"""
Сериализаторы для заказов FREESPORT
Поддерживает создание заказов из корзины с транзакционной логикой
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from apps.users.models import Address

from .models import Order, OrderItem

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
        depth = 1


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
            "id",
            "order_number",
            "user",
            "customer_display_name",
            "customer_name",
            "customer_email",
            "customer_phone",
            "status",
            "total_amount",
            "discount_amount",
            "delivery_cost",
            "delivery_address",
            "delivery_method",
            "delivery_date",
            "tracking_number",
            "payment_method",
            "payment_status",
            "payment_id",
            "notes",
            "created_at",
            "updated_at",
            "items",
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
                    f"Минимальное количество для заказа '{product.name}': {product.min_order_quantity}"
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
        user = None
        if request and request.user and request.user.is_authenticated:
            user = request.user

        # Расчет стоимости доставки (пока статичная)
        delivery_cost = self.calculate_delivery_cost(validated_data["delivery_method"])

        # Создаем заказ
        order_data = {"user": user, "delivery_cost": delivery_cost, **validated_data}

        # Для гостевых заказов сохраняем контактные данные
        if not user:
            if request and hasattr(request, 'data'):
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

        order.total_amount = total_amount + Decimal(delivery_cost)
        order.save()

        # Создаем элементы заказа
        OrderItem.objects.bulk_create(order_items)

        # Очищаем корзину
        cart.clear()

        return order

    def calculate_delivery_cost(self, delivery_method):
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
            "user",
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
