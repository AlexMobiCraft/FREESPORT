"""
Шаблон Django модели для FREESPORT
Скопируйте и адаптируйте под свою сущность
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify


class YourModel(models.Model):
    """
    Описание вашей модели

    TODO: Заполните описание того, что представляет эта модель
    """

    # ===== ОСНОВНЫЕ ПОЛЯ =====
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Slug", max_length=255, unique=True, blank=True)
    description = models.TextField("Описание", blank=True)

    # TODO: Добавьте специфичные поля вашей модели здесь
    # Примеры различных типов полей:

    # Текстовые поля
    # short_text = models.CharField("Короткий текст", max_length=100, blank=True)
    # long_text = models.TextField("Длинный текст", blank=True)

    # Числовые поля
    # price = models.DecimalField("Цена", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    # quantity = models.PositiveIntegerField("Количество", default=0)
    # rating = models.FloatField("Рейтинг", null=True, blank=True)

    # Булевы поля
    # is_featured = models.BooleanField("Рекомендуемый", default=False)
    # is_available = models.BooleanField("Доступен", default=True)

    # Даты
    # publish_date = models.DateField("Дата публикации", null=True, blank=True)
    # event_datetime = models.DateTimeField("Дата и время события", null=True, blank=True)

    # Файлы и изображения
    # image = models.ImageField("Изображение", upload_to="your_model/", blank=True)
    # document = models.FileField("Документ", upload_to="documents/", blank=True)

    # JSON поля (PostgreSQL)
    # specifications = models.JSONField("Спецификации", default=dict, blank=True)
    # metadata = models.JSONField("Метаданные", default=list, blank=True)

    # Связи с другими моделями
    # category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items", verbose_name="Категория")
    # tags = models.ManyToManyField(Tag, blank=True, verbose_name="Теги")
    # parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    # ===== SEO ПОЛЯ (если нужны) =====
    seo_title = models.CharField("SEO заголовок", max_length=200, blank=True)
    seo_description = models.TextField("SEO описание", blank=True)
    seo_keywords = models.CharField("SEO ключевые слова", max_length=500, blank=True)

    # ===== ОБЯЗАТЕЛЬНЫЕ ПОЛЯ (должны быть во ВСЕХ моделях) =====
    is_active = models.BooleanField("Активный", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    # ===== ИНТЕГРАЦИЯ С 1С (если нужна) =====
    onec_id = models.CharField("ID в 1С", max_length=100, blank=True, null=True)

    # ===== ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ АУДИТА (опционально) =====
    # created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_%(class)s", verbose_name="Создал")
    # updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="updated_%(class)s", verbose_name="Обновил")

    class Meta:
        verbose_name = "Ваша сущность"
        verbose_name_plural = "Ваши сущности"
        db_table = "your_table_name"  # 🔥 ВАЖНО: Кастомное имя таблицы
        ordering = ["-created_at"]  # Сортировка по умолчанию

        # Индексы для производительности
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["slug"]),
            # TODO: Добавьте индексы для полей по которым часто фильтруете/сортируете
            # models.Index(fields=['category', 'is_active']),
            # models.Index(fields=['price']),
        ]

        # Ограничения уникальности (если нужны)
        # constraints = [
        #     models.UniqueConstraint(fields=['name', 'category'], name='unique_name_per_category'),
        #     models.CheckConstraint(check=Q(price__gte=0), name='price_non_negative'),
        # ]

    def save(self, *args, **kwargs):
        """
        Переопределение метода сохранения для дополнительной логики
        """
        # Автогенерация slug из названия
        if not self.slug:
            self.slug = slugify(self.name)

        # TODO: Добавьте свою логику здесь
        # Например:
        # - Валидация данных
        # - Обработка изображений
        # - Генерация дополнительных полей
        # - Логирование изменений

        super().save(*args, **kwargs)

    def __str__(self):
        """Строковое представление объекта"""
        return self.name

        # TODO: Можете сделать более информативным:
        # return f"{self.name} ({self.category})" если есть категория
        # return f"{self.name} - {self.price}₽" если есть цена

    def clean(self):
        """
        Валидация на уровне модели
        Вызывается при .full_clean() и в Django Admin
        """
        from django.core.exceptions import ValidationError

        # TODO: Добавьте свою валидацию
        # Примеры:

        # if self.price and self.price < 0:
        #     raise ValidationError({'price': 'Цена не может быть отрицательной'})

        # if self.start_date and self.end_date and self.start_date > self.end_date:
        #     raise ValidationError({'end_date': 'Дата окончания не может быть раньше даты начала'})

        super().clean()

    # ===== COMPUTED PROPERTIES (вычисляемые свойства) =====

    @property
    def display_name(self):
        """Отображаемое название (например, для UI)"""
        return self.name or f"ID: {self.id}"

    # TODO: Добавьте свои computed properties
    # Примеры:

    # @property
    # def is_new(self):
    #     """Новый ли объект (создан менее недели назад)"""
    #     from datetime import timedelta
    #     from django.utils import timezone
    #     return self.created_at > timezone.now() - timedelta(days=7)

    # @property
    # def formatted_price(self):
    #     """Форматированная цена"""
    #     return f"{self.price:,.2f}₽" if self.price else "Цена не указана"

    # ===== BUSINESS LOGIC METHODS (бизнес-логика) =====

    def get_absolute_url(self):
        """URL для детального просмотра объекта"""
        from django.urls import reverse

        return reverse("your_model_detail", kwargs={"slug": self.slug})

    # TODO: Добавьте методы бизнес-логики
    # Примеры:

    # def can_be_deleted(self):
    #     """Можно ли удалить этот объект"""
    #     return not hasattr(self, 'orders') or not self.orders.exists()

    # def get_related_items(self):
    #     """Получить связанные объекты"""
    #     return YourModel.objects.filter(category=self.category).exclude(id=self.id)[:5]

    # def calculate_total(self):
    #     """Вычислить общую сумму"""
    #     return sum(item.price for item in self.items.all())

    # ===== КЛАССОВЫЕ МЕТОДЫ =====

    @classmethod
    def get_active(cls):
        """Получить только активные объекты"""
        return cls.objects.filter(is_active=True)

    @classmethod
    def get_popular(cls, limit=10):
        """Получить популярные объекты"""
        # TODO: Реализуйте логику популярности
        return cls.get_active().order_by("-created_at")[:limit]


# ===== ДОПОЛНИТЕЛЬНЫЕ МОДЕЛИ (если нужны) =====


class YourModelImage(models.Model):
    """
    Модель для хранения изображений вашей основной модели
    Используйте если нужно несколько изображений
    """

    your_model = models.ForeignKey(
        YourModel,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Основной объект",
    )
    image = models.ImageField("Изображение", upload_to="your_model_images/")
    alt_text = models.CharField("Альтернативный текст", max_length=255, blank=True)
    is_main = models.BooleanField("Основное изображение", default=False)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)

    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"
        db_table = "your_model_images"
        ordering = ["sort_order", "created_at"]
        indexes = [
            models.Index(fields=["your_model", "is_main"]),
        ]

    def save(self, *args, **kwargs):
        # Если это основное изображение, убираем флаг у других
        if self.is_main:
            YourModelImage.objects.filter(
                your_model=self.your_model, is_main=True
            ).exclude(pk=self.pk).update(is_main=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Изображение {self.your_model.name}"


# ===== ПРИМЕР МОДЕЛИ СО СВЯЗЯМИ =====


class YourModelCategory(models.Model):
    """Категория для вашей модели (если нужна иерархия)"""

    name = models.CharField("Название", max_length=200)
    slug = models.SlugField("Slug", max_length=255, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родительская категория",
    )
    description = models.TextField("Описание", blank=True)
    image = models.ImageField("Изображение", upload_to="categories/", blank=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)

    is_active = models.BooleanField("Активная", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        db_table = "your_model_categories"
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def full_name(self):
        """Полное название с учетом иерархии"""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name
