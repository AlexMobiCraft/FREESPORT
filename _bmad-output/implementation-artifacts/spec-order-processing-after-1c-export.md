---
title: 'Заказы в личном кабинете: «Новый» → «В обработке» после успешной выгрузки в 1С'
type: 'feature'
created: '2026-11-08'
status: 'ready-for-dev'
route: 'dispatch'
review_loop_iteration: 0
context: ['{project-root}/.windsurf/rules/gitnexus.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Клиент в личном кабинете видит мастер-заказ в статусе «Новый» (`pending`), даже когда 1С уже забрала его: единственные статусы сайта ставит импорт статусов из 1С, а он приходит с задержкой или не приходит вовсе.

**Approach:** В момент, когда выгрузка помечает субзаказ `sent_to_1c=True`, переводить его `pending` → `processing` и пересчитывать статус мастера существующей агрегацией. Фронтенд не менять: «Новый» и «В обработке» он уже показывает.

## Boundaries & Constraints

**Always:** Переход только из `pending` в `processing`; другие статусы (`confirmed`, `cancelled` и т. д.) не трогать. Статус мастера считает `OrderStatusImportService._aggregate_master_status` (мастер уходит в `processing`, только когда ни один субзаказ не остался `pending`). Мастер сохраняется через `save()`, чтобы отработали сигналы (бонусы).

**Decisions (владелец, 08.11.2026):** Отмена клиентом остаётся только для `pending`/`confirmed`: `can_be_cancelled` и `OrderViewSet.cancel` не меняются, после выгрузки отменяет менеджер.

**Never:** Переводить уже выгруженные ранее заказы (отложено в `deferred-work.md`: команда `promote_exported_orders`); миграция данных тоже не нужна. Менять протокол обмена, `ICExchangeView.handle_query`-выборку, импорт статусов из 1С, фронтенд, `.env*`. Не переводить заказы с `export_skipped=True` (в 1С они не попали).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Выгрузка подтверждена | субзаказ `pending`, `sent_to_1c=False`; `mode=success` или повторный `mode=query` | субзаказ `processing`, `sent_to_1c=True`; мастер `processing`, если все субзаказы ушли | — |
| Мастер из нескольких субзаказов | ушёл один из двух | субзаказ `processing`, мастер остаётся `pending` | — |
| Уже не `pending` | субзаказ `confirmed`/`cancelled` | статус не меняется, `sent_to_1c=True` ставится как раньше | — |
| Статус 1С «На согласовании» после перехода | импорт даёт `pending` поверх `processing` | статус сайта не меняется (регрессия блокируется), фактический статус пишется в `status_1c` | как сейчас |
| Повторный `mode=success` | субзаказ уже `sent_to_1c=True` | ничего не меняется | — |
| Fallback по времени (кэш потерян) | `mode=success` без списка ID | то же правило для помеченных субзаказов | — |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/services/` -- новый модуль с функцией перевода `pending → processing` для списка субзаказов и пересчётом их мастеров; её вызывает `views.py` (выделен в отдельный модуль, чтобы позже его переиспользовала отложенная команда backfill). Контракт: принимает только PK, которые только что получили `sent_to_1c=True` (`sub_ids_to_update`, не `sub_ids`); один запрос `filter(pk__in=…, status="pending").update(status="processing", updated_at=now)` (условие по статусу защищает от гонки с ручной сменой); мастера этих субзаказов блокируются `select_for_update` и пересчитываются `_aggregate_master_status`; мастер сохраняется `save(update_fields=["status", "updated_at"])` — `post_save` (бонусы) срабатывает, а полный `save()` экземпляра, загруженного до `queryset.update(sent_to_1c=True)` в `_aggregate_master_sent_to_1c`, вернул бы мастеру `sent_to_1c=False`; вызывается внутри того же `transaction.atomic()`, что и пометка `sent_to_1c`.
- `backend/apps/integrations/onec_exchange/views.py:478-501` -- `_aggregate_master_sent_to_1c`: единая точка, где мастера помечаются отправленными.
- `views.py:503-563,691-842` -- три места, где субзаказы получают `sent_to_1c=True` (`_mark_previous_query_as_sent`, fallback и основная ветка `handle_success`); в каждом перед/вместе с `update(sent_to_1c=True…)` добавить `pending → processing`. Лучше общий хелпер, а не три копии. GitNexus impact: `risk LOW` для всех трёх методов, затронуты потоки `get`/`post` обмена.
- `backend/apps/orders/services/order_status_import.py:822-856` -- `_aggregate_master_status`: переиспользовать, не копировать; сервис без состояния, `OrderStatusImportService()` создаётся без аргументов.
- `backend/apps/orders/constants.py:49-80` -- `ORDER_STATUSES`, `STATUS_PRIORITY`: `pending`=1 < `processing`=3, поэтому позднее «На согласовании» из 1С блокируется как регрессия и пишется в `status_1c` (`_record_blocked_status_1c`).
- `backend/apps/bonuses/signals.py:18` -- `post_save` мастера вызывает `accrue_for_order`; при `accrual_status == "processing"` бонус начислится в момент выгрузки. Это ожидаемо, но проверить.
- Принятый риск: fallback `handle_success` без кэша помечает отправленными все заказы `created_at <= last_query_time`; не попавший в выгрузку заказ (поздний коммит) покажется клиенту «В обработке». Это поведение `sent_to_1c`, не расширять.
- Принятое ограничение (владелец, 08.11.2026): субзаказы создаются в одной транзакции с мастером и уходят одной пачкой `handle_query`; разойтись они могут только через `export_skipped` (`OrderExportService._validate_order` пропускает лишь субзаказ без позиций, при штатном разбиении по группам НДС такого не бывает). Тогда мастер навсегда остаётся `pending`, а клиент может отменить его целиком вместе с субзаказом, который уже в 1С (`OrderViewSet.cancel` → `sub_orders.update(status="cancelled")`, отмены в 1С не уходят). Не закрывать в этой спеке.
- `backend/apps/orders/manager_admin.py:157-160` -- счётчик на главной раздела менеджера (мастер-заказы `status="pending"`) после изменения считает заказы, которые ещё не ушли в 1С; подпись «Новые заказы: N» → «Ждут отправки в 1С: N» (решение владельца 08.11.2026). Фильтр и ссылка `?status__exact=pending` не меняются. Поле `NotificationRecipient.notify_new_orders` («Новые заказы») — другое, не трогать.
- `backend/tests/integration/test_manager_orders_section.py:1259-1475` -- семь проверок подписи «Новые заказы» перевести на новую.
- `backend/tests/integration/test_onec_export.py` -- образец фикстур (`master_with_two_subs`, `authenticated_client`) и тестов `mode=success`/fallback; сюда новые тесты.
- Не менять: `frontend/` (`OrderStatusBadge`, `OrdersList` уже знают оба статуса), `orders/views.py` и `Order.can_be_cancelled` (решение 1).

## Tasks & Acceptance

**Execution:**
- [ ] `backend/apps/orders/services/order_export_status.py` -- функция перевода субзаказов `pending → processing` и пересчёта статуса мастеров через `_aggregate_master_status`; мастер сохраняется `save()` -- одна реализация для трёх мест обмена
- [ ] `backend/apps/integrations/onec_exchange/views.py` -- вызов функции из трёх мест пометки `sent_to_1c` -- статус в кабинете меняется в момент выгрузки
- [ ] `backend/tests/integration/test_onec_export.py` -- тесты по строкам матрицы (success, повторный query, fallback, мастер с двумя субзаказами, не-`pending`, повторный success) -- гарантия поведения
- [ ] `backend/apps/orders/manager_admin.py` + `backend/tests/integration/test_manager_orders_section.py` -- подпись счётчика «Ждут отправки в 1С: N» -- менеджер не принимает пустой счётчик за отсутствие заказов
- [ ] `_bmad-output/implementation-artifacts/epic-42-context.md:61` -- подпись счётчика менеджера в описании главной раздела -- контекст эпика не расходится с кодом
- [ ] `docs/integrations/1c/architecture.md` -- в описании `mode=success` одна строка: после выгрузки субзаказ `pending` → `processing`, мастер пересчитывается -- документация обмена не расходится с кодом

**Acceptance Criteria:**
- Given новый заказ клиента и успешный обмен с 1С, when клиент открывает «Мои заказы», then заказ показан как «В обработке».
- Given мастер из двух субзаказов, выгруженных в разных обменах, when ушёл первый, then мастер «Новый», а после второго — «В обработке».

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs tests/integration/test_onec_export.py tests/unit/test_order_status_import.py tests/integration/test_order_status_import_db.py tests/integration/test_manager_orders_section.py` -- expected: все тесты зелёные
- `npx gitnexus detect-changes --scope all` и `npx gitnexus check --cycles` -- expected: только ожидаемые символы, новых циклов нет
