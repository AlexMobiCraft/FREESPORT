"""
Serializers для каталога товаров
"""
from rest_framework import serializers
from django.db.models import Count, Q
from .models import Product, Category, Brand


class BrandSerializer(serializers.ModelSerializer):
    """
    Serializer для брендов
    """
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description', 'website']


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer для категорий с поддержкой иерархии
    """
    children = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 
            'parent', 'children', 'products_count', 'breadcrumbs',
            'is_active', 'sort_order'
        ]
    
    def get_children(self, obj):
        """Получить дочерние категории"""
        if hasattr(obj, 'prefetched_children'):
            # Если данные уже предзагружены
            children = obj.prefetched_children
            return CategorySerializer(children, many=True, context=self.context).data
        else:
            # Загружаем дочерние категории с подсчетом товаров
            children = obj.children.filter(is_active=True).annotate(
                products_count=Count('products', filter=Q(products__is_active=True))
            ).order_by('sort_order', 'name')
            
            return CategorySerializer(children, many=True, context=self.context).data
    
    def get_products_count(self, obj):
        """Получить количество активных товаров в категории"""
        if hasattr(obj, 'products_count'):
            return obj.products_count
        return obj.products.filter(is_active=True).count()
    
    def get_breadcrumbs(self, obj):
        """Получить навигационную цепочку для категории"""
        breadcrumbs = []
        current = obj
        
        while current:
            breadcrumbs.insert(0, {
                'id': current.id,
                'name': current.name,
                'slug': current.slug
            })
            current = current.parent
        
        return breadcrumbs


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer для списка товаров с ролевым ценообразованием
    """
    brand = BrandSerializer(read_only=True)
    category = serializers.StringRelatedField(read_only=True)
    current_price = serializers.SerializerMethodField()
    price_type = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)
    can_be_ordered = serializers.BooleanField(read_only=True)
    
    # Дополнительные поля для B2B пользователей
    recommended_retail_price = serializers.SerializerMethodField()
    max_suggested_retail_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'category',
            'short_description', 'main_image', 'current_price', 'price_type',
            'recommended_retail_price', 'max_suggested_retail_price',
            'stock_quantity', 'min_order_quantity', 'is_in_stock', 
            'can_be_ordered', 'is_featured', 'created_at'
        ]
    
    def get_current_price(self, obj):
        """Получить текущую цену для пользователя на основе его роли"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return obj.retail_price
        
        return obj.get_price_for_user(request.user)
    
    def get_price_type(self, obj):
        """Получить тип цены для пользователя"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'retail'
        
        return request.user.role
    
    def get_recommended_retail_price(self, obj):
        """RRP отображается только для B2B пользователей"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        if request.user.is_b2b_user:
            return obj.recommended_retail_price
        return None
    
    def get_max_suggested_retail_price(self, obj):
        """MSRP отображается только для B2B пользователей"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        if request.user.is_b2b_user:
            return obj.max_suggested_retail_price
        return None


class ProductDetailSerializer(ProductListSerializer):
    """
    Serializer для детальной информации о товаре
    """
    gallery_images = serializers.JSONField(read_only=True)
    
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'description', 'gallery_images', 'seo_title', 'seo_description'
        ]


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    Специальный serializer для дерева категорий (корневые категории)
    """
    children = serializers.SerializerMethodField()
    products_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image', 'children', 'products_count', 'sort_order']
    
    def get_children(self, obj):
        """Рекурсивно получить все дочерние категории"""
        children = obj.children.filter(is_active=True).annotate(
            products_count=Count('products', filter=Q(products__is_active=True))
        ).order_by('sort_order', 'name')
        
        return CategoryTreeSerializer(children, many=True, context=self.context).data