"""
Django Admin для приложения products
"""
from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Brand, Category, ImportSession, Product


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
        "onec_id",
    )
    list_filter = ("is_active", "brand", "category", "sync_status", "created_at")
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
                    "weight",
                    "dimensions",
                )
            },
        ),
        (
            "Медиа и изображения",
            {
                "fields": ("main_image", "images"),
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
            "Статус и даты",
            {
                "fields": ("is_active", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Product]:
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related("brand", "category")


@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    """Admin для модели ImportSession"""

    list_display = (
        "id",
        "import_type",
        "status",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "import_type", "started_at")
    search_fields = ("id", "error_message")
    readonly_fields = (
        "id",
        "started_at",
        "finished_at",
        "report_details",
    )
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": ("id", "import_type", "status"),
            },
        ),
        (
            "Детали",
            {
                "fields": (
                    "report_details",
                    "error_message",
                ),
            },
        ),
        (
            "Временные метки",
            {
                "fields": ("started_at", "finished_at"),
            },
        ),
    )
