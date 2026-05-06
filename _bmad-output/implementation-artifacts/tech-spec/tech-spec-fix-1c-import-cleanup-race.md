---
title: "Fix 1C import cleanup race in handle_init"
type: "bugfix"
created: "2026-05-05"
status: "done"
baseline_commit: "dcd5cf73e4a452c1c59da5fa7c9184eb78a07895"
context:
  - "{project-root}/_bmad-output/race-condition-analysis.md"
  - "{project-root}/CLAUDE.md"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** При обмене с 1С `handle_init()` (`views.py:421-431`) безусловно выполняет `cleanup_import_dir(force=True)` как только обнаруживает marker `.exchange_complete` от предыдущего цикла. Если Celery-задачи предыдущего цикла ещё не доели свои XML-сегменты (типичная задержка ~14 секунд), их файлы удаляются «из-под ног» — даёт ~50% data loss на медленных типах файлов (`rests`, частично `offers`).

**Approach:** Добавить в `handle_init()` ту же защитную проверку «есть ли активные `ImportSession`», которая уже работает в post-import cleanup (`tasks.py:246`). Чтобы закрыть окно Celery queue, в `finalize_batch()` / `_dispatch_or_dryrun()` переводить сессию в `IN_PROGRESS` **до** `process_1c_import_task.delay(...)` и **до** `file_service.mark_complete()`. Если хоть одна сессия в статусе `IN_PROGRESS` — `handle_init()` пропускает удаление общей директории и сохраняет marker `.exchange_complete`; cleanup произойдёт позже через post-import-хук (`tasks.py:242-261`) или в следующем `handle_init` без активных сессий. Зависшие IN_PROGRESS-сессии автоматически переводятся в `FAILED` существующим cron-таском `cleanup_stale_import_sessions` (через 2 часа) — поэтому риск вечного блока cleanup исключён.

## Boundaries & Constraints

**Always:**
- Проверять только статус `IN_PROGRESS` — согласовано с существующим контрактом: post-import cleanup (`tasks.py:246`) и stale-cron (`tasks.py:308-310`) тоже работают только с `IN_PROGRESS`. Расширение фильтра до `PENDING`/`STARTED` создало бы риск вечного блока, т.к. эти статусы stale-cron не покрывает.
- В `_dispatch_or_dryrun()` для обычного `mode=complete` перед `process_1c_import_task.delay(session.pk, str(self.import_dir))` установить `session.status = ImportSession.ImportStatus.IN_PROGRESS`, сохранить `status`, `report`, `updated_at`, и только после этого dispatch + `file_service.mark_complete()`. Это делает queued Celery-задачу видимой для `handle_init()` guard ещё до фактического старта worker'а. Обычный `_dispatch_import()` не менять только ради этого guard: в normal path он не ставит `.exchange_complete`, поэтому не создаёт тот же cleanup-trigger.
- DB-check выполняется **первым действием** внутри `if file_service.is_complete():`, **ДО** `file_service.cleanup_session(force=True)`. Причина: `cleanup_session(force=True)` сам удаляет marker `.exchange_complete` из session_dir (`file_service.py:262-274` — force-режим стирает все файлы кроме `.dry_run`). Если бы DB-check шёл после `cleanup_session`, при DB-исключении marker уже был бы потерян и retry в следующем init был бы невозможен.
- Запрос активных сессий обернуть в локальный `try/except`. При БД-исключении: лог WARNING, **выйти из cleanup-блока и продолжить формирование обычного init-response** — НЕ вызывать `cleanup_session`, `cleanup_import_dir` и `clear_complete()`. Marker остаётся, следующий init повторит попытку с восстановленной БД. Внешний `try/except` в `handle_init` остаётся как safety net.
- При успешном skip cleanup (active sessions > 0) НЕ вызывать `cleanup_session(force=True)` и `clear_complete()`; пропускается весь destructive cleanup-блок, marker `.exchange_complete` остаётся для повторной проверки в следующем `handle_init`.
- При фактическом cleanup (active == 0) поведение полностью соответствует текущему: `cleanup_session(force=True)` → `cleanup_import_dir(force=True)` → `clear_complete()`.
- Использовать `ImportSession.objects.filter(status=ImportSession.ImportStatus.IN_PROGRESS).count()` (не `.exists()`) — нужно конкретное число для INFO-лога, требуемого ниже.
- Логировать пропуск cleanup на уровне INFO с указанием sessid и точного количества активных сессий — для диагностики в продакшене.
- Изменения только в `backend/apps/integrations/onec_exchange/views.py`, `backend/apps/integrations/onec_exchange/import_orchestrator.py` (продакшен-код) и `backend/apps/integrations/tests/` (регрессионный тест).
- Использовать `ImportSession.ImportStatus.<NAME>` — не строковые литералы.

