"""
Модели пользователей для платформы FREESPORT
Включает кастомную User модель с ролевой системой B2B/B2C
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Кастомная модель пользователя с email аутентификацией
    Поддерживает роли для B2B и B2C пользователей
    """
    
    # Роли пользователей согласно архитектурной документации
    ROLE_CHOICES = [
        ('retail', 'Розничный покупатель'),
        ('wholesale_level1', 'Оптовик уровень 1'),
        ('wholesale_level2', 'Оптовик уровень 2'), 
        ('wholesale_level3', 'Оптовик уровень 3'),
        ('trainer', 'Тренер'),
        ('federation_rep', 'Представитель федерации'),
        ('admin', 'Администратор'),
    ]
    
    # Убираем username, используем email для авторизации
    username = None
    email = models.EmailField('Email адрес', unique=True)
    
    # Дополнительные поля
    role = models.CharField(
        'Роль пользователя',
        max_length=20,
        choices=ROLE_CHOICES,
        default='retail'
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+7\d{10}$',
        message="Номер телефона должен быть в формате: '+79001234567'"
    )
    phone = models.CharField(
        'Номер телефона',
        validators=[phone_regex],
        max_length=12,
        blank=True
    )
    
    # B2B поля
    company_name = models.CharField(
        'Название компании',
        max_length=200,
        blank=True,
        help_text='Для B2B пользователей'
    )
    
    tax_id = models.CharField(
        'ИНН',
        max_length=12,
        blank=True,
        help_text='ИНН для B2B пользователей'
    )
    
    # Статус верификации для B2B
    is_verified = models.BooleanField(
        'Верифицирован',
        default=False,
        help_text='B2B пользователи требуют верификации администратором'
    )
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        db_table = 'users'
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        """Полное имя пользователя"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property 
    def is_b2b_user(self):
        """Является ли пользователь B2B клиентом"""
        b2b_roles = ['wholesale_level1', 'wholesale_level2', 'wholesale_level3', 'trainer', 'federation_rep']
        return self.role in b2b_roles
    
    @property
    def is_wholesale_user(self):
        """Является ли пользователь оптовым покупателем"""
        wholesale_roles = ['wholesale_level1', 'wholesale_level2', 'wholesale_level3']
        return self.role in wholesale_roles
    
    @property
    def wholesale_level(self):
        """Возвращает уровень оптового покупателя (1, 2, 3) или None"""
        if self.role.startswith('wholesale_level'):
            return int(self.role.split('_')[-1])
        return None


class Company(models.Model):
    """
    Модель компании для B2B пользователей
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='company',
        verbose_name='Пользователь'
    )
    
    legal_name = models.CharField('Юридическое название', max_length=255)
    tax_id = models.CharField('ИНН', max_length=12, unique=True)
    kpp = models.CharField('КПП', max_length=9, blank=True)
    legal_address = models.TextField('Юридический адрес')
    
    # Банковские реквизиты
    bank_name = models.CharField('Название банка', max_length=200, blank=True)
    bank_bik = models.CharField('БИК банка', max_length=9, blank=True)
    account_number = models.CharField('Расчетный счет', max_length=20, blank=True)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'
        db_table = 'companies'
    
    def __str__(self):
        return f"{self.legal_name} (ИНН: {self.tax_id})"


class Address(models.Model):
    """
    Модель адресов для пользователей
    """
    ADDRESS_TYPES = [
        ('shipping', 'Адрес доставки'),
        ('billing', 'Адрес для выставления счета'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='Пользователь'
    )
    
    address_type = models.CharField(
        'Тип адреса',
        max_length=10,
        choices=ADDRESS_TYPES,
        default='shipping'
    )
    
    full_name = models.CharField('Полное имя получателя', max_length=100)
    phone = models.CharField('Телефон', max_length=12)
    city = models.CharField('Город', max_length=100)
    street = models.CharField('Улица', max_length=200)
    building = models.CharField('Дом', max_length=10)
    apartment = models.CharField('Квартира/офис', max_length=10, blank=True)
    postal_code = models.CharField('Почтовый индекс', max_length=6)
    
    is_default = models.BooleanField('Адрес по умолчанию', default=False)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Адрес'
        verbose_name_plural = 'Адреса'
        db_table = 'addresses'
        unique_together = ['user', 'address_type', 'is_default']
    
    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.street} {self.building}"
    
    @property
    def full_address(self):
        """Полный адрес строкой"""
        parts = [self.postal_code, self.city, self.street, self.building]
        if self.apartment:
            parts.append(f"кв. {self.apartment}")
        return ", ".join(parts)