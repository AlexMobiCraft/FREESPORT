---
baseline_commit: c87d17b6e52e70beeb3e1f29729276f8d66749a9
---

# Story 40.4: Импорт применяет роль привязанным аккаунтам

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> ✅ **Внешних блокеров нет.** Снимок `backend/data/import_1c/contragents_pricetype/` второй редакции патча БУС лежит в основном клоне (10 файлов, 4735 контрагентов: 485 с `ТипЦенId`, 4250 со статусом `НетСоглашения`, без блока — ноль). Поле `User.onec_price_type_id`, парсер и резолвер готовы (40.1–40.3).
> ⚠️ **Работать в основном клоне `C:\Users\1\DEV\FREESPORT`, не в worktree.** Каталог `backend/data/import_1c/` в `.gitignore` и в worktree отсутствует — `data_dependent`-тесты там молча скипаются, индекс GitNexus в worktree не существует.
> 🔴 **Ключевое правило стори.** Роль применяется **только** к записям, **не** проходящим `unlinked_1c_record_q()`. Нарушение возвращает баг, чинившийся миграцией `0018`: регистрация с известным ИНН откажет, фильтр «Кандидат 1С» опустеет, `find_link_candidates` вернёт пустой список. Это `risk: CRITICAL` по GitNexus — см. Dev Notes → «Blast radius».
> 📉 **Отложенный эффект — это норма, а не дефект.** На проде живых привязанных клиентских аккаунтов нет: первый прогон штатно даст `roles_updated = 0` и ≈4735 в `roles_skipped_unlinked_record`. Не «чинить» это ослаблением правила выше.

## Story

As a **Менеджер**,
I want **чтобы уровень цен клиента приезжал из 1С сам и отчёт импорта объяснял каждое решение**,
so that **я перестал вести уровни вручную, а расхождение портала с 1С было видно в отчёте и в `AuditLog`, а не всплывало на заказе**.

## Acceptance Criteria

