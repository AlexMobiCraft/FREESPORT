---
baseline_commit: c880773b
---

# Story 40.5: Привязка заявки переносит вид цен и сразу выдаёт роль

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> ✅ **Внешних блокеров нет.** Всё, на чём стоит стори, готово: `User.onec_price_type_id` (40.3), `resolve_role_from_price_types` (40.2), снимок `backend/data/import_1c/contragents_pricetype/`, применение роли импортом (40.4). Координаты кода проверены на коммите `c880773`.
> ⚠️ **Работать в основном клоне `C:\Users\1\DEV\FREESPORT`, не в worktree.** Каталог `backend/data/import_1c/` в `.gitignore`; в worktree `data_dependent`-тесты молча скипаются, индекс GitNexus отсутствует.
> 🔴 **Последняя стори эпика 40.** После неё роль приезжает из 1С обоими путями: импортом (40.4, следующим обменом) и привязкой (40.5, мгновенно). Стори закрывает разрыв «менеджер привязал — клиент до утра видит чужие цены».
> 🟢 **Blast radius LOW.** `npx gitnexus impact link_1c_customer --direction upstream` → `risk: LOW`, impacted 2, единственный вызывающий — admin-действие. Подробности в Dev Notes → «Blast radius».

## Story

As a **Менеджер**,
I want **чтобы при связывании заявки с контрагентом 1С аккаунт сразу получал уровень цен из соглашения**,
so that **клиент видел свои цены с первого входа, а не ждал следующего обмена или моего ручного назначения роли**.

## Acceptance Criteria

1. **AC1 (FR-40-11, NFR-3940-04).** `link_1c_customer` (`link_1c_customer.py:99`) переносит `onec_price_type_id` источника на цель **внутри уже существующей** `transaction.atomic()` (`:135`) с `select_for_update()` (`:139`). Значение записывается тем же `target.save(update_fields=target_fields)` (`:222`), что и остальные переносимые поля: отдельная транзакция, отдельный `save()` и любая запись вне блока `with` запрещены.

2. **AC2 (FR-40-11).** Пустой `onec_price_type_id` источника цель не затирает — правило файла «пустые значения источника не переносятся» (`_transfer_company`, `:267`) распространяется и на это поле. Перенос выполняется только когда значение источника непусто и отличается от значения цели.

3. **AC3 (FR-40-11).** Роль разрешается вызовом `resolve_role_from_price_types([<onec_price_type_id источника>])` (`price_type_role.py:71`) в той же транзакции. Источник GUID — **запись 1С**, а не цель: у цели поле пусто по построению (импорт его не писал, привязки не было). `agreement_status` не передаётся — на портале он не хранится, у функции есть значение по умолчанию.

4. **AC4 (FR-40-11).** При `reason="resolved"` роль цели заменяется разрешённой в той же транзакции. Роль **не переносится** с источника: у записи 1С она всегда `unregistered` (§5 задания) — она **выводится** из вида цен.

5. **AC5 (FR-40-11).** Если `resolution.role is None` — роль цели не изменяется, а сама привязка выполняется штатно и успешно: отсутствие вида цен не является отказом привязки. Решение принимается по `resolution.role is None`, а **не** перечислением значений `reason`: перечисление сломается молча при добавлении шестой причины в резолвер.

6. **AC6 (FR-40-11).** Разрешённая роль, не входящая в `User.B2B_ROLES` (`models.py:178`), **не применяется**, привязка при этом выполняется. Сценарий реален: `PriceTypeAdminForm` (`products/forms.py:42`) предлагает менеджеру весь `User.ROLE_CHOICES`, включая `retail`, `admin` и `unregistered`. Применение такой роли выбило бы аккаунт из `link_target_q()` (`link_1c_customer.py:45`), `is_b2b_user` и всех последующих B2B-сценариев.

7. **AC7 (FR-40-11).** `AuditLog` привязки (`action="link_1c_customer"`, `:228`): `role` попадает в `changes["transferred_fields"]` **только когда роль фактически изменилась** — список отражает реальные изменения, как и для `company_name` / `tax_id` / `customer_code`. При неизменной роли `role` в списке отсутствует.

8. **AC8 (FR-40-11).** `changes["previous_values"]` содержит прежнюю роль цели под ключом `role`. Ключ пишется **безусловно** — по образцу `company_name`, `tax_id`, `customer_code` (`:180-184`), которые фиксируются независимо от факта изменения: привязка необратима, и разбор ошибочного случая строится на «что было».

9. **AC9 (FR-40-11, следствие AC1).** Фактический перенос `onec_price_type_id` тоже попадает в `transferred_fields`, а прежнее значение — в `previous_values`. Основание: без этого журнал утверждал бы, что вид цен не переносился, тогда как роль в том же событии сменилась именно из-за него — событие стало бы необъяснимым при разборе.

10. **AC10 (FR-40-11).** Комментарий к `TRANSFERRED_USER_FIELDS` (`link_1c_customer.py:24-27`), объявляющий `role` намеренно непереносимой, приведён в соответствие с новым поведением. В кортеж добавляется `onec_price_type_id` (он действительно переносится); `role` в кортеж **не** добавляется — она не переносится, а выводится из вида цен. ⚠️ Константа нигде в коде не используется (проверено поиском по репозиторию): она документирует поведение, а не управляет им — правка кортежа поведения не меняет, и опираться на неё в реализации нельзя.

11. **AC11 (NFR-3940-04).** Ошибка на любом шаге после переноса вида цен откатывает транзакцию целиком: ни `onec_price_type_id`, ни роль цели не остаются изменёнными, источник остаётся с идентификаторами и `is_active=True`. Частичного состояния не возникает.

