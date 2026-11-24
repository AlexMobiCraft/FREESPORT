---
title: 'Обязательное поле «Фамилия» в форме регистрации /register'
type: 'feature'
created: '2026-11-24'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'c521878847a2d8bd2b4351a10555fc5f38043741'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В основной форме регистрации `/register` нет поля «Фамилия»: она отправляет `last_name: ''`, и менеджер получает заявку без фамилии. API фамилию не требует, поэтому её не проверяет и прямой POST. Форма `/b2b-register` фамилию уже собирает и проверяет на клиенте.

**Approach:** Добавить в `/register` обязательное поле «Фамилия» сразу после «Имени», с той же валидацией, что в `/b2b-register`, и отправлять введённое значение в `last_name`: регистрация всегда создаёт новую запись `User`, так что значение попадёт в `users_user.last_name`. На сервере сделать `last_name` обязательным и непустым, а заодно отклонять `first_name` из пробелов (пункт deferred-work из спеки `spec-register-all-fields-required`).

## Boundaries & Constraints

**Always:** Поле повторяет «Фамилию» из `B2BRegisterForm`: подпись «Фамилия», `autoComplete="family-name"`, плейсхолдер «Петров», `requiredMark`, сообщение «Фамилия обязательна», лимит 150 символов. Строка из пробелов отклоняется и на клиенте, и на сервере. Клиент отправляет введённое значение без изменений; сервер, как и для прочих строк, обрезает пробелы по краям (`" Петров "` → `"Петров"`). Серверная ошибка `last_name` выводится под полем.

**Never:** Не трогать модель `User` и не писать миграцию: `blank=True` нужен записям из 1С, у юрлиц фамилии нет. Не заполнять фамилию задним числом у существующих пользователей. Не менять профиль, чекаут, админку и импорт 1С. Не возвращать `_link_matched_1c_customer`. Не менять формулировки согласий и `.env*`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Успех | `/register`, все поля + «Фамилия» = «Петров» | В запросе `last_name: "Петров"`, у созданного `User` `last_name == "Петров"` | N/A |
| Пусто / пробелы | «Фамилия» = `""` или `"   "` | Запрос не уходит | «Фамилия обязательна» под полем |
| API без поля | POST `/auth/register/` без `last_name` | 400 | `{"last_name": ["Фамилия обязательна."]}` |
| API пусто / пробелы | `last_name` или `first_name` = `""` / `"   "` | 400 | Ошибка по соответствующему полю |
| `/b2b-register` | Как сейчас, с фамилией | 201, поведение не меняется | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/users/serializers.py:74` -- `UserRegistrationSerializer.Meta.extra_kwargs` (стр. ~164): у `last_name` `required: True`, `allow_blank: False`, `error_messages` `required`/`blank`/`null` = «Фамилия обязательна.»; у `first_name` к существующему `required: True` добавить `allow_blank: False` и то же для «Имя обязательно.». Из `"   "` DRF по умолчанию (`trim_whitespace`) делает `""`, дальше срабатывает `blank`. `create()` не трогать: `last_name` уже входит в `Meta.fields` и уходит в `create_user`. Impact: LOW, 4 прямых вызывающих, процессов нет.
- `docs/api/openapi.yaml:5383` -- `UserRegistrationRequest`: `last_name` попадёт в `required`, `minLength: 1` получат `last_name` и `first_name`. Перегенерировать `spectacular` командой из Verification (локальный venv запрещён, в тестовом контейнере `docs/` по умолчанию не смонтирован), не править вручную. `UserRegistrationRequestSchemaExtension` (`serializers.py:499-545`) `required` не переписывает — правок не нужно.
- `frontend/src/types/api.generated.ts:3082` -- `last_name?` станет обязательным; `npm run generate:types` (гейт `api-contract.yml`).
- `frontend/src/schemas/authSchemas.ts:63` -- `registerSchema`: добавить `last_name` по образцу `b2bRegisterSchema.last_name` (стр. 158).
- `frontend/src/components/auth/RegisterForm.tsx` -- `REGISTER_FIELD_ERROR_MAP` (стр. 65): `last_name`; `onSubmit` (стр. 128-131): `last_name: data.last_name`, устаревший комментарий убрать; `<Input label="Фамилия">` сразу после «Имени» (стр. ~319). Impact: LOW, страница `/register`.
- `frontend/src/components/auth/B2BRegisterForm.tsx:380` -- образец поля, правок нет.
- Бэкенд-тесты, в чьих payload нет `last_name`, после правки получат 400. Добавить фамилию: `backend/tests/integration/test_verification_workflow.py:130`, `backend/tests/regression/test_epic_28_intact.py:45,70,135`, `backend/tests/unit/test_user_verification.py:37,56,80,104`, хелпер `_registration_payload` в `backend/tests/unit/test_serializers/test_user_serializers.py:670-685` (11 тестов телефона).
- Фронтенд-тесты: `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` — ожидания `last_name: ''` (стр. 338-1427); «Имя» вводится в 14 тестах прямо в теле и в хелперах `fillB2BFields`/`fillPersonalFields`/`fillCommonFields` — ввод фамилии нужен во всех тестах с отправкой, иначе они станут красными (общий шаг ввода имени и фамилии вынести в хелпер). `frontend/src/schemas/__tests__/authSchemas.test.ts`: `validRegisterBase` (стр. 128) и объект без него на стр. 156.
- `frontend/src/__mocks__/api/handlers.ts:481` -- мок отвечает `last_name: ''`; брать `body.last_name`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/serializers.py` -- обязательные и непустые `last_name` и `first_name` -- закрыть обход через прямой POST.
- [x] `backend/tests/unit/test_serializers/test_user_serializers.py` -- тесты: нет `last_name` → ошибка; `""`/`"   "` у `last_name` и `first_name` → ошибка; успешная регистрация сохраняет `last_name`. Дополнить фамилией старые payload'ы в перечисленных тестах -- покрытие матрицы.
- [x] `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` -- перегенерировать -- контракт и гейт `api-contract.yml`.
- [x] `frontend/src/schemas/authSchemas.ts` + `authSchemas.test.ts` -- `last_name` в `registerSchema`; `test.each(['', '   '])` -- клиентская проверка.
- [x] `frontend/src/components/auth/RegisterForm.tsx` + `RegisterForm.test.tsx` -- поле, отправка, маппинг серверной ошибки; поправить ожидания `last_name: ''` и хелперы; тесты: поле есть с пометкой и `aria-required`, стоит сразу после «Имени», пробелы не отправляются, значение уходит в запрос, серверная ошибка `last_name` показана под полем -- видимый результат.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- закрыть пункт стр. 1391-1392 (`source_spec: spec-register-all-fields-required.md`, «отклонять `first_name`/`last_name` из пробелов… `last_name` обязательным») со ссылкой на эту спеку -- спека выполняет его целиком.

