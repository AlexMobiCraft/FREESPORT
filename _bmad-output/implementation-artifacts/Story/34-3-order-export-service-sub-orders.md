# Story 34.3: OrderExportService — работа с субзаказами (один XML-документ на VAT-группу)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **менеджер 1С**,
I want **получать из FREESPORT отдельный XML-документ на каждую VAT-группу заказа (по одному на Склад А / Склад Б)**,
so that **в 1С:УТ 11 каждый документ уходит в свою организацию/склад с однородной ставкой НДС, без ручной обработки смешанных заказов**.

> Техническая формулировка: рефакторинг `OrderExportService` и `ICExchangeView.handle_query/handle_success` так, чтобы экспорт работал с **дочерними субзаказами** (`is_master=False`, созданными в Story 34-2). Один `sub_order` → один `<Контейнер><Документ>` в XML. Мастер-заказ в XML не попадает, но получает агрегированный `sent_to_1c=True` после подтверждения всех субзаказов.

## Acceptance Criteria

1. **AC1 (queryset субзаказов):** `ICExchangeView.handle_query` выбирает для экспорта **только субзаказы**: `Order.objects.filter(sent_to_1c=False, export_skipped=False, created_at__lte=query_time, is_master=False, parent_order__isnull=False)` с `select_related("user", "parent_order")` и `prefetch_related("items__variant")`. Мастер-заказы (`is_master=True`) в XML **не попадают**.
2. **AC2 (один документ = один субзаказ):** Для каждого `sub_order` `OrderExportService.generate_xml_streaming()` генерирует ровно один `<Контейнер><Документ>`. В `<Ид>` документа — `order-{sub_order.id}` (PK субзаказа, используется в Story 34-4 для обратного маппинга статусов). В `<Номер>` — `sub_order.order_number`.
3. **AC3 (VAT-группа — авторитетный источник):** `_get_order_vat_rate(sub_order)` в первую очередь возвращает `Decimal(sub_order.vat_group)`, если оно не `None`. Только при `vat_group is None` fallback работает по старой цепочке: `OrderItem.vat_rate` snapshot → `variant.vat_rate` → `warehouse_name` rule → `DEFAULT_VAT_RATE`.
4. **AC4 (Организация/Склад детерминированы):** `<Организация>` и `<Склад>` определяются по `sub_order.vat_group` через существующие `ONEC_EXCHANGE.ORGANIZATION_BY_VAT` / `WAREHOUSE_RULES`:
   - `vat_group=5.00` → `ИП Терещенко Л.В.` / `2 ТЛВ склад`
   - `vat_group=22.00` → `ИП Семерюк Д. В.` / `1 СДВ склад`
   - Смешанных организаций в одном `<Документ>` быть не может.
