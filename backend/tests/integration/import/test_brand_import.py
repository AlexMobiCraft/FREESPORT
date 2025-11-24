"""
Интеграционные тесты импорта брендов с дедупликацией (Story 13.3)
"""

from __future__ import annotations

import pytest
from django.test import TestCase

from apps.products.models import Brand, Brand1CMapping, ImportSession
from apps.products.services.processor import ProductDataProcessor
from apps.products.utils.brands import normalize_brand_name


@pytest.mark.integration
@pytest.mark.django_db
class TestBrandImportDeduplication(TestCase):
    """
    Тесты дедупликации брендов при импорте из 1С
    
    Проверяет:
    - Объединение дубликатов по normalized_name
    - Создание Brand1CMapping для каждого onec_id
    - Корректность статистики импорта
    - Структурированное логирование операций
    """

    def setUp(self):
        """Настройка тестового окружения"""
        # Создаём сессию импорта
        self.session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        self.processor = ProductDataProcessor(
            session_id=self.session.id, skip_validation=True
        )

    def test_process_brands_merges_duplicates(self):
        """
        Тест объединения дубликатов брендов
        
        Импортирует "BoyBo" и "BOYBO" и проверяет:
        - Создаётся только один Brand
        - Создаются два Brand1CMapping
        - Статистика корректна
        """
        # Arrange: Подготовка тестовых данных с дубликатами
        brands_data = [
            {"id": "brand-uuid-1", "name": "BoyBo"},
            {"id": "brand-uuid-2", "name": "BOYBO"},
        ]

        # Act: Импорт брендов
        result = self.processor.process_brands(brands_data)

        # Assert: Проверка результатов
        # 1. Создан только один бренд (дубликаты объединены)
        assert Brand.objects.count() == 1
        brand = Brand.objects.first()
        assert brand is not None
        assert normalize_brand_name(brand.name) == "boybo"

        # 2. Созданы два маппинга (по одному на каждый onec_id)
        assert Brand1CMapping.objects.count() == 2
        mapping1 = Brand1CMapping.objects.get(onec_id="brand-uuid-1")
        mapping2 = Brand1CMapping.objects.get(onec_id="brand-uuid-2")
        assert mapping1.brand == brand
        assert mapping2.brand == brand
        assert mapping1.onec_name == "BoyBo"
        assert mapping2.onec_name == "BOYBO"

        # 3. Статистика корректна
        assert result["brands_created"] == 1
        assert result["mappings_created"] == 2
        assert result["mappings_updated"] == 0

    def test_process_brands_idempotent_reimport(self):
        """
        Тест идемпотентности повторного импорта
        
        Повторный импорт тех же данных должен:
        - Не создавать новые бренды
        - Обновлять существующие маппинги
        - Корректно отражать это в статистике
        """
        # Arrange: Первый импорт
        brands_data = [
            {"id": "brand-uuid-1", "name": "Nike"},
            {"id": "brand-uuid-2", "name": "NIKE"},
        ]
        first_result = self.processor.process_brands(brands_data)

        # Сохраняем начальное состояние
        initial_brand_count = Brand.objects.count()
        initial_mapping_count = Brand1CMapping.objects.count()

        # Act: Повторный импорт тех же данных
        second_result = self.processor.process_brands(brands_data)

        # Assert: Проверка идемпотентности
        # 1. Количество брендов не изменилось
        assert Brand.objects.count() == initial_brand_count
        assert Brand.objects.count() == 1

        # 2. Количество маппингов не изменилось
        assert Brand1CMapping.objects.count() == initial_mapping_count
        assert Brand1CMapping.objects.count() == 2

        # 3. Статистика второго импорта показывает только обновления
        assert second_result["brands_created"] == 0
        assert second_result["mappings_created"] == 0
        assert second_result["mappings_updated"] == 2

        # 4. Первый импорт создал бренды и маппинги
        assert first_result["brands_created"] == 1
        assert first_result["mappings_created"] == 2

    def test_process_brands_case_insensitive_merge(self):
        """
        Тест объединения брендов с разным регистром
        
        Проверяет что "adidas", "Adidas", "ADIDAS" объединяются в один бренд
        """
        # Arrange
        brands_data = [
            {"id": "brand-uuid-1", "name": "adidas"},
            {"id": "brand-uuid-2", "name": "Adidas"},
            {"id": "brand-uuid-3", "name": "ADIDAS"},
        ]

        # Act
        result = self.processor.process_brands(brands_data)

        # Assert
        assert Brand.objects.count() == 1
        assert Brand1CMapping.objects.count() == 3
        assert result["brands_created"] == 1
        assert result["mappings_created"] == 3

        # Все маппинги указывают на один бренд
        brand = Brand.objects.first()
        assert brand is not None
        mappings = Brand1CMapping.objects.all()
        for mapping in mappings:
            assert mapping.brand == brand

    def test_process_brands_whitespace_normalization(self):
        """
        Тест нормализации пробелов в названиях брендов
        
        "Under Armour" и "UnderArmour" должны объединяться
        """
        # Arrange
        brands_data = [
            {"id": "brand-uuid-1", "name": "Under Armour"},
            {"id": "brand-uuid-2", "name": "UnderArmour"},
        ]

        # Act
        result = self.processor.process_brands(brands_data)

        # Assert
        assert Brand.objects.count() == 1
        assert Brand1CMapping.objects.count() == 2
        assert result["brands_created"] == 1
        assert result["mappings_created"] == 2

    def test_process_brands_special_chars_normalization(self):
        """
        Тест нормализации специальных символов
        
        "Nike-Pro" и "Nike Pro" должны объединяться
        """
        # Arrange
        brands_data = [
            {"id": "brand-uuid-1", "name": "Nike-Pro"},
            {"id": "brand-uuid-2", "name": "Nike Pro"},
        ]

        # Act
        result = self.processor.process_brands(brands_data)

        # Assert
        assert Brand.objects.count() == 1
        assert Brand1CMapping.objects.count() == 2

    def test_process_brands_unique_slug_generation(self):
        """
        Тест генерации уникальных slug при конфликтах
        
        Если slug уже занят, должен добавляться числовой суффикс
        """
        # Arrange: Создаём бренд с занятым slug
        existing_brand = Brand.objects.create(
            name="Existing Brand",
            slug="test-brand",
            is_active=True,
        )

        # Импортируем бренд с таким же базовым slug
        brands_data = [
            {"id": "brand-uuid-1", "name": "Test Brand"},
        ]

        # Act
        result = self.processor.process_brands(brands_data)

        # Assert
        assert Brand.objects.count() == 2
        new_brand = Brand.objects.exclude(id=existing_brand.id).first()
        assert new_brand is not None
        assert new_brand.slug != existing_brand.slug
        assert new_brand.slug.startswith("test-brand-")

    def test_process_brands_empty_data(self):
        """
        Тест обработки пустого списка брендов
        """
        # Arrange
        brands_data = []

        # Act
        result = self.processor.process_brands(brands_data)

        # Assert
        assert result["brands_created"] == 0
        assert result["mappings_created"] == 0
        assert result["mappings_updated"] == 0

    def test_process_brands_missing_fields(self):
        """
        Тест обработки брендов с отсутствующими полями
        
        Бренды без id или name должны пропускаться
        """
        # Arrange
        brands_data = [
            {"id": "brand-uuid-1"},  # Нет name
            {"name": "Nike"},  # Нет id
            {"id": "brand-uuid-2", "name": "Adidas"},  # Корректный
        ]

        # Act
        result = self.processor.process_brands(brands_data)

        # Assert
        # Только один корректный бренд должен быть создан
        assert Brand.objects.count() == 1
        assert Brand1CMapping.objects.count() == 1
        assert result["brands_created"] == 1
        assert result["mappings_created"] == 1

    def test_process_brands_update_onec_name(self):
        """
        Тест обновления onec_name при изменении в 1С
        
        Если название бренда в 1С изменилось, onec_name в маппинге должен обновиться
        """
        # Arrange: Первый импорт
        brands_data = [
            {"id": "brand-uuid-1", "name": "Old Name"},
        ]
        self.processor.process_brands(brands_data)

        # Act: Повторный импорт с изменённым названием
        brands_data_updated = [
            {"id": "brand-uuid-1", "name": "New Name"},
        ]
        result = self.processor.process_brands(brands_data_updated)

        # Assert
        mapping = Brand1CMapping.objects.get(onec_id="brand-uuid-1")
        assert mapping.onec_name == "New Name"
        assert result["mappings_updated"] == 1

    def test_process_brands_cyrillic_names(self):
        """
        Тест обработки брендов с кириллическими названиями
        
        "Рокки" и "РОККИ" должны объединяться
        """
        # Arrange
        brands_data = [
            {"id": "brand-uuid-1", "name": "Рокки"},
            {"id": "brand-uuid-2", "name": "РОККИ"},
        ]

        # Act
        result = self.processor.process_brands(brands_data)

        # Assert
        assert Brand.objects.count() == 1
        assert Brand1CMapping.objects.count() == 2
        brand = Brand.objects.first()
        assert brand is not None
        assert normalize_brand_name(brand.name) == normalize_brand_name("Рокки")
