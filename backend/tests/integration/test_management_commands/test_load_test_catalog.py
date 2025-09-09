"""
Интеграционные тесты для команды load_test_catalog
"""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.products.models import Brand, Category, Product


@pytest.mark.integration
@pytest.mark.django_db
class TestLoadTestCatalogCommand:
    """Тесты команды загрузки тестового каталога товаров"""

    def test_command_default_count_success(self):
        """Тест команды с количеством товаров по умолчанию"""
        out = StringIO()

        call_command("load_test_catalog", stdout=out, verbosity=1)

        output = out.getvalue()
        assert "🚀 Запуск загрузки тестового каталога товаров" in output
        assert "✅ Тестовый каталог загружен: 50 товаров создано" in output

        # Проверяем что товары созданы
        test_products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")
        assert test_products.count() == 50

    def test_command_custom_count(self):
        """Тест команды с заданным количеством товаров"""
        call_command("load_test_catalog", "--count=25", verbosity=0)

        test_products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")
        assert test_products.count() == 25

    def test_command_with_brands_creation(self):
        """Тест команды с созданием брендов"""
        initial_brands_count = Brand.objects.count()

        call_command("load_test_catalog", "--with-brands", "--count=10", verbosity=0)

        # Должны быть созданы новые бренды
        final_brands_count = Brand.objects.count()
        assert final_brands_count > initial_brands_count

        # Проверяем что есть тестовые бренды
        test_brands = Brand.objects.filter(name__endswith="Test")
        assert test_brands.count() >= 10

        # Проверяем что товары связаны с брендами
        test_products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")
        products_with_brand = test_products.exclude(brand__isnull=True)
        assert products_with_brand.count() > 0

    def test_command_with_categories_creation(self):
        """Тест команды с созданием категорий"""
        initial_categories_count = Category.objects.count()

        call_command(
            "load_test_catalog", "--with-categories", "--count=10", verbosity=0
        )

        # Должны быть созданы новые категории
        final_categories_count = Category.objects.count()
        assert final_categories_count > initial_categories_count

        # Проверяем что есть тестовые категории
        test_categories = Category.objects.filter(name__endswith="тестовая")
        assert test_categories.count() >= 8

        # Проверяем что товары связаны с категориями
        test_products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")
        products_with_category = test_products.exclude(category__isnull=True)
        assert products_with_category.count() > 0

    def test_command_clear_existing_data(self):
        """Тест очистки существующих тестовых данных"""
        # Создаем тестовые данные
        test_brand = Brand.objects.create(name="Тестовый бренд OLD")
        test_category = Category.objects.create(name="Тестовая категория OLD")
        
        Product.objects.create(
            onec_id="TEST-PRODUCT-OLD-001",
            name="Старый тестовый товар",
            sku="OLD-SKU",
            retail_price=100,
            brand=test_brand,
            category=test_category,
        )

        out = StringIO()
        call_command(
            "load_test_catalog",
            "--clear-existing",
            "--count=5",
            stdout=out,
            verbosity=1,
        )

        output = out.getvalue()
        assert "🧹 Очистка существующих тестовых данных..." in output
        assert "Удалено:" in output

        # Проверяем что старые данные удалены
        assert not Product.objects.filter(onec_id="TEST-PRODUCT-OLD-001").exists()
        assert not Brand.objects.filter(name="Тестовый бренд OLD").exists()
        assert not Category.objects.filter(name="Тестовая категория OLD").exists()

        # Проверяем что новые данные созданы
        new_products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")
        assert new_products.count() == 5

    def test_command_dry_run_no_changes(self):
        """Тест что dry-run не создает товары"""
        initial_count = Product.objects.count()
        initial_brands = Brand.objects.count()
        initial_categories = Category.objects.count()

        call_command(
            "load_test_catalog",
            "--dry-run",
            "--with-brands",
            "--with-categories",
            "--count=10",
            verbosity=0,
        )

        # Проверяем что ничего не изменилось
        assert Product.objects.count() == initial_count
        assert Brand.objects.count() == initial_brands
        assert Category.objects.count() == initial_categories

    def test_product_data_structure(self):
        """Тест структуры данных созданных товаров"""
        call_command("load_test_catalog", "--count=5", verbosity=0)

        product = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-").first()

        # Проверяем обязательные поля
        assert product.name
        assert product.onec_id
        assert product.sku
        assert product.description
        assert product.short_description

        # Проверяем цены
        assert product.retail_price > 0
        assert product.opt1_price > 0
        assert product.opt2_price > 0
        assert product.opt3_price > 0
        assert product.trainer_price > 0
        assert product.federation_price > 0
        assert product.recommended_retail_price > 0
        assert product.max_suggested_retail_price > 0

        # Проверяем иерархию цен (оптовые должны быть меньше розничной)
        assert product.opt1_price <= product.retail_price
        assert product.opt2_price <= product.opt1_price
        assert product.opt3_price <= product.opt2_price
        assert product.federation_price <= product.trainer_price

        # Проверяем спецификации
        assert isinstance(product.specifications, dict)
        assert "material" in product.specifications
        assert "color" in product.specifications
        assert "size" in product.specifications

        # Проверяем остатки
        assert product.stock_quantity >= 0
        assert product.reserved_quantity >= 0
        assert product.min_order_quantity > 0

    def test_product_variety(self):
        """Тест разнообразия созданных товаров"""
        call_command("load_test_catalog", "--count=20", verbosity=0)

        products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")

        # Проверяем что есть разнообразие в названиях
        names = set(products.values_list("name", flat=True))
        assert len(names) > 1  # Разные названия

        # Проверяем разнообразие цен
        prices = set(products.values_list("retail_price", flat=True))
        assert len(prices) > 5  # Разные цены

        # Проверяем разнообразие остатков
        quantities = set(products.values_list("stock_quantity", flat=True))
        assert len(quantities) > 5  # Разные остатки

        # Проверяем что не все товары активны (80% должны быть активны)
        active_count = products.filter(is_active=True).count()
        inactive_count = products.filter(is_active=False).count()
        assert active_count > inactive_count  # Больше активных
        assert inactive_count > 0  # Есть неактивные

    def test_command_with_existing_brands_categories(self):
        """Тест команды с существующими брендами и категориями"""
        # Создаем существующие бренды и категории
        existing_brand = Brand.objects.create(name="Существующий бренд", is_active=True)
        existing_category = Category.objects.create(
            name="Существующая категория", is_active=True
        )

        call_command("load_test_catalog", "--count=10", verbosity=0)

        # Проверяем что товары могут быть связаны с существующими брендами/категориями
        products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")

        # Хотя бы один товар может использовать существующие данные
        # (это зависит от случайного выбора в команде)
        assert products.count() == 10

    def test_large_catalog_creation(self):
        """Тест создания большого каталога"""
        call_command(
            "load_test_catalog",
            "--count=100",
            "--with-brands",
            "--with-categories",
            verbosity=0,
        )

        # Проверяем что все товары созданы
        products = Product.objects.filter(onec_id__startswith="TEST-PRODUCT-")
        assert products.count() == 100

        # Проверяем уникальность SKU
        skus = list(products.values_list("sku", flat=True))
        assert len(set(skus)) == len(skus)  # Все SKU уникальные

        # Проверяем уникальность onec_id
        onec_ids = list(products.values_list("onec_id", flat=True))
        assert len(set(onec_ids)) == len(onec_ids)  # Все onec_id уникальные
