# Epic: Рефакторинг интерфейса импорта из 1С - Brownfield Enhancement

## Epic Goal

Разделить функционал импорта из 1С на две независимые страницы: создание нового импорта и просмотр истории сессий, обеспечив более логичный пользовательский интерфейс и исправив недочеты истории 9.5.

## Epic Description

### Existing System Context:

- **Текущая функциональность:** Django admin интерфейс с action "🚀 Запустить импорт из 1С" на странице списка сессий импорта
- **Technology stack:** Django 5.0, Django Admin, Celery для асинхронных задач, Redis для блокировок
- **Integration points:**
  - IntegrationImportSession model (proxy модель ImportSession)
  - Celery задача run_selective_import_task
  - Django admin actions с intermediate page
  - Redis distributed lock для предотвращения дублирования

### Existing Import Infrastructure (из Epic 3):

**Парсеры и процессоры (✅ Реализованы в Epic 3):**

- `XMLDataParser` (`apps/products/services/parser.py`) - парсинг XML файлов CommerceML 3.1
- `ProductDataProcessor` (`apps/products/services/processor.py`) - обработка товаров, категорий, цен
- `CustomerDataParser` (`apps/users/services/parser.py`) - парсинг контрагентов
- `CustomerDataProcessor` (`apps/users/services/processor.py`) - обработка клиентов

**Management команды (✅ Реализованы в Epic 3):**

- `import_catalog_from_1c` - основная команда импорта с параметрами:
  - `--data-dir` - директория с данными (по умолчанию из settings.ONEC_DATA_DIR)
  - `--file-type` - выборочный импорт (goods|offers|prices|rests|all)
  - `--dry-run` - тестовый запуск без записи в БД
  - `--chunk-size` - размер пакетов для bulk операций
  - `--skip-validation` - пропуск валидации для ускорения
  - `--clear-existing` - очистка старых данных перед импортом
- `load_product_stocks` - легковесная команда для обновления только остатков
- `import_customers_from_1c` - импорт клиентов из contragents.xml

**Структура данных 1С (CommerceML 3.1):**

- Сегментированные файлы: `goods_1_*.xml`, `offers_*.xml`, `prices_1_*.xml`, `rests_1_*.xml`
- Справочники: `units.xml`, `storages.xml`, `priceLists.xml`
- Свойства: `propertiesGoods/`, `propertiesOffers/`
- Категории: `groups.xml` (с поддержкой иерархии)
- Клиенты: `contragents.xml`

**ImportSession типы:**

- `CATALOG` - импорт каталога товаров
- `STOCKS` - импорт остатков
- `PRICES` - импорт цен
- `CUSTOMERS` - импорт клиентов

### Enhancement Details:

**Что меняется:**

1. Удаляется admin action "🚀 Запустить импорт из 1С" со страницы сессий
2. Создается новый пункт меню "Импорт из 1С" в разделе ИНТЕГРАЦИИ
3. Страница "Сессии импорта" переименовывается и становится read-only журналом
4. Новая страница "Импорт из 1С" получает форму выбора типов данных и запуска

**Интеграция:**

- Использует существующую Celery задачу run_selective_import_task
- Сохраняет механизм создания ImportSession с celery_task_id
- Поддерживает текущую логику валидации зависимостей
- Сохраняет Redis lock для предотвращения параллельных импортов

**Success criteria:**

- Импорт запускается с новой страницы без выбора существующих сессий
- История импортов доступна на отдельной странице без возможности запуска
- Сохранена вся существующая функциональность импорта

## Stories

### Story 1: Создание новой страницы "Импорт из 1С"

**Описание:**
Создать отдельную страницу для запуска импорта с использованием существующих management команд из Epic 3.

**Технические детали:**

- Создать новый Django admin view без привязки к модели (или использовать ImportSession)
- URL: `/admin/integrations/import_1c/`
- Форма с radio buttons для типов импорта:
  - **"Полный каталог"** → вызывает `import_catalog_from_1c --file-type=all --data-dir={ONEC_DATA_DIR}`
    - Включает: goods, offers, prices, rests, priceLists, units, storages, properties, groups
  - **"Только остатки"** → вызывает `import_catalog_from_1c --file-type=rests --data-dir={ONEC_DATA_DIR}`
  - **"Только цены"** → вызывает `import_catalog_from_1c --file-type=prices --data-dir={ONEC_DATA_DIR}`
  - **"Клиенты"** → вызывает `import_customers_from_1c --file={ONEC_DATA_DIR}/contragents/contragents.xml`
