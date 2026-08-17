# Задача: развести расхождение путей к данным 1С между окружениями

Собрано 2026-08-16. Ветка `develop`. Всё ниже проверено на текущем рабочем дереве, не по памяти.

---

## 1. Симптом

Путь **внутри контейнера везде одинаков** — `/app/data/import_1c`. Каталог **на хосте, из которого
он смонтирован, — разный**:

| Окружение | compose-файл | том | хостовый источник |
|---|---|---|---|
| dev | `docker/docker-compose.yml:81` | `../data:/app/data` | `<repo>/data/import_1c` |
| dev (альт.) | `docker/docker-compose.dev.yml:64` | `../data:/app/data` | `<repo>/data/import_1c` |
| test | `docker/docker-compose.test.yml:72` | `../backend/data/import_1c:/app/data/import_1c` | `<repo>/backend/data/import_1c` |
| prod | `docker/docker-compose.prod.yml:84,211` | `${ONEC_DATA_DIR}:/app/data/import_1c` | путь на сервере из `.env.prod` |
| CI | `.github/workflows/main.yml:70` | checkout data-репо в `backend/data/import_1c` | `<repo>/backend/data/import_1c` |

Из-за этого одна и та же команда `python manage.py import_products_from_1c` в dev-контейнере и
тот же `pytest` в test-контейнере читают **физически разные каталоги**. Обнаружено при попытке
запустить импорт: выгрузка лежала в `backend/data/import_1c/`, dev-контейнер видел пустой
корневой `data/import_1c/`; пришлось копировать 220 МБ, чтобы импорт заработал.

## 2. Как путь вычисляется в Django

`backend/freesport/settings/base.py:280`

```python
ONEC_DATA_DIR = os.environ.get("ONEC_DATA_DIR", str(BASE_DIR / "data" / "import_1c"))
```

`BASE_DIR` = `/app` (в контейнере — смонтированный `backend/`), поэтому дефолт = `/app/data/import_1c`.

Дубль той же строки живёт в `backend/backend/settings.py:199` — **проверить, живой ли этот модуль**:
`backend/manage.py:9` ставит `DJANGO_SETTINGS_MODULE=freesport.settings`, все compose задают
`freesport.settings.*`, так что `backend/backend/settings.py` выглядит мёртвым, но это не подтверждено.

Где переменная задаётся:

| Место | Значение | Смысл |
|---|---|---|
| `docker/docker-compose.yml:65` (backend), `:192` (celery) | `/app/data/import_1c` | путь **в контейнере** |
| `docker/docker-compose.prod.yml:59,195` | `/app/data/import_1c` | путь **в контейнере** |
| `docker/docker-compose.prod.yml:84,211` | `${ONEC_DATA_DIR}` | путь **на хосте** (источник bind-mount) |
| `.env.example:40` | `/app/data/import_1c` | контейнерный |
| `.env.prod.example:47` | `/home/freesport/freesport/data/import_1c` | хостовый |
| `docker-compose.test.yml` | не задаётся | берётся дефолт из settings |

**Переменная `ONEC_DATA_DIR` перегружена:** в prod-compose она одновременно и хостовый путь
(в `volumes`), и контейнерный (в `environment`, захардкожен). В dev она контейнерная,
а хостовый источник зашит в compose как `../data`. Это отдельная мина: правка `.env.prod`
меняет только точку монтирования, а не то, что видит Django.

## 3. Несогласованность есть и внутри одного окружения

| Сервис | `docker-compose.yml` | `docker-compose.dev.yml` |
|---|---|---|
| backend | `../data:/app/data` ✅ (стр. 81) | `../data:/app/data` ✅ (стр. 64) |
| celery | `../data:/app/data` ✅ (стр. 178) | **нет** ❌ (стр. 139-141) |
| celery-beat | **нет** ❌ (стр. 220-222) | **нет** ❌ (стр. 168-170) |

То есть celery-worker в `docker-compose.yml` видит корневой `data/`, а celery-beat в том же файле —
`backend/data/`. Задачи импорта ходят через Celery (`backend/apps/products/tasks.py`), так что это
не косметика.

## 4. Что реально лежит на диске сейчас

