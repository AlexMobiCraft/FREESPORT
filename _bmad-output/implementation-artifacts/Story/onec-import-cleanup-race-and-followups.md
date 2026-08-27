---
baseline_commit: 2d6b1ac9
---

# Story: Гонка cleanup в обмене 1С — тихая потеря данных импорта

Status: review

> 🔴 **Дефект подтверждён на проде замерами, а не рассуждением.** Ручная выгрузка 25.08.2026 (17:03–17:29 UTC) дала 5 сессий в статусе `failed` с `File not found` и — что хуже — **6 из 16 сегментов остатков не были прочитаны никем**. Это ~18 000 строк остатков, которые 1С считает успешно переданными и повторять не будет.
> 🟠 **Главное здесь не падения, а тихая потеря.** Две сессии (62672, 62674) завершились со статусом `completed`, не обработав ни одной записи: их файл удалил сосед раньше, чем задача успела до него добраться, и команда честно написала «Файлы rests.xml не найдены». В отчёте — успех, в данных — дырка.
> 🟢 **Свежесть координат: все строки проверены чтением файлов на коммите `2d6b1ac9`.** Номера строк в Dev Notes соответствуют текущему `develop`.
> 🟢 **Blast radius основных правок LOW.** `npx gitnexus impact process_1c_import_task --direction upstream` → `risk: LOW`, `impactedCount: 0`. `npx gitnexus impact _cleanup_files --direction upstream` → `risk: LOW`, `impactedCount: 1` (единственный вызывающий — `Command.handle`).
> 🔴 **`cleanup_import_dir` трогать нельзя без крайней нужды.** `npx gitnexus impact cleanup_import_dir --direction upstream` → **`risk: CRITICAL`**, `impactedCount: 13`, 7 затронутых процессов (`handle_init`, `handle_complete`, `post`, …). Этот метод уже дважды правили хотфиксами (`ff0bbc0a`, `057afc41`), и его guard сейчас **работает** — в логах видно `Skipping import directory cleanup — other sessions are still IN_PROGRESS`. Виновник этой стори — **другой** cleanup, у которого guard'а нет вовсе.
> ⚠️ **`_bmad-output/race-condition-analysis.md` описывает ту же симптоматику, но устаревшую причину.** Тот анализ писался до Story 36.1 (пути ещё `/app/media/1c_import`) и обвинял `handle_init`. Его «Option A» реализована, `handle_init` закрыт guard'ом. Осталась вторая, не найденная тогда дыра — `_cleanup_files` в management-команде. Не переделывай работу по тому документу заново, читай его как исторический контекст.

## Story

As a **владелец каталога**,
I want **чтобы каждый файл, принятый от 1С, был прочитан ровно тем импортом, который его принял, и удалён только после того, как его данные попали в БД**,
so that **выгрузка из 1С не теряла остатки и цены молча, а статус сессии отражал реальный результат**.

## Что случилось на проде 25.08.2026 (фактура)

Выгрузка шла с 17:03 по 17:29 UTC, 110 сессий. Порядок блоков: справочники → `goods_1_1…20` → `offers_1_1…32` → `prices_1_1…16` → `rests_1_1…16`.

**Сегменты остатков — что реально применилось.** По строкам `• rests_….xml: записей остатков 3000` в логах celery:

| Сегменты | Итог |
|---|---|
| 1, 2, 3, 5, 7, 9, 10, 11, 13, 15 | прочитаны полностью (10 × 3000 = 30 000 строк) |
| **4, 6, 8, 12, 14, 16** | **не прочитаны никем — ≈18 000 строк потеряно** |

**Статусы сессий:**

| id | свой файл | статус | что в `error_message` |
|---|---|---|---|
| 62664 | `rests_1_4` | failed | `File not found: …/rests/rests_1_4_b5d4868f….xml` |
| 62666 | `rests_1_6` | failed | `File not found: …/rests/rests_1_6_f110cf97….xml` |
| 62668 | `rests_1_8` | failed | `File not found: …/rests/rests_1_8_192f208f….xml` |
| 62670 | `rests_1_10` | failed | `File not found: …/rests/rests_1_9_9ba34206….xml` ← **упала на чужом файле** |
| 62676 | `rests_1_16` | failed | `File not found: …/rests/rests_1_16_5e505506….xml` |
| 62672 | `rests_1_12` | **completed** | пусто — «Файлы rests.xml не найдены», ноль записей |
| 62674 | `rests_1_14` | **completed** | пусто — то же самое |

**Состояние БД после выгрузки** (замер 26.08.2026):

| Метрика | Значение |
|---|---|
| Вариантов всего | 16 609 |
| Обновлено в окне остатков (17:27:40+) | 10 000 |
| Не обновлено | 6 609 |
| Из них с ненулевым остатком на сайте | **963** (суммарно 204 003 ед.) |

Верхняя оценка риска — 963 варианта, торгующихся с остатком от предыдущего обмена. Регламентного обмена после 17:29 не было, само не исправится.

**Изображения не пострадали** — проверено отдельно: 11 204 файла в 20 архивах, обработано 11 184 (`images_copied=152`, `images_skipped=11032`, `images_errors=0`), новые файлы привязаны к `products.base_images`. `goods`-сегменты шли с интервалом ~50 сек при обработке ~7 сек, перекрытия не было. Гонка проявляется только там, где интервал 1С меньше времени обработки.

## Механика дефекта

Три условия, каждое по отдельности безобидное:

**1. Каталог обмена общий для всех сессий.** `routing_service.py:82-84`:

```python
# FIXED: Import directory should be shared/root, not session-isolated
self.import_dir = self.import_base          # /app/var/onec/1c_import — без sessid
```

**2. Задачи выполняются параллельно.** Прод: `celery -A freesport worker -l info` без `--concurrency` (`docker/docker-compose.prod.yml:184`), `nproc = 4` → prefork на 4 процесса. В логах чётко видно одновременную работу `ForkPoolWorker-2` и `ForkPoolWorker-4`. 1С отдаёт `rests` каждые ~6,5 сек, задача идёт 6,5–8 сек — перекрытие постоянное.

**3. Cleanup удаляет по маске, а не по списку обработанного.** `import_products_from_1c.py:537-580`:

```python
if file_type in ["all", "rests"]:
    xml_patterns.extend(["rests/rests*.xml"])   # ← маска: и свои, и чужие

for pattern in xml_patterns:
    for file_path in Path(data_dir).glob(pattern):
        file_path.unlink()
```

Прямое доказательство в логах: `✅ Удалено XML файлов: 2` в задаче, которая обрабатывала **один** сегмент.

**Итоговая последовательность** (на примере 62670):

```
17:28:44.2  1С кладёт rests_1_10 → создаётся сессия 62670 → dispatch
17:28:44.8  задача 62669 (rests_1_9) финализируется → _cleanup_files("rests")
            → glob("rests/rests*.xml") сносит и 1_9, и свежий 1_10
17:28:51    задача 62670: _collect_xml_files уже вернул список,
            parse_rests_xml → FileNotFoundError (parser.py:109)
            → CommandError → сессия failed
```

Если чужой cleanup успевает **до** `_collect_xml_files` — сессия завершается как `completed` с нулём записей (62672, 62674). Если **между** сбором списка и парсингом — `failed`. Оба исхода означают потерю данных, но только второй виден в отчёте.

**1С об этом не узнаёт.** `_dispatch_import` (`import_orchestrator.py:287-325`) возвращает `success` сразу после `delay()`, до выполнения задачи. Повторной отправки сегментов не будет.

## Сопутствующие дефекты, найденные при разборе

**A. `file_type` теряется при постановке в очередь.** `import_orchestrator.py:309` вычисляет `file_type` и пишет его в отчёт (`Celery import task dispatched (file_type=rests)`), но `delay()` на строке 324 вызывается **без** `zip_filename`:

```python
task_result = process_1c_import_task.delay(session.pk, str(self.import_dir))
```

В задаче `detected_file_type` остаётся `"all"` (`tasks.py:196-206`), потому что вычисляется он только из `zip_filename`. Последствия, все подтверждённые логами:
- каждый сегмент остатков запускает **полный** импорт каталога — в отчётах 62672/62674 видны шаги «Начало импорта категорий… брендов… товаров… вариантов… цен»;
- cleanup чистит **все** подпапки вместо одной `rests/`, расширяя окно гонки на goods/offers/prices;
- на каждой задаче зря дёргается `backup_db` (шаг только для `file_type == "all"`, `import_products_from_1c.py:190`);
- отчёт сессии врёт: пишет `file_type=rests`, выполняется `all`.

То же самое во второй точке диспатча — `_dispatch_or_dryrun` (`import_orchestrator.py:456`).

**B. Бэкап перед импортом не работает вообще.** В каждой задаче: `⚠️ Не удалось создать backup: [Errno 13] Permission denied: 'backend/backup_db'`. Причина — относительный путь по умолчанию в `backup_db.py:48` (`BACKUP_DIR`, default `"backend/backup_db"`), который в контейнере резолвится от `/app`. Ошибка проглатывается (`except` на `import_products_from_1c.py:195`), импорт идёт без бэкапа. Прод живёт так неизвестно сколько.

**C. `except` в команде затирает отчёт сессии.** `import_products_from_1c.py:322-327`:

```python
except Exception as e:
    session.status = ImportSession.ImportStatus.FAILED
    session.error_message = str(e)
    session.save()                    # ← без update_fields
```

`session` загружен в начале `handle()`, а прогресс всё это время писал в БД `VariantImportProcessor.log_progress`. Полный `save()` перезаписывает строку версией из памяти — весь прогресс упавшей сессии исчезает. Именно поэтому у пяти failed-сессий в отчёте всего 5 строк и не видно, что они успели сделать.

**D. Обновление содержимого картинки невозможно.** `variant_import.py:405-409`: пропуск идёт по факту существования файла с тем же именем в `media`, содержимое не сверяется. Перерисованное в 1С фото с тем же GUID никогда не доедет до сайта.

