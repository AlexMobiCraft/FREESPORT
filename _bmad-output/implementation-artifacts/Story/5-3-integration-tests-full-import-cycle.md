# Story 5.3: Интеграционные тесты полного цикла импорта статусов

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **команда разработки**,
I want **E2E тесты полного цикла: экспорт заказа → симуляция ответа 1С → импорт статуса**,
so that **двусторонний обмен заказами с 1С работает корректно от начала до конца**.

## Acceptance Criteria

1. **AC1:** После экспорта заказа и подтверждения `mode=success` (заказ становится `sent_to_1c=True`) входящий orders.xml со статусом «Отгружен» обновляет статус заказа на `shipped`, а `status_1c` сохраняет «Отгружен».
2. **AC2:** Тест покрывает маппинг статусов для **4** значений: `processing`, `shipped`, `delivered`, `cancelled`.
3. **AC3:** Проверяется извлечение дат оплаты и отгрузки из `<ЗначениеРеквизита>` и сохранение в `paid_at` / `shipped_at`.
4. **AC4:** Проверяется обработка невалидного XML (ошибка парсинга) и случай неизвестного заказа.
5. **AC5:** Тесты используют Factory Boy + `get_unique_suffix()` и маркеры `@pytest.mark.integration`, `@pytest.mark.django_db`.
6. **AC6:** AAA-паттерн (Arrange/Act/Assert) соблюдён во всех тестах.

## Tasks / Subtasks

- [x] Task 1: Создать интеграционный тест полного цикла импорта (AC: 1-6)
  - [x] 1.1: Новый файл тестов в `backend/tests/integration/` (например, `test_order_exchange_import_e2e.py`).
  - [x] 1.2: Использовать `perform_1c_checkauth()` из `backend/tests/utils.py` для получения сессии 1С.
  - [x] 1.3: Создавать данные через Factory Boy (`OrderFactory`, `OrderItemFactory`, `ProductVariantFactory`) + `get_unique_suffix()`.

- [x] Task 2: Подготовить XML-генератор для orders.xml (AC: 1-3)
  - [x] 2.1: Переиспользовать существующий helper `_build_orders_xml()` из `backend/tests/integration/test_orders_xml_mode_file.py` (импортировать или вынести в `backend/tests/utils.py`). **Не создавать дубликат.**
  - [x] 2.2: В XML указывать `<Номер>` и `<Ид>` формата `order-{id}`.

- [x] Task 3: Реализовать тесты полного цикла (AC: 1-4)
  - [x] 3.1: `test_full_cycle_export_then_import_updates_status` — полный цикл: `perform_1c_checkauth()` → `mode=query` → `mode=success` (экспорт, заказ становится `sent_to_1c=True`) → `mode=file` с orders.xml (импорт, Отгружен → shipped).
  - [x] 3.2: Параметризованный тест для 4 статусов маппинга (processing/shipped/delivered/cancelled).
  - [x] 3.3: `test_dates_extracted_from_requisites` — проверка `paid_at` и `shipped_at`.
  - [x] 3.4: `test_invalid_xml_returns_failure` — невалидный XML → `failure`.
  - [x] 3.5: `test_unknown_order_returns_failure` — неизвестный заказ → `failure` и отсутствие обновлений.

- [x] Task 4: Обеспечить изоляцию логов и среду тестов (AC: 5)
  - [x] 4.1: Фикстура `log_dir` с `settings.EXCHANGE_LOG_DIR` и `tmp_path` (как в test_onec_export/test_orders_xml_mode_file).
  - [x] 4.2: Проверить, что тесты не пишут в `MEDIA_ROOT`.

- [x] Task 5: Review Follow-ups (AI)
  - [x] [AI-Review][High] Исправить падение теста `test_dates_extracted_from_requisites` из-за некорректной обработки часовых поясов (UTC vs Moscow) [backend/tests/integration/test_order_exchange_import_e2e.py:176]
  - [x] [AI-Review][Medium] Улучшить работу с timezone в тестах: использовать явное указание таймзоны (settings.TIME_ZONE) вместо неявных конвертаций [backend/tests/integration/test_order_exchange_import_e2e.py]

- [x] Task 6: Review Follow-ups (AI) - Round 2
  - [x] [AI-Review][Medium] Рефакторинг дублирования настройки тестов: вынести создание заказа в фикстуру или хелпер в `backend/tests/integration/test_order_exchange_import_e2e.py`
  - [x] [AI-Review][Medium] Усилить `test_full_cycle_export_then_import_updates_status`: проверять, что экспортированный XML действительно содержит целевой заказ
  - [x] [AI-Review][Low] Удалить избыточную инициализацию `order_number` в тестах, где она сразу перезаписывается через `_align_order_number_with_id`

