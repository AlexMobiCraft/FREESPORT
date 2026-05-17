# Story: Security — Унификация HTTP-статуса `/subscribe/` (201 → 200)

**Story ID:** security-subscribe-status-unification
**Status:** review
**Priority:** High (security follow-up; закрывает остаточный вектор email enumeration)
**Source issues:** Code review `security-email-enumeration-hardening` (2026-05-17, Blind Hunter HIGH) — раздел «Deferred» в `_bmad-output/implementation-artifacts/deferred-work.md`
**Зависит от:** `security-email-enumeration-hardening` (должна быть merged в main/develop перед началом этой story)
**Предшественник:** `security-email-enumeration-hardening` (закрыл 409→200 и 404→200)

---

## Prerequisites (обязательно перед началом)

⚠️ **Эта story может начаться ТОЛЬКО ПОСЛЕ того, как `security-email-enumeration-hardening` будет merged в develop/main.**

Обоснование: обе story модифицируют `backend/tests/integration/test_common_subscribe_api.py`:
- `hardening` заменила `HTTP_409_CONFLICT` → `HTTP_200_OK` (уже выполнено)
- `unification` должна заменить `HTTP_201_CREATED` → `HTTP_200_OK` (этой story)

Если выполнять их в обратном порядке, возникнут merge-конфликты и логическая путаница в тестах.

**Текущий статус hardening:** в review (commit `e76b7e6c`), готова к merge.

---

## Story

Как **команда безопасности FREESPORT**,
я хочу **унифицировать HTTP-статус `/subscribe/` на `200 OK` для новой подписки и для already_subscribed**,
чтобы **анонимный атакующий не мог различать наличие email в базе подписчиков по различию статус-кодов `201` vs `200`**.

---

## Контекст и решения

### Остаточный вектор (после story `security-email-enumeration-hardening`)

Предшествующая story закрыла два вектора (`409→200` на `/subscribe/`, `404→200` на `/unsubscribe/`), но на `/subscribe/` **сохранила** различие:
- новая подписка → `201 Created`
- already_subscribed → `200 OK`

AC-1 предшественника явно принял это («оба success»), но обоснование security-некорректно: для атакующего важна **различимость** ответа, а `201 ≠ 200` различимы идеально. Исходный вектор DN8-1 закрыт лишь наполовину — оракул enumeration сменил коды (было `201` vs `409`, стало `201` vs `200`), но не исчез.

### Impact assessment (Architect, 2026-05-17)

Проведён анализ потребителей API. Вывод: **унификация `201→200` не является breaking change для реальных потребителей.**

- **`frontend/src/services/subscribeService.ts`** — единственный runtime-потребитель. Использует `axios.post()`, который резолвит промис на **любой** 2xx-ответ → код идёт в `try` → `return data`. Статус инспектируется **только в ветке `catch`** (`409`/`400`/`429`/`5xx`). Различие `200` vs `201` сервис **не считывает**.
- **Тело ответа** новой подписки и already_subscribed **уже идентично** (`{"message": ..., "email": ...}`) — оракул держится исключительно на числе статус-кода.
- **Mobile / третьи интеграции** — не обнаружены. API single `/api/v1/`, без path-версионирования, SDK нет.
- **OpenAPI / `api.generated.ts`** — документирует `200` и `201`, оба **без типизированного тела**. `subscribeService` использует рукописный тип `SubscribeResponse` из `api.ts`, а не `operations`.

`201 Created` для пути already_subscribed был **семантически неточен изначально**: этот путь ресурс не создаёт. Унификация на `200 OK` для обоих исходов — REST-корректна.

### Отклонённые альтернативы

- **Header `X-Subscription-New` / поле `is_new` в теле** — реинтродукция уязвимости: атакующий читает признак вместо статус-кода. Отклонено.
- **`/api/v2/subscribe/`** — версионирование ради одного статус-кода, противоречит single-version-политике проекта. Отклонено.

### Граница story (что НЕ закрывается)

Эта story закрывает **HTTP-code-differential** на `/subscribe/`. За её пределами остаются (см. `deferred-work.md`, раздел `security-email-enumeration-hardening`):
- **Timing side-channel** — success-путь делает записи в БД (`Newsletter`, `UserConsent`), already_subscribed — нет; разница во времени ответа измерима усреднением.
- **Behavioral side-channel** — `unsubscribed_at` и эффект повторной отписки на `/unsubscribe/`.

