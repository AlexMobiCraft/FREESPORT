"""Модели бонусной программы для тренеров.

Баланс тренера — всегда `SUM(amount)` по журналу `BonusTransaction`.
Денормализованного поля баланса не существует: журнал является единственным
источником истины, а история операций не редактируется и не удаляется.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.orders.constants import ORDER_STATUSES

if TYPE_CHECKING:
    from datetime import datetime

    from apps.orders.models import Order as OrderType
    from apps.users.models import User as UserType


class BonusProgramSettings(models.Model):
    """Глобальные настройки бонусной программы (singleton, pk=1).

    Процент единый для всех тренеров. `accrual_status` вынесен в настройки,
    чтобы менять момент начисления без деплоя: в УТ 11 статус «Закрыт»
    ставится и на выполненный, и на закрытый с отменой заказ.
    """

    objects = models.Manager()

    if TYPE_CHECKING:
        is_active: bool
        percent: Decimal
        accrual_status: str
        program_start_at: datetime | None
        updated_at: datetime

    is_active = cast(
        bool,
        models.BooleanField(
            "Программа активна",
            default=True,
            help_text="Выключение прекращает начисления; накопленные бонусы сохраняются",
        ),
    )
    percent = cast(
        Decimal,
        models.DecimalField(
            "Процент начисления",
            max_digits=5,
            decimal_places=2,
            default=Decimal("5.00"),
            validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
            help_text="Процент от стоимости товаров в заказе (без доставки)",
        ),
    )
    accrual_status = cast(
        str,
        models.CharField(
            "Статус заказа для начисления",
            max_length=50,
            choices=ORDER_STATUSES,
            default="delivered",
            help_text="Начисление происходит при переходе мастер-заказа в этот статус",
        ),
    )
    program_start_at = cast(
        "datetime | None",
        models.DateTimeField(
            "Дата запуска программы",
            null=True,
            blank=True,
            default=timezone.now,
            help_text=(
                "Бонусы начисляются только по заказам, созданным не раньше этой даты. "
                "Пустое значение отключает отсечку — начисление пойдёт и по старым заказам"
            ),
        ),
    )
    updated_at = cast("datetime", models.DateTimeField("Дата обновления", auto_now=True))

    class Meta:
        """Метаданные Django ORM для модели `BonusProgramSettings`."""

        verbose_name = "Настройки бонусной программы"
        verbose_name_plural = "Настройки бонусной программы"
        db_table = "bonus_program_settings"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Жёстко фиксирует pk=1 — вторая запись настроек невозможна."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """Удаление singleton-настроек запрещено."""
        raise ValidationError("Настройки бонусной программы удалить нельзя.")

    @classmethod
    def load(cls) -> "BonusProgramSettings":
        """Возвращает настройки, создавая их со значениями по умолчанию при отсутствии."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        state = "включена" if self.is_active else "выключена"
        return f"Бонусная программа ({state}, {self.percent}%)"


