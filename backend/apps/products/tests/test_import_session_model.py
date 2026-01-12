"""
Тесты модели ImportSession для проверки нового типа IMAGES.

Story 15.1: Добавление типа импорта "Изображения" в админ-панель
"""

import pytest
from django.test import TestCase

from apps.products.models import ImportSession


@pytest.mark.unit
class TestImportSessionModel(TestCase):
    """Unit-тесты модели ImportSession."""

    def test_import_type_images_choice_exists(self) -> None:
        """Проверка наличия нового типа IMAGES в enum."""
        # Проверяем, что IMAGES доступен в choices
        choices_values = [choice[0] for choice in ImportSession.ImportType.choices]
        assert "images" in choices_values

        # Проверяем human-readable название
        images_label = dict(ImportSession.ImportType.choices)["images"]
        assert images_label == "Изображения товаров"

    def test_create_session_with_images_type(self) -> None:
        """Тест создания сессии с типом IMAGES."""
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.IMAGES,
            status=ImportSession.ImportStatus.STARTED,
        )

        assert session.import_type == "images"
        assert session.get_import_type_display() == "Изображения товаров"
        assert session.status == "started"

    def test_images_type_ordering(self) -> None:
        """Проверка порядка типа IMAGES в choices (после CATALOG, перед STOCKS)."""
        choices_values = [choice[0] for choice in ImportSession.ImportType.choices]

        catalog_index = choices_values.index("catalog")
        images_index = choices_values.index("images")
        stocks_index = choices_values.index("stocks")

        # IMAGES должен быть после CATALOG и перед STOCKS
        assert catalog_index < images_index < stocks_index

    def test_all_import_types_present(self) -> None:
        """Проверка наличия всех ожидаемых типов импорта."""
        expected_types = ["catalog", "images", "stocks", "prices", "customers"]
        choices_values = [choice[0] for choice in ImportSession.ImportType.choices]

        for expected_type in expected_types:
            assert (
                expected_type in choices_values
            ), f"Тип '{expected_type}' отсутствует в choices"
