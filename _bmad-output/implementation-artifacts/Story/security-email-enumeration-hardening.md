# Story: Security — Harden Email Enumeration on Subscribe/Unsubscribe

**Story ID:** security-email-enumeration-hardening
**Status:** review
**Priority:** High (security fix; устраняет два вектора email enumeration, зафиксированных code review Epic 35)
**Source issues:** DN8-1 (Pass 8) · WWWW3 (Pass 4) из `_bmad-output/implementation-artifacts/deferred-work.md`

---

## Story

Как **команда безопасности FREESPORT**,
я хочу **закрыть два вектора email enumeration на `/subscribe/` и `/unsubscribe/`**,
чтобы **анонимный атакующий не мог определять наличие email-адреса в базе подписчиков по HTTP-коду ответа**.

---

## Контекст и решения

### Два вектора (зафиксированы в deferred-work.md)

**DN8-1 — `/subscribe/` (POST):**
Анонимный атакующий с `pdp_consent: true` и валидным email различает «email subscribed» vs «email not subscribed» по HTTP-коду: **201 Created** (новая подписка) vs **409 Conflict** (already_subscribed). Throttle 30/min ограничивает, но не устраняет атаку — 30 проверок в минуту, 1800/час за один IP, обход через несколько IP тривиален.
Файлы: `backend/apps/common/views.py:441-451`, `backend/apps/common/serializers.py:120-127`

**WWWW3 — `/unsubscribe/` (POST):**
Endpoint не throttled (наследует глобальный `anon: 6000/min`), различает «была подписка» vs «не было» по **200 OK** vs **404 Not Found** → пассивный mass enumeration со скоростью до 100 запросов/сек.
Файл: `backend/apps/common/views.py:518-554`

### Решение принято (DN8-1, 2026-05-15)

Оба вектора принадлежат одному классу уязвимости — **differential HTTP response enumeration**. Исправлять единым паттерном в одной story.

### Вне scope этой story

- **W7-1 / trusted-proxy allowlist** — отдельная infra-story (см. `deferred-work.md`)
- **W5N7 / cross-identity reactivation** — Story 35.5 (consent audit linkage)
- **W9-4 / корпоративный NAT throttle bucket** — уже задокументировано как acceptable risk

---

## Текущее состояние кода (прочитано перед реализацией)

### `/subscribe/` — views.py:441-451

```python
# ТЕКУЩИЙ КОД (проблемный):
except DRFValidationError as exc:
    if _has_error_code(exc.detail, ALREADY_SUBSCRIBED_CODE):
        return Response(
            exc.detail,
            status=status.HTTP_409_CONFLICT,  # ← enumeration leak
        )
```

Также строки 477-481 (вне `serializer.is_valid()` ветки):
```python
if _has_error_code(serializer.errors, ALREADY_SUBSCRIBED_CODE):
    return Response(
        serializer.errors,
        status=status.HTTP_409_CONFLICT,  # ← второй путь 409
    )
```

### `/unsubscribe/` — views.py:562-569

```python
# ТЕКУЩИЙ КОД (проблемный):
if "email" in serializer.errors:
    error_msg = str(serializer.errors["email"][0])
    if "не найден" in error_msg or "уже отписан" in error_msg:
        return Response(
            serializer.errors,
            status=status.HTTP_404_NOT_FOUND,  # ← enumeration leak
        )
```

### `/subscribe/` throttle — views.py:403, throttling.py

```python
@throttle_classes([SubscribeRateThrottle])  # 30/min в prod (base.py:177)
def subscribe(request: Request) -> Response:
```

### `/unsubscribe/` throttle — ОТСУТСТВУЕТ

```python
@api_view(["POST"])
@permission_classes([AllowAny])
# ← нет @throttle_classes → наследует global anon 6000/min
def unsubscribe(request: Request) -> Response:
```

### Frontend использование `/unsubscribe/`

Проверено: `frontend/src/services/` **не содержит** сервиса для `/unsubscribe/`. Эндпоинт присутствует только в `frontend/src/types/api.generated.ts:2841` как типы. Frontend не вызывает `/unsubscribe/` — контракт 200/404 в UI **не используется**. Изменение HTTP-кода **не сломает** frontend.

---

## Acceptance Criteria

### AC-1: `/subscribe/` возвращает 200 вместо 409 при already_subscribed

**Given** анонимный пользователь делает POST `/api/v1/subscribe/` с `pdp_consent: true` и email, который уже активно подписан,
**When** запрос обработан,
**Then** ответ — **200 OK** с телом `{"message": "Вы успешно подписались на рассылку", "email": "<email>"}` (идентично успешной подписке).

