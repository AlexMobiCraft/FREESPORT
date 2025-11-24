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

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from transliterate import translit

from apps.products.utils.brands import normalize_brand_name

if TYPE_CHECKING:
    from apps.users.models import User


class Brand(models.Model):
    """
    Модель бренда товаров
    """

    name = cast(str, models.CharField("Название бренда", max_length=100, unique=False))
    slug = cast(str, models.SlugField("Slug", max_length=255, unique=False))
    normalized_name = cast(
        str,
        models.CharField(
            "Нормализованное название",
            max_length=100,
            unique=True,
            blank=False,
            null=False,
            db_index=True,
            help_text="Нормализованное название для дедупликации брендов",
        ),
    )
    logo = cast(
        models.ImageField, models.ImageField("Логотип", upload_to="brands/", blank=True)
    )
    description = cast(str, models.TextField("Описание", blank=True))
    website = cast(str, models.URLField("Веб-сайт", blank=True))
    is_active = cast(bool, models.BooleanField("Активный", default=True))

    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )
    updated_at = cast(datetime, models.DateTimeField("Дата обновления", auto_now=True))

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"
        db_table = "brands"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Вычисляем normalized_name при сохранении
        # Если name пустой, используем пустую строку вместо None
        self.normalized_name = normalize_brand_name(self.name) if self.name else ""

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


class Brand1CMapping(models.Model):
    """
    Маппинг брендов из 1С на master-бренды в системе.
    Позволяет связывать несколько ID из 1С с одним брендом.
    """

    brand = cast(
        Brand,
        models.ForeignKey(
            Brand,
            on_delete=models.CASCADE,
            related_name="onec_mappings",
            verbose_name="Бренд",
            help_text="Master-бренд в системе",
        ),
    )
    onec_id = cast(
        str,
        models.CharField(
            "ID в 1С",
            max_length=100,
            unique=True,
            db_index=True,
            help_text="Уникальный идентификатор бренда из 1С",
        ),
    )
    onec_name = cast(
        str,
        models.CharField(
            "Название в 1С",
            max_length=100,
            help_text="Оригинальное название бренда из 1С",
        ),
    )
    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )

    class Meta:
        verbose_name = "Маппинг бренда 1С"
        verbose_name_plural = "Маппинги брендов 1С"
        db_table = "products_brand_1c_mapping"

    def __str__(self) -> str:
        return f"{self.onec_name} ({self.onec_id}) -> {self.brand}"


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
        parent = self.parent
        if parent:
            return f"{parent.full_name} > {self.name}"
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

    # Маркетинговые флаги для бейджей (Story 11.0)
    is_hit = cast(
        bool,
        models.BooleanField(
            "Хит продаж",
            default=False,
            db_index=True,
            help_text="Отображать бейдж 'Хит продаж' на карточке товара",
        ),
    )
    is_new = cast(
        bool,
        models.BooleanField(
            "Новинка",
            default=False,
            db_index=True,
            help_text="Отображать бейдж 'Новинка' на карточке товара",
        ),
    )
    is_sale = cast(
        bool,
        models.BooleanField(
            "Распродажа",
            default=False,
            db_index=True,
            help_text="Товар участвует в распродаже",
        ),
    )
    is_promo = cast(
        bool,
        models.BooleanField(
            "Акция",
            default=False,
            db_index=True,
            help_text="Товар участвует в акции/промо",
        ),
    )
    is_premium = cast(
        bool,
        models.BooleanField(
            "Премиум",
            default=False,
            db_index=True,
            help_text="Премиум товар (эксклюзив, лимитированная серия)",
        ),
    )
    discount_percent = cast(
        int | None,
        models.PositiveSmallIntegerField(
            "Процент скидки",
            null=True,
            blank=True,
            validators=[MaxValueValidator(100)],
            help_text="Процент скидки для отображения на бейдже (0-100)",
        ),
    )

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
    onec_brand_id = cast(
        str | None,
        models.CharField(
            "ID бренда в 1С",
            max_length=100,
            null=True,
            blank=True,
            db_index=True,
            help_text="Исходный идентификатор бренда из CommerceML для обратной синхронизации",
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
            # Story 11.0: Composite indexes для маркетинговых флагов (PERF-001)
            models.Index(fields=["is_hit", "is_active"]),
            models.Index(fields=["is_new", "is_active"]),
            models.Index(fields=["is_sale", "is_active"]),
            models.Index(fields=["is_promo", "is_active"]),
            models.Index(fields=["is_premium", "is_active"]),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            try:
                # Транслитерация кириллицы в латиницу, затем slugify
                transliterated = translit(self.name, "ru", reversed=True)
                base_slug = slugify(transliterated)
            except RuntimeError:
                # Fallback на обычный slugify
                base_slug = slugify(self.name)

            # Если slug все еще пустой, создаем fallback
            if not base_slug:
                base_slug = f"product-{self.pk or 0}"

            # Обеспечиваем уникальность slug
            self.slug = base_slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                # Добавляем UUID-суффикс для уникальности
                self.slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
                counter += 1
                # Защита от бесконечного цикла (маловероятно с UUID)
                if counter > 10:
                    self.slug = f"{base_slug}-{uuid.uuid4().hex}"
                    break

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
    celery_task_id = cast(
        str | None,
        models.CharField(
            "ID задачи Celery",
            max_length=255,
            null=True,
            blank=True,
            db_index=True,
            help_text="UUID задачи Celery для отслеживания прогресса",
        ),
    )

    class Meta:
        verbose_name = "Сессия импорта"
        verbose_name_plural = "Сессии импорта"
        db_table = "import_sessions"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["import_type", "status"]),
            models.Index(fields=["-started_at"]),
        ]

    if TYPE_CHECKING:

        def get_import_type_display(self) -> str:
            """Заглушка для метода Django, возвращающего название типа импорта."""
            return ""

        def get_status_display(self) -> str:
            """Заглушка для метода Django, возвращающего название статуса."""
            return ""

    def __str__(self) -> str:
        return (
            f"{self.get_import_type_display()} - "
            f"{self.get_status_display()} ({self.started_at})"
        )