**Ask First:**
- Если регрессионный тест требует фикстур, существенно отличающихся от паттернов в `backend/apps/integrations/tests/test_import_orchestration_view.py` — HALT и спросить.
- Если для корректной мокабельности придётся убирать локальный `from .routing_service import FileRoutingService` внутри `handle_init` (`views.py:426`) и опираться на module-level импорт (`views.py:31`) — HALT, потому что это меняет namespace-паттерн в этом view.

**Never:**
- Не блокировать cleanup по статусам `PENDING` или `STARTED` — stale-cron их не переводит в FAILED, появится риск зависания cleanup навсегда.
- Не менять `tasks.py:246` (расширение фильтра там — отдельный backlog-вопрос, чтобы не раздувать scope).
- Не вводить deferred Celery cleanup с `countdown` (Опция А из анализа отклонена — обоснование в Design Notes).
- Не менять структуру каталогов на per-session (Опция Б отклонена — отдельный рефакторинг парсера).
- Не создавать новые миграции, новые модели, новые Celery-таски, новые settings.
- Не трогать `routing_service.cleanup_import_dir()` — его поведение «delete everything» остаётся корректным, защита наслаивается выше.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| --- | --- | --- | --- |
| Очередь Celery после `mode=complete` | `finalize_batch()` диспатчит Celery и сразу ставит marker | Перед `.delay()` сессия уже сохранена как `IN_PROGRESS`; marker ставится только после этого; новый `mode=init` видит active > 0 | штатный |
| Чистый старт нового цикла | marker `.exchange_complete` есть, IN_PROGRESS-сессий нет | DB-check вернул 0 → `cleanup_session(force=True)` → `cleanup_import_dir(force=True)` → `clear_complete()`; INFO-лог о cleanup | штатный |
| Race-сценарий (фикс) | marker есть, есть ≥1 `ImportSession(status=IN_PROGRESS)` | DB-check вернул N>0 → `cleanup_session(force=True)` **НЕ** вызывается; `cleanup_import_dir` **НЕ** вызывается; `clear_complete()` **НЕ** вызывается; marker остаётся; INFO-лог `Skipping import dir cleanup — N sessions in progress (sessid=...)` | штатный |
| Нет marker'а | `is_complete()` = false | Текущий путь без изменений: лог `Continuing existing exchange cycle`, никакого cleanup | штатный |
| БД-исключение в `.count()` | marker есть, БД временно недоступна при запросе active sessions (DB-check выполняется ДО `cleanup_session`) | Локальный `try/except` ловит исключение → WARNING-лог; **ни** `cleanup_session`, **ни** `cleanup_import_dir`, **ни** `clear_complete()` не вызываются; marker сохраняется; HTTP 200 init-response строится как обычно | локальный try/except + внешний try/except как safety net |
| Все сессии в терминальном статусе | только COMPLETED/FAILED в БД | Активных IN_PROGRESS нет → cleanup выполняется | штатный |

</frozen-after-approval>

## Code Map

