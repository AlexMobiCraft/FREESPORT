# Story 4.3: View-обработчики mode=query и mode=success

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **1С система**,
I want **запрашивать заказы через mode=query и подтверждать получение через mode=success**,
So that **заказы передаются по стандартному протоколу обмена с гарантией доставки**.

## Acceptance Criteria

1. **AC1:** В `ICExchangeView` реализован метод `handle_query` для обработки `GET /?mode=query`.
2. **AC2:** `handle_query` возвращает XML с неотправленными заказами (sent_to_1c=False), используя `OrderExportService`.
3. **AC3:** Если передан параметр `zip=yes`, XML упаковывается в ZIP-архив (Content-Type: application/zip).
4. **AC4:** В `ICExchangeView` реализован метод `handle_success` для обработки `GET /?mode=success`.
5. **AC5:** `handle_success` помечает все выгруженные заказы как отправленные (`sent_to_1c=True`, `sent_to_1c_at=now()`).
6. **AC6:** Копии сгенерированных файлов (XML/ZIP) сохраняются в `MEDIA_ROOT/1c_exchange/logs/` для аудита.
7. **AC7:** Integration-тесты проверяют полный цикл: получение XML, получение ZIP, подтверждение успеха.
8. **AC8:** Реализация совместима с существующей аутентификацией `checkauth`.

## Tasks / Subtasks

- [x] Task 1: Подготовка инфраструктуры логирования (AC: 6)
  - [x] 1.1: Убедиться, что директория `MEDIA_ROOT/1c_exchange/logs/` существует (создавать динамически).
  - [x] 1.2: Создать хелпер `_save_exchange_log(filename, content, is_binary=False)` в `views.py` или утилитах.

- [x] Task 2: Реализация `handle_query` (AC: 1, 2, 3)
  - [x] 2.1: Добавить обработку `mode=query` в метод `get()` класса `ICExchangeView`.
  - [x] 2.2: В `handle_query`:
      - Зафиксировать текущее время `query_time`.
      - Сохранить `request.session['last_1c_query_time'] = query_time` (для Task 3).
      - Выбрать заказы `Order.objects.filter(sent_to_1c=False, created_at__lte=query_time)` с `prefetch_related`.
  - [x] 2.3: Вызвать `OrderExportService.generate_xml(orders)`.
  - [x] 2.4: Если заказов нет, вернуть пустой `CommmerceInfo` или корректный пустой ответ (проверить спецификацию, обычно пустой container).
  - [x] 2.5: Обработка `zip=yes`:
      - Создать in-memory zip (io.BytesIO).
      - Записать XML в архив как `orders.xml`.
      - Вернуть `HttpResponse` с content-type `application/zip` и заголовком `filename=orders.zip`.
  - [x] 2.6: Если `zip=no` (по умолчанию), вернуть XML (`application/xml`).
  - [x] 2.7: Сохранить копию ответа в лог (Task 1).

- [x] Task 3: Реализация `handle_success` (AC: 4, 5)
  - [x] 3.1: Добавить обработку `mode=success` в метод `get()` класса `ICExchangeView`.
  - [x] 3.2: В `handle_success`:
      - Использовать timestamp последнего `mode=query` (сохранённый в сессии пользователя в Task 2).
      - Обновить `sent_to_1c=True` только для заказов, где `sent_to_1c=False` И `created_at <= last_query_timestamp`.
      - Если timestamp в сессии нет (сессия истекла или прямой вызов), логировать warning и ничего не обновлять (или обновлять с осторожностью/возвращать ошибку).
      - **Цель:** Исключить Race Condition, когда новые заказы, пришедшие между query и success, помечаются как выгруженные.
  - [x] 3.3: Вернуть "success".

- [x] Task 4: Integration Tests (AC: 7, 8)
  - [x] 4.1: Тест `test_mode_query_returns_xml`: Создать заказ, вызвать `checkauth`, затем `query`, проверить XML.
  - [x] 4.2: Тест `test_mode_query_zip`: Передать `zip=yes`, проверить, что вернулся ZIP и внутри есть XML.
  - [x] 4.3: Тест `test_mode_success_updates_status`: Вызвать `success`, проверить, что `sent_to_1c=True`.
  - [x] 4.4: Тест `test_audit_logging`: Проверить, что файлы сохраняются в `media/1c_exchange/logs`.
  - [x] 4.5: Использовать `APIClient` и фикстуры.

### Review Follow-ups (AI)

