"""
Сервис создания заказов FREESPORT.
Реализует разбивку заказа на мастер + субзаказы по VAT-группам (Story 34-2).
"""

from collections import defaultdict
from decimal import Decimal
from typing import cast

from django.db import transaction
from django.db.models import F
from django.db.models.manager import BaseManager
from rest_framework import serializers

from apps.cart.models import Cart
from apps.orders.models import Order, OrderItem
from apps.products.models import ProductVariant


class OrderCreateService:
    """Создаёт мастер-заказ и N субзаказов по VAT-группам из корзины."""

    def __init__(self, cart, user, validated_data: dict, delivery_cost: Decimal):
        self.cart = cart
        self.user = user
        self.validated_data = validated_data
        self.delivery_cost = delivery_cost

    @transaction.atomic
    def create(self) -> Order:
        user = self.user
        delivery_cost = self.delivery_cost
        validated_data = dict(self.validated_data)

        # Double-submit protection: блокируем строку корзины внутри транзакции.
        # Второй параллельный запрос будет ждать снятия блокировки; после этого
        # увидит пустую корзину (cart.clear() уже вызван) и получит ValidationError.
        cart_manager = cast(BaseManager[Cart], getattr(Cart, "objects"))
        cart = cart_manager.select_for_update().filter(pk=self.cart.pk).first()
        if not cart or not cart.items.exists():
            raise serializers.ValidationError(
                "Корзина пуста или уже используется для создания заказа. " "Обновите корзину и попробуйте снова."
            )

        # discount_amount is server-authoritative; client field removed from input contract.
        # Currently 0: promo system not implemented.
        # Future: replace with PromoCode.calculate(cart, user) or similar server-side logic.
        validated_data.pop("discount_amount", None)
        discount_amount: Decimal = Decimal("0")

        # 1. Сгруппировать позиции корзины по variant.vat_rate
        groups: dict[Decimal | None, list] = defaultdict(list)
        total_items_sum = Decimal("0")

        for ci in cart.items.select_related("variant__product"):
            variant = ci.variant
            product = variant.product if variant else None
            if not variant or not product:
                raise serializers.ValidationError("Некорректный товар в корзине. Обновите корзину и попробуйте снова.")
            raw_vat = getattr(variant, "vat_rate", None)
            key: Decimal | None = Decimal(str(raw_vat)) if raw_vat is not None else None
            groups[key].append(ci)
            # Используем снимок цены из корзины, а не пересчитываем по текущему каталогу.
            total_items_sum += ci.total_price

        # 2. Создать мастер-заказ (delivery_cost и discount_amount только здесь)
        master = Order(
            user=user,
            is_master=True,
            parent_order=None,
            vat_group=None,
            delivery_cost=delivery_cost,
            discount_amount=discount_amount,
            total_amount=total_items_sum + delivery_cost - discount_amount,
            **validated_data,
        )
        master.save()

        # 3. Создать субзаказы + OrderItem для каждой VAT-группы
        variant_updates: list[tuple[int, int]] = []
        order_item_manager = cast(BaseManager[OrderItem], getattr(OrderItem, "objects"))

        for vat_key, items in groups.items():
            group_total = Decimal(sum(ci.total_price for ci in items))
            sub = Order(
                user=user,
                is_master=False,
                parent_order=master,
                vat_group=vat_key,
                delivery_cost=Decimal("0"),
                total_amount=group_total,
                status="pending",
                payment_status="pending",
                customer_name=master.customer_name,
                customer_email=master.customer_email,
                customer_phone=master.customer_phone,
                delivery_address=master.delivery_address,
                delivery_method=master.delivery_method,
                delivery_date=master.delivery_date,
                payment_method=master.payment_method,
                notes=master.notes,
            )
            sub.save()

            sub_items = []
            for ci in items:
                variant = ci.variant
                product = variant.product
                unit_price = ci.price_snapshot
                snapshot = OrderItem.build_snapshot(product, variant)
                sub_items.append(
                    OrderItem(
                        order=sub,
                        product=product,
                        variant=variant,
                        quantity=ci.quantity,
                        unit_price=unit_price,
                        total_price=unit_price * ci.quantity,
                        **snapshot,
                    )
                )
                variant_updates.append((variant.pk, ci.quantity))

            order_item_manager.bulk_create(sub_items)

        # 4. Списать остатки через conditional update — защита от race condition
        # между параллельными checkout'ами: если stock уже забрали, update вернёт 0,
        # бросаем ValidationError, транзакция откатывается целиком.
        variant_manager = cast(BaseManager[ProductVariant], getattr(ProductVariant, "objects"))
        for variant_pk, qty in variant_updates:
            updated = variant_manager.filter(pk=variant_pk, stock_quantity__gte=qty).update(
                stock_quantity=F("stock_quantity") - qty
            )
            if updated == 0:
                variant = variant_manager.filter(pk=variant_pk).only("id", "sku").first()
                sku = getattr(variant, "sku", variant_pk) if variant else variant_pk
                raise serializers.ValidationError(
                    f"Недостаточно товара '{sku}' на складе. "
                    f"Запрошенное количество больше не доступно — возможно, другой покупатель "
                    f"оформил заказ раньше. Обновите корзину и попробуйте снова."
                )

        # 5. Очистить корзину
        cart.clear()

        return master
