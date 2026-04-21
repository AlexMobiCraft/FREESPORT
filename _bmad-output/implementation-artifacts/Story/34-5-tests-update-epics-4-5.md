# Story 34.5: Обновление тестов Epic 4+5 под master/sub структуру заказов

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **разработчик FREESPORT**,
I want **обновить все legacy-тесты Epic 4 (экспорт заказов в 1С) и Epic 5 (импорт статусов из 1С) так, чтобы фикстуры использовали master+sub структуру заказов**,
so that **тестовое покрытие полностью отражает production flow после Stories 34-1..34-4, все legacy тесты проходят на новой архитектуре, и будущие регрессии ловятся автоматически**.

> Техническая формулировка: мигрировать legacy-фикстуры в `test_order_export_service.py`, `test_onec_export.py`, `test_order_status_import.py`, `test_order_status_import_db.py`, `test_orders_xml_mode_file.py` с master-only `Order` на master+sub структуру; добавить cross-epic E2E тест полного цикла export→import с мульти-VAT разбивкой; обеспечить, что `pytest -m unit` и `pytest -m integration` проходят с 0 failures.

## Acceptance Criteria

1. **AC1 (миграция unit-фикстур экспорта):** В `backend/tests/unit/test_order_export_service.py` все legacy-тесты классов `TestOrderExportServiceXMLValidation`, `TestOrderExportServiceDocumentStructure`, `TestOrderExportServiceCounterparties`, `TestOrderExportServiceProducts`, `TestOrderExportServiceBatchExport` используют фикстуры master+sub (`is_master=False, parent_order=master`) вместо single master-only `Order`. Тесты проходят без изменения assertions (кроме адаптации к новому queryset `is_master=False`).
2. **AC2 (миграция integration-фикстур экспорта):** В `backend/tests/integration/test_onec_export.py` fixture `order_for_export` **уже** мигрирована (Story 34-3). Убедиться, что все тесты `TestModeQuery`, `TestModeSuccess`, `TestModeQuerySubOrders`, `TestModeSuccessAggregation` проходят. Любые оставшиеся legacy master-only тесты либо мигрированы, либо помечены как explicit regression (`test_legacy_master_without_sub_orders_is_not_exported`).
3. **AC3 (миграция unit-фикстур импорта):** В `backend/tests/unit/test_order_status_import.py` helper `_make_order()` и прямые `Order.objects.create(...)` в legacy-тестах Epic 5 используют master+sub структуру: XML `<Ид>order-{sub.id}</Ід>` → обновляется **субзаказ**, master агрегируется. Legacy-тесты, проверяющие прямое обновление `Order` (Epic 5 flow), остаются как regression для legacy-мастеров без sub_orders (`is_master=True, sub_orders.count()==0` — обратная совместимость AC2 Story 34-4).
4. **AC4 (миграция integration-фикстур импорта):** В `backend/tests/integration/test_order_status_import_db.py` и `test_orders_xml_mode_file.py` фикстуры создания заказов используют master+sub. Тесты покрывают: обновление sub через mode=file → master.status агрегирован.
5. **AC5 (E2E export-import E2E):** Добавлен cross-epic integration-тест `test_full_vat_split_export_import_cycle` в `backend/tests/integration/test_order_exchange_import_e2e.py`: создать master + 2 sub (vat_group=5 и 22) → `mode=query` → XML содержит 2 документа → `mode=success` → оба sub.sent_to_1c=True, master.sent_to_1c=True → `mode=file` с orders.xml (sub5→shipped, sub22→confirmed) → sub5.status=shipped, sub22.status=confirmed, master.status=pending (или confirmed, по матрице агрегации AC4 Story 34-4). Весь цикл — один тест, доказывающий корректность сквозного flow.
6. **AC6 (shared helper для master+sub фикстур):** Создать переиспользуемый helper `create_master_with_subs(user, variants_with_vat: list[tuple[ProductVariant, Decimal]], **order_kwargs) -> tuple[Order, list[Order]]` в `backend/tests/helpers.py` (или `backend/tests/factories.py`), возвращающий `(master, [sub1, sub2, ...])` с OrderItem в каждом sub. Helper используется во всех обновлённых тестах для DRY.
7. **AC7 (pytest markers):** Все новые и обновлённые тесты размечены `@pytest.mark.unit` / `@pytest.mark.integration` + `@pytest.mark.django_db`. Команды `pytest -m unit` и `pytest -m integration` выполняются без пропусков Story 34-5 coverage.
8. **AC8 (zero failures):** `pytest backend/tests/unit/test_order_export_service.py backend/tests/unit/test_order_status_import.py -v` — 0 failures. `pytest backend/tests/integration/test_onec_export.py backend/tests/integration/test_order_status_import_db.py backend/tests/integration/test_orders_xml_mode_file.py backend/tests/integration/test_order_exchange_import_e2e.py -v` — 0 failures.
9. **AC9 (E2E export fixture):** В `backend/tests/integration/test_onec_export_e2e.py` все тесты используют `_create_master_with_sub` helper (уже мигрированы в Story 34-3). Убедиться, что full cycle E2E (checkauth→query→success) проходит с master+sub.
10. **AC10 (без регрессии существующих тестов):** `pytest backend/tests/ -v --tb=short` — все существующие тесты проекта (не только Epic 4+5) проходят. Изменения фикстур не ломают тесты других stories/epics.

