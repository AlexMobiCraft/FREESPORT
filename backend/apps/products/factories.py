"""
Factory классы для создания тестовых данных
"""
import factory
from factory import fuzzy
from django.utils.text import slugify

from apps.products.models import Product, Category, Brand


class BrandFactory(factory.django.DjangoModelFactory):
    """Factory для создания тестовых брендов"""

    class Meta:
        model = Brand

    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    description = factory.Faker("text", max_nb_chars=200)
    is_active = True


class CategoryFactory(factory.django.DjangoModelFactory):
    """Factory для создания тестовых категорий"""

    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    description = factory.Faker("text", max_nb_chars=200)
    is_active = True


class ProductFactory(factory.django.DjangoModelFactory):
    """Factory для создания тестовых товаров"""

    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    onec_id = factory.Sequence(lambda n: f"product-{n}-uuid#sku-{n}-uuid")
    description = factory.Faker("text", max_nb_chars=500)
    retail_price = fuzzy.FuzzyDecimal(100.0, 10000.0, 2)
    opt1_price = fuzzy.FuzzyDecimal(80.0, 8000.0, 2)
    opt2_price = fuzzy.FuzzyDecimal(60.0, 6000.0, 2)
    opt3_price = fuzzy.FuzzyDecimal(50.0, 5000.0, 2)
    trainer_price = fuzzy.FuzzyDecimal(40.0, 4000.0, 2)
    recommended_retail_price = fuzzy.FuzzyDecimal(120.0, 12000.0, 2)
    max_suggested_retail_price = fuzzy.FuzzyDecimal(130.0, 13000.0, 2)
    stock_quantity = fuzzy.FuzzyInteger(0, 100)
    is_active = True

    # Связи
    category = factory.SubFactory(CategoryFactory)
    brand = factory.SubFactory(BrandFactory)