class BonusTransaction(models.Model):
    """Операция журнала бонусов.

    Знак `amount` определяется типом операции: `accrual` > 0,
    `payout` и `writeoff` < 0. Менеджер вводит положительное число —
    знак проставляется в `save()`.
    """

    objects = models.Manager()

    if TYPE_CHECKING:
        user: UserType
        transaction_type: str
        amount: Decimal
        order: OrderType | None
        percent_applied: Decimal | None
        base_amount: Decimal | None
        comment: str
        created_by: UserType | None
        created_at: datetime

    ACCRUAL = "accrual"
    PAYOUT = "payout"
    WRITEOFF = "writeoff"

    TRANSACTION_TYPES = [
        (ACCRUAL, "Начисление"),
        (PAYOUT, "Выплата"),
        (WRITEOFF, "Списание"),
    ]

    MANUAL_TYPES = {PAYOUT, WRITEOFF}
    """Типы операций, создаваемые менеджером вручную."""

    NEGATIVE_TYPES = {PAYOUT, WRITEOFF}
    """Типы операций, уменьшающие баланс."""

    user = cast(
        "UserType",
        models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="bonus_transactions",
            verbose_name="Тренер",
        ),
    )
    transaction_type = cast(
        str,
        models.CharField("Тип операции", max_length=20, choices=TRANSACTION_TYPES),
    )
    amount = cast(
        Decimal,
        models.DecimalField(
            "Сумма",
            max_digits=10,
            decimal_places=2,
            help_text="Начисление — положительная, выплата и списание — отрицательная",
        ),
    )
    order = cast(
        "OrderType | None",
        models.ForeignKey(
            "orders.Order",
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="bonus_transactions",
            verbose_name="Заказ",
            help_text="Заполняется только для начислений",
        ),
    )
    percent_applied = cast(
        "Decimal | None",
        models.DecimalField(
            "Применённый процент",
            max_digits=5,
            decimal_places=2,
            null=True,
            blank=True,
            help_text="Снимок процента на момент начисления",
        ),
    )
    base_amount = cast(
        "Decimal | None",
        models.DecimalField(
            "База начисления",
            max_digits=10,
            decimal_places=2,
            null=True,
            blank=True,
            help_text="Снимок стоимости товаров на момент начисления",
        ),
    )
    comment = cast(
        str,
        models.TextField(
            "Комментарий",
            blank=True,
            help_text="Обязателен для выплат и списаний: основание операции",
        ),
    )
    created_by = cast(
        "UserType | None",
        models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="created_bonus_transactions",
            verbose_name="Кто создал",
        ),
    )
    created_at = cast("datetime", models.DateTimeField("Дата создания", auto_now_add=True))

    class Meta:
        """Метаданные Django ORM для модели `BonusTransaction`."""

        verbose_name = "Бонусная операция"
        verbose_name_plural = "Бонусные операции"
        db_table = "bonus_transactions"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="idx_bonus_user_created"),
        ]
        constraints = [
            # Знак суммы жёстко связан с типом операции
            models.CheckConstraint(
                condition=(Q(transaction_type="accrual") & Q(amount__gt=0))
                | (Q(transaction_type__in=["payout", "writeoff"]) & Q(amount__lt=0)),
                name="check_bonus_amount_sign",
            ),
            # Идемпотентность начисления: импорт из 1С ретраится
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(transaction_type="accrual"),
                name="uniq_bonus_accrual_per_order",
            ),
        ]

    def _normalize_amount(self) -> None:
        """Приводит знак суммы к типу операции.

        Нормализуются только выплаты и списания — менеджер вводит их
        положительным числом. Начисления знак не меняют: их создаёт сервис,
        и молча переворачивать неверный знак в денежном коде нельзя —
        пусть CheckConstraint отклонит операцию.

        Вызывается из `clean()` до проверки CheckConstraint в `full_clean()`
        и из `save()` — для прямых вызовов `objects.create()` в обход валидации.
        """
        if self.amount is not None and self.transaction_type in self.NEGATIVE_TYPES:
            self.amount = -abs(self.amount)

    def clean(self) -> None:
        """Валидация ручных операций.

        Комментарий обязателен для выплат и списаний. Выплата ограничена
        текущим балансом (защита от опечатки); списание может увести баланс
        в минус — это осознанно отражает долг тренера.
        """
        super().clean()
        self._normalize_amount()

        if self.amount is not None and self.amount == 0:
            raise ValidationError({"amount": "Сумма операции не может быть нулевой."})

        if self.transaction_type in self.MANUAL_TYPES and not (self.comment or "").strip():
            raise ValidationError({"comment": "Укажите основание операции — комментарий обязателен."})

        if self.transaction_type == self.PAYOUT and self.amount is not None and self.user_id is not None:
            from apps.bonuses.services.accrual import get_balance

            requested = abs(self.amount)
            balance = get_balance(self.user_id, exclude_pk=self.pk)
            if requested > balance:
                raise ValidationError(
                    {
                        "amount": (
                            f"Выплата {requested} ₽ превышает текущий баланс тренера "
                            f"({balance} ₽). Уменьшите сумму."
                        )
                    }
                )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Нормализует знак суммы по типу операции перед сохранением."""
        self._normalize_amount()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} {self.amount} ₽"
