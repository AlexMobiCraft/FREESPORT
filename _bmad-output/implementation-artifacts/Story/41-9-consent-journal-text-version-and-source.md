---
baseline_commit: 792ce210
---

# Story 41.9: Аудитируемость журнала согласий — версия текста и источник

Status: review

> 🟠 **Blast radius: GitNexus отдаёт HIGH по `UserConsent`** (CLI, `--repo C:\Users\1\DEV\FREESPORT`, 2026-09-09): 18 прямых зависимостей, 0 затронутых процессов, 0 модулей. **Цифра завышена** — это рёбра импорта уровня файла (`from apps.common.models import ...`); по имени символ упоминают ровно четыре не-тестовых файла, проверено `grep -rn "UserConsent" backend/apps --include=*.py`: `common/models.py`, `common/admin.py`, `common/views.py`, `users/views/authentication.py`. Остальные импортируют из того же модуля другие модели. Смежные символы: `UserRegistrationView` — LOW (0 upstream), `Function:backend/apps/common/views.py:subscribe` — LOW (0 upstream), `UserConsentAdmin` — LOW (1 upstream). Предупреждение о HIGH сделано согласно правилу проекта; фактический радиус — четыре файла плюс тесты.
> 🔴 **Точек записи в коде ДВЕ, а источников ТРИ.** `1c_link` — не третье место в коде, а ветка того же `UserRegistrationView.post`: флаг `pending_1c_link` уже вычислен на `authentication.py:140-142`, **до** обеих вставок (строки 147 и 155). Источник выбирается по этому флагу. Не заводить третью точку записи и не переносить запись в сериализатор — стори 41.2 специально оставила её в одном месте ради этой правки.
> 🔴 **Две живые формы регистрации бьют в один эндпоинт и показывают РАЗНЫЕ тексты ПДн.** `/register` (`RegisterForm.tsx:444-453`) и `/b2b-register` (`B2BRegisterForm.tsx:490-506`) обе шлют `POST /auth/register/`. Различить их на бэкенде **нечем**: роль не помогает — `RegisterForm` предлагает ровно те же три роли (`trainer`, `wholesale_level1`, `federation_rep`, `RegisterForm.tsx:56-60`), что и B2B-форма. Пока тексты не совпадают дословно, поле «версия текста» для источника `registration` не может быть честным. Решение — Task 5, унификация формулировок (Alex, 2026-09-09): осознанное отступление от границы «фронтенд не трогаем», см. «Решения владельца по объёму».
> 🔴 **Бэкенд не может прочитать `frontend/` в тестах.** Контекст сборки backend-образа — `../backend` (`docker/docker-compose.test.yml:48`), в контейнер монтируется только `../backend:/app` (строка 70). Поэтому страж «текст формы == текст реестра» обязан жить в **Vitest**: `frontend-ci.yml` делает полный `actions/checkout` и запускает тесты из `frontend/`, репозиторий целиком лежит на диске. Обратный вариант (pytest, читающий `.tsx`) физически неисполним.
> ⚠️ **Существующий тест сверяет `readonly_fields` списком целиком** — `backend/apps/common/tests/test_user_consent.py:161-170`. Добавление полей в админку его роняет; это ожидаемо и правится в Task 7, а не «обходится».
> ⚠️ **`CheckConstraint` требует комментария-игнора.** В проекте шесть таких мест, все с `# type: ignore[call-arg]  # django-stubs 4.2 не знает condition=` (образец — `common/models.py:650`). Без него mypy падает.
> ⚠️ **Миграцию писать руками.** Поля добавляются без `default` в модели, поэтому `makemigrations` уйдёт в интерактивный вопрос про одноразовое значение — в агентной среде это зависание. Пишем файл миграции вручную, затем сверяем `makemigrations --check --dry-run`.
> 🚫 **Cookie-согласие в журнал не заводится.** `useCookieConsent.ts` пишет только `localStorage` (строки 88-121), бэкенда у него нет и стори 41.1 его не добавляла. Четвёртого источника не появляется.
> 🚫 **`policy_version` не трогаем.** Остаётся `"1.0"` по умолчанию. Осмысленное версионирование политики требует ревизий у модели `Page` (текст политики живёт в БД, не в коде) — отдельная работа, уходит в `deferred-work.md` (Task 10).
> 🚫 **API-контракт не меняется.** `UserConsent` не отдаётся ни одним сериализатором (`grep "UserConsent" backend/apps/common/serializers.py` — ноль совпадений) и ни одним эндпоинтом. `docs/api/openapi.yaml` и `npm run generate:types` **не** трогаются, NFR-41-02 не задействован.

## Story

As a **оператор персональных данных**,
I want **видеть в журнале согласий, какой текст человек подтвердил и где он это сделал**,
so that **согласие оставалось доказуемым по ФЗ-152 ст. 9 после любой правки формулировок**.

**Закрывает:** NFR-41-04 (часть, не покрытую стори 41.3). **Соблюдает:** NFR-41-01, NFR-41-03.

**Фактическая цена вопроса — уже оплаченная один раз.** В стори 41.3 текст чекбокса подписки был переписан; все записи, сделанные до правки, стали относиться к прежней формулировке, и отличить их в журнале было нечем. Спасло только то, что данные оказались тестовыми и были удалены целиком (Task 7 стори 41.3). С реальными пользователями такого выхода нет: удалить журнал согласий — значит уничтожить доказательство.

## Acceptance Criteria

### AC1 (NFR-41-04) — модель и миграция

**Given** модель `UserConsent`
**When** применены миграции
**Then** у неё есть поле `source` с перечислением `newsletter` / `registration` / `1c_link` / `unknown`
**And** есть поле `consent_text_version`, отдельное от `policy_version`
**And** миграция добавляет оба поля одноразовым значением `unknown` (`preserve_default=False`) — существующие строки сохраняются и помечаются как неизвестные
**And** два `CheckConstraint` запрещают пустые `source` и `consent_text_version`: код, забывший передать значение, падает на вставке, а не пишет тихий мусор
**And** `python manage.py makemigrations --check --dry-run` не находит несозданных миграций

### AC2 (NFR-41-04) — реестр текстов согласий

**Given** реестр `backend/apps/common/consent_texts.json`
**When** его читает загрузчик `backend/apps/common/consent_texts.py`
**Then** для каждой живой пары (источник, тип согласия) есть привязка к поверхности согласия, а у поверхности — список ревизий с меткой и дословным текстом чекбокса
**And** версия вычисляется как `<метка>-<первые 8 hex sha256 текста>` — изменить текст, не изменив версию, механически невозможно
**And** ранее записанная версия разрешается обратно в свой текст: история ревизий не переписывается, а дополняется

### AC3 (NFR-41-04) — источник заполнен фактическим значением

**Given** подписка на рассылку (`POST /api/v1/subscribe/`)
**When** согласие фиксируется
**Then** обе записи (`pdp_contract`, `marketing_email`) получают `source = "newsletter"`

**Given** регистрация без привязки к 1С (`pending_1c_link` ложен)
**When** согласие фиксируется
**Then** записи получают `source = "registration"`

**Given** регистрация, ушедшая на привязку к записи 1С (`_pending_admin_review` или `_pending_link_confirmation`)
**When** согласие фиксируется
**Then** записи получают `source = "1c_link"`

**And** ни одна запись, созданная кодом, не имеет `source = "unknown"` — значение зарезервировано за строками, существовавшими до миграции

### AC4 (NFR-41-04) — версия соответствует показанной формулировке

**Given** подписка
**When** пишутся обе записи
**Then** обе получают версию единственного чекбокса формы подписки — он покрывает и ПДн, и рассылку (редакция 2 стори 41.3)

**Given** регистрация или привязка к 1С
**When** пишутся записи
**Then** `pdp_contract` получает версию чекбокса ПДн, `marketing_email` — версию отдельного маркетингового чекбокса

**Given** любая из четырёх форм с чекбоксом согласия (`SubscribeForm`, `ElectricSubscribeForm`, `RegisterForm`, `B2BRegisterForm`)
**When** форма отрисована в тесте
**Then** доступное имя её чекбокса дословно совпадает с текстом текущей ревизии реестра
**And** при отсутствии файла реестра страж падает с сообщением, называющим ожидаемый путь, а не пропускается

### AC5 (NFR-41-04) — старые и новые согласия различимы

**Given** в реестре появилась новая ревизия поверхности с изменённым текстом
**When** записывается новое согласие
**Then** его `consent_text_version` отличается от версии записей, сделанных по прежней ревизии
**And** прежние записи сохраняют свою версию и по-прежнему разрешаются в свой текст

### AC6 (NFR-41-04) — админка

**Given** админка согласий
**When** оператор открывает список
**Then** `source` и `consent_text_version` показаны в списке и доступны как фильтры
**And** оба поля read-only, а `has_add_permission` / `has_change_permission` / `has_delete_permission` по-прежнему возвращают `False`

### AC7 (NFR-41-01) — тесты и статический анализ

**Given** изменения бэкенда
**When** прогоняются тесты
**Then** существующие тесты подписки, регистрации и привязки к 1С зелёные после приведения к новым полям
**And** добавлены тесты на заполнение источника и версии в каждой из трёх веток записи
**And** добавлены тесты реестра: разрешение версии в текст, смена версии при смене текста, отсутствие непривязанных пар
**And** добавлен тест `CheckConstraint`: вставка с пустым `source` или пустой версией падает `IntegrityError`
**And** фронтенд-прогон зелёный; `npx tsc --noEmit`, `npm run lint`, `npm run format:check` — без ошибок
**And** `flake8 . --max-line-length=120 --extend-ignore=E203,W503` чист (единственный блокирующий линтер бэкенда в `backend-ci.yml:105-109`), `black .` не предлагает переформатирования
**And** `mypy --config-file=mypy.ini .` не добавляет новых ошибок к текущему базису — гейтом он не является (`backend-ci.yml:116`, `continue-on-error: true`, ~108 предсуществующих ошибок), поэтому «ноль ошибок» здесь не требуется и не достижим
**And** числа прогонов сняты **до** первой правки и после неё — «ничего не сломалось» без числа не принимается

### AC8 (границы) — что стори НЕ делает

- Не пересматривает состав записей: двойная запись `pdp_contract` + `marketing_email` для подписки остаётся (см. комментарий к `CONSENT_TYPE_CHOICES`, `models.py:589-601`).
- Не меняет `policy_version` и не вводит версионирование текста политики ПДн — текст живёт в БД (`Page`, slug `privacy-policy`), это отдельная работа.
- Не заводит cookie-согласие в журнал.
- Не меняет `UserConsent.__str__` — четыре теста сверяют его вывод дословно.
- Не удаляет мёртвый код привязки (`_link_matched_1c_customer`, `PortalLinkConfirmView`) — решение 2026-07-26 в силе.
- Не меняет API-контракт: `openapi.yaml` и типы фронта не регенерируются.
- Единственная правка фронтенда по существу — унификация двух формулировок регистрации (Task 5); внешний вид, разметка, ARIA и логика форм не меняются.

## Tasks / Subtasks

- [x] **Task 1. Реестр текстов согласий** (AC2)
  - [x] Создать `backend/apps/common/consent_texts.json` со структурой `surfaces` + `bindings` (точный вид — Dev Notes → «Реестр: структура и API»).
  - [x] Занести три поверхности с дословными текстами baseline: `newsletter_checkbox`, `registration_pdp_checkbox`, `registration_marketing_checkbox` (тексты — Dev Notes → «Тексты согласий на baseline»).
  - [x] Создать `backend/apps/common/consent_texts.py`: загрузка JSON через `Path(__file__).with_name(...)`, кэш на уровне модуля, функции `current_consent_text_version(source, consent_type) -> str` и `resolve_consent_text(version) -> str | None`.
  - [x] Версия считается как `f"{label}-{sha256(text.encode('utf-8')).hexdigest()[:8]}"`. Текст в JSON хранится уже нормализованным (одна строка, одиночные пробелы).
  - [x] Загрузчик падает с внятным исключением на непривязанной паре и на дубле версий — молчаливый `unknown` из него выйти не может.

- [x] **Task 2. Модель и миграция** (AC1)
  - [x] `backend/apps/common/models.py`: добавить `SOURCE_CHOICES` и константы (`SOURCE_NEWSLETTER`, `SOURCE_REGISTRATION`, `SOURCE_1C_LINK`, `SOURCE_UNKNOWN`), поля `source` (`max_length=20`, `choices`, `db_index=True`, **без** `default`) и `consent_text_version` (`max_length=64`, `db_index=True`, **без** `default`).
  - [x] Добавить в `Meta.constraints` два `CheckConstraint` — `userconsent_source_required`, `userconsent_text_version_required` — с обязательным `# type: ignore[call-arg]  # django-stubs 4.2 не знает condition=`.
  - [x] Написать **вручную** `backend/apps/common/migrations/0019_userconsent_source_and_text_version.py`: два `AddField` с `default="unknown"` и `preserve_default=False`, затем два `AddConstraint`. Зависимость — `("common", "0018_seed_manager_routing_rules")`.
  - [x] Проверить: `makemigrations --check --dry-run` ничего не предлагает; `migrate` в test-контейнере проходит.
  - [x] `__str__` не менять.

- [x] **Task 3. Точки записи** (AC3, AC4)
  - [x] `backend/apps/common/views.py:420-428`: добавить в `consent_kwargs` `source="newsletter"`, а версию проставить **отдельно каждой записи** — обе записи подписки берут версию `newsletter_checkbox`, но получают её через `current_consent_text_version("newsletter", <тип>)`, а не литералом.
  - [x] `backend/apps/users/views/authentication.py:140-160`: вычислить `consent_source = "1c_link" if pending_1c_link else "registration"` **после** существующего вычисления `pending_1c_link` и до первой вставки; передать `source` и `consent_text_version` в обе `create`.
  - [x] Русские комментарии у обеих правок: почему источник берётся из `pending_1c_link` и почему версия не хардкодится (NFR-41-03).

- [x] **Task 4. Админка** (AC6)
  - [x] `backend/apps/common/admin.py:302-326`: добавить `source` и `consent_text_version` в `list_display`, `list_filter` и `readonly_fields`. Запреты add/change/delete не трогать.

- [x] **Task 5. Унификация формулировок регистрации** (AC4) — *решение Alex 2026-09-09: выполнять, см. «Решения владельца по объёму»*
  - [x] `frontend/src/components/auth/B2BRegisterForm.tsx:486-508`: привести текст чекбокса ПДн к формулировке `RegisterForm` — префикс «Я даю согласие на обработку моих персональных данных в соответствии с», ссылка ««Политикой обработки персональных данных»», суффикса нет. Убрать `b2b-register-pdp-consent-label-suffix` из `aria-labelledby` (строка 474) вместе с самим суффиксным `<label>` — оставшийся в списке несуществующий id молча урежет доступное имя.
  - [x] `frontend/src/components/auth/B2BRegisterForm.tsx:532`: «Я согласен(на)» → «Я согласен (на)» (дословное совпадение с `RegisterForm.tsx:479`).
  - [x] Обновить затронутые ожидания в `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx` (в т.ч. строка 36).
  - [x] Внешний вид, порядок элементов и поведение форм не меняются — правка только текстовая.

- [x] **Task 6. Страж текста на фронте** (AC4)
  - [x] Создать `frontend/src/__tests__/consent-texts-registry.test.tsx` — рядом с существующими кросс-граничными стражами (`app-routes-allowlist.test.ts`, `next-config-headers.test.ts`).
  - [x] Читать `backend/apps/common/consent_texts.json` через `path.dirname(fileURLToPath(import.meta.url))` + `'..','..','..','backend','apps','common','consent_texts.json'` (образец разрешения пути — `SiteJsonLd.test.tsx:25-32`).
  - [x] Для каждой из четырёх форм отрисовать её и найти чекбокс по доступному имени из реестра: `screen.getByRole('checkbox', { name: <текст ревизии> })`. Так уже сделано в существующих тестах форм — там имя задано литералом; здесь оно приходит из реестра.
  - [x] Моки, без которых формы не отрисуются (взять из существующих тест-файлов форм): `next/navigation` → `useRouter` с `push`; `@/services/authService` → `default` с `register`, `registerB2B`, `refreshToken`; `@/services/subscribeService` → `subscribeService.subscribe`; `react-hot-toast` → `toast.success` / `toast.error`.
  - [x] Файл реестра отсутствует или не парсится → тест **падает** с сообщением, называющим ожидаемый путь. Никаких `skipIf`.

