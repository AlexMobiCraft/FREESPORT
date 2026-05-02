---
title: "Order Numbering: Email, Permissions & Admin Fixes"
type: "bugfix"
created: "2026-05-02"
status: "done"
baseline_commit: "59bc681a7889d88c03cd9405f5a0041e9926df34"
context:
  - "backend/apps/orders/services/order_numbering.py"
  - "backend/apps/orders/signals.py"
  - "backend/apps/orders/tasks.py"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Реализация схемы нумерации заказов завершена (~90%), но AI-ревью выявило 7 дефектов: клиенты получают email по каждому субзаказу (а не только по master), письма содержат пустой список товаров, `POST /orders/` возвращает 400 вместо 401 для анонимов, `OrderNumberError` превращается в 500, Django Admin показывает 0 позиций для master-заказов, и отсутствует решение по legacy backfill.

**Approach:** Исправить все 7 follow-ups (RF-1…RF-7): guard `is_master` в signals, единый items-helper для email tasks, `IsAuthenticated` permission в views, перехват `OrderNumberError` в create path, items_count fix в admin, и data migration удаления тестовых legacy-заказов.

## Boundaries & Constraints

**Always:**

- Email-уведомления о заказе (customer + admin) ставятся в очередь ТОЛЬКО для `is_master=True`.
- Items для email/admin display: master → через `sub_orders__items`, прямые `order.items` как fallback (безопасность).
- `OrderNumberError` (и подклассы) перехватываются в create path и возвращаются как DRF `ValidationError`.
- `POST /api/orders/` требует аутентификации на уровне DRF permissions (не только в serializer): 401 для анонимов.
- `items_count` и `total_items_quantity` в admin корректно считают позиции для master-заказов через suborders.
- Data migration удаляет все существующие заказы и связанные записи (все текущие — тестовые данные, реальных заказов нет).

**Never:**

- Не изменять формат хранения `order_number`.
- Не добавлять email-рассылку по субзаказам.
- Не трогать `OrderNumberingService` core-логику без явного требования.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| --- | --- | --- | --- |
| Email на checkout | master + 2 suborders созданы | ровно 1 customer email + 1 admin email | нет дублей |
| Тело customer email | master с 2 suborders, items в каждом | email содержит все items обоих suborders | fallback: прямые items |
| Anonymous POST /orders/ | нет auth | 401 Unauthorized | DRF IsAuthenticated |
| Missing customer_code | auth user, нет customer_code | 400 ValidationError (поле customer_code) | не 500 |
| Sequence overflow | user/year = 999, +1 попытка | 400 ValidationError "sequence exhausted" | rollback, нет order/items/stock изменений |
| Admin items_count | master с 2 suborders | суммарное кол-во из всех suborders | fallback: прямые items |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/signals.py` — post_save receiver, нет guard `is_master`
- `backend/apps/orders/tasks.py` — email tasks, items берутся из order.items (неверно для master)
- `backend/apps/orders/views.py` — OrderViewSet, create action — AllowAny
- `backend/apps/orders/services/order_create.py` — create path, нет перехвата OrderNumberError
- `backend/apps/orders/serializers.py` — validate() использует ValueError вместо ValidationError
- `backend/apps/orders/admin.py` — items_count(), total_items_quantity() считают только direct items

## Tasks & Acceptance

**Execution:**

- [x] `backend/apps/orders/signals.py` — добавить `if not instance.is_master: return` перед постановкой email-задач в `send_order_confirmation_email` — предотвратить дублирование email по субзаказам.
- [x] `backend/apps/orders/tasks.py` — создать helper `_get_order_display_items(order)` (master: items через sub_orders, legacy: прямые items) и использовать в customer confirmation и admin notification tasks — устранить пустой список товаров.
- [x] `backend/apps/orders/views.py` — заменить `permissions.AllowAny()` для action `create` на `IsAuthenticated` — вернуть 401 вместо 400 для анонимных запросов.
- [x] `backend/apps/orders/services/order_create.py` — обернуть `OrderNumberingService.next_master_number()` в `try/except OrderNumberError` и поднимать `ValidationError` — устранить 500 при ошибках нумерации.
- [x] `backend/apps/orders/admin.py` — исправить `items_count()` и `total_items_quantity()`: master → через `sub_orders.prefetch_related("items")`, legacy fallback — показывать корректные данные менеджерам.
- [x] `backend/apps/orders/migrations/` — добавить data migration, удаляющую все существующие `Order` и `CustomerOrderSequence` записи — все текущие данные тестовые, legacy-заказов не останется после clean start.
- [x] `backend/tests/unit/test_order_numbering.py` — добавить: sequence overflow → ValidationError без side effects, email task не ставится для suborders, items helper master/legacy.
- [x] `backend/tests/integration/test_orders_api.py` — добавить regression: anonymous → 401, missing customer_code → 400, один email task на checkout (не 3).

**Acceptance Criteria:**

- Given checkout с 2 suborders, when signals fire, then exactly 1 customer email task + 1 admin email task в очереди (не 3).
- Given master с 2 suborders каждый с items, when customer confirmation email рендерится, then содержит все items из обоих suborders.
- Given unauthenticated `POST /api/orders/`, when запрос приходит, then ответ 401 (не 400).
- Given auth user без customer_code, when `POST /api/orders/`, then 400 ValidationError с полем "customer_code" (не 500).
- Given sequence для user/year = 999, when ещё одна попытка checkout, then 400 ValidationError, нет созданных order/items/stock changes.
- Given master с 2 suborders, when admin list рендерится, then `items_count` показывает суммарное количество из всех suborders (не 0).

## Spec Change Log

- 2026-05-02: RF-7 (legacy backfill) уточнён: все существующие заказы — тестовые данные, выполняется data migration с удалением через `Order.objects.all().delete()`. Legacy fallback код сохраняется как защитный слой на случай непредвиденных сценариев.

## Design Notes

`_get_order_display_items(order)` — логика:
```python
def _get_order_display_items(order):
    if order.is_master and order.sub_orders.exists():
        return OrderItem.objects.filter(order__parent_order=order).select_related("product")
    return order.items.select_related("product").all()
