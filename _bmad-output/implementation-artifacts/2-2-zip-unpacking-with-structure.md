# Story 2.2: Сохранение файлов и маршрутизация

Status: review

<!-- Примечание: Валидация опциональна. Запустите validate-create-story для проверки качества перед dev-story. -->

## Story

Как Backend-разработчик,
Я хочу, чтобы система сохраняла загруженные файлы и маршрутизировала не-архивные файлы в правильные папки,
Чтобы при вызове `mode=import` все файлы были готовы к обработке в правильной структуре.

## Критерии приёмки

1. **Сохранение файлов в temp директорию**
   * **Дано** Загрузка файла через `mode=file` (любое расширение)
   * **Когда** Загрузка успешно завершается
   * **Тогда** Файл сохраняется в `1c_temp/<sessid>/<filename>`
   * **И** ZIP-архивы НЕ распаковываются (распаковка в Story 3.1)
   * **И** Ответ остаётся `success`

2. **Маршрутизация XML файлов**
   * **Дано** Полностью загруженный файл с расширением `.xml`
   * **Когда** Загрузка завершена
   * **Тогда** Файл перемещается в соответствующую папку `1c_import/<sessid>/` по имени:
     - `goods*.xml` -> `1c_import/<sessid>/goods/`
     - `offers*.xml` -> `1c_import/<sessid>/offers/`
     - `prices*.xml` -> `1c_import/<sessid>/prices/`
     - `rests*.xml` -> `1c_import/<sessid>/rests/`
     - `groups*.xml` -> `1c_import/<sessid>/groups/`

