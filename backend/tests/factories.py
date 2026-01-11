import uuid
import factory
from factory.django import DjangoModelFactory

from apps.products.models import (
    Attribute,
    AttributeValue,
    Brand,
    Brand1CMapping,
    Category,
    Product,
    ProductVariant,
)
from apps.users.models import User


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = Brand

    name = factory.Faker("company")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))


class Brand1CMappingFactory(DjangoModelFactory):
    class Meta:
        model = Brand1CMapping

    brand = factory.SubFactory(BrandFactory)
    onec_id = factory.Faker("uuid4")
    onec_name = factory.Faker("company")


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower())


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Faker("catch_phrase")
    brand = factory.SubFactory(BrandFactory)
    category = factory.SubFactory(CategoryFactory)
    slug = factory.LazyAttribute(
        lambda obj: factory.Faker("slug").generate() + "-" + str(uuid.uuid4())[:8]
    )

    @factory.post_generation
    def create_variant(self, create, extracted, **kwargs):
        if not create:
            return
        ProductVariantFactory.create(product=self)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True


class AttributeFactory(DjangoModelFactory):
    class Meta:
        model = Attribute

    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower())
    is_active = True


class AttributeValueFactory(DjangoModelFactory):
    class Meta:
        model = AttributeValue

    attribute = factory.SubFactory(AttributeFactory)
    value = factory.Faker("word")
    slug = factory.LazyAttribute(lambda obj: obj.value.lower())


class ProductVariantFactory(DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    sku = factory.Faker("ean13")
    retail_price = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True
    )
    stock_quantity = factory.Faker("random_int", min=0, max=100)
