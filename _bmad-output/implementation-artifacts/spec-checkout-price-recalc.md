---
title: 'Актуальная цена при оформлении заказа'
type: 'feature'
created: '2026-11-12'
status: 'in-progress'
baseline_commit: '939e3f7a'
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
- [x] `backend/apps/products/pricing_policy.py`, `models.py` -- `PricedField`; `resolve_role_price` отдаёт цену и поле; `resolve_user_price`; `get_price_for_user` через неё; юнит-тесты цепочки и равенства.
- [x] `backend/apps/orders/services/order_create.py` -- блокировка акции; проверки до записей в порядке Boundaries; обновление снимков через `update()`; результат-флаг `prices_changed` со списком изменений и `items_total`; суммы и `OrderItem` из `PricedField`; убрать комментарий о снимке.
- [x] `backend/apps/orders/serializers.py` -- `create` возвращает результат сервиса без изменений.
- [x] `backend/apps/orders/views.py` -- 409 по флагу до `prefetch_related_objects`, тело по Boundaries; в `extend_schema` добавить 409 со схемой тела и пример 400 `price_unavailable`; перегенерировать `python manage.py spectacular --file ../docs/api/openapi.yaml --format openapi --validate` и `cd frontend && npm run generate:types`.
- [x] `frontend/src/services/ordersService.ts` -- класс `OrderApiError extends Error` с `status`, `code` и `priceChanges` (`items`, `items_total` из тела 409); ветка 409 в `parseApiError`; `detail` из 400 `price_unavailable`.
- [x] `frontend/src/stores/orderStore.ts` -- в catch `createOrder` при `code === "prices_changed"` сразу сохранить в сторе `error` = сообщение и `priceChanges`, затем `await useCartStore.getState().fetchCart()`; повторный выброс как сейчас; `priceChanges` сбрасывается при следующей отправке.
- [x] `frontend/src/components/checkout/CheckoutForm.tsx` -- в `InfoPanel` под сообщением список изменившихся строк «товар: было → стало» и новая сумма позиций из `priceChanges`.
- [x] Тесты frontend (`__tests__` у сервиса, стора, `CheckoutForm`) -- 409 обновляет корзину (`cartService.get` с новыми ценами), форма сохранена, сообщение и строки «было → стало» в `InfoPanel`; при упавшем `fetchCart` строки и сумма из тела 409 всё равно показаны.
- [x] Тесты backend -- матрица; переделать опоры на цену корзины: `tests/integration/test_cart_order_integration.py:145`, `tests/unit/test_serializers/test_order_serializers.py:1256` (вызывает `serializer.save()` напрямую — проверять флаг сервиса), `apps/bonuses/tests/test_vat_warehouse_split.py:73-90`, `tests/integration/test_orders_api.py`, `test_order_api.py`, `test_order_create_email_on_commit.py`.

**Acceptance Criteria:**
- Given 409 `prices_changed`, when чекаут получил ответ, then показаны сообщение и изменившиеся строки «было → стало» с новой суммой позиций из тела ответа, корзина перезагружена, `OrderSummary` показывает новую сумму, поля формы сохранены.
- Given 409 и упавший `fetchCart`, when чекаут получил ответ, then строки и новая сумма из тела 409 всё равно показаны.
- Given расхождение в двух позициях из трёх, when `POST /orders/`, then ответ 409, в `items` ровно эти две позиции с прежней и новой ценой, `items_total` = сумма всех трёх по новым ценам, обновлены снимки обеих, третья не тронута, заказов и субзаказов нет, и под `django_capture_on_commit_callbacks(execute=True)` писем нет.

### Review Findings

- [x] [Review][Patch] Различать варианты одного товара в уведомлении об изменении цен: по решению владельца брать их характеристики из уже загруженной корзины по `variant_id`. [frontend/src/components/checkout/CheckoutForm.tsx:60]
- [x] [Review][Patch] Не показывать устаревшую сумму корзины как актуальную после неудачной перезагрузки и не разрешать повторное оформление по такой сводке. [frontend/src/stores/orderStore.ts:92]
- [x] [Review][Patch] Проверить на двух соединениях PostgreSQL, что оформление ожидает завершения сброса акции и затем читает новые цены. [backend/tests/integration/test_checkout_price_recalc.py:243]
- [x] [Review][Patch] Проверить, что ответ 409 не расходует номер заказа, а успешная повторная отправка расходует ровно один. [backend/tests/integration/test_checkout_price_recalc.py:146]
- [x] [Review][Defer] Подтверждение цены не привязано к запросу — первый checkout обновляет общий снимок корзины и возвращает 409, но второй запрос из другой вкладки или параллельная отправка видит обновлённый снимок и создаёт заказ по новой цене, которую его пользователь ещё не подтвердил. [backend/apps/orders/services/order_create.py:121] — отложено владельцем: низкий приоритет.