- Перенести существующую логику валидации зависимостей из `_validate_dependencies`
- Использовать существующий Redis lock механизм
- Создавать ImportSession с правильным типом перед запуском Celery задачи
- Добавить страницу в меню ИНТЕГРАЦИИ перед "Сессии импорта"

**Acceptance Criteria:**

- [ ] Страница доступна по URL `/admin/integrations/import_1c/`
- [ ] Форма отображает 4 типа импорта с описанием
- [ ] При выборе типа вызывается соответствующая management команда через Celery
- [ ] Создается ImportSession с правильным типом (CATALOG/STOCKS/PRICES/CUSTOMERS)
- [ ] Валидация зависимостей работает (остатки/цены требуют каталог)
- [ ] Redis lock предотвращает параллельные импорты
- [ ] Пользователь видит сообщение с Task ID и Session ID после запуска

### Story 2: Рефакторинг страницы сессий импорта

**Описание:**
Преобразовать страницу сессий в read-only журнал с сохранением функционала отслеживания прогресса.

**Технические детали:**

- Удалить admin action "🚀 Запустить импорт из 1С" из IntegrationImportSessionAdmin
- Переименовать URL с `/admin/integrations/integrationimportsession/` на `/admin/integrations/session/`
- Сделать страницу read-only:
  - Убрать возможность создания новых сессий через admin
  - Убрать возможность редактирования существующих сессий
  - Оставить только просмотр и фильтрацию
- Сохранить существующий функционал:
  - Метод `celery_task_status` для отображения статуса Celery задачи
  - JavaScript автообновление (`import_session_auto_refresh.js`)
  - Колонки: ID, Тип импорта, Статус, Celery Task, Начало, Окончание, Длительность
  - Фильтры по статусу, типу импорта, дате

**Acceptance Criteria:**

- [ ] URL изменен на `/admin/integrations/session/`
- [ ] Admin action "🚀 Запустить импорт" удален
- [ ] Невозможно создать/редактировать сессии через admin
- [ ] Колонка "Celery Task" отображает актуальный статус
- [ ] Автообновление работает каждые 5 секунд для активных задач
- [ ] Фильтры и поиск работают корректно
- [ ] История всех импортов доступна для просмотра

### Story 3: Тестирование и документация

**Описание:**
Комплексное тестирование нового flow и обновление документации.

**Технические детали:**

- End-to-end тестирование всех типов импорта:
  - Полный каталог (все файлы)
  - Только остатки (сегментированные rests\_\*.xml)
  - Только цены (сегментированные prices\_\*.xml)
  - Клиенты (contragents.xml)
- Проверка валидации зависимостей
- Проверка Redis lock (предотвращение параллельных импортов)
- Проверка создания ImportSession с правильными типами
- Проверка автообновления статуса на странице сессий
- Обновление документации:
  - Инструкция по использованию новой страницы импорта
  - Описание типов импорта и их зависимостей
  - Troubleshooting guide

**Acceptance Criteria:**

- [ ] Все 4 типа импорта протестированы end-to-end
- [ ] Валидация зависимостей работает (остатки/цены требуют каталог)
- [ ] Redis lock предотвращает параллельные импорты
- [ ] Celery задачи выполняются корректно
- [ ] Автообновление статуса работает на странице сессий
- [ ] Документация обновлена с примерами использования
- [ ] Нет регрессий в существующей функциональности импорта

## Dependencies on Epic 3

**Критические зависимости (все ✅ DONE):**

- ✅ **Story 3.1.1** (import-products-structure) - базовая структура импорта
  - Модели: ImportSession, обновленные Product/Category/Brand с onec_id
  - XMLDataParser, ProductDataProcessor
  - Команда import_catalog_from_1c (базовая версия)

- ✅ **Story 3.1.2** (loading-scripts) - расширенная функциональность команд
  - Параметры: --file-type, --chunk-size, --skip-validation, --clear-existing
  - Поддержка сегментированных файлов (goods*\*.xml, prices*\_.xml, rests\_\_.xml)
  - Команды backup_db, restore_db, rotate_backups

- ✅ **Story 3.1.5** (import-session-and-stocks-command) - импорт остатков
  - Команда load_product_stocks
  - Метод XMLDataParser.parse_rests_xml()
  - Batch processing для остатков

