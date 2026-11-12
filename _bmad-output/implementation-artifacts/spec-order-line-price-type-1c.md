---
title: 'Вид цены в каждой строке заказа и соглашение акции для 1С'
type: 'feature'
created: '2026-11-12'
status: 'draft'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/research-order-line-price-type-1c.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-checkout-price-recalc.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В заказах с сайта в 1С `ЗаказКлиента.Товары.ВидЦены` пуст во всех строках, а соглашение всегда «Стандартное». БУС игнорирует `<ВидЦены>` строки, а сайт пишет туда вид цен роли, а не поля, давшего цену. У менеджеров акционная позиция идёт по виду цен акции, остальные — по виду цен клиента, а соглашение — «Акция …».

**Approach:** Сайт сохраняет в строке заказа поле-источник цены (`PricedField.field` из `pricing_policy.resolve_user_price`, `spec-checkout-price-recalc.md`) и вид цены и выгружает его в строку. Если в субзаказе есть акционная строка, в шапку уходит соглашение с именем вида цен акции, иначе «Стандартное». В 1С обе вещи заполняет настройка БУС `<Свой алгоритм>`, расширение не меняется.

**Зависимость:** начинать после `spec-checkout-price-recalc.md` (функция «цена + поле-источник», пересчёт при оформлении, правило равенства → акция).

**Решения владельца (12.11.2026):** 1) механизм A — настройка БУС, не патч; 2) соглашение текущей акции, если в заказе есть акционные позиции; значение берётся из акционной позиции; 3) вид цены определяется при оформлении заказа.

## Boundaries & Constraints

**Always:**
- Поле → `PriceType`: только `is_active`; для `promo_price` — `current_promo_type()` под той же блокировкой акции, что и пересчёт; при нескольких кандидатах — первый по `onec_name` + warning.
- Строка акционная, если `price_source_field == "promo_price"`.
- Соглашение решается по каждому субзаказу и только по строкам, которые реально выгружаются (с вариантом и `onec_id`).
- Пустой `price_source_field` = старая строка: выгружается как сейчас (`_get_price_type`, шапка «Стандартное»).

**Never:**
- Не искать вид цен в 1С по наименованию.
- Не слать в строке `НомерПозицииКорзины`: БУС подменяет им `КодСтроки`, по которому работает алгоритм.
- Не добавлять новые поля `OrderItem` в `OrderItemSerializer`: имена видов цен клиенту не показываются.
- Не править прод-1С из кода — только runbook для администратора.

## I/O & Edge-Case Matrix

| Сценарий | Состояние | Строка / шапка XML | Ошибки |
|---|---|---|---|
| Акция | источник `promo_price` | строка «АКЦИЯ НОЯБРЬ-26»; шапка «АКЦИЯ НОЯБРЬ-26» | — |
| Цена роли | источник `opt2_price`, акционных строк нет | «Опт 2 …»; шапка «Стандартное» | — |
| Откат на розницу | источник `retail_price` | «РРЦ» | — |
| Спеццена без своей | источник `opt1_price` | «Опт 1 …» | — |
| Нет активного `PriceType` поля | `federation_price` | `<ВидЦены>` и `ВидЦеныИд` не пишутся | warning |
| Акция без активного типа | `promo_price`, `current_promo_type()` = None | вид не пишется, шапка «Стандартное» | warning |
| Два субзаказа | акционная строка в одном | «АКЦИЯ …» только у него | — |
| Старая строка | `price_source_field` пуст | вид по роли, шапка «Стандартное» | — |
| Нет соглашения в 1С | имя не найдено среди действующих | 1С ставит «Стандартное» | — |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/services/order_create.py:133-150` — создание `OrderItem`; сюда — снимок вида.
- `backend/apps/orders/models.py:418` `OrderItem`; `OrderItemInline` в `backend/apps/orders/admin.py`.
- `backend/apps/orders/services/order_export.py:157` `_create_document_element`, `:325` `_create_products_element` (impact HIGH: путь `generate_xml_streaming` → обмен 1С), `:550` `_get_price_type` — fallback.
- `backend/apps/products/models.py` `PriceType`; `backend/apps/products/services/promo.py:109` `current_promo_type`.
- `backend/tests/unit/test_order_export_service.py:1966` `test_vid_tseny_in_item`, `TestOpt4PriceTypeRealSettings`.
- `docs/integrations/1c/order-manager-author-department-setup.md` — образец runbook'а.

## Tasks & Acceptance

**Execution:**
- [ ] `backend/apps/orders/models.py` + миграция -- `OrderItem.price_source_field`, `price_type_onec_id`, `price_type_name` (blank).
- [ ] `backend/apps/orders/services/order_create.py` -- из `PricedField` позиции заполнить три поля по правилам Boundaries.
- [ ] `backend/apps/orders/services/order_export.py` -- `<ВидЦены>` и `ЗначениеРеквизита` `ВидЦеныИд` из снимка; шапка `<Соглашение>` и реквизит «Соглашение» по правилам Boundaries.
- [ ] `backend/apps/orders/admin.py` -- три поля в `OrderItemInline` только для чтения.
- [ ] Тесты -- матрица и AC.
- [ ] `docs/integrations/1c/order-line-price-type-setup.md` -- runbook: строки `Товары.ВидЦены` и «Соглашение» → `<Свой алгоритм>` (исследование, п. 5); GUID «Стандартного» брать из текущей настройки прода; тестовый XML с GUID «Акция МАРТ» `a151b0b5-160d-11f1-973b-f9cdeb93e398` для test_base; контрольный заказ на проде; откат; сайт можно выкатывать раньше настройки 1С.

**Acceptance Criteria:**
- Given клиент Опт 2 и в одном субзаказе акционный и неакционный товар, when выгрузка, then строки несут «АКЦИЯ …» и «Опт 2 …», шапка — «АКЦИЯ …».
- Given узел 1С не настроен, when загружен заказ нового формата, then документ создаётся как раньше (вид цены пуст, «Стандартное»).
- Given узел test_base настроен по runbook'у, when загружен тестовый заказ, then у каждой строки заполнен `Товары.ВидЦены`, соглашение — действующее «Акция …», цены и суммы совпадают с XML.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Design Notes

`[СтрокаXML]` в `<Свой алгоритм>` не работает: ключа нет в `Параметры` (`БУС_ЗагрузкаСервер`, стр. 2405–2427). Строку ищем в `[ДокументXML].Товары` по `[НоваяСтрока].КодСтроки` (заполняется раньше `ВидЦены`; уникален). Любое исключение в алгоритме роняет загрузку документа, поэтому оба алгоритма целиком в `Попытка`. Соглашение ищется по имени среди действующих: без пометки, `Статус = Действует`, в датах действия, ровно одно; иначе «Стандартное». Условие: имя соглашения акции в 1С = имени вида цен акции (в test_base совпадает; на проде сверяет администратор).

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` -- expected: зелёные.

**Manual checks:**
- test_base (БУС 8.1.0.40): загрузить тестовый XML через узел «Обмен локальный» с алгоритмами; COM-запросом проверить `Товары.ВидЦены` и `Соглашение`. Прод (8.1.0.45) — контрольный заказ по runbook'у.