**Повторный прогон, 12.11.2026:**

- [x] [Review][Defer] При одновременном импорте цен и оформлении общая блокировка акции не мешает импорту: оформление может прочитать прежнюю цену, импорт зафиксировать новую, а оформление затем создать заказ по прежней цене. Источник: edge-case-hunter; `medium`. [backend/apps/orders/services/order_create.py:100-105; backend/apps/products/services/variant_import.py:1984-2014] — отложено владельцем: низкий приоритет.
- [x] [Review][Patch] Пока после 409 перезагружается корзина, не показывать прежнюю сумму сводки как актуальную: уведомление уже содержит новую сумму, а `cartRefreshFailed` ещё не установлен. Источник: blind-hunter; `medium`. [frontend/src/stores/orderStore.ts:112-117; frontend/src/components/checkout/OrderSummary.tsx:128-148]
- [x] [Review][Patch] Различать варианты с одинаковыми или отсутствующими цветом и размером, когда вариант найден в корзине, например по SKU. Источник: blind-hunter; `low`. [frontend/src/components/checkout/CheckoutForm.tsx:50-54]
- [x] [Review][Patch] Проверить на форме, что между получением 409 и завершением задержанного `GET /cart/` кнопка оформления остаётся заблокированной. Источник: verification-gap; `medium`. [frontend/src/stores/__tests__/orderStore.test.ts:484; frontend/src/components/checkout/OrderSummary.tsx:180-181]

**Ограничения повторного прогона:** graph-impact не выполнен: Bash в песочнице Codex завершился с `CreateFileMapping`, Win32 error 5. Edge-case-hunter сообщил о недоступном дополнительном файле `review-prompts/references/deletion...`, поэтому проверка удалений неполная. Остальные результаты этого слоя получены; индекс вне песочницы актуален.

**Отклонённые замечания повторного прогона:**
- `maybe-false`, не выше `low` — сброс флага через `clearOrder`: при обычном возврате форма монтируется лишь после успешной загрузки корзины; доступный пользовательский путь обхода не показан.
- `maybe-false`, не выше `low` — повторный параллельный вызов `createOrder`: кнопка блокируется через `isSubmitting`, отдельный пользовательский путь повторной отправки не показан; гонка между вкладками уже отложена владельцем.
- `low` — после восстановления корзины сообщение 409 может описывать предыдущий состав или сумму, если корзина ещё раз изменилась параллельно; сценарий нетипичен и требует дополнительного согласования состояния.
- `low` — позднее завершение запроса после сброса состояния способно повторно выставить флаг ошибки; необходимы уход со страницы во время запроса и его поздний сбой.
- `low` — при падении конкурентного теста до `join()` поток может продолжить работу во время очистки БД; относится к редкому пути отказа теста.
- `low` — нет единого теста формы на последовательность 409 → повтор → 201; отдельные тесты покрывают показ формы и успешный повтор на сервере.
- `false` — обратный порядок позиций не подтверждает предложенную мутацию теста приоритета 400: исключение внутри `transaction.atomic` откатывает даже предварительно обновлённый снимок.
- `low` — отдельный тест отрицательной цены не добавлен; нормальная валидация цены запрещает отрицательные значения, а проверка `≤ 0` уже включает их.
- `low` — переполнение `items_total` при сумме от 10 млрд ₽ подтверждено повторно; нетипичный предел уже отклонён в предыдущем прогоне.

**Ограничение ревью:** слой graph-impact не выполнен: Bash в песочнице Codex завершился с ошибкой `CreateFileMapping`, Win32 error 5. Индекс вне песочницы проверен и актуален; это не заменяет анализ влияния.

