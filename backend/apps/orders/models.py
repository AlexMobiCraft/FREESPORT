"""
Модели заказов для платформы FREESPORT
Поддерживает B2B и B2C заказы с различными способами оплаты и доставки
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from apps.products.models import Product as ProductType
    from apps.users.models import User as UserType

User = get_user_model()


class Order(models.Model):
    """Модель заказа.

    Хранит ключевые сведения о заказе, покупателе и оплате и используется как в B2C,
    так и в B2B-сценариях."""

    objects = models.Manager()

    if TYPE_CHECKING:
        items: RelatedManager["OrderItem"]
        order_number: str
        user: UserType | None
        customer_name: str
        customer_email: str
        customer_phone: str
        status: str
        total_amount: Decimal
        discount_amount: Decimal
        delivery_cost: Decimal
        delivery_address: str
        delivery_method: str
        delivery_date: date | None
        tracking_number: str
        payment_method: str
        payment_status: str
        payment_id: str
        notes: str
        created_at: datetime
        updated_at: datetime

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
    order_number = cast(
        str,
        models.CharField("Номер заказа", max_length=50, unique=True, editable=False),
    )
    user = cast(
        "UserType | None",
        models.ForeignKey(
            User,
            on_delete=models.CASCADE,
            null=True,
            blank=True,
            related_name="orders",
            verbose_name="Пользователь",
        ),
    )

    # Информация о клиенте (для гостевых заказов)
    customer_name = cast(
        str, models.CharField("Имя клиента", max_length=200, blank=True)
    )
    customer_email = cast(str, models.EmailField("Email клиента", blank=True))
    customer_phone = cast(
        str, models.CharField("Телефон клиента", max_length=20, blank=True)
    )

    # Детали заказа
    status = cast(
        str,
        models.CharField(
            "Статус заказа", max_length=50, choices=ORDER_STATUSES, default="pending"
        ),
    )
    total_amount = cast(
        Decimal,
        models.DecimalField(
            "Общая сумма",
            max_digits=10,
            decimal_places=2,
            validators=[MinValueValidator(0)],
        ),
    )
    discount_amount = cast(
        Decimal,
        models.DecimalField(
            "Сумма скидки",
            max_digits=10,
            decimal_places=2,
            default=0,
            validators=[MinValueValidator(0)],
        ),
    )
    delivery_cost = cast(
        Decimal,
        models.DecimalField(
            "Стоимость доставки",
            max_digits=10,
            decimal_places=2,
            default=0,
            validators=[MinValueValidator(0)],
        ),
    )

    # Информация о доставке
    delivery_address = cast(str, models.TextField("Адрес доставки"))
    delivery_method = cast(
        str,
        models.CharField("Способ доставки", max_length=50, choices=DELIVERY_METHODS),
    )
    delivery_date = cast(
        "date | None", models.DateField("Дата доставки", null=True, blank=True)
    )
    tracking_number = cast(
        str,
        models.CharField(
            "Трек-номер",
            max_length=100,
            blank=True,
            help_text="Номер для отслеживания посылки",
        ),
    )
    # Информация об оплате
    payment_method = cast(
        str, models.CharField("Способ оплаты", max_length=50, choices=PAYMENT_METHODS)
    )
    payment_status = cast(
        str,
        models.CharField(
            "Статус оплаты", max_length=50, choices=PAYMENT_STATUSES, default="pending"
        ),
    )
    payment_id = cast(
        str, models.CharField("ID платежа (ЮKassa)", max_length=100, blank=True)
    )

    # Дополнительная информация
    notes = cast(str, models.TextField("Комментарии к заказу", blank=True))

    # Временные метки
    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )
    updated_at = cast(datetime, models.DateTimeField("Дата обновления", auto_now=True))

    class Meta:
        """Метаданные Django ORM для модели `Order`."""

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

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Заказ #{self.order_number}"

    @staticmethod
    def generate_order_number() -> str:
        """Генерация уникального номера заказа на основе UUID"""
        return str(uuid.uuid4())

    @property
    def subtotal(self) -> Decimal:
        """Подытог заказа без учета доставки и скидок"""
        return Decimal(sum(item.total_price for item in self.items.all()))

    @property
    def customer_display_name(self) -> str:
        """Отображаемое имя клиента"""
        user = self.user
        if user:
            full_name = getattr(user, "full_name", "") or ""
            email = getattr(user, "email", "") or ""
            return full_name or email
        return self.customer_name or self.customer_email

    @property
    def total_items(self) -> int:
        """Общее количество товаров в заказе"""
        return sum(item.quantity for item in self.items.all())

    @property
    def calculated_total(self) -> Decimal:
        """Рассчитанная общая сумма заказа"""
        return Decimal(sum(item.total_price for item in self.items.all()))

    @property
    def can_be_cancelled(self) -> bool:
        """Можно ли отменить заказ"""
        return self.status in ["pending", "confirmed"]

    def can_be_refunded(self) -> bool:
        """Можно ли вернуть заказ"""
        return self.status in ["delivered"] and self.payment_status == "paid"


class OrderItem(models.Model):
    """Элемент заказа с информацией о товаре и зафиксированной цене."""

    objects = models.Manager()

    if TYPE_CHECKING:
        order: Order
        product: ProductType | None
        quantity: int
        unit_price: Decimal
        total_price: Decimal
        product_name: str
        product_sku: str
        created_at: datetime
        updated_at: datetime

    order = cast(
        Order,
        models.ForeignKey(
            Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ"
        ),
    )
    product = cast(
        "ProductType | None",
        models.ForeignKey(
            "products.Product", on_delete=models.CASCADE, verbose_name="Товар"
        ),
    )
    quantity = cast(
        int,
        models.PositiveIntegerField("Количество", validators=[MinValueValidator(1)]),
    )
    unit_price = cast(
        Decimal,
        models.DecimalField(
            "Цена за единицу",
            max_digits=10,
            decimal_places=2,
            validators=[MinValueValidator(0)],
        ),
    )
    total_price = cast(
        Decimal,
        models.DecimalField(
            "Общая стоимость",
            max_digits=10,
            decimal_places=2,
            validators=[MinValueValidator(0)],
        ),
    )

    # Снимок данных о продукте на момент заказа
    product_name = cast(str, models.CharField("Название товара", max_length=300))
    product_sku = cast(str, models.CharField("Артикул товара", max_length=100))

    created_at = cast(
        datetime, models.DateTimeField("Дата создания", auto_now_add=True)
    )
    updated_at = cast(datetime, models.DateTimeField("Дата обновления", auto_now=True))

    class Meta:
        """Метаданные Django ORM для модели `OrderItem`."""

        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"
        db_table = "order_items"
        unique_together = ("order", "product")
        indexes = [
            models.Index(fields=["order", "product"]),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Автоматически рассчитываем общую стоимость
        self.total_price = self.unit_price * self.quantity

        # Сохраняем снимок данных продукта
        product = self.product
        if product and not self.product_name:
            self.product_name = getattr(product, "name", self.product_name)
            self.product_sku = getattr(product, "sku", self.product_sku)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        order = self.order
        order_number = getattr(order, "order_number", "")
        return f"{self.product_name} x{self.quantity} в заказе #{order_number}"