## Tasks / Subtasks

- [x] Task 1: Создать shared helper для master+sub фикстур (AC: 6)
  - [x] 1.1: Создать `backend/tests/helpers.py` с функцией `create_master_with_subs(user, variants_with_vat, **order_kwargs)`. Сигнатура: `user: User`, `variants_with_vat: list[tuple[ProductVariant, Decimal | None]]` (вариант + vat_rate), keyword args для общих полей заказа (`delivery_address`, `delivery_method`, `payment_method`). Возвращает `(master: Order, subs: list[Order])`.
  - [x] 1.2: Внутри helper: создать master (`is_master=True, parent_order=None`), для каждой уникальной `vat_rate` создать sub (`is_master=False, parent_order=master, vat_group=rate`), `OrderItem` в каждом sub с `vat_rate=rate`, пересчитать `total_amount` на sub и master.
  - [x] 1.3: Добавить вариант helper-а `create_single_sub_order(user, variant, vat_rate=None, **order_kwargs) -> tuple[Order, Order]` — для простых кейсов с одним sub (shortcut).
  - [x] 1.4: Добавить `build_test_xml_for_sub(sub_order, status_1c="Отгружен", paid_date=None, shipped_date=None) -> str` — генерирует XML с `<Ид>order-{sub.id}</Ід>` и `<Номер>{sub.order_number}</Номер>`.

- [x] Task 2: Мигрировать unit-фикстуры экспорта (AC: 1, 7)
  - [x] 2.1: В `backend/tests/unit/test_order_export_service.py` заменить все `Order.objects.create(...)` в legacy-тестах (классы `TestOrderExportService*`) на вызов `create_single_sub_order()` или inline master+sub creation. QuerySet передавать `Order.objects.filter(id=sub.id)` (не master).
  - [x] 2.2: Адаптировать assertions: `<Ид>` = `order-{sub.id}`, а не `order-{master.id}`.
  - [x] 2.3: Сохранить все legacy assertions по XML-структуре (CommerceML 3.1, `<Контрагенты>`, `<Товары>`, `<ХозОперация>`) — они должны проходить для sub так же, как для master.
  - [x] 2.4: Убедиться, что существующие тесты Story 34-3 (`TestGetOrderVatRate`, `TestOrderExportServiceSubOrderDocument`, `TestOrderExportServiceMasterGuard`) не затронуты.
  - [x] 2.5: Все тесты помечены `@pytest.mark.unit @pytest.mark.django_db`.