12. **AC12 (спека).** В `spec-1c-manager-link-counterparty.md` зафиксирована отмена правила «`role` не переносится при привязке»:
    - раздел **Spec Change Log** в спеке **отсутствует** — создать его (образец формата — `spec-1c-unregistered-role.md:105-133`, четыре подзаголовка: что отменено / чем заменено / что осталось в силе / известно-плохое состояние);
    - в теле спеки отменённый текст **вычеркнут** (`~~…~~`) со ссылкой на запись Change Log — тело документа читают, а changelog нет. Места перечислены в Dev Notes → «Правка спеки»;
    - правка затрагивает блок `<frozen-after-approval>`; она санкционирована AC стори 40.5 в `epics.md` (решение Alex) и является тем renegotiation, которого требует атрибут `reason`. Указать это явно в записи Change Log; остальное содержимое frozen-блока не трогать.

13. **AC13 (план выката).** Шаг ручной привязки тестового аккаунта к контрагенту с известным видом цен внесён в `action_items` эпика 40 в `sprint-status.yaml` (`owner: "Alex"`, `status: open`). Без него критерии приёмки #1–#3 задания непроверяемы: живых привязанных клиентских аккаунтов на проде нет, применять роль не к чему.

14. **AC14 (границы стори).** Не изменяются: `apps/users/services/processor.py`, `apps/users/services/parser.py`, `apps/users/services/price_type_role.py`, `apps/users/models.py`, `apps/users/admin.py`, `apps/users/serializers.py`, `apps/products/**`, `apps/orders/**`, `docs/api/openapi.yaml`, `frontend/**`. Миграций в стори нет. Шаблон `templates/admin/users/link_1c_customer.html` не трогается — страница подтверждения новых полей не показывает.

15. **AC15 (NFR-3940-01, -02, -03).** Покрыты: перенос вида цен, применение роли в одной транзакции, отказы в применении, состав `AuditLog`, откат при ошибке. Unit-тесты строят `User` напрямую (это не тесты импорта — синтетический XML в них не участвует вовсе); интеграционный тест использует **реальный** снимок `backend/data/import_1c/contragents_pricetype/`. Маркеры проставляются автоматически по каталогу, `@pytest.mark.data_dependent` — вручную. Покрытие `apps/users/services/link_1c_customer.py` ≥ 90 %.

## Tasks / Subtasks

- [x] **Task 1: Перенос вида цен и разрешение роли в сервисе** (AC: 1–6)
  - [x] 1.1: Добавить импорт в `link_1c_customer.py` (после `from apps.users.models import ...`, `:20`): `from apps.users.services.price_type_role import resolve_role_from_price_types`. Импорт на уровне модуля, не локальный: `price_type_role` тянет `apps.products.models`, цикла нет — проверено в 40.3 и подтверждено 40.4
  - [x] 1.2: Обновить комментарий и кортеж `TRANSFERRED_USER_FIELDS` (`:24-27`) — точный текст в Dev Notes → «Точный код: константа». AC10
  - [x] 1.3: В `previous` (`:180-184`) добавить ключи `"role": target.role` и `"onec_price_type_id": target.onec_price_type_id` — безусловно, как три существующих ключа (AC8, AC9)
  - [x] 1.4: После блока переноса `tax_id` (`:214-217`), **до** `target.save(...)` (`:222`), вставить перенос вида цен и применение роли — точный код в Dev Notes. Порядок обязателен: и `onec_price_type_id`, и `role` обязаны попасть в `target_fields` до единственного `save()`
  - [x] 1.5: Роль разрешать **по значению источника** (`source.onec_price_type_id`), а не по уже присвоенному значению цели: читаемость выше, а при пустом источнике (AC2) значения расходятся
  - [x] 1.6: Гейт `resolution.role in User.B2B_ROLES` — обязателен (AC6). `User` уже импортирован (`:20`)
  - [x] 1.7: Дополнить `logger.info` (`:250-255`) сведением о новой роли — менеджер разбирает привязки по логу, а смена роли теперь её часть. Формат — в Dev Notes
  - [x] 1.8: Обновить docstring `link_1c_customer` (`:108-131`): переносится вид цен, роль выводится из него. Раздел `Raises` не меняется — новых исключений стори не вводит

- [x] **Task 2: Правка спеки** (AC: 12)
  - [x] 2.1: Вычеркнуть отменённое правило в `spec-1c-manager-link-counterparty.md` в двух местах — точные строки в Dev Notes → «Правка спеки»
  - [x] 2.2: Создать раздел `## Spec Change Log` (в спеке его нет) — разместить после `## Design Notes`/перед `## Review Findings` по образцу `spec-1c-unregistered-role.md`; запись датой реализации со ссылкой на стори 40.5 и FR-40-11
  - [x] 2.3: В записи явно указать, что правка внутри `<frozen-after-approval>` санкционирована AC стори в `epics.md`

- [x] **Task 3: План выката** (AC: 13)
  - [x] 3.1: Добавить пункт в секцию `action_items` `sprint-status.yaml` (`epic: 40`, `owner: "Alex"`, `status: open`) — текст в Dev Notes. Существующие пункты не править

