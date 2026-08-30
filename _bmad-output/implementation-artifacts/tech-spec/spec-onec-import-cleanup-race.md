---
baseline_commit: 633e6213
title: 'Гонка cleanup в обмене 1С: точечное удаление и сериализация задач импорта'
type: 'bugfix'
created: '2026-08-26'
status: 'review'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/Story/onec-import-cleanup-race-and-followups.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `_cleanup_files` в `import_products_from_1c` удаляет XML по маске `glob("rests/rests*.xml")` из каталога обмена, общего для всех сессий. При параллельных задачах Celery (prefork ×4, 1С шлёт сегмент каждые ~6,5 с при обработке 7–8 с) задача сносит файлы соседей. Выгрузка 25.08.2026: 5 сессий `failed`, 6 из 16 сегментов остатков (~18 000 строк) не прочитаны никем, две сессии отчитались `completed` с нулём записей — тихая потеря данных.

**Approach:** Команда запоминает пути, которые она реально распарсила, и удаляет только их; `glob` как приём удаления исчезает. Параллельно `process_1c_import_task` берёт распределённый лок на каталог обмена через Redis (`cache.add`) и при занятом локе уходит в `retry`, а не работает одновременно. Пропавший файл перестаёт валить импорт целиком.

## Boundaries & Constraints

**Always:**
- Правки в `_dispatch_import` / `_dispatch_or_dryrun` — только аддитивные (добавить аргумент вызова). Сигнатуры самих методов и порядок «`session` → `IN_PROGRESS` **до** `delay()`» не менять: обе точки — `risk: CRITICAL`, 7 затронутых процессов обмена.
- Лок берётся и `retry` бросается **вне** внешнего `try/except Exception` задачи: `celery.exceptions.Retry` наследует `Exception`, и текущий обработчик пометил бы сессию `FAILED`.
- Лок освобождается в `finally` и только владельцем (сверка значения с `self.request.id`).
- TTL лока и параметры retry — из `settings`, не константами в коде.
- Тесты импорта — только на реальных XML из `data/import_1c/` (16 сегментов `rests_1_*.xml` уже лежат там). Синтетику не создавать.

**Ask First:**
- Если станет ясно, что сериализации через `cache.add` недостаточно и нужна изоляция каталога по сессиям — HALT. Изоляция вынесена в tech-debt п. 26 и в объём не входит.
- Любая правка `cleanup_import_dir` (`routing_service.py:187-225`) — `risk: CRITICAL`, 13 зависимостей, уже дважды чинился хотфиксами.