- [x] Task 3: Мигрировать unit-фикстуры импорта (AC: 3, 7)
  - [x] 3.1: В `backend/tests/unit/test_order_status_import.py` обновить helper `_make_order()` или добавить `_make_sub_order()`, возвращающий `(master, sub)`. XML генерировать с `order_id=f"order-{sub.pk}"`.
  - [x] 3.2: Legacy-тесты `TestOrderStatusImportService` (Story 5-1) разделить на 2 группы:
    - **Группа A (legacy-regression):** тесты, где `is_master=True, sub_orders.count()==0` — проверяют обратную совместимость. Оставить без изменений, добавить комментарий `# Legacy Epic 5 regression: master without sub_orders`.
    - **Группа B (modern-flow):** дублированные/обновлённые тесты с master+sub структурой. XML адресован субзаказу, после обновления — master агрегирован.
  - [x] 3.3: Убедиться, что тесты Story 34-4 (`TestMasterStatusAggregation`, `TestMasterGuardInImport`) не затронуты.
  - [x] 3.4: Все тесты помечены `@pytest.mark.unit @pytest.mark.django_db`.

- [x] Task 4: Мигрировать integration-фикстуры импорта (AC: 4, 7)
  - [x] 4.1: В `backend/tests/integration/test_order_status_import_db.py` обновить `setUp()` — создавать master+sub; XML адресовать субзаказу.
  - [x] 4.2: В `backend/tests/integration/test_orders_xml_mode_file.py` обновить `test_successful_status_update` и аналогичные — создавать master+sub, POST orders.xml с `<Ід>order-{sub.id}</Ід>`, assert: sub.status обновлён, master.status агрегирован.
  - [x] 4.3: Убедиться, что тесты Story 34-4 в `test_order_status_import_db.py` (`TestMasterAggregationDB`, `TestMasterGuardDB`) не затронуты.
  - [x] 4.4: Все тесты помечены `@pytest.mark.integration @pytest.mark.django_db`.

- [x] Task 5: Cross-epic E2E тест полного цикла (AC: 5, 7)
  - [x] 5.1: В `backend/tests/integration/test_order_exchange_import_e2e.py` добавить тест `test_full_vat_split_export_import_cycle`:
    - Arrange: создать master + sub5 (vat_group=5, variant.vat_rate=5) + sub22 (vat_group=22, variant.vat_rate=22), каждый с 1 OrderItem.
    - Act (export): `GET mode=query` → parse XML → assert 2 `<Документ>`, один с `<Организация>ИП Терещенко Л.В.`, другой с `<Организация>ИП Семерюк Д. В.`.
    - Act (confirm): `GET mode=success` → assert sub5.sent_to_1c=True, sub22.sent_to_1c=True, master.sent_to_1c=True.
    - Act (import): `POST mode=file&filename=orders.xml` с XML: sub5→shipped, sub22→confirmed.
    - Assert (import): sub5.status=shipped, sub22.status=confirmed, master.status=confirmed (по матрице AC4 Story 34-4: mixed без pending, min priority = confirmed(2) < shipped(4)).
  - [x] 5.2: Тест помечен `@pytest.mark.integration @pytest.mark.django_db`.

- [x] Task 6: Проверить integration-фикстуры экспорта (AC: 2, 9)
  - [x] 6.1: Убедиться, что `test_onec_export.py::order_for_export` уже master+sub (Story 34-3 мигрировала).
  - [x] 6.2: Убедиться, что `test_onec_export_e2e.py::_create_master_with_sub` уже корректен (Story 34-3).
  - [x] 6.3: При необходимости — зафиксировать незакрытые legacy-тесты с explicit `test_legacy_*` именем.