5. **AC5 (НДС строк — snapshot first):** В `_create_products_element` ставка НДС строки берётся в приоритете `OrderItem.vat_rate` (snapshot, Story 34-1) → `variant.vat_rate` → `_get_order_vat_rate(sub_order)`. Это гарантирует корректный XML даже если `variant.vat_rate` изменился после оформления заказа.
6. **AC6 (контрагент и адрес — из самого субзаказа):** `_create_counterparties_element` использует `sub_order.user`, `sub_order.customer_name/email/phone`, `sub_order.delivery_address` **без обращения к `parent_order`** — эти поля уже скопированы на субзаказ при создании (Story 34-2, AC6). Поведение для B2B (с ИНН) и гостевых заказов сохраняется.
7. **AC7 (сумма документа):** `<Сумма>` документа равна `sub_order.total_amount` (сумма позиций VAT-группы, **без `delivery_cost`**). `delivery_cost` не дублируется в XML, так как живёт только на мастере (Story 34-2, AC4).
8. **AC8 (legacy-обработка `vat_group=None`):** Субзаказ с `vat_group is None` (позиции без `variant.vat_rate`) экспортируется как единый документ: VAT определяется по fallback-цепочке AC3, организация/склад — по `DEFAULT_ORGANIZATION/DEFAULT_WAREHOUSE`. Логируется `logger.warning(f"Sub-order {sub.order_number}: vat_group is None, using defaults")`.
9. **AC9 (пометка `sent_to_1c` и агрегация мастера):** `handle_success` и `_mark_previous_query_as_sent` помечают **субзаказы** (`sent_to_1c=True, sent_to_1c_at=now`). После обновления субзаказов — для каждого уникального `master_id` из затронутых субзаказов: если **все** `master.sub_orders` имеют `sent_to_1c=True` → `master.sent_to_1c=True, master.sent_to_1c_at=now`. Всё — в одной `transaction.atomic()`.
10. **AC10 (fallback time-window в handle_success):** Fallback-ветка `handle_success` (когда cache потерял `exported_ids`) обновляет только `is_master=False, parent_order__isnull=False` субзаказы в окне `created_at <= last_query_time`. Мастера напрямую в fallback не обновляются — только через агрегацию.
11. **AC11 (сигнал `orders_bulk_updated`):** Сигнал эмитится с `order_ids` субзаказов (как раньше) и дополнительно `master_order_ids` — список master PK, агрегированных на этом же шаге. Обратная совместимость текущей подписи сигнала сохраняется (новое поле — опциональное, `kwargs` не ломают существующие обработчики).
12. **AC12 (пропуск по-прежнему работает):** `_validate_order(sub_order)` пропускает субзаказы без `items` и добавляет их в `skipped_ids` → `export_skipped=True`. Пропуск одного субзаказа **не влияет** на sibling-субзаказы того же мастера (они экспортируются независимо).
13. **AC13 (`is_master=True` исключены защитно):** Даже если каким-то путём `Order.objects.filter(sent_to_1c=False, is_master=True, parent_order__isnull=True)` окажется в queryset передано в сервис (прямой вызов из shell/management command), `generate_xml_streaming` пропускает такие записи с `logger.warning(f"Order {order.order_number}: is_master=True, export skipped — expected sub-orders only")` и добавляет PK в `skipped_ids`. Это защита от регресса и неправильного вызова.
14. **AC14 (обратная совместимость настроек):** Все существующие ключи `ONEC_EXCHANGE` (`COMMERCEML_VERSION`, `DEFAULT_UNIT`, `ORDER_DEFAULTS`, `DEFAULT_AGREEMENT`, `PRICE_TYPE_BY_ROLE`, `ORGANIZATION_BY_VAT`, `WAREHOUSE_RULES`, `DEFAULT_VAT_RATE`, `DEFAULT_ORGANIZATION`, `DEFAULT_WAREHOUSE`) читаются без изменений. Новых ключей настроек story не вводит.
15. **AC15 (purely тесты subtree):** Новые unit-тесты покрывают: AC3 (vat_group priority), AC4 (org/warehouse по vat_group), AC5 (snapshot priority), AC8 (vat_group=None fallback), AC13 (master-защита). Новые integration-тесты покрывают: AC1+AC2 (queryset + N документов), AC9 (агрегация мастера), AC10 (fallback time-window), AC12 (skip одного субзаказа не ломает siblings). Все тесты размечены `@pytest.mark.unit` или `@pytest.mark.integration` (+ `@pytest.mark.django_db`).

## Tasks / Subtasks

