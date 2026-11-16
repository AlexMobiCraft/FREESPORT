---
title: 'Временно отключить выбор способа доставки при оформлении заказа'
type: 'feature'
created: '2026-11-16'
status: 'done'
route: 'dispatch'
baseline_commit: 'e26820b26e9822312ca00bffe20b307a731636a9'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На `/checkout` покупатель обязан выбрать способ доставки (радиокнопки из `/delivery/methods/`). Владелец временно убирает выбор: способ и стоимость доставки согласует менеджер.

**Approach:** Константой во фронтенде скрыть выбор и показать плашку; заказ создавать с новым способом `by_agreement` («Согласуется с менеджером», стоимость 0 ₽).

**Решения владельца (16.11.2026):**
1. В заказ пишется новое значение `by_agreement` — «Согласуется с менеджером», `delivery_cost` = 0.
2. На месте блока — плашка «Способ и стоимость доставки согласует менеджер после оформления заказа».
3. Выбор возвращается переключением константы во фронтенде (PR + релиз), не из админки.

## Boundaries & Constraints

**Always:** заказ создаётся без ошибки валидации `deliveryMethod`; подписи уже созданных заказов не меняются, кроме унификации подписи в письмах (см. задачу `tasks.py`); при включённой константе форма работает как сейчас.

**Never:** не удалять `DeliveryOptions.tsx`, `deliveryService`, app `delivery`; не добавлять `by_agreement` в справочник `DeliveryMethod`; не трогать экспорт в 1С (`order_export.py` способ доставки не выгружает), блок адреса, способ оплаты; миграция — только `AlterField` choices.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Оформление | Выбор выключен, корзина не пуста, адрес заполнен | Радиокнопок нет, есть плашка; `delivery_method=by_agreement`, `delivery_cost=0` | N/A |
| Черновик | Выбор выключен, в черновике `deliveryMethod: 'courier'` | В заказ уходит `by_agreement` | N/A |
| Возврат выбора | Выбор включён, в черновике `deliveryMethod: 'by_agreement'` | Значение сброшено, покупатель выбирает сам | Ошибка «Выберите способ доставки» |
| Отображение | Заказ с `by_agreement` | Карточка, страница успеха, PDF, оба письма: «Согласуется с менеджером» | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/checkout/CheckoutForm.tsx` -- `defaultValues` `:173-193`, `...initialDraft?.values` последним перекрывает `deliveryMethod`; `<DeliveryOptions>` `:461`; черновик пишется из `form.getValues()` `:403`. `/delivery/methods/` запрашивает только `DeliveryOptions.tsx:41`.
- `backend/apps/orders/models.py:86-92` `DELIVERY_METHODS`; последняя миграция `orders/0017_orderitem_price_type_snapshot.py`. Админка и фильтры берут choices из модели.
- `backend/apps/orders/serializers.py:298-307` `calculate_delivery_cost`.
- `backend/apps/orders/tasks.py:123,262` -- две разошедшиеся карты подписей (во второй нет `transport_schedule`); `admin.py:244` уже использует `get_delivery_method_display()`.
- Подписи фронтенда: `utils/orderPdfExport.ts:67` `getDeliveryMethodLabel` (её же зовёт `OrderDetail.tsx:186`; GitNexus risk HIGH — правка только добавляет ключ), `checkout/OrderSuccessView.tsx:43`, тип `types/order.ts:22`.
- `docs/api/openapi.yaml:3164` `DeliveryMethodEnum`; `check_openapi_sync` сверяет разобранную структуру буквально, включая `description`.
- Тесты backend заказов — в `backend/tests/` (`apps/orders/tests/` нет).

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/orders/models.py` + `migrations/0018_*` -- добавить `("by_agreement", "Согласуется с менеджером")`, `makemigrations` в контейнере.
- [x] `backend/apps/orders/serializers.py` -- явный `"by_agreement": 0` в `calculate_delivery_cost`.
- [x] `backend/apps/orders/tasks.py` -- обе карты заменить на `order.get_delivery_method_display()`; письмо клиенту для `transport_schedule` станет «Транспортная компания (по расписанию)».
- [x] `backend/tests/unit/test_serializers/test_order_serializers.py`, `backend/tests/integration/test_order_create_email_on_commit.py` -- заказ с `by_agreement`: `delivery_cost=0`, подпись в тексте письма.
- [x] `docs/api/openapi.yaml` -- `by_agreement` в `DeliveryMethodEnum` и строка `description` в формате drf-spectacular; затем `npm run generate:types`.
- [x] `docs/architecture/03-api-specification.md:1544,1587`, `docs/database/er-diagram.md:332` -- дописать код в перечисления.
- [x] `frontend/src/config/checkout.ts` -- `DELIVERY_METHOD_SELECTION_ENABLED = false`, `DEFAULT_DELIVERY_METHOD = 'by_agreement'`, комментарий, как вернуть выбор.
- [x] `frontend/src/components/checkout/CheckoutForm.tsx` -- выключено: `deliveryMethod = DEFAULT_DELIVERY_METHOD` после спреда черновика, вместо `DeliveryOptions` секция «Способ доставки» с плашкой (стиль плашки из `DeliveryOptions`). Включено: `by_agreement` из черновика сбрасывать в `''`.
- [x] `frontend/src/types/order.ts`, `utils/orderPdfExport.ts`, `checkout/OrderSuccessView.tsx` -- код и подпись `by_agreement`.
- [x] Vitest: в `CheckoutForm.test.tsx`, `.integration.test.tsx`, `.draft.test.tsx`, `.priceChanges.test.tsx` сценарии с выбором оставить под `vi.mock('@/config/checkout', … ENABLED: true)`; новый `CheckoutForm.deliveryDisabled.test.tsx` -- I/O-матрица (плашка, нет запроса методов, payload `by_agreement`, черновик в обе стороны); подписи в `OrderSuccessView.test.tsx`, `OrderDetail.test.tsx`.
- [x] `frontend/tests/e2e/checkout.spec.ts`, `pages/CheckoutPage.ts` -- заполнение формы без выбора доставки; `selects delivery method` (`:437`), `requires delivery method selection` (`:625`), `handles delivery methods loading error` (`:788`) -- `test.skip` с причиной; новый сценарий: плашка видна.