**Acceptance Criteria:**
- Given открыта `/register`, when пользователь видит форму, then сразу после «Имени» есть поле «Фамилия» со звёздочкой и `aria-required="true"`.
- Given регистрация через `/register` прошла, when менеджер открывает пользователя в админке, then фамилия заполнена введённым значением.
- Given существующие тесты `/b2b-register`, when они запущены, then проходят без правок.

## Implementation Notes

- **Вкладка, открытая до релиза (принятый риск, решение владельца 2026-11-24).** Старый бандл шлёт `last_name: ''`, новый сервер отвечает 400 `{"last_name": ["Фамилия обязательна."]}`. В старом `REGISTER_FIELD_ERROR_MAP` нет `last_name`, поэтому сообщение уходит в верхний баннер, а поля на странице нет — до перезагрузки отправить форму нельзя. Окно — только вкладки, открытые до выката; B2B-заявок мало, лечится перезагрузкой. Два релиза (сначала фронт, потом сервер) не делаем.
- **Обязательность для всех ролей (решение владельца 2026-11-24).** `last_name` обязателен безусловно, а не только для B2B, как формулировал пункт deferred-work. При включении `REGISTRATION_ALLOW_RETAIL` розничный покупатель тоже вводит фамилию — это намеренно.
- **Зачем это менеджеру.** Письма админу и региональному менеджеру уже печатают `ФИО: {{ user.full_name }}` (`backend/templates/emails/manager_region_notification.txt:7`, `admin_new_verification_request.txt:6`), а `User.full_name` = `f"{first_name} {last_name}".strip()` — сейчас там одно имя. Шаблоны не трогать.
- **Негативные тесты.** `test_user_verification.py:37` проверяет только `errors["role"]` и остался бы зелёным без фамилии. Фамилию в payload добавить, чтобы тест падал по своей причине.

## Spec Change Log

## Review Triage Log

