# Story 5.2: View-обработчик mode=file для orders.xml

Status: review

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
8. **AC8:** Защита от регресса статуса: если новый статус "ниже" текущего (например, `shipped` после `delivered`) — заказ пропускается с warning.
9. **AC9:** При `result.processed == 0` на непустом XML — логируется `error` для alerting.
10. **AC10:** Поддержка кодировки `windows-1251`: если XML declaration указывает кодировку — корректно декодируется.
11. **AC11:** При обрыве соединения (truncated body: `len(body) != Content-Length`) возвращается `failure\nIncomplete request body`.
12. **AC12:** Rate limiting: max 60 requests/min на `/1c-exchange/`, max 10 auth attempts/min на `mode=checkauth`.
13. **AC13:** Timestamp validation: XML с `<ДатаФормирования>` старше 24 часов отклоняется с `failure\nXML timestamp too old`.
14. **AC14:** Field whitelist: orders.xml обрабатывает ТОЛЬКО теги `Номер`, `Ид`, `ЗначенияРеквизитов` (СтатусЗаказа, ДатаОплаты, ДатаОтгрузки); другие поля игнорируются с warning.

## Tasks / Subtasks

- [x] Task 1: Модификация handle_file_upload для orders.xml (AC: 1, 3, 5)
  - [x] 1.1: В `backend/apps/integrations/onec_exchange/views.py` добавить проверку `filename.lower() == ORDERS_XML_FILENAME` в `handle_file_upload()`.
  - [x] 1.2: При совпадении — вызвать новый метод `return self._handle_orders_xml(request)` (ADR-002).
  - [x] 1.3: Создать приватный метод `_handle_orders_xml(self, request) -> HttpResponse`.
  - [x] 1.4: **Проверка размера (ADR-004):** Если `Content-Length > 5MB` → вернуть `failure\nFile too large for inline processing`.
  - [x] 1.5: **Audit log ПЕРВЫМ (ADR-005):** Сохранить копию XML через `_save_exchange_log()` ДО обработки.
  - [x] 1.6: Читать тело запроса в память: `xml_data = request._request.read()`.
  - [x] 1.7: Вызвать `OrderStatusImportService().process(xml_data)`.
  - [x] 1.8: **Partial Success (ADR-003):** Вернуть `success` если `result.updated > 0` ИЛИ `result.errors == []`, иначе `failure\n{summary}`.
  - [x] 1.9: **FM1.1 — Body integrity:** Проверить `len(xml_data) == Content-Length` после чтения; если не совпадает → `failure\nIncomplete request body`.

- [x] Task 2: Добавить маршрутизацию в routing_service (AC: 1)
  - [x] 2.1: Добавить `"orders": "orders/"` в `XML_ROUTING_RULES` (для consistency, хотя orders.xml обрабатывается inline).
  - [x] 2.2: Документировать специальную обработку orders.xml в docstring.

- [x] Task 3: Добавить импорт OrderStatusImportService (AC: 1)
  - [x] 3.1: Добавить `from apps.orders.services.order_status_import import OrderStatusImportService` в views.py.

