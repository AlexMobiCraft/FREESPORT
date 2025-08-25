
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
            "id",
            "order_number",
            "user",
            "customer_display_name",
            "status",
            "total_amount",
            "discount_amount",
            "delivery_cost",
            "subtotal",
            "total_items",
            "delivery_address",
            "delivery_method",
            "delivery_date",
            "tracking_number",
            "payment_method",
            "payment_status",
            "notes",
            "created_at",
            "updated_at",
            "items",
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
