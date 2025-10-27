"""
Общие модели для платформы FREESPORT
Включает аудиторский журнал и логи синхронизации с 1С
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.products.models import ImportSession

User = get_user_model()


class AuditLog(models.Model):
    """
    Аудиторский журнал для соответствия требованиям B2B
    Логирует все важные действия пользователей в системе
    """

    user: models.ForeignKey = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        verbose_name="Пользователь",
    )
    action: models.CharField = models.CharField(
        "Действие",
        max_length=100,
        help_text="Тип выполненного действия (create, update, delete, login, etc.)",
    )
    resource_type: models.CharField = models.CharField(
        "Тип ресурса",
        max_length=50,
        help_text=(
            "Тип объекта над которым выполнено действие (User, Product, Order, " "etc.)"
        ),
    )
    resource_id: models.CharField = models.CharField(
        "ID ресурса", max_length=100, help_text="Идентификатор объекта"
    )
    changes: models.JSONField = models.JSONField(
        "Изменения", default=dict, help_text="JSON с деталями изменений"
    )
    ip_address: models.GenericIPAddressField = models.GenericIPAddressField(
        "IP адрес", help_text="IP адрес пользователя"
    )
    user_agent: models.TextField = models.TextField(
        "User Agent", help_text="Браузер и устройство пользователя"
    )
    timestamp: models.DateTimeField = models.DateTimeField(
        "Время действия", auto_now_add=True
    )

    objects = models.Manager()

    class Meta:
        """Мета-опции для модели AuditLog."""

        verbose_name = "Запись аудита"
        verbose_name_plural = "Аудиторский журнал"
        db_table = "audit_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        user_display = (
            getattr(self.user, "email", "Anonymous") if self.user else "Anonymous"
        )
        return (
            f"{user_display} - {self.action} "
            f"{self.resource_type}#{self.resource_id}"
        )

    @classmethod
    def log_action(
        cls,
        user,
        action,
        resource_type,
        resource_id,
        changes=None,
        ip_address=None,
        user_agent=None,
    ):
        """
        Удобный метод для создания записи аудита

        Args:
            user: Пользователь, выполняющий действие
            action: Тип действия (create, update, delete, etc.)
            resource_type: Тип ресурса (User, Product, etc.)
            resource_id: ID ресурса
            changes: Словарь с изменениями
            ip_address: IP адрес пользователя
            user_agent: User Agent строка
        """
        return cls.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            changes=changes or {},
            ip_address=ip_address or "0.0.0.0",
            user_agent=user_agent or "",
        )


class SyncLog(models.Model):
    """
    Журнал синхронизации с 1С
    Отслеживает состояние синхронизации товаров, остатков и заказов
    """

    SYNC_TYPES = [
        ("products", "Товары"),
        ("stocks", "Остатки"),
        ("orders", "Заказы"),
        ("prices", "Цены"),
    ]

    SYNC_STATUSES = [
        ("started", "Начата"),
        ("completed", "Завершена"),
        ("failed", "Ошибка"),
    ]

    sync_type: models.CharField = models.CharField(
        "Тип синхронизации", max_length=50, choices=SYNC_TYPES
    )
    status: models.CharField = models.CharField(
        "Статус", max_length=20, choices=SYNC_STATUSES
    )
    records_processed: models.PositiveIntegerField = models.PositiveIntegerField(
        "Обработано записей", default=0
    )
    errors_count: models.PositiveIntegerField = models.PositiveIntegerField(
        "Количество ошибок", default=0
    )
    error_details: models.JSONField = models.JSONField(
        "Детали ошибок",
        default=list,
        blank=True,
        help_text="Список ошибок, возникших при синхронизации",
    )
    started_at: models.DateTimeField = models.DateTimeField(
        "Время начала", auto_now_add=True
    )
    completed_at: models.DateTimeField = models.DateTimeField(
        "Время завершения", null=True, blank=True
    )

    class Meta:
        """Мета-опции для модели SyncLog."""

        verbose_name = "Лог синхронизации"
        verbose_name_plural = "Логи синхронизации"
        db_table = "sync_logs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["sync_type", "status"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self):
        try:
            # Используем getattr для безопасного доступа к методам
            sync_type_display = getattr(
                self, "get_sync_type_display", lambda: self.sync_type
            )()
            status_display = getattr(self, "get_status_display", lambda: self.status)()
            return f"{sync_type_display} - {status_display} ({self.started_at})"
        except AttributeError as e:
            logger = logging.getLogger(__name__)
            logger.error("Ошибка в SyncLog.__str__(): %s", e)
            logger.error(
                "SyncLog pk: %s, sync_type: %s, status: %s",
                getattr(self, "pk", "unknown"),
                getattr(self, "sync_type", "unknown"),
                getattr(self, "status", "unknown"),
            )
            logger.error("Тип объекта: %s", type(self))
            logger.error("Модуль: %s", getattr(self, "__module__", "unknown"))
            # Fallback к базовому отображению
            return (
                f"SyncLog(pk={getattr(self, 'pk', 'unknown')}, "
                f"sync_type={getattr(self, 'sync_type', 'unknown')}, "
                f"status={getattr(self, 'status', 'unknown')})"
            )

    def mark_completed(self, records_processed=0, errors_count=0, error_details=None):
        """
        Отметить синхронизацию как завершенную

        Args:
            records_processed: Количество обработанных записей
            errors_count: Количество ошибок
            error_details: Список деталей ошибок
        """

        self.status = "completed"
        self.records_processed = records_processed
        self.errors_count = errors_count
        self.error_details = error_details or []
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, error_details=None):
        """
        Отметить синхронезацию как неудачную

        Args:
            error_details: Список деталей ошибок
        """

        self.status = "failed"
        self.error_details = error_details or []
        self.errors_count = len(self.error_details)
        self.completed_at = timezone.now()
        self.save()

    @property
    def duration(self):
        """Продолжительность синхронизации"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def success_rate(self):
        """Процент успешности синхронизации"""
        if self.records_processed == 0:
            return 0
        return (
            (self.records_processed - self.errors_count) / self.records_processed
        ) * 100


class CustomerSyncLog(models.Model):
    """
    Детальное логирование операций импорта клиентов из 1С
    Связан с ImportSession для двухуровневого логирования
    """

    class OperationType(models.TextChoices):
        CREATED = "created", "Создан"
        UPDATED = "updated", "Обновлен"
        SKIPPED = "skipped", "Пропущен"
        ERROR = "error", "Ошибка"

    class StatusType(models.TextChoices):
        SUCCESS = "success", "Успешно"
        FAILED = "failed", "Ошибка"
        WARNING = "warning", "Предупреждение"

    session = models.ForeignKey(
        "products.ImportSession",
        on_delete=models.CASCADE,
        related_name="customer_logs",
        verbose_name="Сессия импорта",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Пользователь",
    )
    onec_id = models.CharField("ID в 1С", max_length=100)
    operation_type = models.CharField(
        "Тип операции", max_length=20, choices=OperationType.choices
    )
    status = models.CharField("Статус", max_length=20, choices=StatusType.choices)
    error_message = models.TextField("Сообщение об ошибке", blank=True)
    details = models.JSONField(
        "Детали операции",
        default=dict,
        blank=True,
        help_text="Дополнительная информация: старые/новые значения, причина пропуска",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Лог синхронизации клиента"
        verbose_name_plural = "Логи синхронизации клиентов"
        db_table = "customer_sync_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "operation_type"]),
            models.Index(fields=["onec_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.operation_type} - {self.onec_id} ({self.status})"
