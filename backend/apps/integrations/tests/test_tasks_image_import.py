"""
Тесты для Celery задач импорта изображений.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.integrations.tasks import (
    _execute_import_type,
    _get_product_images,
    _run_image_import,
)
from apps.products.factories import ProductFactory
from apps.products.models import ImportSession, Product


@pytest.mark.unit
class TestGetProductImages:
    """Unit-тесты для функции _get_product_images."""

    def test_get_product_images_no_onec_id(self):
        """Тест: товар без onec_id возвращает пустой список."""
        product = Mock(onec_id=None)
        base_dir = Path("/fake/path")

        result = _get_product_images(product, base_dir)

        assert result == []

    @patch("pathlib.Path.exists", return_value=False)
    def test_get_product_images_missing_subdirectory(self, mock_exists):
        """Тест: отсутствующая поддиректория возвращает пустой список."""
        product = Mock(onec_id="001a16a4-b810-11ed-860f")
        base_dir = Path("/fake/path")

        result = _get_product_images(product, base_dir)

        assert result == []

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists", return_value=True)
    def test_get_product_images_finds_images(self, mock_exists, mock_glob):
        """Тест: поиск изображений для товара."""
        product = Mock(onec_id="001a16a4-b810-11ed-860f")
        base_dir = Path("/fake/path")

        # Мокировать найденные файлы
        mock_file1 = MagicMock()
        mock_file1.name = "001a16a4-b810-11ed-860f_24062354.jpg"
        mock_file1.suffix = ".jpg"

        mock_file2 = MagicMock()
        mock_file2.name = "001a16a4-b810-11ed-860f_24062355.png"
        mock_file2.suffix = ".png"

        # glob вызывается для каждого расширения
        mock_glob.return_value = [mock_file1, mock_file2]

        result = _get_product_images(product, base_dir)

        # Результат будет дублироваться для каждого расширения (*.jpg, *.jpeg, *.png)
        # Но filter по suffix гарантирует корректность
        assert len(result) > 0
        assert any("24062354.jpg" in path for path in result)
        assert any("24062355.png" in path for path in result)


@pytest.mark.unit
class TestExecuteImportTypeImages:
    """Unit-тесты для _execute_import_type с типом images."""

    @patch("apps.integrations.tasks._run_image_import")
    def test_execute_import_type_images(self, mock_run_import):
        """Тест вызова _run_image_import через _execute_import_type."""
        mock_run_import.return_value = {
            "type": "images",
            "message": "Обработано 10 товаров",
        }

        result = _execute_import_type("images", "test-task-id")

        assert result["type"] == "images"
        assert "Изображения обновлены" in result["message"]
        mock_run_import.assert_called_once_with("test-task-id")


@pytest.mark.integration
class TestRunImageImportIntegration(TestCase):
    """Интеграционные тесты импорта изображений."""

    @patch("apps.integrations.tasks.ProductDataProcessor")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("apps.integrations.tasks._get_product_images")
    def test_run_image_import_success(
        self, mock_get_images, mock_path_exists, mock_processor_class
    ):
        """Тест успешного импорта изображений."""
        # Создать товары
        products = [ProductFactory.create(onec_id=f"00{i}a16a4") for i in range(3)]

        # Создать сессию
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.IMAGES,
            status=ImportSession.ImportStatus.STARTED,
            celery_task_id="test-task-id",
        )

        # Mock _get_product_images
        mock_get_images.return_value = [
            "00/001a16a4_image1.jpg",
            "00/001a16a4_image2.jpg",
        ]

        # Mock processor
        mock_processor = mock_processor_class.return_value
        mock_processor.import_product_images.return_value = {
            "copied": 2,
            "skipped": 0,
            "errors": 0,
        }

        # Execute
        result = _run_image_import("test-task-id")

        # Reload session
        session.refresh_from_db()

        # Assert
        assert session.status == ImportSession.ImportStatus.COMPLETED
        assert session.finished_at is not None
        assert session.report_details["total_products"] == 3
        assert session.report_details["processed"] == 3
        assert session.report_details["copied"] == 6  # 3 товара * 2 изображения
        assert result["type"] == "images"
        assert "Обработано 3 товаров" in result["message"]

    @patch("pathlib.Path.exists", return_value=False)
    def test_run_image_import_missing_directory(self, mock_exists):
        """Тест ошибки при отсутствии директории import_files."""
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.IMAGES,
            status=ImportSession.ImportStatus.STARTED,
            celery_task_id="test-task-id",
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            _run_image_import("test-task-id")

        assert "import_files" in str(exc_info.value)

        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.FAILED

    @patch("apps.integrations.tasks.ProductDataProcessor")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("apps.integrations.tasks._get_product_images")
    def test_run_image_import_skips_products_without_images(
        self, mock_get_images, mock_path_exists, mock_processor_class
    ):
        """Тест пропуска товаров без изображений."""
        # Создать товары
        ProductFactory.create_batch(5)

        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.IMAGES,
            status=ImportSession.ImportStatus.STARTED,
            celery_task_id="test-task-id",
        )

        # Mock: только для 2 товаров есть изображения
        call_count = [0]

        def get_images_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                return ["00/001a16a4_image.jpg"]
            return []  # Для остальных нет изображений

        mock_get_images.side_effect = get_images_side_effect

        mock_processor = mock_processor_class.return_value
        mock_processor.import_product_images.return_value = {
            "copied": 1,
            "skipped": 0,
            "errors": 0,
        }

        # Execute
        result = _run_image_import("test-task-id")

        # Reload session
        session.refresh_from_db()

        # Assert
        assert session.status == ImportSession.ImportStatus.COMPLETED
        assert session.report_details["total_products"] == 5
        assert session.report_details["processed"] == 5
        assert session.report_details["copied"] == 2  # Только 2 товара с изображениями
        assert session.report_details["skipped"] == 3  # 3 товара без изображений
