# Story 41.11: Раздельные согласия в подписке и канал рассылки при регистрации

Status: review

> Заведена 2026-09-10 по повторному аудиту (`sprint-change-proposal-2026-09-10.md`, п. 4.3). Отменяет решение редакции 2 стори 41.3 («один чекбокс на ПДн и рассылку»).
> Координаты кода проверены на `c0c89798` (2026-09-12, `develop`). Индекс GitNexus — свежий, на том же коммите.

## Story

As a подписчик и регистрирующийся пользователь,
I want давать согласие на обработку данных и согласие на письма раздельно и знать, по какому каналу придут письма,
so that каждое согласие было конкретным, отдельным и доказуемым, как требуют 152-ФЗ и 38-ФЗ.

**Закрывает:** FR-41-05 (редакция 3), FR-41-26. Попутно — чекбоксная часть отложенного пункта ревью 41.3 про `aria-required` (`deferred-work.md:923`).

**Правовое основание (из SCP, одобрено Alex 2026-09-10):** ст. 9 ч. 1 152-ФЗ в ред. 156-ФЗ (действует с 01.09.2025) требует оформлять согласие на обработку ПДн отдельно от иных документов, которые подтверждает субъект. Согласие на рекламу по ст. 18 38-ФЗ — такой документ. Оба чекбокса подписки обязательны (решение Alex, 2026-09-10): подписки без согласия на письма не бывает.

## Acceptance Criteria

### AC1 (FR-41-05 ред. 3) — два отдельных чекбокса в формах подписки

**Given** формы подписки `SubscribeForm` (`/home`) и `ElectricSubscribeForm` (`/electric`)
**When** они отображаются
**Then** в каждой два неотмеченных чекбокса с дословными текстами:
- ПДн: `Я даю согласие на обработку моих персональных данных в соответствии с «Политикой обработки персональных данных»`, где «Политикой…» — ссылка на `/privacy-policy` (`target="_blank"`, `rel="noopener noreferrer"`, вне `<label>`);
- рассылка: `Я согласен(на) получать информационные и рекламные рассылки от OPTISPORT по электронной почте`.

**And** тексты не пересекаются: в доступном имени чекбокса ПДн нет слова «рассыл», а в доступном имени чекбокса рассылки нет «персональн» и «обработк».
**And** тексты в обеих формах совпадают посимвольно.

### AC2 (FR-41-05 ред. 3) — оба согласия обязательны

**Given** не отмечен чекбокс ПДн
**When** форма отображается
**Then** кнопка «Подписаться» неактивна — правило `disabled={isSubmitting || !pdpConsent}` прежнее (решение Alex, 2026-09-12). Состояние чекбокса рассылки на активность кнопки **не влияет**.

**Given** чекбокс ПДн отмечен, чекбокс рассылки — нет
**When** пользователь нажимает «Подписаться»
**Then** запрос не отправляется. Под чекбоксом рассылки — сообщение (`role="alert"`), у самого чекбокса `aria-invalid="true"` и `aria-describedby` на это сообщение, фокус переходит на него.
**And** после установки галочки рассылки ошибка снимается и отправка проходит.

**Given** клиентская проверка обойдена
**When** запрос приходит на сервер
**Then** сервер отвечает `400` плоским объектом с ошибкой в поле `pdp_consent` и/или `marketing_consent`. Принимается только JSON `true`: `false`, `null`, `"true"`, `1`, `"on"` и отсутствие поля отклоняются.
**And** ни `Newsletter`, ни записи `UserConsent` не создаются.
**And** если не отмечены оба чекбокса, ответ содержит обе ошибки сразу, а не по одной.

### AC3 (FR-41-05 ред. 3, NFR-41-04) — две записи, у каждой своя версия

**Given** успешная подписка (оба согласия и обе версии действующие)
**When** запрос обработан
**Then** создаются две записи `UserConsent`: `pdp_contract` и `marketing_email`, у обеих `source="newsletter"`.
**And** у `pdp_contract` версия равна `current_consent_text_version("newsletter", "pdp_contract")`, у `marketing_email` — `current_consent_text_version("newsletter", "marketing_email")`, и эти версии **различаются**.
**And** прочее поведение подписки — нейтральный `200` (enumeration), запись согласия активного подписчика, гонка на уникальном email, `503 consent_persistence_failed` — не изменилось.

### AC4 — прежний формат запроса отклоняется как устаревшая форма

**Given** запрос в формате 41.9: `{email, pdp_consent: true, consent_text_version}` без новых полей
**When** он приходит на обновлённый сервер
**Then** ответ `400` с `error: "consent_text_outdated"`. В `details` у `pdp_consent_text_version` и `marketing_consent_text_version` — `CONSENT_TEXT_OUTDATED`, а попутная ошибка `marketing_consent` сохраняется.
**And** записи не создаются.
**And** форма в ответ на `consent_text_outdated` показывает требование обновить страницу — через уже существующую ветку `isConsentTextOutdatedError`.

**Given** запрос, где версия одного чекбокса подставлена в поле другого (например, `marketing_consent_text_version` = действующая версия ПДн)
**When** он приходит на сервер
**Then** ответ `400 consent_text_outdated` по этому полю: каждое поле сверяется со своей привязкой реестра.

### AC5 (FR-41-26) — канал рассылки в формах регистрации

**Given** формы `RegisterForm` (`/register`) и `B2BRegisterForm` (`/b2b-register`)
**When** они отображаются
**Then** текст необязательного чекбокса рассылки: `Я согласен(на) получать рекламные и информационные рассылки от OPTISPORT по электронной почте` — канал назван, «согласен(на)» без пробела.
**And** формулировка одна в обеих формах. У поверхности `registration_marketing_checkbox` — новая ревизия, `CONSENT_TEXT_VERSIONS.registrationMarketing` указывает на неё.
**And** чекбокс остаётся необязательным, кнопка регистрации — прежней, текст ПДн регистрации не меняется.
**And** регистрация с `marketing_consent: true` и **прежней** маркетинговой версией (`2026-09-09-e26471e47eba2ba742a4f4488dfdda05`) получает `400 consent_text_outdated`.

### AC6 — реестр, история версий, контракт

**Given** формулировки изменены
**When** прогоняются тесты
**Then** страж `frontend/src/__tests__/consent-texts-registry.test.tsx` зелёный и сверяет с реестром все **шесть** чекбоксов четырёх форм.
**And** прежние версии остаются в `known_versions` и разрешаются в свой текст: `2026-08-30-77dbceafc3c487ffc24975cf2ce76778` (объединённый чекбокс подписки) и `2026-09-09-e26471e47eba2ba742a4f4488dfdda05` (маркетинг регистрации без канала).
**And** `docs/api/openapi.yaml` перегенерирован. `check_openapi_sync` отвечает «Контракт синхронен с кодом», `npm run generate:types` выполнен, ручной `SubscribeRequest` в `types/api.ts` совпадает с контрактом (NFR-41-02).
**And** пример запроса подписки в схеме содержит **действующие** версии — это закреплено тестом.

### AC7 (NFR-41-06) — доступность

**Given** новые чекбоксы подписки
**When** проверяется доступность
**Then** каждый достижим с клавиатуры (Tab) и переключается пробелом.
**And** доступное имя каждого чекбокса содержит весь его текст.
**And** у каждого `aria-required="true"`: не `required` — нативная валидация перехватила бы отправку до `react-hook-form`.
**And** ошибки связаны через `aria-describedby`.
**And** `axe` нарушений не находит — в начальном состоянии и в состоянии с ошибками.
**And** `id` уникальны при двух экземплярах формы на странице (`React.useId()`).

### AC8 (NFR-41-01) — тесты и статический анализ

**Given** изменения готовы
**When** выполняются проверки
**Then** полный backend-прогон и полный frontend-прогон зелёные, числа «до/после» записаны в Debug Log.
**And** `flake8` и `black --check` на изменённых Python-файлах чисты, дельта `mypy` к базису — 0 (базис 0).
**And** `tsc --noEmit`, `eslint`, `prettier --check` на изменённых TS-файлах чисты.
**And** `npx gitnexus detect-changes --scope all` показывает только ожидаемые символы.

### AC9 (NFR-41-08) — приёмка глазами анонима

**Given** стори готова к приёмке
**When** она проверяется
**Then** `/home` и `/electric` открыты в приватном окне без cookie, пользователь не вошёл.
**And** в каждой форме видны два чекбокса.
**And** проверено: без галочки ПДн кнопка неактивна при любом состоянии галочки рассылки; с галочкой ПДн, но без галочки рассылки отправка не проходит, и ошибка стоит у чекбокса рассылки.
**And** проверено, что подписка с двумя отмеченными проходит и в журнале (админка «Согласия пользователей») появились две записи с **разными** версиями и `source = Подписка на рассылку`.
**And** на `/register` и `/b2b-register` виден новый текст рассылки.
**And** проверка проводилась авторизованным пользователем — приёмкой не считается.

### AC10 — границы: что стори НЕ делает

