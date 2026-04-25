# Story 3.1.2: Импорт изображений в Django media storage - Brownfield Enhancement

## Status

Ready for Review

---

## Story Title

Копирование изображений товаров из 1С в Django media storage и установка связей с Product

## User Story

**Как** система импорта товаров из 1С,
**Я хочу** копировать физические файлы изображений из директории выгрузки 1С в Django media storage,
**Чтобы** изображения были доступны через Django ImageField и отображались на frontend.

## Story Context

### Existing System Integration

**Интегрируется с:**

- `ProductDataProcessor` (`backend/apps/products/services/processor.py`) — процессор обработки данных товаров
- `Product` модель (`backend/apps/products/models.py`) — модель товара с полями изображений
- Django `default_storage` — file storage backend для media файлов
- Команда `import_catalog_from_1c` (`backend/apps/products/management/commands/import_catalog_from_1c.py`) — оркестрация импорта

**Технологии:**

- Django 4.2 ImageField для хранения изображений
- Django default_storage (FileSystemStorage или S3)
- PostgreSQL JSONField для галереи изображений
- Python Pillow для валидации изображений
- Batch операции для производительности

**Существующий паттерн:**

```python
# ProductDataProcessor использует bulk операции (processor.py:40-42)
def __init__(self, session_id: int, skip_validation: bool = False, chunk_size: int = 1000):
    self.session_id = session_id
    self.chunk_size = chunk_size  # Батчинг для производительности
```

**Точки интеграции:**

1. Модель `Product` - поля `main_image` (ImageField) и `gallery_images` (JSONField) (models.py:309-315)
2. `ProductDataProcessor.create_product_placeholder()` - установка main_image при создании товара
3. Django settings.MEDIA_ROOT и MEDIA_URL для путей к файлам
4. ImportSession для логирования процесса импорта
5. Story 3.1.1 уже гарантирует валидацию расширений и нормализацию путей изображений на этапе парсинга (`backend/apps/products/services/parser.py`), поэтому данная история может предполагать корректный формат `goods_data["images"]` без дополнительной очистки

### Текущее состояние

✅ **Уже реализовано:**

- Product модель имеет поля `main_image` и `gallery_images` (models.py:309-315)
- ProductDataProcessor устанавливает placeholder изображение (processor.py:196)
- ProductDataProcessor поддерживает bulk операции через chunk_size
- ImportSession логирует статистику импорта

❌ **Что требуется добавить:**

1. **Метод копирования изображений** из директории 1С в Django media
2. **Установка связей** main_image (первое изображение) и gallery_images (остальные)
3. **Обработка дубликатов** и отсутствующих файлов
4. **Опциональный параметр `--skip-images`** в команде импорта
5. **Батчинг копирования** для производительности
6. **Unit-тесты** с моками файловых операций

## Acceptance Criteria

### Функциональные требования

1. **Копирование изображений из директории 1С**
   - ⚠️ Новый метод `ProductDataProcessor.import_product_images(product: Product, image_paths: list[str], base_dir: str, validate_images: bool = False) -> dict[str, int]`
   - ⚠️ Копирует физические файлы из `{base_dir}/{image_path}` в Django media storage
   - ⚠️ Использует Django `default_storage.save()` для совместимости с S3/FileSystem
   - ⚠️ **Сохраняет оригинальные имена файлов из 1С** (они уже уникальны благодаря UUID структуре `parent_id#sku_id`)
   - ⚠️ **Сохраняет структуру поддиректорий** из 1С (`media/products/{first_two_chars}/{filename}`) для производительности при >10,000 изображений

2. **Установка связей с моделью Product**
   - ⚠️ Первое изображение устанавливается как `Product.main_image`
   - ⚠️ Остальные изображения добавляются в `Product.gallery_images` как JSON список путей
   - ⚠️ Пути хранятся относительно MEDIA_ROOT (например, `products/00/image.jpg`)
   - ⚠️ **Семантика повторного импорта:**
     - `main_image` НЕ меняется, если уже установлен (сохранение выбора администратора)
     - Новые изображения добавляются в конец `gallery_images` (append)
     - Дубликаты проверяются: `if path not in gallery_images` (предотвращение накопления)
     - Future enhancement: флаг `--replace-images` для полной замены всех изображений товара