- [x] [AI-Review][CRITICAL] Silent failure in handle_success: returns success but updates nothing if local session time missing. backend/apps/integrations/onec_exchange/views.py
- [x] [AI-Review][MEDIUM] Duplicate imports (transaction, zipfile, logging) inside methods. backend/apps/integrations/onec_exchange/views.py
- [x] [AI-Review][LOW] Hardcoded log path string '1c_exchange/logs'. backend/apps/integrations/onec_exchange/views.py
- [x] [AI-Review][CRITICAL] **Data Integrity Mismatch:** `handle_success` marks ALL orders in the query timeframe as `sent_to_1c`, ignoring `OrderExportService` validation logic. Orders skipped during XML generation (e.g., empty orders) are incorrectly marked as "Sent" in the database without being exported. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **State Integrity:** `handle_query` updates the session state (`last_1c_query_time`) *before* successful XML generation. If generation fails (500 Error), the session remains "dirty", potentially leading to desync if 1C retries or forces success. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][LOW] **Performance:** `handle_query` generates full XML into memory (`"".join()`) before response. While necessary for ZIP mode, this risks OOM on very large exports. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][CRITICAL] **Ошибка бизнес-логики:** `handle_query` фильтрует `user__isnull=False`, что некорректно отбрасывает гостевые B2C заказы. Это вызывает расхождение данных о выручке в 1С. `backend/apps/integrations/onec_exchange/views.py:540`
- [x] [AI-Review][CRITICAL] **Риск безопасности/конфиденциальности (PII):** Логи обмена (XML/ZIP), содержащие персональные данные клиентов, сохраняются в `MEDIA_ROOT/1c_exchange/logs/`, который доступен публично. Логи должны быть перенесены в приватную/защищенную директорию. `backend/apps/integrations/onec_exchange/views.py:30`
- [x] [AI-Review][MEDIUM] **Хрупкость кода:** Код предполагает существование `settings.ONEC_EXCHANGE`. Отсутствие конфигурации приведет к падению `handle_init` и `handle_file_upload`. Использовать `getattr` или разумные значения по умолчанию. `backend/apps/integrations/onec_exchange/views.py`


## Dev Notes

### КРИТИЧНО: Исправление XML-тегов (FR1.4)

> [!IMPORTANT]
> **Change Request (CommerceML 3.1):**
> Корневой тег должен быть `<КоммерческаяИнформация ВерсияСхемы="3.1">`.
> View должна ожидать, что Service вернет структуру 3.1 (с Контейнерами).
> Тесты `test_onec_export.py` должны быть обновлены для проверки версии 3.1.