- Модель `UserConsent`, миграции и админку не трогает — поля `source` и `consent_text_version` появились в 41.9.
- **Поле модели `UserConsent.consent_text_version` не переименовывается и не удаляется.** Из контракта уходит только одноимённое поле **запроса** подписки.
- Логику записи согласий во view (две вставки, общий `consent_kwargs`, `transaction.atomic`) не перестраивает, `bulk_create` не вводит.
- Текст и поведение чекбокса ПДн регистрации, правило `disabled={isSubmitting || !pdpConsentChecked}` форм регистрации и необязательность маркетинга при регистрации не меняет.
- `policy_version`, строгость JSON boolean в регистрации (`deferred-work.md`, запись ревью 41.9), ARIA email-поля `ElectricSubscribeForm` (`deferred-work.md:24`), MSW-хендлер `/subscribe` не трогает.
- Подвалы, форму входа, `aria-label` цепочки и обоснование по форме входа не трогает — это стори 41.12.

## Tasks / Subtasks

- [x] **Task 1 — реестр текстов согласий** (AC1, AC3, AC5, AC6) — `backend/apps/common/consent_texts.json`
  - [x] 1.1 Поверхность `newsletter_checkbox` **оставить** с её единственной ревизией `2026-08-30`. Текст не трогать ни на символ — иначе загрузчик упадёт на `known_versions`. Обновить только `description`: «Исторический объединённый чекбокс подписки (редакция 2 стори 41.3), заменён двумя чекбоксами в стори 41.11. Привязок нет; хранится, чтобы записи журнала с этой версией разрешались в свой текст.» `description` в версию не входит.
  - [x] 1.2 Добавить поверхность `newsletter_pdp_checkbox`: ревизия с текстом ПДн из AC1, `label` = дата реализации `YYYY-MM-DD`. **Не `2026-09-09`**: текст дословно равен ревизии `registration_pdp_checkbox`, и при той же метке версии совпадут — загрузчик отклонит дубль (`consent_texts.py:172-176`).
  - [x] 1.3 Добавить поверхность `newsletter_marketing_checkbox`: ревизия с текстом рассылки подписки из AC1, та же метка.
  - [x] 1.4 В `registration_marketing_checkbox.revisions` **дописать последней** ревизию с текстом из AC5, метка — та же дата. Прежнюю ревизию не менять и не удалять.
  - [x] 1.5 Перепривязать: `"newsletter.pdp_contract": "newsletter_pdp_checkbox"`, `"newsletter.marketing_email": "newsletter_marketing_checkbox"`. Остальные четыре привязки не менять: `1c_link.marketing_email` сам начнёт указывать на новую ревизию регистрации.
  - [x] 1.6 Дописать три новые версии в `known_versions`. Вручную не считать: запустить загрузку (`python -c "from apps.common.consent_texts import load_registry; load_registry()"` в контейнере). Сообщение об ошибке назовёт готовые строки — их и внести.
  - [x] 1.7 Обновить `description` у `registration_marketing_checkbox`: упомянуть ревизию 41.11 (канал назван).

- [x] **Task 2 — `SubscribeSerializer`** (AC2, AC3, AC4) — `backend/apps/common/serializers.py`
  - [x] 2.1 Добавить константу `MARKETING_CONSENT_REQUIRED = "Необходимо согласие на получение рассылок по электронной почте."` рядом с `PDP_CONSENT_REQUIRED` (`:18`).
  - [x] 2.2 Добавить поле `marketing_consent = serializers.BooleanField(write_only=True, required=True, error_messages={...})`. Три ключа `required`/`invalid`/`null` → `MARKETING_CONSENT_REQUIRED`, как у `pdp_consent` (`:126-134`).
  - [x] 2.3 Заменить `consent_text_version` (`:140-152`) двумя полями — `pdp_consent_text_version` и `marketing_consent_text_version`. Оба `CharField(write_only=True, required=True, max_length=MAX_VERSION_LENGTH)` с теми же **пятью** ключами `error_messages`: `required`, `blank`, `null`, `invalid`, `max_length`. Все пять → `CONSENT_TEXT_OUTDATED`. Словарь вынести в модульную константу, а не копировать дважды. Обе версии обязательны **безусловно**, в отличие от регистрации: маркетинговое согласие при подписке обязательно.
  - [x] 2.4 Заменить `validate_consent_text_version` (`:164-179`) двумя field-level валидаторами. `validate_pdp_consent_text_version` сверяет с `(SOURCE_NEWSLETTER, "pdp_contract")`, `validate_marketing_consent_text_version` — с `(SOURCE_NEWSLETTER, "marketing_email")`. При несовпадении — `raise consent_text_outdated_error()`. **Не переносить в `validate()`**: при любой field-level ошибке DRF его не вызывает, и машинный код потеряется (урок пятого круга ревью 41.9).
  - [x] 2.5 В `validate()` (`:181-190`) проверять оба флага строго через `self.initial_data.get(...) is not True`. Ошибки копить в один словарь и поднимать одним `ValidationError`, чтобы AC2 «обе ошибки сразу» выполнялся. Проверку `isinstance(self.initial_data, dict)` оставить первой.
  - [x] 2.6 В `create()` (`:198-201`) снимать `marketing_consent`, `pdp_consent_text_version`, `marketing_consent_text_version` вместо `consent_text_version`. Комментарий «версия уже сверена…» привести к двум валидаторам.
  - [x] 2.7 Из `CONSENT_TEXT_VERSION_FIELDS` (`:39-45`) убрать `"consent_text_version"`: после стори это поле не шлёт ни один эндпоинт. Проверить поиском по `backend/`, что это имя больше нигде не значит «поле запроса». Совпадения с полем модели, миграциями `0019`, админкой и документами не трогать.

- [x] **Task 3 — view и описание контракта** (AC3, AC4, AC6) — `backend/apps/common/views.py`, `backend/apps/common/api_schema.py`
  - [x] 3.1 В `subscribe` (`views.py:453-462`) код двух `UserConsent.objects.create` не менять. Обновить только комментарий `:447-452`: чекбоксов теперь два, у каждого своя версия. Прежний комментарий как раз предупреждал об этом расщеплении.
  - [x] 3.2 `@extend_schema` (`:311-404`):
    - [x] пример запроса — пять полей: `email`, `pdp_consent: true`, `marketing_consent: true`, обе версии **действующими литералами** из загрузки реестра;
    - [x] описание `400` — перечислить `marketing_consent` и оба поля версии;
    - [x] пример `marketing_consent_required`;
    - [x] `consent_text_outdated_example("pdp_consent_text_version")` вместо `"consent_text_version"`.
  - [x] 3.3 `api_schema.py:100-105`: в `help_text` поля `details` убрать `consent_text_version` из перечня полей версии.

- [x] **Task 4 — backend-тесты** (AC2–AC6)
  - [x] 4.1 `backend/tests/consent_versions.py`: заменить неиспользуемый `NEWSLETTER_TEXT_VERSION` на `NEWSLETTER_PDP_TEXT_VERSION` и `NEWSLETTER_MARKETING_TEXT_VERSION`.
  - [x] 4.2 `backend/tests/integration/test_common_subscribe_api.py`: локальную константу `:36` заменить импортом из `tests.consent_versions`. Добавить модульный словарь валидных согласий, собирать payload через него. Обновить **все** payload — около 45 мест.
  - [x] 4.3 Там же переписать ожидания:
    - [x] ключ версии в `details` — `pdp_consent_text_version`;
    - [x] в `test_subscribe_creates_two_consent_records_*` и `test_subscribe_duplicate_email` — у каждого типа своя версия, и версии различаются (`:83`, `:503-505`).
  - [x] 4.4 Новые тесты — проверка по `response.json()`, а не `response.data`:
    - [x] `marketing_consent` отсутствует / `false` / `null` → `400` с ошибкой `marketing_consent`, записей нет;
    - [x] параметризованный truthy не-boolean для `marketing_consent`: `"true"`, `1`, `"on"`;
    - [x] оба флага `false` → обе ошибки в одном ответе;
    - [x] прежний формат запроса (AC4) → точное тело `consent_text_outdated`, записей нет;
    - [x] устаревшая только маркетинговая версия → `details.marketing_consent_text_version`;
    - [x] версии перепутаны местами (AC4, вторая часть) → отказ.
  - [x] 4.5 Параметризованные тесты нестроковой версии и версии, отсечённой валидатором (`:390-453`), распространить на оба новых поля.
  - [x] 4.6 `backend/apps/common/tests/test_consent_texts.py`:
    - [x] `test_newsletter_pair_shares_one_surface` (`:101-105`) заменить на `test_newsletter_pdp_and_marketing_have_different_versions` — по образцу `:116-121`;
    - [x] добавить: историческая версия `2026-08-30-77dbc…` разрешается в объединённый текст и есть в `known_versions`; то же для `2026-09-09-e2647…`;
    - [x] добавить: единственная поверхность без привязок — `newsletter_checkbox`. Читать JSON файла, как `test_registry_file_is_valid_json_with_normalized_texts`.
  - [x] 4.7 `backend/apps/common/tests/test_api_schema.py`:
    - [x] `SubscribeRequest.required` == `{email, pdp_consent, marketing_consent, pdp_consent_text_version, marketing_consent_text_version}`, свойства `consent_text_version` нет;
    - [x] версии в примере запроса `/subscribe/` равны `current_consent_text_version(...)`.
  - [x] 4.8 `backend/tests/integration/test_auth_registration_consent.py`: регистрация с `marketing_consent: true` и прежней маркетинговой версией → `400 consent_text_outdated` (AC5). Остальные регистрационные тесты берут версию из `tests.consent_versions` и правки не требуют — убедиться прогоном.