**Never:**
- Не трогать `cleanup_import_dir`, guard в `tasks.py:245-266` и guard в `views.py:426-453` — они работают, дублировать их не нужно.
- Не менять сигнатуру `_collect_xml_files` (`risk: MEDIUM`, 8 вызывающих).
- Не использовать `FileLock` из `file_service.py:34`: `LOCK_TIMEOUT_SECONDS = 30` мал для полного импорта, stale-локи не снимаются.
- Не переиспользовать параметр `zip_filename` для передачи имени файла: он включает ветку `file_service.unpack_zip()`, которая сегодня мертва и резолвит `sessid` как `Path(data_dir).name` (= `1c_import`).
- Вне объёма (уже в `deferred-work.md`): `session.save(update_fields=…)` в `except` команды, путь `backup_db`, длина `size_value`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Точечный cleanup | Команда распарсила `rests_1_1.xml`; к моменту cleanup в `rests/` появился чужой `rests_1_2.xml` | Удалён только `rests_1_1.xml`; `rests_1_2.xml` цел | N/A |
| Лок свободен | `process_1c_import_task` первая на каталоге | `cache.add` → True, импорт идёт, лок снят в `finally` | N/A |
| Лок занят | Вторая задача на том же каталоге | `self.retry(countdown=…)`; сессия остаётся `IN_PROGRESS`, `report` не засоряется (запись только при `self.request.retries == 0`) | `MaxRetriesExceededError` → сессия `FAILED` с внятным текстом |
| Воркер упал с локом | Лок в Redis, владелец мёртв | Лок истекает по TTL, обмен разблокируется сам | N/A |
| Файл исчез, часть обработана | Список из 3 файлов, 1 исчез до парсинга | 2 файла обработаны, сессия `COMPLETED`, в `report` строка о пропущенном файле | `FileNotFoundError` → WARNING, цикл продолжается |
| Файлы исчезли все | Список непустой, распарсено 0 | Сессия `FAILED` с перечнем пропавших файлов | Не `COMPLETED` с нулём записей |
| Файлов типа нет изначально | `_collect_xml_files` вернул `[]` | Текущее поведение: WARNING «Файлы не найдены», статус не меняется | N/A |
| `file_type` сегмента | 1С прислала `rests_1_16_….xml` в `mode=import` | В задаче `detected_file_type == "rests"`; в `report` нет строк «Начало импорта категорий/брендов/товаров» | N/A |
| `mode=complete` | Оркестратор создан как `ImportOrchestratorService(sessid, "complete")` | `detect_file_type("complete")` → `"all"`, поведение прежнее | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/products/management/commands/import_products_from_1c.py` — `_cleanup_files` (:537, корень дефекта), `_collect_xml_files` (:654, не менять), `_import_variant_stocks` (:508), `handle` (:150-330), вызов cleanup (:317).
- `backend/apps/products/tasks.py` — `process_1c_import_task` (:18), блок `detected_file_type` (:196-206), финализация сессии (:238-244), post-import cleanup с рабочим guard'ом (:245-266, не трогать), внешний `except Exception` (:275).
- `backend/apps/integrations/onec_exchange/import_orchestrator.py` — `_dispatch_import` (:287, `delay()` на :324), `_detect_file_type` (:329), `_dispatch_or_dryrun` (:425, `delay()` на :456), `self.filename` (:45).
- `backend/apps/integrations/onec_exchange/views.py` — `:272` (`filename` от 1С), `:297` (`"complete"`).
- `backend/apps/products/services/parser.py` — `_validate_file` (:105-113), источник `FileNotFoundError`.
- `backend/freesport/settings/base.py` — `CACHES` (:232, Redis), место для новых настроек лока.
- `data/import_1c/rests/` — 16 реальных сегментов для регрессионного теста.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/products/tests/test_import_cleanup_race.py` — **создать первым**, прогнать на текущем `develop` и убедиться, что тесты **красные**; покрыть все строки матрицы I/O. Тест, который зелёный до правок, ничего не ловит.
- [x] `backend/apps/integrations/onec_exchange/file_type_detection.py` — новый модуль с единственной функцией `detect_file_type(filename: str | None) -> str`; логика — объединение двух текущих копий (`tasks.py:196-206` знает префикс `propertiesgoods`, `_detect_file_type` — нет; сохранить оба).
- [x] `backend/apps/integrations/onec_exchange/import_orchestrator.py` — `_detect_file_type` делегирует в новый модуль; оба `delay()` получают имя файла **новым именованным аргументом** `source_filename=self.filename`. Сигнатуры методов не менять.
- [x] `backend/apps/products/tasks.py` — добавить параметр `source_filename: str | None = None`; `detected_file_type = detect_file_type(source_filename or zip_filename)`; **в начале функции, до `try`**, взять лок `cache.add(f"onec:import:lock:{effective_data_dir}", self.request.id, ONEC_IMPORT_LOCK_TTL)`, при неудаче — `self.retry(...)`; освобождение — в `finally` с проверкой владельца.
- [x] `backend/freesport/settings/base.py` — `ONEC_IMPORT_LOCK_TTL` (по умолчанию 1800 с — переживает полный импорт каталога), `ONEC_IMPORT_LOCK_RETRY_COUNTDOWN` (10 с), `ONEC_IMPORT_LOCK_MAX_RETRIES` (180). Все через `config()`.
- [x] `backend/apps/products/management/commands/import_products_from_1c.py` — накапливать `self._processed_files` (путь добавляется **после** успешного парсинга, не после сбора) и `self._missing_files`; парсинг каждого файла в шагах импорта обернуть так, чтобы `FileNotFoundError` пропускал файл; `_cleanup_files` принимает список обработанных путей и удаляет через `Path(p).unlink(missing_ok=True)` — все `xml_patterns`/`glob` удалить; очистку `import_files` (:583-608) оставить по каталогу; перед `finalize_session` выбрать статус по правилу из матрицы.
- [x] `docs/integrations/1c/import-process.md` — зафиксировать лок каталога обмена и точечный cleanup как контракт.