| # | Слой | Находка | Вердикт | Маршрут | Обоснование |
|---|------|---------|---------|---------|-------------|
| 1 | graph-impact | Индекс `stale`, слой не выполнен | medium | defer | `stale` только из-за незакоммиченного diff (8 файлов diff). Восполнено вручную: `impact UserRegistrationSerializer` без тестов — LOW, процессов 0, вызывающие — импорты модулей `views`; `check --cycles` = базовая линия. Исправление — в `.windsurf/rules/gitnexus.md`. |
| 2 | edge-case | `.max(150)` в `registerSchema.last_name` считает необрезанную строку, сервер режет пробелы до `max_length` | low | defer | Подтверждено: DRF `CharField` обрезает до валидаторов. Правило дословно скопировано из `b2bRegisterSchema` (спека требует ту же валидацию) — исправлять в обеих схемах сразу. |
| 3 | edge-case, blind | Имя/фамилия из `​` или `"-"` проходят обе проверки | low | reject | Пользователь такое не вводит, а исправление — новый валидатор (буквы) на сервере и клиенте. |
| 4 | edge-case, blind | `minLength: 1` в OpenAPI пропускает `"   "` | low | reject | Генерируемые типы паттерны не проверяют, сервер отвечает 400; исправление — новый код в `UserRegistrationRequestSchemaExtension`. |
| 5 | blind | Спеки нет в diff, deferred-work закрыт до конца ревью | false | reject | Спеку из diff исключили намеренно (claims-файл), она лежит в дереве (`git add -N`) и уйдёт тем же коммитом, что и закрытие пункта. |
| 6 | blind | PATCH профиля может стереть ФИО после регистрации | medium | defer | Подтверждено: `UserProfileSerializer` (стр. 650-651) пишет `first_name`/`last_name` без `allow_blank=False`. Не вызвано этой правкой, профиль спека трогать запрещает. |
| 7 | blind | Не заданы сообщения `max_length`/`invalid` на сервере | false | reject | Стандартный текст DRF локализован и корректен; клиент отсекает 151 символ раньше — вреда для пользователя нет. |
| 8 | blind | API-тесты: нет проверки сохранения `last_name` через HTTP | low | patch | `test_user_registration` проверяет лишь `exists()`; добавлена проверка `last_name`. Прочие случаи (без `first_name`, `null`) покрыты тестами сериализатора. |
| 9 | blind | Тексты клиента и сервера расходятся точкой | false | reject | Оба текста заданы матрицей в замороженном разделе спеки. |
| 10 | blind | Правила имени/фамилии продублированы (фронт и бэк) | low | reject | Спека требует повторить поле из B2B; общий конструктор — рефакторинг без названного вреда. |
| 11 | blind | `views-documentation.md:337`: `confirm_password` и не помечена обязательность ФИО | low | patch | Подтверждено: параметр называется `password_confirm`, фамилия теперь обязательна. |
| 12 | blind | Мок `handlers.ts` вернёт `undefined` без `last_name` | false | reject | Обе формы всегда шлют `last_name` по своим схемам; вызова без фамилии нет. `role: 'retail'` — старый мок, не эта правка. |
| 13 | blind | Закрытие в deferred-work без API-тестов и принятого риска | low | patch | Дописаны ссылки на API-тесты и риск старого бандла. |

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -p no:sugar tests/unit/test_serializers/test_user_serializers.py tests/unit/test_user_verification.py tests/integration/test_verification_workflow.py tests/regression/test_epic_28_intact.py tests/integration/test_user_api.py tests/integration/test_auth_registration_consent.py tests/integration/test_registration_emails.py tests/integration/test_portal_registration_1c_link.py tests/integration/test_auth_registration_tokens.py tests/integration/test_registration_transaction_safety.py tests/integration/test_responsible_manager_events.py tests/integration/test_catalog_api.py tests/integration/test_import_role_from_1c.py apps/common/tests/test_api_schema.py` -- expected: всё зелёное.
- Генерация схемы (Git Bash, из `docker/`, после pytest): `MSYS_NO_PATHCONV=1 docker compose -p freesport-test -f docker-compose.test.yml run --rm --no-deps -T -v "C:/Users/1/DEV/FREESPORT/docs:/contract" backend python manage.py spectacular --file /contract/api/openapi.yaml --format openapi --validate`; затем `cd frontend; npm run generate:types` -- expected: в diff `openapi.yaml` только `UserRegistrationRequest`.
- Сверка: `MSYS_NO_PATHCONV=1 docker compose -p freesport-test -f docker-compose.test.yml run --rm --no-deps -T -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml` -- expected: схема синхронна.
- `cd frontend; npx vitest run src/components/auth src/schemas src/__tests__; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок.

**Manual checks (if no CLI):**
- `/register`: «Фамилия» стоит после «Имени», пустая и из пробелов не отправляется.