3. **Обработка дубликатов и ошибок**
   - ⚠️ Проверка существования файла перед копированием (skip если файл уже есть)
   - ⚠️ Отсутствующие физические файлы логируются как WARNING и пропускаются
   - ⚠️ Товары без изображений обрабатываются корректно (пропускаются без ошибок)
   - ⚠️ Невалидные изображения (не Pillow-совместимые) логируются и пропускаются

4. **Интеграция с командой импорта**
   - ⚠️ Добавлен параметр `--skip-images` в команду `import_catalog_from_1c`
   - ⚠️ Копирование изображений вызывается после `create_product_placeholder()`
   - ⚠️ Статистика импорта изображений (`images_copied`, `images_skipped`, `images_errors`) добавлена в `ImportSession.report_details` и в `processor.stats`
   - ⚠️ Progress bar для копирования изображений (если > 10 изображений)

### Требования производительности

5. **Batch операции для минимизации I/O**
   - ⚠️ Группировка копирования файлов по директориям
   - ⚠️ Использование `default_storage.exists()` для проверки дубликатов
   - ⚠️ Ленивая валидация изображений (только если включен флаг)
   - ⚠️ Максимум 1000 изображений за один batch

6. **Логирование и мониторинг**
   - ⚠️ INFO: успешное копирование каждого изображения
   - ⚠️ WARNING: отсутствующие или невалидные файлы
   - ⚠️ Статистика в конце импорта: `images_copied`, `images_skipped`, `images_errors`
   - ⚠️ Сохранение статистики в ImportSession.report_details

### Требования интеграции

7. **Существующая функциональность остается нетронутой**
   - ✅ Все существующие тесты для ProductDataProcessor проходят
   - ✅ API Product модели не изменяется
   - ✅ Команда `import_catalog_from_1c` без флага `--skip-images` работает как раньше
   - ✅ Импорт товаров без изображений работает корректно

8. **Обратная совместимость**
   - ✅ Товары созданные до этой истории не затрагиваются
   - ✅ Placeholder изображение остается для товаров без изображений
   - ✅ Повторный импорт обновляет изображения без потери данных

## Tasks / Subtasks

- [x] Task 1: Реализовать метод `import_product_images()` (AC: 1, 2, 3)
  - [x] Создать метод с указанной сигнатурой и логикой копирования файлов
  - [x] Реализовать сохранение структуры директорий и обработку дубликатов
  - [x] Добавить логирование и сбор статистики копирования
- [x] Task 2: Интегрировать метод с `create_product_placeholder()` (AC: 1, 2, 4)
  - [x] Передавать `base_dir` и `skip_images` при создании товара
  - [x] Обновить статистику процессора с учётом изображений
- [x] Task 3: Обновить команду `import_catalog_from_1c` (AC: 4, 6)
  - [x] Добавить флаг `--skip-images` и прокинуть его в процессор
  - [x] Вывести статистику изображений (ключи `images_copied`, `images_skipped`, `images_errors`) в итоговом отчёте команды
- [x] Task 4: Написать unit-тесты с моками файловых операций (AC: все)
  - [x] Реализовать 12 сценариев из раздела Testing Strategy
  - [x] Обеспечить изоляцию тестов и уникальность данных
- [x] Task 5: Обновить документацию и кодовые комментарии (DoD)
  - [x] Расширить docstrings новых методов
  - [x] Обновить README команды `import_catalog_from_1c`

## Technical Notes

### Структура физических файлов 1С

**Пример директории:**

```
data/import_1c/goods/import_files/
├── 00/
│   ├── 001a16a4-b810-11ed-860f-fa163edba792_24062354-2f7b-11ee-998f-fa163e775e1f.jpg
│   └── ...
├── 01/
├── ...
└── 73/
    ├── 73f9d61e-5673-11f0-8041-fa163ea88911_a62d33ce-5673-11f0-8041-fa163ea88911.png
    └── 73f9d61e-5673-11f0-8041-fa163ea88911_a62d33ce-5673-11f0-8041-fa163ea88912.jpg
```

**Маппинг в Django media (сохранение структуры директорий):**

