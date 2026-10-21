"""
conftest.py - Центральный файл фикстур для тестирования OPTISPORT
Соответствует требованиям docs/architecture/10-testing-strategy.md
"""
import pytest
import uuid
import time
from django.core.cache import cache
from django.db import connection, transaction
from django.apps import apps
from rest_framework.test import APIClient

# ===== СИСТЕМА УНИКАЛЬНЫХ ДАННЫХ =====

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0


def get_unique_suffix():
    """Генерирует абсолютно уникальный суффикс по требованиям OPTISPORT"""
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"


# ===== ОБЯЗАТЕЛЬНЫЕ ФИКСТУРЫ ИЗОЛЯЦИИ OPTISPORT =====


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Автоматически включает доступ к базе данных для всех тестов"""
    pass


@pytest.fixture(autouse=True)
def clear_db_before_test(transactional_db):
    """
    🔥 КРИТИЧЕСКИ ВАЖНО: Полная изоляция тестов по стандартам OPTISPORT

    СООТВЕТСТВУЕТ docs/architecture/10-testing-strategy.md секция 10.4.1
    """
    # Очищаем кэши Django
    cache.clear()

    # Принудительная очистка всех таблиц перед тестом
    with connection.cursor() as cursor:
        models = apps.get_models()
        for model in models:
            table_name = model._meta.db_table
            try:
                cursor.execute(
                    f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'
                )
            except Exception:
                pass  # Игнорируем ошибки для системных таблиц

    # Используем транзакционную изоляцию
    with transaction.atomic():
        yield


# ===== ФИКСТУРЫ ДЛЯ API ТЕСТИРОВАНИЯ =====


@pytest.fixture
def api_client():
    """APIClient для тестирования Django REST API"""
    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, retail_user):
    """APIClient с авторизованным retail пользователем"""
    api_client.force_authenticate(user=retail_user)
    return api_client


@pytest.fixture
def b2b_api_client(api_client, wholesale_user):
    """APIClient с авторизованным B2B пользователем"""
    api_client.force_authenticate(user=wholesale_user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """APIClient с авторизованным администратором"""
    api_client.force_authenticate(user=admin_user)
    return api_client


# ===== ФИКСТУРЫ ПОЛЬЗОВАТЕЛЕЙ (РОЛЕВАЯ СИСТЕМА) =====


@pytest.fixture
def retail_user():
    """Розничный пользователь"""
    from tests.factories import UserFactory

    return UserFactory(role="retail", email=f"retail-{get_unique_suffix()}@example.com")


@pytest.fixture
def wholesale_user():
    """B2B оптовый пользователь"""
    from tests.factories import UserFactory

    return UserFactory(
        role="wholesale_level2",
        email=f"wholesale-{get_unique_suffix()}@example.com",
        company_name=f"ООО Компания-{get_unique_suffix()}",
        tax_id=f"{get_unique_suffix()}"[:10],
        is_verified=True,
    )


@pytest.fixture
def trainer_user():
    """Пользователь-тренер"""
    from tests.factories import UserFactory

    return UserFactory(
        role="trainer", email=f"trainer-{get_unique_suffix()}@example.com"
    )


@pytest.fixture
def federation_user():
    """Представитель федерации"""
    from tests.factories import UserFactory

    return UserFactory(
        role="federation_rep", email=f"federation-{get_unique_suffix()}@example.com"
    )


@pytest.fixture
def admin_user():
    """Администратор системы"""
    from tests.factories import UserFactory

    return UserFactory(
        role="admin",
        email=f"admin-{get_unique_suffix()}@example.com",
        is_staff=True,
        is_superuser=True,
    )


# ===== ФИКСТУРЫ ПРОДУКТОВ С РОЛЕВЫМ ЦЕНООБРАЗОВАНИЕМ =====


@pytest.fixture
def product_with_all_prices():
    """Товар со всеми уровнями цен"""
    from tests.factories import ProductFactory, BrandFactory, CategoryFactory
    from decimal import Decimal

    brand = BrandFactory(name=f"Brand-{get_unique_suffix()}")
    category = CategoryFactory(name=f"Category-{get_unique_suffix()}")

    return ProductFactory(
        name=f"Product-{get_unique_suffix()}",
        brand=brand,
        category=category,
        retail_price=Decimal("1000.00"),
        opt1_price=Decimal("800.00"),
        opt2_price=Decimal("750.00"),
        opt3_price=Decimal("700.00"),
        trainer_price=Decimal("900.00"),
        federation_price=Decimal("650.00"),
        recommended_retail_price=Decimal("1200.00"),  # RRP для B2B
        max_suggested_retail_price=Decimal("1300.00"),  # MSRP для B2B
        stock_quantity=100,
        is_active=True,
    )


@pytest.fixture
def product_without_special_prices():
    """Товар только с розничной ценой (для тестирования fallback)"""
    from tests.factories import ProductFactory, BrandFactory, CategoryFactory
    from decimal import Decimal

    brand = BrandFactory(name=f"Brand-{get_unique_suffix()}")
    category = CategoryFactory(name=f"Category-{get_unique_suffix()}")

    return ProductFactory(
        name=f"Product-{get_unique_suffix()}",
        brand=brand,
        category=category,
        retail_price=Decimal("500.00"),
        opt1_price=None,
        opt2_price=None,
        opt3_price=None,
        trainer_price=None,
        federation_price=None,
        stock_quantity=50,
        is_active=True,
    )


# ===== ФИКСТУРЫ ДЛЯ КОРЗИНЫ И ЗАКАЗОВ =====


@pytest.fixture
def cart_with_items(retail_user, product_with_all_prices):
    """Корзина с товарами"""
    from tests.factories import CartFactory, CartItemFactory

    cart = CartFactory(user=retail_user)
    CartItemFactory(
        cart=cart,
        product=product_with_all_prices,
        quantity=2,
        price_snapshot=product_with_all_prices.get_price_for_user(retail_user),
    )
    return cart


@pytest.fixture
def b2b_order(wholesale_user, product_with_all_prices):
    """B2B заказ"""
    from tests.factories import OrderFactory, OrderItemFactory

    order = OrderFactory(user=wholesale_user, status="pending")
    OrderItemFactory(
        order=order,
        product=product_with_all_prices,
        quantity=10,
        unit_price=product_with_all_prices.get_price_for_user(wholesale_user),
    )
    return order


# ===== МОКИНГ ВНЕШНИХ СИСТЕМ =====


@pytest.fixture
def mock_1c_server():
    """Mock сервер для имитации 1С в тестах"""
    from unittest.mock import Mock

    mock = Mock()
    mock.create_customer.return_value = {
        "status": "success",
        "onec_id": f"MOCK_CLIENT_{get_unique_suffix()}",
        "message": "Customer created successfully",
    }
    mock.get_customers.return_value = {
        "status": "success",
        "customers": [],
        "total_count": 0,
    }
    return mock


@pytest.fixture
def mock_yukassa_payment():
    """Mock для YuKassa платежей"""
    from unittest.mock import Mock

    mock = Mock()
    mock.create_payment.return_value = {
        "id": f"payment_{get_unique_suffix()}",
        "status": "pending",
        "amount": {"value": "1000.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "confirmation_url": "https://mock-payment-url.com",
        },
    }
    return mock


# ===== ФИКСТУРЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ =====


@pytest.fixture
def django_assert_num_queries():
    """
    Фикстура для проверки количества SQL запросов
    Используется в тестах производительности
    """
    from django.test.utils import override_settings
    from django.db import connection
    from contextlib import contextmanager

    @contextmanager
    def assert_num_queries(expected_count):
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            yield
            final_queries = len(connection.queries)
            actual_count = final_queries - initial_queries

            if actual_count != expected_count:
                queries = connection.queries[initial_queries:]
                raise AssertionError(
                    f"Expected {expected_count} queries, got {actual_count}:\n"
                    + "\n".join([q["sql"] for q in queries])
                )

    return assert_num_queries


# ===== НАСТРОЙКИ PYTEST =====


def pytest_configure(config):
    """Конфигурация pytest для OPTISPORT"""
    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": "freesport_test",
                    "USER": "postgres",
                    "PASSWORD": "postgres",
                    "HOST": "localhost",
                    "PORT": "5432",
                }
            },
            SECRET_KEY="test-key-for-pytest",
            USE_TZ=True,
        )

    django.setup()


def pytest_collection_modifyitems(config, items):
    """Автоматическая маркировка тестов"""
    for item in items:
        # Автоматически добавляем django_db маркер для интеграционных тестов
        if hasattr(item, "pytestmark"):
            marks = [mark.name for mark in item.pytestmark if hasattr(mark, "name")]
            if "integration" in marks and "django_db" not in marks:
                item.add_marker(pytest.mark.django_db)


# ===== ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ =====


@pytest.fixture
def temp_media_root(tmp_path, settings):
    """Временная директория для медиа файлов в тестах"""
    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = str(media_root)
    return media_root


@pytest.fixture
def sample_image():
    """Создает тестовое изображение"""
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    import io

    image = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return SimpleUploadedFile(
        name="test_image.png", content=buffer.getvalue(), content_type="image/png"
    )
