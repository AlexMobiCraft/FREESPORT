# История: Оркестрация Асинхронного Импорта

**Story ID:** 3.1
**Story Key:** 3-1-async-import-orchestration
**Epic:** 3 - Asynchronous Import Triggering
**Status:** done

## История

**Как** Система,
**Я хочу** запускать процесс импорта асинхронно, когда 1С отправляет команду импорта,
**Чтобы** соединение с 1С не прерывалось по таймауту во время обработки данных.

## Критерии Приемки (Acceptance Criteria)

### AC1: Эндпоинт Запуска Импорта
**Дано:** Файлы успешно загружены и распакованы в `MEDIA_ROOT/1c_import/`
**Когда:** Отправлен GET-запрос с параметрами `?mode=import&filename=<любое_имя_файла>`
**Тогда:** Система должна проверить наличие активных сессий (`pending` или `in-progress`)
**И:** Если активных сессий нет, создать запись `ImportSession` со статусом `pending`
**И:** Запустить Celery-задачу `process_1c_import_task` и вернуть `success`
**И:** Если активная сессия существует, вернуть ответ `failure\nImport already in progress` с кодом 200 (согласно протоколу 1С)

### AC2: Успешное Выполнение
**Дано:** Задача импорта завершилась успешно
**Тогда:** Статус `ImportSession` должен обновиться на `completed`

### AC3: Обработка Ошибок
**Дано:** Задача импорта завершилась с ошибкой
**Тогда:** Статус `ImportSession` должен обновиться на `failed` с деталями ошибки
**И:** Используется пакетная атомарность (Batch-Level Atomicity) для сохранения прогресса и предотвращения перерасхода памяти. Частично успешно обработанные пакеты сохраняются в БД.

### AC4: Оркестрация Задач (Универсальная Задача)
**Дано:** Запущена задача `process_1c_import_task`
**Тогда:** Она должна проанализировать директорию `1c_import/`
**И:** Обработать файлы в правильном порядке зависимостей (goods -> groups -> offers -> prices -> rests)
**И:** Использовать существующий `VariantImportProcessor` или эквивалентную логику для обработки XML

### AC5: Индикация Прогресса (UX)
**Дано:** Задача импорта находится в процессе выполнения
**Тогда:** Она должна периодически (например, каждые 100 обработанных объектов) обновлять поле `updated_at` в `ImportSession`
**И:** Добавлять текстовые записи о текущем этапе в поле `report` (например, "Обработка товаров: 500 из 1200")
**И:** Это позволит администратору видеть прогресс через стандартный интерфейс Django Admin

### AC6: Защита от Зависших Сессий (Cleanup)
**Дано:** Существует сессия в статусе `in-progress`, которая не обновлялась более 2 часов
**Тогда:** Система должна иметь механизм (Celery Beat задача), который переводит такие сессии в статус `failed` с пометкой "Зависла/Таймаут"
**И:** Это необходимо для разблокировки очереди импорта (согласно AC1)

## Задачи (Tasks)

### Review Follow-ups (AI)
- [x] [AI-Review][High] Architecture: Move sync ZIP unpacking from Import1CView to Celery task to prevent timeouts <!-- file:backend/apps/integrations/onec_exchange/views.py -->
- [x] [AI-Review][Medium] Reliability: Explicitly set COMPLETED/FAILED status in process_1c_import_task instead of relying on management command <!-- file:backend/apps/products/tasks.py -->
- [x] [AI-Review][Low] Documentation: Add test_import_session_structure.py and test_import_orchestration.py to Story File List <!-- file:_bmad-output/implementation-artifacts/3-1-async-import-orchestration.md -->

- [x] [AI-Review][Medium] Coverage: Add integration test for ImportSession.status -> COMPLETED transition (currently mocked) <!-- file:backend/apps/products/tests/test_import_orchestration_tasks.py -->
- [x] [AI-Review][Medium] Git State: Track `backend/freesport/celery.py` and `backend/apps/products/services/variant_import.py` in Story File List <!-- file:_bmad-output/implementation-artifacts/3-1-async-import-orchestration.md -->
- [x] [AI-Review][Low] Refactor: Remove redundant error handling in process_1c_import_task (double DB write) <!-- file:backend/apps/products/tasks.py -->
- [x] [AI-Review][Medium] Git State: Track `apps/products/tasks.py` and `apps/products/migrations/0039_...`, `0040_...` <!-- file:apps/products/tasks.py -->
- [x] [AI-Review][Medium] Git State: Track `apps/integrations/tests/test_import_orchestration_view.py` <!-- file:apps/integrations/tests/test_import_orchestration_view.py -->
- [x] [AI-Review][Medium] Git State: Track `apps/products/tests/...` files <!-- file:apps/products/tests/ -->
- [x] [AI-Review][Medium] AC3 Atomicity: Document/Accept batch-level atomicity or implement improvements <!-- file:apps/products/management/commands/import_products_from_1c.py -->
- [x] [AI-Review][Low] Task/Command Coupling: Harden process_1c_import_task error handling <!-- file:apps/products/tasks.py -->
- [x] [AI-Review][Critical] Test Quality: Fix broken test `test_process_1c_import_task_logic` in `test_import_orchestration.py` (incomplete, missing assertions) <!-- file:backend/apps/products/tests/integration/test_import_orchestration.py -->
- [x] [AI-Review][Medium] Documentation: Add missing test file `test_import_orchestration.py` to Story File List <!-- file:_bmad-output/implementation-artifacts/3-1-async-import-orchestration.md -->

- [x] **Инфраструктура и Модели**
    - [x] Проверить/Обновить модель `ImportSession` в `apps/products/models.py` (поля: status, created_at, updated_at, finished_at, report).
    - [x] Создать/Обновить миграцию.