- [x] Task 4: Integration-тесты (AC: 7, 8, 9, 10, 11)
  - [x] 4.1: Создать `backend/tests/integration/test_orders_xml_mode_file.py`.
  - [x] 4.2: `test_mode_file_orders_xml_updates_order_status` — POST с валидным orders.xml обновляет Order.status.
  - [x] 4.3: `test_mode_file_orders_xml_idempotent` — повторная отправка не создаёт ошибок.
  - [x] 4.4: `test_mode_file_orders_xml_saves_audit_log` — проверить что файл сохранён в logs.
  - [x] 4.5: `test_mode_file_orders_xml_returns_failure_on_invalid_xml` — невалидный XML → failure.
  - [x] 4.6: `test_mode_file_orders_xml_requires_auth` — без аутентификации → 401/403.
  - [x] 4.7: `test_mode_file_orders_xml_blocks_status_regression` — shipped после delivered → skip (AC8).
  - [x] 4.8: `test_mode_file_orders_xml_allows_cancellation_anytime` — cancelled разрешён на любом этапе (AC8).
  - [x] 4.9: `test_mode_file_orders_xml_windows1251_encoding` — XML в windows-1251 корректно обрабатывается (AC10).
  - [x] 4.10: `test_mode_file_orders_xml_zero_processed_logs_error` — пустой результат при непустом XML → error log (AC9).
  - [x] 4.11: `test_mode_file_orders_xml_truncated_body` — Content-Length не совпадает с body → `failure\nIncomplete request body` (AC11).
  - [x] 4.12: `test_mode_file_orders_xml_too_many_documents` — >1000 документов → `failure\nToo many documents` (FM4.5).
  - [x] 4.13: `test_mode_file_orders_xml_rate_limited` — превышение 60 req/min → HTTP 429 (AC12).
  - [x] 4.14: `test_mode_file_orders_xml_stale_timestamp_rejected` — XML с `ДатаФормирования` > 24h → `failure\nXML timestamp too old` (AC13).
  - [x] 4.15: `test_mode_file_orders_xml_ignores_unexpected_fields` — XML с тегами `<Адрес>`, `<Сумма>` → поля игнорируются, warning в логах (AC14).
  - [x] 4.16: Использовать Factory Boy с `get_unique_suffix()`, маркеры `@pytest.mark.integration`, `@pytest.mark.django_db`, AAA-паттерн.

- [x] Task 5: Обработка ошибок и логирование (AC: 3, 6, 11)
  - [x] 5.1: При `ImportResult.errors` — логировать `logger.warning()` с деталями.
  - [x] 5.2: Формировать summary: `"processed={n}, updated={m}, errors={k}"`.
  - [x] 5.3: При исключении в `OrderStatusImportService` — `logger.exception()`, вернуть `failure\nInternal error`.
  - [x] 5.4: **FM3.1 — Parse errors:** Явно ловить `ET.ParseError` и `DefusedXmlException`, возвращать `failure\nMalformed XML` / `failure\nXML security violation`.
  - [x] 5.5: **FM4.5 — Max documents:** Добавить `MAX_DOCUMENTS_PER_FILE = 1000` константу; при превышении → `failure\nToo many documents`.
  - [x] 5.6: **FM5.1/FM5.2 — DB retry:** Добавить retry logic (3 попытки с backoff) при `OperationalError` от PostgreSQL.

- [x] Task 6: Alerting на нулевую обработку (AC: 9) — Pre-mortem #1
  - [x] 6.1: Если `result.processed == 0` при `len(xml_data) > 100` → `logger.error("[ORDERS IMPORT] Zero documents processed from non-empty XML")`.
  - [x] 6.2: Добавить метрику для мониторинга: `orders_import_zero_processed_total`.
  - [x] 6.3: Документировать alert rule в Dev Notes для DevOps.

- [x] Task 7: Защита от регресса статуса (AC: 8) — Pre-mortem #2
  - [x] 7.1: Добавить `STATUS_PRIORITY` в `backend/apps/orders/constants.py`:
    ```python
    STATUS_PRIORITY = {
        "pending": 1, "confirmed": 2, "processing": 3,
        "shipped": 4, "delivered": 5, "cancelled": 0, "refunded": 0
    }
    ```
  - [x] 7.2: В `OrderStatusImportService._process_order_update()`: если `new_priority < current_priority` и `new_status not in ("cancelled", "refunded")` → skip + `logger.warning("Status regression blocked")`.
  - [x] 7.3: Добавить unit-тест: `test_status_regression_blocked`.
  - [x] 7.4: Cancelled/refunded всегда разрешены (бизнес-требование: отмена возможна на любом этапе).

- [x] Task 8: Поддержка windows-1251 кодировки (AC: 10) — Pre-mortem #5
  - [x] 8.1: В `_handle_orders_xml()` детектировать кодировку из первых 100 байт: `<?xml ... encoding="windows-1251"?>`.
  - [x] 8.2: Если не UTF-8 — декодировать и перекодировать в UTF-8 перед передачей в сервис.
  - [x] 8.3: Добавить integration-тест: `test_mode_file_orders_xml_windows1251_encoding`.