- ✅ **Story 3.2.1.0** (import-existing-customers) - импорт клиентов
  - CustomerDataParser, CustomerDataProcessor
  - Команда import_customers_from_1c
  - Модель CustomerSyncLog

**Используемые компоненты из Epic 3:**

```python
# Парсеры
from apps.products.services.parser import XMLDataParser
from apps.users.services.parser import CustomerDataParser

# Процессоры
from apps.products.services.processor import ProductDataProcessor
from apps.users.services.processor import CustomerDataProcessor

# Модели
from apps.products.models import ImportSession
from apps.common.models import CustomerSyncLog

# Management команды (вызов через call_command)
call_command('import_catalog_from_1c', data_dir=..., file_type=...)
call_command('load_product_stocks', file=...)
call_command('import_customers_from_1c', file=...)
```

## Compatibility Requirements

- [x] Существующие API остаются неизменными (Celery задачи)
- [x] Изменения схемы БД не требуются
- [x] UI изменения следуют паттернам Django Admin
- [x] Performance impact минимален (перенос логики)
- [x] Все management команды из Epic 3 работают без изменений

## Risk Mitigation

- **Primary Risk:** Нарушение работы существующих импортов при рефакторинге
- **Mitigation:** Поэтапная миграция с сохранением старого кода до полного тестирования
- **Rollback Plan:** Git revert изменений, рестарт backend и celery контейнеров

## Definition of Done

- [ ] Новая страница "Импорт из 1С" создана и функционирует
- [ ] Страница сессий переименована и работает в read-only режиме
- [ ] Весь функционал импорта протестирован
- [ ] Автообновление статуса работает на странице сессий
- [ ] Документация обновлена
- [ ] Нет регрессий в существующих функциях

## Validation Checklist

### Scope Validation:

- [x] Epic может быть завершен в 3 истории
- [x] Архитектурная документация не требуется
- [x] Enhancement следует существующим паттернам Django Admin
- [x] Интеграционная сложность управляема

### Risk Assessment:

- [x] Риск для существующей системы низкий
- [x] План отката выполним (Git revert)
- [x] Подход к тестированию покрывает существующую функциональность
- [x] Команда имеет достаточные знания точек интеграции

### Completeness Check:

- [x] Цель эпика ясна и достижима
- [x] Истории правильно определены
- [x] Критерии успеха измеримы
- [x] Зависимости идентифицированы

---

## Story Manager Handoff:

"Пожалуйста, разработайте детальные пользовательские истории для этого brownfield эпика. Ключевые соображения:

- Это улучшение существующей системы на Django 5.0 с Django Admin
- Точки интеграции: Celery задачи, Redis locks, ImportSession модели
- Существующие паттерны: Django Admin custom pages, admin actions с intermediate pages
- Критические требования совместимости: сохранение работы Celery задач, поддержка автообновления статуса
- Каждая история должна включать проверку сохранения существующей функциональности

Эпик должен поддерживать целостность системы при разделении функционала импорта на две логически независимые страницы."

---

## Implementation Notes

### Технические детали для разработки:

**1. Новая страница "Импорт из 1С" (Story 1):**