- `backend/apps/integrations/onec_exchange/views.py` — функция `handle_init` (строки 407–450), блок 421–431 — точка правки cleanup guard. **Нюанс импорта:** `FileRoutingService` импортируется и на module level (`views.py:31`), и **повторно** локально внутри `handle_init` (`views.py:426`). Локальный `from .routing_service import` пересоздаёт имя в области функции и обходит mock на `views.FileRoutingService` → patch target должен указывать на исходный модуль (см. Execution).
- `backend/apps/integrations/onec_exchange/import_orchestrator.py:416-442` — `_dispatch_or_dryrun()` в `mode=complete`: сейчас dispatch Celery (`process_1c_import_task.delay`) идёт до `file_service.mark_complete()`, но session остаётся `PENDING` до старта worker'а. Здесь нужно перевести session в `IN_PROGRESS` до dispatch и marker.
- `backend/apps/integrations/onec_exchange/import_orchestrator.py:287-318` — `_dispatch_import()` normal path dispatches Celery, но не вызывает `mark_complete()`; не включать в race-fix без отдельного решения, чтобы не ломать multi-file `mode=import` accumulation по одному sessid.
- `backend/apps/integrations/onec_exchange/file_service.py:255-280` — `cleanup_session(force=True)` итерирует по `session_dir` и удаляет ВСЕ файлы (кроме `.dry_run`), включая marker `.exchange_complete`. Это и есть причина, по которой DB-check должен идти ДО `cleanup_session`.
- `backend/apps/integrations/onec_exchange/file_service.py:282-299` — `mark_complete` / `is_complete` / `clear_complete`, без изменений. `clear_complete` идемпотентен (`if marker.exists(): marker.unlink()`).
- `backend/apps/products/models.py:574-579` — `ImportStatus` (PENDING / STARTED / IN_PROGRESS / COMPLETED / FAILED).
- `backend/apps/products/tasks.py:242-261` — эталонный паттерн `other_active`-проверки (только `IN_PROGRESS`), который мы повторяем.
- `backend/apps/products/tasks.py:300-322` — `cleanup_stale_import_sessions` (Celery Beat), переводит `IN_PROGRESS`-сессии старше 2 ч в `FAILED` → гарантирует, что наш guard не зависнет навсегда.
- `backend/apps/integrations/onec_exchange/routing_service.py:195-228` — `cleanup_import_dir`, без изменений.
- `backend/apps/integrations/tests/test_import_orchestration_view.py` — паттерн тестов на view; рядом разместить новый тест.

## Tasks & Acceptance

**Execution:**

- [x] `backend/apps/integrations/onec_exchange/import_orchestrator.py` — в `_dispatch_or_dryrun()` для non-dry-run `mode=complete` перед `process_1c_import_task.delay(session.pk, str(self.import_dir))` установить `session.status = ImportSession.ImportStatus.IN_PROGRESS`, добавить report-запись вида `Celery task queued; session marked IN_PROGRESS before complete marker`, сохранить `status`, `report`, `updated_at`; затем dispatch Celery; затем `file_service.mark_complete()` как сейчас. `process_1c_import_task` может повторно установить `IN_PROGRESS` при старте — это идемпотентно.
- [x] `backend/apps/integrations/onec_exchange/views.py` — в `handle_init`, **первым действием** внутри `if file_service.is_complete():` (ДО `file_service.cleanup_session(force=True)`), добавить локальный `try/except` вокруг `active = ImportSession.objects.filter(status=ImportSession.ImportStatus.IN_PROGRESS).count()`. Импорт `ImportSession` лениво (внутри блока) — для согласованности с уже существующими ленивыми импортами и избежания циклов. Ветвление по результату:<br>• `active > 0` → INFO-лог `Skipping import dir cleanup — {active} sessions in progress (sessid={sessid})`; **не вызывать** `cleanup_session(force=True)`, `cleanup_import_dir`, `clear_complete`; продолжить построение обычного init-response, marker остаётся.<br>• `active == 0` → текущее поведение без изменений: `cleanup_session(force=True)` → `cleanup_import_dir(force=True)` → `clear_complete()`.<br>• Исключение в `.count()` → WARNING-лог `Active sessions check failed for {sessid}: {err}`, не вызывая `cleanup_session`, `cleanup_import_dir`, `clear_complete`; продолжить построение обычного init-response, marker сохраняется. Внешний `try/except` в `handle_init` остаётся как safety net.
- [x] `backend/apps/integrations/tests/test_handle_init_cleanup_race.py` — новый файл с регрессионными тестами по 6 сценариям I/O Matrix. Использовать APIClient + фикстуры стиля `test_import_orchestration_view.py`. **Patch target — `apps.integrations.onec_exchange.routing_service.FileRoutingService`** (или метод `cleanup_import_dir` на этом классе). НЕ `apps.integrations.onec_exchange.views.FileRoutingService`: внутри `handle_init` есть локальный `from .routing_service import FileRoutingService` (`views.py:426`), который пересоздаёт имя в области функции и обходит mock на `views`-namespace. Без правильного target тест физически удалит shared import directory. Для `FileStreamService` (импорт только на module level, `views.py:27`) — patch на `apps.integrations.onec_exchange.views.FileStreamService` работает; мокать его `is_complete()` / `cleanup_session()` / `clear_complete()`. Для активных сессий создавать через `ImportSession.objects.create(session_key=sessid, status=ImportSession.ImportStatus.IN_PROGRESS, import_type=ImportSession.ImportType.CATALOG)`. Для DB-исключения — `mocker.patch("apps.products.models.ImportSession.objects")` или patch на менеджер с `side_effect=OperationalError(...)`.

