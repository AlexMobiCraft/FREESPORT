# Story 34.2: Логика создания субзаказов по VAT-группам и API-фильтрация мастер-заказов
 
 Status: review
 
 <!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
 
 ## Story

As a **клиент FREESPORT**,
I want **оформлять заказ как единый заказ, даже если товары имеют разные ставки НДС**,
so that **на моей стороне остаётся привычный UX (один заказ = один чек), а бэкенд при этом корректно разбивает его на технические субзаказы для 1С**.

> Техническая формулировка: реализовать в `OrderCreateSerializer.create()` автоматическую разбивку оформляемого заказа на один **мастер-заказ** (`is_master=True`) и N **дочерних субзаказов** (`is_master=False`) по группам `variant.vat_rate`; обеспечить, что клиентский API (`GET/LIST/RETRIEVE /api/v1/orders/`) возвращает только мастер-заказы.

## Acceptance Criteria

1. **AC1 (разбивка при создании):** При вызове `POST /api/v1/orders/` из корзины, содержащей товары **с разными `variant.vat_rate`**, создаётся **ровно один мастер-заказ** (`is_master=True, parent_order=None`) и **N субзаказов** (`is_master=False, parent_order=<master>`, `vat_group=<ставка>`), где N — количество уникальных ненулевых `vat_rate` в корзине.
2. **AC2 (однородная корзина):** Если в корзине все товары одной `vat_rate` (или только один товар), создаётся **1 мастер + 1 субзаказ** с этой `vat_group`. Мастер-заказ всегда присутствует — это единая точка контракта с клиентом.
3. **AC3 (перенос OrderItem):** Каждый `OrderItem` принадлежит **субзаказу**, соответствующему `vat_rate` его варианта. На мастере `items` не создаются (`master.items.count() == 0`). Поле `OrderItem.vat_rate` заполняется снимком `variant.vat_rate` через существующий `OrderItem.build_snapshot()` (Story 34-1).
4. **AC4 (финансовые поля):** `master.total_amount` = сумма по всем субзаказам (товары + доставка). `sub_order.total_amount` = сумма `OrderItem.total_price` его группы. `delivery_cost` записывается **только на мастере**; у субзаказов `delivery_cost=0` (доставка не дублируется). `discount_amount` — аналогично только на мастере.
5. **AC5 (атомарность и списание остатков):** Вся операция (создание мастера, субзаказов, `OrderItem`, списание `stock_quantity`, очистка корзины) выполняется в одной транзакции (`@transaction.atomic`). При ошибке — ни одна запись не остаётся.
6. **AC6 (общие атрибуты субзаказа):** Каждый субзаказ наследует от мастера: `user`, `customer_name/email/phone`, `delivery_address`, `delivery_method`, `delivery_date`, `payment_method`, `notes`. `status` субзаказа = `pending`, `payment_status` = `pending`. `order_number` — собственный у каждого субзаказа (генерируется автоматически в `Order.save()`).
7. **AC7 (обработка `vat_rate=None`):** Если у варианта `vat_rate` не задан (`None`), позиция попадает в субзаказ с `vat_group=None` (отдельная группа). Это не должно ломать создание заказа; после Story 34-3 такие субзаказы попадут в лог экспорта как требующие проверки.
8. **AC8 (API-фильтрация LIST):** `GET /api/v1/orders/` возвращает **только мастер-заказы** авторизованного пользователя: `Order.objects.filter(user=request.user, is_master=True)`. Субзаказы клиенту не видны.
9. **AC9 (API-фильтрация RETRIEVE):** `GET /api/v1/orders/{id}/` возвращает 404 при попытке прочитать субзаказ напрямую. Доступ разрешён только к мастер-заказам пользователя.
10. **AC10 (CANCEL только мастер):** `POST /api/v1/orders/{id}/cancel/` работает только с мастером. При отмене мастера каскадом отменяются все его субзаказы (`sub_orders` → `status='cancelled'`). Субзаказ напрямую отменить нельзя (404).
11. **AC11 (ответ POST):** `POST /api/v1/orders/` возвращает `OrderDetailSerializer(master).data`. Поле `items` в ответе мастера — **агрегированный список `OrderItem` из всех субзаказов** (клиент видит все позиции в одном заказе); реализуется через property `Order.items_aggregated` или переопределение `items` в сериализаторе для мастера.
12. **AC12 (обратная совместимость клиентского контракта):** Структура ответа `OrderDetailSerializer` и `OrderListSerializer` для клиента не меняется (кроме уже добавленных в Story 34-1 полей `is_master`, `vat_group`). Существующие frontend-вызовы продолжают работать.
13. **AC13 (покрытие тестами):** Новые unit- и integration-тесты покрывают: мульти-VAT разбивку, однородную корзину, агрегированные `items` мастера, 404 при доступе к субзаказу, cascade cancel, корректность `total_amount` мастера и суммы субзаказов, атомарность при ошибке. Тесты размечены `@pytest.mark.unit` / `@pytest.mark.integration`.

## Tasks / Subtasks

- [x] Task 1: Расширить `OrderCreateSerializer.create()` логикой разбивки на мастер + субзаказы (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] 1.1: Извлечь создание мастер-заказа в отдельный блок: `master = Order(**order_data, is_master=True, parent_order=None)`; `master.total_amount` и `delivery_cost` остаются на мастере.
  - [x] 1.2: Сгруппировать `cart.items` по `variant.vat_rate` (helper `_group_cart_items_by_vat(cart_items)` в сервисе/приватный метод сериализатора; ключ группы — `Decimal | None`).
  - [x] 1.3: Для каждой VAT-группы создать `sub_order = Order(parent_order=master, is_master=False, vat_group=<rate>, user=master.user, ..., delivery_cost=Decimal("0"), total_amount=<сумма группы>)` и сохранить.
  - [x] 1.4: `OrderItem` для каждой позиции строить с `order=sub_order` (а не мастер), сохранять через `bulk_create` с вызовом `OrderItem.build_snapshot()` (как в Story 34-1).
  - [x] 1.5: `master.total_amount` = сумма всех позиций + `delivery_cost`; сохранить мастер после расчёта субзаказов.
  - [x] 1.6: Логика списания `stock_quantity` и `cart.clear()` остаётся после создания всех субзаказов, внутри общей `@transaction.atomic`.
  - [x] 1.7: Вернуть `master` из `create()` (а не субзаказ). `to_representation(master)` уже вызывает `OrderDetailSerializer`.
- [x] Task 2: Выделить создание заказа в сервисный слой (AC: 1, 5) — **опционально, рекомендуется**
  - [x] 2.1: Создать `backend/apps/orders/services/order_create.py` с классом `OrderCreateService` (метод `create_from_cart(cart, user, validated_data) -> Order`).
  - [x] 2.2: Перенести туда логику разбивки; `OrderCreateSerializer.create()` становится тонкой обёрткой (соответствие "Service Layer" паттерну, см. `order_export.py`, `order_status_import.py`).
  - [x] 2.3: Если Task 2 пропущен — оставить логику в сериализаторе, но покрыть комментариями и unit-тестами отдельно.
