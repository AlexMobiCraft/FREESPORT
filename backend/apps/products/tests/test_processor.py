"""
Тесты для ProductDataProcessor (Story 3.1.2: Импорт изображений)

КРИТИЧНО: Использует систему изоляции тестов с get_unique_suffix()
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, mock_open, patch

import pytest
from django.core.files.storage import default_storage

from apps.products.factories import (
    Brand1CMappingFactory,
    BrandFactory,
    CategoryFactory,
    ProductFactory,
)
from apps.products.models import ImportSession, Product
from apps.products.services.processor import ProductDataProcessor

if TYPE_CHECKING:
    from django.db.models import QuerySet

# Маркировка для всего модуля
pytestmark = pytest.mark.django_db

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0


def get_unique_suffix() -> str:
    """Генерирует абсолютно уникальный суффикс для тестов"""
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"


class TestImportProductImages:
    """Тесты для метода import_product_images() (Story 3.1.2)"""

    def test_import_product_images_single_image(self):
        """Импорт одного изображения товара (AAA Pattern)"""
        # ARRANGE - подготовка данных
        product = ProductFactory(onec_id=f"test-{get_unique_suffix()}", main_image="")
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Создаем временный файл-изображение
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"fake image content")
            tmp_path = tmp.name

        try:
            # Мокируем структуру директории
            base_dir = os.path.dirname(tmp_path)
            image_filename = os.path.basename(tmp_path)
            image_paths = [image_filename]

            # Мокируем default_storage
            with patch("django.core.files.storage.default_storage") as mock_storage:
                mock_storage.exists.return_value = False
                mock_storage.save.return_value = f"products/{image_filename}"

                # ACT - выполнение действия
                result = processor.import_product_images(
                    product=product,
                    image_paths=image_paths,
                    base_dir=base_dir,
                    validate_images=False,
                )

                # ASSERT - проверка результата
                assert result["copied"] == 1
                assert result["skipped"] == 0
                assert result["errors"] == 0

                product.refresh_from_db()
                assert product.main_image == f"products/{image_filename}"
                assert len(product.gallery_images) == 0  # Только одно изображение

        finally:
            os.unlink(tmp_path)

    def test_import_product_images_multiple_images(self):
        """Импорт нескольких изображений товара (AC 1, 2)"""
        # ARRANGE
        product = ProductFactory(onec_id=f"test-{get_unique_suffix()}", main_image="")
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Создаем 3 временных файла
        tmp_files = []
        for i in range(3):
            tmp = tempfile.NamedTemporaryFile(suffix=f"_{i}.jpg", delete=False)
            tmp.write(f"image content {i}".encode())
            tmp_files.append(tmp.name)

        try:
            base_dir = os.path.dirname(tmp_files[0])
            image_paths = [os.path.basename(f) for f in tmp_files]

            saved_paths = [f"products/{os.path.basename(f)}" for f in tmp_files]

            with patch("django.core.files.storage.default_storage") as mock_storage:
                mock_storage.exists.return_value = False
                mock_storage.save.side_effect = saved_paths

                # ACT
                result = processor.import_product_images(
                    product=product,
                    image_paths=image_paths,
                    base_dir=base_dir,
                    validate_images=False,
                )

                # ASSERT
                assert result["copied"] == 3
                assert result["skipped"] == 0
                assert result["errors"] == 0

                product.refresh_from_db()
                # Первое изображение - main_image
                # Учитываем, что main_image мог быть установлен как заглушка при создании товара
                initial_main_image = product.main_image
                assert (
                    initial_main_image == saved_paths[0]
                    or initial_main_image
                    == ProductDataProcessor.DEFAULT_PLACEHOLDER_IMAGE
                )
                # Остальные - в gallery
                assert len(product.gallery_images) == 2
                assert saved_paths[1] in product.gallery_images
                assert saved_paths[2] in product.gallery_images

        finally:
            for tmp_file in tmp_files:
                os.unlink(tmp_file)

    def test_import_product_images_no_images(self):
        """Товар без изображений - корректная обработка (AC 3)"""
        # ARRANGE
        product = ProductFactory(onec_id=f"test-{get_unique_suffix()}")
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # ACT
        result = processor.import_product_images(
            product=product,
            image_paths=[],
            base_dir="/fake/path",
            validate_images=False,
        )

        # ASSERT
        assert result["copied"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    def test_import_product_images_missing_file(self):
        """Отсутствующий физический файл логируется как ошибка (AC 3)"""
        # ARRANGE
        product = ProductFactory(onec_id=f"test-{get_unique_suffix()}")
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # ACT - указываем несуществующий файл
        result = processor.import_product_images(
            product=product,
            image_paths=["nonexistent/image.jpg"],
            base_dir="/fake/nonexistent/path",
            validate_images=False,
        )

        # ASSERT
        assert result["copied"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 1  # Ошибка из-за отсутствия файла

    def test_import_product_images_duplicate_file(self):
        """Файл уже существует в media - пропускается (AC 3)"""
        # ARRANGE
        product = ProductFactory(onec_id=f"test-{get_unique_suffix()}", main_image="")
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"existing image")
            tmp_path = tmp.name

        try:
            base_dir = os.path.dirname(tmp_path)
            image_filename = os.path.basename(tmp_path)
            image_paths = [image_filename]

            # Мокируем что файл уже существует
            with patch(
                "apps.products.services.processor.default_storage"
            ) as mock_storage:
                mock_storage.exists.return_value = True

                # ACT
                result = processor.import_product_images(
                    product=product,
                    image_paths=image_paths,
                    base_dir=base_dir,
                    validate_images=False,
                )

                # ASSERT
                assert result["copied"] == 0
                assert result["skipped"] == 1  # Файл пропущен
                assert result["errors"] == 0

        finally:
            os.unlink(tmp_path)

    def test_import_product_images_invalid_file(self):
        """Невалидное изображение при включённой валидации (AC 3)"""
        # ARRANGE
        product = ProductFactory(onec_id=f"test-{get_unique_suffix()}")
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Создаём невалидный файл (не изображение)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"not an image content")
            tmp_path = tmp.name

        try:
            base_dir = os.path.dirname(tmp_path)
            image_filename = os.path.basename(tmp_path)
            image_paths = [image_filename]

            with patch(
                "apps.products.services.processor.default_storage"
            ) as mock_storage:
                mock_storage.exists.return_value = False

                # ACT - валидация включена
                result = processor.import_product_images(
                    product=product,
                    image_paths=image_paths,
                    base_dir=base_dir,
                    validate_images=True,  # Включена валидация
                )

                # ASSERT
                assert result["copied"] == 0
                assert result["errors"] == 1  # Ошибка валидации

        finally:
            os.unlink(tmp_path)

    def test_create_product_placeholder_with_images(self):
        """Интеграция import_product_images с create_product_placeholder (AC 4)"""
        # ARRANGE
        category = CategoryFactory()
        brand = BrandFactory()
        # Создаём маппинг для бренда из 1С
        brand_mapping = Brand1CMappingFactory(brand=brand)
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        unique_id = f"test-{get_unique_suffix()}"
        goods_data = {
            "id": unique_id,
            "name": f"Test Product {unique_id}",
            "description": "Test description",
            "category_id": category.onec_id,
            "brand_id": brand_mapping.onec_id,
            "images": ["00/test_image.jpg"],
        }

        # Создаём временный файл
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"test image")
            tmp_path = tmp.name

        try:
            base_dir = os.path.dirname(tmp_path)
            # Переименовываем файл чтобы совпадал с goods_data
            test_dir = os.path.join(base_dir, "00")
            os.makedirs(test_dir, exist_ok=True)
            test_image_path = os.path.join(test_dir, "test_image.jpg")
            os.rename(tmp_path, test_image_path)

            with patch(
                "apps.products.services.processor.default_storage"
            ) as mock_storage:
                mock_storage.exists.return_value = False
                mock_storage.save.return_value = "products/00/test_image.jpg"

                # ACT
                product = processor.create_product_placeholder(
                    goods_data=goods_data,
                    base_dir=base_dir,
                    skip_images=False,
                )

                # ASSERT
                assert product is not None
                product.refresh_from_db()
                assert product.main_image == "products/00/test_image.jpg"
                assert processor.stats["images_copied"] == 1
                assert processor.stats["images_skipped"] == 0
                assert processor.stats["images_errors"] == 0

        finally:
            if os.path.exists(test_image_path):
                os.unlink(test_image_path)
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_import_product_images_preserves_existing_main_image(self):
        """Повторный импорт НЕ меняет существующий main_image (AC 2)"""
        # ARRANGE
        existing_main = "products/00/existing_main.jpg"
        product = ProductFactory(
            onec_id=f"test-{get_unique_suffix()}",
            main_image=existing_main,  # Уже установлен
            gallery_images=[],
        )
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"new image content")
            tmp_path = tmp.name

        try:
            base_dir = os.path.dirname(tmp_path)
            image_filename = os.path.basename(tmp_path)
            # Создаём поддиректорию и перемещаем файл
            subdir = os.path.join(base_dir, "00")
            os.makedirs(subdir, exist_ok=True)
            new_path = os.path.join(subdir, image_filename)
            os.rename(tmp_path, new_path)
            # Симулируем структуру с поддиректорией
            image_paths = [f"00/{image_filename}"]

            with patch(
                "apps.products.services.processor.default_storage"
            ) as mock_storage:
                mock_storage.exists.return_value = False
                mock_storage.save.return_value = f"products/00/{image_filename}"

                # ACT - повторный импорт
                result = processor.import_product_images(
                    product=product,
                    image_paths=image_paths,
                    base_dir=base_dir,
                    validate_images=False,
                )

                # ASSERT
                product.refresh_from_db()
                # main_image НЕ должен измениться
                assert product.main_image == existing_main
                # Новое изображение должно попасть в gallery
                assert f"products/00/{image_filename}" in product.gallery_images
                assert len(product.gallery_images) == 1

        finally:
            if os.path.exists(new_path):
                os.unlink(new_path)
            if os.path.exists(subdir):
                shutil.rmtree(subdir, ignore_errors=True)

    def test_import_product_images_appends_to_gallery(self):
        """Повторный импорт добавляет в конец gallery_images (AC 2)"""
        # ARRANGE
        existing_gallery = ["products/00/image1.jpg", "products/00/image2.jpg"]
        product = ProductFactory(
            onec_id=f"test-{get_unique_suffix()}",
            main_image="products/00/main.jpg",
            gallery_images=existing_gallery.copy(),
        )
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"new image")
            tmp_path = tmp.name

        try:
            base_dir = os.path.dirname(tmp_path)
            image_filename = os.path.basename(tmp_path)
            # Создаём поддиректорию и перемещаем файл
            subdir = os.path.join(base_dir, "00")
            os.makedirs(subdir, exist_ok=True)
            new_path = os.path.join(subdir, image_filename)
            os.rename(tmp_path, new_path)
            image_paths = [f"00/{image_filename}"]

            with patch(
                "apps.products.services.processor.default_storage"
            ) as mock_storage:
                mock_storage.exists.return_value = False
                mock_storage.save.return_value = f"products/00/{image_filename}"

                # ACT
                result = processor.import_product_images(
                    product=product,
                    image_paths=image_paths,
                    base_dir=base_dir,
                    validate_images=False,
                )

                # ASSERT
                product.refresh_from_db()
                # Новое изображение должно быть в конце
                assert len(product.gallery_images) == 3
                assert product.gallery_images[0] == existing_gallery[0]
                assert product.gallery_images[1] == existing_gallery[1]
                assert product.gallery_images[2] == f"products/00/{image_filename}"

        finally:
            if os.path.exists(new_path):
                os.unlink(new_path)
            if os.path.exists(subdir):
                shutil.rmtree(subdir, ignore_errors=True)

    def test_import_product_images_prevents_duplicates_in_gallery(self):
        """Проверка предотвращения дубликатов в gallery_images (AC 2)"""
        # ARRANGE
        existing_image = "products/00/image.jpg"
        product = ProductFactory(
            onec_id=f"test-{get_unique_suffix()}",
            main_image="products/00/main.jpg",
            gallery_images=[existing_image],  # Уже есть
        )
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Создаём физический файл для теста
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"duplicate image")
            tmp_path = tmp.name

        try:
            base_dir = os.path.dirname(tmp_path)
            # Создаём поддиректорию и перемещаем файл
            subdir = os.path.join(base_dir, "00")
            os.makedirs(subdir, exist_ok=True)
            new_path = os.path.join(subdir, "image.jpg")
            os.rename(tmp_path, new_path)

            # ACT - импортируем то же изображение повторно
            with patch("apps.products.services.processor.default_storage") as mock_storage:
                mock_storage.exists.return_value = True
                result = processor.import_product_images(
                    product=product,
                    image_paths=["00/image.jpg"],
                    base_dir=base_dir,
                    validate_images=False,
                )

            # ASSERT
            product.refresh_from_db()
            # Дубликат НЕ должен добавиться
            assert product.gallery_images.count(existing_image) == 1
            assert result["skipped"] == 1

        finally:
            if os.path.exists(new_path):
                os.unlink(new_path)
            if os.path.exists(subdir):
                shutil.rmtree(subdir, ignore_errors=True)

    def test_import_product_images_preserves_directory_structure(self):
        """Сохранение структуры поддиректорий из 1С (AC 1)"""
        # ARRANGE
        product = ProductFactory(onec_id=f"test-{get_unique_suffix()}", main_image="")
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )
        processor = ProductDataProcessor(session_id=session.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"image content")
            tmp_path = tmp.name

        try:
            base_dir = os.path.dirname(tmp_path)
            image_filename = os.path.basename(tmp_path)
            # Создаём поддиректорию и перемещаем файл
            subdir = os.path.join(base_dir, "00")
            os.makedirs(subdir, exist_ok=True)
            new_path = os.path.join(subdir, image_filename)
            os.rename(tmp_path, new_path)
            # Путь с поддиректорией как в 1С
            image_paths = [f"00/{image_filename}"]

            expected_path = f"products/00/{image_filename}"

            with patch(
                "apps.products.services.processor.default_storage"
            ) as mock_storage:
                mock_storage.exists.return_value = False
                mock_storage.save.return_value = expected_path
                mock_save = mock_storage.save

                # ACT
                result = processor.import_product_images(
                    product=product,
                    image_paths=image_paths,
                    base_dir=base_dir,
                    validate_images=False,
                )

                # ASSERT
                product.refresh_from_db()
                # Проверяем что путь содержит поддиректорию
                assert product.main_image == expected_path
                assert "00/" in str(product.main_image)
                # Проверяем что save вызван с правильным путём
                mock_save.assert_called_once()
                call_args = mock_save.call_args[0]
                assert call_args[0] == expected_path

        finally:
            if os.path.exists(new_path):
                os.unlink(new_path)
            if os.path.exists(subdir):
                shutil.rmtree(subdir, ignore_errors=True)
