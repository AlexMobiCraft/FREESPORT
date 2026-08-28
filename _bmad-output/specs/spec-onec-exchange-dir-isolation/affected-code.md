# Карта затронутого кода

Компаньон к `SPEC.md`. Все координаты сверены чтением файлов на коммите `0fc2e4dc` (28.08.2026). Номера строк — ориентир, а не якорь: перед правкой каждого символа обязателен `npx gitnexus impact <symbol> --direction upstream`.

## T1. Раскладка каталога обмена — по сессии (ядро, CAP-1, CAP-2)

### `backend/apps/integrations/onec_exchange/routing_service.py`

| Координата | Что там сейчас | Что требуется |
|---|---|---|
| `FileRoutingService.__init__`, стр. 79-83 | `self.import_dir = self.import_base` с комментарием `FIXED: Import directory should be shared/root` | `self.import_dir = self.import_base / session_id`. Комментарий снять — он фиксирует ровно то поведение, которое чинится |
| `route_file` / `_ensure_import_dir`, стр. 96+ | Все подпапки типа создаются под `self.import_dir` | Исключение для картинок: если маршрут — `import_files/…`, файл кладётся в **общий** `import_base / "import_files"` (вариант 1 развилки) |
| `cleanup_import_dir`, стр. 212 | `if item.name == ".dry_run": continue` — флаг защищён от удаления | Защита сохраняется, но флаг теперь живёт в `import_base`, а не в сессионном каталоге (см. ниже) |

### Флаг `.dry_run` — остаётся в общем `import_base`

Второе исключение из изоляции. Флаг — переключатель режима, ставится оператором вручную по известному пути; уехав в сессионный каталог, он стал бы невидим.

| Координата | Что там |
|---|---|
| `import_orchestrator.py:310` | `dry_run = (self.import_dir / ".dry_run").exists()` — проверка перед dispatch |
| `import_orchestrator.py:421-424` | `if not dry_run and (self.import_dir / ".dry_run").exists():` — повторная проверка в `finalize_batch` |
| `routing_service.py:212` | Пропуск при удалении в `cleanup_import_dir` |
| `file_service.py:261-262` | Пропуск при auto-cleanup |

Все четыре точки после изоляции должны смотреть на `import_base / ".dry_run"`, а не на сессионный каталог.

Маркер `.exchange_complete` изоляции **не касается** — он живёт в `session_dir` временного каталога (`file_service.py:283-296`), который и так был сессионным.

### `backend/apps/integrations/onec_exchange/import_orchestrator.py`

⚠️ У оркестратора **собственная** копия пути, не через `FileRoutingService` — это второй, независимый носитель допущения об общем каталоге.

| Координата | Что там сейчас |
|---|---|
| `__init__`, стр. 47 | `self.import_dir = Path(str(settings.ONEC_EXCHANGE["IMPORT_DIR"]))` |
| `_unpack_zips`, стр. 202, 214-217 | `self.import_dir.glob("*.zip")`, распаковка с zip-slip guard относительно `self.import_dir` |
| `_route_unpacked_files`, стр. 260, 287 | `file_path = self.import_dir / unpacked_name`, `dest_dir = self.import_dir / target_subdir` |
| `_dispatch_import`, стр. 310, 344-346 | `.dry_run` ищется в `self.import_dir`; в задачу передаётся `str(self.import_dir)` как `data_dir` |
| `_dispatch_or_dryrun`, стр. 468, 488-490 | Распаковка zip и второй dispatch с `str(self.import_dir)` |
| `execute` / `_resolve_session`, стр. 67-70 | Guard «сессия `IN_PROGRESS` → не трогать `import_dir`» |

Задаче должен передаваться `data_dir` = каталог **своей** сессии.

### `backend/apps/products/management/commands/import_products_from_1c.py`

**Править не нужно.** Команда уже принимает `data_dir` параметром (`handle`, стр. 338-341: `data_dir = options["data_dir"]`, при пустом — фолбэк на `settings.ONEC_DATA_DIR`), а `_collect_xml_files` (стр. 949) собирает файлы относительно переданного `base_dir` — заработает как есть.

### `backend/apps/products/services/variant_import.py` — развязка путей картинок

Единственное место, где `base_dir` для XML и для изображений расходятся. Путь из XML (`import_files/xx/file.jpg`) нормализуется и ищется от `base_dir`:

| Координата | Что там |
|---|---|
| `_get_effective_min_size`, стр. 405, 420 | `source_path = Path(base_dir) / normalized_path` |
| `_import_base_images`, стр. 720, 744, 754 | `source_path = Path(base_dir) / normalized_path` |
| `_import_variant_images`, стр. 1039, 1064, 1074 | `source_path = Path(base_dir) / normalized_path` |
| Вызовы из команды импорта | `import_products_from_1c.py:660`, `:706` — `base_dir=base_dir` |