- [x] Task 7: Review Follow-ups (AI) - Round 3
  - [x] [AI-Review][Medium] Рефакторинг тестовых хелперов: Переместить `_build_orders_xml` в `backend/tests/utils.py`, чтобы избежать импорта из соседних тест-файлов в `backend/tests/integration/test_order_exchange_import_e2e.py`

- [x] Task 8: Review Follow-ups (AI) - Round 4
  - [x] [AI-Review][Medium] Завершить рефакторинг: Удалить дублирование `_build_multi_orders_xml` в `backend/tests/integration/test_orders_xml_mode_file.py` и использовать централизованный хелпер
  - [x] [AI-Review][Low] Исправить жестко заданную дату в `backend/tests/utils.py:175` - использовать динамическую дату вместо `2026-02-02`
  - [x] [AI-Review][Low] Централизовать константу `EXCHANGE_URL` в `backend/tests/utils.py` для избежания дублирования в тестовых файлах

- [x] Task 9: Review Follow-ups (AI) - Round 5
  - [x] [AI-Review][Medium] Рефакторинг `backend/tests/integration/test_orders_xml_mode_file.py`: Заменить локальный `_authenticate` на `perform_1c_checkauth` из `tests.utils`
  - [x] [AI-Review][Medium] Рефакторинг `backend/tests/integration/test_orders_xml_mode_file.py`: Использовать `UserFactory` вместо `User.objects.create_user` для унификации
  - [x] [AI-Review][Medium] Рефакторинг `backend/tests/integration/test_orders_xml_mode_file.py`: Заменить хрупкий патчинг `__import__` в `test_rate_limiting_returns_429` на стандартный путь
  - [x] [AI-Review][Low] Очистка: Удалить неиспользуемый импорт `STATUS_PRIORITY` из `backend/tests/integration/test_orders_xml_mode_file.py`
  - [x] [AI-Review][Low] Очистка: Добавить аннотации типов в хелперы `backend/tests/integration/test_order_exchange_import_e2e.py`
  - [x] [AI-Review][Low] Очистка: Унифицировать пароль 1С пользователя в тестах (использовать константу)

- [x] Task 10: Review Follow-ups (AI) - Round 6
  - [x] [AI-Review][Medium] Заменить захардкоженную дату `2026-02-02` на динамическую в `test_windows_1251_encoding` [backend/tests/integration/test_orders_xml_mode_file.py:284]
  - [x] [AI-Review][Low] Оптимизировать очистку кэша в тесте лимитов — использовать более точечный подход вместо `cache.clear()` [backend/tests/integration/test_orders_xml_mode_file.py]
  - [x] [AI-Review][Low] Рефакторинг `test_multi_orders_in_single_xml`: использовать данные фабрик вместо ручного создания словарей [backend/tests/integration/test_orders_xml_mode_file.py]

## Dev Notes

### Контекст интеграции и поведения API

- Полный flow 1С: `checkauth → query → success → file` (orders.xml обрабатывается inline в `mode=file`).
- `ICExchangeView._handle_orders_xml()` возвращает `success` при `updated > 0` **или** отсутствии ошибок, иначе — `failure`.
- При одном «неизвестном заказе» будет `failure`, т.к. `updated=0` и есть ошибки в `ImportResult`.
- Невалидный XML обрабатывается как `failure\nMalformed XML`.

### Сервисы и ожидаемое поведение

- `OrderExportService` формирует CommerceML 3.1 с `<Контейнер><Документ>` и ID заказа `order-{id}`.
- `OrderStatusImportService` ищет заказ по `<Номер>` или `<Ид>`, применяет маппинг статусов и обновляет `sent_to_1c`/`sent_to_1c_at`.

### Существующие тесты для референса (не дублировать)

- Экспорт: `backend/tests/integration/test_onec_export.py`, `test_onec_export_e2e.py`.
- Импорт mode=file: `backend/tests/integration/test_orders_xml_mode_file.py`.
- DB-интеграция сервиса: `backend/tests/integration/test_order_status_import_db.py`.

### Testing Standards

- Интеграционные тесты: `@pytest.mark.integration`, `@pytest.mark.django_db`.
- Структура AAA и фабрики через Factory Boy (`tests/conftest.py`).

### Project Structure Notes

