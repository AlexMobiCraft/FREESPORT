---
title: 'Импорт 1С включает товары, выключенные на сайте'
type: 'bugfix'
created: '2026-10-30'
status: 'done'
route: 'dispatch'
baseline_commit: '755b82e049c35c09a1bb73a16be8dcb1ed8a638f'
review_loop_iteration: 0
context:
  - '{project-root}/backend/docs/testing-standards.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Товар с `is_active=False`, `onec_deleted=False` импорт 1С обратно не включает, даже если товар допущен и в 1С не помечен удалённым. На проде на 30.10.2026 так застряли 113 товаров, среди них «Фигурные коньки Cosmoride Сира» (id 327, SKCR25PKSIRA).

**Approach:** 1С имеет приоритет над флагом сайта: импорт включает такой товар, когда 1С присылает его снова. Это отменяет правило «ручное выключение импорт не отменяет» из `spec-1c-deletion-marked-goods.md` и решение от 07.10.2026 из `spec-activate-stuck-inactive-products.md`. Скрыть товар надолго теперь можно только пометкой удаления в 1С.

**Решение владельца 30.10.2026:** включается только товар с положительной ценой. Товар без цены ждёт цену из 1С. Остаток не обязателен: товар с ценой и нулевым остатком включается.

## Boundaries & Constraints

**Always:**
- Товар с `onec_deleted=True` включается только прежним путём — допуском в goods.xml.
- Товар с `is_active=False`, `onec_deleted=False` включается, только если у него есть активный вариант (`is_active=True`, `onec_deleted=False`) с положительной ценой по `priced_variant_q`. Цена скрытого варианта не считается. «Все предложения помечены» остаётся выключенным.
- Импорт только включает товар: обнуление цены активный товар не выключает.
- Условие проверяется при каждом приходе goods, offer и цены: цены приходят отдельной сессией после goods и offers.
- Вернуть скрытый вариант может только offer без пометки удаления. Цена этого не делает.
- `_create_new_variant` и `create_default_variants` не меняются: новый вариант включает товар без проверки цены.
- По каждому такому включению — строка `INFO` в логгер `import_products` (Ид 1С, артикул, наименование) и счётчик `reenabled_products` в отчёте сессии: лог показывает, какой товар включён, а счётчик остаётся в `report_details`, когда лог уже перезаписан.
- Галочка «Активный» в карточке товара предупреждает, что выключение держится до прихода данных 1С. Подсказка задаётся в форме админки, модель не меняется.

**Never:**
- Не включать застрявшие товары скриптом или миграцией: решение владельца 30.10.2026 — они включаются сами, когда после выката по ним придут goods, offer или цена.
- Не чинить на сайте отсутствие offers/prices у коньков: их не присылает 1С.
- Не добавлять миграции и новые поля.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Goods по выключенному товару | `is_active=False`, `onec_deleted=False`, активный вариант с ценой | `is_active=True`, строка в логе | — |
| Offer по существующему варианту | родитель выключен, вариант с ценой | родитель включён | — |
| Goods или offer без цены | вариант с нулевыми ценами | остаётся выключенным | — |
| Пришла цена | товар выключен, цена варианта стала > 0 | товар включён, строка в логе | — |
| Цена на скрытом варианте | `onec_deleted=True` у варианта, других цен нет | остаётся выключенным | — |
| Все предложения помечены, пришли цены | в 1С пометки стоят, все варианты `onec_deleted=True` | цены записаны в скрытые варианты, товар и варианты остаются выключенными | — |
| Пометку сняли, offer пришёл, цена уже записана | вариант `onec_deleted=True`, цена > 0 | вариант возвращён, товар включён при этом же offer | — |
| Пометку сняли, offer пришёл, цены ещё нет | вариант `onec_deleted=True`, цены 0 | вариант возвращён, товар включится с приходом цены | — |
| Первый вариант товара | `_create_new_variant`, цены ещё нет | товар включается сразу, как сейчас | — |
| Вариант выключен без пометки | `is_active=False`, `onec_deleted=False`, приходит offer | вариант включён, товар включён при цене | — |
| Цена только оптовая или акционная | `retail_price=0`, `opt1_price` или `promo_price` > 0 | товар включён | — |
| Дубли `parent_onec_id` | вариант принадлежит второму Product | включается владелец варианта | — |
| Якорь не найден | goods в режиме `_anchor_missing` | goods не включает товар, как и остальное в этом режиме | — |
| Цена обнулилась | товар активен, цены стали 0 | остаётся активным | — |
| Товар скрыт импортом | `onec_deleted=True`, приходит offer или цена | не включается | — |
| Товар не допущен | goods вне дерева или с пометкой | скрывается, как раньше | — |
| Уже активен | `is_active=True` | записи в БД и строки в логе нет | — |

