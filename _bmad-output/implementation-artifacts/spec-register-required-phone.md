---
title: 'Обязательный телефон в форме регистрации (формат по стране)'
type: 'feature'
created: '2026-10-20'
status: 'done'
baseline_commit: '20f0effa87df92c514514584c7b9e9ec3fc0e1ee'
review_loop_iteration: 0
context:
  - '{project-root}/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Форма `/register` не спрашивает телефон и шлёт `phone: ''`, а `UserRegistrationSerializer` это принимает — заявка уходит региональному менеджеру без контакта. Форма `/b2b-register` телефон собирает, но Zod пропускает любую смесь цифр и скобок, а поле всегда подставляет `+7`, хотя в форме можно выбрать Беларусь.

**Approach:** Телефон обязателен в обеих формах и в API регистрации. Формат зависит от выбранной страны: поле «Страна» стоит выше поля «Телефон», смена страны меняет префикс и маску. Россия и Казахстан — `+7` и 10 цифр; Беларусь — `+375` и 9 цифр.

## Boundaries & Constraints

**Always:** Формат определяет страна: `Россия`, `Казахстан` → `^\+7\d{10}$`; `Беларусь` → `^\+375\d{9}$`. Страна не передана → Россия (как в модели). Сервер проверяет сам, независимо от фронта, и сверяет номер со страной из того же запроса. Сообщения на русском. Контракт API (`docs/api/openapi.yaml`, `api.generated.ts`) обновляется вместе с кодом.

**Ask First:** Правка телефонов существующих пользователей; расширение страны сверх трёх текущих.

**Never:** Не трогать профиль, чекаут, адреса доставки (`PhoneInput` без параметра страны остаётся прежним: `+7`) и импорт из 1С (`_normalize_phone`) — записать в `deferred-work.md`. Не нормализовать на сервере `8 (900)…`. Не добавлять в `/register` фамилию. Не менять `.env*`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| РФ / КЗ | `country: "Россия"` или `"Казахстан"`, `phone: "+79001234567"` | Заявка создана | N/A |
| Беларусь | `country: "Беларусь"`, `phone: "+375291234567"` | Заявка создана | N/A |
| Страна не передана | `phone: "+79001234567"` | Проверка как для России | N/A |
| Номер не той страны | `"Беларусь"` + `+79001234567`, или `"Россия"` + `+375291234567` | 400 по полю `phone` | «Номер телефона должен быть в формате: '+375291234567'» / «…'+79001234567'» |
| Пусто или нет поля | `""` / отсутствует | 400 по полю `phone` | «Укажите номер телефона.» |
| Мусор | `"89001234567"`, `"+7900"`, `"+7 900 123 45 67"` | 400 по полю `phone` | сообщение формата страны |
| Форма: смена страны | РФ ↔ КЗ | Введённые цифры сохраняются | N/A |
| Форма: смена страны | РФ/КЗ ↔ Беларусь | Поле сбрасывается к префиксу новой страны (`+7` / `+375`) | N/A |
| Форма: пустой номер | только префикс | Submit блокируется, ошибка под полем | Zod: «Укажите номер телефона в формате …» |
| Ошибка сервера по `phone` | 400 | Сообщение под полем телефона | `applyBackendFieldErrors` |

</frozen-after-approval>

## Code Map

