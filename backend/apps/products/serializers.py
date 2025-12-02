"""
Serializers для каталога товаров
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db.models import Count, Q
from rest_framework import serializers

from .models import Brand, Category, ColorMapping, Product, ProductImage, ProductVariant

if TYPE_CHECKING:
    from apps.users.models import User


class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Serializer для ProductVariant с роле-ориентированной ценой

    Поля:
    - current_price: цена для текущего пользователя (роле-ориентированная)
    - color_hex: hex-код цвета из ColorMapping
    - is_in_stock: computed property из модели
    - available_quantity: computed property из модели
    """

    current_price = serializers.SerializerMethodField()
    color_hex = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "color_name",
            "size_value",
            "current_price",
            "color_hex",
            "stock_quantity",
            "is_in_stock",
            "available_quantity",
            "main_image",
            "gallery_images",
        ]
        read_only_fields = fields  # Все поля read-only

    def get_current_price(self, obj: ProductVariant) -> str:
        """
        Получить роле-ориентированную цену для текущего пользователя

        Args:
            obj: ProductVariant instance

        Returns:
            str: Цена как строка (сериализация Decimal)
        """
        request = self.context.get("request")
        user: User | None = request.user if request else None

        price: Decimal = obj.get_price_for_user(user)
        return str(price)  # Сериализация Decimal → str

    def get_color_hex(self, obj: ProductVariant) -> str | None:
        """
        Получить hex-код цвета из ColorMapping

        Args:
            obj: ProductVariant instance

        Returns:
            str | None: Hex-код цвета или None если маппинг не найден
        """
        if not obj.color_name:
            return None

        try:
            mapping = ColorMapping.objects.get(name=obj.color_name)
            return mapping.hex_code
        except ColorMapping.DoesNotExist:
            return None  # Fallback на None (frontend покажет текст)




class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer для изображений товара
    """

    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["url", "alt_text", "is_main", "sort_order"]

    def get_url(self, obj):
        """Получить URL изображения с учетом контекста запроса"""
        if isinstance(obj, dict):
            return obj.get("url", "")

        # Если obj - это модель с полем изображения
        if hasattr(obj, "url"):
            url = obj.url
        elif hasattr(obj, "image") and hasattr(obj.image, "url"):
            url = obj.image.url
        else:
            return ""

        request = self.context.get("request")
        if request and hasattr(request, "build_absolute_uri"):
            return request.build_absolute_uri(url)
        return url


class BrandSerializer(serializers.ModelSerializer):
    """
    Serializer для брендов
    """

    slug = serializers.SlugField(required=False)

    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo", "description", "website"]

    def validate(self, attrs):
        """Автоматически создаём slug если не указан"""
        if not attrs.get("slug") and attrs.get("name"):
            from django.utils.text import slugify

            attrs["slug"] = slugify(attrs["name"])
        return attrs


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
            "id",
            "name",
            "slug",
            "description",
            "image",
            "parent",
            "children",
            "products_count",
            "breadcrumbs",
            "is_active",
            "sort_order",
        ]

    def get_children(self, obj):
        """Получить дочерние категории"""
        if hasattr(obj, "prefetched_children"):
            # Если данные уже предзагружены
            children = obj.prefetched_children
            return CategorySerializer(children, many=True, context=self.context).data
        else:
            # Загружаем дочерние категории с подсчетом товаров
            children = (
                obj.children.filter(is_active=True)
                .annotate(
                    products_count=Count("products", filter=Q(products__is_active=True))
                )
                .order_by("sort_order", "name")
            )

            return CategorySerializer(children, many=True, context=self.context).data

    def get_products_count(self, obj):
        """Получить количество активных товаров в категории"""
        if hasattr(obj, "products_count"):
            return obj.products_count
        return obj.products.filter(is_active=True).count()

    def get_breadcrumbs(self, obj):
        """Получить навигационную цепочку для категории"""
        breadcrumbs: list[dict[str, Any]] = []
        current = obj

        while current:
            breadcrumbs.insert(
                0, {"id": current.id, "name": current.name, "slug": current.slug}
            )
            current = current.parent

        return breadcrumbs


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer для списка товаров с ролевым ценообразованием
    """

    brand = BrandSerializer(read_only=True)
    category: Any = serializers.StringRelatedField(read_only=True)
    current_price = serializers.SerializerMethodField()
    price_type = serializers.SerializerMethodField()
    can_be_ordered = serializers.BooleanField(read_only=True)
    specifications = serializers.JSONField(read_only=True)

    # Дополнительные поля для B2B пользователей
    rrp = serializers.SerializerMethodField()
    msrp = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "brand",
            "category",
            "short_description",
            "main_image",
            "current_price",
            "price_type",
            "retail_price",
            "rrp",
            "msrp",
            "specifications",
            "stock_quantity",
            "min_order_quantity",
            "can_be_ordered",
            "is_featured",
            # Story 11.0: Маркетинговые флаги для бейджей
            "is_hit",
            "is_new",
            "is_sale",
            "is_promo",
            "is_premium",
            "discount_percent",
            "created_at",
        ]
        read_only_fields = [
            "is_hit",
            "is_new",
            "is_sale",
            "is_promo",
            "is_premium",
            "discount_percent",
        ]

    def get_current_price(self, obj):
        """Получить текущую цену для пользователя на основе его роли"""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return f"{obj.retail_price:.2f}"

        price = obj.get_price_for_user(request.user)
        return f"{price:.2f}"

    def get_price_type(self, obj):
        """Получить тип цены для пользователя"""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return "retail"

        return request.user.role

    def get_rrp(self, obj):
        """RRP отображается только для B2B пользователей"""
        request = self.context.get("request")
        if (
            request
            and request.user.is_authenticated
            and request.user.is_b2b_user
            and obj.recommended_retail_price
        ):
            return f"{obj.recommended_retail_price:.2f}"
        return None

    def get_msrp(self, obj):
        """MSRP отображается только для B2B пользователей"""
        request = self.context.get("request")
        if (
            request
            and request.user.is_authenticated
            and request.user.is_b2b_user
            and obj.max_suggested_retail_price
        ):
            return f"{obj.max_suggested_retail_price:.2f}"
        return None

    def to_representation(self, instance):
        """Conditionally remove rrp and msrp for non-B2B users."""
        ret = super().to_representation(instance)
        request = self.context.get("request")
        if (
            not request
            or not request.user.is_authenticated
            or not request.user.is_b2b_user
        ):
            ret.pop("rrp", None)
            ret.pop("msrp", None)
        return ret


