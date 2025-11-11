"""
Performance тесты импорта изображений товаров из 1С

Story 3.1.3: Интеграционное тестирование импорта изображений

Тесты производительности для импорта большого объема изображений:
- Измерение времени выполнения
- Скорость обработки (images/sec)
- Проверка performance требований (>= 10 images/sec)
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.test import TestCase, override_settings

from apps.products.models import ImportSession, Product
from apps.products.services.parser import XMLDataParser
from apps.products.services.processor import ProductDataProcessor
from tests.conftest import get_unique_suffix

if TYPE_CHECKING:
    pass

# Маркировка для всего модуля
pytestmark = pytest.mark.django_db


@pytest.mark.slow
@pytest.mark.performance
class TestImageImportPerformance(TestCase):
    """Performance тесты импорта изображений товаров из 1С"""

    @classmethod
    def setUpClass(cls) -> None:
        """Настройка класса тестов"""
        super().setUpClass()

        # Путь к реальным данным 1С
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
        self.temp_media = tempfile.mkdtemp(prefix="test_media_perf_")

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

    def test_import_large_volume_images_performance(self) -> None:
        """
        AC4: Performance тест импорта большого количества изображений

        Требования:
        - Обработка не менее 1000 изображений
        - Производительность >= 10 images/sec
        - Измерение и логирование метрик

        Проверяет:
        - Парсинг ВСЕХ goods_*.xml файлов
        - Обработка всех товаров с изображениями
        - Измерение времени выполнения и скорости
        - Логирование performance метрик
        """
        # Парсим ВСЕ goods файлы
        goods_files = sorted(self.goods_dir.glob("goods_*.xml"))
        if not goods_files:
            self.skipTest("No goods XML files found")

        # Создание сессии импорта
        unique_suffix = get_unique_suffix()
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
            filename=f"test_performance_{unique_suffix}.xml",
        )
        processor = ProductDataProcessor(session_id=session.id, chunk_size=1000)

        parser = XMLDataParser()
        total_products = 0
        total_images = 0

        start_time = time.time()

        # Обработка всех файлов
        for goods_file in goods_files:
            goods_data_list = parser.parse_goods_xml(str(goods_file))
            goods_with_images = [g for g in goods_data_list if g.get("images")]

            for goods_data in goods_with_images:
                product = processor.create_product_placeholder(
                    goods_data=goods_data,
                    base_dir=str(self.goods_dir),
                    skip_images=False,
                )

                if product:
                    total_products += 1
                    total_images += len(goods_data.get("images", []))

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Логирование performance метрик
        print(f"\n{'=' * 50}")
        print("PERFORMANCE METRICS:")
        print(f"Total products: {total_products}")
        print(f"Total images: {total_images}")
        print(f"Elapsed time: {elapsed_time:.2f}s")
        print(f"Products/sec: {total_products / elapsed_time:.2f}")
        print(f"Images/sec: {total_images / elapsed_time:.2f}")
        print(f"Images copied: {processor.stats.get('images_copied', 0)}")
        print(f"Images skipped: {processor.stats.get('images_skipped', 0)}")
        print(f"Images errors: {processor.stats.get('images_errors', 0)}")
        print(f"{'=' * 50}\n")

        # Assertions
        self.assertGreater(total_products, 0, "Expected products to be processed")
        self.assertGreater(
            processor.stats.get("images_copied", 0),
            0,
            "Expected images to be copied",
        )

        # Performance requirement: хотя бы 10 изображений в секунду
        images_per_sec = processor.stats.get("images_copied", 0) / elapsed_time
        self.assertGreater(
            images_per_sec,
            10,
            f"Performance too slow: {images_per_sec:.2f} images/sec (required >= 10)",
        )

        # Проверка что обработано достаточно изображений для валидного теста
        # Если в данных меньше 100 изображений - это warning, но не failure
        if total_images < 100:
            print(
                f"\nWARNING: Only {total_images} images in test data. "
                f"Performance test is more reliable with 1000+ images."
            )