- [x] **Task 5 — контракт и типы** (AC6)
  - [x] 5.1 Перегенерировать `docs/api/openapi.yaml` целиком командой `spectacular --validate` (рецепт — Dev Notes, «Команды»), не править руками.
  - [x] 5.2 `check_openapi_sync` → «Контракт синхронен с кодом».
  - [x] 5.3 `cd frontend; npm run generate:types` — `SubscribeRequest` в `types/api.generated.ts` получил пять полей.
  - [x] 5.4 Ручной `SubscribeRequest` в `frontend/src/types/api.ts:235-240`:
    - [x] поля `pdp_consent: boolean`, `marketing_consent: boolean`, `pdp_consent_text_version: string`, `marketing_consent_text_version: string`;
    - [x] `consent_text_version` удалить;
    - [x] комментарий — про два чекбокса.
  - [x] 5.5 Новый компиляционный страж `frontend/src/__tests__/subscribe-request-contract.test.ts` по образцу `register-request-contract.test.ts`. В **оба** типа (ручной и `Pick` сгенерированного) — `@ts-expect-error` на payload:
    - [x] без `marketing_consent`;
    - [x] без `marketing_consent_text_version`;
    - [x] с лишним `consent_text_version` в объектном литерале (проверка excess property).

- [x] **Task 6 — фронтовые константы** (AC3, AC5) — `frontend/src/constants/consentTexts.ts`
  - [x] 6.1 В `CONSENT_TEXT_VERSIONS` вместо `newsletter` — `newsletterPdp` и `newsletterMarketing` с JSDoc. `registrationMarketing` → новая версия, `registrationPdp` не меняется.
  - [x] 6.2 Из `CONSENT_TEXT_VERSION_FIELDS` (`:58-62`) убрать `'consent_text_version'`. На время выката, если новый бандл встретит старый сервер, запасное `CONSENT_TEXT_OUTDATED_MESSAGE` даёт тот же текст.

- [x] **Task 7 — `SubscribeForm`** (AC1, AC2, AC7) — `frontend/src/components/home/SubscribeForm.tsx`
  - [x] 7.1 В `SubscribeFormData` добавить `marketing_consent: boolean`, в `defaultValues` — `marketing_consent: false`. Константа `MARKETING_CONSENT_REQUIRED` — тот же текст, что на бэкенде.
  - [x] 7.2 Чекбокс ПДн. Суффиксная `<label>` (`:217-220`) удаляется, `aria-labelledby` = префикс + ссылка — ровно как в `RegisterForm.tsx:447`. Удалить неиспользуемый `pdpConsentLabelSuffixId`.
  - [x] 7.3 Второй `Checkbox` для рассылки:
    - [x] свои `id` и `errorId` от того же `React.useId()`;
    - [x] одна `<label htmlFor>` с полным текстом;
    - [x] `register('marketing_consent', { required: MARKETING_CONSENT_REQUIRED })` и `checked={watch('marketing_consent')}` — **реализовано правилом `validate`, а не `required`** (Change Log 1.2–1.3);
    - [x] `aria-invalid`, `aria-describedby`, error-стили и `<p role="alert">` — по образцу чекбокса ПДн.
  - [x] 7.4 Обоим чекбоксам — `aria-required="true"`.
  - [x] 7.5 Кнопка: правило `disabled={isSubmitting || !pdpConsent}` **не меняется**, `marketing_consent` в него **не добавлять** (решение Alex, 2026-09-12). Без галочки рассылки отправку блокирует `handleSubmit` из `react-hook-form` по правилу `required` из 7.3: `onSubmit` не вызывается, ошибка появляется у чекбокса рассылки (AC2). `shouldFocusError` в `useForm` оставить по умолчанию (`true`).
  - [x] 7.6 `onSubmit`:
    - [x] в начале `clearErrors(['pdp_consent', 'marketing_consent'])`;
    - [x] payload — пять полей из AC6 (версии из `CONSENT_TEXT_VERSIONS.newsletterPdp` / `.newsletterMarketing`);
    - [x] в ветке `validation_error` — `getBackendFieldError(error, 'marketing_consent')` → `setError`;
    - [x] приоритет тоста: ПДн → рассылка → email → прочее.
  - [x] 7.7 Ветку `isConsentTextOutdatedError` и хелперы не менять.

- [x] **Task 8 — `ElectricSubscribeForm`** (AC1, AC2, AC7) — `frontend/src/components/home/ElectricSubscribeForm.tsx`
  - [x] 8.1 То же, что Task 7, в стилистике electric: скошенный квадрат `-skew-x-12`, `sr-only peer` input, `uppercase`.
  - [x] 8.2 Разметка чекбокса (`:228-291`) повторяется дважды — вынести её в локальный компонент внутри того же файла, без экспорта. Общий компонент между темами не заводить — стили разные.
  - [x] 8.3 Кнопка `ElectricButton` — правило `disabled={isSubmitting || !pdpConsent}` не меняется, галочка рассылки в него не входит (как в 7.5). Тосты — прежние, `electricToastErrorOptions`, uppercase.

- [x] **Task 9 — формы регистрации** (AC5)
  - [x] 9.1 `RegisterForm.tsx:498` и `B2BRegisterForm.tsx:547` — текст из AC5. Больше ничего в этих файлах не менять.

- [x] **Task 10 — фронтовые тесты** (AC1–AC7)
  - [x] 10.1 `frontend/src/__tests__/consent-texts-registry.test.tsx`:
    - [x] список поверхностей — пять;
    - [x] константы текстов `NEWSLETTER_PDP_TEXT`, `NEWSLETTER_MARKETING_TEXT` берутся из новых поверхностей;
    - [x] обе формы подписки находят **оба** чекбокса по точному имени;
    - [x] `newsletterPdp`, `newsletterMarketing`, `registrationMarketing` сверяются с `currentVersion(...)`;
    - [x] привязки `newsletter.*` указывают на новые поверхности, `newsletter_checkbox` не привязан ни к чему;
    - [x] `known_versions` содержит две исторические версии из AC6 — литералами: это неизменяемая история, литерал здесь уместен.
  - [x] 10.2 `components/home/__tests__/SubscribeForm.test.tsx` и `ElectricSubscribeForm.test.tsx`:
    - [x] константы имён — два текста;
    - [x] `fillEmailAndAcceptConsent` отмечает оба чекбокса;
    - [x] тест «keeps submit disabled until PDN consent is checked» сохранить и дополнить: кнопка неактивна без галочки ПДн и при отмеченной галочке рассылки; галочка рассылки без галочки ПДн кнопку не активирует;
    - [x] новый тест: ПДн отмечен, рассылка нет → клик по кнопке, сервис не вызван, у чекбокса рассылки ошибка (`role="alert"`, `aria-invalid`, `aria-describedby`), фокус на нём; после установки галочки рассылки отправка проходит;
    - [x] AC1: имена не пересекаются;
    - [x] серверная ошибка `marketing_consent` ложится на чекбокс рассылки;
    - [x] payload — пять полей;
    - [x] `reset()` снимает оба чекбокса;
    - [x] уникальность `id` при двух экземплярах — для обоих чекбоксов;
    - [x] `aria-required`;
    - [x] `axe` в начальном состоянии и после неудачной отправки.
  - [x] 10.3 `services/__tests__/subscribeService.test.ts` — payload пяти полей. Тест проброса `consent_text_outdated` оставить.
  - [x] 10.4 `components/auth/__tests__/B2BRegisterForm.test.tsx:16` — новый текст. В `RegisterForm.test.tsx:47-50` регулярка остаётся совпадающей: дописать проверку «по электронной почте» и «согласен(на)».
  - [x] 10.5 **Проверить, что страж ловит расхождение.** Временно изменить один символ текста в `SubscribeForm`, убедиться, что `consent-texts-registry.test.tsx` падает, вернуть, убедиться, что `git diff` по файлу пуст. Результат записать в Debug Log — приём стори 41.3.

- [x] **Task 11 — документация** (AC6)
  - [x] 11.1 `docs/architecture/11-security-performance.md`:
    - [x] раздел «Сбор согласий при подписке — Story 35.3» (`:965-972`) — два обязательных чекбокса, две версии, строгий JSON `true` у обоих флагов;
    - [x] абзац «Клиент присылает показанную версию…» (`:983`) — `/subscribe/` требует `pdp_consent_text_version` и `marketing_consent_text_version` вместо `consent_text_version`;
    - [x] строка `:962` («строгую проверку… делает только подписка») — теперь оба флага подписки;
    - [x] «Соответствие текста форм и реестра…» — шесть чекбоксов вместо «все четыре формы».
  - [x] 11.2 `docs/architecture/18-b2b-verification-workflow.md:142` — в примере payload новая версия маркетинга регистрации.
  - [x] 11.3 `docs/architecture/index.md` — строка истории `Epic 41 / Story 41.11` сверху списка (`:48`): что изменилось, в каких файлах, контракт `SubscribeRequest` изменён.
  - [x] 11.4 `_bmad-output/implementation-artifacts/deferred-work.md:923` — пометить чекбоксную часть закрытой стори 41.11 (`aria-required` в обеих формах подписки). Пункт `:24` (email-поле electric) не трогать.
  - `docs/api/views-documentation.md` подписку не описывает (проверено поиском на `c0c89798`) — правки не требует.

