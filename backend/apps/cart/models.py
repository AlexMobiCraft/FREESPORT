"""
Модели корзины покупок для платформы FREESPORT
Поддерживает как авторизованных, так и гостевых пользователей
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

if TYPE_CHECKING:
    from django.db.models import QuerySet

User = get_user_model()


class Cart(models.Model):
    """
    Модель корзины покупок
    Поддерживает как авторизованных пользователей, так и гостей (по session_key)
    """

    if TYPE_CHECKING:
        items: QuerySet["CartItem"]  # Hint для Pylance о related_name

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart",
        verbose_name="Пользователь",
    )
    session_key = models.CharField(
        "Ключ сессии",
        max_length=100,
        blank=True,
        help_text="Для гостевых пользователей",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"
        db_table = "carts"
        constraints = [
            # Корзина должна иметь либо пользователя, либо session_key
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(session_key__isnull=False),
                name="cart_must_have_user_or_session",
            )
        ]

    def __str__(self):
        if self.user:
            return f"Корзина пользователя {self.user.email}"
        return f"Гостевая корзина {self.session_key[:10]}..."

    @property
    def total_items(self):
        """Общее количество товаров в корзине"""
        from django.db.models import Sum

        result = self.items.aggregate(total=Sum("quantity"))["total"]
        return result or 0

    @property
    def total_amount(self):
        """Общая стоимость товаров в корзине"""
        total = 0
        for item in self.items.select_related("product").all():
            user = self.user
            price = item.product.get_price_for_user(user)
            total += price * item.quantity
        return total

    def clear(self):
        """Очистить корзину"""
        self.items.all().delete()
        # Обновляем только updated_at без лишнего save()
        self.save(update_fields=["updated_at"])


class CartItem(models.Model):
    """
    Элемент корзины - товар с количеством
    """

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name="Корзина"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, verbose_name="Товар"
    )
    quantity = models.PositiveIntegerField(
        "Количество", default=1, validators=[MinValueValidator(1)]
    )
    added_at = models.DateTimeField("Дата добавления", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        db_table = "cart_items"
        unique_together = ("cart", "product")
        indexes = [
            models.Index(fields=["cart", "added_at"]),
        ]

    def __str__(self):
        return f"{self.product.name} x{self.quantity} в корзине"

    @property
    def total_price(self):
        """Стоимость этого элемента корзины"""
        user = self.cart.user
        price = self.product.get_price_for_user(user)
        return price * self.quantity

    def clean(self):
        """Валидация элемента корзины"""
        from django.core.exceptions import ValidationError

        # Проверяем, что товар активен
        if not self.product.is_active:
            raise ValidationError("Товар неактивен")

        # Проверяем наличие на складе
        if self.quantity > self.product.stock_quantity:
            raise ValidationError(
                f"Недостаточно товара на складе. Доступно: {self.product.stock_quantity}"
            )

        # Проверяем минимальное количество заказа
        if self.quantity < self.product.min_order_quantity:
            raise ValidationError(
                f"Минимальное количество заказа: {self.product.min_order_quantity}"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        # Обновляем время модификации корзины
        self.cart.save(update_fields=["updated_at"])
