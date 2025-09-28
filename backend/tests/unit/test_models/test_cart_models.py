"""
Тесты для моделей корзины FREESPORT Platform
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.cart.models import Cart, CartItem
from tests.conftest import (CartFactory, CartItemFactory, ProductFactory,
                            UserFactory)


@pytest.mark.django_db
class TestCartModel:
    """Тесты модели Cart"""

    def test_cart_creation_with_user(self):
        """Тест создания корзины с пользователем"""
        user = UserFactory.create()
        cart = CartFactory.create(user=user)

        assert cart.user == user
        assert cart.session_key == ""
        assert str(cart) == f"Корзина пользователя {user.email}"

    def test_cart_creation_guest(self):
        """Тест создания корзины для гостя"""
        cart = CartFactory.create(user=None, session_key="guest123")

        assert cart.user is None
        assert cart.session_key == "guest123"
        assert "Гостевая корзина guest123" in str(cart)

    def test_cart_total_items(self):
        """Тест подсчета общего количества товаров в корзине"""
        cart = CartFactory.create()
        CartItemFactory.create(cart=cart, quantity=2)
        CartItemFactory.create(cart=cart, quantity=3)

        assert cart.total_items == 5

    def test_cart_total_amount(self):
        """Тест подсчета общей стоимости корзины"""
        user = UserFactory.create(role="retail")
        cart = CartFactory.create(user=user)

        # Создаем товары с известными ценами
        product1 = ProductFactory.create(retail_price=Decimal("1000.00"))
        product2 = ProductFactory.create(retail_price=Decimal("500.00"))

        CartItemFactory.create(cart=cart, product=product1, quantity=2)
        CartItemFactory.create(cart=cart, product=product2, quantity=1)

        expected_total = Decimal("1000.00") * 2 + Decimal("500.00") * 1
        assert cart.total_amount == expected_total

    def test_cart_total_amount_different_user_roles(self):
        """Тест стоимости корзины для разных ролей пользователей"""
        # Оптовый пользователь
        wholesale_user = UserFactory.create(role="wholesale_level1")
        cart = CartFactory.create(user=wholesale_user)

        product = ProductFactory.create(
            retail_price=Decimal("1000.00"), opt1_price=Decimal("900.00")
        )
        CartItemFactory.create(cart=cart, product=product, quantity=1)

        # Должна использоваться оптовая цена
        assert cart.total_amount == Decimal("900.00")

    def test_cart_clear(self):
        """Тест очистки корзины"""
        cart = CartFactory.create()
        CartItemFactory.create(cart=cart)
        CartItemFactory.create(cart=cart)

        assert cart.items.count() == 2

        cart.clear()
        assert cart.items.count() == 0

    def test_cart_meta_configuration(self):
        """Тест настроек Meta класса Cart"""
        assert Cart._meta.verbose_name == "Корзина"
        assert Cart._meta.verbose_name_plural == "Корзины"
        assert Cart._meta.db_table == "carts"


@pytest.mark.django_db
class TestCartItemModel:
    """Тесты модели CartItem"""

    def test_cart_item_creation(self):
        """Тест создания элемента корзины"""
        cart = CartFactory.create()
        product = ProductFactory.create(name="Тестовый товар")
        item = CartItemFactory.create(cart=cart, product=product, quantity=2)

        assert item.cart == cart
        assert item.product == product
        assert item.quantity == 2
        assert str(item) == "Тестовый товар x2 в корзине"

    def test_cart_item_total_price(self):
        """Тест подсчета стоимости элемента корзины"""
        user = UserFactory.create(role="retail")
        cart = CartFactory.create(user=user)
        product = ProductFactory.create(retail_price=Decimal("1000.00"))
        item = CartItemFactory.create(cart=cart, product=product, quantity=3)

        assert item.total_price == Decimal("3000.00")

    def test_cart_item_total_price_with_user_role(self):
        """Тест стоимости элемента для разных ролей пользователей"""
        trainer_user = UserFactory.create(role="trainer")
        cart = CartFactory.create(user=trainer_user)
        product = ProductFactory.create(
            retail_price=Decimal("1000.00"), trainer_price=Decimal("850.00")
        )
        item = CartItemFactory.create(cart=cart, product=product, quantity=2)

        # Должна использоваться цена тренера
        assert item.total_price == Decimal("1700.00")

    def test_cart_item_unique_constraint(self):
        """Тест уникальности товара в корзине"""
        cart = CartFactory.create()
        product = ProductFactory.create()

        CartItemFactory.create(cart=cart, product=product)

        # Попытка добавить тот же товар в ту же корзину должна вызвать ошибку
        with pytest.raises(ValidationError):
            CartItemFactory.create(cart=cart, product=product)

    def test_cart_item_validation_inactive_product(self):
        """Тест валидации неактивного товара"""
        inactive_product = ProductFactory.create(is_active=False)
        cart = CartFactory.create()

        with pytest.raises(ValidationError):
            item = CartItemFactory.build(
                cart=cart, product=inactive_product, quantity=1
            )
            item.full_clean()

    def test_cart_item_validation_insufficient_stock(self):
        """Тест валидации недостаточного количества на складе"""
        product = ProductFactory.create(stock_quantity=5)
        cart = CartFactory.create()

        with pytest.raises(ValidationError):
            item = CartItemFactory.build(cart=cart, product=product, quantity=10)
            item.full_clean()

    def test_cart_item_validation_min_order_quantity(self):
        """Тест валидации минимального количества заказа"""
        product = ProductFactory.create(min_order_quantity=5)
        cart = CartFactory.create()

        with pytest.raises(ValidationError):
            item = CartItemFactory.build(cart=cart, product=product, quantity=3)
            item.full_clean()

    def test_cart_item_validation_positive_quantity(self):
        """Тест валидации положительного количества"""
        cart = CartFactory.create()
        product = ProductFactory.create()

        with pytest.raises(ValidationError):
            item = CartItemFactory.build(cart=cart, product=product, quantity=0)
            item.full_clean()

    def test_cart_item_updates_cart_timestamp(self):
        """Тест обновления времени модификации корзины при добавлении товара"""
        cart = CartFactory.create()
        original_updated_at = cart.updated_at

        # Небольшая задержка
        import time

        time.sleep(0.01)

        CartItemFactory.create(cart=cart)
        cart.refresh_from_db()

        assert cart.updated_at > original_updated_at

    def test_cart_item_meta_configuration(self):
        """Тест настроек Meta класса CartItem"""
        assert CartItem._meta.verbose_name == "Элемент корзины"
        assert CartItem._meta.verbose_name_plural == "Элементы корзины"
        assert CartItem._meta.db_table == "cart_items"