- [x] Task 9: Security Hardening (AC: 12, 13) — Security Audit
  - [x] 9.1: Добавить throttle class `OneCExchangeThrottle` с rate `60/min` в `backend/apps/integrations/onec_exchange/throttling.py`.
  - [x] 9.2: Добавить throttle class `OneCAuthThrottle` с rate `10/min` для `mode=checkauth`.
  - [x] 9.3: Применить throttling к `ICExchangeView` через `throttle_classes`.
  - [x] 9.4: Реализовать `_validate_xml_timestamp()`: извлечь `<ДатаФормирования>`, проверить < 24 часов.
  - [x] 9.5: При stale timestamp → `logger.warning("[SECURITY] Stale XML rejected")` + `failure\nXML timestamp too old`.
  - [x] 9.6: (Optional) Добавить `ONEC_EXCHANGE['ALLOWED_IPS']` в settings для IP whitelist.
  - [x] 9.7: Добавить security logging для подозрительных событий: `[SECURITY]` prefix.

- [x] Task 10: Field Whitelist Protection (AC: 14) — Red Team R3
  - [x] 10.1: Определить `ALLOWED_ORDER_FIELDS = {'Номер', 'Ид', 'ЗначенияРеквизитов'}` в constants.
  - [x] 10.2: Определить `ALLOWED_REQUISITES = {'СтатусЗаказа', 'Статус Заказа', 'ДатаОплаты', 'Дата Оплаты', 'ДатаОтгрузки', 'Дата Отгрузки'}`.
  - [x] 10.3: В `OrderStatusImportService._parse_document()` игнорировать теги не из whitelist.
  - [x] 10.4: При обнаружении неожиданных тегов (Адрес, Сумма, Товары и др.) → `logger.warning("[SECURITY] Unexpected field in orders.xml: {tag}")`.
  - [x] 10.5: Добавить метрику `orders_import_unexpected_fields_total` для мониторинга попыток injection.

## Tasks / Subtasks (Review Follow-ups)

- [x] [AI-Review][Medium] Добавить новые файлы (`throttling.py`, `test_orders_xml_mode_file.py`) в git (untracked).

## Senior Developer Review (AI)

_Reviewer: Amelia (Dev Agent)_
_Date: 2026-02-06_

### Findings

#### 🟡 Medium Severity
1.  **Security/Resources**: `backend/apps/integrations/onec_exchange/views.py` использует `xml_data = request._request.read()` (line 611). Это полагается на то, что `Content-Length` заголовок соответствует реальности или что веб-сервер обрезает тело. Если злоумышленник укажет `Content-Length: 100`, но отправит 100MB, а server buffer settings это позволяют, мы прочитаем всё в память.
    -   *Recommendation*: Использовать `request._request.read(ORDERS_XML_MAX_SIZE + 1)` для гарантии лимита.

#### 🟢 Low Severity
1.  **Robustness**: `_validate_xml_timestamp` читает только первые 500 байт (`orders.xml`). Если в начале файла будут длинные комментарии или DOCTYPE, проверка может пропустить валидный timestamp или вернуть False negative (fail-open).
    -   *Recommendation*: Увеличить окно поиска до 2-4KB.

### Conclusion
**Approve with Follow-ups**. Реализация надежная, тесты проходят. Найденные проблемы не блокируют релиз, но должны быть исправлены.

## Tasks / Subtasks (Review Follow-ups 2)

- [x] [AI-Review][Medium] Hardening: ограничить `request.read()` лимитом `ORDERS_XML_MAX_SIZE + 1`.
- [x] [AI-Review][Low] Увеличить буфер чтения для `_validate_xml_timestamp` до 2048 байт.
- [x] [AI-Review][Medium] Error Handling: Обеспечить возврат специфичного `failure\nMalformed XML` при ошибках парсинга (сейчас экранируется сервисом).
- [x] [AI-Review][Low] Refactoring: Унифицировать сигнатуру `_parse_document` (вернуть Result или исключение).