**Acceptance Criteria:**
- Given выбор выключен, when покупатель открывает `/checkout`, then запроса `/delivery/methods/` нет и радиокнопок нет.
- Given выбор выключен, when заказ отправлен, then в payload `delivery_method: 'by_agreement'`, а итог заказа не содержит стоимости доставки.
- Given константа = `true`, when страница открыта, then блок выбора работает как до правки.

## Implementation Notes

- Миграция `orders/0018_order_delivery_method_by_agreement.py` — один `AlterField` choices, сгенерирована `makemigrations` в тестовом контейнере.
- `CheckoutForm.tsx`: начальный способ считает `initialDeliveryMethod()` после спреда черновика; дублирующий ключ `deliveryMethod` до спреда убран. При выключенном выборе `DeliveryOptions` не монтируется, поэтому `/delivery/methods/` не запрашивается; поле в RHF не зарегистрировано и уходит из `defaultValues`.
- `DELIVERY_METHOD_SELECTION_ENABLED` объявлен с типом `boolean`, чтобы TS не сужал его до литерала `false` и не считал ветку выбора мёртвой.
- E2E: пропуски сделаны условными (`test.skip(!DELIVERY_METHOD_SELECTION_ENABLED, причина)`), клики по `courier` в остальных сценариях — через `chooseDeliveryMethod()`, который ничего не делает при выключенном выборе. После включения флага сценарии с выбором заработают без правок, а новый сценарий с плашкой пропустится.
- Mutation-проверка: при отключённой подмене черновика и без сброса `by_agreement` падают 2 теста `CheckoutForm.deliveryDisabled.test.tsx`.

## Spec Change Log

## Review Triage Log

Итерация 0 (слои: blind-hunter, edge-case-hunter, verification-gap, graph-impact).

