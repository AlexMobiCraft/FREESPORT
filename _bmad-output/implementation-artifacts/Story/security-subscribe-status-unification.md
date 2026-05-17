# Story: Security — Унификация HTTP-статуса `/subscribe/` (201 → 200)

**Story ID:** security-subscribe-status-unification
**Status:** draft
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

- [ ] Task 1: Унифицировать статус subscribe на `200` (AC: 1, 2)
  - [ ] 1.1: `backend/apps/common/views.py:476` — заменить `status.HTTP_201_CREATED` → `status.HTTP_200_OK` в success-ветке
- [ ] Task 2: Обновить OpenAPI-схему (AC: 3)
  - [ ] 2.1: `views.py:330-356` — убрать ответ `201` из `@extend_schema`, оставить один `200` с нейтральным описанием
- [ ] Task 3: Обновить backend-тесты (AC: 4)
  - [ ] 3.1: `test_common_subscribe_api.py` — заменить все `HTTP_201_CREATED` → `HTTP_200_OK` (14 мест, вкл. строку 495)
- [ ] Task 4: Синхронизировать frontend-мок и сервис (AC: 5, 6)
  - [ ] 4.1: `handlers.ts:631-663` — успех `200`, убрать/заменить ветку `409`
  - [ ] 4.2: `subscribeService.ts:68-70` — удалить мёртвую ветку `409`
  - [ ] 4.3: Прогнать `subscribeService.test.ts` / `SubscribeForm.test.tsx` / `ElectricSubscribeForm.test.tsx`, обновить при падении
- [ ] Task 5: Регенерировать артефакты (AC: 7)
  - [ ] 5.1: `manage.py spectacular` → `docs/api/openapi.yaml`
  - [ ] 5.2: `cd frontend && npm run generate:types`
- [ ] Task 6: Закрыть deferred-пункт предшественника (AC: 8)
  - [ ] 6.1: `deferred-work.md` — пометить пункт `201 vs 200` как resolved

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
