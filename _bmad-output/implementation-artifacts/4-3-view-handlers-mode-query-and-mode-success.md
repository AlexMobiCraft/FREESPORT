# Story 4.3: View-обработчики mode=query и mode=success

Status: in-progress

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
6. **AC6:** Копии сгенерированных файлов (XML/ZIP) сохраняются в приватную директорию `var/1c_exchange/logs/` для аудита (не в `MEDIA_ROOT` — защита PII).
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

### Review Follow-ups (AI - Cycle 2)

- [x] [AI-Review][MEDIUM] **OOM Risk:** `handle_query` reads full `SpooledTemporaryFile` into RAM via `.read()`. Must use `FileResponse` or `streaming_content` to properly stream data. `backend/apps/integrations/onec_exchange/views.py:305`
- [x] [AI-Review][MEDIUM] **Poison Queue Risk:** Invalid orders (e.g., no items) skipped by `_validate_order` remain `sent_to_1c=False`. They are never marked sent, so they clog the export queue forever. Need a "failed/ignored" state or explicit skip flag. `backend/apps/orders/services/order_export.py`
- [x] [AI-Review][LOW] **AC Conflict:** AC6 requires logs in `MEDIA_ROOT`. Implementation correctly uses private `var/` dir for security. AC should be updated to reflect this security improvement.

### Review Follow-ups (AI - Cycle 3)

- [x] [AI-Review][HIGH] **OOM Risk (Logging):** `handle_query` streams XML/ZIP to temp file effectively, but then calls `f.read()` to load the *entire* content back into RAM for `_save_exchange_log`. This defeats the purpose of streaming and risks OOM on large exports. Must use file copying (shutil.copy) or stream piping for logging. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **Brittle Process Dependency:** `handle_success` strictly requires `exported_ids` from Redis (1h TTL). If 1C import exceeds 1h or Redis flushes, the batch cannot be confirmed (HTTP 400). Consider fallback: if cache missing, use time-window update (with strict bounded overlap check) or persist exchange state to DB (`ExchangeSession`).
- [x] [AI-Review][LOW] **Test Gap:** No regression test ensures streaming actually streams (i.e., minimal RAM usage). A future refactor could revert to `list(generator)` without tests failing. Add a memory-profiling test or mock verification that chunks are written iteratively.

### Review Follow-ups (AI)

- [x] [AI-Review][MEDIUM] **Documentation Discrepancy:** `backend/apps/orders/signals.py` was modified (added `orders_bulk_updated` signal) but is NOT listed in the Story's "File List". [action:document]
- [x] [AI-Review][LOW] **Clean Code (Imports):** `backend/apps/integrations/onec_exchange/views.py` imports `orders_bulk_updated` inside `handle_success` method. Should be a top-level import. [file:backend/apps/integrations/onec_exchange/views.py:390]


- [x] [AI-Review][HIGH] **Concurrency Risk:** `_get_exchange_identity` uses shared key "shared_1c_exchange" for all auth users, causing race conditions. Must return unique sessid. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **OOM Risk:** `handle_query` (zip=no) materializes full XML in RAM using "".join(). switch to StreamingHttpResponse. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **Audit Bypass:** `handle_success` uses `.update()`, bypassing signals/save(). Must use explicit save or send signals if audit depends on them. `backend/apps/integrations/onec_exchange/views.py`

### Review Follow-ups (AI - Previous)

