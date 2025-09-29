"""
Django Model - Реальный пример из проекта FREESPORT
Демонстрирует паттерны ролевого ценообразования, кастомные таблицы, SEO поля
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify


class Product(models.Model):
    """
    Модель товара с роле-ориентированным ценообразованием
    Реальный пример из apps/products/models.py
    """

    name = models.CharField("Название", max_length=300)
    slug = models.SlugField("Slug", max_length=255, unique=True)
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="products", verbose_name="Бренд"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="Категория",
    )
    description = models.TextField("Описание")
    short_description = models.CharField("Краткое описание", max_length=500, blank=True)
    specifications = models.JSONField(
        "Технические характеристики", default=dict, blank=True
    )

    # ✅ ПАТТЕРН: Ролевое ценообразование - ключевая особенность FREESPORT
    retail_price = models.DecimalField(
        "Розничная цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    opt1_price = models.DecimalField(
        "Оптовая цена уровень 1",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    opt2_price = models.DecimalField(
        "Оптовая цена уровень 2",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    opt3_price = models.DecimalField(
        "Оптовая цена уровень 3",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    trainer_price = models.DecimalField(
        "Цена для тренера",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    federation_price = models.DecimalField(
        "Цена для представителя федерации",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    # ✅ ПАТТЕРН: Информационные цены для B2B
    recommended_retail_price = models.DecimalField(
        "Рекомендованная розничная цена (RRP)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    max_suggested_retail_price = models.DecimalField(
        "Максимальная рекомендованная цена (MSRP)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    # ✅ ПАТТЕРН: Стандартные поля для всех моделей
    is_active = models.BooleanField("Активный", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    # ✅ ПАТТЕРН: Интеграция с 1С
    onec_id = models.CharField("ID в 1С", max_length=100, blank=True, null=True)

    # ✅ ПАТТЕРН: Кастомное имя таблицы и правильная Meta
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        db_table = "products"  # 👈 ВАЖНО: Кастомные имена таблиц
        ordering = ["-created_at"]
        indexes = [  # 👈 ВАЖНО: Индексы для производительности
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["brand", "is_active"]),
            models.Index(fields=["stock_quantity"]),
        ]

    def save(self, *args, **kwargs):
        """✅ ПАТТЕРН: Авто-генерация slug и SKU"""
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            import uuid
            import time

            self.sku = f"AUTO-{int(time.time())}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_price_for_user(self, user):
        """
        ✅ ПАТТЕРН: Основной метод ролевого ценообразования
        ИСПОЛЬЗУЙТЕ ЭТОТ ПАТТЕРН во всех моделях с ценами!
        """
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

    # ✅ ПАТТЕРН: Computed properties для бизнес-логики
    @property
    def is_in_stock(self):
        """Проверка наличия товара на складе"""
        return self.stock_quantity > 0

    @property
    def can_be_ordered(self):
        """Можно ли заказать товар"""
        return self.is_active and self.is_in_stock


# ✅ ШАБЛОН МОДЕЛИ ДЛЯ НОВЫХ СУЩНОСТЕЙ
class YourNewModel(models.Model):
    """
    Шаблон новой модели по стандартам FREESPORT
    Скопируйте и адаптируйте под свои нужды
    """

    # Основные поля
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Slug", max_length=255, unique=True, blank=True)
    description = models.TextField("Описание", blank=True)

    # SEO поля (если нужны)
    seo_title = models.CharField("SEO заголовок", max_length=200, blank=True)
    seo_description = models.TextField("SEO описание", blank=True)

    # Стандартные поля (ОБЯЗАТЕЛЬНО во всех моделях)
    is_active = models.BooleanField("Активный", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    # Интеграция с 1С (если нужна)
    onec_id = models.CharField("ID в 1С", max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Ваша сущность"
        verbose_name_plural = "Ваши сущности"
        db_table = "your_table_name"  # 👈 ВАЖНО: Кастомное имя таблицы
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"]),
            # добавьте индексы по мере необходимости
        ]

    def save(self, *args, **kwargs):
        """Авто-генерация slug"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