- [ ] Task 1: Рефакторинг `OrderExportService` для работы с субзаказами (AC: 2, 3, 4, 5, 6, 7, 8, 13)
  - [ ] 1.1: В `_get_order_vat_rate(self, order)` добавить первым условием: `if order.vat_group is not None: return Decimal(str(order.vat_group))`. Остальная логика (item.variant.vat_rate → warehouse → default) остаётся как fallback для `vat_group is None`.
  - [ ] 1.2: В `_create_products_element`, в цикле по `order.items.all()`, перед вызовом `_get_variant_vat_rate` добавить приоритет `OrderItem.vat_rate` snapshot: `item_vat_rate = Decimal(str(item.vat_rate)) if item.vat_rate is not None else self._get_variant_vat_rate(item.variant, order_vat_rate)`.
  - [ ] 1.3: В `generate_xml_streaming`, внутри цикла `for order in orders.iterator(...)`, добавить defensive guard: если `order.is_master` is True — залогировать warning, добавить PK в `skipped_ids` (если передан), `continue`. Это защита AC13 от некорректного вызова сервиса.
  - [ ] 1.4: Docstring `generate_xml` / `generate_xml_streaming` обновить: явно указать, что входной QuerySet должен содержать **субзаказы** (`is_master=False, parent_order__isnull=False`). Упомянуть, что `vat_group` субзаказа — авторитетный источник для организации/склада.
  - [ ] 1.5: Комментарии в `_create_document_element` (в блоке определения `org_name`/`warehouse_name`) обновить: "sub_order.vat_group → ORGANIZATION_BY_VAT, однородная группа НДС".
  - [ ] 1.6: Метод `_create_counterparties_element` — **не менять**: `order.user` и `order.customer_*` на субзаказе уже корректны (Story 34-2, AC6). Добавить только inline-комментарий: "Customer fields скопированы с мастера в Story 34-2, прямое использование безопасно.".

- [ ] Task 2: Обновить `ICExchangeView.handle_query` queryset (AC: 1, 12)
  - [ ] 2.1: В `backend/apps/integrations/onec_exchange/views.py:449-457` изменить queryset:
    ```python
    orders = (
        Order.objects.filter(
            sent_to_1c=False,
            export_skipped=False,
            created_at__lte=query_time,
            is_master=False,
            parent_order__isnull=False,
        )
        .select_related("user", "parent_order")
        .prefetch_related("items__variant")
    )
    ```
  - [ ] 2.2: Обновить комментарий над queryset: "Экспортируем только субзаказы (is_master=False). Мастер-заказы — агрегирующие, в 1С не попадают.".
  - [ ] 2.3: Проверить, что `skipped_ids` по-прежнему помечается через `Order.objects.filter(pk__in=skipped_ids).update(export_skipped=True)` — это работает для субзаказов без изменений.

- [ ] Task 3: Агрегация `sent_to_1c` мастера после пометки субзаказов (AC: 9, 10, 11)
  - [ ] 3.1: В `handle_success` (успешная ветка, где `exported_ids` есть в cache) **после** `Order.objects.filter(pk__in=exported_ids, sent_to_1c=False).update(...)` и **внутри той же** `transaction.atomic()` добавить агрегацию:
    ```python
    # Агрегация sent_to_1c мастеров: если все субзаказы мастера помечены — пометить мастер.
    master_ids = set(
        Order.objects.filter(pk__in=exported_ids, parent_order__isnull=False)
        .values_list("parent_order_id", flat=True)
    )
    aggregated_master_ids: list[int] = []
    for master_id in master_ids:
        remaining = Order.objects.filter(
            parent_order_id=master_id, sent_to_1c=False
        ).exists()
        if not remaining:
            Order.objects.filter(pk=master_id, sent_to_1c=False).update(
                sent_to_1c=True, sent_to_1c_at=now, updated_at=now,
            )
            aggregated_master_ids.append(master_id)
    ```
  - [ ] 3.2: В `_mark_previous_query_as_sent` повторить ту же агрегацию после основного `update(...)`. Использовать один и тот же private helper `_aggregate_master_sent_to_1c(sub_ids, now)` в том же `views.py` (DRY).
  - [ ] 3.3: Для fallback time-window ветки `handle_success` (когда `exported_ids is None`): в `Order.objects.filter(...).update(...)` добавить `is_master=False, parent_order__isnull=False` (AC10), собрать ID субзаказов в окне через `values_list` **до** update, затем вызвать тот же `_aggregate_master_sent_to_1c`.
  - [ ] 3.4: Сигнал `orders_bulk_updated` — передавать `order_ids=<sub_ids>` (как раньше) и добавить keyword-аргумент `master_order_ids=<aggregated_master_ids>`. Не ломать подпись: проверить, что ни один существующий обработчик в `apps/orders/signals.py` / `apps/orders/tasks.py` не полагается на точный список `kwargs`.