- `backend/apps/users/models.py:201` -- `User.phone_regex`: сейчас только `+7`; расширяется до `+7\d{10}` или `+375\d{9}`, иначе Django-админка не сохранит белорусский номер.
- `backend/apps/users/migrations/` -- новая `0026_…` (`AlterField phone`), последняя сейчас `0025`.
- `backend/apps/users/serializers.py:66` -- `UserRegistrationSerializer`: `extra_kwargs["phone"]` и проверка в `validate()` рядом с проверкой `country`.
- `frontend/src/utils/validators/phone.ts` (новый) -- конфиг по странам: префикс, число цифр, regex, подсказка, сообщение; единый источник для схем и `PhoneInput`.
- `frontend/src/components/ui/Input/PhoneInput.tsx` -- необязательный проп `country`; без него поведение прежнее (профиль не меняется).
- `frontend/src/schemas/authSchemas.ts` -- `registerSchema` и `b2bRegisterSchema`: `phone` + `refine` по `country`.
- `frontend/src/components/auth/RegisterForm.tsx` -- «Телефон» сразу под «Страной», сброс при смене региона номера, `phone` в запросе и в `REGISTER_FIELD_ERROR_MAP`.
- `frontend/src/components/auth/B2BRegisterForm.tsx:345` -- блок «Страна» (сейчас в «Реквизитах компании», стр. ~430) переносится в «Контактное лицо» над телефоном.
- `docs/api/openapi.yaml:5177`, `frontend/src/types/api.generated.ts` -- `phone` обязателен, `pattern` расширен.
- Тесты регистрации без телефона: `backend/tests/integration/test_auth_registration_*.py`, `test_registration_*.py`, `test_portal_registration_1c_link.py`, `test_responsible_manager_events.py`, `test_verification_workflow.py`, `test_import_role_from_1c.py`, `backend/tests/regression/test_epic_28_intact.py`, `backend/tests/unit/test_user_verification.py`, `backend/tests/unit/test_serializers/test_user_serializers.py`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/models.py` + миграция `0026` -- расширить `phone_regex`, сообщение: два формата -- хранение +375.
- [x] `backend/apps/users/serializers.py` -- `phone` обязателен и непуст; в `validate()` сверка номера со страной, сообщение по формату страны -- серверная гарантия.
- [x] `backend/tests/unit/test_serializers/test_user_serializers.py` -- строки матрицы I/O; `makemigrations --check` чисто -- закрепить контракт.
- [x] Остальные backend-тесты регистрации (Code Map) -- корректный `phone` в payload -- иначе падают на новом 400.
- [x] `frontend/src/utils/validators/phone.ts` + тест -- конфиг и функции проверки/сброса префикса -- единый источник.
- [x] `PhoneInput.tsx` + тест -- проп `country`: префикс, лимит цифр, placeholder; без пропа как раньше -- регрессии профиля нет.
- [x] `authSchemas.ts`, `RegisterForm.tsx`, `B2BRegisterForm.tsx` -- поля и порядок по Code Map -- формы.
- [x] Тесты `RegisterForm.test.tsx`, `B2BRegisterForm.test.tsx` (оба файла), `register-request-contract.test.ts` -- телефон в существующих сценариях; новые: пусто, смена страны, серверная ошибка поля.
- [x] `docs/api/openapi.yaml`, `api.generated.ts` -- регенерировать (`check_openapi_sync`).
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- запись: профиль/чекаут/адреса остаются на `+7`; в профиле белорусский номер при правке превратится в `+7…`, чекаут с автозаполнением из профиля его не примет.

**Acceptance Criteria:**
- Given `/register` или `/b2b-register`, when выбрана Беларусь, then поле «Телефон» стоит ниже «Страны», подставляет `+375` и принимает 9 цифр после него.
- Given выбранная Россия и пустой или короткий номер, when отправка, then запрос не уходит, под полем ошибка.
- Given POST `/auth/register/` с белорусским номером и `country: "Россия"`, when обработка, then 400 по `phone`, пользователь не создан.
- Given пользователь с `+375…` в `User.phone`, when сохранение в Django-админке, then валидация проходит.

## Design Notes

Страна в B2B-форме переезжает в блок «Контактное лицо», чтобы порядок «страна → телефон» не разрывал блоки. Для Казахстана формат совпадает с российским (общий код `+7`), поэтому сервер различает только две маски. Смена страны внутри группы `+7` цифры сохраняет — человек мог выбрать страну по ошибке, а ввод номера уже закончить.

## Verification

**Commands:**
- `cd docker; docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -p no:sugar tests/unit/test_serializers/test_user_serializers.py tests/integration/test_auth_registration_consent.py tests/integration/test_auth_registration_tokens.py tests/integration/test_registration_emails.py tests/integration/test_registration_transaction_safety.py tests/integration/test_portal_registration_1c_link.py tests/integration/test_responsible_manager_events.py tests/integration/test_verification_workflow.py tests/integration/test_import_role_from_1c.py tests/regression/test_epic_28_intact.py tests/unit/test_user_verification.py apps/common/tests/test_api_schema.py` -- expected: зелёные.
- `makemigrations --check --dry-run` в том же контейнере -- expected: без изменений.
- `cd frontend; npx vitest run src/components/auth src/components/ui/Input src/utils/validators src/__tests__; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок.

