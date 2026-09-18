---
baseline_commit: 43ea1539
---

# Story 41.20: Согласие на рассылку как согласие, формы без плейсхолдеров `example`, дополнение реестра 168-ФЗ

Status: done
Baseline Revision: 43ea1539

## Story

As a оператор персональных данных,
I want чтобы согласие на рассылку однозначно читалось как согласие, а формы не содержали технических образцов на латинице,
so that форма соответствовала 152-ФЗ и 38-ФЗ по букве и не порождала новых срабатываний 168-ФЗ.

**Закрывает:** FR-41-36; запись `deferred-work.md` о плейсхолдере формы восстановления пароля (стори 41.4, 2026-09-05). **Решения владельца:** D5 (Alex, 17.09.2026, `sprint-change-proposal-2026-09-16.md` §4); E20, E21 и охват D5 — Alex, 17.09.2026, раздел «Решения по вопросам create-story».

## Утверждённые решения (дословно, не пересматривать)

- **D5 — текст согласия на рассылку:** «Я даю согласие на получение информационных и рекламных рассылок от OPTISPORT по электронной почте». Обязательность **не менять**: в подписке галочка рассылки обязательна, в регистрации — необязательна.
- **Охват D5 — четыре формы, не три.** `SubscribeForm` и `ElectricSubscribeForm` показывают поверхность `newsletter_marketing_checkbox`; `RegisterForm` **и** `B2BRegisterForm` — одну общую поверхность `registration_marketing_checkbox`. Правка поверхности меняет текст в обеих формах регистрации автоматически, и страж `consent-texts-registry.test.tsx` этого требует. Поверхность **не разделять**.
- **E21 — плейсхолдеры `example` удалить, не заменять.** Видимая подпись «Электронная почта» есть у всех пяти полей, тип поля — `email`, поэтому образец адреса не нужен. Любая замена оставляет латиницу и рискует повторить регресс E10 (стори 41.16 заменила плейсхолдер на `name@example.ru` и сама создала срабатывание). Плейсхолдер, дублирующий видимую подпись, — антипаттерн доступности, поэтому текстовая подсказка вместо образца тоже отклонена.
- **E20 `Edition` — оставить.** Официальное наименование товарных линеек BoyBo «First Edition» и «Black Edition», источник — данные 1С. Основание то же, что у E12 `B-series`, E14 `Brooklyn`, E17 `RuscoSport`, E19 `Tsunami`. Правок кода нет, только запись в реестре.

### Новые ревизии реестра текстов согласий

Текст обеих ревизий дословно одинаков (D5), поэтому различать их обязана **метка**: версия считается как `<метка>-<32 hex sha256 текста>`, и загрузчик `consent_texts.py` отклоняет загрузку при совпадении версий двух ревизий. Прецедент — ПДн подписки и ПДн регистрации: тексты совпадают дословно со стори 41.11, версии различает только метка.

| Поверхность | Метка ревизии | Версия (внести дословно) |
|---|---|---|
| `newsletter_marketing_checkbox` | `2026-09-17-newsletter` | `2026-09-17-newsletter-4e2471b54124acaf12cfed1b8196b684` |
| `registration_marketing_checkbox` | `2026-09-17-registration` | `2026-09-17-registration-4e2471b54124acaf12cfed1b8196b684` |

Хеш `4e2471b54124acaf12cfed1b8196b684` посчитан от текста D5 (97 символов) и от метки не зависит. Если ревизии вносятся не 17.09.2026, метки берут фактическую дату с теми же суффиксами (`<ГГГГ-ММ-ДД>-newsletter`, `<ГГГГ-ММ-ДД>-registration`), хеш при этом не меняется. Длина версии — 54 и 56 символов, предел `UserConsent.consent_text_version` — 64.

## Acceptance Criteria

### AC1 — текст согласия на рассылку во всех четырёх формах

**Given** формы подписки (blue и electric) и регистрации (обычная и B2B)
**When** они отображаются
**Then** доступное имя чекбокса рассылки — дословно текст D5 «Я даю согласие на получение информационных и рекламных рассылок от OPTISPORT по электронной почте»
**And** обязательность не изменилась: в подписке обе галочки обязательны (`aria-required="true"`, отправку блокирует `react-hook-form`, а не нативный `required`), в регистрации чекбокс рассылки необязателен и без inline error-state

### AC2 — реестр текстов согласий и журнал

**Given** новые формулировки
**When** форма отправляется
**Then** в запросе и в `UserConsent` уходит новая версия текста рассылки — своя у подписки и своя у регистрации
**And** прежние версии `2026-09-12-1a97b44f2bc0b52e69d15d705be59c0c` и `2026-09-12-a49604a66adaadfdc221bdc141d8d97d` остаются в `known_versions` и разрешаются в свой текст; записи журнала прода их не теряют
**And** неизвестная или устаревшая версия отклоняется бэкендом кодом `consent_text_outdated`, как раньше
**And** backend-тесты реестра, схемы и журнала выполнены в Docker/PostgreSQL; `docs/api/openapi.yaml` синхронизирован с кодом (`check_openapi_sync` — OK, NFR-41-02)

### AC3 — публичные формы без `example`

**Given** публичные формы: подписка blue, подписка electric, регистрация, B2B-регистрация, восстановление пароля
**When** проверяется разметка
**Then** ни в видимом тексте, ни в атрибуте `placeholder` нет подстроки `example`; у поля электронной почты каждой формы атрибута `placeholder` нет вовсе
**And** у каждого поля электронной почты сохранена видимая подпись «Электронная почта» и доступное имя по ней
**And** axe-проверки форм подписки проходят без новых нарушений

### AC4 — реестр редакторских решений 41.16 дополнен

**Given** реестр решений в `Story/41-16-editorial-audit-decision-register.md`
**When** он дополняется по отчёту 16.09.2026
**Then** основание E03 `privacy` исправлено: видимый URL политики присутствует в тексте CMS (`https://optisport.ru/privacy-policy`), адрес не переводится; решение «оставить» сохранено
**And** добавлена запись E20 `Edition`: контекст по данным 1С, решение «оставить», согласующий Alex, дата 17.09.2026
**And** добавлена запись E21 `example`: контекст (пять плейсхолдеров публичных форм, регресс E10), решение «удалить плейсхолдер», исполнитель DEV, ссылка на коммит этой стори
**And** итог реестра пересчитан: 21 основной ID вместо 19

### AC5 — приёмка на проде (NFR-41-08)

**Given** выкат на прод
**When** гость без cookie открывает `/home`, `/electric`, `/register`, `/b2b-register`, `/password-reset`
**Then** новые подписи чекбоксов рассылки видны, поля электронной почты без плейсхолдеров, подписи полей на месте
**And** в клиентских чанках этих страниц 0 вхождений `example` и 0 вхождений прежних формулировок «Я согласен(на) получать…»
**And** результат приложен к стори

## Tasks / Subtasks

- [x] **Task 0 — preflight** (все AC)
  - [x] 0.1 Ветка `feature/41-20-newsletter-consent-wording` от актуального `origin/develop`. Прямые коммиты в `develop` запрещены.
  - [x] 0.2 `npx gitnexus status`. При `stale` сверить `git diff --stat <indexed> HEAD`: если разница только в merge-коммитах без изменений кода — индекс годен; иначе попросить пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [x] 0.3 `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` перед правкой символов. Снимок create-story — в Dev Notes, раздел «GitNexus». `impact` по именам компонентов **неоднозначен** (`Function:` и `Const:` на одну строку) — звать по UID вида `Function:frontend/src/components/home/SubscribeForm.tsx:SubscribeForm`.
  - [x] 0.4 Зафиксировать исходный прогон (в `frontend/`), до правок всё зелёное:
    ```bash
    npx vitest run src/__tests__/consent-texts-registry.test.tsx \
      src/components/home/__tests__/SubscribeForm.test.tsx \
      src/components/home/__tests__/ElectricSubscribeForm.test.tsx \
      src/components/auth/__tests__/RegisterForm.test.tsx \
      src/components/auth/__tests__/B2BRegisterForm.test.tsx \
      src/components/auth/__tests__/PasswordResetRequestForm.test.tsx
    ```