Текущая заглушка в `views.py:517-521` использует **латинские** теги `<Commerceml version="2.10">`, что **нарушает FR1.4** и стандарт CommerceML 2.10. Корректный корневой тег — `<КоммерческаяИнформация ВерсияСхемы="2.10">` (кириллица). `OrderExportService` уже генерирует правильный XML. При реализации Task 2 заглушка **полностью заменяется** вызовом сервиса — проблема устраняется автоматически. Если по какой-то причине нужно оставить fallback для пустого ответа (нет заказов), использовать кириллические теги:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="3.1" ДатаФормирования="...">
</КоммерческаяИнформация>
```

### Архитектурные требования

- **Толстые сервисы, тонкие взгляды:** `ICExchangeView` должен только оркестрировать процесс. Логика генерации XML — в `OrderExportService`.
- **Логирование:** Обязательно сохранять исходящие файлы. Это единственный способ отладки проблем с 1С на проде.

### Files to Touch

- `backend/apps/integrations/onec_exchange/views.py`: Основная реализация.
- `backend/tests/integration/test_onec_export.py`: Новые тесты (создать файл).

### Dependencies

- **OrderExportService**: Должен быть реализован в Story 4.2. Если 4.2 еще не готова, можно реализовать заглушку или объединить работы, но формально 4.3 зависит от 4.2.
- **Модель Order**: Поля `sent_to_1c` (Story 4.1).

### Anti-patterns

- ❌ Не писать генерацию XML внутри view.
- ❌ Не использовать `print` для отладки — только `logger`.
- ❌ Не забывать про `transaction.atomic` при массовом обновлении статусов.

### References

- [Source: backend/apps/integrations/onec_exchange/views.py] - Текущая реализация View.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3] - Оригинальные требования.
- [Source: backend/apps/orders/services/order_export.py] - Сервис экспорта (ожидается).
- [Documentation: Протокол обмена с сайтом (Bitrix)](https://dev.1c-bitrix.ru/api_help/sale/algorithms/doc_from_site.php) - Описание команд exchange.php (checkauth, init, query, success).
- [Documentation: CommerceML 2 (1C)](https://v8.1c.ru/edi/edi_stnd/131/) - Стандарт формата XML для обмена данными.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- ✅ Resolved review finding [CRITICAL]: handle_success now returns failure (400) when no prior query timestamp exists in session, preventing silent data loss.
- ✅ Resolved review finding [MEDIUM]: Removed duplicate imports of `transaction`, `zipfile` from method bodies — they are already imported at module level.
- ✅ Resolved review finding [LOW]: Extracted hardcoded log path '1c_exchange/logs' into module constant `EXCHANGE_LOG_SUBDIR`.
- ✅ Resolved review finding [CRITICAL]: handle_success now marks ONLY orders actually exported by OrderExportService (via exported_ids list), not all orders in timeframe. Orders skipped by validation (e.g., no items) are no longer incorrectly marked as sent.
- ✅ Resolved review finding [MEDIUM]: Session state (query_time, exported_ids) is now set AFTER successful XML generation, preventing dirty session state on generation failure.
- ✅ Resolved review finding [LOW]: Performance concern noted. Streaming via `generate_xml_streaming` is available for future optimization; current `"".join()` approach is necessary for ZIP mode and acceptable for typical order volumes.
- ✅ Resolved review finding [CRITICAL]: Removed `user__isnull=False` filter from `handle_query` — guest B2C orders are now correctly exported to 1C. Added `test_mode_query_includes_guest_orders` test.
- ✅ Resolved review finding [CRITICAL]: Exchange audit logs moved from public `MEDIA_ROOT/1c_exchange/logs/` to private `BASE_DIR/var/1c_exchange/logs/` (configurable via `settings.EXCHANGE_LOG_DIR`). Added `_get_exchange_log_dir()` helper. Tests verify logs are NOT in MEDIA_ROOT.
- ✅ Resolved review finding [MEDIUM]: Replaced direct `settings.ONEC_EXCHANGE` access with `getattr(settings, "ONEC_EXCHANGE", {})` in `handle_init` and `handle_file_upload`. App no longer crashes when config is missing. Added `test_handle_init_without_onec_exchange_setting` test.
- Task 1: Реализован хелпер `_save_exchange_log()` с автосозданием директории, поддержкой текстовых и бинарных файлов, таймстемпом в имени файла.
- Task 2: Реализован `handle_query` — фиксирует `query_time` в сессии, фильтрует заказы по `sent_to_1c=False` и `created_at <= query_time`, генерирует XML через `OrderExportService`, поддерживает ZIP-сжатие (`zip=yes`), сохраняет аудит-копию.
- Task 3: Реализован `handle_success` — берёт `last_1c_query_time` из сессии, обновляет заказы через `transaction.atomic`, защита от race condition (без timestamp — не обновляет). Добавлен роутинг `mode=success` в `get()`.
- Task 4: 17 integration-тестов покрывающих все AC: логирование, XML/ZIP генерация, пустые ответы, фильтрация, race condition, data integrity, гостевые заказы, PII-защита логов, устойчивость к отсутствию конфигурации, полный цикл checkauth→query→success.

### Change Log

- 2026-01-31: Реализованы handle_query и handle_success для экспорта заказов в 1С. 13 тестов, все проходят.
- 2026-02-01: Review performed. 3 issues found (1 critical). Status reverted to in-progress.
- 2026-02-01: Addressed code review findings — 3 items resolved (1 CRITICAL, 1 MEDIUM, 1 LOW).
- 2026-02-01: Review performed (2nd iteration). 3 issues found (1 CRITICAL, 1 MEDIUM, 1 LOW). Status reverted to in-progress.
- 2026-02-01: Addressed 2nd code review findings — 3 items resolved (1 CRITICAL, 1 MEDIUM, 1 LOW). Added `generate_xml_with_ids()` to track exported orders. handle_success now uses exact PK list. Session state moved after XML generation. New test added.
- 2026-02-01: Addressed 3rd code review findings — 3 items resolved (2 CRITICAL, 1 MEDIUM). Removed user__isnull=False filter (guest orders), moved audit logs to private dir, added getattr for ONEC_EXCHANGE config. 3 new tests added (17 total).

### File List

- `backend/apps/integrations/onec_exchange/views.py` (modified) — добавлены `_save_exchange_log()`, `_get_exchange_log_dir()`, `handle_query()`, `handle_success()`, роутинг `mode=success`; убран `user__isnull=False` фильтр; логи перемещены в приватную директорию; `getattr` для `ONEC_EXCHANGE`
- `backend/apps/orders/services/order_export.py` (modified) — добавлен `generate_xml_with_ids()`, `generate_xml_streaming` принимает `exported_ids` параметр; обновлены docstrings (гостевые заказы поддерживаются)
- `backend/tests/integration/test_onec_export.py` (modified) — 17 integration-тестов для Story 4.3 (добавлены: guest orders, PII log protection, config resilience)
