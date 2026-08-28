---
baseline_commit: 7c9e8525
spec: _bmad-output/specs/spec-onec-exchange-dir-isolation/SPEC.md
---

# Story: Изоляция каталога обмена 1С по сессии

Status: review

> 🟢 **Канонический контракт — не этот файл.** Требования задаёт `_bmad-output/specs/spec-onec-exchange-dir-isolation/SPEC.md` и его компаньоны (`evidence.md`, `affected-code.md`, `post-deploy-verification.md`, `project-context.md`). Стори добавляет к ним координаты, проверенные чтением кода, и разбор трёх мест, где контракт молчит или расходится сам с собой (см. «Развилки, решённые в стори»).
> 🟢 **Свежесть координат: все строки проверены чтением файлов на коммите `7c9e8525`** (28.08.2026). Номера строк — ориентир; якорь — имя символа.
> 🔴 **`cleanup_import_dir` — `risk: CRITICAL`.** `npx gitnexus impact cleanup_import_dir --direction upstream` → `impactedCount: 13`, `direct: 2`, 7 затронутых процессов (`handle_init`, `post`, `handle_success`, `handle_import`, `handle_query`, `handle_file_upload`, …). Метод уже правился двумя хотфиксами (`ff0bbc0a`, `057afc41`). **Перед правкой прогнать impact заново и показать Alex.**
> 🟢 **Остальное — LOW.** `process_1c_import_task` → `impactedCount: 0`. `route_file` → `impactedCount: 4`, `direct: 1`.
> ⚠️ **Индекс GitNexus на момент написания стори устарел** (`indexed 0393e02`, `current 7c9e852`). До старта разработки выполнить `! npx gitnexus analyze`, иначе `impact`/`context` не увидят изменения последних коммитов.
> 🔴 **Главная мина этой работы — в п. «Развилка 1: лок каталога обмена».** Наивная реализация изоляции молча уничтожает сериализацию задач, которую SPEC в Non-goals прямо требует сохранить. Прочитать до первой правки.

## Story

As a **владелец каталога**,
I want **чтобы каждая сессия обмена с 1С получала собственный каталог входящих XML и видела только свои файлы**,
so that **сегмент, постоявший в очереди за локом, не обнаруживал, что его файл уже прочитал и удалил сосед, и статус сессии отражал реальную судьбу данных**.

## Почему это делается (сжатая фактура)

Замер прода 28.08.2026, окно 7 дней: 110 упавших сессий, из них **85 с «файл не найден в каталоге обмена», и все 85 — ровно те, что ждали лока** (100 % корреляция). Суточный объём — 1 509 сессий (500 `mode=complete`, 1 009 `mode=import`).

Механизм (сессии 66453 / 66454, 04:50 UTC):

| Время | Что произошло |
|---|---|
| 04:50:18.905 | Сессия **66453** (`mode=complete`) → `IN_PROGRESS`, задача взяла лок каталога |
| 04:50:20.954 | Сессия **66454** (`mode=import`) с файлом `rests_1_1_74a08eed….xml` |
| 04:50:20.958 | Файл принят и положен в **общий** `1c_import/rests/` |
| 04:50:20.961 | Задача 66454 → «Каталог обмена занят другим импортом, задача отложена» |
| 04:50:21 | Держатель лока 66453 собирает по маске **все** `rests/rests*.xml`, включая чужой свежий файл, читает его и законно удаляет как обработанный |
| 04:50:30 | 66454 получает лок, обещанного файла нет → `CommandError` → **FAILED** |

Сегодня цена — **недостоверный статус**: в разобранных случаях данные доезжали чужим прогоном. Опасность в том, что **настоящая потеря выглядит идентично** — инцидент 25.08.2026: 6 сегментов остатков, ≈18 000 строк, 963 варианта торговались по старым данным.

Ключевой факт, на котором держится решение: **`session_key` уникален для каждого файла** (85 сессий за 20 минут → 85 разных ключей; 1С не держит cookie-сессию между запросами). Изоляция по `session_key` даёт каталог на файл — пересечься физически невозможно.

Три существующих guard-а не спасают: каждый — проверка в один момент времени, после которой конкурент появляется. Классический TOCTOU на уровне сессий. Полный разбор — `evidence.md`.

## Что уже сделано и переделывать НЕ нужно

- `_cleanup_files` **не** удаляет по glob-маске и сверяет отпечаток файла перед удалением (`import_products_from_1c.py:820+`) — стори `onec-import-cleanup-race-and-followups.md`.
- `_restrict_to_expected` (`import_products_from_1c.py:122-152`) сужает собранное до обещанных имён — **прогон с обещанием чужого уже не ест**. Остался виноватым только прогон **без** обещания (`mode=complete`, ~500/сутки).
- `_assert_expected_file_processed` (`:793-818`) переводит тихий `COMPLETED` с нулём записей в `FAILED` — именно поэтому дефект сегодня виден.
- Лок каталога обмена в Redis (`tasks.py:104-171`) сериализует задачи; `save(update_fields=…)` в `except` команды не затирает отчёт упавшей сессии.
- `_bmad-output/race-condition-analysis.md` — исторический контекст (причина образца Story 36.1, пути `/app/media/1c_import`). Работу по нему не переделывать.

---

## Acceptance Criteria

### AC1 — сессионная раскладка каталога обмена (CAP-1, ядро)

`FileRoutingService.import_dir == import_base / session_id`; `ImportOrchestratorService` передаёт задаче `data_dir` = каталог **своей** сессии.

**Приёмка — регрессионный тест:** две сессии с разными `session_key` и файлами одного типа (`rests_1_1_*.xml` и `rests_1_2_*.xml`), задачи запускаются последовательно при **занятом локе** — обе завершаются `COMPLETED`, каждая прочитала ровно свой файл.

🔴 **Тест обязан упасть на коде до правки (показать RED).** Зафиксировать факт RED в Dev Agent Record — иначе тест ничего не ловит.

### AC2 — изображения остаются доступными изолированному XML (CAP-2)

XML-сегмент из сессионного каталога находит изображения, приехавшие отдельным обменом с другим `sessid`, в общем `import_files`.

**Приёмка — тест на реальной выгрузке:** `goods.xml` в `<sessid>/goods/`, файл картинки в общем `import_base/import_files/<xx>/` → путь из XML разрешается, изображение привязывается к товару/варианту.

### AC3 — `mode=complete` не сгребает каталог (CAP-3)

Прогон без обещанных имён (`promised_filenames is None`) завершается `COMPLETED` с **пометкой в `session.report`** о том, что своих файлов нет; ни один файл соседних сессий не прочитан и не удалён.

**Приёмка — тест:** при наличии заполненных каталогов чужих сессий прогон `mode=complete` завершается `COMPLETED`, в `report` есть подстрока-пометка, файлы соседей на диске целы и не распарсены. Проверяется тестом, а не наблюдением на проде.

### AC4 — уборка ограничена своим каталогом (CAP-4)

`cleanup_import_dir` и post-import cleanup работают в границах каталога собственной сессии.

**Приёмка — тест:** `cleanup_import_dir` сессии A не удаляет ничего из каталога сессии B.

### AC5 — каталоги обмена не накапливаются (CAP-5)

После завершения обмена каталог сессии удаляется из `1c_temp` и `1c_import`. Каталоги, осиротевшие при падении воркера, подбираются автоматически периодической `celery-beat` задачей с порогом **24 часа** (порог зафиксирован контрактом, не «на усмотрение реализации»).

**Приёмка:** тест на задачу уборки — каталог старше 24 ч удаляется, свежий не трогается; задача зарегистрирована в расписании и реально попадает в beat (см. 🔴 «Мина: два расписания beat» в Dev Notes).

### AC6 — очередь за локом сохраняется

Ожидание лока каталога обмена остаётся легитимным поведением: две задачи обмена по-прежнему сериализуются между собой.

**Приёмка — тест:** две задачи с разными `session_key` конкурируют за **один и тот же** ключ лока; вторая получает `Retry` с сообщением «Каталог обмена занят другим импортом, задача отложена», затем отрабатывает успешно.