- [x] **Task 1 — две новые ревизии в реестре текстов согласий** (AC1, AC2)
  - [x] 1.1 `backend/apps/common/consent_texts.json` — в `surfaces.newsletter_marketing_checkbox.revisions` **дописать** ревизию в конец списка (действующая — последняя, история дополняется, а не переписывается): `label` = `2026-09-17-newsletter`, `text` = текст D5 дословно, одной строкой, с одиночными пробелами (загрузчик отклоняет ненормализованный текст).
  - [x] 1.2 То же для `surfaces.registration_marketing_checkbox.revisions`: `label` = `2026-09-17-registration`, тот же текст.
  - [x] 1.3 В `known_versions` **добавить** две строки из таблицы «Новые ревизии». Прежние шесть строк **не трогать**: удаление или правка исторической версии роняет загрузку (`_check_known_versions`) и обрывает связь записей журнала прода со своим текстом.
  - [x] 1.4 Обновить `description` обеих поверхностей: назвать стори 41.20 и решение D5 как причину новой ревизии. Формулировки про 41.11 сохранить — они объясняют историю.
  - [x] 1.5 **Не менять:** `consent_texts.py` (загрузчик, формула версии, `MAX_VERSION_LENGTH`, `VERSION_DIGEST_HEX_LENGTH`), состав `surfaces` (пять поверхностей), состав `bindings` (шесть привязок), поверхность `newsletter_checkbox`.
  - [x] 1.6 Проверка загрузки: `load_registry` кэширован через `lru_cache`, поэтому после правки JSON **перезапустить backend-контейнер** (`docker compose --env-file .env -f docker/docker-compose.yml restart backend`), иначе в живом процессе останется прежний реестр. В тестовом контейнере процесс новый, кэш пустой.

- [x] **Task 2 — константы версий на фронте** (AC1, AC2)
  - [x] 2.1 `frontend/src/constants/consentTexts.ts` — `CONSENT_TEXT_VERSIONS.newsletterMarketing` и `.registrationMarketing` заменить на новые версии из таблицы. `newsletterPdp` и `registrationPdp` **не трогать**.
  - [x] 2.2 JSDoc обеих констант дополнить ссылкой на стори 41.20 и D5. Остальной файл (`CONSENT_TEXT_OUTDATED_CODE`, `getConsentTextOutdatedMessage`, `CONSENT_TEXT_VERSION_FIELDS`) не менять.

- [x] **Task 3 — текст чекбокса рассылки в четырёх формах** (AC1)
  - [x] 3.1 `frontend/src/components/home/SubscribeForm.tsx:295-296` — текст внутри `<label id={marketingConsentLabelId}>` заменить на текст D5. Перенос строки в JSX допустим: доступное имя нормализует пробелы. **Не менять** `aria-labelledby`, `aria-required`, `validate` (`MARKETING_CONSENT_REQUIRED`), `disabled`, порядок `register`, `disabled={isSubmitting || !pdpConsent}` у кнопки.
  - [x] 3.2 `frontend/src/components/home/ElectricSubscribeForm.tsx:385-386` — то же внутри `ElectricConsentCheckbox`. Структуру метки (один `<label>`, `labelledBy={marketingConsentLabelId}`) не менять.
  - [x] 3.3 `frontend/src/components/auth/RegisterForm.tsx:498-499` — то же. Чекбокс остаётся необязательным: `register('marketing_consent')` без `validate`/`required`, inline error-state не назначается, `aria-required` не добавлять.
  - [x] 3.4 `frontend/src/components/auth/B2BRegisterForm.tsx:547-548` — то же, те же ограничения.
  - [x] 3.5 Текст чекбоксов **ПДн** во всех четырёх формах не трогать: их поверхности и версии не меняются.
  - [x] 3.6 Сообщение ошибки `MARKETING_CONSENT_REQUIRED` («Необходимо согласие на получение рассылок по электронной почте.») не менять — оно дословно совпадает с бэкендом.

- [x] **Task 4 — удалить плейсхолдеры `example`** (AC3)
  - [x] 4.1 `frontend/src/components/home/SubscribeForm.tsx:219` — удалить строку `placeholder="name@example.ru"`. `label="Электронная почта"`, `type="email"`, `aria-required`, `aria-invalid` сохранить.
  - [x] 4.2 `frontend/src/components/home/ElectricSubscribeForm.tsx:328` — удалить `placeholder="name@example.ru"`. Класс `placeholder:text-[var(--color-text-muted)]` в `className` можно оставить (мёртвое правило, вёрстку не меняет) — **стили не трогать**, чтобы не расширять дифф.
  - [x] 4.3 `frontend/src/components/auth/RegisterForm.tsx:307` — удалить `placeholder="user@example.com"`.
  - [x] 4.4 `frontend/src/components/auth/B2BRegisterForm.tsx:374` — удалить `placeholder="company@example.com"`.
  - [x] 4.5 `frontend/src/components/auth/PasswordResetRequestForm.tsx:77` — удалить `placeholder="example@email.com"`. `autoComplete="email"`, `aria-required`, `aria-describedby` сохранить.
  - [x] 4.6 **Не трогать** остальные плейсхолдеры этих форм: `«Иван»`, `«Петров»`, `«ООО «Спортмастер»»`, `«1234567890 или 123456789012»`, `«+7 (999) 123-45-67»`, `«г. Москва, ул. Примерная, д. 1»`, `«••••••••»` — они русскоязычные или нейтральные, в объём E21 не входят.
  - [x] 4.7 **Не трогать** `user@example.com` в примере OpenAPI (`backend/apps/common/views.py:336, 353`) и тестовые фикстуры `*@example.com` в `__tests__`/`e2e`: это не видимый текст публичной формы. Прецедент — остаток E08 в `help_text` Swagger (реестр 41.16), зафиксированный как осознанное исключение. Зафиксировать так же в Completion Notes.
  - [x] 4.8 Проверка AC3 (из корня репозитория; обе команды должны вернуть пусто):
    ```bash
    grep -rn 'example' frontend/src --include=*.tsx --include=*.ts | grep -v '__tests__\|__mocks__\|\.test\.\|api\.generated' | grep -v '\* *@example'
    grep -rn 'placeholder' frontend/src/components/home/SubscribeForm.tsx frontend/src/components/home/ElectricSubscribeForm.tsx frontend/src/components/auth/PasswordResetRequestForm.tsx
    ```
    Второй grep в `RegisterForm.tsx`/`B2BRegisterForm.tsx` не делать: там остаются законные плейсхолдеры по 4.6.

- [x] **Task 5 — примеры контракта и документации** (AC2)
  - [x] 5.1 `backend/apps/common/views.py:339` — в `OpenApiExample` `successful_subscription_request` заменить литерал `marketing_consent_text_version` на новую версию подписки. `pdp_consent_text_version` (`:338`) не менять. Литералы обязаны совпадать с действующими ревизиями — это закреплено `test_api_schema.py::test_subscribe_example_uses_current_versions`.
  - [x] 5.2 `docs/api/openapi.yaml:105` — привести то же значение примера в соответствие **точечной правкой**, затем проверить `check_openapi_sync`. Полную регенерацию `spectacular` не делать: в стори 41.16 она подтянула несвязанный дрейф схемы (`/newsletter/unsubscribe/one-click/{token}/`, порядок методов `users_addresses`) и раздула дифф. Команда сверки (из `docker/`, `docs` монтируется отдельно — в тестовом контейнере смонтирован только `backend/`):
    ```bash
    MSYS_NO_PATHCONV=1 docker compose -p freesport-lint -f docker-compose.test.yml run --rm --no-deps -T \
      -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend \
      python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml
    ```
  - [x] 5.3 `npm run generate:types` (в `frontend/`) — запустить и убедиться, что `src/types/api.generated.ts` **не изменился**: меняется только значение примера, а его `openapi-typescript` в типы не переносит. Появился дифф — это несвязанный дрейф: остановиться и доложить, в коммит не включать.
  - [x] 5.4 `docs/architecture/18-b2b-verification-workflow.md:142` — в примере запроса регистрации заменить `marketing_consent_text_version` на новую версию регистрации.
  - [x] 5.5 Story-файлы 35.2, 41.3, 41.9, 41.11 и `tasks/intent-site-audit-*.md` **не править**: это исторические артефакты, прежние формулировки в них верны на свою дату.

