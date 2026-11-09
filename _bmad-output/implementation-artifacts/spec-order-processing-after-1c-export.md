---
title: 'Заказы в личном кабинете: «Новый» → «В обработке» после успешной выгрузки в 1С'
type: 'feature'
created: '2026-11-08'
status: 'done'
baseline_commit: '22528fa1ce4aa2b13d24a876386305991e3b5798'
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
- [x] `backend/apps/orders/services/order_export_status.py` -- функция перевода субзаказов `pending → processing` и пересчёта статуса мастеров через `_aggregate_master_status`; мастер сохраняется `save()` -- одна реализация для трёх мест обмена
- [x] `backend/apps/integrations/onec_exchange/views.py` -- вызов функции из трёх мест пометки `sent_to_1c` -- статус в кабинете меняется в момент выгрузки
- [x] `backend/tests/integration/test_onec_export.py` -- тесты по строкам матрицы (success, повторный query, fallback, мастер с двумя субзаказами, не-`pending`, повторный success) -- гарантия поведения
- [x] `backend/apps/orders/manager_admin.py` + `backend/tests/integration/test_manager_orders_section.py` -- подпись счётчика «Ждут отправки в 1С: N» -- менеджер не принимает пустой счётчик за отсутствие заказов
- [x] `_bmad-output/implementation-artifacts/epic-42-context.md:61` -- подпись счётчика менеджера в описании главной раздела -- контекст эпика не расходится с кодом
- [x] `docs/integrations/1c/architecture.md` -- в описании `mode=success` одна строка: после выгрузки субзаказ `pending` → `processing`, мастер пересчитывается -- документация обмена не расходится с кодом

### Review Findings

- [x] [Review][Patch][Medium] Подпись очереди не соответствует фильтру — счётчик `status="pending"` включает частично выгруженные и ранее выгруженные мастер-заказы, но исключает невыгруженные заказы в других статусах; ссылка использует тот же фильтр. Решение владельца: изменить фильтр и ссылку в соответствии с подписью «Ждут отправки в 1С». [backend/apps/orders/manager_admin.py:157-162]
- [x] [Review][Patch][Medium] Устаревший список впервые отправленных заказов при параллельном подтверждении — два запроса могут выбрать один и тот же неотправленный субзаказ; после завершения первого менеджер возвращает его в `pending`, а второй по ранее выбранному PK снова переводит его в `processing`. Нужны атомарное определение действительно впервые помеченных PK и конкурентный тест. [backend/apps/integrations/onec_exchange/views.py:809-824]
- [x] [Review][Patch][Medium] Проверить реальное начисление бонусов при выгрузке — существующий тест подменяет `accrue_for_order` и не проверяет транзакцию бонусов, сумму и идемпотентность для `accrual_status="processing"`. [backend/tests/integration/test_onec_export.py:1905-1917]
- [x] [Review][Patch][Medium] Проверить общий откат при ошибке агрегации — тесты не подтверждают, что ошибка сохранения мастера откатывает и статусы, и отметки отправки во всех трёх ветках подтверждения. [backend/apps/integrations/onec_exchange/views.py:824]
- [x] [Review][Patch][Low] Закрывать потоковые ответы в новых тестах — `_exchange` возвращает `FileResponse` для `mode=query`, но вызовы не читают и не закрывают ответ; зарегистрированный очиститель временного XML не вызывается. [backend/tests/integration/test_onec_export.py:1745-1748]

