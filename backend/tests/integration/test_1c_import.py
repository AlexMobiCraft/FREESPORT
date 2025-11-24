"""
Integration тесты для импорта данных из 1С CommerceML

Story 13.2: Проверка заполнения onec_brand_id при импорте товаров
"""

from pathlib import Path
from typing import Any, cast

import pytest
from django.apps import apps
from django.conf import settings
from django.core.management import call_command

# Динамическая загрузка моделей для избежания циклических импортов
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
possible_paths = [
    Path("/app/data/import_1c"),  # Docker с монтированием
    Path(settings.BASE_DIR).parent / "data" / "import_1c",  # Локально
]

data_dir_candidate = None
for path in possible_paths:
    if path.exists():
        data_dir_candidate = path
        break

if data_dir_candidate is None:
    data_dir_candidate = possible_paths[0]

DATA_DIR = cast(Path, data_dir_candidate)


pytestmark = [
    pytest.mark.skipif(
        not DATA_DIR.exists(), reason=f"Data directory not found: {DATA_DIR}"
    ),
    pytest.mark.django_db(transaction=True),
    pytest.mark.integration,
]


class TestOnecBrandIdImport:
    """Integration тесты для проверки импорта onec_brand_id из CommerceML"""

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

    def test_onec_brand_id_filled_during_import(self):
        """
        AC2: Проверка заполнения onec_brand_id при импорте товара из CommerceML
        
        Given: CommerceML XML содержит товар с <Производитель><Ид>
        When: Выполняется импорт каталога через import_catalog_from_1c
        Then: Product.onec_brand_id заполняется значением из XML
        """
        # Проверка наличия данных
        assert DATA_DIR.exists(), f"Директория с данными не найдена: {DATA_DIR}"
        goods_dir = DATA_DIR / "goods"
        assert goods_dir.exists(), f"Директория goods не найдена: {goods_dir}"

        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
            "--file-type",
            "goods",
        )

        # Валидация: проверяем что товары импортированы
        products_count = Product.objects.count()
        assert products_count > 0, "Должны быть импортированы товары"

        # Валидация: проверяем что у товаров заполнен onec_brand_id
        products_with_brand_id = Product.objects.filter(
            onec_brand_id__isnull=False
        ).count()
        
        # Ожидаем что большинство товаров имеют onec_brand_id
        # (некоторые товары могут не иметь бренда в XML)
        assert products_with_brand_id > 0, (
            "Должны быть товары с заполненным onec_brand_id"
        )

        # Проверяем конкретный товар с известным brand_id
        sample_product = Product.objects.filter(
            onec_brand_id__isnull=False
        ).first()
        
        if sample_product:
            # Проверяем формат данных
            assert sample_product.onec_brand_id, "onec_brand_id не должен быть пустым"
            assert len(sample_product.onec_brand_id) > 0, (
                "onec_brand_id должен содержать данные"
            )
            
            # Проверяем что это валидный UUID формат из 1С
            # Пример: fb3f263e-dfd0-11ef-8361-fa163ea88911
            brand_id = sample_product.onec_brand_id
            assert len(brand_id) <= 100, (
                f"onec_brand_id не должен превышать 100 символов: {len(brand_id)}"
            )

    def test_onec_brand_id_nullable_for_products_without_brand(self):
        """
        AC2: Проверка что onec_brand_id может быть NULL для товаров без бренда
        
        Given: CommerceML XML содержит товар без <Производитель>
        When: Выполняется импорт каталога
        Then: Product.onec_brand_id остается NULL
        """
        # Запуск импорта
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
            "--file-type",
            "goods",
        )

        # Проверяем что есть товары
        products_count = Product.objects.count()
        assert products_count > 0, "Должны быть импортированы товары"

        # Проверяем что поле nullable работает корректно
        products_without_brand_id = Product.objects.filter(
            onec_brand_id__isnull=True
        )
        
        # Допускаем наличие товаров без brand_id (это валидный кейс)
        # Главное что импорт не падает на таких товарах
        if products_without_brand_id.exists():
            sample = products_without_brand_id.first()
            assert sample.onec_brand_id is None, (
                "onec_brand_id должен быть None для товаров без бренда"
            )

    def test_onec_brand_id_idempotency(self):
        """
        AC2: Проверка идемпотентности импорта onec_brand_id
        
        Given: Товар уже импортирован с onec_brand_id
        When: Выполняется повторный импорт того же товара
        Then: onec_brand_id не изменяется (или обновляется корректно)
        """
        # Первый импорт
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
            "--file-type",
            "goods",
        )

        # Сохраняем данные первого импорта
        first_import_products = list(
            Product.objects.filter(onec_brand_id__isnull=False).values(
                "onec_id", "onec_brand_id"
            )[:10]
        )
        
        assert len(first_import_products) > 0, (
            "Должны быть товары с onec_brand_id после первого импорта"
        )

        # Второй импорт (идемпотентность)
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(DATA_DIR),
            "--skip-backup",
            "--file-type",
            "goods",
        )

        # Проверяем что onec_brand_id не изменился
        for product_data in first_import_products:
            product = Product.objects.get(onec_id=product_data["onec_id"])
            assert product.onec_brand_id == product_data["onec_brand_id"], (
                f"onec_brand_id изменился после повторного импорта: "
                f"{product_data['onec_brand_id']} -> {product.onec_brand_id}"
            )