**Обоснование:** SPEC, Non-goals — «Не устранять само ожидание лока каталога. Очередь остаётся легитимной; устраняются падения **после** неё». Без явной правки изоляция ломает это молча (см. Развилку 1).

### AC7 — регресс зелёный

`apps/products` + `apps/integrations` проходят целиком (на 28.08.2026 — 605 тестов). Black + Flake8 чисто. Mypy по изменённым файлам не даёт новых ошибок.

### AC8 — прод-замер после выката *(гейт статуса `done`, не гейт мержа)*

За сутки после выката: **ноль** сессий с ошибкой «не найден в каталоге обмена»; контрольная полная выгрузка номенклатуры — 20 сегментов `goods`, все `COMPLETED`, сумма обработанных сегментов равна числу присланных файлов; число каталогов в `1c_temp` и `1c_import` возвращается к исходному. Процедура и SQL — `post-deploy-verification.md`.

⚠️ Само сообщение об ожидании лока в отчётах **успешных** сессий регрессом не считается.

---

## Развилки, решённые в стори

Три места, где контракт молчит или расходится сам с собой. Решения приняты здесь; если Alex решит иначе — правится стори, а не код на ходу.

### 🔴 Развилка 1: лок каталога обмена ключуется по `data_dir`

**Факт кода.** `tasks.py:29-31`:

```python
def _import_lock_key(data_dir: str) -> str:
    """Ключ лока каталога обмена. Лок именно на каталог, а не на сессию."""
    return f"{IMPORT_LOCK_KEY_PREFIX}{data_dir}"
```

и `tasks.py:104`: `lock_key = _import_lock_key(effective_data_dir)`, где `effective_data_dir` — это ровно тот `data_dir`, который изоляция делает **разным для каждой сессии**.

**Последствие наивной реализации.** Каждая сессия получает собственный ключ → лок никогда не конкурентен → сериализация задач исчезает целиком и молча. Это:

1. нарушает Non-goal SPEC «не устранять само ожидание лока»;
2. делает сценарий AC1 («при занятом локе») невоспроизводимым — тест перестаёт проверять то, ради чего написан;
3. возвращает полный параллелизм импорта без единого замера, что́ он делает с БД.

**Решение: ключ лока считается от общего корня, а не от сессионного каталога.** Если `data_dir` лежит внутри `ONEC_EXCHANGE["IMPORT_DIR"]` — ключ строится по `IMPORT_DIR`; иначе (ручной прогон по `ONEC_DATA_DIR`, тесты с `tmp_path`) — по самому `data_dir`, как сейчас. Правка локальная, в `_import_lock_key` и точке вызова. Закрывается AC6.

### 🟠 Развилка 2: `affected-code.md` противоречит себе по картинкам

Компаньон одновременно утверждает, что `import_products_from_1c.py` **править не нужно**, и что развязка путей картинок **обязательна**, иначе CAP-2 не выполняется.

**Факт кода.** `base_dir` для картинок вычисляет именно команда, не `variant_import`:

- `import_products_from_1c.py:655` — `base_dir = os.path.join(data_dir, "goods", "import_files")`
- `import_products_from_1c.py:694-701` — `os.path.join(data_dir, "offers", "import_files")` с фолбэком на `goods/import_files`

`variant_import.py` только принимает `base_dir` параметром и делает `Path(base_dir) / normalize_image_path(...)` (строки 420, 754, 1074). Развязать путь внутри `variant_import.py` физически негде.

**Решение: минимальная правка команды в двух точках (`:655` и `:694`), детерминированным правилом, без эвристик.**

> Если `data_dir` — подкаталог `ONEC_EXCHANGE["IMPORT_DIR"]` (то есть прогон идёт по сессионной раскладке), картинки берутся из общего `IMPORT_DIR / "import_files"`. Во всех прочих случаях (ручной прогон по `ONEC_DATA_DIR`, тесты) поведение остаётся текущим.

Ограничение SPEC «`import_products_from_1c` не правится» относится к `data_dir` и `_collect_xml_files` — они действительно работают как есть. Правка картинок этого не касается. Отдельного аргумента командной строки не заводить: параметр без вызывающих — мёртвый код.

### 🟠 Развилка 3: переходное окно на проде — картинки в старой раскладке

Сегодня на проде картинки лежат в `1c_import/goods/import_files/<xx>/`. После выката новые едут в `1c_import/import_files/<xx>/`. `goods.xml`, приехавший сразу после выката и ссылающийся на картинку, доставленную **до** выката, файла не найдёт.

Опасность неочевидная: `_import_base_images(..., mirror_composition=True)` (`variant_import.py:720+`) при **частичном** разрешении зеркалирует состав по разрешённым — то есть у товара может пропасть часть фото. Полная неудача разрешения безопасна (состав остаётся прежним, `variant_import.py:750-762`), частичная — нет.

**Решение: добавить фолбэк на легаси-раскладку.** Если файла нет в `IMPORT_DIR / "import_files"`, искать в `IMPORT_DIR / "goods" / "import_files"`. Реализуется там же, где Развилка 2, стоит несколько строк, снимает единственный сценарий порчи данных этой стори. Фолбэк пометить комментарием как переходный, со ссылкой на эту стори.

---

## Tasks / Subtasks

### T1. Раскладка каталога обмена — по сессии (AC1, AC2)

- [x] **Перед первой правкой:** `! npx gitnexus analyze`, затем `npx gitnexus impact FileRoutingService --direction upstream` и `npx gitnexus impact cleanup_import_dir --direction upstream`; blast radius показать Alex (`cleanup_import_dir` ожидается `CRITICAL`).
- [x] `routing_service.py`, `FileRoutingService.__init__` (стр. 79-83): `self.import_dir = self.import_base / session_id`. Снять комментарий `FIXED: Import directory should be shared/root, not session-isolated` — он фиксирует ровно то поведение, которое чинится. Docstring класса и модуля (стр. 1-10, 47-57) уже описывают сессионную раскладку — сверить, что описание совпало с фактом.
- [x] `routing_service.py`, `move_to_import` / `_ensure_import_dir`: исключение для картинок — маршрут `import_files` кладёт файл в **общий** `import_base / "import_files"`, сохраняя подкаталог `<xx>` из имени. Остальные маршруты — под сессионный `import_dir`.
- [x] `import_orchestrator.py`, `__init__` (стр. 47): `self.import_dir` = каталог **своей** сессии (`IMPORT_DIR / sessid`). ⚠️ У оркестратора **собственная копия пути**, мимо `FileRoutingService` — правки одного `routing_service.py` недостаточно, изоляция останется дырявой. Через эту копию идут: `_unpack_zips` (`:202`, `:214-217`), `_route_unpacked_files` (`:260`, `:287`), `_dispatch_import` (`:310`, `:344-346`), `_dispatch_or_dryrun` (`:468`, `:488-490`).
- [x] `import_orchestrator.py`, `_route_unpacked_files` (стр. 287): картинки из архива → общий `import_files`; XML → сессионный каталог.
- [x] 🔴 `tasks.py` (стр. ~255-275): **вторая, дублирующая копия** той же логики маршрутизации распакованного (`target_subdir = "goods"` / `"goods/import_files"`). Правится **обеими** — иначе `mode=complete` с накопившимися zip разложит картинки мимо общего каталога. Это самая пропускаемая точка работы.
- [x] `.dry_run` остаётся в корне общего `import_base`. Точки: `import_orchestrator.py:310` и `:421-424` — обе должны смотреть на `import_base / ".dry_run"`, а не на сессионный каталог.
  - ⚠️ **`file_service.py:255-262` НЕ трогать.** Компаньон называет её четвёртой точкой `.dry_run`, но это ошибка: `FileStreamService.session_dir = TEMP_DIR / session_id` (`file_service.py:150-151`) — там свой `.dry_run` во временном каталоге, к `import_base` отношения не имеющий.
  - Маркер `.exchange_complete` изоляции не касается — живёт в `session_dir` временного каталога (`file_service.py:283-296`), который и так был сессионным.