3. **Маршрутизация изображений**
   * **Дано** Полностью загруженный файл с расширением `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
   * **Когда** Загрузка завершена
   * **Тогда** Файл перемещается в `1c_import/<sessid>/import_files/`

4. **ZIP файлы остаются в temp**
   * **Дано** Полностью загруженный файл с расширением `.zip` (регистронезависимо)
   * **Когда** Загрузка завершена
   * **Тогда** Файл остаётся в `1c_temp/<sessid>/` БЕЗ распаковки
   * **И** Распаковка будет выполнена в Story 3.1 при вызове `mode=import`

5. **Прочие файлы**
   * **Дано** Файл с неизвестным расширением (не XML, не изображение, не ZIP)
   * **Когда** Загрузка завершена
   * **Тогда** Файл перемещается в корень `1c_import/<sessid>/`

## Задачи / Подзадачи

- [x] **Задача 1: Расширение настроек** (КП: 1-5)
  - [x] Добавить `IMPORT_DIR` в конфиг `ONEC_EXCHANGE`: `MEDIA_ROOT / '1c_import'`
  - [x] Документировать новую настройку в settings/base.py

- [x] **Задача 2: Создание FileRoutingService** (КП: 2, 3, 5)
  - [x] Создать `backend/apps/integrations/onec_exchange/routing_service.py`
  - [x] Реализовать класс `FileRoutingService` с изоляцией сессий
  - [x] Метод `route_file(filename: str) -> Path` для определения целевой папки
  - [x] Метод `move_to_import(filename: str) -> Path` для перемещения файла
  - [x] Метод `should_route(filename: str) -> bool` — True для XML и изображений, False для ZIP

- [x] **Задача 3: Логика маршрутизации** (КП: 2, 3, 5)
  - [x] Реализовать константы маршрутизации:
    ```python
    XML_ROUTING_RULES = {
        'goods': 'goods/',
        'offers': 'offers/',
        'prices': 'prices/',
        'rests': 'rests/',
        'groups': 'groups/',
    }
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ZIP_EXTENSIONS = {'.zip'}
    ```
  - [x] Pattern matching для XML: `filename.lower().startswith(key)`
  - [x] Pattern matching для изображений: `Path(filename).suffix.lower() in IMAGE_EXTENSIONS`
  - [x] ZIP файлы: `Path(filename).suffix.lower() in ZIP_EXTENSIONS` → НЕ маршрутизировать

- [x] **Задача 4: Интеграция с обработчиком загрузки** (КП: 1, 4)
  - [x] Модифицировать `views.py:handle_file_upload()` для вызова routing после успешной записи
  - [x] Если `should_route(filename)` == True → вызвать `move_to_import()`
  - [x] Если ZIP файл → оставить в temp (без действий)
  - [x] Сохранить существующий формат ответа (`success` / `failure\n...`)

- [x] **Задача 5: Тестирование**
  - [x] TC1: Загрузка `goods.xml` -> перемещён в `1c_import/<sessid>/goods/`
  - [x] TC2: Загрузка `offers_1_uuid.xml` -> перемещён в `1c_import/<sessid>/offers/`
  - [x] TC3: Загрузка `image.jpg` -> перемещён в `1c_import/<sessid>/import_files/`
  - [x] TC4: Загрузка `photo.PNG` (uppercase) -> перемещён в `import_files/`
  - [x] TC5: Загрузка `import.zip` -> остаётся в `1c_temp/<sessid>/` (НЕ распакован)
  - [x] TC6: Загрузка `archive.ZIP` (uppercase) -> остаётся в temp
  - [x] TC7: Загрузка `unknown.dat` -> перемещён в корень `1c_import/<sessid>/`
  - [x] TC8: Изоляция сессий -> файлы не смешиваются между сессиями
  - [x] TC9: Повторная загрузка файла с тем же именем -> перезаписывает существующий

- [x] **Review Follow-ups (AI) - Round 1**
  - [x] [AI-Review][Medium] Commit untracked files: routing_service.py, test_file_routing.py, conftest.py
  - [x] [AI-Review][Low] Fix DeprecationWarning: CheckConstraint.check -> condition in apps/cart/models.py

- [x] **Review Follow-ups (AI) - Round 2** (Code Review 2026-01-24)
  - [x] [AI-Review][High] Add integration tests for routing in views.py - verify end-to-end file routing after upload [backend/tests/integration/test_1c_file_upload.py]
  - [x] [AI-Review][Medium] Clarify File List: cart/models.py already committed in 00e8c82, cart/views.py shows in git status but not in File List [story documentation]
  - [x] [AI-Review][Medium] Consider adding routing failure indication to client response (optional: `success\nwarning: routing failed`) [backend/apps/integrations/onec_exchange/views.py:240-243]
  - [x] [AI-Review][Low] Improve docstring for route_file() - clarify that empty string return means "root directory" [backend/apps/integrations/onec_exchange/routing_service.py:104]

## Заметки для разработчика

### Архитектурные паттерны и ограничения

- **Service Layer Pattern:** Логика маршрутизации в `routing_service.py`, НЕ в views.py
- **Изоляция сессий:** ВСЕ import файлы в `1c_import/<sessid>/` для предотвращения коллизий
- **Формат ответа:** 1С ожидает `text/plain` с `success` или `failure\n<message>`
- **ZIP остаётся в temp:** Распаковка переносится в Story 3.1 (`mode=import`)
- **Существующие паттерны:** Следовать `FileStreamService` из Story 2.1

### Разделение ответственности (Party Mode Decision)

```
Story 2.1: mode=file → сохранение чанков в 1c_temp/<sessid>/
Story 2.2: mode=file → маршрутизация XML/images в 1c_import/<sessid>/ (эта story)
Story 3.1: mode=import → распаковка ZIP + триггер Celery task
```

**Почему ZIP не распаковывается здесь:**
- 1С отправляет файлы чанками
- `mode=import` — явный сигнал "все файлы загружены"
- Распаковка неполного ZIP = `BadZipFile` или corrupted data

### Интеллект предыдущей истории (2.1)

**Ключевые паттерны для переиспользования:**
- `FileStreamService._ensure_session_dir()` - создание директории с parents
- `get_file_path()` с санитизацией имени файла (`Path(filename).name`)
- Формат логирования: `f"... (session: {self.session_id[:8]}...)"`
- Доступ к настройкам: `settings.ONEC_EXCHANGE.get('KEY', default)`

**Файлы, созданные в 2.1:**
- `backend/apps/integrations/onec_exchange/file_service.py` - FileStreamService
- `backend/apps/integrations/onec_exchange/views.py` - ICExchangeView
- `backend/tests/integration/test_1c_file_upload.py` - 26 тестов

### Заметки о структуре проекта

**Новые файлы для создания:**
- `backend/apps/integrations/onec_exchange/routing_service.py` - FileRoutingService
- `backend/tests/integration/test_1c_file_routing.py` - тесты маршрутизации

**Файлы для модификации:**
- `backend/freesport/settings/base.py` - добавить `IMPORT_DIR` в `ONEC_EXCHANGE`
- `backend/apps/integrations/onec_exchange/views.py` - вызвать routing service

### Последовательность реализации

1. Добавить настройку `IMPORT_DIR`
2. Создать `routing_service.py` с логикой маршрутизации
3. Написать тесты (TDD)
4. Интегрировать в `views.py:handle_file_upload()`
5. Запустить полный набор тестов

### Что переносится в Story 3.1

Следующие элементы будут реализованы в Story 3.1:
- Распаковка ZIP архивов
- Защита от Zip Bomb (MAX_UNCOMPRESSED_SIZE, MAX_FILES_IN_ARCHIVE)
- Защита от Path Traversal в архивах
- Игнорирование symlinks при извлечении
- Удаление оригинального ZIP после распаковки

### Ссылки

- [Источник: _bmad-output/planning-artifacts/epics.md#Story 2.2]
- [Источник: _bmad-output/implementation-artifacts/2-1-file-stream-upload.md]
- [Party Mode Discussion: 2026-01-23]

## Запись Dev Agent

### Использованная модель агента

Amelia (Developer Agent) via Gemini 2.0 Flash

### Ссылки на лог отладки

N/A

### Список заметок о завершении

- **Реализация:**
  - Добавлен `IMPORT_DIR` в `ONEC_EXCHANGE` settings: `MEDIA_ROOT / '1c_import'`
  - Создан `FileRoutingService` с методами `route_file()`, `move_to_import()`, `should_route()`
  - XML файлы маршрутизируются по prefix (goods, offers, prices, rests, groups)
  - Изображения (.jpg, .jpeg, .png, .gif, .webp) маршрутизируются в `import_files/`
  - ZIP файлы НЕ маршрутизируются (остаются в temp для Story 3.1)
  - Прочие файлы маршрутизируются в корень import директории

- **Тестирование:**
  - 29 unit тестов написаны и прошли успешно
  - Все 9 тест-кейсов из AC покрыты
  - 6 интеграционных тестов добавлено в `test_1c_file_routing.py`
  - Исправлены регрессии в `test_1c_file_upload.py` и `test_debug_cart.py`

- **Интеграция:**
  - `views.py:handle_file_upload()` вызывает routing service после успешной записи
  - Routing ошибки логируются но не прерывают upload (файл уже сохранён в temp)

- **Review Follow-ups Resolved:**
  - ✅ Resolved review finding [Medium]: Commit untracked files - all implementation files committed
  - ✅ Resolved review finding [Low]: Fix DeprecationWarning - CheckConstraint.check -> condition in cart/models.py
  - ✅ Resolved review finding [High]: Added integration tests for file routing (6 passed)
  - ✅ Resolved review finding [Medium]: Clarified File List
  - ✅ Resolved review finding [Medium]: Decision to keep simple "success" response for protocol compliance
  - ✅ Resolved review finding [Low]: Improved docstring for `route_file`

### Список файлов

- `backend/freesport/settings/base.py` (Изменён: добавлен IMPORT_DIR в ONEC_EXCHANGE)
- `backend/apps/integrations/onec_exchange/routing_service.py` (Добавлен: FileRoutingService)
- `backend/apps/integrations/onec_exchange/views.py` (Изменён: интеграция роутинга)
- `backend/tests/unit/test_file_routing.py` (Добавлен: 29 unit тестов)
- `backend/tests/unit/conftest.py` (Добавлен: конфигурация для unit тестов)
- `backend/apps/cart/models.py` (Изменён: фикс CheckConstraint)
- `backend/tests/integration/test_1c_file_routing.py` (Добавлен: 6 интеграционных тестов)
- `backend/tests/integration/test_1c_file_upload.py` (Изменён: фикс регрессий)
- `backend/tests/unit/test_models/test_debug_cart.py` (Изменён: фикс регрессий)

## Лог изменений

- 2026-01-23: Story создана SM-агентом с комплексным контекстом для разработчика
- 2026-01-23: **[Party Mode Review]** Добавлены security КП (Zip Bomb, Path Traversal)
- 2026-01-23: **[Party Mode Decision]** Архитектурный рефакторинг: ZIP распаковка перенесена в Story 3.1
- 2026-01-23: **[Party Mode Decision]** Story переименована: "Сохранение файлов и маршрутизация"
- 2026-01-23: **[Party Mode Decision]** КП упрощены: XML/images маршрутизируются, ZIP остаётся в temp
- 2026-01-24: **[Dev Agent]** Реализация завершена: FileRoutingService, 29 тестов, интеграция с views.py
- 2026-01-24: **[Dev Agent]** Addressed code review findings - 2 items resolved (DeprecationWarning fix, files committed)
- 2026-01-24: **[Code Review]** Adversarial review completed - 4 action items created (1 High, 2 Medium, 1 Low). Status → in-progress
- 2026-01-24: **[Dev Agent]** Finalized Story 2.2 after Round 2 review. All tests passed. Status → review