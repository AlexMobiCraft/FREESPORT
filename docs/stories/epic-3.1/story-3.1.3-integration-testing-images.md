# Story 3.1.3: Интеграционное тестирование импорта изображений - Brownfield Enhancement

## Story Title

End-to-end интеграционное тестирование импорта изображений товаров из 1С с реальными данными

## User Story

**Как** команда разработки,
**Мы хотим** иметь полный набор интеграционных тестов для импорта изображений,
**Чтобы** гарантировать корректную работу всей цепочки импорта от XML до Django media storage на production данных.

## Story Context

### Existing System Integration

**Интегрируется с:**
- Вся цепочка импорта: XMLDataParser → ProductDataProcessor → import_catalog_from_1c команда
- Реальные данные из `data/import_1c/goods/` - XML файлы и директория `import_files/`
- Django test framework с PostgreSQL database
- Django FileSystemStorage для media файлов в тестах
- Существующие тесты Epic 3 для импорта товаров

**Технологии:**
- pytest + pytest-django для тестирования
- Django TestCase с транзакционной изоляцией
- Temporary directories для изоляции файловых операций
- Factory Boy для создания тестовых данных
- PostgreSQL для тестовой БД

**Существующий паттерн тестирования:**
```python
# Из backend/docs/testing-standards.md
# Интеграционные тесты с реальными данными
@pytest.mark.integration
class TestImportCatalogFrom1C:
    def test_full_import_workflow(self):
        # Использование реальных файлов из data/import_1c/
        pass
```

**Точки интеграции:**
1. Реальные XML файлы из `data/import_1c/goods/goods_*.xml`
2. Реальные изображения из `data/import_1c/goods/import_files/`
3. Тестовая БД PostgreSQL
4. Temporary MEDIA_ROOT для изоляции тестов

### Текущее состояние

✅ **Уже реализовано:**
- Базовые unit-тесты для XMLDataParser и ProductDataProcessor
- Интеграционные тесты импорта товаров без изображений (Epic 3)
- Фабрики для создания тестовых данных (Product, ImportSession)
- Реальные данные 1С в `data/import_1c/`

❌ **Что требуется добавить:**
1. **Интеграционные тесты полного цикла** импорта изображений
2. **Тесты с реальными данными** из production выгрузки 1С
3. **Верификация физических файлов** в media storage
4. **Edge cases тестирование** - отсутствующие файлы, дубликаты, большие объемы
5. **Performance тесты** - импорт 1000+ изображений
6. **Rollback сценарии** - восстановление после ошибок

## Acceptance Criteria

### Функциональные требования

1. **End-to-end тест полного импорта с изображениями**
   - ⚠️ Тест `test_import_catalog_with_images_full_workflow()` проходит успешно
   - ⚠️ Используются реальные XML файлы из `data/import_1c/goods/`
   - ⚠️ Используются реальные изображения из `data/import_1c/goods/import_files/`
   - ⚠️ Верифицируется создание товаров в БД с корректными путями к изображениям
   - ⚠️ Верифицируется физическое наличие файлов в temporary MEDIA_ROOT

2. **Верификация связей товар-изображение**
   - ⚠️ Первое изображение установлено как `Product.main_image`
   - ⚠️ Остальные изображения добавлены в `Product.gallery_images`
   - ⚠️ Пути в БД соответствуют физическим файлам в media storage
   - ⚠️ Товары без изображений обработаны корректно (placeholder или пустое поле)

3. **Edge cases тестирование**
   - ⚠️ Тест `test_import_with_missing_image_files()` - отсутствующие физические файлы
   - ⚠️ Тест `test_import_with_duplicate_images()` - дублирующиеся изображения
   - ⚠️ Тест `test_import_with_invalid_image_format()` - невалидные форматы файлов
   - ⚠️ Тест `test_import_products_without_images()` - товары без изображений
   - ⚠️ Тест `test_reimport_updates_images()` - повторный импорт обновляет изображения

4. **Тестирование флага --skip-images**
   - ⚠️ Тест `test_import_with_skip_images_flag()` - импорт без изображений работает
   - ⚠️ Товары создаются без копирования изображений
   - ⚠️ Статистика images_copied = 0 при использовании флага

### Требования производительности

5. **Performance тестирование**
   - ⚠️ Тест `test_import_large_volume_images()` - импорт 1000+ изображений
   - ⚠️ Время импорта измеряется и логируется
   - ⚠️ Memory usage остается в разумных пределах (<500MB)
   - ⚠️ Batch операции работают корректно

6. **Мониторинг и статистика**
   - ⚠️ ImportSession.report_details содержит корректную статистику изображений
   - ⚠️ Логи содержат информацию о копировании/пропуске/ошибках
   - ⚠️ Progress bar отображается корректно (визуальная проверка)

### Требования качества