- [x] **Task 12 — проверки** (AC8)
  - [x] 12.1 Полный backend-прогон «до» (на `develop`) и «после», числа — в Debug Log. Прогоны строго последовательно в одном compose-проекте.
  - [x] 12.2 Линтеры backend в отдельном compose-проекте, **не одновременно** с зачётным pytest.
  - [x] 12.3 Frontend: `npm run test` (полный), `npx tsc --noEmit`, `npx eslint` и `npx prettier --check` по изменённым файлам.
  - [x] 12.4 `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"`. Ожидаемые символы: `SubscribeSerializer` и его методы, `subscribe`, `SubscribeForm`, `ElectricSubscribeForm`, `RegisterForm`, `B2BRegisterForm`, тесты. Всё прочее объяснить.
  - [x] 12.5 File List собирать по `git diff --name-status`, а не по памяти.

- [x] **Task 13 — приёмка NFR-41-08** (AC9)
  - [x] 13.1 Локально:
    - [x] `restart frontend`, затем `restart nginx`; backend — рестарт после правки реестра, реестр кэшируется `lru_cache`;
    - [x] приватное окно, `/home` и `/electric`: клавиатурой пройти оба чекбокса; без галочки ПДн кнопка неактивна (в том числе при отмеченной рассылке); с ПДн без рассылки — ошибка у чекбокса рассылки; с двумя — успех;
    - [x] в админке две новые записи с разными версиями.
  - [x] 13.2 `/register` и `/b2b-register` — новый текст рассылки.
  - [x] 13.3 Если браузерных инструментов в сессии нет — временный Playwright-спек, как в 41.4/41.10, в коммит не входит. Способ проверки — в Debug Log.

## Dev Notes

### Что меняется и что сохраняется — по файлам

| Файл | Сейчас | Что меняет стори | Что сохранить |
|---|---|---|---|
| `backend/apps/common/consent_texts.json` | 3 поверхности; `newsletter.*` → одна `newsletter_checkbox` | +2 поверхности, +1 ревизия регистрации, перепривязка, +3 версии в `known_versions` | Все существующие ревизии побайтно, привязки `registration.*` и `1c_link.*` |
| `backend/apps/common/serializers.py` | `SubscribeSerializer`: `pdp_consent` + одна `consent_text_version`, сверяемая для обоих типов (`:164-179`) | + `marketing_consent`, две версии, два field-level валидатора, строгая проверка обоих флагов | `validate_email`, `create()` целиком (реактивация, гонка, активный подписчик), `consent_text_outdated_payload`, `has_error_code` |
| `backend/apps/common/views.py` | Две вставки `UserConsent`, версия запрашивается у реестра на каждый тип (`:453-462`) | Комментарии и `@extend_schema` | Код view, `503`-ветки, материализация сессии, нейтральный `200` |
| `backend/apps/common/api_schema.py` | `help_text` перечисляет три поля версии | Два поля версии | Компоненты, `oneOf`, имена |
| `frontend/src/constants/consentTexts.ts` | `newsletter`, `registrationPdp`, `registrationMarketing` | `newsletterPdp`, `newsletterMarketing`, новая `registrationMarketing` | `isConsentTextOutdated`, `getConsentTextOutdatedMessage`, тип из контракта |
| `SubscribeForm.tsx`, `ElectricSubscribeForm.tsx` | Один чекбокс, кнопка неактивна до галочки | Два чекбокса; без галочки рассылки — ошибка у её чекбокса | Правило `disabled={isSubmitting \|\| !pdpConsent}`, заголовок, подзаголовок, email-поле, тосты, ветки ошибок сервиса, `reset()` после успеха |
| `RegisterForm.tsx`, `B2BRegisterForm.tsx` | «Я согласен (на)… от OPTISPORT» | Текст с каналом | Всё остальное |
| `frontend/src/services/subscribeService.ts` | Шлёт `SubscribeRequest` как есть | **Ничего** — меняется только тип | Разбор `error` и `details` |
| `backend/apps/common/models.py` | `UserConsent` с `source` и `consent_text_version` | **Ничего** | — |

### Контракт `POST /api/v1/subscribe/` после стори

```json
{
  "email": "user@example.com",
  "pdp_consent": true,
  "marketing_consent": true,
  "pdp_consent_text_version": "<действующая версия newsletter.pdp_contract>",
  "marketing_consent_text_version": "<действующая версия newsletter.marketing_email>"
}
```

Имена полей **те же, что у регистрации**: `pdp_consent_text_version` и `marketing_consent_text_version` уже есть в `CONSENT_TEXT_VERSION_FIELDS` на обеих сторонах. Отсюда три следствия:

1. `consent_text_outdated_payload()` и фронтовый `getConsentTextOutdatedMessage()` правки не требуют — только убирается мёртвое `consent_text_version`.
2. **Вкладка со старым бандлом на проде переживёт выкат корректно.** Бандл 41.9 шлёт `consent_text_version`, сервер ответит `consent_text_outdated` с сообщением в `details.pdp_consent_text_version`. Список полей старого бандла это имя уже содержит (`consentTexts.ts:58-62` на проде такой же), поэтому человек увидит «Текст согласия обновился. Обновите страницу…», а не «введите корректный email».
   > **Поправка ревью, 2026-09-13.** Пункт 2 неверен для реального бандла 41.9. Он шлёт POST на `/subscribe` без слэша, и при `DEBUG=False` Django отвечает 301. Браузер повторяет запрос как GET и получает 405, сервис считает это `network_error`, форма пишет «Не удалось подписаться». До сверки версии запрос не доходит. Так было со стори 11.3, слэш исправлен в этой стори (Change Log 1.3). Ответ `consent_text_outdated` на формат 41.9 получит только клиент, который шлёт на `/subscribe/`.
3. Сервер в журнал кладёт версию из реестра (`current_consent_text_version`), а не присланную. Присланная только сверяется. Так в 41.9, так и остаётся.

Ожидаемое тело AC4 (порядок ключей в `details` произволен, сравнивать словарём):

```json
{
  "error": "consent_text_outdated",
  "details": {
    "marketing_consent": ["Необходимо согласие на получение рассылок по электронной почте."],
    "pdp_consent_text_version": ["Текст согласия обновился. Обновите страницу и подтвердите согласие заново."],
    "marketing_consent_text_version": ["Текст согласия обновился. Обновите страницу и подтвердите согласие заново."]
  }
}
```

### Реестр после стори

```json
{
  "surfaces": {
    "newsletter_checkbox":           { "description": "Исторический… (41.11)", "revisions": [ /* 2026-08-30, без изменений */ ] },
    "newsletter_pdp_checkbox":       { "revisions": [ { "label": "YYYY-MM-DD", "text": "Я даю согласие на обработку моих персональных данных в соответствии с «Политикой обработки персональных данных»" } ] },
    "newsletter_marketing_checkbox": { "revisions": [ { "label": "YYYY-MM-DD", "text": "Я согласен(на) получать информационные и рекламные рассылки от OPTISPORT по электронной почте" } ] },
    "registration_pdp_checkbox":     { /* без изменений */ },
    "registration_marketing_checkbox": { "revisions": [
      { "label": "2026-09-09", "text": "Я согласен (на) получать рекламные и информационные рассылки от OPTISPORT" },
      { "label": "YYYY-MM-DD", "text": "Я согласен(на) получать рекламные и информационные рассылки от OPTISPORT по электронной почте" }
    ] }
  },
  "known_versions": [ /* три прежние + три новые */ ],
  "bindings": {
    "newsletter.pdp_contract": "newsletter_pdp_checkbox",
    "newsletter.marketing_email": "newsletter_marketing_checkbox",
    "registration.pdp_contract": "registration_pdp_checkbox",
    "registration.marketing_email": "registration_marketing_checkbox",
    "1c_link.pdp_contract": "registration_pdp_checkbox",
    "1c_link.marketing_email": "registration_marketing_checkbox"
  }
}
```

`YYYY-MM-DD` — дата реализации, одна на все три новые ревизии. Действующая ревизия поверхности — **последняя** в списке (`consent_texts.py:180`), поэтому новая ревизия регистрации дописывается в конец.

**Почему `newsletter_checkbox` не удаляется и не получает новую ревизию.**
- Удалить нельзя: 41.9 на проде, записи журнала после её выката ссылаются на `2026-08-30-77dbc…`. Загрузчик требует точного совпадения `known_versions` с ревизиями, и удаление уронит загрузку.
- Сделать её поверхностью ПДн с новой ревизией тоже нельзя: история такой поверхности утверждала бы, что объединённый текст был согласием только на ПДн.
- Загрузчик поверхности без привязок допускает (`_ingest_binding` проверяет только ссылки привязок), `resolve_consent_text` ищет по всем ревизиям.

**Почему текст ПДн подписки дословно равен тексту ПДн регистрации.** AC1 запрещает упоминать рассылку в чекбоксе ПДн. Без неё формулировка регистрации — ровно то, что нужно. Поверхность при этом отдельная, а не привязка к `registration_pdp_checkbox`: формы живут независимо, и правка текста регистрации не должна молча требовать правки подписки. Совпадение текстов безопасно, пока различаются метки ревизий — отсюда запрет метки `2026-09-09` в Task 1.2.