**E. 12 вариантов не сохранились: `value too long for type character varying(50)`.** Окно `offers` 17:20–17:24, сообщения `Error processing variant from offer` / `Error saving variant`. Единственное поле `varchar(50)` у `ProductVariant` — `size_value` (`models.py:858`). На проде `max(length(size_value)) = 49`, 9 записей длиннее 40 символов — поле упирается в лимит вплотную.

## Acceptance Criteria

**AC1 (ядро — cleanup только своего).**
**Given** команда `import_products_from_1c` завершила импорт успешно
**When** выполняется удаление обработанных файлов
**Then** удаляются **только** те файлы, которые эта команда собрала через `_collect_xml_files` и реально распарсила
**And** ни один файл, появившийся в каталоге после сбора списка, не удаляется
**And** удаление по маске `glob(...)` из `_cleanup_files` исчезает как приём

**AC2 (ядро — сериализация).**
**Given** 1С отдаёт файлы быстрее, чем идёт обработка (интервал 6,5 сек при обработке 7–8 сек)
**When** несколько `process_1c_import_task` претендуют на один каталог обмена
**Then** одновременно исполняется **ровно одна** задача импорта на каталог
**And** остальные ждут или переносятся (`retry`), но не начинают работу параллельно
**And** механизм сериализации не зависит от значения `--concurrency` воркера: увеличение числа процессов не должно возвращать гонку

**AC3 (устойчивость к исчезнувшему файлу).**
**Given** файл из собранного списка всё же исчез к моменту парсинга
**When** `parse_rests_xml` (или другой парсер) бросает `FileNotFoundError`
**Then** импорт **не** падает целиком: пропущенный файл логируется как предупреждение, остальные файлы списка обрабатываются
**And** сессия получает статус, отражающий частичный результат, а не `completed` с нулём записей

**AC4 (правдивый `file_type`).**
**Given** 1С прислала сегмент одного типа (`rests_1_16_….xml`)
**When** задача ставится в очередь
**Then** имя файла передаётся в `process_1c_import_task`, и `detected_file_type` совпадает с тем, что записано в отчёт сессии
**And** для сегмента остатков выполняется только шаг остатков — в отчёте нет строк «Начало импорта категорий/брендов/товаров»
**And** это работает в обеих точках диспатча: `_dispatch_import` и `_dispatch_or_dryrun`

**AC5 (отчёт не затирается).**
**Given** импорт упал исключением
**When** команда фиксирует ошибку в сессии
**Then** прогресс, записанный в `report` до падения, сохраняется
**And** сохранение идёт с явным `update_fields` либо после `refresh_from_db()`

**AC6 (бэкап либо работает, либо честно отключён).**
**Given** запускается импорт с `file_type == "all"`
**When** вызывается `backup_db`
**Then** бэкап либо создаётся в существующем и доступном на запись каталоге, либо шаг явно отключён настройкой
**And** молчаливое `Permission denied` в WARNING больше не является штатным поведением прода

**AC7 (`size_value` вмещает данные 1С).**
**Given** 1С прислала вариант с размером длиннее 50 символов
**When** вариант сохраняется
**Then** он сохраняется без `DataError`, либо значение усекается осознанно с предупреждением в лог
**And** решение зафиксировано миграцией или явной нормализацией на входе

**AC8 (регрессия закрыта тестом).**
**Given** тестовый прогон имитирует 8 последовательных сессий с интервалом меньше времени обработки
**When** прогон завершён
**Then** ни одна сессия не в статусе `failed`
**And** количество обработанных записей равно сумме по всем файлам — ни один сегмент не потерян
**And** тест падает на текущем коде `develop` (проверить это до внесения правок — иначе тест ничего не ловит)

**AC9 (проверка на проде после выката).**
**Given** правки выкачены и запущена повторная выгрузка остатков из 1С
**When** выгрузка завершилась
**Then** в `import_sessions` за окно выгрузки нет записей со статусом `failed`
**And** число сегментов в логах (`записей остатков`) равно числу отправленных 1С файлов
**And** `count(*) FILTER (WHERE last_sync_at >= <начало выгрузки>)` по `product_variants` покрывает всю активную номенклатуру

## Tasks / Subtasks

> **Объём сужен решением Alex 2026-08-26 (Split).** В работу взято ядро гонки — T1–T5;
> T6/T7/T8 отделены в `deferred-work.md` как независимо отгружаемые правки. Исполняемый
> контракт — `_bmad-output/implementation-artifacts/spec-onec-import-cleanup-race.md`.

- [x] **T1. Написать падающий тест до правок (AC8).**
  - [x] Прогнать его на `develop` и убедиться, что он **красный** — воспроизводит гонку.
  - [x] Разместить в `backend/apps/products/tests/test_import_orchestration_tasks.py` или соседнем файле рядом с существующими тестами задачи.
- [x] **T2. Точечный cleanup (AC1).**
  - [x] `_collect_xml_files` (`import_products_from_1c.py:654`) — сохранять собранный список в атрибут команды.
  - [x] Отмечать файл как обработанный **после** успешного парсинга, а не после сбора.
  - [x] `_cleanup_files` (`:537`) — принимать список обработанных путей, удалять через `Path(p).unlink(missing_ok=True)`.
  - [x] Очистку `import_files` (`:583-608`) оставить как есть — картинки чистятся по каталогу и гонки там не наблюдалось.
- [x] **T3. Сериализация импорта (AC2).**
  - [x] Взять лок на каталог обмена в `process_1c_import_task` (`tasks.py:19`) — Redis через `django.core.cache` (`cache.add(key, value, timeout)` = атомарный `SETNX`, Redis уже подключён: `settings/base.py:232`, `settings/production.py:61`).
  - [x] При неудачном захвате — `self.retry(countdown=…, max_retries=…)`, а не блокирующее ожидание: воркер prefork на 4 процесса, блокировка займёт слот.
  - [x] TTL лока должен переживать самый долгий импорт (полный каталог — минуты), но истекать сам, чтобы упавший воркер не заблокировал обмен навсегда.
  - [x] **Не использовать `FileLock` из `file_service.py:34`** как есть: `LOCK_TIMEOUT_SECONDS = 30` мал для полного импорта, а stale-локи он не снимает — упавший процесс оставит `.lock` навсегда.
- [x] **T4. Устойчивость к исчезнувшему файлу (AC3).**
  - [x] Обернуть парсинг каждого файла в `_import_variant_stocks` (`:508`) и в аналогичных шагах так, чтобы `FileNotFoundError` пропускал файл, а не валил команду.
- [x] **T5. Передача `file_type` (AC4).**
  - [x] `import_orchestrator.py:324` и `:456` — передавать `self.filename` третьим аргументом в `delay()`.
  - [x] Сверить, что `_detect_file_type` (`:329`) и `detected_file_type` (`tasks.py:196`) дают одинаковый результат на одинаковом имени — сейчас это две независимые копии логики; свести к одной.
  - [x] Проверить, что для `mode=complete` (где имени файла нет) поведение остаётся `all`.
- [~] **T6. Отчёт (AC5).** Отделено в `deferred-work.md` (Split 2026-08-26) — независимая правка на одну строку, к механике гонки отношения не имеет.
- [~] **T7. Бэкап (AC6).** Отделено в `deferred-work.md` (Split 2026-08-26) — деплой-вопрос: абсолютный путь из настроек и права каталога в образе.
- [~] **T8. `size_value` (AC7).** Отделено в `deferred-work.md` (Split 2026-08-26) — требует отдельной миграции схемы, ревьюится независимо.
- [x] **T9. Проверка на проде (AC9).** Выполнена на полномасштабной выгрузке 2026-08-27 07:43–08:07 UTC: 130 файлов, 172 сессии, **все `completed`**, 0 `failed`, 0 зависших, 0 непрочитанных обещаний, каталог обмена пуст. 63 сессии прошли через ожидание лока, guard сработал 6 раз.

### Review Findings

