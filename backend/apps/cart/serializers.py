"""
Serializers для корзины покупок
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Cart, CartItem
from apps.products.models import Product

User = get_user_model()


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer для элемента корзины с ценовой информацией
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_image = serializers.URLField(source='product.main_image.url', read_only=True)
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'product_image',
            'quantity', 'unit_price', 'total_price', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_unit_price(self, obj):
        """Получить цену товара для пользователя корзины"""
        user = obj.cart.user
        price = obj.product.get_price_for_user(user)
        return f"{price:.2f}"


class CartItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer для создания элемента корзины
    """
    class Meta:
        model = CartItem
        fields = ['product', 'quantity']
    
    def validate_product(self, value):
        """Валидация товара"""
        if not value.is_active:
            raise serializers.ValidationError("Товар неактивен")
        return value
    
    def validate(self, attrs):
        """Дополнительная валидация"""
        product = attrs['product']
        quantity = attrs['quantity']
        
        # Проверяем наличие на складе
        if quantity > product.stock_quantity:
            raise serializers.ValidationError(
                f"Недостаточно товара на складе. Доступно: {product.stock_quantity}"
            )
        
        # Проверяем минимальное количество заказа
        if quantity < product.min_order_quantity:
            raise serializers.ValidationError(
                f"Минимальное количество заказа: {product.min_order_quantity}"
            )
        
        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer для обновления количества в элементе корзины
    """
    class Meta:
        model = CartItem
        fields = ['quantity']
    
    def validate_quantity(self, value):
        """Валидация количества"""
        if value < 1:
            raise serializers.ValidationError("Количество должно быть больше 0")
        return value
    
    def validate(self, attrs):
        """Валидация остатков на складе"""
        quantity = attrs['quantity']
        product = self.instance.product
        
        if quantity > product.stock_quantity:
            raise serializers.ValidationError(
                f"Недостаточно товара на складе. Доступно: {product.stock_quantity}"
            )
        
        return attrs


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer для корзины с полной информацией
    """
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'total_items', 'total_amount', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']