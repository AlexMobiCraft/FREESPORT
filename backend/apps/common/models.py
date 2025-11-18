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
    Детальное логирование всех операций синхронизации клиентов.
    Используется для аудита, мониторинга и отчетности интеграции с 1С.
    """

    class OperationType(models.TextChoices):
        # Основные операции
        IMPORT_FROM_1C = "import_from_1c", "Импорт из 1С"
        EXPORT_TO_1C = "export_to_1c", "Экспорт в 1С"
        SYNC_CHANGES = "sync_changes", "Синхронизация изменений"

        # Служебные операции
        CUSTOMER_IDENTIFICATION = "customer_identification", "Идентификация клиента"
        CONFLICT_RESOLUTION = "conflict_resolution", "Разрешение конфликтов"
        DATA_VALIDATION = "data_validation", "Валидация данных"
        BATCH_OPERATION = "batch_operation", "Пакетная операция"

        # Legacy операции (для обратной совместимости)
        CREATED = "created", "Создан"
        UPDATED = "updated", "Обновлен"
        SKIPPED = "skipped", "Пропущен"
        ERROR = "error", "Ошибка"
        IDENTIFY_CUSTOMER = "identify_customer", "Идентификация клиента"
        NOTIFICATION_FAILED = "notification_failed", "Ошибка отправки уведомления"

    class StatusType(models.TextChoices):
        SUCCESS = "success", "Успешно"
        ERROR = "error", "Ошибка"
        WARNING = "warning", "Предупреждение"
        SKIPPED = "skipped", "Пропущено"
        PENDING = "pending", "В процессе"

        # Legacy статусы (для обратной совместимости)
        FAILED = "failed", "Ошибка"
        NOT_FOUND = "not_found", "Не найден"

    # Основные поля
    operation_type = models.CharField(
        "Тип операции", max_length=30, choices=OperationType.choices, db_index=True
    )
    status = models.CharField(
        "Статус", max_length=20, choices=StatusType.choices, db_index=True
    )

    # Связь с клиентом (может быть null если клиент не найден)
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sync_logs",
        verbose_name="Клиент",
    )
    customer_email = models.EmailField("Email клиента", blank=True, db_index=True)
    onec_id = models.CharField("ID в 1С", max_length=100, blank=True, db_index=True)

    # Детальная информация
    details = models.JSONField(
        "Детали операции",
        default=dict,
        help_text="Структурированные данные операции",
    )
    error_message = models.TextField("Сообщение об ошибке", blank=True)

    # Метаданные
    duration_ms = models.PositiveIntegerField(
        "Длительность (мс)",
        null=True,
        blank=True,
        help_text="Длительность операции в миллисекундах",
    )
    correlation_id = models.CharField(
        "Correlation ID",
        max_length=50,
        blank=True,
        db_index=True,
        help_text="ID для отслеживания связанных операций",
    )

    # Legacy поля (для обратной совместимости)
    session = models.ForeignKey(
        "products.ImportSession",
        on_delete=models.CASCADE,
        related_name="customer_logs",
        verbose_name="Сессия импорта",
        null=True,
        blank=True,
        help_text="Сессия импорта (опционально)",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Пользователь (legacy)",
        related_name="legacy_sync_logs",
        help_text="Legacy поле, используйте customer вместо этого",
    )

    # Временные метки
    created_at = models.DateTimeField("Дата операции", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Лог синхронизации клиентов"
        verbose_name_plural = "Логи синхронизации клиентов"
        db_table = "customer_sync_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["operation_type", "status", "created_at"]),
            models.Index(fields=["customer_email"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        operation = self.get_operation_type_display()
        identifier = self.onec_id or self.customer_email
        status = self.get_status_display()
        return f"{operation} - {identifier} ({status})"


class SyncConflict(models.Model):
    """
    Модель для хранения конфликтов синхронизации между порталом и 1С.
    Архивирует старые и новые данные для возможности отката изменений.
    """

    CONFLICT_TYPE_CHOICES = [
        ("portal_registration_blocked", "Регистрация на портале заблокирована"),
        ("customer_data", "Конфликт данных клиента"),
        ("order_data", "Конфликт данных заказа"),
        ("product_data", "Конфликт данных товара"),
    ]

    RESOLUTION_STRATEGY_CHOICES = [
        ("onec_wins", "1С имеет приоритет"),
        ("portal_wins", "Портал имеет приоритет"),
        ("manual", "Ручное разрешение"),
    ]

    conflict_type = models.CharField(
        "Тип конфликта",
        max_length=50,
        choices=CONFLICT_TYPE_CHOICES,
        help_text="Тип конфликта синхронизации",
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sync_conflicts",
        verbose_name="Клиент",
        help_text="Клиент, для которого возник конфликт",
    )
    platform_data = models.JSONField(
        "Данные портала",
        default=dict,
        help_text="Архив данных из портала до разрешения конфликта",
    )
    onec_data = models.JSONField(
        "Данные 1С",
        default=dict,
        help_text="Данные из 1С, вызвавшие конфликт",
    )
    conflicting_fields = models.JSONField(
        "Конфликтующие поля",
        default=list,
        help_text="Список полей с различиями",
    )
    resolution_strategy = models.CharField(
        "Стратегия разрешения",
        max_length=20,
        choices=RESOLUTION_STRATEGY_CHOICES,
        default="onec_wins",
        help_text="Стратегия разрешения конфликта",
    )
    is_resolved = models.BooleanField(
        "Разрешен",
        default=False,
        help_text="Флаг разрешения конфликта",
    )
    resolution_details = models.JSONField(
        "Детали разрешения",
        default=dict,
        blank=True,
        help_text="Детали примененных изменений и источник конфликта",
    )
    resolved_at = models.DateTimeField(
        "Дата разрешения",
        null=True,
        blank=True,
        help_text="Дата и время разрешения конфликта",
    )
    resolved_by = models.CharField(
        "Разрешено",
        max_length=100,
        blank=True,
        help_text="Кем разрешен конфликт (система или пользователь)",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Конфликт синхронизации"
        verbose_name_plural = "Конфликты синхронизации"
        db_table = "sync_conflicts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "conflict_type"]),
            models.Index(fields=["is_resolved", "created_at"]),
            models.Index(fields=["conflict_type", "created_at"]),
        ]

    def __str__(self) -> str:
        status = "Разрешен" if self.is_resolved else "Не разрешен"
        return (
            f"{self.get_conflict_type_display()} - " f"{self.customer.email} ({status})"
        )


class Newsletter(models.Model):
    """
    Модель подписки на email-рассылку.
    Хранит email адреса подписчиков с временными метками.
    """

    email: models.EmailField = models.EmailField(
        "Email адрес",
        unique=True,
        max_length=255,
        db_index=True,
        help_text="Уникальный email адрес подписчика",
    )
    is_active: models.BooleanField = models.BooleanField(
        "Активна",
        default=True,
        db_index=True,
        help_text="Флаг активности подписки (для отписки)",
    )
    subscribed_at: models.DateTimeField = models.DateTimeField(
        "Дата подписки",
        auto_now_add=True,
        db_index=True,
        help_text="Дата и время подписки",
    )
    unsubscribed_at: models.DateTimeField = models.DateTimeField(
        "Дата отписки",
        null=True,
        blank=True,
        help_text="Дата и время отписки (null если активна)",
    )
    ip_address: models.GenericIPAddressField = models.GenericIPAddressField(
        "IP адрес",
        null=True,
        blank=True,
        help_text="IP адрес при подписке (для антиспам)",
    )
    user_agent: models.TextField = models.TextField(
        "User Agent",
        blank=True,
        help_text="Браузер и устройство при подписке",
    )

    objects = models.Manager()

    class Meta:
        verbose_name = "Подписка на рассылку"
        verbose_name_plural = "Подписки на рассылку"
        db_table = "newsletter_subscriptions"
        ordering = ["-subscribed_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "subscribed_at"]),
            models.Index(fields=["subscribed_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_active=True, unsubscribed_at__isnull=True)
                | models.Q(is_active=False, unsubscribed_at__isnull=False),
                name="newsletter_active_consistency",
            )
        ]

    def __str__(self) -> str:
        status = "Активна" if self.is_active else "Неактивна"
        return f"{self.email} ({status})"

    def unsubscribe(self) -> None:
        """Отписать email от рассылки."""
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=["is_active", "unsubscribed_at"])


class News(models.Model):
    """
    Модель новостей и акций.
    Отображаются на главной странице и в блоге компании.
    """

    title: models.CharField = models.CharField(
        "Заголовок",
        max_length=200,
        help_text="Заголовок новости",
    )
    slug: models.SlugField = models.SlugField(
        "URL slug",
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Уникальный идентификатор для URL",
    )
    excerpt: models.TextField = models.TextField(
        "Краткое описание",
        max_length=500,
        help_text="Краткое описание для главной страницы (до 500 символов)",
    )
    content: models.TextField = models.TextField(
        "Полный текст",
        blank=True,
        help_text="Полный текст новости (опционально)",
    )
    image: models.ImageField = models.ImageField(
        "Изображение",
        upload_to="news/%Y/%m/",
        null=True,
        blank=True,
        help_text="Изображение новости (опционально)",
    )
    author: models.CharField = models.CharField(
        "Автор",
        max_length=100,
        blank=True,
        help_text="Имя автора (опционально)",
    )
    category: models.CharField = models.CharField(
        "Категория",
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Категория новости (акция, новинка, событие)",
    )
    is_published: models.BooleanField = models.BooleanField(
        "Опубликована",
        default=False,
        db_index=True,
        help_text="Флаг публикации (только опубликованные видны на сайте)",
    )
    published_at: models.DateTimeField = models.DateTimeField(
        "Дата публикации",
        db_index=True,
        help_text="Дата и время публикации",
    )
    created_at: models.DateTimeField = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        "Дата обновления",
        auto_now=True,
    )

    objects = models.Manager()

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        db_table = "news"
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["is_published", "published_at"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["category", "published_at"]),
            models.Index(fields=["published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        """Автоматическая генерация slug из заголовка."""
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)
