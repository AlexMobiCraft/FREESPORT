"""
Django Admin для приложения products
"""

from __future__ import annotations

import logging
from typing import Any

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render

from .forms import MergeBrandsActionForm, TransferMappingsActionForm
from .models import (
    Attribute,
    AttributeValue,
    Brand,
    Brand1CMapping,
    Category,
    ColorMapping,
    Product,
    ProductImage,
    ProductVariant,
)

logger = logging.getLogger(__name__)


class ProductImageInline(admin.TabularInline):
    """Инлайн для изображений продукта"""

    model = ProductImage
    extra = 1  # Количество пустых форм для добавления
    fields = ("image", "alt_text", "is_main", "sort_order")
    readonly_fields = ("created_at", "updated_at")


class Brand1CMappingInline(admin.TabularInline):
    """Инлайн маппингов 1С для бренда"""

    model = Brand1CMapping
    extra = 0
    readonly_fields = ("created_at",)
    classes = ("collapse",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Admin для модели Brand"""

    list_display = (
        "name",
        "slug",
        "normalized_name",
        "mappings_count",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "slug", "normalized_name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("normalized_name", "created_at", "updated_at")
    inlines = [Brand1CMappingInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Brand]:
        """Оптимизация запросов и аннотация количества маппингов"""
        qs = super().get_queryset(request)
        return qs.annotate(mappings_count=Count("onec_mappings"))

    @admin.display(description="Маппинги 1С", ordering="mappings_count")
    def mappings_count(self, obj: Brand) -> int:
        """Возвращает количество связанных маппингов 1С"""
        return getattr(obj, "mappings_count", 0)

    @admin.action(description="Объединить выбранные бренды")
    def merge_brands(self, request: HttpRequest, queryset: QuerySet[Brand]) -> Any:
        """Действие для объединения нескольких брендов в один"""
        if "apply" in request.POST:
            form = MergeBrandsActionForm(request.POST)
            if form.is_valid():
                target_brand = form.cleaned_data["target_brand"]
                count = 0
                try:
                    with transaction.atomic():
                        for source_brand in queryset:
                            if source_brand == target_brand:
                                continue

                            # Перенос маппингов
                            for mapping in source_brand.onec_mappings.all():
                                if target_brand.onec_mappings.filter(
                                    onec_id=mapping.onec_id
                                ).exists():
                                    logger.warning(
                                        f"Duplicate mapping for brand {target_brand}: {mapping.onec_id}. Skipping transfer."
                                    )
                                    continue  # Mapping will be deleted with source_brand
                                mapping.brand = target_brand
                                mapping.save()

                            # Перенос продуктов
                            # У продуктов brand PROTECT, поэтому их НАДО перенести перед удалением бренда
                            source_brand.products.update(brand=target_brand)

                            source_brand.delete()
                            count += 1

                    self.message_user(
                        request,
                        f"Успешно объединено {count} брендов в {target_brand}",
                        messages.SUCCESS,
                    )
                    return HttpResponseRedirect(request.get_full_path())
                except Exception as e:
                    logger.error(f"Error merging brands: {e}")
                    self.message_user(request, f"Ошибка: {e}", messages.ERROR)
                    return HttpResponseRedirect(request.get_full_path())
        else:
            form = MergeBrandsActionForm()

        return render(
            request,
            "admin/products/brand/merge_action.html",
            context={
                "brands": queryset,
                "form": form,
                "title": "Объединение брендов",
                "opts": self.model._meta,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,  # type: ignore
            },
        )

    actions = ["merge_brands"]


@admin.register(Brand1CMapping)
class Brand1CMappingAdmin(admin.ModelAdmin):
    """Admin для модели Brand1CMapping"""

    list_display = ("brand", "onec_id", "onec_name", "created_at")
    list_filter = ("brand", "created_at")
    search_fields = ("onec_id", "onec_name", "brand__name")
    autocomplete_fields = ("brand",)
    readonly_fields = ("created_at",)

    @admin.action(description="Перенести на другой бренд")
    def transfer_to_brand(
        self, request: HttpRequest, queryset: QuerySet[Brand1CMapping]
    ) -> Any:
        """Действие для переноса маппингов на другой бренд"""
        if "apply" in request.POST:
            form = TransferMappingsActionForm(request.POST)
            if form.is_valid():
                target_brand = form.cleaned_data["target_brand"]
                try:
                    with transaction.atomic():
                        count = 0
                        for mapping in queryset:
                            if target_brand.onec_mappings.filter(
                                onec_id=mapping.onec_id
                            ).exists():
                                logger.warning(
                                    f"Mapping {mapping.onec_id} already exists in {target_brand}. Skipping."
                                )
                                continue
                            mapping.brand = target_brand
                            mapping.save()
                            count += 1
                    self.message_user(
                        request,
                        f"Перенесено {count} маппингов на {target_brand}",
                        messages.SUCCESS,
                    )
                    return HttpResponseRedirect(request.get_full_path())
                except Exception as e:
                    self.message_user(request, f"Ошибка: {e}", messages.ERROR)
                    return HttpResponseRedirect(request.get_full_path())
        else:
            form = TransferMappingsActionForm()

        return render(
            request,
            "admin/products/brand1cmapping/transfer_action.html",
            context={
                "mappings": queryset,
                "form": form,
                "title": "Перенос маппингов",
                "opts": self.model._meta,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,  # type: ignore
            },
        )

    actions = ["transfer_to_brand"]


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
        "brand",
        "category",
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
    search_fields = ("name", "onec_id", "parent_onec_id", "onec_brand_id")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "created_at",
        "updated_at",
        "last_sync_at",
        "sync_status",
        "error_message",
        "onec_brand_id",
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
            "Изображения (Hybrid подход - Story 13.1)",
            {
                "fields": ("base_images",),
                "description": "Общие изображения товара из 1С. Используются как fallback для вариантов.",
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
                    "onec_brand_id",
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


@admin.register(ColorMapping)
class ColorMappingAdmin(admin.ModelAdmin):
    """Admin для модели ColorMapping"""

    list_display = ("name", "hex_code", "swatch_image")
    search_fields = ("name", "hex_code")
    ordering = ("name",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """Admin для модели ProductVariant"""

    list_display = (
        "sku",
        "product",
        "color_name",
        "size_value",
        "retail_price",
        "stock_quantity",
        "is_active",
    )
    list_filter = ("is_active", "color_name", "size_value")
    search_fields = ("sku", "onec_id", "product__name")
    raw_id_fields = ("product",)
    readonly_fields = ("created_at", "updated_at", "last_sync_at")
    fieldsets = (
        (
            "Идентификация",
            {
                "fields": (
                    "product",
                    "sku",
                    "onec_id",
                )
            },
        ),
        (
            "Характеристики",
            {
                "fields": (
                    "color_name",
                    "size_value",
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
                )
            },
        ),
        (
            "Остатки",
            {
                "fields": (
                    "stock_quantity",
                    "reserved_quantity",
                )
            },
        ),
        (
            "Изображения (опционально)",
            {
                "fields": (
                    "main_image",
                    "gallery_images",
                ),
                "description": "Собственные изображения варианта. Если не заданы, используются Product.base_images.",
            },
        ),
        (
            "Статус и даты",
            {
                "fields": ("is_active", "last_sync_at", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[ProductVariant]:
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related("product")


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    """Admin для модели Attribute"""

    list_display = ("name", "slug", "onec_id", "type", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("name", "slug", "onec_id")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    """Admin для модели AttributeValue"""

    list_display = ("value", "attribute", "slug", "onec_id", "created_at")
    list_filter = ("attribute", "created_at")
    search_fields = ("value", "slug", "onec_id", "attribute__name")
    prepopulated_fields = {"slug": ("value",)}
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("attribute",)
    ordering = ("attribute", "value")