- Новые тесты размещать в `backend/tests/integration/` рядом с остальными интеграционными тестами.
- Использовать утилиты `backend/tests/utils.py` (checkauth, parse_commerceml_response).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#233-248]
- [Source: backend/apps/integrations/onec_exchange/views.py#590-744]
- [Source: backend/apps/orders/services/order_status_import.py#624-760]
- [Source: backend/apps/orders/services/order_export.py#80-126]
- [Source: backend/tests/integration/test_onec_export.py#415-449]
- [Source: backend/tests/integration/test_onec_export_e2e.py#59-239]
- [Source: backend/tests/integration/test_orders_xml_mode_file.py#123-214]
- [Source: backend/tests/utils.py#54-122]
- [Source: docs/architecture/10-testing-strategy.md#123-129]
- [Source: _bmad-output/planning-artifacts/architecture.md#156-159]
- [Source: project-context.md#9-18]

## Dev Agent Record

### Agent Model Used

Cascade (OpenAI)

### Debug Log References

- `docker compose -f docker/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend` (полный прогон): 64 failed, 1591 passed, 3 skipped.
- `docker compose -f docker/docker-compose.test.yml run --rm backend pytest -v -m integration --cov=apps --cov-report=term-missing` (интеграционные тесты): exit code 0.
- `docker compose -f docker/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend` (полный прогон): 65 failed, 1590 passed, 3 skipped, exit code 1 (см. тесты `tests/unit/test_file_routing.py`).

### Completion Notes List

- ✅ Исправлена проблема часовых поясов в `test_dates_extracted_from_requisites`: используем `timezone.localdate()` вместо naive `.date()`
- ✅ Добавлен импорт `django.utils.timezone` для явной работы с таймзонами
- ✅ Все 8 интеграционных тестов проходят (pytest tests/integration/test_order_exchange_import_e2e.py -v)
- Полный прогон тестов завершился с падениями вне текущей истории (см. Debug Log).
- `test_order_exchange_import_e2e.py` прошёл в общем прогоне (в логах около 83%).
- Изоляция логов: фикстура `log_dir` использует `settings.EXCHANGE_LOG_DIR` + `tmp_path`, тесты не пишут в `MEDIA_ROOT`.
- ✅ Рефакторинг тестов: вынесено создание заказа в `_create_order_with_item`, добавлена проверка экспортированного XML, убрана лишняя инициализация `order_number`.
- ✅ Интеграционные тесты (docker compose run ... -m integration) проходят.
- ✅ Task 6 (Round 2 review follow-ups): Подтверждено — все 3 подзадачи уже реализованы в предыдущей сессии. 8/8 тестов PASSED (2026-02-10). Story → review.
- ✅ Task 7: `_build_orders_xml` перемещена в `backend/tests/utils.py` как `build_orders_xml`. Оба тест-файла используют импорт из `tests.utils` с алиасом `_build_orders_xml`. 29/29 тестов PASSED (2026-02-10).
- ✅ Linting: Flake8 и MyPy успешно прошли для 3 изменённых файлов (0 issues).
- 🔄 Task 8: Созданы задачи для исправления оставшихся проблем код-ревью (3 пункта).
- ✅ Task 8: `_build_multi_orders_xml` перемещена в `tests/utils.py` как `build_multi_orders_xml`. Жёсткая дата `2026-02-02` заменена на динамическую (`order_date` параметр). `EXCHANGE_URL` централизована в `tests/utils.py`. 29/29 тестов PASSED (2026-02-10). Story → review.
- ✅ Task 9 (Round 5 review follow-ups): Рефакторинг `test_orders_xml_mode_file.py` — заменён `_authenticate` на `perform_1c_checkauth`, `User.objects.create_user` на `UserFactory`, хрупкий `__import__` на прямой импорт `OneCExchangeThrottle`, удалён неиспользуемый `STATUS_PRIORITY`. Добавлены аннотации типов в хелперы `test_order_exchange_import_e2e.py`. `ONEC_PASSWORD` централизован в `tests/utils.py`. 425/425 интеграционных тестов PASSED (2026-02-10). Story → review.
- ✅ Task 10 (Round 6 review follow-ups): Заменена захардкоженная дата `2026-02-02` на динамическую `timezone.now()` в `test_windows_1251_encoding`. Оптимизирована очистка кэша: точечное удаление throttle-ключа `throttle_1c_exchange_{user.pk}` вместо `cache.clear()`. Рефакторинг `test_multiple_orders_in_single_xml`: `OrderFactory.create()` вместо `Order.objects.create()`, данные-driven подход с zip. 21/21 + 8/8 тестов PASSED, 425/425 интеграционных тестов PASSED (2026-02-10). Story → review.

### File List

- `backend/tests/utils.py` (modified — добавлены `build_multi_orders_xml`, `EXCHANGE_URL`, `ONEC_PASSWORD`, параметр `order_date` в `build_orders_xml`)
- `backend/tests/integration/test_order_exchange_import_e2e.py` (modified — импорт `ONEC_PASSWORD`/`EXCHANGE_URL` из `tests.utils`, аннотации типов в хелперах, импорт `Order`)
- `backend/tests/integration/test_orders_xml_mode_file.py` (modified — `UserFactory`+`perform_1c_checkauth` вместо ручной auth, удалён `_authenticate`, прямой импорт `OneCExchangeThrottle`, удалён `STATUS_PRIORITY`, динамическая дата в `test_windows_1251_encoding`, точечная очистка кэша throttle, `OrderFactory` в `test_multiple_orders_in_single_xml`)
- `backend/tests/integration/test_onec_export_e2e.py` (modified — импорт `ONEC_PASSWORD` из `tests.utils`)
