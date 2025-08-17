"""
Фильтры для каталога товаров
"""
import django_filters
from django.db.models import Q
from .models import Product, Category, Brand


class ProductFilter(django_filters.FilterSet):
    """
    Фильтр для товаров согласно Story 2.4 требованиям
    """

    # Фильтр по категории
    category_id = django_filters.NumberFilter(
        field_name="category__id", help_text="ID категории для фильтрации"
    )

    # Фильтр по бренду (поддерживает как ID, так и slug)
    brand = django_filters.CharFilter(
        method="filter_brand", help_text="Бренд по ID или slug"
    )

    # Ценовой диапазон
    min_price = django_filters.NumberFilter(
        method="filter_min_price",
        help_text="Минимальная цена (адаптируется к роли пользователя)",
    )

    max_price = django_filters.NumberFilter(
        method="filter_max_price",
        help_text="Максимальная цена (адаптируется к роли пользователя)",
    )

    # Фильтр по наличию
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock", help_text="Товары в наличии (true/false)"
    )

    # Дополнительные фильтры
    is_featured = django_filters.BooleanFilter(
        field_name="is_featured", help_text="Рекомендуемые товары"
    )

    search = django_filters.CharFilter(
        method="filter_search", help_text="Поиск по названию товара и артикулу"
    )

    class Meta:
        model = Product
        fields = [
            "category_id",
            "brand",
            "min_price",
            "max_price",
            "in_stock",
            "is_featured",
            "search",
        ]

    def filter_brand(self, queryset, name, value):
        """Фильтр по бренду через ID или slug"""
        if value.isdigit():
            # Фильтр по ID
            return queryset.filter(brand__id=value)
        else:
            # Фильтр по slug
            return queryset.filter(brand__slug=value)

    def filter_min_price(self, queryset, name, value):
        """Фильтр по минимальной цене с учетом роли пользователя"""
        request = self.request
        if not request or not request.user.is_authenticated:
            return queryset.filter(retail_price__gte=value)

        user_role = request.user.role

        # Определяем поле цены в зависимости от роли
        if user_role == "wholesale_level1":
            return queryset.filter(
                Q(opt1_price__gte=value)
                | Q(opt1_price__isnull=True, retail_price__gte=value)
            )
        elif user_role == "wholesale_level2":
            return queryset.filter(
                Q(opt2_price__gte=value)
                | Q(opt2_price__isnull=True, retail_price__gte=value)
            )
        elif user_role == "wholesale_level3":
            return queryset.filter(
                Q(opt3_price__gte=value)
                | Q(opt3_price__isnull=True, retail_price__gte=value)
            )
        elif user_role == "trainer":
            return queryset.filter(
                Q(trainer_price__gte=value)
                | Q(trainer_price__isnull=True, retail_price__gte=value)
            )
        elif user_role == "federation_rep":
            return queryset.filter(
                Q(federation_price__gte=value)
                | Q(federation_price__isnull=True, retail_price__gte=value)
            )
        else:
            return queryset.filter(retail_price__gte=value)

    def filter_max_price(self, queryset, name, value):
        """Фильтр по максимальной цене с учетом роли пользователя"""
        request = self.request
        if not request or not request.user.is_authenticated:
            return queryset.filter(retail_price__lte=value)

        user_role = request.user.role

        # Определяем поле цены в зависимости от роли
        if user_role == "wholesale_level1":
            return queryset.filter(
                Q(opt1_price__lte=value)
                | Q(opt1_price__isnull=True, retail_price__lte=value)
            )
        elif user_role == "wholesale_level2":
            return queryset.filter(
                Q(opt2_price__lte=value)
                | Q(opt2_price__isnull=True, retail_price__lte=value)
            )
        elif user_role == "wholesale_level3":
            return queryset.filter(
                Q(opt3_price__lte=value)
                | Q(opt3_price__isnull=True, retail_price__lte=value)
            )
        elif user_role == "trainer":
            return queryset.filter(
                Q(trainer_price__lte=value)
                | Q(trainer_price__isnull=True, retail_price__lte=value)
            )
        elif user_role == "federation_rep":
            return queryset.filter(
                Q(federation_price__lte=value)
                | Q(federation_price__isnull=True, retail_price__lte=value)
            )
        else:
            return queryset.filter(retail_price__lte=value)

    def filter_in_stock(self, queryset, name, value):
        """Фильтр по наличию товара"""
        if value:
            return queryset.filter(stock_quantity__gt=0)
        else:
            return queryset.filter(stock_quantity=0)

    def filter_search(self, queryset, name, value):
        """Поиск по названию товара и артикулу"""
        return queryset.filter(
            Q(name__icontains=value)
            | Q(sku__icontains=value)
            | Q(short_description__icontains=value)
        )
