"""
Глобальные фикстуры pytest для проекта FREESPORT
Настройка базовых объектов и утилит для тестирования
"""
import pytest
from unittest.mock import patch
from decimal import Decimal


# Создание фабрик как lazy functions
def create_factories():
    """Ленивое создание фабрик после инициализации Django"""
    import factory
    from django.contrib.auth import get_user_model

    User = get_user_model()

    class UserFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания пользователей"""

        class Meta:
            model = User

        email = factory.Sequence(lambda n: f"user{n}@freesport.test")
        first_name = factory.Faker("first_name")
        last_name = factory.Faker("last_name")
        role = "retail"
        is_active = True
        is_verified = False
        phone = ""
        company_name = ""
        tax_id = ""
        password = factory.PostGenerationMethodCall(
            "set_password", "default_password123"
        )

    class CompanyFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания компаний"""

        class Meta:
            model = "users.Company"

        user = factory.SubFactory(
            UserFactory, role="wholesale_level1", is_verified=True
        )
        legal_name = factory.Faker("company", locale="ru_RU")
        tax_id = factory.Sequence(lambda n: f"{1234567890 + n:012d}")
        kpp = factory.Sequence(lambda n: f"{123456000 + n:09d}")
        legal_address = factory.Faker("address", locale="ru_RU")
        bank_name = factory.Faker("company", locale="ru_RU")
        bank_bik = factory.Sequence(lambda n: f"{44000000 + n:09d}")
        account_number = factory.Sequence(lambda n: f"{40702810000000000000 + n:020d}")

    class AddressFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания адресов"""

        class Meta:
            model = "users.Address"

        user = factory.SubFactory(UserFactory)
        address_type = "shipping"
        full_name = factory.LazyAttribute(
            lambda obj: f"{obj.user.first_name} {obj.user.last_name}"
        )
        phone = "+79001234567"
        city = factory.Faker("city", locale="ru_RU")
        street = factory.Faker("street_name", locale="ru_RU")
        building = factory.Faker("building_number")
        apartment = factory.Faker("random_int", min=1, max=999)
        postal_code = factory.Faker("postcode", locale="ru_RU")
        is_default = False

    class BrandFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания брендов"""

        class Meta:
            model = "products.Brand"

        name = factory.Faker("company", locale="ru_RU")
        slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
        description = factory.Faker("text", max_nb_chars=200, locale="ru_RU")
        is_active = True

    class CategoryFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания категорий"""

        class Meta:
            model = "products.Category"

        name = factory.Faker("word", locale="ru_RU")
        slug = factory.LazyAttribute(lambda obj: obj.name.lower())
        description = factory.Faker("text", max_nb_chars=200, locale="ru_RU")
        is_active = True
        sort_order = factory.Sequence(lambda n: n)

    class ProductFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания товаров"""

        class Meta:
            model = "products.Product"

        name = factory.Faker("catch_phrase", locale="ru_RU")
        slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
        brand = factory.SubFactory(BrandFactory)
        category = factory.SubFactory(CategoryFactory)
        description = factory.Faker("text", max_nb_chars=500, locale="ru_RU")
        short_description = factory.Faker("sentence", nb_words=10, locale="ru_RU")

        # Ценообразование
        retail_price = factory.Faker(
            "pydecimal", left_digits=4, right_digits=2, positive=True
        )
        opt1_price = factory.LazyAttribute(
            lambda obj: obj.retail_price * Decimal("0.9")
        )
        opt2_price = factory.LazyAttribute(
            lambda obj: obj.retail_price * Decimal("0.8")
        )
        opt3_price = factory.LazyAttribute(
            lambda obj: obj.retail_price * Decimal("0.7")
        )
        trainer_price = factory.LazyAttribute(
            lambda obj: obj.retail_price * Decimal("0.85")
        )
        federation_price = factory.LazyAttribute(
            lambda obj: obj.retail_price * Decimal("0.75")
        )

        # Инвентаризация
        sku = factory.Sequence(lambda n: f"SKU-{n:06d}")
        stock_quantity = factory.Faker("random_int", min=0, max=1000)
        min_order_quantity = 1

        is_active = True
        is_featured = False

    class CartFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания корзин"""

        class Meta:
            model = "cart.Cart"

        user = factory.SubFactory(UserFactory)

    class CartItemFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания элементов корзины"""

        class Meta:
            model = "cart.CartItem"

        cart = factory.SubFactory(CartFactory)
        product = factory.SubFactory(ProductFactory)
        quantity = factory.Faker("random_int", min=1, max=10)

    class OrderFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания заказов"""

        class Meta:
            model = "orders.Order"

        user = factory.SubFactory(UserFactory)
        status = "pending"
        total_amount = factory.Faker(
            "pydecimal", left_digits=5, right_digits=2, positive=True
        )
        delivery_address = factory.Faker("address", locale="ru_RU")
        delivery_method = "courier"
        payment_method = "card"

    class OrderItemFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания элементов заказа"""

        class Meta:
            model = "orders.OrderItem"

        order = factory.SubFactory(OrderFactory)
        product = factory.SubFactory(ProductFactory)
        quantity = factory.Faker("random_int", min=1, max=10)
        unit_price = factory.Faker(
            "pydecimal", left_digits=4, right_digits=2, positive=True
        )
        product_name = factory.LazyAttribute(lambda obj: obj.product.name)
        product_sku = factory.LazyAttribute(lambda obj: obj.product.sku)

    class AuditLogFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания записей аудита"""

        class Meta:
            model = "common.AuditLog"

        user = factory.SubFactory(UserFactory)
        action = factory.Faker("word", locale="en")
        resource_type = "Product"
        resource_id = factory.Sequence(lambda n: str(n))
        changes = factory.Dict({"field": "value"})
        ip_address = factory.Faker("ipv4")
        user_agent = factory.Faker("user_agent")

    class SyncLogFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания логов синхронизации"""

        class Meta:
            model = "common.SyncLog"

        sync_type = "products"
        status = "completed"
        records_processed = factory.Faker("random_int", min=1, max=1000)
        errors_count = 0
        error_details = []

    return {
        "UserFactory": UserFactory,
        "CompanyFactory": CompanyFactory,
        "AddressFactory": AddressFactory,
        "BrandFactory": BrandFactory,
        "CategoryFactory": CategoryFactory,
        "ProductFactory": ProductFactory,
        "CartFactory": CartFactory,
        "CartItemFactory": CartItemFactory,
        "OrderFactory": OrderFactory,
        "OrderItemFactory": OrderItemFactory,
        "AuditLogFactory": AuditLogFactory,
        "SyncLogFactory": SyncLogFactory,
    }


