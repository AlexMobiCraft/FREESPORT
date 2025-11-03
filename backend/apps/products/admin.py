"""
Django Admin для приложения products
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib import admin
from django.core.management import call_command
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django_redis import get_redis_connection

from .models import Brand, Category, ImportSession, Product, ProductImage


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
    """Admin для модели ImportSession с мониторингом и запуском импорта"""

    list_display = (
        "id",
        "import_type",
        "colored_status",
        "started_at",
        "duration",
        "progress_display",
    )
    list_filter = ("status", "import_type", "started_at")
    search_fields = ("id", "error_message")
    readonly_fields = (
        "id",
        "started_at",
        "finished_at",
        "report_details",
    )
    actions = ["trigger_catalog_import"]
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

    @admin.action(description="🚀 Запустить импорт каталога из 1С")
    def trigger_catalog_import(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Запуск импорта каталога из 1С с защитой от concurrent runs.

        Использует distributed lock через Redis для предотвращения
        одновременного запуска нескольких импортов.
        """
        redis_conn = get_redis_connection("default")
        lock_key = "import_catalog_lock"
        lock = redis_conn.lock(lock_key, timeout=3600)  # 1 час TTL

        # Пытаемся захватить блокировку (non-blocking)
        if not lock.acquire(blocking=False):
            self.message_user(
                request,
                "⚠️ Импорт уже запущен! Дождитесь завершения текущего импорта.",
                level="WARNING",
            )
            return

        try:
            # Проверяем наличие настройки ONEC_DATA_DIR
            data_dir = getattr(settings, "ONEC_DATA_DIR", None)
            if not data_dir:
                raise ValueError(
                    "Настройка ONEC_DATA_DIR не найдена в settings. "
                    "Убедитесь, что путь к данным 1С настроен."
                )

            # Запускаем management command синхронно
            call_command("import_catalog_from_1c", "--data-dir", str(data_dir))

            self.message_user(
                request,
                "✅ Импорт каталога завершен успешно!",
                level="SUCCESS",
            )
        except Exception as e:
            self.message_user(
                request,
                f"❌ Ошибка при импорте каталога: {e}",
                level="ERROR",
            )
        finally:
            # Всегда освобождаем lock, даже при ошибке
            lock.release()

    @admin.display(description="Статус")
    def colored_status(self, obj: ImportSession) -> str:
        """
        Отображение статуса с цветовой индикацией и иконками.

        - 🟢 Зеленый: completed
        - 🟡 Желтый: in_progress
        - 🔴 Красный: failed
        - ⚪ Серый: started
        """
        colors = {
            "completed": "green",
            "in_progress": "orange",
            "failed": "red",
            "started": "gray",
        }
        icons = {
            "completed": "✅",
            "in_progress": "⏳",
            "failed": "❌",
            "started": "⏸️",
        }
        color = colors.get(obj.status, "black")
        icon = icons.get(obj.status, "❓")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display(),
        )

    @admin.display(description="Длительность")
    def duration(self, obj: ImportSession) -> str:
        """
        Расчет длительности импорта.

        Показывает время в минутах если импорт завершен,
        или "В процессе..." если еще выполняется.
        """
        if obj.finished_at and obj.started_at:
            delta = obj.finished_at - obj.started_at
            minutes = delta.total_seconds() / 60
            if minutes < 1:
                seconds = delta.total_seconds()
                return f"{seconds:.0f} сек"
            return f"{minutes:.1f} мин"
        elif obj.started_at:
            return "В процессе..."
        return "-"

    @admin.display(description="Прогресс")
    def progress_display(self, obj: ImportSession) -> str:
        """
        Отображение прогресс-бара для импортов в процессе выполнения.

        Показывает HTML5 progress bar с процентами, если:
        - Статус: in_progress
        - Есть данные о total_items в report_details
        """
        if obj.status == "in_progress" and obj.report_details:
            total = obj.report_details.get("total_items", 0)
            processed = obj.report_details.get("processed_items", 0)

            if total > 0:
                progress = (processed / total) * 100
                progress_percent = f"{progress:.0f}"
                return format_html(
                    '<progress value="{}" max="100" style="width: 150px; height: 20px;"></progress> '
                    '<span style="font-weight: bold;">{}%</span> ({}/{})',
                    progress,
                    progress_percent,
                    processed,
                    total,
                )
        return "-"
