---
title: 'Story 41.11 — раздельные согласия в подписке и канал рассылки при регистрации'
type: 'feature'
created: '2026-09-12'
status: 'done'
baseline_commit: 'c0c89798c8880f8533a740b98b6b3681cf620e02'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/Story/41-11-separate-subscribe-consents.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Формы подписки `/home` и `/electric` берут согласие на ПДн и на рекламную рассылку одним чекбоксом. Статья 9 152-ФЗ (ч. 1, в ред. 156-ФЗ) требует оформлять согласие на ПДн отдельно от согласия на рекламу, которое даётся по ст. 18 38-ФЗ. Кроме того, чекбокс рассылки в формах регистрации не называет канал (FR-41-26).

**Approach:** В подписке — два обязательных чекбокса. У каждого своя поверхность и своя версия в реестре `consent_texts.json`. Контракт `/subscribe/` повторяет имена полей регистрации: `marketing_consent`, `pdp_consent_text_version`, `marketing_consent_text_version`. У текста рассылки в регистрации — новая ревизия, в которой назван канал. Дословные тексты, ожидаемые тела ответов и ловушки лежат в story-файле из `context`; он авторитетен.

## Boundaries & Constraints

**Always:**
- Тексты чекбоксов — дословно из AC1 и AC5 стори, они утверждены Alex.
- Кнопка подписки остаётся `disabled={isSubmitting || !pdpConsent}`. Без галочки рассылки отправку останавливает только правило формы `register('marketing_consent', { validate: v => v === true || … })`, ошибка показывается у этого чекбокса.
- Флаги подписки принимаются только как JSON `true` (`initial_data.get(...) is not True`). Если не прошли оба флага, обе ошибки приходят одним ответом. Версии сверяются только в field-level `validate_<поле>`; все пять ключей `error_messages` у полей версии → `CONSENT_TEXT_OUTDATED`.
- Реестр:
  - существующие ревизии не меняются ни на байт;
  - новая ревизия дописывается последней;
  - три новые ревизии получают одну метку — дату реализации `2026-09-12`;
  - строки `known_versions` берутся из сообщения загрузчика, вручную не вычисляются.
- У чекбоксов `aria-required="true"`, а не `required`. `id` строятся от `React.useId()`. Комментарии — на русском.
- Перед правкой символа — `gitnexus impact`. Прогоны pytest — строго последовательно в одном compose-проекте.

**Ask First:** всё, что выходит за AC10 стори:
- модель, миграции или админка `UserConsent`;
- поведение форм регистрации, кроме текста;
- MSW-хендлер `/subscribe`;
- подвалы и форма входа;
- правка утверждённых текстов.

**Never:**
- Удалять поверхность `newsletter_checkbox` или менять её ревизию — допустима только правка `description`.
- Переименовывать поле модели `UserConsent.consent_text_version`.
- Заменять `consent_text_version` массово.
- Добавлять `!marketingConsent` в `disabled`.
- Перестраивать запись согласий во view или вводить `bulk_create`.
- Вписывать в отслеживаемые файлы плейсхолдеры или непроверенные числа.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Успех | email, оба флага `true`, обе версии действующие | Нейтральный `200`. Две записи `UserConsent` (`pdp_contract`, `marketing_email`) с `source=newsletter`, версии у них разные | — |
| Нет согласия на рассылку | `marketing_consent` отсутствует, либо `false`, `null`, `"true"`, `1`, `"on"` | `400`, ошибка в `marketing_consent`, записей нет | — |
| Оба флага `false` | — | `400`, ошибки `pdp_consent` и `marketing_consent` в одном ответе | — |
| Запрос в формате 41.9 | `{email, pdp_consent, consent_text_version}` | `400 consent_text_outdated`. В `details`: у обоих полей версии — `CONSENT_TEXT_OUTDATED`, ошибка `marketing_consent` сохраняется | Форма идёт в ветку `isConsentTextOutdatedError` |
| Версии перепутаны | Версия ПДн пришла в `marketing_consent_text_version` | `400 consent_text_outdated` по этому полю | — |
| Регистрация с прежней маркетинговой версией | `marketing_consent: true`, `2026-09-09-e2647…` | `400 consent_text_outdated` | — |
| UI: ПДн отмечен, рассылка — нет | Клик «Подписаться» | Запрос не уходит. У чекбокса рассылки `role="alert"`, `aria-invalid`, `aria-describedby`, фокус на нём | Галочка рассылки снимает ошибку |
| UI: ПДн не отмечен | Рассылка в любом состоянии | Кнопка неактивна | — |