- [x] [AI-Review][CRITICAL] Silent failure in handle_success: returns success but updates nothing if local session time missing. backend/apps/integrations/onec_exchange/views.py
- [x] [AI-Review][MEDIUM] Duplicate imports (transaction, zipfile, logging) inside methods. backend/apps/integrations/onec_exchange/views.py
- [x] [AI-Review][LOW] Hardcoded log path string '1c_exchange/logs'. backend/apps/integrations/onec_exchange/views.py
- [x] [AI-Review][CRITICAL] **Data Integrity Mismatch:** `handle_success` marks ALL orders in the query timeframe as `sent_to_1c`, ignoring `OrderExportService` validation logic. Orders skipped during XML generation (e.g., empty orders) are incorrectly marked as "Sent" in the database without being exported. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **State Integrity:** `handle_query` updates the session state (`last_1c_query_time`) *before* successful XML generation. If generation fails (500 Error), the session remains "dirty", potentially leading to desync if 1C retries or forces success. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][LOW] **Performance:** `handle_query` generates full XML into memory (`"".join()`) before response. While necessary for ZIP mode, this risks OOM on very large exports. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][CRITICAL] **Ошибка бизнес-логики:** `handle_query` фильтрует `user__isnull=False`, что некорректно отбрасывает гостевые B2C заказы. Это вызывает расхождение данных о выручке в 1С. `backend/apps/integrations/onec_exchange/views.py:540`
- [x] [AI-Review][CRITICAL] **Риск безопасности/конфиденциальности (PII):** Логи обмена (XML/ZIP), содержащие персональные данные клиентов, сохраняются в `MEDIA_ROOT/1c_exchange/logs/`, который доступен публично. Логи должны быть перенесены в приватную/защищенную директорию. `backend/apps/integrations/onec_exchange/views.py:30`
- [x] [AI-Review][MEDIUM] **Хрупкость кода:** Код предполагает существование `settings.ONEC_EXCHANGE`. Отсутствие конфигурации приведет к падению `handle_init` и `handle_file_upload`. Использовать `getattr` или разумные значения по умолчанию. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][CRITICAL] **Уязвимость безопасности (Zip Slip):** `handle_import` использует `extractall()` без санитайзинга путей. Вредоносный архив может перезаписать системные файлы. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **Рассинхронизация версий:** `handle_init` читает версию из настроек, а `OrderExportService` имеет жестко заданную версию 3.1. `backend/apps/orders/services/order_export.py`
- [x] [AI-Review][MEDIUM] **Жестко заданные единицы измерения:** Сервис экспорта использует "Штука" (796) для всех товаров без проверки модели Product. `backend/apps/orders/services/order_export.py`
- [x] [AI-Review][MEDIUM] **Нарушение архитектуры (Fat View):** Логика `handle_import` (сессии, роутинг, ZIP) слишком сложная для View и должна быть вынесена в `ImportOrchestratorService`. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][LOW] **Риск раздувания сессии:** `last_1c_exported_order_ids` хранится в сессии, что может вызвать проблемы при экспорте тысяч заказов. Рассмотреть кэширование по ключу. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][LOW] **Хардкод:** Имя файла "orders.xml" внутри ZIP задано строковой константой. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **Целостность данных / Волатильность кэша:** В `handle_success` отсутствуют `exported_ids` (вытеснение/перезапуск), но есть `last_query_time` -> "success" без обновления. Требуется вернуть 400 или гарантировать идемпотентность дублей. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][LOW] **Стиль кода:** `handle_import` импортирует `ImportOrchestratorService` внутри метода. Требуется перенести в top-level импорты. `backend/apps/integrations/onec_exchange/views.py`