Атакующий **не может** различить новую подписку (201) от существующей (ранее 409, теперь 200) — статус-коды разные (201 vs 200), но это допустимо: оба «успех», смысловая разница не раскрывает факт подписки.

> **Примечание:** 201 для новой подписки сохраняется. Только already_subscribed меняется с 409 → 200.

### AC-2: `/subscribe/` 409 полностью устранён из всех путей

**Given** любой запрос на `/api/v1/subscribe/`,
**When** обработан,
**Then** HTTP-код ответа **никогда не равен 409**. Проверить оба пути в views.py (строки 441-451 и 477-481).

### AC-3: `/unsubscribe/` добавляется throttle `UnsubscribeRateThrottle` (30/min)

**Given** endpoint `/api/v1/unsubscribe/`,
**When** один и тот же IP делает более 30 запросов в минуту,
**Then** endpoint возвращает **429 Too Many Requests**.

Реализация: добавить `UnsubscribeRateThrottle(SimpleRateThrottle)` по аналогии с `SubscribeRateThrottle` в `apps/common/throttling.py`. Добавить scope `"unsubscribe"` в `DEFAULT_THROTTLE_RATES` (base.py, development.py, staging.py, test.py). Применить `@throttle_classes([UnsubscribeRateThrottle])` к view `unsubscribe`.

### AC-4: Контракт `/unsubscribe/` 200/404 — два варианта (выбрать один)

> **Решение для dev agent:** Реализовать **Вариант A** (маскировка 404 → 200). Обоснование: frontend не использует 200/404 различие (проверено выше), Вариант A полностью устраняет enumeration, а throttle (AC-3) — дополнительный барьер.

**Вариант A (Маскировка — ВЫБРАН):**
**Given** POST `/api/v1/unsubscribe/` с email, которого нет в подписчиках (или уже отписан),
**When** запрос обработан,
**Then** ответ — **200 OK** с телом `{"message": "Запрос на отписку обработан", "email": "<email>"}` — идентично успешной отписке.

Реализация: в `views.py:562-569` убрать ветку `HTTP_404_NOT_FOUND`. Возвращать 200 с нейтральным сообщением при любом исходе (`is_valid()` → отписан ИЛИ не найден).

Обновить `UnsubscribeSerializer.save()` в `serializers.py`: метод не должен бросать `ValidationError` при «не найден» — он должен возвращать нейтральный объект или `None`. View обрабатывает оба исхода одинаково.

**Вариант B (альтернатива, не реализовывать):**
Оставить 200/404 контракт, только добавить throttle (AC-3). Менее разрушительно, но не устраняет enumeration — только замедляет.

### AC-5: `/unsubscribe/` 404 полностью устранён из ответов

**Given** любой запрос на `/api/v1/unsubscribe/` с валидным email,
**When** обработан,
**Then** HTTP-код **никогда не равен 404** (кроме стандартного Django 404 при неправильном URL, что не относится к endpoint-логике).

### AC-6: Settings обновлены — `unsubscribe` rate в DEFAULT_THROTTLE_RATES

**Given** файлы настроек backend,
**When** проверяется `DEFAULT_THROTTLE_RATES`,
**Then** ключ `"unsubscribe"` присутствует в:
- `backend/freesport/settings/base.py` → `"30/min"` (production rate)
- `backend/freesport/settings/development.py` → `"100000/min"` (не блокирует dev)
- `backend/freesport/settings/staging.py` → `"30/min"` (production-like; исправлено по CR pass 2 — staging должен совпадать с прод-rate, симметрично `subscribe`)
- `backend/freesport/settings/test.py` → `"100000/min"` (не блокирует тесты)

### AC-7: Тесты обновлены — 409 заменён на 200 в тестах подписки

**Given** файл `backend/tests/integration/test_common_subscribe_api.py`,
**When** запускается тест `test_subscribe_duplicate_email` (строка 43) и смежные тесты,
**Then** все ассерты `status.HTTP_409_CONFLICT` заменены на `status.HTTP_200_OK`.

Список тестов, требующих обновления (проверить весь файл на `409`):
- `test_subscribe_duplicate_email` (строка 43-55)
- `test_subscribe_returns_409_when_newsletter_unique_race_hits_integrity_error` (строка 445-456)

> Проверить: возможно, названия тестов тоже надо обновить (`409` в имени → `200`).

### AC-8: Новые тесты для `/unsubscribe/` throttle и маскировки

**Given** файл `backend/tests/integration/test_common_subscribe_api.py` (или отдельный файл для unsubscribe),
**When** добавлены тесты,
**Then** покрыты:

- `test_unsubscribe_unknown_email_returns_200` — POST с несуществующим email → 200 OK
- `test_unsubscribe_already_unsubscribed_returns_200` — POST с email, подписка которого уже `is_active=False` → 200 OK
- `test_unsubscribe_success_returns_200` — POST с активным subscriber → 200 OK (регрессия)
- `test_unsubscribe_throttle_kicks_in` — более 5 запросов за 1 мин → 429 (по аналогии с `test_subscribe_scope_throttle_kicks_in_during_valid_payload_flood`)
- `test_unsubscribe_throttle_scope_check_rejects_missing_rate` — по аналогии с `test_subscribe_throttle_scope_check_rejects_missing_rate` в `test_common_config.py`

### AC-9: OpenAPI обновлён, если контракт изменился

**Given** декоратор `@extend_schema` на view `subscribe` (строка 331-398) и `unsubscribe` (строка 490-536),
**When** реализован новый контракт,
**Then**:
- `/subscribe/`: убрать `409` из `responses` в `@extend_schema`; оставить/добавить `200` для already_subscribed с нейтральным описанием.
- `/unsubscribe/`: убрать `404` из `responses` в `@extend_schema`; убрать из description фразу «Если email не найден или уже отписан - возвращает 404 Not Found».
- Регенерировать типы: `cd frontend && npm run generate:types` (путь настроен в `package.json`).

### AC-10: Django system check для `unsubscribe` rate (опционально, если `common.E002` расширяется)

**Given** `backend/apps/common/apps.py` функция `check_session_engine_for_subscribe_consent`,
**When** в `DEFAULT_THROTTLE_RATES` отсутствует ключ `"unsubscribe"`,
**Then** проверить, стоит ли добавить аналогичный check `common.E003` (по образцу `common.E002` для subscribe). Это защитит от случайного удаления rate в будущем.

> Реализовать если diff небольшой; пропустить если добавляет complexity без ценности.

---

## Tasks / Subtasks

- [x] Task 1: Исправить `/subscribe/` — убрать 409 (AC: 1, 2)
  - [x] 1.1: В `backend/apps/common/views.py` строки 441-451: заменить `HTTP_409_CONFLICT` → `HTTP_200_OK`, убедиться что тело ответа нейтральное (не раскрывает «вы уже подписаны»)
  - [x] 1.2: В `backend/apps/common/views.py` строки 477-481: убрать вторую ветку `HTTP_409_CONFLICT` (или изменить на 200)
  - [x] 1.3: Обновить `@extend_schema` на subscribe — убрать 409, добавить 200 для already_subscribed

- [x] Task 2: Добавить `UnsubscribeRateThrottle` (AC: 3, 6)
  - [x] 2.1: В `backend/apps/common/throttling.py` добавить класс `UnsubscribeRateThrottle(ProxyAwareThrottleIdentMixin, SimpleRateThrottle)` с `scope = "unsubscribe"` — по образцу `SubscribeRateThrottle`
  - [x] 2.2: В `backend/freesport/settings/base.py` добавить `"unsubscribe": "30/min"` в `DEFAULT_THROTTLE_RATES`
  - [x] 2.3: В `backend/freesport/settings/development.py`, `staging.py`, `test.py` добавить `"unsubscribe": "100000/min"`
  - [x] 2.4: В `backend/apps/common/views.py` добавить `@throttle_classes([UnsubscribeRateThrottle])` к view `unsubscribe`
  - [x] 2.5: Добавить import `UnsubscribeRateThrottle` в views.py

- [x] Task 3: Замаскировать 404 на `/unsubscribe/` (AC: 4, 5)
  - [x] 3.1: В `backend/apps/common/serializers.py` обновить `UnsubscribeSerializer.save()` — при «не найден / уже отписан» **не бросать** `ValidationError`, а возвращать нейтральный объект (например, `None` или mock-subscription с переданным email)
  - [x] 3.2: В `backend/apps/common/views.py` строки 562-569: убрать ветку `HTTP_404_NOT_FOUND`, вместо неё возвращать 200 с нейтральным сообщением `"Запрос на отписку обработан"` при любом исходе (подписан / не найден / уже отписан)
  - [x] 3.3: Обновить `@extend_schema` на unsubscribe — убрать 404 из responses, обновить description

- [x] Task 4: Обновить существующие тесты (AC: 7)
  - [x] 4.1: В `backend/tests/integration/test_common_subscribe_api.py` найти все ассерты `HTTP_409_CONFLICT` → заменить на `HTTP_200_OK`
  - [x] 4.2: Обновить описания/названия тестов если упоминают 409