</frozen-after-approval>

## Code Map

- `backend/apps/common/consent_texts.json` — реестр: поверхности, ревизии, `known_versions`, привязки.
- `backend/apps/common/consent_texts.py` — загрузчик `load_registry` (`lru_cache`), функции `current_consent_text_version` и `is_current_consent_text_version`.
- `backend/apps/common/serializers.py:18-259` — константы, `CONSENT_TEXT_VERSION_FIELDS`, `SubscribeSerializer`.
- `backend/apps/common/views.py:311-493` — `@extend_schema` и view `subscribe`.
- `backend/apps/common/api_schema.py:86-142` — компоненты ответа `400`.
- `backend/apps/users/serializers.py:82-236` — образец полей версии в регистрации.
- `frontend/src/constants/consentTexts.ts` — `CONSENT_TEXT_VERSIONS` и разбор отказа.
- `frontend/src/components/home/SubscribeForm.tsx`, `ElectricSubscribeForm.tsx` — формы подписки.
- `frontend/src/components/auth/RegisterForm.tsx`, `B2BRegisterForm.tsx` — текст рассылки в регистрации.
- `frontend/src/types/api.ts`, `api.generated.ts` — тип `SubscribeRequest`.
- `frontend/src/__tests__/consent-texts-registry.test.tsx`, `register-request-contract.test.ts` — стражи.

## Tasks & Acceptance

**Execution** (T — номера задач стори):
- [x] `consent_texts.json`:
  - добавить поверхности `newsletter_pdp_checkbox` и `newsletter_marketing_checkbox`;
  - дописать новую ревизию в `registration_marketing_checkbox`;
  - перепривязать `newsletter.*` на новые поверхности;
  - обновить `description` у двух поверхностей;
  - добавить три версии в `known_versions` (T1).
- [x] `serializers.py`:
  - константа `MARKETING_CONSENT_REQUIRED` и поле `marketing_consent`;
  - два поля версии с общим модульным словарём `error_messages` и два валидатора;
  - в `validate()` ошибки флагов копятся и поднимаются вместе;
  - `create()` снимает новые поля;
  - убрать `consent_text_version` из `CONSENT_TEXT_VERSION_FIELDS` (T2).
- [x] `views.py`, `api_schema.py`: комментарий во view; пример запроса с действующими версиями литералами; описание и примеры ответа `400`; `help_text` (T3).
- [x] Backend-тесты: `tests/consent_versions.py`, `tests/integration/test_common_subscribe_api.py`, `apps/common/tests/test_consent_texts.py`, `test_api_schema.py`, `tests/integration/test_auth_registration_consent.py`. Покрыть I/O-матрицу и T4 (T4).
- [x] Контракт: перегенерировать `docs/api/openapi.yaml` и `api.generated.ts`, поправить ручной `api.ts`, добавить страж `__tests__/subscribe-request-contract.test.ts` (T5). Ручной `SubscribeRequest` правился после подтверждения Alex: `gitnexus impact` показал CRITICAL, но это артефакт — все 120 рёбер являются импортами файла `types/api.ts`, а интерфейс использует только `subscribeService.ts:75`. `tsc --noEmit` чистый.
- [x] `frontend/src/services/subscribeService.ts`: POST идёт на `'/subscribe/'` со слэшем, тест URL в `subscribeService.test.ts`. Решение Alex (a), 2026-09-12: без слэша Django `APPEND_SLASH` отвечает 500 при `DEBUG` и 301 на GET при `DEBUG=False`. MSW-хендлер не тронут (Ask First), расхождение путей записано в `deferred-work.md`.
- [x] `consentTexts.ts`: константы `newsletterPdp` и `newsletterMarketing`, новая `registrationMarketing`; убрать `'consent_text_version'` (T6).
- [x] `SubscribeForm.tsx`, `ElectricSubscribeForm.tsx`:
  - второй чекбокс;
  - у чекбокса ПДн `aria-labelledby` = префикс + ссылка;
  - в electric — локальный компонент чекбокса;
  - payload из пяти полей;
  - серверная ошибка `marketing_consent` ложится на чекбокс рассылки (T7, T8).