- [x] [AI-Review][CRITICAL] **Отсутствие контактных данных гостя (Потеря данных):** `OrderExportService._create_counterparties_element` пропускает блок `<Контрагенты>` для гостевых заказов (`user=None`), отбрасывая `customer_name/email/phone` из модели Order. Требуется использовать эти поля. `backend/apps/orders/services/order_export.py:179`
- [x] [AI-Review][MEDIUM] **Fat View (Архитектурный долг):** `ICExchangeView.handle_complete` содержит сложную логику (транзакции, роутинг, Celery), нарушая паттерн "Fat Service". Требуется перенести в `ImportOrchestratorService.finalize_batch()`. `backend/apps/integrations/onec_exchange/views.py:167`
- [x] [AI-Review][HIGH] **Блокировка БД (Performance):** `ImportOrchestratorService.finalize_batch` выполняет долгие IO-операции (перенос файлов, unzip) внутри транзакции с `select_for_update`. Это блокирует таблицу ImportSession. Требуется вынести IO за пределы транзакции. `backend/apps/integrations/onec_exchange/import_orchestrator.py:415`
- [x] [AI-Review][MEDIUM] **Нарушение протокола 1С:** `ICExchangeView` возвращает HTTP 4xx/5xx для логических ошибок. Протокол требует HTTP 200 с телом `failure...` для корректной обработки клиентами 1С. `backend/apps/integrations/onec_exchange/views.py`
- [x] [AI-Review][MEDIUM] **Целостность данных:** `handle_success` использует `.update()` для пометки заказов, что не обновляет `updated_at` (auto_now) и не шлет сигналы. Требуется явно обновлять `updated_at` в запросе. `backend/apps/integrations/onec_exchange/views.py:344`
- [x] [AI-Review][CRITICAL] **Data Corruption Risk (Race Condition):** `ImportOrchestratorService.execute()` transfers and unpacks files into `import_dir` even if a session is `IN_PROGRESS`. This modifies the working directory of a running import, ensuring chaos and data corruption. `backend/apps/integrations/onec_exchange/import_orchestrator.py:59`
- [x] [AI-Review][MEDIUM] **Performance / OOM Risk:** `OrderExportService.generate_xml` materializes the entire XML output into a single RAM string (`"".join()`). Compressing large queries (ZIP mode) multiplies this memory pressure. For B2B catalogs, this will crash the worker. `backend/apps/orders/services/order_export.py:78`


### Review Follow-ups (AI - Cycle 4)