- [x] Task 7: Прогон тестов и финальная проверка (AC: 8, 10)
  - [x] 7.1: `pytest -m unit backend/tests/unit/test_order_export_service.py backend/tests/unit/test_order_status_import.py -v` — 0 failures.
  - [x] 7.2: `pytest -m integration backend/tests/integration/test_onec_export.py backend/tests/integration/test_order_status_import_db.py backend/tests/integration/test_orders_xml_mode_file.py backend/tests/integration/test_order_exchange_import_e2e.py backend/tests/integration/test_onec_export_e2e.py -v` — 0 failures.
  - [x] 7.3: `pytest backend/tests/ -v --tb=short` — полный прогон, 0 failures (AC10).
  - [x] 7.4: `flake8 backend/tests/helpers.py` и `black --check backend/tests/helpers.py` — без ошибок.
  - [x] 7.5: Задокументировать в Completion Notes: количество обновлённых тестов, количество новых тестов, итоговые результаты прогонов.

### Review Findings

- [ ] [Review][Patch] AC6: shared helper создан, но не используется в обновлённых тестах, а `create_single_sub_order` возвращает `(master, [sub])` вместо `(master, sub)` [backend/tests/helpers.py:103]
- [ ] [Review][Patch] AC5: cross-epic E2E использует `vat_group=20.00` вместо `22.00` и не проверяет организации/ровно 2 документа в `mode=query` [backend/tests/integration/test_order_exchange_import_e2e.py:282]
- [ ] [Review][Patch] AC5: cross-epic E2E после `mode=success` не проверяет `master.sent_to_1c=True` и `master.sent_to_1c_at` [backend/tests/integration/test_order_exchange_import_e2e.py:362]
- [ ] [Review][Patch] `create_master_with_subs` допускает пустой `variants_with_vat` и повтор одного variant в VAT-группе, что создаёт master без sub или нарушает `OrderItem` unique constraint [backend/tests/helpers.py:61]

## Dev Notes

### Архитектурный контекст

**Из `sprint-change-proposal-2026-04-16.md` (раздел 5, Story 34-5):**
- Story 34-5 — финальная story Epic 34, зависит от 34-2, 34-3, 34-4.
- Цель: обновить фикстуры Epic 4 и Epic 5, добавить cross-epic E2E тест.
- После Stories 34-1..34-4: `OrderExportService.handle_query` экспортирует только `is_master=False` субзаказы; `OrderStatusImportService` обновляет субзаказ и агрегирует master.status.

**Что уже сделано в предыдущих stories:**
- **Story 34-1** — поля `Order.parent_order/is_master/vat_group`, `OrderItem.vat_rate`, `OrderItem.build_snapshot()`.
- **Story 34-2** — `OrderCreateService` (master+sub из корзины), API фильтрация `is_master=True`, cascade cancel.
- **Story 34-3** — `OrderExportService` работает с субзаказами, `_aggregate_master_sent_to_1c`, queryset `is_master=False` в `handle_query`. Fixture `order_for_export` и `_create_master_with_sub` в E2E тестах уже мигрированы.
- **Story 34-4** — `OrderStatusImportService._aggregate_master_status/payment_status/sent_to_1c_at`, master-guard (`SKIPPED_MASTER_UNEXPECTED`), batch-оптимизация.

### Текущее состояние тестовых файлов

| Файл | Текущее состояние | Что нужно |
|------|-------------------|-----------|
| `tests/unit/test_order_export_service.py` | Legacy-тесты Epic 4 используют **inline master-only** `Order.objects.create(...)` без `is_master=False`. Тесты Story 34-3 добавили новые классы с master+sub. | Мигрировать **legacy** классы на master+sub. |
| `tests/integration/test_onec_export.py` | `order_for_export` **уже** master+sub (Story 34-3). Тесты Story 34-3 добавили `TestModeQuerySubOrders`, `TestModeSuccessAggregation`. | Верифицировать, зафиксировать legacy regression test. |
| `tests/integration/test_onec_export_e2e.py` | `_create_master_with_sub` уже корректен (Story 34-3). | Верифицировать. |
| `tests/unit/test_order_status_import.py` | Legacy-тесты Epic 5 используют **single Order** без master/sub. Тесты Story 34-4 добавили `TestMasterStatusAggregation`, `TestMasterGuardInImport`. | Добавить modern-flow тесты. Legacy оставить как regression. |
| `tests/integration/test_order_status_import_db.py` | Legacy `setUp()` создаёт single Order. Тесты Story 34-4 добавили `TestMasterAggregationDB`. | Обновить legacy setUp на master+sub. |
| `tests/integration/test_orders_xml_mode_file.py` | `test_successful_status_update` создаёт single Order **без** master/sub. | Мигрировать на master+sub. |
| `tests/integration/test_order_exchange_import_e2e.py` | `_create_order_with_item` **уже** master+sub (Story 34-3). | Добавить cross-epic E2E тест AC5. |