- [x] `import_products_from_1c.py:655` и `:694-701` — развязка путей картинок по правилу из Развилки 2 + фолбэк на легаси-раскладку из Развилки 3. `_collect_xml_files` и обработку `data_dir` (`handle`, стр. 338-341) **не трогать** — они заработают как есть.
- [x] `tasks.py`, `_import_lock_key` (стр. 29-31) и вызов (стр. 104) — ключ от общего корня по правилу из Развилки 1 (AC6).
- [x] 🔒 `routing_service.py`, `FileRoutingService.__init__`: валидировать `session_id` как **один безопасный сегмент пути** — отклонять `/`, `\`, `..` и пустое (сейчас проверяется только непустота, стр. 68-72). `sessid` приходит прямо из query-параметра (`views.py:174-177`) и нигде не санитизируется. До изоляции `cleanup_import_dir` работал по фиксированному пути; после — по пути, сегмент которого задаёт клиент, и `shutil.rmtree` пойдёт туда, куда его увели. Эндпоинт закрыт `Basic1CAuthentication` + `Is1CExchangeUser` (`views.py:196-197`), поэтому это укрепление, а не открытая дыра, — но вводить рычаг удаления по внешнему пути без проверки нельзя.

### T2. `mode=complete` больше не сгребает каталог (AC3)

- [x] `tasks.py`: прогон без `promised_filenames` при сессионной раскладке видит только свой пустой каталог. Убедиться, что он завершается `COMPLETED`, а не пытается импортировать пустоту.
- [x] Пометка «своих файлов нет» пишется в `session.report` (`tasks.py:480-482` — туда уже накапливаются строки `[{timestamp}] …`). Отдельного поля и миграции не требуется. Текст выбрать стабильным: тест AC3 вешается на подстроку.
- [x] `defer_to_active_sessions` (`tasks.py:414-423`) **не удалять** — после изоляции избыточен для этого сценария, но остаётся страховкой для ручных прогонов с `data_dir` по умолчанию.

### T3. Уборка (AC4, AC5)

- [x] `routing_service.py`, `cleanup_import_dir` (стр. 192-230): чистит **свою** папку. Переписать docstring — сейчас он прямо описывает общий каталог («As the import directory is shared across sessions…»).
- [x] Проверить вызывающих: `views.py:452-453` (`handle_init`, guard стр. 427-453), `tasks.py:501-502` (post-import, guard `other_active` стр. 486-506), комментарий `import_orchestrator.py:328`. Guard-ы **не удалять** (Non-goal SPEC).
  - Ожидаемое следствие, не регресс: `session_key` уникален на файл, поэтому `cleanup_import_dir(force=True)` в `handle_init` почти всегда попадёт на свежий (пустой или несуществующий) каталог и станет практически no-op. Уборку чужого мусора берёт на себя задача из AC5. Guard оставить как есть.
- [x] `backend/apps/integrations/tests/test_handle_init_cleanup_race.py` — 6 ассертов на вызовы/невызовы метода. Router там мокается, так что тесты должны остаться зелёными; если поехали — разобраться, а не подгонять.
- [x] Удаление каталога сессии в `1c_temp` и `1c_import` после завершения обмена (сегодня копится 32 276 пустых папок).
- [x] Новая периодическая задача уборки осиротевших сессионных каталогов старше **24 часов** в `1c_temp` и `1c_import`. Место — `apps/products/tasks.py`, рядом с `cleanup_stale_import_sessions`.
  - ⚠️ Каталоги сессий в `1c_import` **не будут пустыми**: `tasks.py:311-325` («Defensive directory creation») создаёт в `data_dir` подпапки `goods`, `offers`, `prices`, `rests`, `priceLists` на каждом прогоне. Удаление — `shutil.rmtree`, а не `rmdir`; возраст считать по каталогу сессии, а не по файлам внутри.
- [x] 🔴 Зарегистрировать задачу в `backend/freesport/celery.py` (`app.conf.beat_schedule`), **не только** в `settings/base.py`. См. «Мина: два расписания beat» в Dev Notes — регистрация только в настройках означает, что задача не запустится никогда.
- [x] Разовую зачистку накопленных 32 276 каталогов **не делать** — Alex выполняет вручную вне этой работы. Миграцию/management-команду под это не писать.

### T4. Тесты (AC1-AC6)

- [x] **RED-first, обязателен:** регрессионный тест AC1. Сначала прогнать на коде до правки и зафиксировать падение в Dev Agent Record.
- [x] Тест AC3: `mode=complete` при заполненных каталогах чужих сессий.
- [x] Тест AC2: XML из сессионного каталога + картинка в общем `import_files`.
- [x] Тест AC4: `cleanup_import_dir` сессии A против каталога сессии B.
- [x] Тест AC6: конкуренция двух сессий за один ключ лока.
- [x] Тест AC5: порог 24 часа у задачи уборки.
- [x] Только реальные выгрузки. Синтетические XML запрещены.

### T5. Документация и сдача

- [x] Обновить `docs/integrations/1c/import-process.md` — раскладка каталога обмена меняется структурно.
- [x] `_bmad-output/planning-artifacts/tech-debt.md` п. 26 — закрыть или переписать по факту.
- [x] `npx gitnexus detect-changes --scope all` перед коммитом: затронуты только ожидаемые символы и процессы.
- [x] Black + Flake8 (навык `backend-lint`).
- [x] Обновить статус в `sprint-status.yaml`.

### Review Findings

- [x] [Review][Patch] Запретить `sessid`, совпадающие с общими каталогами: `import_files`, `goods` и другими `SHARED_ROOT_NAMES`; иначе cleanup сессии удаляет общие данные [`backend/apps/integrations/onec_exchange/routing_service.py:65-70,142-157,184-195`]
- [x] [Review][Patch] Не удалять активный сессионный каталог только по старому `mtime` корня: учитывать статус/лок и свежесть вложенных файлов, закрыв также TOCTOU между проверкой возраста и `rmtree` [`backend/apps/products/tasks.py:621-666`]
- [x] [Review][Patch] Убрать очистку общих изображений по 24-часовому `mtime`: контракт не задаёт связь между обменом изображений и будущим XML, поэтому такая уборка нарушает AC2 [`backend/apps/products/tasks.py:630-631,668-679`]
- [x] [Review][Patch] Ограничить `defer_to_active_sessions` ручным общим каталогом: изолированный `mode=complete` с собственным XML сейчас молча пропускает импорт при любой чужой `IN_PROGRESS`-сессии [`backend/apps/products/tasks.py:436-475`]
- [x] [Review][Patch] Удалять каталог завершённой изолированной сессии независимо от чужих `IN_PROGRESS`-сессий, сохранив исторический guard только для общего ручного каталога [`backend/apps/products/tasks.py:526-550`]
- [x] [Review][Patch] Добавить единый приёмочный тест AC1: занятый общий лок → Retry второй реальной задачи → освобождение лока → обе сессии COMPLETED и каждая обработала только свой сегмент [`backend/apps/products/tests/test_exchange_dir_isolation.py:147-178,406-435`]
- [x] [Review][Patch] Дополнить AC2 тестом `offers.xml`, проверяющим привязку изображения из общего `import_files` к `ProductVariant`, а не только к `Product.base_images` [`backend/apps/products/tests/test_exchange_dir_isolation.py:199-222`]
- [x] [Review][Defer] `mode=file` допускает path traversal через `FileStreamService(sessid)` до вызова нового валидатора [`backend/apps/integrations/onec_exchange/file_service.py:139-160`] — deferred, pre-existing: произвольная запись вне `TEMP_DIR` существовала до текущего diff; исправить отдельной security-задачей с общей валидацией на входе протокола
- [x] [Review][Defer] Ошибка публикации `.delay()` оставляет сессию `IN_PROGRESS` без Celery-задачи, а повторный запрос получает ложный успех [`backend/apps/integrations/onec_exchange/import_orchestrator.py:82-87,341-364,473-520`] — deferred, pre-existing: текущая story не меняла обработку ошибки брокера
- [x] [Review][Defer] XML во вложенном каталоге ZIP маршрутизируется по полному имени member и может не распознаться по префиксу [`backend/apps/integrations/onec_exchange/import_orchestrator.py:266-310`, `backend/apps/products/tasks.py:250-303`] — deferred, pre-existing: алгоритм сравнивал полное имя и до изоляции
- [x] [Review][Defer] `mode=complete` в dry-run после переноса ZIP читает список архивов из уже опустевшего temp-каталога и может отметить цикл завершённым без распаковки [`backend/apps/integrations/onec_exchange/import_orchestrator.py:428-443,473-487`] — deferred, pre-existing
- [x] [Review][Defer] При частично отсутствующем наборе изображений `mirror_composition=True` способен сократить ранее сохранённый состав; новый legacy fallback исправляет только наличие файла во второй раскладке [`backend/apps/products/services/variant_import.py:747-810,1066-1135`] — deferred, pre-existing

---

## Dev Notes

### 🔴 Мина: два расписания Celery Beat, побеждает не то, что ожидается

Расписание объявлено **дважды**:

- `backend/freesport/settings/base.py:252` — `CELERY_BEAT_SCHEDULE = {...}`
- `backend/freesport/celery.py:26` — `app.conf.beat_schedule = {...}`

Порядок в `celery.py`: `app.config_from_object("django.conf:settings", namespace="CELERY")` (стр. 21) → **затем** `app.conf.beat_schedule = {...}` (стр. 26). Второе присваивание **затирает** загруженное из настроек целиком.

Наблюдаемое следствие: `cleanup-stale-import-sessions` в `base.py` объявлен «раз в час», в `celery.py` — `crontab(minute="30")`; фактически работает вариант из `celery.py`.

**Новая задача уборки, добавленная только в `settings/base.py`, не запустится никогда, и тест на саму функцию этого не покажет.** Регистрировать в `celery.py`; тест должен проверять присутствие ключа в `app.conf.beat_schedule` после импорта приложения, а не в настройках.

### Как файл проходит систему сегодня (маршрут, который меняется)

```
1С POST → views.handle_file_upload → FileStreamService.append_chunk
                                      → TEMP_DIR/<sessid>/<file>          [уже сессионный]