- [x] Task 5: Написать новые тесты (AC: 8)
  - [x] 5.1: Добавить тесты для `/unsubscribe/` (unknown email → 200, already_unsubscribed → 200, throttle → 429) — добавить в существующий файл `test_common_subscribe_api.py` или создать `test_common_unsubscribe_api.py`
  - [x] 5.2: Добавить `test_unsubscribe_throttle_scope_check_rejects_missing_rate` в `test_common_config.py`

- [x] Task 6: Регенерировать OpenAPI типы (AC: 9)
  - [x] 6.1: `cd frontend && npm run generate:types` (проверить команду в `package.json`)
  - [x] 6.2: Убедиться что в `frontend/src/types/api.generated.ts` у `unsubscribe_create` нет 404 в responses

- [x] Task 7: (опционально) Добавить Django system check для unsubscribe rate (AC: 10)
  - [x] 7.1: В `backend/apps/common/apps.py` расширить `check_session_engine_for_subscribe_consent` или добавить отдельный check для `"unsubscribe"` rate

---

## Review Findings

_Code review 2026-05-17 (bmad-code-review, 3 слоя: Blind Hunter, Edge Case Hunter, Acceptance Auditor). Все 10 AC формально выполнены, но обнаружен дефект самого замысла AC-1._

### Deferred (resolved from decision-needed)

- [x] [Review][Defer] `/subscribe/` всё ещё допускает email enumeration через различие `201` vs `200` — Новая подписка возвращает `201 Created`, already_subscribed — `200 OK`. Атакующий по-прежнему различает «email в базе» (200) vs «нет в базе» (201) — оракул enumeration сохранён, лишь сменил коды (было 201 vs 409). AC-1 явно принимает это («оба success, смысловая разница не раскрывает факт подписки»), но это обоснование security-некорректно: атакующему важна различимость ответа, а `201 ≠ 200` различимы идеально. Исходный вектор DN8-1 закрыт лишь частично. Нашёл независимо Blind Hunter (HIGH). — deferred, требуется уточнить, критична ли REST-семантика 201 для потребителей API

### Patch

- [x] [Review][Patch] `unsubscribe` не оборачивает `serializer.save()` в try/except `DatabaseError` — асимметрия с `subscribe`, который при сбое БД отдаёт 503; здесь любая `DatabaseError` пробросится наружу как `HTTP 500` [backend/apps/common/views.py:547]
- [x] [Review][Patch] Тест `test_unsubscribe_throttle_kicks_in` не проверяет, что первые 5 запросов реально успешны (`200`) — ассертится только отсутствие `429` в `statuses[:5]`; subscribe-аналог ассертит `[201]*5` [backend/tests/integration/test_common_subscribe_api.py:937]
- [x] [Review][Patch] Нет теста на `400`-ветку `unsubscribe` (невалидный/пустой/отсутствующий email) — ветка изменилась в diff (над ней удалена 404-обработка), но осталась без покрытия [backend/tests/integration/test_common_subscribe_api.py]

### Deferred

- [x] [Review][Defer] Поведенческие side-channels `/unsubscribe/` за пределами HTTP-кода (запись `unsubscribed_at`, эффект повторной отписки) [backend/apps/common/serializers.py:155] — deferred, вне scope story (story закрывает только HTTP-код-differential)
- [x] [Review][Defer] Timing side-channel на `/subscribe/` и `/unsubscribe/` (разное время ответа для существующего vs несуществующего email) не адресован — deferred, вне scope story
- [x] [Review][Defer] В коммит security-фикса попали несвязанные правки docs (Next.js 14→15, счётчик символов GitNexus 8500→8499) [AGENTS.md, CLAUDE.md, docs/architecture/04-component-structure.md] — deferred, гигиена коммита, уже закоммичено
- [x] [Review][Defer] Full regression: 11 падающих тестов (10 — отсутствие `data/import_1c/contragents`, 1 — perf-тест 562ms vs порог 500ms) — deferred, инфраструктурные/pre-existing, заявлены вне scope в Dev Agent Record
- [x] [Review][Defer] System check `common.E003` ловит только отсутствие ключа `"unsubscribe"`, не `None`/пустой rate (при `rate=None` throttle молча отключается) [backend/apps/common/apps.py:36] — deferred, унаследованный паттерн (`common.E002` имеет тот же дефект)
- [x] [Review][Defer] `/unsubscribe/` позволяет отписать чужой активный email без подтверждения личности (abuse) — deferred, pre-existing класс abuse, намеренное проектное решение story (маскировка без токена подтверждения)

