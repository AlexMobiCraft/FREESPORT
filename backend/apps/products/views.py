"""
Views для каталога товаров
"""
from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Prefetch
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Product, Category, Brand
from .serializers import (
    ProductListSerializer, 
    ProductDetailSerializer,
    CategorySerializer,
    CategoryTreeSerializer,
    BrandSerializer
)
from .filters import ProductFilter


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для товаров с фильтрацией, сортировкой и ролевым ценообразованием
    """
    permission_classes = [permissions.AllowAny]  # Каталог доступен всем
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    ordering_fields = ['name', 'retail_price', 'created_at', 'stock_quantity']
    ordering = ['-created_at']  # Сортировка по умолчанию (override при search)

    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        """Оптимизированный QuerySet с предзагрузкой связанных объектов"""
        return Product.objects.filter(is_active=True).select_related(
            'brand', 'category'
        ).prefetch_related(
            'category__parent'
        ).order_by(self.ordering[0])
    
    def get_serializer_class(self):
        """Выбор serializer в зависимости от действия"""
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer
    
    @extend_schema(
        summary="Список товаров",
        description="Получение списка товаров с фильтрацией, сортировкой и ролевым ценообразованием",
        parameters=[
            OpenApiParameter('category_id', OpenApiTypes.INT, description='ID категории'),
            OpenApiParameter('brand', OpenApiTypes.STR, description='Бренд (ID или slug). Поддерживает множественный выбор: brand=nike,adidas'),
            OpenApiParameter('min_price', OpenApiTypes.NUMBER, description='Минимальная цена'),
            OpenApiParameter('max_price', OpenApiTypes.NUMBER, description='Максимальная цена'),
            OpenApiParameter('in_stock', OpenApiTypes.BOOL, description='Товары в наличии'),
            OpenApiParameter('is_featured', OpenApiTypes.BOOL, description='Рекомендуемые товары'),
            OpenApiParameter(
                'search', 
                OpenApiTypes.STR, 
                description='Полнотекстовый поиск по названию, описанию, артикулу. Поддерживает русский язык, ранжирование по релевантности. Мин. 2 символа, макс. 100'
            ),
            OpenApiParameter('size', OpenApiTypes.STR, description='Размер товара из спецификаций (XS, S, M, L, XL, XXL, 38, 40, 42 и т.д.)'),
            OpenApiParameter('ordering', OpenApiTypes.STR, description='Сортировка: name, -name, retail_price, -retail_price, created_at, -created_at'),
        ],
        tags=["Products"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Детали товара",
        description="Получение детальной информации о товаре",
        tags=["Products"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для категорий с поддержкой иерархии
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        """QuerySet с подсчетом товаров в категориях"""
        return Category.objects.filter(is_active=True).annotate(
            products_count=Count('products', filter=Q(products__is_active=True))
        ).prefetch_related(
            Prefetch(
                'children',
                queryset=Category.objects.filter(is_active=True).annotate(
                    products_count=Count('products', filter=Q(products__is_active=True))
                ),
                to_attr='prefetched_children'
            )
        ).order_by('sort_order', 'name')
    
    @extend_schema(
        summary="Список категорий",
        description="Получение списка всех категорий с иерархией и количеством товаров",
        tags=["Categories"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Детали категории",
        description="Получение детальной информации о категории с навигационной цепочкой",
        tags=["Categories"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class CategoryTreeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для дерева категорий (только корневые категории)
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CategoryTreeSerializer
    
    def get_queryset(self):
        """Только корневые категории с рекурсивной предзагрузкой дочерних"""
        return Category.objects.filter(
            is_active=True, 
            parent__isnull=True
        ).annotate(
            products_count=Count('products', filter=Q(products__is_active=True))
        ).order_by('sort_order', 'name')
    
    @extend_schema(
        summary="Дерево категорий",
        description="Получение иерархического дерева категорий для навигации",
        tags=["Categories"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для брендов
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = BrandSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Только активные бренды"""
        return Brand.objects.filter(is_active=True).order_by('name')
    
    @extend_schema(
        summary="Список брендов",
        description="Получение списка всех активных брендов",
        tags=["Brands"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Детали бренда",
        description="Получение детальной информации о бренде",
        tags=["Brands"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
