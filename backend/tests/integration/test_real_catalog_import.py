"""
Integration тесты для валидации импорта реального каталога из 1С

Story 3.1.3: test-catalog-loading
Валидация корректности импорта реального каталога из data/import_1c/
"""
from pathlib import Path
from typing import Any, Optional, cast

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.utils import OperationalError

from django.apps import apps

brand_model = apps.get_model("products", "Brand")
category_model = apps.get_model("products", "Category")
import_session_model = apps.get_model("products", "ImportSession")
product_model = apps.get_model("products", "Product")

if None in {
    brand_model,
    category_model,
    import_session_model,
    product_model,
}:
    raise RuntimeError("Не удалось загрузить модели products приложения")

Brand = cast(Any, brand_model)
Category = cast(Any, category_model)
ImportSession = cast(Any, import_session_model)
Product = cast(Any, product_model)


# Путь к реальным данным 1С
# Проверяем несколько возможных расположений
# 1. Docker: /app/data/import_1c (монтирование из ./data)
# 2. Локально: ../data/import_1c относительно BASE_DIR
possible_paths = [
    Path("/app/data/import_1c"),  # Docker с монтированием
    Path(settings.BASE_DIR).parent / "data" / "import_1c",  # Локально
]

data_dir_candidate: Optional[Path] = None
for path in possible_paths:
    if path.exists():
        data_dir_candidate = path
        break

if data_dir_candidate is None:
    data_dir_candidate = possible_paths[0]

DATA_DIR = cast(Path, data_dir_candidate)


def is_database_available():
    """Проверяет доступность базы данных"""
    try:
        connection.ensure_connection()
        return True
    except OperationalError:
        return False


# Skip all tests if data directory or database is not available
# Важно: эти тесты требуют миграций для создания таблицы ImportSession
pytestmark = [
    pytest.mark.skipif(
        not DATA_DIR.exists(), reason=f"Data directory not found: {DATA_DIR}"
    ),
    pytest.mark.django_db(transaction=True),
    pytest.mark.integration,
]