- [x] **Task 4: Unit-тесты сервиса** (AC: 1–11, 15)
  - [x] 4.1: Новый класс `TestLinkAppliesPriceTypeAndRole` в `backend/tests/unit/test_services/test_link_1c_customer.py`. Переиспользовать существующие хелперы файла: `make_1c_record`, `make_applicant`, `unique_tax_id`, `unique_suffix` (`:32-74`) — новых не заводить. `pytestmark` уже объявлен на уровне модуля (`:27`), в классе не дублировать
  - [x] 4.2: Записи `PriceType` заводить **только** через `get_or_create` — GUID «Опт 4» (`4c1962d2-f8ed-11eb-81f3-00155d3cae02`, `user_role="wholesale_level4"`) уже засеян миграцией `products/0053`, а тестовая БД строится **с** миграциями. `create` даст `duplicate key`
  - [x] 4.3: Тест AC1/AC4: источник с `onec_price_type_id` = GUID «Опт 4», цель с ролью `wholesale_level1` → после привязки `linked.onec_price_type_id` равен GUID источника, `linked.role == "wholesale_level4"`; после `refresh_from_db()` то же самое (доказывает, что значения попали в `update_fields`, а не остались в памяти)
  - [x] 4.4: Тест AC2: источник с пустым `onec_price_type_id` → поле цели остаётся пустым, роль не меняется, привязка успешна
  - [x] 4.5: Тест AC5 (`unknown_price_type`, GUID неизвестен справочнику): источник с произвольным GUID, отсутствующим в `PriceType` → роль цели не изменилась, `onec_price_type_id` **перенесён** (перенос и применение роли независимы), привязка успешна
  - [x] 4.6: Тест AC5 (`unknown_price_type`, GUID известен, роль пуста): `get_or_create` записи с `user_role=""` (образец — РРЦ `3d1482c4-bd77-11e4-afc8-20cf3073dde3`) → роль не изменилась, поле перенесено
  - [x] 4.7: Тест AC6: `get_or_create` записи `PriceType` с `user_role="retail"` → роль цели **не** изменилась (осталась B2B), поле перенесено, привязка успешна
  - [x] 4.8: Тест AC7/AC8: успешная смена роли → в `changes["transferred_fields"]` есть `"role"` и `"onec_price_type_id"`, в `changes["previous_values"]["role"]` — прежняя роль цели
  - [x] 4.9: Тест AC7 (обратная сторона): роль цели уже совпадает с разрешённой → `"role"` в `transferred_fields` **отсутствует**, `previous_values["role"]` при этом заполнен
  - [x] 4.10: Тест AC11: `patch` на `AuditLog.log_action` с `side_effect=RuntimeError` (образец — `test_failure_mid_transfer_rolls_back_both_rows`, `:467`) → после `refresh_from_db()` у цели прежняя роль и пустой `onec_price_type_id`, у источника идентификаторы на месте и `is_active is True`
  - [x] 4.11: ⚠️ **Проверить существующий `test_does_not_touch_identity_fields_of_target`** (`:349`): он утверждает неизменность `role`. Тест остаётся зелёным (у `make_1c_record` поле `onec_price_type_id` пусто → `no_data`), но его смысл изменился — дописать в него комментарий, объясняющий, что роль сохраняется **из-за отсутствия вида цен у источника**, а не по отменённому правилу. Утверждения про `email`, `password`, `verification_status`, `is_active` остаются в силе и не ослабляются

- [x] **Task 5: Интеграционный тест на реальной выгрузке** (AC: 4, 7, 15)
  - [x] 5.1: Новый файл `backend/tests/integration/test_link_applies_role_from_1c.py`; маркеры: `integration` автоматически по каталогу, добавить `@pytest.mark.data_dependent` и `@pytest.mark.django_db`
  - [x] 5.2: Переиспользовать помощники выбора файла снимка `_snapshot_files` / `_pick_representative_file` и фикстуру `snapshot_data_dir` из `tests/integration/test_import_customers_price_type.py:31-85` (скопировать в новый файл либо импортировать — общего conftest для них нет). Фикстура каталога снимка — `onec_data_dir` (`tests/conftest.py:419`)
  - [x] 5.3: Сценарий: (1) прогнать импорт снимка (`call_command("import_customers_from_1c", ...)`) либо разобрать файл и импортировать одного контрагента через `CustomerDataProcessor.process_customer` — второй путь дешевле; (2) взять импортированную запись с непустым `onec_price_type_id`; (3) `PriceType.objects.get_or_create(onec_id=<её GUID>, defaults={... "user_role": "wholesale_level2" ...})`; (4) завести B2B-заявку с тем же ИНН; (5) `link_1c_customer(...)`; (6) роль цели равна `user_role` **созданной записи справочника** (брать из объекта, не из литерала), `onec_price_type_id` перенесён, есть `AuditLog(action="link_1c_customer")` с `role` в `transferred_fields`
  - [x] 5.4: ⚠️ Не зашивать конкретный GUID и не предполагать, что в выбранном файле есть «Опт 4»: состав видов цен внутри файла не зафиксирован (замер 40.3), поиск по литералу дал бы недетерминированный `skip`
  - [x] 5.5: ⚠️ Мина объёма: копировать в tmp-каталог **один** файл снимка, не все 10 (4735 `User` + столько же `CustomerSyncLog` — десятки минут)
  - [x] 5.6: Ключевое утверждение стори: роль применяется **сразу при привязке**, без повторного прогона импорта. Зафиксировать это в docstring теста — до 40.5 тот же результат достигался только следующим обменом (`test_link_then_import_1c.py`)