**Повторное ревью:**
- [x] [Review][Patch][High] Отмена по устаревшему состоянию после подтверждения выгрузки — клиент может прочитать `pending` до выгрузки, затем после её коммита сохранить старый мастер как `cancelled`, перезаписав `sent_to_1c=False`, и отменить субзаказы; отмена в 1С не передаётся. Владелец разрешил изменение отмены для устранения гонки. [backend/apps/orders/views.py:168-194; backend/apps/orders/services/order_export_status.py:54-62]
- [x] [Review][Patch][Medium] Взаимная блокировка отмены и частичной выгрузки — отмена блокирует мастер, затем субзаказы, а новое подтверждение выгрузки блокирует субзаказ, затем мастер; PostgreSQL может прервать одну из транзакций. При частичной выгрузке новая блокировка мастера расширяет существующий риск. Владелец разрешил изменение отмены для устранения блокировки. [backend/apps/integrations/onec_exchange/views.py:517-518; backend/apps/orders/services/order_export_status.py:54-55; backend/apps/orders/views.py:191-194]
- [x] [Review][Patch][Medium] Исключить `export_skipped=True` при переводе статуса — в подтверждениях по кешированным ID этот флаг не перепроверяется; если он установлен после формирования кеша, субзаказ всё равно переходит в `processing`, вопреки ограничению спецификации. [backend/apps/orders/services/order_export_status.py:41-43]

**Повторное ревью: ранее принятые риски, не вынесены повторно:**
- Fallback по времени может подтвердить заказ, не вошедший в выгрузку: риск явно принят в Code Map.
- Взаимная блокировка выгрузки с импортом статусов: изменение кода ранее отклонено владельцем; разнесение запуска в 1С не проверялось автоматически.

**Отклонено:**
- [Review][Medium] Возможная взаимная блокировка выгрузки и импорта статусов: владелец отклонил изменение кода; одновременное выполнение этих операций будет исключено разнесением времени запуска в 1С. Автоматическое исключение пересечения кодом не проверялось. [backend/apps/orders/services/order_export_status.py:54-56; backend/apps/orders/services/order_status_import.py:879-888]
- [Review][Low] Дополнительные отрицательные данные fallback: отдельного показанного дефекта не установлено; существующие условия выборки исключают `export_skipped` и заказы вне окна, а расширение теста без конкретного сбоя несущественно.
- [Review][Low] Отдельный тест отображения в личном кабинете: изменение не затрагивает фронтенд, новый статус уже поддерживается; отсутствие сквозного теста само по себе не доказывает ошибку отображения.

**Ограничение ревью:** слой `graph-impact` не выполнен: Git Bash в песочнице Codex завершился с `CreateFileMapping ... Win32 error 5`. Остальные четыре слоя завершились.

### Review Findings — 2026-11-09

- [x] [Review][Patch][Medium] Взаимная блокировка отмены и импорта статусов — отмена блокирует субзаказы перед мастером, а импорт блокирует все найденные заказы по PK, включая мастер до проверки master-guard. Если пакет содержит мастер и субзаказ, транзакции могут ждать друг друга. Владелец разрешил изменить импорт для согласования порядка блокировок. [backend/apps/orders/views.py:188-196; backend/apps/orders/services/order_status_import.py:617-620]
- [x] [Review][Patch][Medium] Пропущенный после формирования пачки субзаказ остаётся `pending` — подтверждение по кэшу ставит ему `sent_to_1c=True`, но новый сервис исключает `export_skipped=True`. После снятия флага заказ уже не выбирается повторно и не переводится автоматически. Решение владельца: сохранить отметку отправки и предусмотреть восстановление статуса после снятия `export_skipped`. [backend/apps/integrations/onec_exchange/views.py:517-526; backend/apps/orders/services/order_export_status.py:40-45]
- [x] [Review][Patch][Low] Поток конкурентного теста не завершается по таймауту `join`: зависший недемонический поток может удерживать процесс pytest после ошибки проверки. [backend/tests/integration/test_onec_export.py:2048-2049,2074-2076]
- [x] [Review][Patch][Low] Документация подтверждения не упоминает исключение `export_skipped=True` при переводе статуса. [docs/integrations/1c/architecture.md:180]
- [x] [Review][Defer][Medium] Одновременные подтверждения разных субзаказов одного мастера могут оставить `master.sent_to_1c=False` — deferred: существующая до изменений агрегация проверяет остальные субзаказы без блокировки мастера и при параллельных неподтверждённых транзакциях обе проверки могут увидеть неотправленный субзаказ. [backend/apps/integrations/onec_exchange/views.py:494-499]
- [x] [Review][Defer][Medium] Отмена частично выгруженного заказа не передаётся в 1С — deferred: существующее поведение явно принято владельцем в Code Map. [backend/apps/orders/views.py:196-207]
- [x] [Review][Defer][Medium] Отмена выгруженного мастера в статусе `confirmed` не передаётся в 1С — deferred: существующее правило разрешает отмену `confirmed`, и владелец сохранил это правило. [backend/apps/orders/views.py:196-207]
- [x] [Review][Defer][Medium] Отмена между выдачей XML и подтверждением не передаётся в 1С — deferred: существующее окно между `query` и подтверждением, не устраняемое изменением статуса при подтверждении. [backend/apps/orders/views.py:196-207; backend/apps/integrations/onec_exchange/views.py:820-824]
- [x] [Review][Defer][Medium] Fallback может подтвердить не попавший в XML заказ — deferred: неточный fallback и его влияние на новый статус явно приняты в Code Map. [backend/apps/integrations/onec_exchange/views.py:754-767]
- [x] [Review][Defer][Medium] Выгрузка и импорт статусов могут взаимно блокироваться — deferred: владелец ранее отклонил исправление, рассчитывая разнести расписания; автоматическое исключение пересечения не проверено. [backend/apps/orders/services/order_export_status.py:56-58; backend/apps/orders/services/order_status_import.py:888]
- [x] [Review][Defer][Medium, не подтверждено] Исторический статус 1С «Подтвержден» после выгрузки блокируется как регрессия — deferred: поведение тестом подтверждено, но наличие действующих отправителей этого исторического ключа не установлено; для оценки влияния нужно проверить их конфигурацию. [backend/tests/integration/test_order_exchange_import_e2e.py:394-408]