Оба требуют отдельного решения (равнизация времени ответа / constant-time паттерн) либо фиксации как acceptable risk. Не в scope этой story.

---

## Текущее состояние кода (прочитано перед реализацией)

### `/subscribe/` success-путь — `backend/apps/common/views.py:468-478`

```python
# ТЕКУЩИЙ КОД (новая подписка):
response_serializer = SubscribeResponseSerializer(
    {
        "message": "Вы успешно подписались на рассылку",
        "email": subscription.email,
    }
)
return Response(
    response_serializer.data,
    status=status.HTTP_201_CREATED,  # ← различимо от 200 already_subscribed
)
```

Путь already_subscribed (`views.py:442-451` и `views.py:480-491`) уже возвращает `HTTP_200_OK` — менять не нужно.

### `@extend_schema` subscribe — `views.py:330-356`

Содержит оба ответа: `201` («Подписка успешно создана») и `200` («Email уже был подписан»). После унификации остаётся один `200`.

### Тесты — `backend/tests/integration/test_common_subscribe_api.py`

14 ассертов `status.HTTP_201_CREATED` (строки 38, 87, 120, 195, 223, 241, 259, 282, 302, 317, 344, 364, 469, 495). Имён тестов с `201`/`created` нет — переименование не требуется. Строка 495 — throttle-флуд-тест: `statuses[:5] == [status.HTTP_201_CREATED] * 5`.

### MSW-мок — `frontend/src/__mocks__/api/handlers.ts:631-663`

Мок отдаёт `201` на успех и `409` на дубликат — **уже рассинхронизирован** с бэкендом (бэкенд `409` не возвращает после предшествующей story).

### Мёртвый код — `frontend/src/services/subscribeService.ts:68-70`

Ветка `if (axiosError.response?.status === 409)` недостижима — бэкенд `409` больше не возвращает.

---

## Acceptance Criteria

### AC-1: `/subscribe/` возвращает `200 OK` при новой подписке

**Given** анонимный пользователь делает POST `/api/v1/subscribe/` с `pdp_consent: true` и email, которого нет в базе,
**When** запрос обработан и подписка успешно создана,
**Then** ответ — **200 OK** с телом `{"message": "Вы успешно подписались на рассылку", "email": "<email>"}`.

### AC-2: `/subscribe/` никогда не возвращает `201`

**Given** любой запрос на `/api/v1/subscribe/`,
**When** обработан,
**Then** HTTP-код ответа **никогда не равен 201**. Новая подписка и already_subscribed возвращают идентичный `200 OK` с идентичным телом — атакующий не может различить исходы по статус-коду.

### AC-3: `@extend_schema` subscribe обновлён

**Given** декоратор `@extend_schema` на view `subscribe` (`views.py:330-356`),
**When** проверяется секция `responses`,
**Then** ключ `201` удалён; остаётся один `200` с нейтральным описанием (например, «Запрос на подписку обработан»), покрывающий и новую подписку, и already_subscribed. Описание не раскрывает факт существования подписки.

### AC-4: Существующие тесты subscribe обновлены

**Given** `backend/tests/integration/test_common_subscribe_api.py`,
**When** запускается весь файл,
**Then** все 14 ассертов `status.HTTP_201_CREATED` заменены на `status.HTTP_200_OK` (включая throttle-флуд-тест на строке 495: `[status.HTTP_200_OK] * 5`). Все тесты проходят.

### AC-5: MSW-мок синхронизирован с бэкендом

**Given** `frontend/src/__mocks__/api/handlers.ts` хендлер `POST /subscribe` (строки 631-663),
**When** проверяется мок,
**Then**:
- успешная подписка возвращает `200` (не `201`);
- ветка `409` (already subscribed) удалена либо заменена на `200` с нейтральным телом — мок отражает реальный контракт бэкенда.

### AC-6: Мёртвая ветка `409` удалена из `subscribeService`

**Given** `frontend/src/services/subscribeService.ts`,
**When** проверяется обработка ошибок,
**Then** недостижимая ветка `if (axiosError.response?.status === 409)` (строки 68-70) и связанный код ошибки `already_subscribed` удалены. Существующие тесты `subscribeService.test.ts` проходят (или обновлены, если ассертили эту ветку).

