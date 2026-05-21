# Story 36.1: Перенос файлов импорта 1С из публичного MEDIA_ROOT

**Epic:** 36 — Critical Security & Export Fixes (Week 1)
**Story ID:** 36.1
**Status:** review
**Priority:** 🔴 CRITICAL
**Source:** tech-debt.md #15

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

---

## User Story

Как Security Engineer,
я хочу, чтобы файлы импорта 1С не размещались в публично доступном `MEDIA_ROOT`,
чтобы XML-данные контрагентов, цен и остатков не утекали по прямой ссылке.

---

## Контекст и суть уязвимости (tech-debt #15)

Каталог приёма файлов обмена с 1С (`1c_import`) и каталог чанковой загрузки (`1c_temp`) сейчас лежат внутри `MEDIA_ROOT`:

```python
# backend/freesport/settings/base.py:302-303
ONEC_EXCHANGE = {
    ...
    "TEMP_DIR": MEDIA_ROOT / "1c_temp",     # чанки загрузки
    "IMPORT_DIR": MEDIA_ROOT / "1c_import", # маршрутизированные файлы импорта
}
```

`MEDIA_ROOT` раздаётся nginx как статика (`location /media/` → `alias /var/www/media/`). Файлы обмена содержат **коммерчески чувствительные данные**: прайс-листы, остатки складов, реквизиты контрагентов (ИНН, наименования ООО/ИП). Подобрав URL вида `https://<домен>/media/1c_import/<sessid>/prices/prices_*.xml`, анонимный пользователь может скачать эти данные.

**Частичная защита уже есть**, но она неполная:

- nginx содержит `location /media/1c_temp/ { return 404; }` (`docker/nginx/conf.d/default.conf:86-88`) — закрыт **только** `1c_temp`.
- `1c_import` **не закрыт ничем** — это и есть дыра.

**Рекомендация аудита:** перенести оба каталога в приватную директорию вне web-root, а не латать nginx-правилами для каждого подкаталога.

### Готовый прецедент в проекте

Аудиторские логи обмена 1С уже хранятся приватно по паттерну `BASE_DIR / "var" / ...`:

```python
# backend/apps/integrations/onec_exchange/views.py:117-127
EXCHANGE_LOG_SUBDIR = "1c_exchange/logs"

def _get_exchange_log_dir() -> Path:
    """... BASE_DIR / "var" / EXCHANGE_LOG_SUBDIR которая НЕ внутри
    MEDIA_ROOT (and therefore not publicly accessible)."""
    custom = getattr(settings, "EXCHANGE_LOG_DIR", None)
    if custom:
        return Path(custom)
    return Path(settings.BASE_DIR) / "var" / EXCHANGE_LOG_SUBDIR
```

Каталог `backend/var/1c_exchange/` уже существует в репозитории. Эта story расширяет тот же паттерн `var/` на каталоги приёма файлов импорта.

> **Не путать с `ONEC_DATA_DIR`** (`data/import_1c/`) — это РЕАЛЬНЫЕ тестовые XML для ручного импорта через management-команды. Их трогать НЕ нужно. Story касается только **рантайм-каталогов HTTP-обмена** (`1c_temp`, `1c_import`).

---

## Acceptance Criteria

### AC-1: Файлы импорта сохраняются в приватную директорию вне MEDIA_ROOT

**Given** входящие файлы обмена с 1С (контрагенты, товары, цены, остатки),
**When** они принимаются (`mode=file`) и распаковываются/маршрутизируются (`mode=import`/`mode=complete`),
**Then** они сохраняются в приватную директорию вне `MEDIA_ROOT`, которая не раздаётся nginx.

### AC-2: Файлы недоступны по media-URL

**Given** приватную директорию импорта,
**When** анонимный пользователь запрашивает файл по предполагаемому media-URL (`/media/1c_import/...`, `/media/1c_temp/...`),
**Then** сервер возвращает 404 — файл физически отсутствует под `MEDIA_ROOT` и не раздаётся ни nginx, ни Django dev-сервером.

### AC-3: Пайплайн импорта работает без регрессий

**Given** существующий пайплайн импорта (`ImportOrchestratorService`, `FileRoutingService`, `FileStreamService`, Celery-задача `process_1c_import_task`, `VariantImportProcessor`),
**When** путь хранения изменён на приватный,
**Then** полный цикл обмена (приём чанков → маршрутизация → распаковка ZIP → асинхронный импорт товаров и контрагентов) отрабатывает без регрессий.

