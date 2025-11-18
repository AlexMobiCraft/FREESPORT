"""
Простые интеграционные тесты для маркетинговых флагов (Story 11.0)
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from apps.products.models import Product, Brand, Category
from apps.products.filters import ProductFilter
from apps.products.serializers import ProductListSerializer


@pytest.mark.django_db
class TestBadgesIntegration:
    """Простые интеграционные тесты для проверки работоспособности бейджей"""

    @pytest.fixture
    def brand(self):
        return Brand.objects.create(name="Test Brand", slug="test-brand")

    @pytest.fixture
    def category(self):
        return Category.objects.create(name="Test Category", slug="test-category")

    def test_filter_by_is_hit(self, brand, category):
        """Тест: фильтр по is_hit работает"""
        # Создаём хит и обычный товар
        hit = Product.objects.create(
            name="Hit",
            slug="hit",
            sku="HIT",
            brand=brand,
            category=category,
            retail_price=Decimal("100"),
            is_hit=True,
        )
        regular = Product.objects.create(
            name="Regular",
            slug="regular",
            sku="REG",
            brand=brand,
            category=category,
            retail_price=Decimal("100"),
        )

        # Фильтр должен вернуть только хит
        filterset = ProductFilter({"is_hit": True}, queryset=Product.objects.all())
        assert filterset.qs.count() == 1
        assert filterset.qs.first() == hit

    def test_serializer_includes_badge_fields(self, brand, category):
        """Тест: сериализатор включает поля бейджей"""
        product = Product.objects.create(
            name="Product",
            slug="product",
            sku="PROD",
            brand=brand,
            category=category,
            retail_price=Decimal("100"),
            is_hit=True,
            discount_percent=25,
        )

        serializer = ProductListSerializer(product)
        data = serializer.data

        assert "is_hit" in data
        assert "is_new" in data
        assert "discount_percent" in data
        assert data["is_hit"] is True
        assert data["discount_percent"] == 25

    def test_multiple_filters_combined(self, brand, category):
        """Тест: комбинация фильтров работает"""
        # Товар с двумя флагами
        combo = Product.objects.create(
            name="Combo",
            slug="combo",
            sku="COMBO",
            brand=brand,
            category=category,
            retail_price=Decimal("100"),
            is_hit=True,
            is_sale=True,
        )
        # Товар с одним флагом
        hit_only = Product.objects.create(
            name="Hit",
            slug="hit",
            sku="HIT",
            brand=brand,
            category=category,
            retail_price=Decimal("100"),
            is_hit=True,
        )

        # Фильтр по двум флагам
        filterset = ProductFilter(
            {"is_hit": True, "is_sale": True}, queryset=Product.objects.all()
        )
        assert filterset.qs.count() == 1
        assert filterset.qs.first() == combo
