"""
Тесты для ProductViewSet.visible_categories action и аннотации in_stock_count
в CategoryTreeViewSet (bugfix: сортировка и скрытие пустых категорий в каталоге).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.factories import CategoryFactory, ProductFactory, ProductVariantFactory
from apps.products.models import Brand, Category


@pytest.mark.django_db
class TestVisibleCategoriesAction:
    """GET /products/visible-categories/"""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def url(self):
        return reverse("products:product-visible-categories")

    @pytest.fixture
    def brand_nike(self):
        return Brand.objects.create(name="Nike", slug="nike")

    @pytest.fixture
    def brand_adidas(self):
        return Brand.objects.create(name="Adidas", slug="adidas")

    @pytest.fixture
    def cat_shoes(self):
        return CategoryFactory(name="Обувь", slug="shoes")

    @pytest.fixture
    def cat_clothing(self):
        return CategoryFactory(name="Одежда", slug="clothing")

    @pytest.fixture
    def cat_uncategorized(self):
        return CategoryFactory(name="Без категории", slug="uncategorized")

    def test_returns_category_ids_for_in_stock_products(self, client, url, cat_shoes, cat_clothing):
        """Возвращает категории с товарами в наличии."""
        p = ProductFactory(category=cat_shoes, create_variant=False)
        ProductVariantFactory(product=p, stock_quantity=5, retail_price=Decimal("1000"))
        # Товар без остатка
        p2 = ProductFactory(category=cat_clothing, create_variant=False)
        ProductVariantFactory(product=p2, stock_quantity=0, retail_price=Decimal("500"))

        resp = client.get(url, {"in_stock": "true"})

        assert resp.status_code == status.HTTP_200_OK
        ids = set(resp.data["category_ids"])
        assert cat_shoes.id in ids
        assert cat_clothing.id not in ids

    def test_ignores_category_id_param(self, client, url, cat_shoes, cat_clothing):
        """category_id не должен сужать результат."""
        p1 = ProductFactory(category=cat_shoes, create_variant=False)
        ProductVariantFactory(product=p1, stock_quantity=3, retail_price=Decimal("1000"))
        p2 = ProductFactory(category=cat_clothing, create_variant=False)
        ProductVariantFactory(product=p2, stock_quantity=2, retail_price=Decimal("800"))

        # Передаём category_id=cat_shoes.id — он должен быть проигнорирован
        resp = client.get(url, {"category_id": cat_shoes.id})

        assert resp.status_code == status.HTTP_200_OK
        ids = set(resp.data["category_ids"])
        # Обе категории должны быть видны несмотря на category_id
        assert cat_shoes.id in ids
        assert cat_clothing.id in ids

    def test_filter_by_brand(self, client, url, cat_shoes, cat_clothing, brand_nike, brand_adidas):
        """Фильтрация по бренду возвращает только нужные категории."""
        p_nike = ProductFactory(category=cat_shoes, brand=brand_nike, create_variant=False)
        ProductVariantFactory(product=p_nike, stock_quantity=1, retail_price=Decimal("2000"))
        p_adidas = ProductFactory(category=cat_clothing, brand=brand_adidas, create_variant=False)
        ProductVariantFactory(product=p_adidas, stock_quantity=1, retail_price=Decimal("1500"))

        resp = client.get(url, {"brand": str(brand_nike.id)})

        assert resp.status_code == status.HTTP_200_OK
        ids = set(resp.data["category_ids"])
        assert cat_shoes.id in ids
        assert cat_clothing.id not in ids

    def test_includes_ancestor_ids(self, client, url):
        """Возвращает ID предков категорий с товарами."""
        parent = CategoryFactory(name="Спорт", slug="sport", parent=None)
        child = CategoryFactory(name="Лыжи", slug="skiing", parent=parent)

        p = ProductFactory(category=child, create_variant=False)
        ProductVariantFactory(product=p, stock_quantity=2, retail_price=Decimal("5000"))

        resp = client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        ids = set(resp.data["category_ids"])
        assert child.id in ids
        assert parent.id in ids  # предок должен быть включён

    def test_empty_result_when_no_matching_products(self, client, url, cat_uncategorized):
        """Возвращает пустой список если нет товаров по фильтру."""
        p = ProductFactory(category=cat_uncategorized, create_variant=False)
        ProductVariantFactory(product=p, stock_quantity=0, retail_price=Decimal("100"))

        resp = client.get(url, {"in_stock": "true"})

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["category_ids"] == []

    def test_filter_by_price_range(self, client, url, cat_shoes, cat_clothing):
        """Фильтрация по диапазону цен."""
        p_cheap = ProductFactory(category=cat_shoes, create_variant=False)
        ProductVariantFactory(product=p_cheap, stock_quantity=1, retail_price=Decimal("500"))
        p_expensive = ProductFactory(category=cat_clothing, create_variant=False)
        ProductVariantFactory(product=p_expensive, stock_quantity=1, retail_price=Decimal("10000"))

        resp = client.get(url, {"min_price": "1000", "max_price": "15000"})

        assert resp.status_code == status.HTTP_200_OK
        ids = set(resp.data["category_ids"])
        assert cat_clothing.id in ids
        assert cat_shoes.id not in ids


@pytest.mark.django_db
class TestCategoryTreeInStockCount:
    """in_stock_count в CategoryTreeViewSet"""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def url(self):
        return reverse("products:category-tree-list")

    def test_in_stock_count_field_present(self, client, url):
        """Поле in_stock_count присутствует в ответе."""
        sport = CategoryFactory(name="СПОРТ", slug="sport-root", onec_id="sport-root", parent=None)
        cat = CategoryFactory(name="Тест", parent=sport)
        p = ProductFactory(category=cat, create_variant=False)
        ProductVariantFactory(product=p, stock_quantity=3, retail_price=Decimal("1000"))

        resp = client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        category_data = next((c for c in results if c["id"] == cat.id), None)
        assert category_data is not None
        assert "in_stock_count" in category_data

    def test_in_stock_count_excludes_zero_stock(self, client, url):
        """in_stock_count не считает товары с нулевым остатком."""
        sport = CategoryFactory(name="СПОРТ", slug="sport-root", onec_id="sport-root", parent=None)
        cat = CategoryFactory(name="Склад", parent=sport)
        p_in = ProductFactory(category=cat, create_variant=False)
        ProductVariantFactory(product=p_in, stock_quantity=2, retail_price=Decimal("1000"))
        p_out = ProductFactory(category=cat, create_variant=False)
        ProductVariantFactory(product=p_out, stock_quantity=0, retail_price=Decimal("900"))

        resp = client.get(url)

        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        category_data = next((c for c in results if c["id"] == cat.id), None)
        assert category_data is not None
        assert category_data["in_stock_count"] == 1
        assert category_data["products_count"] == 2

    def test_public_tree_returns_sport_children_only(self, client, url):
        """Публичное дерево отдаёт детей СПОРТ и скрывает тех/fallback категории."""
        sport = CategoryFactory(name="СПОРТ", slug="sport-root", onec_id="sport-root", parent=None)
        football = CategoryFactory(name="Футбол", slug="football-public", parent=sport)
        balls = CategoryFactory(name="Мячи", slug="balls-public", parent=football)
        CategoryFactory(name="Категория unknown-uuid", slug="category-unknown-uuid", parent=None, is_active=True)
        CategoryFactory(name="Без категории", slug="uncategorized", parent=sport, is_active=True)
        CategoryFactory(
            name="Техническая категория: неразрешенные ссылки 1С",
            slug="onec-unresolved-category",
            parent=sport,
            is_active=False,
        )

        resp = client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        names = [item["name"] for item in results]
        assert names == ["Футбол"]
        assert results[0]["id"] == football.id
        assert results[0]["children"][0]["id"] == balls.id