### AC-4: Единый источник пути — устранение хардкода MEDIA_ROOT

**Given** код проекта,
**When** выполняется поиск хардкода `MEDIA_ROOT / "1c_import"` / `MEDIA_ROOT / "1c_temp"`,
**Then** все обращения к каталогам обмена идут через `settings.ONEC_EXCHANGE["IMPORT_DIR"]` / `["TEMP_DIR"]`; прямых склеек с `MEDIA_ROOT` в продакшен-коде не остаётся.

---

## Анализ кодовой базы (что и где менять)

### Проблема №1 — определение путей в settings

`backend/freesport/settings/base.py:296-303` — `TEMP_DIR`/`IMPORT_DIR` склеены с `MEDIA_ROOT`. Это корень проблемы.

### Проблема №2 — хардкод в оркестраторе

`backend/apps/integrations/onec_exchange/import_orchestrator.py:46`:

```python
def __init__(self, sessid: str, filename: str = "unknown"):
    ...
    self.import_dir = Path(settings.MEDIA_ROOT) / "1c_import"  # ❌ ИГНОРИРУЕТ ONEC_EXCHANGE["IMPORT_DIR"]
```

Оркестратор **не использует** `ONEC_EXCHANGE["IMPORT_DIR"]`, а строит путь сам. Даже если поправить settings — оркестратор продолжит писать в `MEDIA_ROOT`. Это нужно исправить обязательно.

### Проблема №3 — хардкод fallback в Celery-задаче

`backend/apps/products/tasks.py:71`:

```python
target_import_dir = Path(data_dir) if data_dir else (Path(settings.MEDIA_ROOT) / "1c_import")  # ❌ fallback на MEDIA_ROOT
```

В штатном потоке `data_dir` всегда передаётся (`process_1c_import_task.delay(session.pk, str(self.import_dir))`), но fallback-ветка остаётся источником утечки и хардкода. Привести к `settings.ONEC_EXCHANGE["IMPORT_DIR"]`.

### Уже корректно (НЕ менять логику, только проверить)

`routing_service.py:76,79` и `file_service.py:150` **уже** читают путь из настроек:

```python
temp_dir = settings.ONEC_EXCHANGE.get("TEMP_DIR", Path(settings.MEDIA_ROOT) / "1c_temp")
import_dir = settings.ONEC_EXCHANGE.get("IMPORT_DIR", Path(settings.MEDIA_ROOT) / "1c_import")
```

После исправления `base.py` они автоматически начнут писать в приватный каталог. Fallback-значения на `MEDIA_ROOT` можно оставить (они срабатывают, только если ключ вообще отсутствует) — но в рамках AC-4 их разумно тоже привести к приватному пути или убрать, т.к. ключи всегда заданы в `base.py`.

### Инфраструктура — критично для production

В **dev** (`docker/docker-compose.yml`) сервисы `backend` и `celery` монтируют исходники целиком: `../backend:/app`. Поэтому каталог `/app/var/...` автоматически общий между ними — дополнительный volume в dev НЕ нужен.

В **production** (`docker/docker-compose.prod.yml`) общий каталог обмена между `backend` (пишет файлы) и `celery` (читает и импортирует) обеспечивается **только** монтированием `../data/prod/media:/app/media` на оба сервиса (строки 200 и 197-200). Если перенести `1c_import`/`1c_temp` в `/app/var/...` **без нового общего volume**, то Celery-воркер в проде **не увидит файлы, записанные backend-ом, и импорт сломается**.

🔴 **Поэтому в `docker-compose.prod.yml` обязательно добавить общий bind-mount приватного каталога обмена на оба сервиса `backend` и `celery`** (например, `../data/prod/onec_private:/app/var/onec`). `celery-beat` этот каталог не требует.

---

## Технические требования и рекомендуемое решение

### Шаг 1 — settings (`backend/freesport/settings/base.py`)

Заменить склейку с `MEDIA_ROOT` на приватный путь по паттерну `var/`, с поддержкой override через переменную окружения (как у `ONEC_DATA_DIR` и `EXCHANGE_LOG_DIR`):

