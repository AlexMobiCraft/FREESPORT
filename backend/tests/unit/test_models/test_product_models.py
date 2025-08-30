"""
Тесты для моделей товаров FREESPORT Platform
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
import uuid
import time

from tests.conftest import ProductFactory, BrandFactory, CategoryFactory, UserFactory
from apps.products.models import Product, Brand, Category


@pytest.mark.django_db
class TestBrandModel:
    """Тесты модели Brand"""

    def test_brand_creation(self):
        """Тест создания бренда"""
        brand = BrandFactory.create(name="Nike")

        assert brand.name == "Nike"
        assert brand.is_active is True
        assert brand.slug is not None
        assert str(brand) == "Nike"

    def test_brand_slug_generation(self):
        """Тест автогенерации slug"""
        brand = BrandFactory.build(name="Adidas Russia")
        brand.save()

        assert brand.slug == "adidas-russia"

    def test_brand_unique_name(self):
        """Тест уникальности названия бренда"""
        test_brand_name = "Puma"
        BrandFactory.create(name=test_brand_name)

        with pytest.raises(IntegrityError):
            BrandFactory.create(name=test_brand_name)
    def test_brand_meta_configuration(self):
        """Тест настроек Meta класса"""
        assert Brand._meta.verbose_name == "Бренд"
        assert Brand._meta.verbose_name_plural == "Бренды"
        assert Brand._meta.db_table == "brands"


@pytest.mark.django_db
class TestCategoryModel:
    """Тесты модели Category"""

    def test_category_creation(self):
        """Тест создания категории"""
        category = CategoryFactory.create(name="Футбол")

        assert category.name == "Футбол"
        assert category.is_active is True
        assert category.parent is None
        assert str(category) == "Футбол"

    def test_category_hierarchy(self):
        """Тест иерархии категорий"""
        parent = CategoryFactory.create(name="Спорт")
        child = CategoryFactory.create(name="Футбол", parent=parent)

        assert child.parent == parent
        assert str(child) == "Спорт > Футбол"
        assert child.full_name == "Спорт > Футбол"

    def test_category_deep_hierarchy(self):
        """Тест глубокой иерархии категорий"""
        root = CategoryFactory.create(name="Спорт")
        level1 = CategoryFactory.create(name="Командные игры", parent=root)
        level2 = CategoryFactory.create(name="Футбол", parent=level1)

        assert level2.full_name == "Спорт > Командные игры > Футбол"

    def test_category_ordering(self):
        """Тест сортировки категорий"""
        cat1 = CategoryFactory.create(name="Б", sort_order=2)
        cat2 = CategoryFactory.create(name="А", sort_order=1)

        categories = list(Category.objects.all())
        assert categories[0] == cat2  # Сортировка по sort_order
        assert categories[1] == cat1


@pytest.mark.django_db
class TestProductModel:
    """Тесты модели Product"""

    def test_product_creation(self):
        """Тест создания товара"""
        product = ProductFactory.create(
            name="Футбольный мяч Nike", retail_price=Decimal("2500.00")
        )

        assert product.name == "Футбольный мяч Nike"
        assert product.retail_price == Decimal("2500.00")
        assert product.is_active is True
        assert product.stock_quantity >= 0
        assert str(product) == f"Футбольный мяч Nike ({product.sku})"

    def test_product_pricing_for_different_roles(self):
        """Тест ценообразования для разных ролей пользователей"""
        product = ProductFactory.create(
            retail_price=Decimal("1000.00"),
            opt1_price=Decimal("900.00"),
            opt2_price=Decimal("800.00"),
            opt3_price=Decimal("700.00"),
            trainer_price=Decimal("850.00"),
            federation_price=Decimal("750.00"),
        )

        # Тест для разных ролей пользователей
        retail_user = UserFactory.create(role="retail")
        opt1_user = UserFactory.create(role="wholesale_level1")
        opt2_user = UserFactory.create(role="wholesale_level2")
        opt3_user = UserFactory.create(role="wholesale_level3")
        trainer_user = UserFactory.create(role="trainer")
        federation_user = UserFactory.create(role="federation_rep")

        assert product.get_price_for_user(retail_user) == Decimal("1000.00")
        assert product.get_price_for_user(opt1_user) == Decimal("900.00")
        assert product.get_price_for_user(opt2_user) == Decimal("800.00")
        assert product.get_price_for_user(opt3_user) == Decimal("700.00")
        assert product.get_price_for_user(trainer_user) == Decimal("850.00")
        assert product.get_price_for_user(federation_user) == Decimal("750.00")

    def test_product_price_fallback_to_retail(self):
        """Тест возврата к розничной цене если оптовая не указана"""
        product = ProductFactory.create(
            retail_price=Decimal("1000.00"),
            opt1_price=None,  # Не указана
            opt2_price=Decimal("800.00"),
        )

        opt1_user = UserFactory.create(role="wholesale_level1")
        opt2_user = UserFactory.create(role="wholesale_level2")

        assert product.get_price_for_user(opt1_user) == Decimal("1000.00")  # Fallback
        assert product.get_price_for_user(opt2_user) == Decimal("800.00")

    def test_product_price_for_anonymous_user(self):
        """Тест цены для анонимного пользователя"""
        product = ProductFactory.create(retail_price=Decimal("1000.00"))

        assert product.get_price_for_user(None) == Decimal("1000.00")

    def test_product_stock_properties(self):
        """Тест свойств наличия товара"""
        # Товар в наличии
        in_stock_product = ProductFactory.create(stock_quantity=10, is_active=True)
        assert in_stock_product.is_in_stock is True
        assert in_stock_product.can_be_ordered is True

        # Товар закончился
        out_of_stock_product = ProductFactory.create(stock_quantity=0, is_active=True)
        assert out_of_stock_product.is_in_stock is False
        assert out_of_stock_product.can_be_ordered is False

        # Товар неактивен
        inactive_product = ProductFactory.create(stock_quantity=10, is_active=False)
        assert inactive_product.is_in_stock is True
        assert inactive_product.can_be_ordered is False

    def test_product_sku_uniqueness(self):
        """Тест уникальности артикула"""
        test_sku = "UNIQUE-001"
        ProductFactory.create(sku=test_sku)

        with pytest.raises(IntegrityError):
            ProductFactory.create(sku=test_sku)
    def test_product_slug_generation(self):
        """Тест автогенерации slug"""
        brand = BrandFactory.create()
        category = CategoryFactory.create()
        product = ProductFactory.build(
            name="Супер Товар 2024", brand=brand, category=category
        )
        product.save()

        assert product.slug == "супер-товар-2024"

    def test_product_relationships(self):
        """Тест связей товара с брендом и категорией"""
        brand = BrandFactory.create(name="Nike")
        category = CategoryFactory.create(name="Футбол")
        product = ProductFactory.create(brand=brand, category=category)

        assert product.brand == brand
        assert product.category == category
        assert product in brand.products.all()
        assert product in category.products.all()

    def test_product_constraints_validation(self):
        """Тест валидации ограничений товара"""
        # Тест отрицательных цен
        with pytest.raises(ValidationError):
            product = ProductFactory.build(retail_price=Decimal("-100.00"))
            product.full_clean()

        # Тест отрицательного количества на складе
        with pytest.raises(ValidationError):
            product = ProductFactory.build(stock_quantity=-1)
            product.full_clean()

        # Тест минимального количества заказа
        with pytest.raises(ValidationError):
            product = ProductFactory.build(min_order_quantity=0)
            product.full_clean()

    def test_product_meta_configuration(self):
        """Тест настроек Meta класса Product"""
        assert Product._meta.verbose_name == "Товар"
        assert Product._meta.verbose_name_plural == "Товары"
        assert Product._meta.db_table == "products"
        assert Product._meta.ordering == ["-created_at"]