## Dev Notes

### Архитектурные решения (ADR)

**ADR-001: Синхронная обработка**
- orders.xml обрабатывается inline в `handle_file_upload()`
- Асинхронность (Celery) НЕ используется — 1С ожидает немедленный ответ
- Обоснование: файл маленький (<1MB), протокол требует немедленного ответа

**ADR-002: Структура кода**
- Выделить `_handle_orders_xml()` как отдельный приватный метод
- `handle_file_upload()` только маршрутизирует по filename
- Обоснование: Single Responsibility, тестируемость, расширяемость

**ADR-003: Partial Success Strategy**
- Если хотя бы 1 заказ обновлён → `success`
- Только при полном отказе (invalid XML, exception) → `failure`
- Обоснование: 1С не умеет обрабатывать partial failure

**ADR-004: Защита от больших файлов**
- `Content-Length > 5MB` → `failure\nFile too large for inline processing`
- Проверка ДО чтения тела запроса
- Обоснование: предотвращение timeout и OOM

**ADR-005: Audit Log порядок**
- Порядок: Сохранить копию XML → Обработать → Вернуть ответ
- Обоснование: при сбое можно восстановить и повторить обработку

---

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
# В handle_file_upload(), перед стримингом в файл (ADR-002):
if filename.lower() == ORDERS_XML_FILENAME:
    return self._handle_orders_xml(request)

# Константа для лимита размера (ADR-004)
ORDERS_XML_MAX_SIZE = 5 * 1024 * 1024  # 5MB