**Отклонённые замечания:**
- `low` — переполнение `items_total` требует суммы от 10 млрд ₽; пример ревьюера с ценой 6 млрд за единицу недопустим для поля товара, а допустимый вариант с огромным количеством нетипичен и потребует дополнительной обработки пределов.
- `low` — то же переполнение, независимо отмеченное Edge Case Hunter: нетипичный объём заказа, при котором существующее поле суммы заказа также ограничено.
- `maybe-false`, не выше `low` — некорректные элементы `items` в 409 не продемонстрированы: действующий backend формирует их типизированным сериализатором.
- `maybe-false`, не выше `low` — неверное сообщение для другого вида 409: в действующем endpoint другой источник такого ответа не обнаружен.
- `low` — тест 409 не читает снимки после реального коммита из другого соединения; видимость проверена в тестовой транзакции, а фиксация задаётся штатными транзакционными механизмами Django.
- `low` — дополнительные проверки резервов, количества и состава корзины после 400/409: новые ветки изменяют только снимки через `update`; проверка счётчика номера выделена в отдельное задание.
- `low` — нет единого теста повторного оформления после 409 с несколькими группами НДС и складов: повторное оформление и разбиение успешного заказа уже проверяются отдельно.

**Третий прогон, 13.11.2026:**

- [x] [Review][Patch] Проверить отказ `price_unavailable`, когда позиция с нулевой ценой следует за позицией с положительной ценой: существующие тесты не обнаружат проверку только первой позиции. Источник: verification-gap; `medium`. [backend/tests/integration/test_checkout_price_recalc.py:196]
- [x] [Review][Patch] В тесте двух изменившихся позиций проверить длину списка и полные поля строк: преобразование в словарь скрывает дубликаты и не проверяет количество и название. Источник: blind-hunter; `low`. [backend/tests/integration/test_checkout_price_recalc.py:237]
- [x] [Review][Defer] Повторно подтверждена гонка подтверждения цены между вкладками; отдельная задача уже отложена владельцем. Источники: blind-hunter, edge-case-hunter; `medium`. [backend/apps/orders/services/order_create.py:121]
- [x] [Review][Defer] Повторно подтверждена гонка импорта цены и оформления; отдельная задача уже отложена владельцем. Источники: blind-hunter, edge-case-hunter; `medium`. [backend/apps/orders/services/order_create.py:100]

**Ограничения третьего прогона:** graph-impact не выполнен: Git Bash в песочнице Codex завершился с `CreateFileMapping`, Win32 error 5. Edge-case-hunter не нашёл дополнительный `review-prompts/references/deletion-check.md`; проверка удалений по отдельному файлу недоступна. Индекс вне песочницы актуален; это не заменяет graph-impact.

**Отклонённые замечания третьего прогона:**
- Blind hunter: `low` — переполнение `items_total` от 10 млрд ₽ уже отклонено как нетипичный предел, устранение требует дополнительной обработки.
- Blind hunter: `maybe-false`, не выше `low` — для 400 схема допускает произвольный объект, но действующий клиент не использует сгенерированный тип этого ответа; конкретный ущерб потребителю не показан.
- Blind hunter: `false` — успешный заказ при цене акции выше и ниже цены роли уже проверяет `PromoPriceCartOrderTest.test_order_and_export_use_the_lower_price_for_every_role`.
- Blind hunter: `low` — отдельный тест 409 → повтор с несколькими группами и доставкой уже отклонён; успешный повтор и разбиение с доставкой покрыты отдельно.
- Blind hunter: `low` — дополнительные проверки резервов и количества после 409 уже отклонены; предлагаемое расширение теста не показывает текущего дефекта.
- Blind hunter: `low` — незавершённый поток при падении конкурентного теста уже отклонён как редкий путь отказа.
- Blind hunter: `low` — несовпадение суммы уведомления и обновлённой корзины при параллельном изменении состава уже отклонено как нетипичный сценарий.
- Edge-case hunter: `low` — то же переполнение `items_total` при допустимой цене и большом количестве; ранее отклонено.
- Edge-case hunter: `low` — тот же редкий путь отказа конкурентного теста без `join()`; ранее отклонён.

**Четвёртый прогон, 13.11.2026:**

