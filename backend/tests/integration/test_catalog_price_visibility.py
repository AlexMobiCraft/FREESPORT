"""
Тест-сторож утечки оптовых цен через публичный каталог.

Стори `security-wholesale-price-visibility`, AC7. Сторож формулируется по
всем ключам вида `opt*_price`, а не перечислением трёх имён, — чтобы
`opt4_price` из стори 39.3 попал под проверку автоматически, без правки теста.

Если этот файл начал падать после снятия гейта в `to_representation` —
это не «устаревший тест», а сработавшая защита: оптовая ценовая сетка
снова уходит анонимам (см. `tech-debt.md` п. 18).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.products.models import Brand, Category, Product, ProductVariant
from tests.conftest import get_unique_suffix

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

User = get_user_model()

RETAIL_PRICE = Decimal("1000.00")
OPT1_PRICE = Decimal("900.00")
OPT2_PRICE = Decimal("800.00")
OPT3_PRICE = Decimal("700.00")


def _wholesale_values(payload: dict) -> list[float]:
    """Все значения полей вида opt*_price — включая те, что появятся позже (opt4_price)"""
    return [float(value or 0) for key, value in payload.items() if key.startswith("opt") and key.endswith("_price")]


@pytest.fixture
def product(db):
    """Товар с заполненной оптовой сеткой"""
    suffix = get_unique_suffix()
    category = Category.objects.create(name=f"Кат-{suffix}", slug=f"cat-{suffix}")
    brand = Brand.objects.create(name=f"Бренд-{suffix}", slug=f"brand-{suffix}")
    product = Product.objects.create(
        name=f"Товар-{suffix}",
        slug=f"product-{suffix}",
        category=category,
        brand=brand,
        onec_id=f"1c-{suffix}",
        is_active=True,
    )
    ProductVariant.objects.create(
        product=product,
        sku=f"SKU-{suffix}",
        onec_id=f"var-{suffix}",
        color_name="Чёрный",
        size_value="L",
        retail_price=RETAIL_PRICE,
        opt1_price=OPT1_PRICE,
        opt2_price=OPT2_PRICE,
        opt3_price=OPT3_PRICE,
        rrp=Decimal("1200.00"),
        msrp=Decimal("1300.00"),
        stock_quantity=50,
        is_active=True,
    )
    return product


@pytest.fixture
def api_client():
    return APIClient()


def _make_user(role: str, *, is_verified: bool):
    suffix = get_unique_suffix()
    return User.objects.create_user(
        email=f"{role}-{suffix}@visibility.test",
        password="TestPass123!",
        role=role,
        is_verified=is_verified,
    )


def _list_item(api_client, product) -> dict:
    """Найти товар в ответе списочного endpoint'а"""
    response = api_client.get("/api/v1/products/", {"search": product.name})
    assert response.status_code == 200, response.data
    results = response.data.get("results", response.data)
    items = [item for item in results if item["slug"] == product.slug]
    assert items, f"Товар {product.slug} не найден в ответе каталога"
    return items[0]


