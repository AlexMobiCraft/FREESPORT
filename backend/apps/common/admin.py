"""
Django Admin конфигурация для моделей приложения common
"""
import csv

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from .models import AuditLog, CustomerSyncLog, SyncConflict, SyncLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin конфигурация для AuditLog"""

    list_display = ["timestamp", "user", "action", "resource_type", "resource_id"]
    list_filter = ["action", "resource_type", "timestamp"]
    search_fields = ["user__email", "resource_id", "ip_address"]
    readonly_fields = ["timestamp"]
    date_hierarchy = "timestamp"


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """Admin конфигурация для SyncLog"""

    list_display = [
        "started_at",
        "sync_type",
        "status",
        "records_processed",
        "errors_count",
    ]
    list_filter = ["sync_type", "status", "started_at"]
    readonly_fields = ["started_at", "completed_at"]
    date_hierarchy = "started_at"


@admin.register(CustomerSyncLog)
class CustomerSyncLogAdmin(admin.ModelAdmin):
    """
    Расширенный интерфейс Django Admin для просмотра и управления
    логами синхронизации клиентов
    """

    list_display = [
        "created_at",
        "operation_type",
        "status",
        "customer_email",
        "onec_id",
        "duration_ms",
        "correlation_id_short",
    ]

    list_filter = [
        "operation_type",
        "status",
        ("created_at", admin.DateFieldListFilter),
        "customer__role",
    ]

    search_fields = [
        "customer_email",
        "onec_id",
        "correlation_id",
        "error_message",
        "customer__email",
        "customer__first_name",
        "customer__last_name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "correlation_id",
        "duration_ms",
        "session",
    ]

    date_hierarchy = "created_at"

    actions = ["export_to_csv", "mark_as_reviewed"]

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "operation_type",
                    "status",
                    "customer",
                    "customer_email",
                    "onec_id",
                )
            },
        ),
        (
            "Детали операции",
            {
                "fields": ("details", "error_message", "duration_ms", "correlation_id"),
                "classes": ("collapse",),
            },
        ),
        (
            "Служебные поля",
            {
                "fields": ("session", "user"),
                "classes": ("collapse",),
            },
        ),
        (
            "Временные метки",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    list_per_page = 50

    def correlation_id_short(self, obj: CustomerSyncLog) -> str:
        """Короткая версия correlation_id для списка"""
        if obj.correlation_id:
            return obj.correlation_id[:8] + "..."
        return "-"

    correlation_id_short.short_description = "Correlation ID"  # type: ignore

    @admin.action(description="Экспортировать выбранные логи в CSV")
    def export_to_csv(
        self, request: HttpRequest, queryset: QuerySet[CustomerSyncLog]
    ) -> HttpResponse:
        """Экспорт выбранных логов в CSV файл"""
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="sync_logs.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Дата",
                "Операция",
                "Статус",
                "Email",
                "ID в 1С",
                "Длительность (мс)",
                "Ошибка",
                "Correlation ID",
            ]
        )

        for log in queryset:
            writer.writerow(
                [
                    log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    log.get_operation_type_display(),
                    log.get_status_display(),
                    log.customer_email,
                    log.onec_id,
                    log.duration_ms or "",
                    log.error_message[:100] if log.error_message else "",
                    log.correlation_id,
                ]
            )

        return response

    @admin.action(description="Отметить как просмотренные")
    def mark_as_reviewed(
        self, request: HttpRequest, queryset: QuerySet[CustomerSyncLog]
    ) -> None:
        """Пометка логов как просмотренных (добавляет метку в details)"""
        count = 0
        user_email = getattr(request.user, "email", "unknown")
        
        for log in queryset:
            if not log.details:
                log.details = {}
            log.details["reviewed"] = True
            log.details["reviewed_by"] = user_email
            log.details["reviewed_at"] = timezone.now().isoformat()
            log.save()
            count += 1

        self.message_user(
            request, f"Отмечено как просмотренные: {count} лог(ов)", level="success"
        )


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    """Admin конфигурация для SyncConflict"""

    list_display = [
        "created_at",
        "conflict_type",
        "customer",
        "resolution_strategy",
        "is_resolved",
    ]
    list_filter = [
        "conflict_type",
        "resolution_strategy",
        "is_resolved",
        "created_at",
    ]
    search_fields = ["customer__email", "customer__first_name", "customer__last_name"]
    readonly_fields = ["created_at", "resolved_at"]
    date_hierarchy = "created_at"