- [x] [Review][Patch] Для конкретного `source_filename` отсутствие ожидаемого сегмента до `_collect_xml_files` должно переводить сессию в `FAILED`; успех с пустым списком сохраняется только для `mode=complete` и ручного общего импорта. Решение Alex 2026-08-26. [`backend/apps/products/management/commands/import_products_from_1c.py:345-357,572-576`, `backend/apps/products/tasks.py:282-314`]
- [x] [Review][Patch] Точечный cleanup проверяет только путь и может удалить новый файл, подменивший распарсенный файл с тем же именем [`backend/apps/products/management/commands/import_products_from_1c.py:612-618`]
- [x] [Review][Patch] Ошибка публикации `self.retry()` в брокер, отличная от `MaxRetriesExceededError`, оставляет сессию в `IN_PROGRESS` [`backend/apps/products/tasks.py:121-133`]
- [x] [Review][Patch] AC2 отмечен выполненным без конкурентного прогона двух задач и проверки единственного входа в импорт [`backend/apps/products/tests/test_import_cleanup_race.py:335-426`]
- [x] [Review][Patch] Основной AC8-тест создаёт восемь копий одного fixture вместо обязательных реальных сегментов из `data/import_1c/` [`backend/apps/products/tests/test_import_cleanup_race.py:39-65,207-271`]
- [x] [Review][Defer] Post-import cleanup имеет TOCTOU между проверкой активных сессий и рекурсивным удалением общего каталога [`backend/apps/products/tasks.py:325-344`] — deferred, pre-existing
- [x] [Review][Defer] Каталожная очистка `goods/offers/import_files` может удалить изображения уже ожидающей сессии, поскольку HTTP-upload не участвует в Redis-локе [`backend/apps/products/management/commands/import_products_from_1c.py:624-652`] — deferred, pre-existing
- [x] [Review][Patch] Задача конкретного сегмента собирает, обрабатывает и удаляет все уже ожидающие сегменты того же типа; их собственные задачи затем завершаются `FAILED`, поэтому AC8 не воспроизводит реальную очередь с накопившимся backlog [`backend/apps/products/management/commands/import_products_from_1c.py:784-833`, `backend/apps/products/tests/test_import_cleanup_race.py:371-409`]
- [x] [Review][Patch] Наличие любого `contragents*.xml` полностью обходит импорт обещанного товарного сегмента: задача вызывает `import_customers_from_1c`, после чего помечает сессию сегмента успешной [`backend/apps/products/tasks.py:295-332`]
- [x] [Review][Patch] Ошибка Redis во время первичного `cache.add` возникает вне обработчиков, оставляя сессию `IN_PROGRESS` до stale-cleanup, хотя отказ публикации `retry` уже переводит её в `FAILED` [`backend/apps/products/tasks.py:94-99`]
- [x] [Review][Patch] Связать `import_files.zip` с конкретным goods XML: архив сейчас определяется как `goods`, но не считается обещанием, поэтому задача запускает несужаемый импорт и может забрать backlog соседних `goods*.xml`. Решение Alex: сохранить строгий per-session контракт через явную связь image ZIP → owning goods segment; до реализации нельзя позволять задаче архива собирать чужие XML. [`backend/apps/products/tasks.py:312-365`, `backend/apps/products/management/commands/import_products_from_1c.py:108-144,523-555`]
- [x] [Review][Patch] Ветка содержит несвязанный откат story 41.5: удаляются security-тесты и nginx snippets, ослабляются заголовки Next/nginx; перед merge нужно восстановить эти файлы или перебазировать ветку на актуальный `develop` [`frontend/next.config.ts:98-139`, `docker/nginx/conf.d/default.conf`, `backend/tests/unit/test_nginx_security_headers.py`]
- [x] [Review][Patch] Cleanup fail-open при отсутствии отпечатка: если `os.stat()` вернул `None`, но парсер затем успешно открыл файл, путь попадает в `_processed_files` без signature и безусловно удаляется; подмена до cleanup снова может удалить файл соседа. При неизвестном отпечатке удаление должно пропускаться [`backend/apps/products/management/commands/import_products_from_1c.py:73-106,731-746`]
- [x] [Prod][Patch] `mode=complete` забирал сегменты, обещанные ещё не отработавшим задачам: 48 из 48 объяснённых `failed` прод-прогона AC9 27.08.2026. Прогон без обещания уступает дорогу активным сессиям [`backend/apps/products/tasks.py`]
- [x] [Review][Patch] Case-insensitive сужение может выбрать несколько физических файлов как один обещанный сегмент: `rests_….xml` и `Rests_….xml` собираются разными glob-паттернами, после чего оба проходят сравнение через `.lower()`; одна задача обработает и удалит оба, а вторая завершится `FAILED`. При нескольких совпадениях команда должна завершаться явной ошибкой [`backend/apps/products/management/commands/import_products_from_1c.py:108-144,822-871`]

## Dev Notes

### Карта координат (коммит `2d6b1ac9`)

| Файл | Строки | Что там |
|---|---|---|
| `backend/apps/products/management/commands/import_products_from_1c.py` | 537-580 | `_cleanup_files` — удаление по маске, **корень дефекта** |
| | 654-703 | `_collect_xml_files` — сбор списка, `sorted(p.glob(...))` |
| | 508-535 | `_import_variant_stocks` — парсинг без защиты от исчезнувшего файла |
| | 190-196 | шаг `backup_db`, ошибка проглатывается |
| | 322-327 | `except` с затирающим `session.save()` |
| `backend/apps/products/services/parser.py` | 105-113 | `_validate_file` → `FileNotFoundError` |
| `backend/apps/products/tasks.py` | 196-206 | `detected_file_type` — вычисляется только из `zip_filename` |
| | 219, 234 | `call_command(...)` |
| | 245-266 | post-import cleanup с guard'ом по `IN_PROGRESS` (этот работает) |
| `backend/apps/integrations/onec_exchange/import_orchestrator.py` | 287-325 | `_dispatch_import`, `delay()` без имени файла |
| | 425-468 | `_dispatch_or_dryrun`, то же самое |
| `backend/apps/integrations/onec_exchange/routing_service.py` | 82-84 | общий `import_dir` без sessid |
| | 187-225 | `cleanup_import_dir` — **CRITICAL, не трогать** |
| `backend/apps/integrations/onec_exchange/views.py` | 407-458 | `handle_init` с рабочим guard'ом |
| `backend/apps/integrations/onec_exchange/file_service.py` | 34-105 | `FileLock` — не подходит как есть, см. T3 |
| `backend/apps/products/services/variant_import.py` | 340, 362-420 | пороги и логика пропуска изображений |
| `backend/apps/products/models.py` | 858 | `size_value`, `max_length=50` |
| `backend/apps/products/management/commands/backup_db.py` | 48 | `BACKUP_DIR` с относительным путём |

### Грабли

**Общий каталог — не баг, а осознанное решение.** Комментарий на `routing_service.py:81-83` объясняет: парсер ждёт файлы в `<import_dir>/goods`, а не `<import_dir>/<sessid>/goods`. Изоляция по сессиям потребовала бы переработки `_collect_xml_files` и всех путей команды — это отдельная большая работа, и в эту стори она **не входит**. Сериализация + точечный cleanup закрывают дефект без смены раскладки.

**Guard по `IN_PROGRESS` уже есть и работает — не дублируй его.** `tasks.py:245-266` и `views.py:426-453` корректно пропускают cleanup, когда живы другие сессии. Проблема ровно в том, что `_cleanup_files` в команде о них не знает вообще.

**Сессия переводится в `IN_PROGRESS` до `delay()`** (`import_orchestrator.py:317-321` и `:445-451`) — это часть предыдущего race-fix, и она нужна. Не откатывай.

**Повторный запуск задачи на одном каталоге идемпотентен по картинкам, но не по остаткам.** Остатки суммируются в `_stock_buffer` **в пределах процесса** (`variant_import.py:1181-1187`): повторная обработка того же файла в новом процессе перезапишет `stock_quantity`, а не удвоит. Но если сегментация 1С разрезала строки одного товара между файлами, суммирование по складам между сегментами теряется. Это отдельный вопрос — в эту стори не входит, но при правках `_import_variant_stocks` держи в голове.

**Порядок файлов лексикографический**, не числовой: `rests_1_10…` идёт раньше `rests_1_9…`. Не закладывайся на порядковые номера сегментов.

**MIN_IMAGE_SIZE_BYTES = 100 КБ** (`variant_import.py:340`) с fallback 8 КБ: 1С шлёт превью и полноразмер одного фото, берётся крупная версия. Счётчик `images_skipped` смешивает «уже существует» и «слишком мелкая» — при отладке картинок это сбивает с толку.

### Тестирование

Тесты только через Docker с PostgreSQL:

```bash
cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs apps/products/tests/test_import_orchestration_tasks.py
```

`--env-file` тестовому compose не передаётся, `run --rm` вместо `exec` — см. CLAUDE.md.

Существующие тесты, которые нельзя сломать:

| Файл | Что покрывает |
|---|---|
| `backend/apps/integrations/tests/test_handle_init_cleanup_race.py` | guard `handle_init`, 6 тестов, включая `test_session_marked_in_progress_before_dispatch_and_marker` |
| `backend/apps/products/tests/test_import_orchestration_tasks.py` | `process_1c_import_task`: успех, падение, `CommandError`, таймаут, распаковка zip, резолв `data_dir` |
| `backend/apps/products/tests/integration/test_import_orchestration.py` | сквозной прогон команды |
| `backend/apps/products/tests/management/commands/test_import_products_fix.py` | поведение команды импорта |

Для тестов импорта использовать **реальные XML** из `data/import_1c/` — синтетику не создавать (CLAUDE.md, раздел «Интеграция с 1С»). Каталог `data/` под широким правилом `.gitignore`: новые файлы туда — только через `git add -f`.

### Выкат и восстановление данных

**Деплой на прод ручной** — CI-шаг «Deploy to Production» всегда skipped. Выкат по SSH, `root@5.35.124.149`, проект в `/home/freesport/freesport`, конфиг `docker/docker-compose.prod.yml` c `--env-file /home/freesport/freesport/.env.prod`. После пересборки backend **обязателен `restart nginx`**: он держит старый IP апстрима и весь внешний API уходит в 502.

**Данные за 25.08 восстанавливаются только повторной выгрузкой остатков из 1С** — файлы удалены, `/app/var/onec/1c_import/rests/` пуст.

Порядок:
1. Выкатить правки, перезапустить `backend` и `celery`, `restart nginx`.
2. Запустить из 1С выгрузку **только остатков**.
3. Проверить по AC9: `failed`-сессий нет, число сегментов в логах равно отправленному, `last_sync_at` покрывает номенклатуру.

Если выкат откладывается, а остатки нужны сегодня — временно поднять воркер с `--concurrency=1` (`docker/docker-compose.prod.yml:184`). Это лечит симптом на время одной выгрузки и не заменяет правки.

Полезные запросы (навык `production-database`):

```sql
-- сессии за окно выгрузки
SELECT id, status, to_char(created_at,'HH24:MI:SS') AS created,
       left(coalesce(error_message,''),100) AS err
FROM import_sessions WHERE created_at > now() - interval '1 day' ORDER BY id DESC;

-- покрытие остатков
SELECT count(*) FILTER (WHERE last_sync_at >= '<начало выгрузки>') AS synced,
       count(*) AS total FROM product_variants;
```

## Definition of Done

