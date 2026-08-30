---
title: 'Автогенерация customer_code при оформлении заказа'
type: 'bugfix'
created: '2026-07-11'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '1c20c5fc33c1cd96b201407b96e2c5009e48ef0d'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Checkout требует `User.customer_code` (`orders/serializers.py:204`), но это поле нигде не заполняется автоматически — ни при регистрации, ни при импорте контрагентов из 1С (в выгрузке `data/import_1c/contragents/*.xml` вообще нет подходящего 5-значного поля кода клиента, только GUID и опциональный ОКПО). На проде из 4621 пользователя `customer_code` есть только у одного (тестовый аккаунт), т.е. оформление заказа сейчас недоступно практически никому.

**Approach:** Портал сам присваивает `customer_code` лениво и атомарно в момент первого обращения к `OrderNumberingService.next_master_number()` (внутри уже существующей транзакции создания заказа, на уже заблокированной через `select_for_update` строке пользователя) — по аналогии с существующим счётчиком `CustomerOrderSequence`. Новый глобальный singleton-счётчик выдаёт следующий свободный 5-значный код; существующий `customer_code`, если он уже проставлен вручную (админом/будущим импортом), не трогается.

## Boundaries & Constraints

**Always:** генерация кода происходит внутри той же атомарной транзакции и на той же заблокированной строке пользователя, которую уже лочит `next_master_number()` — не открывать вторую отдельную транзакцию/блокировку; если у пользователя уже есть валидный `customer_code`, он используется как есть и никогда не перезаписывается; счётчик читается через `select_for_update()` по образцу `OrderNumberingService._get_locked_counter` (тот же файл, тот же стиль).

**Ask First:** нет открытых решений — источник и точка генерации подтверждены человеком 2026-07-11.

**Never:** не писать backfill-миграцию для существующих 4620 пользователей без кода — код присваивается лениво при их первом заказе, это осознанное решение (упрощает scope, не трогает данные без необходимости); не менять формат/маппинг импорта контрагентов из 1С — там неоткуда брать этот код; не трогать `_link_matched_1c_customer` и остальной flow регистрации/привязки 1С-клиента (`spec-1c-client-portal-linking.md`) — он не источник этого бага и вне скоупа; не делать код изменяемым после первого заказа — существующая защита в `User.save()` (`orders.exists()` guard) остаётся как есть.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Оформление заказа, у пользователя нет `customer_code` | `user.customer_code` пусто/None, корзина непустая | Присваивается следующий свободный 5-значный код (напр. `00001`), заказ создаётся с этим кодом в `customer_code_snapshot` | N/A |
| Оформление заказа, `customer_code` уже проставлен | `user.customer_code = "05000"` (задан вручную) | Используется существующий код, счётчик не трогается, новый код не выдаётся | N/A |
| Два разных пользователя без кода оформляют заказ друг за другом | Оба `customer_code` пусты | Каждый получает свой уникальный код (напр. `00001` и `00002`), коллизий нет | N/A |
| Счётчик исчерпан (все 99999 кодов выданы) | `CustomerCodeSequence.last_value == 99999` | Заказ не создаётся | `ValidationError` (аналог `OrderNumberSequenceExhausted`) |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/models.py` -- новая модель `CustomerCodeSequence` (singleton-счётчик, по образцу `CustomerOrderSequence`)
- `backend/apps/orders/migrations/` -- новая миграция для `CustomerCodeSequence` + data-migration, сидирующая `last_value` текущим максимумом среди `users.customer_code` (на проде сейчас `00000` → сид `0`, безопасно)
- `backend/apps/orders/services/order_numbering.py` -- `OrderNumberingService.next_master_number()`: вместо `raise MissingCustomerCodeError` при пустом коде -- вызов нового `_assign_customer_code(locked_user)`; удалить класс `MissingCustomerCodeError` (после фикса не используется); добавить `CustomerCodeSequenceExhausted(OrderNumberError)`
- `backend/apps/orders/serializers.py:203-205` -- убрать дублирующую раннюю проверку `if not customer_code: raise ValidationError(...)` в `OrderCreateSerializer.validate()` -- источник правды теперь `OrderNumberingService`
- `backend/tests/unit/test_order_numbering.py` -- переписать `test_next_master_number_requires_customer_code` на автоприсвоение; добавить тест уникальности кодов для двух пользователей подряд
- `backend/tests/integration/test_orders_api.py` -- переписать `test_create_order_user_without_customer_code_failure` на успешное создание заказа с автоприсвоенным кодом

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/orders/models.py` -- добавить `CustomerCodeSequence(models.Model)`: `last_value = PositiveIntegerField(default=0)`, singleton (`pk=1`) -- источник атомарной выдачи кодов, паттерн идентичен `CustomerOrderSequence`
- [x] `backend/apps/orders/migrations/00XX_add_customer_code_sequence.py` -- `CreateModel` + `RunPython`, сидирующий `last_value = max(int(customer_code) for users with customer_code) or 0` -- защита от коллизий, если в БД окружения уже есть ручные коды
- [x] `backend/apps/orders/services/order_numbering.py` -- `next_master_number()`: если `is_valid_customer_code(customer_code)` ложно -- вызвать `_assign_customer_code(locked_user)` вместо `raise MissingCustomerCodeError`; новый classmethod `_assign_customer_code(locked_user)` лочит `CustomerCodeSequence` через `select_for_update()` (get-or-create по образцу `_get_locked_counter`), инкрементирует, форматирует `f"{next_value:05d}"`, сохраняет на `locked_user` (`update_fields=["customer_code"]`) и возвращает код; при `next_value > 99999` -- `raise CustomerCodeSequenceExhausted`
- [x] `backend/apps/orders/services/order_numbering.py` -- удалить неиспользуемый `MissingCustomerCodeError`, добавить `CustomerCodeSequenceExhausted(OrderNumberError)`
- [x] `backend/apps/orders/serializers.py` -- удалить блок `if not getattr(user, "customer_code", ""): raise ValidationError(...)` в `OrderCreateSerializer.validate()` (строки 203-205) -- проверка стала избыточной и блокирующей
- [x] `backend/tests/unit/test_order_numbering.py` -- переписать `test_next_master_number_requires_customer_code` в `test_next_master_number_auto_assigns_customer_code`: пользователь без кода получает валидный `\d{5}` код и заказ создаётся; добавить `test_next_master_number_preserves_existing_customer_code` и `test_next_master_number_assigns_unique_codes_to_different_users`
- [x] `backend/tests/integration/test_orders_api.py` -- переписать `test_create_order_user_without_customer_code_failure` в `test_create_order_auto_assigns_customer_code_when_missing`: ожидать `201`, а не `400`, и проверить, что у пользователя в БД появился `customer_code`
- [x] `docs/architecture/09-database-schema.md` -- в разделе "Дополнение по заказам (2026-05-02)" добавить одно предложение: `customer_code` теперь присваивается автоматически при первом заказе, если отсутствует