**Acceptance Criteria:**

- Given `mode=complete` диспатчит Celery и worker ещё не стартовал, when `_dispatch_or_dryrun()` ставит marker `.exchange_complete`, then связанная `ImportSession` уже сохранена как `IN_PROGRESS`, чтобы следующий `mode=init` видел active session до старта worker'а.
- Given в БД есть `ImportSession(status=IN_PROGRESS)` от предыдущего цикла **и** marker присутствует, when приходит `mode=init`, then `cleanup_session(force=True)` **НЕ** вызван, `cleanup_import_dir` **НЕ** вызван, `clear_complete()` **НЕ** вызван (marker сохранён), в логе строка, матчащая regex `Skipping import dir cleanup — \d+ sessions in progress`.
- Given активных IN_PROGRESS-сессий нет **и** marker присутствует, when приходит `mode=init`, then `cleanup_session(force=True)` вызван, `cleanup_import_dir(force=True)` вызван ровно один раз, `clear_complete()` вызван.
- Given marker отсутствует, when приходит `mode=init`, then ни `cleanup_session`, ни `cleanup_import_dir`, ни `clear_complete` не вызываются (текущее поведение сохраняется).
- Given `ImportSession.objects.filter(...).count()` бросает `OperationalError` (мок), marker присутствует, when приходит `mode=init`, then `cleanup_session` **НЕ** вызывается, `cleanup_import_dir` **НЕ** вызывается, `clear_complete` **НЕ** вызывается (marker сохраняется на диске), HTTP-ответ 200 с телом формата `zip=(yes|no)\nfile_limit=\d+\nsessid=<sessid>\nversion=<version>\n` (Content-Type `text/plain; charset=utf-8`), в логе WARNING-запись с упоминанием sessid.
- Given в БД только сессии в статусах `COMPLETED`/`FAILED`, marker присутствует, when приходит `mode=init`, then DB-check возвращает 0 → `cleanup_import_dir(force=True)` вызван (терминальные статусы не блокируют cleanup).

### Review Findings

- [x] [Review][Decision] Очередь Celery остаётся без защиты до перехода `PENDING -> IN_PROGRESS` — RESOLVED: в spec добавлено требование переводить session в `IN_PROGRESS` в `_dispatch_or_dryrun()` до Celery dispatch и до `mark_complete()`, не расширяя guard на `PENDING/STARTED`.
- [x] [Review][Decision] После skip cleanup marker удаляется, но fallback "next init" фактически пропадает — RESOLVED: skip cleanup теперь не вызывает `cleanup_session(force=True)` и `clear_complete()`, marker остаётся для retry в следующем `handle_init`.
- [x] [Review][Patch] `return` в DB-error ветке может нарушить контракт HTTP 200 [`tech-spec-fix-1c-import-cleanup-race.md:71`] — RESOLVED: DB-error ветка теперь пропускает cleanup и продолжает построение обычного init-response, без раннего выхода из `handle_init`.

## Spec Change Log

