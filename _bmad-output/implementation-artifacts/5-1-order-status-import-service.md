# Story 5.1: Сервис импорта статусов (OrderStatusImportService)

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **система интеграции**,
I want **сервис, парсящий orders.xml из 1С и обновляющий статусы заказов**,
So that **статусы заказов на сайте соответствуют актуальным данным из 1С**.

## Acceptance Criteria

1. **AC1:** XML-файл orders.xml в формате CommerceML 3.1 с тегами `<Контейнер>`, содержащими `<Документ>`, корректно парсится.
2. **AC2:** Заказ найден по `<Номер>` (order_number) или `<Ид>` (order-{id}) (FR2.2).
3. **AC3:** Статус обновлён по маппингу: `Отгружен→shipped`, `Доставлен→delivered`, `ОжидаетОбработки→processing`, `Отменен→cancelled`, `Подтвержден→confirmed`, `Возвращен→refunded` (FR2.3).
4. **AC4:** Оригинальный статус из 1С сохранён в поле `status_1c`.
5. **AC5:** Даты оплаты и отгрузки извлечены из `<ЗначениеРеквизита>` (`ДатаОплаты`, `ДатаОтгрузки`) и сохранены в соответствующие поля Order (FR2.4).
6. **AC6:** При неизвестном статусе — логируется предупреждение, заказ **не** обновляется (защита от некорректных данных).
7. **AC7:** При отсутствии заказа по ID — логируется ошибка, обработка **продолжается** для остальных заказов.
8. **AC8:** Операции идемпотентны — повторная обработка того же файла не ломает данные.
9. **AC9:** Unit-тесты: парсинг XML, маппинг всех 6 статусов, обработка отсутствующего заказа, извлечение дат.
10. **AC10:** Сервис реализован в `services.py`, парсинг XML отделён от бизнес-логики (Parser/Processor pattern).

## Tasks / Subtasks

- [x] Task 1: Создание OrderStatusImportService (AC: 1, 2, 3, 4, 10)
  - [x] 1.1: Создать `backend/apps/orders/services/order_status_import.py` — новый сервис.
  - [x] 1.2: Реализовать `STATUS_MAPPING` словарь для маппинга статусов 1С → FREESPORT.
  - [x] 1.3: Реализовать метод `process(xml_data: str | bytes) -> ImportResult` — основная точка входа.
  - [x] 1.4: Реализовать `_parse_orders_xml(xml_data) -> list[OrderUpdateData]` — парсер XML (Parser).
  - [x] 1.5: Реализовать `_process_order_update(order_data: OrderUpdateData) -> bool` — обработчик (Processor).
  - [x] 1.6: Поиск заказа: сначала по `<Номер>` (order_number), затем по `<Ид>` формата `order-{id}`.

- [x] Task 2: Извлечение дат из реквизитов (AC: 5)
  - [x] 2.1: Реализовать `_extract_requisite_value(document: ET.Element, name: str) -> str | None`.
  - [x] 2.2: Парсинг `<ЗначениеРеквизита>` с `<Наименование>ДатаОплаты</Наименование>` → поле `paid_at`.
  - [x] 2.3: Парсинг `<ЗначениеРеквизита>` с `<Наименование>ДатаОтгрузки</Наименование>` → поле `shipped_at`.
  - [x] 2.4: Добавить поля `paid_at`, `shipped_at` в модель Order если отсутствуют (миграция).

- [x] Task 3: Обработка ошибок и логирование (AC: 6, 7, 8)
  - [x] 3.1: При неизвестном статусе — `logger.warning()`, пропуск заказа, счётчик `skipped_count`.
  - [x] 3.2: При отсутствии заказа — `logger.error()`, продолжение обработки, счётчик `not_found_count`.
  - [x] 3.3: Возврат `ImportResult(processed=N, updated=M, skipped=K, not_found=L, errors=[...])`.
  - [x] 3.4: Идемпотентность: не обновлять заказ если статус уже совпадает.

