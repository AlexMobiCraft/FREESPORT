# Story 5.2: View-обработчик mode=file для orders.xml

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **1С система**,
I want **отправлять файл orders.xml с обновлёнными статусами через mode=file**,
So that **статусы заказов на сайте обновляются автоматически при обработке в 1С**.

## Acceptance Criteria

1. **AC1:** При POST `?type=sale&mode=file&filename=orders.xml` файл распознаётся как orders.xml (по filename) и маршрутизируется в `OrderStatusImportService` (FR2.1).
2. **AC2:** 1С аутентифицирована через существующий mode=checkauth (NFR3) — используется `Basic1CAuthentication` + `CsrfExemptSessionAuthentication`.
3. **AC3:** Ответ: `success` при успешной обработке, `failure\n<причина>` при ошибке.
4. **AC4:** Обработка идемпотентна — повторная отправка того же файла не ломает данные (гарантируется `OrderStatusImportService`).
5. **AC5:** Копия файла сохраняется в `MEDIA_ROOT/1c_exchange/logs/` для отладки (NFR4).
6. **AC6:** Возвращается `ImportResult` с метриками: `processed`, `updated`, `skipped`, `not_found`, `errors`.
7. **AC7:** Integration-тесты: POST с XML обновляет статус заказа в БД, повторная отправка не создаёт ошибок.

## Tasks / Subtasks

- [ ] Task 1: Модификация handle_file_upload для orders.xml (AC: 1, 3, 5)
  - [ ] 1.1: В `backend/apps/integrations/onec_exchange/views.py` добавить проверку `filename.lower() == "orders.xml"` в `handle_file_upload()`.
  - [ ] 1.2: При совпадении — читать тело запроса в память (orders.xml обычно <1MB) вместо стриминга в файл.
  - [ ] 1.3: Вызвать `OrderStatusImportService().process(xml_data)` с полученным XML.
  - [ ] 1.4: Сохранить копию XML через `_save_exchange_log("orders.xml", xml_data)` (NFR4).
  - [ ] 1.5: Вернуть `success` при `result.errors == []`, иначе `failure\n{summary}`.

- [ ] Task 2: Добавить маршрутизацию в routing_service (AC: 1)
  - [ ] 2.1: Добавить `"orders": "orders/"` в `XML_ROUTING_RULES` (для consistency, хотя orders.xml обрабатывается inline).
  - [ ] 2.2: Документировать специальную обработку orders.xml в docstring.

- [ ] Task 3: Добавить импорт OrderStatusImportService (AC: 1)
  - [ ] 3.1: Добавить `from apps.orders.services.order_status_import import OrderStatusImportService` в views.py.

- [ ] Task 4: Integration-тесты (AC: 7)
  - [ ] 4.1: Создать `backend/tests/integration/test_orders_xml_mode_file.py`.
  - [ ] 4.2: `test_mode_file_orders_xml_updates_order_status` — POST с валидным orders.xml обновляет Order.status.
  - [ ] 4.3: `test_mode_file_orders_xml_idempotent` — повторная отправка не создаёт ошибок.
  - [ ] 4.4: `test_mode_file_orders_xml_saves_audit_log` — проверить что файл сохранён в logs.
  - [ ] 4.5: `test_mode_file_orders_xml_returns_failure_on_invalid_xml` — невалидный XML → failure.
  - [ ] 4.6: `test_mode_file_orders_xml_requires_auth` — без аутентификации → 401/403.
  - [ ] 4.7: Использовать Factory Boy с `get_unique_suffix()`, маркеры `@pytest.mark.integration`, `@pytest.mark.django_db`, AAA-паттерн.

- [ ] Task 5: Обработка ошибок и логирование (AC: 3, 6)
  - [ ] 5.1: При `ImportResult.errors` — логировать `logger.warning()` с деталями.
  - [ ] 5.2: Формировать summary: `"processed={n}, updated={m}, errors={k}"`.
  - [ ] 5.3: При исключении в `OrderStatusImportService` — `logger.exception()`, вернуть `failure\nInternal error`.

## Dev Notes

### Архитектурные требования

**Fat Services, Thin Views (docs/architecture-backend.md):**
- View только читает XML из request body и передаёт в сервис
- Вся бизнес-логика уже в `OrderStatusImportService` (Story 5.1)
- View возвращает plain text ответ согласно протоколу 1С

**Существующий код для референса:**
- `backend/apps/integrations/onec_exchange/views.py:496-545` — `handle_file_upload()`
- `backend/apps/integrations/onec_exchange/views.py:29` — `ORDERS_XML_FILENAME = "orders.xml"`
- `backend/apps/integrations/onec_exchange/views.py:46-58` — `_save_exchange_log()`

### Паттерн обработки orders.xml