- [ ] Task 4: Unit-тесты `OrderExportService` (AC: 3, 4, 5, 8, 13, 15)
  - [ ] 4.1: В `backend/tests/unit/test_order_export_service.py` добавить helper `_make_master_with_sub(vat_group, variant_vat_rate=..., item_vat_rate=...)`, возвращающий пару `(master, sub_order)` с одним `OrderItem`.
  - [ ] 4.2: `TestGetOrderVatRate::test_returns_vat_group_when_set` — `sub_order.vat_group = Decimal("5.00")`, `item.variant.vat_rate=22`, `item.vat_rate=22`. `_get_order_vat_rate(sub_order) == Decimal("5.00")` (vat_group выигрывает).
  - [ ] 4.3: `TestGetOrderVatRate::test_falls_back_to_item_when_vat_group_none` — `sub_order.vat_group=None`, `item.variant.vat_rate=22`. Результат `Decimal("22")`.
  - [ ] 4.4: `TestOrderExportServiceSubOrderDocument::test_sub_order_generates_single_document` — создать master + 1 sub (vat_group=22, 1 OrderItem). `generate_xml(Order.objects.filter(id=sub.id))` → ровно 1 `<Контейнер>/<Документ>`, `<Ид>` = `order-{sub.id}`, `<Номер>` = `sub.order_number`, `<Организация>` = `ИП Семерюк Д. В.`, `<Склад>` = `1 СДВ склад`, `<Сумма>` = `sub.total_amount` (без delivery).
  - [ ] 4.5: `TestOrderExportServiceSubOrderDocument::test_multi_vat_master_produces_two_documents` — создать master + sub5 (vat_group=5) + sub22 (vat_group=22). `generate_xml(Order.objects.filter(parent_order=master))` → 2 документа, у одного `<Организация>ИП Терещенко Л.В.</Организация>`, у другого `<Организация>ИП Семерюк Д. В.</Организация>`.
  - [ ] 4.6: `TestOrderExportServiceSubOrderDocument::test_item_vat_rate_snapshot_has_priority` — `sub.vat_group=22`, `item.vat_rate=5` (снимок старой ставки), `item.variant.vat_rate=22`. В `<Налоги><Ставка>` должно быть `5`, а `<Организация>` — `ИП Семерюк Д. В.` (определяется по `vat_group`, независимо от item.vat_rate). Это защищает AC5.
  - [ ] 4.7: `TestOrderExportServiceSubOrderDocument::test_vat_group_none_falls_back_to_defaults` — `sub.vat_group=None`, `item.variant.vat_rate=None`, `settings.ONEC_EXCHANGE["DEFAULT_VAT_RATE"]=22`, `DEFAULT_ORGANIZATION="ИП Семерюк Д. В."`. Документ успешно генерируется, `<Организация>` = дефолтная, логируется warning `"vat_group is None, using defaults"`.
  - [ ] 4.8: `TestOrderExportServiceMasterGuard::test_master_order_is_skipped_with_warning` — передать QuerySet с `is_master=True` orders. `generate_xml_streaming` добавляет PK в `skipped_ids`, в логах — warning `"is_master=True, export skipped"`, в XML этих документов нет.
  - [ ] 4.9: Все тесты файла помечены `@pytest.mark.unit` и `@pytest.mark.django_db`.

