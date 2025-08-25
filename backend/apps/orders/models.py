"""
Модели заказов для платформы FREESPORT
Поддерживает B2B и B2C заказы с различными способами оплаты и доставки
"""
import uuid
from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

User = get_user_model()


class Order(models.Model):
    """
    Модель заказа
    Поддерживает как авторизованных пользователей, так и гостевые заказы
    """

    ORDER_STATUSES = [
        ("pending", "Ожидает обработки"),
        ("confirmed", "Подтвержден"),
        ("processing", "В обработке"),
        ("shipped", "Отправлен"),
        ("delivered", "Доставлен"),
        ("cancelled", "Отменен"),
        ("refunded", "Возвращен"),
    ]

    DELIVERY_METHODS = [
        ("pickup", "Самовывоз"),
        ("courier", "Курьерская доставка"),
        ("post", "Почтовая доставка"),
        ("transport", "Транспортная компания"),
    ]

    PAYMENT_METHODS = [
        ("card", "Банковская карта"),
        ("cash", "Наличные"),
        ("bank_transfer", "Банковский перевод"),
        ("payment_on_delivery", "Оплата при получении"),
    ]

    PAYMENT_STATUSES = [
        ("pending", "Ожидает оплаты"),
        ("paid", "Оплачен"),
        ("failed", "Ошибка оплаты"),
        ("refunded", "Возвращен"),
    ]

    # Идентификация заказа
    order_number = models.CharField(
        "Номер заказа", max_length=50, unique=True, editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Пользователь",
    )

    # Информация о клиенте (для гостевых заказов)
    customer_name = models.CharField("Имя клиента", max_length=200, blank=True)
    customer_email = models.EmailField("Email клиента", blank=True)
    customer_phone = models.CharField("Телефон клиента", max_length=20, blank=True)

    # Детали заказа
    status = models.CharField(
        "Статус заказа", max_length=50, choices=ORDER_STATUSES, default="pending"
    )
    total_amount = models.DecimalField(
        "Общая сумма",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount_amount = models.DecimalField(
        "Сумма скидки",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    delivery_cost = models.DecimalField(
        "Стоимость доставки",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    # Информация о доставке
    delivery_address = models.TextField("Адрес доставки")
    delivery_method = models.CharField(
        "Способ доставки", max_length=50, choices=DELIVERY_METHODS
    )
    delivery_date = models.DateField('Дата доставки', null=True, blank=True)
    tracking_number = models.CharField(
        'Трек-номер',
        max_length=100,
        blank=True,
        help_text='Номер для отслеживания посылки'
    )
    # Информация об оплате
    payment_method = models.CharField(
        "Способ оплаты", max_length=50, choices=PAYMENT_METHODS
    )
    payment_status = models.CharField(
        "Статус оплаты", max_length=50, choices=PAYMENT_STATUSES, default="pending"
    )
    payment_id = models.CharField("ID платежа (ЮKassa)", max_length=100, blank=True)

    # Дополнительная информация
    notes = models.TextField("Комментарии к заказу", blank=True)

    # Временные метки
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        db_table = "orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["order_number"]),
            models.Index(fields=["payment_status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Заказ #{self.order_number}"

    @staticmethod
    def generate_order_number():
        """Генерация уникального номера заказа в формате FS-YYMMDD-XXXXX"""
        date_part = datetime.now().strftime('%y%m%d')
        random_part = str(uuid.uuid4().hex)[:5].upper()
        return f"FS-{date_part}-{random_part}"

    @property
    def subtotal(self):
        """Подытог заказа без учета доставки и скидок"""
        return sum(item.total_price for item in self.items.all())

    @property
    def customer_display_name(self):
        """Отображаемое имя клиента"""
        if self.user:
            return self.user.full_name or self.user.email
        return self.customer_name or self.customer_email

    @property
    def total_items(self):
        """Общее количество товаров в заказе"""
        return sum(item.quantity for item in self.items.all())

    @property
    def calculated_total(self):
        """Рассчитанная общая сумма заказа"""
        return sum(item.total_price for item in self.items.all())

    @property
    def can_be_cancelled(self):
        """Можно ли отменить заказ"""
        return self.status in ["pending", "confirmed"]

    def can_be_refunded(self):
        """Можно ли вернуть заказ"""
        return self.status in ["delivered"] and self.payment_status == "paid"


class OrderItem(models.Model):
    """
    Элемент заказа - товар с количеством и ценой на момент заказа
    """

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, verbose_name="Товар"
    )
    quantity = models.PositiveIntegerField(
        "Количество", validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        "Цена за единицу",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    total_price = models.DecimalField(
        "Общая стоимость",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    # Снимок данных о продукте на момент заказа
    product_name = models.CharField("Название товара", max_length=300)
    product_sku = models.CharField("Артикул товара", max_length=100)

    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"
        db_table = "order_items"
        unique_together = ("order", "product")
        indexes = [
            models.Index(fields=["order", "product"]),
        ]

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем общую стоимость
        self.total_price = self.unit_price * self.quantity

        # Сохраняем снимок данных продукта
        if self.product and not self.product_name:
            self.product_name = self.product.name
            self.product_sku = self.product.sku

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.product_name} x{self.quantity} в заказе #{self.order.order_number}"
        )
