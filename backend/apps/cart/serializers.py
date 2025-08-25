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
<<<<<<< HEAD
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_image = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.ReadOnlyField()
    # Добавляем вложенный объект продукта для совместимости с тестами
    product = serializers.SerializerMethodField()
    
=======

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_image = serializers.URLField(
        source="product.main_image.url", read_only=True
    )
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.ReadOnlyField()

>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "product_image",
            "quantity",
            "unit_price",
            "total_price",
            "added_at",
        ]
<<<<<<< HEAD
        read_only_fields = ['id', 'added_at']
    
    def get_product_image(self, obj):
        """Получить URL изображения товара"""
        if obj.product.main_image:
            request = self.context.get('request')
            if request and hasattr(request, 'build_absolute_uri'):
                return request.build_absolute_uri(obj.product.main_image.url)
            return obj.product.main_image.url
        return None
    
=======
        read_only_fields = ["id", "added_at"]

>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
    def get_unit_price(self, obj):
        """Получить цену товара для пользователя корзины"""
        user = obj.cart.user
        price = obj.product.get_price_for_user(user)
        return price
    
    def get_product(self, obj):
        """Получить информацию о продукте для совместимости с тестами"""
        product = obj.product
        user = obj.cart.user
        
        data = {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'retail_price': str(product.retail_price),
        }
        
        # Добавляем B2B цены если пользователь B2B
        if user and hasattr(user, 'is_b2b_user') and user.is_b2b_user:
            if hasattr(product, 'opt1_price') and product.opt1_price:
                data['opt1_price'] = str(product.opt1_price)
            if hasattr(product, 'opt2_price') and product.opt2_price:
                data['opt2_price'] = str(product.opt2_price)
            if hasattr(product, 'opt3_price') and product.opt3_price:
                data['opt3_price'] = str(product.opt3_price)
        
        return data


class CartItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer для создания элемента корзины
    """

    class Meta:
        model = CartItem
        fields = ["product", "quantity"]

    def validate_product(self, value):
        """Валидация товара"""
        if not value.is_active:
            raise serializers.ValidationError("Товар неактивен")
        return value

    def validate(self, attrs):
        """Дополнительная валидация"""
        product = attrs["product"]
        quantity = attrs["quantity"]

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
        fields = ["quantity"]

    def validate_quantity(self, value):
        """Валидация количества"""
        if value < 1:
            raise serializers.ValidationError("Количество должно быть больше 0")
        return value

    def validate(self, attrs):
        """Валидация остатков на складе"""
        quantity = attrs["quantity"]
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
<<<<<<< HEAD
    total_amount = serializers.SerializerMethodField()
    
=======
    total_amount = serializers.ReadOnlyField()

>>>>>>> b9cb5403e397f615917fa522c8bf3e0f81cc0fcf
    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "total_amount",
            "created_at",
            "updated_at",
        ]
<<<<<<< HEAD
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_amount(self, obj):
        """Получить общую стоимость корзины как число"""
        return obj.total_amount
=======
        read_only_fields = ["id", "created_at", "updated_at"]
>>>>>>> b9cb5403e397f615917fa522c8bf3e0f81cc0fcf