```
MEDIA_ROOT/products/
├── 00/
│   ├── 001a16a4-b810-11ed-860f-fa163edba792_24062354.jpg
│   └── ...
├── 01/
├── ...
└── 73/
    ├── 73f9d61e-5673-11f0-8041-fa163ea88911_a62d33ce-5673-11f0-8041-fa163ea88911.png
    └── 73f9d61e-5673-11f0-8041-fa163ea88911_a62d33ce-5673-11f0-8041-fa163ea88912.jpg
```

**Обоснование структуры:**

- Сохранение поддиректорий из 1С улучшает производительность при большом количестве изображений (>10,000)
- Упрощает отладку и трассировку исходных файлов
- Оригинальные имена файлов содержат UUID и уже уникальны

### Реализация метода import_product_images()

**Новый метод в ProductDataProcessor:**

```python
def import_product_images(
    self,
    product: Product,
    image_paths: list[str],
    base_dir: str,
    validate_images: bool = False
) -> dict[str, int]:
    """
    Копирование изображений товара из директории 1С в Django media storage

    Args:
        product: Product instance для установки изображений
        image_paths: Список относительных путей из goods_data["images"]
        base_dir: Базовая директория импорта (например, data/import_1c/goods/)
        validate_images: Валидировать изображения через Pillow (медленнее)

    Returns:
        dict с количеством copied, skipped, errors
    """
    from pathlib import Path
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    result = {"copied": 0, "skipped": 0, "errors": 0}

    if not image_paths:
        logger.debug(f"No images for product {product.onec_id}")
        return result

    # Проверяем существующий main_image (семантика повторного импорта)
    main_image_set = bool(product.main_image)
    gallery_images = list(product.gallery_images or [])

    for image_path in image_paths:
        try:
            # Построение полного пути к исходному файлу
            source_path = Path(base_dir) / image_path
            if not source_path.exists():
                logger.warning(
                    f"Image file not found: {source_path} for product {product.onec_id}"
                )
                result["errors"] += 1
                continue

            # Сохранение структуры директорий из 1С
            # image_path: "00/001a16a4-b810-11ed-860f-fa163edba792_24062354.jpg"
            filename = source_path.name
            subdir = image_path.split('/')[0] if '/' in image_path else ''
            destination_path = f"products/{subdir}/{filename}" if subdir else f"products/{filename}"

            # Проверка существования файла в media
            if default_storage.exists(destination_path):
                logger.debug(f"Image already exists: {destination_path}")
                result["skipped"] += 1

                # Устанавливаем связь даже если файл уже существует
                # При повторном импорте main_image НЕ меняется если уже установлен
                if not main_image_set:
                    product.main_image = destination_path
                    main_image_set = True
                else:
                    # Проверка дубликатов в gallery_images
                    if destination_path not in gallery_images:
                        gallery_images.append(destination_path)
                continue

            # Валидация изображения (опционально)
            if validate_images:
                try:
                    from PIL import Image
                    with Image.open(source_path) as img:
                        img.verify()
                except Exception as e:
                    logger.warning(
                        f"Invalid image file {source_path}: {e}"
                    )
                    result["errors"] += 1
                    continue

            # Копирование файла в media storage
            with open(source_path, "rb") as f:
                file_content = f.read()
                saved_path = default_storage.save(
                    destination_path,
                    ContentFile(file_content)
                )

            logger.info(f"Copied image: {source_path} -> {saved_path}")
            result["copied"] += 1

            # Установка связи с Product
            # При повторном импорте main_image НЕ меняется если уже установлен
            if not main_image_set:
                product.main_image = saved_path
                main_image_set = True
            else:
                # Проверка дубликатов в gallery_images
                if saved_path not in gallery_images:
                    gallery_images.append(saved_path)

        except Exception as e:
            logger.error(f"Error copying image {image_path}: {e}")
            result["errors"] += 1

    # Сохранение изменений в Product
    if main_image_set or gallery_images:
        product.gallery_images = gallery_images
        product.save(update_fields=["main_image", "gallery_images"])
        logger.info(
            f"Updated product {product.onec_id} images: "
            f"main_image={product.main_image}, gallery={len(gallery_images)}"
        )

    return result
```

### Интеграция с create_product_placeholder()

**Обновление метода в ProductDataProcessor:**

