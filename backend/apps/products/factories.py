"""
Factory классы для создания тестовых данных

КРИТИЧНО: Использует LazyFunction с get_unique_suffix() для полной изоляции тестов
"""

import time
import uuid

import factory
from django.utils.text import slugify
from factory import fuzzy

from apps.products.models import Brand, Category, Product

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0


def get_unique_suffix() -> str:
    """Генерирует абсолютно уникальный суффикс"""
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"


class BrandFactory(factory.django.DjangoModelFactory):
    """Factory для создания тестовых брендов"""

    class Meta:
        model = Brand

    name = factory.LazyFunction(lambda: f"Brand-{get_unique_suffix()}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    onec_id = factory.LazyFunction(lambda: f"brand-1c-{get_unique_suffix()}")
    description = factory.Faker("text", max_nb_chars=200)
    is_active = True


class CategoryFactory(factory.django.DjangoModelFactory):
    """Factory для создания тестовых категорий"""

    class Meta:
        model = Category

    name = factory.LazyFunction(lambda: f"Category-{get_unique_suffix()}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    onec_id = factory.LazyFunction(lambda: f"cat-1c-{get_unique_suffix()}")
    description = factory.Faker("text", max_nb_chars=200)
    is_active = True


class ProductFactory(factory.django.DjangoModelFactory):
    """Factory для создания тестовых товаров"""

    class Meta:
        model = Product

    name = factory.LazyFunction(lambda: f"Product-{get_unique_suffix()}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    sku = factory.LazyFunction(lambda: f"SKU-{get_unique_suffix().upper()}")
    onec_id = factory.LazyFunction(lambda: f"1c-{get_unique_suffix()}")
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