- [x] **Task 7. Приведение существующих тестов** (AC7)
  - [x] `backend/apps/common/tests/test_user_consent.py`: семь прямых `UserConsent.objects.create` (строки 31, 50, 64, 76, 88, 112, 123) получают `source` и `consent_text_version`; `test_user_consent_admin_is_read_only` (161-170) приводится к новому `readonly_fields`.
  - [x] `backend/tests/integration/test_common_subscribe_api.py:369` — тот же приём для прямого `create`.
  - [x] `backend/tests/integration/test_auth_registration_consent.py:591-592` — комментарий «policy_version в этой стори осмысленно не заполняется (объём 41.9)» заменить на проверку новых полей; сам `policy_version == "1.0"` остаётся верным и сохраняется.
  - [x] Прогнать оба integration-файла целиком и убедиться, что упавших нет.

- [x] **Task 8. Новые тесты** (AC3, AC4, AC5, AC7)
  - [x] `backend/apps/common/tests/test_consent_texts.py` (unit): все живые пары привязаны; версия меняется при смене текста (две ревизии в фикстуре, не правкой файла); `resolve_consent_text` возвращает текст исторической ревизии; версии уникальны.
  - [x] `backend/apps/common/tests/test_user_consent.py`: `CheckConstraint` роняет вставку с пустым `source` и с пустой версией; `db_index` у обоих полей; `unknown` присутствует в `SOURCE_CHOICES`.
  - [x] `backend/tests/integration/test_common_subscribe_api.py`: `source == "newsletter"` и версия у обеих записей — анонимный и авторизованный случаи.
  - [x] `backend/tests/integration/test_auth_registration_consent.py`: `source == "registration"` и две версии (ПДн + маркетинг); ветка привязки через существующий помощник `_pending_create` (строки 540-562) даёт `source == "1c_link"` при тех же версиях.
  - [x] Маркеры руками не ставить — их проставляет `pytest_collection_modifyitems` по каталогу.

- [x] **Task 9. Проверка обратной совместимости миграции** (AC1)
  - [x] На локальной dev-БД: до применения `0019` вставить строку в `common_userconsent` (`docker compose --env-file .env -f docker/docker-compose.yml exec db psql -U <user> -d <db>`), применить миграцию, прочитать строку — `source` и `consent_text_version` равны `unknown`, остальные поля не изменились.
  - [x] Записать фактический вывод в Debug Log References. Автотест обратной совместимости **не** писать: `django-test-migrations` в проекте нет, а откат/накат общей тестовой БД внутри прогона ломает соседние тесты.
  - [x] Перед выкатом проверить на проде `SELECT count(*) FROM common_userconsent;` — на 2026-08-30 было 0 строк; если появились, значение `unknown` у них ожидаемо и допустимо.

- [x] **Task 10. Документация** (AC1, AC6)
  - [x] `docs/architecture/02-data-models.md:54-63` — добавить два поля в ER-блок `UserConsent`.
  - [x] `docs/architecture/09-database-schema.md:378-408,522-527` — DDL, два новых CHECK-ограничения, два индекса, упоминание миграции `0019`.
  - [x] `docs/architecture/04-component-structure.md:154-164` — реестр `consent_texts.json` / `consent_texts.py` и миграция `0019` в перечне.
  - [x] `docs/architecture/11-security-performance.md:948-966` — описать источник и версию текста в разделе 152-ФЗ.
  - [x] `docs/architecture/18-b2b-verification-workflow.md:206` — утверждение «`UserConsent` для этого пути не создаётся» **неверно с 2026-09-05** (стори 41.2). Исправить: запись создаётся, источник `1c_link`.
  - [x] `docs/architecture/index.md` — строка в «История изменений».
  - [x] `_bmad-output/implementation-artifacts/deferred-work.md` — запись: `policy_version` остаётся константой, версия текста политики (модель `Page`, slug `privacy-policy`) не фиксируется; чекбокс ссылается на политику, но какая её редакция действовала в момент согласия — из журнала не восстановить.

- [x] **Task 11. Прогон и сдача** (AC7)
  - [x] Backend: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest apps/common tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py`, затем полный `make test`-эквивалент. Два прогона в одном compose-проекте параллельно **не** запускать.
  - [x] Backend-статика: `flake8`, `black --check`, `mypy`.
  - [x] Frontend: `npm run test`, `npx tsc --noEmit`, `npm run lint`, `npm run format:check`. Числа «до» и «после» записать.
  - [x] `npx gitnexus detect-changes --scope all` перед коммитом; расхождения объяснить.
  - [x] `File List` собрать командой `git diff --name-status`, а не по памяти.

### Review Findings

- [x] [Review][Patch] Синхронизировать ручной `RegisterRequest` с обязательной маркетинговой версией: сейчас тип допускает `marketing_consent: true` без `marketing_consent_text_version`, хотя generated-контракт помечает версию обязательной, backend отклоняет такую комбинацию, а обе формы уже всегда отправляют версию. Сделать `marketing_consent_text_version` обязательным, чтобы новый типизированный вызов `authService.register*` не компилировал заведомо отклоняемый payload. [`frontend/src/types/api.ts:143-160`]
  - Сделано: поле стало обязательным. Расхождение закреплено стражем
    `frontend/src/__tests__/register-request-contract.test.ts`: проверка компиляционная — payload без версии
    помечен `@ts-expect-error`, и если поле снова сделают необязательным, `tsc` упадёт на неиспользованной
    директиве. RED-фаза снята явно: временное `marketing_consent_text_version?: string` дало обе ожидаемые
    ошибки (`TS2322` на присваивании и `TS2578` на директиве), после отката — чисто. Сверяются в страже
    только consent-поля: у `country` (перечисление в контракте, `string` вручную) и `email` (`| null`)
    типы расходятся давно и по другим причинам.
- [x] [Review][Patch] Выразить в OpenAPI условную обязательность `marketing_consent_text_version`: при `marketing_consent: true` backend требует действующую версию, но схема разрешает поле не передавать. Описать зависимость средствами OpenAPI 3.1 и синхронизировать источник `@extend_schema`, контракт и generated types. [`docs/api/openapi.yaml:4982-5006`, `backend/apps/users/serializers.py:105-119,206-209`]
  - Сделано: у компонента `UserRegistrationRequest` появились `if` / `then` (JSON Schema 2020-12, доступна
    в OpenAPI 3.1): при `marketing_consent: true` версия обязательна и непуста (`minLength: 1` —
    `default: ""` в схеме иначе разрешал бы пустую строку, которую сервер отклонит тем же кодом).
    `dependentRequired` не подошёл: он срабатывает на само присутствие `marketing_consent`, а обе формы
    всегда шлют его, в том числе `false`, — версию требовали бы и от них. Источник — не ручная правка YAML:
    условие добавляет `UserRegistrationRequestSchemaExtension` (`OpenApiSerializerExtension`) рядом с
    сериализатором, поэтому `check_openapi_sync` остаётся зелёным. Расширение живёт в
    `apps/users/serializers.py`, а не в отдельном модуле схемы: оно регистрируется самим фактом объявления
    класса, а отдельный модуль пришлось бы импортировать из `AppConfig.ready()`.
- [x] [Review][Patch] Типизировать две формы ответа `400` вместо свободного `object`: сейчас `consent_text_outdated` существует только в prose/examples, а generated types получают `{ [key: string]: unknown }` и не защищают machine-code `error`/`details`. Использовать именованные схемы и `oneOf` для обычных field errors и структурированного отказа. [`docs/api/openapi.yaml:112-142,342-371`]
  - Сделано: новый модуль `backend/apps/common/api_schema.py` объявляет три компонента —
    `FieldValidationErrorResponse` (плоское «поле → список сообщений»), `ConsentTextOutdatedResponse`
    (`error` + `details`) и `ConsentValidationErrorResponse` (`oneOf` из первых двух); оба эндпоинта
    ссылаются на третий. Плоская форма не описывается обычным сериализатором — набор её ключей зависит от
    запроса, а `Serializer` даёт фиксированный `properties`, — поэтому её схему задаёт
    `OpenApiSerializerExtension`, а класс-маркер нужен лишь чтобы drf-spectacular зарегистрировал имя: на
    голый dict он `$ref` не создаёт. У `error` стоит `const`, а не `enum` из одного значения: `enum`
    хук `postprocess_schema_enums` вынес бы отдельным компонентом-перечислением. Результат в типах фронта —
    `error: 'consent_text_outdated'` литералом и `details: { [key: string]: string[] }` вместо прежнего
    `{ [key: string]: unknown }`. Типы не остались лежать без дела: `constants/consentTexts.ts` теперь
    сужает ответ к сгенерированному `ConsentTextOutdatedResponse`, поэтому расхождение машинного кода
    между сервером и фронтом становится ошибкой компиляции.
- [x] [Review][Patch] Добавить `USER_CONSENT_SOURCE_VALUES` в сокращённый Python-пример модели: блок использует константу в `Meta.constraints`, но не объявляет её, поэтому буквальное выполнение примера даёт `NameError`. [`docs/architecture/02-data-models.md:720-815`]
  - Сделано: константа объявлена перед классом — там же, где в коде, — вместе с комментарием, объясняющим,
    почему она модульная, а не атрибут класса. Заодно добавлен псевдоним `SOURCE_VALUES`, который в коде
    есть: без него пример расходился с моделью второй раз.
- [x] [Review][Patch] Привести новые индексы `UserConsent` в DDL к фактической PostgreSQL-схеме: документ показывает вымышленные `idx_userconsent_source` / `idx_userconsent_text_version` и не отражает автоматически созданные `_like`-индексы, тогда как фактические имена уже сняты после миграции. [`docs/architecture/09-database-schema.md:421-427`]
  - Сделано: весь блок индексов заменён на фактический, снятый запросом
    `SELECT indexname, indexdef FROM pg_indexes WHERE tablename='common_userconsent'` к dev-БД после
    миграции `0020`. Правились не только два новых: вымышлены были все шесть — Django не создаёт ни
    `idx_*`-имён, ни частичных `WHERE`, ни `DESC`, а каждому индексируемому `varchar` добавляет парный
    `_like` с `varchar_pattern_ops`. Оставить половину блока настоящей, а половину придуманной значило бы
    сделать документ хуже, чем он был. Заодно исправлено «и два индекса» в сводке раздела: их четыре.
- [x] [Review][Patch] Обновить пример payload B2B-регистрации: в нём отсутствуют обязательные `pdp_consent` и `pdp_consent_text_version`, поэтому показанный как действующий запрос получает `400 consent_text_outdated`; добавить consent-поля и указать источник актуальных версий. [`docs/architecture/18-b2b-verification-workflow.md:124-145`]
  - Сделано: в пример добавлены все четыре consent-поля, а под ним — предупреждение: версии в документе
    **устаревают** при каждой правке формулировки, поэтому копировать их отсюда нельзя; канонический
    источник — реестр `consent_texts.json` и собранная из него константа фронта. Там же названо, что
    `marketing_consent_text_version` обязателен только при `marketing_consent: true`. Список шагов
    валидации дополнен сверкой версий и записью двух `UserConsent` с `source = "registration"`.
- [x] [Review][Patch] Ослабить завышенные compliance-гарантии до фактически обеспеченных: строка версии подтверждает совместимость официального frontend-бандла, но произвольный API-клиент может прислать её без показа текста; БД гарантирует допустимый `source` и лишь непустую версию, а append-only обеспечен admin/API-путями, но не ORM/SQL. [`docs/architecture/11-security-performance.md:948-987`, `docs/architecture/02-data-models.md:817-825`]
  - Сделано, три утверждения по отдельности. **Версия текста:** «доказывает, что было на экране» заменено
    на то, что она фактически даёт, — отсекает вкладку, открытую до правки формулировки; произвольный
    API-клиент пришлёт ту же строку, ничего не отрисовав, и сервер такой запрос примет. Связку
    «версия ↔ отрисованный текст» держит только официальный фронт и стережёт Vitest-тест реестра. Та же
    правка внесена в docstring `frontend/src/constants/consentTexts.ts` — оставлять в коде утверждение,
    снятое в документе, значило бы разойтись с самим собой. **Ограничения БД:** названа асимметрия — у
    `source` проверяется принадлежность перечислению, у `consent_text_version` только непустота; версию вне
    реестра база примет, потому что набор действующих версий меняется правкой JSON и CHECK по нему требовал
    бы миграции на каждую правку формулировки. **Append-only:** это ограничение путей (admin-запреты и
    отсутствие API, пишущего что-либо кроме вставки), а не схемы — `objects.update()/delete()` и прямой SQL
    журнал меняют, ни триггера, ни `REVOKE` для роли приложения нет.
- [x] [Review][Patch] Исправить GitNexus audit trail: committed diff `792ce210..HEAD` уже заканчивается на `9743/16069`, а текущая переиндексация рабочего дерева дала `9749/16083`; story ошибочно называет `9743/16069` незакоммиченным сдвигом. [`_bmad-output/implementation-artifacts/Story/41-9-consent-journal-text-version-and-source.md:205-206,819-820,927-932`, `AGENTS.md:164`, `CLAUDE.md:168`]
  - Сделано: числа сняты заново двумя командами. `git diff 792ce210..HEAD -- AGENTS.md CLAUDE.md` даёт
    `9657/15912 → 9743/16069` (по коммитам: `0f6e13e3` → `9695/15982`, `8ef96123` → `9717/16022`,
    `34fbe487` → `9743/16069`); `git diff HEAD -- AGENTS.md CLAUDE.md` — незакоммиченный
    `9743/16069 → 9749/16083`. Запись в File List переписана по этим двум срезам и объясняет, почему
    прежняя формулировка устарела: `9743/16069` был незакоммиченным на момент внесения записи и стал
    закоммиченным в `34fbe487`. Исторические заметки прошлых кругов не переписываются задним числом —
    урок стори 41.3.
- [x] [Review][Patch] Уточнить границы гарантии `known_versions`: список хранится в том же редактируемом JSON, поэтому защищает только от случайной односторонней правки, но не обеспечивает механическую append-only неизменяемость при согласованной замене ревизии и её хеша. Решение Alex: оставить текущий процедурный guard и убрать из кода, тестов и story утверждения о более сильной гарантии. [`backend/apps/common/consent_texts.py:13-16,157-198`, `backend/apps/common/consent_texts.json:31-35`]
  - Сделано: страж оставлен как есть, убраны утверждения о более сильной гарантии. Формулировка «история неизменяема» заменена на «страж от односторонней правки» в docstring модуля и `_check_known_versions`, в тексте ошибки («по нему сверяется история ревизий» вместо «он и делает историю неизменяемой»), в заголовке блока тестов, в комментарии фронтенд-стража, в `11-security-performance.md`, `index.md` и в Completion Notes. Границы названы явно: список лежит в том же редактируемом JSON, согласованная замена ревизии вместе с её строкой пройдёт.
- [x] [Review][Patch] Вывести machine-code `consent_text_outdated` в реальный HTTP JSON и применять его также при отсутствующей версии. Решение Alex: контракт top-level `{error: "consent_text_outdated", details: {...}}`, сохранив массивы строк в `details`; синхронизировать оба endpoint, OpenAPI, frontend-обработку и тесты. Сейчас `ErrorDetail.code` остаётся только во внутреннем `response.data`, JSONRenderer отдаёт массив строк, а пропущенное поле имеет внутренний code `required`. [`backend/apps/common/serializers.py:23-32,73-82`, `backend/apps/users/serializers.py:94-119`, `frontend/src/constants/consentTexts.ts:24-25`]
  - Сделано: `consent_text_outdated_payload()` в `apps/common/serializers.py` собирает `{error: "consent_text_outdated", details: {поле: [строки]}}`; признак — любая ошибка на полях версии (`CONSENT_TEXT_VERSION_FIELDS`) или DRF-код `consent_text_outdated`, поэтому пропущенное поле с внутренним кодом `required` попадает в ту же ветку. `details` сохраняет **все** ошибки запроса, чтобы попутная ошибка email не пропала. Оба эндпоинта возвращают тело до прочих веток (`subscribe` — раньше нейтрального «уже подписан», чтобы недоказанная версия не дала ложный успех). `_has_error_code` переехал в сериализаторы как публичный `has_error_code` — им теперь пользуются оба места. Тесты сверяют **отрендеренный** `response.json()`, а не `response.data`. Фронт: `getConsentTextOutdatedMessage()` в `constants/consentTexts.ts`, обработка во всех четырёх формах, машинный код прокинут через `SubscribeServiceError.code`. OpenAPI — см. следующий пункт.
- [x] [Review][Patch] Исправить невалидный OpenAPI-пример подписки и описание 400: `SuccessfulSubscriptionRequest` не содержит обязательный `consent_text_version`, поэтому скопированный из Swagger запрос получает 400; описание ответа перечисляет только `email` и `pdp_consent`. Обновить источник `@extend_schema` и синхронизировать `openapi.yaml`. [`backend/apps/common/views.py:325-329`, `docs/api/openapi.yaml:98-112,4615-4623`]
  - Сделано: в `successful_subscription_request` добавлен обязательный `consent_text_version`; описание 400 обоих эндпоинтов называет обе формы ответа. Попутно выяснилось, **почему** пример не ловился контрактом: без `response=` drf-spectacular выбрасывает примеры целиком — у 400 не было `content`, и ни один пример в схему не попадал. Обоим 400 задан `response=OpenApiTypes.OBJECT` (у ответа две формы, одной схемой их не описать), после чего примеры видны в контракте и в Swagger UI. `docs/api/openapi.yaml` правился точечно, сверен `check_openapi_sync` → «Контракт синхронен с кодом»; типы фронта перегенерированы.
- [x] [Review][Patch] Синхронизировать полный Python-блок `UserConsent` в data-models: Mermaid уже содержит новые поля, но основной пример модели не показывает `SOURCE_CHOICES`, `source`, `consent_text_version` и два новых CheckConstraint. Документ противоречит сам себе и текущей модели. [`docs/architecture/02-data-models.md:54-65,720-763`]
  - Сделано: в блок добавлены `SOURCE_CHOICES` с константами, поля `source` и `consent_text_version` и два новых `CheckConstraint`; в «Ключевые инварианты» — две строки про обязательность полей на уровне БД и про вычисление версии. Под блоком помечено, что он сокращён (в коде у каждого `CheckConstraint` есть `# type: ignore[call-arg]`), и назван канонический источник.