</frozen-after-approval>

## Code Map

Пути от `backend/`.

- `apps/products/services/variant_import.py` новый хелпер `_enable_priced_product(product_id)` -- один условный `UPDATE` по `pk`, `is_active=False`, `onec_deleted=False` и `Exists` активного варианта с ценой; ставит `is_active` и `updated_at`, `sync_status` не трогает; при обновлённой строке увеличивает `reenabled_products`, пишет лог и возвращает `True`.
- `apps/products/services/variant_import.py:360`, `:554`, `:575` -- счётчик `reenabled_products`: добавить в `stats`, в `ADMISSION_COUNTERS` и в конец строки `admission_report_line` сегментом `, включено выключенных N`. Дописывать именно в конец: тесты `test_variant_import_admission.py:931` и `tests/integration/test_import_deletion_marked_goods.py:313` проверяют вхождение прежней строки.
- `apps/products/management/commands/import_products_from_1c.py:1051` -- вывести счётчик рядом с `restored_products`.
- `apps/products/services/variant_import.py:918` `_readmit_product` -- вызывается для всех совпадений по goods; для товара без `onec_deleted` вызвать хелпер и обновить `is_active` на объекте. Ветку `onec_deleted` не менять: там включение без проверки цены.
- `apps/products/services/variant_import.py:1458` -- после `_update_existing_variant` вызвать хелпер с `variant.product_id`, а не `product.pk`: `_get_product_by_parent_id` берёт `.first()` среди дублей. `if restored: _activate_parent_product` убрать.
- `apps/products/services/variant_import.py:1632` `_activate_parent_product` -- не менять, им пользуется `_create_new_variant`; цену здесь не проверять.
- `apps/products/services/variant_import.py:1906` `update_variant_prices` -- третий триггер, только ПОСЛЕ блока `atomic` (`:1942`) и при записанной цене. Внутри блока нельзя: UPDATE варианта уже прошёл, а общий порядок блокировок — «товар → вариант» (`promo.lock_variant`). `return True` на `:1975` стоит внутри блока: вынести его за блок, запомнив признак записи. Это один запрос на строку цены. Вызывающие метод в транзакцию не оборачивают: команда импорта и задачи `apps/products/tasks.py:543`, `apps/integrations/tasks.py` идут без `atomic`.
- `apps/products/serializers.py:452` `priced_variant_q` -- определение «есть цена», импорт внутри функции, как модели в этом файле.
- `apps/products/tests/unit/test_variant_import_admission.py:321` -- тест закрепляет старое правило, заменить; `:425`, `:507`, `:635` не должны измениться.
- `docs/integrations/1c/import-process.md:448,452,454-459` -- обновить таблицу и абзац про `onec_deleted`.
- `apps/products/models.py:651`, докстринг `_readmit_product` (`:921`) -- описывают старое правило, поправить. `:651` — комментарий, миграции не будет.
- `apps/products/admin.py:377` `ProductAdmin` -- добавить `get_form` с `help_text` у `is_active`, как `:368`, с проверкой `"is_active" in form.base_fields`: метод наследует `MarketingProductAdmin` (`marketing_admin.py:106`). Текст: «Выключение держится до прихода данных из 1С. Чтобы скрыть товар надолго, пометьте его на удаление в 1С.»

## Tasks & Acceptance

**Execution:**
- [x] `apps/products/services/variant_import.py` -- включение в путях goods, offer и цен через общий хелпер с проверкой цены, логом и счётчиком `reenabled_products` -- закрыть дефект.
- [x] `apps/products/management/commands/import_products_from_1c.py` -- показать счётчик в итогах импорта.
- [x] `apps/products/admin.py` -- подсказка у галочки «Активный» -- выключение больше не постоянное.
- [x] `apps/products/tests/unit/test_variant_import_admission.py` -- заменить тест `:321`, покрыть строки I/O-матрицы отдельными сессиями (`_new_processor()`) и счётчик -- на проде goods, offers и цены идут разными сессиями.
- [x] `docs/integrations/1c/import-process.md`, `apps/products/models.py` -- описать приоритет 1С и счётчик -- сейчас утверждают обратное.