- [x] Task 3: Добавить агрегацию `OrderItem` для мастера в API-ответ (AC: 11)
  - [x] 3.1: Добавить property/метод на `Order` (либо `items_all` в сериализаторе) — при `is_master=True` возвращает `OrderItem.objects.filter(order__in=[self, *self.sub_orders.all()])`.
  - [x] 3.2: Переопределить `OrderDetailSerializer.items` (через `SerializerMethodField` или кастомный источник), чтобы для мастера показывались позиции всех субзаказов.
  - [x] 3.3: `total_items`, `subtotal`, `calculated_total` на мастере — считать с учётом позиций субзаказов (не трогая оригинальные property на `Order` для сохранения обратной совместимости; использовать `SerializerMethodField`).
- [x] Task 4: Обновить `OrderViewSet.get_queryset()` — фильтрация мастер-заказов (AC: 8, 9)
  - [x] 4.1: Добавить `.filter(is_master=True)` в `get_queryset()`.
  - [x] 4.2: Обновить `prefetch_related` — добавить `sub_orders__items__product` чтобы детальный endpoint выдавал `items` без N+1.
  - [x] 4.3: Проверить, что `retrieve(id=<sub_order_id>)` возвращает 404 при попытке прочитать субзаказ напрямую. Доступ разрешён только к мастер-заказам пользователя.
- [x] Task 5: Cascade cancel мастера (AC: 10)
  - [x] 5.1: В `OrderViewSet.cancel()` после `order.status = "cancelled"; order.save()` добавить: `order.sub_orders.update(status="cancelled")`.
  - [x] 5.2: Явно запрещать cancel субзаказа — за счёт фильтра `is_master=True` в queryset это уже даёт 404, но добавить явную проверку `if not order.is_master: return 400/404` для защиты от обходных путей.
- [x] Task 6: Unit-тесты (AC: 13)
  - [x] 6.1: `test_order_create_service.py` (или `test_order_serializers.py`): тест разбивки корзины с 2 ставками НДС (5% и 22%) → 1 мастер + 2 субзаказа, корректные `vat_group` и `total_amount`.
  - [x] 6.2: Тест однородной корзины (1 ставка) → 1 мастер + 1 субзаказ.
  - [x] 6.3: Тест корзины со смесью `vat_rate=None` и `vat_rate=5` → 2 субзаказа (`vat_group=None` и `vat_group=5`).
  - [x] 6.4: Тест: `master.items.count() == 0`, а позиции живут в субзаказах.
  - [x] 6.5: Тест: `delivery_cost` только на мастере, у субзаказов = 0; `master.total_amount` = сумма по субзаказам + delivery_cost.
  - [x] 6.6: Тест атомарности: при искусственной ошибке (например, `variant.stock_quantity < quantity` после валидации) — ни одна запись не остаётся.
  - [x] 6.7: Тест snapshot `OrderItem.vat_rate`: заполняется через `build_snapshot` во всех субзаказах.
  - [x] 6.8: Все тесты файла помечены `@pytest.mark.unit` и `@pytest.mark.django_db`.
- [x] Task 7: Integration/API-тесты (AC: 8, 9, 10, 11, 12, 13)
  - [x] 7.1: В `backend/tests/integration/test_cart_order_integration.py` добавить тест: `POST /api/v1/orders/` с мульти-VAT корзиной → 201, в БД 1 master + 2 sub, ответ содержит все позиции в `items`.
  - [x] 7.2: Тест `GET /api/v1/orders/` возвращает только мастера (субзаказов нет в списке).
  - [x] 7.3: Тест `GET /api/v1/orders/<sub_order_id>/` → 404.
  - [x] 7.4: Тест `POST /api/v1/orders/<master_id>/cancel/` → мастер и все субзаказы в статусе `cancelled`.
  - [x] 7.5: Тест `POST /api/v1/orders/<sub_order_id>/cancel/` → 404.
  - [x] 7.6: Регрессионный тест: существующий сценарий однородной корзины продолжает работать без изменений в клиентском контракте.
  - [x] 7.7: Все тесты помечены `@pytest.mark.integration` и `@pytest.mark.django_db`.
- [x] Task 8: Обновление сериализатора ответа (AC: 11, 12)
  - [x] 8.1: В `OrderDetailSerializer` — переопределить источник `items` через `SerializerMethodField` `get_items(self, obj)`, который для `obj.is_master=True` агрегирует позиции из `sub_orders`.
  - [x] 8.2: Для субзаказа (если каким-то образом попадёт в сериализатор, например во внутренней админке) — отдавать свои `items` как раньше.
  - [x] 8.3: `total_items`, `subtotal`, `calculated_total` — также через `SerializerMethodField` с учётом агрегации для мастера.
- [x] Task 9: Проверка/обновление документации API (опционально)
  - [x] 9.1: Обновить docstring `OrderViewSet` и `extend_schema` description: отметить, что клиенту видны только мастер-заказы, а субзаказы — внутренняя структура для 1С.

### Review Follow-ups (AI)