### Re-review 2026-05-17 (pass 2 — bmad-code-review, 3 слоя: Blind Hunter, Edge Case Hunter, Acceptance Auditor)

_Повторное ревью после resolve 3 Patch finding'ов. Все 3 Patch из pass 1 подтверждены закрытыми. 9/10 AC выполнены корректно._

#### Decision needed (resolved 2026-05-17)

- [x] [Review][Decision] AC-1 / DN8-1 — вектор email enumeration на `/subscribe/` закрыт лишь частично (201 vs 200). **Решено: Вариант A** — унифицировать `/subscribe/` на `200` для обоих исходов (новая подписка + already_subscribed), вектор закрывается полностью. → перенесено в Patch (P3).
- [x] [Review][Decision] `staging.py` — `unsubscribe: "100000/min"` делает staging не production-like. **Решено: Вариант A** — выставить staging `unsubscribe: "30/min"` симметрично `subscribe`; AC-6 исправлен (требование для staging: `30/min`, не `100000/min`). → перенесено в Patch (P4).

#### Patch

- [x] [Review][Patch] P1 — subscribe: ветка `already_subscribed` в `serializer.errors` эхо-ит email из `initial_data` без type-guard значения: при `email` в виде JSON-массива/объекта `str(...)` вернёт `"[...]"`/`"{...}"` в теле нейтрального `200`. Path успеха использует чистый `validated_data["email"]` — расхождение формата ответа. Добавить `isinstance(raw, str)`-guard. [`backend/apps/common/views.py:482-491`]
- [x] [Review][Patch] P2 — `@extend_schema` для `unsubscribe` не документирует `503` ответ (`unsubscribe_processing_failed`), который view возвращает при `DatabaseError`. `subscribe` свой `503` документирует — асимметрия; сгенерированные TS-типы не имеют обработчика 503. Добавить `503` в `responses` + регенерировать OpenAPI/типы. [`backend/apps/common/views.py:507-533`]
- [x] [Review][Patch] P3 (из D1) — унифицировать `/subscribe/` на `200`: success-path новой подписки вернуть `200` вместо `201`; обновить `@extend_schema` (убрать `201`, оставить единый `200`); обновить тесты, ассертящие `HTTP_201_CREATED` (включая `statuses[:5] == [201]*5` в throttle-тесте); регенерировать `docs/api/openapi.yaml` и `frontend/src/types/api.generated.ts`. [`backend/apps/common/views.py`, `backend/tests/integration/test_common_subscribe_api.py`]
- [x] [Review][Patch] P4 (из D2) — `staging.py`: `unsubscribe: "100000/min"` → `"30/min"` симметрично `subscribe`; вернуть комментарий о production-like throttle rates. [`backend/freesport/settings/staging.py:53`]

#### Deferred

- [x] [Review][Defer] `UnsubscribeSerializer.save()` делает `Newsletter.objects.get()` + `unsubscribe()` без `select_for_update()`/`transaction.atomic()` — гонка при конкурентной отписке (lost-update, перезапись `unsubscribed_at`). [`backend/apps/common/serializers.py:156-168`] — deferred, pre-existing (lock отсутствовал и до изменения)
- [x] [Review][Defer] `try/except` в `unsubscribe` ловит только `DatabaseError` — non-`DatabaseError` исключение в `unsubscribe()` существующего email → `500` (vs `200` для неизвестного) — остаточный status/timing-сигнал. [`backend/apps/common/views.py:547-562`] — deferred, узкий/теоретический путь, паттерн симметричен `subscribe`
- [x] [Review][Defer] `unsubscribe` без `@parser_classes([JSONParser])`, который есть у `subscribe` — принимает form-urlencoded/multipart, более широкая поверхность атаки. [`backend/apps/common/views.py:536`] — deferred, pre-existing асимметрия декораторов
- [x] [Review][Defer] `UnsubscribeRateThrottle.get_cache_key` — bucket чисто per-IP: за корпоративным NAT/CGNAT все пользователи делят лимит. [`backend/apps/common/throttling.py`] — deferred, явно принятый риск (W9-4 в deferred-work.md)
- [x] [Review][Defer] `test_unsubscribe_throttle_scope_check_rejects_missing_rate` ассертит `errors[0].id` по индексу — хрупко при добавлении новых system check. [`backend/apps/common/tests/test_common_config.py`] — deferred, унаследованный паттерн (тест `common.E002` тот же)
- [x] [Review][Defer] «Промах» `/unsubscribe/` (неизвестный email) не логируется — массовый harvesting не оставляет следа в аудите/логах. [`backend/apps/common/serializers.py`] — deferred, by-design tradeoff маскировки; кандидат на внутреннюю метрику