```python
def create_product_placeholder(
    self,
    goods_data: GoodsData,
    base_dir: str | None = None,
    skip_images: bool = False
) -> Product | None:
    """Создание заготовки товара из goods.xml (с опциональным импортом изображений)"""
    try:
        # ... существующий код создания товара ...

        product.save()
        logger.info(f"Created product placeholder: {parent_id}")
        self.stats["created"] += 1

        # НОВАЯ ФУНКЦИОНАЛЬНОСТЬ: Импорт изображений
        if not skip_images and base_dir and "images" in goods_data:
            image_result = self.import_product_images(
                product=product,
                image_paths=goods_data["images"],
                base_dir=base_dir,
                validate_images=self.skip_validation == False
            )

            # Обновление статистики
            self.stats.setdefault("images_copied", 0)
            self.stats.setdefault("images_skipped", 0)
            self.stats.setdefault("images_errors", 0)

            self.stats["images_copied"] += image_result["copied"]
            self.stats["images_skipped"] += image_result["skipped"]
            self.stats["images_errors"] += image_result["errors"]

        return product

    except Exception as e:
        self._log_error(f"Error creating product placeholder: {e}", goods_data)
        return None
```

### Обновление команды import_catalog_from_1c

**Добавление параметра --skip-images:**

```python
# В методе add_arguments() (import_catalog_from_1c.py)
parser.add_argument(
    "--skip-images",
    action="store_true",
    help="Пропустить импорт изображений товаров (только метаданные)",
)
```

**Использование в handle():**

```python
# В методе handle() после валидации
skip_images = options.get("skip_images", False)

# Передача параметра в процессор (около строки 292)
for goods_item in tqdm(goods_data, desc=f"   Обработка {Path(file_path).name}"):
    processor.create_product_placeholder(
        goods_item,
        base_dir=data_dir,  # Передаем базовую директорию
        skip_images=skip_images
    )
```

**Вывод статистики изображений:**

```python
# В конце метода handle() (около строки 394)
self.stdout.write("=" * 50)
self.stdout.write(self.style.SUCCESS("✅ ИМПОРТ ЗАВЕРШЕН УСПЕШНО"))
self.stdout.write("=" * 50)
self.stdout.write(f"Создано товаров:   {processor.stats['created']}")
self.stdout.write(f"Обновлено товаров: {processor.stats['updated']}")
self.stdout.write(f"Пропущено:         {processor.stats['skipped']}")
self.stdout.write(f"Ошибок:            {processor.stats['errors']}")

# НОВАЯ СТАТИСТИКА
if not skip_images:
    self.stdout.write("\n📸 Статистика изображений:")
    self.stdout.write(f"Скопировано:       {processor.stats.get('images_copied', 0)}")
    self.stdout.write(f"Пропущено:         {processor.stats.get('images_skipped', 0)}")
    self.stdout.write(f"Ошибок:            {processor.stats.get('images_errors', 0)}")

self.stdout.write("=" * 50)
```

## Definition of Done

- [ ] Функциональность импорта изображений соответствует всем Acceptance Criteria (регулярный и повторный импорт)
- [ ] Команда `import_catalog_from_1c` поддерживает флаг `--skip-images` и выводит статистику изображений
- [ ] Добавлены и проходят unit-тесты из Testing Strategy, существующие тесты регрессий не ломаются
- [ ] Логирование и статистика импорта изображений доступны в ImportSession и выводе команды
- [ ] Документация и docstrings обновлены для новых/изменённых методов
- [ ] Code review подтверждает соответствие стандартам, изменения задокументированы в Change Log

## Testing Strategy

### Требования изоляции тестов

**КРИТИЧЕСКИ ВАЖНО:** Все тесты должны использовать систему полной изоляции согласно [docs/architecture/10-testing-strategy.md](../../architecture/10-testing-strategy.md) разделы 10.4.1-10.4.2.

**Обязательные фикстуры изоляции:**

```python
# conftest.py - автоматические фикстуры (уже существуют в проекте)
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Автоматически включает доступ к базе данных для всех тестов"""
    pass

@pytest.fixture(autouse=True)
def clear_db_before_test(transactional_db):
    """Очищает базу данных перед каждым тестом для полной изоляции"""
    from django.core.cache import cache
    from django.db import connection
    from django.apps import apps

    cache.clear()

    with connection.cursor() as cursor:
        models = apps.get_models()
        for model in models:
            table_name = model._meta.db_table
            try:
                cursor.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
            except Exception:
                pass
```

**Генерация уникальных данных:**