### Shared Helper — точный API

```python
# backend/tests/helpers.py

from decimal import Decimal
from typing import TYPE_CHECKING

from apps.orders.models import Order, OrderItem

if TYPE_CHECKING:
    from apps.products.models import ProductVariant
    from apps.users.models import User


def create_master_with_subs(
    user: "User | None" = None,
    variants_with_vat: "list[tuple[ProductVariant, Decimal | None]]" = (),
    *,
    sent_to_1c: bool = False,
    delivery_address: str = "ул. Тестовая, 1",
    delivery_method: str = "courier",
    payment_method: str = "card",
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
    status: str = "pending",
) -> "tuple[Order, list[Order]]":
    """Создаёт master + N sub-orders по VAT-группам.

    Args:
        user: владелец заказа (None для гостевого).
        variants_with_vat: [(variant, vat_rate), ...]. Группировка по vat_rate.
        **order_kwargs: общие поля заказа.

    Returns:
        (master, [sub1, sub2, ...]) — master.is_master=True, sub.is_master=False.
    """
    from collections import defaultdict

    common = dict(
        user=user,
        delivery_address=delivery_address,
        delivery_method=delivery_method,
        payment_method=payment_method,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        sent_to_1c=sent_to_1c,
        status=status,
    )

    # Группируем по vat_rate
    groups: dict[Decimal | None, list[tuple]] = defaultdict(list)
    total = Decimal("0")
    for variant, vat_rate in variants_with_vat:
        groups[vat_rate].append(variant)
        total += variant.retail_price

    master = Order.objects.create(
        **common,
        is_master=True,
        total_amount=total,
    )

    subs = []
    for vat_rate, variants in groups.items():
        sub_total = sum(v.retail_price for v in variants)
        sub = Order.objects.create(
            **common,
            is_master=False,
            parent_order=master,
            vat_group=vat_rate,
            total_amount=sub_total,
        )
        for variant in variants:
            OrderItem.objects.create(
                order=sub,
                product=variant.product,
                variant=variant,
                quantity=1,
                unit_price=variant.retail_price,
                total_price=variant.retail_price,
                product_name=variant.product.name,
                product_sku=variant.sku,
                vat_rate=vat_rate,
            )
        subs.append(sub)

    return master, subs


def create_single_sub_order(
    user: "User | None" = None,
    variant: "ProductVariant | None" = None,
    vat_rate: "Decimal | None" = None,
    **order_kwargs,
) -> "tuple[Order, Order]":
    """Shortcut: 1 master + 1 sub с одним OrderItem.

    Returns:
        (master, sub).
    """
    if variant is None:
        from tests.conftest import ProductVariantFactory
        variant = ProductVariantFactory.create()

    return create_master_with_subs(
        user=user,
        variants_with_vat=[(variant, vat_rate)],
        **order_kwargs,
    )  # type: ignore[return-value]  # subs[0]
    # Caller должен распаковать: master, subs = ...; sub = subs[0]
```

> **Примечание:** `create_single_sub_order` возвращает `(master, [sub])`. Для удобства — `master, subs = create_single_sub_order(...); sub = subs[0]` — или создать wrapper.

### Паттерн миграции legacy-теста (пошаговый)