class TestRealCatalogImport:
    """Integration тесты для импорта реального каталога из 1С"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Очистка БД перед каждым тестом"""
        Product.objects.all().delete()
        Category.objects.all().delete()
        Brand.objects.all().delete()
        ImportSession.objects.all().delete()
        yield
        # Cleanup after test
        Product.objects.all().delete()
        Category.objects.all().delete()
        Brand.objects.all().delete()
        ImportSession.objects.all().delete()

    def test_import_real_goods(self):
        """
        AC1: Валидация импорта товаров из реальных файлов
        Проверяет что импортировано ≥1900 товаров из goods_1_*.xml
        (Реальные данные содержат ~1916 товаров в 4 файлах)
        """
        # Проверка наличия данных
        assert DATA_DIR.exists(), f"Директория с данными не найдена: {DATA_DIR}"
        goods_dir = DATA_DIR / "goods"
        assert goods_dir.exists(), f"Директория goods не найдена: {goods_dir}"

        goods_files = list(goods_dir.glob("goods_1_*.xml"))
        assert (
            len(goods_files) >= 4
        ), f"Ожидается минимум 4 файла goods, найдено: {len(goods_files)}"

        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
            "--file-type",
            "goods",
        )

        # Валидация результатов
        products_count = Product.objects.count()
        assert (
            products_count >= 1900
        ), f"Ожидается ≥1900 товаров, импортировано: {products_count}"

        # Проверка что все товары имеют onec_id
        products_without_onec_id = Product.objects.filter(onec_id__isnull=True).count()
        assert (
            products_without_onec_id == 0
        ), f"Найдены товары без onec_id: {products_without_onec_id}"

        # Проверка что товары имеют базовые поля
        sample_product = Product.objects.first()
        assert sample_product is not None, "Должен существовать хотя бы один товар"
        assert sample_product.name, "Товар должен иметь название"
        assert sample_product.onec_id, "Товар должен иметь onec_id"

    def test_import_real_categories(self):
        """
        AC1: Валидация иерархии категорий из groups_*.xml
        Проверяет корректность импорта категорий и их иерархии
        """
        # Проверка наличия данных
        groups_dir = DATA_DIR / "groups"
        assert groups_dir.exists(), f"Директория groups не найдена: {groups_dir}"

        groups_files = list(groups_dir.glob("groups_1_*.xml"))
        assert (
            len(groups_files) >= 1
        ), f"Ожидается минимум 1 файл groups, найдено: {len(groups_files)}"

        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
            "--file-type",
            "all",
        )

        # Валидация результатов
        categories_count = Category.objects.count()
        assert categories_count > 0, "Категории должны быть импортированы"

        # Проверка наличия корневых категорий
        root_categories = Category.objects.filter(parent__isnull=True)
        assert root_categories.exists(), "Должны существовать корневые категории"

        # Проверка иерархии
        categories_with_parent = Category.objects.filter(parent__isnull=False)
        if categories_with_parent.exists():
            # Проверяем что parent существуют
            for cat in categories_with_parent:
                parent_id = getattr(cat, "parent_id", None)
                assert parent_id is not None
                assert Category.objects.filter(id=parent_id).exists()

        # Проверка что категории имеют onec_id
        categories_without_onec_id = Category.objects.filter(
            onec_id__isnull=True
        ).count()
        assert (
            categories_without_onec_id == 0
        ), f"Найдены категории без onec_id: {categories_without_onec_id}"

    def test_import_real_prices(self):
        """
        AC2: Валидация всех типов цен из prices_*.xml
        Проверяет что цены корректно импортированы для всех 7 ролей
        """
        # Проверка наличия данных
        prices_dir = DATA_DIR / "prices"
        assert prices_dir.exists(), f"Директория prices не найдена: {prices_dir}"

        prices_files = list(prices_dir.glob("prices_1_*.xml"))
        assert (
            len(prices_files) >= 5
        ), f"Ожидается минимум 5 файлов prices, найдено: {len(prices_files)}"

        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
        )

        # Валидация цен для всех ролей
        products_with_prices = Product.objects.filter(retail_price__gt=0)
        assert (
            products_with_prices.exists()
        ), "Должны быть товары с установленными ценами"

        # Проверка всех типов цен
        for product in products_with_prices[:100]:  # Проверяем первые 100
            # retail_price обязательна
            assert (
                product.retail_price > 0
            ), f"Product {product.id} должен иметь retail_price"

            # Проверяем что опциональные цены неотрицательные (если установлены)
            if product.opt1_price:
                assert product.opt1_price >= 0
            if product.opt2_price:
                assert product.opt2_price >= 0
            if product.opt3_price:
                assert product.opt3_price >= 0
            if product.trainer_price:
                assert product.trainer_price >= 0
            if product.federation_price:
                assert product.federation_price >= 0

            # Проверяем информационные цены (РРЦ, МРЦ)
            if product.recommended_retail_price:
                assert product.recommended_retail_price >= 0
            if product.max_suggested_retail_price:
                assert product.max_suggested_retail_price >= 0

    def test_real_data_integrity(self):
        """
        AC4: Проверка связей и целостности данных
        Валидирует что связи Product → Category → Brand корректны
        """
        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
        )

        # Проверка связей Product → Category
        products_count = Product.objects.count()
        assert products_count > 0, "Должны быть импортированы товары"

        products_with_category = Product.objects.filter(category__isnull=False)
        if products_with_category.exists():
            # Проверяем что категории существуют
            for product in products_with_category[:100]:
                assert product.category is not None
                assert Category.objects.filter(id=product.category.id).exists()

        # Проверка уникальности onec_id
        products = Product.objects.values_list("onec_id", flat=True)
        unique_onec_ids = set(products)
        assert len(products) == len(
            unique_onec_ids
        ), "onec_id товаров должны быть уникальными"

        # Проверка отсутствия orphan records
        # Все категории с parent должны иметь существующий parent
        categories_with_invalid_parent = Category.objects.filter(
            parent__isnull=False
        ).exclude(parent__in=Category.objects.values_list("id", flat=True))

        assert categories_with_invalid_parent.count() == 0, (
            f"Найдены категории с несуществующим parent: "
            f"{categories_with_invalid_parent.count()}"
        )

    def test_specifications_from_properties(self):
        """
        AC3: Валидация характеристик из propertiesGoods_*.xml
        Проверяет что технические характеристики заполнены корректно
        """
        # Проверка наличия данных
        props_dir = DATA_DIR / "propertiesGoods"
        assert props_dir.exists(), f"Директория propertiesGoods не найдена: {props_dir}"

        props_files = list(props_dir.glob("propertiesGoods_1_*.xml"))
        assert len(props_files) >= 9, (
            f"Ожидается минимум 9 файлов propertiesGoods, "
            f"найдено: {len(props_files)}"
        )

        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
        )

        # Валидация specifications
        products_with_specs = Product.objects.exclude(
            specifications__isnull=True
        ).exclude(specifications={})

        if products_with_specs.exists():
            # Проверка структуры JSON
            for product in products_with_specs[:50]:
                specs = product.specifications
                assert isinstance(
                    specs, dict
                ), f"Product {product.id} specifications должен быть dict"

                # Проверка типов данных в характеристиках
                for key, value in specs.items():
                    assert isinstance(
                        key, str
                    ), f"Ключ спецификации должен быть строкой: {key}"
                    # Значения могут быть строками, списками, числами
                    assert isinstance(
                        value, (str, list, int, float, bool)
                    ), f"Неверный тип значения спецификации: {type(value)}"

    def test_api_returns_real_products(self):
        """
        AC5: Проверка API с реальными данными
        Валидирует что API возвращает корректные данные после импорта
        """
        from rest_framework.test import APIClient

        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
        )

        client = APIClient()

        # Проверка списка товаров
        response = client.get("/api/v1/products/")
        assert response.status_code == 200

        data = response.json()
        assert "results" in data or isinstance(data, list)

        # Проверка что возвращаются реальные товары
        if isinstance(data, dict) and "results" in data:
            results = data["results"]
        else:
            results = data

        if results:
            product = results[0]
            assert "id" in product
            assert "name" in product
            assert "retail_price" in product or "price" in product

    def test_admin_displays_real_catalog(self):
        """
        AC5: Проверка админки с реальным каталогом
        Валидирует что админка корректно отображает импортированные данные
        """
        from django.contrib.admin.sites import site
        from django.test import RequestFactory

        from apps.products.admin import ProductAdmin

        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
        )

        # Проверка что админка может получить список товаров
        factory = RequestFactory()
        request = factory.get("/admin/products/product/")

        product_admin = ProductAdmin(Product, site)
        queryset = product_admin.get_queryset(request)

        assert queryset.count() > 0, "Админка должна показывать импортированные товары"

        # Проверка что товары можно отобразить
        for product in queryset[:10]:
            # str() не должен падать
            product_str = str(product)
            assert (
                product_str
            ), f"Product {product.id} должен иметь строковое представление"

    def test_price_fallback_with_real_data(self):
        """
        AC2: Проверка fallback цен на реальных примерах
        Валидирует логику fallback для отсутствующих цен
        """
        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
        )

        products = Product.objects.filter(retail_price__gt=0)[:50]

        for product in products:
            # Проверка fallback для разных ролей
            # Метод get_price_for_user должен всегда возвращать цену
            retail_price = product.retail_price
            assert retail_price > 0

            # Если opt цены отсутствуют, fallback на retail
            if hasattr(product, "get_price_for_user"):
                # Создаем mock пользователя с разными ролями
                class MockUser:
                    def __init__(self, role):
                        self.role = role
                        self.is_authenticated = True

                for role in [
                    "retail",
                    "wholesale_level1",
                    "wholesale_level2",
                    "wholesale_level3",
                    "trainer",
                    "federation_rep",
                ]:
                    user = MockUser(role)
                    price = product.get_price_for_user(user)
                    assert price > 0, (
                        f"Product {product.id} должен возвращать цену "
                        f"для роли {role}"
                    )
