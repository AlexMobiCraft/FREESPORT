"""Unit-тесты для моделей Attribute и AttributeValue."""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.products.models import Attribute, AttributeValue, Product, ProductVariant
from tests.conftest import get_unique_suffix


@pytest.mark.unit
@pytest.mark.django_db
class TestAttributeModel:
    """Тесты для модели Attribute."""

    def test_attribute_creation_with_cyrillic_name(self) -> None:
        """Тест: создание атрибута с кириллическим названием."""
        # ARRANGE
        suffix = get_unique_suffix()
        name = f"Цвет {suffix}"
        onec_id = f"attr-color-{suffix}"

        # ACT
        attribute = Attribute.objects.create(
            name=name, onec_id=onec_id, type="color"
        )

        # ASSERT
        assert attribute.name == name
        assert attribute.onec_id == onec_id
        assert attribute.type == "color"
        assert attribute.slug is not None
        assert len(attribute.slug) > 0

    def test_attribute_slug_generation(self) -> None:
        """Тест: автоматическая генерация slug из кириллического имени."""
        # ARRANGE
        suffix = get_unique_suffix()
        name = f"Материал {suffix}"
        onec_id = f"attr-material-{suffix}"

        # ACT
        attribute = Attribute.objects.create(name=name, onec_id=onec_id)

        # ASSERT
        # Проверяем что slug создан и транслитерирован
        assert attribute.slug is not None
        # slug должен содержать только латиницу, цифры и дефисы
        assert all(c.isalnum() or c == "-" for c in attribute.slug)
        # slug не должен содержать кириллицу
        assert not any("\u0400" <= c <= "\u04FF" for c in attribute.slug)

    def test_attribute_str_representation(self) -> None:
        """Тест: строковое представление модели."""
        # ARRANGE
        suffix = get_unique_suffix()
        name = f"Размер {suffix}"
        onec_id = f"attr-size-{suffix}"
        attribute = Attribute.objects.create(name=name, onec_id=onec_id)

        # ACT
        result = str(attribute)

        # ASSERT
        assert result == name

    def test_attribute_onec_id_uniqueness(self) -> None:
        """Тест: onec_id должен быть уникальным."""
        # ARRANGE
        suffix = get_unique_suffix()
        onec_id = f"attr-duplicate-{suffix}"
        Attribute.objects.create(
            name=f"Атрибут 1 {suffix}", onec_id=onec_id
        )

        # ACT & ASSERT
        with pytest.raises(IntegrityError):
            Attribute.objects.create(
                name=f"Атрибут 2 {suffix}", onec_id=onec_id
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestAttributeValueModel:
    """Тесты для модели AttributeValue."""

    def test_attribute_value_creation_with_cyrillic(self) -> None:
        """Тест: создание значения атрибута с кириллицей."""
        # ARRANGE
        suffix = get_unique_suffix()
        attribute = Attribute.objects.create(
            name=f"Цвет {suffix}", onec_id=f"attr-color-{suffix}"
        )
        value = f"Красный {suffix}"
        onec_id = f"val-red-{suffix}"

        # ACT
        attr_value = AttributeValue.objects.create(
            attribute=attribute, value=value, onec_id=onec_id
        )

        # ASSERT
        assert attr_value.value == value
        assert attr_value.attribute == attribute
        assert attr_value.onec_id == onec_id
        assert attr_value.slug is not None
        assert len(attr_value.slug) > 0

    def test_attribute_value_slug_generation(self) -> None:
        """Тест: автоматическая генерация slug из кириллического значения."""
        # ARRANGE
        suffix = get_unique_suffix()
        attribute = Attribute.objects.create(
            name=f"Материал {suffix}", onec_id=f"attr-material-{suffix}"
        )
        value = f"Хлопок {suffix}"
        onec_id = f"val-cotton-{suffix}"

        # ACT
        attr_value = AttributeValue.objects.create(
            attribute=attribute, value=value, onec_id=onec_id
        )

        # ASSERT
        # Проверяем что slug создан и транслитерирован
        assert attr_value.slug is not None
        # slug должен содержать только латиницу, цифры и дефисы
        assert all(c.isalnum() or c == "-" for c in attr_value.slug)
        # slug не должен содержать кириллицу
        assert not any("\u0400" <= c <= "\u04FF" for c in attr_value.slug)

    def test_attribute_value_foreign_key_relationship(self) -> None:
        """Тест: FK связь с Attribute."""
        # ARRANGE
        suffix = get_unique_suffix()
        attribute = Attribute.objects.create(
            name=f"Размер {suffix}", onec_id=f"attr-size-{suffix}"
        )
        value1 = AttributeValue.objects.create(
            attribute=attribute,
            value=f"XL {suffix}",
            onec_id=f"val-xl-{suffix}",
        )
        value2 = AttributeValue.objects.create(
            attribute=attribute,
            value=f"XXL {suffix}",
            onec_id=f"val-xxl-{suffix}",
        )

        # ACT
        values = attribute.values.all()

        # ASSERT
        assert values.count() == 2
        assert value1 in values
        assert value2 in values

    def test_attribute_value_str_representation(self) -> None:
        """Тест: строковое представление модели."""
        # ARRANGE
        suffix = get_unique_suffix()
        attribute = Attribute.objects.create(
            name=f"Цвет {suffix}", onec_id=f"attr-color-{suffix}"
        )
        value = f"Синий {suffix}"
        attr_value = AttributeValue.objects.create(
            attribute=attribute, value=value, onec_id=f"val-blue-{suffix}"
        )

        # ACT
        result = str(attr_value)

        # ASSERT
        assert result == f"{attribute.name}: {value}"

    def test_attribute_value_onec_id_uniqueness(self) -> None:
        """Тест: onec_id должен быть уникальным."""
        # ARRANGE
        suffix = get_unique_suffix()
        attribute = Attribute.objects.create(
            name=f"Атрибут {suffix}", onec_id=f"attr-test-{suffix}"
        )
        onec_id = f"val-duplicate-{suffix}"
        AttributeValue.objects.create(
            attribute=attribute,
            value=f"Значение 1 {suffix}",
            onec_id=onec_id,
        )

        # ACT & ASSERT
        with pytest.raises(IntegrityError):
            AttributeValue.objects.create(
                attribute=attribute,
                value=f"Значение 2 {suffix}",
                onec_id=onec_id,
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestProductAttributeRelationship:
    """Тесты для M2M отношений Product и AttributeValue."""

    def test_product_can_add_attribute_values(
        self, brand_factory, category_factory
    ) -> None:
        """Тест: можно добавить атрибуты к Product."""
        # ARRANGE
        suffix = get_unique_suffix()
        brand = brand_factory.create()
        category = category_factory.create()
        product = Product.objects.create(
            name=f"Товар {suffix}",
            slug=f"product-{suffix}",
            brand=brand,
            category=category,
            description="Test product",
            onec_id=f"prod-{suffix}",
        )
        attribute = Attribute.objects.create(
            name=f"Цвет {suffix}", onec_id=f"attr-color-{suffix}"
        )
        attr_value = AttributeValue.objects.create(
            attribute=attribute,
            value=f"Красный {suffix}",
            onec_id=f"val-red-{suffix}",
        )

        # ACT
        product.attributes.add(attr_value)

        # ASSERT
        assert product.attributes.count() == 1
        assert attr_value in product.attributes.all()

    def test_product_can_have_multiple_attributes(
        self, brand_factory, category_factory
    ) -> None:
        """Тест: Product может иметь несколько атрибутов."""
        # ARRANGE
        suffix = get_unique_suffix()
        brand = brand_factory.create()
        category = category_factory.create()
        product = Product.objects.create(
            name=f"Товар {suffix}",
            slug=f"product-{suffix}",
            brand=brand,
            category=category,
            description="Test product",
            onec_id=f"prod-{suffix}",
        )
        color_attr = Attribute.objects.create(
            name=f"Цвет {suffix}", onec_id=f"attr-color-{suffix}"
        )
        size_attr = Attribute.objects.create(
            name=f"Размер {suffix}", onec_id=f"attr-size-{suffix}"
        )
        red_value = AttributeValue.objects.create(
            attribute=color_attr,
            value=f"Красный {suffix}",
            onec_id=f"val-red-{suffix}",
        )
        xl_value = AttributeValue.objects.create(
            attribute=size_attr,
            value=f"XL {suffix}",
            onec_id=f"val-xl-{suffix}",
        )

        # ACT
        product.attributes.add(red_value, xl_value)

        # ASSERT
        assert product.attributes.count() == 2
        assert red_value in product.attributes.all()
        assert xl_value in product.attributes.all()


@pytest.mark.unit
@pytest.mark.django_db
class TestProductVariantAttributeRelationship:
    """Тесты для M2M отношений ProductVariant и AttributeValue."""

    def test_variant_can_add_attribute_values(
        self, brand_factory, category_factory
    ) -> None:
        """Тест: можно добавить атрибуты к ProductVariant."""
        # ARRANGE
        suffix = get_unique_suffix()
        brand = brand_factory.create()
        category = category_factory.create()
        product = Product.objects.create(
            name=f"Товар {suffix}",
            slug=f"product-{suffix}",
            brand=brand,
            category=category,
            description="Test product",
            onec_id=f"prod-{suffix}",
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku=f"SKU-{suffix}",
            onec_id=f"variant-{suffix}",
            retail_price=100.00,
        )
        attribute = Attribute.objects.create(
            name=f"Цвет {suffix}", onec_id=f"attr-color-{suffix}"
        )
        attr_value = AttributeValue.objects.create(
            attribute=attribute,
            value=f"Синий {suffix}",
            onec_id=f"val-blue-{suffix}",
        )

        # ACT
        variant.attributes.add(attr_value)

        # ASSERT
        assert variant.attributes.count() == 1
        assert attr_value in variant.attributes.all()

    def test_variant_can_have_multiple_attributes(
        self, brand_factory, category_factory
    ) -> None:
        """Тест: ProductVariant может иметь несколько атрибутов."""
        # ARRANGE
        suffix = get_unique_suffix()
        brand = brand_factory.create()
        category = category_factory.create()
        product = Product.objects.create(
            name=f"Товар {suffix}",
            slug=f"product-{suffix}",
            brand=brand,
            category=category,
            description="Test product",
            onec_id=f"prod-{suffix}",
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku=f"SKU-{suffix}",
            onec_id=f"variant-{suffix}",
            retail_price=100.00,
        )
        color_attr = Attribute.objects.create(
            name=f"Цвет {suffix}", onec_id=f"attr-color-{suffix}"
        )
        material_attr = Attribute.objects.create(
            name=f"Материал {suffix}", onec_id=f"attr-material-{suffix}"
        )
        green_value = AttributeValue.objects.create(
            attribute=color_attr,
            value=f"Зелёный {suffix}",
            onec_id=f"val-green-{suffix}",
        )
        cotton_value = AttributeValue.objects.create(
            attribute=material_attr,
            value=f"Хлопок {suffix}",
            onec_id=f"val-cotton-{suffix}",
        )

        # ACT
        variant.attributes.add(green_value, cotton_value)

        # ASSERT
        assert variant.attributes.count() == 2
        assert green_value in variant.attributes.all()
        assert cotton_value in variant.attributes.all()