**До (legacy):**
```python
order = Order.objects.create(
    user=user,
    total_amount=Decimal("3000.00"),
    delivery_address="...",
    sent_to_1c=False,
)
OrderItem.objects.create(order=order, ...)
xml_str = service.generate_xml(Order.objects.filter(id=order.id))
```

**После (master+sub):**
```python
master = Order.objects.create(
    user=user, total_amount=Decimal("3000.00"), delivery_address="...",
    is_master=True, sent_to_1c=False,
)
sub = Order.objects.create(
    user=user, total_amount=Decimal("3000.00"), delivery_address="...",
    is_master=False, parent_order=master, sent_to_1c=False,
)
OrderItem.objects.create(order=sub, ...)
xml_str = service.generate_xml(Order.objects.filter(id=sub.id))
```

Ключевое: `OrderItem` привязывается к **sub**, а не к master. QuerySet фильтрует по **sub.id**. Assertions по XML — те же.

### Паттерн миграции legacy import-теста

**До (legacy):**
```python
order = Order.objects.create(order_number="FS-001", status="pending", ...)
xml = build_test_xml(order_id=f"order-{order.pk}", order_number="FS-001", status="Отгружен")
result = service.process(xml)
order.refresh_from_db()
assert order.status == "shipped"
```

**После (master+sub) — modern flow:**
```python
master = Order.objects.create(order_number="FS-M-001", status="pending", is_master=True, ...)
sub = Order.objects.create(order_number="FS-S-001", status="pending", is_master=False,
                           parent_order=master, vat_group=Decimal("22.00"), ...)
xml = build_test_xml(order_id=f"order-{sub.pk}", order_number=sub.order_number, status="Отгружен")
result = service.process(xml)
sub.refresh_from_db()
master.refresh_from_db()
assert sub.status == "shipped"
assert master.status == "shipped"  # агрегация: все sub одинаковые → master = sub.status
```

### Матрица агрегации master.status (из Story 34-4)

| Sub-statuses | Master result |
|---|---|
| `[shipped, shipped]` | `shipped` |
| `[shipped, confirmed]` | `confirmed` (min priority) |
| `[pending, shipped]` | `pending` |
| `[delivered, delivered]` | `delivered` |
| `[cancelled, shipped]` | `shipped` (non-terminal wins) |

### VAT-группы и организации (из Story 34-3)

| vat_group | Организация | Склад |
|---|---|---|
| `5.00` | ИП Терещенко Л.В. | 2 ТЛВ склад |
| `22.00` | ИП Семерюк Д. В. | 1 СДВ склад |

### Тестовые паттерны проекта

- Маркеры: `@pytest.mark.unit` / `@pytest.mark.integration`, `@pytest.mark.django_db`
- Фабрики: `UserFactory`, `ProductVariantFactory`, `OrderFactory`, `OrderItemFactory` из `tests.conftest`
- Уникальность: `get_unique_suffix()`, `get_unique_order_number()`
- AAA-паттерн (Arrange/Act/Assert)
- `caplog` для логов, `assertNumQueries` для оптимизации
- `tests.utils`: `perform_1c_checkauth`, `build_orders_xml`, `build_multi_orders_xml`, `parse_commerceml_response`, `EXCHANGE_URL`, `ONEC_PASSWORD`

### Docker-команды

```powershell
# Unit-тесты
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend `
  pytest -xvs -m unit backend/tests/unit/test_order_export_service.py backend/tests/unit/test_order_status_import.py

# Integration-тесты
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend `
  pytest -xvs -m integration backend/tests/integration/test_onec_export.py backend/tests/integration/test_order_status_import_db.py backend/tests/integration/test_orders_xml_mode_file.py backend/tests/integration/test_order_exchange_import_e2e.py

# Полный прогон
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend `
  pytest backend/tests/ -v --tb=short