```python
# Приватный корень для рантайм-каталогов обмена с 1С (вне MEDIA_ROOT — не раздаётся nginx).
# Переопределяется через ONEC_PRIVATE_DIR для production-окружения.
ONEC_PRIVATE_DIR = Path(
    os.environ.get("ONEC_PRIVATE_DIR", str(BASE_DIR / "var" / "onec"))
)

ONEC_EXCHANGE = {
    ...
    "TEMP_DIR": ONEC_PRIVATE_DIR / "1c_temp",
    "IMPORT_DIR": ONEC_PRIVATE_DIR / "1c_import",
    ...
}
```

- Имена подкаталогов `1c_temp`/`1c_import` сохранить — это снижает diff и не ломает логику маршрутизации.
- `os` и `Path` уже импортированы в `base.py` (проверь перед добавлением).

### Шаг 2 — оркестратор (`import_orchestrator.py:46`)

```python
def __init__(self, sessid: str, filename: str = "unknown"):
    self.sessid = sessid
    self.filename = filename
    self.import_dir = Path(str(settings.ONEC_EXCHANGE["IMPORT_DIR"]))
```

`Path(str(...))` — чтобы корректно отрабатывать и при значении-`Path`, и при значении-`str` (в тестах `conftest.py` ключ задаётся строкой `"/tmp/1c_import"`).

### Шаг 3 — Celery-задача (`tasks.py:71`)

```python
target_import_dir = (
    Path(data_dir) if data_dir
    else Path(str(settings.ONEC_EXCHANGE["IMPORT_DIR"]))
)
```

### Шаг 4 — Docker production (`docker/docker-compose.prod.yml`)

Добавить общий bind-mount приватного каталога обмена и переменную `ONEC_PRIVATE_DIR` на сервисы `backend` и `celery`:

```yaml
# сервис backend (volumes)
- ../data/prod/onec_private:/app/var/onec
# сервис celery worker (volumes)
- ../data/prod/onec_private:/app/var/onec
```

```yaml
# environment обоих сервисов
- ONEC_PRIVATE_DIR=/app/var/onec
```

Каталог `data/prod/onec_private/` создаётся на хосте при деплое (по аналогии с `data/prod/media`, `data/prod/static`).

### Шаг 5 — Docker dev (`docker/docker-compose.yml`)

Дополнительный volume **не требуется** — `backend` и `celery` уже монтируют `../backend:/app`, поэтому `/app/var/onec` общий. Достаточно убедиться, что каталог создаётся автоматически (`mkdir(parents=True, exist_ok=True)` в `_ensure_import_dir` / `FileStreamService` уже это делает).

### Шаг 6 — nginx (`docker/nginx/conf.d/default.conf` и `local.conf`)

Блок `location /media/1c_temp/ { return 404; }` (default.conf:86-88) после переноса становится «мёртвым» — каталога под `MEDIA_ROOT` больше нет.

**Рекомендация:** оставить блок как defense-in-depth (на случай ошибочного rollback или ручного создания каталога) — но это решение на усмотрение; допустимо и удалить. Если оставляешь — добавь комментарий, что каталог перенесён в Story 36.1 и блок оставлен как страховка. **Никаких новых `location`-правил для `1c_import` добавлять НЕ нужно** — каталог физически вне `MEDIA_ROOT`.

### Что НЕ менять

- `ONEC_DATA_DIR` / `data/import_1c/` — реальные тестовые XML для ручного импорта.
- Логику маршрутизации (`XML_ROUTING_RULES`, `_route_unpacked_files`), Zip Slip protection — переезд не затрагивает алгоритмы.
- `MEDIA_ROOT`, `MEDIA_URL`, `STATIC_*` — остаются как есть.
- `_get_exchange_log_dir()` / `EXCHANGE_LOG_*` — логи обмена уже приватны.

---

## Структура файлов (изменения)