- [x] [Review][Patch] Исправить описание латентной привязки к 1С: раздел утверждает, что система сейчас автоматически связывает найденного 1С-клиента и создаёт `UserConsent(source="1c_link")`, хотя `_link_matched_1c_customer` не вызывается с 2026-07-26 и ветка недостижима по HTTP. Описать её как отключённый/латентный сценарий, для которого поведение согласия сохранено на случай безопасного возврата. [`docs/architecture/18-b2b-verification-workflow.md:195-210`, `backend/apps/users/serializers.py:335-347`]
  - Сделано: раздел переименован в «Этап 2.5: … — ОТКЛЮЧЕНА (латентный сценарий)» и открывается предупреждением: ветка мертва с `ffee94d5` (2026-07-26), по HTTP недостижима, причина отключения названа. Описание переведено в сослагательное: поведение согласия сохранено на случай безопасного возврата, `pending_1c_link` сегодня всегда ложен, ветка покрыта тестами через патч сериализатора, а не по HTTP.
- [x] [Review][Patch] Убрать ложное утверждение о строгом JSON boolean при регистрации из security-документа либо явно пометить известную асимметрию до закрытия defer: сейчас DRF `BooleanField` принимает ряд truthy-значений. [`docs/architecture/11-security-performance.md:956-961`, `backend/apps/users/serializers.py:81-89,193-194`]
  - Сделано: строка «JSON boolean, строгая — не `"true"` / `1`» заменена. Асимметрия названа явно: строгую проверку делает только подписка (`initial_data … is not True`), регистрация на DRF `BooleanField` принимает truthy-значения; дано указание не утверждать строгость до закрытия записи в `deferred-work.md`.
- [x] [Review][Patch] Заменить хрупкие line-number ссылки dev-task на устойчивые ссылки по заголовкам/тексту: добавление новых записей в начало `deferred-work.md` уже сдвинуло `:1025`, `:1037`, `:1039`, `:1041-1045` на чужие пункты. [`_bmad-output/implementation-artifacts/tasks/dev-task-textcontent-price-cta-separation.md:31-33,56-57,282-287`]
  - Сделано: все четыре ссылки на `deferred-work.md` переведены на цитаты заголовков пунктов (§2, §8.1 и §10). В §10 добавлено пояснение, почему номера строк здесь не работают: новые записи добавляются сверху и сдвигают нумерацию.
- [x] [Review][Patch] Исправить описание побочного GitNexus diff в File List: фактический committed diff `792ce210..0f6e13e` меняет счётчики `9657/15912` на `9695/15982`, а story указывает `9647/15902`; последующие незакоммиченные `9717/16022` в branch diff не входят. [`_bmad-output/implementation-artifacts/Story/41-9-consent-journal-text-version-and-source.md:670-673`, `AGENTS.md:164`, `CLAUDE.md:168`]
  - Сделано: числа сверены `git diff`. В коммитах стори (`792ce210..0f6e13e3`) счётчик сдвинулся `9657/15912 → 9695/15982`; незакоммиченный сдвиг рабочего дерева `9695/15982 → 9717/16022` в дифф ветки не входит. Прежняя запись `→ 9647, 15902` была неверна и направлением, и значениями.
- [x] [Review][Defer] Ручная архитектурная спецификация `/auth/register/` давно расходится с каноническим OpenAPI и serializer: неверные роли и обязательные поля, отсутствуют consent version fields [`docs/architecture/03-api-specification.md:27-72`] — deferred, pre-existing
- [x] [Review][Defer] Регистрация принимает truthy-значения `pdp_consent`, не являющиеся JSON boolean `true` [`backend/apps/users/serializers.py:81-89,193-194`] — deferred, pre-existing
- [x] [Review][Patch] Сервер должен отклонять устаревшую версию текста согласия — решение Alex: форма передаёт показанную версию, сервер сравнивает её с текущей; при несовпадении запрос отклоняется с требованием обновить страницу. Сейчас формы отправляют только boolean-согласие, а `current_consent_text_version(...)` всегда фиксирует текущую серверную версию, даже если пользователь отправил старую вкладку с прежним текстом. [`backend/apps/users/views/authentication.py:157-174`, `backend/apps/common/views.py:437-445`, `frontend/src/components/auth/RegisterForm.tsx:111-133`, `frontend/src/components/auth/B2BRegisterForm.tsx:111-129`]
  - Версия зашита в бандл фронта (`frontend/src/constants/consentTexts.ts`), а **не** запрашивается у сервера: она обязана доказывать, какой текст был на экране. Версия, полученная запросом в момент отправки, всегда актуальна и не доказывает ничего — старая вкладка получила бы свежее значение и записала согласие на формулировку, которой не видела.
  - `SubscribeSerializer.consent_text_version` (обязательное), `UserRegistrationSerializer.pdp_consent_text_version` (обязательное) и `marketing_consent_text_version` (обязательное при `marketing_consent: true`). Несовпадение или отсутствие — `400`, код `consent_text_outdated`, сообщение «Текст согласия обновился. Обновите страницу и подтвердите согласие заново.».
  - В журнал по-прежнему кладётся значение из реестра, а не присланное клиентом: запрос лишь доказывает право записать текущую версию.
  - Контракт обновлён по правилу проекта: `docs/api/openapi.yaml` (перегенерирован `spectacular`, сверен `check_openapi_sync`) и `npm run generate:types`.
- [x] [Review][Patch] Исторические версии не защищены от изменения или удаления ревизии из реестра [`backend/apps/common/consent_texts.py:98-133`]
  - Раздел `known_versions` — список версий всех когда-либо действовавших формулировок; загрузчик требует **точного** совпадения с набором, вычисленным из ревизий. Односторонняя правка текста старой ревизии и её удаление ловятся одинаково: версия исчезает из вычисленного набора, реестр перестаёт загружаться и называет пропавшие строки. Новая ревизия тоже обязана быть внесена — её версию не нужно считать руками, сообщение об ошибке печатает готовую строку. Границы гарантии уточнены отдельным замечанием ревью (см. первый пункт списка): это процедурный страж, а не механическая неизменяемость.
- [x] [Review][Patch] JSON-загрузчик молча принимает повторяющиеся ключи и может подменить поверхность либо привязку [`backend/apps/common/consent_texts.py:194-199`]
  - `json.loads(..., object_pairs_hook=_reject_duplicate_keys)`: повтор ключа — `ConsentTextsError`, а не «побеждает нижний».
- [x] [Review][Patch] Загрузчик допускает версию длиннее `UserConsent.consent_text_version(max_length=64)` [`backend/apps/common/consent_texts.py:105-124`]
  - Константа `MAX_VERSION_LENGTH = 64` в модуле (Django он не импортирует — тот же JSON читает страж на фронте); расхождение с полем модели ловит `test_max_version_length_matches_model_field`.
- [x] [Review][Patch] В diff присутствует посторонний task-файл, отсутствующий в заявленном File List [`_bmad-output/implementation-artifacts/tasks/dev-task-textcontent-price-cta-separation.md:1-6`]
  - Файл добавлен коммитом `786881e7` («создать стори … и dev-task по склейкам textContent») — то есть частью создания стори, а не её реализации; в диффе ветки против `develop` он поэтому присутствует. Файл нужен (задача-продолжение стори 41.8) и не удаляется; он назван в File List отдельным разделом.
- [x] [Review][Defer] Celery-задачи B2B-регистрации публикуются до фиксации транзакции и могут получить ID откатившегося пользователя [`backend/apps/users/serializers.py:266-271`] — deferred, pre-existing
- [x] [Review][Decision] Оставить в админке только `consent_text_version` — решение Alex: буквальный AC6 считается достаточным; дословный текст при необходимости разрешается через реестр и `resolve_consent_text()`, операторский интерфейс не расширяем. [`backend/apps/common/admin.py:311-332`, `backend/apps/common/consent_texts.py:304-306`]
- [x] [Review][Patch] Ограничить `UserConsent.source` допустимыми значениями на уровне БД: Django `choices` не запрещает сохранить произвольную непустую строку, а текущий `CheckConstraint` отсекает только `""`; для юридически значимого аудита значение вне `newsletter` / `registration` / `1c_link` / `unknown` является тихим мусором. [`backend/apps/common/models.py:666-701`, `backend/apps/common/migrations/0019_userconsent_source_and_text_version.py:57-69`]
  - Сделано: `userconsent_source_required` (`CHECK (source <> '')`) заменён на `userconsent_source_valid`
    (`CHECK (source IN ('newsletter','registration','1c_link','unknown'))`) миграцией
    `0020_userconsent_source_valid`. Новое ограничение строго сильнее прежнего — пустая строка в список не
    входит, поэтому оба существующих теста пустого источника остались зелёными без правки, а отдельное
    `..._source_required` избыточно и снято. Список значений объявлен модульной константой
    `USER_CONSENT_SOURCE_VALUES`, а не атрибутом класса: тело вложенного `class Meta` не видит пространство
    имён внешнего класса (Python пропускает class scope), а `CheckConstraint` нужен именно там; синхронность
    с `SOURCE_CHOICES` держит `test_source_values_match_choices`. Новый тест
    `test_source_outside_choices_violates_check_constraint` роняет `objects.create(source="registartion")` —
    путь, который `choices` не закрывают вовсе (они работают на формах и `full_clean()`).
- [x] [Review][Patch] Оборачивать ошибку декодирования реестра в `ConsentTextsError`: `Path.read_text(encoding="utf-8")` может поднять `UnicodeDecodeError`, который не является `OSError`, поэтому повреждённый по кодировке реестр нарушает обещание загрузчика выдавать единое понятное исключение с путём. [`backend/apps/common/consent_texts.py:278-289`]
  - Сделано: у `load_registry` добавлена ветка `except UnicodeDecodeError` (он наследуется от `ValueError`,
    а не от `OSError`, поэтому мимо прежнего `except` проходил насквозь). Сообщение называет путь и причину
    — «не читается как UTF-8». Тест `test_broken_encoding_raises_consent_texts_error` пишет реестр в CP1251.
- [x] [Review][Defer] Устранить TOCTOU-гонку регистрации по email: два параллельных запроса могут одновременно пройти `exists()`, после чего второй получает необработанный `IntegrityError` на `create_user` вместо контролируемого ответа о занятом email. [`backend/apps/users/serializers.py:240-246,289-305`] — deferred, pre-existing
- [x] [Review][Patch] При `consent_text_outdated` формы подписки должны приоритизировать сообщение поля версии: сейчас `getFirstBackendError()` берёт первое значение из `details`, поэтому смешанный ответ `{email, consent_text_version}` показывает ошибку email вместо требования обновить страницу. В `consentTexts.ts` уже есть `getConsentTextOutdatedMessage()`, который сортирует поля версии первыми. Добавить regression-тесты смешанного `details` для обеих subscribe-форм — текущие тесты передают только `consent_text_version` и пропускают дефект. [`frontend/src/components/home/SubscribeForm.tsx:55-76,120-124`, `frontend/src/components/home/ElectricSubscribeForm.tsx:56-77,129-136`, `frontend/src/constants/consentTexts.ts:61-82`, `frontend/src/components/home/__tests__/SubscribeForm.test.tsx:169-188`, `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx:242-279`]
  - Сделано: обе формы подписки перешли с `getFirstBackendError()` на `getConsentTextOutdatedMessage()`
    (он уже сортировал поля версии первыми и применялся в формах регистрации) через локальный
    `getConsentOutdatedMessage()`, собирающий из `SubscribeServiceError` тот же вид ответа `{error, details}`.
    Regression-тесты со смешанным `details` (`{email, consent_text_version}`) добавлены обеим формам; до
    правки падали ровно они (2 failed / 36 passed), после — 38 passed.
- [x] [Review][Patch] Исправить ложноположительную проверку отката пользователя при устаревшей PDP-версии: тест второй раз вызывает `trainer_payload()`, который генерирует новый уникальный email, поэтому ошибочно созданный пользователь по email исходного запроса останется незамеченным. Сохранить payload в переменную и проверять именно `payload["email"]`. [`backend/tests/integration/test_auth_registration_consent.py:113-131`]
  - Сделано: payload сохраняется в переменную, проверка идёт по `payload["email"]`. Тот же приём применён к
    соседнему `test_registration_requires_pdp_text_version`, где проверки отката не было вовсе — отсутствие
    пользователя там теперь тоже утверждается.
- [x] [Review][Patch] Добавить тест отсутствующей `marketing_consent_text_version` при `marketing_consent=True`: поле опционально на уровне DRF и становится обязательным условно в `validate()`, но сейчас проверены только устаревшая версия и отсутствие PDP-версии. Тест должен ожидать `400 consent_text_outdated`, поле `marketing_consent_text_version` в `details` и отсутствие пользователя/согласий. [`backend/apps/users/serializers.py:105-119,206-209`, `backend/tests/integration/test_auth_registration_consent.py:134-195`]
  - Сделано: `test_registration_requires_marketing_text_version_when_consent_given` — поле удаляется из
    payload при `marketing_consent=True`, ожидается `400` с телом
    `{error: consent_text_outdated, details: {marketing_consent_text_version: [...]}}`, отсутствие
    пользователя по тому же email и ноль записей `UserConsent`. Путь «поле отсутствует» на уровне DRF молчит
    (`required=False`, `default=""`) и доходит до `validate()` уже пустой строкой — ветка отказа там та же,
    что у устаревшей версии, но добирается до неё иначе, поэтому проверяется отдельным тестом.
- [x] [Review][Defer] Привести URL подписки к каноническому `/subscribe/`: сервис отправляет POST на `/subscribe` без завершающего slash, тогда как Django route и OpenAPI используют `/subscribe/`; при стандартном `APPEND_SLASH=True` редирект POST может потерять метод или тело. [`frontend/src/services/subscribeService.ts:75-78`, `backend/apps/common/urls.py:19`] — deferred, pre-existing
- [x] [Review][Defer] Сделать валидацию `tax_id` в `B2BRegisterForm` зависимой от страны: текущая схема пропускает только российские 10/12 цифр и блокирует валидный 9-значный УНП Беларуси, хотя backend принимает 8–12 цифр для Беларуси/Казахстана. [`frontend/src/schemas/authSchemas.ts:154-163`, `backend/apps/users/serializers.py:232-238`] — deferred, pre-existing