**Почему текст рассылки регистрации не выровнен дословно с подпиской.** Порядок слов разный: «рекламные и информационные» у регистрации, «информационные и рекламные» у подписки. Выравнивание дало бы две ревизии с одинаковым текстом и одинаковой меткой (обе в день реализации), то есть одну версию на двух поверхностях — загрузчик это отклоняет. Минимальная правка регистрации (пробел + канал) снимает конфликт и сохраняет совпадение регулярки в `RegisterForm.test.tsx:49`.

### Сериализатор — как не потерять машинный код

- Сверка версий — **только** в `validate_<поле>`. Object-level `validate()` DRF не вызывает, если хоть одно поле не прошло field-level проверку.
- Все пять ключей `error_messages` у полей версии → `CONSENT_TEXT_OUTDATED`. `invalid` обязателен: массив, объект или boolean иначе получат «Not a valid string.» (седьмой круг ревью 41.9). Ноль-байт и одиночный суррогат выравнивает `consent_text_outdated_payload()` — её не трогать.
- Строгий `true` — через `self.initial_data.get(...) is not True`: `BooleanField` превращает `"true"`, `"on"`, `1` в `True`.
- Образец безусловной обязательности — `pdp_consent_text_version` регистрации (`apps/users/serializers.py:96-108`, `:194-210`). Условная обязательность маркетинговой версии регистрации (`:112-125`, `:212-236`, `UserRegistrationRequestSchemaExtension` `:426-466`) к подписке **не** переносится: там согласие обязательно, и `if`/`then` в схеме не нужен.

### Форма — кнопка зависит только от ПДн (решение Alex, 2026-09-12)

Две блокировки разного устройства:

- **ПДн** — прежняя: кнопка неактивна, пока галочка не стоит (`disabled={isSubmitting || !pdpConsent}`, `SubscribeForm.tsx:236`, `ElectricSubscribeForm.tsx:297`). Клиентской ошибки у чекбокса ПДн поэтому не бывает — только серверная, через `setError` (путь обхода клиента).
- **Рассылка** — через валидацию: `register('marketing_consent', { required: MARKETING_CONSENT_REQUIRED })`. Кнопка активна, `handleSubmit` не вызывает `onSubmit`, выставляет ошибку и переводит фокус на чекбокс рассылки (`shouldFocusError`).

**Не добавлять `!marketingConsent` в `disabled`** — это прямо противоречит решению владельца. И не убирать `!pdpConsent`.

Ловушка теста: сценарий «рассылка без ПДн» до валидации не доходит — кнопка неактивна, клик ничего не делает. Ошибку рассылки проверять только при отмеченном ПДн.

Правило `required` у ПДн (`:112-114`) остаётся как есть: при неактивной кнопке оно не срабатывает, но и не мешает.

Формы регистрации сохраняют свою неактивную кнопку (AC10) — стори 41.11 их поведение не трогает.

`aria-required="true"`, а не `required`: форма не объявляет `noValidate`, и нативный `required` показал бы всплывающую подсказку браузера до `react-hook-form`, в обход разметки ошибок.

### Выкат (для владельца, вне объёма dev-story)

- Миграций нет. Меняются backend (сериализатор, реестр, схема) и frontend.
- На проде: `git fetch origin main; git reset --hard origin/main`, пересборка backend и frontend **одним заходом** (`up -d --build backend frontend`), затем обязательно `restart nginx`.
- Окно между рестартами: старый бандл против нового сервера получит `consent_text_outdated` (штатно, см. «Контракт»), новый бандл против старого сервера — то же с запасным текстом. Подписка в эти секунды не проходит, записей не создаётся.
  > **Поправка ревью, 2026-09-13.** Старый бандл до сервера не дойдёт: POST без слэша получает 301, затем GET и 405, форма пишет «Не удалось подписаться» (см. поправку к «Контракту», п. 2). Подписка на проде не работала и до выката, заработает только с новым бандлом. После выката проверить подписку в приватном окне по AC9 обязательно.
- Проверка после выката — AC9 на `https://optisport.ru/home` в приватном окне. Если серверный HTML через `curl` вернёт только глобальный спиннер `AuthProvider` (так было с `/checkout` в 41.10), это ожидаемо: приёмка по DOM.
- Повторный прогон сканера — после выката 41.10–41.12 и правки п. 1.2 политики (эпик, «Обоснование приоритета стори 41.10–41.12»). Гипотеза H2 SCP («отдельный чекбокс рассылки засчитывается, только если назван канал») проверяется только прогоном.

### Команды

```bash
# Backend-тесты (из docker/, строго последовательно в одном проекте)
docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest <путь>

# Перегенерация контракта: docs смонтирован на запись
MSYS_NO_PATHCONV=1 docker compose -p freesport-lint -f docker-compose.test.yml run --rm --no-deps -T \
  -v "C:/Users/1/DEV/FREESPORT/docs:/contract" backend \
  python manage.py spectacular --validate --file /contract/api/openapi.yaml

# Сверка контракта
MSYS_NO_PATHCONV=1 docker compose -p freesport-lint -f docker-compose.test.yml run --rm --no-deps -T \
  -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend \
  python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml

# Линтеры — в freesport-lint, не одновременно с зачётным pytest (роняет перф-тест 500 мс)
docker compose -p freesport-lint -f docker-compose.test.yml run --rm --no-deps -T backend flake8 <файлы>
```

Без `MSYS_NO_PATHCONV=1` Git Bash переписывает путь назначения тома, и файл не находится. `--env-file` тестовому compose не передаётся.

### Blast radius (GitNexus, `c0c89798`)

- `SubscribeSerializer` — **LOW**, 7 затронутых, 4 прямых. Все рёбра — импорты уровня файла: `apps/users/serializers.py` и `authentication.py` импортируют из `common/serializers.py` константы (`CONSENT_TEXT_OUTDATED`, `consent_text_outdated_error`, `consent_text_outdated_payload`), а не сам класс. Регистрацию правка класса не затрагивает. Вызывающих в графе нет, процессов нет.
- `SubscribeForm`, `ElectricSubscribeForm`, `RegisterForm`, `B2BRegisterForm` — 0 затронутых: JSX-рёбра граф не ловит. Фактические места рендера: `SubscribeNewsSection.tsx:22`, `ElectricSubscribeSection.tsx:16`. Страницы регистрации меняются только текстом.
- `subscribe` (view) — достигается только через URLconf `common:subscribe`.
- HIGH/CRITICAL нет. Перед правкой каждого символа dev-story всё равно выполняет `impact` (правило проекта).

### Ловушки

- **Массовая замена `consent_text_version` запрещена.** Это же имя носят поле модели `UserConsent`, миграция `0019`, админка и документы архитектуры. Уходит только поле запроса подписки; правки точечные, по результатам поиска.
- **Реестр кэшируется** (`lru_cache` в `load_registry`). После правки JSON перезапустить backend-контейнер, иначе локальная проверка увидит старые версии.
- **`known_versions` сверяется на точное равенство.** Новая ревизия без строки в списке и правка старого текста — обе роняют загрузку. Сообщение называет готовые строки.
- **Страж на фронте считает версию сам** (sha256 от текста последней ревизии). Константа `CONSENT_TEXT_VERSIONS` обязана совпасть — копировать из сообщения загрузчика, а не набирать.
- **`vi.mock('@/services/subscribeService')`** в тестах форм — автомок: `mockResolvedValue`/`mockRejectedValue` на каждый тест, как сейчас.
- **HMR на Windows не подхватывает правки.** Нужны `restart frontend`, затем `restart nginx`.
- **Параллельные pytest-прогоны в одном compose-проекте** дают лавину ложных падений на deadlock `TRUNCATE`.
- **Числа в отслеживаемые файлы — только готовыми.** Владелец может закоммитить дерево посреди dev-story.
- **Уточнение AC по ходу работы** — строкой Change Log, а не правкой AC задним числом (урок 41.3 и 41.9).

### Previous story intelligence

- **41.9 — фундамент этой стори.** Реестр, `known_versions`, версия из бандла, field-level сверка, `{error, details}`, страж в Vitest — всё готово, стори только добавляет поверхности и поля. Семь кругов ревью 41.9 ушли на машинный код, тексты сообщений и контракт `400`. Не переизобретать: `consent_text_outdated_error`, `consent_text_outdated_payload`, `consent_validation_error_response`, `consent_text_outdated_example`.
- **41.9 — метаданные.** `review_head` ставится один раз, File List — по `git diff`. Побочные правки (автосчётчик GitNexus в `AGENTS.md` / `CLAUDE.md`) — отдельным разделом.
- **41.10.** Приёмка анонимом (NFR-41-08). `curl` может отдать спиннер `AuthProvider`. Без браузерных инструментов — временный Playwright-спек.
- **41.3.** RED/GREEN-проверка стража — временная поломка и откат с пустым `git diff` (Task 10.5). Отложенный пункт про `aria-required` закрывается здесь для чекбоксов подписки.
- **41.6.** Страж, сравнивающий литерал с литералом, зелёный при неверной разметке. Поэтому текст в страже — из реестра, версия — пересчётом хеша.

