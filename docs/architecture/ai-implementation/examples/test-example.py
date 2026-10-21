"""
Тестирование - Реальные примеры из проекта OPTISPORT
Демонстрирует паттерны изоляции тестов, Factory Boy, pytest маркеры
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.products.models import Product, Brand, Category
from tests.factories import ProductFactory, UserFactory, BrandFactory, CategoryFactory

User = get_user_model()


# ===== СИСТЕМА УНИКАЛЬНЫХ ДАННЫХ =====

import uuid
import time

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0


def get_unique_suffix():
    """Генерирует абсолютно уникальный суффикс по требованиям OPTISPORT"""
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"


# ===== ОБЯЗАТЕЛЬНАЯ ФИКСТУРА ИЗОЛЯЦИИ =====


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Автоматически включает доступ к базе данных для всех тестов"""
    pass


@pytest.fixture(autouse=True)
def clear_db_before_test(transactional_db):
    """🔥 КРИТИЧЕСКИ ВАЖНО: Полная изоляция тестов по стандартам OPTISPORT"""
    from django.core.cache import cache
    from django.db import connection
    from django.apps import apps
    from django.db import transaction

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


class TestProductModel:
    """
    ✅ РЕАЛЬНЫЙ ПРИМЕР: Unit тесты для модели Product
    Тестирует ролевое ценообразование - ключевую фичу проекта
    """

    @pytest.mark.integration  # ✅ ИСПРАВЛЕНО: Тесты с Factory = integration
    @pytest.mark.django_db
    def test_get_price_for_user_retail(self):
        """Розничная цена для обычного пользователя"""
        user = UserFactory(
            role="retail",
            email=f"retail-{get_unique_suffix()}@example.com",  # ✅ Уникальные данные
        )
        product = ProductFactory(
            name=f"Product-{get_unique_suffix()}",
            retail_price=Decimal("1000.00"),
            opt1_price=Decimal("800.00"),
        )

        assert product.get_price_for_user(user) == Decimal("1000.00")

    @pytest.mark.integration  # ✅ ИСПРАВЛЕНО
    @pytest.mark.django_db
    def test_get_price_for_user_wholesale(self):
        """Оптовая цена для оптовика"""
        user = UserFactory(role="wholesale_level1")
        product = ProductFactory(
            retail_price=Decimal("1000.00"), opt1_price=Decimal("800.00")
        )

        assert product.get_price_for_user(user) == Decimal("800.00")

    @pytest.mark.integration  # ✅ ИСПРАВЛЕНО
    @pytest.mark.django_db
    def test_get_price_fallback_to_retail(self):
        """Fallback к розничной цене если оптовой нет"""
        user = UserFactory(role="wholesale_level1")
        product = ProductFactory(
            retail_price=Decimal("1000.00"), opt1_price=None  # Нет оптовой цены
        )

        assert product.get_price_for_user(user) == Decimal("1000.00")

    @pytest.mark.integration  # ✅ ИСПРАВЛЕНО
    @pytest.mark.django_db
    def test_anonymous_user_gets_retail_price(self):
        """Анонимный пользователь получает розничную цену"""
        product = ProductFactory(
            retail_price=Decimal("1000.00"), opt1_price=Decimal("800.00")
        )

        assert product.get_price_for_user(None) == Decimal("1000.00")

    @pytest.mark.integration  # ✅ ИСПРАВЛЕНО
    @pytest.mark.django_db
    def test_computed_properties(self):
        """Тест computed properties"""
        product = ProductFactory(is_active=True, stock_quantity=10)

        assert product.is_in_stock is True
        assert product.can_be_ordered is True

        # Товар неактивен
        product.is_active = False
        assert product.can_be_ordered is False

    @pytest.mark.integration  # ✅ ИСПРАВЛЕНО
    @pytest.mark.django_db
    def test_auto_slug_generation(self):
        """Автогенерация slug при сохранении"""
        brand = BrandFactory()
        category = CategoryFactory()

        product = Product.objects.create(
            name="Кроссовки Nike Air Max",
            brand=brand,
            category=category,
            description="Описание",
            retail_price=Decimal("5000.00"),
        )

        assert product.slug == "krossovki-nike-air-max"