- [x] AC1–AC4 и AC8 выполнены, тест из T1 зелёный (красный до правок), остальные тесты импорта не сломаны. AC5–AC7 отделены в `deferred-work.md` (Split 2026-08-26).
- [x] Все замечания ревью закрыты правками и тестами: 5 items в итерации 1.1 + 3 items в итерации 1.2 (2026-08-26) + 4 items в итерации 1.3 (2026-08-27). Два пункта `[Review][Defer]` осознанно отложены как pre-existing.
- [x] `npx gitnexus detect-changes --scope all` — затронуты только ожидаемые символы (итерация 1.3: 8 файлов, 40 символов, 16 процессов, risk `critical`. Critical даёт `_dispatch_import`; по `git diff -U0` правки в оркестраторе строго аддитивные — новое поле в `__init__`, накопление имён в `_route_unpacked_files`, один аргумент в `delay()` и новый `_promised_names`. Тела `execute`, `_detect_file_type`, `finalize_batch` не менялись и попали в список из-за сдвига строк).
- [x] Покрытие не ниже действующих порогов: локальный полный прогон `-m "not performance and not slow"` — **79 %** (TOTAL 14263 строки, 2932 не покрыто) при пороге CI 73–75. Итерация 1.3 (2026-08-27, 31 мин 28 с): 3118 passed, 75 skipped, 35 deselected, 15 subtests passed, 0 failed.
- [x] AC9 проверен на проде после реальной выгрузки, результат записан в Dev Agent Record. Первый прогон (223 сессии) вскрыл остаточный дефект `mode=complete`; после его исправления полная выгрузка (172 сессии, 130 файлов, 63 ожидания лока) дала **0 `failed`** и 0 непрочитанных обещаний.
- [~] Если T8 решён усечением, а не миграцией — остаток по `size_value` занесён в `tech-debt.md`. T8 не решался: отделён в `deferred-work.md`.

> Дефект **D** (обновление картинок) в объём стори **не входит** — он уже зафиксирован как долг: `tech-debt.md` п. 24. Там же п. 25 (модель `ProductImage` не заполняется, галерея пуста) и п. 26 (изоляция каталога обмена по сессиям как отложенный вариант). Заново заводить их не нужно.

## Change Log

| Дата | Версия | Описание | Автор |
|---|---|---|---|
| 2026-08-26 | 0.1 | Стори создана по разбору инцидента выгрузки 25.08.2026 | Claude |
| 2026-08-26 | 0.2 | Объём сужен до ядра гонки (T1-T5); T6/T7/T8 отделены в `deferred-work.md` | Alex |
| 2026-08-26 | 1.0 | Реализовано ядро: точечный cleanup, лок каталога обмена, устойчивость к исчезнувшему файлу, передача `source_filename`. 30 новых тестов, регрессии зелёные | Claude |
| 2026-08-26 | 1.1 | Закрыты замечания ревью — 5 items: строгий статус для обещанного сегмента, сверка отпечатка файла при cleanup, обработка ошибки публикации `retry`, конкурентный тест AC2, реальные разные сегменты в фикстурах AC8 | Claude |
| 2026-08-27 | 1.6 | AC9 закрыт полномасштабной выгрузкой: 172 сессии, 130 файлов, 63 ожидания лока, guard сработал 6 раз — **0 `failed`**, 0 зависших, 0 непрочитанных обещаний, каталог пуст | Claude |
| 2026-08-27 | 1.5 | AC9 проверен на проде после выката guard: 0 `failed` из 9 сессий, 0 зависших, 0 непрочитанных файлов, каталог пуст. Guard подтверждён на связке 64763/64764 — ровно той, что раньше давала `failed` | Claude |
| 2026-08-27 | 1.4 | Прод-прогон AC9 выявил остаточный дефект: `mode=complete` воровал сегменты из очереди (48 из 48 объяснённых падений). Прогон без обещания теперь уступает дорогу активным сессиям. Ядро стори подтверждено на проде: потери 963 → 6 вариантов, тихих `completed` с нулём нет | Claude |
| 2026-08-27 | 1.3 | Закрыты последние 4 замечания ревью: явная связь «архив → его XML-сегменты» (обещание передаёт оркестратор, распаковывающий архив в HTTP-обработчике), cleanup fail-closed при неснятом отпечатке, `CommandError` на неоднозначном имени сегмента, ветка перебазирована на `develop` (откат story 41.5 отсутствует) | Claude |
| 2026-08-26 | 1.2 | Закрыты оставшиеся 3 замечания ревью: прогон читает только обещанный файл (backlog соседей не съедается ни одним шагом), `contragents*.xml` не отменяет обещанный товарный сегмент, отказ Redis на захвате лока переводит сессию в `FAILED`. Попутно: `groups.xml` → тип `goods`, имя архива не считается обещанием | Claude |

## Dev Agent Record

### Context Reference

- Инцидент: ручная выгрузка 1С 25.08.2026, 17:03–17:29 UTC, прод `optisport.ru`.
- Исторический контекст: `_bmad-output/race-condition-analysis.md` (устаревшая причина, см. врезку выше), хотфиксы `ff0bbc0a`, `057afc41`.

### Agent Model Used

claude-opus-5 (Claude Code, скилл `bmad-dev-story`).

### Debug Log References

**Итерация 1.4 — прод-прогон AC9 2026-08-27 и остаточный дефект `mode=complete`.**

Правки итерации 1.3 выкачены на прод (`d1e963bc`, `main`), пересобраны backend +
frontend + celery, `restart nginx` выполнен. Внешние проверки: `/oferta`,
`/privacy-policy`, `/api/v1/banners/`, `/api/v1/news/`, `/blog`, каталог — 200;
точка обмена 1С отвечает 401 без авторизации. Условие воспроизведения дефекта
на месте: celery prefork, `concurrency: 4`.

**Замер прогона (223 сессии, 05:34–06:13 UTC):**

| Замер | Прогон 27.08 | Инцидент 25.08 |
|---|---|---|
| Вариантов обновлено в окне | 15 775 из 16 609 (95 %) | 10 000 из 16 609 (60 %) |
| С ненулевым остатком не обновлено | **6** | **963** |
| Тихих `completed` с нулём записей | **0** | 2 |
| Зависших `in_progress` | 0 | — |
| Каталог обмена после прогона | пуст | — |
| Сессий `failed` | 53 | 5 |

**Ядро стори подтверждено на проде: тихая потеря устранена.** Потери упали с 963
вариантов до 6, `completed` с нулём записей не было ни одного, зависших сессий нет.
Лок, сужение сбора и точечный cleanup отработали — в отчётах видно штатное
«Каталог обмена занят другим импортом, задача отложена».

**AC9 формально не выполнен: 53 `failed`.** Причина одна и измерена, а не
предположена: запрос «кто прочитал файл упавшей сессии» дал **48 из 48**
объяснённых случаев с потребителем `mode=complete`. Ни одного другого виновника.
Пять файлов (`groups_1_1`, `offers_1_1`, `prices_1_1`, два `rests_1_1` из поздних
мелких циклов) не прочитал никто.

Механика по отчётам сессий 64360/64361/64362 и 64368/64369/64370:

```
mode=import  goods_1_6 → сессия IN_PROGRESS → задача в очередь
             «Каталог обмена занят другим импортом» → retry 10 с    ← лок работает
mode=complete (через 2 с) → обещания нет → сбор НЕ сужается
             забирает каталог целиком вместе с goods_1_6, импортирует, удаляет
задача сегмента через 10 с → своего файла нет → FAILED
```

Это дыра в контракте, а не ошибка реализации: `mode=complete` был намеренно
выведен из-под сужения («complete значит забрать каталог целиком»). Для сценария
«файлы загрузили через `mode=file`, своих задач у них нет» это верно. Реальный
протокол этой 1С шлёт `mode=import` на каждый файл **и** `mode=complete` следом,
каждые пару секунд — и `complete` систематически воровал сегменты из очереди.
Тест `test_complete_mode_with_contragents_keeps_legacy_route` фиксировал прежнее
поведение как правильное; прод показал, что оно правильное только наполовину.

**RED до правки** (`pytest -k CompleteDoesNotSteal`): 2 падения —
`test_complete_skips_sweep_while_other_sessions_active`,
`test_unknown_file_type_also_defers_to_active_sessions`. Два теста класса были
зелёными: они фиксируют, что guard не трогает ни прогон со своим сегментом, ни
`complete` при отсутствии других активных сессий.

**Регрессия в собственных тестах — два теста конкурентности.**
`TestImportLockUnderConcurrency` дispatchил задачи без `source_filename`, то есть
несужаемыми, и после guard'а они стали уступать дорогу друг другу вместо входа в
импорт. Обоим прогонам добавлены имена сегментов — это и есть прод-сценарий,
который лок обязан сериализовать: на проде каждый сегмент приходит своим
`mode=import`. Смысл теста не ослаблен, а уточнён.

**GREEN после правки:** 110 passed + 1 skipped на связке импортных сьютов
(было 108). Black + Flake8 — чисто.

**Итерация ревью 2026-08-27 (третья, 4 items).**

Blast radius перед правками (`npx gitnexus impact … --direction upstream`, индекс на `41bf7a8`):

| Символ | risk | impacted |
|---|---|---|
| `_restrict_to_expected` | LOW | 10 |
| `_parse_or_skip` | MEDIUM | 8 |
| `_cleanup_files` | LOW | 1 |
| `_assert_expected_file_processed` | LOW | 1 |
| `process_1c_import_task` | LOW | 0 |

HIGH/CRITICAL нет. Сигнатуры `_parse_or_skip` и `_cleanup_files` не менялись.

**Замечание про откат story 41.5 закрыто перебазированием, а не правкой файлов.**
`git merge-base develop HEAD` = `460b3b6f` = `origin/develop@HEAD`, то есть ветка
лежит прямо поверх текущего `develop`. `git diff develop...HEAD` не содержит ни
`frontend/next.config.ts`, ни `docker/nginx/conf.d/default.conf`, ни
`backend/tests/unit/test_nginx_security_headers.py`. Story 41.5 (коммит `2d6b1ac9`,
он же прежний `baseline_commit` этой стори) в `develop` не влита и живёт на своей
ветке `feature/story-41-5-security-headers` — ревью сравнивало с ней как с базой.
Ничего не откатывалось; восстанавливать нечего.