| # | Слой | Находка | Вердикт | Обоснование | Маршрут |
|---|------|---------|---------|-------------|---------|
| 1 | blind, edge | `OrderDetail.tsx:170` пишет «Доставка: Бесплатно» для `by_agreement` (cost 0) | medium | Тернарник `> 0 ? цена : 'Бесплатно'` не знает про `by_agreement`; карточка противоречит подписи «Согласуется с менеджером» в ней же | patch |
| 2 | verification-gap | Нет теста: при включённом выборе обычный способ из черновика восстанавливается | gap (pre-verified) | Ветка `return draftValue` в `initialDeliveryMethod` не покрыта; упрощение до сброса всегда прошло бы все тесты | patch |
| 3 | verif-gap other, edge, blind | `test_by_agreement_label_in_both_emails`: `assert delivery_cost == 0` тавтологичен | low | Стоимость передаётся в `OrderCreateService` готовой (`Decimal("0")`), тариф не вызывается; реальная проверка — unit-тест сериализатора | patch (удалить assert) |
| 4 | blind | `DEFAULT_DELIVERY_METHOD` типизирован как `string` | low | Опечатку в коде способа TS не поймает; исправление — аннотация `DeliveryMethodCode` | patch |
| 5 | blind, edge | Backend не проверяет флаг: API принимает `courier` при выключенном выборе / `by_agreement` при включённом | false | Решение владельца №3 — переключатель только во фронтенде; серверная блокировка интентом не предусмотрена | reject |
| 6 | blind, verif-gap other | Подпись `transport_schedule` в письме расходится с сайтом; нет теста | false | Унификация подписи в письмах прямо задана интентом (Always) | reject |
| 7 | blind | Пропал ключ `"transport"` (0001) — в письме будет голый код | low | Код выведен из choices давно; встретить в новых письмах маловероятно, фикс — лишняя ветка | reject |
| 8 | blind | Текст письма «Администратор свяжется» / «Уточняется администратором» vs «менеджер» | false | Формулировки не противоречат интенту: стоимость уточняется после заказа; плохого исхода нет | reject |
| 9 | blind | Две карты подписей во фронтенде, `Record<string,string>` | low | Существовало до правки; обе карты синхронно дополнены | reject |
| 10 | blind | `initialDeliveryMethod` сравнивает с константой, а не с литералом | low | Спекулятивно: константу менять не планируется; с п.4 тип зафиксирован | reject |
| 11 | blind | `CheckoutPage.deliveryAgreementNotice` не используется, `fillForm` не знает флаг | low | Page object не импортируется ни одним spec; вреда нет | reject |
| 12 | blind | E2E не проверяет подпись на странице успеха | false | Подпись покрыта `OrderSuccessView.test.tsx` | reject |
| 13 | blind | `er-diagram.md` фиксирует состояние UI | low | Косметика документации | reject |
| 14 | blind | 1С не получает признак `by_agreement` | false | Интент (Never) исключает экспорт в 1С | reject |
| 15 | blind | В диффе нет `api.generated.ts` и спеки | false | Исключены намеренно; синхронность контракта проверена `check_openapi_sync` и `tsc` | reject |
| 16 | graph-impact | Слой не выполнен: `status` = stale из-за незакоммиченного diff | maybe-false | Upstream-impact изменённых символов снят до правок на индексе `e26820b` (LOW; `getDeliveryMethodLabel` HIGH — только новый ключ); новых циклов нет по отчёту исполнителя. Перепроверить после коммита и `analyze --force` | reject (сбой слоя, зафиксирован) |

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/unit/test_serializers/test_order_serializers.py tests/integration/test_order_create_email_on_commit.py tests/integration/test_cart_order_integration.py` -- зелёные
- там же `python manage.py makemigrations --check --dry-run` и `check_openapi_sync` (рецепт с монтированием `docs` в `/contract`) -- OK
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit` -- без ошибок
- `cd frontend && npx vitest run src/components/checkout src/components/business src/utils` -- зелёные
- `cd frontend && npx playwright test tests/e2e/checkout.spec.ts` -- зелёные (skip допустимы только перечисленные)