- [x] [AI-Review][High] Исправить финансовую агрегацию `calculated_total` для мастер-заказа: значение должно включать сумму позиций всех субзаказов и `delivery_cost`, чтобы не расходиться с `total_amount`. [backend/apps/orders/serializers.py:80-85]
- [x] [AI-Review][High] Привести pytest-маркеры новых и изменённых тестов Story 34-2 к project-standard контракту `unit` / `integration`, чтобы AC13 и выборочные прогоны `pytest -m unit` / `pytest -m integration` не пропускали покрытие. [backend/tests/unit/test_serializers/test_order_serializers.py:151-152, backend/tests/integration/test_cart_order_integration.py:17-18]
- [x] [AI-Review][High] Добавить regression-тесты на сериализованный `calculated_total` мастер-заказа, чтобы AC4/AC11 подтверждались не только полем `total_amount`, но и фактическим API/serializer output. [backend/tests/unit/test_serializers/test_order_serializers.py:1058-1063, backend/tests/integration/test_cart_order_integration.py:338-355]
- [x] [AI-Review][Medium] Синхронизировать `Dev Agent Record -> File List` с фактическим git diff: задокументировать изменения story-артефактов (`34-2` story и `sprint-status.yaml`) либо привести review snapshot к полностью воспроизводимому набору файлов. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:367-373]
- [x] [AI-Review][Medium] Уточнить `Debug Log References`: claim `Все 50 тестов прошли с первого запуска. Линтинг (flake8) чистый.` не подтверждён артефактами ревью и должен быть либо доказан командами/логами, либо переформулирован в проверяемый вид. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:353-356]
- [x] [AI-Review][Low] Довести Task 5.2 до буквального соответствия story: добавить явную defensive-проверку `order.is_master` в `cancel()`, а не полагаться только на фильтр queryset и комментарий. [backend/apps/orders/views.py:134-159]
- [x] [AI-Review][High] Исправить регрессию list-contract: `GET /api/v1/orders/` должен возвращать корректный агрегированный `total_items` для мастер-заказов, а не `0` из-за чтения `Order.total_items` только по direct `items`. [backend/apps/orders/views.py:47-60, backend/apps/orders/serializers.py:263-267, backend/apps/orders/models.py:303-305]
- [x] [AI-Review][High] Восстановить `vat_group` в `OrderListSerializer`, иначе list endpoint нарушает AC12 и теряет уже добавленное в Story 34-1 поле клиентского контракта. [backend/apps/orders/serializers.py:297-327]
- [x] [AI-Review][Medium] Сделать `OrderViewSet.cancel()` атомарным, чтобы каскадная отмена мастера и субзаказов не могла завершиться частично при сбое между `order.save()` и `sub_orders.update(...)`. [backend/apps/orders/views.py:195-197]
- [x] [AI-Review][Medium] Добавить regression-тесты на `vat_group` в API/serializer output (`POST`/`LIST`/`RETRIEVE`), потому что текущий suite проверяет `vat_group` только на уровне БД у `sub_orders`, но не в `POST`/`LIST`/`RETRIEVE` payload, поэтому регресс контракта в сериализаторе прошёл незамеченным. [backend/tests/unit/test_serializers/test_order_serializers.py:734-840, backend/tests/integration/test_cart_order_integration.py:339-423, backend/tests/integration/test_orders_api.py:53-105]
- [x] [AI-Review][Low] Добавить integration coverage для успешного guest checkout через session cart, чтобы публичный `AllowAny` flow был защищён regression-тестом, а не только негативным кейсом пустой корзины. [backend/apps/orders/views.py:35-37, backend/apps/orders/serializers.py:224-237, backend/tests/integration/test_orders_api.py:161-179]
- [x] [AI-Review][Medium] Восстановить в `Dev Agent Record` обязательную секцию `File List` и синхронизировать её с фактическим review snapshot, иначе workflow-аудит changed-files claims остаётся неполным, а review snapshot не воспроизводится формально. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md]
- [x] [AI-Review][High] Исправить регрессию финансового snapshot contract в `OrderCreateService`: использовать `CartItem.price_snapshot`/`cart_item.total_price` при создании `OrderItem` и расчёте финансовых totals, а не пересчитывать цену через `variant.get_price_for_user(user)` в момент оформления. [backend/apps/orders/services/order_create.py:47-47, backend/apps/orders/services/order_create.py:66-66, backend/apps/orders/services/order_create.py:91-100, backend/apps/cart/models.py:129-155]
- [x] [AI-Review][Medium] Расширить integration regression на price drift после изменения цены варианта между add-to-cart и checkout. [backend/tests/integration/test_cart_order_integration.py:111-135]
- [x] [AI-Review][Medium] Добавить unit regression на snapshot-derived `unit_price`/`sub_order.total_amount`/`master.total_amount`. [backend/tests/unit/test_serializers/test_order_serializers.py:714-1184]
- [x] [AI-Review][Low] Ужесточить rollback-тест cancel, чтобы он валидировал и поведение endpoint, а не только состояние БД. [backend/tests/integration/test_cart_order_integration.py:587-621]
- [x] [AI-Review][High] Синхронизировать реальный checkout contract между frontend и backend: текущий `ordersService.createOrder()`/`orderStore` отправляет `email`/`phone`/`first_name`/`last_name`/`items`/`comment`, тогда как `OrderCreateSerializer` принимает `customer_*`/`notes` и не принимает `items`; AC12 про «existing frontend calls continue to work» сейчас не подтверждён. [frontend/src/services/ordersService.ts:42-57, frontend/src/stores/orderStore.ts:61-63, backend/apps/orders/serializers.py:156-166]
- [x] [AI-Review][Medium] Восстановить или явно переопределить list-contract: `ordersService.getAll()` и общий frontend `Order` type трактуют `/orders/` как detail-shape, но `OrderListSerializer` отдаёт суженный payload. Нужен либо расширенный backend response, либо отдельный frontend list type + contract/regression tests. [backend/apps/orders/serializers.py:297-313, frontend/src/services/ordersService.ts:138-142, frontend/src/types/order.ts:65-92]
- [x] [AI-Review][Medium] Синхронизировать `Dev Agent Record -> File List` с текущим review snapshot: в рабочем дереве есть изменённый `sprint-status.yaml` и mixed staged/unstaged state, но story не документирует этот snapshot как единый воспроизводимый набор файлов. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:266-281, _bmad-output/implementation-artifacts/sprint-status.yaml:129-132]
- [x] [AI-Review][Medium] Пере-подтвердить `Debug Log References` для текущего snapshot перед возвратом в `review`: story всё ещё опирается на claim `114 passed ... flake8/black clean` для предыдущего набора изменений, хотя в git уже есть новые staged/unstaged правки. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:3, _bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:256-273]

- [x] [AI-Review][High] Реализовать и покрыть тестами non-zero `discount_amount` end-to-end для Story 34-2: discount/promo из checkout/cart должен попадать только в мастер-заказ, не дублироваться на субзаказах и влиять на финансовый output по AC4. [backend/apps/orders/services/order_create.py:50-59, frontend/src/stores/cartStore.ts:16-35, frontend/src/components/checkout/OrderSummary.tsx:32-99]
- [x] [AI-Review][Medium] Синхронизировать frontend MSW POST `/orders/` handler с текущим create contract (`customer_*`, `notes`, server-side cart) и прогнать `ordersService`/`orderStore` tests, потому что тестовый handler всё ещё требует legacy payload `email`/`phone`/`first_name`/`last_name`/`items`/`comment`. [frontend/src/__mocks__/handlers/ordersHandlers.ts:94-132, frontend/src/services/__tests__/ordersService.test.ts:173-227, frontend/src/stores/__tests__/orderStore.test.ts:97-222]
- [x] [AI-Review][Medium] Обновить frontend list mocks/contract-tests под `OrderListItem`: текущий MSW `GET /orders/` возвращает detail-shaped `mockSuccessOrder` без `is_master`/`vat_group`/`sent_to_1c`, поэтому `ordersService.getAll()` не защищён от регрессов Story 34-2. [frontend/src/__mocks__/handlers/ordersHandlers.ts:12-87, frontend/src/__mocks__/handlers/ordersHandlers.ts:135-156, frontend/src/services/__tests__/ordersService.test.ts:229-243]
- [x] [AI-Review][Medium] Добавить regression-тесты на discount UI в checkout: текущий suite не проверяет `promo-discount-row`, discounted `Итого` и `До скидки`, поэтому заявленный fix `OrderSummary` не защищён от повторной регрессии. [frontend/src/components/checkout/OrderSummary.tsx:92-114, frontend/src/components/checkout/__tests__/CheckoutForm.test.tsx:179-202, frontend/src/components/checkout/__tests__/CheckoutForm.integration.test.tsx:244-259]
- [x] [AI-Review][Medium] Синхронизировать frontend detail mocks/tests с полным `OrderDetailSerializer` контрактом: `mockSuccessOrder` по-прежнему не отражает обязательные поля detail-shape (`sent_to_1c_at`, `status_1c`, `variant`, `variant_info`), поэтому `ordersService.getById()` и связанные frontend tests не подтверждают AC12 на реальном ответе backend. [frontend/src/__mocks__/handlers/ordersHandlers.ts:14-64, frontend/src/types/order.ts:39-97, frontend/src/services/__tests__/ordersService.test.ts:188-195, frontend/src/services/__tests__/ordersService.test.ts:300-305]
- [x] [AI-Review][Medium] Пересобрать review snapshot под текущий mixed staged/unstaged snapshot: `File List`/`Debug Log References` уже не соответствуют фактическому git diff (13 changed files), поэтому story нельзя считать reproducible review snapshot до следующего возврата в `review`. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:228-364, _bmad-output/implementation-artifacts/sprint-status.yaml:129-132]