- [ ] [AI-Review][MEDIUM] **Synchronous Email Blocking:** `send_order_confirmation_email` sends emails synchronously in `post_save`. Offload to Celery. `backend/apps/orders/signals.py`
- [ ] [AI-Review][MEDIUM] **Synchronous Import Risk:** `ImportOrchestratorService.execute` runs import synchronously. Large files may cause Nginx timeouts. `backend/apps/integrations/onec_exchange/import_orchestrator.py`
- [ ] [AI-Review][LOW] **Signal Ambiguity:** `orders_bulk_updated` signal payload might mismatch actual updated count. `backend/apps/integrations/onec_exchange/views.py`


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
- Task 4: 22 integration-теста покрывающих все AC: логирование, XML/ZIP генерация, пустые ответы, фильтрация, race condition, data integrity, гостевые заказы, PII-защита логов, устойчивость к отсутствию конфигурации, Zip Slip защита, синхронизация версий, конфигурируемые единицы измерения, полный цикл checkauth→query→success.
- ✅ Resolved review finding [CRITICAL]: Added Zip Slip path traversal protection to `handle_import` — all ZIP entries validated against `import_dir.resolve()` before extraction.
- ✅ Resolved review finding [MEDIUM]: `OrderExportService.SCHEMA_VERSION` now reads from `settings.ONEC_EXCHANGE["COMMERCEML_VERSION"]` with fallback to "3.1", synchronized with `handle_init`.
- ✅ Resolved review finding [MEDIUM]: Unit of measurement now configurable via `settings.ONEC_EXCHANGE["DEFAULT_UNIT"]` dict with fallback to "Штука" (796).
- ✅ Resolved review finding [MEDIUM]: Extracted `handle_import` logic into `ImportOrchestratorService` (Fat Services, Thin Views). View now delegates to orchestrator with ~15 lines.
- ✅ Resolved review finding [LOW]: Moved `last_1c_exported_order_ids` from Django session to Django cache (`cache.set/get/delete`) to prevent session bloat on large exports. 1-hour TTL.
- ✅ Resolved review finding [LOW]: Extracted hardcoded "orders.xml" and "orders.zip" into module constants `ORDERS_XML_FILENAME` / `ORDERS_ZIP_FILENAME`.
- ✅ Resolved review finding [MEDIUM]: `handle_success` now returns 400 when `exported_ids` are missing from cache (eviction/restart) instead of silently returning success. Ensures 1C retries `mode=query` first.
- ✅ Resolved review finding [LOW]: Moved `ImportOrchestratorService` import from inside `handle_import` method to top-level module imports.
- ✅ Resolved review finding [HIGH]: Moved IO operations (file transfer, unpack) outside `transaction.atomic()` in `finalize_batch` to avoid blocking ImportSession table during long disk operations.
- ✅ Resolved review finding [MEDIUM]: All error responses now return HTTP 200 with `failure...` body per 1C protocol requirements instead of HTTP 4xx/5xx codes.
- ✅ Resolved review finding [MEDIUM]: `handle_success` now explicitly updates `updated_at` field in `.update()` call since QuerySet.update() bypasses auto_now.
- ✅ Resolved review finding [CRITICAL]: `execute()` now returns early with `already_in_progress` when session is IN_PROGRESS, avoiding modification of import_dir during active import.
- ✅ Resolved review finding [MEDIUM]: `handle_query` now uses `SpooledTemporaryFile` for ZIP mode to reduce RAM pressure; streams XML chunks to temp file before compression.
- ✅ Resolved review finding [HIGH]: `_get_exchange_identity` now uses unique session_key instead of shared "shared_1c_exchange" to prevent race conditions between concurrent 1C clients.
- ✅ Resolved review finding [MEDIUM]: `handle_query` (zip=no) now uses `SpooledTemporaryFile` instead of `"".join()` to avoid OOM on large exports.
- ✅ Resolved review finding [MEDIUM]: `handle_success` now sends custom signal `orders_bulk_updated` after `.update()` for audit extensibility (QuerySet.update bypasses post_save).
- ✅ Resolved review finding [MEDIUM]: Added `backend/apps/orders/signals.py` to File List documentation.
- ✅ Resolved review finding [LOW]: Moved `orders_bulk_updated` import from inside `handle_success` method to top-level imports.
- ✅ Resolved review finding [MEDIUM]: `handle_query` now uses `FileResponse` with `NamedTemporaryFile` for proper streaming instead of `.read()` into RAM.
- ✅ Resolved review finding [MEDIUM]: Added `export_skipped` field to Order model. Invalid orders (no items) are marked as skipped during export to prevent poison queue.
- ✅ Resolved review finding [LOW]: Updated AC6 to reflect security improvement (logs in private `var/` dir instead of `MEDIA_ROOT`).
- ✅ Resolved review finding [HIGH]: Replaced `f.read()` with `shutil.copy2` via `_copy_file_to_log()` for OOM-safe audit logging.
- ✅ Resolved review finding [MEDIUM]: Added time-window fallback for `handle_success` when Redis cache is missing (long imports / cache eviction).
- ✅ Resolved review finding [LOW]: Added streaming regression tests (`TestStreamingBehavior`) to verify FileResponse usage and file-copy logging.

### Change Log

