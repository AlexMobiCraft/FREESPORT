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

**Approach:** Ввести роль `unregistered` для контрагентов, импортированных из 1С и ещё не зарегистрированных на портале; перевести в неё существующие 4606 записей data-миграцией; запретить импорту перезаписывать роль уже зарегистрированных пользователей; заменить `.get()` в поиске по ИНН на список кандидатов, устраняющий `MultipleObjectsReturned`.

**Автопривязка регистрации к записи 1С отключается** (решение человека, 2026-07-26). ИНН публичен, а email есть лишь у 149 из 4606 записей 1С, поэтому «подтверждение» уходило бы на адрес самого заявителя и позволяло занять запись чужой компании. Регистрация с ИНН, известным 1С, создаёт обычную заявку с ролью из формы; запись 1С не изменяется, связывание выполняет менеджер при верификации.

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
- Регистрация не изменяет запись 1С: ни `password`, ни `email`, ни `verification_status`. Запрет абсолютный — именно это делало возможным присвоение чужого контрагента по публичному ИНН.
- Не удалять `PortalLinkConfirmView`, `PortalLinkConfirmSerializer`, URL и задачу письма — они остаются в коде неиспользуемыми (решение человека), удаление вынесено в `deferred-work.md`.
- Не накладывать unique-констрейнт на `User.tax_id` (миграция упадёт на 502 строках).
- Не объединять валидаторы ИНН трёх сериализаторов и не трогать проверку дублей при смене ИНН — это отдельные отложенные пункты в `deferred-work.md`.
- Не менять формат номера заказа, ценообразование и логику верификации.
- Не выполнять UPDATE на проде вручную — только через Django data-миграцию.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ИНН известен 1С | B2B-регистрация с ИНН, которому соответствуют только записи `created_in_1c=True, role='unregistered'` с пустым паролем | Создаётся новая заявка с ролью и данными из формы, `verification_status='pending'`. Записи 1С не изменяются: пароль, email и статус остаются прежними. В лог пишется ИНН и id кандидатов для менеджера | N/A |
| Неоднозначный ИНН | ИНН принадлежит нескольким записям 1С (до 74) | То же: одна новая заявка, ни одна запись 1С не тронута. Неоднозначность не блокирует регистрацию | N/A, не 500 |
| ИНН у зарегистрированного | Среди записей с этим ИНН есть портальный аккаунт (роль не `unregistered`, либо задан пароль, либо статус не `unverified`) | HTTP 400 «Компания с данным ИНН уже зарегистрирована» — поведение сохраняется | 400 |
| Email занят | Email формы принадлежит существующему пользователю | HTTP 400 «Пользователь с таким email уже существует» | 400 |
| Роль `unregistered` в запросе | Клиент присылает `role='unregistered'` | HTTP 400: роль недоступна для регистрации и не показывается в `/users/roles/` | 400 |
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
- [x] `backend/apps/users/services/identity_resolution.py` -- `find_by_tax_id` (публичный) возвращает список кандидатов вместо `.get()`; `identify_customer` сужает по email, при неудаче отдаёт `AMBIGUOUS_TAX_ID` -- устранение `MultipleObjectsReturned`
- [x] `backend/apps/users/serializers.py` -- автопривязка отключена: `create()` всегда создаёт нового пользователя; `validate` отклоняет занятый email и ИНН, принадлежащий живому аккаунту; `validate_role` запрещает `unregistered`; `_link_matched_1c_customer` помечен как неиспользуемый -- закрытие присвоения чужой записи 1С
- [x] `backend/apps/users/models.py` -- свойство `is_unlinked_1c_record` -- единый признак «контрагент 1С без портального аккаунта»
- [x] `backend/apps/users/views/misc.py` -- скрыть `unregistered` в `/users/roles/` -- служебная роль не предлагается при регистрации
- [x] `backend/tests/unit/test_services/test_customer_processor.py` -- удалить тесты `map_role`; добавить тесты на роль новых, сохранение роли существующих и фильтр по `<Роль>` -- покрытие изменённого импорта
- [x] `backend/tests/unit/test_customer_identity_resolver.py` -- тесты на несколько кандидатов по ИНН: сужение по email и `tax_id_ambiguous` -- покрытие строк I/O-матрицы
- [x] `backend/tests/unit/test_migration_unregistered_role.py` -- тесты forward/reverse data-миграции, включая идемпотентность и защиту поданной заявки -- самый рискованный артефакт был без покрытия
- [x] `backend/tests/integration/test_portal_registration_1c_link.py` -- переписан под отключённую привязку: запись 1С не изменяется, неоднозначный ИНН не блокирует, `unregistered` отклоняется; фикстура приведена к продовому `password=''` -- устранение расхождения фикстур с реальными данными
- [x] `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts`, `frontend/src/types/index.ts`, `frontend/src/utils/pricing.ts`, `frontend/src/utils/server-auth.ts` -- `unregistered` добавлен в enum и все рукописные union'ы ролей -- контракт синхронен на обоих слоях