**Acceptance Criteria:**
- Given товар выключен в админке и остаётся допущенным, when приходит его goods, offer или цена и у него есть цена, then он включён, в `import_products` есть строка с Ид 1С, а `reenabled_products` в отчёте сессии равен 1.
- Given уже активный товар или товар без цены, when приходит его goods, offer или цена, then `reenabled_products` не меняется.
- Given карточка товара в `/admin/`, when она открыта, then у поля «Активный» видна подсказка, а новых миграций нет.
- Given карточка товара в разделе маркетинга, где поля «Активный» нет, when она открыта, then форма открывается без ошибки.
- Given полный прогон backend-тестов, when изменения внесены, then падений нет.
- Given данные прода на 30.10.2026 (113 застрявших) и выкат, when по застрявшим товарам приходят данные 1С, then включаются только товары с ценой (45 кандидатов), а 68 без цены, в их числе id 327, остаются выключенными. Проверяется на проде после выката, см. Verification; на приёмку разработки не влияет.

## Implementation Notes

- **Хелпер сбрасывает `_product_cache`, этого нет в Code Map.** После `UPDATE` объект в кэше сессии держит старый `is_active=False`, а `_reject_offer` решает по нему, снимать ли товар с витрины: товар, включённый offer или ценой, оставался бы активным без единого варианта, если следом в той же сессии все предложения помечены. Сброс по `onec_id` и `parent_onec_id` закрывает все три пути одним местом, поэтому объект `product` в `process_variant_from_offer` на месте не обновляется. Закреплено тестами `test_enabled_by_offer_then_all_marked_in_same_session_is_disabled_again` и `test_enabled_by_price_then_all_marked_in_same_session_is_disabled_again`.
- **Путь goods вызывает хелпер только при `not product.is_active`.** Объект там только что прочитан из БД, поэтому лишнего запроса на каждый активный товар нет. В путях offer и цены объект может быть устаревшим или чужим при дублях, там `UPDATE` идёт всегда и при активном товаре не находит строк.
- **AC про подсказку в разделе маркетинга не выполним без смены белого списка.** Поля «Активный» в карточке `/marketing/` нет: `MarketingProductAdmin.fieldsets` его не содержит, а `tests/unit/test_marketing_admin_site.py::TestWhitelists::test_product_card` закрепляет состав полей. В колонке списка оно есть, но там `help_text` не показывается. Подсказка есть только в карточке `/admin/`; `get_form` наследуется и в маркетинге не падает (`test_marketing_card_has_no_is_active_field`). Поле в раздел не добавлено: это расширение белого списка, а не правка этой спеки. Нужно решение владельца: снять эту часть AC или добавить поле.
- **Тесты подсказки — в `apps/products/tests/unit/test_admin_onec_deleted.py`**, этого файла нет в Tasks.
- **Сбой после записи цены.** Хелпер вызывается после `atomic`, поэтому если он упадёт, цена уже записана, а `update_variant_prices` вернёт `False` и `_log_error` учтёт ошибку. Товар включится при следующем приходе данных.
## Spec Change Log

- 2026-10-30, решение владельца после проверки спеки: Never и последний AC переписаны под самостоятельное включение после выката (полная выгрузка для этого не нужна); добавлены счётчик `reenabled_products` и подсказка в админке; в Code Map уточнён `return True` на `:1975`, снят вопрос о транзакции вызывающих.
- 2026-10-30, ревью (bad_spec): AC требовал подсказку у поля «Активный» в карточке раздела маркетинга, но этого поля там нет, и `test_product_card` закрепляет состав формы. AC разделён: подсказка в `/admin/`, в маркетинге форма открывается без ошибки. Известное плохое состояние, которого избегаем: добавить поле в маркетинг только ради подсказки и дать маркетологу право выключать товары. KEEP: код уже соответствует Code Map, поэтому откат и повторная реализация не выполнялись, они дали бы тот же diff.

## Review Triage Log

Ревью 2026-10-30: Blind Hunter (15 находок), Edge Case Hunter (5).

- **bad_spec, medium:** подсказка в маркетинге, см. Spec Change Log.
- **defer, low:** `_reject_offer` решает по `product.is_active` из кэша и по первому дублю `parent_onec_id`.
- **defer, low:** `report_details` не пишется в упавшей сессии, поэтому `reenabled_products` такой сессии не попадёт в сверку из Verification. Строка `admission_report_line` в `report` останется.
- **reject:** обход сигналов через `.update()` (у `Product` обработчиков нет); внешняя транзакция в пути offer (команда `atomic` не использует); гонка `EXISTS` с параллельным скрытием варианта (узкое окно, спека требует один условный `UPDATE`); дефолтный вариант с ценой при помеченных `#` (`_reject_offer` такой товар тоже не выключает).
- **reject как решения спеки:** приоритет 1С над флагом сайта, отсутствие лимита на включение, цена по `priced_variant_q`, включение через `_create_new_variant`, неизменный `sync_status`, запрос на каждую строку.

