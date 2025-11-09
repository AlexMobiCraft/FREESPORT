# Story 3.1.3: Интеграционное тестирование импорта изображений - Brownfield Enhancement

## Status

Ready

## Business Value

**Why is this important?**
Эта история критически важна для обеспечения стабильности и надежности ключевой функции импорта каталога. Корректное отображение изображений напрямую влияет на пользовательский опыт и конверсию. Создание полного набора тестов защитит нас от будущих регрессий, снизит риски при развертывании и гарантирует, что данные о товарах всегда будут представлены верно.

## Story

**As a** команда разработки,
**I want to** создать полный набор интеграционных тестов для импорта изображений,
**so that** мы можем гарантировать надежность всей цепочки импорта, предотвратить будущие регрессии и обеспечить корректное отображение изображений товаров для конечных пользователей.

## Acceptance Criteria

### AC 1: Happy Path - Сценарий успешного импорта
- [ ] **E2E тест полного цикла:** Реализован и успешно проходит тест `test_import_catalog_with_images_full_workflow()`, использующий реальные XML и файлы изображений из `data/import_1c/goods/`.
- [ ] **Верификация в БД:** Тест подтверждает, что для товаров корректно заполняются поля `main_image` и `gallery_images`.
- [ ] **Верификация в хранилище:** Тест проверяет, что файлы изображений физически скопированы в тестовый `MEDIA_ROOT`.
- [ ] **Корректность связей:** Первое изображение из XML становится `main_image`, остальные попадают в `gallery_images`.

### AC 2: Edge Cases - Обработка пограничных случаев
- [ ] **Отсутствующие файлы:** Тест `test_import_with_missing_image_files()` подтверждает, что импорт не падает, а в статистике `images_errors` > 0.
- [ ] **Дубликаты изображений:** Тест `test_import_with_duplicate_images()` проверяет, что дубликаты не создаются, а счетчик `images_skipped` корректен.
- [ ] **Невалидный формат:** Тест `test_import_with_invalid_image_format()` проверяет, что система логирует ошибку, но продолжает импорт.
- [ ] **Товары без изображений:** Тест `test_import_products_without_images()` подтверждает корректное создание товаров без тега `<Картинка>`.
- [ ] **Повторный импорт:** Тест `test_reimport_updates_images()` гарантирует, что при повторном импорте изображения корректно обновляются.

### AC 3: Feature Flags - Функциональные флаги
- [ ] **Флаг `--skip-images`:** Тест `test_import_with_skip_images_flag()` подтверждает, что при установленном флаге изображения не копируются, а `images_copied = 0`.

### AC 4: Non-Functional Requirements (NFR)
- [ ] **Производительность:** Реализован и проходит performance-тест `test_import_large_volume_images()` (не менее 1000 изображений), который измеряет и логирует время выполнения. Производительность должна быть не ниже 10 изображений/сек.
- [ ] **Покрытие кода:** Инструменты анализа (например, `pytest-cov`) показывают покрытие не менее 90% для критических модулей `processor.py` и `parser.py`.
- [ ] **Стабильность и изоляция:** Все тесты стабильно проходят в Docker-окружении с PostgreSQL и используют временные директории для `MEDIA_ROOT` для полной изоляции.
- [ ] **Статистика и мониторинг:** По завершении импорта `ImportSession.report_details` содержит корректную статистику по скопированным, пропущенным и ошибочным изображениям.

## Tasks / Subtasks

### Подготовка тестовой инфраструктуры

- [ ] **Настроить структуру интеграционных тестов** (AC: 8)
  - [ ] Создать файл `backend/tests/integration/test_import_images_integration.py`
  - [ ] Реализовать базовый класс `TestImportImagesIntegration` с setUp/tearDown
  - [ ] Настроить temporary MEDIA_ROOT для изоляции тестов
  - [ ] Проверить наличие реальных данных в `data/import_1c/goods/`
  - [ ] Реализовать helper методы `_count_files_in_media()` и `_verify_image_exists()`

