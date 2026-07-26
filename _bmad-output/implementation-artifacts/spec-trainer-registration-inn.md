---
title: 'Обязательный ИНН при регистрации роли «Тренер / Спортивный клуб»'
type: 'bugfix'
created: '2026-07-26'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'bbac5a63'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** При регистрации с типом аккаунта «Тренер / Спортивный клуб» (`role: trainer`) форма не показывает поле ИНН, а бэкенд его не требует. В результате `CustomerIdentityResolver.identify_customer()` вызывается с `tax_id=None`, поиск существующего клиента по ИНН (приоритет 3) не отрабатывает, и вместо привязки к записи из 1С создаётся дубль пользователя. Дополнительно ломается маршрутизация заявки на регионального менеджера по коду субъекта РФ (первые 2 цифры ИНН).

**Approach:** Включить `trainer` в правило обязательного ИНН на всех трёх уровнях (React-форма, Zod-схема, DRF-сериализатор) — так, чтобы правило распространялось на все B2B-роли (`role != retail`), и добавить проверку формата ИНН (10 или 12 цифр) на клиенте и сервере, чтобы в резолвер не попадало значение, которое `normalize_inn()` отбросит.

## Boundaries & Constraints

**Always:**
- Правило формулируется как «все B2B-роли» (`role != 'retail'`), а не перечислением ролей — иначе баг повторится при добавлении новой роли.
- Формат ИНН: только цифры, длина 10 (юр. лицо) или 12 (ИП / физлицо) — согласованно с `CustomerIdentityResolver.normalize_inn()` и `validateINN()`.
- Серверная валидация обязательна и самодостаточна: клиентская проверка её не заменяет.
- Существующая логика привязки к 1С (`_link_matched_1c_customer`, «1C wins», нейтральный ответ без PII) не меняется.

**Ask First:**
- Любая миграция или backfill ИНН для уже зарегистрированных тренеров без ИНН.
- Изменение поведения `B2BRegisterForm` (отдельный B2B-поток `/b2b-register`) — в текущий скоуп не входит.