## Design Notes

Снимок выгрузки от 21.09.2026 (`data/import_1c/`) по id 327 (`5eb4932a-45d9-11f0-9dea-fa163ea88911`): товар есть в goods, в offers и prices его нет, в rests одна запись без `#` с нулями. `updated_at` с декабря этому не противоречит: `_update_existing_product` пишет в БД только изменившиеся поля. На проде goods по id 327 приходил и 27.10.2026 (сессии 156491, 156493). У всех 113 товаров нет ни одного варианта с `#`. Журнал админки по ним содержит только 9 правок поля «Новинка»: следов намеренного выключения нет.

Прод на 30.10.2026: 45 и 68 подтверждены по `priced_variant_q`; все 113 в дереве СПОРТ, категории активны, в реестре исключений их нет. Дублей `parent_onec_id` на проде нет, товаров с дефолтным вариантом и полностью помеченными `#` тоже: строки матрицы про них защищают от будущих данных. Варианты всех 45 синхронизированы 27–30.10 (`last_sync_at` пишут и цены, и остатки), волны цен идут раз в несколько дней (5085 строк 27.10), поэтому большинство 45 должно включиться в первые дни после выката. Срок — оценка.

Лог: `import_products` нет в `LOGGING` из `production.py`; судя по конфигу, строки попадают в вывод контейнера `celery` (`-l info`), а это 30 МБ на все строки обмена. На проде не проверялось. Поэтому нужен счётчик в `report_details`.

Известный хвост вне объёма: `_create_new_variant` не убирает дефолтный вариант. На проде таких товаров уже 78. Id 327 попадёт в их число, когда 1С начнёт присылать размеры: `_create_new_variant` включит его до прихода цены. Запись — в `deferred-work.md`.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/products/tests/unit/test_variant_import_admission.py` -- expected: зелено.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` -- expected: зелено.
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` -- expected: только символы из Code Map.

**После выката на проде (владелец, через несколько дней):**
- `SELECT count(*) FROM products WHERE is_active=false AND onec_deleted=false;` -- expected: число снижается со 113 к 68.
- `SELECT is_active FROM products WHERE id=327;` -- expected: `f`, пока 1С не пришлёт по товару предложения или цену.
- `SELECT sum((report_details->>'reenabled_products')::int) FROM import_sessions WHERE started_at > '<дата выката>';` -- expected: совпадает со снижением первого числа, если товары не выключали вручную.

## Suggested Review Order

**Правило включения**

- Один условный UPDATE: цена, активный вариант, сброс кэша сессии, лог и счётчик.
  [`variant_import.py:1651`](../../backend/apps/products/services/variant_import.py#L1651)

**Три триггера**

- Goods: ветка `onec_deleted` не меняется, остальные идут через хелпер.
  [`variant_import.py:945`](../../backend/apps/products/services/variant_import.py#L945)

- Offer: владелец берётся из варианта, потому что `product` при дублях лишь первый.
  [`variant_import.py:1467`](../../backend/apps/products/services/variant_import.py#L1467)

- Цена: вызов после `atomic`, чтобы не нарушить порядок блокировок «товар → вариант».
  [`variant_import.py:2022`](../../backend/apps/products/services/variant_import.py#L2022)

**Отчёт**

- Счётчик добавлен в конец строки: тесты проверяют вхождение прежней строки.
  [`variant_import.py:584`](../../backend/apps/products/services/variant_import.py#L584)

- Счётчик в итогах команды импорта.
  [`import_products_from_1c.py:1052`](../../backend/apps/products/management/commands/import_products_from_1c.py#L1052)

**Админка и документация**

- Подсказка задаётся в форме; в маркетинге поля нет, поэтому стоит проверка.
  [`admin.py:509`](../../backend/apps/products/admin.py#L509)

- Описание приоритета 1С и исключения для первого варианта.
  [`import-process.md:461`](../../docs/integrations/1c/import-process.md#L461)

**Тесты**

- Строки I/O-матрицы отдельными сессиями, счётчик и лог.
  [`test_variant_import_admission.py:494`](../../backend/apps/products/tests/unit/test_variant_import_admission.py#L494)

- Подсказка в HTML карточки товара.
  [`test_admin_onec_deleted.py:54`](../../backend/apps/products/tests/unit/test_admin_onec_deleted.py#L54)