```
backend/
  freesport/settings/base.py                              [MODIFY] — ONEC_PRIVATE_DIR + TEMP_DIR/IMPORT_DIR
  apps/integrations/onec_exchange/import_orchestrator.py   [MODIFY] — import_dir из ONEC_EXCHANGE
  apps/products/tasks.py                                   [MODIFY] — fallback на ONEC_EXCHANGE["IMPORT_DIR"]
  apps/integrations/onec_exchange/routing_service.py       [REVIEW] — при AC-4: убрать MEDIA_ROOT-fallback
  apps/integrations/onec_exchange/file_service.py          [REVIEW] — при AC-4: убрать MEDIA_ROOT-fallback

docker/
  docker-compose.prod.yml                                  [MODIFY] — общий volume + ONEC_PRIVATE_DIR
  nginx/conf.d/default.conf                                [REVIEW] — комментарий к /media/1c_temp/ блоку

backend/
  tests/unit/test_file_routing.py                          [REVIEW/MODIFY] — проверка приватного пути
  tests/integration/                                       [CREATE/MODIFY] — e2e импорт на приватном пути
```

---

## Тесты

> **КРИТИЧНО (правило проекта):** для тестов импорта 1С использовать ТОЛЬКО реальные XML из `data/import_1c/`. Синтетические XML не создавать.

### Unit

**Файл:** `backend/tests/unit/test_file_routing.py` (уже существует — расширить)

- `test_service_uses_import_dir_from_settings` уже проверяет чтение `IMPORT_DIR` из settings — убедиться, что проходит.
- Добавить тест: `settings.ONEC_EXCHANGE["IMPORT_DIR"]` и `["TEMP_DIR"]` НЕ являются подкаталогами `settings.MEDIA_ROOT` (`assert MEDIA_ROOT not in IMPORT_DIR.parents`).
- Добавить тест на `ImportOrchestratorService`: `service.import_dir` равен `settings.ONEC_EXCHANGE["IMPORT_DIR"]`, а не `MEDIA_ROOT / "1c_import"`.

**Файл:** проверить `backend/tests/unit/conftest.py:24-27` — там `IMPORT_DIR`/`TEMP_DIR` уже мокаются строками `/tmp/...`. После правок оркестратора (`Path(str(...))`) тесты должны остаться зелёными.

### Integration / E2E

**Каталог:** `backend/tests/integration/`

- Полный цикл HTTP-обмена: `mode=checkauth` → `mode=init` → `mode=file` (чанки реальных файлов из `data/import_1c/`) → `mode=import`/`mode=complete` → проверка, что `ImportSession` дошла до `COMPLETED` и товары/контрагенты импортированы.
- Проверить, что в ходе цикла файлы физически создаются под `ONEC_EXCHANGE["IMPORT_DIR"]`, а под `MEDIA_ROOT` каталоги `1c_import`/`1c_temp` НЕ появляются.
- Изолировать каталоги через `settings`-override на `tmp_path` (паттерн как `EXCHANGE_LOG_DIR` в `test_onec_export.py:154-158`), чтобы тест не писал в реальный `var/`.

**Покрытие:** изменённые ветки `ImportOrchestratorService.__init__`, `process_1c_import_task` fallback — ≥ 90% (модуль интеграции — критический).

### Запуск

```bash
make test-unit
docker compose --env-file .env -f docker/docker-compose.test.yml exec backend \
  pytest -xvs tests/unit/test_file_routing.py
make test-integration
```

---

## Связанные истории

- **Эпик 36** — security/bugfix-спринт от 2026-05-18. Параллельно: 36.2 (доставка в XML-экспорте), 36.3 (хардкод SITE_URL) — независимы, общих файлов нет.
- **Прецедент:** приватные логи обмена (`var/1c_exchange/logs`, `views.py`) — та же идея `var/`-каталога, переиспользуется паттерн.
- **Не блокирует и не блокируется** другими историями эпика.

---

## Примечания для разработчика

1. **Проверь импорты в `base.py`** — `os` и `Path` должны быть уже импортированы (используются для `ONEC_DATA_DIR`). Если нет — добавь.
2. **Самая частая ошибка здесь — забыть про оркестратор.** Правка только `base.py` НЕ закроет уязвимость: `import_orchestrator.py:46` строит путь сам. Меняй оба места.
3. **Production без общего volume = сломанный импорт.** Celery-воркер и backend — разные контейнеры; без общего bind-mount `/app/var/onec` воркер не увидит файлы. Это самый рискованный пункт story — не пропусти Шаг 4.
4. **Не трогай `data/import_1c/`** — это `ONEC_DATA_DIR`, реальные тестовые XML, а не рантайм-каталог обмена.
5. **Тестовые settings** (`backend/tests/unit/conftest.py`) уже задают `IMPORT_DIR`/`TEMP_DIR` строками — поэтому в коде используй `Path(str(...))`, иначе тесты упадут на склейке `str / str`.
6. **`mkdir` уже есть** в `_ensure_import_dir` (`routing_service.py:100`) и `FileStreamService` — приватный каталог создастся автоматически при первом обмене, отдельная инициализация не нужна.
7. После правок прогони полный e2e-цикл импорта на реальных файлах из `data/import_1c/` — это единственный надёжный способ убедиться в отсутствии регрессий (AC-3).