- [x] **Task 6: Прогон, регресс, линтеры** (AC: 14, 15)
  - [x] 6.1: Прогон новых тестов в тест-контейнере (команды — в Dev Notes → «Тестирование: как запускать»)
  - [x] 6.2: Регресс обязательным списком: `tests/unit/test_services/test_link_1c_customer.py`, `tests/unit/test_models/test_unlinked_1c_predicate.py`, `tests/unit/test_services/test_price_type_role.py`, `tests/unit/test_services/test_customer_processor.py`, `tests/integration/test_admin_link_1c_customer.py`, `tests/integration/test_link_then_import_1c.py`, `tests/integration/test_import_role_from_1c.py`, `tests/integration/test_import_customers_price_type.py`, `tests/integration/test_portal_registration_1c_link.py`
  - [x] 6.3: Полный прогон `pytest -q` **без** `-m`: маркер-фильтры CI оставляют 852 теста вне гейтов, регрессия ловится только полным набором
  - [x] 6.4: `manage.py makemigrations --check --dry-run` → `No changes detected` (доказывает, что модели не тронуты, AC14)
  - [x] 6.5: `black` + `flake8` на изменённых файлах
  - [x] 6.6: `git diff HEAD --stat` — убедиться, что в диффе нет `processor.py`, `parser.py`, `price_type_role.py`, `models.py`, `admin.py`, `serializers.py`, `apps/products/**`, `apps/orders/**`, `openapi.yaml`, `frontend/**` (AC14)
  - [x] 6.7: `npx gitnexus detect-changes --scope all` из основного клона. Ожидаемые символы: `link_1c_customer` (сервис). Затронутый процесс — admin-действие `link_1c_customer`, что и предсказал pre-flight

## Dev Notes

### Что уже есть и переиспользуется (не изобретать)

| Нужное | Где уже есть |
|---|---|
| Разрешение роли по GUID и все пять `reason` | `resolve_role_from_price_types(price_type_ids, agreement_status="", *, role_map=None) -> RoleResolution(role, reason, matched)` (`apps/users/services/price_type_role.py:71`) |
| Транзакция, блокировки, повторные проверки | Уже внутри `link_1c_customer` (`link_1c_customer.py:135-176`) — новый код встраивается в неё, своей не заводит |
| Список B2B-ролей | `User.B2B_ROLES` (`apps/users/models.py:178`). Третьей копии списка быть не должно |
| Поле хранения GUID | `User.onec_price_type_id` — `CharField(max_length=100, blank=True, default="")` (`models.py:287`). Миграция заведена в 40.3 |
| Наименование вида цен для админки | `UserAdmin.onec_price_type_name` (`admin.py:397`) — readonly, уже выводится в карточке; в этой стори не трогается |
| Запись в аудит | `AuditLog.log_action(...)` уже вызывается в конце транзакции (`link_1c_customer.py:228`) — новых вызовов не добавлять, дополняется `changes` существующего |
| Хелперы unit-тестов | `make_1c_record`, `make_applicant`, `unique_tax_id`, `unique_suffix` (`tests/unit/test_services/test_link_1c_customer.py:32-74`) |
| Образец теста отката | `test_failure_mid_transfer_rolls_back_both_rows` (`test_link_1c_customer.py:467`) |
| Выбор файла реального снимка по содержимому | `_snapshot_files` / `_pick_representative_file` / `snapshot_data_dir` (`tests/integration/test_import_customers_price_type.py:31-85`) |

### Точный код: константа

`link_1c_customer.py:24-27` заменяется на:

```python
# Поля User, переносимые с контрагента 1С на аккаунт заявителя.
# email, password, verification_status и is_active не переносятся намеренно:
# email — логин заявителя. role не переносится тоже, но по другой причине:
# у записи 1С она всегда unregistered, а роль аккаунта ВЫВОДИТСЯ из
# перенесённого вида цен через resolve_role_from_price_types (FR-40-11).
# Кортеж документирует поведение и переносом не управляет — фактический
# список полей собирается ниже по факту изменения значений.
TRANSFERRED_USER_FIELDS = ("onec_id", "onec_guid", "company_name", "tax_id", "onec_price_type_id")
```

### Точный код: перенос и применение роли

`link_1c_customer.py`, между блоком `tax_id` (`:214-217`) и `target.save(...)` (`:222`):

```python
        # Вид цен переносится по тому же правилу, что и прочие реквизиты:
        # пустое значение источника ничего не затирает (привязка необратима).
        if source.onec_price_type_id and source.onec_price_type_id != target.onec_price_type_id:
            target.onec_price_type_id = source.onec_price_type_id
            target_fields.append("onec_price_type_id")
            transferred.append("onec_price_type_id")

        # Роль не переносится, а выводится: у записи 1С она всегда
        # unregistered (§5 задания). Источник GUID — именно source: при
        # пустом значении источника поле цели не менялось (правило выше).
        # Статус соглашения на портале не хранится — параметр не передаётся.
        resolution = resolve_role_from_price_types([source.onec_price_type_id or ""])
        # Проверять role is None, а не reason: перечисление причин сломалось
        # бы молча, если резолвер заведёт шестую.
        if resolution.role is not None and resolution.role != target.role:
            # Вид цен, дающий не-B2B роль, применять нельзя: PriceTypeAdminForm
            # предлагает менеджеру весь ROLE_CHOICES, а retail/admin выбили бы
            # аккаунт из link_target_q(), is_b2b_user и B2B-сценариев целиком.
            if resolution.role in User.B2B_ROLES:
                target.role = resolution.role
                target_fields.append("role")
                transferred.append("role")
```

`previous` (`:180-184`) дополняется двумя ключами:

```python
        previous: dict[str, str | None] = {
            "company_name": target.company_name,
            "tax_id": target.tax_id,
            "customer_code": target.customer_code,
            # Прежняя роль и вид цен пишутся безусловно — как три ключа выше:
            # привязка необратима, и разбор ошибочного случая строится на «что было».
            "role": target.role,
            "onec_price_type_id": target.onec_price_type_id,
        }
```