---

## Структура файлов (изменения)

| Файл | Тип | Что меняется |
|------|-----|-------------|
| `backend/apps/common/views.py` | UPDATE | Убрать 409 из subscribe (строки 441-451, 477-481); добавить throttle + убрать 404 в unsubscribe (строки 539, 562-569); обновить @extend_schema |
| `backend/apps/common/serializers.py` | UPDATE | `UnsubscribeSerializer.save()` не бросает ValidationError при «не найден» |
| `backend/apps/common/throttling.py` | UPDATE | Добавить `UnsubscribeRateThrottle` |
| `backend/freesport/settings/base.py` | UPDATE | `"unsubscribe": "30/min"` в DEFAULT_THROTTLE_RATES |
| `backend/freesport/settings/development.py` | UPDATE | `"unsubscribe": "100000/min"` |
| `backend/freesport/settings/staging.py` | UPDATE | `"unsubscribe": "100000/min"` |
| `backend/freesport/settings/test.py` | UPDATE | `"unsubscribe": "100000/min"` |
| `backend/tests/integration/test_common_subscribe_api.py` | UPDATE | Заменить HTTP_409 → HTTP_200; добавить unsubscribe тесты |
| `backend/tests/integration/test_common_unsubscribe_api.py` | NEW (опционально) | Отдельный файл для unsubscribe тестов |
| `backend/apps/common/tests/test_common_config.py` | UPDATE | Добавить check для unsubscribe scope |
| `backend/apps/common/apps.py` | UPDATE (опционально) | System check для unsubscribe rate |
| `frontend/src/types/api.generated.ts` | REGENERATE | npm run generate:types |

---

## Технические ограничения и паттерны

### Паттерн UnsubscribeRateThrottle (по образцу SubscribeRateThrottle)

```python
class UnsubscribeRateThrottle(ProxyAwareThrottleIdentMixin, SimpleRateThrottle):
    """Отдельный лимит для write-endpoint отписки от рассылки."""
    scope = "unsubscribe"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
```

### Нейтральный ответ при already_subscribed (subscribe)

Вместо раскрытия факта подписки — тот же тип ответа что при успехе, но 200 (не 201):
```python
# При already_subscribed возвращать 200, используя email из запроса
response_serializer = SubscribeResponseSerializer({
    "message": "Вы успешно подписались на рассылку",
    "email": validated_email,  # из serializer.validated_data или exc.detail
})
return Response(response_serializer.data, status=status.HTTP_200_OK)
```

### Нейтральный ответ при unsubscribe (не найден)

```python
# При «не найден» или «уже отписан» — тот же ответ что при успехе
response_serializer = UnsubscribeResponseSerializer({
    "message": "Запрос на отписку обработан",
    "email": email_from_request,
})
return Response(response_serializer.data, status=status.HTTP_200_OK)
```

### Обновление UnsubscribeSerializer.save()

Текущий код: при «не найден» бросает ValidationError → view возвращает 404.
Новый подход: вернуть sentinel или None; view сам формирует нейтральный ответ:

```python
def save(self, **kwargs):
    email = self.validated_data["email"]
    try:
        subscription = Newsletter.objects.get(email=email, is_active=True)
        # ... deactivate ...
        return subscription
    except Newsletter.DoesNotExist:
        return None  # ← view обработает нейтрально
```

---

## Важные предупреждения для dev agent

1. **Не удалять existing subscriber status 201 vs 200 разницу.** Новая подписка → 201 Created. Already_subscribed → 200 OK. Это не нарушает сокрытие: оба «успех», а атакующий не может узнать о существующей подписке (он видит только «200» и правдоподобный ответ).

2. **Throttle tests используют `patch.object(SubscribeRateThrottle, 'THROTTLE_RATES', ...)`** — применить тот же паттерн для UnsubscribeRateThrottle тестов.

3. **`cache.clear()` в throttle тестах** — использовать тот же паттерн что в `test_subscribe_scope_throttle_kicks_in_during_valid_payload_flood` (строки 469-492 в test_common_subscribe_api.py).

4. **NEVER создавать синтетические XML или mock-данные для 1С** — не имеет отношения к этой story, но стандартное правило проекта.

5. **Тест `test_subscribe_duplicate_email` (строка 43)** ассертит `"уже подписан" in str(response.data["email"][0])` и `response.data["email"][0].code == "already_subscribed"` — эти ассерты тела ответа, вероятно, тоже изменятся, если в 200 ответе возвращается `message` а не field-level error. Проверить что тело ответа при AC-1 не содержит `already_subscribed` error code — иначе тест надо переписать принципиально.