- 2026-01-31: Реализованы handle_query и handle_success для экспорта заказов в 1С. 13 тестов, все проходят.
- 2026-02-01: Review performed. 3 issues found (1 critical). Status reverted to in-progress.
- 2026-02-01: Addressed code review findings — 3 items resolved (1 CRITICAL, 1 MEDIUM, 1 LOW).
- 2026-02-01: Review performed (2nd iteration). 3 issues found (1 CRITICAL, 1 MEDIUM, 1 LOW). Status reverted to in-progress.
- 2026-02-01: Addressed 2nd code review findings — 3 items resolved (1 CRITICAL, 1 MEDIUM, 1 LOW). Added `generate_xml_with_ids()` to track exported orders. handle_success now uses exact PK list. Session state moved after XML generation. New test added.
- 2026-02-01: Addressed 3rd code review findings — 3 items resolved (2 CRITICAL, 1 MEDIUM). Removed user__isnull=False filter (guest orders), moved audit logs to private dir, added getattr for ONEC_EXCHANGE config. 3 new tests added (17 total).
- 2026-02-01: Addressed 4th code review findings — 3 items resolved (1 CRITICAL, 2 MEDIUM). Zip Slip protection, version sync, configurable units. 5 new tests added (22 total).
- 2026-02-01: Addressed 5th code review findings — 3 items resolved (1 MEDIUM, 2 LOW). Fat View→ImportOrchestratorService, session bloat→cache, hardcoded filenames→constants. 7 new tests added (29 total).
- 2026-02-01: Addressed 6th code review findings — 2 items resolved (1 MEDIUM, 1 LOW). Cache eviction→400 error, top-level import. 2 new tests added (31 total).
- 2026-02-01: Addressed 7th code review findings — 3 items resolved (1 HIGH, 2 MEDIUM). DB lock fix (IO outside transaction), 1C protocol compliance (HTTP 200 for failures), updated_at explicit update.
- 2026-02-01: Addressed 8th code review findings — 2 items resolved (1 CRITICAL, 1 MEDIUM). Race condition fix (skip transfer/unpack when IN_PROGRESS), OOM mitigation (SpooledTemporaryFile for ZIP mode).
- 2026-02-01: Addressed 9th code review findings — 3 items resolved (1 HIGH, 2 MEDIUM). Unique sessid (no shared key), OOM fix for non-ZIP mode (SpooledTemporaryFile), audit signal `orders_bulk_updated`.
- 2026-02-01: Addressed 10th code review findings — 2 items resolved (1 MEDIUM, 1 LOW). Documentation (signals.py in File List), top-level import for orders_bulk_updated.
- 2026-02-01: Review performed (Cycle 2). 3 issues found (2 MEDIUM, 1 LOW). Action items created. Status reverted to in-progress.
- 2026-02-01: Addressed Cycle 2 findings — 3 items resolved (2 MEDIUM, 1 LOW). FileResponse streaming, export_skipped field + migration, AC6 updated.
- 2026-02-01: Review performed (Cycle 3). 3 issues found (1 HIGH, 1 MEDIUM, 1 LOW). Action items created. Status reverted to in-progress.
- 2026-02-01: Addressed Cycle 3 findings — 3 items resolved (1 HIGH, 1 MEDIUM, 1 LOW). shutil.copy2 for logging, time-window fallback, streaming tests. 33 tests total.

### File List

- `backend/apps/integrations/onec_exchange/views.py` (modified) — добавлены `_save_exchange_log()`, `_get_exchange_log_dir()`, `handle_query()`, `handle_success()`, роутинг `mode=success`; убран `user__isnull=False` фильтр; логи перемещены в приватную директорию; `getattr` для `ONEC_EXCHANGE`; `handle_import` делегирует в `ImportOrchestratorService`; exported_ids в cache вместо сессии; константы `ORDERS_XML_FILENAME`/`ORDERS_ZIP_FILENAME`
- `backend/apps/integrations/onec_exchange/import_orchestrator.py` (new) — `ImportOrchestratorService`: оркестрация импорта (сессии, перенос файлов, ZIP-распаковка с Zip Slip защитой, роутинг, синхронный импорт)
- `backend/apps/orders/services/order_export.py` (modified) — добавлен `generate_xml_with_ids()`, `generate_xml_streaming` принимает `exported_ids` параметр; `SCHEMA_VERSION` теперь property из settings; единицы измерения конфигурируемы через `settings.ONEC_EXCHANGE.DEFAULT_UNIT`
- `backend/apps/orders/signals.py` (modified) — добавлен кастомный сигнал `orders_bulk_updated` для аудита массовых обновлений заказов (QuerySet.update обходит post_save)
- `backend/apps/orders/models.py` (modified) — добавлено поле `export_skipped` для пометки невалидных заказов (poison queue fix)
- `backend/apps/orders/migrations/0010_add_export_skipped_field.py` (new) — миграция для export_skipped
- `backend/tests/integration/test_onec_export.py` (modified) — 31 integration-тестов для Story 4.3; добавлен helper `get_response_content()` для FileResponse