- [ ] Task 5: Integration-тесты `handle_query` / `handle_success` (AC: 1, 9, 10, 11, 12, 15)
  - [ ] 5.1: В `backend/tests/integration/test_onec_export.py` добавить fixture `master_with_two_subs(customer_user, product_variant, vat5_variant)` — создаёт 1 master + 2 sub (vat_group=5, vat_group=22), по 1 OrderItem в каждом sub, `sent_to_1c=False`.
  - [ ] 5.2: `TestModeQuerySubOrders::test_query_returns_only_sub_orders` — при `master_with_two_subs` в БД: `GET mode=query` → XML содержит 2 `<Документ>` (по одному на sub), `<Ид>` = `order-{sub.id}` для каждого. Мастер-заказа в XML нет.
  - [ ] 5.3: `TestModeQuerySubOrders::test_query_multi_vat_produces_two_organizations` — в 2 документах `<Организация>` различаются: один `ИП Терещенко Л.В.`, второй `ИП Семерюк Д. В.`.
  - [ ] 5.4: `TestModeQuerySubOrders::test_query_excludes_master_orders` — создать мастер с `sent_to_1c=False, is_master=True, parent_order=None`, **без** `sub_orders`. `GET mode=query` → мастер не попадает в XML.
  - [ ] 5.5: `TestModeSuccessAggregation::test_success_aggregates_master_when_all_subs_sent` — `master_with_two_subs` → `mode=query` → `mode=success` → оба sub_orders имеют `sent_to_1c=True`, **и** `master.sent_to_1c=True`.
  - [ ] 5.6: `TestModeSuccessAggregation::test_success_does_not_aggregate_master_when_sub_pending` — создать master + 2 sub, но один из sub был `sent_to_1c=True` до query (чтобы второй прошёл как "последний"). После `mode=success` — `master.sent_to_1c=True` только если оба sub помечены; если один по какой-то причине остался `sent_to_1c=False` — master не должен помечаться.
  - [ ] 5.7: `TestModeSuccessAggregation::test_success_does_not_mark_sibling_in_other_master` — два независимых мастера (master_A, master_B), у каждого свой sub. `mode=query/success` только для master_A субзаказа → master_A.sent_to_1c=True, master_B.sent_to_1c=False.
  - [ ] 5.8: `TestModeSuccessFallback::test_fallback_updates_only_sub_orders` — очистить `cache` перед `mode=success`, проверить что fallback time-window обновляет только `is_master=False` субзаказы, а `is_master=True` мастера напрямую не трогаются, но агрегируются через helper.
  - [ ] 5.9: `TestModeQuerySkippedSibling::test_skipped_sub_does_not_affect_siblings` — sub_a (vat_group=5, без items), sub_b (vat_group=22, с items). `mode=query` → sub_a помечен `export_skipped=True`, sub_b в XML, sub_a нет. После `mode=success` — master не агрегируется, потому что sub_a всё ещё `sent_to_1c=False` (expected behavior: skipped orders не считаются отправленными; фиксируем это в тесте).
  - [ ] 5.10: Все тесты помечены `@pytest.mark.integration` и `@pytest.mark.django_db`.

- [ ] Task 6: Обновление существующих тестов Epic 4 (AC: 15) — **scoped as minimal compatibility fix**
  - [ ] 6.1: В `test_order_export_service.py` helper `_make_order_with_variant(variant, ...)` оставить для legacy unit-тестов (cover только pure XML-структура), но новые тесты использовать `_make_master_with_sub`.
  - [ ] 6.2: В `test_onec_export.py::order_for_export` fixture оставить старую структуру (один Order без master/sub) как **legacy regression**: при `is_master=True, parent_order=None` такой заказ **не попадает** в новый queryset. Добавить тест `test_legacy_master_without_sub_orders_is_not_exported` подтверждающий новое поведение. **Полное обновление Epic 4+5 test-fixtures** выполняется в Story 34-5.
  - [ ] 6.3: Отметить в story Completion Notes: `test_onec_export.py::TestModeQuery::test_mode_query_returns_xml` и другие тесты, опирающиеся на legacy master-only fixture, могут начать возвращать пустой XML после этой story — это ожидаемо и будет закрыто в Story 34-5 (миграция fixtures на master+sub).

- [ ] Task 7: Линтинг и финальная проверка (AC: все)
  - [ ] 7.1: Прогнать `pytest -m unit backend/tests/unit/test_order_export_service.py` — новые тесты зелёные.
  - [ ] 7.2: Прогнать `pytest -m integration backend/tests/integration/test_onec_export.py` — новые тесты зелёные; отметить в Completion Notes, какие из legacy тестов Epic 4 упадут и почему (перенос в Story 34-5).
  - [ ] 7.3: `flake8 backend/apps/orders/services/order_export.py backend/apps/integrations/onec_exchange/views.py` без ошибок.
  - [ ] 7.4: `black --check` на затронутых файлах без отличий.