- [x] **Task 6 — тесты** (AC1–AC3)
  - [x] 6.1 `frontend/src/components/home/__tests__/SubscribeForm.test.tsx:18-19` — константу `MARKETING_CONSENT_NAME` заменить на текст D5. Больше в файле правок нет: чекбокс ищется по этой константе.
  - [x] 6.2 `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx:33-34` — то же.
  - [x] 6.3 `frontend/src/components/auth/__tests__/RegisterForm.test.tsx`:
    - `:47-50` — регулярку `getMarketingConsent` перевести на новый текст (предпочтительно: завести константу `MARKETING_CONSENT_NAME` с дословным текстом D5 и искать по точному имени, как в B2B-тесте);
    - `:115-124` — тест `should name the email channel in the marketing consent (Story 41.11)`: ожидание `/^Я согласен\(на\) получать/` **упадёт**. Заменить на `/^Я даю согласие на получение/`; проверку `/по электронной почте$/` (канал, FR-41-26) сохранить; в комментарии добавить D5 и стори 41.20 рядом с FR-41-26.
  - [x] 6.4 `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx:16-17` — константу `MARKETING_CONSENT_NAME` заменить на текст D5, комментарий дополнить D5.
  - [x] 6.5 `frontend/src/components/auth/__tests__/PasswordResetRequestForm.test.tsx:45-50` — тест `should have email placeholder` переписать в «поле электронной почты не имеет плейсхолдера»: `expect(emailInput).not.toHaveAttribute('placeholder')`, доступное имя по видимой подписи сохраняется. Фикстуры `user@example.com` в остальных тестах файла не трогать.
  - [x] 6.6 `frontend/src/__tests__/consent-texts-registry.test.tsx` — тексты подтягиваются из реестра, поэтому основные проверки зелёные без правок. **Добавить** две:
    - в тест «константы версий фронта совпадают с действующими ревизиями реестра» — `expect(CONSENT_TEXT_VERSIONS.newsletterMarketing).not.toBe(CONSENT_TEXT_VERSIONS.registrationMarketing)` с комментарием: тексты дословно совпадают, версии различает метка ревизии, иначе загрузчик отклонил бы дубль;
    - в тест «исторические версии остаются в known_versions» — литералы `2026-09-12-1a97b44f2bc0b52e69d15d705be59c0c` и `2026-09-12-a49604a66adaadfdc221bdc141d8d97d` (прежние формулировки рассылки подписки и регистрации, на них ссылается журнал).
  - [x] 6.7 NEW `frontend/src/__tests__/public-forms-no-example-placeholders.test.tsx` — страж инварианта AC3, один на все пять форм. Блок моков взять из `consent-texts-registry.test.tsx` (`next/navigation`, `@/services/authService`, `@/services/subscribeService`, `react-hot-toast`) и дополнить `requestPasswordReset: vi.fn()` для `authService`. Для каждой формы:
    - `render`, затем `cleanup` в `beforeEach`;
    - у `input[type="email"]` нет атрибута `placeholder`;
    - у него есть доступное имя, содержащее «Электронная почта»;
    - `container.innerHTML` не содержит `example` (регистр не важен) — ловит и видимый текст, и любой другой атрибут.
    Тест пишется как `it.each` по списку `[имя формы, компонент]`, чтобы новая публичная форма добавлялась одной строкой.
  - [x] 6.8 NEW backend-тест в `backend/apps/common/tests/test_consent_texts.py` — `test_newsletter_marketing_version_differs_from_registration_marketing_version`: зеркало существующего `test_newsletter_pdp_version_differs_from_registration_pdp_version`. Проверяет, что `current_consent_text_version(SOURCE_NEWSLETTER, "marketing_email") != current_consent_text_version(SOURCE_REGISTRATION, "marketing_email")` при дословно совпадающих текстах. Docstring — на русском, с причиной: совпадение версий роняет загрузку реестра.
  - [x] 6.9 Тесты, которые обязаны пройти **без правок** (проверить, не ослаблять): `test_api_schema.py::test_subscribe_example_uses_current_versions` (ловит незаменённый литерал в `views.py`), `test_consent_texts.py::test_version_digest_is_32_hex` (новые метки с суффиксом формулу не ломают: хеш по-прежнему после последнего дефиса), `test_registry_file_declares_every_version_in_known_versions`, `test_only_unbound_surface_is_historical_newsletter_checkbox`, `test_historical_versions_still_resolve_to_their_text`, интеграционные `tests/integration/test_auth_registration_consent.py` и `test_common_subscribe_api.py` (они берут версию через `current_consent_text_version`, литералов действующих версий не содержат).

- [x] **Task 7 — реестр решений 41.16 и deferred-work** (AC4)
  - [x] 7.1 `_bmad-output/implementation-artifacts/Story/41-16-editorial-audit-decision-register.md`, строка E03 — исправить колонку «Контекст / основание»: видимого текста «privacy» нет **неверно**; в тексте политики (ответ прод-API) виден адрес `https://optisport.ru/privacy-policy`. Решение «оставить» сохранить, формулировку решения переписать на «оставить: видимый URL политики в тексте CMS, адрес не переводится». Статус дополнить ссылкой на стори 41.20 и дату.
  - [x] 7.2 Добавить строку **E20 `Edition`** в таблицу реестра: URL из отчёта `?category=edinoborstva`; решение «оставить» (Alex, 17.09.2026); контекст — официальные линейки BoyBo «First Edition» и «Black Edition», 24 товара по данным прода 17.09.2026 (19 First Edition + 5 Black Edition), источник — данные 1С; исполнитель «—»; статус «Закрыто решением Alex 17.09.2026, контекст установлен стори 41.20».
  - [x] 7.3 Добавить строку **E21 `example`** : URL `/home`, `/register`, `/b2b-register`, `/password-reset`, `/electric`; решение «удалить плейсхолдер» (Alex, 17.09.2026); контекст — пять плейсхолдеров публичных форм, из них `name@example.ru` внесён самой стори 41.16 (регресс E10); исполнитель DEV; статус — выполнено стори 41.20 со ссылкой на коммит и доказательства AC3/AC5.
  - [x] 7.4 Обновить абзац-итог под таблицей и раздел «Итог реестра (AC4)»: 21 основной ID вместо 19; перечислить E20 как «оставить», E21 как выполненную замену. **Существующие 19 записей и их решения не переписывать.**
  - [x] 7.5 `_bmad-output/implementation-artifacts/deferred-work.md`, раздел «Deferred from: стори 41.4 — торговая информация при оплате (2026-09-05)» — запись о плейсхолдере `example@email.com` пометить закрытой стори 41.20 с датой. Указать, что решение владельца — **удалить** плейсхолдер, а не заменить на `pochta@mail.ru`, как предполагала запись: замена оставляла латиницу. Текст записи сохранить как историю.
  - [x] 7.6 `_bmad-output/planning-artifacts/epic-41-site-audit.md` не править: FR-41-36 и текст Story 41.20 уже внесены correct-course 17.09.2026.

- [x] **Task 8 — проверки и приёмка** (все AC)
  - [x] 8.1 Frontend (в `frontend/`): `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check`. Ориентир полного прогона после 41.19 — 190 файлов, 3303 passed, 16 skipped (ориентир, не требование).
  - [x] 8.2 Backend (из `docker/`): `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/common/tests/test_consent_texts.py apps/common/tests/test_api_schema.py apps/common/tests/test_user_consent.py tests/integration/test_auth_registration_consent.py tests/integration/test_common_subscribe_api.py`. `--env-file` не передавать. Параллельно с этим прогоном линтеры не гонять.
  - [x] 8.3 `check_openapi_sync` по рецепту 5.2 — OK. Миграций нет: `consent_texts.json` — данные, не модель. Для страховки `makemigrations --check` → «No changes detected».
  - [x] 8.4 Локально: `docker compose --env-file .env -f docker/docker-compose.yml restart frontend backend` (зависимости и `next.config.ts` не менялись — полный rebuild не нужен; backend обязателен из-за `lru_cache` реестра), затем при работе через nginx на :80 — `restart nginx`.
  - [x] 8.5 Сквозная проверка подписки на dev-стенде: отправить форму `/home` с обеими галочками → 200, в БД две записи `UserConsent` с новыми версиями (`pdp_contract` — прежняя версия ПДн, `marketing_email` — новая версия подписки). Затем отправить запрос с прежней версией `2026-09-12-1a97b44f2bc0b52e69d15d705be59c0c` → `400` с `error: consent_text_outdated`. Так проверяются оба направления AC2.
  - [x] 8.6 NFR-41-08 на dev-стенде: чистый контекст без cookie (приватное окно или headless Chromium проекта, как в 41.19) — `/home`, `/electric`, `/register`, `/b2b-register`, `/password-reset`; новые подписи чекбоксов видны, у полей почты плейсхолдера нет, подпись «Электронная почта» на месте. Серверный HTML через `curl` формы **не показывает** (они клиентские) — проверять браузером и чанками (8.7).
  - [x] 8.7 Проверка по клиентским чанкам (работает и локально, и на проде; приём стори 41.3 «старая формулировка исчезла из чанков»):
    ```bash
    for page in home electric register b2b-register password-reset; do
      curl -s "https://optisport.ru/$page" -o /tmp/pg.html
      grep -o '/_next/static/chunks/[^"]*\.js' /tmp/pg.html | sort -u | while read c; do
        body=$(curl -s "https://optisport.ru$c")
        echo "$body" | grep -q "example" && echo "$page $c: example"
        echo "$body" | grep -q "согласен(на) получать" && echo "$page $c: старый текст"
      done
    done
    ```
    Ожидание после выката — пусто по обеим строкам.
  - [x] 8.8 `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только ожидаемые символы: пять компонентов форм, `CONSENT_TEXT_VERSIONS`, `subscribe` (только литерал примера). Символы загрузчика реестра появиться не должны — `consent_texts.py` не менялся.
  - [x] 8.9 Dev Agent Record, File List; `sprint-status.yaml` → `review`.
  - [x] 8.10 **Внешний шаг (после мёрджа и ручного выката по SSH):** `up -d --build frontend` (текст зашит в бандл — restart недостаточен), `restart backend celery celery-beat`, затем обязательный `restart nginx`. Приёмка AC5: шаги 8.6 и 8.7 против `https://optisport.ru`; снимок положить в стори. Повторный прогон сканера — шаг владельца после 41.17–41.20.

