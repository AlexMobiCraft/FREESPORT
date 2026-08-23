---
title: 'Убрать регистрацию розничных клиентов из формы регистрации'
type: 'feature'
created: '2026-08-23'
status: 'done'
review_loop_iteration: 1
baseline_commit: 'b2866246'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/spec-trainer-registration-inn.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `/register` предлагает роль «Розничный покупатель» (выбрана по умолчанию), бэкенд разрешает `retail` в `SELF_SERVICE_ROLES`. Портал OPTISPORT — B2B-площадка: розничные саморегистрации создают аккаунты, которые никто не верифицирует.

**Approach:** Убрать `retail` из саморегистрации на всех трёх уровнях (React-форма, Zod-схема, DRF-сериализатор). `/register` остаётся универсальной точкой входа с тремя B2B-ролями и без предвыбора — роль выбирается осознанно.

## Boundaries & Constraints

**Always:**
- Роль обязательна на всех трёх уровнях. На бэкенде `role` → `required=True`: у модели `User.role` есть `default="retail"`, без явного `required` пропуск поля создаст розничный аккаунт в обход запрета.
- Разрешённые роли саморегистрации: `wholesale_level1`, `trainer`, `federation_rep` — списки в форме и в `SELF_SERVICE_ROLES` совпадают.
- Существующие `retail`-аккаунты продолжают логиниться и работать — запрет только на создание новых.
- Правила B2B-полей не меняются: `company_name`, `tax_id`, `country` обязательны для любой роли (см. `spec-trainer-registration-inn.md`).
- Серверная проверка самодостаточна: клиентская её не заменяет.

**Ask First:**
- Миграция или массовое изменение роли существующих `retail`-пользователей.
- Изменение `/b2b-register` и `B2BRegisterForm` (роль зашита в `wholesale_level1`, ОГРН и юр. адрес обязательны) — вне скоупа.
- Удаление или редирект `/register`.