- **2026-05-05 / Review pass 1 / Finding #1: Узкий контракт IN_PROGRESS** — Спека первоначально требовала блокировать cleanup по `PENDING|STARTED|IN_PROGRESS`. Это создавало риск вечного зависания: stale-cron (`tasks.py:308`) переводит в `FAILED` только `IN_PROGRESS`, а post-import cleanup (`tasks.py:246`) тоже фильтрует только `IN_PROGRESS`. Сужение до `IN_PROGRESS` устраняет несогласованность и даёт гарантированный escape-hatch через 2 часа stale-cron'a. KEEP: симметрия с `tasks.py:246` — это и есть rationale выбора варианта 1 над A/B.
- **2026-05-05 / Review pass 1 / Finding #2: Поведение при БД-исключении** — Прежняя редакция полагалась на внешний `try/except` в `handle_init` и одновременно требовала «безусловный `clear_complete()`», что несовместимо. Зафиксировано: локальный `try/except` вокруг `.count()`, при исключении — skip cleanup **и** skip `clear_complete()`, marker сохраняется для retry. Гарантирует idempotency и не теряет состояние при транзиентных проблемах с БД.
- **2026-05-05 / Review pass 1 / Finding #3: Rationale отклонения Option A** — Анализ (`race-condition-analysis.md:213,272,298`) рекомендовал deferred Celery cleanup. Перенесено в Design Notes с обоснованием отклонения. KEEP: Option A не выбирается даже при будущих рефакторингах без явного решения race-on-write.
- **2026-05-05 / Review pass 1 / Finding #4: Синхронизация AC по DB-исключению** — AC #4 переписан под уточнённое поведение из Finding #2 (skip cleanup + skip clear_complete + WARNING + 200 OK).
- **2026-05-05 / Review pass 1 / Finding #5: `.exists()` → `.count()`** — Always-правило обязывает логировать число активных сессий; `.exists()` не даёт такого числа. Зафиксирован `.count()`. Стоимость одного `SELECT COUNT(*)` пренебрежима для нашей нагрузки.
- **2026-05-05 / Review pass 1 / Finding #6: Patch target для теста** — Явно указано: мокать `apps.integrations.onec_exchange.views.FileRoutingService`, а не `...routing_service.FileRoutingService`. В Python mock работает по «местy импорта»; неверный target пропустит реальный вызов и сотрёт shared import directory во время тестов. **Скорректировано в pass 2 (см. Finding #2 ниже).**
- **2026-05-05 / Review pass 2 / Finding #1: DB-check ДО `cleanup_session`** — Прежняя редакция размещала DB-check после `cleanup_session(force=True)`. Но `cleanup_session(force=True)` (`file_service.py:255-280`) удаляет ВСЕ файлы в session_dir, включая marker `.exchange_complete`. При DB-исключении marker оказывался уже потерян → retry в следующем init был невозможен, контракт «marker preserved on DB error» не выполнялся. Перенесено: DB-check — первое действие внутри `if is_complete():`. KEEP: порядок DB-check → cleanup_session → cleanup_import_dir → clear_complete нельзя менять, иначе ломается idempotency.
- **2026-05-05 / Review pass 2 / Finding #2: Patch target — `routing_service`, не `views`** — Pass 1 ошибочно зафиксировал patch target на `views.FileRoutingService`. Реальность (`views.py:426`): внутри `handle_init` есть локальный `from .routing_service import FileRoutingService`, который пересоздаёт имя в области функции и обходит mock на module-level атрибуте `views`. Корректный target — `apps.integrations.onec_exchange.routing_service.FileRoutingService`. Для `FileStreamService` (импорт только на module level в `views.py:27`) патч на `views`-namespace остаётся корректным. KEEP: при будущем рефакторинге, если локальный импорт уберут (Ask First gate), patch target можно будет менять обратно.
- **2026-05-05 / Review pass 2 / Finding #3: Удалён бесполезный Ask First gate** — Пункт «если `handle_init` вызывается из других мест» формально срабатывает уже на существующий POST-dispatch (`views.py:234`) и GET-dispatch — gate был ложно-положительным с самого начала. Удалён. Заменён на полезный gate: «если для мокабельности придётся убрать локальный импорт `FileRoutingService` — HALT», т.к. это меняет namespace-паттерн.
- **2026-05-05 / Review pass 2 / Finding #4: AC #4 — точное тело init-ответа** — Прежнее «HTTP-ответ 200 с корректным телом» было неоднозначным. Зафиксирован конкретный формат `zip=(yes|no)\nfile_limit=\d+\nsessid=<sessid>\nversion=<version>\n` и Content-Type `text/plain; charset=utf-8` (соответствует `views.py:447-449`).
- **2026-05-05 / Review pass 2 / Finding #5: Verification формулировки** — Команды описывались как «все тесты зелёные», что читается как утверждение о текущем состоянии, а не как ожидаемый результат после реализации. Переформулировано в формат `command -- expected: <criterion>` (см. Verification ниже).
- **2026-05-05 / Review pass 3 / Finding #1: Очередь Celery до `IN_PROGRESS`** — `mode=complete` создавал окно: session ещё `PENDING`, Celery уже dispatched, marker уже поставлен. Решение: в `_dispatch_or_dryrun()` переводить session в `IN_PROGRESS` до `.delay()` и до `mark_complete()`. Guard остаётся только по `IN_PROGRESS`, чтобы не расширять stale-cleanup на `PENDING/STARTED`.
- **2026-05-05 / Review pass 3 / Finding #2: Marker при skip cleanup** — Skip-ветка больше не вызывает `cleanup_session(force=True)` и `clear_complete()`. Marker сохраняется, поэтому fallback "следующий init повторит cleanup после active==0" стал реальным, а не декларативным.
- **2026-05-05 / Review pass 3 / Finding #3: DB-error без раннего HTTP return** — Формулировка "return из ветки" заменена на "пропустить cleanup-блок и продолжить построение init-response", чтобы AC #4 с HTTP 200 не зависел от интерпретации разработчика.
- **2026-05-06 / Review pass 4 / Acceptance auditor: SPEC_FULLY_SATISFIED** — Audit subagent подтвердил: все Always/Never правила соблюдены, все 6 строк I/O Matrix покрыты, все 6 AC ассертятся в тестах, patch targets корректны (`routing_service.FileRoutingService` — не `views`), marker preservation на DB-error реально гарантировано порядком (DB-check ДО `cleanup_session`). 0 findings. KEEP: контракт спеки полностью совпадает с реализацией — при будущих изменениях не вводить регрессий по этим точкам.
- **2026-05-06 / Review pass 4 / Blind hunter F4 (patch): узкий мок DB-error** — Тест мокал `ImportSession.objects` целиком, что заменяло default manager на время request и могло пропускать ошибки в signals/middleware. Сужено до `ImportSession.objects.filter`, переменная `mock_objects` → `mock_filter`. Тесты остались зелёные.
- **2026-05-06 / Review pass 4 / Blind hunter F5 (patch): specific DB exception** — `except Exception as db_err` в `handle_init` сужено до `except DatabaseError as db_err` (импорт уже был добавлен в `views.py:16`). Не маскирует посторонние исключения, оставляет внешний `try/except` как safety net. `OperationalError` — наследник `DatabaseError`, поэтому покрытие сохраняется.
- **2026-05-06 / Review pass 4 / Defer F3, F8** — F3 (sub-ms race window между `.count()` и cleanup) и F8 (локальный re-import `FileRoutingService`) записаны в `deferred-work.md`. F3 — реальный, но сужен на 4 порядка vs изначальный bug; F8 — pre-existing code smell.
- **2026-05-06 / Review pass 4 / Edge case hunter не отработал** — Запуск review subagent'а упёрся в account rate limit (без полезного output). Pass получился частичный (Blind + Acceptance). Записано в `deferred-work.md` для возможного запуска отдельной сессией. Acceptance auditor подтвердил полное покрытие спеки, что снижает риск пропущенных нарушений контракта.