### Review Findings

- [x] [Review][Patch] Запись E21 не ссылается на неизменяемый commit и преждевременно выдаёт локальную chunk-проверку за прод-доказательство AC5 [_bmad-output/implementation-artifacts/Story/41-16-editorial-audit-decision-register.md:174]
- [x] [Review][Patch] Страж AC3 проверяет доступное имя, но не видимость подписи «Электронная почта» [frontend/src/__tests__/public-forms-no-example-placeholders.test.tsx:79]
- [x] [Review][Patch] Нет интеграционных API-тестов, что непосредственно предыдущие версии `2026-09-12-*` отклоняются подпиской и регистрацией [backend/tests/integration/test_common_subscribe_api.py:465; backend/tests/integration/test_auth_registration_consent.py:386]

#### Rejected

- [Rejected][low] Команда 4.8 с `grep 'placeholder'` не может вернуть пусто из-за разрешённого Tailwind-класса; это дефект формулировки Story, не кода.
- [Rejected][low] AC5 буквально требует текст чекбокса на пяти страницах, хотя `/password-reset` его не имеет; Completion Notes уже дают однозначное толкование, а fix требует правки Story.
- [Rejected][medium] Родительская Task 8 отмечена выполненной при открытом 8.10 и частичном AC5; finding реален, но исправление редактирует саму Story under review.
- [Rejected][low] Шаг 8.7 показан с прод-URL, но отмечен по локальному эквиваленту; расхождение только в тексте Story.
- [Rejected][maybe-false] Критерий нуля `example` в chunk-файлах может захватить vendor-код; фактический прод-набор chunk-файлов пока не проверен, а fix меняет AC5.
- [Rejected][false] Выбор `input[type="email"]` не проверяет неверное поле в текущем diff: в каждой из пяти форм только одно email-поле.
- [Rejected][low] Фраза о соответствии 152-ФЗ/38-ФЗ шире факта внедрения D5, но её исправление меняет Story, а не implementation.
- [Rejected][medium] Порядок выката допускает окно `consent_text_outdated` между новым frontend и неперезапущенным backend; finding реален, но fix изменяет deployment-инструкцию Story under review.
- [Rejected][low] Completion Notes указывают девять GitNexus-символов, но перечисляют только четыре формы и константу; это дефект отчёта Story, а не кода.
- [Rejected][false] Фраза `deferred-work.md` о четырёх других формах верно описывает последствие точечной замены только в `PasswordResetRequestForm`.
- [Rejected][low] File List называет файл Story 41.20 `UPDATE`, хотя diff создаёт его; это мелкая ошибка самой Story.
- [Rejected][low] Для E20 нет отдельного снимка prod-ответа, но AC4 требует контекст и решение владельца, которые зафиксированы; добавление артефакта не оправдано.
- [Rejected][medium] Acceptance Auditor дублировал незакрытую Task 8/AC5; вердикт тот же: факт реален, но fix редактирует Story under review.
- [Rejected][false] Полный `npm run format:check` во время review завершился успешно: все файлы соответствуют Prettier.

#### Повторное ревью 18.09.2026

- [x] [Review][Patch] Непосредственно предыдущие версии рассылки `2026-09-12-*` не закреплены в тесте восстановления точного исторического текста [backend/apps/common/tests/test_consent_texts.py:141]
- [x] [Review][Patch] Доказательство E21 неточно утверждает, что grep по всему `frontend/src` пуст, хотя фактическая команда исключает тесты, моки и `@example` [_bmad-output/implementation-artifacts/Story/41-16-editorial-audit-decision-register.md:174]

##### Rejected

- [Rejected][medium] Родительская Task 8 отмечена выполненной при открытом шаге 8.10; факт уже явно отражён в Story, а предлагаемое исправление редактирует саму спецификацию under review.
- [Rejected][low] AC5 буквально распространяет подпись чекбокса на `/password-reset`; Completion Notes уже однозначно ограничивают чекбокс четырьмя формами, а fix меняет Story.
- [Rejected][medium] Последовательный deploy создаёт краткое окно несовместимости версий согласия; исправление требует выбрать и записать иную стратегию выката в Story, поэтому не является code patch этого review.
- [Rejected][low] Шаг 8.7 назван локальным и production, но содержит только production URL; это дефект инструкции Story, не реализации.
- [Rejected][medium] `curl -s` и пустой список чанков допускают ложное зелёное доказательство; исправление относится к acceptance-команде в Story under review.
- [Rejected][low] Сканирование shared/vendor chunks может давать нерелевантные совпадения `example`; текущий вред ограничен шумом, а исправление усложняет Story-команду.
- [Rejected][false] Ручной список `PUBLIC_FORMS` полностью покрывает утверждённый AC3 набор из пяти форм; будущие формы не входят в scope этой Story.
- [Rejected][false] В каждой из пяти проверяемых форм сейчас ровно одно поле `input[type="email"]`, поэтому выбор первого поля не пропускает текущий дефект.
- [Rejected][false] Ни одно текущее email-поле не использует несколько ID в `aria-labelledby`; описанный ложный отказ на рассматриваемой разметке недостижим.
- [Rejected][false] Равенство текущих маркетинговых текстов уже косвенно закреплено кросс-граничным registry-тестом и точными ожиданиями D5 во всех четырёх component-тестах.
- [Rejected][medium] Edge Case Hunter продублировал окно несовместимости при deploy; вердикт тот же: реальный риск требует правки стратегии в Story, а не однозначного code patch.
- [Rejected][false] AC5 не выдан за завершённый: Story имеет статус `review`, шаг 8.10 открыт, а Completion Notes прямо отмечают частичное закрытие.
- [Rejected][low] Acceptance Auditor продублировал неоднозначность AC5 для `/password-reset`; толкование уже зафиксировано в Completion Notes, а fix меняет Story.

## Dev Notes

### Текущее состояние (код `43ea1539`, прод 17.09.2026)

**Реестр текстов согласий — единый источник формулировок.**
- `backend/apps/common/consent_texts.json` — пять поверхностей, шесть версий в `known_versions`, шесть привязок `<источник>.<тип согласия>`.
- `backend/apps/common/consent_texts.py` — загрузчик без зависимости от Django: считает версию как `<метка>-<32 hex sha256 текста>`, валидирует нормализацию текста, длину версии (≤ 64), **отклоняет совпадение версий двух ревизий** и требует точного равенства набора ревизий разделу `known_versions`. `load_registry` обёрнут `lru_cache`.
- `frontend/src/constants/consentTexts.ts` — `CONSENT_TEXT_VERSIONS`: четыре версии, зашитые в бандл. Версия уезжает в запрос; сервер сверяет её с действующей и отклоняет устаревшую кодом `consent_text_outdated`. Открытая до выката вкладка получит отказ с предложением обновить страницу — это заложенное поведение, а не дефект.
- `frontend/src/__tests__/consent-texts-registry.test.tsx` — кросс-граничный страж: читает тот же JSON с диска, **пересчитывает** версию из текста (не берёт готовую строку) и сверяет доступные имена чекбоксов четырёх форм с текущими ревизиями. Пропуск при отсутствии файла в нём запрещён осознанно.

**Формулировки до правки.**

| Поверхность | Формы | Текст |
|---|---|---|
| `newsletter_marketing_checkbox` | `SubscribeForm`, `ElectricSubscribeForm` | Я согласен(на) получать информационные и рекламные рассылки от OPTISPORT по электронной почте |
| `registration_marketing_checkbox` | `RegisterForm`, `B2BRegisterForm` | Я согласен(на) получать рекламные и информационные рассылки от OPTISPORT по электронной почте |

Отличие двух текстов — только порядок слов «информационные/рекламные». После правки они совпадут дословно, различать ревизии будет метка.