**Never:**
- Не менять модель `User`, не добавлять миграции.
- Не вводить контрольную сумму ИНН (алгоритм контрольных разрядов) — MVP-проверка только формат/длина.
- Не трогать `resolve_manager_recipients()` — она заработает корректно сама, получив ИНН.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Форма: выбран trainer | `role = trainer` в селекторе «Тип аккаунта» | Рендерятся поля «Название компании», «ИНН» (required, helper «10 цифр для юр. лица или 12 цифр для ИП»), «Страна» | N/A |
| Форма: retail | `role = retail` | Поле ИНН не рендерится | N/A |
| Zod: trainer без ИНН | `{role: 'trainer', tax_id: ''}` | Схема отклоняет | Ошибка на поле `tax_id`: «ИНН обязателен для B2B регистрации» |
| Zod: trainer с ИНН неверной длины | `{role: 'trainer', tax_id: '12345'}` | Схема отклоняет | Ошибка на `tax_id`: «ИНН должен содержать 10 цифр (юр. лицо) или 12 цифр (ИП)» |
| API: trainer без ИНН | POST `/api/v1/auth/register/` `{role: 'trainer', company_name: 'Клуб'}` | 400, пользователь не создан | `{"tax_id": ["ИНН обязателен для B2B пользователей."]}` |
| API: trainer с нечисловым ИНН | `{role: 'trainer', tax_id: 'abc1234567'}` | 400 | `{"tax_id": ["ИНН должен содержать 10 или 12 цифр."]}` |
| API: trainer совпал с 1С-записью по ИНН | В БД `User(role='trainer', created_in_1c=True, verification_status='unverified', tax_id=X)`; регистрация с тем же email и `tax_id=X` | 201, дубль не создан, найденной записи выставлен пароль и `verification_status='pending'` | N/A |
| API: ИНН уже занят порталом | Верифицированная запись с `tax_id=X` | 400 | `{"tax_id": ["Компания с данным ИНН уже зарегистрирована."]}` |
| API: retail без ИНН | `{role: 'retail'}` | 201, регистрация проходит как раньше | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/auth/RegisterForm.tsx:175` — `requiresTaxId` перечисляет только `wholesale_level1 | federation_rep`; управляет рендером поля ИНН (строка 255).
- `frontend/src/schemas/authSchemas.ts:81-96` — `registerSchema.refine` для `tax_id` с тем же неполным перечнем ролей.
- `frontend/src/utils/validators/b2b-validators.ts:20` — `validateINN()`, готовая проверка 10/12 цифр (уже используется в `b2bRegisterSchema`).
- `backend/apps/users/serializers.py:95-100` — `UserRegistrationSerializer.validate()`, условие `role.startswith("wholesale") or role == "federation_rep"`.
- `backend/apps/users/serializers.py:102-105` — вызов `CustomerIdentityResolver.identify_customer()` с `attrs.get("tax_id")`.
- `backend/apps/users/serializers.py:315-321` — `UserProfileSerializer.validate_tax_id()`, эталон проверки формата ИНН для переиспользования.
- `backend/apps/users/services/identity_resolution.py:57-64,107-128` — приоритет 3 (поиск по ИНН) и `normalize_inn()`.
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx:861-863,937-985` — тесты, закрепляющие текущее (ошибочное) поведение для trainer; подлежат обновлению.
- `backend/tests/integration/test_registration_emails.py:25-55` и `backend/tests/regression/test_epic_28_intact.py:104-129` — регистрируют trainer без ИНН, после фикса вернут 400.
- `backend/tests/integration/test_portal_registration_1c_link.py` — хелперы `b2b_registration_payload` / `create_1c_customer` для нового теста матча тренера.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/auth/RegisterForm.tsx` -- заменить `requiresTaxId` на условие «все B2B-роли» (переиспользовать `isB2BRole`) -- поле ИНН должно появляться для trainer.
- [x] `frontend/src/schemas/authSchemas.ts` -- в `registerSchema` переписать refine для `tax_id`: для `role !== 'retail'` требовать непустое значение и проходить `validateINN` -- согласовать с серверным правилом и форматом резолвера.
- [x] `backend/apps/users/serializers.py` -- в `UserRegistrationSerializer` требовать `tax_id` для всех ролей `!= 'retail'` (внутри существующей ветки B2B) и добавить `validate_tax_id()` с проверкой 10/12 цифр по образцу `UserProfileSerializer` -- закрыть обход клиентской валидации.
- [x] `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` -- обновить тест видимости ИНН (trainer → поле видно) и тест сабмита trainer (заполнять ИНН, ожидать `tax_id` в payload); добавлен тест блокировки сабмита без ИНН.
- [x] `frontend/src/schemas/__tests__/authSchemas.test.ts` -- добавить кейсы Zod-матрицы: trainer без ИНН, trainer с коротким ИНН, trainer с валидным 12-значным ИНН.
- [x] `backend/tests/integration/test_registration_emails.py`, `backend/tests/regression/test_epic_28_intact.py` -- добавить `tax_id` в payload регистрации trainer -- тесты проверяют email/flow, а не правило ИНН. Дополнительно потребовалось то же в `tests/integration/test_verification_workflow.py` и `tests/unit/test_user_verification.py`.
- [x] `backend/tests/integration/test_portal_registration_1c_link.py` -- добавить тесты API-строк матрицы: trainer без ИНН → 400; trainer с ИНН, совпавший с 1С-записью (`role='trainer'`) → 201 без дубля; плюс кейс нечислового ИНН.

**Acceptance Criteria:**
- Given форма регистрации, when пользователь выбирает «Тренер / Спортивный клуб», then поле ИНН отображается как обязательное наравне с «Название компании» и «Страна».
- Given запрос регистрации в обход UI с `role='trainer'` и без `tax_id`, when он приходит на `/api/v1/auth/register/`, then API отвечает 400 и пользователь не создаётся.
- Given импортированный из 1С тренер с ИНН X и `verification_status='unverified'`, when тренер регистрируется с тем же ИНН, then срабатывает существующая привязка к 1С-записи, а новый `User` не создаётся.
- Given регистрация тренера с ИНН, when ставится задача `send_manager_region_email`, then в `resolve_manager_recipients()` передаётся непустой `tax_id` (маршрутизация по коду субъекта РФ работает).
- Given роль `retail`, when пользователь регистрируется, then поведение не изменилось: поля ИНН нет, регистрация проходит.

## Spec Change Log

- **2026-07-26, после adversarial-ревью (Blind Hunter + Edge Case Hunter).**
  - *Триггер:* маска «10 или 12 цифр» закрывала регистрацию для клиентов из Беларуси (УНП — 9 цифр), хотя форма предлагает страны Россия/Беларусь/Казахстан. Исходная формулировка ограничения в `Boundaries` не рассматривала зарубежных B2B.
  - *Решение человека (Alex):* маска 10/12 применяется только при `country = Россия`; для Беларуси и Казахстана — обязательное поле, 8–12 цифр. Проверка длины перенесена из field-level валидатора в `validate()`, где доступна страна; field-level валидатор теперь только нормализует значение (оставляет ASCII-цифры).
  - *Известное плохое состояние, которого избегаем:* полная блокировка регистрации белорусских B2B — регрессия относительно поведения до правки.
  - *Второй вопрос:* конфликт «два тренера одного клуба с одним ИНН». Решение человека — оставить действующее правило «один ИНН = один аккаунт»; изменена только подсказка под полем.
  - *KEEP:* формулировка правила через «все B2B-роли» (`role !== 'retail'`), а не перечень ролей; обязательность и самодостаточность серверной валидации; неизменность логики привязки к 1С.
  - *Патчи из ревью:* нормализация ИНН с разделителями (` 770 123 4567 ` → `7701234567`); `tax_id` не отправляется с фронта и обнуляется на сервере для `retail` (иначе значение, оставшееся после переключения роли, матчило заявку на чужое юрлицо из 1С); формат проверяется в Zod с учётом страны; усилены ассерты теста привязки 1С («1C wins», общее число пользователей).
  - *Отложено (см. `deferred-work.md`):* отсутствие unique-констрейнта на `tax_id` (риск `MultipleObjectsReturned` → 500 и гонка при одновременной регистрации), смена ИНН в профиле без проверки дублей, дублирование валидатора ИНН в трёх сериализаторах.

## Design Notes

Правило записывается через уже существующий флаг B2B, а не новым перечнем ролей:

```tsx
// RegisterForm.tsx
const isB2BRole = selectedRole !== 'retail';
// ИНН нужен всем B2B-ролям: без него не работает поиск клиента в 1С
const requiresTaxId = isB2BRole;
```

На бэкенде проверка формата выносится в field-level валидатор (`validate_tax_id`), выполняющийся до `validate()`, поэтому в `identify_customer()` заведомо попадает либо пусто (retail), либо строка из 10/12 цифр — то есть значение, которое `normalize_inn()` не отбросит.

Побочный эффект, принятый намеренно: `wholesale_*` и `federation_rep` в `registerSchema` тоже начинают проверяться на формат ИНН (сейчас — только на непустоту), что устраняет расхождение с `b2bRegisterSchema`.

## Verification

**Commands:**
- `cd frontend && npm run test -- src/components/auth/__tests__/RegisterForm.test.tsx src/schemas/__tests__/authSchemas.test.ts` -- expected: все тесты зелёные.
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec backend pytest -q tests/integration/test_portal_registration_1c_link.py tests/integration/test_registration_emails.py tests/regression/test_epic_28_intact.py` -- expected: 0 failed.
- `cd backend && black apps/users/serializers.py tests/ && flake8 apps/users/serializers.py` -- expected: без ошибок.