6. **Проверить `_has_error_code` helper** — используется для детекции `already_subscribed` в view. После рефактора он может стать ненужным для этого пути.

---

## Dev notes / learnings из предыдущих story

Из Story 35.3 (consent checkbox in subscribe form):
- `SubscribeRateThrottle` уже работает и протестирован. `UnsubscribeRateThrottle` — точная копия с другим scope.
- `DEFAULT_THROTTLE_RATES` обновляется в 4 файлах settings: base, development, staging, test. Не забыть ни один.
- Импорт `SubscribeRateThrottle` уже в `views.py:32` — добавить рядом `UnsubscribeRateThrottle`.
- `@throttle_classes([])` применён к некоторым view-функциям в этом файле (строка 73) — для unsubscribe нужен конкретный класс, не пустой список.
- System check `common.E002` проверяет `"subscribe"` rate; аналогичная проверка для `"unsubscribe"` — хороший pattern.

---

## Связанные артефакты

- `_bmad-output/implementation-artifacts/deferred-work.md` — исходный контекст (DN8-1, WWWW3)
- `backend/apps/common/views.py` — основной файл реализации
- `backend/apps/common/serializers.py` — логика UnsubscribeSerializer
- `backend/apps/common/throttling.py` — throttle классы
- `backend/apps/common/apps.py` — system checks
- `backend/tests/integration/test_common_subscribe_api.py` — основной тестовый файл
- `backend/apps/common/tests/test_common_config.py` — config checks
- `backend/freesport/settings/base.py:175-179` — DEFAULT_THROTTLE_RATES

---

## Dev Agent Record

### Debug Log

- 2026-05-16: Загружен workflow `bmad-dev-story`, конфигурация BMAD и полный story-файл.
- 2026-05-17: Выполнен follow-up CR: 3 Patch finding'а из code review resolved — DatabaseError wrap в unsubscribe view, улучшен assert throttle-теста, добавлен тест на 400-ветку unsubscribe. Тесты 42/42 passed. Flake8/Black проходят.
- 2026-05-16: GitNexus impact перед правками: `subscribe`, `unsubscribe`, `UnsubscribeSerializer`, `SubscribeRateThrottle` — LOW risk.
- 2026-05-16: GitNexus impact перед расширением system check: `check_session_engine_for_subscribe_consent` — LOW risk.
- 2026-05-16: GitNexus detect-changes после реализации: 16 файлов, 12 symbols, 3 affected flows (`Subscribe → Get_client_ip`, `Subscribe → Normalize_consent_ip`, `Subscribe → Sanitize_log_value`), risk `medium`.
- 2026-05-17: GitNexus impact перед CR pass 2 patch: `subscribe` и `unsubscribe` — LOW risk, direct callers/importers 0; `subscribe` затрагивает 3 audit/IP flows, `unsubscribe` без process flows.
- 2026-05-17: RED для P3 подтверждён: `test_subscribe_success` ожидал `200`, старый код возвращал `201`.
- 2026-05-17: GitNexus detect-changes после P1-P4: 10 files, 4 symbols, 3 affected flows, risk `medium`.

### Completion Notes