### Git intelligence

Последние коммиты `develop`: `c0c89798` (#164, landmark `main` темы electric — `app/(electric)/electric/page.tsx`, `ElectricSidebar`), `f157c6e3` (заметка о health прода), `045466f8` (удаление вспомогательных файлов BMad), `27ffdbd5` (#158, стори 41.10 — checkout/cart). Файлы подписки, регистрации и реестра они не трогали. Последние правки этих файлов — стори 41.9 (`fc507169`, влита PR #149, и седьмой круг ревью), её паттерны — образец.

### Технологический контекст

Новых зависимостей нет. Django 5.2.7, DRF 3.14.0, drf-spectacular (OpenAPI 3.1), Next 15.5.18, React 19.1.0, react-hook-form (`register`, `handleSubmit`, `setError`, `shouldFocusError`), Vitest ^4, `vitest-axe` ^0.1.0. `Checkbox` — `React.forwardRef` (`components/ui/Checkbox/Checkbox.tsx`); его не переписывать, стори его только использует. Веб-исследование не требовалось: новых API нет, правовая рамка взята из одобренного SCP.

### Project Structure Notes

- Реестр — `backend/apps/common/consent_texts.json` (попадает в образ через `COPY . .`). Новых модулей не заводится.
- Backend unit-тесты — `backend/apps/common/tests/`, integration — `backend/tests/integration/`. Маркеры проставляет `pytest_collection_modifyitems`, руками не ставить.
- Кросс-граничные и компиляционные стражи фронта — `frontend/src/__tests__/`, тесты компонентов — рядом, в `__tests__/`.
- Комментарии и docstrings — на русском (NFR-41-03).
- Ветка `feature/story-41-11-separate-subscribe-consents` от `develop`. Прямые коммиты в `develop` запрещены, 5 обязательных контекстов CI.
- Отклонений от структуры нет.

### References

- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.11`] — AC эпика, контекст, выкат
- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md` — FR-41-05 (ред. 3), FR-41-26, NFR-41-04, NFR-41-06, NFR-41-08] — требования
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-09-10.md#4.3`] — происхождение, правовое основание, риск «средний»
- [Source: `_bmad-output/implementation-artifacts/Story/41-9-consent-journal-text-version-and-source.md#Dev Notes`, `#Change Log`] — реестр, ловушки, семь кругов ревью
- [Source: `backend/apps/common/consent_texts.py:62-180, 182-228, 321-348`] — версия, ингест ревизий, `known_versions`, API реестра
- [Source: `backend/apps/common/consent_texts.json`] — текущие поверхности и привязки
- [Source: `backend/apps/common/serializers.py:18-112, 115-259`] — константы, `CONSENT_TEXT_VERSION_FIELDS`, payload отказа, `SubscribeSerializer`
- [Source: `backend/apps/common/views.py:311-493`] — схема и view подписки
- [Source: `backend/apps/common/api_schema.py:86-142`] — компоненты `400`
- [Source: `backend/apps/users/serializers.py:82-125, 194-236, 426-466`] — образец полей версии регистрации
- [Source: `backend/apps/common/models.py:595-718`] — `UserConsent` (не меняется)
- [Source: `backend/tests/consent_versions.py`; `backend/tests/integration/test_common_subscribe_api.py:36, 297-505`; `backend/apps/common/tests/test_consent_texts.py:101-121`; `backend/apps/common/tests/test_api_schema.py`] — тесты
- [Source: `frontend/src/constants/consentTexts.ts:21-97`] — версии и разбор отказа
- [Source: `frontend/src/components/home/SubscribeForm.tsx:25-244`; `ElectricSubscribeForm.tsx:22-304`] — формы подписки
- [Source: `frontend/src/components/auth/RegisterForm.tsx:440-500`; `B2BRegisterForm.tsx:536-549`] — чекбоксы регистрации
- [Source: `frontend/src/types/api.ts:234-240`; `frontend/src/types/api.generated.ts:2698-2706`; `frontend/src/services/subscribeService.ts`] — типы и сервис
- [Source: `frontend/src/__tests__/consent-texts-registry.test.tsx`; `frontend/src/__tests__/register-request-contract.test.ts`] — стражи
- [Source: `docs/api/openapi.yaml:85-155, 4694-4717`] — текущий контракт
- [Source: `docs/architecture/11-security-performance.md:962-991`; `18-b2b-verification-workflow.md:140-149`; `index.md:48`] — документация к правке
- [Source: `_bmad-output/implementation-artifacts/deferred-work.md:24, 923`] — отложенные пункты ARIA
- [Source: `project-context.md` §1, §4, §5, §7] — Docker, тесты, GitNexus, фронт

## Change Log

| Дата | Версия | Изменение | Автор |
|---|---|---|---|
| 2026-09-12 | 1.0 | Стори создана. Сверх скелета эпика: (а) контракт повторяет имена полей регистрации — старый бандл на проде переживает выкат без правок; (б) `newsletter_checkbox` остаётся исторической поверхностью без привязок; (в) метка ревизии ПДн подписки не может быть `2026-09-09` — дубль версии с регистрацией; (г) текст рассылки регистрации не выравнивается дословно с подпиской по той же причине; (д) без галочки рассылки отправку блокирует валидация формы, ошибка — у этого чекбокса; (е) `aria-required` закрывает чекбоксную часть `deferred-work.md:923`. | Alex / create-story |
| 2026-09-12 | 1.1 | Решения Alex по вопросам create-story, получены до старта dev-story: (1) кнопка подписки активна только при галочке ПДн, галочка рассылки на неё не влияет — правило `disabled={isSubmitting \|\| !pdpConsent}` прежнее, без рассылки отправку останавливает валидация с ошибкой у чекбокса рассылки (AC2, AC9, Task 7.5, 8.3, 10.2, 13.1, Dev Notes); (2) тексты чекбоксов и сообщение `MARKETING_CONSENT_REQUIRED` утверждены; (3) разный порядок слов в тексте рассылки регистрации и подписки принят. | Alex / create-story |
| 2026-09-12 | 1.2 | Реализация через bmad-quick-dev (спека `spec-41-11-separate-subscribe-consents.md`, ветка `feature/story-41-11-separate-subscribe-consents` от `c0c89798`), статус ready-for-dev → review. Отклонения от текста задач: (1) у чекбокса рассылки правило `validate` по значению формы, а не `required` из Task 7.3/спеки — `required` у чекбокса читает DOM, и `disabled={isSubmitting}` делал отмеченный чекбокс «пустым» до его проверки; (2) ручной `SubscribeRequest` в `types/api.ts` (Task 5.4) **не изменён**: `gitnexus impact` — CRITICAL, правка ждёт подтверждения владельца. Подробности — Completion Notes. | Claude / quick-dev |
| 2026-09-13 | 1.3 | Решения Alex по итогам реализации:<br>(1) правка ручного `SubscribeRequest` в `types/api.ts` разрешена — CRITICAL оказался артефактом файловых импортов, Task 5.4 выполнена;<br>(2) правило `validate` вместо `required` у чекбокса рассылки принято, строка спеки пересмотрена (Spec Change Log);<br>(3) слэш в `subscribeService` исправлен в этой стори: POST на `'/subscribe/'`, тест URL. Это расширение объёма — по таблице Dev Notes сервис не менялся. MSW-хендлер `/subscribe` не тронут (AC10), записан в `deferred-work.md`. | Alex / Claude, quick-dev |

## Dev Agent Record

### Review Findings

Ревью 2026-09-13 шло шагом 4 bmad-quick-dev. Два независимых ревьюера — Blind Hunter (состязательный) и Edge Case Hunter (граничные пути) — смотрели diff `c0c89798..` рабочего дерева вместе с неотслеживаемыми файлами. Находок было 21, после дедупликации — 18. Находок `intent_gap` и `bad_spec` нет, поэтому возврата к спеке не было.

**patch — исправлено:**
- [x] **Документы неверно описывали выкат.** Утверждалось, что старый бандл 41.9 получит `consent_text_outdated`. На деле он шлёт POST на `/subscribe` без слэша: 301, затем GET и 405, форма пишет «Не удалось подписаться». Нашли оба ревьюера. Поправлены «Контракт» п. 2 и «Выкат» (поправки-врезки), Design Notes спеки и sprint-status.
- [x] **Правка слэша не была проверена на живом стенде.** Проверено `curl` через nginx: `POST /api/v1/subscribe/` отвечает `400 consent_text_outdated` от сериализатора, `POST /api/v1/subscribe` — 500 `RuntimeError` (`APPEND_SLASH`).
- [x] **Фокус при двух ошибках уходил на чекбокс рассылки, а не на email.** Причина — порядок `register`. Теперь порядок ПДн → email → рассылка в обеих формах: ПДн остаётся первым, потому что его `required` читает DOM. Порядок описан комментарием. Тесты фокуса в обеих формах: до правки RED, после GREEN.
- [x] **Ошибки флагов собирались не всегда.** `validate()` не вызывался при ошибке email или при `null` у одного из флагов. Строгая проверка `is not True` перенесена в `validate_pdp_consent` и `validate_marketing_consent`. Новые тесты: неверный email вместе с двумя `false` и три сочетания «ошибка поля + строгая проверка». Нашли оба ревьюера.
- [x] **Тест требовал дословного равенства текстов ПДн подписки и регистрации.** Переписан как `test_newsletter_pdp_version_differs_from_registration_pdp_version`: проверяет только, что версии различаются.
- [x] **Метаданные:**
  - задачи стори отмечены `[x]`;
  - в Task 7.3 указано, что сделано правилом `validate`;
  - строки Change Log идут по порядку;
  - перечень перестановок в `openapi.yaml` в Debug Log уточнён;
  - длительность прогона «до» помечена как сомнительная;
  - правка слэша добавлена в `docs/architecture/index.md`.