**RED до правок** (сорсы откачены на `HEAD`, тесты новые;
`pytest -k "ArchiveOwnsOnlyItsOwnXml or UnknownSignature or AmbiguousPromisedSegment or CollectionIsLimitedToPromisedFile"`):
**7 падений** — `test_own_xml_from_archive_becomes_the_promise`,
`test_image_only_archive_does_not_start_catalog_import`,
`test_archive_run_does_not_eat_neighbour_segment`,
`test_file_without_signature_survives_cleanup`,
`test_foreign_family_is_not_collected`, `test_promised_file_is_collected`,
`test_case_variants_of_promised_name_raise`. Два теста выборки были зелёными —
они фиксируют неизменность прежнего поведения (ручной прогон, единственное совпадение).

**Находка по ходу правки, изменившая решение.** Первая версия связывала архив с
его XML **внутри задачи** — по тому, что она сама распаковала. Это работает только
для архивов, накопившихся в каталоге. Штатный `mode=import` распаковывает архив
**в HTTP-обработчике**: `ImportOrchestratorService.execute` зовёт `_unpack_zips`
(и удаляет `.zip`) до `_dispatch_import`, поэтому к старту задачи архива на диске
уже нет, `unpacked_xml_names` пуст — и задача уходила бы в «архив без XML», то есть
**не импортировала бы ничего**. Связь перенесена в оркестратор: `_route_unpacked_files`
копит `_unpacked_xml_names`, `_promised_names()` отдаёт `[<имя архива>, <его XML>…]`,
задача принимает `source_filename` как строку или список.

**GREEN после правок:** 66 тестов в файле регрессии (было 53 + 13 новых);
106 passed + 1 skipped на связке `test_import_cleanup_race.py` +
`test_import_orchestration_tasks.py` + `test_handle_init_cleanup_race.py` +
`integration/test_import_orchestration.py` +
`management/commands/test_import_products_fix.py` + `tests/integration/test_onec_import.py`.

**Регрессия в собственных тестах — два ассерта на форму контракта.**
`test_concrete_segment_reaches_command` и `test_promised_segment_wins_over_leftover_contragents`
сверяли `source_filename` со строкой; теперь команда получает список (одиночный
сегмент — список из одного имени). Это проверяемое изменение контракта, а не
подгонка теста под код. Тесты оркестратора (`delay(...)` со строкой) не менялись:
для не-архива `_promised_names()` возвращает прежнюю строку.

**Качество.** Black (`--line-length 120`) переформатировал командный файл, Flake8 — чисто.

**Итерация ревью 2026-08-26 (вторая, 3 items).**

Blast radius перед правками (`npx gitnexus impact … --direction upstream`, индекс на `0f98501`):

| Символ | risk | impacted |
|---|---|---|
| `_collect_xml_files` | MEDIUM | 9 |
| `detect_file_type` | LOW | 4 |
| `process_1c_import_task` | LOW | 0 |

HIGH/CRITICAL нет. Сигнатура `_collect_xml_files` не менялась — изменился только
возврат (список пропускается через новый `_restrict_to_expected`), и сужение
включается исключительно при переданном `--source-filename`. Все девять вызывающих
(шаги импорта и `_dry_run_import`) при ручном прогоне получают прежний список.

**RED до правок** (`pytest apps/products/tests/test_import_cleanup_race.py -k "Backlog or Contragents or LockBackendFailure or detect_file_type"`):
5 падений — `test_waiting_segments_are_left_untouched`,
`test_full_backlog_queue_loses_nothing_and_fails_nobody`,
`test_promised_segment_wins_over_leftover_contragents`,
`test_cache_failure_marks_session_failed`,
`test_detect_file_type[contragents_1_1_abc.xml-contragents]`.
Остальные 14 из выборки были зелёными с самого начала — они фиксируют, что правки
не забирают прежнее поведение (ручной импорт, `mode=complete`, маршрут контрагентов).

**GREEN после правок:** 49 passed в файле регрессии (было 41);
89 passed + 1 skipped на связке `test_import_cleanup_race.py` +
`test_import_orchestration_tasks.py` + `test_handle_init_cleanup_race.py` +
`integration/test_import_orchestration.py` +
`management/commands/test_import_products_fix.py` + `tests/integration/test_onec_import.py`.
Существующие тесты править не пришлось: сужение списка не срабатывает там, где
имя файла не передаётся, а маршрут контрагентов сохранён для `all`.

`npx gitnexus detect-changes --scope all`: 8 файлов, 10 символов, 5 процессов,
risk `medium`. Из символов по существу изменены `detect_file_type` и
`process_1c_import_task`; `Command`, `add_arguments`, `_dry_run_import`, `fn_lower`,
`holder`, `options` попали в список из-за сдвига строк (вставка `_restrict_to_expected`
и `try` вокруг `cache.add`). Потоки — `Handle_init → Detect_file_type`,
`Process_1c_import_task → Get_file_path`, три `Handle → *`; постороннего нет.
Файлы `AGENTS.md` и `CLAUDE.md` в списке — незакоммиченные изменения рабочей копии,
к этой итерации отношения не имеют.

**Полный backend-прогон после правок** (`-m "not performance and not slow" --cov=apps --cov=freesport`,
31 мин 48 с): **3109 passed, 75 skipped, 35 deselected, 15 subtests passed, 0 failed**;
покрытие **79 %** (TOTAL 14206 строк, 2954 не покрыто) при пороге CI 73 (без
`data_dependent`) / 75 (с ними). Существующие тесты не правились ни одного:
сужение сбора не срабатывает без переданного имени файла, а маршрут контрагентов
сохранён для `all`.

**Качество.** Black (`--line-length 120`, как в `backend/pyproject.toml`) — файлы
без изменений, Flake8 — чисто.

**Итерация ревью 2026-08-26.**

Blast radius перед правками (`npx gitnexus impact … --direction upstream`, индекс на `3f5bc8b`):

| Символ | risk | impacted |
|---|---|---|
| `_cleanup_files` | LOW | 1 |
| `process_1c_import_task` | LOW | 0 |
| `_parse_or_skip` | MEDIUM | 8 |
| `handle` / `add_arguments` | UNKNOWN | 0 |

HIGH/CRITICAL нет. Сигнатура `_parse_or_skip` не менялась — внутрь добавлен только
съём отпечатка файла, все 8 вызывающих (шаги импорта в том же файле) работают как прежде.

**RED до правок** (`pytest apps/products/tests/test_import_cleanup_race.py`): 9 падений —
`test_replaced_file_with_same_name_survives_cleanup`, четыре теста
`TestExpectedSegmentIsMandatory`, `test_concrete_segment_reaches_command`,
`test_eight_overlapping_sessions_lose_nothing`, `test_real_runtime_segments_lose_nothing`,
`test_retry_publish_failure_marks_session_failed`. `TestImportLockUnderConcurrency` был
зелёным с самого начала — и это правильно: замечание ревью касалось отсутствия проверки,
а не поломки лока.

**GREEN после правок:** 41 passed в файле регрессии; 81 passed + 1 skipped на связке
`test_import_cleanup_race.py` + `test_import_orchestration_tasks.py` +
`test_handle_init_cleanup_race.py` + `integration/test_import_orchestration.py` +
`management/commands/test_import_products_fix.py` + `tests/integration/test_onec_import.py`.

**Регрессия в существующем тесте — один ассерт на точные kwargs `call_command`.**
`integration/test_import_orchestration.py::test_process_1c_import_task_logic` сверял вызов
буквально; добавился `source_filename=None`. Обновлён до нового контракта — это
проверяемое изменение поведения, а не подгонка теста под код.

`npx gitnexus detect-changes --scope all`: 10 файлов, 18 символов, 8 процессов.
Все правки в командном файле — чистые вставки (`89 +`, ни одного `-`), поэтому
`_import_brands`, `_clear_existing_data`, `_print_stats`, `_collect_xml_files` и
локальные переменные попали в список только из-за сдвига строк; их тела не менялись.
Потоки — `Handle → *` и `Process_1c_import_task → Get_file_path`, всё из Code Map спеки.

**Полный backend-прогон после правок** (`-m "not performance and not slow" --cov=apps --cov=freesport`,
29 мин): **3093 passed, 75 skipped, 35 deselected, 0 failed**; покрытие **79 %**
(TOTAL 14186 строк, 2954 не покрыто) при пороге CI 73 (без `data_dependent`) / 75 (с ними).

**Грабли прогона (для протокола).** Первый полный прогон дал 292 failed и 1159 errors —
это был артефакт метода, а не кода: параллельно с ним запускались точечные `pytest` в том
же проекте `freesport-test`, и две сессии дрались за одну тестовую БД
(`psycopg2.errors.DeadlockDetected` на `TRUNCATE` в autouse-фикстуре очистки).
Повторный прогон в одиночку — зелёный. Вывод на будущее: `docker-compose.test.yml`
поднимает одну БД на проект, параллельные прогоны по нему невозможны.

**Качество.** Black применён, Flake8 — чисто. Mypy по изменённым файлам новых ошибок
не даёт (те же 8 предсуществующих в `staging.py`, `development.py`, `order_numbering.py`,
`variant_import.py`).

**Blast radius перед правками** (`npx gitnexus impact … --direction upstream`, индекс на `2d6b1ac`):

| Символ | risk | impacted |
|---|---|---|
| `_cleanup_files` | LOW | 1 |
| `process_1c_import_task` | LOW | 0 |
| `_detect_file_type` | LOW | 3 |
| `_import_variant_stocks` | LOW | 1 |
| `_dispatch_import` | **CRITICAL** | 4 |
| `_dispatch_or_dryrun` | **CRITICAL** | 4 |

Обе CRITICAL-точки правились строго аддитивно: добавлен один именованный аргумент
`source_filename=self.filename` в `delay()`. Сигнатуры методов и порядок
«`session` → `IN_PROGRESS` **до** `delay()`» не тронуты.