⚠️ `previous` заполняется **до** присвоений (`:180` идёт раньше `:207`) — переносить его ниже нельзя, иначе «прежнее» станет равным новому.

`logger.info` (`:250-255`) — дополнить последним аргументом:

```python
    logger.info(
        "Заявка %s связана с контрагентом 1С %s (onec_id=%s), исходная запись деактивирована, роль=%s",
        target.pk,
        source.pk,
        onec_id,
        target.role,
    )
```

### Какие ветки резолвера здесь достижимы (важно для тестов)

Резолвер знает пять исходов, но через эту точку входа достижимы **три**:

| `reason` | Достижим при привязке | Почему |
|---|---|---|
| `resolved` | да | GUID источника есть в `PriceType` с непустым `user_role` |
| `no_data` | да | у источника `onec_price_type_id == ""` (нет соглашения, либо старый снимок без блока) |
| `unknown_price_type` | да | GUID неизвестен справочнику **либо** известен, но `user_role` пуст (РРЦ, МРЦ) |
| `no_agreement` | **нет** | требует аргумент `agreement_status`; портал его не хранит и не передаёт |
| `ambiguous` | **нет** | требует ≥ 2 различных GUID; `User.onec_price_type_id` однозначен по построению — 40.3 гасит его при `НетСоглашения` и не пишет при двух и более GUID |

Отсюда два следствия для реализации: (1) тесты на `no_agreement` и `ambiguous` **не сочинять** — они потребовали бы мока резолвера и проверяли бы мок, а не поведение; (2) код обязан всё равно обрабатывать их обобщённо, через `resolution.role is None`, — именно поэтому AC5 запрещает перечисление причин. Инвариант однозначности поля описан в `epics.md#Epic 40` → «Заметки реализации», и на нём стоит вся конструкция.

### Почему роль не переносится, а выводится

Соблазн добавить `role` в перенос по образцу `company_name` силён и ошибочен: у записи 1С роль всегда `unregistered` (§5 задания, `IMPORTED_CUSTOMER_ROLE`), и перенос выдал бы заявителю нерабочий аккаунт — `unregistered` не B2B-роль, цены розничные, `approve_b2b_users` такую заявку не видит. Переносится **вид цен**, роль из него выводится справочником.

### Стык 40.4 → 40.5 (знать и не «чинить»)

До этой стори роль после ручной привязки появлялась **следующим обменом**: `link_1c_customer` переносил `onec_id`, импорт находил аккаунт по нему, аккаунт не проходил `unlinked_1c_record_q()` (B2B-роль, задан пароль) — и роль приезжала из свежих `customer_data` (40.4). Этот путь остаётся рабочим и после 40.5; стори закрывает разрыв между привязкой и ближайшим обменом, а не заменяет его.

Практические следствия:

- `tests/integration/test_link_then_import_1c.py` продолжает проверять путь «привязка → импорт» и обязателен в регрессе. Его ассерт `applicant.role == applicant_role` (`:108`) остаётся зелёным: старый снимок `contragents/` блока `<ЗначенияРеквизитов>` не содержит, у импортированной записи `onec_price_type_id` пуст → при привязке `no_data`, при импорте `no_data`. Комментарий `:104-107` уже это объясняет — трогать его не нужно.
- Источник GUID при привязке — сохранённое поле записи 1С (другого входа нет), при импорте — свежая выгрузка. Это осознанная асимметрия: не «чинить» её чтением `user.onec_price_type_id` в импорте.
- `onec_price_type_id` у источника **не гасится**: запись деактивируется и остаётся аудиторским следом, как `company_name` и `tax_id`, которые тоже остаются. Уникальности у поля нет — constraint переносу не мешает.

### Мины в существующих тестах

Ни один существующий тест не должен покраснеть. Проверить обязательно:

| Тест | Почему остаётся зелёным | Что сделать |
|---|---|---|
| `test_does_not_touch_identity_fields_of_target` (`test_link_1c_customer.py:349`) | `make_1c_record` не задаёт `onec_price_type_id` → `""` → `no_data` → роль не меняется | Дописать комментарий: роль сохраняется из-за отсутствия вида цен у источника, а не по отменённому правилу (Task 4.11) |
| `test_transfers_identifiers_and_requisites` (`:131`), `test_audit_log_records_previous_values_and_real_changes` (`:262`) | Ассерты проверяют вхождение отдельных ключей (`in`), а не равенство списка целиком | Не трогать. ⚠️ Если решишь усилить их до сравнения списков — не делай: `transferred_fields` теперь длиннее |
| `test_link_then_reimport_updates_applicant_without_duplicate` (`tests/integration/test_link_then_import_1c.py:104`) | Старый снимок без блока реквизитов → `no_data` на обоих путях | Не трогать — комментарий уже корректен |
| `tests/integration/test_admin_link_1c_customer.py` (весь файл) | Фикстуры не задают `onec_price_type_id` | Не трогать; держать в регрессе — это HTTP-слой того же пути |

### Правка спеки

`_bmad-output/implementation-artifacts/spec-1c-manager-link-counterparty.md` — вычеркнуть (`~~…~~`) в двух местах:

| Строка | Текст | Комментарий |
|---|---|---|
| `:50` (Never) | «Не переносить и не изменять у заявителя `email`, `password`, **`role`**, `verification_status`, `is_active`: email — его логин, роль — выданный менеджером уровень цен.» | Вычёркивается **только часть про `role`**. Запрет на `email`, `password`, `verification_status`, `is_active` остаётся в полной силе и переформулируется без `role` |
| `:74` (I/O-матрица, «Импорт после привязки») | «…новая запись не создаётся, `role` и `email` сохраняются» | Часть про `role` отменена стори **40.4** (импорт применяет роль привязанному аккаунту). Строка осталась несогласованной после 40.4 — привести в порядок здесь, отдельной ссылкой на 40.4 в записи Change Log |

