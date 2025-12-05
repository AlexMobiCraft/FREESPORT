"""
Integration tests for Story 14.4: Link Attributes to Products & Variants

Tests attribute linking during import process:
- goods.xml → Product attributes (via onec_id mapping)
- offers.xml → ProductVariant attributes (via normalized name/value)
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.test import TestCase

from apps.products.models import (
    Attribute,
    Attribute1CMapping,
    AttributeValue,
    AttributeValue1CMapping,
    Brand,
    Category,
    ImportSession,
    Product,
    ProductVariant,
)
from apps.products.services.parser import GoodsData, OfferData, PropertyValueData
from apps.products.services.processor import ProductDataProcessor
from apps.products.services.variant_import import VariantImportProcessor
from tests.conftest import get_unique_suffix


@pytest.mark.integration
@pytest.mark.django_db
class TestProductAttributeLinking(TestCase):
    """Integration tests for linking attributes to Product via goods.xml"""

    def setUp(self) -> None:
        """Set up test data"""
        super().setUp()
        self.suffix = get_unique_suffix()

        # Create import session
        self.session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )

        # Create processor
        self.processor = ProductDataProcessor(
            session_id=self.session.id,
            skip_validation=True,
        )

        # Create test Brand and Category
        self.brand = Brand.objects.create(
            name=f"Test Brand {self.suffix}",
            slug=f"test-brand-{self.suffix}",
            is_active=True,
        )

        self.category = Category.objects.create(
            name=f"Test Category {self.suffix}",
            slug=f"test-category-{self.suffix}",
            is_active=True,
        )

        # Create test Attribute and AttributeValue with 1C mappings
        self.attribute = Attribute.objects.create(
            name="Цвет",
            slug=f"color-{self.suffix}",
            is_active=True,
        )

        self.attribute_value = AttributeValue.objects.create(
            attribute=self.attribute,
            value="Красный",
            slug=f"red-{self.suffix}",
        )

        # Create 1C mappings
        self.attr_guid = str(uuid.uuid4())
        self.value_guid = str(uuid.uuid4())

        Attribute1CMapping.objects.create(
            attribute=self.attribute,
            onec_id=self.attr_guid,
            onec_name="Цвет",
            source="goods",
        )

        AttributeValue1CMapping.objects.create(
            attribute_value=self.attribute_value,
            onec_id=self.value_guid,
            onec_value="Красный",
            source="goods",
        )

    def test_link_attributes_to_product_via_onec_mapping(self) -> None:
        """Test linking attributes via onec_id mapping from goods.xml"""
        # GIVEN: goods_data with property_values
        product_guid = str(uuid.uuid4())
        goods_data: GoodsData = {
            "id": product_guid,
            "name": f"Test Product {self.suffix}",
            "description": "Test description",
            "category_id": self.category.onec_id or "",
            "property_values": [
                {
                    "property_id": self.attr_guid,
                    "value_id": self.value_guid,
                }
            ],
        }

        # WHEN: create product placeholder
        product = self.processor.create_product_placeholder(goods_data)

        # THEN: product should be created with linked attributes
        assert product is not None
        assert product.attributes.count() == 1
        linked_attr_value = product.attributes.first()
        assert linked_attr_value == self.attribute_value
        assert self.processor.stats["attributes_linked"] == 1
        assert self.processor.stats["attributes_missing_mapping"] == 0

    def test_skip_empty_guid_values(self) -> None:
        """Test skipping empty GUID values (00000000-0000-0000-0000-000000000000)"""
        # GIVEN: goods_data with empty GUID value
        product_guid = str(uuid.uuid4())
        empty_guid = "00000000-0000-0000-0000-000000000000"
        goods_data: GoodsData = {
            "id": product_guid,
            "name": f"Test Product {self.suffix}",
            "property_values": [
                {
                    "property_id": self.attr_guid,
                    "value_id": empty_guid,  # Empty GUID should be skipped
                }
            ],
        }

        # WHEN: create product placeholder
        product = self.processor.create_product_placeholder(goods_data)

        # THEN: product should be created WITHOUT linked attributes
        assert product is not None
        assert product.attributes.count() == 0
        assert self.processor.stats["attributes_linked"] == 0

    def test_link_inactive_attribute_to_product(self) -> None:
        """
        Test linking INACTIVE attributes to Product (Variant C - no filtering).
        Import layer links ALL attributes regardless of is_active status.
        """
        # GIVEN: Inactive attribute
        self.attribute.is_active = False
        self.attribute.save()

        product_guid = str(uuid.uuid4())
        goods_data: GoodsData = {
            "id": product_guid,
            "name": f"Test Product {self.suffix}",
            "property_values": [
                {
                    "property_id": self.attr_guid,
                    "value_id": self.value_guid,
                }
            ],
        }

        # WHEN: create product placeholder
        product = self.processor.create_product_placeholder(goods_data)

        # THEN: inactive attribute SHOULD be linked (Variant C)
        assert product is not None
        assert product.attributes.count() == 1
        linked_attr_value = product.attributes.first()
        assert linked_attr_value == self.attribute_value
        assert linked_attr_value.attribute.is_active is False

    def test_missing_attribute_logging(self) -> None:
        """Test logging warnings for missing attribute mappings"""
        # GIVEN: goods_data with non-existent value_id
        product_guid = str(uuid.uuid4())
        non_existent_value_guid = str(uuid.uuid4())
        goods_data: GoodsData = {
            "id": product_guid,
            "name": f"Test Product {self.suffix}",
            "property_values": [
                {
                    "property_id": self.attr_guid,
                    "value_id": non_existent_value_guid,  # Does not exist
                }
            ],
        }

        # WHEN: create product placeholder
        product = self.processor.create_product_placeholder(goods_data)

        # THEN: product created but attribute not linked
        assert product is not None
        assert product.attributes.count() == 0
        assert self.processor.stats["attributes_missing_mapping"] == 1

    def test_attribute_linking_statistics(self) -> None:
        """Test stats tracking for attributes_linked and attributes_missing_mapping"""
        # GIVEN: Multiple property values (some valid, some invalid)
        product_guid = str(uuid.uuid4())
        invalid_guid = str(uuid.uuid4())

        # Create second valid attribute
        attr2 = Attribute.objects.create(
            name="Размер",
            slug=f"size-{self.suffix}",
            is_active=True,
        )
        attr_value2 = AttributeValue.objects.create(
            attribute=attr2,
            value="M",
            slug=f"m-{self.suffix}",
        )
        attr2_guid = str(uuid.uuid4())
        value2_guid = str(uuid.uuid4())
        Attribute1CMapping.objects.create(
            attribute=attr2,
            onec_id=attr2_guid,
            onec_name="Размер",
            source="goods",
        )
        AttributeValue1CMapping.objects.create(
            attribute_value=attr_value2,
            onec_id=value2_guid,
            onec_value="M",
            source="goods",
        )

        goods_data: GoodsData = {
            "id": product_guid,
            "name": f"Test Product {self.suffix}",
            "property_values": [
                {"property_id": self.attr_guid, "value_id": self.value_guid},  # Valid
                {"property_id": attr2_guid, "value_id": value2_guid},  # Valid
                {"property_id": self.attr_guid, "value_id": invalid_guid},  # Invalid
            ],
        }

        # WHEN: create product placeholder
        product = self.processor.create_product_placeholder(goods_data)

        # THEN: stats should reflect 2 linked and 1 missing
        assert product is not None
        assert product.attributes.count() == 2
        assert self.processor.stats["attributes_linked"] == 2
        assert self.processor.stats["attributes_missing_mapping"] == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestVariantAttributeLinking(TestCase):
    """Integration tests for linking attributes to ProductVariant via offers.xml"""

    def setUp(self) -> None:
        """Set up test data"""
        super().setUp()
        self.suffix = get_unique_suffix()

        # Create import session
        self.session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )

        # Create variant processor
        self.processor = VariantImportProcessor(
            session_id=self.session.id,
            skip_validation=True,
        )

        # Create test Brand and Category
        self.brand = Brand.objects.create(
            name=f"Test Brand {self.suffix}",
            slug=f"test-brand-{self.suffix}",
            is_active=True,
        )

        self.category = Category.objects.create(
            name=f"Test Category {self.suffix}",
            slug=f"test-category-{self.suffix}",
            is_active=True,
        )

        # Create test Product
        self.product = Product.objects.create(
            onec_id=str(uuid.uuid4()),
            parent_onec_id=str(uuid.uuid4()),
            name=f"Test Product {self.suffix}",
            slug=f"test-product-{self.suffix}",
            brand=self.brand,
            category=self.category,
            description="Test description",
            is_active=True,
        )

        # Create test Attribute (for variant characteristics)
        self.color_attr = Attribute.objects.create(
            name="Цвет",
            slug=f"color-attr-{self.suffix}",
            is_active=True,
        )

        self.size_attr = Attribute.objects.create(
            name="Размер",
            slug=f"size-attr-{self.suffix}",
            is_active=True,
        )

    def test_link_variant_attributes_by_normalized_name(self) -> None:
        """Test linking variant attributes by normalized name/value"""
        # GIVEN: Pre-existing AttributeValue for color
        color_value = AttributeValue.objects.create(
            attribute=self.color_attr,
            value="Красный",
            slug=f"red-value-{self.suffix}",
        )

        variant_guid = str(uuid.uuid4())
        offer_data = {
            "id": f"{self.product.parent_onec_id}#{variant_guid}",
            "name": f"Test Variant {self.suffix}",
            "article": f"SKU-{self.suffix}",
            "characteristics": [
                {"name": "Цвет", "value": "Красный"},  # Should link existing
            ],
        }

        # WHEN: process variant from offer
        variant = self.processor.process_variant_from_offer(offer_data)

        # THEN: variant should be linked to existing attribute value
        assert variant is not None
        assert variant.attributes.count() == 1
        linked_value = variant.attributes.first()
        assert linked_value == color_value
        assert self.processor.stats["attributes_linked"] == 1
        assert self.processor.stats["attributes_missing"] == 0

    def test_create_attribute_value_on_the_fly(self) -> None:
        """Test creating AttributeValue on-the-fly for missing values (AC3)"""
        # GIVEN: Attribute exists but AttributeValue doesn't
        variant_guid = str(uuid.uuid4())
        offer_data = {
            "id": f"{self.product.parent_onec_id}#{variant_guid}",
            "name": f"Test Variant {self.suffix}",
            "article": f"SKU-{self.suffix}",
            "characteristics": [
                {"name": "Цвет", "value": "Синий"},  # New value (not in DB)
            ],
        }

        # WHEN: process variant from offer
        variant = self.processor.process_variant_from_offer(offer_data)

        # THEN: AttributeValue should be created on-the-fly
        assert variant is not None
        assert variant.attributes.count() == 1

        # Verify new AttributeValue was created
        new_value = AttributeValue.objects.filter(
            attribute=self.color_attr,
            value="Синий",
        ).first()
        assert new_value is not None
        assert new_value.slug is not None  # Slug generated
        assert new_value.normalized_value is not None

        # Verify it's linked to variant
        linked_value = variant.attributes.first()
        assert linked_value == new_value

    def test_missing_attribute_logging_variant(self) -> None:
        """Test logging warnings for missing attributes in variant linking"""
        # GIVEN: Characteristic with non-existent attribute
        variant_guid = str(uuid.uuid4())
        offer_data = {
            "id": f"{self.product.parent_onec_id}#{variant_guid}",
            "name": f"Test Variant {self.suffix}",
            "article": f"SKU-{self.suffix}",
            "characteristics": [
                {"name": "Материал", "value": "Хлопок"},  # Attribute doesn't exist
            ],
        }

        # WHEN: process variant from offer
        variant = self.processor.process_variant_from_offer(offer_data)

        # THEN: variant created but attribute not linked
        assert variant is not None
        assert variant.attributes.count() == 0
        assert self.processor.stats["attributes_missing"] == 1

    def test_link_inactive_attribute_to_variant(self) -> None:
        """
        Test linking INACTIVE attributes to ProductVariant (Variant C).
        Import layer does NOT filter by is_active.
        """
        # GIVEN: Inactive attribute
        self.color_attr.is_active = False
        self.color_attr.save()

        color_value = AttributeValue.objects.create(
            attribute=self.color_attr,
            value="Желтый",
            slug=f"yellow-value-{self.suffix}",
        )

        variant_guid = str(uuid.uuid4())
        offer_data = {
            "id": f"{self.product.parent_onec_id}#{variant_guid}",
            "name": f"Test Variant {self.suffix}",
            "article": f"SKU-{self.suffix}",
            "characteristics": [
                {"name": "Цвет", "value": "Желтый"},
            ],
        }

        # WHEN: process variant from offer
        variant = self.processor.process_variant_from_offer(offer_data)

        # THEN: inactive attribute SHOULD be linked (Variant C)
        assert variant is not None
        assert variant.attributes.count() == 1
        linked_value = variant.attributes.first()
        assert linked_value == color_value
        assert linked_value.attribute.is_active is False