- [x] `RegisterForm.tsx`, `B2BRegisterForm.tsx`: только текст (T9).
- [x] Фронт-тесты: страж реестра, тесты обеих форм подписки, `subscribeService.test.ts`, тесты регистрации; RED/GREEN-проверка стража (T10).
- [x] Документация: `docs/architecture/11-security-performance.md`, `18-b2b-verification-workflow.md`, `index.md`; пометка в `deferred-work.md:923` (T11).
- [x] Story-файл: Dev Agent Record (Debug Log, File List по `git diff`), статус; `sprint-status.yaml`.

**Acceptance Criteria:**
- Given обновлённый реестр, when отрабатывают загрузчик и страж фронта, then все шесть чекбоксов четырёх форм совпадают с реестром, а исторические версии `2026-08-30-77dbc…` и `2026-09-09-e2647…` разрешаются каждая в свой текст.
- Given изменённый контракт, when запускается `check_openapi_sync`, then он отвечает «Контракт синхронен с кодом», а тест закрепляет, что в примере `/subscribe/` стоят действующие версии.
- Given новые чекбоксы, when axe проверяет начальное состояние и состояние после неудачной отправки, then нарушений нет; при двух экземплярах формы `id` уникальны.
- Given готовый код, when выполнены полные прогоны backend и frontend и линтеры, then всё зелёное; числа «до/после» записаны в Debug Log стори; `detect-changes` показывает только ожидаемые символы.
- Given локальный стенд, when аноним в приватном окне открывает `/home`, `/electric`, `/register` и `/b2b-register`, then поведение из AC9 стори подтверждается, а в админке появляются две записи с разными версиями.

## Spec Change Log

- **2026-09-12, шаг 3, решение Alex.**
  - **Повод.** При реализации правило `required` у чекбокса рассылки ломало отправку. В `react-hook-form` 7.62.0 оно проверяется через `getCheckboxValue`: галочка засчитывается только при `checked && !disabled`, то есть по DOM. `handleSubmit` выставляет `isSubmitting` до проверки полей, и `disabled={isSubmitting}` делал отмеченный чекбокс «пустым».
  - **Что изменено.** В строке Always о кнопке `register('marketing_consent', { required })` заменено на правило формы `{ validate: v => v === true || … }`.
  - **Чего избегаем.** Отмеченная рассылка давала ошибку, и подписка не отправлялась.
  - **KEEP.** Кнопка — `disabled={isSubmitting || !pdpConsent}`. Ошибка, `role="alert"` и фокус — у чекбокса рассылки. У ПДн `required` не трогать.

## Design Notes

Имена полей контракта совпадают с регистрацией, поэтому `consent_text_outdated_payload()` и `getConsentTextOutdatedMessage()` менять не нужно. Попросить обновить страницу этот ответ сможет только у бандла со слэшем в URL. Бандл 41.9 шлёт POST на `/subscribe` без слэша: при `DEBUG=False` он получает 301, затем GET и 405, до сверки версии запрос не доходит, и форма показывает «Не удалось подписаться». Так было и до выката — слэш исправлен в этой стори.

Текст ПДн подписки дословно равен тексту ПДн регистрации. Поверхность у него всё равно своя, но метка ревизии обязана отличаться от `2026-09-09`: иначе версии совпадут, и загрузчик отклонит дубль.

## Verification

**Commands** (backend — из `docker/`):
- `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest` — все тесты зелёные, числа «до/после» записаны.
- `flake8`, `black --check`, `mypy` на изменённых Python-файлах в проекте `freesport-lint`, не одновременно с pytest — чисто, дельта mypy 0.
- `check_openapi_sync` (рецепт — в стори) — «Контракт синхронен с кодом».
- Из `frontend/`: `npm run test -- --run`, `npx tsc --noEmit`, `npx eslint <files>`, `npx prettier --check <files>` — чисто.
- `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` — только ожидаемые символы.

**Manual checks:**
- Приёмка анонимом по AC9 стори. Если браузерных инструментов нет — временный Playwright-спек, в коммит не входит.

## Suggested Review Order

**Реестр: две поверхности подписки и новая ревизия регистрации**

