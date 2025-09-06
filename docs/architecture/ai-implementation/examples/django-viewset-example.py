"""
Django ViewSet - Реальный пример из проекта FREESPORT
Демонстрирует паттерны ReadOnlyModelViewSet, фильтрации, пагинации, OpenAPI документации
"""
from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Prefetch
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Product, Category, Brand
from .serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    CategorySerializer,
    BrandSerializer,
)
from .filters import ProductFilter


# ✅ ПАТТЕРН: Кастомная пагинация
class CustomPageNumberPagination(PageNumberPagination):
    """Кастомная пагинация с настраиваемым размером страницы"""
    page_size_query_param = 'page_size'
    page_size = 20
    max_page_size = 100


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ✅ РЕАЛЬНЫЙ ПРИМЕР: ViewSet для товаров с фильтрацией и ролевым ценообразованием
    Из apps/products/views.py
    
    КЛЮЧЕВЫЕ ПАТТЕРНЫ:
    - ReadOnlyModelViewSet для каталога (не CRUD)
    - Продвинутая фильтрация через django-filter
    - OpenAPI документация с drf-spectacular
    - Оптимизированные QuerySet с select_related/prefetch_related
    - Динамический выбор serializer
    """

    # ✅ ПАТТЕРН: Публичный доступ к каталогу
    permission_classes = [permissions.AllowAny]
    
    # ✅ ПАТТЕРН: Множественные backend'ы для фильтрации
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter  # Кастомные фильтры
    ordering_fields = ["name", "retail_price", "created_at", "stock_quantity"]
    ordering = ["-created_at"]  # По умолчанию новые первыми
    
    # ✅ ПАТТЕРН: Кастомная пагинация
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        """
        ✅ ПАТТЕРН: Оптимизированный QuerySet
        ВСЕГДА используйте select_related/prefetch_related для ForeignKey
        """
        return (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category")  # ForeignKey оптимизация
            .prefetch_related("category__parent")  # Избегаем N+1 для иерархии
            .order_by(self.ordering[0])
        )

    def get_serializer_class(self):
        """
        ✅ ПАТТЕРН: Динамический serializer
        Разные serializer для list/detail для оптимизации
        """
        if self.action == "retrieve":
            return ProductDetailSerializer  # Полная информация
        return ProductListSerializer  # Только основная информация

    @extend_schema(
        summary="Список товаров",
        description="Получение списка товаров с фильтрацией, сортировкой и ролевым ценообразованием",
        parameters=[
            # ✅ ПАТТЕРН: Подробная OpenAPI документация
            OpenApiParameter("category_id", OpenApiTypes.INT, description="ID категории"),
            OpenApiParameter("brand", OpenApiTypes.STR, description="Бренд (ID или slug). Поддерживает множественный выбор: brand=nike,adidas"),
            OpenApiParameter("min_price", OpenApiTypes.NUMBER, description="Минимальная цена"),
            OpenApiParameter("max_price", OpenApiTypes.NUMBER, description="Максимальная цена"),
        ],
        tags=["Products"],  # ✅ ПАТТЕРН: Группировка в OpenAPI
    )
    def list(self, request, *args, **kwargs):
        """Получение списка товаров"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Детали товара",
        description="Получение детальной информации о товаре",
        tags=["Products"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Получение деталей товара"""
        return super().retrieve(request, *args, **kwargs)


# ✅ ШАБЛОН VIEWSET ДЛЯ НОВЫХ СУЩНОСТЕЙ
class YourNewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Шаблон нового ViewSet по стандартам FREESPORT
    Скопируйте и адаптируйте под свои нужды
    """
    
    # Базовая конфигурация
    permission_classes = [permissions.AllowAny]  # или DRF_DEFAULT_PERMISSION_CLASSES
    serializer_class = YourModelSerializer
    pagination_class = CustomPageNumberPagination
    
    # Фильтрация и сортировка
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = YourModelFilter  # Создайте в filters.py
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]
    search_fields = ["name", "description"]  # Для SearchFilter
    
    # Lookup field (по умолчанию pk, но может быть slug)
    lookup_field = "slug"  # если нужен SEO-friendly URL

    def get_queryset(self):
        """Оптимизированный QuerySet"""
        return (
            YourModel.objects.filter(is_active=True)
            .select_related("foreign_key_field")  # для ForeignKey
            .prefetch_related("many_to_many_field")  # для ManyToMany/обратные FK
            .order_by(*self.ordering)
        )

    @extend_schema(
        summary="Список ваших объектов",
        description="Подробное описание endpoint'а",
        parameters=[
            OpenApiParameter("param1", OpenApiTypes.STR, description="Описание параметра"),
        ],
        tags=["YourModel"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)