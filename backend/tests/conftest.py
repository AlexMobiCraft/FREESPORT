"""
Глобальные фикстуры pytest для проекта FREESPORT
Настройка базовых объектов и утилит для тестирования
"""
import random
import time
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0


def get_unique_suffix():
    """Генерирует абсолютно уникальный суффикс с глобальным счетчиком,
    временной меткой и UUID"""
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"


def get_unique_order_number():
    """Генерирует абсолютно уникальный номер заказа"""
    global _unique_counter
    _unique_counter += 1
    date_part = datetime.now().strftime("%y%m%d")
    unique_part = f"{_unique_counter:04d}{uuid.uuid4().hex[:3].upper()}"
    timestamp = (
        int(time.time() * 1000) % 100000
    )  # последние 5 цифр microsecond timestamp
    return f"FS-{date_part}-{unique_part}-{timestamp}"


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
        phone = factory.LazyFunction(
            lambda: f"+7{random.randint(9000000000, 9999999999)}"
        )
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
        tax_id = factory.LazyFunction(
            lambda: f"{123456789000 + int(time.time()) % 999999:012d}"
        )
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

        name = factory.LazyFunction(lambda: f"Brand-{get_unique_suffix()}")
        slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
        description = factory.Faker("text", max_nb_chars=200, locale="ru_RU")
        is_active = True

    class CategoryFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания категорий"""

        class Meta:
            model = "products.Category"

        name = factory.Faker("word", locale="ru_RU")
        slug = factory.LazyAttribute(
            lambda obj: f"{obj.name.lower()}-{get_unique_suffix()}"
        )
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
        sku = factory.LazyFunction(lambda: f"SKU-{get_unique_suffix().upper()}")
        # Фиксированное количество на складе, чтобы избежать случайных падений тестов
        stock_quantity = 100
        min_order_quantity = 1

        is_active = True
        is_featured = False

    class ProductImageFactory(factory.django.DjangoModelFactory):
        """Фабрика для создания изображений товаров"""

        class Meta:
            model = "products.ProductImage"

        product = factory.SubFactory(ProductFactory)
        image = factory.django.ImageField(color="red")
        alt_text = factory.Faker("sentence", nb_words=5, locale="ru_RU")
        is_main = False
        sort_order = factory.Sequence(lambda n: n)

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
        order_number = factory.LazyFunction(get_unique_order_number)
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
        total_price = factory.LazyAttribute(lambda obj: obj.quantity * obj.unit_price)

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
        "ProductImageFactory": ProductImageFactory,
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

    def create_batch(self, *args, **kwargs):
        return get_factories()[self.factory_name].create_batch(*args, **kwargs)


UserFactory = FactoryWrapper("UserFactory")
CompanyFactory = FactoryWrapper("CompanyFactory")
AddressFactory = FactoryWrapper("AddressFactory")
BrandFactory = FactoryWrapper("BrandFactory")
CategoryFactory = FactoryWrapper("CategoryFactory")
ProductFactory = FactoryWrapper("ProductFactory")
ProductImageFactory = FactoryWrapper("ProductImageFactory")
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
    return UserFactory


@pytest.fixture
def company_factory():
    return CompanyFactory


@pytest.fixture
def address_factory():
    return AddressFactory


@pytest.fixture
def brand_factory():
    return BrandFactory


@pytest.fixture
def category_factory():
    return CategoryFactory


@pytest.fixture
def product_factory():
    return ProductFactory


@pytest.fixture
def product_image_factory():
    return ProductImageFactory


@pytest.fixture
def cart_factory():
    return CartFactory


@pytest.fixture
def cart_item_factory():
    return CartItemFactory


@pytest.fixture
def order_factory():
    return OrderFactory


@pytest.fixture
def order_item_factory():
    return OrderItemFactory


@pytest.fixture
def audit_log_factory():
    return AuditLogFactory


@pytest.fixture
def sync_log_factory():
    return SyncLogFactory


@pytest.fixture
def api_request_factory():
    """
    Фабрика для создания mock-запросов
    """
    from rest_framework.test import APIRequestFactory

    return APIRequestFactory()


@pytest.fixture
def retail_user(db, user_factory):
    """
    Розничный пользователь
    """
    return user_factory.create(role="retail")


@pytest.fixture
def wholesale_user(db, user_factory):
    """
    Оптовый пользователь уровень 1
    """
    return user_factory.create(role="wholesale_level1", is_verified=True)


@pytest.fixture
def trainer_user(db, user_factory):
    """
    Пользователь-тренер
    """
    return user_factory.create(role="trainer", is_verified=True)


@pytest.fixture
def admin_user(db, user_factory):
    """
    Пользователь-администратор
    """
    return user_factory.create(
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
    access_token = str(refresh.access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    # Добавляем ссылку на пользователя для удобства (расширяем тип)
    client.user = retail_user  # type: ignore[attr-defined]
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
    access_token = str(refresh.access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    client.user = admin_user  # type: ignore[attr-defined]
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
    from io import BytesIO

    from django.core.files.uploadedfile import InMemoryUploadedFile
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    img_io = BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)

    return InMemoryUploadedFile(
        img_io, None, "test.png", "image/png", len(img_io.getvalue()), None
    )


@pytest.fixture
def access_token(db, user_factory):
    """
    Создает розничного пользователя и возвращает JWT токен доступа
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    user = user_factory.create(role="retail")
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    return access_token


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Автоматически включает доступ к базе данных для всех тестов
    с мягким управлением соединениями
    """
    from django.db import connection

    # Минимальная проверка соединения без агрессивных действий
    try:
        # Просто проверяем, что соединение работает
        if not connection.is_usable():
            connection.ensure_connection()
    except Exception:
        # Если проблема с соединением, пытаемся восстановить
        try:
            connection.ensure_connection()
        except Exception:
            pass

    yield

    # НЕ закрываем соединение - оставляем для следующих тестов


@pytest.fixture(autouse=False)
def clear_db_before_test(transactional_db):
    """
    Оптимизированная очистка базы данных без deadlock'ов
    """
    from django.apps import apps
    from django.core.cache import cache
    from django.db import connection, transaction

    # Очищаем кэши Django
    cache.clear()

    # Сбрасываем счетчик перед каждым тестом
    global _unique_counter
    _unique_counter = 0

    try:
        # Проверяем существование соединения с базой
        if not connection.is_usable():
            connection.ensure_connection()

        # Используем мягкий подход - удаляем только пользовательские данные
        from django.apps import apps

        # Список моделей для очистки (в правильном порядке зависимостей)
        model_order = [
            "cart.CartItem",
            "orders.OrderItem",
            "orders.Order",
            "cart.Cart",
            "products.ProductImage",
            "products.Product",
            "products.Category",
            "products.Brand",
            "users.Address",
            "users.Company",
            "common.AuditLog",
            "common.SyncLog",
        ]

        # Используем DELETE вместо TRUNCATE для избежания проблем с базой
        for model_name in model_order:
            try:
                model = apps.get_model(model_name)
                # Быстрое удаление без сигналов
                model._default_manager.all().delete()
            except (LookupError, Exception):
                continue

    except Exception:
        # В случае критической ошибки просто пропускаем очистку
        pass

    yield

    # Минимальная очистка после теста
    try:
        cache.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True, scope="function")
def close_db_connections():
    """
    Автоматическое закрытие соединений с БД после каждого теста.
    Предотвращает ошибки "database is being accessed by other users".
    
    ВАЖНО: Закрывает только неактивные соединения, не трогая транзакции.
    """
    yield
    
    # Закрываем все соединения с БД после теста
    try:
        from django.db import connection, connections
        
        # Проверяем, что нет активных транзакций
        if not connection.in_atomic_block:
            connections.close_all()
    except Exception:
        # В случае ошибки просто пропускаем закрытие
        pass