**Обязательность чекбоксов — не менять.**
- Подписка: оба чекбокса обязательны. ПДн — через `required` в `register` (читает DOM, поэтому зарегистрирован **первым**: `handleSubmit` успевает выставить `isSubmitting` → `disabled`, и `required` следующего поля посчитал бы отключённый чекбокс пустым). Рассылка — через `validate: value => value === true`, ровно по этой причине. Оба несут `aria-required="true"`, а не нативный `required`: тот перехватил бы отправку до `react-hook-form`. Кнопка блокируется только по ПДн (`disabled={isSubmitting || !pdpConsent}`) — решение Alex 2026-09-12.
- Регистрация: `register('marketing_consent')` без правил, inline error-state намеренно не назначается.

**Плейсхолдеры `example` — ровно пять, все проверены на `43ea1539`:**

| Файл:строка | Значение | Видимая подпись поля |
|---|---|---|
| `SubscribeForm.tsx:219` | `name@example.ru` | `label="Электронная почта"` (`Input`) |
| `ElectricSubscribeForm.tsx:328` | `name@example.ru` | `<label>Электронная почта</label>` |
| `RegisterForm.tsx:307` | `user@example.com` | `label="Электронная почта"` |
| `B2BRegisterForm.tsx:374` | `company@example.com` | `label="Электронная почта"` |
| `PasswordResetRequestForm.tsx:77` | `example@email.com` | `label="Электронная почта"` |

`label` у компонента `Input` (`frontend/src/components/ui/Input/Input.tsx:15`) — **обязательный** prop, `placeholder` идёт через `...props` и необязателен: удаление безопасно, подпись не пострадает.

**Снимок прода до правки (17.09.2026, `curl` без cookie).** Серверный HTML форм не содержит — они клиентские; строки живут в чанках:

| Страница | Чанк | Найдено |
|---|---|---|
| `/home` | `app/(blue)/home/page-d1d30da1d0a619d8.js` | `name@example.ru`, «Я согласен(на) получать информационные…» |
| `/electric` | `app/(electric)/electric/page-020a145211f854a4.js` | `name@example.ru`, тот же текст |
| `/register` | `app/(blue)/(auth)/register/page-a860616b4e63445d.js` | `user@example.com`, «Я согласен(на) получать рекламные…» |
| `/b2b-register` | `app/(blue)/(auth)/b2b-register/page-ed75fa99cc73a8f2.js` | `company@example.com`, тот же текст |
| `/password-reset` | `app/(blue)/(auth)/password-reset/page-10fda356633351cf.js` | `example@email.com` |

Все пять страниц отдают 200. Хеши чанков после пересборки изменятся — сверять по содержимому, не по имени.

**Контекст E20 `Edition` (прод-API 17.09.2026).** `GET /api/v1/products/?search=Edition` — 24 товара, все бренда BoyBo: 19 «First Edition», 5 «Black Edition». По категориям: 15 в подкатегориях «СПОРТ > Единоборства» (совпадает с URL отчёта `?category=edinoborstva`), 1 в «СПОРТ > Фитнес и атлетика > Тяжелая атлетика», 6 в «Номенклатура к удалению / Выбыло из ассортимента», 2 в категории без имени (`72fb61ec-…`). Источник названий — данные 1С; сайт номенклатуру не редактирует. Оговорка: query-параметр `category` на публичном API **не фильтрует** (`?category=nonexistent-xyz` даёт тот же `count`), поэтому распределение по категориям взято из поля категории каждого товара, а не из фильтра.

### Почему двум ревизиям нужны разные метки

Тексты D5 дословно совпадают, значит совпадут и хеши. Версия = `<метка>-<хеш>`, и `ConsentTextRegistry._ingest_surface` роняет загрузку при повторе версии («версия встречается дважды — дубль ревизии»). Прецедент уже в реестре: `newsletter_pdp_checkbox` и `registration_pdp_checkbox` несут дословно одинаковый текст, а версии `2026-09-12-de992f50…` и `2026-09-09-de992f50…` различает только метка — это зафиксировано тестом `test_newsletter_pdp_version_differs_from_registration_pdp_version`. Отсюда суффиксы `-newsletter` / `-registration`: они читаются человеком в админке (`UserConsent.consent_text_version` — в `list_display` и `list_filter`) и не ломают ни формулу, ни ограничение длины 64, ни тест «хеш после последнего дефиса — 32 hex».

**Отклонённая альтернатива:** слить обе привязки `*.marketing_email` на одну поверхность. Отклонено — страж фронта требует ровно пять поверхностей и шесть привязок, а комментарий `test_consent_texts.py` прямо объясняет, почему поверхности раздельны: формы живут независимо, и правка текста одной не должна ронять другую.

### Что ломается, если не сделать

- `RegisterForm.test.tsx:122` проверяет `toHaveAccessibleName(/^Я согласен\(на\) получать/)` — с новым текстом упадёт. Правка предписана Task 6.3, ослаблять регулярку до «любое начало» нельзя: она страхует дословность.
- `test_api_schema.py::test_subscribe_example_uses_current_versions` упадёт, если не обновить литерал в `views.py:339`.
- `consent-texts-registry.test.tsx` упадёт, если текст в форме и текст ревизии разойдутся хотя бы на пробел.
- Если обновить реестр, но не `CONSENT_TEXT_VERSIONS` (или наоборот), страж поймает это до прода; в проде такое расхождение означало бы отказ **всех** форм или запись согласия на неувиденную формулировку.
- Если внести ревизию, но не строку в `known_versions` — не загрузится весь реестр, то есть упадут и подписка, и регистрация. Сообщение загрузчика называет готовую строку для вставки.

### Технические ограничения

- Backend меняется только данными (`consent_texts.json`) и одним литералом примера (`views.py`). Модели, сериализаторы, миграции, nginx — не трогать. `consent_texts.py` не трогать.
- NFR-41-02 задействован в минимальном объёме: меняется значение примера в `openapi.yaml`, типы фронта не должны измениться.
- Комментарии и docstrings нового кода — на русском (NFR-41-03).
- Правки `frontend/src/` локально применяются `restart frontend`; зависимости и `next.config.ts` не меняются, поэтому `--build` локально не нужен. **На проде — полный `up -d --build frontend`**: текст зашит в бандл, а частичное копирование `.next/` даёт `Failed to find Server Action`.
- После правки `consent_texts.json` живой backend обязан быть перезапущен: `load_registry` кэширован `lru_cache`.
- Прогон backend-тестов — только в Docker с PostgreSQL, один pytest на compose-проект (параллельные прогоны дают лавину падений на `TRUNCATE`).
- Не трогать: `middleware.ts`, `robots.ts`, `app/layout.tsx`, каталоги `(auth)/register`/`(auth)/b2b-register` (`layout.tsx` — стори 41.19), `Header.tsx` и каталог (41.17), ветки auth (41.18), `utils/seo.ts`/`buildMetadata` (HIGH).
- Тема electric на проде живой витриной не является (`ACTIVE_THEME=coming_soon`), но `/electric` отвечает 200 и входит в приёмку.

### Архитектура и версии

Next.js 15.5.18, React 19.1, TypeScript 5.8, Vitest 4.x (`npm run test`), react-hook-form 7.62, Playwright 1.57; backend — Django + DRF + drf-spectacular. Новые зависимости не нужны. Формы — Client Components (`'use client'`), доступное имя чекбокса задаётся через `aria-labelledby`, а не «все `<label for>`»: первый такой label в компоненте `Checkbox` — пустой квадрат, и при `aria-describedby` axe (`label-title-only`) счёл бы чекбокс подписанным только описанием.

### GitNexus (create-story, индекс `43ea153`, HEAD `43ea1539`, 17.09.2026)

`status` — `up-to-date`, индексированный и текущий коммит совпадают.

| Символ | Risk | Прямых вызывающих | Примечание |
|---|---|---|---|
| `SubscribeForm` | LOW | 1 (`SubscribeNewsSection`) | процесс `BlueHomePage`, 2 модуля |
| `ElectricSubscribeForm` | LOW | 1 | процесс `ElectricHomePage` |
| `RegisterForm` | LOW | 1 | процесс `RegisterPage` |
| `B2BRegisterForm` | LOW | 1 | процесс `B2BRegisterPage` |
| `PasswordResetRequestForm` | LOW | 1 | процесс `PasswordResetPage` |
| `load_registry` | **HIGH** | 2 (`current_consent_text_version`, `resolve_consent_text`) | 9 затронутых, процессы `subscribe` и `post` (регистрация), 4 модуля. **Функция не меняется** — меняются данные, которые она читает. Риск реализуется только при неверном JSON: реестр не загрузится, и откажут оба эндпоинта согласия. Поэтому Task 8.2 и 8.5 обязательны до коммита |
| `current_consent_text_version` | **HIGH** | 3 (`post`, `subscribe`, `is_current_consent_text_version`) | 7 затронутых, те же два процесса. Тоже не меняется |