**Acceptance Criteria:**
- Given прогон имитирует 8 последовательных сессий с наложением (файл соседа появляется до cleanup предыдущей), when прогон завершён, then ни одна сессия не `failed` и сумма обработанных записей равна сумме по всем 8 файлам — ни один сегмент не потерян.
- Given воркер поднят с `--concurrency=4`, when несколько задач претендуют на один каталог, then одновременно исполняется ровно одна; механизм не зависит от значения `--concurrency`.
- Given правки выкачены на прод и запущена повторная выгрузка только остатков, when выгрузка завершилась, then в `import_sessions` за окно нет `failed`, число строк «записей остатков» в логах равно числу отправленных 1С сегментов, а `count(*) FILTER (WHERE last_sync_at >= <начало>)` по `product_variants` покрывает активную номенклатуру.
- Given существующие тесты обмена, when прогон завершён, then `test_handle_init_cleanup_race.py`, `test_import_orchestration_tasks.py`, `integration/test_import_orchestration.py` и `management/commands/test_import_products_fix.py` зелёные.

## Spec Change Log

- 2026-08-26 — **поправка контракта решением Alex (ревью).** Строка матрицы «Файлов
  типа нет изначально → успех с предупреждением» действует **только когда конкретного
  файла не обещали**: `mode=complete` и ручной общий импорт. Если `detect_file_type`
  дал конкретный тип, имя файла доезжает до команды (`--source-filename`), и её
  отсутствие в каталоге к моменту `_collect_xml_files` — это `FAILED`, а не тихий
  успех. Frozen-блок оставлен как есть: он фиксирует изначально согласованный контракт,
  а эта запись — его renegotiation.

- 2026-08-26 — реализация: все Execution-пункты выполнены, статус `draft` → `review`.
  Тест `test_import_cleanup_race.py` подтверждён красным до правок (5 падений на гонке)
  и зелёным после (30 passed). Регрессии обмена 1С — 70 passed + 1 skipped.
  Полный backend-прогон: 3081 passed, 0 failed, покрытие 79 %. Сам контракт не менялся.
  Два существующих ассерта на точную сигнатуру `delay()` обновлены до нового контракта
  (`test_import_orchestration.py`, `tests/integration/test_onec_import.py`).

## Design Notes

**Точка внедрения для регрессионного теста.** В `handle()` (:314-317) `finalize_session` вызывается непосредственно перед `_cleanup_files`. Патч на `VariantImportProcessor.finalize_session`, который подкладывает в `<dir>/rests/` следующий реальный сегмент, честно воспроизводит «сосед положил файл между сбором списка и cleanup» без потоков и без Celery-конкурентности.

**Почему лок в задаче, а не в команде.** Команду вызывают и вручную (навык `import-1c`), и из тестов; лок в `process_1c_import_task` покрывает ровно тот путь, где есть параллелизм, и не мешает ручным прогонам.

**Почему `retry`, а не блокирующее ожидание.** Воркер prefork на 4 процесса: блокировка съедает слот и при 16 сегментах приводит к дедлоку пула. `retry` возвращает задачу в брокер.

**Освобождение лока.** `cache.get(key) == self.request.id` перед `cache.delete(key)` — гонка «TTL истёк, ключ перезахвачен, старый владелец удаляет чужой лок» остаётся теоретически возможной, но требует импорта дольше TTL; при 1800 с это принимаемый риск. Отметить комментарием в коде.

**Порядок файлов лексикографический**, не числовой: `rests_1_10…` идёт раньше `rests_1_9…`. На порядковые номера сегментов не закладываться.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs apps/products/tests/test_import_cleanup_race.py` — ожидается: **красный до правок**, зелёный после.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest apps/products/tests/test_import_orchestration_tasks.py apps/integrations/tests/test_handle_init_cleanup_race.py apps/products/tests/integration/test_import_orchestration.py apps/products/tests/management/commands/test_import_products_fix.py` — ожидается: без регрессий.
- `npx gitnexus detect-changes --scope all` — ожидается: затронуты только символы из Code Map.
- Backend-линт (Black + Flake8, навык `backend-lint`) — ожидается: чисто.

**Manual checks (if no CLI):**
- В логах прогона регрессионного теста строка `✅ Удалено XML файлов: N` — `N` равно числу файлов, распарсенных этой командой, и никогда не больше.
- Прод после выката (AC9): SQL по `import_sessions` и `product_variants` из раздела «Выкат и восстановление данных» исходной стори; после пересборки backend обязателен `restart nginx`.