# Ленивая загрузка фабрик
_factories = None


def get_factories():
    global _factories
    if _factories is None:
        _factories = create_factories()
    return _factories


# Экспорт фабрик с методами создания
class FactoryWrapper:
    def __init__(self, factory_name):
        self.factory_name = factory_name

    def create(self, *args, **kwargs):
        return get_factories()[self.factory_name].create(*args, **kwargs)

    def build(self, *args, **kwargs):
        return get_factories()[self.factory_name].build(*args, **kwargs)


UserFactory = FactoryWrapper("UserFactory")
CompanyFactory = FactoryWrapper("CompanyFactory")
AddressFactory = FactoryWrapper("AddressFactory")
BrandFactory = FactoryWrapper("BrandFactory")
CategoryFactory = FactoryWrapper("CategoryFactory")
ProductFactory = FactoryWrapper("ProductFactory")
CartFactory = FactoryWrapper("CartFactory")
CartItemFactory = FactoryWrapper("CartItemFactory")
OrderFactory = FactoryWrapper("OrderFactory")
OrderItemFactory = FactoryWrapper("OrderItemFactory")
AuditLogFactory = FactoryWrapper("AuditLogFactory")
SyncLogFactory = FactoryWrapper("SyncLogFactory")


@pytest.fixture
def api_client():
    """
    Клиент DRF API для тестирования endpoints
    """
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def client():
    """
    Стандартный Django тест клиент
    """
    from django.test import Client

    return Client()


@pytest.fixture
def user_factory():
    """
    Фабрика для создания пользователей
    """
    from tests.factories import UserFactory

    return UserFactory


@pytest.fixture
def retail_user(db):
    """
    Розничный пользователь
    """
    from tests.factories import UserFactory

    return UserFactory.create(role="retail")


@pytest.fixture
def wholesale_user(db):
    """
    Оптовый пользователь уровень 1
    """
    from tests.factories import UserFactory

    return UserFactory.create(role="wholesale_level1", is_verified=True)


@pytest.fixture
def trainer_user(db):
    """
    Пользователь-тренер
    """
    from tests.factories import UserFactory

    return UserFactory.create(role="trainer", is_verified=True)


@pytest.fixture
def admin_user(db):
    """
    Пользователь-администратор
    """
    from tests.factories import UserFactory

    return UserFactory.create(
        role="admin", is_staff=True, is_superuser=True, is_verified=True
    )


@pytest.fixture
def authenticated_client(retail_user):
    """
    Создает и возвращает аутентифицированный API-клиент с retail пользователем
    """
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(retail_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    client.user = retail_user  # Добавляем ссылку на пользователя для удобства
    return client


@pytest.fixture
def admin_client(admin_user):
    """
    Создает и возвращает API-клиент с правами администратора
    """
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    client.user = admin_user  # Добавляем ссылку на пользователя для удобства
    return client


@pytest.fixture
def mock_redis():
    """
    Mock для Redis в тестах
    """
    with patch("django_redis.cache.RedisCache") as mock:
        yield mock


@pytest.fixture
def mock_email():
    """
    Mock для отправки email в тестах
    """
    with patch("django.core.mail.send_mail") as mock:
        yield mock


@pytest.fixture
def sample_image():
    """
    Создает образец изображения для тестов
    """
    from PIL import Image
    from io import BytesIO
    from django.core.files.uploadedfile import InMemoryUploadedFile

    img = Image.new("RGB", (100, 100), color="red")
    img_io = BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)

    return InMemoryUploadedFile(
        img_io, None, "test.png", "image/png", len(img_io.getvalue()), None
    )