`npx gitnexus detect-changes --scope all`: 8 файлов, 51 символ, 10 процессов,
risk `high` — затронуты ровно символы и потоки из Code Map спеки
(`Handle_init → Mark_complete`, `Handle_init → _detect_file_type`,
`Handle_complete → Mark_complete`, `Handle → *`). Постороннего нет.
`finalize_batch` попал в список из-за сдвига строк — его тело не изменялось
(см. `git diff import_orchestrator.py`).

**RED до правок** (`pytest apps/products/tests/test_import_cleanup_race.py` на коде без фикса
команды): 5 падений — `test_neighbour_file_survives_cleanup`,
`test_cleanup_files_ignores_unparsed_neighbours`, `test_partial_loss_completes_and_reports`,
`test_eight_overlapping_sessions_lose_nothing`, `test_real_runtime_segments_lose_nothing`.
Тесты ловят именно гонку, а не отсутствие импортов: модули лока и `detect_file_type`
к моменту замера уже существовали.

**GREEN после правок:** 30 passed в новом файле; 70 passed + 1 skipped на связке
`tests/integration/test_onec_import.py` + `test_import_cleanup_race.py` +
`test_import_orchestration_tasks.py` + `test_handle_init_cleanup_race.py` +
`integration/test_import_orchestration.py` + `management/commands/test_import_products_fix.py`.

**Полный backend-прогон** (`-m "not performance and not slow" --cov=apps --cov=freesport`,
35 мин): **3081 passed, 75 skipped, 35 deselected, 0 failed**; покрытие **79 %**
(TOTAL 14146 строк, 2955 не покрыто) при пороге CI 73 (без `data_dependent`) / 75 (с ними).
Локальный прогон включает `data_dependent`-тесты импорта 1С, на раннере они скипаются —
порог калибруется по CI.

### Completion Notes List

**AC9 — полная выгрузка после выката guard (2026-08-27, 07:43–08:07 UTC).**

Полномасштабный прогон, тот самый, которого не хватало предыдущему замеру.
Точка отсчёта: сессия 64907. Прислано 130 файлов: `goods` 42, `offers` 32,
`prices` 29, `rests` 21, плюс блок справочников (`groups`, `priceLists`,
`propertiesGoods`, `propertiesOffers`, `storages`, `units`).

| Критерий AC9 | Результат |
|---|---|
| Сессий за окно | 172, **все `completed`** |
| Сессий `failed` | **0** |
| Зависших `in_progress` | **0** |
| Обещанных файлов не прочитано никем | **0** |
| Каталог обмена после прогона | пуст, включая корень (0 zip) |
| Вариантов синхронизировано в окне | 15 894 из 16 619 |
| Вариантов с остатком без свежей синхронизации | 6 (см. ниже — к обмену отношения не имеют) |

**Нагрузка была настоящей, а не формальной.** 63 сессии прошли через ожидание
лока («Каталог обмена занят другим импортом») — это ровно та конкуренция, что на
коде до guard'а давала 53 `failed` из 223 сессий. Guard сработал 6 раз: столько
`mode=complete` уступили дорогу активным сессиям вместо того, чтобы забрать их
файлы. Ни одного падения.

**Поправка к замеру итерации 1.5.** Шесть вариантов с остатком и несвежим
`last_sync_at` я тогда записал как след прогона до guard'а — это неверно. Их
`last_sync_at` датируется январём и июлем 2026 (id 4984, 4987, 5039 — 25.01.2026;
id 25917, 25918, 26010 — 08.07.2026), то есть 1С не присылает их месяцами. К гонке
cleanup они отношения не имеют и полной выгрузкой не закрываются. Пять файлов,
не прочитанных в прогоне 05:34–06:13, эта выгрузка перекрыла: непрочитанных
обещаний в ней ноль.

**Итог:** AC9 выполнен по всем трём критериям на полномасштабной выгрузке.
Ограничение предыдущего замера (9 сессий, дельта вместо полного прохода) снято.

**AC9 — проверка на проде после выката guard (2026-08-27, 07:05–07:07 UTC).**

Выкачен `b6f597fb`, пересобраны `backend` + `celery` + `celery-beat`, `restart nginx`.
Точка отсчёта: сессия 64758, `last_sync_at = 07:05:29`.

| Критерий AC9 | Результат |
|---|---|
| Сессий `failed` за окно | **0** из 9 |
| Зависших `in_progress` | **0** |
| Обещанных файлов не прочитано никем | **0** |
| Каталог обмена после прогона | пуст (все подпапки 0 файлов) |
| Вариантов с остатком без синхронизации > 24 ч | **6** из 2470 |
| Вариантов с остатком, не синхронизированных никогда | 0 |

**Прямое доказательство работы guard'а** — сессии 64763 и 64764:

```
64763  07:06:42  (complete)                  Импорт каталога пропущен   ← guard сработал
64764  07:06:44  rests_1_1_aff6f6fd….xml     ждал лок → COMPLETED       ← файл уцелел
```

Это ровно та связка, которая до фикса давала `failed`: сегмент в очереди за локом
и `complete` следом через две секунды. Сессии 64759 и 64761 также прошли через
ожидание лока и завершились успешно.

**Сравнение за 4 часа:** до выката guard — 72 `failed` из 556 сессий; после
выката — **0 из 9**.

**Ограничение замера, которое нужно держать в голове.** Прогон вышел маленький:
9 сессий за 95 секунд, 1С прислала дельту, а не полную выгрузку. Прогон на 223
сессиях, где дефект и проявился, повторён не был. Механика подтверждена на той
самой комбинации, что раньше ломалась, но подтверждение на полномасштабной
выгрузке усилило бы доказательство — стоит снять цифры на ближайшей полной.

**Остаточные 6 вариантов** — след прогона 05:34–06:13 на коде без guard'а: пять
файлов (`groups_1_1`, `offers_1_1`, `prices_1_1`, два `rests_1_1`) тогда не
прочитал никто. Ближайшая полная выгрузка их закроет; отдельных действий не
требуется.

**Итерация 1.4 (2026-08-27) — остаточный дефект, найденный прод-прогоном AC9.**

✅ Прогон без обещания уступает дорогу активным сессиям. `mode=complete` (а с ним
`units.xml`, `storages.xml` и прочие имена без распознанного типа) сгребает каталог
целиком, и на проде это систематически воровало сегменты, чьи задачи стояли в
очереди за локом: 48 из 48 объяснённых падений имели потребителем именно `complete`.
Теперь такой прогон **не запускает импорт каталога, пока живы другие сессии в
`IN_PROGRESS`** — их файлы заберут собственные задачи. Guard тот же, что уже стоит
на post-import cleanup и в `views.handle_init`, новый приём не вводится.

Прежнее поведение сохранено ровно там, где оно нужно: при отсутствии других
активных сессий `complete` забирает каталог как раньше, поэтому сценарий «файлы
загрузили через `mode=file`, своих задач у них нет» не ломается.

Проверка решения на конкретном прод-случае: в 05:55:17 сессия 64361 была
`IN_PROGRESS` (её переводят до `delay()` — часть прошлого race-fix), значит
`complete` пропустил бы сбор, а задача 64361 в 05:55:25 нашла бы свой файл и
отчиталась `completed`.

**Тесты итерации.** +4 к файлу регрессии (66 → 70): `TestCompleteDoesNotStealPromisedSegments`
— `complete` при живых сессиях не трогает каталог и пишет причину в отчёт;
`complete` без других активных сессий собирает как раньше (`file_type=all`,
`source_filename=None`); прогон со своим сегментом guard'ом не задет; `units.xml`
уступает дорогу так же, как `complete`.

**Итерация ревью 2026-08-27 (третья) — 4 items закрыто.**

✅ Resolved review finding [High]: у архива появился собственный сегмент, и чужие
он больше не трогает. Прежде обещанием считалось только имя XML, а имя архива —
нет; из этого следовало «обещания нет», а значит сбор не сужается, и задача
`import_files.zip` сгребала весь ожидающий backlog соседних `goods*.xml`,
обрабатывала и удаляла его, топя собственные задачи этих файлов в `FAILED`.
Связь установлена явно: **обещание архива — XML, который он принёс**.
Оркестратор, распаковывающий архив в HTTP-обработчике `mode=import`, копит имена
в `_unpacked_xml_names` и передаёт задаче `source_filename=[<архив>, <его XML>…]`
(`_promised_names`); архивы, накопившиеся в каталоге, распаковывает сама задача и
берёт имена оттуда. Тип сегмента для архива теперь следует за содержимым, а не за
именем (`rests_1_1_….xml` внутри → `file_type=rests`; разнотипный → `all` при
сохранённом сужении). Архив, не принёсший ни одного XML (только картинки либо он
уже распакован соседом), **не запускает импорт каталога вовсе**: своего сегмента
нет, чужие не его. Изображения при этом остаются в `goods/import_files/` — cleanup
команды не выполняется, тогда как раньше прогон архива их же и стирал.

**Побочный дефект, найденный здесь же (закрыт).** В копии маршрутизации внутри
задачи (`tasks.py`) не создавался родительский каталог для имени с путём внутри
архива (`import_files/photo.jpg`): `shutil.move` падал, картинка оставалась в корне
каталога обмена, где её не ищет ни один шаг импорта. В копии оркестратора
(`_route_unpacked_files`) эта строка была. Копии выровнены.

✅ Resolved review finding [Med]: cleanup стал fail-closed при неснятом отпечатке.
`_parse_or_skip` писал отпечаток в `_file_signatures` только когда `os.stat()`
удался; если он упал, а парсер файл затем всё же открыл, путь попадал в
`_processed_files` без отпечатка — и `_cleanup_files` удалял его безусловно
(`expected_signature is not None and …`). Подмена файла до cleanup снова сносила
файл соседа. Теперь отпечаток пишется всегда, включая `None` («снять не удалось» —
это факт, а не отсутствие записи), и при неизвестном отпечатке удаление
пропускается с предупреждением: файл уберёт `cleanup_import_dir`.

