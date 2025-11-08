# Story 3.1.1: Парсинг путей изображений из XML - Brownfield Enhancement

## Story Title

Парсинг путей изображений товаров из goods.xml - Расширение XMLDataParser

## User Story

**Как** система импорта товаров из 1С,
**Я хочу** извлекать все пути к изображениям из тегов `<Картинка>` в goods.xml,
**Чтобы** эти пути могли использоваться для копирования физических файлов изображений в Django media storage.

## Story Context

### Existing System Integration

**Интегрируется с:**
- `XMLDataParser` ([backend/apps/products/services/parser.py](backend/apps/products/services/parser.py:75-461)) - существующий парсер CommerceML 3.1
- `parse_goods_xml()` метод ([backend/apps/products/services/parser.py:164-207](backend/apps/products/services/parser.py#L164-L207)) - парсинг базовых данных товаров
- `GoodsData` TypedDict ([backend/apps/products/services/parser.py:13-22](backend/apps/products/services/parser.py#L13-L22)) - структура данных товара

**Технологии:**
- Python 3.11+ с type hints
- defusedxml.ElementTree для безопасного парсинга XML
- Django settings для путей к файлам
- CommerceML 3.1 формат выгрузки 1С

**Существующий паттерн:**
```python
# Текущая реализация parse_goods_xml() в parser.py:198-202
image_elements = self._find_children(product_element, "Картинка")
if image_elements:
    goods_data["images"] = [
        image.text.strip() for image in image_elements if image.text
    ]
```

**Точки интеграции:**
1. Расширение `GoodsData` TypedDict - добавление поля `images: list[str]` (уже существует!)
2. Метод `parse_goods_xml()` - уже извлекает пути изображений из тегов `<Картинка>`
3. Вспомогательные методы `_find_children()` для безопасного поиска элементов

### Текущее состояние

✅ **Уже реализовано:**
- `GoodsData` TypedDict содержит поле `images: list[str]` (строка 21)
- `parse_goods_xml()` извлекает все теги `<Картинка>` (строки 198-202)
- Пути изображений добавляются в `goods_data["images"]` как список строк

❌ **Что требуется добавить:**
1. **Валидация путей изображений** - проверка формата и расширения файлов
2. **Обработка абсолютных и относительных путей** - нормализация путей
3. **Unit-тесты** для парсинга изображений с реальными данными
4. **Документация** расширенного функционала

## Acceptance Criteria

### Функциональные требования

1. **Извлечение путей изображений из XML**
   - ✅ XMLDataParser.parse_goods_xml() извлекает все теги `<Картинка>` для каждого товара (УЖЕ РЕАЛИЗОВАНО)
   - ✅ Пути сохраняются в поле `images` как список строк в GoodsData (УЖЕ РЕАЛИЗОВАНО)
   - ✅ Поддерживается множество изображений для одного товара (УЖЕ РЕАЛИЗОВАНО)
   - ✅ Пустые или отсутствующие теги `<Картинка>` не вызывают ошибок (УЖЕ РЕАЛИЗОВАНО)

2. **Валидация путей изображений (НОВАЯ ФУНКЦИОНАЛЬНОСТЬ)**
   - ⚠️ Пути изображений валидируются на корректность формата
   - ⚠️ Поддерживаемые расширения: `.jpg`, `.jpeg`, `.png`, `.webp` (case-insensitive)
   - ⚠️ Невалидные пути логируются как WARNING и пропускаются
   - ⚠️ Пути нормализуются (убираются лишние слеши, исправляются backslashes на forward slashes)

3. **Обработка edge cases**
   - ✅ Товары без изображений корректно обрабатываются (поле images отсутствует или пустой список) (УЖЕ РЕАЛИЗОВАНО)
   - ✅ Дублирующиеся пути изображений для одного товара дедуплицируются (ДОБАВИТЬ)
   - ⚠️ Пути с пробелами и специальными символами корректно обрабатываются

### Требования интеграции

4. **Существующая функциональность остается нетронутой**
   - ✅ Все существующие unit-тесты для `parse_goods_xml()` проходят без изменений
   - ✅ Структура GoodsData TypedDict не изменяется (только используется поле images)
   - ✅ API XMLDataParser остается обратно совместимым

5. **Новые методы следуют существующим паттернам**
   - ⚠️ Валидация путей реализована как приватный метод `_validate_image_path(path: str) -> str | None`
   - ⚠️ Используется существующий logger для предупреждений
   - ⚠️ Следует стилю кода проекта (type hints, docstrings)

### Требования качества

6. **Код покрыт unit-тестами**
   - ⚠️ Тесты с реальными XML данными из `data/import_1c/goods/goods_*.xml`
   - ⚠️ Тесты edge cases: отсутствующие изображения, множественные изображения, невалидные пути
   - ⚠️ Покрытие новой функциональности >= 90%

7. **Документация обновлена**
   - ⚠️ Docstring метода `parse_goods_xml()` включает описание обработки изображений
   - ⚠️ Добавлены примеры использования в комментариях кода

## Technical Notes

### Структура XML из 1С (CommerceML 3.1)

**Пример реального XML из goods.xml:**
```xml
<Товар>
    <Ид>73f9d61e-5673-11f0-8041-fa163ea88911</Ид>
    <Наименование>Детский защитный велошлем COSMORIDE</Наименование>
    <Картинка>import_files/73/73f9d61e-5673-11f0-8041-fa163ea88911_a62d33ce-5673-11f0-8041-fa163ea88911.png</Картинка>
    <!-- Возможны дополнительные теги <Картинка> для галереи -->
    <Картинка>import_files/73/73f9d61e-5673-11f0-8041-fa163ea88911_a62d33ce-5673-11f0-8041-fa163ea88912.jpg</Картинка>
</Товар>
```

**Формат путей:**
- Относительные пути: `import_files/73/filename.png`
- Структура: `import_files/{первые_2_символа_ID}/{ID_товара}_{ID_файла}.{расширение}`
- Базовая директория: `data/import_1c/goods/`

### Реализация валидации путей

**Новый приватный метод в XMLDataParser:**

```python
def _validate_image_path(self, path: str) -> str | None:
    """
    Валидация и нормализация пути к изображению

    Args:
        path: Относительный путь к изображению из XML

    Returns:
        Нормализованный путь или None если путь невалиден
    """
    if not path or not isinstance(path, str):
        return None

    # Нормализация пути
    normalized = path.strip().replace("\\", "/")

    # Валидация расширения
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    _, ext = os.path.splitext(normalized.lower())

    if ext not in valid_extensions:
        logger.warning(f"Invalid image extension: {path}")
        return None

    return normalized
```

**Обновление parse_goods_xml():**

```python
# В методе parse_goods_xml(), строки 198-202
image_elements = self._find_children(product_element, "Картинка")
if image_elements:
    validated_images = []
    seen_paths = set()  # Для дедупликации

    for image in image_elements:
        if image.text:
            validated_path = self._validate_image_path(image.text.strip())
            if validated_path and validated_path not in seen_paths:
                validated_images.append(validated_path)
                seen_paths.add(validated_path)

    if validated_images:
        goods_data["images"] = validated_images
```

### Интеграция с ProductDataProcessor

**Связь с Story 3.1.2:**
- ProductDataProcessor будет использовать `goods_data["images"]` для копирования файлов
- Валидированные пути гарантируют что физические файлы существуют
- Нормализованные пути совместимы с Django `default_storage.save()`

### Обработка ошибок

**Стратегия:**
- **Невалидные пути** - WARNING лог, путь пропускается, импорт продолжается
- **Отсутствие изображений** - не является ошибкой, товар импортируется без изображений
- **Дубликаты путей** - дедуплицируются автоматически через set

**Логирование:**
```python
logger.warning(f"Invalid image path for product {goods_data['id']}: {path}")
logger.debug(f"Found {len(validated_images)} valid images for product {goods_data['id']}")
```

## Definition of Done

- [x] **Базовый функционал парсинга изображений реализован** (уже существует в parser.py:198-202)
- [ ] **Добавлена валидация путей изображений** через метод `_validate_image_path()`
- [ ] **Реализована дедупликация путей** через set при парсинге
- [ ] **Написаны unit-тесты** для парсинга изображений с реальными данными
- [ ] **Все существующие тесты проходят** без регрессий
- [ ] **Документация обновлена** (docstrings в parse_goods_xml() и _validate_image_path())
- [ ] **Code review пройден** - соответствие стандартам типизации и стиля кода
- [ ] **Покрытие тестами >= 90%** для новой функциональности

## Testing Strategy

### Unit-тесты (backend/apps/products/tests/test_parser.py)

**Тестовые сценарии:**

1. **test_parse_goods_xml_with_single_image** - товар с одним изображением
2. **test_parse_goods_xml_with_multiple_images** - товар с несколькими изображениями
3. **test_parse_goods_xml_with_no_images** - товар без изображений
4. **test_parse_goods_xml_with_invalid_image_extension** - невалидное расширение файла
5. **test_parse_goods_xml_with_duplicate_image_paths** - дублирующиеся пути
6. **test_parse_goods_xml_with_real_data** - реальный XML из `data/import_1c/goods/`

**Пример теста:**

```python
def test_parse_goods_xml_with_multiple_images(self):
    """Парсинг товара с несколькими изображениями"""
    xml_content = """
    <Каталог>
        <Товары>
            <Товар>
                <Ид>test-product-id</Ид>
                <Наименование>Test Product</Наименование>
                <Картинка>import_files/73/image1.png</Картинка>
                <Картинка>import_files/73/image2.jpg</Картинка>
                <Картинка>import_files/73/image3.webp</Картинка>
            </Товар>
        </Товары>
    </Каталог>
    """

    # Создаем временный XML файл
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(xml_content)
        temp_file = f.name

    try:
        parser = XMLDataParser()
        goods_list = parser.parse_goods_xml(temp_file)

        assert len(goods_list) == 1
        goods_data = goods_list[0]

        assert goods_data["id"] == "test-product-id"
        assert "images" in goods_data
        assert len(goods_data["images"]) == 3
        assert "import_files/73/image1.png" in goods_data["images"]
        assert "import_files/73/image2.jpg" in goods_data["images"]
        assert "import_files/73/image3.webp" in goods_data["images"]
    finally:
        os.unlink(temp_file)
```

### Интеграционные тесты (Story 3.1.3)

- Интеграция с ProductDataProcessor для копирования изображений
- End-to-end тест импорта товаров с изображениями
- Верификация физического наличия файлов в media storage

## Dependencies

**Зависит от:**
- ✅ Epic 3 - Импорт товаров из 1С (реализован)
- ✅ XMLDataParser базовый функционал (существует)
- ✅ GoodsData TypedDict с полем images (существует)

**Блокирует:**
- ⏳ Story 3.1.2 - Импорт изображений в Django media storage (требует валидированные пути)

## Risk Mitigation

**Риск:** Большое количество изображений с невалидными путями может замедлить парсинг из-за WARNING логов

**Митигация:**
- Используем уровень DEBUG для успешных валидаций
- WARNING только для действительно проблемных путей
- Батчинг логов (логировать только первые N невалидных путей)

**Rollback план:**
- Откат изменений в XMLDataParser через git revert
- Валидация является опциональной - можно отключить через feature flag

## Story Complexity

**Оценка:** 2 Story Points (малая задача)

**Обоснование:**
- Базовый функционал УЖЕ реализован (парсинг тегов `<Картинка>`)
- Требуется только добавить валидацию и дедупликацию
- Изменения локализованы в одном файле (parser.py)
- Unit-тесты просты в написании

**Ожидаемое время:** 2-3 часа разработки + 1-2 часа тестирования

---

**Дата создания:** 2025-01-08
**Приоритет:** High (блокирует Story 3.1.2)
**Epic:** Epic 3.1 - Импорт и связь изображений товаров из 1С
**Assigned to:** Developer Team
