"""
Отладочный тест для проблемы с очисткой корзины
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.cart.models import Cart, CartItem
from tests.conftest import CartFactory, CartItemFactory, ProductFactory, UserFactory

@pytest.mark.django_db
class TestDebugCart:
    def test_cart_clear_debug(self):
        print("\n--- Starting test_cart_clear_debug ---")

        # Переопределяем методы для отладки
        def new_clean(self):
            print(f"[DEBUG] Cleaning CartItem {self.id} for product {self.product.id} (qty: {self.quantity})")
            # ... исходная логика clean ...
            if not self.product.is_active:
                raise ValidationError("Товар неактивен")
            if self.quantity > self.product.available_quantity:
                 raise ValidationError(f"Недостаточно товара на складе. Доступно: {self.product.available_quantity}")
            if self.quantity < self.product.min_order_quantity:
                raise ValidationError(f"Минимальное количество заказа: {self.product.min_order_quantity}")

        def new_save(self, *args, **kwargs):
            print(f"[DEBUG] Saving CartItem {self.id or 'new'} for product {self.product.id} (qty: {self.quantity})")
            self.full_clean()
            super(CartItem, self).save(*args, **kwargs)
            self.cart.save(update_fields=["updated_at"])

        def new_delete(self, *args, **kwargs):
            print(f"[DEBUG] Deleting CartItem {self.id} for product {self.product.id} (qty: {self.quantity})")
            super(CartItem, self).delete(*args, **kwargs)

        CartItem.clean = new_clean
        CartItem.save = new_save
        CartItem.delete = new_delete

        # Логика теста
        product = ProductFactory.create(stock_quantity=10)
        print(f"Product {product.id} created with stock_quantity={product.stock_quantity}")

        cart = CartFactory.create()
        print(f"Cart {cart.id} created.")

        print("Creating CartItem 1...")
        item1 = CartItemFactory.create(cart=cart, product=product, quantity=2)
        product.refresh_from_db()
        print(f"CartItem 1 ({item1.id}) created. Product stock: {product.stock_quantity}, reserved: {product.reserved_quantity}")

        print("Creating CartItem 2...")
        # Создадим другой продукт, чтобы избежать ошибки unique_together
        product2 = ProductFactory.create(stock_quantity=5)
        print(f"Product {product2.id} created with stock_quantity={product2.stock_quantity}")
        item2 = CartItemFactory.create(cart=cart, product=product2, quantity=3)
        product2.refresh_from_db()
        print(f"CartItem 2 ({item2.id}) created. Product2 stock: {product2.stock_quantity}, reserved: {product2.reserved_quantity}")

        assert cart.items.count() == 2
        print("\n--- Calling cart.clear() ---")
        cart.clear()
        print("--- cart.clear() finished ---")

        assert cart.items.count() == 0
        print("Test finished successfully.")