```python
# В handle_file_upload(), перед стримингом в файл:
if filename.lower() == ORDERS_XML_FILENAME:
    return self._handle_orders_xml(request)

def _handle_orders_xml(self, request) -> HttpResponse:
    """
    Handle orders.xml import synchronously.

    Unlike catalog files (streamed to disk), orders.xml is processed
    inline because:
    1. It's typically small (<1MB)
    2. 1C expects immediate status response
    3. No need for mode=import follow-up
    """
    try:
        # Read full body (orders.xml is small)
        xml_data = request._request.read()

        # Audit log
        _save_exchange_log(ORDERS_XML_FILENAME, xml_data, is_binary=True)

        # Process via service
        from apps.orders.services.order_status_import import OrderStatusImportService
        service = OrderStatusImportService()
        result = service.process(xml_data)

        # Log metrics
        logger.info(
            f"[ORDERS IMPORT] processed={result.processed}, "
            f"updated={result.updated}, skipped={result.skipped}, "
            f"not_found={result.not_found}, errors={len(result.errors)}"
        )

        if result.errors:
            logger.warning(f"[ORDERS IMPORT] Errors: {result.errors[:5]}")
            # Still return success if some orders were processed
            # Only fail on complete failure

        return HttpResponse("success", content_type="text/plain; charset=utf-8")

    except Exception as e:
        logger.exception(f"[ORDERS IMPORT] Failed: {e}")
        return HttpResponse(
            f"failure\nInternal error",
            content_type="text/plain; charset=utf-8",
        )
```

### XML структура orders.xml (референс из Story 5.1)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="3.1" ДатаФормирования="2026-02-04T12:00:00">
  <Контейнер>
    <Документ>
      <Ид>order-123</Ид>
      <Номер>FS-20260204-001</Номер>
      <ЗначенияРеквизитов>
        <ЗначениеРеквизита>
          <Наименование>СтатусЗаказа</Наименование>
          <Значение>Отгружен</Значение>
        </ЗначениеРеквизита>
      </ЗначенияРеквизитов>
    </Документ>
  </Контейнер>
</КоммерческаяИнформация>
```

### Протокол 1С (type=sale)

**Полный flow обмена заказами:**
1. `GET /?type=sale&mode=checkauth` → Basic Auth, установка сессии
2. `GET /?type=sale&mode=init` → Capability negotiation
3. `GET /?type=sale&mode=query` → Экспорт заказов (уже реализовано, Story 4.3)
4. `GET /?type=sale&mode=success` → Подтверждение получения (уже реализовано, Story 4.3)
5. `POST /?type=sale&mode=file&filename=orders.xml` → **ЭТА STORY** — импорт статусов

**ВАЖНО:** В отличие от catalog import (mode=file → mode=import), orders.xml обрабатывается синхронно в mode=file, т.к.:
- Файл маленький (обычно <1MB)
- 1С ожидает немедленный ответ о результате
- Не требуется распаковка ZIP или batch processing

### Testing Standards (10-testing-strategy.md)

**§10.3.1 Integration-тесты:**
- Размещение: `backend/tests/integration/test_orders_xml_mode_file.py`
- Маркировка: `@pytest.mark.integration`, `@pytest.mark.django_db`
- Используют реальную БД через Docker

**§10.4.2 Factory Boy:**
```python
from tests.conftest import get_unique_suffix

# Создание тестового заказа
order = OrderFactory(
    order_number=f"FS-{get_unique_suffix()}",
    status="pending",
    sent_to_1c=True,  # Заказ уже был экспортирован в 1С
)
```

**§10.6.3 AAA-паттерн:**
```python
def test_mode_file_orders_xml_updates_order_status(self, api_client, order):
    # ARRANGE
    xml_data = build_orders_xml(order_id=order.pk, status="Отгружен")

    # ACT
    response = api_client.post(
        "/api/v1/1c-exchange/?type=sale&mode=file&filename=orders.xml",
        data=xml_data,
        content_type="application/xml",
    )

    # ASSERT
    assert response.status_code == 200
    assert response.content == b"success"
    order.refresh_from_db()
    assert order.status == "shipped"
```

### Файлы референса из Story 5.1

- `backend/apps/orders/services/order_status_import.py` — OrderStatusImportService
- `backend/apps/orders/constants.py` — ORDER_ID_PREFIX, ProcessingStatus
- `backend/tests/unit/test_order_status_import.py` — 45 unit-тестов
- `backend/tests/integration/test_order_status_import_db.py` — 7 интеграционных тестов

### Anti-patterns

- ❌ Не стримить orders.xml в файл — обрабатывать inline
- ❌ Не требовать mode=import после mode=file для orders.xml
- ❌ Не дублировать логику парсинга — использовать OrderStatusImportService
- ❌ Не игнорировать ImportResult.errors — логировать для отладки
- ❌ Не возвращать `failure` при частичных ошибках — только при полном отказе

### Dependencies

- **Story 5.1:** OrderStatusImportService (in-progress) — **BLOCKER**
- **Story 4.3:** ICExchangeView (done) — базовый класс
- **Story 1.1:** Basic1CAuthentication (done) — аутентификация

### Files to Create/Modify

- `backend/apps/integrations/onec_exchange/views.py` (MODIFY) — добавить обработку orders.xml
- `backend/apps/integrations/onec_exchange/routing_service.py` (MODIFY) — добавить "orders" в XML_ROUTING_RULES
- `backend/tests/integration/test_orders_xml_mode_file.py` (NEW) — интеграционные тесты

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2] — Оригинальные AC
- [Source: backend/apps/integrations/onec_exchange/views.py:496-545] — handle_file_upload()
- [Source: backend/apps/orders/services/order_status_import.py] — OrderStatusImportService
- [Source: docs/architecture-backend.md] — Fat Services, Thin Views паттерн
- [Source: docs/integrations/1c/analysis-orders-xml.md] — Анализ формата orders.xml
- [Source: 5-1-order-status-import-service.md] — Story 5.1 контекст

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

N/A

### Completion Notes List

(To be filled by dev agent)

### Change Log

- 2026-02-04: Story created by SM agent

### File List

(To be filled by dev agent after implementation)