## Dev Notes

### Что есть сейчас (проверено чтением файлов на `792ce210`)

`UserConsent` (`backend/apps/common/models.py:587-664`) хранит: `user` (nullable FK, `SET_NULL`), `session_key` (для анонимов), `consent_type` (`pdp_contract` | `marketing_email`), `given_at` (`auto_now_add`), `ip_address` (nullable `inet`), `user_agent` (`max_length=512`), `policy_version` (`default="1.0"`, никем осмысленно не заполняется). Единственное ограничение — `userconsent_user_or_session_required` (`models.py:649-653`). Журнал append-only: админка запрещает add/change/delete.

Записи создаются в двух местах:

| Файл, строки | Ветка | Что пишет | Источник (после стори) |
|---|---|---|---|
| `apps/common/views.py:417-428` | подписка на рассылку | всегда две записи, `pdp_contract` + `marketing_email`, общий `consent_kwargs` | `newsletter` |
| `apps/users/views/authentication.py:147-160` | регистрация, `pending_1c_link` ложен | `pdp_contract` + опционально `marketing_email` по флагу `_marketing_consent` | `registration` |
| `apps/users/views/authentication.py:147-160` | та же строка кода, `pending_1c_link` истинен | то же | `1c_link` |

Третьей строки в таблице нет по ошибке — это одна и та же пара `create`, различаемая уже вычисленным флагом. `pending_1c_link` собирается на `authentication.py:140-142` из `_pending_admin_review` / `_pending_link_confirmation`, которые выставляет `UserRegistrationSerializer._link_matched_1c_customer` (`serializers.py:281-330`). Метод **мёртв** с `ffee94d5` (2026-07-26): вызовов нет, автопривязка отключена. Значит ветка `1c_link` сегодня недостижима по HTTP — тестируется патчем сериализатора, готовый помощник `_pending_create` уже лежит в `backend/tests/integration/test_auth_registration_consent.py:540-562`.

Вспомогательные функции записи — `get_consent_ip_address` и `sanitize_consent_user_agent` (`apps/common/utils/consent_audit.py:121-153`). Их не трогаем.

### Тексты согласий на baseline (дословно, координаты проверены)

| Поверхность | Где отрисовывается | Текст |
|---|---|---|
| `newsletter_checkbox` | `SubscribeForm.tsx:169-184`, `ElectricSubscribeForm.tsx:228-243` — **тексты идентичны** | `Я даю согласие на обработку моих персональных данных в соответствии с «Политикой обработки персональных данных» и согласен(на) получать информационные и рекламные рассылки от OPTISPORT по электронной почте` |
| `registration_pdp_checkbox` | `RegisterForm.tsx:438-455` | `Я даю согласие на обработку моих персональных данных в соответствии с «Политикой обработки персональных данных»` |
| — то же, вариант B2B | `B2BRegisterForm.tsx:484-509` | `Я даю согласие на обработку моих персональных данных в соответствии с Политикой` |
| `registration_marketing_checkbox` | `RegisterForm.tsx:467-481` | `Я согласен (на) получать рекламные и информационные рассылки от OPTISPORT` |
| — то же, вариант B2B | `B2BRegisterForm.tsx:520-533` | `Я согласен(на) получать рекламные и информационные рассылки от OPTISPORT` |

Расхождений два: у ПДн B2B-форма не называет политику по имени, у маркетинга — отличается один пробел. Оба варианта уходят после Task 5; в реестр заносится формулировка `RegisterForm` (она полнее — политика названа и на неё ведёт ссылка).

Текст в JSON хранится в нормализованном виде: одна строка, между словами один пробел, без ведущих и хвостовых пробелов. В JSX он разбит на три узла (`label` + `Link` + `label`), и доступное имя, которое собирает testing-library, уже нормализовано так же — сравнение будет посимвольным без дополнительной обработки.

### Реестр: структура и API

```json
{
  "surfaces": {
    "newsletter_checkbox": {
      "revisions": [{ "label": "2026-08-30", "text": "Я даю согласие ... по электронной почте" }]
    },
    "registration_pdp_checkbox": {
      "revisions": [{ "label": "2026-09-09", "text": "Я даю согласие ... персональных данных»" }]
    },
    "registration_marketing_checkbox": {
      "revisions": [{ "label": "2026-09-09", "text": "Я согласен (на) получать ... от OPTISPORT" }]
    }
  },
  "bindings": {
    "newsletter.pdp_contract": "newsletter_checkbox",
    "newsletter.marketing_email": "newsletter_checkbox",
    "registration.pdp_contract": "registration_pdp_checkbox",
    "registration.marketing_email": "registration_marketing_checkbox",
    "1c_link.pdp_contract": "registration_pdp_checkbox",
    "1c_link.marketing_email": "registration_marketing_checkbox"
  }
}
```

Три вещи, которые легко сделать неправильно:

1. **Подписка привязана к одной поверхности дважды.** Чекбокс там один и покрывает оба согласия (редакция 2 стори 41.3) — обе записи обязаны получить одну и ту же версию. Это не дубль в конфиге, а факт формы.
2. **`1c_link` ссылается на те же поверхности, что и `registration`.** Человек заполнял ту же форму регистрации; отличается исход, а не текст. Отдельных текстов для привязки заводить нельзя — их не существует.
3. **Метка ревизии — дата, когда формулировка стала действующей.** Для подписки это `2026-08-30` (правка стори 41.3). Для обеих регистрационных поверхностей — дата **этой** стори, потому что Task 5 меняет B2B-вариант; до унификации единой действующей формулировки не было. История ревизий пуста не потому, что её решили не вести, а потому, что журнал пуст: на 2026-08-30 в `common_userconsent` на проде 0 строк.

Версия: `f"{label}-{sha256(text.encode('utf-8')).hexdigest()[:8]}"`, например `2026-08-30-3f9ac21b`. Метка читается человеком в админке, хеш делает пропуск бампа невозможным: правка текста меняет версию сама, без дисциплины разработчика. `max_length=64` взят с запасом.

`resolve_consent_text(version)` ищет по всем ревизиям всех поверхностей — иначе версия, оставшаяся в старых строках после переименования привязки, перестала бы разрешаться.

### Почему страж живёт на фронте, а не на бэкенде

Единственный способ поймать расхождение «текст в форме поехал, реестр не обновили» — сравнить отрисованную форму с реестром. Бэкенд этого не может: в test-контейнер смонтирован только `backend/` (`docker/docker-compose.test.yml:70`), файлов фронта там нет. Vitest может: `frontend-ci.yml` делает `actions/checkout` целиком и запускает `npm run test:coverage` из `frontend/`, соседний `backend/` лежит рядом на диске.

Отсюда требование «падать, а не пропускаться». Страж, который молча скипается при ненайденном файле, охраняет ровно ничего — это буквально находка ревью стори 41.6 («тест, проверяющий мок, не охраняет ничего»). Если однажды frontend-тесты станут гонять внутри контейнера `frontend` (контекст сборки — `frontend/`), страж упадёт и потребует смонтировать реестр; это правильное поведение, а не дефект.

### Ловушки, на которых легко потерять день

- **Не давать полям `default` в модели.** С `default="unknown"` забытый источник тихо запишется как «неизвестно» — ровно та беда, которую стори чинит. Одноразовое значение живёт **только** в миграции (`preserve_default=False`).
- **`makemigrations` спросит про default в интерактиве и повиснет.** Миграция пишется руками; `makemigrations --check --dry-run` затем подтверждает, что модель и миграции сошлись.
- **`CheckConstraint` без `# type: ignore[call-arg]` роняет mypy.** В `mypy.ini` включён `warn_unused_ignores`, поэтому лишний игнор тоже ошибка — ставить ровно на строку `models.CheckConstraint(`.
- **Восемь прямых `objects.create` в тестах упадут `IntegrityError`** после появления ограничений. Это не «сломанные тесты», а работающая защита; правятся, а не отключаются.
- **`consent_kwargs` в подписке общий для двух записей.** Версия у обеих одинаковая, но получать её нужно вызовом на каждый тип — иначе при будущем расщеплении чекбоксов дефект вернётся молча. `source` можно класть прямо в `consent_kwargs`.
- **`pending_1c_link` вычисляется внутри `with transaction.atomic()`.** Источник считать там же, рядом; не выносить наружу и не менять структуру блока — на этом уже спотыкались в 41.2.
- **`list_filter` по `consent_text_version` работает без ручного фильтра**: Django для `CharField` без `choices` подставляет `AllValuesFieldListFilter` и сам собирает различные значения. Свой `SimpleListFilter` писать не нужно.
- **`__str__` не трогать** — четыре теста (`test_user_consent.py:83-135`) сверяют его вывод дословно, включая формат даты и локальную таймзону.
- **Не «оптимизировать» две вставки в `bulk_create`** — существующие тесты сверяют `count()` и набор типов, выигрыша нет.
- **Тесты запускать в одном compose-проекте последовательно.** Два параллельных прогона дают лавину ложных падений на дедлоке `TRUNCATE`.

### Уроки предыдущих стори эпика 41

- **41.3 → 41.9:** дефект оказался не там, где его видел эпик (там — «чекбоксов должно быть два», фактически — «текст не тот»). Здесь тот же риск: если по ходу выяснится, что AC неточен, править AC отдельной строкой Change Log, а не «по факту реализации».
- **41.2:** ветка привязки к 1С недостижима по HTTP; тест, который «проверяет регистрацию», в неё не попадёт и проверит пустоту. Использовать готовый `_pending_create`.
- **41.6:** страж, сравнивающий литералы между собой, остаётся зелёным при неверной разметке. Поэтому текст в стражe Task 6 приходит **из реестра**, а не из константы рядом.
- **41.0, 41.4, 41.5, 41.6, 41.7:** `File List` расходился с фактическим диффом в пяти стори подряд. Собирать `git diff --name-status`; побочные правки (автосчётчик GitNexus в `AGENTS.md` / `CLAUDE.md`) вносить отдельным разделом, а не выкидывать.
- **41.6, 41.8:** `[x]` ставится только по факту. В этой стори единственный пункт, который не закрывается автотестом, — Task 9 (проверка миграции на живой БД); он и требует вывода в Debug Log.
- **41.5:** «done по прод-замеру, а не по мержу». Здесь применимо частично: наблюдаемого поведения на проде стори не меняет, но миграция на прод накатывается вручную — приёмка включает `showmigrations` после выката.

### Project Structure Notes

- Реестр кладётся в `backend/apps/common/` рядом с моделью: `consent_texts.json` + `consent_texts.py`. Каталог `apps/common/utils/` занят helper'ами запроса (`consent_audit.py`) — это другой слой, туда не мешать. JSON попадает в образ: `backend/Dockerfile*` делают `COPY . .`, `.dockerignore` `*.json` не исключает.
- Unit-тесты бэкенда — в `backend/apps/common/tests/`, integration — в `backend/tests/integration/`. Маркеры проставляет `pytest_collection_modifyitems` по каталогу; руками не ставить.
- Кросс-граничный страж на фронте — в `frontend/src/__tests__/` (там уже живут `app-routes-allowlist.test.ts`, `next-config-headers.test.ts`, `og-image.test.ts`), не в `components/**/__tests__/`.
- Миграция — `backend/apps/common/migrations/0019_userconsent_source_and_text_version.py`; предыдущая `0018_seed_manager_routing_rules`.
- Комментарии и docstrings нового кода — на русском (NFR-41-03).
- Покрытие меряет только `main.yml` (порог 73, `--cov=apps --cov=freesport`); быстрый гейт `backend-ci.yml` покрытие не считает и `integration` не гоняет. Новые integration-тесты в PR-гейт не попадут — это нормально, их прогонит `main.yml`. Порог калибруется по CI, не по локальному прогону.
- Ветка `feature/story-41-9-*` от `develop`; прямые коммиты в `develop` запрещены. Обе защищённые ветки требуют 5 зелёных обязательных контекстов.
- Новых зависимостей не вводится: `hashlib`, `json`, `pathlib` — стандартная библиотека, `requirements.txt` не меняется.
- Правки `frontend/src/` применяются рестартом контейнера (`docker compose --env-file .env -f docker/docker-compose.yml restart frontend`), пересборка не нужна — конфиг и зависимости не менялись.
- Backend после правок моделей — пересборка/рестарт backend-контейнера и `migrate`; на проде после рестарта backend обязателен дополнительный `restart nginx`.

### Latest tech information

Веб-исследование не требовалось: стори не добавляет и не обновляет ни одной библиотеки. Задействовано только уже установленное — Django 5.2.7 (`AddField`/`AddConstraint`, `CheckConstraint(condition=...)`), DRF 3.14.0, django-stubs 4.2.6 (отсюда обязательный `# type: ignore[call-arg]`), Vitest + Testing Library на фронте. Стандартная библиотека: `hashlib.sha256`, `json`, `pathlib.Path`.

Правовая рамка — ФЗ-152 ст. 9: согласие должно быть конкретным и доказуемым, то есть оператор обязан уметь показать, **на что именно** человек соглашался. Дата, IP и User-Agent это не покрывают; версия формулировки — покрывает.

### Git intelligence

- `792ce210` (HEAD, `develop`) — merge PR #147, закрытие стори 41.8. Последние шесть коммитов — только markdown (`Story/41-8-*.md`, `sprint-status.yaml`); кода они не касались, конфликтов с этой стори нет.
- Индекс GitNexus снят на `318abed` и помечен `stale`, но расхождение с HEAD — исключительно документация, поэтому граф символов актуален. Перед следующей стори индекс стоит переиндексировать.
- `ffee94d5` (2026-07-26) — коммит, сделавший ветку привязки мёртвой. Читать его тело перед работой с `1c_link`.
- Стори 41.2 (PR, 2026-09-05) — предыдущая правка тех же строк `authentication.py`; её решение «запись согласия остаётся в одном месте» — прямая предпосылка Task 3.

### References

- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.9`] — user story, AC-скелет, границы
- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md#NonFunctional Requirements`] — NFR-41-04 и пометка «покрыт частично», NFR-41-01, NFR-41-03
- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md:60-64`] — FR-41-05 редакция 2: один чекбокс подписки покрывает оба согласия
- [Source: `backend/apps/common/models.py:587-664`] — модель, `CONSENT_TYPE_CHOICES` с комментарием о двойной записи, `policy_version`, существующий `CheckConstraint`
- [Source: `backend/apps/common/views.py:417-428`] — точка записи подписки, общий `consent_kwargs`
- [Source: `backend/apps/users/views/authentication.py:132-160`] — `pending_1c_link`, обе вставки, комментарий стори 41.2
- [Source: `backend/apps/users/serializers.py:239-330`] — `create()`, `_marketing_consent`, мёртвый `_link_matched_1c_customer` с флагами
- [Source: `backend/apps/common/admin.py:302-326`] — `UserConsentAdmin`, текущие `list_display` / `list_filter` / `readonly_fields`
- [Source: `backend/apps/common/utils/consent_audit.py:121-153`] — `get_consent_ip_address`, `sanitize_consent_user_agent`
- [Source: `backend/apps/common/migrations/0016_userconsent_review_fixes.py`] — образец `AlterField` + `AddConstraint` для этой модели
- [Source: `backend/apps/common/tests/test_user_consent.py:25-183`] — семь прямых `create`, тест read-only админки со списком полей
- [Source: `backend/tests/integration/test_auth_registration_consent.py:488-495,540-608,672`] — `policy_version`-тест, помощник `_pending_create`, патч `UserConsent.objects.create`
- [Source: `backend/tests/integration/test_common_subscribe_api.py:218-243,362-385`] — тесты двойной записи и прямой `create` в тесте реактивации
- [Source: `frontend/src/components/home/SubscribeForm.tsx:150-186`] — чекбокс подписки, три текстовых узла, `aria-labelledby`
- [Source: `frontend/src/components/home/ElectricSubscribeForm.tsx:224-245`] — тот же текст в electric-теме
- [Source: `frontend/src/components/auth/RegisterForm.tsx:56-60,421-481`] — роли B2C-формы (совпадают с B2B), тексты обоих чекбоксов
- [Source: `frontend/src/components/auth/B2BRegisterForm.tsx:467-533`] — расходящиеся формулировки, подлежащие унификации
- [Source: `frontend/src/components/common/__tests__/SiteJsonLd.test.tsx:18-45`] — образец разрешения пути к файлу и требование «падать, а не пропускаться»
- [Source: `frontend/src/__tests__/app-routes-allowlist.test.ts:21`] — образец кросс-структурного стража в `src/__tests__/`
- [Source: `docker/docker-compose.test.yml:44-71`] — контекст сборки и монтирование только `backend/`
- [Source: `.github/workflows/frontend-ci.yml:29-84`] — полный checkout и запуск тестов из `frontend/`
- [Source: `docs/architecture/02-data-models.md:54-63`, `09-database-schema.md:378-408,522-527`, `04-component-structure.md:154-164`, `11-security-performance.md:948-966`, `18-b2b-verification-workflow.md:206`, `index.md:45-47`] — документация, требующая обновления
- [Source: `_bmad-output/implementation-artifacts/Story/41-2-consent-record-on-1c-link.md`] — ветка привязки, рецепт её тестирования, решение оставить запись в одном месте
- [Source: `project-context.md` §1, §2, §4, §5, §6] — Docker-команды, запреты, автоматические маркеры, GitNexus-дисциплина, язык комментариев
- [Source: `backend/docs/testing-standards.md`] — что гоняют `backend-ci.yml` и `main.yml`, порог покрытия 73 по CI
- [Source: `git ffee94d5`] — отключение автопривязки к 1С

### Решения владельца по объёму

1. **Унификация формулировок регистрации (Task 5) — выполнять. Решение Alex, 2026-09-09; переоткрывать в ходе реализации не нужно.** Эпик говорит «стори не трогает фронтенд-формы». Правка Task 5 формально нарушает эту границу и формально же неизбежна: две живые формы с разными текстами шлют запросы в один эндпоинт, различить их бэкенд не может, и без унификации поле «версия текста» для источника `registration` указывало бы на формулировку, которую часть пользователей не видела. Расширение объёма эпика принято осознанно — прецедент стори 41.4 (починка мёртвой ссылки «Возврат»). Правка чисто текстовая: смысл согласия не меняется, B2B-текст становится полнее (политика названа и на неё ведёт ссылка), разметка, ARIA-связки и поведение форм сохраняются. Отвергнутый вариант Б — объявить одну версию покрывающей обе формулировки — оставлял бы поле точным лишь до «одна из двух».
2. **Автотест обратной совместимости миграции не пишется (Task 9).** `django-test-migrations` в зависимостях нет, а откат и накат миграции внутри общей тестовой БД ломает соседние тесты прогона. Проверка выполняется руками на локальной БД с записью вывода. Альтернатива — добавить зависимость — выходит за объём стори.

## Change Log

| Дата | Версия | Изменение | Автор |
|---|---|---|---|
| 2026-09-09 | 1.0 | Стори создана. Сверх скелета эпика: (а) источников три, а точек записи в коде две — `1c_link` различается уже вычисленным `pending_1c_link`; (б) две живые формы регистрации с разными текстами бьют в один эндпоинт и неразличимы на бэкенде, отсюда Task 5; (в) страж текста обязан жить в Vitest — backend-контейнер не видит `frontend/`; (г) версия считается как метка+хеш текста, чтобы бамп нельзя было забыть; (д) шесть файлов документации архитектуры требуют правки, включая неверное с 2026-09-05 утверждение в `18-b2b-verification-workflow.md:206`. Решение владельца по единственному открытому вопросу получено до старта: Task 5 выполняется. | Alex / create-story |
| 2026-09-09 | 1.1 | Стори реализована. Все 11 задач и 58 подзадач закрыты. Backend 3236 → 3264 passed (+28), падений нет; frontend 2797 → 2803 passed (+6), падений нет. Обратная совместимость миграции проверена руками на dev-БД: строка, созданная до `0019`, сохранилась целиком и помечена `unknown` (вывод — в Debug Log). Единственное отклонение от текста стори — исправлен дефект в собственном тесте `test_empty_revisions_raise` (пустой `bindings` заслонял проверяемую ошибку); поведение кода не менялось. Дополнительно к плану: два новых замечания mypy закрыты точечными `# type: ignore[attr-defined]`, чтобы удержать дельту к базису на нуле (AC7). | Claude Opus 5 / dev-story |
| 2026-09-09 | 1.2 | Закрыты пять замечаний ревью. Главное — сервер больше не проставляет версию текста «за клиента»: формы присылают версию показанной формулировки, сервер сверяет её с реестром и отклоняет несовпадение (`400`, код `consent_text_outdated`). **Утверждение шапки и AC8 «API-контракт не меняется» с этой доработкой недействительно** (правится строкой Change Log, а не задним числом в AC — урок стори 41.3): `SubscribeRequest` получил `consent_text_version`, `UserRegistrationRequest` — `pdp_consent_text_version` и `marketing_consent_text_version`; `docs/api/openapi.yaml` перегенерирован и сверен `check_openapi_sync`, типы фронта — `npm run generate:types`. Прочие четыре замечания: `known_versions` защищает историю ревизий от правки и удаления, дубли ключей JSON отбраковываются, версия длиннее `max_length=64` не проходит загрузку, посторонний task-файл объяснён и назван в File List. Frontend 2803 → 2807 passed (167 файлов, падений нет); backend — числа в Debug Log. | Claude Opus 5 / dev-story |
| 2026-09-09 | 1.3 | Закрыты оставшиеся восемь замечаний ревью. Главное — машинный код `consent_text_outdated` дошёл до клиента: оба эндпоинта отвечают `{error, details}` (прежде код жил только в `ErrorDetail.code`, который JSONRenderer выбрасывает, а у пропущенного поля был и вовсе `required`); фронт разводит этот отказ по коду, а не по тексту сообщения. Заодно найдена причина, по которой невалидный пример подписки не ловился контрактом: без `response=` drf-spectacular выбрасывает `examples` целиком — обоим `400` задан `OpenApiTypes.OBJECT`, и обе формы ответа теперь видны в схеме. **Уточнение к версии 1.2:** утверждение «история ревизий стала неизменяемой» отменяется — `known_versions` лежит в том же редактируемом JSON и ловит только одностороннюю правку; решение владельца — оставить процедурный страж и убрать заявления о более сильной гарантии (правится строкой Change Log, а не задним числом в тексте). Прочие замечания: Python-блок `UserConsent` в `02-data-models.md` приведён к коду; привязка к 1С в `18-b2b-verification-workflow.md` описана как отключённый латентный сценарий; из `11-security-performance.md` убрано ложное утверждение о строгом JSON boolean при регистрации; ссылки dev-task на `deferred-work.md` переведены с номеров строк на заголовки; числа побочного GitNexus-диффа сверены `git diff`. Backend 3279 → 3282 passed, frontend 2807 → 2810 passed, падений нет; `check_openapi_sync` — контракт синхронен. | Claude Opus 5 / dev-story |
| 2026-09-09 | 1.4 | Закрыты последние пять замечаний ревью. Главное — источник согласия ограничен перечислением на уровне БД: `choices` в Django проверяются формами и `full_clean()`, а прямой `objects.create(source="registartion")` их не касается, и опечатка легла бы в юридически значимый журнал молча. Миграция `0020_userconsent_source_valid` заменяет `userconsent_source_required` (`CHECK (source <> '')`) на проверку `source IN (...)`; новое ограничение строго сильнее, поэтому прежнее снято как избыточное. **Уточнение к версиям 1.0–1.3:** имя ограничения `userconsent_source_required` в тексте Task 2 и Dev Notes с этой миграции недействительно — оно называется `userconsent_source_valid` (правится строкой Change Log, а не задним числом в тексте задачи — урок стори 41.3). Прочие замечания: `UnicodeDecodeError` при чтении реестра заворачивается в `ConsentTextsError` (он наследник `ValueError`, а не `OSError`, и проходил мимо `except`); формы подписки при `consent_text_outdated` показывают сообщение поля версии, а не попутную ошибку email (порядок ключей в `details` произволен, а совет «исправьте email» не чинит устаревшую вкладку); ложноположительная проверка отката пользователя исправлена — payload сохраняется в переменную вместо повторного вызова генератора уникального email; закрыт непроверенный путь «галочка маркетинга стоит, версии нет». Backend 3282 → 3286 passed, frontend 2810 → 2812 passed, падений нет; дополнительно полный прогон без фильтра маркеров — 3321 passed, покрытие 81 %. | Claude Opus 5 / dev-story |
| 2026-09-10 | 1.5 | Закрыты восемь замечаний четвёртого круга ревью. Главное — контракт `400` перестал быть свободным объектом: обе формы ответа стали именованными схемами (`FieldValidationErrorResponse`, `ConsentTextOutdatedResponse`) и связаны `oneOf`, поэтому в типах фронта `error` теперь литерал `'consent_text_outdated'`, а `details` — `{ [key: string]: string[] }` вместо `unknown`; `constants/consentTexts.ts` сужает ответ к этому типу, и расхождение машинного кода между сервером и фронтом ломает компиляцию. Условная обязательность `marketing_consent_text_version` выражена `if`/`then` (OpenAPI 3.1) — `dependentRequired` не подошёл, он срабатывает на присутствие `marketing_consent`, а обе формы всегда шлют его, в том числе `false`. Обе правки схемы идут из кода (`apps/common/api_schema.py`, `UserRegistrationRequestSchemaExtension`), контракт перегенерирован и сверен `check_openapi_sync`. **Уточнение к версиям 1.0–1.4:** compliance-утверждения ослаблены до фактически обеспеченных — версия текста подтверждает совместимость официального бандла, но не факт показа текста человеку (произвольный API-клиент пришлёт её, ничего не отрисовав); append-only держится запретами админки и отсутствием пишущих путей, а не схемой; база проверяет допустимость `source`, но у версии только непустоту. Прочие замечания: `marketing_consent_text_version` стал обязательным в ручном `RegisterRequest` (компиляционный страж с `@ts-expect-error`); в пример модели `02-data-models.md` добавлен `USER_CONSENT_SOURCE_VALUES`, без которого блок падал бы `NameError`; блок индексов в DDL заменён фактическим из `pg_indexes` (вымышлены были все шесть, а не два, и `_like`-индексы не показывались вовсе); пример payload B2B-регистрации дополнен consent-полями с предупреждением, что версии из документа копировать нельзя; числа GitNexus-диффа пересняты двумя срезами — закоммиченным и рабочего дерева. Backend 3321 → 3328 passed (полный прогон без фильтра маркеров, 75 skipped, падений нет), frontend 2812 → 2815 passed (168 файлов), падений нет. | Claude Opus 5 / dev-story |

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), скилл `bmad-dev-story`.

### Debug Log References

**Task 9 — обратная совместимость миграции (локальная dev-БД, 2026-09-09).**

До применения `0019` в `common_userconsent` вставлена строка (`id=15`) при схеме на `0018`:

```
 id |      session_key       | consent_type |  ip_address  |          user_agent           | policy_version
----+------------------------+--------------+--------------+-------------------------------+----------------
 15 | pre-0019-probe-session | pdp_contract | 198.51.100.7 | Story41-9 pre-migration probe | 1.0
```

`python manage.py migrate common 0019` → `Applying common.0019_userconsent_source_and_text_version... OK`.
Та же строка после миграции:

```
 id |      session_key       | consent_type |  ip_address  |          user_agent           | policy_version | source  | consent_text_version
----+------------------------+--------------+--------------+-------------------------------+----------------+---------+----------------------
 15 | pre-0019-probe-session | pdp_contract | 198.51.100.7 | Story41-9 pre-migration probe | 1.0            | unknown | unknown
```

Ни одно из существовавших полей не изменилось; оба новых заполнены одноразовым `unknown`. В схеме появились
`source varchar(20) NOT NULL`, `consent_text_version varchar(64) NOT NULL`, ограничения
`userconsent_source_required` (`CHECK (NOT source::text = ''::text)`) и `userconsent_text_version_required`,
а также индексы `common_userconsent_source_e7b538c5` и `common_userconsent_consent_text_version_a95c89c4`
(плюс парные `_like`). Синтетическая строка после снятия вывода удалена — в dev-БД снова 0 записей.
`python manage.py makemigrations --check --dry-run` → `No changes detected`.

**Числа прогонов «до» и «после».**

| Прогон | До (786881e7, дерево без правок) | После | Дельта |
|---|---|---|---|
| Backend, `pytest -m "not performance and not slow"` | 3236 passed, 75 skipped, 35 deselected, 0 failed (27:54) | 3264 passed, 75 skipped, 35 deselected, 0 failed (37:25) | **+28 passed**, падений нет |
| Frontend, `npm run test` | 166 файлов, 2797 passed, 16 skipped | 167 файлов, 2803 passed, 16 skipped | **+1 файл, +6 тестов**, падений нет |

Прирост backend раскладывается ровно: 19 тестов `apps/common/tests/test_consent_texts.py` + 7 новых в
`test_user_consent.py` + 2 новых в `test_auth_registration_consent.py` = 28. Прирост фронтенда — 6 тестов
стража `consent-texts-registry.test.tsx`. Число skipped и deselected не изменилось: новые тесты не выпадают
из фильтров CI, ничего не «спряталось».

Базис снимался на дереве **без правок** (реализация временно убрана в `git stash`): первый фоновый прогон
стартовал одновременно с правкой моделей, а тестовый контейнер монтирует `../backend:/app` — число было бы
загрязнено, поэтому оно отброшено и снято заново.

**Целевой набор** (`apps/common` + два интеграционных файла) — 129 passed, прогнан дважды: после приведения
тестов и повторно на финальном коде, потому что переформатирование `black` в `apps/common/views.py` и
точечные `# type: ignore` в `test_user_consent.py` легли уже во время полного прогона.

**Статический анализ бэкенда.**

- `flake8 . --max-line-length=120 --extend-ignore=E203,W503` — чисто (единственный блокирующий линтер).
- `black --check .` — из файлов стори переформатирования потребовал только `apps/common/views.py` (перенос
  одного вызова в строку), он применён. Оставшиеся 8 файлов в выводе `black --check` по репозиторию
  (`apps/pages/models.py`, `apps/pages/tests.py`, `apps/products/category_utils.py`,
  `apps/products/management/commands/fix_category_tree_public_roots.py`,
  `apps/products/tests/test_visible_categories.py`,
  `apps/products/tests/unit/test_fix_category_tree_public_roots.py`,
  `apps/products/tests/unit/test_variant_import_migrated.py`, `tests/helpers.py`) — предсуществующие,
  стори их не касается и не трогает.
- `mypy --config-file=mypy.ini .` — **129 ошибок, дельта к базису 0**. Первый замер дал 131: два новых
  замечания `"CharField[Any, Any]" has no attribute "db_index"` в новом тесте
  `test_audit_fields_are_indexed_and_bounded`. Закрыты точечными `# type: ignore[attr-defined]` (при
  `warn_unused_ignores = True` лишний игнор сам был бы ошибкой). Все оставшиеся ошибки в затронутых файлах —
  на строках, которых стори не писала: `apps/common/admin.py:337,340` (`has_change_permission` /
  `has_delete_permission`) и `apps/common/tests/test_user_consent.py:166-168` (существовавший тест индексов).
  Новые файлы (`consent_texts.py`, `test_consent_texts.py`, миграция `0019`) не дают ни одной ошибки.

**Статический анализ фронтенда:** `npx tsc --noEmit` — 0 ошибок; `npm run lint` (`eslint . --max-warnings=0`)
— чисто; `npm run format:check` — `All matched files use Prettier code style!`.

**Проверка, что страж Task 6 действительно охраняет** (красная фаза, обе правки откатаны):

1. Текст маркетингового чекбокса в реестре изменён на `Я согласен(на)` (без пробела) → упали 2 теста:
   `RegisterForm показывает тексты registration_pdp_checkbox и registration_marketing_checkbox` и
   `B2BRegisterForm показывает те же тексты, что и RegisterForm` с сообщением
   `Unable to find an accessible element with the role "checkbox" and name "Я согласен(на) получать..."`.
2. Файл реестра временно убран → тест-файл упал целиком с сообщением
   `Реестр текстов согласий не читается: <путь>. Он обязан существовать — по нему вычисляется
   UserConsent.consent_text_version` (в итоге `Tests: no tests`, а не «пропущено»).

