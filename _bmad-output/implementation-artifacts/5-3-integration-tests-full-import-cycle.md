# Story 5.3: Интеграционные тесты полного цикла импорта статусов

Status: ready-for-dev

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

- [ ] Task 1: Создать интеграционный тест полного цикла импорта (AC: 1-6)
  - [ ] 1.1: Новый файл тестов в `backend/tests/integration/` (например, `test_order_exchange_import_e2e.py`).
  - [ ] 1.2: Использовать `perform_1c_checkauth()` из `backend/tests/utils.py` для получения сессии 1С.
  - [ ] 1.3: Создавать данные через Factory Boy (`OrderFactory`, `OrderItemFactory`, `ProductVariantFactory`) + `get_unique_suffix()`.

- [ ] Task 2: Подготовить XML-генератор для orders.xml (AC: 1-3)
  - [ ] 2.1: Переиспользовать существующий helper `_build_orders_xml()` из `backend/tests/integration/test_orders_xml_mode_file.py` (импортировать или вынести в `backend/tests/utils.py`). **Не создавать дубликат.**
  - [ ] 2.2: В XML указывать `<Номер>` и `<Ид>` формата `order-{id}`.

- [ ] Task 3: Реализовать тесты полного цикла (AC: 1-4)
  - [ ] 3.1: `test_full_cycle_export_then_import_updates_status` — полный цикл: `perform_1c_checkauth()` → `mode=query` → `mode=success` (экспорт, заказ становится `sent_to_1c=True`) → `mode=file` с orders.xml (импорт, Отгружен → shipped).
  - [ ] 3.2: Параметризованный тест для 4 статусов маппинга (processing/shipped/delivered/cancelled).
  - [ ] 3.3: `test_dates_extracted_from_requisites` — проверка `paid_at` и `shipped_at`.
  - [ ] 3.4: `test_invalid_xml_returns_failure` — невалидный XML → `failure`.
  - [ ] 3.5: `test_unknown_order_returns_failure` — неизвестный заказ → `failure` и отсутствие обновлений.

- [ ] Task 4: Обеспечить изоляцию логов и среду тестов (AC: 5)
  - [ ] 4.1: Фикстура `log_dir` с `settings.EXCHANGE_LOG_DIR` и `tmp_path` (как в test_onec_export/test_orders_xml_mode_file).
  - [ ] 4.2: Проверить, что тесты не пишут в `MEDIA_ROOT`.

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

- N/A

### Completion Notes List

- N/A

### File List

- `backend/tests/integration/test_order_exchange_import_e2e.py` (new)