7. **Покрытие тестами >= 90%**
   - ⚠️ Все новые методы (import_product_images, валидация) покрыты
   - ⚠️ Все критические пути импорта протестированы
   - ⚠️ Coverage report показывает >= 90% для processor.py и parser.py

8. **Тесты стабильны и воспроизводимы**
   - ⚠️ Тесты проходят в Docker с PostgreSQL
   - ⚠️ Изоляция через temporary directories - нет конфликтов между тестами
   - ⚠️ Cleanup после тестов - удаление временных файлов и данных

## Technical Notes

### Структура интеграционных тестов

**Файл тестов:** `backend/apps/products/tests/test_import_images_integration.py`

**Базовый класс теста:**

```python
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.files.storage import default_storage

from apps.products.models import Product, ImportSession
from apps.products.services.parser import XMLDataParser
from apps.products.services.processor import ProductDataProcessor


@pytest.mark.integration
class TestImportImagesIntegration(TestCase):
    """Интеграционные тесты импорта изображений товаров из 1С"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Путь к реальным данным 1С
        cls.real_data_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "import_1c"
        cls.goods_dir = cls.real_data_dir / "goods"
        cls.import_files_dir = cls.goods_dir / "import_files"

        # Проверка наличия реальных данных
        if not cls.goods_dir.exists():
            pytest.skip("Real 1C data not found in data/import_1c/goods/")

    def setUp(self):
        """Создание temporary MEDIA_ROOT для каждого теста"""
        self.temp_media = tempfile.mkdtemp(prefix="test_media_")
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media)
        self.media_override.__enter__()

    def tearDown(self):
        """Очистка temporary MEDIA_ROOT после теста"""
        self.media_override.__exit__(None, None, None)
        if os.path.exists(self.temp_media):
            shutil.rmtree(self.temp_media)

    def _count_files_in_media(self, subdirectory: str = "products") -> int:
        """Подсчет файлов в media subdirectory"""
        media_path = Path(self.temp_media) / subdirectory
        if not media_path.exists():
            return 0
        return len(list(media_path.glob("*")))

    def _verify_image_exists(self, image_path: str) -> bool:
        """Проверка физического существования изображения в media"""
        full_path = Path(self.temp_media) / image_path
        return full_path.exists() and full_path.is_file()
```

### Основной интеграционный тест

**Test 1: Полный цикл импорта с изображениями**

```python
def test_import_catalog_with_images_full_workflow(self):
    """
    End-to-end тест импорта каталога с изображениями из реальных данных 1С

    Проверяет:
    1. Парсинг goods.xml с путями изображений
    2. Копирование физических файлов в media storage
    3. Установку связей main_image и gallery_images
    4. Корректную статистику импорта
    """
    # Подготовка: Находим реальный goods.xml с изображениями
    goods_files = list(self.goods_dir.glob("goods_*.xml"))
    if not goods_files:
        self.skipTest("No goods XML files found")

    goods_file = goods_files[0]

    # Шаг 1: Парсинг XML
    parser = XMLDataParser()
    goods_data_list = parser.parse_goods_xml(str(goods_file))

    # Находим товары с изображениями
    goods_with_images = [g for g in goods_data_list if g.get("images")]
    self.assertGreater(
        len(goods_with_images), 0,
        "Expected at least one product with images in real data"
    )

    # Шаг 2: Создание сессии импорта
    session = ImportSession.objects.create(
        import_type=ImportSession.ImportType.CATALOG,
        status=ImportSession.ImportStatus.STARTED,
    )

    # Шаг 3: Обработка товаров с изображениями
    processor = ProductDataProcessor(session_id=session.id, chunk_size=100)

    for goods_data in goods_with_images[:5]:  # Ограничиваем для скорости теста
        product = processor.create_product_placeholder(
            goods_data=goods_data,
            base_dir=str(self.goods_dir),
            skip_images=False
        )

        self.assertIsNotNone(product, f"Failed to create product {goods_data.get('id')}")

        # Верификация изображений в БД
        product.refresh_from_db()

        if goods_data.get("images"):
            # Проверяем main_image
            self.assertTrue(
                product.main_image,
                f"Product {product.onec_id} should have main_image"
            )

            # Проверяем физическое существование main_image
            self.assertTrue(
                self._verify_image_exists(product.main_image),
                f"Main image file not found: {product.main_image}"
            )

            # Проверяем gallery_images
            if len(goods_data["images"]) > 1:
                self.assertGreater(
                    len(product.gallery_images), 0,
                    f"Product {product.onec_id} should have gallery images"
                )

                # Проверяем физическое существование gallery изображений
                for gallery_path in product.gallery_images:
                    self.assertTrue(
                        self._verify_image_exists(gallery_path),
                        f"Gallery image file not found: {gallery_path}"
                    )

    # Шаг 4: Верификация статистики
    self.assertGreater(
        processor.stats.get("images_copied", 0), 0,
        "Expected at least one image to be copied"
    )

    # Проверяем физическое количество файлов в media
    files_count = self._count_files_in_media("products")
    self.assertGreater(files_count, 0, "Expected files in media/products/")

    # Финализация сессии
    processor.finalize_session(status=ImportSession.ImportStatus.COMPLETED)
    session.refresh_from_db()
    self.assertEqual(session.status, ImportSession.ImportStatus.COMPLETED)
```