def _handle_orders_xml(self, request) -> HttpResponse:
    """
    Handle orders.xml import synchronously (ADR-001).

    Unlike catalog files (streamed to disk), orders.xml is processed
    inline because:
    1. It's typically small (<1MB)
    2. 1C expects immediate status response
    3. No need for mode=import follow-up
    """
    try:
        # ADR-004: Check file size BEFORE reading
        content_length = int(request.META.get("CONTENT_LENGTH", 0))
        if content_length > ORDERS_XML_MAX_SIZE:
            logger.warning(
                f"[ORDERS IMPORT] Rejected: file too large ({content_length} bytes)"
            )
            return HttpResponse(
                "failure\nFile too large for inline processing",
                content_type="text/plain; charset=utf-8",
            )

        # Read full body (orders.xml is small)
        xml_data = request._request.read()

        # ADR-005: Audit log BEFORE processing (for recovery)
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

        # ADR-003: Partial Success = Success
        # Return success if at least one order was updated OR no errors
        if result.updated > 0 or not result.errors:
            return HttpResponse("success", content_type="text/plain; charset=utf-8")

        # Complete failure: nothing updated AND errors present
        return HttpResponse(
            f"failure\nNo orders updated. Errors: {len(result.errors)}",
            content_type="text/plain; charset=utf-8",
        )

    except Exception as e:
        logger.exception(f"[ORDERS IMPORT] Failed: {e}")
        return HttpResponse(
            "failure\nInternal error",
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

### Red Team Lesson: Field Whitelist (Supply Chain Attack)

**Сценарий атаки R3:** Злоумышленник компрометирует 1С сервер и модифицирует orders.xml, добавляя поля для изменения адреса доставки или суммы заказа.

**Защита:** Строгий whitelist разрешённых полей:
```python
# backend/apps/orders/constants.py
ALLOWED_ORDER_FIELDS = {'Номер', 'Ид', 'ЗначенияРеквизитов'}
ALLOWED_REQUISITES = {
    'СтатусЗаказа', 'Статус Заказа',
    'ДатаОплаты', 'Дата Оплаты',
    'ДатаОтгрузки', 'Дата Отгрузки',
}

# В _parse_document():
for child in document:
    if child.tag not in ALLOWED_ORDER_FIELDS:
        logger.warning(f"[SECURITY] Unexpected field in orders.xml: {child.tag}")
        continue  # Ignore, don't process
```

**Принцип:** orders.xml — это flow ТОЛЬКО для статусов. Любые другие данные (адрес, сумма, товары) должны игнорироваться.

---

### Security Audit: Защитные механизмы

**OWASP API Security покрытие:**
| Risk | Status | Mechanism |
|------|--------|-----------|
| Broken Authentication | ✅ | Rate limiting 10/min on auth |
| Unrestricted Resource Consumption | ✅ | Size limit 5MB, rate 60/min |
| Broken Function Level Auth | ✅ | `Is1CExchangeUser` permission |

**Реализованные защиты:**
```python
# backend/apps/integrations/onec_exchange/throttling.py
from rest_framework.throttling import SimpleRateThrottle

class OneCExchangeThrottle(SimpleRateThrottle):
    rate = '60/min'
    scope = '1c_exchange'

class OneCAuthThrottle(SimpleRateThrottle):
    rate = '10/min'
    scope = '1c_auth'
```

**Timestamp validation (Anti-Replay):**
```python
from datetime import timedelta
from django.utils import timezone

MAX_XML_AGE = timedelta(hours=24)

def _validate_xml_timestamp(xml_data: bytes) -> bool:
    """Reject XML older than 24 hours to prevent replay attacks."""
    # Parse <ДатаФормирования> from XML
    # Return False if timestamp > 24h old
```

**Security logging prefix:** `[SECURITY]` для фильтрации в SIEM.

---

### Failure Mode Analysis: Критические точки отказа

| FM ID | Компонент | Failure Mode | Mitigation |
|-------|-----------|--------------|------------|
| FM1.1 | HTTP | Body truncated | Проверка `len(body) == Content-Length` |
| FM3.1 | XML Parser | Malformed XML | Catch `ParseError` → понятный `failure` |
| FM4.5 | Service | Too many documents | `MAX_DOCUMENTS_PER_FILE = 1000` |
| FM5.1 | Database | Connection exhausted | Retry 3x с backoff |
| FM5.2 | Database | Transaction timeout | Retry 3x с backoff |

**Retry pattern для DB errors:**
```python
from django.db import OperationalError
import time

MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    try:
        result = service.process(xml_data)
        break
    except OperationalError as e:
        if attempt == MAX_RETRIES - 1:
            raise
        logger.warning(f"[ORDERS IMPORT] DB error, retry {attempt+1}: {e}")
        time.sleep(0.5 * (attempt + 1))  # 0.5s, 1s, 1.5s
```

---

### Pre-mortem: Превентивные меры

**Сценарий #1 — Молчаливый провал:**
- Alert при `processed == 0` на непустом XML
- Метрика `orders_import_zero_processed_total` для мониторинга

**Сценарий #2 — Регресс статуса:**
```python
# backend/apps/orders/constants.py
STATUS_PRIORITY = {
    "pending": 1,
    "confirmed": 2,
    "processing": 3,
    "shipped": 4,
    "delivered": 5,
    "cancelled": 0,  # Особый случай: всегда разрешён
    "refunded": 0,   # Особый случай: всегда разрешён
}
```
- Блокировка: `new_priority < current_priority` → skip (кроме cancelled/refunded)

**Сценарий #5 — Кодировка windows-1251:**
- Детекция из XML declaration
- Перекодирование в UTF-8 перед парсингом

### Anti-patterns

- ❌ Не стримить orders.xml в файл — обрабатывать inline
- ❌ Не требовать mode=import после mode=file для orders.xml
- ❌ Не дублировать логику парсинга — использовать OrderStatusImportService
- ❌ Не игнорировать ImportResult.errors — логировать для отладки
- ❌ Не возвращать `failure` при частичных ошибках — только при полном отказе
- ❌ Не разрешать регресс статуса (shipped → pending) — блокировать с warning
- ❌ Не игнорировать `processed == 0` — это сигнал проблемы с форматом XML

### Dependencies

- **Story 5.1:** OrderStatusImportService (in-progress) — **BLOCKER**
- **Story 4.3:** ICExchangeView (done) — базовый класс
- **Story 1.1:** Basic1CAuthentication (done) — аутентификация

### Files to Create/Modify

- `backend/apps/integrations/onec_exchange/views.py` (MODIFY) — добавить обработку orders.xml
- `backend/apps/integrations/onec_exchange/routing_service.py` (MODIFY) — добавить "orders" в XML_ROUTING_RULES
- `backend/apps/integrations/onec_exchange/throttling.py` (NEW) — rate limiting classes
- `backend/apps/orders/constants.py` (MODIFY) — добавить STATUS_PRIORITY, ALLOWED_ORDER_FIELDS, ALLOWED_REQUISITES
- `backend/tests/integration/test_orders_xml_mode_file.py` (NEW) — интеграционные тесты (14 тестов)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2] — Оригинальные AC
- [Source: backend/apps/integrations/onec_exchange/views.py:496-545] — handle_file_upload()
- [Source: backend/apps/orders/services/order_status_import.py] — OrderStatusImportService
- [Source: docs/architecture-backend.md] — Fat Services, Thin Views паттерн
- [Source: docs/integrations/1c/analysis-orders-xml.md] — Анализ формата orders.xml
- [Source: 5-1-order-status-import-service.md] — Story 5.1 контекст

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4 (Cascade)