- [x] [Review][Patch] Переименован тест изменения цены роли: он напрямую сохраняет вариант и не проверяет импорт, хотя прежнее имя утверждало обратное. Источник: blind-hunter; `low`. [backend/tests/integration/test_checkout_price_recalc.py:123-129]
- [x] [Review][Defer] Повторно подтверждена гонка подтверждения цены между вкладками. Источники: blind-hunter, edge-case-hunter; `medium`. [backend/apps/orders/services/order_create.py:121-124] — ранее отложено владельцем: низкий приоритет.
- [x] [Review][Defer] Повторно подтверждена гонка импорта цены и оформления. Источники: blind-hunter, edge-case-hunter; `medium`. [backend/apps/orders/services/order_create.py:100-105] — ранее отложено владельцем: низкий приоритет.

**Ограничения четвёртого прогона:** graph-impact не выполнен: Git Bash в песочнице Codex завершился с `CreateFileMapping`, Win32 error 5. Edge-case-hunter не нашёл дополнительный файл `review-prompts/references/deletion-check.md`; проверка удалений неполная. Индекс вне песочницы актуален, но это не заменяет graph-impact.

**Отклонённые замечания четвёртого прогона:**

- Blind hunter, `low` — переполнение `items_total` от 10 млрд ₽: нетипичный предел, ранее отклонён; исправление требует дополнительной обработки.
- Blind hunter, `low` — уведомление после перезагрузки может описывать предыдущую сумму при параллельном изменении корзины; нетипичный сценарий, ранее отклонён.
- Blind hunter, `low` — фоновый поток теста может остаться активным при ошибке до `join()`; редкий путь отказа, ранее отклонён.
- Blind hunter, `low` — нет единого теста формы 409 → повтор → 201; успешный повтор на сервере и поведение формы проверяются отдельно.
- Blind hunter, `maybe-false`, не выше `low` — схема 409 допускает произвольный `code`, но сервер всегда задаёт `prices_changed`; ущерб конкретному потребителю не показан.
- Blind hunter, `low` — нет отдельного теста второго 409 после нового изменения цены; те же проверки пересчёта и обновления снимка уже применяются к каждому запросу.
- Blind hunter, `low` — нет теста сбоя второго обновления снимка; ветка находится внутри `transaction.atomic`, а успешное обновление нескольких позиций проверено.
- Edge-case hunter, `low` — то же переполнение `items_total` от 10 млрд ₽; ранее отклонено.
- Edge-case hunter, `low` — поздний ответ после `clearOrder` может повторно выставить `cartRefreshFailed`; требуется уход со страницы во время запроса и поздний сбой, ранее отклонено.
- Edge-case hunter, `low` — тот же редкий путь отказа конкурентного теста без `join()`; ранее отклонён.
- Acceptance auditor, `low` — английские фразы в журнале изменений спецификации нарушают правило языка документации; исправление касается самой проверяемой спецификации и по правилам триажа отклоняется.

Проверка исправления: переименованный тест прошёл в Docker с PostgreSQL (`1 passed`).

## Implementation Notes

## Spec Change Log

- 2026-11-12, решение владельца после реализации: порядок в catch `createOrder` изменён на «сообщение и `priceChanges` сразу, затем `fetchCart()`» (было: `priceChanges`, `fetchCart()`, затем сообщение). Причина: при 5xx на `GET /cart/` apiClient повторяет запрос с паузами 1/2/4 с, и панель «Цены изменились» появлялась бы только через ~7 с. Кнопка оформления остаётся заблокированной (`isSubmitting`) до конца перезагрузки корзины.

## Review Triage Log

## Verification

**Commands:**
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit && npx vitest run src/components/checkout src/stores src/services` -- expected: без ошибок.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` -- expected: зелёные (включая `test_b2b_workflow.py`, `test_pricing_integration.py`, `test_b2c_workflow.py` без правок).
- `python manage.py check_openapi_sync` в контейнере backend -- expected: схема совпадает.

## Dev Agent Record

### Debug Log