**Доработка по замечаниям ревью — числа прогонов (2026-09-09).**

| Прогон | До доработки (версия 1.1) | После | Дельта |
|---|---|---|---|
| Backend, `pytest -m "not performance and not slow"` | 3264 passed, 75 skipped, 35 deselected, 0 failed | 3279 passed, 75 skipped, 35 deselected, 0 failed (32:57) | **+15 passed**, падений нет |
| Frontend, `npm run test` | 167 файлов, 2803 passed, 16 skipped | 167 файлов, 2807 passed, 16 skipped, 0 failed | **+4 теста**, падений нет |

Прирост фронтенда раскладывается: +2 в страже `consent-texts-registry.test.tsx` (константы версий совпадают с
реестром; версии зафиксированы в `known_versions`), +1 в `SubscribeForm.test.tsx` и +1 в `RegisterForm.test.tsx`
(сервер отклонил устаревшую версию — человеку показано требование обновить страницу). Число файлов не выросло:
новых тест-файлов доработка не завела.

Прирост backend раскладывается ровно: +10 в `apps/common/tests/test_consent_texts.py` (19 → 29 — защита истории,
дубли ключей, длина версии, сверка константы с полем модели), +2 в `test_common_subscribe_api.py` и +3 в
`test_auth_registration_consent.py` (отклонение устаревшей и отсутствующей версии; версия маркетинга проверяется
только вместе с галочкой). Число skipped и deselected не изменилось — новые тесты не выпадают из фильтров CI.

**Статический анализ после доработки.**

- `flake8 . --max-line-length=120 --extend-ignore=E203,W503` — чисто.
- `black --check .` — те же 8 предсуществующих файлов, что и в версии 1.1. Промежуточный прогон `black` по всему
  дереву успел их переформатировать; правки откачены `git checkout`, потому что стори их не касается и чужой шум
  в диффе ревью уже отмечало.
- `mypy --config-file=mypy.ini .` — **129 ошибок, дельта к базису 0**. Первый замер дал 130: `unused-ignore` в
  собственном новом тесте (`# type: ignore[attr-defined]` на `field.max_length` оказался лишним — mypy знает это
  свойство `CharField`). Игнор снят; при `warn_unused_ignores = True` он сам был ошибкой.
- `python manage.py makemigrations --check --dry-run` — `No changes detected`: доработка модель не трогала.
- `python manage.py check_openapi_sync --schema-file …` — «Контракт синхронен с кодом». Файл правился точечно, а
  не заменялся выводом `spectacular` целиком: генератор недетерминирован в порядке ключей и дал бы 400 строк шума
  (об этом прямо предупреждает комментарий в `api-contract.yml`), а гейт сравнивает разобранные структуры.
- **Целевой набор на финальном коде** (`apps/common` + подписка + согласия регистрации + unit-тесты сериализаторов
  пользователя) — 181 passed. Прогнан повторно после снятия `unused-ignore`, потому что правка легла уже во время
  полного прогона.

**`npx gitnexus detect-changes --scope all` перед сдачей (после доработки):** 38 файлов, 54 символа, 9 затронутых
потоков, risk **high** против 18/23/4/medium в версии 1.1. Расхождение объяснимо и ожидаемо:

- `high` здесь — агрегат объёма правки, а не blast radius: `impact --direction upstream` по каждому правимому
  символу (`SubscribeSerializer`, `UserRegistrationSerializer`, `load_registry`, `ConsentTextRegistry`) дал
  **LOW**, и снят он был до внесения правок.
- В списке изменённых символов — `current_text`, `resolve_text`, `bound_pairs`, `versions` и другие члены
  `consent_texts.py`, которых доработка не касалась: вставка `_check_known_versions` сдвинула вниз всё, что
  объявлено после неё, а сопоставление идёт по смещению строк. Та же причина, что и в версии 1.1.
- Новые потоки в списке — `RegisterPage → …` и `OnSubmit → …`: формы теперь собирают payload с версиями. Поток
  `Subscribe → …` присутствовал и раньше.

**Вторая доработка по замечаниям ревью — числа прогонов (2026-09-09).**

| Прогон | До второй доработки (версия 1.2) | После | Дельта |
|---|---|---|---|
| Backend, `pytest -m "not performance and not slow"` | 3279 passed, 75 skipped, 35 deselected, 0 failed | 3282 passed, 75 skipped, 35 deselected, 0 failed (27:06) | **+3 passed**, падений нет |
| Frontend, `npm run test` | 167 файлов, 2807 passed, 16 skipped | 167 файлов, 2810 passed, 16 skipped, 0 failed | **+3 теста**, падений нет |

Прирост backend раскладывается ровно: +2 в `test_common_subscribe_api.py`
(`test_subscribe_outdated_version_response_keeps_other_field_errors` — попутная ошибка email остаётся в
`details`; `test_subscribe_plain_validation_error_keeps_flat_shape` — обычная валидация не переехала в новую
форму) и +1 в `test_auth_registration_consent.py` (та же проверка плоской формы для регистрации). Прирост
фронтенда: +1 в `subscribeService.test.ts` (машинный код прокинут с верхнего уровня ответа), +1 в
`ElectricSubscribeForm.test.tsx`, +1 в `B2BRegisterForm.test.tsx` (обе формы показывают требование обновить
страницу). Число файлов, skipped и deselected не изменилось.

**Два теста подписки уточнены, а не «починены».** `test_subscribe_requires_pdp_consent` и
`test_subscribe_missing_pdp_consent_does_not_leak_subscriber_status` слали запрос вообще без
`consent_text_version` и после правки ушли бы в ветку `consent_text_outdated` — то есть проверяли бы не то,
что заявлено в их названиях. В оба добавлена действующая версия; их предмет — отсутствие галочки и
отсутствие утечки статуса подписчика.

**Проверка, что новый контракт действительно проверяется** (ассерты сверяют `response.json()`, а не
`response.data`): прежние ассерты читали `ErrorDetail.code` — поле, которое JSONRenderer выбрасывает, — и
остались бы зелёными без исправления. Теперь сравнивается отрендеренное тело целиком.

**Статический анализ после второй доработки.**

- `flake8 . --max-line-length=120 --extend-ignore=E203,W503` — чисто.
- `black --check .` — те же 8 предсуществующих файлов, что и в версиях 1.1 и 1.2; файлов стори среди них нет.
- `mypy --config-file=mypy.ini .` — **129 ошибок, дельта к базису 0**. Новых замечаний доработка не внесла;
  все оставшиеся — на строках, которых стори не писала.
- Фронтенд: `npx tsc --noEmit` — 0 ошибок; `npm run lint` (`eslint . --max-warnings=0`) — чисто;
  `npm run format:check` — `All matched files use Prettier code style!` (шесть правленых файлов прогнаны
  `prettier --write`).
- `python manage.py check_openapi_sync --schema-file /docs/api/openapi.yaml` — «Контракт синхронен с кодом».
  Файл снова правился точечно, а не заменялся выводом `spectacular`: сверка идёт по разобранным структурам,
  а генератор недетерминирован в порядке ключей. Структурная сверка `openapi.yaml` со свежесгенерированной
  схемой — **0 расхождений**.
- `npm run generate:types` — дифф аддитивный: у обоих `400` появился `content` со свободным объектом и
  обновилось описание.
- **Целевой набор** (`apps/common` + подписка + согласия регистрации + unit-тесты сериализаторов
  пользователя) — 184 passed.

**Blast radius второй доработки (GitNexus CLI, индекс `up-to-date` на `0f6e13e`).** Все правимые символы —
**LOW**: `SubscribeSerializer` (2 прямых), `UserRegistrationSerializer` (4), `consent_text_outdated_error`
(2), `Function:backend/apps/common/views.py:subscribe` (0), `UserRegistrationView` (0). Предупреждать о
HIGH/CRITICAL было не о чем. CLI требует `--repo` с путём к репозиторию: в индексе их два (второй —
`FREESPORT-pr117`), без параметра команда возвращает `error` вместо результата, а `risk` читается как `null`.

**`npx gitnexus detect-changes --scope all` перед сдачей (после второй доработки):** 31 файл, 53 символа,
12 затронутых потоков, risk **high**. Расхождение объяснимо и ожидаемо по тем же причинам, что и раньше:

- `high` — агрегат объёма правки, а не blast radius: `impact --direction upstream` по каждому правимому
  символу дал LOW (см. выше), и снят он был до внесения правок.
- В списке изменённых символов — `email`, `pdp_consent`, `validate_email`, `already_subscribed_error`,
  `_ingest_binding` и другие члены тех же файлов, которых доработка не касалась: вставка
  `consent_text_outdated_payload` и `has_error_code` сдвинула вниз всё, что объявлено после них, а
  сопоставление идёт по смещению строк.
- Потоки `RegisterPage → …`, `B2BRegisterPage → …`, `OnSubmit → …` и `Subscribe → …` присутствовали и в
  прошлом прогоне: правились те же формы и та же вью подписки.
- `detect-changes --scope all` видит только рабочее дерево против `HEAD`, поэтому закоммиченная часть стори
  в эти 31 файл не входит.

**Blast radius доработки (GitNexus CLI, индекс `up-to-date` на `28a40a6`).** Все правимые символы — **LOW**:
`SubscribeSerializer`, `UserRegistrationSerializer`, `load_registry`, `ConsentTextRegistry`. Предупреждать о
HIGH/CRITICAL было не о чем.

**Что осталось непокрытым автотестом.** Реальный переход «текст поправили → открытая вкладка получила отказ»
воспроизводится только в браузере: тесты подменяют версию литералом, а не пересобирают бандл. Механика при этом
проверена с обеих сторон — сервер отклоняет чужую версию (backend-тесты подписки и регистрации), а константа
фронта не может разойтись с реестром (страж пересчитывает версию из текста той же формулой).

**Blast radius (GitNexus CLI, индекс `up-to-date` на `786881e7`).** `UserConsent` — HIGH, 18 прямых
зависимостей, 0 процессов, 0 модулей; как и предупреждала стори, это рёбра импорта уровня файла, а не
вызовы. `UserConsentAdmin` — LOW (1), `UserRegistrationView` — LOW (0).

**`npx gitnexus detect-changes --scope all` перед сдачей:** 18 файлов, 23 символа, 4 затронутых потока,
risk **medium**. Расхождения объяснимы и ожидаемы:

- В списке изменённых символов присутствуют `News`, `title`, `slug`, `content`, `image`, `author` из
  `apps/common/models.py` и `has_add_permission` из `apps/common/admin.py`, которых стори не касалась.
  Это следствие сопоставления символов по смещению строк: вставка полей в `UserConsent` сдвинула вниз всё,
  что объявлено после неё в тех же файлах.
- Затронутые потоки — `B2BRegisterPage → Cn` (правка `B2BRegisterForm`, Task 5) и три потока `Subscribe → …`
  (правка `subscribe`, Task 3). Поток регистрации в списке не появился, что согласуется с нулевым upstream
  у `UserRegistrationView`.
- 18 файлов против 21 в `File List`: GitNexus считает только разбираемые им файлы кода и не учитывает
  markdown-документацию.

**Blast radius третьей доработки (GitNexus CLI, индекс `up-to-date` на `8ef9612`).** `UserConsent` — **HIGH**
(19 прямых, 0 процессов, 0 модулей): те же рёбра импорта уровня файла, что и в прошлых кругах, а не вызовы;
правится только `Meta.constraints`, публичный интерфейс класса не трогается. `load_registry` — LOW
(2 прямых, 2 потока: `subscribe` и `UserRegistrationView.post`), правится единственная ветка `except`.
Предупреждение о HIGH сделано по правилу проекта до внесения правок.

**Третья доработка по замечаниям ревью — числа прогонов (2026-09-09).**

| Прогон | До доработки (версия 1.3) | После | Дельта |
|---|---|---|---|
| Backend, `pytest -m "not performance and not slow"` | 3282 passed, 75 skipped, 35 deselected, 0 failed | 3286 passed, 75 skipped, 35 deselected, 0 failed (27:45) | **+4 passed**, падений нет |
| Frontend, `npm run test` | 167 файлов, 2810 passed, 16 skipped | 167 файлов, 2812 passed, 16 skipped, 0 failed | **+2 теста**, падений нет |

Прирост backend раскладывается ровно: +2 в `test_user_consent.py` (`test_source_outside_choices_violates_check_constraint`,
`test_source_values_match_choices`), +1 в `test_consent_texts.py` (`test_broken_encoding_raises_consent_texts_error`),
+1 в `test_auth_registration_consent.py` (`test_registration_requires_marketing_text_version_when_consent_given`) = 4.
Прирост фронтенда — по одному regression-тесту смешанного `details` в каждой из двух форм подписки. Число
skipped и deselected не изменилось: новые тесты не выпадают из фильтров CI.

**Дополнительно снят полный прогон без фильтра маркеров** (`make test`-эквивалент, `up --build` с
пересборкой образа и сбросом volumes): **3321 passed, 75 skipped, 0 failed** за 32:35, покрытие
`TOTAL 14521 / 2816 → 81%`. Он включает `performance` и `slow`, поэтому с рядом чисел выше не сопоставим и
приводится как отдельная проверка: под тем же кодом падений нет и в наборе, который PR-гейт не гоняет.
Разница `3321 − 3286 = 35` совпадает с числом deselected в фильтрованном прогоне.

**`npx gitnexus detect-changes --scope all` перед сдачей (после третьей доработки):** 18 файлов, 24 символа,
4 затронутых потока, risk **medium**. Расхождения те же, что и в прошлых кругах, и объяснимы:

- Потоки ровно ожидаемые: `Subscribe → Load_registry` и `Post → Load_registry` (правка ветки `except` в
  загрузчике) плюс два `OnSubmit → GetBackendMessage` (обе формы подписки).
- Среди «изменённых символов» — `session_key`, `who`, `__str__` из `apps/common/models.py` и `details`,
  `message`, `getFirstBackendError` из `ElectricSubscribeForm.tsx`, которых доработка не касалась: вставка
  `USER_CONSENT_SOURCE_VALUES` и хелпера `getConsentOutdatedMessage` сдвинула вниз всё, что объявлено после
  них, а сопоставление идёт по смещению строк.
- 18 файлов против 19 в `git status`: новая миграция `0020_userconsent_source_valid.py` ещё не под
  версионным контролем на момент замера, и `detect-changes` её не видит.

**RED-фаза фронтенд-правки снята явно.** С заглушенными `SubscribeForm.tsx` / `ElectricSubscribeForm.tsx`
(`git stash`) новые тесты смешанного `details` дали **2 failed / 36 passed** — падали ровно они. После
возврата правки — **38 passed**. Дефект был реальным, а не гипотетическим.

**Ограничение `userconsent_source_valid` строго сильнее заменённого.** Пустая строка не входит в список
допустимых значений, поэтому оба теста пустого источника (`test_empty_source_violates_check_constraint` и
его версия для `consent_text_version`) остались зелёными без правки, а прежнее `userconsent_source_required`
стало избыточным и снято миграцией `0020`. Само переименование в тексте Task 2 и Dev Notes задним числом
**не правится** — расхождение фиксируется строкой Change Log (урок стори 41.3).

**Статика после третьей доработки.** `flake8 . --max-line-length=120 --extend-ignore=E203,W503` — чисто.
`black --check` по шести правленым файлам — `6 files would be left unchanged`; предсуществующие 8 файлов,
которые black переформатировал бы (`apps/pages/models.py`, `apps/products/category_utils.py` и др.), стори
не касается. `mypy --config-file=mypy.ini .` — 129 ошибок; в правленых файлах отчёт называет только
`test_user_consent.py:166-168` — это предсуществующий тест
`test_user_consent_hot_fields_are_indexed_and_user_agent_is_bounded`, строки которого доработка не трогала.
Дельта к базису — ноль. Фронт: `npx tsc --noEmit` — чисто, `npm run lint` — чисто, `npm run format:check` —
после `prettier --write` по двум формам «All matched files use Prettier code style».

**Четвёртая доработка по замечаниям ревью — числа прогонов (2026-09-10).**