- [x] Task 4: Unit-тесты (AC: 9)
  - [x] 4.1: Создать `backend/tests/unit/test_order_status_import.py`.
  - [x] 4.2: `test_parse_valid_xml_extracts_order_data` — парсинг валидного XML.
  - [x] 4.3: `test_status_mapping_all_statuses` — проверка всех 6 статусов маппинга.
  - [x] 4.4: `test_process_updates_order_status_and_status_1c` — обновление статуса + status_1c.
  - [x] 4.5: `test_process_extracts_payment_and_shipment_dates` — извлечение дат.
  - [x] 4.6: `test_unknown_status_logs_warning_and_skips` — неизвестный статус.
  - [x] 4.7: `test_missing_order_logs_error_and_continues` — отсутствующий заказ.
  - [x] 4.8: `test_idempotent_processing_no_duplicate_updates` — идемпотентность.
  - [x] 4.9: Использовать Factory Boy с `get_unique_suffix()`, маркеры `@pytest.mark.unit`, AAA-паттерн.

- [x] Task 5: Интеграция и экспорт (AC: 10)
  - [x] 5.1: Добавить `OrderStatusImportService` в `__init__.py` сервисов.
  - [x] 5.2: Документировать публичный API сервиса (docstrings).

### Review Follow-ups (AI)

- [ ] [AI-Review][High] Исправить баг идемпотентности: обновление дат игнорируется, если статус не изменился `backend/apps/orders/services/order_status_import.py:304`
- [ ] [AI-Review][Medium] Оптимизация N+1: реализовать bulk fetching заказов перед обработкой `backend/apps/orders/services/order_status_import.py:109`
- [ ] [AI-Review][Low] Рассмотреть использование `defusedxml` для защиты от XML-атак `backend/apps/orders/services/order_status_import.py:12`
- [ ] [AI-Review][Low] Использовать `parse_datetime` вместо `parse_date` для сохранения времени из 1С `backend/apps/orders/services/order_status_import.py:253`

## Dev Notes

### Архитектурные требования

**Service Layer Pattern (docs/architecture-backend.md):**
- Вся бизнес-логика в `apps/orders/services/order_status_import.py`
- View (Story 5-2) только оркестрирует вызов сервиса

**Parser/Processor Pattern:**
- `_parse_orders_xml()` — чистый парсинг XML, возврат dataclass/TypedDict
- `_process_order_update()` — бизнес-логика обновления Order
- Разделение упрощает unit-тестирование

### Маппинг статусов 1С → FREESPORT

```python
STATUS_MAPPING = {
    # 1С статус → FREESPORT статус
    "ОжидаетОбработки": "processing",
    "Подтвержден": "confirmed",
    "Отгружен": "shipped",
    "Доставлен": "delivered",
    "Отменен": "cancelled",
    "Возвращен": "refunded",
}
```

**Order.ORDER_STATUSES (apps/orders/models.py:66-74):**
- `pending` — Ожидает обработки (default)
- `confirmed` — Подтвержден
- `processing` — В обработке
- `shipped` — Отправлен
- `delivered` — Доставлен
- `cancelled` — Отменен
- `refunded` — Возвращен

### XML структура orders.xml (CommerceML 3.1)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="3.1" ДатаФормирования="2026-02-02T12:00:00">
  <Контейнер>
    <Документ>
      <Ид>order-123</Ид>
      <Номер>FS-20260202-001</Номер>
      <Дата>2026-02-02</Дата>
      <ХозОперация>Заказ товара</ХозОперация>
      <ЗначенияРеквизитов>
        <ЗначениеРеквизита>
          <Наименование>СтатусЗаказа</Наименование>
          <Значение>Отгружен</Значение>
        </ЗначениеРеквизита>
        <ЗначениеРеквизита>
          <Наименование>ДатаОплаты</Наименование>
          <Значение>2026-02-01</Значение>
        </ЗначениеРеквизита>
        <ЗначениеРеквизита>
          <Наименование>ДатаОтгрузки</Наименование>
          <Значение>2026-02-02</Значение>
        </ЗначениеРеквизита>
      </ЗначенияРеквизитов>
    </Документ>
  </Контейнер>
</КоммерческаяИнформация>
```

### Паттерны из OrderExportService (Story 4-2)

**Референсный файл:** `backend/apps/orders/services/order_export.py`

Применить аналогичные паттерны:
- Использование `xml.etree.ElementTree` для парсинга
- Логирование через `logging.getLogger(__name__)`
- Type hints с `TYPE_CHECKING` для избежания циклических импортов
- Docstrings в Google style

### Структура ImportResult

```python
from dataclasses import dataclass, field