### AC-7: OpenAPI и frontend-типы регенерированы

**Given** изменённый контракт,
**When** регенерируются артефакты,
**Then**:
- `docs/api/openapi.yaml` обновлён через `manage.py spectacular`;
- `frontend/src/types/api.generated.ts` обновлён через `cd frontend && npm run generate:types`;
- у `subscribe_create` в `responses` **отсутствует** `201`, присутствует `200`.

### AC-8: Документация story-предшественника закрыта

**Given** `_bmad-output/implementation-artifacts/deferred-work.md`,
**When** проверяется раздел `Deferred from: code review of security-email-enumeration-hardening (2026-05-17)`,
**Then** пункт «`/subscribe/` остаточный вектор enumeration (201 vs 200)» помечен как resolved (ссылка на эту story).

---

## Tasks / Subtasks

⚠️ **Все нижеперечисленные tasks БЛОКИРОВАНЫ до merge `security-email-enumeration-hardening` в main/develop.**

Проверить статус: `git log --oneline | head -5` должен содержать commit `e76b7e6c` (или его cherry-pick на develop).

---

- [x] Task 1: Унифицировать статус subscribe на `200` (AC: 1, 2)
  - [x] 1.1: `backend/apps/common/views.py:476` — заменить `status.HTTP_201_CREATED` → `status.HTTP_200_OK` в success-ветке
- [x] Task 2: Обновить OpenAPI-схему (AC: 3)
  - [x] 2.1: `views.py:330-356` — убрать ответ `201` из `@extend_schema`, оставить один `200` с нейтральным описанием
- [x] Task 3: Обновить backend-тесты (AC: 4)
  - [x] 3.1: `test_common_subscribe_api.py` — заменить все `HTTP_201_CREATED` → `HTTP_200_OK` (14 мест, вкл. строку 495)
- [x] Task 4: Синхронизировать frontend-мок и сервис (AC: 5, 6)
  - [x] 4.1: `handlers.ts:631-663` — успех `200`, убрать/заменить ветку `409`
  - [x] 4.2: `subscribeService.ts:68-70` — удалить мёртвую ветку `409`
  - [x] 4.3: Прогнать `subscribeService.test.ts` / `SubscribeForm.test.tsx` / `ElectricSubscribeForm.test.tsx`, обновить при падении
- [x] Task 5: Регенерировать артефакты (AC: 7)
  - [x] 5.1: `manage.py spectacular` → `docs/api/openapi.yaml`
  - [x] 5.2: `cd frontend && npm run generate:types`
- [x] Task 6: Закрыть deferred-пункт предшественника (AC: 8)
  - [x] 6.1: `deferred-work.md` — пометить пункт `201 vs 200` как resolved

---

## Структура файлов (изменения)

| Файл | Тип | Что меняется |
|------|-----|-------------|
| `backend/apps/common/views.py` | UPDATE | `HTTP_201_CREATED` → `HTTP_200_OK` (строка 476); убрать `201` из `@extend_schema` |
| `backend/tests/integration/test_common_subscribe_api.py` | UPDATE | 14 ассертов `HTTP_201_CREATED` → `HTTP_200_OK` |
| `frontend/src/__mocks__/api/handlers.ts` | UPDATE | Хендлер `/subscribe` — успех `200`, убрать `409` |
| `frontend/src/services/subscribeService.ts` | UPDATE | Удалить мёртвую ветку `409` |
| `docs/api/openapi.yaml` | REGENERATE | `manage.py spectacular` |
| `frontend/src/types/api.generated.ts` | REGENERATE | `npm run generate:types` |
| `_bmad-output/implementation-artifacts/deferred-work.md` | UPDATE | Закрыть deferred-пункт `201 vs 200` |

---

## Важные предупреждения для dev agent