## Design Notes

**Почему Option A (deferred Celery cleanup из анализа) отклонена.** Анализ предложил убрать cleanup из `handle_init` и ставить отдельную Celery-задачу с `countdown=120s`. Проблема: в окне countdown 1С может прислать новый `mode=init` с **новым** sessid и начать загружать файлы в ту же общую директорию `/app/media/1c_import/`. Когда отложенная задача сработает — она удалит файлы новой сессии. Race на удаление превращается в race на запись, симптом сохраняется. Защита через `IN_PROGRESS`-фильтр гарантирует, что cleanup пропускается ровно тогда, когда есть реально активный consumer файлов. Для очереди Celery в `mode=complete` активное состояние создаётся до `.delay()` и до marker. Cleanup срабатывает либо в post-import-хуке (`tasks.py:246`) сразу после завершения последней задачи, либо в следующем `init`, когда активное состояние уже снято и marker всё ещё присутствует.

**Почему `.count()`, а не «расширенный `.exists()` + второй запрос для лога».** Один `SELECT COUNT(*)` дешевле двух запросов и даёт точное число для лога одной операцией.

**Почему не guard по `PENDING`/`STARTED`.** Эти статусы используются как pre-dispatch / transitional состояния и не покрываются текущим stale-cron. Вместо расширения guard статус batch-session из очереди переводится в уже поддерживаемый `IN_PROGRESS` до marker, после чего существующий stale-cron остаётся escape-hatch.

**Почему marker сохраняется при DB error.** Если БД упала в момент проверки, мы не знаем — есть активные сессии или нет. Сохранение marker'а гарантирует, что в следующем init (с восстановленной БД) логика отработает корректно. Удаление marker'а в этой ситуации привело бы к «потере цикла»: мы бы зашли в новую загрузку, не очистив директорию от файлов предыдущего цикла.