### Основные функциональные тесты

- [ ] **Реализовать основной E2E тест импорта** (AC: 1, 2)
  - [ ] Написать `test_import_catalog_with_images_full_workflow()`
  - [ ] Парсинг реальных XML файлов с изображениями
  - [ ] Создание ImportSession и обработка товаров через ProductDataProcessor
  - [ ] Верификация main_image и gallery_images в БД
  - [ ] Проверка физического существования файлов в temporary MEDIA_ROOT
  - [ ] Проверка статистики processor.stats (images_copied, images_skipped, images_errors)

### Edge Cases тестирование

- [ ] **Реализовать Edge Cases тесты** (AC: 3)
  - [ ] Написать `test_import_with_missing_image_files()` - отсутствующие файлы
    - Проверка что импорт НЕ падает с ошибкой
    - Статистика images_errors > 0
    - Товар создаётся без изображений
  - [ ] Написать `test_import_with_duplicate_images()` - дубликаты
    - Проверка дедупликации путей
    - Статистика images_skipped корректна
  - [ ] Написать `test_import_with_invalid_image_format()` - невалидные форматы
    - Логирование WARNING для невалидных путей
    - Импорт продолжается без сбоев
  - [ ] Написать `test_import_products_without_images()` - товары без изображений
    - Корректная обработка товаров без тегов `<Картинка>`
    - Товары создаются успешно
  - [ ] Написать `test_reimport_updates_images()` - повторный импорт
    - Проверка обновления изображений при повторном импорте
    - Новые изображения добавляются в gallery

### Специальные функции и performance

- [ ] **Реализовать тест флага --skip-images** (AC: 4)
  - [ ] Написать `test_import_with_skip_images_flag()`
  - [ ] Проверка images_copied = 0 при использовании флага
  - [ ] Верификация что файлы НЕ копируются в media
  - [ ] Товары создаются без изображений

- [ ] **Реализовать Performance тест** (AC: 5, 6)
  - [ ] Создать файл `backend/tests/performance/test_image_import_performance.py`
  - [ ] Переместить и реализовать `test_import_large_volume_images_performance()` в нем
  - [ ] Парсинг ВСЕХ goods_*.xml файлов из data/import_1c/goods/
  - [ ] Обработка всех товаров с изображениями
  - [ ] Измерение времени выполнения и скорости (images/sec)
  - [ ] Логирование performance метрик
  - [ ] Проверка >= 10 images/sec (performance requirement)

### Финализация и верификация

- [ ] **Запустить и верифицировать тесты** (AC: 7, 8)
  - [ ] Запустить все тесты в Docker: `make test` или `docker-compose -f docker/docker-compose.test.yml run --rm backend pytest`
  - [ ] Проверить coverage >= 90% для processor.py и parser.py
  - [ ] Убедиться в стабильности (no flaky failures при повторных запусках)
  - [ ] Проверить cleanup временных файлов после тестов (tearDown работает)
  - [ ] Запустить быстрые тесты без performance: `pytest -m "not slow"`

- [ ] **Документация и code review**
  - [ ] Обновить docstrings всех тестовых методов
  - [ ] Добавить комментарии к сложным проверкам
  - [ ] Проверить соответствие Testing Strategy стандартам (AAA Pattern, маркировка)
  - [ ] Обновить Testing Strategy документацию при необходимости

## Dev Notes

### Story Context

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

### Technical Notes

#### Структура интеграционных тестов

**Файлы тестов:**
- **Интеграционные:** `backend/tests/integration/test_import_images_integration.py`
- **Производительности:** `backend/tests/performance/test_image_import_performance.py`

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

#### Основной интеграционный тест

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

#### Edge Cases тесты

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

#### Performance тест

**Test 4: Импорт большого объема изображений**

**Примечание:** Этот тест должен быть вынесен в отдельный файл `backend/tests/performance/test_image_import_performance.py` в соответствии со структурой тестов проекта. Для переиспользования `setUp` можно унаследовать тестовый класс.

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