Обе строки внутри `<frozen-after-approval>`. Раздела `## Spec Change Log` в спеке **нет** — создать. Формат записи (образец — `spec-1c-unregistered-role.md:125-133`):

```markdown
## Spec Change Log

### 2026-08-05 — итерация 2: роль аккаунта выводится из вида цен при привязке (стори 40.5)

**Что отменено.** …
**Чем заменено.** …
**Что осталось в силе.** …
**Известно-плохое состояние, которого это избегает.** …
```

Что остаётся в силе и **не** вычёркивается: `role` по-прежнему не **переносится** с записи 1С (у неё всегда `unregistered`); отменено лишь утверждение, что роль цели при привязке не изменяется.

### План выката: текст пункта для `sprint-status.yaml`

В секцию `action_items`, рядом с существующими пунктами эпиков:

```yaml
  - epic: 40
    action: "Выкат: вручную привязать тестовый аккаунт к контрагенту 1С с известным видом цен — без этого критерии приёмки #1-#3 задания непроверяемы (живых привязанных клиентских аккаунтов на проде нет)"
    owner: "Alex"
    status: open
```

### Blast radius (обязательный pre-flight выполнен)

```
npx gitnexus impact link_1c_customer --direction upstream   → risk: LOW, impacted: 2
  (uid Function:backend/apps/users/services/link_1c_customer.py:link_1c_customer)
```

Единственный вызывающий — `UserAdmin._apply_link_1c_customer` (`admin.py:636`), а через него admin-действие `UserAdmin.link_1c_customer` (`admin.py:577`). Затронутых модулей — 1 (Users), процессов — 1 (то самое admin-действие). Второй документированный потребитель — ручной разбор из shell (спека, Design Notes); сигнатура сервиса не меняется, поэтому он не затрагивается.

Изменение аддитивное: новых полей моделей нет, миграций нет, ни одна сигнатура не меняется, исключений не добавляется. Расширяется содержимое `changes` в `AuditLog` — потребителей у конкретных ключей нет (`AuditLog.changes` читается как JSON в админке).

⚠️ **`unlinked_1c_record_q` (`risk: CRITICAL`, 12 impacted, 5 процессов) стори не изменяет** — сервис только **читает** его через `matches_q` при проверке источника (`link_1c_customer.py:161`). Это единственный безопасный режим работы с ним; трогать предикат в этой стори нельзя ни при каких обстоятельствах.

### Тестирование: как запускать

`make` на машине недоступен, а таргеты `test-*` ищут несуществующий `docker/.env`. Рабочий эквивалент из основного клона:

```bash
cd /c/Users/1/DEV/FREESPORT/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -q tests/unit/test_services/test_link_1c_customer.py \
            tests/integration/test_link_applies_role_from_1c.py
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down
```