@dataclass
class ImportResult:
    """Результат импорта статусов заказов."""
    processed: int = 0       # Всего обработано документов
    updated: int = 0         # Успешно обновлено заказов
    skipped: int = 0         # Пропущено (неизвестный статус, уже актуальный)
    not_found: int = 0       # Заказ не найден в БД
    errors: list[str] = field(default_factory=list)  # Ошибки парсинга/обработки
```

### Поля Order для дат (Task 2.4)

Если поля `paid_at` и `shipped_at` отсутствуют, создать миграцию:

```python
# Добавить в Order model
paid_at = models.DateTimeField("Дата оплаты", null=True, blank=True)
shipped_at = models.DateTimeField("Дата отгрузки", null=True, blank=True)
```

**Проверить существующие поля:** возможно `delivery_date` уже используется для отгрузки.

### Testing Standards (10-testing-strategy.md)

**§10.2.1 Unit-тесты:**
- Размещение: `backend/tests/unit/test_order_status_import.py`
- Маркировка: `@pytest.mark.unit`
- НЕ используют БД — мокают Order.objects

**§10.4.2 Factory Boy:**
```python
from tests.conftest import get_unique_suffix

# В тестах использовать:
order_number = f"FS-{get_unique_suffix()}"
```

**§10.6.3 AAA-паттерн:**
```python
def test_status_mapping_shipped(self):
    # ARRANGE
    xml_data = build_test_xml(status="Отгружен")
    
    # ACT
    result = service.process(xml_data)
    
    # ASSERT
    assert result.updated == 1
```

### Anti-patterns

- ❌ Не изменять Order.status напрямую во View — только через сервис
- ❌ Не игнорировать ошибки парсинга XML — логировать и возвращать в errors
- ❌ Не хардкодить статусы — использовать STATUS_MAPPING константу
- ❌ Не использовать `Sequence` в Factory Boy — только `LazyFunction`
- ❌ Не обновлять заказ при неизвестном статусе — безопасный пропуск

### Dependencies

- **Story 4-1:** Поля `sent_to_1c`, `sent_to_1c_at`, `status_1c` в Order (done)
- **Story 4-2:** OrderExportService — референс для паттернов (done)
- **Story 4-3:** ICExchangeView — базовый класс для Story 5-2 (done)

### Files to Create/Modify

- `backend/apps/orders/services/order_status_import.py` (NEW) — основной сервис
- `backend/apps/orders/services/__init__.py` (MODIFY) — экспорт сервиса
- `backend/apps/orders/migrations/XXXX_add_payment_shipment_dates.py` (NEW) — если нужны поля
- `backend/tests/unit/test_order_status_import.py` (NEW) — unit-тесты

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1] — Оригинальные AC
- [Source: backend/apps/orders/services/order_export.py] — Референсный сервис (паттерны)
- [Source: backend/apps/orders/models.py:66-74] — ORDER_STATUSES
- [Source: docs/architecture/10-testing-strategy.md#10.2.1] — Unit-тест стандарты
- [Source: docs/architecture-backend.md] — Service Layer паттерн
- [Source: project-context.md] — Общий контекст проекта

## Dev Agent Record

### Agent Model Used

Gemini 2.5 Pro (Antigravity)

### Debug Log References

N/A

### Completion Notes List

- Implemented `OrderStatusImportService` with Parser/Processor pattern (AC10)
- STATUS_MAPPING covers all 6 status translations (AC3)
- Order lookup by order_number (priority) then order-{id} (AC2)
- Date extraction from `ЗначенияРеквизитов` for `paid_at`/`shipped_at` (AC5)
- Error handling: unknown status → skip with warning (AC6), missing order → continue (AC7)
- Idempotency: skip if status already matches (AC8)
- 18 unit tests passing (AC9)

### Change Log

- 2026-02-03: Initial implementation of Story 5.1 (all tasks complete)

### File List

- `backend/apps/orders/services/order_status_import.py` (NEW) — основной сервис
- `backend/apps/orders/services/__init__.py` (MODIFY) — экспорт сервиса
- `backend/apps/orders/models.py` (MODIFY) — добавлены поля `paid_at`, `shipped_at`
- `backend/apps/orders/migrations/0011_add_payment_shipment_dates.py` (NEW) — миграция
- `backend/tests/unit/test_order_status_import.py` (NEW) — 18 unit-тестов