class TestWholesalePricesHiddenFromUnauthorized:
    """AC7: анонимы, розница и неверифицированный B2B не видят оптовых цен"""

    def test_anonymous_list_has_no_wholesale_prices(self, api_client, product):
        """Анонимный GET /api/v1/products/ — все opt*_price нулевые"""
        item = _list_item(api_client, product)

        values = _wholesale_values(item)
        assert values, "Ожидались ключи opt*_price в ответе (вариант B: ключи не удаляются)"
        assert all(value == 0 for value in values), f"Утечка оптовых цен анониму: {values}"

    def test_anonymous_detail_has_no_wholesale_prices(self, api_client, product):
        """Анонимный GET /api/v1/products/{slug}/ — все opt*_price нулевые, ключи на месте"""
        response = api_client.get(f"/api/v1/products/{product.slug}/")

        assert response.status_code == 200
        assert "opt1_price" in response.data, "Ключи оптовых полей должны остаться в ответе"
        values = _wholesale_values(response.data)
        assert all(value == 0 for value in values), f"Утечка оптовых цен анониму: {values}"

    def test_anonymous_related_products_have_no_wholesale_prices(self, api_client, product):
        """Вложенный список related_products тоже под гейтом"""
        suffix = get_unique_suffix()
        related = Product.objects.create(
            name=f"Связанный-{suffix}",
            slug=f"related-{suffix}",
            category=product.category,
            brand=product.brand,
            onec_id=f"1c-rel-{suffix}",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=related,
            sku=f"SKU-REL-{suffix}",
            onec_id=f"var-rel-{suffix}",
            retail_price=RETAIL_PRICE,
            opt1_price=OPT1_PRICE,
            stock_quantity=10,
            is_active=True,
        )

        response = api_client.get(f"/api/v1/products/{product.slug}/")

        assert response.status_code == 200
        assert response.data["related_products"], "Ожидался хотя бы один связанный товар"
        for item in response.data["related_products"]:
            values = _wholesale_values(item)
            assert all(value == 0 for value in values), f"Утечка в related_products: {values}"

    def test_retail_user_has_no_wholesale_prices(self, api_client, product):
        """Аутентифицированная розница — те же нули"""
        api_client.force_authenticate(user=_make_user("retail", is_verified=True))

        item = _list_item(api_client, product)

        assert all(value == 0 for value in _wholesale_values(item))

    def test_unverified_wholesale_user_has_no_wholesale_prices(self, api_client, product):
        """Неверифицированный wholesale_level1 — нули и розничная current_price"""
        api_client.force_authenticate(user=_make_user("wholesale_level1", is_verified=False))

        item = _list_item(api_client, product)

        assert all(value == 0 for value in _wholesale_values(item))
        assert float(item["current_price"]) == float(RETAIL_PRICE)

    def test_unverified_b2b_detail_has_no_info_prices(self, api_client, product):
        """AC6: неверифицированный оптовик не видит и РРЦ/МРЦ"""
        api_client.force_authenticate(user=_make_user("wholesale_level1", is_verified=False))

        response = api_client.get(f"/api/v1/products/{product.slug}/")

        assert response.status_code == 200
        assert "rrp" not in response.data
        assert "msrp" not in response.data


class TestWholesalePricesVisibleForVerifiedB2B:
    """AC3: обратная сторона гейта — верифицированный B2B видит сетку целиком"""

    def test_verified_wholesale_user_sees_wholesale_prices(self, api_client, product):
        """Верифицированный wholesale_level1 получает фактические оптовые цены"""
        api_client.force_authenticate(user=_make_user("wholesale_level1", is_verified=True))

        item = _list_item(api_client, product)

        assert float(item["opt1_price"]) == float(OPT1_PRICE)
        assert float(item["opt2_price"]) == float(OPT2_PRICE)
        assert float(item["opt3_price"]) == float(OPT3_PRICE)
        assert float(item["current_price"]) == float(OPT1_PRICE)

    def test_verified_wholesale_level2_sees_full_grid(self, api_client, product):
        """AC3, решение 4: wholesale_level2 видит всю сетку, а не только свой уровень"""
        api_client.force_authenticate(user=_make_user("wholesale_level2", is_verified=True))

        response = api_client.get(f"/api/v1/products/{product.slug}/")

        assert response.status_code == 200
        assert float(response.data["opt1_price"]) == float(OPT1_PRICE)
        assert float(response.data["opt3_price"]) == float(OPT3_PRICE)
        assert float(response.data["current_price"]) == float(OPT2_PRICE)
        assert response.data["rrp"] == 1200.0


class TestUnverifiedB2BCartPrice:
    """AC4: гейт достаёт до корзины через price_snapshot"""

    def test_unverified_b2b_cart_price_is_retail(self, api_client, product):
        """Неверифицированный оптовик кладёт товар — price_snapshot розничный"""
        api_client.force_authenticate(user=_make_user("wholesale_level1", is_verified=False))
        variant = product.variants.first()

        response = api_client.post("/api/v1/cart/items/", {"variant_id": variant.id, "quantity": 2})

        assert response.status_code == 201, response.data
        cart = api_client.get("/api/v1/cart/")
        assert float(cart.data["total_amount"]) == float(RETAIL_PRICE) * 2

    def test_verified_b2b_cart_price_is_wholesale(self, api_client, product):
        """Контрольный кейс: верифицированный оптовик получает оптовую цену"""
        api_client.force_authenticate(user=_make_user("wholesale_level1", is_verified=True))
        variant = product.variants.first()

        response = api_client.post("/api/v1/cart/items/", {"variant_id": variant.id, "quantity": 2})

        assert response.status_code == 201, response.data
        cart = api_client.get("/api/v1/cart/")
        assert float(cart.data["total_amount"]) == float(OPT1_PRICE) * 2