- [x] [AI-Review][High] Синхронизировать detail-contract `OrderItem.product` между backend и frontend: `OrderItemSerializer` с `depth=1` возвращает nested `product` object, тогда как `frontend/src/types/order.ts` и `mockSuccessOrder` по-прежнему описывают/тестируют `product` как numeric id. Это делает `ordersService.createOrder()`/`getById()` типизированными неавторитетной схемой и оставляет AC12 незакрытым для detail response. [backend/apps/orders/serializers.py:19-45, frontend/src/types/order.ts:50-60, frontend/src/__mocks__/handlers/ordersHandlers.ts:36-69]
- [x] [AI-Review][Medium] Синхронизировать contract `order.id`/`orderId` в frontend services/tests с реальным backend PK: backend отдаёт numeric `id`, но `ordersService.getById()`/`getOrderByIdServer()` принимают `string`, а tests/MSW закрепляют UUID-like path и string `id` в response. Нужен единый numeric contract или явная нормализация. [backend/apps/orders/serializers.py:102-104, frontend/src/services/ordersService.ts:152-157, frontend/src/services/ordersService.server.ts:67-74, frontend/src/services/__tests__/ordersService.test.ts:300-305, frontend/src/__mocks__/handlers/ordersHandlers.ts:185-196]
- [x] [AI-Review][Medium] Добавить в frontend delivery enum поддержку backend value `transport_schedule`, иначе `Order`/`OrderListItem`/create payload по-прежнему не покрывают один из валидных `delivery_method` и AC12 остаётся неполным по type-contract. [backend/apps/orders/models.py:83-86, backend/apps/orders/serializers.py:286-295, frontend/src/types/order.ts:18-23]
- [x] [AI-Review][High] Довести runtime-отображение `delivery_method` до фактического backend contract: `OrderSuccessView` сейчас маппит несуществующий ключ `transport` вместо `transport_company` и не поддерживает `transport_schedule`, из-за чего пользователь видит raw backend code вместо локализованного лейбла. [frontend/src/components/checkout/OrderSuccessView.tsx:42-47, frontend/src/components/checkout/OrderSuccessView.tsx:119-124]
- [x] [AI-Review][Medium] Добавить поддержку `transport_schedule` в `OrderDetail` runtime labels: тип уже расширен, но UI detail page по-прежнему не локализует это значение и fallback-ит в сырой код ответа. [frontend/src/components/business/OrderDetail/OrderDetail.tsx:71-76, frontend/src/components/business/OrderDetail/OrderDetail.tsx:188-192]
- [x] [AI-Review][Medium] Добавить frontend regression-тесты на локализацию `transport_company`/`transport_schedule` в `OrderSuccessView` и `OrderDetail`, потому что текущий suite покрывает только `courier`/`pickup` и не ловит уже проявившийся runtime drift после type-level fix. [frontend/src/components/checkout/__tests__/OrderSuccessView.test.tsx:132-155, frontend/src/components/checkout/__tests__/OrderSuccessView.test.tsx:272-276, frontend/src/components/business/OrderDetail/OrderDetail.test.tsx:114-118]
- [x] [AI-Review][Medium] Синхронизировать `Dev Agent Record -> File List` с текущим review snapshot: в git изменён `sprint-status.yaml`, но он не отражён в `File List`, поэтому snapshot Twentieth follow-up формально не воспроизводится как полный набор changed files. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:371-391, _bmad-output/implementation-artifacts/sprint-status.yaml:129-132]

- [x] [AI-Review][High] Довести локализацию `delivery_method` до всех user-facing consumers detail-contract: `generateOrderPdf()` по-прежнему пишет raw backend code (`transport_company` / `transport_schedule`) через прямую интерполяцию `order.delivery_method`, поэтому B2B export остаётся несинхронизированным с runtime fix в success/detail UI. [frontend/src/utils/orderPdfExport.ts:84-89, frontend/src/components/business/OrderDetail/OrderDetailClient.tsx:109-116]
- [x] [AI-Review][Medium] Добавить regression coverage и/или общий helper для delivery labels в PDF/export path: текущие Story 34-2 тесты защищают только `OrderSuccessView` и `OrderDetail`, поэтому оставшийся drift в `generateOrderPdf()` не был пойман автоматически. [frontend/src/utils/orderPdfExport.ts:84-89, frontend/src/components/checkout/__tests__/OrderSuccessView.test.tsx:278-287, frontend/src/components/business/OrderDetail/OrderDetail.test.tsx:120-127]
- [x] [AI-Review][Medium] Пере-подтвердить `Debug Log References` на актуальном snapshot: story всё ещё опирается на historical claim `133 test files passed, 2222 tests passed, 14 skipped` / `npx tsc --noEmit` clean, хотя текущий worktree снова dirty и эти результаты не доказаны именно для него. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:291-294, _bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:3]
- [x] [AI-Review][Low] Нормализовать legacy delivery code в `DeliveryOptionsPlaceholder`: placeholder по-прежнему использует `transport`, оставляя в кодовой базе второй, несовместимый с backend/TS-contract идентификатор доставки рядом с авторитетным `transport_company`. [frontend/src/components/checkout/DeliveryOptionsPlaceholder.tsx:30-34, frontend/src/types/order.ts:22-27]