Имена компонентов в графе **неоднозначны** (`Function:` и `Const:` на одну строку) — `impact` по короткому имени возвращает `status: ambiguous` и `risk: UNKNOWN`, что не означает «0 затронутых». Звать по полному UID.

### Project Structure Notes

- UPDATE `backend/apps/common/consent_texts.json` (две ревизии, два `known_versions`, два `description`)
- UPDATE `backend/apps/common/views.py` (один литерал примера, `:339`)
- UPDATE `frontend/src/constants/consentTexts.ts` (две константы версий)
- UPDATE `frontend/src/components/home/SubscribeForm.tsx` (текст чекбокса, плейсхолдер)
- UPDATE `frontend/src/components/home/ElectricSubscribeForm.tsx` (то же)
- UPDATE `frontend/src/components/auth/RegisterForm.tsx` (то же)
- UPDATE `frontend/src/components/auth/B2BRegisterForm.tsx` (то же)
- UPDATE `frontend/src/components/auth/PasswordResetRequestForm.tsx` (плейсхолдер)
- UPDATE `docs/api/openapi.yaml` (значение примера), `docs/architecture/18-b2b-verification-workflow.md` (значение примера)
- UPDATE тесты: `src/__tests__/consent-texts-registry.test.tsx`, `src/components/home/__tests__/SubscribeForm.test.tsx`, `src/components/home/__tests__/ElectricSubscribeForm.test.tsx`, `src/components/auth/__tests__/RegisterForm.test.tsx`, `src/components/auth/__tests__/B2BRegisterForm.test.tsx`, `src/components/auth/__tests__/PasswordResetRequestForm.test.tsx`, `backend/apps/common/tests/test_consent_texts.py`
- NEW тест: `frontend/src/__tests__/public-forms-no-example-placeholders.test.tsx`
- UPDATE артефакты: `Story/41-16-editorial-audit-decision-register.md`, `deferred-work.md`, `sprint-status.yaml`

**Общие файлы с другими стори.** С 41.17 (каталог, `Header.tsx`) и 41.19 (маршруты, корневой layout, `next.config.ts`) пересечений нет — 41.19 это прямо зафиксировала. 41.18 правит `middleware.ts`, `robots.ts` и ветки auth: файлы этой стори с ней не пересекаются, но обе идут после 41.19, поэтому ветку брать от свежего `origin/develop`. 41.15 (этап 2 отписки) живёт в `apps/common/views.py` — при параллельной работе возможен конфликт в этом файле; правка здесь одна строка примера.

### Previous Story Intelligence (41.19, 41.16, 41.11, 41.9, 41.3)

- **41.19** (последняя закрытая, `dd64c357`): ветку брать от `origin/develop`, а не от локального `develop` — они расходились. Локальный `tsc --noEmit` может падать на устаревшем `.next/types/validator.ts` после прошлой сборки — артефакт, в CI `.next` нет. NFR-41-08 закрывали чистым контекстом headless Chromium проекта вместо приватного окна — приём годится и здесь. `restart frontend` без `restart nginx` даёт 502 на :80.
- **41.16:** полная регенерация `openapi.yaml` подтягивает несвязанный дрейф схемы — отсюда точечная правка примера в Task 5.2. Остаток E08 в Swagger `help_text` оставлен осознанно и записан в реестр — тот же приём применён к `user@example.com` в примере OpenAPI (Task 4.7). В контейнере MSW-хендлеры читают `NEXT_PUBLIC_API_URL` в момент импорта, до `vitest.setup.ts`: при прогоне Vitest внутри контейнера может понадобиться `-e NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`.
- **41.11:** загрузчик отклоняет дубль версии — урок, из которого выросли суффиксы меток. Тогда же чекбокс рассылки подписки стал обязательным через `validate`, а не `required`, и `aria-required` заменил нативный `required`.
- **41.9:** формула версии (32 hex — после того, как перебор нашёл коллизию на 8 hex), `known_versions` как страж односторонней правки истории, требование «страж обязан падать, а не пропускаться».
- **41.3:** доказательство «старая формулировка исчезла из клиентских чанков (0 вхождений)» — приём, лёгший в основу Task 8.7.
- Память проекта: `vi.restoreAllMocks()` не снимает `spyOn` на `localStorage` — восстанавливать явно; тяжёлые прогоны не гонять параллельно; `curl` через Bash, а не `Invoke-WebRequest` (PowerShell здесь 5.1).

### Git Intelligence