**Never:**
- Не менять модель `User`: `retail` остаётся в `ROLE_CHOICES` и `default`, миграций нет.
- Не рефакторить ветки `if role == "retail"` в `UserRegistrationSerializer.validate()` и `.create()` — после запрета недостижимы через API, но остаются защитой при прямом вызове.
- Не трогать `RoleInfoPanel`, привязку к 1С (`CustomerIdentityResolver`, `_reject_if_tax_id_belongs_to_account`), маршрутизацию на менеджера.
- Не менять `RoleEnum` в `docs/api/openapi.yaml` — это enum модели, не список ролей регистрации.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Форма открыта | Первый рендер `/register` | Селектор показывает плейсхолдер «Выберите тип аккаунта» и 3 опции; B2B-поля и `RoleInfoPanel` скрыты | N/A |
| Роль не выбрана | Submit с пустым `role` | Форма не отправляется | Ошибка под селектором: «Выберите тип аккаунта» |
| Выбрана B2B-роль | `role = trainer` | Появляются «Название компании», «ИНН» (required), «Страна», `RoleInfoPanel` | N/A |
| API: retail | `POST /api/v1/auth/register/`, `role=retail` | 400, пользователь не создан | `{"role": ["Недопустимая роль для регистрации."]}` |
| API: role отсутствует | `POST /api/v1/auth/register/` без `role` | 400, пользователь не создан (модельный `retail` не подставляется) | `{"role": ["Обязательное поле."]}` |
| API: B2B-роль | `role=wholesale_level1` + company_name + валидный ИНН | 201, `is_verified=false`, токены не выдаются, письма ставятся в очередь | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/auth/RegisterForm.tsx` -- `ROLE_OPTIONS` (52-57), `defaultValues.role`, `isB2BRole`, фолбэк `data.role ?? 'retail'` в `onSubmit`
- `frontend/src/schemas/authSchemas.ts` -- `registerSchema`: `role` enum с `.default('retail')` (54) и три `.refine()` с условием `role !== 'retail'`
- `frontend/src/app/(blue)/(auth)/register/page.tsx` -- подзаголовок «Создайте аккаунт для доступа к платформе»
- `frontend/src/app/(blue)/(auth)/b2b-register/page.tsx` -- блок «Не бизнес-клиент? Обычная регистрация» (27-36)
- `backend/apps/users/serializers.py` -- `UserRegistrationSerializer`: `SELF_SERVICE_ROLES` (85), `validate_role()`, `Meta.extra_kwargs`
- `backend/apps/users/views/authentication.py` -- `@extend_schema` description и пример `successful_registration_retail` (63-105)
- `backend/apps/users/views/misc.py` -- `user_roles_view`: публичный список ролей, найден при реализации — тоже предлагал `retail`
- `docs/api/openapi.yaml` -- description операции `auth_register_create` (288-290)
- Тесты с регистрацией `retail` через API: `backend/tests/integration/` — `test_auth_registration_consent.py` (фикстура `retail_payload`, 24 теста), `test_auth_registration_tokens.py`, `test_portal_registration_1c_link.py`, `test_registration_emails.py`, `test_user_api.py`; `backend/tests/regression/test_epic_28_intact.py`; `backend/tests/unit/test_serializers/test_user_serializers.py`; `backend/tests/unit/test_user_verification.py`
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` -- кейсы предвыбора `retail` и переключения ролей

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/serializers.py` -- убрать `"retail"` из `SELF_SERVICE_ROLES`; `"role": {"required": True}` в `Meta.extra_kwargs`
- [x] `backend/apps/users/views/authentication.py` -- description и пример `successful_registration_retail` → B2B-вариант
- [x] `docs/api/openapi.yaml` -- синхронизировать description `auth_register_create`
- [x] `frontend/src/schemas/authSchemas.ts` -- `role`: enum из трёх ролей, без `.default()`, сообщение «Выберите тип аккаунта»; снять условия `role !== 'retail'` в трёх `.refine()`
- [x] `frontend/src/components/auth/RegisterForm.tsx` -- `ROLE_OPTIONS` без `retail`; пустой `defaultValues.role` + `<option value="">Выберите тип аккаунта</option>`; `isB2BRole` = роль выбрана; снять фолбэк `?? 'retail'` и условие `data.role !== 'retail'` для `tax_id`
- [x] `frontend/src/app/(blue)/(auth)/register/page.tsx` -- подзаголовок про регистрацию бизнес-партнёра
- [x] `frontend/src/app/(blue)/(auth)/b2b-register/page.tsx` -- переписать блок «Не бизнес-клиент?»: ссылка ведёт на форму, где розницы больше нет
- [x] `backend/tests/**` -- перевести регистрационные payload'ы с `retail` на B2B-роль (уникальный ИНН на вызов); добавить тесты отказа `role=retail` и отсутствующего `role`
- [x] `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` -- обновить кейсы селектора: 3 опции, нет предвыбора, ошибка при пустой роли
- [x] `backend/apps/users/views/misc.py` + `frontend/src/schemas/__tests__/authSchemas.test.ts` -- `user_roles_view` строит список из `SELF_SERVICE_ROLES`; тесты Zod-схемы на отказ `retail` и отсутствующей роли (сверх исходного плана)
- [x] `backend/tests/integration/test_catalog_api.py` -- хелпер `register_and_login_user` заводит розничного пользователя напрямую: розничные аккаунты остаются в системе и должны видеть retail-цены (найдено полным прогоном)

**Acceptance Criteria:**
- Given чистая форма `/register`, when пользователь открывает страницу, then опции «Розничный покупатель» нет и ни одна роль не выбрана.
- Given роль `trainer`, when форма отправлена с валидными данными, then заявка уходит с `role=trainer`, аккаунт создаётся неверифицированным.
- Given существующий `retail`-пользователь, when он логинится, then вход и работа с каталогом не изменились.
- Given весь набор тестов, when прогнаны бэкенд и фронтенд, then регрессий нет и покрытие не ниже порога 73.

## Spec Change Log

### Итерация ревью 1 (2026-08-23)

Находки Blind Hunter и Edge Case Hunter, устранённые как `patch` (спека не менялась, код не перевыводился):

1. **Два блокера CI.** `check_openapi_sync` упал бы на `paths./users/roles/.get.description` (описание изменено в коде, не в контракте), а гейт типов — на неперегенерированном `api.generated.ts` после добавления `role` в `required`. Контракт пересобран `manage.py spectacular`, типы — `npm run generate:types`; гейт прогнан локально.
2. **Молчаливый редирект после успешной заявки** (найдено обоими ревьюерами независимо). Автологина не осталось ни для одной роли, а форма по-прежнему делала `router.push('/')` — заявка выглядела потерянной. Добавлено состояние «Заявка на рассмотрении» по образцу `B2BRegisterForm`.
3. **`user` в store без токенов.** `authService.register/registerB2B` клали пользователя в store при отсутствии токенов; `CheckoutForm` определяет вход как `!!user` → «полуавторизованный» чекаут с запросами без `Authorization`. Теперь `setUser` вызывается только вместе с `setTokens`.
4. Мёртвые ветки `if role != "retail"` после раннего `return`, непоследовательное глушение celery-задач, докстринг `test_epic_28_intact.py`, отсутствие теста на отказ `admin`/`unregistered`, устаревший `docs/architecture/18-b2b-verification-workflow.md`, `manual_test_user_management_api.py`.

**KEEP при любых будущих переработках:**
- `role` обязателен в сериализаторе — без этого модельный `default="retail"` обходит запрет.
- `user_roles_view` строит список из `SELF_SERVICE_ROLES`, а не из собственного набора исключений.
- Розничный пользователь в `test_catalog_api.py` создаётся напрямую: покрытие retail-ценообразования должно сохраниться после отключения розничной регистрации.
- `RegisterForm` не редиректит, пока заявка не верифицирована.

Отложено в `deferred-work.md`: сужение `ChoiceField` роли до `SELF_SERVICE_ROLES`, расхождение 3 ролей формы против 6 разрешённых, дублирование `SELF_SERVICE_ROLES`/`B2B_ROLES`, отсутствие фамилии и телефона в заявке, пересечение аудиторий `/register` и `/b2b-register`, отсутствие settings-флага.

## Design Notes

Перевод бэкенд-тестов на B2B требует трёх поправок разом, иначе они падают не по делу:
1. `company_name` и валидный `tax_id` обязательны (10 или 12 цифр для России);
2. ИНН уникален на каждую регистрацию — `_reject_if_tax_id_belongs_to_account` отклонит повтор;
3. B2B-регистрация не выдаёт JWT (`is_verified=False`) и ставит в очередь три celery-задачи — тесты, ожидавшие токены, переписываются на проверку их отсутствия.

```python
def b2b_payload(**overrides):
    return {
        "email": unique_email("consent_b2b"),
        "role": "trainer",
        "company_name": "Клуб Тест",
        "tax_id": unique_inn(),  # 10 цифр, уникальный на вызов
        "country": "Россия",
        **overrides,
    }
```

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest tests/integration/test_auth_registration_consent.py tests/integration/test_auth_registration_tokens.py tests/unit/test_serializers/test_user_serializers.py` -- expected: зелёные
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -m "not performance and not slow"` -- expected: нет регрессий
- `cd frontend && npm run test -- RegisterForm` -- expected: зелёные
- `cd frontend && npx tsc --noEmit` -- expected: без ошибок типов

### Итерация 2 (2026-08-23): отключение сделано обратимым

**Новый факт от Alex:** розница отключена **временно** — в дальнейшем планируется отдельный розничный сайт, работающий с этим же бэкендом. Внешних потребителей `/api/v1/auth/register/`, кроме нашего фронтенда, нет.

Это меняет требование: список ролей саморегистрации больше не должен быть зашит в код, иначе запуск розничного сайта потребует релиза бэкенда.

- Добавлена настройка `REGISTRATION_ALLOW_RETAIL` (default `False`, `backend/freesport/settings/base.py`). Из неё строится единая функция `get_self_service_roles()`, которой пользуются: `choices` поля `role`, серверная проверка `validate_role()` и ответ `GET /api/v1/users/roles/`. Включение розницы — правка окружения и рестарт.
- База списка — `User.B2B_ROLES` (тот же источник истины, что у `is_b2b_user` и admin-действий). Это закрыло отложенную находку про два независимых списка ролей.
- Поле `role` объявлено явным `ChoiceField` с сохранением текста ошибки «Недопустимая роль для регистрации.». В схеме появился `UserRegistrationRoleEnum` ровно из принимаемых ролей — закрыта отложенная находка про контракт, обещавший `admin`/`unregistered`. Побочный эффект генератора: общий `RoleEnum` переименован в `UserProfileRoleEnum` (в ручном коде фронта не использовался).
- Ветки `role == "retail"` в `validate()` и `create()` перестали быть мёртвым кодом — это спящая розничная логика. Покрыты тестами под `override_settings(REGISTRATION_ALLOW_RETAIL=True)`: аккаунт активен и верифицирован, письма менеджеру не ставятся, ИНН отбрасывается. Плюс тест, что состав ролей следует флагу, и тест `/users/roles/` под флагом.

**KEEP:** флаг — единственный переключатель состава ролей; список читается на каждое создание сериализатора (иначе `override_settings` не дошёл бы до поля); `choices` передаются парами из `ROLE_CHOICES`, иначе подписи в схеме вырождаются в «trainer - trainer».

## Suggested Review Order

**Запрет на бэкенде — единственный барьер, который нельзя обойти**

- Единый источник ролей саморегистрации; розница возвращается флагом, без релиза
  [`serializers.py:36`](../../backend/apps/users/serializers.py#L36)

- Настройка, которой переключается канал регистрации
  [`base.py:229`](../../backend/freesport/settings/base.py#L229)

- Явный `ChoiceField`: схема перечисляет ровно то, что принимает сервер
  [`serializers.py:73`](../../backend/apps/users/serializers.py#L73)

- Роль обязательна — иначе модельный `default="retail"` обходит запрет
  [`serializers.py:124`](../../backend/apps/users/serializers.py#L124)

- Публичный список ролей идёт из того же источника
  [`misc.py:48`](../../backend/apps/users/views/misc.py#L48)

**Форма: роль обязательна и не предвыбрана**

- Три B2B-роли, розничной нет
  [`RegisterForm.tsx:55`](../../frontend/src/components/auth/RegisterForm.tsx#L55)

- Плейсхолдер вместо предвыбранной роли — выбор осознанный
  [`RegisterForm.tsx:304`](../../frontend/src/components/auth/RegisterForm.tsx#L304)

- Zod: enum без `retail` и без `.default()`
  [`authSchemas.ts:57`](../../frontend/src/schemas/authSchemas.ts#L57)

**Исход заявки (правки по итогам ревью)**

- Автологина больше нет: pending вместо молчаливого редиректа
  [`RegisterForm.tsx:145`](../../frontend/src/components/auth/RegisterForm.tsx#L145)

- Экран «Заявка на рассмотрении» по образцу B2B-формы
  [`RegisterForm.tsx:205`](../../frontend/src/components/auth/RegisterForm.tsx#L205)

- `user` в store только вместе с токенами: иначе чекаут считает вход состоявшимся
  [`authService.ts:55`](../../frontend/src/services/authService.ts#L55)

**Периферия**

- Контракт пересобран из кода; `role` добавлена в `required`
  [`openapi.yaml:4828`](../../docs/api/openapi.yaml#L4828)

- Тесты формы: отсутствие предвыбора, отказ без роли, экран заявки
  [`RegisterForm.test.tsx:836`](../../frontend/src/components/auth/__tests__/RegisterForm.test.tsx#L836)

- Розничный пользователь заводится напрямую — покрытие retail-цен сохранено
  [`test_catalog_api.py:126`](../../backend/tests/integration/test_catalog_api.py#L126)