**Acceptance Criteria:**
- Given запись 1С с ИНН и пустым паролем, when B2B-пользователь регистрируется с этим ИНН, then создаётся новая заявка, а у записи 1С не меняются `password`, `email`, `verification_status` и `role`.
- Given ИНН, принадлежащий десяткам записей 1С, when пользователь регистрируется с этим ИНН, then ответ 201 и ни один кандидат не изменён — вместо HTTP 500.
- Given ИНН, принадлежащий живому аккаунту портала, when кто-то регистрируется с этим ИНН, then ответ 400 «Компания с данным ИНН уже зарегистрирована».
- Given заявка, поданная с ролью `trainer`, when она создана, then `role='trainer'` и `verification_status='pending'` — заявка видна admin-действию верификации B2B.
- Given запрос регистрации с `role='unregistered'`, when он обработан, then ответ 400, и роль не возвращается эндпоинтом `/users/roles/`.
- Given пользователь с ролью `wholesale_level2`, выданной менеджером, when запускается импорт контрагентов из 1С, then роль остаётся `wholesale_level2`.
- Given применённая data-миграция, when выполняется её reverse, then затронутые записи возвращаются в `retail` без потери прочих полей, а заявка в статусе `pending` не понижается.
- Given пользователь с ролью `unregistered`, when он открывает каталог, then видит розничные цены и не получает B2B-функций.

## Spec Change Log

### 2026-07-26 — итерация 1: отключение автопривязки

**Что вскрыло ревью.** Критерий привязки `role == "unregistered"` вместе с миграцией `0018` впервые сделал ветку `_link_matched_1c_customer` достижимой: до этого она была мертва, потому что все 4606 записей 1С имели `role='retail'`. Ветка ставит пароль на найденную запись (`serializers.py:234-244`), а при несовпадении email отправляет ссылку подтверждения на адрес заявителя и затем перезаписывает email записи 1С. ИНН публичен (ЕГРЮЛ, счета, сайт), а email заполнен лишь у 149 из 4606 записей — значит для 4014 записей путь «different-email» доступен любому, кто знает ИНН компании. Вторая находка: привязанная заявка сохраняла `role='unregistered'` и выпадала из admin-действия `approve_b2b_users` (`admin.py:305-314`) — фича не доходила до конца.

**Что изменено.** Автопривязка отключена целиком: регистрация с ИНН, известным 1С, создаёт обычную заявку с ролью из формы, а запись 1С остаётся нетронутой. `PortalLinkConfirmView` и связанные артефакты сохранены в коде неиспользуемыми. Матрица I/O переписана; в Never внесён абсолютный запрет на изменение записи 1С из регистрации.

**Известно-плохое состояние, которого это избегает.** Заявитель, знающий только публичный ИНН, устанавливает пароль на контрагента чужой компании либо переводит его email на свой; менеджер видит заявку с корректными реквизитами прямо из 1С и одобряет её.

**KEEP — должно пережить перевывод кода.** (1) Устранение первопричины в `processor.py`: удалённые `ROLE_MAPPING`/`map_role`, фильтр по `<Роль>Покупатель</Роль>`, отказ от перезаписи роли существующего пользователя. (2) `_find_by_tax_id`, возвращающий список кандидатов вместо `.get()` — снимает `MultipleObjectsReturned` независимо от привязки. (3) Обе миграции и признак `password=''` для выборки записей 1С. (4) Проверенный факт: парсер отдаёт `<Роль>` для всех 500 контрагентов реального XML, фильтр отсеивает 0.

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