- [x] [AI-Review][High] Синхронизировать user-facing локализацию способов оплаты с backend contract: `OrderDetail` не покрывает валидные значения `bank_transfer` и `payment_on_delivery`, а `generateOrderPdf()` по-прежнему выводит raw `payment_method`/`payment_status` codes, поэтому B2B/detail flows остаются несовместимыми с реальными choices модели `Order`. [backend/apps/orders/models.py:89-100, frontend/src/components/business/OrderDetail/OrderDetail.tsx:82-97, frontend/src/components/business/OrderDetail/OrderDetail.tsx:219-228, frontend/src/utils/orderPdfExport.ts:98-103]
- [x] [AI-Review][Medium] Добавить regression-тесты на локализацию `payment_method`/`payment_status` в `OrderDetail` и PDF export path, потому что текущий suite закрепляет только happy-path `card`/`pending` и не ловит runtime drift для валидных backend codes `bank_transfer` и `payment_on_delivery`. [frontend/src/components/business/OrderDetail/OrderDetail.test.tsx:17-85, frontend/src/utils/__tests__/orderPdfExport.test.ts:32-76]
- [x] [AI-Review][Medium] Устранить drift по `delivery_method='post'`: `OrderDetail` показывает `Почта России`, тогда как backend choice и общий helper `getDeliveryMethodLabel()` возвращают `Почтовая доставка`, из-за чего один и тот же заказ локализуется по-разному в detail и PDF/success flows. [backend/apps/orders/models.py:81-87, frontend/src/components/business/OrderDetail/OrderDetail.tsx:71-77, frontend/src/utils/orderPdfExport.ts:52-60]
- [x] [AI-Review][Medium] Пере-подтвердить `Debug Log References` именно на текущем mixed staged/unstaged snapshot: claims `134 test files passed, 2232 tests passed, 14 skipped` и `npx tsc --noEmit` clean не сопровождаются воспроизводимыми логами/командами для нынешнего dirty worktree. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:226-259]

### Предыдущая история — Story 34-1 (фундамент)

