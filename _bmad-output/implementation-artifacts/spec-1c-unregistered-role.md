---
title: 'Роль unregistered для контрагентов 1С и восстановление привязки при регистрации'
type: 'bugfix'
created: '2026-07-26'
status: 'in-review'
review_loop_iteration: 1
baseline_commit: '530e542057ed7e32a9c1f77ecaf9bd1b75256797'
context:
  - '{project-root}/project-context.md'
  - '{project-root}/backend/docs/testing-standards.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Импорт 1С присваивает всем контрагентам `role='retail'` (`parser` отдаёт `customer_type` = `legal_entity|individual_entrepreneur|individual`, а `processor.ROLE_MAPPING` ждёт названия типов цен `Опт 1|Тренерская|РРЦ` — пересечения нет, всегда срабатывает fallback). Из-за этого ветка привязки в `UserRegistrationSerializer.validate` требует `role != "retail"` и не выполняется никогда: B2B-регистрация с любым из 3712 известных 1С ИНН отклоняется как дубль, а для 65 неоднозначных ИНН падает в `MultipleObjectsReturned` → HTTP 500. На проде это 4606 записей.

**Approach:** Ввести роль `unregistered` для контрагентов, импортированных из 1С и ещё не зарегистрированных на портале; перевести в неё существующие 4606 записей data-миграцией; запретить импорту перезаписывать роль уже зарегистрированных пользователей; сделать критерий привязки явным (`role == "unregistered"`); заменить `.get()` в поиске по ИНН на детерминированное разрешение с отказом 400 при неоднозначности.

## Boundaries & Constraints

**Always:**
- `tax_id` остаётся неуникальным. Дубли ИНН легитимны (одно юрлицо = несколько контрагентов 1С: филиалы, точки, договоры) — 65 групп, до 74 записей на ИНН.
- Импорт 1С назначает роль **только при создании** записи. Роль существующего пользователя импорт не меняет никогда — её выдаёт менеджер при верификации.
- `unregistered` не является B2B-ролью: `is_b2b_user` → `False`, ценовые фильтры отдают `retail_price` (ветка `else` в `products/filters.py`).
- Данные 1С в тестах — только реальные XML из `backend/data/import_1c/`.
- Все backend-тесты помечены `@pytest.mark.unit` или `@pytest.mark.integration`.

**Ask First:**
- Если data-миграция затронет отличное от ~4606 число строк или заденет записи с непустым `password`.
- Если фильтр по `<Роль>Покупатель</Роль>` отсеет более 0 контрагентов из `backend/data/import_1c/contragents/`.
- Прежде чем удалять `map_role`/`ROLE_MAPPING`, если обнаружится их вызов вне `processor.py` и его тестов.