**defer — записано в `deferred-work.md`:**
- тексты `*_CONSENT_REQUIRED` повторены в бэкенде и в обеих формах без стража на совпадение — нашли оба ревьюера;
- `blogService` и `newsService` зовут `/blog` и `/news` без слэша, это лишний 301.

**reject:**
- одинаковый текст на двух поверхностях и риск коллизии метки при будущей правке в один день — так задумано и описано в Dev Notes;
- текст ПДн не называет цель обработки — утверждён Alex;
- `description` у `newsletter_checkbox` якобы утверждает непроверенное — формулировка условная;
- дубль словаря `error_messages` в регистрации — вне объёма;
- односторонний страж типов и `boolean` вместо литерала `true` — образец `register-request-contract.test.ts` и сгенерированный тип.

### Agent Model Used

Claude Opus 5 (claude-opus-5), через /bmad-quick-dev (шаг 3 — реализация).

### Debug Log References

Команды backend — из `docker/`, frontend — из `frontend/`, `git` и `gitnexus` — из корня.

| Проверка | Команда | Результат | Ограничение |
|---|---|---|---|
| Точка ветвления | `git checkout -b feature/story-41-11-separate-subscribe-consents` | От `c0c89798` (`develop` = `origin/develop`, 0/0). В дереве до правок кода — только документы create-story и счётчики GitNexus | — |
| Backend «до» | `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -p no:cacheprovider` | 3358 passed, 75 skipped, 19 subtests passed, 28:22 — длительность до секунды совпадает с первым прогоном «после»; вероятна ошибка переноса, перепроверить нельзя. Числа тестов достоверны | Пропуски — тесты, читающие файлы вне `backend/` (память проекта) |
| Frontend «до» | `npm run test -- --run` | 173 файла, 2897 passed, 16 skipped | — |
| GitNexus impact | `npx gitnexus impact <symbol> --direction upstream --repo "C:\Users\1\DEV\FREESPORT"` | `SubscribeSerializer` LOW (7, 4 прямых — импорты уровня файла); `validate_consent_text_version` LOW (0); `ConsentTextOutdatedResponseSerializer` LOW (2); `CONSENT_TEXT_VERSIONS` LOW (0); `subscribe`, `CONSENT_TEXT_VERSION_FIELDS`, четыре формы — 0 затронутых. **`SubscribeRequest` (`types/api.ts`) — CRITICAL, 120 затронутых, 44 прямых** | Все 120 рёбер — `IMPORTS` файла `types/api.ts`; интерфейс использует только `subscribeService.ts:75` (поиск по `frontend/`). Символ не правился — см. Completion Notes |
| Версии реестра | `python -c "from apps.common.consent_texts import load_registry; load_registry()"` в `freesport-lint` | Загрузчик назвал `2026-09-12-1a97b44f…`, `2026-09-12-a49604a6…`, `2026-09-12-de992f50…` — внесены в `known_versions`; повторная загрузка чистая, привязки `newsletter.*` → новые поверхности | Версии совпали с локальным пересчётом sha256 |
| Затрагиваемые наборы backend | `pytest -q tests/integration/test_common_subscribe_api.py apps/common/tests/test_consent_texts.py apps/common/tests/test_api_schema.py tests/integration/test_auth_registration_consent.py apps/common/tests/test_user_consent.py` | 208 passed, 2 failed (ошибка в новом тесте — `email` в overrides); после правки 6/6 | — |
| Затрагиваемые наборы frontend | `npx vitest run` по 7 файлам (страж реестра, страж контракта, обе формы подписки, `subscribeService`, обе формы регистрации) | Первый прогон: 29 падений — `subscribe` не вызывался; причина — `required` у чекбокса рассылки при `disabled={isSubmitting}` (Completion Notes). Плюс axe `label-title-only` у синего чекбокса рассылки. После правок: 7 файлов, 127 passed | — |
| RED/GREEN стража (Task 10.5) | Временно `информационные и рекламные` → `…рекламныe` (латинская «e») в `SubscribeForm.tsx`, `npx vitest run src/__tests__/consent-texts-registry.test.tsx`, восстановление из копии | RED: `1 failed \| 9 passed` — «Unable to find … checkbox … name "Я согласен(на) получать информационные и рекламные…"». Хеш файла до и после совпал (`d0bad14e091790d9`). GREEN: 10 passed | — |
| Линтеры backend | `flake8` и `black --check` по 8 изменённым Python-файлам; `mypy .` — всё в `freesport-lint`, не одновременно с зачётным pytest | flake8, black — чисто. mypy: первый прогон — 2 ошибки (`dict[str, str]` в `error_messages` — `dict` инвариантен); после аннотации `dict[str, Any]` — `Success: no issues found in 562 source files`, дельта к базису 0 | — |
| Контракт | `spectacular --validate --file /contract/api/openapi.yaml` (docs смонтирован); `check_openapi_sync --schema-file /contract/api/openapi.yaml`; `npm run generate:types` | «Контракт синхронен с кодом». Структурно (сравнение YAML-деревьев) изменились только `/subscribe/`, `SubscribeRequest` и `help_text` у `ConsentTextOutdatedResponse`. `api.generated.ts`: `SubscribeRequest` — пять полей | Текстовый diff `openapi.yaml` больше смыслового: генератор переставил порядок путей и операций — `/users/addresses/`, `/users/favorites/`, `/orders/`, `/orders/{id}/`, `/cart/items/{id}/`. Меняется только порядок ключей, не содержание (перечень уточнён на ревью) |
| Линтеры frontend | `npx eslint`, `npx prettier --check` по изменённым TS-файлам | eslint — чисто; prettier — 3 файла отформатированы `--write`, затем чисто | — |
| Frontend «после» | `npm run test -- --run` | 174 файла, 2915 passed, 16 skipped (+1 файл, +18 тестов). Первый прогон «после» ронял `constants/__tests__/consentTexts.test.ts` (поле `consent_text_version` в `details`, которое фронт больше не читает) — тест переведён на `pdp_consent_text_version` и дополнен случаем ответа старого сервера | — |
| Backend «после» | Та же команда, что «до», в `freesport-test`, без параллельных линтеров | 3389 passed, 75 skipped, 19 subtests passed, 28:22 (+31 тест, падений нет) | — |
| Типы frontend | `npx tsc --noEmit` | **14 ошибок в 4 файлах:** `subscribeService.test.ts` (7), `subscribe-request-contract.test.ts` (5), `SubscribeForm.tsx` (1), `ElectricSubscribeForm.tsx` (1). Все — несоответствие неизменённому ручному `SubscribeRequest` (`consent_text_version` вместо четырёх новых полей) | Устраняются правкой Task 5.4 после подтверждения владельца; сгенерированный тип страж уже принимает |
| GitNexus detect-changes | `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` | 30 файлов, 47 символов, 17 процессов, risk critical. Ожидаемые: `SubscribeSerializer` и его методы, `subscribe`, `ConsentTextOutdatedResponseSerializer`, `CONSENT_TEXT_VERSION_FIELDS`, `SubscribeForm`/`ElectricSubscribeForm` (`onSubmit`), `RegisterForm`, `B2BRegisterForm`, тесты | `validate_email`, `consent_text_outdated_error`, `ALREADY_SUBSCRIBED_CODE`, локальные `request`/`ip_address`/`user_agent`/`raced` в `create()`, `isConsentTextOutdated` — сдвиг строк от правок выше, тела не менялись. Уровень critical — от числа процессов (формы регистрации и подписки), HIGH/CRITICAL-символов среди изменённых нет |
| Приёмка NFR-41-08 (AC9) | Временный `tests/e2e/tmp-story-41-11-check.spec.ts`, `PLAYWRIGHT_BASE_URL=http://localhost`, `--workers=1`, после `restart backend`, `restart frontend`, `restart nginx` | 4/4. `/home` и `/electric` в чистом контексте без cookie: два неотмеченных чекбокса с `aria-required`; Tab: email → ПДн → ссылка на политику → рассылка; пробел переключает; без ПДн кнопка неактивна и при отмеченной рассылке; ПДн без рассылки — клик, POST не ушёл, `role="alert"` с текстом ошибки, `aria-invalid`, `aria-describedby`, фокус на чекбоксе рассылки; обе галочки — `200`, payload из пяти полей с разными версиями, форма сброшена. `/register`, `/b2b-register` — чекбокс с новым текстом. Журнал (ORM в dev-контейнере): на каждую подписку две записи — `pdp_contract` `2026-09-12-de992f50…` и `marketing_email` `2026-09-12-1a97b44f…`, `source` = «Подписка на рассылку» | **Предсуществующий дефект вне стори:** `subscribeService` шлёт POST на `/subscribe` без слэша → Django (`APPEND_SLASH`) отвечает 500; для приёмки спек переадресовал запрос на `/subscribe/` (`page.route`), тело не менялось. Тост успеха в DOM не найден (0) — успех проверен сбросом формы. Спек, артефакты `test-results/` и тестовые записи (10 `UserConsent`, 5 `Newsletter`) удалены, `test-results/.last-run.json` восстановлен. Браузерных MCP-инструментов не было |
| Доработка по решениям Alex (2026-09-13) | Правка `SubscribeRequest` в `types/api.ts` и URL `'/subscribe/'` в `subscribeService.ts`; `npx tsc --noEmit`; `npx vitest run` по 5 затронутым наборам; `npx eslint`, `npx prettier --check` по 3 файлам; `npm run test -- --run` | `tsc` — 0 ошибок, 14 прежних ушли. Затронутые наборы — 5 файлов, 69 passed. eslint и prettier — чисто. Полный Vitest — 174 файла, 2915 passed, 16 skipped: число тестов прежнее, у одного изменились имя и ожидание URL | Backend не менялся, повторный прогон не нужен. Подписка через стенд проверена на ревью — `curl`, см. следующую строку |
| Доработка по ревью (2026-09-13) | `curl -X POST` на `http://localhost/api/v1/subscribe/` и `…/subscribe`. `npx vitest run` по тестам фокуса до и после правки форм. Затронутые backend-наборы: `pytest -q tests/integration/test_common_subscribe_api.py apps/common/tests/test_consent_texts.py apps/common/tests/test_api_schema.py tests/integration/test_auth_registration_consent.py`. `flake8`, `black --check` по 3 Python-файлам, `mypy .` в `freesport-lint`. `npx tsc --noEmit`, `npx eslint`, `npx prettier --check` по 4 TS-файлам. `npm run test -- --run`. `npx gitnexus detect-changes --scope all` | Стенд через nginx: `/subscribe/` — `400 consent_text_outdated` от сериализатора, `/subscribe` — 500 `RuntimeError` (`APPEND_SLASH`). Тесты фокуса: RED — 2 failed, фокус на чекбоксе рассылки; GREEN — обе формы, 50 passed. Backend-наборы — 193 passed. flake8 и black чистые, mypy — «no issues found in 562 source files». `tsc`, eslint, prettier чистые. Полный Vitest — 174 файла, 2917 passed, 16 skipped (+2 теста фокуса). detect-changes: 32 файла, 53 символа, 18 процессов, critical. Новые символы — `validate_pdp_consent`, `validate_marketing_consent`, `SubscribeRequest`, `subscribe` в `subscribeService` | `impact` по формам в CLI неоднозначен: у каждой два символа, а флага выбора нет. Вызывающие найдены через `cypher`: `SubscribeNewsSection` и `ElectricSubscribeSection`, по одному, LOW. Формы на стенде после правки фокуса не перезапускались, фокус проверен только в jsdom |
| Backend после ревью | `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -p no:cacheprovider`, без параллельных линтеров и Vitest | 3393 passed, 75 skipped, 19 subtests passed за 1717 с (0:28:37), падений нет. К прогону «после» 3389 прибавились 4 теста: неверный email и три случая со смешанными ошибками флагов | Пропуски — те же 75 |