- С чего начать. Отдельная поверхность ПДн подписки; метка `2026-09-12` не даёт её версии совпасть с версией регистрации.
  [`consent_texts.json:12`](../../backend/apps/common/consent_texts.json#L12)

- Привязки `newsletter.*` переведены на новые поверхности, у `newsletter_checkbox` привязок не осталось.
  [`consent_texts.json:62`](../../backend/apps/common/consent_texts.json#L62)

**Сервер: строгие флаги и две версии**

- Каждое поле версии сверяется со своей привязкой реестра: перепутанные версии отклоняются.
  [`serializers.py:194`](../../backend/apps/common/serializers.py#L194)

- Флаг принимается только как JSON `true`, проверка на уровне поля, все ошибки — одним ответом.
  [`serializers.py:216`](../../backend/apps/common/serializers.py#L216)

- Флаг рассылки обязателен, сообщения об ошибке — как у ПДн.
  [`serializers.py:155`](../../backend/apps/common/serializers.py#L155)

- `consent_text_version` запроса подписки убрано из полей версии.
  [`serializers.py:44`](../../backend/apps/common/serializers.py#L44)

- Пример запроса в схеме — пять полей, версии действующие.
  [`views.py:331`](../../backend/apps/common/views.py#L331)

- В `help_text` ответа `400` перечислены два поля версии.
  [`api_schema.py:102`](../../backend/apps/common/api_schema.py#L102)

**Формы подписки**

- Порядок `register`: ПДн первым, потому что `required` читает DOM; email раньше рассылки, чтобы фокус шёл сверху.
  [`SubscribeForm.tsx:121`](../../frontend/src/components/home/SubscribeForm.tsx#L121)

- Рассылка проверяется правилом `validate` по значению формы, кнопку не блокирует.
  [`SubscribeForm.tsx:145`](../../frontend/src/components/home/SubscribeForm.tsx#L145)

- Payload несёт две версии из константы бандла.
  [`SubscribeForm.tsx:163`](../../frontend/src/components/home/SubscribeForm.tsx#L163)

- `aria-required` вместо `required`: нативная валидация не перехватывает отправку.
  [`SubscribeForm.tsx:221`](../../frontend/src/components/home/SubscribeForm.tsx#L221)

- В electric — локальный компонент чекбокса в стиле темы.
  [`ElectricSubscribeForm.tsx:96`](../../frontend/src/components/home/ElectricSubscribeForm.tsx#L96)

- Порядок регистрации полей тот же, что в синей форме.
  [`ElectricSubscribeForm.tsx:205`](../../frontend/src/components/home/ElectricSubscribeForm.tsx#L205)

**Клиентский контракт**

- Слэш в URL: без него Django не пропускал POST, и подписка не работала.
  [`subscribeService.ts:79`](../../frontend/src/services/subscribeService.ts#L79)

- Ручной тип: четыре обязательных поля согласий, как в сгенерированном.
  [`api.ts:235`](../../frontend/src/types/api.ts#L235)

- Отдельные версии бандла для двух чекбоксов подписки.
  [`consentTexts.ts:26`](../../frontend/src/constants/consentTexts.ts#L26)

**Регистрация: канал назван**

- Изменён только текст рассылки, поведение формы прежнее.
  [`RegisterForm.tsx:498`](../../frontend/src/components/auth/RegisterForm.tsx#L498)

- Та же формулировка в форме B2B.
  [`B2BRegisterForm.tsx:547`](../../frontend/src/components/auth/B2BRegisterForm.tsx#L547)

**Тесты и документация**

- Запрос формата 41.9 получает `consent_text_outdated` с ошибками обеих версий.
  [`test_common_subscribe_api.py:400`](../../backend/tests/integration/test_common_subscribe_api.py#L400)

- Ошибки флагов с разных уровней проверки приходят одним ответом.
  [`test_common_subscribe_api.py:376`](../../backend/tests/integration/test_common_subscribe_api.py#L376)

- Без рассылки отправка останавливается, ошибка и фокус — на её чекбоксе.
  [`SubscribeForm.test.tsx:198`](../../frontend/src/components/home/__tests__/SubscribeForm.test.tsx#L198)

- Если ошибок две, фокус получает email.
  [`SubscribeForm.test.tsx:237`](../../frontend/src/components/home/__tests__/SubscribeForm.test.tsx#L237)

- Компиляционный страж ручного и сгенерированного типов.
  [`subscribe-request-contract.test.ts:12`](../../frontend/src/__tests__/subscribe-request-contract.test.ts#L12)

- Страж реестра: шесть чекбоксов, исторические версии.
  [`consent-texts-registry.test.tsx:51`](../../frontend/src/__tests__/consent-texts-registry.test.tsx#L51)

- Тест фиксирует в примере схемы действующие версии.
  [`test_api_schema.py:22`](../../backend/apps/common/tests/test_api_schema.py#L22)

- Документ архитектуры: подписка требует две версии текста.
  [`11-security-performance.md:988`](../../docs/architecture/11-security-performance.md#L988)