**Never:**
- Не накладывать unique-констрейнт на `User.tax_id` (миграция упадёт на 502 строках).
- Не объединять валидаторы ИНН трёх сериализаторов и не трогать проверку дублей при смене ИНН — это отдельные отложенные пункты в `deferred-work.md`.
- Не менять формат номера заказа, ценообразование и логику верификации.
- Не выполнять UPDATE на проде вручную — только через Django data-миграцию.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Привязка к записи 1С | B2B-регистрация с ИНН, которому соответствует ровно одна запись `created_in_1c=True, role='unregistered', verification_status='unverified'` | Регистрация привязывается к записи 1С, `verification_status='pending'`, дубль не создаётся | N/A |
| Неоднозначный ИНН, email сузил | ИНН принадлежит нескольким записям 1С, email формы совпадает с email одной из них | Привязка к записи с совпавшим email | N/A |
| Неоднозначный ИНН, email не сузил | ИНН принадлежит нескольким записям 1С, email формы не совпадает ни с одной | HTTP 400, `tax_id`: обращение к менеджеру; запись в лог с ИНН и списком id кандидатов | 400, не 500 |
| ИНН у зарегистрированного | ИНН принадлежит записи с ролью не `unregistered` (портальный аккаунт или верифицированный) | HTTP 400 «Компания с данным ИНН уже зарегистрирована» — поведение сохраняется | 400 |
| Импорт нового контрагента | Контрагент из 1С с `<Роль>Покупатель</Роль>`, ИНН отсутствует в БД | Создаётся `User` с `role='unregistered'` | N/A |
| Импорт существующего | Контрагент из 1С совпал с пользователем, у которого `role='wholesale_level2'` | Данные обновляются, `role` остаётся `wholesale_level2` | N/A |
| Контрагент не покупатель | Контрагент из 1С с `<Роль>` не равной «Покупатель» | Пропускается, пишется в лог, не импортируется | N/A |
| Retail-покупатель портала | Регистрация retail без ИНН | Поведение не меняется: `verified`, немедленный доступ | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/users/models.py:69-89` -- `ROLE_CHOICES` и поле `role`; `is_b2b_user` (строка 248) — проверить, что `unregistered` не попадает в `b2b_roles`
- `backend/apps/users/services/processor.py:34-63` -- `ROLE_MAPPING` и `map_role` — первопричина, подлежат удалению
- `backend/apps/users/services/processor.py:65-130` -- `process_customer`: место фильтра по `<Роль>` и выбора роли
- `backend/apps/users/services/processor.py:302-350` -- `_create_customer`: назначение роли новому пользователю
- `backend/apps/users/services/processor.py:353-388` -- `_update_customer:368` `user.role = role` — перезатирание роли
- `backend/apps/users/services/parser.py:96` -- уже извлекает `<Роль>` в `customer_data["role"]`, значение сейчас игнорируется
- `backend/apps/users/services/identity_resolution.py:93-98` -- `_find_by_tax_id` с `.get()` → источник 500
- `backend/apps/users/services/identity_resolution.py:33-77` -- `identify_customer`: возврат метода идентификации
- `backend/apps/users/serializers.py:136-161` -- критерий привязки и ветка отказа
- `backend/apps/users/migrations/0016_user_country.py` -- последняя миграция, база для новых
- `backend/tests/unit/test_services/test_customer_processor.py:41-62` -- тесты `map_role`
- `backend/tests/unit/test_customer_identity_resolver.py` -- тесты резолвера
- `backend/tests/integration/test_portal_registration_1c_link.py:115,343,407` -- фикстуры с B2B-ролями, расходятся с проданными данными
- `docs/api/openapi.yaml` -- enum `role` в схемах пользователя

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/models.py` -- добавить `("unregistered", "Не зарегистрирован на портале")` в `ROLE_CHOICES`; убедиться, что `is_b2b_user` его не включает -- новая роль отделяет контрагента 1С от розничного покупателя
- [x] `backend/apps/users/migrations/0017_add_unregistered_role.py` -- миграция `AlterField` для `role` -- синхронизация choices со схемой
- [x] `backend/apps/users/migrations/0018_migrate_1c_users_to_unregistered.py` -- data-миграция: `role='retail'` → `'unregistered'` для `created_in_1c=True, password='', verification_status='unverified'`; reverse возвращает `retail` -- перевод 4606 существующих записей локально и на проде
- [x] `backend/apps/users/services/processor.py` -- удалить `ROLE_MAPPING` и `map_role`; в `process_customer` пропускать контрагентов с `<Роль>` ≠ «Покупатель»; `_create_customer` назначает `unregistered`; `_update_customer` не трогает `user.role` -- устранение первопричины и защита роли, выданной менеджером
- [x] `backend/apps/users/services/identity_resolution.py` -- `_find_by_tax_id` возвращает список кандидатов вместо `.get()`; `identify_customer` при нескольких кандидатах сужает по нормализованному email, при неудаче возвращает метод `tax_id_ambiguous` и логирует ИНН со списком id -- устранение `MultipleObjectsReturned`
- [x] `backend/apps/users/serializers.py` -- критерий привязки `matched_customer.role == "unregistered"`; обработка `tax_id_ambiguous` → 400 с указанием обратиться к менеджеру -- явный критерий вместо отрицания
- [x] `backend/tests/unit/test_services/test_customer_processor.py` -- удалить тесты `map_role`; добавить тесты на роль новых, сохранение роли существующих и фильтр по `<Роль>` -- покрытие изменённого импорта
- [x] `backend/tests/unit/test_customer_identity_resolver.py` -- тесты на несколько кандидатов по ИНН: сужение по email и `tax_id_ambiguous` -- покрытие строк I/O-матрицы
- [x] `backend/tests/integration/test_portal_registration_1c_link.py` -- перевести фикстуры 1С-записей на `role='unregistered'`; добавить интеграционные тесты неоднозначного ИНН (400) и отказа для зарегистрированного -- устранение расхождения фикстур с реальными данными
- [x] `docs/api/openapi.yaml` -- регенерировать схему, обновить типы фронта -- обязательная синхронизация контракта