## Dev Notes

### Архитектурный контекст (зачем эта story)

**Из `sprint-change-proposal-2026-04-16.md` (раздел 4.5):**
- Проблема Epic 4: `_get_order_vat_rate()` брал НДС первого товара, для смешанных заказов (5% + 22%) экспорт был некорректен.
- Решение после Story 34-2: заказ уже **разбит на master + N sub** по VAT-группам. Этой story остаётся только научить `OrderExportService` работать с субзаказами.

**Что уже сделано:**
- Story 34-1: `Order.parent_order`, `Order.is_master`, `Order.vat_group`, `OrderItem.vat_rate`, миграция `0012_add_vat_split_fields`.
- Story 34-2: `OrderCreateService` создаёт 1 master + N sub при оформлении; client API фильтрует `is_master=True`.
- **Эта story (34-3):** рефакторинг ExportService + queryset в `handle_query` + агрегация `sent_to_1c` на мастер в `handle_success`.

**Что НЕ в scope:**
- Story 34-4: `OrderStatusImportService` — обратная агрегация статусов из 1С на мастер.
- Story 34-5: миграция фикстур Epic 4+5 под новую структуру + новые test-кейсы.

### Точный код для ключевых изменений

**1. `_get_order_vat_rate` в `backend/apps/orders/services/order_export.py` (~строка 371):**

```python
def _get_order_vat_rate(self, order: "Order") -> Decimal:
    """
    Определяет ставку НДС заказа.
    Приоритет: order.vat_group (Story 34-2) → OrderItem.vat_rate (snapshot, Story 34-1)
             → variant.vat_rate → warehouse_name → DEFAULT_VAT_RATE.
    """
    if order.vat_group is not None:
        return Decimal(str(order.vat_group))

    exchange_cfg = getattr(settings, "ONEC_EXCHANGE", {})
    default_rate = Decimal(str(exchange_cfg.get("DEFAULT_VAT_RATE", 22)))
    for item in order.items.all():
        # Приоритет snapshot (Story 34-1)
        if item.vat_rate is not None:
            return Decimal(str(item.vat_rate))
        if not item.variant:
            continue
        if item.variant.vat_rate is not None:
            return Decimal(str(item.variant.vat_rate))
        warehouse_vat_rate = self._get_vat_rate_by_warehouse_name(item.variant.warehouse_name)
        if warehouse_vat_rate is not None:
            return warehouse_vat_rate
    return default_rate
```

**2. Snapshot priority в `_create_products_element` (~строка 338):**

```python
# Вместо текущего:
# item_vat_rate = self._get_variant_vat_rate(item.variant, order_vat_rate)
# Должно быть:
if item.vat_rate is not None:
    item_vat_rate = Decimal(str(item.vat_rate))
else:
    item_vat_rate = self._get_variant_vat_rate(item.variant, order_vat_rate)
```

**3. Master-guard в `generate_xml_streaming` (сразу после `if not self._validate_order(order): ...`):**

```python
for order in orders.iterator(chunk_size=100):
    if order.is_master:
        logger.warning(
            f"Order {order.order_number}: is_master=True, export skipped — "
            f"OrderExportService expects sub-orders only"
        )
        if skipped_ids is not None:
            skipped_ids.append(order.pk)
        continue
    if not self._validate_order(order):
        if skipped_ids is not None:
            skipped_ids.append(order.pk)
        continue
    # ... остальная логика без изменений
```

**4. Новый queryset в `handle_query` (`backend/apps/integrations/onec_exchange/views.py:449-457`):**

```python
orders = (
    Order.objects.filter(
        sent_to_1c=False,
        export_skipped=False,
        created_at__lte=query_time,
        is_master=False,
        parent_order__isnull=False,
    )
    .select_related("user", "parent_order")
    .prefetch_related("items__variant")
)
```

**5. Helper агрегации мастера (новый private метод в `ICExchangeView` или module-level):**