```

Перехват `OrderNumberError` в `order_create.py`:
```python
try:
    master_number_data = OrderNumberingService.next_master_number(user)
except OrderNumberError as e:
    raise ValidationError({"order_number": str(e)}) from e
```

## Verification

**Commands:**

- `docker compose --env-file .env -f docker/docker-compose.test.yml run --rm backend pytest backend/apps/orders backend/apps/users -m "unit or integration" -x` -- expected: все тесты pass, включая новые regression
- `docker compose --env-file .env -f docker/docker-compose.test.yml run --rm backend pytest backend/tests/integration/test_orders_api.py -xvs` -- expected: 401 для анонимов, корректные email task counts

## Suggested Review Order

**Email deduplication**

- Entry point: guard `is_master` блокирует все задачи email для субзаказов
  [`signals.py:37`](../../../backend/apps/orders/signals.py#L37)

- Helper агрегирует items master-заказа из всех субзаказов через parent_order FK
  [`tasks.py:23`](../../../backend/apps/orders/tasks.py#L23)

- Customer email рендерит items через новый helper (был `order.items.all()`)
  [`tasks.py:104`](../../../backend/apps/orders/tasks.py#L104)

- Admin notification context также получает items через helper
  [`tasks.py:198`](../../../backend/apps/orders/tasks.py#L198)

**Permission boundary**

- Все actions требуют IsAuthenticated → 401 для анонимов вместо 400
  [`views.py:35`](../../../backend/apps/orders/views.py#L35)

**Error handling**

- OrderNumberError → ValidationError: 500 превращается в контролируемый 400
  [`order_create.py:82`](../../../backend/apps/orders/services/order_create.py#L82)

**Admin display accuracy**

- Queryset расширен prefetch sub_orders__items для N+1 защиты
  [`admin.py:132`](../../../backend/apps/orders/admin.py#L132)

- items_count для master агрегирует из субзаказов (был всегда 0)
  [`admin.py:149`](../../../backend/apps/orders/admin.py#L149)

- total_items_quantity аналогично для master
  [`admin.py:156`](../../../backend/apps/orders/admin.py#L156)

**Data cleanup**

- Data migration удаляет все тестовые Order и CustomerOrderSequence
  [`0014_delete_test_orders.py:4`](../../../backend/apps/orders/migrations/0014_delete_test_orders.py#L4)

**Tests**

- Overflow sequence 999 → OrderNumberSequenceExhausted без side effects
  [`test_order_numbering.py:45`](../../../backend/tests/unit/test_order_numbering.py#L45)

- Signal guard: suborder save не ставит email задачи
  [`test_order_numbering.py:81`](../../../backend/tests/unit/test_order_numbering.py#L81)

- Items helper: master с suborders возвращает агрегированные items
  [`test_order_numbering.py:132`](../../../backend/tests/unit/test_order_numbering.py#L132)

- Regression: anonymous → 401 и один email task на checkout
  [`test_orders_api.py:202`](../../../backend/tests/integration/test_orders_api.py#L202)