Story 34-1 (status: review) уже добавила:
- Поля `Order.parent_order`, `Order.is_master`, `Order.vat_group` (миграция `0012_add_vat_split_fields`)
- Поле `OrderItem.vat_rate` и его snapshot через `OrderItem.build_snapshot(product, variant)`
- `OrderItem.vat_rate` уже корректно заполняется в `OrderCreateSerializer.create()` в bulk_create path (используется `build_snapshot` — см. [backend/apps/orders/serializers.py:251-262](file:///c:/Users/1/DEV/FREESPORT/backend/apps/orders/serializers.py))
- `is_master`, `vat_group` добавлены в `OrderDetailSerializer` и `OrderListSerializer` как `read_only`
- `OrderAdmin` получил fieldset "VAT / Субзаказы"
- Pytest markers `@pytest.mark.unit` / `@pytest.mark.integration` используются как стандарт проекта

**Следствие для 34-2:** не дублируй snapshot-логику — используй `OrderItem.build_snapshot()`. Все новые поля модели уже доступны, дополнительных миграций не требуется.

### Ключевые файлы

| Файл | Действие |
|------|----------|
| `backend/apps/orders/serializers.py` | Расширить `OrderCreateSerializer.create()` + `OrderDetailSerializer` (агрегация items) |
| `backend/apps/orders/views.py` | `get_queryset()` → `.filter(is_master=True)`; `cancel()` → cascade на субзаказы |
| `backend/apps/orders/services/order_create.py` | **Новый** (опционально): `OrderCreateService` |
| `backend/apps/orders/models.py` | Опционально: property `items_aggregated` на `Order` |
| `backend/tests/unit/test_serializers/test_order_serializers.py` | Unit-тесты разбивки |
| `backend/tests/unit/test_models/test_order_models.py` | Регрессия: property `items_aggregated` / агрегированные totals |
| `backend/tests/integration/test_cart_order_integration.py` | API-тесты (list/retrieve/create/cancel) |

### Тестовые паттерны проекта

- Маркеры: `@pytest.mark.django_db` + `@pytest.mark.unit` / `@pytest.mark.integration` (из AGENTS.md и Story 34-1 Third Follow-up).
- Фабрики: `UserFactory`, `OrderFactory`, `OrderItemFactory` из `backend/tests/conftest.py`.
- Для API-тестов: `APIClient` из `rest_framework.test`; для cart setup — смотри существующие паттерны в `backend/tests/integration/test_cart_order_integration.py`.
- Для варианта с заданной `vat_rate` — проверь, есть ли в фабриках `ProductVariantFactory` с параметром `vat_rate`; если нет — создавай явно в тесте.

### Docker команды для запуска тестов

```bash
# Unit-тесты сериализаторов/сервисов
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  pytest -xvs -m unit backend/tests/unit/test_serializers/test_order_serializers.py

# Integration-тесты API
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  pytest -xvs -m integration backend/tests/integration/test_cart_order_integration.py

# Полный прогон orders
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  pytest backend/apps/orders backend/tests/unit/test_models/test_order_models.py \
          backend/tests/unit/test_serializers/test_order_serializers.py \
          backend/tests/integration/test_cart_order_integration.py
```

### Архитектурные ограничения

- **PostgreSQL ONLY** — без сырых SQL, только Django ORM.
- **Обратная совместимость API** — клиентский контракт (`OrderDetailSerializer`, `OrderListSerializer`, `OrderCreateSerializer`) не должен сломаться для фронтенда. Поля `is_master`, `vat_group` уже добавлены в Story 34-1 как read_only.
- **Транзакционная целостность** — вся логика создания в одной `@transaction.atomic`.
- **Никаких data migrations** — в БД только тестовые заказы (подтверждено в sprint-change-proposal §Техническое влияние).
- **Не менять поля `OrderCreateSerializer.Meta.fields`** — клиентский input остаётся прежним. Разбивка выполняется полностью на бэкенде, прозрачно для клиента.

### Антипаттерны (НЕ ДЕЛАТЬ)

- НЕ трогать `apps/orders/services/order_export.py` — это Story 34-3.
- НЕ трогать `apps/orders/services/order_status_import.py` — это Story 34-4.
- НЕ создавать новую миграцию — поля уже есть из Story 34-1.
- НЕ ломать property `Order.items`, `Order.subtotal`, `Order.total_items` — они используются в сигналах/сервисах 1С. Для агрегации на мастере добавлять отдельные property/методы или делать агрегацию в `SerializerMethodField`.
- НЕ создавать `OrderItem` на мастере — все позиции живут на субзаказах.
- НЕ дублировать `delivery_cost` на субзаказах — доставка одна на весь заказ (на мастере).
- НЕ забывать про `vat_rate=None` — это валидный кейс (товары без указанной ставки), не падай, клади в группу с `vat_group=None`.
- НЕ хардкодить список ставок (5, 22) — группировка по факту из `variant.vat_rate`, любое число.
- НЕ позволять клиенту видеть субзаказы ни в одном endpoint.

### Project Structure Notes

- Структура соответствует unified project structure.
- Orders app: `backend/apps/orders/` (models, admin, serializers, views, urls, constants, services/).
- При выделении `OrderCreateService` — класть в `backend/apps/orders/services/order_create.py` (рядом с `order_export.py`, `order_status_import.py`).
- Тесты: unit — `backend/tests/unit/test_serializers/`, `backend/tests/unit/test_models/`; integration — `backend/tests/integration/`.

### Potential Risks & Open Questions

1. **Гостевые заказы** (`user=None`): логика та же — мастер и субзаказы с `user=None`, но гость в любом случае не видит список заказов. Проверить, что flow гостя не сломан.
2. **Каскадное удаление**: при `master.delete()` все субзаказы удаляются автоматически (`on_delete=CASCADE` на `parent_order`) — но `ProductVariant.stock_quantity` не возвращается. В текущем flow клиент не удаляет заказы (только cancel), поэтому это не регресс, но зафиксировать в retrospective Epic 34.
3. **Агрегация `status` на мастере** — согласно proposal §3 (UX-решение), мастер должен показывать агрегированный статус (`pending` → `confirmed` → `delivered`). **Эта агрегация — задача Story 34-4** (при импорте статусов из 1С). В 34-2 оставляй `master.status = "pending"` при создании и оставляй `cancel` как прямой переход в `cancelled` (cascade).
4. **Конфликт с `sent_to_1c` / `status_1c`** — эти поля живут на субзаказах (1С шлёт статус отдельно на каждый документ). На мастере они остаются со значениями по умолчанию. Это консистентно со Story 34-3/34-4.
5. **Existing OrderFactory**: может создавать `Order` без `is_master` setup (будет по дефолту `True`). Фикстуры Epic 4+5 — задача Story 34-5; в 34-2 не трогать.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#4.3-создание]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#4.4-api-фильтрация]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#3-ux-решение]
- [Source: _bmad-output/implementation-artifacts/Story/34-1-order-model-vat-split-fields-migrations.md — модель и snapshot helper]
- [Source: backend/apps/orders/models.py — Order, OrderItem, build_snapshot]
- [Source: backend/apps/orders/serializers.py — OrderCreateSerializer.create(), OrderDetailSerializer]
- [Source: backend/apps/orders/views.py — OrderViewSet.get_queryset(), cancel()]
- [Source: backend/apps/orders/services/order_export.py:371 — _get_order_vat_rate() (контекст потребителя субзаказов)]
- [Source: backend/tests/conftest.py — OrderFactory, UserFactory, get_unique_suffix()]
- [Source: AGENTS.md — pytest markers unit/integration]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

**Twenty-Sixth Follow-up (2026-04-18) — подтверждённые результаты:**

Frontend regression suite (текущий snapshot):
```
134 test files passed, 2249 tests passed, 14 skipped
npx tsc --noEmit → clean (нет ошибок)
```

**Команды воспроизведения (Docker, `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend ...`):**

Полная регрессия по затронутым областям:
```bash
pytest apps/orders tests/unit/test_models/test_order_models.py \
       tests/unit/test_serializers/test_order_serializers.py \
       tests/integration/test_cart_order_integration.py
```

Выборочные прогоны маркеров (AC13 — подтверждение contract):
```bash
pytest -m unit tests/unit/test_serializers/test_order_serializers.py
pytest -m integration tests/integration/test_cart_order_integration.py
```

Линтинг:
```bash
  flake8 apps/orders/serializers.py apps/orders/views.py apps/orders/services/order_create.py \
         tests/unit/test_serializers/test_order_serializers.py \
         tests/integration/test_cart_order_integration.py
  black --check apps/orders/serializers.py apps/orders/views.py apps/orders/services/order_create.py \
         tests/unit/test_serializers/test_order_serializers.py \
         tests/integration/test_cart_order_integration.py
  ```

### Completion Notes List

- ✅ Checkout/list contract между frontend и backend синхронизирован: `customer_*`, `notes`, server-side cart, отдельный `OrderListItem`.
- ✅ Финансовый snapshot contract восстановлен: order creation использует cart snapshot вместо live catalog price.
- ✅ `discount_amount` реализован end-to-end и согласован с serializer output (`calculated_total == total_amount`).
- ✅ Frontend detail-contract синхронизирован: nested `items[].product`, numeric `order.id`, поля Story 34-1/34-2, `transport_schedule` в `DeliveryMethodCode`.
- ✅ `OrderSuccessView` и `OrderDetail` доведены до фактического backend contract по `delivery_method`; добавлены regression-тесты на `transport_company`/`transport_schedule`.
- ✅ Resolved review finding [High]: `generateOrderPdf()` использует `getDeliveryMethodLabel()` — raw codes больше не попадают в PDF.
- ✅ Resolved review finding [Medium]: добавлен `orderPdfExport.test.ts` с 10 regression-тестами на локализацию delivery labels в PDF export path; экспортирован helper `getDeliveryMethodLabel`.
- ✅ Resolved review finding [Medium]: Debug Log References обновлены на актуальные результаты (134 test files, 2232 tests passed, tsc clean).
- ✅ Resolved review finding [Low]: `DeliveryOptionsPlaceholder` нормализован: `transport` → `transport_company`.
- ✅ Resolved review finding [High]: добавлены `getPaymentMethodLabel()` и `getPaymentStatusLabel()` в `orderPdfExport.ts`; `generateOrderPdf()` больше не выводит raw `payment_method`/`payment_status` codes.
- ✅ Resolved review finding [Medium]: `OrderDetail.tsx` импортирует `getDeliveryMethodLabel` из `orderPdfExport.ts` (единый source of truth); `post` → `Почтовая доставка` согласован во всех flows.
- ✅ Resolved review finding [Medium]: `paymentMethodLabels` в `OrderDetail.tsx` приведён к backend choices (`bank_transfer`, `payment_on_delivery`; удалены `invoice`/`online`); `refunded` исправлен на `Возвращен`.
- ✅ Resolved review finding [Medium]: добавлены regression-тесты на `bank_transfer`/`payment_on_delivery`/`refunded` в `OrderDetail.test.tsx` (3 новых) и `orderPdfExport.test.ts` (8 новых helpers + PDF tests).
- ✅ Resolved review finding [Medium]: Debug Log References обновлены — 134 test files, 2249 tests passed, tsc clean, подтверждено на текущем snapshot.

### File List

**Изменённые файлы (Twentieth Follow-up, 2026-04-18):**

- `frontend/src/types/order.ts` — добавлен `OrderItemProduct`; `OrderItem.product` переведён на nested object; `transport_schedule` добавлен в `DeliveryMethodCode`.
- `frontend/src/__mocks__/handlers/ordersHandlers.ts` — items[].product переведены на объект `{ id, name }`; GET `/orders/:id/` возвращает numeric `id`.
- `frontend/src/components/checkout/OrderSuccessView.tsx` — key обновлён на `item.product.id`.
- `frontend/src/services/__tests__/ordersService.test.ts` — добавлены contract regression tests на nested product / numeric id / `transport_schedule`.
- `frontend/src/components/checkout/__tests__/OrderSuccessView.test.tsx` — mock items[].product переведены на объект; добавлены Story 34-1 поля.
- `frontend/src/components/business/OrderDetail/OrderDetail.test.tsx` — mock items[].product переведены на объект; добавлены Story 34-1 поля.

**Изменённые файлы (Twenty-Second Follow-up, 2026-04-18):**

- `frontend/src/components/checkout/OrderSuccessView.tsx` — `transport` заменён на `transport_company`, добавлен `transport_schedule`.
- `frontend/src/components/business/OrderDetail/OrderDetail.tsx` — добавлен `transport_schedule` в `deliveryMethodLabels`.
- `frontend/src/components/checkout/__tests__/OrderSuccessView.test.tsx` — добавлены 2 regression-теста на локализацию `transport_company`/`transport_schedule`.
- `frontend/src/components/business/OrderDetail/OrderDetail.test.tsx` — добавлены 2 regression-теста на локализацию `transport_company`/`transport_schedule`.

**Изменённые файлы (Twenty-Sixth Follow-up, 2026-04-18):**

- `frontend/src/utils/orderPdfExport.ts` — добавлены `getPaymentMethodLabel()` и `getPaymentStatusLabel()` helpers; `generateOrderPdf()` использует их вместо raw codes.
- `frontend/src/utils/__tests__/orderPdfExport.test.ts` — добавлены 13 regression-тестов на payment method/status localization в helpers и PDF output.
- `frontend/src/components/business/OrderDetail/OrderDetail.tsx` — импортирует `getDeliveryMethodLabel` из `orderPdfExport.ts`; `paymentMethodLabels` приведён к backend contract (`bank_transfer`, `payment_on_delivery`); `refunded` исправлен.
- `frontend/src/components/business/OrderDetail/OrderDetail.test.tsx` — добавлены 4 regression-теста на `bank_transfer`/`payment_on_delivery`/`refunded`/`post`.
- `_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md` — обновлены Review Follow-ups, Action Items, File List, Completion Notes, Debug Log, Change Log, Status → review.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story 34-2 синхронизирована в `review`.

**Изменённые файлы (Twenty-Fourth Follow-up, 2026-04-18):**

- `frontend/src/utils/orderPdfExport.ts` — добавлен экспортируемый helper `getDeliveryMethodLabel()`; `generateOrderPdf()` использует его для локализации `delivery_method`.
- `frontend/src/utils/__tests__/orderPdfExport.test.ts` — **новый файл**: 10 regression-тестов на `getDeliveryMethodLabel` и `generateOrderPdf` delivery-label output.
- `frontend/src/components/checkout/DeliveryOptionsPlaceholder.tsx` — нормализован legacy id `transport` → `transport_company`.
- `_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md` — обновлены Review Follow-ups, Action Items, File List, Completion Notes, Debug Log, Change Log, Status → review.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story 34-2 синхронизирована в `review`.

## Senior Developer Review (AI)

### Twenty-Third Follow-up Review (AI)

#### Review Date

2026-04-18

#### Outcome

Changes Requested

#### Summary

- Найдено 4 issue: 1 High, 2 Medium, 1 Low.
- Последние fixes по `OrderSuccessView`/`OrderDetail` и новым regression-тестам закрывают runtime drift на двух ключевых экранах, но delivery-method contract всё ещё не доведён до всех user-facing consumers.
- Основной риск: B2B PDF export по-прежнему выводит raw backend codes для валидных значений `delivery_method`, а review evidence не подтверждена на текущем dirty snapshot.

#### Findings

1. **[High] `generateOrderPdf()` остаётся несовместимым с backend `delivery_method` contract** — утилита экспорта в PDF напрямую интерполирует `order.delivery_method` в документ, не используя локализованный label map. Для заказов с `transport_company` и `transport_schedule` экспортируемый PDF будет содержать raw backend codes, хотя Story 34-2 уже заявляет синхронизированный frontend contract для detail response. Поскольку этот путь реально вызывается из `OrderDetailClient`, drift остаётся user-visible и не ограничивается только success/detail pages. [frontend/src/utils/orderPdfExport.ts:84-89, frontend/src/components/business/OrderDetail/OrderDetailClient.tsx:109-116]
2. **[Medium] Regression coverage не защищает PDF/export consumer** — новые tests Twenty-Second follow-up проверяют только локализацию в `OrderSuccessView` и `OrderDetail`. Путь `generateOrderPdf(order)` не покрыт regression-проверкой на delivery labels, поэтому оставшийся runtime drift прошёл мимо автоматической валидации. [frontend/src/utils/orderPdfExport.ts:84-89, frontend/src/components/checkout/__tests__/OrderSuccessView.test.tsx:278-287, frontend/src/components/business/OrderDetail/OrderDetail.test.tsx:120-127]
3. **[Medium] `Debug Log References` не подтверждены для текущего snapshot** — story продолжает ссылаться на результаты Twenty-Second follow-up (`133 test files passed, 2222 tests passed, 14 skipped`, `npx tsc --noEmit` clean) как на актуальное evidence, хотя worktree снова dirty и новые review-артефакты ещё не были заново провалидированы этими командами. Пока свежий прогон не выполнен именно на текущем дереве, snapshot нельзя считать формально review-ready. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:3]
4. **[Low] В кодовой базе остаётся legacy delivery identifier `transport`** — `DeliveryOptionsPlaceholder` всё ещё содержит статический option id `transport`, который уже не соответствует авторитетному backend/frontend contract (`transport_company`). Компонент сейчас выглядит как placeholder, но сохранение второго несовместимого кода повышает риск future reintroduction bug при переиспользовании или копировании этой реализации. [frontend/src/components/checkout/DeliveryOptionsPlaceholder.tsx:30-34, frontend/src/types/order.ts:22-27]

#### Action Items

- [x] [High] Локализовать `delivery_method` в `frontend/src/utils/orderPdfExport.ts` для backend values `transport_company` и `transport_schedule` и не выводить raw codes в PDF.
- [x] [Medium] Добавить regression coverage на PDF/export path и/или вынести общий helper для delivery labels, чтобы один fix покрывал `OrderSuccessView`, `OrderDetail` и `generateOrderPdf()`.
- [x] [Medium] Перезапустить frontend regression/TypeScript checks на текущем snapshot и обновить `Debug Log References` только подтверждёнными результатами.
- [x] [Low] Нормализовать legacy `transport` → `transport_company` в `DeliveryOptionsPlaceholder` или явно удалить устаревший placeholder, если он больше не нужен.

### Twenty-Fifth Follow-up Review (AI)

#### Review Date

2026-04-18

#### Outcome

Changes Requested

#### Summary

- Найдено 4 issue: 1 High, 3 Medium.
- Последние fixes действительно закрыли `delivery_method` drift для `transport_company` / `transport_schedule` и добавили regression coverage на PDF export path.
- Однако текущий snapshot всё ещё не review-ready: локализация payment contract неполная, `post` маппится непоследовательно между user-facing consumers, а debug evidence не подтверждена именно для текущего mixed staged/unstaged worktree.

#### Findings

1. **[High] Frontend payment labels остаются несовместимыми с backend contract** — в `OrderDetail` словарь `paymentMethodLabels` по-прежнему содержит legacy key `invoice`, но не покрывает валидные backend choices `bank_transfer` и `payment_on_delivery`, а `generateOrderPdf()` вообще вставляет в документ raw `order.payment_method` и `order.payment_status`. Для реальных заказов из B2B/checkout flow пользователь увидит сырые коды (`bank_transfer`, `payment_on_delivery`, `pending`) вместо локализованных значений, то есть AC12 про совместимый user-facing contract пока не подтверждён полностью. [backend/apps/orders/models.py:89-100, frontend/src/components/business/OrderDetail/OrderDetail.tsx:82-97, frontend/src/components/business/OrderDetail/OrderDetail.tsx:219-228, frontend/src/utils/orderPdfExport.ts:98-103]
2. **[Medium] Regression coverage не защищает payment label contract** — текущие frontend tests для `OrderDetail` и `orderPdfExport` используют только `card` / `pending` и не имеют ни одного assert на локализацию `bank_transfer` / `payment_on_delivery`, поэтому описанный runtime drift проходит мимо автопроверок. [frontend/src/components/business/OrderDetail/OrderDetail.test.tsx:17-85, frontend/src/utils/__tests__/orderPdfExport.test.ts:32-76]
3. **[Medium] `delivery_method='post'` локализуется непоследовательно в разных consumers** — backend choice для `post` = `Почтовая доставка`, тот же label возвращает `getDeliveryMethodLabel()`, но `OrderDetail` использует отдельный map и показывает `Почта России`. В результате один и тот же заказ получает разные русские названия доставки на detail и PDF/success путях. [backend/apps/orders/models.py:81-87, frontend/src/components/business/OrderDetail/OrderDetail.tsx:71-77, frontend/src/utils/orderPdfExport.ts:52-60]
4. **[Medium] `Debug Log References` по-прежнему не доказаны для текущего snapshot** — story теперь заявляет `134 test files passed, 2232 tests passed, 14 skipped` и `npx tsc --noEmit` clean как подтверждённые результаты, но review проходил по dirty worktree с mixed staged/unstaged правками, а свежие логи/артефакты этих прогонов в story не приложены. До повторной валидации именно на текущем дереве claims остаются unverifiable. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:226-259]