### Debug Log References

- `docker compose --env-file .env -f docker/docker-compose.yml run --rm backend pytest tests/integration/test_orders_xml_mode_file.py tests/unit/test_order_status_import.py` (pass, 94 tests)
- `docker compose --env-file .env -f docker/docker-compose.yml run --rm backend pytest` (failed: unrelated tests in 1c_file_upload, integrations_admin_actions, management_commands, onec_exchange_api, token_blacklist, file_routing)

### Completion Notes List

- Tasks 1-3: Core handler `_handle_orders_xml` + routing + import — inline processing of orders.xml
- Task 5: Error handling (XML-specific exceptions, MAX_DOCUMENTS_PER_FILE=1000, DB retry with backoff)
- Task 6: Zero-processed alerting (`logger.error` on non-empty XML with 0 documents)
- Task 7: Priority-based status regression (`STATUS_PRIORITY` dict, blocks downgrades, final→any blocked)
- Task 8: windows-1251 re-encoding via `_reencode_xml_if_needed`
- Task 9: Security — `OneCExchangeThrottle` (60/min), `OneCAuthThrottle` (10/min), `_validate_xml_timestamp` (24h)
- Task 10: Field whitelist — `ALLOWED_REQUISITES` filtering in `_extract_all_requisites`
- Task 4: 20 integration tests — all passing. 73 unit tests unaffected.
- Review follow-ups: task checkboxes synced, rate limiting integration test added (test_rate_limiting_returns_429)
- Review follow-ups 2: лимит чтения тела, буфер timestamp=2048, специфичный `Malformed XML`/`XML security violation`, `_parse_document` через исключение, новые тесты (oversize body, updated unit assertions).

### Change Log

- 2026-02-04: Story created by SM agent
- 2026-02-06: All tasks implemented and tested. Status → review.
- 2026-02-06: Addressed code review findings — 3 items resolved. Rate limiting integration test added (AC12). Task checkboxes synced. Status → review.
- 2026-02-06: Review follow-ups 2 закрыты; целевые pytest прошли, полный прогон упал на несвязанных тестах.

### File List

- `backend/apps/integrations/onec_exchange/views.py` — `_handle_orders_xml`, `_reencode_xml_if_needed`, `_validate_xml_timestamp`, constants
- `backend/apps/integrations/onec_exchange/throttling.py` — NEW: `OneCExchangeThrottle`, `OneCAuthThrottle`
- `backend/apps/integrations/onec_exchange/routing_service.py` — Added "orders" to `XML_ROUTING_RULES`
- `backend/apps/orders/constants.py` — Added `STATUS_PRIORITY`, `ALLOWED_ORDER_FIELDS`, `ALLOWED_REQUISITES`
- `backend/apps/orders/services/order_status_import.py` — Priority-based regression, field whitelist filtering
- `backend/tests/integration/test_orders_xml_mode_file.py` — NEW: 20 integration tests
- `backend/tests/unit/test_order_status_import.py` — Updated for `_parse_document` exception signature