**Отклонено:**
- [Review][Low] Повторное чтение заказа при его одновременном удалении может вернуть 500: редкая гонка с удалением, исправление требует дополнительных веток.
- [Review] Противоречие двух исторических Completion Notes: исправление требует правки рассматриваемой спеки.

**Acceptance Criteria:**
- Given новый заказ клиента и успешный обмен с 1С, when клиент открывает «Мои заказы», then заказ показан как «В обработке».
- Given мастер из двух субзаказов, выгруженных в разных обменах, when ушёл первый, then мастер «Новый», а после второго — «В обработке».

## Implementation Notes

## Spec Change Log

## Review Triage Log

- 2026-11-09, quick-dev step-04 (Blind Hunter + Edge Case Hunter, diff от `22528fa1`): 1 patch, defer/intent_gap/bad_spec нет.
  - [Patch][Low] `promote_exported_sub_orders` пересчитывал и сохранял мастеров всех переданных субзаказов, даже если ни один не переведён (лишняя блокировка мастера, `save()` и бонусный `post_save`). Исправлено: переводимые субзаказы выбираются `select_for_update` по `pk`, при пустом списке — ранний выход, пересчитываются только мастера переведённых. Тест `test_master_untouched_when_no_sub_promoted`; мутация (мастера по всем `sub_ids`) — красный `'confirmed' == 'pending'`.
  - Отклонено как уже принятое или отложенное: частичная выгрузка и отмена клиентом, fallback по окну времени, бонус при `processing`, «Подтвержден» как регрессия, порядок мастеров в `_aggregate_master_sent_to_1c` (выгрузка vs импорт — владелец отклонил правку), backfill ранее выгруженных, подпись и состав счётчика менеджера, приватный `_aggregate_master_status` (переиспользование предписано Code Map).
  - Отклонено как неподтверждённое: сбой бонусов роняет обмен (`accrue_for_order` в своём savepoint, сигнал ловит исключение), deadlock через `SubOrderInline` (поля `export_skipped` в админке нет), сигнал перекрывает ручной `pending` (нет UI-пути), лишний SELECT в `pre_save` (осознанный компромисс), удаление раздела runbook и правка `tasks.py` (артефакт diff со старой базой `98973f7`).

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs tests/integration/test_onec_export.py tests/unit/test_order_status_import.py tests/integration/test_order_status_import_db.py tests/integration/test_manager_orders_section.py` -- expected: все тесты зелёные
- `npx gitnexus detect-changes --scope all` и `npx gitnexus check --cycles` -- expected: только ожидаемые символы, новых циклов нет

## Dev Agent Record

### Implementation Plan

- `promote_exported_sub_orders(sub_ids, now)` в `apps/orders/services/order_export_status.py`: один `update(status="processing")` с условием `status="pending"`, затем мастера субзаказов под `select_for_update` (по `pk`) пересчитываются `OrderStatusImportService()._aggregate_master_status` и сохраняются `save(update_fields=["status", "updated_at"])`. Мастер загружается после `update(sent_to_1c=True)`, а `update_fields` защищает агрегированный `sent_to_1c` в любом случае.
- `views.py`: вызов в трёх местах сразу после `_aggregate_master_sent_to_1c`, внутри того же `transaction.atomic()`; передаются только впервые помеченные PK (`sub_ids_to_update`, в fallback — `fallback_sub_ids_to_update` и только при `updated > 0`). Общий хелпер — сама функция сервиса, копий логики нет.
- Ревью, гонка подтверждений: впервые помеченные субзаказы выбирает `ICExchangeView._claim_unsent_sub_orders` — `select_for_update()` по `sent_to_1c=False` (порядок `pk`) и `update` с тем же условием. Второе подтверждение ждёт коммита первого, после него PostgreSQL перепроверяет условие и пропускает уже помеченные строки. Хелпер используют все три ветки (`mode=success`, повторный `mode=query`, fallback).
- Повторное ревью, отмена (владелец разрешил менять `OrderViewSet.cancel`): в `transaction.atomic()` сначала `select_for_update` всех субзаказов мастера (по `pk`), затем мастера — тот же порядок, что у подтверждения выгрузки и импорта статусов (`order_status_import.py:617` → `:888`). Статус проверяется на перечитанном под блокировкой мастере; сохранение — `save(update_fields=["status", "updated_at"])`, `post_save` срабатывает, `sent_to_1c` не перезаписывается. Ответ сериализует свежий экземпляр из `get_queryset()`. Условия отмены (`pending`/`confirmed`) и `can_be_cancelled` не менялись.
- Повторное ревью, `export_skipped`: условие `export_skipped=False` в `update` статуса `promote_exported_sub_orders`; пометка `sent_to_1c` по кэшу ID не менялась.
- Ревью, счётчик менеджера: `awaiting_1c_export()` в `manager_admin.py` — мастер-заказы с субзаказом, который заберёт следующий `handle_query` (`sent_to_1c=False`, `export_skipped=False`, статус не важен). Тот же queryset применяет фильтр списка `AwaitingExportFilter` («Отправка в 1С», `?export_1c=waiting`) — ссылка счётчика ведёт на него.
- Ревью 2026-11-09, блокировки импорта статусов (владелец разрешил менять импорт): единый порядок «сначала субзаказы, потом мастера, внутри по pk». `OrderStatusImportService._bulk_fetch_orders` — `order_by("is_master", "pk")` (False раньше True); `_apply_master_aggregation` обходит мастеров `sorted(master_ids)`, а не множество в произвольном порядке.
- Ревью 2026-11-09, восстановление статуса после снятия `export_skipped` (решение владельца — сигнал): в `apps/orders/signals.py` `pre_save` (`remember_export_skipped_cleared`) у существующего субзаказа читает из БД, был ли `export_skipped=True`, — только если сохраняется `export_skipped=False`, не `raw` и `update_fields` пуст или содержит поле; `post_save` (`promote_sub_order_after_export_skipped_cleared`) проверяет в БД `sent_to_1c=True` и `status="pending"` и вызывает `promote_exported_sub_orders([pk], timezone.now())`, экземпляр получает `status="processing"`. Мастер сохраняется с `is_master=True` — повторного входа нет. `queryset.update()`/SQL сигнал не ловит — ограничение в docstring и в `architecture.md`. Подключение — существующий `import apps.orders.signals` в `OrdersConfig.ready()`.
- Ревью 2026-11-09, потоки тестов: `_BackgroundConfirmation` создаёт поток `daemon=True`; `join(timeout=30)` и `assert not is_alive()` уже были. Новый конкурентный тест использует тот же класс.
- Ревью 2026-11-09, документация: в п. 4 «Success» `docs/integrations/1c/architecture.md` — исключение `export_skipped=True` и восстановление статуса сигналом при `save()`, не при `queryset.update()`/SQL.

### Debug Log

- Полный прогон (`-n 4`, `not performance and not slow`): 5525 passed, 80 skipped, 1 failed — `test_order_exchange_import_e2e.py::test_full_vat_split_export_import_cycle`. Причина — ожидаемое следствие спеки: после выгрузки субзаказ `processing`(3), исторический ключ 1С «Подтвержден» → `confirmed`(2) блокируется защитой от регрессии, как «На согласовании» в матрице, и пишется в `status_1c`. Реальные статусы УТ 11 в `confirmed` не отображаются. Тест переведён на новое поведение (sub2 остаётся `processing`, `status_1c="Подтвержден"`, мастер `processing` по min-priority) и зелёный (9/9 в файле).
- Строку матрицы «На согласовании поверх processing» уже покрывает `tests/unit/test_order_status_import.py::test_reverse_transition_keeps_status_but_records_status_1c`, новый тест не нужен.
- Ревью, мутация: без `select_for_update` в `_claim_unsent_sub_orders` все три варианта `TestConcurrentExportConfirmation` красные — `('processing', 'processing') != ('pending', 'pending')`, то есть ровно дефект из находки; с блокировкой зелёные. Код восстановлен из копии.
- Ревью, `FileResponse`: `file_to_stream` после чтения через тестовый клиент — `None` (клиент оборачивает поток и сам вызывает `close()` после полного чтения), поэтому проверка по пути временного файла невозможна. `_exchange` дочитывает ответ и закрывает его в `finally`.
- Повторное ревью, red: все четыре новых теста падали на прежнем коде по своим причинам — `export_skipped`-субзаказ уходил в `processing` (оба режима подтверждения), устаревшая отмена отвечала 200 вместо 400, частичная выгрузка параллельно с отменой давала `deadlock detected`.
- Повторное ревью, мутация: без блокировки субзаказов в `cancel` (мастер блокируется первым) `test_cancel_and_partial_export_do_not_deadlock` снова падает с `deadlock detected`; с блокировкой зелёный. Код восстановлен из копии.
- Ревью, полный прогон (`-n 4`, `not performance and not slow`): 5533 passed, 80 skipped, 0 failed. Одно падение до правки теста — `TestChangelist::test_columns_filters_and_title` сверял список фильтров по `field_path`, у `SimpleListFilter` его нет; тест сверяет и новый фильтр по `parameter_name`.
- Ревью 2026-11-09, red/мутация блокировок: `TestCancelDuringStatusImport::test_cancel_and_import_with_master_and_sub_do_not_deadlock` — отмена заблокировала субзаказы и стоит перед блокировкой мастера (пауза через подмену `QuerySet.get` только в потоке отмены), импорт пакета «мастер + субзаказ» запускается во втором соединении и встаёт в очередь, затем отмена продолжает. С возвращённым `order_by("pk")` тест красный: `OperationalError: deadlock detected` («while locking tuple ... in relation "orders"»); с `("is_master", "pk")` зелёный. Код восстановлен из копии.
- Ревью 2026-11-09, red/мутация сигнала: без регистрации `post_save`-обработчика красные 4 теста `TestStatusRestoredAfterExportSkippedCleared` (обмен `query` → флаг → `success` → `save()` и три варианта `update_fields`) — `'pending' == 'processing'`; без условия `sent_to_1c=True` красный `test_not_promoted_unless_sent_and_pending[not_sent]`. Код восстановлен из копии.
- Ревью 2026-11-09, unit-тест `TestRound6ReviewFollowups::test_bulk_fetch_creates_correct_cache_keys` сверял `order_by("pk")` — переведён на новый порядок `("is_master", "pk")`.
- Ревью 2026-11-09, прогоны: набор из Verification + `test_order_exchange_import_e2e.py`, `test_orders_api.py`, `unit/test_orders_admin.py`, `test_supervisor_section.py`, `unit/test_manager_orders_admin.py` — 460 passed, 1 failed (unit-тест порядка выше), после правки `unit/test_order_status_import.py` — 106 passed. Полный прогон (`-n 4`, `not performance and not slow`) — 5547 passed, 80 skipped, 0 failed (+10 новых тестов).

### Completion Notes

- Субзаказ при первом подтверждении выгрузки (явный `mode=success`, повторный `mode=query`, fallback по времени) переходит `pending` → `processing`; мастер пересчитывается и уходит в `processing`, когда ни один субзаказ не остался `pending`. Не-`pending` статусы, `export_skipped` и ранее выгруженные субзаказы не трогаются; повторный success ничего не меняет.
- `post_save` мастера (бонусы) срабатывает — проверено тестом с патчем `accrue_for_order`.
- Подпись счётчика менеджера — «Ждут отправки в 1С: N»; кроме семи проверок в `test_manager_orders_section.py` подпись обновлена ещё в `test_supervisor_section.py` и `tests/unit/test_manager_orders_admin.py` (иначе регрессия).
- `epic-42-context.md:61` уже содержал новую подпись (обновлён при создании спеки) — изменений не потребовалось.
- Тесты: 9 новых в `TestOrderProcessingAfterExport`; набор из Verification + supervisor/unit-менеджер — 406 passed; e2e-файл — 9 passed. black/isort/flake8 чистые; mypy по новому модулю — только старая ошибка в `apps/orders/tasks.py:175`.
- Находки ревью закрыты: (1) счётчик «Ждут отправки в 1С» и ссылка считают мастер-заказы с субзаказом для следующего обмена в любом статусе — без ранее выгруженных «Новых» и мастеров, чей невыгруженный субзаказ пропущен; частично выгруженный мастер считается, его остаток ждёт обмена; (2) атомарный выбор впервые помеченных субзаказов и конкурентный тест на три ветки; (3) настоящее начисление бонуса при `accrual_status="processing"` — сумма, база, процент, одна операция при повторном подтверждении и пересохранении мастера; частичная выгрузка бонус не начисляет; (4) сбой сохранения мастера откатывает `sent_to_1c`, `sent_to_1c_at` и статусы во всех трёх ветках (`ATOMIC_REQUESTS` выключен, как на проде; fallback отвечает `failure`); (5) `_exchange` закрывает ответы.
- `epic-42-context.md:61` — описание счётчика приведено к новому условию и ссылке.
- Находки повторного ревью закрыты: (1) [High] отмена клиентом перечитывает статус мастера под блокировкой — после коммита полной выгрузки мастер `processing`, отмена отвечает 400 и не затирает `sent_to_1c`; (2) [Medium] отмена блокирует субзаказы раньше мастера, как выгрузка и импорт статусов, — взаимной блокировки с частичной выгрузкой нет; при частичной выгрузке отмена по-прежнему разрешена (принятое ограничение Code Map); (3) [Medium] субзаказ с `export_skipped=True`, выставленным после формирования пачки, в `processing` не переводится. Тесты: `TestCancelDuringExportConfirmation` (2, два соединения PostgreSQL) и `test_sub_skipped_after_query_is_not_promoted` (`success`/`query`). Изменение `OrderViewSet.cancel` расходится с Decisions в замороженной части — сделано по разрешению владельца из повторного ревью; правила отмены и `can_be_cancelled` те же, схема OpenAPI не менялась.
- Повторное ревью, проверки: полный прогон — 5537 passed, 80 skipped, 0 failed; black/isort/flake8 по изменённым файлам чистые; GitNexus detect-changes — 11 файлов, risk low, затронутых процессов нет; `check --cycles` — два цикла базовой линии.
- GitNexus: impact `handle_success`, `_mark_previous_query_as_sent`, `manager_queue`, `ManagerOrderAdmin` — `LOW`; detect-changes — 8 файлов, только ожидаемые символы, risk low; `check --cycles` — два цикла базовой линии, новых нет. Индекс был `stale` только из-за docs-коммитов, владелец разрешил продолжить без переиндексации.
- Находки ревью 2026-11-09 закрыты: (1) [Medium] импорт статусов блокирует субзаказы раньше мастеров, как отмена и подтверждение выгрузки, мастера агрегации — по возрастанию pk; конкурентный тест отмены и импорта на двух соединениях PostgreSQL; (2) [Medium] снятие `export_skipped` через `save()` у отправленного `pending`-субзаказа переводит его в `processing` и пересчитывает мастера (сигнал `pre_save`/`post_save`); отметка отправки не менялась; `queryset.update()`/SQL — осознанное ограничение; 9 тестов `TestStatusRestoredAfterExportSkippedCleared` (положительные: обмен с флагом после пачки, `save()` и `update_fields` с полем; отрицательные: `sent_to_1c=False`, статус не `pending`, сохранение без смены флага, `update_fields` без поля, `queryset.update`); (3) [Low] поток `_BackgroundConfirmation` демонический; (4) [Low] `architecture.md` описывает исключение `export_skipped` и восстановление статуса.
- Ревью 2026-11-09, проверки: полный прогон — 5547 passed, 80 skipped, 0 failed; black/isort/flake8 по изменённым файлам чистые; mypy по `signals.py` и `order_status_import.py` — только старая ошибка `apps/orders/tasks.py:175`. GitNexus: индекс `up-to-date` (98973f7); impact `_bulk_fetch_orders` и `_apply_master_aggregation` — `LOW`, прямой вызывающий `OrderStatusImportService.process`, процессы `post` и `handle_file_upload` обмена 1С; `_BackgroundConfirmation` — 0 вызывающих (`UNKNOWN`, тестовый хелпер); новые обработчики сигналов в индексе отсутствуют (хуки, вызывающих нет). detect-changes — 15 файлов, 71 символ, затронутых процессов 0, risk low; `check --cycles` — два цикла базовой линии, новых нет.

## File List

- `backend/apps/orders/views.py`
- `backend/apps/orders/services/order_export_status.py` (новый)
- `backend/apps/integrations/onec_exchange/views.py`
- `backend/apps/orders/manager_admin.py`
- `backend/apps/orders/signals.py`
- `backend/apps/orders/services/order_status_import.py`
- `backend/tests/integration/test_onec_export.py`
- `backend/tests/integration/test_order_exchange_import_e2e.py`
- `backend/tests/integration/test_manager_orders_section.py`
- `backend/tests/integration/test_supervisor_section.py`
- `backend/tests/unit/test_manager_orders_admin.py`
- `backend/tests/unit/test_order_status_import.py`
- `docs/integrations/1c/architecture.md`
- `_bmad-output/implementation-artifacts/epic-42-context.md`
- `_bmad-output/implementation-artifacts/spec-order-processing-after-1c-export.md`

## Change Log

- 2026-11-08: реализация — перевод субзаказов `pending` → `processing` при подтверждении выгрузки в 1С с пересчётом мастера, подпись счётчика менеджера «Ждут отправки в 1С», тесты и документация обмена.
- 2026-11-08: исправлены замечания ревью, закрыто 5 пунктов: фильтр и ссылка счётчика «Ждут отправки в 1С», атомарный выбор впервые отправленных субзаказов с конкурентным тестом, тесты реального начисления бонуса и отката, закрытие ответов обмена в тестах.
- 2026-11-08: исправлены замечания повторного ревью, закрыто 3 пункта: отмена клиентом проверяет статус под блокировкой и сохраняет только `status`/`updated_at`, порядок блокировок отмены «субзаказы → мастер», `export_skipped` исключён из перевода статуса.
- 2026-11-09: исправлены замечания ревью 2026-11-09, закрыто 4 пункта: порядок блокировок импорта статусов «субзаказы → мастера» с конкурентным тестом против отмены, восстановление статуса субзаказа сигналом при снятии `export_skipped` через `save()`, демонические потоки конкурентных тестов, документация подтверждения выгрузки.
- 2026-11-09: ревью quick-dev — мастера пересчитываются только для действительно переведённых субзаказов (`promote_exported_sub_orders`), тест и мутация; прогон `test_onec_export.py`, `unit/test_order_status_import.py`, `test_order_status_import_db.py`, `test_order_exchange_import_e2e.py` — 212 passed.

## Suggested Review Order

**Перевод статуса при подтверждении выгрузки**

- Точка входа: одна реализация перевода `pending` → `processing` и пересчёта мастеров.
  [`order_export_status.py:22`](../../backend/apps/orders/services/order_export_status.py#L22)

- Сначала блокируются субзаказы, ранний выход, если перевести нечего.
  [`order_export_status.py:46`](../../backend/apps/orders/services/order_export_status.py#L46)

- Агрегация мастера переиспользует импорт статусов, `save(update_fields)` бережёт `sent_to_1c`.
  [`order_export_status.py:70`](../../backend/apps/orders/services/order_export_status.py#L70)

**Три ветки подтверждения в обмене**

- Атомарный выбор впервые помеченных субзаказов закрывает гонку подтверждений.
  [`views.py:504`](../../backend/apps/integrations/onec_exchange/views.py#L504)

- Повторный `mode=query` как неявное подтверждение.
  [`views.py:557`](../../backend/apps/integrations/onec_exchange/views.py#L557)

- Fallback по окну времени (риск принят в Code Map).
  [`views.py:767`](../../backend/apps/integrations/onec_exchange/views.py#L767)

- Явный `mode=success`.
  [`views.py:824`](../../backend/apps/integrations/onec_exchange/views.py#L824)

**Порядок блокировок «субзаказы → мастер»**

- Отмена клиентом блокирует субзаказы, затем перечитывает мастер под блокировкой.
  [`views.py:189`](../../backend/apps/orders/views.py#L189)

- Импорт статусов блокирует субзаказы раньше мастеров.
  [`order_status_import.py:625`](../../backend/apps/orders/services/order_status_import.py#L625)

- Мастера агрегации — по возрастанию pk.
  [`order_status_import.py:896`](../../backend/apps/orders/services/order_status_import.py#L896)

**Восстановление после снятия `export_skipped`**

- `pre_save` фиксирует переход флага True → False по значению из БД.
  [`signals.py:78`](../../backend/apps/orders/signals.py#L78)

- `post_save` переводит отправленный `pending`-субзаказ; `queryset.update` не ловится.
  [`signals.py:98`](../../backend/apps/orders/signals.py#L98)

**Счётчик менеджера**

- Условие очереди повторяет выборку `handle_query`, статус не важен.
  [`manager_admin.py:98`](../../backend/apps/orders/manager_admin.py#L98)

- Подпись «Ждут отправки в 1С» и ссылка на фильтр.
  [`manager_admin.py:195`](../../backend/apps/orders/manager_admin.py#L195)

**Тесты и документация**

- Матрица сценариев выгрузки, бонусы, откат, мастер без переведённых субзаказов.
  [`test_onec_export.py:1780`](../../backend/tests/integration/test_onec_export.py#L1780)

- Сигнал снятия `export_skipped`: положительные и отрицательные случаи.
  [`test_onec_export.py:2046`](../../backend/tests/integration/test_onec_export.py#L2046)

- Конкурентные тесты на двух соединениях PostgreSQL.
  [`test_onec_export.py:2212`](../../backend/tests/integration/test_onec_export.py#L2212)

- Описание `mode=success` в документации обмена.
  [`architecture.md:180`](../../docs/integrations/1c/architecture.md#L180)