### Edge Cases тесты

**Test 2: Отсутствующие файлы изображений**

```python
def test_import_with_missing_image_files(self):
    """Импорт продолжается при отсутствии физических файлов изображений"""
    session = ImportSession.objects.create(
        import_type=ImportSession.ImportType.CATALOG,
        status=ImportSession.ImportStatus.STARTED,
    )
    processor = ProductDataProcessor(session_id=session.id)

    # Создаем GoodsData с несуществующими путями изображений
    goods_data = {
        "id": "test-product-123",
        "name": "Test Product",
        "images": [
            "import_files/99/nonexistent_image1.png",
            "import_files/99/nonexistent_image2.jpg"
        ]
    }

    # Импорт НЕ должен упасть с ошибкой
    product = processor.create_product_placeholder(
        goods_data=goods_data,
        base_dir=str(self.goods_dir),
        skip_images=False
    )

    self.assertIsNotNone(product)

    # Проверяем статистику ошибок
    self.assertGreater(
        processor.stats.get("images_errors", 0), 0,
        "Expected errors for missing image files"
    )

    # Товар должен быть создан, но без изображений
    product.refresh_from_db()
    # main_image может быть placeholder или пустым
```

**Test 3: Флаг --skip-images**

```python
def test_import_with_skip_images_flag(self):
    """Импорт с флагом --skip-images не копирует изображения"""
    session = ImportSession.objects.create(
        import_type=ImportSession.ImportType.CATALOG,
        status=ImportSession.ImportStatus.STARTED,
    )
    processor = ProductDataProcessor(session_id=session.id)

    # Парсим реальный товар с изображениями
    goods_files = list(self.goods_dir.glob("goods_*.xml"))
    if not goods_files:
        self.skipTest("No goods XML files found")

    parser = XMLDataParser()
    goods_data_list = parser.parse_goods_xml(str(goods_files[0]))
    goods_with_images = [g for g in goods_data_list if g.get("images")]

    if not goods_with_images:
        self.skipTest("No products with images in XML")

    goods_data = goods_with_images[0]

    # Импорт с skip_images=True
    product = processor.create_product_placeholder(
        goods_data=goods_data,
        base_dir=str(self.goods_dir),
        skip_images=True  # КЛЮЧЕВОЙ ПАРАМЕТР
    )

    self.assertIsNotNone(product)

    # Статистика изображений должна быть нулевая
    self.assertEqual(processor.stats.get("images_copied", 0), 0)
    self.assertEqual(processor.stats.get("images_skipped", 0), 0)

    # Файлы не должны быть скопированы в media
    files_count = self._count_files_in_media("products")
    self.assertEqual(files_count, 0, "No files should be copied with --skip-images")
```

### Performance тест

**Test 4: Импорт большого объема изображений**

```python
@pytest.mark.slow
def test_import_large_volume_images_performance(self):
    """Performance тест импорта большого количества изображений"""
    import time

    # Парсим ВСЕ goods файлы
    goods_files = sorted(self.goods_dir.glob("goods_*.xml"))
    if not goods_files:
        self.skipTest("No goods XML files found")

    session = ImportSession.objects.create(
        import_type=ImportSession.ImportType.CATALOG,
        status=ImportSession.ImportStatus.STARTED,
    )
    processor = ProductDataProcessor(session_id=session.id, chunk_size=1000)

    parser = XMLDataParser()
    total_products = 0
    total_images = 0

    start_time = time.time()

    for goods_file in goods_files:
        goods_data_list = parser.parse_goods_xml(str(goods_file))
        goods_with_images = [g for g in goods_data_list if g.get("images")]

        for goods_data in goods_with_images:
            processor.create_product_placeholder(
                goods_data=goods_data,
                base_dir=str(self.goods_dir),
                skip_images=False
            )
            total_products += 1
            total_images += len(goods_data.get("images", []))

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Логирование performance метрик
    print(f"\n{'='*50}")
    print(f"PERFORMANCE METRICS:")
    print(f"Total products: {total_products}")
    print(f"Total images: {total_images}")
    print(f"Elapsed time: {elapsed_time:.2f}s")
    print(f"Products/sec: {total_products / elapsed_time:.2f}")
    print(f"Images/sec: {total_images / elapsed_time:.2f}")
    print(f"Images copied: {processor.stats.get('images_copied', 0)}")
    print(f"Images skipped: {processor.stats.get('images_skipped', 0)}")
    print(f"Images errors: {processor.stats.get('images_errors', 0)}")
    print(f"{'='*50}\n")

    # Assertions
    self.assertGreater(total_products, 0)
    self.assertGreater(processor.stats.get("images_copied", 0), 0)

    # Performance requirement: хотя бы 10 изображений в секунду
    images_per_sec = processor.stats.get("images_copied", 0) / elapsed_time
    self.assertGreater(
        images_per_sec, 10,
        f"Performance too slow: {images_per_sec:.2f} images/sec"
    )
```

