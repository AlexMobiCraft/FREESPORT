# Исправление проблемы с фильтром и действиями в Django Admin

## Проблема

В административной панели Django при работе с разделом "ИНТЕГРАЦИИ" → "Сессии импорта" возникала следующая проблема:

1. При применении фильтра "Тип импорта" выбор объектов через чекбоксы не работал
2. При попытке выполнить действие "Запустить импорт каталога из 1С" появлялась ошибка: "Чтобы произвести действия над объектами, необходимо их выбрать. Объекты не были изменены."

## Причина

Проблема связана с двумя аспектами:

1. **Django Admin поведение**: При применении фильтров URL страницы изменяется (добавляются query параметры), и Django может передать пустой queryset в action, если объекты не были явно выбраны
2. **Отсутствие валидации**: Метод `trigger_catalog_import` не проверял наличие выбранных объектов перед выполнением

## Решение

Добавлена проверка на наличие выбранных объектов в начале метода `trigger_catalog_import` в файле `backend/apps/integrations/admin.py`:

```python
@admin.action(description="🚀 Запустить импорт каталога из 1С")
def trigger_catalog_import(self, request: HttpRequest, queryset: QuerySet) -> None:
    """
    Запуск импорта каталога из 1С с защитой от concurrent runs.

    Примечание: Это действие не требует выбора объектов, так как
    создает новую сессию импорта независимо от существующих.
    """
    # Проверка: действие не зависит от выбранных объектов
    # Но Django Admin требует выбора для выполнения действия
    # Информируем пользователя, если ничего не выбрано
    if not queryset.exists():
        self.message_user(
            request,
            "ℹ️ Для запуска действия выберите хотя бы одну сессию импорта. "
            "Действие создаст новую сессию импорта независимо от выбора.",
            level="INFO",
        )
        return

    # ... остальной код
```

## Инструкция по использованию

После применения исправления:

1. Перейдите в админ-панель: http://localhost:8001/admin
2. Откройте раздел "ИНТЕГРАЦИИ" → "Сессии импорта"
3. **Важно**: Сначала выберите одну или несколько сессий импорта через чекбоксы
4. Затем можете применить фильтр "Тип импорта" (опционально)
5. Выберите действие "Запустить импорт каталога из 1С" из выпадающего списка
6. Нажмите кнопку "Выполнить"

### Важные замечания

- **Действие требует выбора**: Хотя действие "Запустить импорт каталога из 1С" не зависит от конкретных выбранных сессий (оно создает новую сессию), Django Admin требует выбора хотя бы одного объекта для выполнения любого действия
- **Фильтры не влияют на выбор**: После применения фильтра ваш выбор чекбоксов сохраняется
- **Информативные сообщения**: Если вы забудете выбрать объекты, система покажет информационное сообщение с подсказкой

## Тестирование

Созданы следующие тесты:

### Unit-тесты (`backend/tests/unit/test_integrations_admin.py`)

- ✅ `test_trigger_catalog_import_with_empty_queryset` - проверка поведения при пустом queryset
- ✅ `test_trigger_catalog_import_with_valid_queryset` - проверка успешного выполнения
- ✅ `test_trigger_catalog_import_with_concurrent_lock` - проверка блокировки при параллельном запуске
- ✅ `test_colored_status_display` - проверка отображения статуса
- ✅ `test_duration_calculation_completed` - проверка расчета длительности
- ✅ `test_duration_calculation_in_progress` - проверка отображения прогресса
- ✅ `test_progress_display_with_data` - проверка прогресс-бара
- ✅ `test_progress_display_without_data` - проверка отображения без данных

### Интеграционные тесты (`backend/tests/integration/test_integrations_admin_actions.py`)

- ✅ `test_admin_filter_by_import_type` - проверка фильтрации
- ✅ `test_admin_action_with_selection_and_filter` - проверка действия с фильтром
- ✅ `test_admin_list_display_fields` - проверка отображения полей
- ✅ `test_admin_search_functionality` - проверка поиска
- ✅ `test_admin_detail_page_readonly_fields` - проверка readonly полей

Все тесты успешно проходят ✅

## Запуск тестов

```bash
# Unit-тесты
docker exec freesport-backend pytest tests/unit/test_integrations_admin.py -v

# Интеграционные тесты
docker exec freesport-backend pytest tests/integration/test_integrations_admin_actions.py -v
```

## Файлы изменений

### Основное исправление

- ✏️ `backend/apps/integrations/admin.py` - добавлена проверка queryset
- ➕ `backend/tests/unit/test_integrations_admin.py` - новый файл с unit-тестами (8 тестов)
- ➕ `backend/tests/integration/test_integrations_admin_actions.py` - новый файл с интеграционными тестами

### Исправление настройки ONEC_DATA_DIR

- ✏️ `backend/freesport/settings/base.py` - исправлена настройка ONEC_DATA_DIR (теперь возвращает строку и поддерживает переменную окружения)
- ✏️ `backend/backend/settings.py` - добавлена настройка ONEC_DATA_DIR (для совместимости)
- ➕ `backend/tests/unit/test_settings_onec.py` - новый файл с тестами настроек (6 тестов)
- ➕ `docs/fixes/admin-filter-action-fix.md` - документация по исправлению

## Дополнительное исправление: настройка ONEC_DATA_DIR

### Проблема

После первого исправления возникла новая ошибка: "❌ Ошибка при импорте каталога: Директория не найдена: /data/import_1c"

### Причина

Отсутствовала настройка `ONEC_DATA_DIR` в `backend/backend/settings.py`, которая указывает путь к директории с данными для импорта из 1С.

### Решение

Добавлена настройка в конец файла `backend/backend/settings.py`:

```python
# ==============================================================================
# ИНТЕГРАЦИЯ С 1С (1C INTEGRATION)
# ==============================================================================
# Путь к директории с данными для импорта из 1С
# В Docker контейнере это будет /app/data/import_1c
# В локальной разработке это BASE_DIR.parent / "data" / "import_1c"
ONEC_DATA_DIR = os.environ.get(
    "ONEC_DATA_DIR",
    str(BASE_DIR.parent / "data" / "import_1c")
)
```

### Проверка

Директория `/app/data/import_1c` существует в Docker контейнере и содержит:

- `contragents/` - контрагенты
- `goods/` - товары (содержит XML файлы)
- `groups/` - группы товаров
- `offers/` - предложения
- `priceLists/` - прайс-листы
- `prices/` - цены
- `propertiesGoods/` - свойства товаров
- `propertiesOffers/` - свойства предложений
- `rests/` - остатки
- `storages/` - склады
- `units/` - единицы измерения

## Дата исправления

03 ноября 2025