Линтеры:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  black apps/users/services/link_1c_customer.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend flake8 apps/users/
```

Особенности тестовой среды, проверенные в 40.2–40.4:

- **Тестовая БД строится С миграциями** (в `backend/pytest.ini` нет `--nomigrations`, вопреки `backend/CLAUDE.md`). Запись «Опт 4» (`4c1962d2-f8ed-11eb-81f3-00155d3cae02`, `user_role="wholesale_level4"`) уже засеяна миграцией `products/0053` — только `get_or_create`. Остальные GUID снимка справочнику неизвестны и годятся для ветки `unknown_price_type`.
- Маркеры `unit` / `integration` проставляются автоматически по каталогу (`backend/conftest.py`); `@pytest.mark.data_dependent` — вручную.
- `container_name` в `docker-compose.test.yml` зашит жёстко — параллельно поднятый тест-стек даст конфликт имён.
- `pytest-timeout` не установлен, `--timeout=` не работает.

### Реальные данные: что лежит в снимке

`backend/data/import_1c/contragents_pricetype/` — 10 файлов, 4735 контрагентов: с блоком реквизитов — все, с непустым `ТипЦенId` — 485, со статусом `НетСоглашения` — 4250, с более чем одним различным GUID — **0**.

| GUID | Наименование | Контрагентов | Есть в `PriceType` тестовой БД |
|---|---|---|---|
| `c05f0e2b-b3f2-11ea-81c3-00155d3cae02` | Опт 3 (50-150 тыс.руб в квартал) | 176 | нет |
| `4c1962d2-f8ed-11eb-81f3-00155d3cae02` | Опт 4 (до 50 тыс.руб в квартал) | 123 | **да**, `user_role="wholesale_level4"` |
| `a91bdb02-b3f2-11ea-81c3-00155d3cae02` | Опт 2 (150-300 тыс.руб в квартал) | 78 | нет |
| `90d2c899-b3f2-11ea-81c3-00155d3cae02` | Опт 1 (300-600 тыс.руб в квартал) | 64 | нет |
| `3d1482c4-bd77-11e4-afc8-20cf3073dde3` | РРЦ | 42 | нет (на проде — с пустым `user_role`) |
| `28049309-b6be-11ec-a301-04421a23d8e8` | Детский мир Залоговая | 2 | нет |

Состав видов цен внутри конкретного файла снимка **не зафиксирован** — тесты не должны предполагать наличие конкретного GUID в выбранном файле. `backend/data/import_1c/contragents/` — старый снимок от 11.04.2026 **без** блока реквизитов: готовые данные для ветки `no_data`.

### Границы стори (что сделали соседние — здесь НЕ делать)

- **40.1** (done) — парсер (`price_type_ids`, `price_type_meta`, `agreement_status`), детектор регресса выгрузки. `parser.py` не трогается.
- **40.2** (done) — `PriceType.user_role`, админка справочника, `resolve_role_from_price_types`, сторож `PRICE_TYPE_BY_ROLE ↔ PriceType.user_role`. `price_type_role.py` не трогается: стори его **вызывает**, а не правит.
- **40.3** (done) — `User.onec_price_type_id`, `_price_type_id_to_store`, отображение вида цен в карточке админки. Ни поле, ни его отображение не переписываются.
- **40.4** (done) — применение роли **импортом**, `AuditLog(action="role_from_1c")`, девять ролевых счётчиков отчёта. `processor.py` не трогается; ролевые счётчики привязки **не заводятся** — привязка выполняется по одной и её результат виден в `AuditLog` и в сообщении админки.

API-контракт не меняется: `openapi.yaml` и типы фронта не трогаются, `npm run generate:types` не запускается, frontend не затрагивается (NFR-3940-07 к эпику 40 неприменим). Новых зависимостей нет — `requirements.txt` не трогается.

### Project Structure Notes

| Файл | Статус | Что |
|---|---|---|
| `backend/apps/users/services/link_1c_customer.py` | UPDATE | Импорт резолвера, правка `TRANSFERRED_USER_FIELDS`, перенос `onec_price_type_id`, применение роли с гейтом `B2B_ROLES`, два ключа в `previous`, `logger.info`, docstring |
| `backend/tests/unit/test_services/test_link_1c_customer.py` | UPDATE | Класс `TestLinkAppliesPriceTypeAndRole`, комментарий в `test_does_not_touch_identity_fields_of_target` |
| `backend/tests/integration/test_link_applies_role_from_1c.py` | **NEW** | Привязка реальной импортированной записи 1С → роль применена сразу, без повторного импорта |
| `_bmad-output/implementation-artifacts/spec-1c-manager-link-counterparty.md` | UPDATE | Вычёркивание отменённого правила (2 места) + новый раздел Spec Change Log |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | UPDATE | Пункт `action_items` про ручную привязку тестового аккаунта на проде + статус стори |

Миграций нет: `onec_price_type_id` заведено в 40.3, `PriceType.user_role` — в 40.2. Новых полей стори не вводит.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story 40.5`] — AC в BDD-форме, FR-40-11
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic 40`] — порядок стори, инвариант однозначности `onec_price_type_id`, отложенный эффект на проде
- [Source: `_bmad-output/planning-artifacts/epics.md#NonFunctional Requirements`] — NFR-3940-01 (реальные XML), -02 (маркеры), -03 (покрытие ≥ 90 %), -04 (атомарность), -05 (критические пути привязки)
- [Source: `_bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md` §8 C5] — состав изменений привязки; §9 — строка таблицы тестов; §10 — критерии приёмки #1–#3
- [Source: `_bmad-output/implementation-artifacts/spec-1c-manager-link-counterparty.md`] — контракт сервиса, правило «пустые значения источника не переносятся», отменяемое правило и его места
- [Source: `_bmad-output/implementation-artifacts/Story/40-4-import-applies-role-to-linked-accounts.md`] — стык 40.4 → 40.5, состав снимка, особенности тестовой среды, образец записи Spec Change Log
- [Source: `_bmad-output/implementation-artifacts/Story/40-2-price-type-role-mapping-and-resolver.md`] — контракт резолвера, различие `no_agreement` / `no_data`, `PriceTypeAdminForm`
- [Source: `project-context.md` §3, §4, §6] — критические операции в `transaction.atomic()` с `select_for_update()`, стандарты тестирования, русские комментарии
- [Source: `backend/docs/testing-standards.md`] — маркеры pytest и автоматическая разметка по каталогу

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, dev-story workflow)

### Debug Log References

Pre-flight (обязательный, CLAUDE.md §GitNexus):

- `npx gitnexus status` → `up-to-date`, indexed commit `c880773` = current.
- `npx gitnexus impact "Function:backend/apps/users/services/link_1c_customer.py:link_1c_customer" --direction upstream` → `risk: LOW`, `impactedCount: 2`, direct 1 (`UserAdmin._apply_link_1c_customer`), depth 2 — admin-действие `UserAdmin.link_1c_customer`. По имени без uid команда отвечает `ambiguous` (сервисная функция и одноимённый метод админки) — нужен uid.
- `npx gitnexus detect-changes --scope all` → 6 файлов, 10 символов, risk medium. Единственный изменённый исполняемый символ — `link_1c_customer`; остальные символы файла (`logger`, `TRANSFERRED_USER_FIELDS`, `TRANSFERRED_COMPANY_FIELDS`, `_transfer_company`, локальные `customer_code`/`changed`) попали в скан из-за сдвига строк, их тела не менялись. `AGENTS.md`/`CLAUDE.md` были изменены до начала стори (см. `git status` на старте) и к ней отношения не имеют. Все 4 затронутых flow — один и тот же admin-путь привязки, что и предсказал pre-flight.

Прогоны (тест-контейнер `freesport-test`, PostgreSQL + Redis):

