"""
Модели продуктов для платформы FREESPORT
Включает товары, категории, бренды с роле-ориентированным ценообразованием
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from transliterate import translit

if TYPE_CHECKING:
    from apps.users.models import User


class Brand(models.Model):
    """
    Модель бренда товаров
    """

    name = cast(str, models.CharField("Название бренда", max_length=100, unique=True))
    slug = cast(str, models.SlugField("Slug", max_length=255, unique=True))
    logo = cast(
        models.ImageField, models.ImageField("Логотип", upload_to="brands/", blank=True)
    )
    description = cast(str, models.TextField("Описание", blank=True))
    website = cast(str, models.URLField("Веб-сайт", blank=True))
    is_active = cast(bool, models.BooleanField("Активный", default=True))

    # Интеграция с 1С
    onec_id = cast(
        str,
        models.CharField(
            "ID в 1С",
            max_length=100,
            unique=True,
            null=True,
            blank=True,
            db_index=True,
            help_text="Уникальный идентификатор бренда из 1С",
        ),
    )

    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )
    updated_at = cast(datetime, models.DateTimeField("Дата обновления", auto_now=True))

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"
        db_table = "brands"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            try:
                # Транслитерация кириллицы в латиницу, затем slugify
                transliterated = translit(self.name, "ru", reversed=True)
                self.slug = slugify(transliterated)
            except RuntimeError:
                # Fallback на обычный slugify
                self.slug = slugify(self.name)

            # Если slug все еще пустой, создаем fallback
            if not self.slug:
                self.slug = f"brand-{self.pk or 0}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)


class Category(models.Model):
    """
    Модель категорий товаров с поддержкой иерархии
    """

    name = cast(str, models.CharField("Название", max_length=200))
    slug = cast(str, models.SlugField("Slug", max_length=255, unique=True))
    parent = cast(
        "Category | None",
        models.ForeignKey(
            "self",
            on_delete=models.CASCADE,
            null=True,
            blank=True,
            related_name="children",
            verbose_name="Родительская категория",
        ),
    )
    description = cast(str, models.TextField("Описание", blank=True))
    image = cast(
        models.ImageField,
        models.ImageField("Изображение", upload_to="categories/", blank=True),
    )
    is_active = cast(bool, models.BooleanField("Активная", default=True))
    sort_order = cast(int, models.PositiveIntegerField("Порядок сортировки", default=0))

    # SEO поля
    seo_title = cast(str, models.CharField("SEO заголовок", max_length=200, blank=True))
    seo_description = cast(str, models.TextField("SEO описание", blank=True))

    # Интеграция с 1С
    onec_id = cast(
        str,
        models.CharField(
            "ID в 1С",
            max_length=100,
            unique=True,
            null=True,
            blank=True,
            db_index=True,
            help_text="Уникальный идентификатор категории из 1С",
        ),
    )

    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )
    updated_at = cast(datetime, models.DateTimeField("Дата обновления", auto_now=True))

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        db_table = "categories"
        ordering = ["sort_order", "name"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            try:
                # Транслитерация кириллицы в латиницу, затем slugify
                transliterated = translit(self.name, "ru", reversed=True)
                self.slug = slugify(transliterated)
            except RuntimeError:
                # Fallback на обычный slugify
                self.slug = slugify(self.name)

            # Если slug все еще пустой, создаем fallback
            if not self.slug:
                self.slug = f"category-{self.pk or 0}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        """Полное название категории с учетом иерархии"""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name


class Product(models.Model):
    """
    Модель товара с роле-ориентированным ценообразованием
    """

    name = cast(str, models.CharField("Название", max_length=300))
    slug = cast(str, models.SlugField("Slug", max_length=255, unique=True))
    brand = cast(
        Brand,
        models.ForeignKey(
            Brand,
            on_delete=models.CASCADE,
            related_name="products",
            verbose_name="Бренд",
        ),
    )
    category = cast(
        Category,
        models.ForeignKey(
            Category,
            on_delete=models.CASCADE,
            related_name="products",
            verbose_name="Категория",
        ),
    )
    description = cast(str, models.TextField("Описание"))
    short_description = cast(
        str, models.CharField("Краткое описание", max_length=500, blank=True)
    )
    specifications = cast(
        dict, models.JSONField("Технические характеристики", default=dict, blank=True)
    )

    # Ценообразование для различных ролей пользователей
    retail_price = cast(
        Decimal,
        models.DecimalField(
            "Розничная цена",
            max_digits=10,
            decimal_places=2,
            validators=[MinValueValidator(0)],
        ),
    )
    opt1_price = cast(
        Decimal | None,
        models.DecimalField(
            "Оптовая цена уровень 1",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            validators=[MinValueValidator(0)],
        ),
    )
    opt2_price = cast(
        Decimal | None,
        models.DecimalField(
            "Оптовая цена уровень 2",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            validators=[MinValueValidator(0)],
        ),
    )
    opt3_price = cast(
        Decimal | None,
        models.DecimalField(
            "Оптовая цена уровень 3",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            validators=[MinValueValidator(0)],
        ),
    )
    trainer_price = cast(
        Decimal | None,
        models.DecimalField(
            "Цена для тренера",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            validators=[MinValueValidator(0)],
        ),
    )
    federation_price = cast(
        Decimal | None,
        models.DecimalField(
            "Цена для представителя федерации",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            validators=[MinValueValidator(0)],
        ),
    )

    # Информационные цены для B2B пользователей
    recommended_retail_price = cast(
        Decimal | None,
        models.DecimalField(
            "Рекомендованная розничная цена (RRP)",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            validators=[MinValueValidator(0)],
        ),
    )
    max_suggested_retail_price = cast(
        Decimal | None,
        models.DecimalField(
            "Максимальная рекомендованная цена (MSRP)",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            validators=[MinValueValidator(0)],
        ),
    )

    # Инвентаризация
    sku = cast(
        str, models.CharField("Артикул", max_length=100, unique=True, blank=True)
    )
    stock_quantity = cast(
        int,
        models.PositiveIntegerField(
            "Количество на складе",
            default=0,
            help_text="Доступное количество на складе",
        ),
    )
    reserved_quantity = cast(
        int,
        models.PositiveIntegerField(
            "Зарезервированное количество",
            default=0,
            help_text="Количество товара, зарезервированного в корзинах и заказах",
        ),
    )
    min_order_quantity = cast(
        int, models.PositiveIntegerField("Минимальное количество заказа", default=1)
    )

    # Изображения
    main_image = cast(
        models.ImageField,
        models.ImageField("Основное изображение", upload_to="products/"),
    )
    gallery_images = cast(
        list, models.JSONField("Галерея изображений", default=list, blank=True)
    )

    # SEO и мета информация
    seo_title = cast(str, models.CharField("SEO заголовок", max_length=200, blank=True))
    seo_description = cast(str, models.TextField("SEO описание", blank=True))

    # Флаги
    is_active = cast(bool, models.BooleanField("Активный", default=True))
    is_featured = cast(bool, models.BooleanField("Рекомендуемый", default=False))

    # Временные метки и интеграция с 1С
    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )
    updated_at = cast(datetime, models.DateTimeField("Дата обновления", auto_now=True))

    # 1С Integration fields (Story 3.1.1 AC: 3)
    class SyncStatus(models.TextChoices):
        PENDING = "pending", "Ожидает синхронизации"
        IN_PROGRESS = "in_progress", "Синхронизация"
        COMPLETED = "completed", "Синхронизировано"
        FAILED = "failed", "Ошибка"

    onec_id = cast(
        str | None,
        models.CharField(
            "ID товара в 1С (SKU)",
            max_length=100,
            unique=True,
            blank=True,
            null=True,
            db_index=True,
            help_text="Составной ID из offers.xml: parent_id#sku_id",
        ),
    )
    parent_onec_id = cast(
        str | None,
        models.CharField(
            "ID родительского товара в 1С",
            max_length=100,
            blank=True,
            null=True,
            db_index=True,
            help_text="ID базового товара из goods.xml",
        ),
    )
    sync_status = cast(
        str,
        models.CharField(
            "Статус синхронизации",
            max_length=20,
            choices=SyncStatus.choices,
            default=SyncStatus.PENDING,
            db_index=True,
        ),
    )
    last_sync_at = cast(
        datetime | None,
        models.DateTimeField("Последняя синхронизация", null=True, blank=True),
    )
    error_message = cast(str, models.TextField("Сообщение об ошибке", blank=True))

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["brand", "is_active"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["stock_quantity"]),
            models.Index(fields=["onec_id"]),  # 1С integration index
            models.Index(fields=["parent_onec_id"]),  # Parent 1C ID index
            models.Index(fields=["sync_status"]),  # Sync status index
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            try:
                # Транслитерация кириллицы в латиницу, затем slugify
                transliterated = translit(self.name, "ru", reversed=True)
                self.slug = slugify(transliterated)
            except RuntimeError:
                # Fallback на обычный slugify
                self.slug = slugify(self.name)

            # Если slug все еще пустой, создаем fallback
            if not self.slug:
                self.slug = f"product-{self.pk or 0}"

        if not self.sku:
            self.sku = f"AUTO-{int(time.time())}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"

    def get_price_for_user(self, user: User | None) -> Decimal:
        """Получить цену товара для конкретного пользователя на основе его роли"""
        if not user or not user.is_authenticated:
            return self.retail_price

        role_price_mapping = {
            "retail": self.retail_price,
            "wholesale_level1": self.opt1_price or self.retail_price,
            "wholesale_level2": self.opt2_price or self.retail_price,
            "wholesale_level3": self.opt3_price or self.retail_price,
            "trainer": self.trainer_price or self.retail_price,
            "federation_rep": self.federation_price or self.retail_price,
        }

        return role_price_mapping.get(user.role, self.retail_price)

    @property
    def is_in_stock(self) -> bool:
        """Проверка наличия товара на складе"""
        return self.stock_quantity > 0

    @property
    def can_be_ordered(self) -> bool:
        """Можно ли заказать товар"""
        available_quantity = self.stock_quantity - self.reserved_quantity
        return (
            self.is_active
            and self.is_in_stock
            and available_quantity >= self.min_order_quantity
        )

    @property
    def available_quantity(self) -> int:
        """Доступное количество товара (с учетом резерва)"""
        return max(0, self.stock_quantity - self.reserved_quantity)


class ProductImage(models.Model):
    """
    Модель изображений товара
    """

    product = cast(
        Product,
        models.ForeignKey(
            Product,
            on_delete=models.CASCADE,
            related_name="images",
            verbose_name="Товар",
        ),
    )
    objects = models.Manager()
    image = cast(
        models.ImageField,
        models.ImageField("Изображение", upload_to="products/gallery/"),
    )
    alt_text = cast(
        str, models.CharField("Альтернативный текст", max_length=255, blank=True)
    )
    is_main = cast(bool, models.BooleanField("Основное изображение", default=False))
    sort_order = cast(int, models.PositiveIntegerField("Порядок сортировки", default=0))

    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )
    updated_at = cast(datetime, models.DateTimeField("Дата обновления", auto_now=True))

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        db_table = "product_images"
        ordering = ["sort_order", "created_at"]
        indexes = [
            models.Index(fields=["product", "is_main"]),
            models.Index(fields=["sort_order"]),
        ]

    def __str__(self) -> str:
        image_type = "основное" if self.is_main else "дополнительное"
        return f"Изображение {self.product.name} ({image_type})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Если это основное изображение, убираем флаг у других изображений этого товара
        if self.is_main:
            ProductImage.objects.filter(product=self.product, is_main=True).exclude(
                pk=self.pk
            ).update(is_main=False)
        super().save(*args, **kwargs)


class ImportSession(models.Model):
    """
    Модель для отслеживания сессий импорта данных из 1С
    """

    class ImportType(models.TextChoices):
        CATALOG = "catalog", "Каталог товаров"
        STOCKS = "stocks", "Остатки товаров"
        PRICES = "prices", "Цены товаров"
        CUSTOMERS = "customers", "Клиенты"

    class ImportStatus(models.TextChoices):
        STARTED = "started", "Начато"
        IN_PROGRESS = "in_progress", "В процессе"
        COMPLETED = "completed", "Завершено"
        FAILED = "failed", "Ошибка"

    import_type = cast(
        str,
        models.CharField(
            "Тип импорта",
            max_length=20,
            choices=ImportType.choices,
            default=ImportType.CATALOG,
        ),
    )
    status = cast(
        str,
        models.CharField(
            "Статус",
            max_length=20,
            choices=ImportStatus.choices,
            default=ImportStatus.STARTED,
        ),
    )
    started_at = cast(
        datetime, models.DateTimeField("Начало импорта", auto_now_add=True)
    )
    finished_at = cast(
        datetime | None,
        models.DateTimeField("Окончание импорта", null=True, blank=True),
    )
    report_details = cast(
        dict,
        models.JSONField(
            "Детали отчета",
            default=dict,
            blank=True,
            help_text="Статистика: created, updated, skipped, errors",
        ),
    )
    error_message = cast(str, models.TextField("Сообщение об ошибке", blank=True))

    class Meta:
        verbose_name = "Сессия импорта"
        verbose_name_plural = "Сессии импорта"
        db_table = "import_sessions"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["import_type", "status"]),
            models.Index(fields=["-started_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_import_type_display()} - "
            f"{self.get_status_display()} ({self.started_at})"
        )
