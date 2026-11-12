---
title: 'Актуальная цена при оформлении заказа'
type: 'feature'
created: '2026-11-12'
status: 'ready-for-dev'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/research-order-line-price-type-1c.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Цена строки заказа берётся из снимка корзины (`CartItem.price_snapshot`), сделанного при добавлении товара, и при оформлении не пересчитывается. Если акция закончилась или цена роли поменялась, заказ уходит по устаревшей цене, а из какого поля взята цена, неизвестно. Это нужно истории 2 (вид цены строки для 1С).

**Approach:** При оформлении цена каждой позиции считается заново вместе с полем-источником, до создания заказа. Если цена хоть одной позиции изменилась (в любую сторону), заказ не создаётся: снимки корзины обновляются, покупатель видит «Цены изменились», какие строки изменились (было → стало) и новую сумму, повторное оформление проходит. Нулевая цена блокирует оформление.

**Решения владельца (12.11.2026):** цена пересчитывается при оформлении, оплата будет по цене заказа; при расхождении со снимком — отказ с «Цены изменились», обновление корзины и новая сумма на чекауте; при равенстве цены роли и акции источник — акция; цена ≤ 0 — ошибка оформления. Дополнение после ревью (12.11.2026): тело 409 перечисляет изменившиеся строки и новую сумму позиций; чекаут показывает их из тела ответа, а не из перезагруженной корзины.

## Boundaries & Constraints

**Always:**
- `pricing_policy.resolve_user_price(variant, user) -> PricedField(price: Decimal, field: str)` — цепочка `get_price_for_user` (акция → поле роли → запасное поле → `retail_price`); при равенстве цены роли и акции `field = "promo_price"`. `get_price_for_user` возвращает её `price`, контракт не меняется. Это контракт для истории 2. Поле цепочки роли отдаёт `resolve_role_price`, доработанная так, чтобы возвращать и цену, и поле (вызывающий один — `get_regular_price_for_user`, `models.py:1543`). Копировать цепочку в `resolve_user_price` нельзя: она общая с ценовыми фильтрами каталога.
- `OrderCreateService.create`: первым делом `promo.lock_promo_state(shared=True)`, затем по каждой позиции корзины `resolve_user_price`. Проверки — до `next_master_number` и любых записей заказа, в порядке: (1) любая цена ≤ 0 → `price_unavailable`; (2) любая цена ≠ `price_snapshot` → `prices_changed`.
- `prices_changed`: в той же транзакции `CartItem.objects.filter(pk=…).update(price_snapshot=…)` для разошедшихся позиций (не `save()`: `full_clean` и сигнал `reserved_quantity`). Сервис возвращает результат-флаг со списком изменений, без исключения. `OrderCreateSerializer.create` отдаёт результат сервиса как есть. `OrderViewSet.create` (`views.py:120`) проверяет флаг сразу после `serializer.save()`, до `prefetch_related_objects`, и отвечает `Response({"code": "prices_changed", "detail": "Цены изменились. Проверьте сумму заказа", "items": [{"variant_id", "product_name", "quantity", "old_price", "new_price"}], "items_total": "<сумма всех позиций корзины по новым ценам>"}, status=409)`. Суммы — строками, как `price_snapshot` в `CartItemSerializer`; в `items` только разошедшиеся позиции. Снимки фиксируются на проде коммитом `@transaction.atomic` сервиса (`ATOMIC_REQUESTS` там нет), а в тестах (`ATOMIC_REQUESTS=True` в `settings/test.py`) — коммитом запроса: ответ 409 без исключения отката не вызывает.
- `price_unavailable`: сервис выбрасывает `ValidationError({"code": "price_unavailable", "detail": "<товар> сейчас недоступен для заказа"})` строками (не из `validate()`), ответ 400, корзина не меняется.
- Сервис держит `PricedField` по каждой позиции и строит из него `unit_price`, `total_price`, суммы групп и мастера.

**Never:** не менять правило `min(роль, акция)`; не пересчитывать снимок при GET корзины; не править `docs/api/openapi.yaml` и `api.generated.ts` руками.

## I/O & Edge-Case Matrix

| Сценарий | Состояние | Результат | Ответ |
|---|---|---|---|
| Цены не менялись | снимок = текущая цена | заказ создан, суммы как в корзине | 201 |
| Акция закончилась | снимок = акция, сейчас цена роли | заказа нет, снимок = цена роли; в `items` строка с `old_price` = акция, `new_price` = цена роли | 409 |
| Цена роли изменилась | импорт 1С поменял `opt2_price` | заказа нет, снимок = новая цена | 409 |
| Цена снизилась | B2B верифицирован после добавления в корзину | заказа нет, снимок = цена «Опт» | 409 |
| Повтор после 409 | снимки обновлены | заказ создан по новой цене | 201 |
| Равенство роли и акции | `promo_price` = `opt2_price` | цена та же, `field = promo_price` | 201 |
| Нулевая цена | `retail_price` = 0, акции нет | заказа нет, корзина не тронута | 400 `price_unavailable` |
| Ноль и изменение сразу | одна позиция 0, другая подорожала | заказа нет, снимки не тронуты | 400 `price_unavailable` |

</frozen-after-approval>

## Code Map

