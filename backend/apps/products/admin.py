"""
Django Admin для приложения products
"""
from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Brand, Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    """Инлайн для изображений продукта"""

    model = ProductImage
    extra = 1  # Количество пустых форм для добавления
    fields = ("image", "alt_text", "is_main", "sort_order")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Admin для модели Brand"""

    list_display = ("name", "slug", "onec_id", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "slug", "onec_id")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin для модели Category"""

    list_display = ("name", "slug", "parent", "onec_id", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "slug", "onec_id")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("parent",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin для модели Product"""

    list_display = (
        "name",
        "sku",
        "brand",
        "category",
        "retail_price",
        "stock_quantity",
        "is_active",
        # Story 11.0: Маркетинговые флаги
        "is_hit",
        "is_new",
        "is_sale",
        "is_promo",
        "is_premium",
        "discount_percent",
        "onec_id",
    )
    list_filter = (
        "is_active",
        "brand",
        "category",
        "sync_status",
        # Story 11.0: Маркетинговые фильтры
        "is_hit",
        "is_new",
        "is_sale",
        "is_promo",
        "is_premium",
        "created_at",
    )
    search_fields = ("name", "sku", "onec_id", "parent_onec_id")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "created_at",
        "updated_at",
        "last_sync_at",
        "sync_status",
        "error_message",
    )
    raw_id_fields = ("brand", "category")
    inlines = [ProductImageInline]  # Добавляем инлайн для изображений
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "name",
                    "slug",
                    "brand",
                    "category",
                    "description",
                    "short_description",
                )
            },
        ),
        (
            "Ценообразование",
            {
                "fields": (
                    "retail_price",
                    "opt1_price",
                    "opt2_price",
                    "opt3_price",
                    "trainer_price",
                    "federation_price",
                    "recommended_retail_price",
                    "max_suggested_retail_price",
                )
            },
        ),
        (
            "Инвентаризация",
            {
                "fields": (
                    "sku",
                    "stock_quantity",
                    "reserved_quantity",
                )
            },
        ),
        (
            "Медиа и изображения",
            {
                "fields": ("main_image",),
            },
        ),
        (
            "Характеристики",
            {
                "fields": ("specifications",),
            },
        ),
        (
            "Интеграция с 1С",
            {
                "fields": (
                    "onec_id",
                    "parent_onec_id",
                    "sync_status",
                    "last_sync_at",
                    "error_message",
                ),
            },
        ),
        (
            "Маркетинговые флаги (Story 11.0)",
            {
                "fields": (
                    "is_hit",
                    "is_new",
                    "is_sale",
                    "is_promo",
                    "is_premium",
                    "discount_percent",
                ),
            },
        ),
        (
            "Статус и даты",
            {
                "fields": ("is_active", "created_at", "updated_at"),
            },
        ),
    )

    # Story 11.0: Массовые действия для маркетинговых флагов
    actions = [
        "mark_as_hit",
        "unmark_as_hit",
        "mark_as_new",
        "unmark_as_new",
        "mark_as_sale",
        "unmark_as_sale",
        "mark_as_promo",
        "unmark_as_promo",
        "mark_as_premium",
        "unmark_as_premium",
    ]

    @admin.action(description="✓ Отметить как хит продаж")
    def mark_as_hit(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """Массовое действие: пометить как хит продаж"""
        updated = queryset.update(is_hit=True)
        self.message_user(request, f"Отмечено хитами продаж: {updated} товаров")

    @admin.action(description="✗ Снять отметку хит продаж")
    def unmark_as_hit(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """Массовое действие: снять отметку хит продаж"""
        updated = queryset.update(is_hit=False)
        self.message_user(request, f"Снята отметка хитов продаж: {updated} товаров")

    @admin.action(description="✓ Отметить как новинку")
    def mark_as_new(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """Массовое действие: пометить как новинку"""
        updated = queryset.update(is_new=True)
        self.message_user(request, f"Отмечено новинками: {updated} товаров")

    @admin.action(description="✗ Снять отметку новинка")
    def unmark_as_new(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """Массовое действие: снять отметку новинка"""
        updated = queryset.update(is_new=False)
        self.message_user(request, f"Снята отметка новинок: {updated} товаров")

    @admin.action(description="✓ Отметить как распродажа")
    def mark_as_sale(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """Массовое действие: пометить как распродажа"""
        updated = queryset.update(is_sale=True)
        self.message_user(request, f"Отмечено распродажей: {updated} товаров")

    @admin.action(description="✗ Снять отметку распродажа")
    def unmark_as_sale(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """Массовое действие: снять отметку распродажа"""
        updated = queryset.update(is_sale=False)
        self.message_user(request, f"Снята отметка распродажи: {updated} товаров")

    @admin.action(description="✓ Отметить как акция")
    def mark_as_promo(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """Массовое действие: пометить как акция"""
        updated = queryset.update(is_promo=True)
        self.message_user(request, f"Отмечено акцией: {updated} товаров")

    @admin.action(description="✗ Снять отметку акция")
    def unmark_as_promo(
        self, request: HttpRequest, queryset: QuerySet[Product]
    ) -> None:
        """Массовое действие: снять отметку акция"""
        updated = queryset.update(is_promo=False)
        self.message_user(request, f"Снята отметка акции: {updated} товаров")

    @admin.action(description="✓ Отметить как премиум")
    def mark_as_premium(
        self, request: HttpRequest, queryset: QuerySet[Product]
    ) -> None:
        """Массовое действие: пометить как премиум"""
        updated = queryset.update(is_premium=True)
        self.message_user(request, f"Отмечено премиум: {updated} товаров")

    @admin.action(description="✗ Снять отметку премиум")
    def unmark_as_premium(
        self, request: HttpRequest, queryset: QuerySet[Product]
    ) -> None:
        """Массовое действие: снять отметку премиум"""
        updated = queryset.update(is_premium=False)
        self.message_user(request, f"Снята отметка премиум: {updated} товаров")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Product]:
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related("brand", "category")