### Testing

#### Обязательные требования к тестированию

**🔴 КРИТИЧНО:** Все тесты ДОЛЖНЫ соответствовать [Testing Strategy](docs/architecture/10-testing-strategy.md) и стандартам изоляции (раздел 10.4).

#### Тестовый Workflow

```text
1. Setup Environment
   ├── Check real data exists (data/import_1c/goods/)
   ├── Create temporary MEDIA_ROOT
   └── Initialize test DB (PostgreSQL)

2. Main E2E Test
   ├── Parse goods.xml with images
   ├── Process products with images
   ├── Verify DB records (main_image, gallery_images)
   └── Verify physical files in media

3. Edge Cases Tests
   ├── Missing files → Warning + continue
   ├── Duplicates → Skip + log
   ├── Invalid formats → Error + skip
   └── No images → Success (empty images)

4. Performance Test
   ├── Import 1000+ images
   ├── Measure time and throughput
   └── Log metrics

5. Cleanup
   ├── Remove temporary MEDIA_ROOT
   └── Rollback DB transactions
```

#### Unit-тесты

**Расположение:**
- **Интеграционные тесты:** `backend/tests/integration/test_import_images_integration.py`
- **Тесты производительности:** `backend/tests/performance/test_image_import_performance.py`

**Обязательная маркировка тестов:**
```python
import pytest

# Маркировка для всего модуля
pytestmark = pytest.mark.django_db

@pytest.mark.integration
class TestImportImagesIntegration:
    """Интеграционные тесты импорта изображений из goods.xml"""
    # тесты здесь
```

#### Обязательная система изоляции

**🚨 КРИТИЧНО:** Для предотвращения constraint violations и flaky tests:

1. **Использовать `get_unique_suffix()` для генерации уникальных данных:**
```python
from tests.conftest import get_unique_suffix

# В тестовых XML данных:
unique_id = get_unique_suffix()
xml_content = f"""
<Каталог>
    <Товары>
        <Товар>
            <Ид>{unique_id}</Ид>
            ...
```

2. **Обязательные pytest настройки:**
   - `--create-db` - создавать чистую БД перед тестами
   - `--nomigrations` - не выполнять миграции для скорости
   - Запуск через Docker с PostgreSQL (НЕ SQLite)

3. **Автоматическая изоляция через fixtures:**
   - `@pytest.fixture(autouse=True)` в `conftest.py` очищает БД перед каждым тестом
   - Используется `TRUNCATE TABLE ... RESTART IDENTITY CASCADE`

#### Команды запуска тестов

**🔴 ОБЯЗАТЕЛЬНО:** Все тесты запускаются через Docker с PostgreSQL:

```bash
# Запуск всех интеграционных тестов импорта изображений (рекомендуемый способ)
make test

# Или напрямую через docker-compose для интеграционных тестов
docker-compose -f docker/docker-compose.test.yml run --rm backend \
  pytest backend/tests/integration/test_import_images_integration.py -v

# Только быстрые тесты (без performance)
docker-compose -f docker/docker-compose.test.yml run --rm backend \
  pytest backend/tests/integration/test_import_images_integration.py -v -m "not slow"

# Performance тест отдельно
docker-compose -f docker/docker-compose.test.yml run --rm backend \
  pytest backend/tests/performance/test_image_import_performance.py -v -s

# С coverage отчетом для интеграционных тестов
docker-compose -f docker/docker-compose.test.yml run --rm backend \
  pytest backend/tests/integration/test_import_images_integration.py --cov=apps.products.services --cov-report=html
```

**⚠️ ВАЖНО:** SQLite НЕ поддерживается для тестов из-за ограничений JSON операторов PostgreSQL.

#### Требования к покрытию