```
<repo>/data/
├── import_1c/        220,8 МБ — скопировано мной 16.08 ради dev-импорта
│                     contragents(10) goods(19) groups offers(31) priceLists
│                     prices(16) propertiesGoods(9) propertiesOffers rests(16) storages units
└── webdata/          старая выгрузка 04.08 (contragents + references) + «Обмен локальный»

<repo>/backend/data/import_1c/
├── goods/ groups/ offers/ priceLists/ prices/ propertiesGoods/
├── propertiesOffers/ rests/ storages/ units/     ← старые данные
├── README.md
├── snapshots/2026-08-16/«Выгрузка на диск»/      228,8 МБ — снимок свежей выгрузки (все 13 разделов)
└── webdata/«Выгрузка на диск»/                   рабочий каталог 1С, СТИРАЕТСЯ каждым обменом
```

**Критично:** в `backend/data/import_1c/` **нет `contragents/` и нет `contragents_pricetype/`** —
а именно они нужны data_dependent-тестам. Локально эти тесты сейчас скипаются либо читают не то.
Полный набор контрагентов есть в `data/import_1c/contragents/` и в снимке.

Ни один из каталогов не под git — `.gitignore:194-206` (строка `data` игнорирует любой каталог с
таким именем; `backend/data/import_1c/` продублирован трижды). Новые файлы туда — только `git add -f`.

## 5. Кто на какой путь завязан

**Ожидают `backend/data/import_1c` (канон де-факто):**
- `.github/workflows/main.yml:70` — checkout приватного `AlexMobiCraft/FREESPORT-1c-test-data`
- `docker/docker-compose.test.yml:72`
- `scripts/prep-1c-test-data.sh` — пакует `contragents/`, `contragents_pricetype/`, `priceLists/`, `prices/` (~48 МБ) в data-репо
- `backend/docs/testing-standards.md:112` — история порога покрытия 73 → 75
- тесты: `backend/tests/integration/test_customers_price_type_detector.py:9`,
  `test_import_customers_price_type.py:9`, `test_import_opt4_prices.py:11,36`,
  `test_import_role_from_1c.py:14`, `test_link_applies_role_from_1c.py:10`,
  `test_onec_import.py:41,379`

**Ожидают корневой `data/import_1c`:**
- `docker/docker-compose.yml:81`, `docker-compose.dev.yml:64`
- `.github/workflows/sync-to-public.yml:30` — `rm -rf data/import_1c/` перед зеркалированием
  (**дыра**: `backend/data/import_1c/` не удаляется, а там ПДн — ФИО, ИНН, счета)
- `CLAUDE.md` («Неочевидное в коде» и раздел про 1С), `.claude/skills/import-1c/SKILL.md:26,31`,
  `.claude/skills/docker-test-run/SKILL.md:78`

**Гибриды (сначала пробуют `/app/...`, потом BASE_DIR):**
- `backend/tests/integration/test_management_commands/test_import_customers.py:34-40`
- `backend/tests/conftest.py:418-426` — фикстура `onec_data_dir` = `BASE_DIR/data/import_1c`

**Прочее:** `backend/apps/products/management/commands/fix_variant_sizes.py:13,74` подсказывает
`--data-dir=data/import_1c`; `backend/apps/integrations/views.py:95` документирует
`data/import_1c/goods/import_files/**`; `routing_service.py:81` комментирует ожидаемую структуру.

## 6. Противоречия, которые надо решить

1. **Два хостовых каталога под один контейнерный путь** — основная задача.
2. **CLAUDE.md и навыки называют каноном `data/import_1c/`, а CI, тесты и prep-скрипт — `backend/data/import_1c/`.** Документация разошлась с кодом; после выбора канона её надо привести в порядок (CLAUDE.md, оба SKILL.md, README в каталоге).
3. **`sync-to-public.yml` чистит только корневой путь** — если канон станет `backend/`, публичное зеркало начнёт утекать ПДн. Правится в том же заходе, независимо от выбора.
4. **`ONEC_DATA_DIR` означает разное на хосте и в контейнере** (см. §2). Стоит развести на две переменные, например `ONEC_DATA_HOST_DIR` (bind-mount) и `ONEC_DATA_DIR` (внутри).
5. **celery / celery-beat не видят данные** в части compose-файлов (§3).
6. **`backend/data/import_1c/` неполон** — нет `contragents/`, `contragents_pricetype/`, хотя тесты и prep-скрипт их ждут.
7. **`docker-compose.dev.yml` дублирует `docker-compose.yml`** — неясно, какой из них живой; расходятся по томам. Возможно, один надо удалить.
8. **Дубль `ONEC_DATA_DIR` в `backend/backend/settings.py`** — проверить, мёртвый ли модуль, и удалить.