## Definition of Done

- [ ] **End-to-end тест полного импорта реализован** и проходит с реальными данными
- [ ] **Edge cases тесты написаны** - отсутствующие файлы, дубликаты, невалидные форматы
- [ ] **Тест флага --skip-images** проходит успешно
- [ ] **Performance тест** измеряет скорость импорта >= 10 images/sec
- [ ] **Верификация физических файлов** в media storage работает
- [ ] **Все тесты проходят в Docker** с PostgreSQL
- [ ] **Coverage >= 90%** для новой функциональности
- [ ] **Изоляция тестов** через temporary directories - нет конфликтов
- [ ] **Cleanup после тестов** - удаление временных файлов
- [ ] **Документация тестов** - docstrings и комментарии
- [ ] **CI/CD интеграция** - тесты запускаются в GitHub Actions

## Testing Strategy

### Запуск тестов

**Команды для локального запуска:**

```bash
# Все интеграционные тесты импорта изображений
docker-compose -f docker/docker-compose.test.yml run --rm backend \
    pytest apps/products/tests/test_import_images_integration.py -v

# Только быстрые тесты (без performance)
docker-compose -f docker/docker-compose.test.yml run --rm backend \
    pytest apps/products/tests/test_import_images_integration.py -v -m "not slow"

# Performance тест отдельно
docker-compose -f docker/docker-compose.test.yml run --rm backend \
    pytest apps/products/tests/test_import_images_integration.py::TestImportImagesIntegration::test_import_large_volume_images_performance -v -s

# С coverage отчетом
docker-compose -f docker/docker-compose.test.yml run --rm backend \
    pytest apps/products/tests/test_import_images_integration.py --cov=apps.products.services --cov-report=html
```

### Тестовые данные

**Используемые реальные данные:**
- `data/import_1c/goods/goods_*.xml` - XML файлы с товарами
- `data/import_1c/goods/import_files/` - директория с изображениями
- Минимум 5-10 товаров с изображениями для тестов
- Минимум 20-30 файлов изображений различных форматов

**Требования к тестовым данным:**
- Данные НЕ коммитятся в git (gitignore)
- Данные загружаются из production выгрузки 1С
- Структура соответствует CommerceML 3.1

## Dependencies

**Зависит от:**
- ✅ Story 3.1.1 - Парсинг путей изображений из XML
- ✅ Story 3.1.2 - Импорт изображений в Django media storage
- ✅ Реальные данные в `data/import_1c/goods/`

**Блокирует:**
- ⏳ Релиз Epic 3.1 в production

## Risk Mitigation

**Риск 1:** Реальные данные 1С могут отсутствовать в CI/CD

**Митигация:**
- pytest.skip() если данные не найдены
- Возможность загрузки тестовых данных из S3 в CI
- Минимальный набор синтетических данных как fallback

**Риск 2:** Performance тесты нестабильны в CI

**Митигация:**
- Маркировка как @pytest.mark.slow - опционально запускаются
- Адаптивные threshold для performance (зависят от окружения)
- Логирование метрик вместо строгих assertions

**Риск 3:** Тесты заполняют диск в CI

**Митигация:**
- Temporary directories с автоочисткой
- Ограничение количества обрабатываемых товаров в тестах
- Очистка в tearDown() даже при ошибках

**Rollback план:**
- Тесты не влияют на production данные
- Изоляция через temporary MEDIA_ROOT
- Транзакционные тесты - автоматический rollback БД

## Story Complexity

**Оценка:** 3 Story Points (средняя задача)

**Обоснование:**
- Требуется написание нескольких интеграционных тестов
- Работа с реальными данными требует тщательной верификации
- Performance тестирование добавляет сложности
- Необходима изоляция тестов через temporary directories
- Требуется интеграция с CI/CD

**Ожидаемое время:** 3-4 часа разработки тестов + 1-2 часа отладки

---

**Дата создания:** 2025-01-08
**Приоритет:** High (блокирует релиз Epic 3.1)
**Epic:** Epic 3.1 - Импорт и связь изображений товаров из 1С
**Assigned to:** QA/Developer Team
**Depends on:** Story 3.1.1, Story 3.1.2