1. **Менять только success-ветку.** Путь already_subscribed (`views.py:442-451`, `480-491`) уже возвращает `200` — не трогать.
2. **Тело ответа не меняется.** `SubscribeResponseSerializer` и `{message, email}` остаются как есть — меняется только числовой статус.
3. **Throttle-тест на строке 495** ассертит `[status.HTTP_201_CREATED] * 5` — заменить на `[status.HTTP_200_OK] * 5`, иначе тест упадёт.
4. **Имена тестов не содержат `201`/`created`** — переименование не требуется, только тела ассертов.
5. **Ветка `409` в `subscribeService.ts`** недостижима с предыдущей story — удалить вместе с кодом ошибки `already_subscribed`, если он больше нигде не используется (проверить grep по проекту).
6. **Регрессия:** прогнать `pytest tests/integration/test_common_subscribe_api.py` и frontend `npm run test -- subscribe`.

---

## Связанные артефакты

- `_bmad-output/implementation-artifacts/Story/security-email-enumeration-hardening.md` — story-предшественник
- `_bmad-output/implementation-artifacts/deferred-work.md` — раздел `security-email-enumeration-hardening (2026-05-17)`
- `backend/apps/common/views.py` — основной файл реализации
- `backend/tests/integration/test_common_subscribe_api.py` — тесты subscribe
- `frontend/src/services/subscribeService.ts`, `frontend/src/__mocks__/api/handlers.ts` — frontend-потребитель и мок

---

## Change Log

- 2026-05-17: Story создана по итогам Architect impact assessment рефакторинга `/subscribe/` (Winston).
- 2026-05-17: Story принята в разработку по workflow `bmad-dev-story`; prerequisite `e76b7e6c` подтверждён как ancestor текущего `develop`.
- 2026-05-17: Story выполнена: `/subscribe/` contract зафиксирован на `200`, frontend mock/service синхронизированы, OpenAPI/types перегенерированы, deferred-пункт закрыт; story → review.
- 2026-05-17: Review-патч закрыт: удалены устаревшие ветки `already_subscribed` из фронтенд-форм подписки и удалён unreachable-тест; story и sprint-status синхронизированы на `review`.

---

## Dev Agent Record

### Debug Log

- 2026-05-17: Загружены workflow `bmad-dev-story`, BMAD config, `project-context.md`, story-файл и полный `sprint-status.yaml`.
- 2026-05-17: Prerequisite проверен: `git merge-base --is-ancestor e76b7e6c HEAD` подтвердил, что hardening-предшественник уже входит в текущий `develop`.
- 2026-05-17: GitNexus impact перед правками: `Function:backend/apps/common/views.py:subscribe` — LOW risk, 0 direct callers/process flows; `Method:frontend/src/services/subscribeService.ts:subscribe#1` — LOW risk, 0 direct callers/process flows.
- 2026-05-17: RED подтверждён frontend-тестом `does not expose the removed already_subscribed contract for unexpected 409 responses`: на старом `subscribeService` тест падал, потому что `409` мапился в `already_subscribed`.
- 2026-05-17: `manage.py spectacular --file ../docs/api/openapi.yaml --validate` и `npm run generate:types` выполнены успешно.
- 2026-05-17: GitNexus detect-changes после реализации: 11 files, 2 indexed symbols (`AGENTS.md`, `CLAUDE.md`), affected processes 0, risk low. GitNexus не индексирует изменённые generated/docs/frontend mock symbols как affected flows.
- 2026-05-17: Frontend Docker container перезапущен после изменений в `frontend/src/`: `docker compose --env-file ../.env -f ../docker/docker-compose.yml restart frontend`.
- 2026-05-17: После review-патча выполнены `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/__tests__/subscribeService.test.ts`, `npx eslint src/components/home/SubscribeForm.tsx src/components/home/ElectricSubscribeForm.tsx src/components/home/__tests__/SubscribeForm.test.tsx --max-warnings=0`, `npm run test`, `npm run build`; все проверки прошли.

### Completion Notes

