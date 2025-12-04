"""
Фильтры для каталога товаров
"""

import django_filters
from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.db.models import Q

from .models import Brand, Category, Product


class ProductFilter(django_filters.FilterSet):
    """
    Фильтр для товаров согласно Story 2.4 и 2.9 требованиям
    """

    # Фильтр по категории (с учетом дочерних)
    category_id = django_filters.NumberFilter(
        method="filter_category_id",
        help_text="ID категории для фильтрации (включая дочерние категории)",
    )

    # Фильтр по бренду (поддерживает как ID, так и slug)
    brand = django_filters.CharFilter(
        method="filter_brand",
        help_text=(
            "Бренд по ID или slug. Поддерживает множественный выбор: brand=nike,adidas"
        ),
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
        method="filter_search",
        help_text=(
            "Полнотекстовый поиск по названию, описанию и артикулу "
            "(PostgreSQL FTS с русскоязычной конфигурацией)"
        ),
    )

    # Фильтр по размеру из JSON specifications
    size = django_filters.CharFilter(
        method="filter_size",
        help_text=(
            "Размер из спецификаций товара (XS, S, M, L, XL, XXL, 38, 40, 42 и т.д.)"
        ),
    )

    # Story 11.0: Маркетинговые фильтры для бейджей
    is_hit = django_filters.BooleanFilter(field_name="is_hit", help_text="Хиты продаж")
    is_new = django_filters.BooleanFilter(field_name="is_new", help_text="Новинки")
    is_sale = django_filters.BooleanFilter(
        field_name="is_sale", help_text="Товары на распродаже"
    )
    is_promo = django_filters.BooleanFilter(
        field_name="is_promo", help_text="Акционные товары"
    )
    is_premium = django_filters.BooleanFilter(
        field_name="is_premium", help_text="Премиум товары"
    )
    has_discount = django_filters.BooleanFilter(
        method="filter_has_discount",
        help_text="Товары со скидкой (имеют discount_percent)",
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
            "size",
            # Story 11.0: Маркетинговые фильтры
            "is_hit",
            "is_new",
            "is_sale",
            "is_promo",
            "is_premium",
            "has_discount",
        ]

    def filter_brand(self, queryset, name, value):
        """Фильтр по бренду через ID или slug с поддержкой множественного выбора"""
        if not value:
            return queryset

        # Поддержка множественных значений: brand=nike,adidas
        brand_values = [v.strip() for v in value.split(",") if v.strip()]
        if not brand_values:
            return queryset

        # Создаем Q-объект для множественного выбора
        brand_queries = Q()

        for brand_value in brand_values:
            if brand_value.isdigit():
                # Фильтр по ID
                brand_queries |= Q(brand__id=brand_value)
            else:
                # Фильтр по slug (case-insensitive)
                brand_queries |= Q(brand__slug__iexact=brand_value)

        return queryset.filter(brand_queries)

    def filter_category_id(self, queryset, name, value):
        """Фильтрует товары по категории и всем её дочерним категориям"""
        if not value:
            return queryset

        try:
            category_id = int(value)
        except (TypeError, ValueError):
            return queryset

        if not Category.objects.filter(id=category_id, is_active=True).exists():
            return queryset.none()

        category_ids = {category_id}
        to_process = [category_id]

        while to_process:
            children = list(
                Category.objects.filter(
                    parent_id__in=to_process, is_active=True
                ).values_list("id", flat=True)
            )

            new_children = [
                child_id for child_id in children if child_id not in category_ids
            ]
            if not new_children:
                break

            category_ids.update(new_children)
            to_process = new_children

        return queryset.filter(category__id__in=category_ids)

    def filter_min_price(self, queryset, name, value):
        """Фильтр по минимальной цене с учетом роли пользователя"""
        # Валидация значения
        if value is None or value < 0:
            return queryset

        request = self.request
        if not request or not request.user.is_authenticated:
            return queryset.filter(variants__retail_price__gte=value).distinct()

        user_role = request.user.role

        # Определяем поле цены в зависимости от роли
        if user_role == "wholesale_level1":
            return queryset.filter(
                Q(variants__opt1_price__gte=value)
                | Q(variants__opt1_price__isnull=True, variants__retail_price__gte=value)
            ).distinct()
        elif user_role == "wholesale_level2":
            return queryset.filter(
                Q(variants__opt2_price__gte=value)
                | Q(variants__opt2_price__isnull=True, variants__retail_price__gte=value)
            ).distinct()
        elif user_role == "wholesale_level3":
            return queryset.filter(
                Q(variants__opt3_price__gte=value)
                | Q(variants__opt3_price__isnull=True, variants__retail_price__gte=value)
            ).distinct()
        elif user_role == "trainer":
            return queryset.filter(
                Q(variants__trainer_price__gte=value)
                | Q(variants__trainer_price__isnull=True, variants__retail_price__gte=value)
            ).distinct()
        elif user_role == "federation_rep":
            return queryset.filter(
                Q(variants__federation_price__gte=value)
                | Q(variants__federation_price__isnull=True, variants__retail_price__gte=value)
            ).distinct()
        else:
            return queryset.filter(variants__retail_price__gte=value).distinct()

    def filter_max_price(self, queryset, name, value):
        """Фильтр по максимальной цене с учетом роли пользователя"""
        # Валидация значения
        if value is None or value < 0:
            return queryset

        request = self.request
        if not request or not request.user.is_authenticated:
            return queryset.filter(variants__retail_price__lte=value).distinct()

        user_role = request.user.role

        # Определяем поле цены в зависимости от роли
        if user_role == "wholesale_level1":
            return queryset.filter(
                Q(variants__opt1_price__lte=value)
                | Q(variants__opt1_price__isnull=True, variants__retail_price__lte=value)
            ).distinct()
        elif user_role == "wholesale_level2":
            return queryset.filter(
                Q(variants__opt2_price__lte=value)
                | Q(variants__opt2_price__isnull=True, variants__retail_price__lte=value)
            ).distinct()
        elif user_role == "wholesale_level3":
            return queryset.filter(
                Q(variants__opt3_price__lte=value)
                | Q(variants__opt3_price__isnull=True, variants__retail_price__lte=value)
            ).distinct()
        elif user_role == "trainer":
            return queryset.filter(
                Q(variants__trainer_price__lte=value)
                | Q(variants__trainer_price__isnull=True, variants__retail_price__lte=value)
            ).distinct()
        elif user_role == "federation_rep":
            return queryset.filter(
                Q(variants__federation_price__lte=value)
                | Q(variants__federation_price__isnull=True, variants__retail_price__lte=value)
            ).distinct()
        else:
            return queryset.filter(variants__retail_price__lte=value).distinct()

    def filter_in_stock(self, queryset, name, value):
        """Фильтр по наличию товара с учетом флага is_active"""
        if value:
            # Товары в наличии: есть хотя бы один вариант с количеством > 0
            return queryset.filter(variants__stock_quantity__gt=0, is_active=True).distinct()
        else:
            # Товары НЕ в наличии: все варианты имеют 0 или товар неактивен
            # Или у товара вообще нет вариантов
            return queryset.filter(
                Q(variants__stock_quantity=0) | Q(variants__isnull=True) | Q(is_active=False)
            ).distinct()

    def filter_search(self, queryset, name, value):
        """Полнотекстовый поиск с поддержкой PostgreSQL FTS и fallback для других БД"""
        if not value:
            return queryset

        # Валидация длины запроса и защита от XSS
        search_query = value.strip()
        if len(search_query) > 100 or "<" in search_query or ">" in search_query:
            return queryset.none()

        if len(search_query) < 2:
            return queryset

        # Проверяем тип базы данных
        from django.db import connection

        if connection.vendor == "postgresql":
            # PostgreSQL full-text search с русскоязычной конфигурацией
            search_vector = (
                SearchVector("name", weight="A", config="russian")
                + SearchVector("short_description", weight="B", config="russian")
                + SearchVector("description", weight="C", config="russian")
                + SearchVector("sku", weight="A", config="russian")
            )

            search_query_obj = SearchQuery(search_query, config="russian")

            # Добавляем Q-объект для поиска по SKU через icontains
            sku_q = Q(sku__icontains=search_query)

            # Возвращаем результаты с ранжированием по релевантности
            return (
                queryset.annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query_obj),
                )
                .filter(Q(search=search_query_obj) | sku_q)
                .order_by("-rank", "-created_at")
            )
        else:
            # Fallback для SQLite и других БД - простой icontains поиск с приоритизацией
            from django.db.models import Case, IntegerField, Value, When

            # Поиск точного совпадения в названии (высший приоритет)
            exact_name = queryset.filter(name__iexact=search_query)
            # Если найдены точные совпадения, возвращаем их
            if exact_name.exists():
                return exact_name.order_by("-created_at")

            # Поиск частичного совпадения с приоритизацией
            # по полям (регистронезависимый)
            name_match = Q(name__icontains=search_query)
            sku_match = Q(sku__icontains=search_query)
            desc_match = Q(short_description__icontains=search_query) | Q(
                description__icontains=search_query
            )

            # Применяем фильтр
            results = queryset.filter(name_match | sku_match | desc_match)

            # Добавляем аннотацию для приоритизации и сортируем
            prioritized_results = results.annotate(
                priority=Case(
                    When(name_match, then=Value(1)),
                    When(sku_match, then=Value(2)),
                    When(desc_match, then=Value(3)),
                    default=Value(4),
                    output_field=IntegerField(),
                )
            ).order_by("priority", "-created_at")

            return prioritized_results

    def filter_size(self, queryset, name, value):
        """
        Фильтрация по размеру из JSON поля specifications

        ВАЖНО: Работает только с PostgreSQL. SQLite не поддерживается.
        """
        if not value:
            return queryset

        # Нормализуем значение размера
        size_value = value.strip()
        if not size_value:
            return queryset

        # Создаем Q-объекты для различных вариантов хранения размера в JSON
        size_queries = Q()

        # Вариант 1: {"size": "XL"} - одиночный размер
        size_queries |= Q(specifications__size=size_value)

        # Вариант 3: {"размер": "XL"} - русский ключ
        size_queries |= Q(specifications__размер=size_value)

        # Проверяем, используется ли PostgreSQL для поддержки contains lookup
        is_postgresql = connection.vendor == "postgresql"

        if is_postgresql:
            # Вариант 2: {"sizes": ["M", "L", "XL"]} - массив размеров (PostgreSQL)
            size_queries |= Q(specifications__sizes__contains=[size_value])

            # Вариант 4: {"размеры": ["M", "L", "XL"]} - русский массив (PostgreSQL)
            size_queries |= Q(specifications__размеры__contains=[size_value])

            # Вариант 5: Case-insensitive поиск для строковых значений (PostgreSQL)
            size_queries |= Q(specifications__size__iexact=size_value)
            size_queries |= Q(specifications__размер__iexact=size_value)

        return queryset.filter(size_queries)

    def filter_has_discount(self, queryset, name, value):
        """Фильтр товаров со скидкой (discount_percent не null)"""
        if value:
            # Товары со скидкой
            return queryset.filter(discount_percent__isnull=False)
        else:
            # Товары без скидки
            return queryset.filter(discount_percent__isnull=True)