```python
# backend/apps/integrations/admin.py

class ImportFrom1CAdmin(admin.ModelAdmin):
    """Страница для запуска импорта из 1С"""

    def changelist_view(self, request):
        # Отображение формы выбора типа импорта
        if request.method == 'POST':
            import_type = request.POST.get('import_type')

            # Валидация зависимостей
            if import_type in ['stocks', 'prices']:
                if not Product.objects.exists():
                    messages.error(request, "Сначала импортируйте каталог")
                    return redirect('.')

            # Redis lock
            redis_conn = get_redis_connection("default")
            lock = redis_conn.lock("import_catalog_lock", timeout=3600)
            if not lock.acquire(blocking=False):
                messages.warning(request, "Импорт уже запущен")
                return redirect('.')

            try:
                # Создание ImportSession
                session_type_map = {
                    'catalog': ImportSession.ImportType.CATALOG,
                    'stocks': ImportSession.ImportType.STOCKS,
                    'prices': ImportSession.ImportType.PRICES,
                    'customers': ImportSession.ImportType.CUSTOMERS,
                }

                session = ImportSession.objects.create(
                    import_type=session_type_map[import_type],
                    status=ImportSession.ImportStatus.STARTED,
                )

                # Запуск Celery задачи
                data_dir = settings.ONEC_DATA_DIR

                if import_type == 'catalog':
                    task = run_selective_import_task.delay(['catalog'], data_dir)
                elif import_type == 'stocks':
                    task = run_selective_import_task.delay(['stocks'], data_dir)
                elif import_type == 'prices':
                    task = run_selective_import_task.delay(['prices'], data_dir)
                elif import_type == 'customers':
                    task = run_selective_import_task.delay(['customers'], data_dir)

                session.celery_task_id = task.id
                session.save(update_fields=['celery_task_id'])

                messages.success(
                    request,
                    f"Импорт запущен (Task ID: {task.id}, Session ID: {session.pk})"
                )
            finally:
                lock.release()

        # Отображение формы
        context = {
            'title': 'Импорт из 1С',
            'import_types': [
                {'value': 'catalog', 'label': 'Полный каталог',
                 'description': 'Товары, категории, цены, остатки, свойства'},
                {'value': 'stocks', 'label': 'Только остатки',
                 'description': 'Обновление остатков товаров'},
                {'value': 'prices', 'label': 'Только цены',
                 'description': 'Обновление цен товаров'},
                {'value': 'customers', 'label': 'Клиенты',
                 'description': 'Импорт контрагентов из 1С'},
            ],
        }
        return TemplateResponse(request, 'admin/integrations/import_1c.html', context)

# Регистрация
admin.site.register(ImportFrom1C, ImportFrom1CAdmin)
```

**2. Обновление IntegrationImportSessionAdmin (Story 2):**

```python
class IntegrationImportSessionAdmin(admin.ModelAdmin):
    model = IntegrationImportSession

    # Удалить actions
    actions = []  # Было: ["trigger_selective_import"]

    # Read-only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Сохранить существующий функционал
    list_display = (
        "id",
        "import_type",
        "colored_status",
        "celery_task_status",  # ← Сохранить
        "started_at",
        "finished_at",
        "duration",
    )

    @admin.display(description="Celery Task")
    def celery_task_status(self, obj):
        # Существующая реализация из истории 9.5
        if not obj.celery_task_id:
            return format_html('<span style="color: gray;">-</span>')

        from celery.result import AsyncResult
        task_result = AsyncResult(obj.celery_task_id)
        state = task_result.state

        status_map = {
            "PENDING": ("⏳", "gray", "В очереди"),
            "STARTED": ("▶️", "blue", "Выполняется"),
            "SUCCESS": ("✅", "green", "Завершено"),
            "FAILURE": ("❌", "red", "Ошибка"),
            "RETRY": ("🔄", "orange", "Повтор"),
        }

        icon, color, label = status_map.get(state, ("❓", "black", state))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, label
        )

    class Media:
        js = ("admin/js/import_session_auto_refresh.js",)  # ← Сохранить
```

**3. Обновление Celery задачи (apps/integrations/tasks.py):**

Задача `run_selective_import_task` уже реализована и вызывает:

- `import_catalog_from_1c --file-type=all` для 'catalog'
- `import_catalog_from_1c --file-type=rests` для 'stocks'
- `import_catalog_from_1c --file-type=prices` для 'prices'
- `import_customers_from_1c` для 'customers'

**4. Валидация зависимостей:**

```python
def _validate_dependencies(import_types):
    """Проверка зависимостей между типами импорта"""
    if 'stocks' in import_types or 'prices' in import_types:
        if not Product.objects.exists():
            return False, "Сначала импортируйте каталог товаров"
    return True, ""
```

**5. Обработка сегментированных файлов:**

Команда `import_catalog_from_1c` автоматически обрабатывает:

- `goods_1_*.xml`, `goods_2_*.xml`, ... (метод `_collect_xml_files`)
- `prices_1_*.xml`, `prices_2_*.xml`, ...
- `rests_1_*.xml`, `rests_2_*.xml`, ...

**6. JavaScript автообновление (сохранить без изменений):**

```javascript
// backend/static/admin/js/import_session_auto_refresh.js
// Уже реализовано в истории 9.5
// Автообновление каждые 5 секунд для активных задач
```

---

**Статус:** Эпик готов к разработке
**Приоритет:** Высокий (исправление недочетов истории 9.5)
**Оценка:** 3-5 дней разработки
