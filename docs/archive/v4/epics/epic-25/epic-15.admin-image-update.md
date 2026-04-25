# Epic 15: Обновление изображений товаров через админ-панель Django - Brownfield Enhancement

> **Тип**: Brownfield Enhancement
> **Дата создания**: 2025-11-26
> **Статус**: 📋 Запланирован
> **Приоритет**: Medium

---

## Epic Goal

Добавить в админ-панель Django возможность обновления изображений товаров из 1С через удобный интерфейс, используя существующую функцию `import_product_images()` из `ProductDataProcessor`.

---

## Epic Description

### Existing System Context

**Текущая функциональность:**

- Существует класс `ProductDataProcessor` ([processor.py:784-924](backend/apps/products/services/processor.py#L784-L924)) с методом `import_product_images()`, который:
  - Копирует изображения товаров из директории 1С в Django media storage
  - Устанавливает первое изображение как `main_image`
  - Добавляет остальные изображения в `gallery_images`
  - Поддерживает валидацию изображений через Pillow
  - Предотвращает дубликаты в галерее
  - Сохраняет структуру поддиректорий из 1С

- Админ-панель импорта 1С расположена по адресу: `http://localhost:8001/admin/integrations/import_1c/`
- Реализован механизм запуска импорта через custom admin view ([views.py](backend/apps/integrations/views.py))
- Существует система ImportSession для отслеживания процесса импорта

**Технологический стек:**

- Backend: Django 5.2.7 + Django REST Framework
- База данных: PostgreSQL 15+ (JSONB для хранения `gallery_images`)
- Task Queue: Celery + Redis для асинхронных задач
- Admin: Django Admin с custom views и URL routing

**Точки интеграции:**

- `apps/integrations/admin_urls.py` - monkey-patching для добавления custom URLs
- `apps/integrations/views.py` - custom view `import_from_1c_view` для страницы импорта
- `apps/integrations/admin.py` - `ImportSessionAdmin` для отображения сессий
- `apps/products/services/processor.py` - `ProductDataProcessor.import_product_images()`

### Enhancement Details

**Что добавляется:**

1. **Новый тип импорта "Изображения товаров"** в форме выбора на странице `/admin/integrations/import_1c/`:
   - Radio button: "Только изображения товаров"
   - Описание: "Обновление изображений товаров из директории 1С (main_image и gallery_images)"
   - Files: "data/import*1c/goods/import_files/XX/*.jpg, data/import*1c/goods/import_files/XX/*.png"
   - Requires catalog: `true` (требуется наличие товаров в БД)

2. **Backend обработка**:
   - Новый тип в `ImportSession.ImportType`: `IMAGES`
   - Celery задача для обработки импорта изображений
   - Использование существующего метода `ProductDataProcessor.import_product_images()`
   - Отображение прогресса в реальном времени через `ImportSessionAdmin`

3. **Валидация и безопасность**:
   - Проверка наличия товаров в БД перед запуском
   - Проверка существования директории `data/import_1c/goods/import_files/`
   - Redis lock для предотвращения параллельного запуска
   - Опциональная валидация изображений через Pillow

**Как это интегрируется:**

- Расширение существующего механизма импорта через добавление нового типа
- Использование существующей архитектуры Celery tasks
- Интеграция с системой мониторинга `ImportSession`
- Соответствие паттернам существующих типов импорта (catalog, stocks, prices, customers)

**Критерии успеха:**

- ✅ Администратор может выбрать тип импорта "Изображения товаров"
- ✅ Импорт запускается асинхронно через Celery
- ✅ Прогресс отображается в реальном времени на странице сессий
- ✅ Изображения корректно загружаются для существующих товаров
- ✅ Существующие изображения не дублируются
- ✅ При ошибках показываются понятные сообщения
- ✅ Все тесты проходят успешно

---

## Stories

### 1. Story 15.1: Добавление типа импорта "Изображения" в админ-панель

**Описание**: Расширить форму выбора типа импорта на странице `/admin/integrations/import_1c/` добавлением опции "Только изображения товаров".

**Задачи**:

- Добавить новый `ImportType.IMAGES` в модель `ImportSession`
- Обновить список `import_types` в `import_from_1c_view` ([views.py:54-83](backend/apps/integrations/views.py#L54-L83))
- Добавить валидацию зависимостей (требуется каталог товаров)
- Обновить template `admin/integrations/import_1c.html`

**Acceptance Criteria**:

- Radio button "Только изображения товаров" отображается в форме
- При отсутствии товаров в БД показывается предупреждение
- Выбор типа сохраняется при отправке формы

---

### 2. Story 15.2: Реализация Celery задачи для импорта изображений

**Описание**: Создать Celery задачу `run_image_import_task`, которая использует существующий метод `ProductDataProcessor.import_product_images()` для обработки изображений всех товаров.

**Задачи**:

- Создать новую Celery задачу в `apps/integrations/tasks.py`
- Реализовать итерацию по товарам с обновлением прогресса
- Использовать `ProductDataProcessor.import_product_images()` для каждого товара
- Обновлять `ImportSession` с прогрессом и статистикой
- Обрабатывать ошибки и логировать детали

**Acceptance Criteria**:

- Задача запускается асинхронно при выборе типа "Изображения"
- Прогресс обновляется в `ImportSession.report_details`
- Статистика содержит: total_products, processed, copied, skipped, errors
- При ошибках сессия помечается как failed с детальным error_message

---

### 3. Story 15.3: Интеграция с системой мониторинга и тестирование

**Описание**: Интегрировать импорт изображений с существующей системой мониторинга `ImportSessionAdmin` и обеспечить покрытие тестами.

**Задачи**:

- Обновить маппинг типов в `_create_and_run_import` ([views.py:229-239](backend/apps/integrations/views.py#L229-L239))
- Добавить проверку директории `import_files/` перед запуском
- Создать интеграционные тесты для импорта изображений
- Добавить unit тесты для валидации зависимостей
- Обновить документацию в `CLAUDE.md` и `scripts/server/README_IMPORT_ON_SERVER.md`

**Acceptance Criteria**:

- Импорт изображений отображается в списке сессий с корректными статусами
- Прогресс-бар работает корректно (если применимо)
- Тесты покрывают: успешный импорт, отсутствие товаров, отсутствие директории
- Coverage >= 80% для нового кода
- Документация обновлена с примерами использования

---

## Compatibility Requirements

- [x] Существующие API остаются без изменений
- [x] Схема БД расширяется только через добавление нового enum значения
- [x] UI следует существующим паттернам админ-панели
- [x] Производительность: импорт для 1000 товаров < 10 минут
- [x] Не ломает существующие типы импорта (catalog, stocks, prices, customers)

---

## Risk Mitigation

### Primary Risk

**Риск**: Импорт большого количества изображений может вызвать таймауты или исчерпание памяти.

**Mitigation**:

- Использовать chunked processing (по 100 товаров за итерацию)
- Асинхронная обработка через Celery с большим timeout (1 час)
- Мониторинг памяти и прогресса через `ImportSession`
- Возможность пропустить валидацию изображений (`validate_images=False`) для производительности

### Rollback Plan

1. Удалить новый тип `ImportType.IMAGES` из выбора в UI
2. Откатить миграцию добавления enum значения (если применимо)
3. Удалить Celery задачу `run_image_import_task`
4. Восстановить предыдущую версию `import_from_1c_view`

**Шаги отката**:

```bash
# 1. Откатить миграции Django
python manage.py migrate integrations <previous_migration>

# 2. Удалить новый код из views.py и tasks.py
git revert <commit_hash>

# 3. Перезапустить Celery workers
docker compose restart celery celery-beat
```

---

## Definition of Done

- [x] Story 15.1 завершена с acceptance criteria
- [x] Story 15.2 завершена с acceptance criteria
- [x] Story 15.3 завершена с acceptance criteria
- [x] Все интеграционные и unit тесты проходят
- [x] Существующая функциональность импорта не нарушена (regression tests)
- [x] Точки интеграции работают корректно (admin URL, views, tasks)
- [x] Документация обновлена с примерами
- [x] Code review пройден и замечания исправлены
- [x] Нет regression в существующих фичах (verified through tests)

---

## Story Manager Handoff

**Story Manager Handoff:**

"Пожалуйста, разработайте детальные user stories для этого brownfield epic. Ключевые соображения:

- **Это расширение существующей системы** на Django 5.2.7 + DRF + PostgreSQL 15+ + Celery
- **Точки интеграции**:
  - `apps/integrations/admin_urls.py` - добавление custom URL
  - `apps/integrations/views.py` - расширение формы выбора импорта
  - `apps/integrations/tasks.py` - новая Celery задача
  - `apps/products/services/processor.py` - использование метода `import_product_images()`

- **Существующие паттерны для следования**:
  - Архитектура custom admin views через monkey-patching
  - Celery задачи с Redis locks
  - Система мониторинга через `ImportSession` и `ImportSessionAdmin`
  - Валидация зависимостей перед запуском импорта

- **Критические требования совместимости**:
  - Не ломать существующие типы импорта (catalog, stocks, prices, customers)
  - Использовать существующий метод `ProductDataProcessor.import_product_images()`
  - Следовать паттернам обработки ошибок и логирования
  - Каждая story должна включать проверку, что существующая функциональность остается неизменной

Epic должен поддерживать целостность системы импорта, добавляя удобный способ обновления изображений товаров через админ-панель."

---

## Notes

- **Scope**: Этот Epic специально ограничен 3 stories для быстрой реализации
- **Приоритет**: Medium - функциональность полезна, но не критична для MVP
- **Dependencies**: Требует завершенной Story 3.1.2 (импорт изображений реализован)
- **Related Epics**: Epic 3 (Интеграция с 1С)

---

## References

- [ProductDataProcessor.import_product_images()](backend/apps/products/services/processor.py#L784-L924)
- [import_from_1c_view](backend/apps/integrations/views.py#L29-L85)
- [ImportSessionAdmin](backend/apps/integrations/admin.py#L14-L236)
- [Admin custom URLs](backend/apps/integrations/admin_urls.py)
- [CLAUDE.md - Интеграции с 1С](CLAUDE.md#интеграции-и-внешние-сервисы)