class TestProductAPI:
    """
    ✅ РЕАЛЬНЫЙ ПРИМЕР: Интеграционные тесты API
    Тестирует реальные HTTP запросы через APIClient
    """

    @pytest.fixture
    def api_client(self):
        """APIClient для тестов"""
        return APIClient()

    @pytest.fixture
    def sample_products(self):
        """Набор тестовых товаров"""
        brand = BrandFactory(name="Nike")
        category = CategoryFactory(name="Кроссовки")

        return [
            ProductFactory(
                name="Nike Air Max 270",
                brand=brand,
                category=category,
                retail_price=Decimal("8000.00"),
                is_active=True,
                stock_quantity=50,
            ),
            ProductFactory(
                name="Nike Air Force 1",
                brand=brand,
                category=category,
                retail_price=Decimal("6000.00"),
                is_active=True,
                stock_quantity=30,
            ),
        ]

    @pytest.mark.integration
    def test_product_list_api(self, api_client, sample_products):
        """Получение списка товаров через API"""
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2

        # Проверяем структуру ответа
        product = data["results"][0]
        required_fields = ["id", "name", "brand", "category", "price"]
        for field in required_fields:
            assert field in product

    @pytest.mark.integration
    def test_product_detail_api(self, api_client, sample_products):
        """Получение деталей товара"""
        product = sample_products[0]
        response = api_client.get(f"/api/v1/products/{product.id}/")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["name"] == product.name
        assert data["id"] == product.id

    @pytest.mark.integration
    def test_product_filtering_by_brand(self, api_client, sample_products):
        """Фильтрация товаров по бренду"""
        brand = sample_products[0].brand
        response = api_client.get(f"/api/v1/products/?brand={brand.slug}")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["results"]) == 2  # Все товары Nike

    @pytest.mark.integration
    def test_product_price_for_authenticated_user(self, api_client):
        """Ролевое ценообразование для авторизованного пользователя"""
        # Создаем пользователя-оптовика
        user = UserFactory(role="wholesale_level1")
        product = ProductFactory(
            retail_price=Decimal("1000.00"), opt1_price=Decimal("800.00")
        )

        # Авторизуемся
        api_client.force_authenticate(user=user)

        response = api_client.get(f"/api/v1/products/{product.id}/")
        data = response.json()

        # Должны получить оптовую цену
        assert Decimal(str(data["price"])) == Decimal("800.00")


# ✅ ШАБЛОН ТЕСТОВ ДЛЯ НОВЫХ МОДЕЛЕЙ
class TestYourNewModel:
    """Шаблон тестов для новой модели"""

    @pytest.mark.unit
    def test_model_creation(self):
        """Базовый тест создания модели"""
        obj = YourModelFactory(name="Тест")

        assert obj.name == "Тест"
        assert obj.is_active is True
        assert obj.created_at is not None

    @pytest.mark.unit
    def test_model_str_representation(self):
        """Тест строкового представления"""
        obj = YourModelFactory(name="Тестовый объект")
        assert str(obj) == "Тестовый объект"

    @pytest.mark.unit
    def test_model_slug_generation(self):
        """Тест автогенерации slug (если есть)"""
        obj = YourModel.objects.create(name="Тест Слаг")
        assert obj.slug == "test-slag"


class TestYourNewAPI:
    """Шаблон API тестов"""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.mark.integration
    def test_list_endpoint(self, api_client):
        """Тест списка объектов"""
        YourModelFactory.create_batch(3)

        response = api_client.get("/api/v1/your-endpoint/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 3

    @pytest.mark.integration
    def test_detail_endpoint(self, api_client):
        """Тест детального просмотра"""
        obj = YourModelFactory()

        response = api_client.get(f"/api/v1/your-endpoint/{obj.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == obj.name


# ✅ ПАТТЕРН: Фикстуры для переиспользования
@pytest.fixture
def authenticated_user():
    """Авторизованный пользователь для тестов"""
    return UserFactory(role="retail")


@pytest.fixture
def wholesale_user():
    """Пользователь-оптовик"""
    return UserFactory(role="wholesale_level1")


@pytest.fixture
def admin_user():
    """Администратор"""
    return UserFactory(role="admin", is_staff=True, is_superuser=True)