- [x] **Реализация Celery-задач**
    - [x] Создать `process_1c_import_task` в `apps/products/tasks.py`.
    - [x] Реализовать логику обновления прогресса (`report` и `updated_at`) внутри циклов обработки.
    - [x] **Реализовать задачу очистки:** `cleanup_stale_import_sessions` (поиск старых `in-progress` сессий).
    - [x] Настроить запуск задачи очистки через Celery Beat (например, раз в час).

- [x] **Интеграция API Эндпоинта**
    - [x] Обновить метод `get()` в `Import1CView` для обработки `mode=import`.
    - [x] Реализовать проверку на наличие активных сессий `ImportSession`.
    - [x] Добавить логику возврата `failure\nImport already in progress`, если импорт уже запущен.
    - [x] Добавить логику вызова `process_1c_import_task.delay(session_id)`.
    - [x] Немедленно вернуть текстовый ответ `success`.

- [x] **Тестирование**
    - [x] Создать юнит-тесты для модели `ImportSession`.
    - [x] Создать юнит-тесты для `process_1c_import_task` (с моками актуальной логики импорта).
    - [x] Создать интеграционный тест для API эндпоинта (проверить, что задача вызывается, сессия создается, ответ корректный).
    - [x] **Добавить тест на блокировку (TC7):** повторный запрос `mode=import` при наличии активной сессии должен возвращать ошибку.
    - [x] Проверить переходы статусов `ImportSession` (pending -> completed/failed).

## Заметки Разработчика

### Архитектура и Контекст
- **Ссылка:** `apps/products/services/import_1c/` и `apps/products/management/commands/import_products_from_1c.py` уже существуют (из Обзора Проекта). Используйте их повторно!
- **Директория:** Распакованные файлы находятся в `MEDIA_ROOT/1c_import/` (реализовано в Истории 2.2).
- **Модель:** `ImportSession` упоминается в Architecture.md как гарант атомарности.
- **Процессор:** `VariantImportProcessor` — это процессор нового поколения.

### Предыдущие Уроки
- **История 2.2:** Мы утвердили структуру папок. Задача ДОЛЖНА искать файлы в `1c_import/goods/`, `1c_import/offers/` и т.д., а не только в корне `1c_import/`.
- **Формат Ответа:** Помните, что 1С ожидает `text/plain` "success" или "failure".

### Технические Ограничения
- **Асинхронность:** ОБЯЗАТЕЛЬНО использовать Celery (`.delay()`).
- **Логирование:** Логировать все основные шаги как в стандартный лог, так и в поле report модели `ImportSession`, если доступно.
- **Идемпотентность:** `mode=import` создает НОВУЮ сессию каждый раз.

## Запись Dev Агента

### План Реализации
- [x] Инициализация
- [x] Тесты
- [x] Реализация
- [x] Верификация

### Список Файлов
- `backend/apps/products/models.py`
- `backend/apps/products/tasks.py`
- `backend/apps/products/tests/integration/test_import_orchestration.py`
- `backend/apps/integrations/onec_exchange/views.py`
- `backend/apps/integrations/tests/test_import_orchestration_view.py`
- `backend/apps/products/tests/test_import_orchestration_models.py`
- `backend/apps/products/tests/test_import_orchestration_tasks.py`
- `backend/apps/products/tests/test_import_session_model.py`
- `backend/apps/products/migrations/0040_alter_importsession_created_at.py`
- `backend/freesport/settings/base.py`
- `backend/freesport/celery.py`
- `backend/apps/products/services/variant_import.py`

### Заметки о Завершении
- Verified ImportSession model structure with unit tests.
- Generated migration for ImportSession created_at field.
- Implemented and tested Celery tasks for asynchronous import and session cleanup.
- Настроено расписание Celery Beat для задачи очистки.
- Проверена интеграция Import1CView с новыми юнит-тестами, покрывающими сценарии успеха и ошибок.
- **Review Follow-up:** Задокументирована стратегия пакетной атомарности в `import_products_from_1c.py`.
- **Review Follow-up:** Усилена обработка ошибок в `process_1c_import_task` (CommandError, TimeLimitExceeded) в `tasks.py`.
- **Review Follow-up:** Проверено отслеживание git для всех новых файлов и миграций.
- **Verification:** Rewrite `test_import_session_model.py` to fix legacy/incorrect tests. Verified all orchestration tests (model, tasks, view) pass (17 tests).

### Change Log
- 2026-01-24: Исправлены замечания Amelia (Amelia Review): Удалены отладочные файлы, унифицированы статусы сессий (STARTED -> IN_PROGRESS), исправлена хардкод аутентификации в views.py, обновлены тесты. AC3 изменен на Batch-Level Atomicity.
- 2026-01-24: Завершены все задачи Review Follow-up. Исправлен и дополнен тест `test_process_1c_import_task_logic` (покрыты сценарии успеха и ошибок). Обновлен список файлов.
- 2026-01-24: Исправлены замечания код-ревью - решено 5 пунктов (Документация атомарности, Обработка ошибок, Состояние Git).
- 2026-01-24: Code Review - added 3 follow-up tasks (Test Coverage, Git State, Refactoring). Status reverted to in-progress.
- 2026-01-24: Change Log - Resolved AI Review Follow-ups: Enforced COMPLETED status, fixed redundant error handling, updated File List with correct paths.
- 2026-01-24: Resolved [High] Architecture issue: Refactored Import1CView to delegate ZIP unpacking to `process_1c_import_task` via Celery (NFR2/Timeout prevention).
- 2026-01-24: Tests: Rewrite `test_import_session_model.py` to target Story 3.1 requirements (removed incorrect Story 15.1 legacy code).

## Статус
done