```python
def _aggregate_master_sent_to_1c(
    self, sub_ids: list[int] | None, now: datetime
) -> list[int]:
    """После пометки субзаказов — пометить мастеров, у которых ВСЕ sub_orders отправлены.

    Args:
        sub_ids: PK субзаказов, которые были только что помечены sent_to_1c=True.
        now: timestamp для sent_to_1c_at / updated_at.
    Returns:
        list master_id, которые были дополнительно помечены в рамках этой агрегации.
    """
    if not sub_ids:
        return []
    master_ids = set(
        Order.objects.filter(pk__in=sub_ids, parent_order__isnull=False)
        .values_list("parent_order_id", flat=True)
    )
    aggregated: list[int] = []
    for master_id in master_ids:
        has_pending = Order.objects.filter(
            parent_order_id=master_id, sent_to_1c=False
        ).exists()
        if not has_pending:
            updated = Order.objects.filter(
                pk=master_id, sent_to_1c=False, is_master=True
            ).update(sent_to_1c=True, sent_to_1c_at=now, updated_at=now)
            if updated > 0:
                aggregated.append(master_id)
    return aggregated
```

Вызвать этот helper **внутри той же** `transaction.atomic()` после основного `Order.objects.filter(pk__in=exported_ids).update(...)` в `handle_success` и в `_mark_previous_query_as_sent`.

### Ключевые файлы для изменения

| Файл | Действие |
|------|----------|
| `backend/apps/orders/services/order_export.py` | `_get_order_vat_rate` (vat_group priority), snapshot в `_create_products_element`, master-guard в `generate_xml_streaming`, docstring |
| `backend/apps/integrations/onec_exchange/views.py` | Queryset `handle_query` → `is_master=False`, `_aggregate_master_sent_to_1c` helper, вызовы в `handle_success` и `_mark_previous_query_as_sent`, сигнал `orders_bulk_updated` с `master_order_ids` |
| `backend/tests/unit/test_order_export_service.py` | Новый helper `_make_master_with_sub`, тесты AC3/AC4/AC5/AC8/AC13 |
| `backend/tests/integration/test_onec_export.py` | Fixture `master_with_two_subs`, `TestModeQuerySubOrders`, `TestModeSuccessAggregation`, `TestModeSuccessFallback`, `TestModeQuerySkippedSibling`, legacy-master тест |

### Паттерны и ограничения

**Atomicity (`transaction.atomic`):** Весь блок обновления sub_orders + агрегации master должен быть в одной транзакции, чтобы не возникло промежуточного состояния "sub_orders помечены, master ещё нет" при сбое.

**Order PK в `<Ид>`:** Story 34-4 будет парсить `order-{id}` из XML-ответа 1С для обратного маппинга на субзаказ. Поэтому `sub.id` обязателен (не order_number, который может потенциально меняться).

**Отсутствие data migration (из `sprint-change-proposal-2026-04-16.md`):**
- БД содержит только тестовые заказы → legacy master-only заказы (`is_master=True, sub_orders.count()==0`) в production можно игнорировать; они просто не попадут в экспорт.
- В тестах Epic 4 такие fixtures остаются как regression ("legacy не экспортируется") до полной миграции в Story 34-5.

**Settings `ONEC_EXCHANGE` не меняется:**
- `ORGANIZATION_BY_VAT`, `WAREHOUSE_RULES`, `DEFAULT_*` читаются как и раньше.
- Story 34-3 ПОЛНОСТЬЮ использует существующую конфигурацию.

### Паттерн тестов (соответствие проекту)

Из `backend/tests/conftest.py` и существующих unit-тестов:
- Маркеры: `@pytest.mark.unit` / `@pytest.mark.integration`, плюс `@pytest.mark.django_db`
- Фабрики: `UserFactory`, `ProductVariantFactory`, `get_unique_suffix()` из `tests.factories`
- AAA-паттерн (Arrange/Act/Assert)
- Использование `caplog` для проверки логов (`with caplog.at_level(logging.WARNING):`)
- Для `handle_query`/`handle_success` integration — использовать `authenticated_client` fixture из `test_onec_export.py`