При общем `import_files` вне сессионного каталога один и тот же `base_dir` больше не годится для XML и для картинок — развязка обязательна, иначе CAP-2 не выполняется.

## T2. `mode=complete` больше не сгребает каталог (CAP-3)

### `backend/apps/products/tasks.py`

| Координата | Что там сейчас | Что требуется |
|---|---|---|
| стр. 402-423, `defer_to_active_sessions` | Прогон без `promised_filenames` уступает дорогу, если жива хоть одна `IN_PROGRESS` сессия. Считывается один раз на старте задачи | **Не удалять** — остаётся страховкой для ручных прогонов с `data_dir` по умолчанию |
| стр. 425-430+ | `call_command(..., data_dir=effective_data_dir)` | При сессионной раскладке прогон без обещанных имён видит только свой пустой каталог. Убедиться, что он завершается `COMPLETED`, а не пытается импортировать пустоту |
| `session.report`, стр. 480-482 | Отчёт сессии накапливается строками вида `[{timestamp}] …` | Сюда пишется пометка «своих файлов нет» — решение Alex. Отдельного поля и миграции не требуется; тест CAP-3 вешается на подстроку в `report` |

## T3. Уборка (CAP-4, CAP-5)

### `backend/apps/integrations/onec_exchange/routing_service.py:192` — `cleanup_import_dir`

Сейчас метод обходит `self.import_dir.iterdir()` и удаляет всё, кроме `.dry_run` — при общем каталоге это удаление файлов соседей. Docstring прямо описывает общий каталог («As the import directory is shared across sessions…») и подлежит переписыванию.

После изоляции метод чистит **свою** папку, чем снимается `risk: CRITICAL` (13 impacted, 7 процессов): удаление физически не может задеть соседа.

⚠️ **Обязателен `npx gitnexus impact cleanup_import_dir --direction upstream` до правки** — метод уже правился двумя хотфиксами (`ff0bbc0a`, `057afc41`).

Известные вызывающие:

- `backend/apps/integrations/onec_exchange/views.py:453` — `cleanup_import_dir(force=True)` внутри `handle_init` (guard «пропуск при активных сессиях», стр. 427-453)
- `backend/apps/products/tasks.py:502` — post-import cleanup (guard `other_active`, стр. 486-506)
- `backend/apps/integrations/onec_exchange/import_orchestrator.py:328` — комментарий о порядке относительно `cleanup_import_dir(force=True)`
- `backend/apps/integrations/tests/test_handle_init_cleanup_race.py` — 6 ассертов на вызовы/невызовы метода; при смене семантики их поведение перепроверить

### Новое: удаление каталога сессии и подбор осиротевших

- Удалять каталог сессии в `1c_temp` после завершения обмена — сегодня копится 32 276 пустых папок, по одной на сессию.
- Периодическая уборка сессионных каталогов старше **24 часов** в `1c_temp` и `1c_import`: при падении воркера папка иначе останется навсегда. Механизм (предположительно `celery-beat`) — см. Assumptions в `SPEC.md`.

Разовая зачистка уже накопленных 32 276 каталогов **в область работы не входит** — Alex делает её вручную (см. Non-goals в `SPEC.md`). Писать миграцию или management-команду под это не нужно.

## T4. Тесты (RED-первым для CAP-1)

| Тест | Покрывает | Требование |
|---|---|---|
| Две сессии, разные `session_key`, файлы одного типа (`rests_1_1`, `rests_1_2`), задачи последовательно при занятом локе | CAP-1 | Обе `COMPLETED`, каждая прочитала свой файл. **На текущем коде обязан упасть (RED)**, иначе не ловит дефект |
| `mode=complete` при наличии чужих сессионных каталогов | CAP-3 | Ничего из них не читает и не удаляет |
| XML из сессионного каталога + картинка в общем `import_files` | CAP-2 | Изображение найдено и привязано |
| `cleanup_import_dir` сессии A против каталога сессии B | CAP-4 | Каталог B не тронут |

Запуск (одна БД на compose-проект, параллельные прогоны невозможны):

```bash
cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend \
  pytest -x apps/products apps/integrations
```

Реальные выгрузки — из `data/import_1c/`; синтетические XML запрещены.

## Перед коммитом

```bash
npx gitnexus detect-changes --scope all
```

Затронутыми должны оказаться только перечисленные выше символы и их процессы.