**Manual checks (if no CLI):**
- `/register` и `/b2b-register`: смена страны меняет префикс и маску, РФ↔КЗ цифры сохраняются, пустой номер не отправляется.

## Suggested Review Order

**Формат номера по стране (серверный источник)**

- Единая таблица форматов: Россия и Казахстан делят `+7`, Беларусь — `+375`; сверка идёт с `re.ASCII`.
  [`phone.py:34`](../../backend/apps/users/phone.py#L34)

- Телефон обязателен, модельные валидаторы сняты: формат зависит от страны из запроса.
  [`serializers.py:160`](../../backend/apps/users/serializers.py#L160)

- Проверка по стране из исходных данных; некорректную страну отклоняет её собственное поле.
  [`serializers.py:198`](../../backend/apps/users/serializers.py#L198)

- Модель принимает номера всех стран, иначе Django-админка не сохранит `+375…`.
  [`models.py:202`](../../backend/apps/users/models.py#L202)

- Миграция только меняет валидатор, данные не трогает.
  [`0026_alter_user_phone_country_formats.py:1`](../../backend/apps/users/migrations/0026_alter_user_phone_country_formats.py#L1)

**Формат номера по стране (клиент)**

- Зеркало таблицы форматов; защита префикса, вставки и чужих номеров.
  [`phone.ts:64`](../../frontend/src/utils/validators/phone.ts#L64)

- При смене страны цифры сохраняются внутри `+7`, иначе сбрасываются к новому префиксу.
  [`phone.ts:95`](../../frontend/src/utils/validators/phone.ts#L95)

- `PhoneInput` без `country` остаётся российским — профиль и чекаут не затронуты.
  [`PhoneInput.tsx:12`](../../frontend/src/components/ui/Input/PhoneInput.tsx#L12)

- Одна проверка номера по стране для обеих схем; ошибка ложится на поле `phone`.
  [`authSchemas.ts:23`](../../frontend/src/schemas/authSchemas.ts#L23)

**Формы**

- `/register`: «Телефон» под «Страной», сброс и пересчёт ошибки при смене страны.
  [`RegisterForm.tsx:227`](../../frontend/src/components/auth/RegisterForm.tsx#L227)
  [`RegisterForm.tsx:439`](../../frontend/src/components/auth/RegisterForm.tsx#L439)

- `/b2b-register`: «Страна» перенесена в «Контактное лицо» над телефоном.
  [`B2BRegisterForm.tsx:404`](../../frontend/src/components/auth/B2BRegisterForm.tsx#L404)
  [`B2BRegisterForm.tsx:425`](../../frontend/src/components/auth/B2BRegisterForm.tsx#L425)

**Контракт API**

- `phone` обязателен, `pattern` расширен у регистрации и у профильных схем.
  [`openapi.yaml:5209`](../../docs/api/openapi.yaml#L5209)

**Тесты**

- Матрица I/O: обязательность, страны, чужой номер, не-ASCII цифры, невалидная страна.
  [`test_user_serializers.py:687`](../../backend/tests/unit/test_serializers/test_user_serializers.py#L687)

- Поведение форм: порядок полей, префикс, сброс при смене страны, ошибки.
  [`RegisterForm.test.tsx:1255`](../../frontend/src/components/auth/__tests__/RegisterForm.test.tsx#L1255)