✅ Resolved review finding [Med]: неоднозначное имя сегмента останавливает импорт.
`_collect_xml_files` ищет регистронезависимо (`rests_*.xml`, `Rests_*.xml`), а
сравнение с обещанным именем идёт через `.lower()` — на регистрозависимой ФС оба
физических файла проходили как «наш сегмент». Один прогон прочитал и удалил бы оба,
второй ушёл бы в `FAILED`. `_restrict_to_expected` теперь группирует совпадения по
имени и при нескольких физических файлах на одно обещанное имя бросает
`CommandError` с перечнем: угадывание здесь означало бы удаление чужого файла.

✅ Resolved review finding [Med]: отката story 41.5 в ветке нет — она перебазирована
на `develop`. Проверено: `git merge-base develop HEAD` = `460b3b6f` = `origin/develop@HEAD`,
а `git diff develop...HEAD` не содержит `frontend/next.config.ts`,
`docker/nginx/conf.d/default.conf` и `backend/tests/unit/test_nginx_security_headers.py`.
Story 41.5 в `develop` не влита, живёт на `feature/story-41-5-security-headers`
(коммит `2d6b1ac9` — прежний `baseline_commit` этой стори), и ревью сравнивало с ней
как с базой. Восстанавливать нечего; база для PR — `develop`, как требует CLAUDE.md.

**Изменение контракта задачи.** `process_1c_import_task(source_filename=…)` принимает
строку или список; `--source-filename` команды стал повторяемым (`action="append"`),
а `Command._expected_filename` превратился в `_expected_filenames: set[str] | None`.
`None` по-прежнему значит «конкретных файлов не обещали» (ручной прогон,
`mode=complete`) — там сужение и строгая проверка выключены, поведение прежнее.

**Тесты итерации.** +13 к файлу регрессии (53 → 66):
`TestArchiveOwnsOnlyItsOwnXml` (пять тестов: XML из архива становится обещанием и
задаёт тип; архив только с картинками не запускает импорт и не трогает соседа;
список имён от оркестратора отрабатывается; список из одного имени архива читается
как «своих сегментов нет»; сквозной прогон архива не съедает соседний сегмент),
`TestUnknownSignatureIsNotDeleted`, `TestAmbiguousPromisedSegment` (два теста:
регистровые двойники → `CommandError`, единственное совпадение — как раньше),
плюс два теста оркестратора в `TestOrchestratorPassesFilename`.

**Итерация ревью 2026-08-26 (вторая) — 3 items закрыто.**

✅ Resolved review finding [High]: сегмент читает **только свой** файл. Лок
превратил параллельную гонку в очередь, но не убрал её следствие: пока задача
держит лок, 1С успевает положить в общий каталог следующие сегменты, и
`_collect_xml_files` забирал весь накопившийся backlog по маске `rests_*.xml`.
Прогон обрабатывал и удалял чужие файлы, а их собственные задачи затем падали
`FAILED` — «сегмент не найден». Данные в БД доезжали, но выгрузка отчитывалась
провалом, и AC8 («ни одна сессия не в статусе failed») нарушался на реальной
очереди. Новый `Command._restrict_to_expected` сужает собранный список до
обещанного имени на **всех** шагах прогона; пропущенные чужие файлы пишутся
предупреждением в отчёт. Ручной общий импорт и `mode=complete` имени не обещают —
там список не сужается, каталог забирается целиком, как раньше.

Первая версия правки сужала список только внутри «семейства» файлов (сбор
остатков — по префиксу `rests`, товаров — `goods`/`import`), и этого оказалось
мало: сегмент `offers_….xml` запускает ещё и шаги цен и остатков
(`file_type in ["all", "prices", "offers"]`), то есть съедал бы уже ожидающие
`prices_*`/`rests_*` — тот же backlog через другое семейство. На выгрузке
25.08.2026 это достижимо: 32 сегмента `offers` разбираются по очереди под локом,
а 1С в это время уже шлёт `prices`. Сужение распространено на все шаги;
справочники (`groups.xml`, `propertiesGoods.xml`, `priceLists.xml`) приходят
своими файлами и обрабатываются своими сессиями.

✅ Resolved review finding [High]: `contragents*.xml` больше не съедает
обещанный товарный сегмент. Задача выбирала маршрут по содержимому каталога:
нашла любой `contragents*.xml` → звала `import_customers_from_1c` и помечала
сессию успешной, даже если ей обещали `rests_1_12_….xml`. Файл контрагентов,
оставшийся от соседней сессии, таким образом молча уничтожал сегмент. Теперь
`detect_file_type` знает тип `contragents`, и маршрут выбирается по имени файла;
по содержимому каталога — только там, где имени не обещали (`mode=complete`,
ручной прогон), то есть прежнее поведение сохранено ровно в прежней области.

**Второй пробел того же класса (закрыт здесь же).** `groups.xml` не имел префикса
в `detect_file_type` и давал `all` — то есть каждая выгрузка справочника групп
запускала несужаемый полный проход по каталогу и сгребала весь ожидающий backlog.
Файл при этом команда читает (`_import_categories`), поэтому префикс `groups`
добавлен в группу `goods`. `units`, `storages`, `propertiesOffers` намеренно
оставлены в `all`: команда их не собирает вовсе, и обещание «этот файл обязан
быть прочитан» утопило бы такие сессии в `FAILED`. Ограничение отмечено
комментарием в `file_type_detection.py`.

**Побочный дефект, найденный при этой правке (закрыт здесь же).** Строгость,
введённая в итерации 1.1, обещанием считала любое имя, для которого
`detect_file_type` дал конкретный тип — включая имя архива:
`detect_file_type("import_files.zip")` → `goods`, а команда собирает XML и файла
с таким именем не найдёт никогда. Штатная выгрузка изображений архивом уходила бы
в `FAILED`. Теперь обещанием считается только имя, оканчивающееся на `.xml`.

✅ Resolved review finding [Med]: отказ бэкенда лока переводит сессию в `FAILED`.
`cache.add` вызывался вне обработчиков: при недоступном Redis задача падала, а
сессия висела `IN_PROGRESS` до `cleanup_stale_import_sessions` (порог 2 часа) —
хотя отказ публикации `retry` уже обрабатывался и давал `FAILED`. Теперь захват
обёрнут в `try/except`: импорт не запускается (работа без лока вернула бы
гонку — fail-closed сохранён), но сессия честно получает `FAILED` с текстом
ошибки. Чтение `holder` для лога тоже защищено — оно нужно только тексту
сообщения.

**Тесты итерации.** +12 к файлу регрессии (41 → 53):
`TestSegmentBacklogBelongsToItsOwnTask` (три теста: backlog из четырёх сегментов
не тронут; полная очередь из восьми сегментов, уже лежащих в каталоге, не теряет
ничего и никого не топит в `FAILED`; ручной прогон по-прежнему забирает всё),
`TestContragentsDoNotSwallowPromisedSegment` (три теста: обещанный сегмент
выигрывает у чужих контрагентов, файл контрагентов по-прежнему уходит в
`import_customers_from_1c`, `mode=complete` сохраняет прежний маршрут),
`TestLockBackendFailure` (падение `cache.add` → `FAILED`, `call_command` не
вызван), `TestCollectionIsLimitedToPromisedFile` (три теста на сужение сбора,
включая чужое семейство и неизменный ручной прогон),
`TestArchiveNameIsNotAPromise` (имя архива не передаётся как обещанный сегмент),
плюс кейсы `contragents_1_1_abc.xml → contragents`, `groups.xml → goods`,
`groups_1_1_abc.xml → goods`, `units.xml → all`, `storages.xml → all`
в параметризации `detect_file_type`.

Ключевое отличие нового AC8-теста от прежнего: раньше следующий сегмент
подкладывался в каталог на `finalize_session`, то есть **после** сбора списка —
такая расстановка backlog не воспроизводила. Теперь все восемь сегментов лежат
в каталоге **до** первого прогона, ровно как под локом на проде.

**Итерация ревью 2026-08-26 — 5 items закрыто.**

✅ Resolved review finding [High]: для конкретного `source_filename` отсутствие
ожидаемого сегмента переводит сессию в `FAILED`. Команда получила опцию
`--source-filename`; задача передаёт имя в `call_command` **только** когда
`detect_file_type` дал конкретный тип (`rests`/`goods`/`offers`/`prices`), для `all`
передаётся `None`. Новый `_assert_expected_file_processed` вызывается перед
`finalize_session` и бросает `CommandError` с указанием причины («не найден в каталоге
обмена» / «исчез из каталога обмена до парсинга»). Пустой каталог остаётся успехом
ровно там, где конкретного файла не обещали: `mode=complete` и ручной общий импорт.

✅ Resolved review finding [High]: точечный cleanup сверяет отпечаток файла, а не
путь. `_file_signature` снимает `(st_dev, st_ino, st_mtime_ns, st_size)` в момент
парсинга (в `_parse_or_skip`, до вызова парсера); `_cleanup_files` перед `unlink`
сверяет отпечаток заново и при расхождении пропускает файл с предупреждением —
под этим именем уже лежит чужой файл. Остаточное окно TOCTOU между `stat` и `unlink`
неустранимо без работы по дескриптору, но это доли миллисекунды вместо секунд обработки;
отмечено в docstring.

✅ Resolved review finding [Med]: ошибка публикации `self.retry()` больше не оставляет
сессию в `IN_PROGRESS`. Ветка `except Retry: raise` сохраняет штатный путь,
`MaxRetriesExceededError` обрабатывается как прежде, а любое другое исключение
(`kombu.exceptions.OperationalError` при недоступном брокере) логируется и переводит
сессию в `FAILED` с текстом ошибки. Чужой лок при этом не трогается.