- Task 1/2/3: backend success-путь `subscribe()` уже был приведён к `HTTP_200_OK` в текущем `develop`; `@extend_schema`, `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` и `test_common_subscribe_api.py` подтверждают отсутствие `201` у `subscribe_create`.
- Task 4: MSW handler `/subscribe` теперь возвращает нейтральный `200` с тем же success-body для валидных email, включая ранее special-cased `existing@example.com`; мёртвая ветка `409 -> already_subscribed` удалена из `subscribeService`.
- Task 4 tests: добавлен regression-тест в `subscribeService.test.ts`; RED падал на старом маппинге `409`, после правки проходит.
- Task 5: OpenAPI schema перегенерирована через `manage.py spectacular --file ../docs/api/openapi.yaml --validate`; frontend-типы перегенерированы через `npm run generate:types` и отформатированы Prettier.
- Task 6: deferred-пункт `/subscribe/` `201 vs 200` в `_bmad-output/implementation-artifacts/deferred-work.md` помечен как resolved by `security-subscribe-status-unification`.
- Validation targeted backend: `pytest tests/integration/test_common_subscribe_api.py apps/common/tests/test_common_config.py` — 47 passed.
- Validation targeted frontend: `npm run test -- src/services/__tests__/subscribeService.test.ts src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx` — 36 passed.
- Validation frontend full: `npm run test` — passed; `npx tsc --noEmit` — passed.
- Code quality: `npx prettier --check ...`, `npx eslint ... --max-warnings=0`, `git diff --check`, `python manage.py check` — passed.
- Full backend regression: первый `pytest -q` остановлен таймаутом инструмента через 30 минут без итогового вывода; после остановки фоновых pytest-процессов fail-fast `pytest --maxfail=1 --tb=short -q` дал `1758 passed, 3 skipped` и остановился на известном data-dependent blocker `tests/integration/test_management_commands/test_import_customers.py::TestImportCustomersCommand::test_command_imports_real_customers` из-за отсутствующей `/app/data/import_1c/contragents`. Повторный прогон с `--ignore=tests/integration/test_management_commands/test_import_customers.py` остановлен таймаутом инструмента через 20 минут без итогового вывода.
- Review patch: удалены устаревшие ветки `already_subscribed` из `SubscribeForm` и `ElectricSubscribeForm`, а ложный тест `SubscribeForm.test.tsx` удалён; компонентный fallback теперь унифицирован на общий error-path.

### File List

- `_bmad-output/implementation-artifacts/Story/security-subscribe-status-unification.md`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/api/openapi.yaml`
- `frontend/src/__mocks__/api/handlers.ts`
- `frontend/src/services/__tests__/subscribeService.test.ts`
- `frontend/src/services/subscribeService.ts`
- `frontend/src/types/api.generated.ts`
- `frontend/src/components/home/SubscribeForm.tsx`
- `frontend/src/components/home/ElectricSubscribeForm.tsx`
- `frontend/src/components/home/__tests__/SubscribeForm.test.tsx`

---

### Review Findings

Code review (2026-05-17, 3 слоя: Blind Hunter / Edge Case Hunter / Acceptance Auditor). AC-1..AC-5, AC-7, AC-8 подтверждены выполненными. AC-6 закрыт — см. ниже.

- [x] [Review][Patch] Осиротевший код `already_subscribed` в формах подписки и ложно-зелёный тест — resolved: после удаления ветки `409 → already_subscribed` из `subscribeService` сервис больше никогда не бросает `'already_subscribed'`. Ветки `if (error.message === 'already_subscribed')` удалены из `SubscribeForm` и `ElectricSubscribeForm`, а unreachable-тест `SubscribeForm.test.tsx` удалён. AC-6 + Важное предупреждение №5 полностью закрыты. [`frontend/src/components/home/SubscribeForm.tsx:102`, `frontend/src/components/home/ElectricSubscribeForm.tsx:111`, `frontend/src/components/home/__tests__/SubscribeForm.test.tsx`]
- [x] [Review][Defer] Аномальный `409` от бэкенда классифицируется как `network_error` с потерей `details` — pre-existing catch-all паттерн `subscribeService` (любой статус вне 400/429/5xx → `network_error`); spec явно зафиксировал `409 → network_error` тестом. Не введено этой story. [`frontend/src/services/subscribeService.ts:78`] — deferred, pre-existing
- [x] [Review][Defer] Коммит `83f30fb0` содержит изменения вне scope story — правка файла story-предшественника `security-email-enumeration-hardening.md` (статус + блок re-review pass 4, 27 строк) не указана в File List этой story. Гигиена коммита; уже закоммичено, откату не подлежит. [`_bmad-output/implementation-artifacts/Story/security-email-enumeration-hardening.md`] — deferred, pre-existing