`43ea1539` (develop) — merge PR #199, закрытие стори 41.19 после подтверждения AC6 на проде; до него `bb940a61` (PR #197, реализация 41.19) и `28d39c83`. Файлов этой стори последние коммиты не касались: 41.19 работала в маршрутах, `middleware.ts`, `robots.ts` и корневом layout. Конвенция сообщений — `feat(frontend): …`, `test(frontend): …`, `docs(story): …` на русском.

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.20], FR-41-36, NFR-41-01/02/03/06/08
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-16.md#4 (D5), #5.5, #5.7]
- [Source: _bmad-output/implementation-artifacts/tasks/intent-site-audit-2026-09-16.md] — H1/H2 по согласию, регресс `example`, неверное основание E03, новый элемент `Edition`
- [Source: _bmad-output/implementation-artifacts/Story/41-16-editorial-audit-decision-register.md] — реестр 19 элементов, формат строки, прецеденты «оставить»
- [Source: _bmad-output/implementation-artifacts/Story/41-9-consent-journal-text-version-and-source.md] — формула версии, `known_versions`
- [Source: _bmad-output/implementation-artifacts/Story/41-11-separate-subscribe-consents.md] — раздельные согласия, дубль версии
- [Source: _bmad-output/implementation-artifacts/Story/41-19-public-surface-hygiene-demo-routes-register-meta.md] — грабли стенда, приёмка NFR-41-08, отсутствие пересечений с этой стори
- [Source: _bmad-output/implementation-artifacts/deferred-work.md] — запись о плейсхолдере формы восстановления пароля (стори 41.4)
- [Source: project-context.md#1, #3, #4, #5, #6, #7]
- `backend/apps/common/consent_texts.py` — формула версии, валидация, `lru_cache`; `backend/apps/common/tests/test_consent_texts.py` — существующие стражи

## Решения по вопросам create-story (Alex, 17.09.2026)

1. **E20 `Edition`** — «оставить». Официальное наименование товарных линеек BoyBo из данных 1С; основание совпадает с E12, E14, E17, E19. Правок кода нет.
2. **E21 `example`** — плейсхолдер удалить, не заменять. Замена оставляет латиницу и рискует повторить регресс E10; видимая подпись и `type="email"` делают образец избыточным.
3. **Охват D5** — все четыре формы, включая B2B-регистрацию. Поверхность `registration_marketing_checkbox` не разделяется.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (claude-opus-5), bmad-create-story, 17.09.2026
Claude Opus 5 (claude-opus-5), bmad-dev-story, 17.09.2026

### Debug Log References

- **Хеш текста D5 пересчитан перед правкой реестра:** 97 символов, sha256[:32] = `4e2471b54124acaf12cfed1b8196b684` — совпал с таблицей стори. Версии после правки: `current_consent_text_version('newsletter', 'marketing_email')` = `2026-09-17-newsletter-4e2471b54124acaf12cfed1b8196b684`, `('registration', 'marketing_email')` = `2026-09-17-registration-4e2471b54124acaf12cfed1b8196b684`; привязка `1c_link.marketing_email` разделяет поверхность регистрации и получила ту же версию.
- **Red-фаза нового стража:** плейсхолдер `name@example.ru` временно возвращён в `SubscribeForm` — `public-forms-no-example-placeholders.test.tsx` дал 2 падения из 15 («у поля почты нет плейсхолдера», «разметка не содержит подстроки example»), после отката — 15 passed. Страж действительно ловит регресс, а не проходит вхолостую.
- **503 на первой сквозной проверке подписки — не дефект стори.** `POST /api/v1/subscribe/` с новой версией вернул `consent_persistence_failed`; в логах backend — `ProgrammingError: column common_newsletter.unsubscribe_token does not exist`, то есть локальная dev-БД отставала на миграцию `common.0021_newsletter_unsubscribe_token`. Сверку версии запрос при этом прошёл (иначе был бы 400). После `migrate` — 200. Правок кода не потребовалось.
- **Эндпоинт подписки — `/api/v1/subscribe/`, а не `/api/v1/newsletter/subscribe/`** (`backend/apps/common/urls.py:19`); под `newsletter/` живёт только отписка.
- **`networkidle` на локальном стенде не наступает** (dev-сокет HMR): headless-проверка пяти страниц выполнена с `domcontentloaded` плюс ожидание видимости `input[type="email"]`.
- **`example` в HTML `/home` — из inline-рантайма Next** (комментарий со ссылкой на спецификацию streams `#example-rbs-pull`), не из разметки формы; проверка ведётся по разметке без содержимого `<script>`.
- **Повторное ревью 18.09.2026 — версии литералов подтверждены пересчётом:** `compute_consent_text_version('2026-09-12', <текст newsletter до правки>)` = `2026-09-12-1a97b44f2bc0b52e69d15d705be59c0c`, `compute_consent_text_version('2026-09-12', <текст registration до правки>)` = `2026-09-12-a49604a66adaadfdc221bdc141d8d97d` — оба совпали с `known_versions` и с версиями, отклоняемыми review-тестами предыдущего круга (`test_subscribe_rejects_previous_marketing_text_version`, `test_registration_rejects_previous_marketing_text_version_before_d5`), поэтому тексты для новых параметров взяты из тех же литералов, а не заново.

### Completion Notes List

- 17.09.2026, dev-story (ветка `feature/41-20-newsletter-consent-wording` от `origin/develop` `43ea1539`): реализованы Task 0–8 кроме внешнего шага 8.10.
  - **AC1:** текст D5 внесён в четыре формы; обязательность не тронута — в подписке чекбокс рассылки остался обязательным через `validate` + `aria-required`, в регистрации `register('marketing_consent')` без правил и без inline error-state. Сообщение `MARKETING_CONSENT_REQUIRED` не менялось.
  - **AC2:** две ревизии дописаны в конец списков поверхностей, прежние шесть строк `known_versions` не тронуты, добавлены две новые. Загрузка реестра проверена вживую; на dev-стенде подписка с новой версией → 200 и две записи `UserConsent` (`pdp_contract` — прежняя версия ПДн `2026-09-12-de992f50…`, `marketing_email` — новая `2026-09-17-newsletter-…`), с прежней версией рассылки → 400 `consent_text_outdated`. `check_openapi_sync` — «Контракт синхронен с кодом»; `npm run generate:types` не изменил `api.generated.ts`; `makemigrations --check` — «No changes detected».
  - **AC3:** пять плейсхолдеров удалены; grep по `frontend/src` (без тестов, моков и `@example`) пуст; в разметке всех пяти форм нет подстроки `example`, у полей почты нет атрибута `placeholder`, подпись «Электронная почта» и доступное имя по ней сохранены. Axe-проверки форм подписки входят в общий прогон Vitest и остались зелёными.
  - **AC4:** основание E03 исправлено (видимый URL политики в тексте CMS, решение «оставить» сохранено), добавлены E20 `Edition` («оставить») и E21 `example` («удалить плейсхолдер», выполнено); итог реестра пересчитан — 21 основной ID. Запись `deferred-work.md` о плейсхолдере формы восстановления пароля закрыта с явным указанием, что решение — удалить, а не заменить на `pochta@mail.ru`.
  - **AC5 — закрыт полностью 18.09.2026, после выката (шаг 8.10, Alex).** Прод-приёмка `https://optisport.ru`: шаг 8.6 (браузер, чистый контекст без cookie) выполнил владелец — на пяти страницах новые подписи чекбоксов видны, у полей почты `placeholder` отсутствует, подпись «Электронная почта» на месте; подтверждено визуально. Шаг 8.7 (клиентские чанки, `curl`) выполнен dev-агентом по рецепту стори против `https://optisport.ru/{home,electric,register,b2b-register,password-reset}`: во всех пяти страницах 0 вхождений прежней формулировки «Я согласен(на) получать»; вхождений `example` в собственном коде форм — 0. Общий для всех пяти страниц vendor-чанк `3688-912aa751a9ddbcb4.js` содержит одно вхождение слова `Example` — это `console.warn` стороннего state-менеджмент-пакета (сигнатура `getState/setState/subscribe`, синтаксис `[DEPRECATED] The 'destroy' method...`), не относится к формам стори и не является плейсхолдером; предвиденное ревью замечание «критерий нуля `example` в chunk-файлах может захватить vendor-код» (Rejected, maybe-false) подтвердилось именно так — вхождение чужое, а не регресс E21. AC5 буквально требует «0 вхождений `example`» без оговорки про vendor-код; фактический результат — 0 в коде форм и 1 в независимом от стори библиотечном коде, что и зафиксировано здесь явно, а не скрыто за формулировкой «пусто».
- **Осознанные исключения (Task 4.7), зафиксированы как прецедент E08 стори 41.16:** `user@example.com` в примере OpenAPI (`backend/apps/common/views.py:336,353`) и фикстуры `*@example.com` в `__tests__`/`e2e` не трогались — это не видимый текст публичной формы. Тестовые фикстуры `user@example.com` внутри `PasswordResetRequestForm.test.tsx` тоже сохранены.
- **Не менялись, как предписано:** `consent_texts.py` (загрузчик, формула версии, пределы), состав `surfaces` и `bindings`, поверхность `newsletter_checkbox`, тексты ПДн-чекбоксов, константы `newsletterPdp`/`registrationPdp`, Tailwind-класс `placeholder:text-…` в `ElectricSubscribeForm`, русскоязычные и нейтральные плейсхолдеры остальных полей, story-файлы 35.2/41.3/41.9/41.11 и `tasks/intent-site-audit-*.md`, `epic-41-site-audit.md`.
- **Прогоны.** Фронт: `npm test` — 191 файл, 3318 passed, 16 skipped (ориентир после 41.19 — 190/3303/16; прирост даёт новый страж на 15 тестов); `npm run lint`, `npx tsc --noEmit`, `prettier --check` по затронутым файлам — чисто. Backend в Docker/PostgreSQL: 218 passed за 4 м 58 с (`test_consent_texts.py`, `test_api_schema.py`, `test_user_consent.py`, `tests/integration/test_auth_registration_consent.py`, `test_common_subscribe_api.py`); `black --check` и `flake8` по затронутым файлам — чисто.
- **GitNexus.** Индекс `up-to-date` (`43ea153`). `impact --direction upstream` по полным UID: пять форм — LOW, по одному прямому вызывающему; `CONSENT_TEXT_VERSIONS` — LOW; `load_registry` — **HIGH** (2 прямых, 9 затронутых, процессы `subscribe` и регистрация), но сама функция не менялась — менялись только читаемые ею данные, поэтому риск закрыт прогонами 8.2 и 8.5. `detect-changes --scope all` — 9 символов: четыре формы и `CONSENT_TEXT_VERSIONS`; символов загрузчика реестра нет, как и требовала проверка 8.8.
- **17.09.2026, code-review (3 findings `[Review][Patch]`) — закрыты:**
  - ✅ Resolved review finding [Patch]: запись E21 в реестре 41.16 переведена со ссылки на ветку на неизменяемый коммит `128bc989`; формулировка доказательства разделена — AC3 и локальная приёмка закрыты по коду, прод-приёмка AC5 явно оставлена за шагом 8.10 (раньше локальная chunk-проверка подавалась как прод-доказательство).
  - ✅ Resolved review finding [Patch]: страж AC3 `public-forms-no-example-placeholders.test.tsx` теперь проверяет не только доступное имя, но и **видимость** подписи: находит сам элемент `<label>` (по `aria-labelledby` или `for`) и требует `toBeVisible()` и текст «Электронная почта». Red-фаза подтверждена — временный `style={{display:'none'}}` у `<label>` в `ui/Input` уронил 4 из 15 тестов, после отката 15 passed; `Input.tsx` в дифф не входит.
  - ✅ Resolved review finding [Patch]: добавлены два интеграционных API-теста на отклонение **непосредственно предыдущих** версий: `test_subscribe_rejects_previous_marketing_text_version` (`2026-09-12-1a97b44f…`, подписка) и `test_registration_rejects_previous_marketing_text_version_before_d5` (`2026-09-12-a49604a6…`, регистрация). Оба ждут 400 `consent_text_outdated`, отсутствие `Newsletter`/`User` и пустой журнал. Литералы намеренные — версии неизменяемы и остаются в `known_versions`; приём взят у существующего `test_registration_rejects_previous_marketing_text_version_without_channel`.
- **18.09.2026, повторное ревью (2 findings `[Review][Patch]`) — закрыты:**
  - ✅ Resolved review finding [Patch]: `test_historical_versions_still_resolve_to_their_text` (`backend/apps/common/tests/test_consent_texts.py:141`) дополнен двумя параметрами — `2026-09-12-1a97b44f2bc0b52e69d15d705be59c0c` разрешается в прежний текст рассылки подписки, `2026-09-12-a49604a66adaadfdc221bdc141d8d97d` — в прежний текст рассылки регистрации. До правки тест 41.9 проверял только *различие* версий этих ревизий (`test_newsletter_marketing_version_differs_from_registration_marketing_version`), а не дословный текст, на который ссылаются записи журнала прода, сделанные до выката 41.20. Прогон `pytest apps/common/tests/test_consent_texts.py` — 41 passed (было 39); полный набор пяти файлов (Task 8.2) — 222 passed; `black --check`/`flake8` по файлу — чисто.
  - ✅ Resolved review finding [Patch]: запись E21 в реестре 41-16 (`_bmad-output/implementation-artifacts/Story/41-16-editorial-audit-decision-register.md:174`) переформулирована — вместо «grep по `frontend/src` пуст» указано, что grep пуст **без тестов, моков, сгенерированных типов API и JSDoc-тегов `@example`**, а `user@example.com` в примере OpenAPI назван осознанным исключением Task 4.7. Формулировка теперь совпадает с фактической командой 4.8, а не с её упрощённым пересказом.
  - `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` после обеих правок — «No changes detected» (изменения только в тестовом файле и двух Markdown-документах, символов кода не затронуто).
- **18.09.2026, шаг 8.10 закрыт владельцем (Alex):** выкат на прод по SSH выполнен (`up -d --build frontend`, `restart backend celery celery-beat`, `restart nginx`). Прод-приёмка AC5: шаг 8.6 подтверждён владельцем визуально в браузере; шаг 8.7 выполнен dev-агентом через `curl` против `https://optisport.ru` — результат и оговорка про vendor-чанк описаны в Completion Notes → AC5. Все Tasks/Subtasks стори закрыты, внешних шагов больше нет.
- 17.09.2026: create-story — анализ эпика, предложения 16.09 (D5), триажа 16.09, реестра 41.16, стори 41.19/41.16/41.11/41.9/41.3; код на `43ea1539`, GitNexus `up-to-date`. Установлено сверх текста эпика: (а) D5 затрагивает **четыре** формы — `B2BRegisterForm` делит поверхность `registration_marketing_checkbox` с `RegisterForm`; (б) дословно одинаковый текст двух поверхностей потребовал бы одинаковых версий, а загрузчик отклоняет дубль — отсюда метки с суффиксами `-newsletter`/`-registration`; (в) `RegisterForm.test.tsx:122` и `test_api_schema.py::test_subscribe_example_uses_current_versions` упадут без явных правок; (г) `views.py:339`, `docs/api/openapi.yaml:105` и `docs/architecture/18-b2b-verification-workflow.md:142` содержат литералы заменяемых версий; (д) `deferred-work.md` несёт незакрытую запись про `example@email.com`, которую стори закрывает — но решением «удалить», а не предполагавшейся заменой; (е) серверный HTML форм не содержит, приёмка идёт браузером и по клиентским чанкам. Контекст E20 установлен по прод-API (24 товара BoyBo). Решения владельца по E20, E21 и охвату D5 получены и внесены. Ultimate context engine analysis completed - comprehensive developer guide created. Код не менялся.

### File List

**Backend**
- `backend/apps/common/consent_texts.json` — UPDATE: две новые ревизии (`2026-09-17-newsletter`, `2026-09-17-registration`), две строки в `known_versions`, дополнены `description` обеих поверхностей.
- `backend/apps/common/views.py` — UPDATE: литерал `marketing_consent_text_version` в примере `successful_subscription_request`.
- `backend/apps/common/tests/test_consent_texts.py` — UPDATE: новый тест `test_newsletter_marketing_version_differs_from_registration_marketing_version`; повторное ревью 18.09.2026 — два параметра в `test_historical_versions_still_resolve_to_their_text` для версий `2026-09-12-1a97b44f…`/`2026-09-12-a49604a6…`.

**Frontend**
- `frontend/src/constants/consentTexts.ts` — UPDATE: `CONSENT_TEXT_VERSIONS.newsletterMarketing` и `.registrationMarketing`, JSDoc обеих констант.
- `frontend/src/components/home/SubscribeForm.tsx` — UPDATE: текст чекбокса рассылки, удалён `placeholder`.
- `frontend/src/components/home/ElectricSubscribeForm.tsx` — UPDATE: то же.
- `frontend/src/components/auth/RegisterForm.tsx` — UPDATE: то же.
- `frontend/src/components/auth/B2BRegisterForm.tsx` — UPDATE: то же.
- `frontend/src/components/auth/PasswordResetRequestForm.tsx` — UPDATE: удалён `placeholder`.
- `frontend/src/__tests__/public-forms-no-example-placeholders.test.tsx` — NEW: страж AC3 по пяти публичным формам (15 тестов).
- `frontend/src/__tests__/consent-texts-registry.test.tsx` — UPDATE: две проверки (различие версий двух маркетинговых поверхностей; прежние версии рассылки в `known_versions`).
- `frontend/src/components/home/__tests__/SubscribeForm.test.tsx` — UPDATE: `MARKETING_CONSENT_NAME`.
- `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx` — UPDATE: то же.
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` — UPDATE: константа `MARKETING_CONSENT_NAME`, поиск по точному имени, ожидание `/^Я даю согласие на получение/`.
- `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx` — UPDATE: `MARKETING_CONSENT_NAME`.
- `frontend/src/components/auth/__tests__/PasswordResetRequestForm.test.tsx` — UPDATE: тест плейсхолдера переписан в «поле электронной почты не имеет плейсхолдера».

- `backend/tests/integration/test_common_subscribe_api.py` — UPDATE: тест отклонения предыдущей версии рассылки подписки (review-фикс).
- `backend/tests/integration/test_auth_registration_consent.py` — UPDATE: тест отклонения предыдущей версии рассылки регистрации (review-фикс).

**Документация и артефакты**
- `docs/api/openapi.yaml` — UPDATE: значение примера `marketing_consent_text_version`.
- `docs/architecture/18-b2b-verification-workflow.md` — UPDATE: то же в примере запроса регистрации.
- `_bmad-output/implementation-artifacts/Story/41-16-editorial-audit-decision-register.md` — UPDATE: основание E03, строки E20 и E21, пересчитанный итог (21 ID); повторное ревью 18.09.2026 — уточнена формулировка доказательства E21 (grep без тестов/моков/сгенерированных типов/`@example`).
- `_bmad-output/implementation-artifacts/deferred-work.md` — UPDATE: запись о плейсхолдере формы восстановления пароля закрыта стори 41.20.
- `_bmad-output/implementation-artifacts/Story/41-20-newsletter-consent-wording-and-placeholders.md` — UPDATE: чекбоксы задач, Dev Agent Record, File List, Change Log, статус.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — UPDATE: статус стори.

### Change Log

- 17.09.2026 — create-story: стори создана, статус ready-for-dev.
- 17.09.2026 — решения Alex: E20 «оставить», E21 «удалить плейсхолдер», охват D5 — четыре формы.
- 17.09.2026 — dev-story: реализованы AC1–AC4 и локальная часть AC5; две ревизии реестра, новые версии на фронте, текст D5 в четырёх формах, пять плейсхолдеров `example` удалены, реестр решений 41.16 дополнен (21 ID), запись `deferred-work.md` закрыта. Прогоны: фронт 3318 passed / 16 skipped, backend 218 passed в Docker, lint/tsc/prettier/black/flake8 чисто, `check_openapi_sync` OK. Открыт внешний шаг 8.10 — выкат на прод и прод-приёмка AC5. Статус: ready-for-dev → review.
- 17.09.2026 — dev-story после code-review: закрыты 3 finding `[Review][Patch]` — ссылка на неизменяемый коммит и разделение доказательств в записи E21, проверка видимости подписи в страже AC3, два интеграционных теста на отклонение версий `2026-09-12-*`. Статус: in-progress → review.
- 18.09.2026 — dev-story после повторного ревью: закрыты 2 finding `[Review][Patch]` — тест на дословный исторический текст непосредственно предыдущих версий рассылки (`2026-09-12-1a97b44f…`, `2026-09-12-a49604a6…`) и уточнение формулировки доказательства E21 (grep исключает тесты/моки/сгенерированные типы/`@example`, а не пуст по всему `frontend/src`). Прогоны: `test_consent_texts.py` — 41 passed; пять файлов Task 8.2 — 222 passed; `black`/`flake8` по изменённому файлу — чисто; `detect-changes --scope all` — без изменений символов кода. Статус: in-progress → review.
- 18.09.2026 — шаг 8.10 закрыт владельцем: ручной выкат на прод по SSH выполнен, шаг 8.6 подтверждён визуально владельцем, шаг 8.7 подтверждён dev-агентом через `curl` против `https://optisport.ru` (0 вхождений старой формулировки на всех пяти страницах; одно вхождение `example` в общем vendor-чанке — сторонний код state-менеджмент-библиотеки, не связано со стори). AC5 закрыт полностью. Все Tasks/Subtasks стори выполнены.