### Docker-команды

```powershell
# Unit-тесты сервиса
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend `
  pytest -xvs -m unit backend/tests/unit/test_order_export_service.py

# Integration-тесты экспорта
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend `
  pytest -xvs -m integration backend/tests/integration/test_onec_export.py

# Локально (с активным venv)
.\backend\venv\Scripts\Activate.ps1
pytest -xvs -m unit backend/tests/unit/test_order_export_service.py
```

### Антипаттерны (НЕ ДЕЛАТЬ)

- **НЕ** менять структуру XML (CommerceML 3.1 уже утверждена).
- **НЕ** создавать `sub_order.customer_name` повторно — оно уже скопировано в Story 34-2 (`OrderCreateService`).
- **НЕ** трогать `OrderStatusImportService` — это Story 34-4.
- **НЕ** писать data migration для legacy заказов — по sprint-change-proposal тестовые заказы можно удалить.
- **НЕ** добавлять новые ключи в `ONEC_EXCHANGE` — используем существующие `ORGANIZATION_BY_VAT` / `WAREHOUSE_RULES`.
- **НЕ** включать `is_master=True` заказы в экспорт ни при каких обстоятельствах (кроме явного теста master-guard).
- **НЕ** дублировать `delivery_cost` в `<Сумма>` документов субзаказов — доставка живёт только на мастере.
- **НЕ** помечать master.sent_to_1c напрямую в основном `update(...)` — только через helper агрегации после обновления субов.
- **НЕ** ломать совместимость сигнала `orders_bulk_updated` (новое поле `master_order_ids` — только как дополнительный keyword).

### Project Structure Notes

- Структура соответствует unified project structure (Service Layer Pattern в `apps/orders/services/`).
- Views (`apps/integrations/onec_exchange/views.py`) тонкие — бизнес-логика генерации XML и агрегации мастера инкапсулирована в сервис/helper.
- Тесты: `backend/tests/unit/test_order_export_service.py` для сервиса, `backend/tests/integration/test_onec_export.py` для handle_query/handle_success end-to-end.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#4.5 OrderExportService — разбивка по VAT]
- [Source: _bmad-output/planning-artifacts/architecture.md#ADR-002 Стратегия интеграции с 1С]
- [Source: _bmad-output/implementation-artifacts/Story/34-1-order-model-vat-split-fields-migrations.md — поля vat_group, vat_rate]
- [Source: _bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md — структура master + sub_orders]
- [Source: _bmad-output/implementation-artifacts/Story/4-2-order-export-service-xml-generation.md — исходная CommerceML 3.1 реализация]
- [Source: _bmad-output/implementation-artifacts/Story/4-3-view-handlers-mode-query-and-mode-success.md — handle_query/handle_success оригинал]
- [Source: backend/apps/orders/services/order_export.py:371-414 — _get_order_vat_rate / _get_org_and_warehouse]
- [Source: backend/apps/orders/services/order_export.py:89-135 — generate_xml_streaming]
- [Source: backend/apps/integrations/onec_exchange/views.py:433-554 — handle_query]
- [Source: backend/apps/integrations/onec_exchange/views.py:556-647 — handle_success]
- [Source: backend/apps/integrations/onec_exchange/views.py:392-431 — _mark_previous_query_as_sent]
- [Source: backend/freesport/settings/base.py:306-325 — ONEC_EXCHANGE (WAREHOUSE_RULES, ORGANIZATION_BY_VAT, DEFAULT_*)]
- [Source: backend/apps/orders/models.py — Order.vat_group / parent_order / is_master, OrderItem.vat_rate]
- [Source: backend/apps/orders/services/order_create.py — OrderCreateService (Story 34-2), как создаются sub с customer_* полями]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Change |
|------|--------|
| 2026-04-19 | Story 34.3 создана в статусе ready-for-dev (bmad-create-story). Источник: sprint-change-proposal-2026-04-16.md (раздел 4.5). Контекст: Story 34-1 (поля), 34-2 (структура master+sub), 4-2/4-3 (исходный ExportService и handlers). |