- GitNexus перед правками (индекс `939e3f7`): `resolve_role_price`, `get_price_for_user`, `get_regular_price_for_user`, `OrderCreateService.create`, `parseApiError` — risk LOW, затронутых процессов нет; у `OrderViewSet.create` и `OrderCreateSerializer.create` статических вызывающих нет (их вызывает DRF). `detect-changes --scope all` — только ожидаемые символы, задеты потоки `CheckoutPageClient → …`; `check --cycles` — два цикла из базовой линии, новых нет.
- Полное `ProductVariant.save()` не пишет `promo_price` (снимает акцию только импорт через `update_fields`) — тест «акция закончилась» снимает её так же.
- drf-spectacular недетерминирован в порядке методов: полная перегенерация `openapi.yaml` давала +262/−189 строк перестановок. Сгенерированные блоки `/orders/` POST и схемы `OrderPriceChange`/`OrderPricesChanged` перенесены в прежний текст; структурное сравнение старой и новой схемы — только эти изменения; `check_openapi_sync` — «Контракт синхронен».
- Примеры у ответа без схемы drf-spectacular отбрасывает (пример «Пустая корзина» никогда не попадал в контракт). 400 получил `response=OpenApiTypes.OBJECT`, теперь в контракте оба примера 400.
- Сбой `GET /cart/` с 5xx apiClient повторяет с паузами 1/2/4 с: при исходном порядке спеки (`fetchCart`, затем `error`) панель «Цены изменились» появлялась бы через ~7 с. По решению владельца порядок изменён (Spec Change Log): сообщение выставляется до `fetchCart`. В тесте стора сбой корзины — 404 (без повторов).
- Пункты ревью (12.11.2026). GitNexus (индекс `939e3f7`, up-to-date): `OrderSummary` и `PriceChangesMessage` — risk LOW, один прямой вызывающий `CheckoutFormFields`, поток чекаута; у `useOrderStore` граф вызывающих не видит — поиском: `CheckoutForm`, `CheckoutPageClient` и тесты, правки аддитивные.
- Тест на двух соединениях проверен мутацией: без `lock_promo_state(shared=True)` оформление тоже встаёт в ожидание (на строках вариантов, уже прочитав цены) и после коммита сброса создаёт заказ по старой акции — 201 вместо 409. Поэтому проверяется исход (409 с новой ценой), а не только факт ожидания. Тест с mock-блокировкой заменён этим.
- Тест номера заказа проверен мутацией: выдача номера до проверок даёт `customer_code` пользователю уже на 409 — тест краснеет. Фронтенд-правки проверены так же: без характеристик и без флага устаревшей корзины падают 5 тестов.
- Пункты повторного прогона ревью (12.11.2026). GitNexus (индекс `939e3f7`, up-to-date): `OrderSummary`, `priceChangeLabel`, `PriceChangesMessage`, `CheckoutFormFields` — risk LOW, по одному прямому вызывающему, поток чекаута. Красная фаза — 5 падений (3 в сторе, 2 на форме). Мутация: `pricesOutdated={cartRefreshFailed}` без `cartRefreshing` — тест формы краснеет, сводка показывает «2 × 2 500 ₽» во время перезагрузки.
- Прежде кнопку «Обновить корзину» вела `cartStore.isLoading`; теперь сводку ведёт `orderStore.cartRefreshing`: `isLoading` корзины выставляют и другие действия (`addItem` и т. п.), а нужен признак именно перезагрузки цен.
- Пункты третьего прогона ревью (13.11.2026). GitNexus (индекс `939e3f7`, up-to-date). Правки только в `test_checkout_price_recalc.py`, продуктовый код не менялся — `impact` не требуется. Мутации сервиса (копия файла, затем восстановление с `cmp`): проверка цены только у первой позиции — краснеет `test_zero_price_wins_over_price_change[zero-after-positive]`; дубль строки в `items` и `quantity=1` — краснеет `test_two_of_three_changed`.

### Completion Notes