class ProductDetailSerializer(ProductListSerializer):
    """
    Serializer для детальной информации о товаре с расширенными полями
    """

    images = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    category_breadcrumbs = serializers.SerializerMethodField()
    specifications = serializers.JSONField(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description",
            "specifications",
            "images",
            "related_products",
            "category_breadcrumbs",
            "seo_title",
            "seo_description",
            "variants",
        ]

    def get_images(self, obj):
        """Получить галерею изображений включая основное"""
        images = []
        request = self.context.get("request")

        # Основное изображение
        if obj.main_image:
            url = obj.main_image.url
            if request and hasattr(request, "build_absolute_uri"):
                url = request.build_absolute_uri(url)

            images.append(
                {
                    "url": url,
                    "alt_text": f"{obj.name} - основное изображение",
                    "is_main": True,
                }
            )

        # Дополнительные изображения из gallery_images
        if obj.gallery_images:
            for idx, img_url in enumerate(obj.gallery_images):
                url = img_url
                if request and hasattr(request, "build_absolute_uri"):
                    url = request.build_absolute_uri(url)

                images.append(
                    {
                        "url": url,
                        "alt_text": f"{obj.name} - изображение {idx + 2}",
                        "is_main": False,
                    }
                )

        return images

    def get_related_products(self, obj):
        """Получить связанные товары из той же категории или бренда"""
        # Сначала товары из той же категории
        related_by_category = (
            Product.objects.filter(category=obj.category, is_active=True)
            .exclude(id=obj.id)
            .select_related("brand", "category")[:5]
        )

        # Если меньше 5, добавляем товары того же бренда
        if len(related_by_category) < 5:
            related_by_brand = (
                Product.objects.filter(brand=obj.brand, is_active=True)
                .exclude(id__in=[obj.id] + [p.id for p in related_by_category])
                .select_related("brand", "category")[: 5 - len(related_by_category)]
            )

            related_products = list(related_by_category) + list(related_by_brand)
        else:
            related_products = list(related_by_category)

        return ProductListSerializer(
            related_products, many=True, context=self.context
        ).data

    def get_category_breadcrumbs(self, obj):
        """Получить навигационную цепочку для категории товара"""
        breadcrumbs: list[dict[str, Any]] = []
        current = obj.category

        while current:
            breadcrumbs.insert(
                0, {"id": current.id, "name": current.name, "slug": current.slug}
            )
            current = current.parent

        return breadcrumbs


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    Специальный serializer для дерева категорий (корневые категории)
    """

    children = serializers.SerializerMethodField()
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "image",
            "children",
            "products_count",
            "sort_order",
        ]

    def get_children(self, obj):
        """Рекурсивно получить все дочерние категории"""
        children = (
            obj.children.filter(is_active=True)
            .annotate(
                products_count=Count("products", filter=Q(products__is_active=True))
            )
            .order_by("sort_order", "name")
        )

        return CategoryTreeSerializer(children, many=True, context=self.context).data
