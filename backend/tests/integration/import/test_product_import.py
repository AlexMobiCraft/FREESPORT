"""
Интеграционные тесты импорта товаров (Story 13.4)

Тестирует:
- Поиск бренда через Brand1CMapping
- Fallback на "No Brand" при отсутствии маппинга
- Сохранение и защиту Product.onec_brand_id
- Логирование и статистику brand_fallbacks
- CLI отчёты
"""

from __future__ import annotations

import logging
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.products.models import Brand, Brand1CMapping, Category, ImportSession, Product
from apps.products.services.processor import ProductDataProcessor


@pytest.mark.integration
@pytest.mark.django_db
class TestProductImportBrandMapping:
    """Интеграционные тесты импорта товаров с Brand1CMapping"""

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
    def category(self):
        """Фикстура категории"""
        return Category.objects.create(
            name="Test Category",
            slug="test-category",
            onec_id="category-uuid-123",
            is_active=True,
        )

    @pytest.fixture
    def master_brand(self):
        """Фикстура master-бренда"""
        return Brand.objects.create(
            name="Nike",
            slug="nike",
            normalized_name="nike",
            is_active=True,
        )

    @pytest.fixture
    def brand_mapping(self, master_brand):
        """Фикстура Brand1CMapping"""
        return Brand1CMapping.objects.create(
            onec_id="1c-nike-001",
            onec_name="Nike Inc",
            brand=master_brand,
        )

    def test_create_product_placeholder_uses_brand_mapping(
        self, processor, category, master_brand, brand_mapping
    ):
        """
        AC1: Метод create_product_placeholder() использует Brand1CMapping
        для поиска master-бренда
        """
        # ARRANGE
        goods_data = {
            "id": "product-uuid-001",
            "name": "Nike Football",
            "description": "Test product",
            "category_id": category.onec_id,
            "brand_id": "1c-nike-001",  # Ссылка на маппинг
        }

        # ACT
        product = processor.create_product_placeholder(goods_data)

        # ASSERT
        assert product is not None
        assert product.brand == master_brand  # Связан с master-брендом
        assert product.onec_brand_id == "1c-nike-001"  # Сохранён исходный ID
        assert processor.stats["brand_fallbacks"] == 0  # Нет fallback
        assert processor.stats["created"] == 1

    def test_create_product_placeholder_fallbacks_when_mapping_missing(
        self, processor, category, caplog
    ):
        """
        AC4: Если маппинг не найден — создаётся "No Brand" и
        инкрементируется stats["brand_fallbacks"]
        AC6: WARNING логируется с точным форматом
        """
        # ARRANGE
        caplog.set_level(logging.WARNING)
        goods_data = {
            "id": "product-uuid-002",
            "name": "Unknown Brand Product",
            "description": "Test product",
            "category_id": category.onec_id,
            "brand_id": "1c-unknown-999",  # Маппинг отсутствует
        }

        # ACT
        product = processor.create_product_placeholder(goods_data)

        # ASSERT
        assert product is not None
        assert product.brand.name == "No Brand"  # Fallback бренд
        assert product.onec_brand_id == "1c-unknown-999"  # Сохранён исходный ID
        assert processor.stats["brand_fallbacks"] == 1  # Инкрементирован счётчик

        # Проверка логирования
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Brand1CMapping not found for onec_id=1c-unknown-999" in record.message
        assert "product=product-uuid-002" in record.message
        assert f"session={processor.session_id}" in record.message
        assert "using 'No Brand' fallback" in record.message

    def test_create_product_placeholder_sets_onec_brand_id(
        self, processor, category, master_brand, brand_mapping
    ):
        """
        AC5: Product.onec_brand_id сохраняется из CommerceML при создании
        """
        # ARRANGE
        goods_data = {
            "id": "product-uuid-003",
            "name": "Nike Sneakers",
            "category_id": category.onec_id,
            "brand_id": "1c-nike-001",
        }

        # ACT
        product = processor.create_product_placeholder(goods_data)

        # ASSERT
        assert product is not None
        assert product.onec_brand_id == "1c-nike-001"
        assert product.brand == master_brand

    def test_reimport_updates_brand_without_overwriting_onec_brand_id(
        self, processor, category, master_brand
    ):
        """
        AC2, AC3: При повторном импорте обновляется product.brand,
        но onec_brand_id не перезаписывается пустыми значениями
        """
        # ARRANGE - создаём товар с "No Brand" (маппинг отсутствовал)
        no_brand = Brand.objects.create(
            name="No Brand", slug="no-brand", is_active=True
        )
        product = Product.objects.create(
            onec_id="product-uuid-004",
            parent_onec_id="product-uuid-004",
            onec_brand_id="1c-nike-002",  # Сохранён исходный ID
            name="Product Placeholder",
            slug="product-placeholder-004",
            brand=no_brand,
            category=category,
            retail_price=Decimal("0.00"),
            is_active=False,
        )

        # Создаём маппинг после первого импорта
        Brand1CMapping.objects.create(
            onec_id="1c-nike-002",
            onec_name="Nike Corp",
            brand=master_brand,
        )

        goods_data = {
            "id": "product-uuid-004",
            "name": "Updated Product",
            "category_id": category.onec_id,
            "brand_id": "1c-nike-002",  # Теперь маппинг существует
        }

        # ACT - повторный импорт
        updated_product = processor.create_product_placeholder(goods_data)

        # ASSERT
        assert updated_product.pk == product.pk  # Тот же товар
        assert updated_product.brand == master_brand  # Обновлён на master-бренд
        assert updated_product.onec_brand_id == "1c-nike-002"  # НЕ перезаписан
        assert processor.stats["updated"] == 1
        assert processor.stats["brand_fallbacks"] == 0

    def test_reimport_with_empty_brand_id(self, processor, category, master_brand):
        """
        Edge case: Повторный импорт с brand_id=None не стирает onec_brand_id
        """
        # ARRANGE - товар с существующим onec_brand_id
        product = Product.objects.create(
            onec_id="product-uuid-005",
            parent_onec_id="product-uuid-005",
            onec_brand_id="1c-original-brand",  # Исходный ID
            name="Product",
            slug="product-005",
            brand=master_brand,
            category=category,
            retail_price=Decimal("0.00"),
            is_active=False,
        )

        goods_data = {
            "id": "product-uuid-005",
            "name": "Updated Product",
            "category_id": category.onec_id,
            # brand_id отсутствует (None)
        }

        # ACT
        updated_product = processor.create_product_placeholder(goods_data)

        # ASSERT
        assert updated_product.pk == product.pk
        assert updated_product.onec_brand_id == "1c-original-brand"  # НЕ стёрт
        assert processor.stats["brand_fallbacks"] == 1  # Fallback из-за None

    def test_reimport_with_different_brand_id(self, processor, category, master_brand):
        """
        Edge case: Повторный импорт с изменённым brand_id обновляет onec_brand_id
        """
        # ARRANGE
        Brand1CMapping.objects.create(
            onec_id="1c-brand-old", onec_name="Old Brand", brand=master_brand
        )
        new_brand = Brand.objects.create(
            name="Adidas", slug="adidas", normalized_name="adidas", is_active=True
        )
        Brand1CMapping.objects.create(
            onec_id="1c-brand-new", onec_name="New Brand", brand=new_brand
        )

        product = Product.objects.create(
            onec_id="product-uuid-006",
            parent_onec_id="product-uuid-006",
            onec_brand_id="1c-brand-old",
            name="Product",
            slug="product-006",
            brand=master_brand,
            category=category,
            retail_price=Decimal("0.00"),
            is_active=False,
        )

        goods_data = {
            "id": "product-uuid-006",
            "name": "Updated Product",
            "category_id": category.onec_id,
            "brand_id": "1c-brand-new",  # Изменённый brand_id
        }

        # ACT
        updated_product = processor.create_product_placeholder(goods_data)

        # ASSERT
        assert updated_product.pk == product.pk
        assert updated_product.brand == new_brand  # Обновлён бренд
        assert updated_product.onec_brand_id == "1c-brand-new"  # Обновлён ID

    def test_product_without_brand_id_in_xml(self, processor, category):
        """
        Error handling: Товар без brand_id в XML получает "No Brand"
        """
        # ARRANGE
        goods_data = {
            "id": "product-uuid-007",
            "name": "Product Without Brand",
            "category_id": category.onec_id,
            # brand_id отсутствует
        }

        # ACT
        product = processor.create_product_placeholder(goods_data)

        # ASSERT
        assert product is not None
        assert product.brand.name == "No Brand"
        assert product.onec_brand_id is None
        assert processor.stats["brand_fallbacks"] == 1

    def test_finalize_session_saves_brand_fallbacks(
        self, processor, category, import_session
    ):
        """
        AC7: finalize_session() сохраняет brand_fallbacks в report_details
        """
        # ARRANGE - создаём несколько товаров с fallback
        for i in range(3):
            goods_data = {
                "id": f"product-uuid-{i}",
                "name": f"Product {i}",
                "category_id": category.onec_id,
                "brand_id": f"1c-unknown-{i}",  # Маппинг отсутствует
            }
            processor.create_product_placeholder(goods_data)

        # ACT
        processor.finalize_session(status=ImportSession.ImportStatus.COMPLETED)

        # ASSERT
        import_session.refresh_from_db()
        assert import_session.status == ImportSession.ImportStatus.COMPLETED
        assert import_session.report_details["brand_fallbacks"] == 3
        assert import_session.report_details["created"] == 3

    def test_logging_format_for_missing_mapping(self, processor, category, caplog):
        """
        AC6: Точный формат WARNING для отсутствующего маппинга
        """
        # ARRANGE
        caplog.set_level(logging.WARNING)
        goods_data = {
            "id": "product-uuid-008",
            "name": "Test Product",
            "category_id": category.onec_id,
            "brand_id": "1c-test-brand",
        }

        # ACT
        processor.create_product_placeholder(goods_data)

        # ASSERT - проверка точного формата логирования
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert record.name == "apps.products.services.processor"
        # Проверяем формат через message (после форматирования)
        expected_parts = [
            "Brand1CMapping not found for onec_id=1c-test-brand",
            "product=product-uuid-008",
            f"session={processor.session_id}",
            "using 'No Brand' fallback",
        ]
        for part in expected_parts:
            assert part in record.message