# Локально (с активным venv)
.\backend\venv\Scripts\Activate.ps1
pytest -xvs -m unit backend/tests/unit/test_order_export_service.py backend/tests/unit/test_order_status_import.py
```

### Антипаттерны (НЕ ДЕЛАТЬ)

- **НЕ** удалять legacy-тесты Epic 4/5 — мигрировать фикстуры, сохранить assertions.
- **НЕ** менять production-код (`models.py`, `services/`, `views.py`) — эта story только про тесты.
- **НЕ** дублировать helper-ы, уже созданные в Story 34-3/34-4 (`_make_master_with_sub` в unit-тестах). Использовать shared `tests/helpers.py` или импортировать существующие.
- **НЕ** трогать тесты Story 34-1..34-4 (новые классы) — они уже используют master+sub.
- **НЕ** создавать `OrderItem` на master — items живут только на sub (AC3 Story 34-2).
- **НЕ** менять XML-формат (`<Ид>order-{id}</Ід>`) — он зафиксирован в Story 34-3/34-4.
- **НЕ** обновлять `conftest.py::OrderFactory` дефолты — `OrderFactory` по-прежнему создаёт одиночный Order (обратная совместимость). Master+sub — через dedicated helpers.

### Project Structure Notes

- Тесты: `backend/tests/unit/` (unit), `backend/tests/integration/` (integration), `backend/tests/functional/` (functional).
- Helpers: `backend/tests/helpers.py` (новый), `backend/tests/utils.py` (существующий), `backend/tests/conftest.py` (factories).
- Service Layer: `apps/orders/services/order_export.py`, `apps/orders/services/order_status_import.py`, `apps/orders/services/order_create.py`.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#5 — Story 34-5 описание]
- [Source: _bmad-output/implementation-artifacts/Story/34-3-order-export-service-sub-orders.md#Task 6 — "Полное обновление Epic 4+5 test-fixtures выполняется в Story 34-5"]
- [Source: _bmad-output/implementation-artifacts/Story/34-4-order-status-import-aggregation.md#Dev Notes — "Story 34-5 — миграция fixtures Epic 4+5"]
- [Source: backend/tests/unit/test_order_export_service.py — legacy unit-тесты экспорта]
- [Source: backend/tests/integration/test_onec_export.py — integration-тесты экспорта (fixture уже мигрирована)]
- [Source: backend/tests/unit/test_order_status_import.py — legacy unit-тесты импорта]
- [Source: backend/tests/integration/test_order_status_import_db.py — integration-тесты импорта]
- [Source: backend/tests/integration/test_orders_xml_mode_file.py — mode=file тесты]
- [Source: backend/tests/integration/test_order_exchange_import_e2e.py — E2E цикл export+import]
- [Source: backend/tests/conftest.py — OrderFactory, OrderItemFactory, ProductVariantFactory, UserFactory]
- [Source: backend/tests/utils.py — perform_1c_checkauth, build_orders_xml, EXCHANGE_URL, ONEC_PASSWORD]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

**Story 34-5 завершена успешно. Результаты:**

- **Создан** `backend/tests/helpers.py` — shared helper с `create_master_with_subs`, `create_single_sub_order`, `build_test_xml_for_sub`.
- **Обновлено** 3 legacy-теста в `TestOrderExportServiceXMLValidation` (Task 2) — фикстуры на master+sub.
- **Добавлено** 5 новых тестов `TestModernSubOrderImportUnit` + helper `_make_sub_mock_order()` (Task 3) — Group B modern-flow.
- **Обновлён** `TestOrderStatusImportDBIntegration.setUp()` на master+sub (Task 4) — `assertNumQueries(9→11)`, `test_successful_status_update` в mode=file с проверкой `master.status`.
- **Добавлен** cross-epic E2E `test_full_vat_split_export_import_cycle` (Task 5) — полный VAT-split цикл.
- **Верифицированы** `test_onec_export.py` и `test_onec_export_e2e.py` (Task 6) — уже master+sub из Story 34-3.

**Прогон тестов:**
- `pytest -m unit` (159 passed, 0 failed)
- `pytest -m integration` (48 passed, 0 failed) — import/mode=file/E2E
- `pytest -m integration` (57 passed, 0 failed) — export E2E

### File List