| Прогон | До четвёртой доработки | После | Дельта |
|---|---|---|---|
| Backend, `pytest -q` (без фильтра маркеров) | 3321 passed, 75 skipped, 19 subtests, 0 failed (38:36) | 3328 passed, 75 skipped, 19 subtests, 0 failed (27:12) | **+7 passed**, падений нет |
| Frontend, `npm run test` | 167 файлов, 2812 passed, 16 skipped | 168 файлов, 2815 passed, 16 skipped, 0 failed | **+3 теста, +1 файл**, падений нет |

Прогон бэкенда взят **без** фильтра маркеров (в прошлых кругах основной таблицей был
`-m "not performance and not slow"`): доработка меняет схему API, а её строит один и тот же код независимо
от маркеров, и полный набор здесь строго сильнее. Число сопоставимо с полным прогоном версии 1.4 (3321 passed).

Прирост фронтенда — новый файл `src/__tests__/register-request-contract.test.ts` (3 теста): payload с обеими
версиями принимается обоими типами; payload без маркетинговой версии и payload без версии ПДн не
компилируются. Проверка компиляционная — её настоящий гейт `npx tsc --noEmit`, а не vitest; в vitest тесты
нужны, чтобы файл не выглядел мёртвым и чтобы `@ts-expect-error` стоял в исполняемом коде.

Прирост бэкенда раскладывается ровно: все **+7** — новый файл `apps/common/tests/test_api_schema.py`
(две формы `400` объявлены именованными компонентами; у плоской формы свободные ключи и нет фиксированных
`properties`; у структурированной машинный код зафиксирован `const`; общий компонент — `oneOf` из обеих;
оба эндпоинта на него ссылаются — параметризация даёт два теста; `if`/`then` у `UserRegistrationRequest`
и то, что версия маркетинга не стала обязательной безусловно). Число skipped, deselected и subtests не
изменилось — новые тесты не выпадают из фильтров CI и не трогают БД.

**Целевой набор** (`apps/common` + подписка + согласия регистрации + unit-тесты сериализаторов
пользователя) — **195 passed** (04:10), против 188 до доработки.

**Красная фаза backend-стража снята не подстройкой, а исправлением теста.** Первый прогон целевого набора
дал `1 failed`: `test_consent_text_outdated_pins_machine_code` сравнивал словарь `details` целиком, а в
схеме у него есть ещё `description` из `help_text`. Тест привязывал бы прогон к тексту подсказки и падал бы
от любой её правки — сверка сужена до структуры (`type` + `additionalProperties`). Схему при этом не
трогали: падал тест, а не код.



**Проверка, что компиляционный страж действительно охраняет** (красная фаза, правка откатана):
`marketing_consent_text_version` временно возвращено в необязательное (`?: string`) — `npx tsc --noEmit` дал
обе ожидаемые ошибки: `TS2322` на присваивании ручного типа к `Pick<>` от сгенерированного
(`Type 'undefined' is not assignable to type 'string'`) и `TS2578: Unused '@ts-expect-error' directive` в
самом страже. После отката — чисто. Без этой проверки страж мог бы быть зелёным всегда.

**Статический анализ после четвёртой доработки.**

- `flake8 . --max-line-length=120 --extend-ignore=E203,W503` — чисто.
- `black --check` по пяти правленым backend-файлам — `5 files would be left unchanged`. `black --check .`
  по-прежнему называет те же 8 предсуществующих файлов (`apps/pages/models.py`,
  `apps/products/category_utils.py`, `apps/pages/tests.py`, `apps/products/tests/test_visible_categories.py`,
  `apps/products/management/commands/fix_category_tree_public_roots.py`,
  `apps/products/tests/unit/test_fix_category_tree_public_roots.py`, `tests/helpers.py`,
  `apps/products/tests/unit/test_variant_import_migrated.py`); ни один из них не входит в дифф ветки
  (`git diff --name-only origin/develop...HEAD` их не содержит), стори их не касается.
- `mypy --config-file=mypy.ini .` — **129 ошибок, дельта к базису 0**. Первый замер дал 131: два новых
  `no-any-return` на неаннотированных вызовах drf-spectacular (`auto_schema._map_serializer`,
  `SchemaGenerator.get_schema`) при включённом `warn_return_any`. Оба закрыты точечным `cast`, а не
  `# type: ignore` — тип здесь известен, скрывать нечего.
- `python manage.py check_openapi_sync` — «Контракт синхронен с кодом». В этот раз файл контракта заменён
  выводом `spectacular --file … --validate` целиком, а не правился точечно: правки затрагивают три новых
  компонента и два ответа, и ручная синхронизация была бы менее надёжной, чем регенерация. Дифф вышел
  умеренный (209 вставок / 161 удаление) — большая часть шума пришлась на порядок HTTP-методов внутри путей,
  к которому гейт нечувствителен по построению.
- Фронтенд: `npx tsc --noEmit` — 0 ошибок; `npm run lint` (`eslint . --max-warnings=0`) — чисто;
  `npm run format:check` — `All matched files use Prettier code style!` (`prettier --write` понадобился двум
  файлам: `types/api.ts` и `constants/consentTexts.ts`).

**`npx gitnexus detect-changes --scope all` перед сдачей (после четвёртой доработки):** 17 файлов,
22 символа, 4 затронутых потока, risk **medium**. Команде обязателен `--repo "C:\Users\1\DEV\FREESPORT"` —
без него CLI падает `Multiple repositories indexed` (проиндексирован ещё и worktree `FREESPORT-pr117`).
Расхождения объяснимы:

- В списке изменённых символов — `new_password`, `new_password_confirm`, `PortalLinkConfirmSerializer`,
  `UserLoginSerializer` и два `validate`, которых доработка не касалась: вставка
  `UserRegistrationRequestSchemaExtension` в середину `apps/users/serializers.py` сдвинула вниз всё, что
  объявлено после неё, а сопоставление идёт по смещению строк. Та же причина, что в версиях 1.1 и 1.3.
- Затронутые потоки — четыре ветки `OnSubmit → IsConsentTextOutdated`: в `constants/consentTexts.ts`
  изменились `isConsentTextOutdated` (сузился к типу из контракта) и `getConsentTextOutdatedMessage`
  (читает `data.details` вместо приведения к локальному типу). Поведение обеих функций прежнее.
- `impact --direction upstream` по правленым символам снят до внесения правок:
  `Function:backend/apps/common/views.py:subscribe` — **LOW** (0 upstream),
  `UserRegistrationView` — **LOW** (0 upstream), `UserRegistrationSerializer` — **LOW** (4 прямых,
  0 процессов, 0 модулей). HIGH/CRITICAL в этом круге нет.

### Completion Notes List

**Что сделано.** `UserConsent` получил два поля — `source` (`newsletter` / `registration` / `1c_link` /
`unknown`) и `consent_text_version`, — и с ними журнал согласий впервые отвечает на главный вопрос ФЗ-152
ст. 9: не только «когда и с какого IP», но и **на что именно** человек соглашался.

**Ключевые решения по ходу реализации.**

1. **Версия не хранится в коде и не проставляется руками.** Она вычисляется как
   `<метка>-<первые 8 hex sha256 текста>` из реестра `backend/apps/common/consent_texts.json`. Правка текста
   меняет версию сама — пропустить бамп механически невозможно. Фактические значения на baseline:
   `2026-08-30-77dbceaf` (подписка), `2026-09-09-de992f50` (ПДн регистрации), `2026-09-09-e26471e4`
   (маркетинг регистрации).
2. **У полей нет `default` в модели.** Одноразовое `unknown` живёт только в миграции
   (`preserve_default=False`). Два `CheckConstraint` роняют вставку без источника или без версии: код,
   забывший их передать, падает сразу, а не пишет тихий мусор в доказательство согласия.
3. **Источник берётся из уже вычисленного `pending_1c_link`.** Точка записи осталась одна (решение стори
   41.2), третьей вставки не заведено, запись не перенесена в сериализатор.
4. **Версия у подписки запрашивается отдельно на каждый тип согласия**, хотя чекбокс там один и версии
   совпадают. Общее значение в `consent_kwargs` вернуло бы дефект молча при будущем расщеплении чекбоксов.
5. **Формулировки двух форм регистрации унифицированы (Task 5, решение владельца до старта).** B2B-текст ПДн
   приведён к формулировке `RegisterForm`: политика теперь названа по имени и на неё ведёт ссылка. Вместе с
   текстом убран суффиксный `<label>` и его id из `aria-labelledby` — оставшийся в списке несуществующий id
   молча урезал бы доступное имя. В маркетинговом чекбоксе `Я согласен(на)` → `Я согласен (на)`.
   Ожидания в `B2BRegisterForm.test.tsx` переведены с регулярок на дословные константы: регулярка
   `/обработку моих персональных данных/i` осталась бы зелёной и при неверном тексте.
6. **Страж соответствия живёт в Vitest, а не в pytest.** Бэкенд-контейнер не видит `frontend/` (смонтирован
   только `../backend`, плюс `docker/` и `.github/`), поэтому сверить отрисованную форму с реестром может
   только фронтенд. Страж падает, а не пропускается: обе ветки падения проверены явно (см. Debug Log).

**Отклонение от текста стори — одно, в тесте, а не в коде.** Подготовленный по Task 8 тест
`test_empty_revisions_raise` изначально передавал пустой `bindings={}`, и загрузчик отбраковывал реестр
раньше — на пустом разделе привязок, а не на пустом списке ревизий. Тест исправлен (привязка сделана
непустой), поведение загрузчика не менялось. Обнаружено первым же прогоном целевого набора.

**Что осталось за границей стори (сознательно).** `policy_version` остаётся константой `"1.0"`: текст
политики ПДн живёт в БД (`Page`, slug `privacy-policy`) и ревизий не имеет, поэтому какая её редакция
действовала в момент согласия — из журнала по-прежнему не восстановить. Запись занесена в
`deferred-work.md`. Cookie-согласие в журнал не заводится. `UserConsent` по-прежнему не отдаётся ни одним
сериализатором и ни одним эндпоинтом — читать журнал можно только в админке. (Утверждение версии 1.1 «контракт
не менялся» относится к самой реализации; доработка по ревью его отменила — см. ниже пункт 6.)

**Доработка по замечаниям ревью (2026-09-09).**

1. **Версию текста теперь заявляет клиент, а сервер её проверяет.** До правки сервер сам подставлял действующую
   версию — то есть вкладка, отрисованная до правки формулировки, записывала согласие на текст, которого человек
   не видел. Теперь форма присылает версию показанной формулировки, сервер сверяет её с реестром и при
   несовпадении отвечает `400` с кодом `consent_text_outdated` и требованием обновить страницу. В журнал
   по-прежнему ложится значение из реестра, а не присланное клиентом: запрос лишь доказывает право записать
   действующую версию.
2. **Версия зашита в бандл фронта, а не запрашивается у сервера.** Это принципиально: значение, полученное
   запросом в момент отправки, всегда актуально и ничего не доказывает — старая вкладка получила бы свежую
   версию и записала согласие на невиданную формулировку. Константа `frontend/src/constants/consentTexts.ts`
   собирается в тот же бандл, что и сам текст чекбокса, поэтому старый бандл присылает старую версию и получает
   отказ. Расхождение константы с реестром ловит тот же страж `consent-texts-registry.test.tsx` — он пересчитывает
   версию из текста реестра той же формулой, а не сверяет литерал с литералом.
3. **История ревизий страхуется сверкой.** Раздел `known_versions` перечисляет версии всех когда-либо
   действовавших формулировок; загрузчик требует точного совпадения этого списка с набором, вычисленным из
   ревизий. Односторонняя правка текста старой ревизии и её удаление ловятся одинаково — версия пропадает из
   вычисленного набора. Новая ревизия тоже обязана быть внесена, и её строку печатает сообщение об ошибке:
   считать хеш руками не нужно. Границы гарантии: список лежит в том же редактируемом JSON, поэтому
   согласованная замена ревизии вместе с её строкой пройдёт — страж процедурный, а не механический
   (уточнено по замечанию ревью, версия 1.3).
4. **Две мелких дыры загрузчика закрыты.** Повторяющиеся ключи JSON (`object_pairs_hook`) больше не «побеждают
   снизу», подменяя привязку; версия длиннее `MAX_VERSION_LENGTH = 64` не проходит загрузку — иначе она
   обрезалась бы базой уже на живом согласии.
5. **Тринадцать backend-файлов и пять фронтенд-тестов приведены к обязательной версии.** Payload регистрации и
   подписки без версии теперь отклоняется — это работающая защита, а не сломанные тесты. Версии берутся из
   общего `backend/tests/consent_versions.py`, который читает тот же реестр: литералы пришлось бы чинить при
   каждой правке текста. Ожидания форм переведены с `objectContaining` без версий на явные значения — иначе
   удаление поля из формы прошло бы мимо тестов.
6. **Контракт API обновлён.** Заявление стори «API-контракт не меняется» (шапка, AC8) этой доработкой отменено —
   расхождение зафиксировано строкой Change Log 1.2, а не переписыванием AC. `openapi.yaml` перегенерирован
   `spectacular` и сверен `check_openapi_sync`; типы фронта — `npm run generate:types`.

**Вторая доработка по замечаниям ревью (2026-09-09).** Закрыты все восемь оставшихся пунктов.

1. **Машинный код отказа дошёл до клиента.** Прежняя версия несла `consent_text_outdated` только внутри
   Python — в `ErrorDetail.code`, который JSONRenderer выбрасывает, отдавая голый массив строк. Фронт мог
   узнать этот случай лишь по тексту сообщения, то есть сломался бы от первой же правки формулировки ошибки.
   Хуже того, у **пропущенного** поля версии внутренний код был `required` — тот же случай для человека, но
   другой признак для кода. Теперь оба эндпоинта отвечают `{"error": "consent_text_outdated", "details":
   {поле: [сообщения]}}` — тем же видом, что уже был у `consent_persistence_failed`. Признаком служит любая
   ошибка на полях версии, поэтому «не прислали» и «прислали старую» неразличимы снаружи, как и должно быть.
   `details` сохраняет **все** ошибки запроса: попутная ошибка email не должна пропадать из-за того, что
   форма ещё и устарела. В `subscribe` проверка стоит **до** нейтрального «уже подписан» — запрос, не
   доказавший показанный текст, не имеет права получить ложный успех.
2. **Тесты сверяют отрендеренный JSON, а не `response.data`.** Прежние ассерты читали `ErrorDetail.code` —
   то самое поле, которое до клиента не доходит, — и потому зелёными были бы и без исправления. Теперь
   сравнивается `response.json()` целиком. Добавлены две проверки на то, что обычная валидация осталась
   плоской: контракт сдвинут только для одного случая, а не для всех 400.
3. **Два теста подписки уточнены, а не «починены».** `test_subscribe_requires_pdp_consent` и тест на
   неразглашение статуса подписчика слали запрос вообще без версии и после правки уходили в ветку
   `consent_text_outdated` — проверяли бы не то, что заявлено в их названии. В оба добавлена действующая
   версия: их предмет — отсутствие галочки и отсутствие утечки, а не устаревшая форма.
4. **Найдена причина, по которой невалидный пример подписки не ловился контрактом.** Без `response=`
   drf-spectacular выбрасывает `examples` целиком: у обоих 400 не было узла `content`, и ни один пример в
   схему не попадал — ни старый (без обязательного `consent_text_version`, из-за чего скопированный из
   Swagger запрос получал 400), ни новый. Обоим ответам задан `response=OpenApiTypes.OBJECT`: у 400 две
   формы, одной схемой их не описать, а свободный объект с двумя примерами описывает обе честно.
   `docs/api/openapi.yaml` правился точечно (генератор недетерминирован в порядке ключей), сверен
   `check_openapi_sync`, типы фронта перегенерированы.
5. **Границы гарантии `known_versions` названы прямо.** Решение владельца — оставить процедурный страж и
   убрать утверждения о более сильной гарантии. Список лежит в том же редактируемом JSON, поэтому
   согласованная замена ревизии **вместе** с её строкой пройдёт; страж ловит одностороннюю правку — самый
   вероятный способ потерять доказательство по неосторожности. Формулировки исправлены в коде, тестах,
   двух документах архитектуры и в этой стори.