1С POST mode=import → ImportOrchestratorService.execute
   _transfer_files  → FileRoutingService.move_to_import
                      → IMPORT_DIR/<type>/<file>                          [ОБЩИЙ ← правится]
   _unpack_zips     → IMPORT_DIR/*.zip                                    [ОБЩИЙ ← правится]
   _dispatch_import → process_1c_import_task.delay(pk, str(IMPORT_DIR), source_filename=…)
                                                        ↑ ОБЩИЙ ← правится
process_1c_import_task
   lock_key = _import_lock_key(effective_data_dir)                        [← Развилка 1]
   call_command("import_products_from_1c", data_dir=effective_data_dir, source_filename=…)
      _collect_xml_files(base_dir, subdir, name) → _restrict_to_expected  [работает как есть]
      base_dir картинок = data_dir/goods/import_files                     [← Развилка 2]
      _assert_expected_file_processed → CommandError, если обещанное не прочитано
      _cleanup_files → удаляет только реально распарсенное, сверяя отпечаток
post-import → FileRoutingService.cleanup_import_dir()                     [← AC4]
```

### Ключевые координаты (проверены на `7c9e8525`)

| Файл | Символ / строки | Роль в работе |
|---|---|---|
| `routing_service.py` | `FileRoutingService.__init__`, 79-83 | `self.import_dir = self.import_base` + комментарий `FIXED:` — ядро дефекта |
| `routing_service.py` | `route_file`, 130-150 | Картинки → `"goods/import_files"`; XML → подпапка типа |
| `routing_service.py` | `move_to_import`, 163-192 | `shutil.move` в `_ensure_import_dir(subdir)` |
| `routing_service.py` | `cleanup_import_dir`, 192-230 | Обходит `import_dir.iterdir()`, удаляет всё кроме `.dry_run` |
| `import_orchestrator.py` | `__init__`, 47 | **Собственная копия** `Path(settings.ONEC_EXCHANGE["IMPORT_DIR"])` |
| `import_orchestrator.py` | `_unpack_zips`, 202, 214-217 | `glob("*.zip")` + zip-slip guard относительно `import_dir` |
| `import_orchestrator.py` | `_route_unpacked_files`, 260, 287 | Маршрутизация распакованного; копит `_unpacked_xml_names` |
| `import_orchestrator.py` | `_dispatch_import`, 310, 344-346 | `.dry_run`; `delay(pk, str(self.import_dir), source_filename=…)` |
| `import_orchestrator.py` | `_dispatch_or_dryrun`, 421-424, 488-490 | Вторая проверка `.dry_run`; второй dispatch |
| `tasks.py` | `_import_lock_key`, 29-31 | Ключ лока от `data_dir` — Развилка 1 |
| `tasks.py` | `process_1c_import_task`, 63-105 | `target_import_dir`, `effective_data_dir`, захват лока |
| `tasks.py` | ~255-275 | **Дубль** маршрутизации распакованного — правится вместе с оркестратором |
| `tasks.py` | 402-423 | `defer_to_active_sessions` — не удалять |
| `tasks.py` | 480-482 | `session.report` — сюда пометка AC3 |
| `tasks.py` | 486-506 | post-import cleanup + guard `other_active` |
| `import_products_from_1c.py` | `handle`, 338-341 | `data_dir` уже параметризован — не трогать |
| `import_products_from_1c.py` | `_restrict_to_expected`, 122-152 | Сужение до обещанного — не трогать |
| `import_products_from_1c.py` | `_collect_xml_files`, 949-998 | Сбор от `base_dir` — не трогать |
| `import_products_from_1c.py` | `_assert_expected_file_processed`, 793-818 | Источник текста «не найден в каталоге обмена» |
| `import_products_from_1c.py` | 655, 694-701 | `base_dir` картинок — Развилки 2 и 3 |
| `variant_import.py` | `normalize_image_path`, 223-238 | Срезает префикс `import_files/` |
| `variant_import.py` | 420, 754, 1074 | `Path(base_dir) / normalized_path` — только потребитель |
| `variant_import.py` | `_import_base_images`, 720-762 | `mirror_composition=True`: частичное разрешение обрезает состав — риск Развилки 3 |
| `views.py` | `handle_init`, 427-453 | Guard пропуска cleanup + `cleanup_import_dir(force=True)` |
| `file_service.py` | 150-151, 255-262, 283-296 | `session_dir` в TEMP; `.dry_run` и `.exchange_complete` — **не трогать** |
| `settings/base.py` | 351-360 | `ONEC_EXCHANGE["TEMP_DIR"]`, `["IMPORT_DIR"]` |
| `celery.py` | 21, 26 | Два расписания beat — см. мину выше |

### Testing

**Запуск (одна БД на compose-проект — параллельные прогоны невозможны):**

```bash
cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend \
  pytest -x apps/products apps/integrations
```

`--env-file` тестовому compose **не передаётся** (файла `docker/.env` нет, и в `docker-compose.test.yml` нет подстановок). `run --rm`, **не** `exec`: у сервиса `backend` команда по умолчанию `pytest`, контейнер отрабатывает и выходит.

**Реальные данные (синтетика запрещена):**

| Источник | Что там | Годится для |
|---|---|---|
| `backend/tests/fixtures/1c-data/rests/segments/` | 8 **разных** реальных сегментов с исходными именами 1С (`rests_1_1_…` … `rests_1_8_…`), непересекающиеся наборы предложений. **Закоммичены** (59 файлов в `git ls-files`), доступны в CI | AC1, AC3, AC4, AC6 |
| `backend/tests/fixtures/1c-data/goods/import_files/goods.xml` + подкаталоги `01/`, `03/`, `06/` с настоящими `.jpg`/`.jpeg` | Товары со ссылками `import_files/<xx>/<file>.jpg` и сами файлы | AC2 |
| `data/import_1c/` (rests, goods, offers, …) | Полноразмерный runtime-корпус. **В `.gitignore`**, на раннере отсутствует | `@pytest.mark.data_dependent` тесты |

Маркеры проставляются автоматически по каталогу (`backend/conftest.py`), руками не ставить. `data_dependent` и `slow` — ортогональны и ставятся вручную. Тесты под `apps/` по умолчанию получают `unit` (это «модульный тест приложения», а не «без БД»).

**Образец для написания:** `backend/apps/products/tests/test_import_cleanup_race.py` — там уже есть `_make_exchange_dir`, `_segment_path`/`_segment_name`, работа с локом (`_release_import_lock`, `cache`), перехват `Retry`/`MaxRetriesExceededError`, разбор отчёта через `SEGMENT_LINE_RE`. Переиспользовать, а не писать заново.

**Правило RED-first для AC1.** Порядок: написать тест → прогнать на неизменённом коде → зафиксировать падение (текст ошибки в Dev Agent Record) → только потом править. Тест, зелёный до правки, дефект не ловит.

### Ограничения проекта — читать до первой команды

- **Только Docker + PostgreSQL.** Локальная БД не поддерживается.
- **Комментарии и docstrings — на русском** (стиль проекта). Английские docstring-и в `routing_service.py` — исторические; новые и переписываемые пишутся по-русски.
- **GitNexus обязателен:** `impact --direction upstream` до правки каждого символа, `detect-changes --scope all` перед коммитом. Только CLI, MCP отключён. Команды `rename` нет — переименования только точечно по списку из `impact`/`context`.
- **Деплой ручной**, CI-шаг `Deploy to Production` всегда skipped. `celery` и `celery-beat` пересобираются **вместе** с `backend` (импорт живёт в воркере); после пересборки backend **обязателен** `docker compose restart nginx`, иначе весь внешний API и обмен 1С падают в 502 на старом IP апстрима. На проде `git fetch origin main; git reset --hard origin/main`, **не** `git pull`.
- **Порог покрытия калибруется по CI, не по локальному прогону** (`data/import_1c/` в `.gitignore`, на раннере скипается ~32 теста импорта 1С; разрыв стабильно ~1,5 п.п.).

### Границы работы (Non-goals SPEC)

Не делать, даже если руки тянутся:

- Не переделывать `_cleanup_files` — оставшийся там TOCTOU в доли миллисекунды вне области.
- Не изолировать `import_files` (вариант 2) и не вводить раскладку `.claimed/<session_pk>/` (вариант 3) — оба отклонены Alex 28.08.2026.
- Не удалять существующие guard-ы: ни `defer_to_active_sessions`, ни пропуск cleanup при активных сессиях в `views.handle_init` и post-import.
- Не устранять само ожидание лока — очередь легитимна (см. AC6).
- Не менять протокол обмена с 1С и не пытаться получить от 1С связь «архив картинок ↔ XML-сессия» — механизма нет.
- Не убирать накопленные 32 276 каталогов в `1c_temp` — ручная разовая зачистка Alex, вне области.
- Не менять поведение тихого `COMPLETED` с нулём записей — `_assert_expected_file_processed` уже переводит такую сессию в `FAILED`.
- Не переделывать работу по `_bmad-output/race-condition-analysis.md`.

### Уроки предыдущей стори (`onec-import-cleanup-race-and-followups`)

- Два теста ломались на буквальной сигнатуре `delay()`: `apps/products/tests/integration/test_import_orchestration.py::test_mode_import_triggers_task` и `tests/integration/test_onec_import.py::TestAsyncImportDispatch::test_execute_dispatches_celery_task`. Эта стори снова меняет аргумент `data_dir` в `delay()` — **проверить оба первыми**.
- Fail-closed при недоступном Redis — осознанное решение: импорт без лока хуже падения. Не «чинить».
- Файлы, которых прогон не читал, он не удаляет; их убирает `cleanup_import_dir`. После изоляции область этой уборки сужается до своей папки — это и есть AC4, а не регресс.
- Строгость «обещанный файл обязан быть прочитан» действует только на товарный каталог; маршрут `contragents` её не имеет. В объём не входит.

### Project Structure Notes

- Раскладка каталога обмена меняется структурно: `IMPORT_DIR/<type>/` → `IMPORT_DIR/<sessid>/<type>/`, с двумя исключениями — общий `IMPORT_DIR/import_files/` (картинки) и `IMPORT_DIR/.dry_run` (флаг режима).
- Временный каталог (`TEMP_DIR/<sessid>/`) уже сессионный, его раскладка не меняется — меняется только то, что каталог теперь удаляется после обмена (AC5).
- Новые файлы: тест изоляции (рядом с `test_import_cleanup_race.py`, в `backend/apps/products/tests/`) и, если понадобится, отдельный модуль задачи уборки — но предпочтительно дописать в существующий `apps/products/tasks.py` рядом с `cleanup_stale_import_sessions`.
- Миграций эта работа не требует: пометка AC3 идёт в существующее поле `report`.

### References

- [Source: _bmad-output/specs/spec-onec-exchange-dir-isolation/SPEC.md] — канонический контракт: CAP-1…CAP-5, Constraints, Non-goals, Success signal
- [Source: _bmad-output/specs/spec-onec-exchange-dir-isolation/evidence.md] — замеры прода, механизм отказа, таблица развилки
- [Source: _bmad-output/specs/spec-onec-exchange-dir-isolation/affected-code.md] — карта кода (⚠️ противоречие по картинкам разобрано в Развилке 2, ошибка про `file_service.py` — в T1)
- [Source: _bmad-output/specs/spec-onec-exchange-dir-isolation/post-deploy-verification.md] — порядок выката, SQL и bash-проверки AC8
- [Source: _bmad-output/implementation-artifacts/tasks/dev-task-onec-exchange-dir-isolation.md] — первоисточник нарратива
- [Source: _bmad-output/implementation-artifacts/Story/onec-import-cleanup-race-and-followups.md] — предыдущая работа: лок, `_restrict_to_expected`, `_assert_expected_file_processed`
- [Source: _bmad-output/planning-artifacts/tech-debt.md#26] — «Каталог обмена 1С общий для всех сессий — изоляция отложена»
- [Source: project-context.md] — среда, запреты, доменные инварианты, тестирование, GitNexus-дисциплина
- [Source: docs/integrations/1c/import-process.md] — архитектура импорта (обновляется в T5)

---

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, `/bmad-dev-story`), 28.08.2026.

### Debug Log References

**GitNexus, индекс актуален (`d9f8c00`, `status: up-to-date`) — `analyze` не потребовался.**

| Символ | impactedCount | direct | risk |
|---|---|---|---|
| `cleanup_import_dir` | 13 | 2 | **CRITICAL** — 7 процессов (`handle_init`, `post`, `handle_success`, `handle_import`, `handle_query`, `handle_file_upload`, …) |
| `FileRoutingService` | 4 | 3 | LOW |
| `route_file` | 4 | 1 | LOW |
| `process_1c_import_task` | 0 | 0 | LOW |

`detect-changes --scope all`: 15 файлов, 61 символ, 26 процессов, `risk: critical` — весь список внутри потока обмена 1С (`handle_init → route_file / _ensure_import_dir / _route_unpacked_files`, `process_variant_from_offer → _build_destination_path`). Постороннего не задето.

**RED-прогон AC1 на коде до правки** (`pytest apps/products/tests/test_exchange_dir_isolation.py`, 15 failed / 5 passed):

```
E   AssertionError: Чужой сегмент прогон без обещания читать не вправе
    assert False
/app/apps/products/tests/test_exchange_dir_isolation.py:167: AssertionError
```

Файл сессии B (`rests_1_2_….xml`) на общем каталоге съеден прогоном сессии A (`mode=complete`) — ровно механика прода 66453/66454. Сопутствующие RED того же прогона:

```
:137  assert PosixPath('…/1c_import') == (PosixPath('…/1c_import') / 'sess-a')
:144  assert PosixPath('…/1c_import/rests/rests_1_1_….xml') == (…/'sess-a'/'rests'/'rests_1_1_….xml')
:183  Failed: DID NOT RAISE ValueError        # sessid не валидировался как сегмент пути
:269  assert 'В каталоге обмена этой сессии нет своих XML-файлов' in '…Импорт завершен со статусом: Завершено…'
```

**GREEN после правки:** `test_exchange_dir_isolation.py` — 20 passed.

**🔴 Dev Note стори про расписание beat оказалась ИНВЕРТИРОВАНА — исправлено по замеру.**
Стори утверждала, что `app.conf.beat_schedule` в `celery.py` затирает `CELERY_BEAT_SCHEDULE` из настроек. Замер в контейнере 28.08.2026:

```
effective: {'monitor-pending-verification-queue': '28800', 'cleanup-stale-import-sessions': '3600'}
settings : ['monitor-pending-verification-queue', 'cleanup-stale-import-sessions']
```

Эффективное расписание `cleanup-stale-import-sessions` — **3600 с из `settings/base.py`**, а не `crontab(minute="30")` из `celery.py`; ключа `cleanup-stale-import-sessions-every-hour` из `celery.py` в `app.conf.beat_schedule` нет вовсе. Причина: `app.conf` ленив, присваивание в `celery.py` выполняется до финализации конфига, и значения из `config_from_object` ложатся поверх. Вывод стори («регистрация только в настройках не запустится никогда») верен по форме, но указывает не на тот файл. Задача зарегистрирована в **обоих** местах, оба комментария переписаны по факту, тест AC5 проверяет `app.conf.beat_schedule` — то есть эффективное расписание, а не источник.

**Раунд 2 — исправление 7 patch-findings код-ревью (28.08.2026).**

`npx gitnexus status`: индекс актуален (`87edbf7`), `analyze` не потребовался.

| Символ | impactedCount | direct | risk |
|---|---|---|---|
| `validate_session_segment` | 3 | 2 (`FileRoutingService.__init__`, `session_import_dir`) | LOW |
| `cleanup_stale_exchange_dirs` | 0 | 0 | LOW |
| `process_1c_import_task` | 0 | 0 | LOW |

HIGH/CRITICAL нет: `cleanup_import_dir` в этом раунде не правился.

**RED-прогон новых тестов на коде до правок** (прод-код убран `git stash`, тесты
оставлены; `pytest apps/products/tests/test_exchange_dir_isolation.py`):
**7 failed, 20 passed**.

```
FAILED …::TestSessionDirIsolation::test_session_id_must_not_collide_with_shared_dirs
FAILED …::TestPromiselessRunKeepsHandsOff::test_own_files_are_imported_despite_active_neighbour
FAILED …::TestCleanupStaysInOwnDir::test_session_dir_removed_even_with_active_neighbour
FAILED …::TestStaleExchangeDirCleanup::test_fresh_file_inside_old_dir_keeps_it
FAILED …::TestStaleExchangeDirCleanup::test_active_session_dir_is_kept
FAILED …::TestStaleExchangeDirCleanup::test_shared_dirs_are_protected
FAILED …::TestStaleExchangeDirCleanup::test_old_shared_images_are_never_pruned
E       assert 1 == 0
E        +  where 1 = cleanup_stale_exchange_dirs()   # общие картинки подрезались по возрасту
```

Падения покрывают findings 1-5 ровно по одному-двум тестам на находку. Тесты
findings 6 и 7 (`test_locked_dir_defers_neighbour_and_both_sessions_complete`,
`test_offers_variant_binds_image_from_shared_dir`) на старом коде **зелёные** — и
это ожидаемо: ревью просило закрыть пробел в приёмочном покрытии, а не дефект
поведения. Отмечено явно, чтобы их зелёность не читалась как «тест ничего не ловит».

**GREEN после правок:** `test_exchange_dir_isolation.py` — 27 passed.
Регресс `apps/products` + `apps/integrations` + `tests/unit/test_file_routing.py`
+ `tests/integration/test_onec_import.py` — **699 passed, 1 skipped, 0 failed**
(было 692 + 7 новых тестов). Полный backend-набор — **3214 passed, 75 skipped,
0 failed, 19 subtests passed** (было 3207 + те же 7). Black и Flake8 чисто. Mypy по изменённым файлам:
5 сообщений, все вне изменённых диапазонов (`settings/staging.py:50`,
`settings/development.py:59`, `orders/services/order_numbering.py:84,117`,
`orders/tasks.py:23`) — они были и до правок.

`detect-changes --scope all`: 10 файлов, 14 символов, 7 процессов — весь список
внутри потока обмена 1С (`Handle_init`, `Process_1c_import_task`,
`Finalize_batch`). Постороннего не задето.

**База сравнения для AC8, снята с прода 28.08.2026 ДО выката.**

Каталоги: `1c_import` — 0 записей, `1c_temp` — 0 записей (разовая зачистка Alex
выполнена). Это и есть исходный счётчик для п. 3 `post-deploy-verification.md`.

Сессии за последние 24 часа:

| Метрика | Значение |
|---|---|
| Всего сессий | 614 |
| `completed` | 605 |
| `failed` | **9** |
| из них `error_message LIKE '%не найден в каталоге обмена%'` | **9** |
| из них `report LIKE '%Каталог обмена занят%'` | **9** |

Корреляция «упало ↔ ждало лока» — 100 %, как и в замере за 7 дней (85 из 85).
Дефект на момент выката живой, приёмка AC8 (`not_found = 0`) измерима.

Хранилище картинок: `media/products/base` — 3,6 ГБ / 15 438 файлов,
`media/products/variants` — 1,3 ГБ / 5 889, всего `media/products` 6,4 ГБ.
Диск: свободно 20 ГБ из 79 (74 % занято).

### Completion Notes List
**Что сделано (AC1-AC7).**

- **AC1.** `FileRoutingService.import_dir = import_base / session_id`; у `ImportOrchestratorService` собственная копия пути переведена туда же через `session_import_dir(sessid)`. Комментарий `FIXED: Import directory should be shared/root…` снят — он фиксировал ровно чинимое поведение.
- **AC2.** Единое детерминированное правило вынесено в `routing_service` (`is_session_import_dir` / `images_dir_for` / `legacy_images_dir_for` / `dry_run_flag_for`) и применяется во всех четырёх местах: роутер, оркестратор, дубль маршрутизации в `tasks.py`, команда импорта. Картинки уходят в общий `IMPORT_DIR/import_files/`, подкаталог `<xx>` из имени внутри архива сохраняется (`image_relative_name`).
- **AC3.** Прогон без обещанных имён при сессионной раскладке и пустом своём каталоге импорт не запускает и пишет в `session.report` стабильную пометку `SESSION_HAS_NO_OWN_FILES`. `defer_to_active_sessions` сохранён и проверяется раньше — он остаётся страховкой ручных прогонов.
- **AC4.** `cleanup_import_dir` работает в границах своей папки; docstring переписан по-русски. Guard-ы вызывающих (`views.handle_init`, post-import) не тронуты. Общий `import_files` под уборку сессии не попадает — он в корне обмена.
- **AC5.** `remove_session_dirs()` удаляет каталоги сессии в `1c_import` и `1c_temp` после обмена; временный сносится только если в нём не осталось полезных файлов (1С может дослать файл в ту же сессию). Осиротевшее подбирает `cleanup_stale_exchange_dirs` с порогом 24 ч.
- **AC6.** `_import_lock_key` считает ключ от общего корня обмена при сессионной раскладке; ручной прогон и тесты с `tmp_path` ключуются по себе. Сериализация задач сохранена, тест проверяет и равенство ключей, и живой `Retry` с прежней формулировкой.
- **AC7.** `apps/products` + `apps/integrations` + `tests/unit/test_file_routing.py` + `tests/integration/test_onec_import.py` — **692 passed, 1 skipped, 0 failed**. Полный backend-набор — см. Change Log. Black и Flake8 чисто. Mypy по изменённым файлам новых ошибок не даёт: все 9 сообщений вне изменённых диапазонов (`variant_import.py:2167-2168`, `import_products_from_1c.py:488`, `orders/*`, `settings/*`) — они были и до правки.

**Решения по развилкам стори.**

- **Развилка 1 (лок)** — реализована как предписано: ключ от `IMPORT_DIR`, а не от `data_dir`.
- **Развилка 2 (картинки)** — правка команды в двух точках, как предписано. Отдельного CLI-аргумента не заведено.
- **Развилка 3 (легаси-раскладка)** — реализована **пофайлово**, а не покаталожно. Стори допускала «несколько строк» на выбор каталога, но покаталожный выбор здесь неверен: `cleanup_import_dir` после изоляции легаси-папку больше не чистит, поэтому обе раскладки сосуществуют неопределённо долго, и одна картинка товара может лежать в новой, другая — в старой. `_import_base_images(mirror_composition=True)` при частичном разрешении обрезает состав фото — ровно тот сценарий порчи данных, ради которого фолбэк и вводился. Поэтому `VariantImportProcessor` получил атрибут `image_fallback_dirs` (по умолчанию пуст — прежнее поведение) и helper `_resolve_image_source`, а список каталогов задаёт команда: решение о раскладке остаётся у неё.

**Что сделано сверх списка задач и почему.**

- **Подрезка общего `import_files` в задаче уборки.** До изоляции общий каталог картинок вычищался `cleanup_import_dir` вместе со всем каталогом обмена. После изоляции его не чистит ни одна сессия — то есть изменение само по себе вводило неограниченный рост диска. Та же задача AC5 удаляет из него файлы старше 24 ч. Защищённые имена (`SHARED_ROOT_NAMES`) исключают снос самого `import_files`, легаси-раскладки и подпапок типов, накопленных до выката.
- **Комментарии, описывавшие каталог как общий**, переписаны в `views.handle_init`, `import_orchestrator._dispatch_import` и `routing_service.should_route` — иначе следующий читатель получил бы неверную модель.

**Правки чужих тестов (все — ожидания, прибитые к старой раскладке; логика тестов сохранена).**

- `test_import_orchestration.py`, `test_import_orchestration_view.py`, `test_onec_import.py` — три ассерта на `data_dir` в `delay()`, ровно те, о которых предупреждала стори в «Уроках предыдущей стори».
- `tests/unit/test_file_routing.py` — 12 ожиданий раскладки (XML и ZIP теперь под `<sessid>/`, картинки — в общем `import_files/`) плюс `test_orchestrator_uses_import_dir_from_settings`.
- `test_handle_init_cleanup_race.py` (6 ассертов) — правок не потребовал, как и предполагала стори.

**Область, оставленная нетронутой:** `_cleanup_files`, `defer_to_active_sessions`, guard-ы активных сессий, `file_service.py`, `_collect_xml_files`, `_restrict_to_expected`, разовая зачистка 32 276 каталогов.

**⚠️ AC8 закрыт быть не может до выката** — это прод-замер (сутки без «не найден в каталоге обмена» + контрольная выгрузка номенклатуры), процедура в `post-deploy-verification.md`. Статус `done` ставится по нему, а не по мержу.

**Порядок выката:** `celery` и `celery-beat` пересобираются **вместе** с `backend`, после пересборки backend обязателен `docker compose restart nginx` (иначе весь внешний API и обмен 1С падают в 502 на старом IP апстрима). Новая beat-задача требует перезапуска именно `celery-beat`.

---

**Раунд 2 — 7 patch-findings код-ревью закрыты (28.08.2026).**

1. **Коллизия `sessid` с общими каталогами.** `validate_session_segment` теперь
   отклоняет и имена из `SHARED_ROOT_NAMES` — регистронезависимо, потому что
   NTFS и APFS регистр не различают. Без этого `sessid=import_files` давал
   каталог сессии `IMPORT_DIR/import_files`, то есть общий каталог картинок
   целиком, вместе с `cleanup_import_dir` и `remove_session_dirs` этой сессии;
   `sessid=goods` уносил легаси-раскладку, на которой держится фолбэк
   переходного окна. Проверка стоит на входе, а не в уборке: такой каталог
   не должен существовать вовсе.
2. **Уборка осиротевших каталогов больше не смотрит на один `mtime` корня.**
   Каталог удаляется, только если выполнены **все три** условия: имя не
   принадлежит сессии в `PENDING`/`STARTED`/`IN_PROGRESS`; в дереве нет файла
   свежее порога (`_newest_mtime`); имя не занято общим каталогом. `IN_PROGRESS`
   одного было мало — сессия лежит в `PENDING`, пока её задача стоит в очереди
   за локом, а файл уже на диске. TOCTOU между проверкой и `rmtree` закрыт
   изъятием каталога переименованием в `.stale-<name>-<hex>` с пересверкой
   возраста; каталог, куда файл приехал в окне, возвращается обмену. Хвосты
   прошлых прогонов (`.stale-*`) доудаляются в начале следующего.
3. **Подрезка общего `import_files` по возрасту убрана.** Контракт связи «обмен
   изображениями ↔ будущий XML» не задаёт, и 1С её не передаёт: картинка старше
   суток остаётся законным источником для `goods.xml`, который приедет завтра.
   Правка предыдущего раунда прямо ломала AC2. Рост каталога — реальная
   проблема, но лечится не возрастом файла: заведён **tech-debt п. 27** с
   указанием искать критерий по фактической ссылочности (картинка перенесена в
   `media/` и не упомянута ни одним товаром/вариантом), а первым шагом — снять
   размер каталога на проде.
4. **`defer_to_active_sessions` ограничен общим ручным каталогом.** Guard писался
   под раскладку, где `data_dir` у всех один. В сессионной раскладке чужого в
   папке нет по построению, а активная соседка есть практически всегда (1С шлёт
   `mode=import` на файл и `mode=complete` следом каждые пару секунд) — guard
   означал «изолированный `mode=complete` со своим XML не импортирует почти
   никогда». Ветка `session_dir_has_no_own_files` упрощена: пересечься с
   `defer` она больше не может.
5. **Каталог завершённой изолированной сессии удаляется независимо от чужих
   `IN_PROGRESS`.** Исторический guard оставлен только для ручного прогона по
   общему каталогу. Именно из-за него после изоляции папки не удалялись бы почти
   никогда — тот же механизм, что дал на проде 32 276 каталогов.
6. **Единый приёмочный тест AC1** (`test_locked_dir_defers_neighbour_and_both_sessions_complete`):
   занятый **общий** лок → реальная задача сессии B получает `Retry` с прежней
   формулировкой → лок освобождён → `mode=complete` сессии A читает только свой
   сегмент, файл B цел → B отрабатывает свой сегмент → обе `COMPLETED`. Раньше
   это проверялось двумя разными тестами, и связка «очередь сохранилась И каждая
   прочитала своё» приёмкой не покрывалась.
7. **AC2 дополнен тестом для `ProductVariant`** (`test_offers_variant_binds_image_from_shared_dir`):
   `_images_base_dir` вызывается дважды — с `xml_subdir="goods"` и `"offers"`, —
   и проверки `Product.base_images` было мало. XML настоящий; изображений
   реальный `offers.xml` не несёт (во всём корпусе `data/import_1c/offers/`,
   31 файл, ноль тегов `<Картинка>` — состав фото 1С отдаёт только в `goods.xml`),
   поэтому ссылка добавляется к уже распарсенному предложению в той же форме
   `import_files/<xx>/<file>.jpg`, какую пишет 1С. Родительский товар создан
   фабрикой: в фикстурном `goods.xml` родителей этих предложений нет, а выдумывать
   XML проект запрещает.

**Попутно исправлено:** docstring теста расписания beat нёс инвертированное
утверждение из Dev Notes стори (будто `celery.py` затирает настройки), хотя замер
раунда 1 показал обратное. Переписан по факту: тест смотрит в `app.conf` — то есть
в эффективное расписание — и остаётся верным при любой перестановке двух мест
объявления.

**Deferred-findings не трогались:** пять `[Review][Defer]` записаны в
`deferred-work.md` и остаются открытыми.

**AC8 по-прежнему открыт** — это прод-замер, статус `done` ставится по нему.

---

**Раунд 3 — закрыт tech-debt п. 27 (рост общего `import_files`), 28.08.2026.**

Finding 3 ревью снял уборку общего каталога картинок как ломающую AC2 — и тем
самым вернул неограниченный рост. Замер прода показал, что откладывать нельзя:

| Что | Значение |
|---|---|
| `1c_import` / `1c_temp` | пусты — разовая зачистка Alex сделана, катим на чистое |
| `media/products/base` | 3,6 ГБ / 15 438 файлов |
| `media/products/variants` | 1,3 ГБ / 5 889 файлов |
| `media/products` всего | 6,4 ГБ |
| Диск | **свободно 20 ГБ из 79 (74 % занято)** |

Полная выгрузка с принудительными картинками положила бы в общий каталог
практически весь каталог исходных JPEG — 5–8 ГБ, навсегда. То есть п. 27 был
условием прод-проверки, а не отложенной уборкой.

**Находка, снявшая необходимость изобретать критерий.** Уборка картинок в команде
уже существовала (`_cleanup_files`, «Очистка папок с изображениями») и целилась в
`<data_dir>/goods/import_files`. После изоляции картинки переехали в общий
`IMPORT_DIR/import_files`, и эта уборка просто **потеряла цель** — вот откуда рост.
Вдобавок `_save_image_if_not_exists` (`variant_import.py:497-514`) с самого начала
спроектирован под исчезнувший исходник: при наличии копии в хранилище он берёт её
оттуда, и состав фото не обрезается. Значит ссылочный критерий — не изобретение, а
то, подо что код уже написан; возраст не нужен вовсе.

**Сделано (два слоя, оба без порога времени):**

1. `VariantImportProcessor.consumed_image_sources` копит исходники, для которых
   копия в хранилище **подтверждена**; `Command._cleanup_consumed_images` их
   удаляет сразу после успешного прогона. Область строго ограничена
   `ONEC_EXCHANGE["IMPORT_DIR"]` — ручной корпус `ONEC_DATA_DIR` (`data/import_1c/`)
   не трогается никогда, это входные данные тестов и повторных прогонов.
2. `_prune_imported_exchange_images` в периодической задаче — страховка для
   прогонов, упавших между переносом и уборкой: файл удаляется, только если копия
   есть в `products/base/<xx>/<name>` либо `products/variants/<xx>/<name>`.

Мёртвый параметр `file_type` из `_cleanup_files` убран вместе со старым блоком —
его единственным потребителем был именно он.

**Осознанно оставлено:** превью ниже `MIN_IMAGE_SIZE_BYTES` (100 КБ) импорт не
сохраняет, копии у них не появляется, ссылочный критерий их не удаляет. Класс
ограничен — имена 1С детерминированы, повторная выгрузка их перезаписывает, — и
задача логирует их число и объём (`Exchange images kept (no stored copy)`).
**Решение Alex 28.08.2026: оставить и замерить через неделю после выката.**
Отвергнуты: удаление по «товар уже импортирован» (снесёт исходник для goods.xml,
стоящего в очереди) и удаление по длинному возрасту (тот же класс, что отвергнутые
ревью 24 часа).

**RED:** с убранным прод-кодом падают `test_command_deletes_sources_it_stored` и
`test_periodic_prune_removes_only_stored_copies`. Два других теста класса
(`test_reimport_after_cleanup_keeps_composition`, `test_manual_corpus_is_never_touched`)
на старом коде зелёные — они сторожат инварианты, которые правка не должна сломать,
а не дефект.

### File List

**Продакшен-код**

- `backend/apps/integrations/onec_exchange/routing_service.py` — ядро изоляции: сессионный `import_dir`, валидация `sessid` (сегмент пути + запрет коллизии с `SHARED_ROOT_NAMES`), общий маршрут картинок, `remove_session_dirs`, модульные хелперы раскладки
- `backend/apps/integrations/onec_exchange/import_orchestrator.py` — своя копия пути переведена на каталог сессии; маршрутизация распакованного и оба `.dry_run`
- `backend/apps/integrations/onec_exchange/views.py` — комментарий `handle_init` про общий каталог
- `backend/apps/products/tasks.py` — ключ лока от общего корня, дубль маршрутизации распакованного, пометка AC3, удаление каталогов сессии, задача `cleanup_stale_exchange_dirs` (+ хелперы `_newest_mtime`, `_quarantine_exchange_dir`, `_remove_quarantined_dir`, константы `ACTIVE_SESSION_STATUSES`/`QUARANTINE_PREFIX`); `defer_to_active_sessions` ограничен общим каталогом; post-import cleanup удаляет свой каталог независимо от чужих `IN_PROGRESS`
- `backend/apps/products/management/commands/import_products_from_1c.py` — `_images_base_dir` (Развилки 2 и 3), две точки вызова; `_cleanup_consumed_images` вместо потерявшей цель уборки каталогов картинок, из `_cleanup_files` убраны мёртвые параметры `data_dir`/`file_type`
- `backend/apps/products/services/variant_import.py` — `image_fallback_dirs` + `_resolve_image_source`, три точки разрешения исходника картинки; `consumed_image_sources` (учёт потреблённых исходников, tech-debt п. 27)
- `backend/freesport/settings/base.py` — регистрация `cleanup-stale-exchange-dirs` (эффективное расписание)
- `backend/freesport/celery.py` — дубль регистрации + комментарий по факту замера

**Тесты**

- `backend/apps/products/tests/test_exchange_dir_isolation.py` — новый: AC1-AC6, **31 тест** (20 в раунде 1 + 7 по findings ревью + 4 по tech-debt п. 27)
- `backend/apps/products/tests/test_import_cleanup_race.py` — вызов `_cleanup_files` под новую сигнатуру
- `backend/apps/products/tests/integration/test_import_orchestration.py` — ожидания `data_dir`
- `backend/apps/integrations/tests/test_import_orchestration_view.py` — ожидание `data_dir`
- `backend/tests/integration/test_onec_import.py` — ожидания `data_dir` и пути маршрутизации
- `backend/tests/unit/test_file_routing.py` — ожидания раскладки

**Документация**

- `docs/integrations/1c/import-process.md` — раздел «Раскладка каталога обмена», правило ключа лока, п. 6 про прогон без обещания; раздел «Уборка» переписан по findings 2/3/5
- `_bmad-output/planning-artifacts/tech-debt.md` — п. 26 закрыт и дополнен; п. 27 заведён и закрыт по основной части (ссылочная уборка), остаток превью — под наблюдением
- `_bmad-output/implementation-artifacts/deferred-work.md` — пять `[Review][Defer]` находок ревью
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — статус стори
- `_bmad-output/implementation-artifacts/Story/onec-exchange-dir-isolation.md` — этот файл

### Change Log

| Дата | Изменение |
|---|---|
| 2026-08-28 | Реализована изоляция каталога обмена 1С по сессии (AC1-AC6). Ключ лока переведён на общий корень, чтобы сериализация задач сохранилась. Картинки остались общими, добавлен пофайловый фолбэк на легаси-раскладку. Уборка сужена до своего каталога, добавлена периодическая `cleanup_stale_exchange_dirs` (порог 24 ч). Регресс зелёный, AC8 ждёт прод-замера. Статус → `review`. |
| 2026-08-28 | Закрыты 7 patch-findings код-ревью: запрет `sessid`, совпадающего с общими каталогами; уборка осиротевших каталогов учитывает живые сессии, свежесть вложенных файлов и закрывает TOCTOU изъятием каталога переименованием; подрезка общего `import_files` по возрасту снята (ломала AC2) и вынесена в tech-debt п. 27; `defer_to_active_sessions` ограничен общим ручным каталогом; каталог завершённой изолированной сессии удаляется независимо от чужих `IN_PROGRESS`; добавлены единый приёмочный тест AC1 и тест AC2 для `ProductVariant`. Регресс: затронутые приложения 699 passed / 1 skipped, полный backend-набор 3214 passed / 75 skipped, 0 failed. Статус → `review`. |
