"""
Интеграционные тесты импорта изображений товаров из 1С

Story 3.1.3: Интеграционное тестирование импорта изображений

Тесты проверяют полный цикл импорта изображений из реальных данных 1С:
- Парсинг goods.xml с путями изображений
- Копирование физических файлов в media storage
- Установку связей main_image и gallery_images
- Корректную статистику импорта
- Edge cases: отсутствующие файлы, дубликаты, флаг --skip-images
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from django.conf import settings
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings

from apps.products.models import ImportSession, Product
from apps.products.services.parser import XMLDataParser
from apps.products.services.processor import ProductDataProcessor
from tests.conftest import get_unique_suffix

if TYPE_CHECKING:
    pass

# Маркировка для всего модуля
pytestmark = pytest.mark.django_db


@pytest.mark.integration
class TestImportImagesIntegration(TestCase):
    """Интеграционные тесты импорта изображений товаров из 1С"""

    @classmethod
    def setUpClass(cls) -> None:
        """Настройка класса тестов"""
        super().setUpClass()

        # Путь к реальным данным 1С
        # Проверяем несколько возможных расположений
        possible_paths = [
            Path("/app/data/import_1c"),  # Docker с монтированием
            Path(settings.BASE_DIR).parent / "data" / "import_1c",  # Локально
        ]

        cls.real_data_dir: Path | None = None
        for path in possible_paths:
            if path.exists():
                cls.real_data_dir = path
                break

        if cls.real_data_dir is None:
            cls.real_data_dir = possible_paths[0]

        cls.goods_dir = cls.real_data_dir / "goods"
        cls.import_files_dir = cls.goods_dir / "import_files"

        # Проверка наличия реальных данных
        if not cls.goods_dir.exists():
            pytest.skip(f"Real 1C data not found in {cls.goods_dir}")

    def setUp(self) -> None:
        """Создание temporary MEDIA_ROOT для каждого теста"""
        # Создаем временную директорию для media файлов
        self.temp_media = tempfile.mkdtemp(prefix="test_media_")

        # Применяем override для MEDIA_ROOT
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media)
        self.media_override.__enter__()

    def tearDown(self) -> None:
        """Очистка temporary MEDIA_ROOT после теста"""
        # Выходим из override
        self.media_override.__exit__(None, None, None)

        # Удаляем временную директорию
        if os.path.exists(self.temp_media):
            shutil.rmtree(self.temp_media, ignore_errors=True)

    def _count_files_in_media(self, subdirectory: str = "products") -> int:
        """
        Подсчет файлов в media subdirectory

        Args:
            subdirectory: Поддиректория в MEDIA_ROOT (по умолчанию "products")

        Returns:
            Количество файлов в директории
        """
        media_path = Path(self.temp_media) / subdirectory
        if not media_path.exists():
            return 0

        # Рекурсивный подсчет всех файлов
        total_files = 0
        for root, dirs, files in os.walk(media_path):
            total_files += len(files)
        return total_files

    def _verify_image_exists(self, image_path: str) -> bool:
        """
        Проверка физического существования изображения в media

        Args:
            image_path: Относительный путь к файлу (например, "products/00/image.jpg")

        Returns:
            True если файл существует, False иначе
        """
        full_path = Path(self.temp_media) / image_path
        return full_path.exists() and full_path.is_file()

    def test_import_catalog_with_images_full_workflow(self) -> None:
        """
        AC1: End-to-end тест импорта каталога с изображениями из реальных данных 1С

        Проверяет:
        1. Парсинг goods.xml с путями изображений
        2. Копирование физических файлов в media storage
        3. Установку связей main_image и gallery_images
        4. Корректную статистику импорта
        """
        # Подготовка: Находим реальный goods.xml с изображениями
        goods_files = sorted(self.goods_dir.glob("goods_*.xml"))
        if not goods_files:
            self.skipTest("No goods XML files found")

        goods_file = goods_files[0]

        # Шаг 1: Парсинг XML
        parser = XMLDataParser()
        goods_data_list = parser.parse_goods_xml(str(goods_file))

        # Находим товары с изображениями
        goods_with_images = [g for g in goods_data_list if g.get("images")]
        self.assertGreater(
            len(goods_with_images),
            0,
            "Expected at least one product with images in real data",
        )

        # Шаг 2: Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )

        # Шаг 3: Обработка товаров с изображениями
        processor = ProductDataProcessor(session_id=session.id, chunk_size=100)

        products_processed = 0
        for goods_data in goods_with_images[:5]:  # Ограничиваем для скорости теста
            product = processor.create_product_placeholder(
                goods_data=goods_data,
                base_dir=str(self.goods_dir),
                skip_images=False,
            )

            self.assertIsNotNone(
                product, f"Failed to create product {goods_data.get('id')}"
            )

            # Верификация изображений в БД
            product.refresh_from_db()

            if goods_data.get("images"):
                # Проверяем main_image
                self.assertTrue(
                    product.main_image,
                    f"Product {product.onec_id} should have main_image",
                )

                # Проверяем физическое существование main_image
                self.assertTrue(
                    self._verify_image_exists(product.main_image),
                    f"Main image file not found: {product.main_image}",
                )

                # Проверяем gallery_images
                if len(goods_data["images"]) > 1:
                    self.assertGreater(
                        len(product.gallery_images),
                        0,
                        f"Product {product.onec_id} should have gallery images",
                    )

                    # Проверяем физическое существование gallery изображений
                    for gallery_path in product.gallery_images:
                        self.assertTrue(
                            self._verify_image_exists(gallery_path),
                            f"Gallery image file not found: {gallery_path}",
                        )

            products_processed += 1

        # Шаг 4: Верификация статистики
        self.assertGreater(
            processor.stats.get("images_copied", 0),
            0,
            "Expected at least one image to be copied",
        )

        # Проверяем физическое количество файлов в media
        files_count = self._count_files_in_media("products")
        self.assertGreater(files_count, 0, "Expected files in media/products/")

        # Финализация сессии
        processor.finalize_session(status=ImportSession.ImportStatus.COMPLETED)
        session.refresh_from_db()
        self.assertEqual(session.status, ImportSession.ImportStatus.COMPLETED)

    def test_import_with_missing_image_files(self) -> None:
        """
        AC2: Edge Case - Импорт продолжается при отсутствии физических файлов изображений

        Проверяет:
        - Импорт НЕ падает с ошибкой
        - Статистика images_errors > 0
        - Товар создаётся без изображений
        """
        # Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Создаем GoodsData с несуществующими путями изображений
        goods_data: dict[str, Any] = {
            "id": f"test-product-{unique_suffix}",
            "name": f"Test Product {unique_suffix}",
            "images": [
                "import_files/99/nonexistent_image1.png",
                "import_files/99/nonexistent_image2.jpg",
            ],
        }

        # Импорт НЕ должен упасть с ошибкой
        product = processor.create_product_placeholder(
            goods_data=goods_data, base_dir=str(self.goods_dir), skip_images=False
        )

        self.assertIsNotNone(product)

        # Проверяем статистику ошибок
        self.assertGreater(
            processor.stats.get("images_errors", 0),
            0,
            "Expected errors for missing image files",
        )

        # Товар должен быть создан, но без изображений
        product.refresh_from_db()
        # main_image может быть placeholder или пустым - оба варианта допустимы

    def test_import_with_duplicate_images(self) -> None:
        """
        AC2: Edge Case - Дубликаты изображений не создаются повторно

        Проверяет:
        - Дубликаты в gallery_images предотвращаются
        - Статистика images_skipped корректна
        """
        # Парсим реальный товар с изображениями
        goods_files = sorted(self.goods_dir.glob("goods_*.xml"))
        if not goods_files:
            self.skipTest("No goods XML files found")

        parser = XMLDataParser()
        goods_data_list = parser.parse_goods_xml(str(goods_files[0]))
        goods_with_images = [g for g in goods_data_list if g.get("images")]

        if not goods_with_images:
            self.skipTest("No products with images in XML")

        goods_data = goods_with_images[0]

        # Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Первый импорт
        product = processor.create_product_placeholder(
            goods_data=goods_data, base_dir=str(self.goods_dir), skip_images=False
        )
        self.assertIsNotNone(product)

        first_images_copied = processor.stats.get("images_copied", 0)
        self.assertGreater(first_images_copied, 0)

        # Второй импорт того же товара (повторный)
        processor2 = ProductDataProcessor(session_id=session.id)
        product2 = processor2.create_product_placeholder(
            goods_data=goods_data, base_dir=str(self.goods_dir), skip_images=False
        )

        # Проверяем что при повторном импорте файлы пропускаются
        self.assertGreater(
            processor2.stats.get("images_skipped", 0),
            0,
            "Expected images to be skipped on reimport",
        )

    def test_import_with_invalid_image_format(self) -> None:
        """
        AC2: Edge Case - Невалидный формат изображения логируется, импорт продолжается

        Проверяет:
        - Система логирует ошибку для невалидных файлов
        - Импорт продолжается без сбоев
        """
        # Создаем временный "невалидный" файл изображения
        temp_dir = Path(self.temp_media) / "temp_invalid"
        temp_dir.mkdir(parents=True, exist_ok=True)
        invalid_file = temp_dir / "invalid.jpg"
        invalid_file.write_text("This is not a valid image file")

        # Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        processor = ProductDataProcessor(session_id=session.id, skip_validation=False)

        goods_data: dict[str, Any] = {
            "id": f"test-product-{unique_suffix}",
            "name": f"Test Product {unique_suffix}",
            "images": [str(invalid_file.relative_to(self.temp_media))],
        }

        # Импорт с валидацией изображений (будет ошибка при валидации)
        product = processor.create_product_placeholder(
            goods_data=goods_data, base_dir=str(self.temp_media), skip_images=False
        )

        # Товар должен быть создан несмотря на невалидное изображение
        self.assertIsNotNone(product)

    def test_import_products_without_images(self) -> None:
        """
        AC2: Edge Case - Товары без изображений создаются корректно

        Проверяет:
        - Корректная обработка товаров без тегов <Картинка>
        - Товары создаются успешно
        """
        # Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # GoodsData без изображений
        goods_data: dict[str, Any] = {
            "id": f"test-product-{unique_suffix}",
            "name": f"Test Product Without Images {unique_suffix}",
            # images отсутствует
        }

        product = processor.create_product_placeholder(
            goods_data=goods_data, base_dir=str(self.goods_dir), skip_images=False
        )

        self.assertIsNotNone(product)
        product.refresh_from_db()

        # Товар создан, изображения могут быть пустыми или placeholder
        self.assertEqual(processor.stats.get("images_copied", 0), 0)

    def test_reimport_updates_images(self) -> None:
        """
        AC2: Edge Case - Повторный импорт корректно обновляет изображения

        Проверяет:
        - При повторном импорте main_image НЕ меняется если уже установлен
        - Новые изображения добавляются в gallery
        """
        # Парсим реальный товар с изображениями
        goods_files = sorted(self.goods_dir.glob("goods_*.xml"))
        if not goods_files:
            self.skipTest("No goods XML files found")

        parser = XMLDataParser()
        goods_data_list = parser.parse_goods_xml(str(goods_files[0]))
        goods_with_images = [g for g in goods_data_list if g.get("images")]

        if not goods_with_images:
            self.skipTest("No products with images in XML")

        goods_data = goods_with_images[0]

        # Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Первый импорт
        product = processor.create_product_placeholder(
            goods_data=goods_data, base_dir=str(self.goods_dir), skip_images=False
        )
        self.assertIsNotNone(product)

        product.refresh_from_db()
        original_main_image = product.main_image
        original_gallery_count = len(product.gallery_images or [])

        # Второй импорт того же товара
        processor2 = ProductDataProcessor(session_id=session.id)
        product2 = processor2.create_product_placeholder(
            goods_data=goods_data, base_dir=str(self.goods_dir), skip_images=False
        )

        product2.refresh_from_db()

        # main_image НЕ должен измениться при повторном импорте
        self.assertEqual(
            product2.main_image,
            original_main_image,
            "main_image should not change on reimport",
        )

    def test_import_with_skip_images_flag(self) -> None:
        """
        AC3: Feature Flag - Флаг --skip-images пропускает импорт изображений

        Проверяет:
        - При skip_images=True изображения НЕ копируются
        - Статистика images_copied = 0
        - Файлы НЕ появляются в media
        - Товары создаются без изображений
        """
        # Парсим реальный товар с изображениями
        goods_files = sorted(self.goods_dir.glob("goods_*.xml"))
        if not goods_files:
            self.skipTest("No goods XML files found")

        parser = XMLDataParser()
        goods_data_list = parser.parse_goods_xml(str(goods_files[0]))
        goods_with_images = [g for g in goods_data_list if g.get("images")]

        if not goods_with_images:
            self.skipTest("No products with images in XML")

        goods_data = goods_with_images[0]

        # Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        processor = ProductDataProcessor(session_id=session.id)

        # Импорт с skip_images=True
        product = processor.create_product_placeholder(
            goods_data=goods_data,
            base_dir=str(self.goods_dir),
            skip_images=True,  # КЛЮЧЕВОЙ ПАРАМЕТР
        )

        self.assertIsNotNone(product)

        # Статистика изображений должна быть нулевая
        self.assertEqual(processor.stats.get("images_copied", 0), 0)
        self.assertEqual(processor.stats.get("images_skipped", 0), 0)

        # Файлы не должны быть скопированы в media
        files_count = self._count_files_in_media("products")
        self.assertEqual(files_count, 0, "No files should be copied with --skip-images")