1. **AC1 (FR-40-07, §5 задания, критерий приёмки #4).** `_update_customer` (`processor.py:433`): если обновляемая запись **проходит** `User.objects.unlinked_1c_record_q()` (непривязанная запись 1С), роль не изменяется ни при каком виде цен, а `onec_price_type_id` записывается по правилам 40.3. Проверка выполняется предикатом в памяти (`user.is_unlinked_1c_record` / `matches_q`), без дополнительного запроса в БД.

2. **AC2 (FR-40-07, FR-40-12).** Если запись **не проходит** `unlinked_1c_record_q()` (живой привязанный аккаунт) и `resolve_role_from_price_types` вернул `reason="resolved"` с ролью, отличной от текущей, — роль аккаунта заменяется разрешённой. Флаг `role_preserved` в `_log_operation` (`processor.py:141-143`) перестаёт быть константой `True` и вычисляется по фактическому исходу.

3. **AC3 (FR-40-12, решение 3 задания).** Роль, выставленная менеджером вручную, перетирается значением из 1С: 1С — источник истины. Прежнее значение сохраняется в `AuditLog`.

4. **AC4 (FR-40-07, критерии приёмки #1, #2).** Привязанный аккаунт контрагента на соглашении «Опт 2» получает роль `wholesale_level2`, на соглашении «Опт 4» — `wholesale_level4`. Маппинг берётся **только** из `PriceType.user_role` через `resolve_role_from_price_types`; хардкод соответствий «GUID → роль» в `processor.py` запрещён.

5. **AC5 (FR-40-08, критерий приёмки #3).** Смена роли импортом создаёт запись `AuditLog` с `action="role_from_1c"`, `resource_type="User"`, `resource_id` = `pk` аккаунта, `user=None` (у импорта нет актора). В `changes` зафиксированы: прежняя роль, новая роль, GUID вида цен, наименование вида цен, наименование соглашения. Наименования берутся из `customer_data["price_type_meta"]` (парсер, 40.1) — **дополнительных запросов в БД за ними нет**.

6. **AC6 (NFR-3940-08, идемпотентность).** Привязанный аккаунт, чья роль уже совпадает с разрешённой: роль не переписывается, `AuditLog` не создаётся, счётчик `roles_updated` не растёт. Повторный прогон той же выгрузки не «дёргает» роль и не плодит записи `AuditLog`.

7. **AC7 (FR-40-09, критерий приёмки #6).** `process_customers` возвращает, а `report_details` сессии импорта содержит счётчики: `roles_updated`, `roles_skipped_no_data`, `roles_skipped_no_agreement`, `roles_skipped_unknown_price_type`, `roles_skipped_ambiguous`. Итоговый вывод команды `import_customers_from_1c` печатает все пять.

8. **AC8 (FR-40-09).** `roles_updated` разбит на две величины — `roles_updated_from_unregistered` (прежняя роль была `unregistered`) и `roles_updated_from_assigned` (прежняя роль была осмысленной). Вторая печатается **отдельной строкой**: перетирание роли, выданной менеджером вручную (AC3), менеджер обязан увидеть, не открывая `AuditLog`. Инвариант: `roles_updated == roles_updated_from_unregistered + roles_updated_from_assigned`.

9. **AC9 (FR-40-09, следствие AC1 и AC6).** Дополнительно к пяти обязательным счётчикам в отчёт входят `roles_skipped_unlinked_record` и `roles_already_actual`. Основание: без первого `roles_updated = 0` первого прогона на проде неотличим от поломки (≈4735 записей пропускаются именно по правилу §5, и это единственное объяснение нуля); без второго счётчики не покрывают все исходы и инвариант AC10 непроверяем. Оба печатаются в итоговом выводе команды.

10. **AC10 (FR-40-09, проверяемость отчёта).** Исходы взаимно исключающие: на каждую успешно **обновлённую** запись приходится ровно один инкремент. Инвариант, проверяемый тестом:
    `roles_updated + roles_already_actual + roles_skipped_unlinked_record + roles_skipped_no_data + roles_skipped_no_agreement + roles_skipped_unknown_price_type + roles_skipped_ambiguous == stats["updated"]`.
    Созданные (`created`) и пропущенные не-покупатели (`skipped`) в ролевые счётчики **не попадают**: у новой записи роль не разрешается вовсе (§5), а не-покупатель до `_update_customer` не доходит.

11. **AC11 (решение 1, критерий приёмки #7).** Привязанный аккаунт с видом цен, неизвестным порталу **или** известным, но не несущим роли (РРЦ, МРЦ, «Детский мир Залоговая», акции, `МКС`, `Закупочные`): роль не изменяется, растёт `roles_skipped_unknown_price_type`.

12. **AC12 (решение 5).** Привязанный аккаунт с двумя и более различными видами цен, каждый из которых несёт роль: роль не изменяется, растёт `roles_skipped_ambiguous`.

13. **AC13 (решение 4).** Привязанный аккаунт без блока `<ЗначенияРеквизитов>` в выгрузке (`price_type_ids == []` и `agreement_status == ""`): роль не изменяется, растёт `roles_skipped_no_data`.

14. **AC14 (FR-40-09, FR-40-05).** Привязанный аккаунт со статусом `НетСоглашения`: роль **не изменяется** — снятие соглашения не означает «клиент больше не оптовик», это решение менеджера. Растёт `roles_skipped_no_agreement`, а `onec_price_type_id` гасится по правилу 40.3 (уже реализовано, не переписывать).

15. **AC15 (критерий приёмки #4, NFR-3940-05).** После прогона импорта контрольной выгрузки запрос
    `SELECT role, COUNT(*) FROM users WHERE created_in_1c AND onec_id IS NOT NULL AND password = '' GROUP BY role`
    возвращает **только** `unregistered`. Доказывается тестом через ORM-эквивалент.

16. **AC16 (NFR-3940-05, критерий приёмки #5).** После того же прогона критические пути привязки не сломаны:
    - `User.objects.unlinked_1c_records()` не пуст;
    - `find_link_candidates(<заявка с ИНН из выгрузки>)` возвращает кандидатов;
    - аннотация `has_1c_candidate_expression()` (`admin.py:91`) и фильтр `Has1CCandidateFilter` (`admin.py:115`) дают непустую выборку;
    - регистрация по ИНН, известному 1С, создаёт заявку (HTTP 201), а не отказ.

17. **AC17 (NFR-3940-09).** Справочник `PriceType` читается **один раз на сессию импорта**: `load_price_type_role_map()` вызывается лениво и кэшируется на экземпляре `CustomerDataProcessor`. Модульный кэш и `lru_cache` запрещены — правка `user_role` в админке не подхватилась бы долгоживущим Celery-воркером. Дополнительного запроса на контрагента не появляется (доказывается `django_assert_num_queries` либо счётчиком запросов).

18. **AC18 (границы стори).** Не изменяются: `apps/users/services/parser.py`, `apps/users/services/price_type_role.py`, `apps/users/services/link_1c_customer.py`, `apps/products/**`, `apps/users/serializers.py`, `apps/users/models.py`, `apps/users/admin.py`, `docs/api/openapi.yaml`, `frontend/**`. Миграций в стори нет. Экспорт заказа (`orders/services/order_export.py`) не трогается.

19. **AC19 (спека).** В `spec-1c-unregistered-role.md` зафиксирована отмена правила «импорт никогда не меняет роль существующего пользователя»: добавлена запись в **Spec Change Log**, а сам текст отменённого правила в теле спеки **вычеркнут** (`~~…~~`) со ссылкой на запись Change Log — во **всех** местах, где он повторён (список — в Dev Notes → «Правка спеки»). Тело документа читают, а changelog — нет.

20. **AC20 (NFR-3940-01, -02, -03).** Тесты построены на реальных XML из `backend/data/import_1c/` (`contragents_pricetype/` — ветки «GUID есть» и `НетСоглашения`; `contragents/` — ветка «блока нет»). Синтетические XML запрещены; конструирование `customer_data` из разобранного снимка — не синтетический XML и разрешено. Покрыты все сценарии таблицы «Часть C» раздела 9 задания. Маркеры проставляются автоматически по каталогу, `@pytest.mark.data_dependent` — вручную. Покрытие затронутых модулей ≥ 90 %.

## Tasks / Subtasks

- [x] **Task 1: Ролевой контракт в процессоре** (AC: 1, 2, 4, 17)
  - [x] 1.1: Расширить импорт из `apps.users.services.price_type_role` (`processor.py:19`): добавить `REASON_AMBIGUOUS`, `REASON_NO_AGREEMENT`, `REASON_NO_DATA`, `REASON_UNKNOWN`, `RoleResolution`, `load_price_type_role_map`, `resolve_role_from_price_types`. `AGREEMENT_STATUS_NONE` уже импортирован — не дублировать; `REASON_RESOLVED` не импортировать (решение принимается по `resolution.role is None`, неиспользуемый импорт покраснеет во flake8)
  - [x] 1.2: Импортировать `matches_q` из `apps.users.models` (`processor.py:18` — там уже `from apps.users.models import Company, User`)
  - [x] 1.3: Объявить на уровне модуля `ROLE_STATS_KEYS` и `SKIP_COUNTER_BY_REASON` (точный код — в Dev Notes). `ROLE_STATS_KEYS` — единственный источник истины набора счётчиков: команда импортирует его же (см. мину «команда суммирует только объявленные ключи»)
  - [x] 1.4: В `__init__` (`processor.py:44`) завести `self._role_map: dict[str, str] | None = None`, `self._role_stats: dict[str, int] = {}`, `self.last_role_outcome: str = ""`
  - [x] 1.5: Добавить property `role_map` с ленивой загрузкой через `load_price_type_role_map()` — AC17. НЕ вешать `lru_cache`, НЕ выносить кэш на уровень модуля
  - [x] 1.6: Добавить приватный метод `_resolve_role_change(user, customer_data) -> RoleChange` (точный код в Dev Notes). Он **не сохраняет** пользователя и **не пишет** `AuditLog` — только решает

- [x] **Task 2: Применение роли и AuditLog** (AC: 2, 3, 5, 6, 14)
  - [x] 2.1: В `_update_customer` (`processor.py:433`) вычислить `change = self._resolve_role_change(user, customer_data)` **до** `user.save()`, при `change.applied` присвоить `user.role = change.new_role`. Строку `user.onec_price_type_id = self._price_type_id_to_store(...)` (`processor.py:465`) не трогать — 40.3 работает как есть
  - [x] 2.2: После `user.save()` при `change.applied` вызвать `self._log_role_change(user, change)` — `AuditLog.log_action(...)` (точный код в Dev Notes). Порядок обязателен: логировать до сохранения значит записать смену, которой может не случиться
  - [x] 2.3: Записать `self.last_role_outcome = change.outcome` в конце `_update_customer`. Сигнатуру метода **не менять** — она читается вызывающим `process_customer`, и смена возвращаемого типа расширила бы blast radius
  - [x] 2.4: В `process_customer` (`processor.py:75`) сбросить `self.last_role_outcome = ""` **в начале** метода — иначе исход предыдущего контрагента протечёт на создание/пропуск
  - [x] 2.5: В ветке `if existing_user:` (`processor.py:131-145`) заменить `"role_preserved": True` на вычисляемое значение и добавить `"role_outcome"` (точный код в Dev Notes). Комментарий над веткой (`processor.py:132-134`) переписать: роль привязанного аккаунта теперь приезжает из 1С
  - [x] 2.6: Обновить docstring `_update_customer` (`processor.py:434-450`) и строку `logger.info(... роль=... сохранена)` (`processor.py:476`) — утверждение «роль сохранена» стало ложным
  - [x] 2.7: НЕ трогать `_create_customer`: новая запись получает `IMPORTED_CUSTOMER_ROLE` всегда (§5). Комментарий у `IMPORTED_CUSTOMER_ROLE` (`processor.py:39-42`) устарел по существу («в выгрузке уровня цен нет») — привести в соответствие, не меняя значение константы

- [x] **Task 3: Счётчики сессии импорта** (AC: 7, 8, 9, 10)
  - [x] 3.1: В `process_customers` (`processor.py:184`) инициализировать `self._role_stats = {key: 0 for key in ROLE_STATS_KEYS}` **до** цикла — счётчики пофайловые, команда суммирует их сама
  - [x] 3.2: После `result = self.process_customer(customer_data)` (`processor.py:226`) инкрементировать `self._role_stats[self.last_role_outcome]`, если `result` не `None` и `self.last_role_outcome` непуст. Счёт **вне** `transaction.atomic()` — откат внутри `process_customer` не должен оставлять фантомный инкремент
  - [x] 3.3: Перед `return stats` вычислить `roles_updated` как сумму двух слагаемых и влить `self._role_stats` в `stats` (точный код в Dev Notes)
  - [x] 3.4: Обновить docstring `process_customers` (`processor.py:185-196`): перечислить новые ключи
  - [x] 3.5: Счётчики `attributes_block_present` / `attributes_block_missing` (40.1) и их логику (`processor.py:213-218`) **не менять**

- [x] **Task 4: Отчёт команды** (AC: 7, 8, 9)
  - [x] 4.1: В `import_customers_from_1c.py` импортировать `ROLE_STATS_KEYS` из `apps.users.services.processor` и добавить ключи в `total_stats` (`import_customers_from_1c.py:116-126`). ⚠️ Мина: цикл суммирования идёт по `total_stats.keys()` (`:146-147`) — незаявленный ключ молча потеряется
  - [x] 4.2: Дополнить итоговый вывод (`:200-219`) блоком ролевых счётчиков (точный текст в Dev Notes). `roles_updated_from_assigned` — **отдельной строкой** (AC8)
  - [x] 4.3: Блок печатается в той же ветке `else` (не dry-run), рядом с существующими строками; предупреждение об аномалии выгрузки (`:180-188`) не трогать
  - [x] 4.4: НЕ добавлять новых аргументов команды и НЕ менять поведение `--dry-run`

- [x] **Task 5: Unit-тесты процессора** (AC: 1–6, 11–14, 17, 20)
  - [x] 5.1: Новый класс `TestCustomerRoleFromPriceType` в `backend/tests/unit/test_services/test_customer_processor.py`, маркеры `@pytest.mark.unit`, `@pytest.mark.django_db`, `@pytest.mark.data_dependent`. Фикстуры `session`/`processor` продублировать по образцу `TestCustomerPriceTypeStorage` (`test_customer_processor.py:490-501`) — они объявлены методами класса и новому классу не видны
  - [x] 5.2: Переиспользовать module-scoped фикстуры реального снимка (`real_customers`, `customer_with_price_type`, `customer_without_agreement`, `customer_without_attributes_block`, `snapshot_price_type_guids`, `test_customer_processor.py:425-475`) — новых не заводить
  - [x] 5.3: Добавить фикстуру `customer_with_opt4` — `dict(customer_with_price_type)` с `price_type_ids`, подменённым на `["4c1962d2-f8ed-11eb-81f3-00155d3cae02"]` («Опт 4»: единственный GUID, засеянный миграцией `products/0053` с `user_role="wholesale_level4"`). ⚠️ **Не искать такого контрагента в снимке**: 40.3 показала, что в первом файле 32 контрагента с одним `ТипЦенId`, но какие именно это виды цен — не зафиксировано, и поиск дал бы недетерминированный `skip`. Подмена `price_type_ids` — вариация входа сервиса, а не синтетический XML (то же решение, что для ветки `ambiguous` в 40.3)
  - [x] 5.4: Тест AC1: непривязанная запись 1С (созданная предыдущим прогоном импорта) + GUID «Опт 4» → `role == "unregistered"`, `onec_price_type_id` заполнен, `AuditLog` нет, `last_role_outcome == "roles_skipped_unlinked_record"`
  - [x] 5.5: Тест AC2/AC4: привязанный аккаунт (`created_in_1c=False`, роль `wholesale_level1`, пароль задан) + «Опт 4» → `role == "wholesale_level4"`; тот же сценарий для «Опт 2» после `get_or_create` записи `PriceType` (GUID `a91bdb02-…`, `user_role="wholesale_level2"`)
  - [x] 5.6: Тест AC3/AC5: роль выставлена вручную (`wholesale_level3`), 1С отдаёт «Опт 4» → роль перетёрта, ровно одна запись `AuditLog` с `action="role_from_1c"`, в `changes` — `previous_role="wholesale_level3"`, `new_role="wholesale_level4"`, непустые `price_type_id`, `price_type_name`, `agreement_name`
  - [x] 5.7: Тест AC6: роль уже совпадает → `AuditLog.objects.count() == 0`, `last_role_outcome == "roles_already_actual"`; повторный прогон на тех же данных → по-прежнему одна запись `AuditLog` (после сценария 5.6) и роль не «дёргается»
  - [x] 5.8: Тест AC11: привязанный аккаунт + GUID, отсутствующий в `PriceType`, и отдельным случаем — GUID **известный, но с пустым `user_role`** (создать через `get_or_create` РРЦ `3d1482c4-…`, `user_role=""`) → роль не изменилась, исход `roles_skipped_unknown_price_type`
  - [x] 5.9: Тест AC12: два GUID, каждый с ролью («Опт 4» + созданный «Опт 2») → роль не изменилась, исход `roles_skipped_ambiguous`
  - [x] 5.10: Тест AC13: `customer_without_attributes_block` (старый снимок) → роль не изменилась, исход `roles_skipped_no_data`
  - [x] 5.11: Тест AC14: `customer_without_agreement` → роль не изменилась, исход `roles_skipped_no_agreement`, `onec_price_type_id == ""`
  - [x] 5.12: Тест AC17: `process_customers` на списке из ≥ 20 контрагентов делает **один** запрос к `price_types` (перехватить через `django_assert_num_queries` на изолированном участке либо через `CaptureQueriesContext` с фильтром по `price_types`); `processor.role_map` дважды подряд — один запрос
  - [x] 5.13: Тест AC10: `process_customers` на реальном списке → сумма ролевых счётчиков равна `stats["updated"]`, `roles_updated == from_unregistered + from_assigned`
  - [x] 5.14: ⚠️ **Проверить и поправить существующие тесты** (список и ожидаемая реакция — в Dev Notes → «Мины в существующих тестах»). Формально они остаются зелёными, но их комментарии утверждают отменённое правило

- [x] **Task 6: Интеграционный тест на реальной выгрузке** (AC: 5, 7, 8, 9, 15, 16, 20)
  - [x] 6.1: Создать `backend/tests/integration/test_import_role_from_1c.py`; маркеры: `integration` автоматически по каталогу, добавить `@pytest.mark.data_dependent` и `@pytest.mark.django_db`. Сборку временного каталога и выбор файла снимка взять из `tests/integration/test_import_customers_price_type.py` (40.3) — не изобретать заново; команда требует подкаталог именно `contragents/`
  - [x] 6.2: Тест AC15: прогнать `call_command("import_customers_from_1c", data_dir=<tmp>)`; ORM-эквивалент критерия #4 — `User.objects.filter(created_in_1c=True, onec_id__isnull=False, password="").values_list("role", flat=True).distinct()` возвращает ровно `{"unregistered"}`
  - [x] 6.3: Тест AC7/AC9: `ImportSession.report_details` последней завершённой сессии содержит все ключи `ROLE_STATS_KEYS`; на прогоне «с нуля» `roles_updated == 0`, а `roles_skipped_unlinked_record == 0` (все записи создаются, не обновляются). Повторный прогон того же файла даёт `roles_skipped_unlinked_record > 0` — это и есть наблюдаемая норма прода
  - [x] 6.4: Тест AC2/AC5 на живых данных. ⚠️ **Не зашивать «Опт 4»**: в выбранном файле снимка контрагента с этим GUID может не быть (40.3 зафиксировала лишь число контрагентов с одним `ТипЦенId`, но не состав видов цен). Порядок: (1) разобрать файл, взять первого покупателя с ровно одним GUID; (2) `PriceType.objects.get_or_create(onec_id=<этот GUID>, defaults={"onec_name": "…", "product_field": "opt2_price", "user_role": "wholesale_level2", "is_active": True})` — `get_or_create`, а не `create`: GUID может оказаться «Опт 4», уже засеянным `products/0053`, и `create` даст `duplicate key`; (3) завести привязанный аккаунт с `onec_id` этого контрагента, роль `wholesale_level1`, пароль задан; (4) после прогона роль равна `user_role` записи справочника, есть `AuditLog(action="role_from_1c")`, в `report_details` `roles_updated == 1` и `roles_updated_from_assigned == 1`. Ожидаемую роль брать из созданной записи `PriceType`, а не из литерала
  - [x] 6.5: Тест AC16: после прогона `User.objects.unlinked_1c_records().exists()`; `find_link_candidates(<заявка с ИНН из выгрузки>)` не пуст; `User.objects.annotate(_has_1c_candidate=has_1c_candidate_expression()).filter(_has_1c_candidate=True).exists()`
  - [x] 6.6: Тест AC16 (регистрация): POST на `REGISTER_URL` с ИНН, известным выгрузке, → HTTP 201. Образец полезной нагрузки и мока письма админу — `tests/integration/test_portal_registration_1c_link.py:98-124`
  - [x] 6.7: ⚠️ Мина объёма: копировать в tmp-каталог **один** файл снимка, не все 10 (4735 `User` + столько же `CustomerSyncLog` — десятки минут)

- [x] **Task 7: Правка спеки** (AC: 19)
  - [x] 7.1: В `_bmad-output/implementation-artifacts/spec-1c-unregistered-role.md` вычеркнуть (`~~…~~`) отменённое правило во всех четырёх местах — точный список строк в Dev Notes → «Правка спеки»
  - [x] 7.2: Добавить запись в раздел **Spec Change Log** датой реализации: что отменено, чем заменено, ссылка на стори 40.4 и FR-40-07/FR-40-12
  - [x] 7.3: Правка затрагивает блок `<frozen-after-approval>` — это санкционировано AC стори 40.4 в `epics.md` (решение Alex). В записи Change Log указать это явно; остальное содержимое frozen-блока не трогать

- [x] **Task 8: Прогон, регресс, линтеры** (AC: 18, 20)
  - [x] 8.1: Прогон новых тестов в тест-контейнере (команды — в Dev Notes → «Тестирование: как запускать»)
  - [x] 8.2: Регресс обязательным списком: `tests/unit/test_services/test_customer_processor.py`, `tests/unit/test_services/test_customer_parser.py`, `tests/unit/test_services/test_price_type_role.py`, `tests/unit/test_services/test_link_1c_customer.py`, `tests/unit/test_users_admin.py`, `tests/integration/test_import_customers_price_type.py`, `tests/integration/test_customers_price_type_detector.py`, `tests/integration/test_management_commands/test_import_customers.py`, `tests/integration/test_link_then_import_1c.py`, `tests/integration/test_portal_registration_1c_link.py`, `tests/integration/test_admin_link_1c_customer.py`
  - [x] 8.3: Полный прогон `pytest -q` **без** `-m`: маркер-фильтры CI оставляют 852 теста вне гейтов, регрессия ловится только полным набором
  - [x] 8.4: `manage.py makemigrations --check --dry-run` → `No changes detected` (доказывает, что модели не тронуты, AC18)
  - [x] 8.5: `black` + `flake8` на изменённых файлах
  - [x] 8.6: `git diff HEAD --stat` — убедиться, что в диффе нет `apps/users/models.py`, `apps/users/admin.py`, `apps/users/serializers.py`, `apps/users/services/parser.py`, `apps/users/services/price_type_role.py`, `apps/users/services/link_1c_customer.py`, `apps/products/**`, `docs/api/openapi.yaml`, `frontend/**` (AC18)
  - [x] 8.7: `npx gitnexus detect-changes --scope all` из основного клона. Ожидаемые символы: `_update_customer`, `process_customer`, `process_customers`, новые `_resolve_role_change` / `_log_role_change` / `role_map`, `Command.handle`

## Dev Notes

### Что уже есть и переиспользуется (не изобретать)

| Нужное | Где уже есть |
|---|---|
| Разрешение роли по GUID + все пять `reason` | `resolve_role_from_price_types` (`apps/users/services/price_type_role.py:71`). Сигнатура: `(price_type_ids, agreement_status="", *, role_map=None) -> RoleResolution(role, reason, matched)` |
| Чтение справочника одним запросом | `load_price_type_role_map()` (`price_type_role.py:36`). Уже отсеивает регистровых двойников и записи с пустым `user_role` |
| Константы причин | `REASON_RESOLVED / REASON_NO_DATA / REASON_NO_AGREEMENT / REASON_UNKNOWN / REASON_AMBIGUOUS` (`price_type_role.py:21-25`). Строковые литералы не дублировать |
| Предикат «непривязанная запись 1С» в памяти | `User.is_unlinked_1c_record` (`models.py:384`) → `matches_q(UserManager.unlinked_1c_record_q(), self)` (`models.py:17`). Запроса в БД не делает |
| GUID, наименование вида цен, наименование соглашения | `customer_data["price_type_meta"]` — список словарей с ключами `price_type_id`, `price_type_name`, `agreement_name`, `agreement_is_standard` (`parser.py:194`, стори 40.1) |
| Запись в аудит | `AuditLog.log_action(user, action, resource_type, resource_id, details=None, changes=None, ...)` (`apps/common/models.py:379`). `changes` кладётся в `details["changes"]`, читается property `AuditLog.changes` |
| Образец `log_action` в users | `apps/users/admin.py:510`, `link_1c_customer.py:228` |
| Запись `onec_price_type_id` | `_price_type_id_to_store` (`processor.py:343`, стори 40.3) — **готово, переписывать нельзя** |
| Аннотация «Кандидат 1С» для регрессионного теста | `has_1c_candidate_expression()` (`admin.py:91`), `Has1CCandidateFilter` (`admin.py:115`) |
| Образец интеграционного теста импорта на реальной выгрузке | `tests/integration/test_import_customers_price_type.py` (40.3) |
| Образец теста регистрации по ИНН | `tests/integration/test_portal_registration_1c_link.py` (`REGISTER_URL`, мок письма админу) |

### Точный код: константы модуля

`backend/apps/users/services/processor.py`, после `logger = logging.getLogger(__name__)` (`processor.py:25`):

```python
# Ключи ролевых счётчиков сессии импорта. Единственный источник истины:
# команда import_customers_from_1c суммирует ТОЛЬКО объявленные у себя ключи,
# поэтому она импортирует этот кортеж, а не перечисляет имена заново.
ROLE_STATS_KEYS = (
    "roles_updated",
    "roles_updated_from_unregistered",
    "roles_updated_from_assigned",
    "roles_already_actual",
    "roles_skipped_unlinked_record",
    "roles_skipped_no_data",
    "roles_skipped_no_agreement",
    "roles_skipped_unknown_price_type",
    "roles_skipped_ambiguous",
)

# Причина отказа резолвера → счётчик отчёта. Словарь, а не цепочка if:
# добавление шестой причины в price_type_role.py обязано падать здесь
# явным KeyError, а не молча теряться в отчёте.
SKIP_COUNTER_BY_REASON = {
    REASON_NO_DATA: "roles_skipped_no_data",
    REASON_NO_AGREEMENT: "roles_skipped_no_agreement",
    REASON_UNKNOWN: "roles_skipped_unknown_price_type",
    REASON_AMBIGUOUS: "roles_skipped_ambiguous",
}

# Исход разрешения роли для одной записи. Отдаётся вызывающему через
# self.last_role_outcome, а не возвращаемым значением _update_customer:
# смена сигнатуры расширила бы blast radius на process_customer и тесты.
class RoleChange(NamedTuple):
    outcome: str                 # ключ из ROLE_STATS_KEYS
    applied: bool                # роль реально меняется
    previous_role: str
    new_role: str
    resolution: RoleResolution | None
```

Импорты (`processor.py:9`, `:19`):

```python
from typing import TYPE_CHECKING, Any, NamedTuple

from apps.common.models import AuditLog
from apps.users.models import Company, User, matches_q
from apps.users.services.price_type_role import (
    AGREEMENT_STATUS_NONE,
    REASON_AMBIGUOUS,
    REASON_NO_AGREEMENT,
    REASON_NO_DATA,
    REASON_UNKNOWN,
    RoleResolution,
    load_price_type_role_map,
    resolve_role_from_price_types,
)
```

⚠️ `apps.common.models` уже импортируется в `processor.py:17` (`CustomerSyncLog`) — добавить `AuditLog` в существующую строку, не заводить вторую.

**Новых межмодульных зависимостей стори не вводит.** Оба модуля (`apps.common.models`, `apps.users.services.price_type_role`) импортируются `processor.py` на уровне модуля уже сейчас. Отсутствие цикла через `price_type_role → apps.products.models` проверено в 40.3 (`manage.py check` чист, запасной вариант с локальным импортом не понадобился) — повторно это выяснять не нужно. Локальные импорты внутри функций здесь заводить не надо: единственный оставшийся локальный импорт в файле — `ImportSession` в `__init__` (`processor.py:51`), и он трогается не должен.

### Точный код: ленивый маппинг и решение о роли

В `__init__` (`processor.py:44-53`), после `self.session = ...`:

```python
        # Справочник видов цен читается один раз на сессию импорта (NFR-3940-09).
        # Кэш живёт на экземпляре, а не на модуле: lru_cache пережил бы правку
        # user_role в админке внутри долгоживущего Celery-воркера.
        self._role_map: dict[str, str] | None = None
        self._role_stats: dict[str, int] = {}
        # Исход разрешения роли для последнего обработанного контрагента.
        # Пустая строка — роль не разрешалась (создание, пропуск, ошибка).
        self.last_role_outcome: str = ""
```

Property и решение — рядом с `_price_type_id_to_store` (`processor.py:343`):

```python
    @property
    def role_map(self) -> dict[str, str]:
        """Маппинг GUID вида цен → роль портала, один запрос на сессию импорта."""
        if self._role_map is None:
            self._role_map = load_price_type_role_map()
        return self._role_map

    def _resolve_role_change(self, user: User, customer_data: dict[str, Any]) -> RoleChange:
        """
        Решает, менять ли роль существующего пользователя по данным из 1С.

        Пользователя НЕ сохраняет и AuditLog НЕ пишет — это делает
        _update_customer, чтобы запись в журнал не опередила сохранение.

        Непривязанная запись 1С роли не получает никогда (§5 задания):
        unlinked_1c_record_q() включает role='unregistered', и смена роли
        выбила бы запись из выборки кандидатов на привязку — вернулся бы
        баг, чинившийся миграцией 0018.

        Args:
            user: существующая запись (поля роли ещё не тронуты).
            customer_data: словарь из парсера.

        Returns:
            RoleChange: исход для счётчика отчёта и решение о применении.
        """
        current_role = user.role

        # Предикат в памяти, а не запрос: тот же Q, что и у queryset-фильтра.
        if matches_q(User.objects.unlinked_1c_record_q(), user):
            return RoleChange("roles_skipped_unlinked_record", False, current_role, current_role, None)

        resolution = resolve_role_from_price_types(
            customer_data.get("price_type_ids") or [],
            str(customer_data.get("agreement_status") or ""),
            role_map=self.role_map,
        )

        # Проверять именно role is None, а не reason != REASON_RESOLVED:
        # резолвер отдаёт непустую роль ровно при reason="resolved", и
        # сравнение по reason дало бы KeyError на несуществующей комбинации.
        if resolution.role is None:
            return RoleChange(SKIP_COUNTER_BY_REASON[resolution.reason], False, current_role, current_role, resolution)

        if resolution.role == current_role:
            # Роль уже актуальна: перезапись породила бы запись AuditLog на
            # каждом обмене и сделала бы журнал нечитаемым (NFR-3940-08).
            return RoleChange("roles_already_actual", False, current_role, current_role, resolution)

        outcome = (
            "roles_updated_from_unregistered"
            if current_role == User.ROLE_UNREGISTERED
            else "roles_updated_from_assigned"
        )
        return RoleChange(outcome, True, current_role, resolution.role, resolution)
```

**Порядок проверок неизменяем.** Сначала «непривязанная запись», потом резолвер: обратный порядок дал бы непривязанным записям причины `no_data`/`unknown_price_type` вместо единственно верной, и `roles_updated = 0` первого прогона на проде перестал бы объясняться отчётом.

### Точный код: журнал смены роли

Рядом с `_log_operation` (`processor.py:479`):

```python
    def _log_role_change(self, user: User, change: RoleChange, customer_data: dict[str, Any]) -> None:
        """
        Пишет AuditLog о смене роли по данным 1С (FR-40-08).

        Наименования вида цен и соглашения берутся из price_type_meta
        парсера, а не запросом в PriceType: в пакете тысячи контрагентов,
        и запрос за подписью свёл бы на нет экономию role_map.

        actor отсутствует: смену выполняет импорт, а не человек.
        """
        guid = change.resolution.matched[0] if change.resolution and change.resolution.matched else ""
        meta = next(
            (item for item in (customer_data.get("price_type_meta") or []) if item.get("price_type_id") == guid),
            {},
        )

        AuditLog.log_action(
            user=None,
            action="role_from_1c",
            resource_type="User",
            resource_id=user.pk,
            details={"source": "import_1c", "session_id": str(self.session.pk), "onec_id": user.onec_id or ""},
            changes={
                "previous_role": change.previous_role,
                "new_role": change.new_role,
                "price_type_id": guid,
                "price_type_name": str(meta.get("price_type_name") or ""),
                "agreement_name": str(meta.get("agreement_name") or ""),
            },
        )
```

### Точный код: встраивание в `_update_customer` и `process_customer`

`_update_customer` — вставки помечены `# NEW`:

```python
        role_change = self._resolve_role_change(user, customer_data)   # NEW: до save()
        if role_change.applied:                                        # NEW
            user.role = role_change.new_role                           # NEW
        user.onec_price_type_id = self._price_type_id_to_store(customer_data, user.onec_price_type_id)
        user.sync_status = "synced"
        user.last_sync_at = timezone.now()

        user.save()

        if role_change.applied:                                        # NEW
            self._log_role_change(user, role_change, customer_data)    # NEW
        self.last_role_outcome = role_change.outcome                   # NEW
```

⚠️ Порядок: `_resolve_role_change` обязан вызываться **до** присвоений `user.*`? — нет, но обязан вызываться до `user.role = ...`. Поля, которые `_update_customer` меняет (`first_name`, `phone`, `company_name`, `tax_id`, `onec_id`, `onec_price_type_id`, `sync_status`, `last_sync_at`), в `unlinked_1c_record_q()` не входят — предикат опирается на `created_in_1c`, `role`, `verification_status`, `password`. Расположение вставки в начале блока выбрано ради читаемости, а не корректности.

`process_customer` (`processor.py:75`), первой строкой тела после docstring:

```python
        # Исход прошлого контрагента не должен протечь: create/skip/error
        # ролевых счётчиков не трогают вовсе.
        self.last_role_outcome = ""
```

`_log_operation` для ветки обновления (`processor.py:136-145`):

```python
                    user = self._update_customer(existing_user, customer_data)
                    self._log_operation(
                        user=user,
                        onec_id=onec_id,
                        operation_type="updated",
                        status="success",
                        details={
                            "role": user.role,
                            "role_outcome": self.last_role_outcome,
                            # Флаг перестал быть константой: у привязанного
                            # аккаунта роль теперь приезжает из 1С (FR-40-12).
                            "role_preserved": self.last_role_outcome
                            not in ("roles_updated_from_unregistered", "roles_updated_from_assigned"),
                        },
                    )
```

### Точный код: счётчики в `process_customers`

До цикла (`processor.py:197`, рядом с инициализацией `stats`):

```python
        # Счётчики пофайловые: команда суммирует результаты по файлам сама.
        self._role_stats = {key: 0 for key in ROLE_STATS_KEYS}
```

После `result = self.process_customer(customer_data)` (`processor.py:226`), в ветке `if result:`:

```python
                # Инкремент вне transaction.atomic() процессора: откат внутри
                # process_customer не должен оставлять фантомный счётчик.
                if self.last_role_outcome:
                    self._role_stats[self.last_role_outcome] += 1
```

Перед `return stats` (`processor.py:253`):

```python
        self._role_stats["roles_updated"] = (
            self._role_stats["roles_updated_from_unregistered"] + self._role_stats["roles_updated_from_assigned"]
        )
        stats.update(self._role_stats)
```

### Точный код: вывод команды

`import_customers_from_1c.py` — в `total_stats` (`:116-126`) добавить `**{key: 0 for key in ROLE_STATS_KEYS}`; в итоговый блок (`:200-219`) после строки «Контрагентов без блока реквизитов»:

```python
                        f"\nРоли из 1С:\n"
                        f"  Обновлено ролей: {total_stats['roles_updated']}\n"
                        f"    из них были unregistered: {total_stats['roles_updated_from_unregistered']}\n"
                        f"    из них перетёрта роль, выданная менеджером: "
                        f"{total_stats['roles_updated_from_assigned']}\n"
                        f"  Роль уже актуальна: {total_stats['roles_already_actual']}\n"
                        f"  Пропущено (непривязанная запись 1С): "
                        f"{total_stats['roles_skipped_unlinked_record']}\n"
                        f"  Пропущено (нет данных о виде цен): {total_stats['roles_skipped_no_data']}\n"
                        f"  Пропущено (нет соглашения): {total_stats['roles_skipped_no_agreement']}\n"
                        f"  Пропущено (вид цен не даёт роли): "
                        f"{total_stats['roles_skipped_unknown_price_type']}\n"
                        f"  Пропущено (несколько видов цен): {total_stats['roles_skipped_ambiguous']}\n"
```

### Мины в существующих тестах

Ни один существующий тест **не должен покраснеть** — но три держатся на утверждениях, которые эта стори отменяет. Прогнать их и привести комментарии в соответствие обязательно: иначе следующее переснятие снимка или пополнение справочника `PriceType` сделает падение необъяснимым.

| Тест | Почему остаётся зелёным | Что сделать |
|---|---|---|
| `test_import_preserves_role_assigned_by_manager` (`test_customer_processor.py:122`) | `customer_data` собран вручную, без `price_type_ids` и `agreement_status` → `reason="no_data"` → роль не меняется | Дописать в docstring: роль сохраняется **потому что** данных о виде цен нет, а не потому, что импорт роль не трогает |
| `test_update_existing_customer_by_onec_id` (`test_customer_processor.py:237`) | То же: `no_data` | Поправить комментарий `# Роль существующей записи импорт не меняет` (`:264`) |
| `test_update_stores_price_type_for_linked_account` (`test_customer_processor.py:513`) | GUID фикстуры отсутствует в `PriceType` (это утверждает соседний `test_price_type_stored_even_if_unknown_to_reference`) → `unknown_price_type` | Заменить комментарий «Роль в 40.3 неприкосновенна» на явное «роль не меняется, потому что GUID не несёт роли», иначе тест станет ложно-зелёным маркером отменённого правила |
| `test_repeated_run_is_idempotent` (`test_customer_processor.py:612`) | Запись создаётся импортом → непривязанная → роль не разрешается → `AuditLog` пуст | Поправить комментарий `# AuditLog заводит стори 40.4 — здесь его быть не должно` (`:637`) |
| `test_link_then_reimport_updates_applicant_without_duplicate` (`tests/integration/test_link_then_import_1c.py:104`) | Снимок `contragents/` блока `<ЗначенияРеквизитов>` не содержит → `no_data` | Уточнить сообщение ассерта: роль сохраняется из-за отсутствия блока в старом снимке, а не по правилу «импорт роль не трогает» |
| `tests/integration/test_import_customers_price_type.py::test_roles_unchanged_after_import` (40.3) | Все записи снимка создаются импортом и остаются непривязанными | Не трогать — теперь это ещё и доказательство критерия приёмки #4 |

### Правка спеки

`_bmad-output/implementation-artifacts/spec-1c-unregistered-role.md` — отменённое правило повторено в четырёх местах, вычеркнуть нужно все:

| Строка | Текст |
|---|---|
| `:27` (Boundaries → Always) | «Импорт 1С назначает роль **только при создании** записи. Роль существующего пользователя импорт не меняет никогда…» |
| `:55` (I/O-матрица, строка «Импорт существующего») | «Данные обновляются, `role` остаётся `wholesale_level2`» |
| `:101` (Acceptance Criteria) | «Given пользователь с ролью `wholesale_level2`, выданной менеджером, when запускается импорт…, then роль остаётся `wholesale_level2`» |
| `:123` (KEEP, пункт 1) | «…отказ от перезаписи роли существующего пользователя» |

Строки `:27`, `:55` и `:101` находятся внутри блока `<frozen-after-approval>`. Правка санкционирована AC стори 40.4 в `epics.md` (решение Alex) — это и есть renegotiation, которого требует атрибут `reason`. В записи Change Log указать это явно. Остальное содержимое frozen-блока не трогать.

Что остаётся в силе и **не** вычёркивается: правило «роль назначается при **создании**» (новая запись по-прежнему получает `unregistered`, §5) — отменена только его вторая половина про существующих пользователей, и только для записей, **не** проходящих `unlinked_1c_record_q()`.

### Почему счётчиков девять, а не пять

Эпик требует пять (`roles_updated` + четыре `roles_skipped_*`) и явно требует разбить `roles_updated` на две величины — это уже семь. Ещё два добавлены с обоснованием:

- **`roles_skipped_unlinked_record`** — на проде это ≈4735 из 4735. Без него `roles_updated = 0` в день выката читается как «не работает», хотя это ожидаемое поведение по §5 (см. «Отложенный эффект» в шапке). Счётчик и есть тот самый наблюдаемый сигнал, что правило §5 отработало, а не что импорт молчит.
- **`roles_already_actual`** — иначе исходы не покрывают все ветки, и инвариант AC10 (сумма счётчиков = число обновлённых записей) непроверяем; молчаливый «шестой исход без счётчика» — ровно тот класс дыры в отчёте, который эпик и закрывает.

### Blast radius (обязательный pre-flight выполнен)

```
npx gitnexus impact _update_customer     --direction upstream → risk: LOW,      impacted: 3
npx gitnexus impact process_customers    --direction upstream → risk: LOW,      impacted: 1
npx gitnexus impact unlinked_1c_record_q --direction upstream → risk: CRITICAL, impacted: 12
```

Цепочка изменяемого кода замкнута внутри импорта контрагентов:
`_update_customer` ← `process_customer` ← `process_customers` ← `Command.handle` (`import_customers_from_1c.py`). Затронутых процессов — 0, модулей — 1 (Services). Единственная точка входа в импорт — эта команда; Celery и вью вызывают её же (`apps/integrations/tasks.py:170`, `apps/products/tasks.py:215`).

🔴 **`unlinked_1c_record_q` — `risk: CRITICAL`, 5 затронутых процессов** (`link_1c_customer`, `onec_link_candidates`, `approve_b2b_users`, `UserAdmin.get_queryset`, `get_fieldsets`). Стори **читает** предикат и **не изменяет** его — это единственный безопасный режим работы с ним. Но сам факт риска объясняет, почему AC16 — обязательный, а не «на всякий случай»: смена роли непривязанной записи выбивает её из всех пяти процессов сразу, и падает не импорт, а привязка через неделю.

Изменение аддитивное: новых полей моделей нет, миграций нет, ни одна существующая сигнатура не меняется. Расширяется набор ключей `stats` / `report_details` — потребителей у конкретных ключей нет (`report_details` показывается в админке как JSON readonly, `apps/integrations/admin.py:41`).

### Тестирование: как запускать

`make` на машине недоступен, а таргеты `test-*` ищут несуществующий `docker/.env`. Рабочий эквивалент из основного клона:

```bash
cd /c/Users/1/DEV/FREESPORT/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -q tests/unit/test_services/test_customer_processor.py \
            tests/integration/test_import_role_from_1c.py
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down
```

Линтеры:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  black apps/users/services/processor.py apps/users/management/commands/import_customers_from_1c.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend flake8 apps/users/
```

Особенности тестовой среды, проверенные в 40.2 и 40.3:

- **Тестовая БД строится С миграциями** (в `backend/pytest.ini` нет `--nomigrations`, вопреки `backend/CLAUDE.md`). Практические следствия: запись «Опт 4» (`4c1962d2-f8ed-11eb-81f3-00155d3cae02`, `user_role="wholesale_level4"`) уже засеяна миграцией `products/0053` — создавать её в тесте нельзя (`duplicate key`), только `get_or_create`. Остальные GUID снимка справочнику неизвестны и годятся для веток `unknown_price_type`.
- Маркеры `unit` / `integration` проставляются автоматически по каталогу (`backend/conftest.py`); `@pytest.mark.data_dependent` — вручную.
- `container_name` в `docker-compose.test.yml` зашит жёстко — параллельно поднятый тест-стек даст конфликт имён.
- `pytest-timeout` не установлен, `--timeout=` не работает.
- Module-scoped фикстуры не могут зависеть от function-scoped `settings` — путь к снимку в них считается из `settings.BASE_DIR` напрямую (`test_customer_processor.py:425-440`). В интеграционных тестах штатно используется фикстура `onec_data_dir` (`tests/conftest.py:419`).

### Реальные данные: что лежит в снимке

`backend/data/import_1c/contragents_pricetype/` — 10 файлов, 4735 контрагентов (замер 40.1, вторая редакция патча): с блоком реквизитов — все 4735, с непустым `ТипЦенId` — 485, со статусом `НетСоглашения` — 4250, с более чем одним **различным** GUID — **0**.

| GUID | Наименование | Контрагентов | Есть в `PriceType` тестовой БД |
|---|---|---|---|
| `c05f0e2b-b3f2-11ea-81c3-00155d3cae02` | Опт 3 (50-150 тыс.руб в квартал) | 176 | нет |
| `4c1962d2-f8ed-11eb-81f3-00155d3cae02` | Опт 4 (до 50 тыс.руб в квартал) | 123 | **да**, `user_role="wholesale_level4"` |
| `a91bdb02-b3f2-11ea-81c3-00155d3cae02` | Опт 2 (150-300 тыс.руб в квартал) | 78 | нет |
| `90d2c899-b3f2-11ea-81c3-00155d3cae02` | Опт 1 (300-600 тыс.руб в квартал) | 64 | нет |
| `3d1482c4-bd77-11e4-afc8-20cf3073dde3` | РРЦ | 42 | нет (на проде — с пустым `user_role`) |
| `28049309-b6be-11ec-a301-04421a23d8e8` | Детский мир Залоговая | 2 | нет |

Ветка `ambiguous` в снимке отсутствует по построению — собирается вариацией входа сервиса (два GUID из того же снимка), синтетический XML запрещён. `backend/data/import_1c/contragents/` — старый снимок от 11.04.2026 **без** блока у кого-либо: готовые данные для ветки `no_data`.

**Первый файл снимка** (замер 40.3): 235 контрагентов, все покупатели — 32 с одним `ТипЦенId`, 203 со статусом `НетСоглашения`, с двумя различными GUID — ноль. Состав видов цен внутри файла **не зафиксирован**, поэтому тесты не должны предполагать наличие конкретного GUID (см. Task 5.3 и 6.4). Интеграционный тест 40.3 выбирает файл **по содержимому** — наименьший, где есть обе ветки, — а не по имени и не по размеру: состав пакетов меняется при каждом переснятии выгрузки. Переиспользовать этот же helper.

### Границы стори (что делают соседние стори — здесь НЕ делать)

- **40.1** (done) — парсер (`price_type_ids`, `price_type_meta`, `agreement_status`), детектор регресса выгрузки. `parser.py` не трогается.
- **40.2** (done) — `PriceType.user_role`, админка справочника, `resolve_role_from_price_types`, сторож `PRICE_TYPE_BY_ROLE ↔ PriceType.user_role`. `price_type_role.py` не трогается: стори его **вызывает**, а не правит.
- **40.3** (done) — `User.onec_price_type_id`, `_price_type_id_to_store`, отображение вида цен в админке. Логика записи поля не переписывается ни в одной строке.
- **40.5** — перенос вида цен и применение роли **при привязке**: `link_1c_customer.py` и `TRANSFERRED_USER_FIELDS` здесь не трогаются, спека `spec-1c-manager-link-counterparty` правится там, а не здесь.

**Стык 40.3 → 40.4 → 40.5 (знать и не «чинить»).** 40.3 зафиксировала промежуточное состояние: привязка вид цен **не переносит**, сохранённый GUID остаётся на деактивированной записи 1С. Для 40.4 это безвредно и работает так: `link_1c_customer` переносит `onec_id` на аккаунт заявителя, при следующем импорте `_find_duplicate` находит аккаунт по этому `onec_id`, тот **не** проходит `unlinked_1c_record_q()` (B2B-роль, задан пароль) — и роль приезжает из свежих `customer_data`, а не из пустого `onec_price_type_id` цели. Практические следствия:

- Роль после ручной привязки на проде появляется **следующим обменом**, а не мгновенно. Именно так проверяются критерии приёмки #1–#3 до выката 40.5 — «мгновенно при привязке» доделывает 40.5, и подменять её здесь не нужно.
- `tests/integration/test_link_then_import_1c.py` — точная модель этого пути и потому обязателен в регрессе (Task 8.2).
- Не добавлять в 40.4 чтение `user.onec_price_type_id` для разрешения роли: источник истины при импорте — выгрузка, а не сохранённое поле. По сохранённому полю роль разрешает только 40.5 (там другого входа нет).

API-контракт не меняется: `openapi.yaml` и типы фронта не трогаются, `npm run generate:types` не запускается, frontend не затрагивается (NFR-3940-07 к эпику 40 неприменим). Новых зависимостей нет — `requirements.txt` не трогается, версии Django/DRF/pytest не меняются.

### Project Structure Notes

| Файл | Статус | Что |
|---|---|---|
| `backend/apps/users/services/processor.py` | UPDATE | `ROLE_STATS_KEYS`, `SKIP_COUNTER_BY_REASON`, `RoleChange`, `role_map`, `_resolve_role_change`, `_log_role_change`, вставки в `_update_customer` / `process_customer` / `process_customers`, правки docstring и комментариев |
| `backend/apps/users/management/commands/import_customers_from_1c.py` | UPDATE | Ролевые ключи в `total_stats`, блок счётчиков в итоговом выводе |
| `backend/tests/unit/test_services/test_customer_processor.py` | UPDATE | Класс `TestCustomerRoleFromPriceType`, фикстура `customer_with_opt4`, правка комментариев четырёх существующих тестов |
| `backend/tests/integration/test_import_role_from_1c.py` | **NEW** | Прогон на реальной выгрузке: критерий #4, счётчики отчёта, смена роли привязанного аккаунта, регрессия критических путей привязки |
| `backend/tests/integration/test_link_then_import_1c.py` | UPDATE | Уточнение сообщения ассерта (`:104`) |
| `_bmad-output/implementation-artifacts/spec-1c-unregistered-role.md` | UPDATE | Вычёркивание отменённого правила (4 места) + запись Spec Change Log |

Миграций нет: поле `onec_price_type_id` заведено в 40.3, `PriceType.user_role` — в 40.2, новых полей стори не вводит.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story 40.4`] — AC в BDD-форме, FR-40-07, -08, -09, -12
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic 40`] — порядок стори, отложенный эффект `roles_updated = 0`, заметки реализации закрытых стори
- [Source: `_bmad-output/planning-artifacts/epics.md#NonFunctional Requirements`] — NFR-3940-01 (реальные XML), -02 (маркеры), -03 (покрытие ≥ 90 %), -05 (критические пути привязки), -08 (идемпотентность), -09 (один запрос на сессию)
- [Source: `_bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md` §4] — решения 1, 3, 4, 5; §5 — правило «роль только живым аккаунтам»; §8 C4 — состав изменений импорта; §9 «Часть C» — таблица тестов; §10 — критерии приёмки #1–#7
- [Source: `_bmad-output/implementation-artifacts/Story/40-3-store-onec-price-type-id.md`] — `_price_type_id_to_store`, фикстуры реального снимка, тестовая БД с миграциями, состав снимка
- [Source: `_bmad-output/implementation-artifacts/Story/40-2-price-type-role-mapping-and-resolver.md`] — контракт резолвера, различие `no_agreement` / `no_data`, запрет `lru_cache`
- [Source: `_bmad-output/implementation-artifacts/spec-1c-unregistered-role.md`] — отменяемое правило и его четыре повтора, история бага, чинившегося миграцией `0018`
- [Source: `project-context.md` §3, §4, §6] — доменные инварианты 1С, реальные XML в тестах, покрытие, русские комментарии
- [Source: `backend/docs/testing-standards.md`] — стандарты тестирования, маркеры pytest

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, bmad-dev-story)

### Debug Log References

- `black` + `flake8` по изменённым файлам — чисто (`flake8 apps/users/ tests/...` без замечаний).
- `manage.py makemigrations --check --dry-run` → `No changes detected` (AC18: модели не тронуты).
- Новый unit-класс `TestCustomerRoleFromPriceType` — 16 тестов, зелёные.
- Новый интеграционный файл `tests/integration/test_import_role_from_1c.py` — 8 тестов, зелёные (79 с).
- Регресс обязательным списком (11 файлов, Task 8.2) — 223 теста, зелёные (626 с).
- Полный прогон `pytest -q` **без** `-m` (Task 8.3): **2981 passed, 6 skipped, 19 subtests passed** за 35 мин — регрессий нет.
- Покрытие затронутых модулей (AC20): `apps/users/services/processor.py` — **97 %**, `apps/users/management/commands/import_customers_from_1c.py` — **99 %** (непокрыта одна строка `else`-ветки внешнего обработчика, достижимая только при `session is None`).
- `git diff HEAD --stat` (Task 8.6): в диффе нет `models.py`, `admin.py`, `serializers.py`, `parser.py`, `price_type_role.py`, `link_1c_customer.py`, `apps/products/**`, `openapi.yaml`, `frontend/**`.
- `npx gitnexus detect-changes --scope all` (Task 8.7): 7 файлов, 22 символа, **affected processes: 0**, **risk: low**; из прикладного кода затронуты только `processor.py` и `import_customers_from_1c.py`.
- Индекс GitNexus на момент разработки помечен `stale` (indexed `6f82bda`, HEAD `7344692`); blast radius взят из pre-flight, зафиксированного в Dev Notes. **Перед мержем стоит выполнить `npx gitnexus analyze`.**

### Completion Notes List

**Реализовано.**

1. **Ролевой контракт в процессоре** (`processor.py`): модульные `ROLE_STATS_KEYS` (9 ключей) и `SKIP_COUNTER_BY_REASON` (словарь причина→счётчик, чтобы шестая причина резолвера падала `KeyError`, а не терялась), `NamedTuple RoleChange`, ленивое свойство `role_map` с кэшем на экземпляре (без `lru_cache` и модульного кэша — AC17), приватный `_resolve_role_change`, который решает и ничего не сохраняет.
2. **Порядок проверок неизменяем**: сначала `matches_q(User.objects.unlinked_1c_record_q(), user)` — предикат в памяти, без запроса, — и только потом резолвер. Непривязанная запись 1С роли не получает никогда (AC1).
3. **Применение и журнал** (`_update_customer`): решение принимается до `user.role = ...`, `AuditLog` пишется строго **после** `user.save()`. `_log_role_change` берёт наименования вида цен и соглашения из `customer_data["price_type_meta"]` — без дополнительных запросов (AC5).
4. **Отступление от «точного кода» Dev Notes (осознанное).** Сопоставление `price_type_meta` с GUID из `resolution.matched` сделано регистронезависимым: резолвер нормализует GUID в нижний регистр, парсер отдаёт как в выгрузке, и строгое `==` молча вернуло бы пустые `price_type_name` / `agreement_name`. Поведение при совпадающем регистре идентично.
5. **Счётчики** (`process_customers`): инициализация до цикла, инкремент по `last_role_outcome` вне `transaction.atomic()`, `roles_updated` вычисляется как сумма двух слагаемых перед `return`. `attributes_block_*` не тронуты.
6. **Отчёт команды**: `ROLE_STATS_KEYS` импортируется из процессора (мина «цикл суммирует только объявленные ключи» закрыта), блок из девяти строк добавлен в итоговый вывод, `roles_updated_from_assigned` — отдельной строкой (AC8). Аргументы команды и `--dry-run` не менялись.
7. **Спека** (`spec-1c-unregistered-role.md`): отменённое правило вычеркнуто во всех четырёх местах (Boundaries → Always, строка I/O-матрицы, Acceptance Criterion, пункт 1 блока KEEP) со ссылкой на новую запись Spec Change Log «2026-08-05 — итерация 3»; правка внутри `<frozen-after-approval>` помечена как санкционированная (AC19).
8. **Комментарии-мины в существующих тестах** приведены в соответствие (5 штук, Task 5.14): каждый теперь объясняет, что роль сохраняется из-за конкретной причины резолвера (`no_data` / `unknown_price_type` / «непривязанная запись»), а не по отменённому правилу.

**Проверено на реальных данных.** Синтетических XML не создавалось. Ветка «два вида цен» собрана вариацией входа сервиса (подмена `price_type_ids` в разобранном снимке) — в снимке контрагентов с двумя различными GUID ноль по построению. Фикстура `customer_with_opt4` подменяет GUID на «Опт 4» (единственный, засеянный миграцией `products/0053` с непустым `user_role`) вместо поиска в снимке — состав видов цен внутри файла не зафиксирован, и поиск дал бы недетерминированный `skip`.

**Отложенный эффект подтверждён тестом.** `test_first_run_reports_no_role_activity` и `test_second_run_reports_unlinked_records` фиксируют норму прода: `roles_updated = 0`, а объяснение нуля даёт `roles_skipped_unlinked_record > 0`.

**Дополнение сверх списка File List стори (обоснование).** В `tests/integration/test_management_commands/test_import_customers.py` добавлены 4 теста на пути ошибок команды. Причина: AC20 требует ≥ 90 % на затронутых модулях, а модуль команды давал 80 % — недоставали ветки `CommandError` (нет подкаталога `contragents/`, нет файлов), пофайловый обработчик сбоя и внешний обработчик критической ошибки. Все четыре — пути, существовавшие до стори и не покрытые ранее; продуктовый код команды в них не менялся. После добавления — 99 %.

### File List

- `backend/apps/users/services/processor.py` — UPDATE
- `backend/apps/users/management/commands/import_customers_from_1c.py` — UPDATE
- `backend/tests/unit/test_services/test_customer_processor.py` — UPDATE
- `backend/tests/integration/test_import_role_from_1c.py` — NEW
- `backend/tests/integration/test_link_then_import_1c.py` — UPDATE
- `backend/tests/integration/test_management_commands/test_import_customers.py` — UPDATE (4 теста на пути ошибок команды ради порога покрытия AC20)
- `_bmad-output/implementation-artifacts/spec-1c-unregistered-role.md` — UPDATE
- `_bmad-output/implementation-artifacts/Story/40-4-import-applies-role-to-linked-accounts.md` — UPDATE
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — UPDATE

## Change Log

| Дата | Версия | Описание | Автор |
|---|---|---|---|
| 2026-08-05 | 0.1 | Создана стори 40.4 (импорт применяет роль привязанным аккаунтам), статус ready-for-dev | claude-opus-5 |
| 2026-08-05 | 1.0 | Реализация: применение роли из вида цен 1С привязанным аккаунтам, `AuditLog(action="role_from_1c")`, девять ролевых счётчиков в отчёте сессии и выводе команды, отмена правила «импорт не меняет роль» в спеке. 28 новых тестов (16 unit + 8 integration + 4 на пути ошибок команды), полный прогон 2981 passed, покрытие 97 % / 99 %. Статус → review | claude-opus-5 |