- Task 1: `/subscribe/` больше не возвращает `409` для `already_subscribed`/unique race; оба пути возвращают нейтральный `200 OK` с success-body.
- Task 1 tests: `test_subscribe_duplicate_email` и `test_subscribe_returns_200_when_newsletter_unique_race_hits_integrity_error` сначала падали на старом `409`, после правки проходят.
- Task 2: добавлен `UnsubscribeRateThrottle`, scope `unsubscribe` прописан в `base/development/staging/test`, view `unsubscribe` использует отдельный throttle.
- Task 2 tests: `test_unsubscribe_throttle_kicks_in` сначала падал на отсутствующем классе, после правки проходит.
- Task 3: `/unsubscribe/` возвращает нейтральный `200 OK` для активной, отсутствующей и уже неактивной подписки; `404` из endpoint-логики убран.
- Task 3 tests: три unsubscribe-теста сначала падали на старом `404`/сообщении, после правки проходят.
- Tasks 4/5/7: существующие subscribe-тесты обновлены, добавлены unsubscribe masking/throttle тесты и Django system check `common.E003`.
- Validation: `pytest tests/integration/test_common_subscribe_api.py apps/common/tests/test_common_config.py` — 41 passed.
- Task 6: OpenAPI схема перегенерирована через `manage.py spectacular`, TypeScript-типы обновлены через `npm run generate:types`; `subscribe_create` без `409`, `unsubscribe_create` без `404`.
- Code quality: `black --check` и `flake8` по затронутым backend-файлам проходят; `python manage.py check` — без issues; `git diff --check` — без ошибок.
- Full regression: test-compose full suite запущен; итог `2270 passed, 15 skipped, 11 failed`. Failures вне scope story: 10 тестов `tests/integration/test_management_commands/test_import_customers.py` падают из-за отсутствующей `/app/data/import_1c/contragents`, 1 performance-тест `apps/products/tests/test_api_products.py::TestProductAPIPerformance::test_retrieve_product_with_100_variants_under_500ms` изолированно дал 562.21ms при пороге 500ms. Subscribe/unsubscribe блоки в full suite прошли.
- CR pass 2 P1: добавлен `isinstance(raw_email, str)` guard для raw `initial_data["email"]`; добавлен regression-тест `test_subscribe_duplicate_non_string_email_is_not_echoed`.
- CR pass 2 P2: `unsubscribe` OpenAPI теперь документирует `503 unsubscribe_processing_failed`; `docs/api/openapi.yaml` и `frontend/src/types/api.generated.ts` регенерированы.
- CR pass 2 P3: `/subscribe/` унифицирован на `200 OK` для новой подписки, реактивации и already_subscribed; все `HTTP_201_CREATED` ожидания в subscribe-тестах заменены на `HTTP_200_OK`.
- CR pass 2 P4: staging `unsubscribe` throttle выставлен в `"30/min"` симметрично `subscribe`.
- Validation CR pass 2: targeted RED `test_subscribe_success` failed на старом `201`; после правки `pytest tests/integration/test_common_subscribe_api.py apps/common/tests/test_common_config.py` — 43 passed.
- Code quality CR pass 2: `black --check apps/common/views.py tests/integration/test_common_subscribe_api.py freesport/settings/staging.py`, `flake8 ...`, `python manage.py check` и `git diff --check` проходят.
- Full regression CR pass 2: `pytest -q` был остановлен таймаутом инструмента через 20 минут без итогового результата. Fail-fast `pytest --maxfail=1 --tb=short -q` сначала остановился на unrelated order/cache-state падении `apps/banners/tests/test_signals.py::TestBannerCacheInvalidation::test_save_marketing_does_not_invalidate_hero_cache`; этот файл изолированно прошёл `7 passed`. Повторный fail-fast был остановлен таймаутом через 10 минут без нового результата.

## File List

- `_bmad-output/implementation-artifacts/Story/security-email-enumeration-hardening.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/apps/common/views.py`
- `backend/apps/common/serializers.py`
- `backend/apps/common/apps.py`
- `backend/apps/common/tests/test_common_config.py`
- `docs/api/openapi.yaml`
- `frontend/src/types/api.generated.ts`
- `backend/apps/common/throttling.py`
- `backend/freesport/settings/base.py`
- `backend/freesport/settings/development.py`
- `backend/freesport/settings/staging.py`
- `backend/freesport/settings/test.py`
- `backend/tests/integration/test_common_subscribe_api.py`

## Change Log

- 2026-05-16: Story переведена в `in-progress` по workflow `bmad-dev-story`.
- 2026-05-16: Task 1 — закрыт `409` enumeration leak на `/subscribe/`.
- 2026-05-16: Task 2 — добавлен отдельный throttle scope для `/unsubscribe/`.
- 2026-05-16: Task 3 — закрыт `404` enumeration leak на `/unsubscribe/`.
- 2026-05-16: Tasks 4/5/7 — обновлены тесты и добавлен system check для `unsubscribe` throttle scope.
- 2026-05-16: Task 6 — обновлены OpenAPI YAML и frontend API-типы.
- 2026-05-16: Story переведена в `review`; validation caveats по full regression зафиксированы в Dev Agent Record.
- 2026-05-17: Follow-up CR: `test_unsubscribe_invalid_email` добавлен; `test_unsubscribe_throttle_kicks_in` теперь ассертит `[200]*5` вместо `not in statuses[:5]`; `unsubscribe` view оборачивает `serializer.save()` в `try/except DatabaseError` с логом и 503 ответом, симметрично `subscribe`. Повторный прогон тестов subscribe/unsubscribe + config: 42 passed.
- 2026-05-17: Follow-up CR pass 2: P1-P4 закрыты; `/subscribe/` полностью унифицирован на `200`, `unsubscribe 503` добавлен в OpenAPI/types, staging `unsubscribe` rate исправлен на `30/min`; targeted tests 43 passed, story возвращена в `review`.