```python
import uuid
import time

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0

def get_unique_suffix():
    """Генерирует абсолютно уникальный суффикс"""
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"

# В Factory Boy - ОБЯЗАТЕЛЬНО использовать LazyFunction
class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.LazyFunction(lambda: f"Product-{get_unique_suffix()}")
    sku = factory.LazyFunction(lambda: f"SKU-{get_unique_suffix().upper()}")
    onec_id = factory.LazyFunction(lambda: f"1C-{get_unique_suffix()}")
```

### Unit-тесты (backend/apps/products/tests/test_processor.py)

**Тестовые сценарии:**

1. **test_import_product_images_single_image** - товар с одним изображением
2. **test_import_product_images_multiple_images** - товар с несколькими изображениями
3. **test_import_product_images_no_images** - товар без изображений
4. **test_import_product_images_missing_file** - отсутствующий физический файл
5. **test_import_product_images_duplicate_file** - файл уже существует в media
6. **test_import_product_images_invalid_file** - невалидное изображение (валидация включена)
7. **test_create_product_placeholder_with_images** - интеграция с create_product_placeholder
8. **test_import_catalog_with_skip_images_flag** - проверка флага --skip-images
9. **test_import_product_images_preserves_existing_main_image** - повторный импорт не меняет main_image (NEW)
10. **test_import_product_images_appends_to_gallery** - повторный импорт добавляет в gallery_images (NEW)
11. **test_import_product_images_prevents_duplicates_in_gallery** - проверка дубликатов в gallery_images (NEW)
12. **test_import_product_images_preserves_directory_structure** - сохранение структуры директорий (NEW)

**Примеры тестов с моками:**

```python
from unittest.mock import patch, MagicMock, mock_open
from django.core.files.storage import default_storage
import tempfile
import os
import pytest

# Маркировка для всего модуля
pytestmark = pytest.mark.django_db

def test_import_product_images_single_image(self):
    """Импорт одного изображения товара (AAA Pattern)"""
    # ARRANGE - подготовка данных
    product = ProductFactory(
        onec_id=f"test-{get_unique_suffix()}",
        main_image=""
    )
    session = ImportSessionFactory()
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
        with patch.object(default_storage, 'exists', return_value=False), \
             patch.object(default_storage, 'save', return_value=f"products/{image_filename}"):

            # ACT - выполнение действия
            result = processor.import_product_images(
                product=product,
                image_paths=image_paths,
                base_dir=base_dir,
                validate_images=False
            )

            # ASSERT - проверка результата
            assert result["copied"] == 1
            assert result["skipped"] == 0
            assert result["errors"] == 0

            product.refresh_from_db()
            assert product.main_image == f"products/{image_filename}"
            assert len(product.gallery_images) == 0  # Только одно изображение - идет в main

    finally:
        os.unlink(tmp_path)

def test_import_product_images_preserves_existing_main_image(self):
    """Повторный импорт НЕ меняет существующий main_image (AC 2)"""
    # ARRANGE
    existing_main = "products/00/existing_main.jpg"
    product = ProductFactory(
        onec_id=f"test-{get_unique_suffix()}",
        main_image=existing_main,  # Уже установлен
        gallery_images=[]
    )
    session = ImportSessionFactory()
    processor = ProductDataProcessor(session_id=session.id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"new image content")
        tmp_path = tmp.name

    try:
        base_dir = os.path.dirname(tmp_path)
        image_filename = os.path.basename(tmp_path)
        image_paths = [f"00/{image_filename}"]  # С поддиректорией

        with patch.object(default_storage, 'exists', return_value=False), \
             patch.object(default_storage, 'save', return_value=f"products/00/{image_filename}"):

            # ACT - повторный импорт
            result = processor.import_product_images(
                product=product,
                image_paths=image_paths,
                base_dir=base_dir,
                validate_images=False
            )

            # ASSERT
            product.refresh_from_db()
            # main_image НЕ должен измениться
            assert product.main_image == existing_main
            # Новое изображение должно попасть в gallery
            assert f"products/00/{image_filename}" in product.gallery_images
            assert len(product.gallery_images) == 1

    finally:
        os.unlink(tmp_path)

def test_import_product_images_prevents_duplicates_in_gallery(self):
    """Проверка предотвращения дубликатов в gallery_images (AC 2)"""
    # ARRANGE
    existing_image = "products/00/image.jpg"
    product = ProductFactory(
        onec_id=f"test-{get_unique_suffix()}",
        main_image="products/00/main.jpg",
        gallery_images=[existing_image]  # Уже есть
    )
    session = ImportSessionFactory()
    processor = ProductDataProcessor(session_id=session.id)

    # ACT - импортируем то же изображение повторно
    with patch.object(default_storage, 'exists', return_value=True):
        result = processor.import_product_images(
            product=product,
            image_paths=["00/image.jpg"],
            base_dir="/fake/path",
            validate_images=False
        )

    # ASSERT
    product.refresh_from_db()
    # Дубликат НЕ должен добавиться
    assert product.gallery_images.count(existing_image) == 1
    assert result["skipped"] == 1

def test_import_product_images_preserves_directory_structure(self):
    """Сохранение структуры поддиректорий из 1С (AC 1)"""
    # ARRANGE
    product = ProductFactory(
        onec_id=f"test-{get_unique_suffix()}",
        main_image=""
    )
    session = ImportSessionFactory()
    processor = ProductDataProcessor(session_id=session.id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"image content")
        tmp_path = tmp.name

    try:
        base_dir = os.path.dirname(tmp_path)
        image_filename = os.path.basename(tmp_path)
        # Путь с поддиректорией как в 1С
        image_paths = [f"00/{image_filename}"]

        expected_path = f"products/00/{image_filename}"

        with patch.object(default_storage, 'exists', return_value=False), \
             patch.object(default_storage, 'save', return_value=expected_path) as mock_save:

            # ACT
            result = processor.import_product_images(
                product=product,
                image_paths=image_paths,
                base_dir=base_dir,
                validate_images=False
            )

            # ASSERT
            product.refresh_from_db()
            # Проверяем что путь содержит поддиректорию
            assert product.main_image == expected_path
            assert "00/" in product.main_image
            # Проверяем что save вызван с правильным путём
            mock_save.assert_called_once()
            call_args = mock_save.call_args[0]
            assert call_args[0] == expected_path

    finally:
        os.unlink(tmp_path)
```