### Completion Notes List

- Подписка берёт два отдельных обязательных согласия: реестр получил поверхности `newsletter_pdp_checkbox` и `newsletter_marketing_checkbox` (метка `2026-09-12`), привязки `newsletter.*` переведены на них, `newsletter_checkbox` остался исторической поверхностью без привязок. У `registration_marketing_checkbox` — вторая ревизия с каналом; прежние версии `2026-08-30-77dbc…` и `2026-09-09-e2647…` разрешаются в свой текст.
- `SubscribeSerializer`: `marketing_consent` (строго JSON `true`), поля `pdp_consent_text_version` и `marketing_consent_text_version` с общим словарём `CONSENT_TEXT_VERSION_ERROR_MESSAGES`, два field-level валидатора — каждый со своей привязкой; ошибки флагов копятся и приходят одним ответом. `consent_text_version` убран из `CONSENT_TEXT_VERSION_FIELDS` на обеих сторонах. Запрос формата 41.9 получает `consent_text_outdated` с ошибками обоих полей версии и `marketing_consent`. Код записи согласий во view не менялся.
- Формы подписки: чекбокс ПДн с `aria-labelledby` = префикс + ссылка, отдельный чекбокс рассылки, оба с `aria-required="true"`, ошибки через `aria-describedby`; кнопка по-прежнему `disabled={isSubmitting || !pdpConsent}`. В electric разметка чекбокса вынесена в локальный `ElectricConsentCheckbox`; галочка «✓» помечена `aria-hidden`, имя — только через `aria-labelledby`.
- **Отклонение 1 — `validate` вместо `required` у чекбокса рассылки.** `handleSubmit` выставляет `isSubmitting` и валидирует поля по очереди через `await`; к проверке второго чекбокса React уже перерисовал его с `disabled`, а правило `required` у чекбокса читает DOM и у отключённого чекбокса значения не видит. Итог — отмеченная рассылка давала ошибку, отправка не проходила. `validate: value => value === true || MARKETING_CONSENT_REQUIRED` читает значение формы. У ПДн `required` оставлен (Dev Notes: «остаётся как есть») — он проверяется первым и под эффект не попадает. Поведение из AC2 (ошибка, фокус, снятие ошибки галочкой) не изменилось.
- **Отклонение 2 — axe `label-title-only`.** У синего чекбокса рассылки первый `label[for]` — пустой квадрат `Checkbox`; с появлением `aria-describedby` axe считал чекбокс подписанным только описанием. Имя задано `aria-labelledby` на текстовую метку — как у ПДн. Тексты не изменились.
- **Task 5.4 — ручной `SubscribeRequest` в `frontend/src/types/api.ts`.** Выполнена после подтверждения Alex, 2026-09-13.
  - `gitnexus impact` вернул CRITICAL (120/44), но это артефакт графа: все рёбра — импорты файла `types/api.ts`, а интерфейс использует только `subscribeService.ts:75`.
  - Теперь в типе четыре обязательных поля: `pdp_consent`, `marketing_consent`, `pdp_consent_text_version`, `marketing_consent_text_version`. Поля `consent_text_version` нет.
  - `tsc --noEmit` чистый.
- **Расширение объёма — слэш в `subscribeService`, решение Alex.**
  - Форма слала POST на `/api/v1/subscribe` без слэша. Маршрут Django — `subscribe/`, и `APPEND_SLASH` отвечал 500 при `DEBUG`, а при `DEBUG=False` — 301 на GET. Дефект шёл со стори 11.3 (`54877cfa`): на проде подписка, вероятно, не работала.
  - Теперь запрос уходит на `'/subscribe/'`, URL закреплён тестом в `subscribeService.test.ts`. Impact `subscribeService` — LOW (0).
  - MSW-хендлер `/subscribe` не тронут по AC10: в unit-тестах он не участвует. Расхождение путей записано в `deferred-work.md`.
- Задачи Task 1–13 выполнены. Task 13 выполнена временным Playwright-спеком; запрос в нём переадресовывался на `/subscribe/` ещё до правки сервиса.

### File List

**Новые файлы:**
- `frontend/src/__tests__/subscribe-request-contract.test.ts`
- `_bmad-output/implementation-artifacts/Story/41-11-separate-subscribe-consents.md` (story-файл, создан create-story)
- `_bmad-output/implementation-artifacts/spec-41-11-separate-subscribe-consents.md` (спека quick-dev)
- `_bmad-output/implementation-artifacts/epic-41-context.md` (контекст эпика quick-dev)

**Изменённые файлы:**
- `backend/apps/common/consent_texts.json`
- `backend/apps/common/serializers.py`
- `backend/apps/common/views.py`
- `backend/apps/common/api_schema.py`
- `backend/apps/common/tests/test_consent_texts.py`
- `backend/apps/common/tests/test_api_schema.py`
- `backend/tests/consent_versions.py`
- `backend/tests/integration/test_common_subscribe_api.py`
- `backend/tests/integration/test_auth_registration_consent.py`
- `docs/api/openapi.yaml`
- `docs/architecture/11-security-performance.md`
- `docs/architecture/18-b2b-verification-workflow.md`
- `docs/architecture/index.md`
- `frontend/src/constants/consentTexts.ts`
- `frontend/src/constants/__tests__/consentTexts.test.ts`
- `frontend/src/components/home/SubscribeForm.tsx`
- `frontend/src/components/home/ElectricSubscribeForm.tsx`
- `frontend/src/components/home/__tests__/SubscribeForm.test.tsx`
- `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx`
- `frontend/src/components/auth/RegisterForm.tsx`
- `frontend/src/components/auth/B2BRegisterForm.tsx`
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx`
- `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx`
- `frontend/src/services/subscribeService.ts`
- `frontend/src/services/__tests__/subscribeService.test.ts`
- `frontend/src/types/api.ts`
- `frontend/src/types/api.generated.ts`
- `frontend/src/__tests__/consent-texts-registry.test.tsx`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (create-story и старт quick-dev)

**Побочные правки, к стори не относятся:** `AGENTS.md`, `CLAUDE.md` — автосчётчик GitNexus (регенерация индекса владельцем до старта).