- Новые unit-тесты + существующие: `tests/unit/test_services/test_link_1c_customer.py` — **40 passed** (было 32, добавлено 8).
- Новый интеграционный: `tests/integration/test_link_applies_role_from_1c.py` — **1 passed** (не skipped: снимок `contragents_pricetype/` на месте, основной клон).
- Регресс обязательным списком из 9 файлов (Task 6.2) — **218 passed**, 3:19.
- Полный прогон `pytest -q` **без** `-m` — **2994 passed, 6 skipped, 19 subtests passed, 0 failed**, 35:46. Регрессий нет.
- `manage.py makemigrations --check --dry-run` → `No changes detected`.
- `black` (3 файла) → `3 files left unchanged`; `flake8 apps/users/` + оба тестовых файла → без замечаний.
- Покрытие `apps/users/services/link_1c_customer.py` — **97 %** (110 stmts, 3 miss: недостижимые в этих трёх файлах ветки `LinkCandidateError` при отсутствующей цели и две ветви `_transfer_company`), порог AC15 ≥ 90 % выполнен.
- `git diff HEAD --stat` — в диффе нет `processor.py`, `parser.py`, `price_type_role.py`, `models.py`, `admin.py`, `serializers.py`, `apps/products/**`, `apps/orders/**`, `openapi.yaml`, `frontend/**` (AC14 подтверждён).

### Completion Notes List

- **Сервис (AC1–AC11).** Перенос `onec_price_type_id` и применение роли встроены в **существующую** `transaction.atomic()` между блоком `customer_code` и единственным `target.save(update_fields=target_fields)`. Своей транзакции, второго `save()` и записи вне блока `with` нет. Роль разрешается по значению **источника** (`source.onec_price_type_id`), `agreement_status` не передаётся. Решение о применении принимается по `resolution.role is None`, не по перечислению `reason` (AC5), плюс гейт `resolution.role in User.B2B_ROLES` (AC6).
- **Журнал (AC7–AC9).** `role` и `onec_price_type_id` попадают в `transferred_fields` только при фактическом изменении; `previous_values` пополнен обоими ключами безусловно — как три существующих. Проверено двумя тестами: смена роли и совпадение роли с разрешённой.
- **Комментарий к `TRANSFERRED_USER_FIELDS` (AC10).** Кортеж дополнен `onec_price_type_id`, `role` в него не добавлена; комментарий переписан. Константа по-прежнему нигде не используется — она документирует поведение, реализация на неё не опирается.
- **Существующие тесты не покраснели.** `test_does_not_touch_identity_fields_of_target` дополнен docstring: роль сохраняется потому, что у `make_1c_record` вид цен пуст (`no_data`), а не по отменённому правилу. Утверждения про `email`, `password`, `verification_status`, `is_active` не ослаблены. `test_transfers_identifiers_and_requisites` и `test_audit_log_records_previous_values_and_real_changes` не трогались (проверяют вхождение ключей, а не равенство списка).
- **Отклонение в Task 5.2 (осознанное).** Из `test_import_customers_price_type.py` скопированы `_snapshot_files` и `_pick_representative_file`; фикстура `snapshot_data_dir` **не** копировалась — она существует только чтобы положить файл в tmp для `call_command`, а тест идёт вторым путём из Task 5.3 (`CustomerDataProcessor.process_customer` на одном разобранном контрагенте). Мина объёма из 5.5 при этом снята полностью: в БД создаётся одна запись, а не 4735. Вместо неё заведена фикстура `customer_with_price_type`, выбирающая покупателя с ИНН и однозначным видом цен; GUID не зашит (5.4), ожидаемая роль читается из созданной записи справочника.
- **Спека (AC12).** Вычеркнуты два места внутри `<frozen-after-approval>` (Never → строка про `email/password/role/...`; строка I/O-матрицы «Импорт после привязки»), обе — со ссылкой на новую запись. Создан раздел `## Spec Change Log` (его в спеке не было) с записью «2026-08-05 — итерация 2» из четырёх подзаголовков; санкция на правку frozen-блока указана явно. Часть про `role` в строке I/O-матрицы была отменена ещё стори 40.4 — это отражено в записи.
- **План выката (AC13).** Пункт добавлен в `action_items` с `epic: 40`, `owner: "Alex"`, `status: open`, текст — из Dev Notes дословно. ⚠️ Он **пересекается по смыслу** с существующим CP-5 (`epic: 39`, «ручная привязка тестового аккаунта к контрагенту с известным видом цен»). Существующие пункты по требованию Task 3.1 не правились; чтобы дубль не выглядел случайным, над новым пунктом оставлен YAML-комментарий со ссылкой на CP-5. Решение о схлопывании двух пунктов в один — за Alex.
- **Границы (AC14).** Миграций нет, сигнатуры не менялись, новых исключений нет, `requirements.txt` не трогался. `templates/admin/users/link_1c_customer.html` не изменялся.

### File List

- `backend/apps/users/services/link_1c_customer.py` — MODIFIED
- `backend/tests/unit/test_services/test_link_1c_customer.py` — MODIFIED
- `backend/tests/integration/test_link_applies_role_from_1c.py` — NEW
- `_bmad-output/implementation-artifacts/spec-1c-manager-link-counterparty.md` — MODIFIED
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED
- `_bmad-output/implementation-artifacts/Story/40-5-link-transfers-price-type-and-role.md` — MODIFIED (этот файл)

## Change Log

| Дата | Версия | Описание | Автор |
|---|---|---|---|
| 2026-08-05 | 0.1 | Создана стори 40.5 (привязка переносит вид цен и применяет роль), статус ready-for-dev | claude-opus-5 |
| 2026-08-05 | 1.0 | Реализация: перенос `onec_price_type_id` и вывод роли из него в `link_1c_customer`, состав `AuditLog`, 8 unit-тестов + интеграционный на реальном снимке, правка спеки (Spec Change Log, итерация 2), пункт выката в `action_items`. Статус → review | claude-opus-5 |
