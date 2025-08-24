"""
Модели продуктов для платформы FREESPORT
Включает товары, категории, бренды с роле-ориентированным ценообразованием
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify


class Brand(models.Model):
    """
    Модель бренда товаров
    """
    name = models.CharField('Название бренда', max_length=100, unique=True)
    slug = models.SlugField('Slug', unique=True)
    logo = models.ImageField('Логотип', upload_to='brands/', blank=True)
    description = models.TextField('Описание', blank=True)
    website = models.URLField('Веб-сайт', blank=True)
    is_active = models.BooleanField('Активный', default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        db_table = 'brands'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Модель категорий товаров с поддержкой иерархии
    """
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('Slug', unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='categories/', blank=True)
    is_active = models.BooleanField('Активная', default=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    # SEO поля
    seo_title = models.CharField('SEO заголовок', max_length=200, blank=True)
    seo_description = models.TextField('SEO описание', blank=True)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        db_table = 'categories'
        ordering = ['sort_order', 'name']

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
        """Полное название категории с учетом иерархии"""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name


class Product(models.Model):
    """
    Модель товара с роле-ориентированным ценообразованием
    """
    name = models.CharField('Название', max_length=300)
    slug = models.SlugField('Slug', unique=True)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Бренд'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Категория'
    )
    description = models.TextField('Описание')
    short_description = models.CharField('Краткое описание', max_length=500, blank=True)
    specifications = models.JSONField('Технические характеристики', default=dict, blank=True)
    
    # Ценообразование для различных ролей пользователей
    retail_price = models.DecimalField(
        'Розничная цена',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    opt1_price = models.DecimalField(
        'Оптовая цена уровень 1',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    opt2_price = models.DecimalField(
        'Оптовая цена уровень 2',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    opt3_price = models.DecimalField(
        'Оптовая цена уровень 3',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    trainer_price = models.DecimalField(
        'Цена для тренера',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    federation_price = models.DecimalField(
        'Цена для представителя федерации',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Информационные цены для B2B пользователей
    recommended_retail_price = models.DecimalField(
        'Рекомендованная розничная цена (RRP)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    max_suggested_retail_price = models.DecimalField(
        'Максимальная рекомендованная цена (MSRP)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Инвентаризация
    sku = models.CharField('Артикул', max_length=100, unique=True)
    stock_quantity = models.PositiveIntegerField('Количество на складе', default=0)
    min_order_quantity = models.PositiveIntegerField('Минимальное количество заказа', default=1)
    
    # Изображения
    main_image = models.ImageField('Основное изображение', upload_to='products/')
    gallery_images = models.JSONField('Галерея изображений', default=list, blank=True)
    
    # SEO и мета информация
    seo_title = models.CharField('SEO заголовок', max_length=200, blank=True)
    seo_description = models.TextField('SEO описание', blank=True)
    
    # Флаги
    is_active = models.BooleanField('Активный', default=True)
    is_featured = models.BooleanField('Рекомендуемый', default=False)
    
    # Временные метки и интеграция с 1С
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    onec_id = models.CharField('ID в 1С', max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['stock_quantity']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_price_for_user(self, user):
        """Получить цену товара для конкретного пользователя на основе его роли"""
        if not user or not user.is_authenticated:
            return self.retail_price
            
        role_price_mapping = {
            'retail': self.retail_price,
            'wholesale_level1': self.opt1_price or self.retail_price,
            'wholesale_level2': self.opt2_price or self.retail_price,
            'wholesale_level3': self.opt3_price or self.retail_price,
            'trainer': self.trainer_price or self.retail_price,
            'federation_rep': self.federation_price or self.retail_price,
        }
        
        return role_price_mapping.get(user.role, self.retail_price)

    @property
    def is_in_stock(self):
        """Проверка наличия товара на складе"""
        return self.stock_quantity > 0

    @property
    def can_be_ordered(self):
        """Можно ли заказать товар"""
        return self.is_active and self.is_in_stock


class ProductImage(models.Model):
    """
    Модель изображений товара
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар'
    )
    image = models.ImageField('Изображение', upload_to='products/gallery/')
    alt_text = models.CharField('Альтернативный текст', max_length=255, blank=True)
    is_main = models.BooleanField('Основное изображение', default=False)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        db_table = 'product_images'
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_main']),
            models.Index(fields=['sort_order']),
        ]

    def __str__(self):
        return f"Изображение {self.product.name} ({'основное' if self.is_main else 'дополнительное'})"

    def save(self, *args, **kwargs):
        # Если это основное изображение, убираем флаг у других изображений этого товара
        if self.is_main:
            ProductImage.objects.filter(product=self.product, is_main=True).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)