- `backend/apps/products/pricing_policy.py:96` `resolve_role_price` — рядом `resolve_user_price`.
- `backend/apps/products/models.py:1516` `get_price_for_user` — `min(роль, акция)` (impact LOW, 3 вызывающих).
- `backend/apps/products/services/promo.py:94` `lock_promo_state` — защищает от смены акции, не от импорта цен ролей (общая блокировка у импорта, `variant_import.py:1985`); пока идёт сброс акции, оформление ждёт.
- `backend/apps/orders/services/order_create.py:31` `@transaction.atomic`; `:60-70` цикл по корзине и сумма (комментарий стр. 69 — «намеренно снимок»); `:80` `next_master_number` (блокирует пользователя и `CustomerCodeSequence`); `:133-150` `OrderItem`.
- `backend/apps/orders/views.py:100-124` `OrderViewSet.create` и его `extend_schema`.
- `backend/apps/orders/serializers.py:209-211` — заказ только для авторизованных; гостевого оформления нет.
- `frontend/src/services/ordersService.ts:70` `parseApiError` (разбирает 400; при 400 без `detail`/`error` даёт «ключ: сообщение»), `:140-145` POST и `throw new Error(message)`; `stores/orderStore.ts:49-86`; `components/checkout/CheckoutForm.tsx:240-292, 338`; `stores/cartStore.ts:111-118` `fetchCart` (глотает ошибки); `components/checkout/OrderSummary.tsx:87`.
- `backend/apps/bonuses/services/accrual.py:57` — база бонусов = `OrderItem.total_price`.

## Tasks & Acceptance

**Execution:**
- [ ] `backend/apps/products/pricing_policy.py`, `models.py` -- `PricedField`; `resolve_role_price` отдаёт цену и поле; `resolve_user_price`; `get_price_for_user` через неё; юнит-тесты цепочки и равенства.
- [ ] `backend/apps/orders/services/order_create.py` -- блокировка акции; проверки до записей в порядке Boundaries; обновление снимков через `update()`; результат-флаг `prices_changed` со списком изменений и `items_total`; суммы и `OrderItem` из `PricedField`; убрать комментарий о снимке.
- [ ] `backend/apps/orders/serializers.py` -- `create` возвращает результат сервиса без изменений.
- [ ] `backend/apps/orders/views.py` -- 409 по флагу до `prefetch_related_objects`, тело по Boundaries; в `extend_schema` добавить 409 со схемой тела и пример 400 `price_unavailable`; перегенерировать `python manage.py spectacular --file ../docs/api/openapi.yaml --format openapi --validate` и `cd frontend && npm run generate:types`.
- [ ] `frontend/src/services/ordersService.ts` -- класс `OrderApiError extends Error` с `status`, `code` и `priceChanges` (`items`, `items_total` из тела 409); ветка 409 в `parseApiError`; `detail` из 400 `price_unavailable`.
- [ ] `frontend/src/stores/orderStore.ts` -- в catch `createOrder` при `code === "prices_changed"` сохранить `priceChanges` в сторе, `await useCartStore.getState().fetchCart()`, затем `error` = сообщение; повторный выброс как сейчас; `priceChanges` сбрасывается при следующей отправке.
- [ ] `frontend/src/components/checkout/CheckoutForm.tsx` -- в `InfoPanel` под сообщением список изменившихся строк «товар: было → стало» и новая сумма позиций из `priceChanges`.
- [ ] Тесты frontend (`__tests__` у сервиса, стора, `CheckoutForm`) -- 409 обновляет корзину (`cartService.get` с новыми ценами), форма сохранена, сообщение и строки «было → стало» в `InfoPanel`; при упавшем `fetchCart` строки и сумма из тела 409 всё равно показаны.
- [ ] Тесты backend -- матрица; переделать опоры на цену корзины: `tests/integration/test_cart_order_integration.py:145`, `tests/unit/test_serializers/test_order_serializers.py:1256` (вызывает `serializer.save()` напрямую — проверять флаг сервиса), `apps/bonuses/tests/test_vat_warehouse_split.py:73-90`, `tests/integration/test_orders_api.py`, `test_order_api.py`, `test_order_create_email_on_commit.py`.

**Acceptance Criteria:**
- Given 409 `prices_changed`, when чекаут получил ответ, then показаны сообщение и изменившиеся строки «было → стало» с новой суммой позиций из тела ответа, корзина перезагружена, `OrderSummary` показывает новую сумму, поля формы сохранены.
- Given 409 и упавший `fetchCart`, when чекаут получил ответ, then строки и новая сумма из тела 409 всё равно показаны.
- Given расхождение в двух позициях из трёх, when `POST /orders/`, then ответ 409, в `items` ровно эти две позиции с прежней и новой ценой, `items_total` = сумма всех трёх по новым ценам, обновлены снимки обеих, третья не тронута, заказов и субзаказов нет, и под `django_capture_on_commit_callbacks(execute=True)` писем нет.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit && npx vitest run src/components/checkout src/stores src/services` -- expected: без ошибок.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` -- expected: зелёные (включая `test_b2b_workflow.py`, `test_pricing_integration.py`, `test_b2c_workflow.py` без правок).
- `python manage.py check_openapi_sync` в контейнере backend -- expected: схема совпадает.
