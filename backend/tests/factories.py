import factory
from factory.django import DjangoModelFactory
from apps.products.models import Brand, Category, Product
from apps.users.models import User


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = Brand

    name = factory.Faker("company")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))


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
    retail_price = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True
    )
    stock_quantity = factory.Faker("random_int", min=0, max=100)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