### Интеграционные тесты (Story 3.1.3)

- End-to-end импорт с реальными изображениями из `data/import_1c/goods/import_files/`
- Проверка физического наличия файлов в MEDIA_ROOT
- Верификация путей в БД соответствуют реальным файлам

## Dependencies

**Зависит от:**

- ✅ Story 3.1.1 - Парсинг путей изображений из XML (валидированные пути)
- ✅ Product модель с полями main_image и gallery_images
- ✅ ProductDataProcessor базовый функционал

**Блокирует:**

- ⏳ Story 3.1.3 - Интеграционное тестирование импорта изображений

## Risk Mitigation

**Риск 1:** Большой объем изображений может заполнить дисковое пространство

**Митигация:**

- Проверка доступного места перед импортом (опционально)
- Флаг `--skip-images` для импорта только метаданных
- Возможность использовать S3 через Django storage backend

**Риск 2:** Импорт изображений значительно замедляет процесс

**Митигация:**

- Батчинг операций копирования
- Опциональная валидация через `--skip-validation`
- Progress bar для визуализации прогресса
- Параллельное копирование файлов (future enhancement)

**Риск 3:** Повторный импорт создает дубликаты файлов

**Митигация:**

- Проверка `default_storage.exists()` перед копированием
- Использование детерминированных имен файлов (из 1С ID)
- Галерея обновляется append, не replace

**Rollback план:**

- Очистка MEDIA_ROOT/products/ от импортированных файлов
- Обнуление полей main_image и gallery_images через SQL
- Восстановление из ImportSession backup

## Story Complexity

**Оценка:** 5 Story Points (средняя задача)

**Обоснование:**

- Требуется новый метод с файловыми операциями
- Интеграция с существующим процессором и командой
- Обработка edge cases (дубликаты, ошибки)
- Написание unit-тестов с моками сложнее обычного
- Требуется тщательное тестирование производительности

**Ожидаемое время:** 4-6 часов разработки + 2-3 часа тестирования

---

**Дата создания:** 2025-01-08
**Приоритет:** High
**Epic:** Epic 3.1 - Импорт и связь изображений товаров из 1С
**Assigned to:** Developer Team
**Depends on:** Story 3.1.1

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes

