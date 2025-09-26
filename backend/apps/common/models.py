"""
Общие модели для платформы FREESPORT
Включает аудиторский журнал и логи синхронизации с 1С
"""
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class AuditLog(models.Model):
    """
    Аудиторский журнал для соответствия требованиям B2B
    Логирует все важные действия пользователей в системе
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        verbose_name="Пользователь",
    )
    action = models.CharField(
        "Действие",
        max_length=100,
        help_text="Тип выполненного действия (create, update, delete, login, etc.)",
    )
    resource_type = models.CharField(
        "Тип ресурса",
        max_length=50,
        help_text="Тип объекта над которым выполнено действие (User, Product, Order, etc.)",
    )
    resource_id = models.CharField(
        "ID ресурса", max_length=100, help_text="Идентификатор объекта"
    )
    changes = models.JSONField(
        "Изменения", default=dict, help_text="JSON с деталями изменений"
    )
    ip_address = models.GenericIPAddressField(
        "IP адрес", help_text="IP адрес пользователя"
    )
    user_agent = models.TextField(
        "User Agent", help_text="Браузер и устройство пользователя"
    )
    timestamp = models.DateTimeField("Время действия", auto_now_add=True)

    class Meta:
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
        user_display = self.user.email if self.user else "Anonymous"
        return f"{user_display} - {self.action} {self.resource_type}#{self.resource_id}"

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

    sync_type = models.CharField("Тип синхронизации", max_length=50, choices=SYNC_TYPES)
    status = models.CharField("Статус", max_length=20, choices=SYNC_STATUSES)
    records_processed = models.PositiveIntegerField("Обработано записей", default=0)
    errors_count = models.PositiveIntegerField("Количество ошибок", default=0)
    error_details = models.JSONField(
        "Детали ошибок",
        default=list,
        blank=True,
        help_text="Список ошибок, возникших при синхронизации",
    )
    started_at = models.DateTimeField("Время начала", auto_now_add=True)
    completed_at = models.DateTimeField("Время завершения", null=True, blank=True)

    class Meta:
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
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка в SyncLog.__str__(): {e}")
            logger.error(
                f"SyncLog pk: {getattr(self, 'pk', 'unknown')}, sync_type: {getattr(self, 'sync_type', 'unknown')}, status: {getattr(self, 'status', 'unknown')}"
            )
            logger.error(f"Тип объекта: {type(self)}")
            logger.error(f"Модуль: {getattr(self, '__module__', 'unknown')}")
            # Fallback к базовому отображению
            return f"SyncLog(pk={getattr(self, 'pk', 'unknown')}, sync_type={getattr(self, 'sync_type', 'unknown')}, status={getattr(self, 'status', 'unknown')})"

    def mark_completed(self, records_processed=0, errors_count=0, error_details=None):
        """
        Отметить синхронизацию как завершенную

        Args:
            records_processed: Количество обработанных записей
            errors_count: Количество ошибок
            error_details: Список деталей ошибок
        """
        from django.utils import timezone

        self.status = "completed"
        self.records_processed = records_processed
        self.errors_count = errors_count
        self.error_details = error_details or []
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, error_details=None):
        """
        Отметить синхронизацию как неудачную

        Args:
            error_details: Список деталей ошибок
        """
        from django.utils import timezone

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
