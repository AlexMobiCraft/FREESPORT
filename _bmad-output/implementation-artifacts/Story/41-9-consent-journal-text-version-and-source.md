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

- [x] [Review][Patch] Сервер должен отклонять устаревшую версию текста согласия — решение Alex: форма передаёт показанную версию, сервер сравнивает её с текущей; при несовпадении запрос отклоняется с требованием обновить страницу. Сейчас формы отправляют только boolean-согласие, а `current_consent_text_version(...)` всегда фиксирует текущую серверную версию, даже если пользователь отправил старую вкладку с прежним текстом. [`backend/apps/users/views/authentication.py:157-174`, `backend/apps/common/views.py:437-445`, `frontend/src/components/auth/RegisterForm.tsx:111-133`, `frontend/src/components/auth/B2BRegisterForm.tsx:111-129`]
  - Версия зашита в бандл фронта (`frontend/src/constants/consentTexts.ts`), а **не** запрашивается у сервера: она обязана доказывать, какой текст был на экране. Версия, полученная запросом в момент отправки, всегда актуальна и не доказывает ничего — старая вкладка получила бы свежее значение и записала согласие на формулировку, которой не видела.
  - `SubscribeSerializer.consent_text_version` (обязательное), `UserRegistrationSerializer.pdp_consent_text_version` (обязательное) и `marketing_consent_text_version` (обязательное при `marketing_consent: true`). Несовпадение или отсутствие — `400`, код `consent_text_outdated`, сообщение «Текст согласия обновился. Обновите страницу и подтвердите согласие заново.».
  - В журнал по-прежнему кладётся значение из реестра, а не присланное клиентом: запрос лишь доказывает право записать текущую версию.
  - Контракт обновлён по правилу проекта: `docs/api/openapi.yaml` (перегенерирован `spectacular`, сверен `check_openapi_sync`) и `npm run generate:types`.
- [x] [Review][Patch] Исторические версии не защищены от изменения или удаления ревизии из реестра [`backend/apps/common/consent_texts.py:98-133`]
  - Раздел `known_versions` — append-only список версий всех когда-либо действовавших формулировок; загрузчик требует **точного** совпадения с набором, вычисленным из ревизий. Правка текста старой ревизии и её удаление ловятся одинаково: версия исчезает из вычисленного набора, реестр перестаёт загружаться и называет пропавшие строки. Новая ревизия тоже обязана быть внесена — её версию не нужно считать руками, сообщение об ошибке печатает готовую строку.
- [x] [Review][Patch] JSON-загрузчик молча принимает повторяющиеся ключи и может подменить поверхность либо привязку [`backend/apps/common/consent_texts.py:194-199`]
  - `json.loads(..., object_pairs_hook=_reject_duplicate_keys)`: повтор ключа — `ConsentTextsError`, а не «побеждает нижний».
- [x] [Review][Patch] Загрузчик допускает версию длиннее `UserConsent.consent_text_version(max_length=64)` [`backend/apps/common/consent_texts.py:105-124`]
  - Константа `MAX_VERSION_LENGTH = 64` в модуле (Django он не импортирует — тот же JSON читает страж на фронте); расхождение с полем модели ловит `test_max_version_length_matches_model_field`.
- [x] [Review][Patch] В diff присутствует посторонний task-файл, отсутствующий в заявленном File List [`_bmad-output/implementation-artifacts/tasks/dev-task-textcontent-price-cta-separation.md:1-6`]
  - Файл добавлен коммитом `786881e7` («создать стори … и dev-task по склейкам textContent») — то есть частью создания стори, а не её реализации; в диффе ветки против `develop` он поэтому присутствует. Файл нужен (задача-продолжение стори 41.8) и не удаляется; он назван в File List отдельным разделом.
- [x] [Review][Defer] Celery-задачи B2B-регистрации публикуются до фиксации транзакции и могут получить ID откатившегося пользователя [`backend/apps/users/serializers.py:266-271`] — deferred, pre-existing

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
3. **История ревизий стала неизменяемой.** Раздел `known_versions` перечисляет версии всех когда-либо
   действовавших формулировок; загрузчик требует точного совпадения этого списка с набором, вычисленным из
   ревизий. Правка текста старой ревизии и её удаление ловятся одинаково — версия пропадает из вычисленного
   набора. Новая ревизия тоже обязана быть внесена, и её строку печатает сообщение об ошибке: считать хеш руками
   не нужно.
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

**Приёмка на проде** (вне объёма разработки, по уроку стори 41.5): миграция на прод накатывается вручную,
после выката нужны `showmigrations common` и `SELECT count(*) FROM common_userconsent;` — на 2026-08-30 там
было 0 строк, значение `unknown` у появившихся ожидаемо и допустимо. После рестарта backend на проде
обязателен дополнительный `restart nginx`.

### File List

Собрано командами `git diff --name-status` и `git status --porcelain`, не по памяти.

**Новые файлы (A):**

- `backend/apps/common/consent_texts.json`
- `backend/apps/common/consent_texts.py`
- `backend/apps/common/migrations/0019_userconsent_source_and_text_version.py`
- `backend/apps/common/tests/test_consent_texts.py`
- `backend/tests/consent_versions.py` — *доработка по ревью:* общие версии для тестовых payload'ов; литералы в тринадцати файлах пришлось бы чинить при каждой правке текста
- `frontend/src/__tests__/consent-texts-registry.test.tsx`
- `frontend/src/constants/consentTexts.ts` — *доработка по ревью:* версии, которые формы отправляют серверу

**Изменённые файлы (M):**

- `backend/apps/common/models.py`
- `backend/apps/common/views.py`
- `backend/apps/common/admin.py`
- `backend/apps/common/serializers.py` — *доработка по ревью*
- `backend/apps/users/serializers.py` — *доработка по ревью*
- `backend/apps/users/views/authentication.py`
- `backend/apps/common/tests/test_user_consent.py`
- `backend/tests/integration/test_common_subscribe_api.py`
- `backend/tests/integration/test_auth_registration_consent.py`
- `frontend/src/components/auth/B2BRegisterForm.tsx`
- `frontend/src/components/auth/RegisterForm.tsx` — *доработка по ревью*
- `frontend/src/components/home/SubscribeForm.tsx` — *доработка по ревью*
- `frontend/src/components/home/ElectricSubscribeForm.tsx` — *доработка по ревью*
- `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx`
- `frontend/src/types/api.ts`, `frontend/src/types/api.generated.ts` — *доработка по ревью*
- `docs/api/openapi.yaml` — *доработка по ревью*
- `docs/architecture/02-data-models.md`
- `docs/architecture/04-component-structure.md`
- `docs/architecture/09-database-schema.md`
- `docs/architecture/11-security-performance.md`
- `docs/architecture/18-b2b-verification-workflow.md`
- `docs/architecture/index.md`
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

**Файл из коммита создания стори, присутствующий в диффе ветки** (замечание ревью, разобрано выше):

- `_bmad-output/implementation-artifacts/tasks/dev-task-textcontent-price-cta-separation.md` — добавлен `786881e7` вместе с самой стори; к реализации не относится, но в `git diff develop...HEAD` виден. Не удаляется: это задача-продолжение стори 41.8.

**Побочные правки, не относящиеся к стори** (по уроку стори 41.0–41.7 — не выкидываются, а называются):

- `AGENTS.md`, `CLAUDE.md` — автосчётчик GitNexus (`9657 symbols, 15912 relationships` → `9647, 15902`).
  Изменения присутствовали в рабочем дереве **до** начала стори и внесены переиндексацией, а не ею.
