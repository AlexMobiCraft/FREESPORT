"""
Unit-тесты для ProductDataProcessor
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.products.models import (
    Brand,
    Brand1CMapping,
    Category,
    ImportSession,
    PriceType,
    Product,
)
from apps.products.services.processor import ProductDataProcessor


@pytest.mark.unit
@pytest.mark.django_db
class TestProductDataProcessor:
    """Тесты процессора данных товаров"""

    @pytest.fixture
    def import_session(self):
        """Фикстура сессии импорта"""
        return ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )

    @pytest.fixture
    def processor(self, import_session):
        """Фикстура процессора"""
        return ProductDataProcessor(session_id=import_session.id)

    @pytest.fixture
    def brand(self):
        """Фикстура бренда"""
        return Brand.objects.create(name="Test Brand", slug="test-brand")

    @pytest.fixture
    def category(self):
        """Фикстура категории"""
        return Category.objects.create(
            name="Test Category", slug="test-category", onec_id="category-uuid"
        )

    def test_create_product_placeholder(self, processor, category):
        """Проверка создания заготовки товара"""
        goods_data = {
            "id": "parent-uuid-123",
            "name": "Base Product",
            "description": "Test description",
            "category_id": "category-uuid",
        }

        product = processor.create_product_placeholder(goods_data)

        assert product is not None
        assert product.parent_onec_id == "parent-uuid-123"
        assert product.name == "Base Product"
        assert product.is_active is False
        assert product.onec_id == "parent-uuid-123"  # onec_id устанавливается сразу
        assert product.sync_status == Product.SyncStatus.PENDING

    def test_enrich_product_from_offer(self, processor, category):
        """Проверка обогащения товара из offer"""
        # Создаем заготовку
        product = Product.objects.create(
            parent_onec_id="parent-uuid",
            name="Placeholder",
            brand=Brand.objects.create(name="Brand", slug="brand"),
            category=category,
            retail_price=Decimal("0.00"),
            is_active=False,
        )

        offer_data = {
            "id": "parent-uuid#sku-uuid-456",
            "name": "Product with Size M",
            "article": "PROD-001-M",
            "characteristics": [
                {"name": "Размер", "value": "M"},
                {"name": "Цвет", "value": "Черный"},
            ],
        }

        result = processor.enrich_product_from_offer(offer_data)

        assert result is True
        product.refresh_from_db()
        assert product.onec_id == "parent-uuid#sku-uuid-456"
        assert product.name == "Product with Size M"
        assert product.sku == "PROD-001-M"
        assert product.is_active is True
        assert "Размер" in product.specifications

    def test_update_product_prices(self, processor, category):
        """Проверка обновления цен товара"""
        # Создаем PriceType
        price_type = PriceType.objects.create(
            onec_id="retail-uuid",
            onec_name="РРЦ",
            product_field="retail_price",
            is_active=True,
        )

        # Создаем товар
        product = Product.objects.create(
            onec_id="product-uuid",
            parent_onec_id="parent-uuid",
            name="Product",
            brand=Brand.objects.create(name="Brand2", slug="brand2"),
            category=category,
            retail_price=Decimal("0.00"),
        )

        price_data = {
            "id": "product-uuid",
            "prices": [
                {"price_type_id": "retail-uuid", "value": Decimal("1000.00")},
            ],
        }

        result = processor.update_product_prices(price_data)

        assert result is True
        product.refresh_from_db()
        assert product.retail_price == Decimal("1000.00")
        assert product.last_sync_at is not None

    def test_federation_price_fallback(self, processor, category):
        """Проверка fallback-логики для federation_price"""
        # Создаем товар с recommended_retail_price
        product = Product.objects.create(
            onec_id="product-uuid",
            parent_onec_id="parent-uuid",
            name="Product",
            brand=Brand.objects.create(name="Brand3", slug="brand3"),
            category=category,
            retail_price=Decimal("1000.00"),
            recommended_retail_price=Decimal("1200.00"),
        )

        price_data = {"id": "product-uuid", "prices": []}

        result = processor.update_product_prices(price_data)

        product.refresh_from_db()
        # Должен быть установлен fallback
        assert product.federation_price == Decimal("1200.00")

    def test_update_product_stock(self, processor, category):
        """Проверка обновления остатков"""
        product = Product.objects.create(
            onec_id="product-uuid",
            parent_onec_id="parent-uuid",
            name="Product",
            brand=Brand.objects.create(name="Brand4", slug="brand4"),
            category=category,
            retail_price=Decimal("1000.00"),
            stock_quantity=0,
        )

        rest_data = {"id": "product-uuid", "quantity": 50}

        result = processor.update_product_stock(rest_data)

        assert result is True
        product.refresh_from_db()
        assert product.stock_quantity == 50
        assert product.sync_status == Product.SyncStatus.COMPLETED

    def test_process_price_types(self, processor):
        """Проверка обработки типов цен"""
        price_types_data = [
            {
                "onec_id": "opt1-uuid",
                "onec_name": "Опт 1",
                "product_field": "opt1_price",
            },
            {
                "onec_id": "trainer-uuid",
                "onec_name": "Тренерская",
                "product_field": "trainer_price",
            },
        ]

        count = processor.process_price_types(price_types_data)

        assert count == 2
        assert PriceType.objects.filter(onec_id="opt1-uuid").exists()
        assert PriceType.objects.filter(onec_id="trainer-uuid").exists()

    def test_determine_brand_with_mapping(self, processor):
        """Проверка _determine_brand() с существующим маппингом"""
        # Создаём master-бренд и маппинг
        master_brand = Brand.objects.create(
            name="Nike", slug="nike", normalized_name="nike"
        )
        Brand1CMapping.objects.create(
            onec_id="1c-nike-001", onec_name="Nike Inc", brand=master_brand
        )

        result_brand = processor._determine_brand(
            brand_id="1c-nike-001", parent_id="product-123"
        )

        assert result_brand == master_brand
        assert processor.stats["brand_fallbacks"] == 0

    def test_determine_brand_without_mapping(self, processor):
        """Проверка _determine_brand() без маппинга (fallback на No Brand)"""
        result_brand = processor._determine_brand(
            brand_id="1c-unknown-999", parent_id="product-456"
        )

        assert result_brand.name == "No Brand"
        assert processor.stats["brand_fallbacks"] == 1

    def test_determine_brand_with_none_brand_id(self, processor):
        """Проверка _determine_brand() с brand_id=None"""
        result_brand = processor._determine_brand(
            brand_id=None, parent_id="product-789"
        )

        assert result_brand.name == "No Brand"
        assert processor.stats["brand_fallbacks"] == 1

    def test_log_brand_mapping_missing(self, processor, caplog):
        """Проверка _log_brand_mapping_missing() логирует WARNING с точным форматом"""
        import logging

        caplog.set_level(logging.WARNING)

        processor._log_brand_mapping_missing(
            brand_id="1c-missing-brand", parent_id="product-999"
        )

        assert processor.stats["brand_fallbacks"] == 1
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Brand1CMapping not found for onec_id=1c-missing-brand" in record.message
        assert "product=product-999" in record.message
        assert f"session={processor.session_id}" in record.message
        assert "using 'No Brand' fallback" in record.message

    def test_increment_brand_fallbacks(self, processor):
        """Проверка _increment_brand_fallbacks() инкрементирует счётчик"""
        assert processor.stats["brand_fallbacks"] == 0

        processor._increment_brand_fallbacks()
        assert processor.stats["brand_fallbacks"] == 1

        processor._increment_brand_fallbacks()
        assert processor.stats["brand_fallbacks"] == 2

    def test_get_no_brand(self, processor):
        """Проверка _get_no_brand() возвращает или создаёт fallback бренд"""
        # Первый вызов создаёт бренд
        brand1 = processor._get_no_brand()
        assert brand1.name == "No Brand"
        assert brand1.slug == "no-brand"
        assert brand1.is_active is True

        # Второй вызов возвращает существующий
        brand2 = processor._get_no_brand()
        assert brand1.pk == brand2.pk

    def test_get_no_brand_idempotent(self, processor):
        """Проверка идемпотентности _get_no_brand()"""
        Brand.objects.create(name="No Brand", slug="no-brand", is_active=True)

        brand = processor._get_no_brand()
        assert brand.name == "No Brand"
        assert Brand.objects.filter(name="No Brand").count() == 1