- `pricing_policy.PricedField(price, field)`; `resolve_role_price` отдаёт цену и поле; `resolve_user_price(variant, user)` — `min(роль, акция)`, при равенстве `promo_price`; `get_price_for_user` и `get_regular_price_for_user` возвращают `.price`, контракт `Decimal` прежний.
- `OrderCreateService.create`: `lock_promo_state(shared=True)` первым делом; цена каждой позиции — `resolve_user_price`; до номера заказа: цена ≤ 0 → `ValidationError({"code": "price_unavailable", "detail": …})`, затем расхождение со снимком → `CartItem.objects.filter(pk).update(price_snapshot=…)` и возврат `PricesChanged(items, items_total)` без исключения. Суммы мастера, групп и `OrderItem.unit_price` — из `PricedField`.
- `OrderViewSet.create`: при `PricesChanged` — 409 с телом `OrderPricesChangedSerializer` (суммы строками `"800.00"`); `extend_schema` дополнен 409 и примером 400 `price_unavailable`.
- Фронтенд: `OrderApiError` (`status`, `code`, `priceChanges`); `parseApiError` разбирает 409; `orderStore.priceChanges` (сброс при отправке и `clearOrder`), при `prices_changed` — сразу сообщение и `priceChanges`, затем `fetchCart()`; `CheckoutForm` выводит в `InfoPanel` строки «товар: было → стало» и «Новая сумма товаров» из тела 409.
- Тесты: backend — `test_checkout_price_recalc.py` (матрица I/O + AC «две из трёх» с перехватом on_commit + общая блокировка акции), цепочка и равенство в `test_pricing_policy.py`, `PricesChanged` без писем в `test_order_create_email_on_commit.py`; переделаны опоры на снимок корзины (`test_cart_order_integration.py`, `test_order_serializers.py`, `test_vat_warehouse_split.py`). Frontend — сервис (409/400), стор (409, сообщение видно до окончания перезагрузки корзины, сбой корзины, сброс, 400), `CheckoutForm.priceChanges.test.tsx` на настоящих сторах.
- Проверки: backend полный прогон `-n 4 -m "not performance and not slow"` — 5596 passed, 80 skipped, 0 failed; black/flake8/isort по изменённым файлам чисто, mypy — 0 ошибок (669 файлов); `check_openapi_sync` — синхронен. Frontend: `format:check`, `lint`, `tsc --noEmit` чисто; `vitest run` целиком — 4138 passed, 16 skipped; после смены порядка в сторе — `vitest run src/components/checkout src/stores src/services` 358 passed, format/lint/tsc чисто.
- ✅ Resolved review finding [Patch]: варианты одного товара различаются — строка «было → стало» дополнена характеристиками «цвет / размер» из загруженной корзины по `variant_id` (`priceChangeLabel`); варианта нет в корзине — только название.
- ✅ Resolved review finding [Patch]: после неудачной перезагрузки корзины стор ставит `cartRefreshFailed`; `OrderSummary` в режиме `pricesOutdated` скрывает цены строк и суммы, показывает предупреждение и кнопку «Обновить корзину» (`orderStore.refreshCart`), кнопка оформления заблокирована; `createOrder` при флаге отказывает без запроса. Флаг снимают успешная перезагрузка и `clearOrder`.
- ✅ Resolved review finding [Patch]: `TestCheckoutWaitsForPromoReset` — сброс акции в транзакции основного соединения, оформление во втором соединении ждёт блокировку (`pg_stat_activity`), после коммита получает 409 с ценой без акции, снимок обновлён, заказа нет.
- ✅ Resolved review finding [Patch]: `test_conflict_does_not_consume_order_number` — после 409 у пользователя нет `customer_code`, счётчики `CustomerCodeSequence` и `CustomerOrderSequence` не тронуты; после успешного повтора — один счётчик с `last_sequence = 1` и номер `…YY001`.
- ✅ Resolved review finding [Patch, medium]: стор ставит `cartRefreshing` на время перезагрузки корзины (после 409 и по кнопке «Обновить корзину», общий helper `refreshCartPrices`); форма передаёт в сводку `pricesOutdated = cartRefreshFailed || cartRefreshing`, сводка в это время скрывает цены строк и суммы и показывает «Загружаем актуальные цены корзины…» (`prices-refreshing`); после неудачи — прежний блок с кнопкой. `clearOrder` снимает и этот флаг.
- ✅ Resolved review finding [Patch, low]: `priceChangeLabel` добавляет «арт. SKU», если в корзине есть другая позиция с тем же названием и теми же (или пустыми) характеристиками; однозначные строки — без артикула.
- ✅ Resolved review finding [Patch, medium]: тест формы с задержанным `GET /cart/` — после 409 и до ответа корзины кнопка оформления заблокирована, сумм и прежних цен в сводке нет, показано «Загружаем актуальные цены корзины»; после ответа — новая сумма и кнопка доступна. В тесте стора — `cartRefreshing` и `isSubmitting` во время перезагрузки, отдельный тест `refreshCart`.
- Проверки после пунктов ревью: frontend `format:check`, `lint`, `tsc --noEmit` чисто, `vitest run` целиком — 4144 passed, 16 skipped; backend `test_checkout_price_recalc.py` — 11 passed, полный прогон `-n 4 -m "not performance and not slow"` — 5597 passed, 80 skipped, 0 failed; black/flake8/isort по новому тестовому файлу чисто. GitNexus `detect-changes --scope all` — задеты только потоки `CheckoutPageClient → …`; `check --cycles` — два цикла базовой линии, новых нет.
- Проверки после пунктов повторного прогона: frontend `format:check`, `lint`, `tsc --noEmit` чисто, `vitest run` целиком — 4147 passed, 16 skipped; backend не менялся, полный прогон `-n 4 -m "not performance and not slow"` — 5597 passed, 80 skipped, 0 failed. GitNexus `detect-changes --scope all` — задеты только потоки `CheckoutPageClient → …`; `check --cycles` — два цикла базовой линии, новых нет.