**Acceptance Criteria:**
- Given прод-подобная БД, где записи 1С имеют `role='unregistered'`, when B2B-пользователь регистрируется с ИНН одной такой записи, then регистрация привязывается к ней и новый `User` не создаётся.
- Given ИНН, принадлежащий 74 записям 1С, when пользователь регистрируется с этим ИНН и email, не совпадающим ни с одной, then ответ 400 с направлением к менеджеру, а не 500.
- Given пользователь с ролью `wholesale_level2`, выданной менеджером, when запускается импорт контрагентов из 1С, then роль остаётся `wholesale_level2`.
- Given применённая data-миграция, when выполняется её reverse, then затронутые записи возвращаются в `retail` без потери прочих полей.
- Given пользователь с ролью `unregistered`, when он открывает каталог, then видит розничные цены и не получает B2B-функций.
- Given полный прогон `make test`, when тесты завершены, then падений нет, покрытие `apps/users` не ниже прежнего.

## Spec Change Log

## Design Notes

Разрешение неоднозначного ИНН — детерминированное, без «взять первого»: при 74 кандидатах случайный выбор привязал бы заявителя к чужому контрагенту. Порядок: сузить по нормализованному email → при единственном совпадении привязать → иначе отказ с логом.

`identify_customer` сохраняет текущую сигнатуру `(User|None, str|None)`; для неоднозначности возвращается `(None, "tax_id_ambiguous")`, что отличимо от `(None, None)` («не найден») и не ломает существующих вызывающих.

Фильтр по `<Роль>Покупатель</Роль>` на текущих выгрузках (3202 контрагента в 7 файлах) отсеивает 0 записей — он защищает от появления поставщиков и конкурентов в будущих выгрузках, а не чинит текущие данные.

Data-миграция опирается на `password=''`: все 4606 записей 1С имеют пустой пароль и не могут войти, тогда как портальные аккаунты всегда имеют хеш. Это отделяет их от 5 настоящих retail-пользователей с `created_in_1c=False`.

## Verification

**Commands:**
- `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py makemigrations users --check --dry-run` -- expected: новых незакоммиченных миграций нет
- `make test-unit` -- expected: зелёный, включая новые тесты процессора и резолвера
- `make test-integration` -- expected: зелёный, включая `test_portal_registration_1c_link.py`
- `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate users` -- expected: обе миграции применяются без ошибок
- Проверка фильтра на реальном XML (`/app/data` перекрыт корневым `data/`, поэтому файл подаётся через `docker cp` в `/tmp`): `CustomerDataParser().parse(<file>)` → все контрагенты имеют `role == "Покупатель"` -- expected: фильтр `is_buyer` отсеивает 0 записей. Команда `import_customers_from_1c` принимает `--data-dir`, не `--file`.
- `npx gitnexus detect-changes --scope all` -- expected: затронуты только символы из Code Map

**Manual checks (if no CLI):**
- После применения миграций на проде: `SELECT role, COUNT(*) FROM users WHERE created_in_1c GROUP BY role` возвращает единственную строку `unregistered | 4606`.