---

## Definition of Done

- [x] `base.py`: `TEMP_DIR`/`IMPORT_DIR` указывают на приватный каталог вне `MEDIA_ROOT`, с override через `ONEC_PRIVATE_DIR`
- [x] `import_orchestrator.py`: `import_dir` берётся из `ONEC_EXCHANGE["IMPORT_DIR"]`
- [x] `tasks.py`: fallback `process_1c_import_task` приведён к `ONEC_EXCHANGE["IMPORT_DIR"]`
- [x] Хардкода `MEDIA_ROOT / "1c_import"` / `"1c_temp"` в продакшен-коде не осталось (AC-4)
- [x] `docker-compose.prod.yml`: добавлен общий volume `/app/var/onec` на `backend` и `celery` + `ONEC_PRIVATE_DIR`
- [x] nginx-блок `/media/1c_temp/` пересмотрен (оставлен с комментарием либо удалён)
- [x] Unit-тесты: путь импорта не под `MEDIA_ROOT`; оркестратор использует settings
- [x] Integration-тест: полный цикл обмена на реальных XML из `data/import_1c/` проходит без регрессий
- [x] Файлы импорта недоступны по `/media/...`-URL (AC-2)
- [x] `make test-unit` и `make test-integration` проходят
- [ ] Black / Flake8 / isort / mypy без ошибок

---

## Dev Agent Record

### Agent Model Used

GPT-5.5

### Debug Log References

- Перевёл рантайм-каталоги 1С на приватный корень `ONEC_PRIVATE_DIR` вне `MEDIA_ROOT`.
- Убрал хардкод `MEDIA_ROOT` из `ImportOrchestratorService` и fallback в `process_1c_import_task`.
- Обновил production docker-compose, чтобы `backend` и `celery` делили `/app/var/onec`.
- Добавил/обновил тесты на приватные пути и реальный XML из `data/import_1c`.
- Валидация: `py_compile` прошёл, точечные тесты прошли, `pytest -m unit` и `pytest -m integration` в Docker прошли.
- Локальный `make` в этой оболочке отсутствует; проверял эквивалентные docker-команды из Makefile.
- Репозиторный `flake8`/`mypy` остаются шумными из-за существующего debt вне scope story.

### Completion Notes List

- Файлы 1С для HTTP-обмена теперь пишутся в приватный каталог вне публичного `MEDIA_ROOT`.
- В проде добавлен общий bind-mount для `backend` и `celery`, чтобы воркер видел те же файлы импорта.
- Реальные XML из `backend/data/import_1c` продолжили работать через HTTP-обмен и асинхронный импорт.
- Проверено, что `1c_import` и `1c_temp` больше не живут под `/media`.
- Проверка `pytest -m unit` завершилась `763 passed`, `pytest -m integration` завершилась `684 passed`.

### File List

- `backend/freesport/settings/base.py`
- `backend/apps/integrations/onec_exchange/import_orchestrator.py`
- `backend/apps/products/tasks.py`
- `backend/apps/integrations/onec_exchange/routing_service.py`
- `backend/apps/integrations/onec_exchange/file_service.py`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.test.yml`
- `docker/nginx/conf.d/default.conf`
- `backend/tests/unit/test_file_routing.py`
- `backend/tests/integration/test_onec_import.py`
- `backend/apps/products/tests/integration/test_import_orchestration.py`
- `backend/apps/products/tests/test_import_orchestration_tasks.py`
- `backend/apps/integrations/tests/test_import_orchestration_view.py`

## Change Log

- 2026-05-18: Создана Story 36.1 (bmad-create-story). Status: ready-for-dev.
- 2026-05-19: Перенёс runtime-каталоги 1С из публичного `MEDIA_ROOT` в `ONEC_PRIVATE_DIR`, обновил оркестратор, fallback задачи, production compose и тестовое покрытие. Status: review.