#### Action Items

- [ ] [High] Нормализовать локализацию `payment_method` / `payment_status` в `OrderDetail` и `generateOrderPdf()` под авторитетные backend choices `card`, `cash`, `bank_transfer`, `payment_on_delivery` и `pending` / `paid` / `failed` / `refunded`.
- [ ] [Medium] Добавить regression-тесты на runtime-локализацию `bank_transfer` / `payment_on_delivery` / `pending` для detail и PDF export consumers.
- [ ] [Medium] Вынести общий helper или единый source of truth для delivery labels, чтобы `post` отображался одинаково во всех user-facing flows.
- [ ] [Medium] Перезапустить frontend regression/TypeScript checks на актуальном snapshot и обновить `Debug Log References` только воспроизводимыми, заново подтверждёнными результатами.

## Change Log

| Date | Change |
|------|--------|
| 2026-04-16 | Story создана через create-story workflow по sprint-change-proposal §4.3–4.4. Status → ready-for-dev. |
| 2026-04-16 | Реализация Story 34-2: OrderCreateService (VAT split), фильтр is_master в ViewSet, cascade cancel, SerializerMethodField агрегация, 15 новых тестов. Status → review. |
| 2026-04-16 | Code Review (AI): добавлены 6 Review Follow-ups (3 High, 2 Medium, 1 Low). Status → in-progress. Outcome: Changes Requested. |
| 2026-04-17 | Follow-up циклы закрыли `total_items`, race condition остатков, `vat_group`, guest checkout и snapshot price contract. |
| 2026-04-17 | Tenth follow-up синхронизировал frontend checkout/list contract с backend (`customer_*`, `notes`, `OrderListItem`). Status → review. |
| 2026-04-18 | Eleventh–Eighteenth follow-up циклы закрыли `discount_amount` end-to-end, serializer totals, marker contract, checkout UI и detail mock-contract. |
| 2026-04-18 | Nineteenth/Twentieth follow-up закрыли detail-contract gaps по `OrderItem.product`, numeric `order.id` и `transport_schedule`; TypeScript приведён в clean state. |
| 2026-04-18 | Twenty-First follow-up code review (AI, YOLO): найдены runtime gaps по delivery labels в `OrderSuccessView`/`OrderDetail` и File List snapshot. Status → in-progress. Outcome: Changes Requested. |
| 2026-04-18 | Twenty-Second review follow-ups: `OrderSuccessView` и `OrderDetail` синхронизированы по delivery labels, добавлены 4 regression-теста, frontend suite: `2222 passed`, `tsc` clean. Status → review. |
| 2026-04-18 | Twenty-Third follow-up code review (AI, YOLO): добавлены 4 новых Review Follow-ups (1 High, 2 Medium, 1 Low). Выявлены remaining gaps по локализации `delivery_method` в B2B PDF export, отсутствию regression coverage для export path, stale `Debug Log References` на текущем dirty snapshot и legacy `transport` code в `DeliveryOptionsPlaceholder`. Status → in-progress. Outcome: Changes Requested. |
| 2026-04-18 | Twenty-Fourth follow-up: добавлен `getDeliveryMethodLabel()` helper в `orderPdfExport.ts`, 10 новых тестов в `orderPdfExport.test.ts`, нормализован `DeliveryOptionsPlaceholder` (transport → transport_company). Frontend: 134 files, 2232 tests passed, tsc clean. Status → review. |
| 2026-04-18 | Twenty-Fifth follow-up code review (AI, YOLO): добавлены 4 новых Review Follow-ups (1 High, 3 Medium). Выявлены remaining gaps по локализации `payment_method`/`payment_status` в detail/PDF flows, непоследовательному label для `post` и неподтверждённым `Debug Log References` на текущем mixed snapshot. Status → in-progress. Outcome: Changes Requested. |
| 2026-04-18 | Twenty-Sixth follow-up: добавлены `getPaymentMethodLabel()`/`getPaymentStatusLabel()` helpers в `orderPdfExport.ts`; `generateOrderPdf()` локализует payment codes; `OrderDetail.tsx` импортирует `getDeliveryMethodLabel` (единый source of truth), `paymentMethodLabels` приведён к backend contract, `post` консистентен (`Почтовая доставка`). Добавлены 17 новых тестов. Frontend: 134 files, 2249 tests passed, tsc clean. Status → review. |