- ✅ Реализован метод `import_product_images()` в ProductDataProcessor ([processor.py:593-717](backend/apps/products/services/processor.py#L593-L717))
- ✅ Интегрирован импорт изображений с `create_product_placeholder()` ([processor.py:218-234](backend/apps/products/services/processor.py#L218-L234))
- ✅ Добавлен флаг `--skip-images` в команду `import_catalog_from_1c` ([import_catalog_from_1c.py:76-80](backend/apps/products/management/commands/import_catalog_from_1c.py#L76-L80))
- ✅ Добавлена статистика изображений в вывод команды ([import_catalog_from_1c.py:410-421](backend/apps/products/management/commands/import_catalog_from_1c.py#L410-L421))
- ✅ Создано 12 unit-тестов с моками файловых операций ([test_processor.py](backend/apps/products/tests/test_processor.py))
- ✅ Обновлены фабрики с использованием `get_unique_suffix()` для изоляции тестов ([factories.py](backend/apps/products/factories.py))
- ✅ Обновлены docstrings для новых методов

### File List

**Modified:**

- `backend/apps/products/services/processor.py` - добавлен метод `import_product_images()` и обновлён `create_product_placeholder()`
- `backend/apps/products/management/commands/import_catalog_from_1c.py` - добавлен флаг `--skip-images` и вывод статистики изображений
- `backend/apps/products/factories.py` - обновлены фабрики с `get_unique_suffix()` для изоляции тестов

**Created:**

- `backend/apps/products/tests/test_processor.py` - 12 unit-тестов для импорта изображений

### Debug Log References

Нет критических проблем или блокеров.

## Change Log

| Date       | Version | Description                                      | Author            |
| ---------- | ------- | ------------------------------------------------ | ----------------- |
| 2025-01-08 | 0.1     | Первоначальный черновик истории                  | Product Team      |
| 2025-11-09 | 0.2     | Обновление после QA Planning Review (Quinn)      | Product Team      |
| 2025-11-09 | 0.3     | Добавлены Tasks/Subtasks и уточнён DoD           | Product Owner     |
| 2025-11-09 | 1.0     | Реализована функциональность импорта изображений | James (Dev Agent) |

## QA Planning Review

**Review Date:** 2025-11-09
**Reviewed By:** Quinn (Test Architect)
**Gate Status:** ✅ PASS

### Статус

- **Quality Score:** 100/100
- **Readiness Score:** 10/10
- **Статус:** ✅ READY FOR IMMEDIATE IMPLEMENTATION

### Ключевые выводы

✅ **Сильные стороны:**

- Исключительно детальная техническая спецификация с примерами кода.
- Продуманная интеграция с существующей архитектурой (`ProductDataProcessor`).
- Полное покрытие edge cases, включая семантику повторного импорта и обработку ошибок.
- Превосходная стратегия тестирования с 12 детализированными сценариями и упором на изоляцию тестов.

✅ **Внедрённые улучшения (финализированы в ходе этого ревью):**

1.  **AC 1:** Уточнено требование по сохранению структуры поддиректорий (`products/{first_two_chars}/{filename}`) для оптимизации производительности.
2.  **AC 2:** Финализирована семантика повторного импорта: `main_image` не перезаписывается, а `gallery_images` пополняется с проверкой на дубликаты.
3.  **Testing:** Закреплено требование по полной изоляции тестов с помощью `get_unique_suffix()` и `pytest.mark.django_db`.
4.  **Testing:** Утверждено расширение тестового покрытия до 12 сценариев для проверки всех аспектов, включая повторный импорт.

### Advisory Notes для разработчика

1.  **Начните с тестов (TDD):** Реализуйте 12 unit-тестов из `Testing Strategy` в первую очередь. Это ваш чек-лист для реализации.
2.  **Обеспечьте изоляцию:** Строго следуйте гайдлайнам по изоляции тестов (`get_unique_suffix`, `pytest.mark.django_db`), чтобы избежать нестабильных тестов.
3.  **Следуйте спецификации:** Реализация метода `import_product_images` должна в точности соответствовать коду и логике, описанным в `Technical Notes` (строки 186-301).

**Детальный анализ:** [docs/qa/gates/3.1.2-import-images-to-media.md](../../qa/gates/3.1.2-import-images-to-media.md)

---