## 7. Два варианта решения

### Вариант A — канон `backend/data/import_1c` (рекомендую)

Совпадает с CI, тестовым compose, prep-скриптом и всеми тестами — правок в самом многочисленном
слое не требуется. Меняются только dev-compose и документация.

- `docker/docker-compose.yml` и `docker-compose.dev.yml`: заменить `../data:/app/data` на
  `../backend/data/import_1c:/app/data/import_1c` (как в тестовом), добавить том в celery и celery-beat.
- Проверить, не нужен ли кому-то ещё `/app/data` целиком (сейчас том даёт контейнеру весь корневой
  `data/`, включая `webdata/`) — если нет, замена безопасна.
- Перенести `data/import_1c/contragents/` → `backend/data/import_1c/contragents/`.
- Поправить `sync-to-public.yml`: добавить `rm -rf backend/data/import_1c/`.
- Обновить CLAUDE.md, `.claude/skills/import-1c/SKILL.md`, `.claude/skills/docker-test-run/SKILL.md`,
  `.agents/skills/docker-test-run/SKILL.md`.

Минус: корневой `data/` остаётся под `webdata/` и `data/prod/*` (prod-тома `../data/prod/static|media`),
то есть каталог `data/` живёт, но перестаёт быть местом выгрузок — это надо явно записать в README.

### Вариант B — канон корневой `data/import_1c`

Ближе к текущему CLAUDE.md, но требует правок в CI (`main.yml:70`), тестовом compose,
`prep-1c-test-data.sh` и ~8 тестах с зашитыми путями. Дороже и рискованнее: тестовый слой сейчас
зелёный, трогать его ради переезда — лишний риск.

## 8. Критерии приёмки

- `docker compose -f docker/docker-compose.yml exec backend python -c "from django.conf import settings; print(settings.ONEC_DATA_DIR)"` и `ls` по нему показывают тот же набор файлов, что видит тестовый контейнер.
- То же для сервисов `celery` и `celery-beat`.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -m data_dependent` — ни одного скипа по причине «нет данных» (сейчас часть скипается: нет `contragents/`).
- Полная регрессия: unit + integration зелёные (было 2030 + 965 passed).
- `sync-to-public.yml` не оставляет XML 1С ни по одному из путей — проверить `git ls-files` и шаг `rm -rf` вручную.
- CLAUDE.md, оба SKILL.md и README каталога называют один путь.

## 9. Ловушки

- **Git Bash ломает пути.** `--data-dir /app/data/import_1c` превращается в `C:/Program Files/Git/app/...`. Спасает префикс `MSYS_NO_PATHCONV=1` перед `docker compose`.
- **`.gitignore` глушит оба каталога** — коммит новых файлов только через `git add -f`.
- **`import_products_from_1c` без `--keep-files` удаляет исходники после успешного импорта.**
- **`backend/data/import_1c/webdata/«Выгрузка на диск»/` стирается целиком** при каждом обмене 1С (`УдалитьФайлы(КаталогВыгрузки)` в расширении БУС) — рабочий каталог, не хранилище. Снимок лежит в `snapshots/2026-08-16/`.
- **В prod менять пути осторожно:** том `${ONEC_DATA_DIR}:/app/data/import_1c` завязан на владельца каталога `1000:1000` (Story 36.1, `scripts/deploy/deploy.sh` шаг 3.5) — bind-mount, созданный root'ом, даёт PermissionError. Деплой ручной, CI его не катит.
- **Данные содержат ПДн** (ФИО, ИНН, расчётные счета контрагентов) — не переносить в публичные репозитории и артефакты.

## 10. Что не проверено

- Живой ли `docker/docker-compose.dev.yml` и `backend/backend/settings.py`.
- `docker/docker-compose-temp.yml` и `docker-compose.build.yml` про `data` не упоминают — но их назначение не изучено.
- Нужен ли кому-то `/app/data/webdata` внутри контейнера (сейчас доступен в dev как побочный эффект тома `../data:/app/data`).
- Состояние прод-каталога `${ONEC_DATA_DIR}` на сервере.

## 11. Стартовая команда для нового окна

> Прочитай `_bmad-output/implementation-artifacts/tasks/dev-task-onec-data-dir-unification.md`
> и реализуй вариант A: свести dev, test, CI и prod к одному хостовому каталогу данных 1С.
> Перед правкой compose-файлов покажи план и список затронутых файлов.