Согласно [Testing Strategy §10.7](docs/architecture/10-testing-strategy.md#10.7):

- **Общее покрытие:** >= 70%
- **Покрытие для processor.py и parser.py:** >= 90% (критические модули)
- **Новая функциональность:** >= 90%

#### Тестовые данные

**Используемые реальные данные:**
- `data/import_1c/goods/goods_*.xml` - XML файлы с товарами
- `data/import_1c/goods/import_files/` - директория с изображениями
- Минимум 5-10 товаров с изображениями для тестов
- Минимум 20-30 файлов изображений различных форматов

**Требования к тестовым данным:**
- Данные НЕ коммитятся в git (gitignore)
- Данные загружаются из production выгрузки 1С
- Структура соответствует CommerceML 3.1

#### Expected Performance Baseline

| Метрика | Минимум | Целевое | Excellent |
|---------|---------|---------|-----------|
| Images/sec | >= 10 | 50 | 100+ |
| Total time (1000 imgs) | < 100s | 20s | 10s |
| Memory usage | < 500MB | 200MB | 100MB |

## Definition of Done

Критерии завершения Story 3.1.3:

- [ ] **Все тесты проходят** - 100% pass в Docker с PostgreSQL
- [ ] **Покрытие >= 90%** - для processor.py и parser.py (критические модули)
- [ ] **Стабильность тестов** - no flaky failures при повторных запусках
- [ ] **Изоляция работает** - cleanup удаляет временные файлы и данные
- [ ] **Реальные данные используются** - тесты работают с файлами из data/import_1c/
- [ ] **Документация обновлена** - docstrings и комментарии для всех тестов
- [ ] **Code review пройден** - соответствие Testing Strategy стандартам (AAA Pattern, маркировка)
- [ ] **CI/CD integration** - тесты успешно запускаются в GitHub Actions
- [ ] **Performance требования выполнены** - >= 10 images/sec в performance тесте
- [ ] **Edge cases покрыты** - все 5 edge cases тестов реализованы и проходят

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

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-08 | 1.0 | Initial story creation | Developer Team |
| 2025-11-09 | 2.0 | Template compliance fixes: added Tasks/Subtasks, Change Log, Dev Agent Record, QA Results sections. Reformatted Definition of Done as completion criteria. Added test workflow diagram and performance baseline table. | Sarah (Product Owner) |

---

## Dev Agent Record

_This section will be populated by the development agent during implementation._

### Agent Model Used

_To be filled by Dev Agent (e.g., "Claude Sonnet 3.5")_

### Debug Log References

_Links to debug logs and traces generated during development_

### Completion Notes

_Notes about task completion and any issues encountered:_

- Task 1: ...
- Task 2: ...

### File List

_List of all files created, modified, or affected during story implementation:_

**Created:**
- `backend/tests/integration/test_import_images_integration.py`
- `backend/tests/performance/test_image_import_performance.py`

**Modified:**
- _(to be filled by Dev Agent)_

---

## QA Results

_This section will be populated by QA Agent after story implementation is completed._

### Test Execution Summary

- **Total Tests Run:** _TBD_
- **Passed:** _TBD_
- **Failed:** _TBD_
- **Coverage:** _TBD_%

### Quality Gate Status

- [ ] All tests pass (100%)
- [ ] Coverage >= 90% for processor.py and parser.py
- [ ] No flaky tests detected
- [ ] Performance requirements met (>= 10 images/sec)
- [ ] Code review approved
- [ ] Documentation complete

### QA Sign-Off

**Reviewed by:** _QA Agent Name_
**Date:** _YYYY-MM-DD_
**Status:** _PASS / FAIL / CONDITIONAL PASS_

**Notes:** _Detailed QA findings and recommendations_

---

**Дата создания:** 2025-01-08
**Дата обновления:** 2025-11-09
**Приоритет:** High (блокирует релиз Epic 3.1)
**Epic:** Epic 3.1 - Импорт и связь изображений товаров из 1С
**Assigned to:** QA/Developer Team
**Depends on:** Story 3.1.1, Story 3.1.2