6. **Три документа архитектуры приведены к коду.** `02-data-models.md` показывал Mermaid с новыми полями и
   Python-блок без них — документ противоречил сам себе. `18-b2b-verification-workflow.md` описывал
   привязку к 1С как действующую, хотя `_link_matched_1c_customer` не вызывается с 2026-07-26: раздел
   помечен как отключённый латентный сценарий, поведение согласия описано как сохранённое на случай
   безопасного возврата. `11-security-performance.md` утверждал строгую проверку JSON boolean при
   регистрации — фактически строга только подписка; асимметрия названа со ссылкой на `deferred-work.md`.
7. **Хрупкие ссылки заменены.** Dev-task ссылался на `deferred-work.md` номерами строк, а новые записи
   добавляются сверху — `:1025`, `:1037`, `:1039`, `:1041-1045` уже указывали на чужие пункты. Все четыре
   ссылки переведены на цитаты заголовков.
8. **Числа побочного GitNexus-диффа сверены `git diff`.** В коммитах стори счётчик сдвинулся
   `9657/15912 → 9695/15982`; незакоммиченный сдвиг рабочего дерева `→ 9717/16022` в дифф ветки не входит.
   Прежняя запись `→ 9647, 15902` была неверна и направлением, и значениями.

**Третий круг ревью — пять замечаний.**

1. **Источник ограничен перечислением на уровне БД.** `choices` в Django — валидация форм и `full_clean()`;
   прямой `UserConsent.objects.create(source="registartion")` их не касается, а прежний `CheckConstraint`
   отсекал только пустую строку. Миграция `0020_userconsent_source_valid` меняет условие на
   `source IN ('newsletter','registration','1c_link','unknown')`. Новое ограничение строго сильнее
   заменённого, поэтому `..._source_required` снято как избыточное, а тесты пустого источника не правились.
   Список объявлен модульной константой `USER_CONSENT_SOURCE_VALUES`, а не атрибутом класса: тело вложенного
   `class Meta` не видит пространство имён внешнего класса — Python пропускает class scope при разрешении
   имён, и `SOURCE_VALUES` внутри `Meta` дал бы `NameError`. Синхронность с `SOURCE_CHOICES` держит тест.
2. **Повреждённая кодировка реестра больше не пролетает мимо `ConsentTextsError`.** `UnicodeDecodeError`
   наследуется от `ValueError`, а не от `OSError`, поэтому `except OSError` его не ловил и обещание модуля
   («одно понятное исключение, называющее файл») нарушалось ровно на том случае, ради которого написано.
3. **Формы подписки перестали показывать попутную ошибку вместо требования обновить страницу.**
   `getFirstBackendError()` брал первое значение из `details`, а порядок ключей в JSON произволен: ответ
   `{email, consent_text_version}` советовал бы исправить email — совет, который ничего не чинит, пока
   вкладка старая. Обе формы перешли на `getConsentTextOutdatedMessage()`, который уже сортировал поля
   версии первыми и применялся в формах регистрации. RED-фаза снята явно (см. Debug Log).
4. **Ложноположительная проверка отката исправлена.** Тест звал `trainer_payload()` второй раз, а тот
   генерирует новый уникальный email — проверка искала несуществующий адрес и прошла бы при ошибочно
   созданном пользователе. Payload сохранён в переменную; тот же приём добавлен соседнему тесту, где
   проверки отката не было вовсе.
5. **Закрыт непроверенный путь маркетинговой версии.** Устаревшая версия и отсутствие PDP-версии были
   покрыты, а «галочка маркетинга стоит, версии нет» — нет. На уровне DRF поле молчит (`required=False`,
   `default=""`) и доходит до `validate()` пустой строкой: ветка отказа та же, но добирается до неё иначе.

**Четвёртый круг ревью — восемь замечаний.**

1. **Ответ `400` перестал быть свободным объектом.** Прежняя схема `type: object` + `additionalProperties: {}`
   давала фронту `{ [key: string]: unknown }`: машинный код `error` и структура `details` существовали
   только в prose и примерах, а компилятор о них не знал. Новый модуль `apps/common/api_schema.py`
   объявляет `FieldValidationErrorResponse` (плоское «поле → список сообщений»),
   `ConsentTextOutdatedResponse` (`error` + `details`) и связывает их `oneOf` в
   `ConsentValidationErrorResponse`, на который ссылаются оба эндпоинта. Плоскую форму обычным
   сериализатором не описать — набор её ключей зависит от запроса, а `Serializer` даёт фиксированный
   `properties`; схему задаёт `OpenApiSerializerExtension`, а класс-маркер нужен лишь затем, чтобы
   drf-spectacular зарегистрировал имя: на голый dict он `$ref` не создаёт. У `error` стоит `const`, а не
   `enum` из одного значения — `enum` хук `postprocess_schema_enums` вынес бы отдельным
   компонентом-перечислением, за которым ничего не стоит. В типах фронта результат:
   `error: 'consent_text_outdated'` литералом, `details: { [key: string]: string[] }`.
2. **Типы не оставлены лежать без дела.** `constants/consentTexts.ts` сужает ответ к сгенерированному
   `ConsentTextOutdatedResponse`, а `CONSENT_TEXT_OUTDATED_CODE` объявлен как
   `ConsentTextOutdatedResponse['error']`: смена кода на сервере теперь ломает компиляцию фронта, а не
   поведение в проде. Иначе «защита машинного кода» осталась бы декларацией в контракте.
3. **Условная обязательность выражена схемой, а не словами.** У `UserRegistrationRequest` появились
   `if` / `then`: при `marketing_consent: true` версия обязательна и непуста. `dependentRequired` был бы
   неверен — он срабатывает на само присутствие `marketing_consent`, а обе формы всегда шлют его, в том
   числе `false`. `minLength: 1` в `then` нужен потому, что `default: ""` иначе разрешал бы пустую строку,
   которую сервер отклонит тем же кодом. Условие добавляет `UserRegistrationRequestSchemaExtension` рядом
   с сериализатором — расширение регистрируется фактом объявления класса, а отдельный модуль схемы
   пришлось бы импортировать из `AppConfig.ready()`.
4. **Ручной `RegisterRequest` приведён к контракту.** Поле `marketing_consent_text_version` стало
   обязательным: сгенерированный тип помечал его так с самого начала (`default` в схеме), backend
   отклоняет комбинацию «галочка есть, версии нет», а обе формы версию всегда шлют — необязательное поле
   позволяло собрать заведомо отклоняемый payload. Страж компиляционный: `@ts-expect-error` сам становится
   ошибкой `tsc`, если поле снова сделают необязательным.
5. **Compliance-утверждения ослаблены до фактически обеспеченных** — три разных завышения.
   *Версия текста* подтверждает совместимость официального бандла (отсекает вкладку, открытую до правки
   формулировки), но не факт показа текста человеку: произвольный API-клиент пришлёт ту же строку, ничего
   не отрисовав. *Append-only* держится запретами админки и отсутствием пишущих путей — `objects.update()`,
   `delete()` и прямой SQL журнал меняют, ни триггера, ни `REVOKE` нет. *Ограничения БД* неравносильны: у
   `source` проверяется принадлежность перечислению, у версии — только непустота, потому что набор
   действующих версий меняется правкой JSON и CHECK по нему требовал бы миграции на каждую правку текста.
   Та же правка внесена в docstring `constants/consentTexts.ts`: оставить в коде утверждение, снятое в
   документе, значило бы разойтись с самим собой.
6. **Три документа приведены к фактам.** В Python-блок `02-data-models.md` добавлен
   `USER_CONSENT_SOURCE_VALUES` — без него буквальное выполнение примера давало `NameError`. Блок индексов
   в `09-database-schema.md` заменён снятым из `pg_indexes`: вымышлены были **все шесть** имён, а не два
   новых (Django не создаёт ни `idx_*`, ни частичных `WHERE`, ни `DESC`), и парные `_like`-индексы не
   показывались вовсе. Пример payload B2B-регистрации в `18-b2b-verification-workflow.md` получил
   consent-поля и предупреждение: версии из документа копировать нельзя, они устаревают при каждой правке
   формулировки.
7. **Числа GitNexus сняты двумя срезами.** Прежняя запись называла `9743/16069` незакоммиченным сдвигом —
   верно на момент внесения, неверно после коммита `34fbe487`. Теперь в File List отдельно закоммиченное
   (`9657/15912 → 9743/16069`, с разбивкой по коммитам) и отдельно рабочее дерево
   (`9743/16069 → 9749/16083`).

**Приёмка на проде** (вне объёма разработки, по уроку стори 41.5): миграции на прод накатываются вручную,
после выката нужны `showmigrations common` (ожидаются применёнными **обе** — `0019` и `0020`) и
`SELECT count(*) FROM common_userconsent;` — на 2026-08-30 там было 0 строк, значение `unknown` у появившихся
ожидаемо и допустимо. `0020` добавляет CHECK и падает при накате, если в `source` найдётся значение вне
перечисления; на такой строке чинить нужно данные, а не ослаблять ограничение. После рестарта backend на проде
обязателен дополнительный `restart nginx`.

### File List

Собрано командами `git diff --name-status` и `git status --porcelain`, не по памяти.

**Новые файлы (A):**

- `backend/apps/common/consent_texts.json`
- `backend/apps/common/consent_texts.py` — *третья доработка по ревью:* `UnicodeDecodeError` заворачивается в `ConsentTextsError`
- `backend/apps/common/migrations/0019_userconsent_source_and_text_version.py`
- `backend/apps/common/migrations/0020_userconsent_source_valid.py` — *третья доработка по ревью:* источник ограничен перечислением на уровне БД
- `backend/apps/common/tests/test_consent_texts.py` — *третья доработка по ревью*
- `backend/apps/common/api_schema.py` — *четвёртая доработка по ревью:* именованные компоненты `400` и их связка `oneOf`
- `backend/apps/common/tests/test_api_schema.py` — *четвёртая доработка по ревью:* страж схемы `400` и условной обязательности версии
- `frontend/src/__tests__/register-request-contract.test.ts` — *четвёртая доработка по ревью:* компиляционный страж обязательных consent-версий в `RegisterRequest`
- `backend/tests/consent_versions.py` — *доработка по ревью:* общие версии для тестовых payload'ов; литералы в тринадцати файлах пришлось бы чинить при каждой правке текста
- `frontend/src/__tests__/consent-texts-registry.test.tsx`
- `frontend/src/constants/consentTexts.ts` — *доработка по ревью:* версии, которые формы отправляют серверу; *четвёртая доработка:* форма ответа и машинный код берутся из сгенерированного контракта

**Изменённые файлы (M):**

- `backend/apps/common/models.py` — *третья доработка по ревью:* `USER_CONSENT_SOURCE_VALUES` и `userconsent_source_valid`
- `backend/apps/common/views.py` — *четвёртая доработка по ревью:* `400` подписки ссылается на именованную схему
- `backend/apps/common/admin.py`
- `backend/apps/common/serializers.py` — *доработка по ревью*
- `backend/apps/users/serializers.py` — *доработка по ревью*; *четвёртая доработка:* `UserRegistrationRequestSchemaExtension` с `if`/`then`
- `backend/apps/users/views/authentication.py` — *четвёртая доработка по ревью:* `400` регистрации ссылается на именованную схему
- `backend/apps/common/tests/test_user_consent.py` — *третья доработка по ревью*
- `backend/tests/integration/test_common_subscribe_api.py`
- `backend/tests/integration/test_auth_registration_consent.py` — *третья доработка по ревью*
- `frontend/src/components/auth/B2BRegisterForm.tsx`
- `frontend/src/components/auth/RegisterForm.tsx` — *доработка по ревью*
- `frontend/src/components/home/SubscribeForm.tsx` — *доработка по ревью*
- `frontend/src/components/home/ElectricSubscribeForm.tsx` — *доработка по ревью*
- `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx`
- `frontend/src/services/subscribeService.ts` — *вторая доработка по ревью:* машинный код с верхнего уровня ответа
- `frontend/src/types/api.ts`, `frontend/src/types/api.generated.ts` — *доработка по ревью*; *четвёртая доработка:* `marketing_consent_text_version` обязателен в ручном типе, в сгенерированном появились три компонента `400` и `if`/`then` у `UserRegistrationRequest`
- `docs/api/openapi.yaml` — *доработка по ревью*; *четвёртая доработка:* перегенерирован целиком (`spectacular --validate`), сверен `check_openapi_sync`
- `frontend/src/services/__tests__/subscribeService.test.ts`, `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx` — *вторая доработка по ревью*
- `_bmad-output/implementation-artifacts/tasks/dev-task-textcontent-price-cta-separation.md` — *вторая доработка по ревью:* ссылки на `deferred-work.md` переведены с номеров строк на заголовки пунктов
- `docs/architecture/02-data-models.md` — *четвёртая доработка по ревью:* `USER_CONSENT_SOURCE_VALUES` в примере модели, ослабленные инварианты
- `docs/architecture/04-component-structure.md` — *четвёртая доработка по ревью:* `api_schema.py` в перечне модулей `apps/common`
- `docs/architecture/09-database-schema.md` — *четвёртая доработка по ревью:* индексы заменены фактическими из `pg_indexes`
- `docs/architecture/11-security-performance.md` — *четвёртая доработка по ревью:* границы append-only, границы гарантии версии, асимметрия CHECK-ограничений
- `docs/architecture/18-b2b-verification-workflow.md` — *четвёртая доработка по ревью:* consent-поля в примере payload
- `docs/architecture/index.md` — *четвёртая доработка по ревью:* строка «История изменений» за 2026-09-10
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `_bmad-output/implementation-artifacts/Story/41-9-consent-journal-text-version-and-source.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Тесты, приведённые к обязательной версии текста** (*доработка по ревью*; payload регистрации и подписки без версии теперь отклоняется — это работающая защита, а не сломанные тесты):

- `backend/tests/integration/test_auth_registration_tokens.py`
- `backend/tests/integration/test_catalog_api.py`
- `backend/tests/integration/test_import_role_from_1c.py`
- `backend/tests/integration/test_portal_registration_1c_link.py`
- `backend/tests/integration/test_registration_emails.py`
- `backend/tests/integration/test_user_api.py`
- `backend/tests/integration/test_verification_workflow.py`
- `backend/tests/integration/manual_test_user_management_api.py`
- `backend/tests/regression/test_epic_28_intact.py`
- `backend/tests/unit/test_serializers/test_user_serializers.py`
- `backend/tests/unit/test_user_verification.py`
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx`
- `frontend/src/components/home/__tests__/SubscribeForm.test.tsx`
- `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx`
- `frontend/src/services/__tests__/subscribeService.test.ts`

**Файл из коммита создания стори** (замечание ревью, разобрано выше):

- `_bmad-output/implementation-artifacts/tasks/dev-task-textcontent-price-cta-separation.md` — добавлен `786881e7` вместе с самой стори; к реализации 41.9 не относится, но в дифф ветки попадает. **Уточнение по факту дерева:** коммит `786881e7` лежит на **локальной** `develop` (она `ahead 1` относительно `origin/develop`, куда его не пустит защита ветки), поэтому `git diff develop...HEAD` файла не показывает, а `git diff origin/develop...HEAD` показывает как `A`. Не удаляется: это задача-продолжение стори 41.8. Вторая доработка по ревью правит его по существу — ссылки на `deferred-work.md`.

**Побочные правки, не относящиеся к стори** (по уроку стори 41.0–41.7 — не выкидываются, а называются):

- `AGENTS.md`, `CLAUDE.md` — автосчётчик GitNexus. Числа сверены `git diff`, а не по памяти
  (замечание ревью), и запись здесь ведётся по **двум** срезам, потому что каждый круг доработок
  переиндексирует дерево и сдвигает счётчик:
  - **Закоммичено** (`git diff 792ce210..HEAD -- AGENTS.md CLAUDE.md`):
    `9657 symbols, 15912 relationships` → `9743, 16069`. Промежуточные значения по коммитам:
    `0f6e13e3` довёл счётчик до `9695, 15982`, `8ef96123` — до `9717, 16022`,
    `34fbe487` — до `9743, 16069`.
  - **Не закоммичено** (`git diff HEAD -- AGENTS.md CLAUDE.md`, четвёртый круг ревью):
    `9743, 16069` → `9749, 16083`.

  Прежняя запись называла `9743/16069` незакоммиченным сдвигом — на момент её внесения это было
  верно, к третьему коммиту стори перестало (замечание ревью). Все правки внесены
  переиндексацией `npx gitnexus analyze`, а не работой над стори; строка лежит вне MCP-маркеров,
  поэтому переживает регенерацию.