✅ Resolved review finding [Med]: AC2 закрыт настоящим конкурентным прогоном.
`TestImportLockUnderConcurrency` (с `transaction=True`) удерживает первую задачу
физически внутри `call_command` в отдельном потоке и в это время запускает вторую на
тот же каталог: вторая уходит в `retry`, в импорт не входит, `max(peak) == 1`. Второй
тест класса проверяет, что после освобождения лока следующая задача заходит без retry —
то есть лок не залипает. Лок живёт в Redis, поэтому проверка отражает и межпроцессный
случай (`--concurrency > 1`).

✅ Resolved review finding [Med]: основной AC8-тест переведён на реальные разные
сегменты. В `backend/tests/fixtures/1c-data/rests/segments/` закоммичены **восемь
срезов настоящей выгрузки** (по 4 предложения из соответствующих
`data/import_1c/rests/rests_1_1…8`), с исходными именами 1С и непересекающимися
наборами `Ид` — проверено при генерации. Тест теперь утверждает не «сумма записей
сошлась», а «множество прочитанных сегментов равно множеству ожидаемых, ни один не
прочитан дважды, каталог обмена опустел»: восемь копий одного файла такую проверку
не прошли бы. `data_dependent`-тест на полноразмерном корпусе сохранён и усилен той же
проверкой по именам.

**Осознанное следствие строгого статуса.** Когда прогон падает по
`_assert_expected_file_processed`, `_cleanup_files` не вызывается — файлы, которые
этот прогон успел распарсить (в том числе чужой сегмент, оказавшийся в каталоге
вместо нашего), остаются на диске и достаются своему хозяину. Двойная обработка
сегмента остатков безопасна: `stock_quantity` перезаписывается, а не суммируется
между процессами (`variant_import.py:1181-1187`). Потери данных этот путь не создаёт,
а неверный `completed` — создавал.

**Что сделано (ядро гонки, T1–T5).**

1. **Точечный cleanup (AC1).** `_cleanup_files` принимает список путей, которые прогон
   реально распарсил, и удаляет только их через `Path(p).unlink(missing_ok=True)`.
   Весь блок `xml_patterns` / `glob` удалён. Накопитель — `Command._processed_files`,
   путь добавляется **после** успешного парсинга (в `_parse_or_skip`), а не после сбора
   списка. Очистка `import_files` осталась по каталогу — там гонки не наблюдалось.

2. **Сериализация задач (AC2).** `process_1c_import_task` берёт лок
   `onec:import:lock:<effective_data_dir>` через `cache.add` (атомарный `SETNX` в Redis)
   **до** внешнего `try` — иначе `celery.exceptions.Retry` (наследник `Exception`) попал бы
   в обработчик и пометил сессию `FAILED`. При занятом локе — `self.retry(countdown, max_retries)`
   из настроек; исчерпание попыток ловится как `MaxRetriesExceededError` и переводит сессию
   в `FAILED` с внятным текстом. Освобождение — в `finally` через `_release_import_lock`,
   с проверкой владельца (`cache.get(key) == task_id`). Механизм не зависит от `--concurrency`.

3. **Устойчивость к исчезнувшему файлу (AC3).** Парсинг каждого файла во **всех** семи шагах
   импорта (категории, бренды, типы цен, товары, предложения, цены, остатки) идёт через
   `_parse_or_skip`: `FileNotFoundError` → предупреждение + `self._missing_files`, цикл
   продолжается. Перед `finalize_session` выбирается статус: есть пропавшие и есть
   распарсенные → `COMPLETED` + строка в `report`; пропали все при непустом списке →
   `CommandError` с перечнем имён → сессия `FAILED`. «Файлов типа нет изначально»
   (`_collect_xml_files` вернул `[]`) — прежнее поведение, предупреждение и успех.

4. **Правдивый `file_type` (AC4).** Новый модуль
   `apps/integrations/onec_exchange/file_type_detection.detect_file_type` — единственная
   копия логики; объединил обе прежние (префикс `propertiesgoods` знала только задача).
   `_detect_file_type` делегирует туда; оба `delay()` передают `source_filename=self.filename`.
   В задаче `detect_file_type(source_filename or zip_filename)` — параметр `zip_filename`
   не переиспользован намеренно: он включает мёртвую ветку `file_service.unpack_zip()`.
   `mode=complete` → `detect_file_type("complete")` → `"all"`, поведение прежнее.
   Итерация 1.2 добавила туда тип `contragents`: по имени файла выбирается не только
   шаг импорта, но и сам маршрут (каталог товаров или `import_customers_from_1c`).

5. **Настройки (спека).** `ONEC_IMPORT_LOCK_TTL` (1800 с), `ONEC_IMPORT_LOCK_RETRY_COUNTDOWN`
   (10 с), `ONEC_IMPORT_LOCK_MAX_RETRIES` (180) — все через `config()`, не константы в коде.

6. **Документация.** `docs/integrations/1c/import-process.md` — новый раздел
   «Concurrency contract (shared exchange directory)»: лок каталога, точечный cleanup
   и передача типа сегмента зафиксированы как контракт.

**Тесты.** `backend/apps/products/tests/test_import_cleanup_race.py`, 30 тестов, покрыты все
строки матрицы I/O спеки. XML — закоммиченный срез реальной выгрузки
(`backend/tests/fixtures/1c-data/rests/rests.xml`), сегменты имитируются побайтовыми копиями
под именами, которые даёт 1С; синтетика не создавалась. Дополнительный `data_dependent` тест
гоняет то же самое на по-настоящему разных сегментах назначенного корпуса
`backend/data/import_1c/rests/` (в CI штатно скипается).

**Регрессии в существующих тестах — два ассерта на точную сигнатуру `delay()`.**
`integration/test_import_orchestration.py::test_mode_import_triggers_task` и
`tests/integration/test_onec_import.py::TestAsyncImportDispatch::test_execute_dispatches_celery_task`
проверяли `delay(session.pk, import_dir)` буквально. Оба обновлены до нового контракта
(`source_filename="test.xml"` и `source_filename="goods.xml"`) — это и есть проверяемое
изменение поведения, а не подгонка теста под код.

**Качество.** Black + Flake8 — чисто. Mypy по изменённым файлам новых ошибок не даёт
(8 найденных — предсуществующие в `staging.py`, `development.py`, `order_numbering.py`,
`variant_import.py`).

**Осознанные ограничения.**
- Гонка «TTL истёк → ключ перезахвачен → старый владелец снимает чужой лок» остаётся
  теоретически возможной, но требует импорта дольше 1800 с. Отмечена комментарием
  в `_release_import_lock`.
- Если Redis недоступен, импорт не запускается вовсе — осознанный fail-closed: параллельный
  импорт без лока хуже падения, а Celery без Redis всё равно не работает. Начиная с итерации
  ревью 1.2 сессия при этом переводится в `FAILED` с текстом ошибки, а не остаётся
  `IN_PROGRESS` до `cleanup_stale_import_sessions` (порог 2 ч).
- Строгость «обещанный файл обязан быть прочитан» действует только на товарный
  каталог. Маршрут `contragents` её не получил: если файл контрагентов исчез до
  прогона, `import_customers_from_1c` отчитается успехом с нулём записей. Это
  отдельная команда со своим контрактом, в объём стори она не входит.
- Файлы, тип которых `detect_file_type` определить не смог (`units.xml`,
  `storages.xml`, `propertiesOffers*.xml`, произвольные имена), по-прежнему
  запускают полный несужаемый импорт: `all` по определению означает «сгрести
  каталог целиком», и обещанного файла там нет. В штатной выгрузке такие файлы
  идут блоком справочников, до сегментов, поэтому забирать им нечего.
- Файлы, которых прогон не читал, теперь не удаляются им вовсе. Их убирает
  `FileRoutingService.cleanup_import_dir` по завершении последней активной сессии —
  рабочий guard в `tasks.py:245-266` и `views.handle_init` не тронут.

**Вне объёма (Split 2026-08-26, в `deferred-work.md`):** `session.save(update_fields=…)`
в `except` команды (AC5), путь `backup_db` (AC6), длина `size_value` (AC7).
Изоляция каталога обмена по сессиям — tech-debt п. 26, не потребовалась.

**AC9 не проверен — требует ручного выката.** Правки не задеплоены. Порядок:
выкатить, `docker compose restart backend celery celery-beat`, затем **обязательно**
`restart nginx` (иначе 502 на старом IP апстрима), запустить из 1С выгрузку только остатков
и снять SQL из раздела «Выкат и восстановление данных». Данные за 25.08 восстанавливаются
только повторной выгрузкой — файлы удалены.

### File List

**Добавлено:**
- `backend/apps/integrations/onec_exchange/file_type_detection.py`
- `backend/apps/products/tests/test_import_cleanup_race.py`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_1_4a5f6f6b-3b16-4cee-8327-79c093def766.xml`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_2_56e28a80-12ac-4880-a106-c63f1f82de95.xml`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_3_c9b163cc-2dec-4f36-879b-987d87fee84e.xml`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_4_e1b8365d-c2dd-4d4f-92ab-bc0fc0d94436.xml`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_5_eed92aac-ccc4-4129-841c-11a0fb1215c3.xml`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_6_01c9a333-8eaa-4696-98bb-0cc054cc43ae.xml`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_7_6e4a27ec-accc-4ebc-8ad4-abaddc4bbff3.xml`
- `backend/tests/fixtures/1c-data/rests/segments/rests_1_8_2d10e98f-331c-447d-8c41-25f5379a3883.xml`

**Изменено:**
- `backend/apps/products/tasks.py`
- `backend/apps/products/management/commands/import_products_from_1c.py`
- `backend/apps/integrations/onec_exchange/import_orchestrator.py`
- `backend/freesport/settings/base.py`
- `backend/apps/products/tests/integration/test_import_orchestration.py`
- `backend/tests/integration/test_onec_import.py`
- `docs/integrations/1c/import-process.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/onec-import-cleanup-race-and-followups.md`
- `_bmad-output/implementation-artifacts/spec-onec-import-cleanup-race.md`