## Verification

**Commands:**

- `docker compose --env-file .env -f docker/docker-compose.test.yml exec backend pytest -xvs apps/integrations/tests/test_handle_init_cleanup_race.py` -- expected: 6 новых тестов (по каждому сценарию I/O Matrix) — все pass, exit code 0.
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec backend pytest -xvs apps/integrations/tests/test_import_orchestration_view.py` -- expected: существующие тесты orchestration view проходят без регрессий, exit code 0.
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec backend pytest apps/integrations/ apps/products/tests/` -- expected: smoke по затронутым модулям проходит, число pass-тестов ≥ baseline до правки.
- `docker compose --env-file .env -f docker/docker-compose.yml exec backend python -m black --check apps/integrations/onec_exchange/views.py apps/integrations/onec_exchange/import_orchestrator.py apps/integrations/tests/test_handle_init_cleanup_race.py` -- expected: «would reformat 0 files», exit code 0.
- `docker compose --env-file .env -f docker/docker-compose.yml exec backend python -m flake8 apps/integrations/onec_exchange/views.py apps/integrations/onec_exchange/import_orchestrator.py apps/integrations/tests/test_handle_init_cleanup_race.py` -- expected: 0 нарушений, exit code 0.

**Manual checks (если доступна dev-среда с реальной 1С):**

- Запустить полный цикл обмена rests на ~16 сегментов; убедиться, что в логе нет `File not found` от Celery, в `ImportSession`-таблице нет FAILED-сессий из-за пропавших файлов, директории `/app/media/1c_import/rests/` остаются непустыми до завершения всех задач, затем чистятся post-import-хуком или следующим `mode=init` после исчезновения active `IN_PROGRESS`.

## Suggested Review Order

**Race-fix entry point — IN_PROGRESS state до Celery dispatch и marker**

- Design intent фикса: создаётся реально-активное состояние session ДО `.delay()` и `mark_complete()` — закрывает окно очереди Celery, на которое опирается guard в `handle_init`.
  [`import_orchestrator.py:432`](../../../backend/apps/integrations/onec_exchange/import_orchestrator.py#L432)

- Конкретное место `session.status = IN_PROGRESS` + save с `update_fields=["status", "report", "updated_at"]`.
  [`import_orchestrator.py:438`](../../../backend/apps/integrations/onec_exchange/import_orchestrator.py#L438)

**Guard в `handle_init` — DB-check ДО cleanup_session, узкий exception, race-skip без побочных эффектов**

- DB-check как первое действие внутри `if is_complete():` — почему порядок имеет значение (в комменте: `cleanup_session(force=True)` стирает marker).
  [`views.py:421`](../../../backend/apps/integrations/onec_exchange/views.py#L421)

- `except DatabaseError` (не `Exception`) — узкий handler сохраняет marker для retry в следующем init без маскировки посторонних исключений.
  [`views.py:431`](../../../backend/apps/integrations/onec_exchange/views.py#L431)

- Race-skip ветка: full bypass `cleanup_session/cleanup_import_dir/clear_complete`, marker остаётся, INFO-лог содержит и `active_sessions`, и `sessid`.
  [`views.py:438`](../../../backend/apps/integrations/onec_exchange/views.py#L438)

**Регрессионные тесты — 6 сценариев I/O Matrix**

- AC #1: тест проверяет ORDER, а не только финальное состояние — captures session.status в `side_effect` для `.delay()` и `mark_complete()`, обе точки видят IN_PROGRESS.
  [`test_handle_init_cleanup_race.py:178`](../../../backend/apps/integrations/tests/test_handle_init_cleanup_race.py#L178)

- DB-error: узкий patch только `ImportSession.objects.filter` (не весь manager) — не ломает ORM для signals/middleware.
  [`test_handle_init_cleanup_race.py:117`](../../../backend/apps/integrations/tests/test_handle_init_cleanup_race.py#L117)

- Race-skip: проверяет, что cleanup-блок ПОЛНОСТЬЮ пропущен (`assert_not_called` для всех трёх методов), marker сохраняется.
  [`test_handle_init_cleanup_race.py:61`](../../../backend/apps/integrations/tests/test_handle_init_cleanup_race.py#L61)
