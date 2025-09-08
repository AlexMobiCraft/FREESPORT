"""
Интеграционные тесты для команды import_catalog_from_1c
"""

import json
import tempfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.products.models import Product, Brand, Category


@pytest.mark.integration
@pytest.mark.django_db
class TestImportCatalogFrom1CCommand:
    """Тесты команды импорта каталога товаров из 1С"""
    
    def test_command_with_mock_data_success(self):
        """Тест команды с тестовыми данными"""
        out = StringIO()
        
        call_command(
            'import_catalog_from_1c',
            '--mock-data',
            '--dry-run',
            stdout=out,
            verbosity=1
        )
        
        output = out.getvalue()
        assert '🚀 Запуск импорта каталога товаров из 1С' in output
        assert '📦 Загружены тестовые данные: 20 товаров' in output
        assert '✅ DRY-RUN завершен: 20 товаров обработано' in output
    
    def test_command_creates_products_with_mock_data(self):
        """Тест создания товаров с тестовыми данными"""
        initial_count = Product.objects.count()
        
        call_command(
            'import_catalog_from_1c',
            '--mock-data',
            verbosity=0
        )
        
        final_count = Product.objects.count()
        assert final_count > initial_count
        
        # Проверяем созданные товары
        test_products = Product.objects.filter(onec_id__startswith='1C-PRODUCT-')
        assert test_products.count() == 20
        
        # Проверяем конкретный товар
        first_product = test_products.get(onec_id='1C-PRODUCT-00001')
        assert first_product.name == 'Товар тестовый #1'
        assert first_product.sku == 'SKU-00001'
        assert first_product.sync_status == 'synced'
        assert first_product.retail_price > 0
    
    def test_command_creates_brands_and_categories(self):
        """Тест создания брендов и категорий"""
        initial_brands = Brand.objects.count()
        initial_categories = Category.objects.count()
        
        call_command(
            'import_catalog_from_1c',
            '--mock-data',
            verbosity=0
        )
        
        # Должны быть созданы бренды и категории
        assert Brand.objects.count() > initial_brands
        assert Category.objects.count() > initial_categories
        
        # Проверяем что товары связаны с брендами и категориями
        test_products = Product.objects.filter(onec_id__startswith='1C-PRODUCT-')
        products_with_brand = test_products.exclude(brand__isnull=True).count()
        products_with_category = test_products.exclude(category__isnull=True).count()
        
        assert products_with_brand > 0
        assert products_with_category > 0
    
    def test_command_with_json_file_success(self):
        """Тест команды с JSON файлом"""
        # Создаем временный JSON файл
        test_data = {
            "products": [
                {
                    "onec_id": "JSON-TEST-001",
                    "name": "Тестовый товар из JSON",
                    "brand": "Test Brand",
                    "category": "Test Category",
                    "sku": "JSON-SKU-001",
                    "stock_quantity": 10,
                    "prices": {
                        "retail_price": "1000.00",
                        "opt1_price": "900.00"
                    }
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, ensure_ascii=False)
            json_file_path = f.name
        
        try:
            call_command(
                'import_catalog_from_1c',
                f'--file={json_file_path}',
                verbosity=0
            )
            
            # Проверяем что товар создан
            product = Product.objects.get(onec_id='JSON-TEST-001')
            assert product.name == 'Тестовый товар из JSON'
            assert product.sku == 'JSON-SKU-001'
            assert product.stock_quantity == 10
            assert product.retail_price == 1000
            
        finally:
            Path(json_file_path).unlink()
    
    def test_command_with_invalid_json_file_fails(self):
        """Тест команды с некорректным JSON файлом"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json content')
            json_file_path = f.name
        
        try:
            with pytest.raises(CommandError, match='Ошибка парсинга JSON'):
                call_command(
                    'import_catalog_from_1c',
                    f'--file={json_file_path}',
                    verbosity=0
                )
        finally:
            Path(json_file_path).unlink()
    
    def test_command_with_nonexistent_file_fails(self):
        """Тест команды с несуществующим файлом"""
        with pytest.raises(CommandError, match='Файл не найден'):
            call_command(
                'import_catalog_from_1c',
                '--file=/nonexistent/file.json',
                verbosity=0
            )
    
    def test_command_xml_not_implemented(self):
        """Тест что XML парсер не реализован"""
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<xml>test</xml>')
            xml_file_path = f.name
        
        try:
            with pytest.raises(CommandError, match='XML парсер будет реализован'):
                call_command(
                    'import_catalog_from_1c',
                    f'--file={xml_file_path}',
                    verbosity=0
                )
        finally:
            Path(xml_file_path).unlink()
    
    def test_command_without_parameters_fails(self):
        """Тест команды без обязательных параметров"""
        with pytest.raises(CommandError, match='Укажите либо --file'):
            call_command(
                'import_catalog_from_1c',
                verbosity=0
            )
    
    def test_command_dry_run_no_changes(self):
        """Тест что dry-run не создает товары"""
        initial_count = Product.objects.count()
        
        call_command(
            'import_catalog_from_1c',
            '--mock-data',
            '--dry-run',
            verbosity=0
        )
        
        final_count = Product.objects.count()
        assert final_count == initial_count  # Нет изменений
    
    def test_command_force_overwrites_existing(self):
        """Тест что --force перезаписывает существующие товары"""
        # Создаем тестовый товар
        product = Product.objects.create(
            onec_id='1C-PRODUCT-00001',
            name='Старое название',
            sku='OLD-SKU',
            retail_price=500
        )
        
        call_command(
            'import_catalog_from_1c',
            '--mock-data',
            '--force',
            verbosity=0
        )
        
        # Проверяем что товар обновился
        product.refresh_from_db()
        assert product.name == 'Товар тестовый #1'
        assert product.sku == 'SKU-00001'
        assert product.retail_price == 1100  # Из mock данных
    
    def test_command_without_force_skips_existing(self):
        """Тест что без --force существующие товары пропускаются"""
        # Создаем тестовый товар
        original_name = 'Оригинальное название'
        product = Product.objects.create(
            onec_id='1C-PRODUCT-00001',
            name=original_name,
            sku='ORIGINAL-SKU',
            retail_price=500
        )
        
        out = StringIO()
        call_command(
            'import_catalog_from_1c',
            '--mock-data',
            stdout=out,
            verbosity=0
        )
        
        # Проверяем что товар НЕ изменился
        product.refresh_from_db()
        assert product.name == original_name
        assert product.sku == 'ORIGINAL-SKU'
        assert product.retail_price == 500
    
    def test_command_with_chunk_size(self):
        """Тест команды с настройкой размера батча"""
        out = StringIO()
        
        call_command(
            'import_catalog_from_1c',
            '--mock-data',
            '--chunk-size=5',
            '--dry-run',
            stdout=out,
            verbosity=1
        )
        
        output = out.getvalue()
        assert '✅ DRY-RUN завершен: 20 товаров обработано' in output