**Acceptance Criteria:**
- Given авторизованный пользователь без `customer_code` и непустой корзиной, when оформляет заказ, then заказ создаётся успешно, `user.customer_code` в БД становится валидным 5-значным кодом, `order.customer_code_snapshot` совпадает с этим кодом
- Given пользователь с уже проставленным `customer_code`, when оформляет заказ, then код не меняется и счётчик `CustomerCodeSequence.last_value` не инкрементируется
- Given два разных пользователя без кода оформляют заказы последовательно, then у них разные `customer_code`, конфликта уникальности нет
- Given `CustomerCodeSequence.last_value == 99999`, when пользователь без кода пытается оформить заказ, then заказ не создаётся и возвращается понятная ошибка

## Design Notes

Счётчик — singleton-строка (`pk=1`), а не per-role/per-year как `CustomerOrderSequence`: код клиента выдаётся один раз за всё время жизни пользователя, а не по годовому циклу. Get-or-create с обработкой `IntegrityError` при гонке — тот же паттерн, что и `OrderNumberingService._get_locked_counter` (`order_numbering.py:168-177`), для консистентности стиля файла.

Данные с прода проверены (2026-07-11): `SELECT MIN(customer_code), MAX(customer_code) FROM users` → `00000`/`00000`, только 1 из 4621 пользователей имеет код. Data-migration сидирует счётчик текущим максимумом (а не хардкодит 0), чтобы миграция была идемпотентна и корректна в любом окружении (dev/staging могут иметь другие ручные коды).

## Verification

**Commands:**
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest backend/tests/unit/test_order_numbering.py backend/tests/integration/test_orders_api.py -v` -- expected: все зелёные, включая новые тесты автоприсвоения
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest backend/tests/integration/test_cart_order_integration.py backend/tests/integration/test_b2b_workflow.py backend/tests/integration/test_b2c_workflow.py -v` -- expected: регресс не сломан (эти тесты создают пользователей с уже заданным `customer_code`)

**Manual checks (if no CLI):**
- В Django Admin создать пользователя без `customer_code`, авторизоваться под ним, добавить товар в корзину и оформить заказ -- убедиться, что заказ создался и в админке у пользователя появился `customer_code`

## Suggested Review Order

**Автоприсвоение кода: точка входа и коллизии**

- Вместо блокирующей ошибки -- ленивый вызов автоприсвоения на уже заблокированной строке пользователя.
  [`order_numbering.py:127`](../../backend/apps/orders/services/order_numbering.py#L127)

- Ядро логики: инкремент singleton-счётчика + retry на `IntegrityError` внутри savepoint, чтобы коллизия с кодом, проставленным в обход счётчика (например, вручную в админке), не отравляла внешнюю транзакцию создания заказа.
  [`order_numbering.py:182`](../../backend/apps/orders/services/order_numbering.py#L182)

- Get-or-create счётчика с блокировкой -- паттерн скопирован с уже проверенного `_get_locked_counter` для `CustomerOrderSequence`.
  [`order_numbering.py:212`](../../backend/apps/orders/services/order_numbering.py#L212)

**Схема данных**

- Новая singleton-модель счётчика (`pk=1`), без привязки к году/клиенту -- код выдаётся один раз за жизнь пользователя.
  [`models.py:395`](../../backend/apps/orders/models.py#L395)

- Data-migration сидирует счётчик текущим максимумом среди существующих `customer_code`, а не хардкодит 0 -- корректно в любом окружении.
  [`0016_customercodesequence.py:10`](../../backend/apps/orders/migrations/0016_customercodesequence.py#L10)

**Удаление избыточной блокировки чекаута**

- Ранняя проверка `customer_code` в сериализаторе стала избыточной и удалена -- источник правды теперь только `OrderNumberingService`.
  [`serializers.py:193`](../../backend/apps/orders/serializers.py#L193)

**Тесты**

- Happy path: пользователь без кода получает валидный код при первом заказе.
  [`test_order_numbering.py:39`](../../backend/tests/unit/test_order_numbering.py#L39)

- Regression-guard на находку ревью: код, занятый в обход счётчика, не роняет чекаут в 500, а пропускается.
  [`test_order_numbering.py:78`](../../backend/tests/unit/test_order_numbering.py#L78)

- End-to-end через API: чекаут больше не возвращает 400 для пользователя без кода.
  [`test_orders_api.py:139`](../../backend/tests/integration/test_orders_api.py#L139)