- ✅ Resolved review finding [Patch, medium]: `test_zero_price_wins_over_price_change` параметризован порядком позиций (`zero-first`, `zero-after-positive`): позиция с нулевой ценой после позиции с положительной даёт 400 `price_unavailable`, снимки обеих не тронуты.
- ✅ Resolved review finding [Patch, low]: `test_two_of_three_changed` сравнивает список `items` целиком — длина, отсутствие дублей и все поля строки (`variant_id`, `product_name`, `quantity`, `old_price`, `new_price`).
- Проверки после пунктов третьего прогона: `test_checkout_price_recalc.py` — 12 passed; полный прогон backend `-n 4 -m "not performance and not slow"` — 5598 passed, 80 skipped, 0 failed; black/isort/flake8 по тестовому файлу чисто. Frontend не менялся. GitNexus `detect-changes --scope all` — задеты только потоки `CheckoutPageClient → …`; `check --cycles` — два цикла базовой линии, новых нет.

### File List

- `backend/apps/products/pricing_policy.py`
- `backend/apps/products/models.py`
- `backend/apps/orders/services/order_create.py`
- `backend/apps/orders/serializers.py`
- `backend/apps/orders/views.py`
- `backend/apps/products/tests/unit/test_pricing_policy.py`
- `backend/apps/bonuses/tests/test_vat_warehouse_split.py`
- `backend/tests/integration/test_checkout_price_recalc.py` (новый)
- `backend/tests/integration/test_cart_order_integration.py`
- `backend/tests/integration/test_order_create_email_on_commit.py`
- `backend/tests/unit/test_serializers/test_order_serializers.py`
- `docs/api/openapi.yaml`
- `frontend/src/types/api.generated.ts`
- `frontend/src/services/ordersService.ts`
- `frontend/src/stores/orderStore.ts`
- `frontend/src/components/checkout/CheckoutForm.tsx`
- `frontend/src/components/checkout/OrderSummary.tsx`
- `frontend/src/__mocks__/handlers/ordersHandlers.ts`
- `frontend/src/services/__tests__/ordersService.test.ts`
- `frontend/src/stores/__tests__/orderStore.test.ts`
- `frontend/src/components/checkout/__tests__/CheckoutForm.priceChanges.test.tsx` (новый)
- `_bmad-output/implementation-artifacts/spec-checkout-price-recalc.md`

## Change Log

- 2026-11-12: реализация — пересчёт цены при оформлении, 409 `prices_changed` и 400 `price_unavailable`, контракт и типы, обработка на чекауте; статус → review.
- 2026-11-12: по решению владельца сообщение «Цены изменились» показывается до перезагрузки корзины; спека и тест стора обновлены.
- 2026-11-12: Addressed code review findings - 4 items resolved: характеристики варианта в строках «было → стало»; режим устаревших цен в сводке с блокировкой оформления; тест ожидания сброса акции на двух соединениях; тест расхода номера заказа.
- 2026-11-12: Addressed code review findings - 3 items resolved (повторный прогон): сводка не показывает прежнюю сумму, пока корзина перезагружается; артикул в строках «было → стало» для неразличимых вариантов; тест блокировки оформления на время задержанной перезагрузки корзины.
- 2026-11-13: Addressed code review findings - 2 items resolved (третий прогон): тест `price_unavailable` для нулевой цены после положительной; полная проверка строк `items` в тесте «две из трёх».