**Manual checks:**
- Форма `/register`: выбрать «Тренер / Спортивный клуб» → поля «Название компании», «ИНН», «Страна» обязательны; при выборе Беларуси подсказка под ИНН меняется на «от 8 до 12 цифр».

## Suggested Review Order

**Серверное правило (источник истины)**

- Точка входа: правило «ИНН нужен всем B2B-ролям» и маска по стране
  [`serializers.py:118`](../../backend/apps/users/serializers.py#L118)

- Обнуление ИНН для retail — закрывает привязку розничной заявки к чужому юрлицу
  [`serializers.py:103`](../../backend/apps/users/serializers.py#L103)

- Field-level нормализация: разделители убираются до поиска в 1С
  [`serializers.py:78`](../../backend/apps/users/serializers.py#L78)

**Клиентская валидация**

- Обязательность ИНН для всех B2B-ролей
  [`authSchemas.ts:85`](../../frontend/src/schemas/authSchemas.ts#L85)

- Формат: маска РФ только для России, иначе 8–12 цифр
  [`authSchemas.ts:103`](../../frontend/src/schemas/authSchemas.ts#L103)

**UI-привязка**

- Условие рендера поля ИНН сведено к признаку B2B
  [`RegisterForm.tsx:181`](../../frontend/src/components/auth/RegisterForm.tsx#L181)

- Payload: ИНН не отправляется для retail
  [`RegisterForm.tsx:124`](../../frontend/src/components/auth/RegisterForm.tsx#L124)

- Подсказка под полем зависит от страны и фиксирует правило «один ИНН — один аккаунт»
  [`RegisterForm.tsx:185`](../../frontend/src/components/auth/RegisterForm.tsx#L185)

**Тесты и документация**

- Матрица API: без ИНН → 400, матч с 1С-записью тренера → 201 без дубля, Беларусь → 9 цифр
  [`test_portal_registration_1c_link.py:312`](../../backend/tests/integration/test_portal_registration_1c_link.py#L312)

- UI: поле видно для всех B2B-ролей, сабмит без ИНН заблокирован, ИНН не утекает в retail-заявку
  [`RegisterForm.test.tsx:843`](../../frontend/src/components/auth/__tests__/RegisterForm.test.tsx#L843)

- Zod-кейсы по ролям и странам
  [`authSchemas.test.ts:295`](../../frontend/src/schemas/__tests__/authSchemas.test.ts#L295)

- Архитектурный документ приведён в соответствие коду
  [`18-b2b-verification-workflow.md:65`](../../docs/architecture/18-b2b-verification-workflow.md#L65)