class PriceType(models.Model):
    """
    Справочник типов цен из 1С для маппинга на поля Product
    """

    onec_id = cast(
        str,
        models.CharField(
            "UUID типа цены в 1С",
            max_length=100,
            unique=True,
            help_text="UUID из priceLists.xml",
        ),
    )
    onec_name = cast(
        str,
        models.CharField(
            "Название в 1С",
            max_length=200,
            help_text='Например: "Опт 1 (300-600 тыс.руб в квартал)"',
        ),
    )
    product_field = cast(
        str,
        models.CharField(
            "Поле в модели Product",
            max_length=50,
            choices=[
                ("retail_price", "Розничная цена"),
                ("opt1_price", "Оптовая цена уровень 1"),
                ("opt2_price", "Оптовая цена уровень 2"),
                ("opt3_price", "Оптовая цена уровень 3"),
                ("trainer_price", "Цена для тренера"),
                ("federation_price", "Цена для представителя федерации"),
                (
                    "recommended_retail_price",
                    "Рекомендованная розничная цена",
                ),
                (
                    "max_suggested_retail_price",
                    "Максимальная рекомендованная цена",
                ),
            ],
            help_text="Поле Product, в которое мапится эта цена",
        ),
    )
    user_role = cast(
        str,
        models.CharField(
            "Роль пользователя",
            max_length=50,
            blank=True,
            help_text="Роль пользователя, для которой применяется эта цена",
        ),
    )
    is_active = cast(bool, models.BooleanField("Активный", default=True))
    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )

    class Meta:
        verbose_name = "Тип цены"
        verbose_name_plural = "Типы цен"
        db_table = "price_types"
        ordering = ["onec_name"]

    def __str__(self) -> str:
        return f"{self.onec_name} → {self.product_field}"
