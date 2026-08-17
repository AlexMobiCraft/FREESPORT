---
baseline_commit: e3fd97e561e4b39d56b3cc6a7e74a2cf65628434
---

# Story: Infra — единый хостовый каталог данных 1С для dev, test, CI и prod

**Story ID:** infra-onec-data-dir-unification
**Status:** ready-for-dev
**Priority:** 🟠 HIGH — блокирует воспроизводимость импорта 1С и держит ~32 теста в скипах локально
**Source:** `_bmad-output/implementation-artifacts/tasks/dev-task-onec-data-dir-unification.md`
**Эпика не имеет** — инфраструктурный долг, не привязан к продуктовому эпику. Имя по образцу `security-*`.
**Координаты проверены на `e3fd97e5`** (16.08.2026), не по памяти.

---

## Story

Как **разработчик FREESPORT**,
я хочу **чтобы `/app/data/import_1c` во всех окружениях указывал на один и тот же хостовый каталог**,
чтобы **одна и та же выгрузка 1С работала и в dev-импорте, и в тестах, и в CI — без копирования 220 МБ между каталогами и без тихих скипов data_dependent-тестов**.

---

## Контекст: что именно сломано

Путь **внутри контейнера везде одинаков** — `/app/data/import_1c`. Хостовый каталог, из которого он смонтирован, **разный**:

| Окружение | Где задано | Хостовый источник |
|---|---|---|
| dev | `docker/docker-compose.yml:81,178` | `<repo>/data` → `/app/data` |
| dev (дубль) | `docker/docker-compose.dev.yml:64` | `<repo>/data` → `/app/data` |
| test | `docker/docker-compose.test.yml:72` | `<repo>/backend/data/import_1c` |
| CI | `.github/workflows/main.yml:70` | checkout data-репо в `backend/data/import_1c` |
| prod | `docker/docker-compose.prod.yml:84,211` | `${ONEC_DATA_DIR}` из `.env.prod` = `/home/freesport/freesport/data/import_1c` |

Следствие, наблюдавшееся 16.08: выгрузка лежала в `backend/data/import_1c/`, dev-контейнер видел пустой корневой `data/import_1c/`, импорт пришлось чинить копированием 220 МБ.

### Три отдельных дефекта под одним симптомом

**1. Резолв пути размазан по девяти местам.** Дефолт живёт в `backend/freesport/settings/base.py:280`:

```python
BASE_DIR = Path(__file__).resolve().parent.parent.parent   # = <repo>/backend
ONEC_DATA_DIR = os.environ.get("ONEC_DATA_DIR", str(BASE_DIR / "data" / "import_1c"))
```

но тесты его **не используют** — каждый резолвит путь сам, двумя несовместимыми способами: `Path(settings.BASE_DIR) / "data" / "import_1c"` и `if os.path.exists("/app/data"): Path("/app/data/import_1c")`. Полный инвентарь — в Dev Notes.

**2. `ONEC_DATA_DIR` означает разное на хосте и в контейнере.** В `docker-compose.prod.yml` она одновременно контейнерный путь (`environment:59,195` — литерал `/app/data/import_1c`) и хостовый (`volumes:84,211` — `${ONEC_DATA_DIR}`). Правка `.env.prod` меняет только точку монтирования, а не то, что видит Django. Мина заряжена и ждёт.

**3. celery-beat не видит данные, celery — видит.** В `docker-compose.yml`: backend (`:81`) и celery (`:178`) имеют `../data:/app/data`, celery-beat (`:220-222`) — нет. Задачи импорта ходят через Celery (`backend/apps/products/tasks.py`), так что это не косметика.

### Проверенное состояние на диске (16.08.2026)

```
<repo>/data/import_1c/           222 МБ  contragents(10) goods groups offers priceLists
                                         prices propertiesGoods propertiesOffers rests storages units
<repo>/data/webdata/                     старая выгрузка 04.08
<repo>/backend/data/import_1c/   1,4 ГБ  старые разделы + README.md
  ├── snapshots/2026-08-16/«Выгрузка на диск»/   228 МБ — свежий снимок, все 13 разделов
  └── webdata/«Выгрузка на диск»/                рабочий каталог 1С, СТИРАЕТСЯ каждым обменом
```

**Ни один из каталогов не под git** (`.gitignore:194-206`, правило `data` глушит любой каталог с таким именем).

### Корпус контрагентов расходится с тем, что ждут тесты — проверено

| Каталог | Файлов | Редакция патча БУС |
|---|---|---|
| `data/import_1c/contragents/` | 10 | 2-я (все 10 содержат `ТипЦен`) |
| `backend/data/import_1c/snapshots/2026-08-16/…/contragents/` | 10 | 2-я (все 10 содержат `ТипЦен`) |
| `backend/data/import_1c/contragents/` | **отсутствует** | — |
| `*/contragents_pricetype/` | **отсутствует нигде локально** | — |

При этом `test_customer_parser.py:34` и `test_link_then_import_1c.py:33` зашивают конкретное имя файла
`contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml` — **его нет ни в одном локальном каталоге**
(проверено `find`). Единственный источник корпуса, на котором тесты зелёные, — приватный data-репо
`AlexMobiCraft/FREESPORT-1c-test-data`, который CI подключает шагом checkout.

**Вывод, определяющий AC-4:** «перенести contragents из корневого каталога» задачу НЕ решает — там
2-я редакция под именем 1-й, а нужного файла нет. Локальный канон обязан засеваться из data-репо,
тем же корпусом, что исполняется в CI.

---

## Принятые решения (не пересматривать при реализации)

| # | Решение | Кем/когда |
|---|---|---|
| 1 | **Канон — корневой `<repo>/data/import_1c`** (вариант B задания, не A). 1С выгружает **туда**, а не в `backend/data/import_1c/`. Прод уже живёт на этом пути и **не трогается**: ни каталог на сервере, ни `.env.prod`, ни деплой. | Alex, 2026-08-16 |
| 2 | **Резолв пути сводится к единственному источнику — `settings.ONEC_DATA_DIR`.** Ни один тест не резолвит путь сам. Это и делает вариант B дешёвым: правится один дефолт в `base.py` вместо девяти копий. | Alex, 2026-08-16 |
| 3 | **`docker/docker-compose.dev.yml` удаляется.** На него не ссылаются ни Makefile, ни навыки, ни скрипты — только 3 упоминания в docs. Дубль расходился с `docker-compose.yml` по томам; один dev-compose расходиться не может. | Alex, 2026-08-16 |
| 4 | **Переменные разводятся:** `ONEC_DATA_HOST_DIR` — хостовый источник bind-mount (только `docker-compose.prod.yml`), `ONEC_DATA_DIR` — путь внутри контейнера. Дефолт `${ONEC_DATA_HOST_DIR:-../data/import_1c}` делает правку `.env.prod` на сервере **необязательной**: без неё бинд резолвится в `<repo>/data/import_1c` — ровно тот каталог, что там сейчас. Прод-поведение не меняется. | Alex, 2026-08-16 |
| 5 | **Инвариант закрывается тестом-сторожем.** Без него следующая правка compose разведёт пути снова, и обнаружится это опять вручную, спустя месяцы. | Amelia, 2026-08-16 |

---

## Acceptance Criteria

### AC-1: Один хостовый каталог во всех окружениях

**Given** dev-, test- и prod-compose и прогон CI,
**When** какой-либо сервис получает `/app/data/import_1c`,
**Then** его хостовый источник — `<repo>/data/import_1c` (в prod — через `${ONEC_DATA_HOST_DIR:-../data/import_1c}`, что резолвится в тот же относительный путь),
**And** ни один compose-файл не монтирует `backend/data/import_1c` и не отдаёт контейнеру каталог `data/` целиком.

### AC-2: Путь резолвится из единственного источника

**Given** любой тест или команду, которым нужен каталог выгрузок,
**When** они определяют путь,
**Then** они читают `settings.ONEC_DATA_DIR` (напрямую или через фикстуру `onec_data_dir`),
**And** `grep -rn "/app/data" backend/tests/` и `grep -rn 'BASE_DIR.*"data".*"import_1c"' backend/tests/` не находят ни одного самодельного резолва.

### AC-3: Дефолт settings указывает на канон

**Given** окружение без переменной `ONEC_DATA_DIR` (локальный venv, раннер CI),
**When** Django читает настройки,
**Then** `settings.ONEC_DATA_DIR == str(BASE_DIR.parent / "data" / "import_1c")` = `<repo>/data/import_1c`,
**And** в тест-контейнере (`BASE_DIR=/app`, где `.parent` дал бы `/`) значение приходит из `environment:` литералом `/app/data/import_1c` — дефолт там не участвует.

### AC-4: data_dependent-тесты исполняются локально без скипов «нет данных»

**Given** локальный канон, засеянный из приватного data-репо (`contragents/`, `contragents_pricetype/`, `priceLists/`, `prices/`),
**When** выполняется `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -m data_dependent -rs`,
**Then** в отчёте `-rs` нет ни одного скипа с причиной «Реальный dataset 1С не найден»,
**And** число исполненных тестов совпадает с CI-прогоном на доверенной ветке.

### AC-5: CI подключает data-репо в канон

**Given** `.github/workflows/main.yml`,
**When** выполняется шаг «Checkout 1C test data»,
**Then** `path: data/import_1c`,
**And** последующий `cd backend && pytest` резолвит `settings.ONEC_DATA_DIR` в тот же каталог,
**And** порог покрытия 75 на доверенном прогоне достигается (регрессии по числу исполненных тестов нет).

### AC-6: celery и celery-beat видят тот же каталог, что backend

**Given** dev-стек,
**When** выполняется `docker compose … exec <service> python -c "from django.conf import settings; print(settings.ONEC_DATA_DIR)"` и `ls` по этому пути для `backend`, `celery`, `celery-beat`,
**Then** все три печатают `/app/data/import_1c` и одинаковый листинг.

### AC-7: переменные разведены, прод не затронут

**Given** `docker-compose.prod.yml`,
**When** он резолвится с существующим `.env.prod`, где задан только старый `ONEC_DATA_DIR`,
**Then** хостовый источник берётся из `${ONEC_DATA_HOST_DIR:-../data/import_1c}` и указывает на `/home/freesport/freesport/data/import_1c` — тот же каталог, что и до правки,
**And** `docker compose --env-file .env.prod -f docker/docker-compose.prod.yml config` проходит без ошибок и без пустых источников томов,
**And** `environment: ONEC_DATA_DIR=/app/data/import_1c` остаётся литералом.

### AC-8: публичное зеркало не утекает ПДн ни по одному пути

**Given** `.github/workflows/sync-to-public.yml`,
**When** выполняется шаг очистки,
**Then** удаляются оба каталога — `data/import_1c/` и `backend/data/import_1c/`,
**And** `git ls-files` в основном репо не показывает ни одного XML 1С (каталоги под `.gitignore`).

### AC-9: дубли конфигурации удалены

**Given** репозиторий,
**When** ищутся конфиги dev-окружения и настроек Django,
**Then** `docker/docker-compose.dev.yml` отсутствует, а `docs/architecture/source-tree.md` и `docs/deploy/local-setup.md` ссылаются на `docker/docker-compose.yml`,
**And** мёртвый `backend/backend/settings.py` (дубль `ONEC_DATA_DIR:199`, на модуль `backend.settings` не ссылается ничто — проверено grep'ом; `manage.py:9` и все compose задают `freesport.settings.*`) удалён — **только этот файл**: каталог `backend/backend/backup_db/` содержит нетронутые дампы БД и игнорируется `backend/.gitignore:22`,
**And** `python manage.py check` в dev-контейнере проходит.

### AC-10: документация называет один путь

**Given** `CLAUDE.md`, `project-context.md`, `backend/docs/testing-standards.md`, `.claude/skills/import-1c/SKILL.md`, `.claude/skills/docker-test-run/SKILL.md`, `.agents/skills/docker-test-run/SKILL.md`, README каталога данных,
**When** в них упоминается каталог выгрузок 1С,
**Then** везде назван `data/import_1c` (корневой), и нигде — `backend/data/import_1c` как место выгрузок.

### AC-11: инвариант закрыт сторожем

**Given** новый тест-сторож,
**When** кто-то возвращает в любой compose-файл монтирование `backend/data/import_1c` или `../data:/app/data`, ломает checkout-путь в `main.yml`, убирает том у `celery`/`celery-beat` или заводит в тесте самодельный резолв пути,
**Then** сторож падает с сообщением, объясняющим инвариант,
**And** сторож исполняется и локально (файлы вне `backend/` уже смонтированы в тест-контейнер — `docker-compose.test.yml:78-83`), а не только в CI.

### AC-12: регрессия зелёная

**Given** полный прогон,
**When** выполняются `make test-unit` и `make test-integration`,
**Then** оба зелёные, число passed не ниже базовой линии (unit 2049, integration 995 на `e3fd97e5`),
**And** покрытие в CI ≥ 75.

---

## Tasks / Subtasks

- [ ] **T1. Дефолт пути в settings** (AC: 3)
  - [ ] `backend/freesport/settings/base.py:280` — дефолт на `BASE_DIR.parent / "data" / "import_1c"`, комментарий: почему `.parent` (BASE_DIR = `backend/`, канон — корень репо) и почему в контейнере дефолт не участвует.
  - [ ] `backend/tests/unit/test_settings_onec.py` — добавить проверку, что дефолт указывает на корень репо, а не на `backend/`.
- [ ] **T2. Compose: единый источник** (AC: 1, 6, 7)
  - [ ] `docker/docker-compose.yml`: у `backend` (`:81`) и `celery` (`:178`) заменить `../data:/app/data` на `../data/import_1c:/app/data/import_1c`; добавить тот же том и `ONEC_DATA_DIR=/app/data/import_1c` сервису `celery-beat` (`:220-233`).
  - [ ] `docker/docker-compose.test.yml:72`: источник → `../data/import_1c`; добавить в `environment:` литерал `ONEC_DATA_DIR=/app/data/import_1c` (**без `${}`** — см. Мины).
  - [ ] `docker/docker-compose.prod.yml:84,211`: `${ONEC_DATA_DIR}` → `${ONEC_DATA_HOST_DIR:-../data/import_1c}`; комментарий про разведение смыслов и про то, что `.env.prod` на сервере править не обязательно.
  - [ ] `.env.prod.example:47`: `ONEC_DATA_DIR` → `ONEC_DATA_HOST_DIR` с тем же значением + комментарий «хостовый источник bind-mount; контейнерный путь задан литералом в compose».
  - [ ] `.env.example:40`: комментарий, что это путь **внутри контейнера**.
  - [ ] Удалить `docker/docker-compose.dev.yml`; поправить `docs/architecture/source-tree.md:113,278` и `docs/deploy/local-setup.md:63`.
- [ ] **T3. Тесты: убрать самодельные резолвы** (AC: 2)
  - [ ] `backend/tests/conftest.py:418-426` — фикстура `onec_data_dir` → `settings.ONEC_DATA_DIR` (возвращать **str**, как сейчас: три вызывающих оборачивают в `Path(...)`).
  - [ ] `backend/tests/integration/test_customers_price_type_detector.py:28-30`
  - [ ] `backend/tests/integration/test_import_opt4_prices.py:33-38`
  - [ ] `backend/tests/integration/test_link_then_import_1c.py:38-43`
  - [ ] `backend/tests/integration/test_management_commands/test_import_customers.py:33-40`
  - [ ] `backend/tests/unit/test_services/test_customer_parser.py:26-46`
  - [ ] `backend/tests/unit/test_services/test_customer_processor.py:405,432`
  - [ ] Проверить, что `test_import_role_from_1c`, `test_link_applies_role_from_1c`, `test_import_customers_price_type` чинятся автоматически (они уже ходят через фикстуру).
- [ ] **T4. CI и prep-скрипт** (AC: 5, 8)
  - [ ] `.github/workflows/main.yml:70` — `path: data/import_1c`; обновить комментарий (упоминание `backend/data/import_1c/` в блоке про порог, `:160`).
  - [ ] `scripts/prep-1c-test-data.sh:34,39,60,64,125` — `SOURCE_DIR` и текст на корневой `data/import_1c`.
  - [ ] `.github/workflows/sync-to-public.yml:30` — добавить `rm -rf backend/data/import_1c/`.
- [ ] **T5. Перенос данных на диске** (AC: 4) — **шаги необратимы, порядок соблюдать**
  - [ ] Зафиксировать инвентарь ДО: число XML и размер по каждому разделу обоих каталогов — записать в Dev Agent Record.
  - [ ] Перенести `backend/data/import_1c/snapshots/` → `data/import_1c/snapshots/` и `backend/data/import_1c/README.md` → `data/import_1c/README.md`.
  - [ ] Засеять `data/import_1c/contragents/` и `contragents_pricetype/` из приватного data-репо (`git clone https://github.com/AlexMobiCraft/FREESPORT-1c-test-data` во временный каталог, скопировать 4 раздела). **Не перезаписывать** уже лежащие в каноне свежие `prices/`, `priceLists/` — копировать только отсутствующие разделы.
  - [ ] Убедиться, что `data/import_1c/contragents/contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml` на месте — на нём завязаны `test_customer_parser` и `test_link_then_import_1c`.
  - [ ] Сверить инвентарь ПОСЛЕ, затем удалить `backend/data/import_1c/` целиком. Каталог `backend/data/` не содержит ничего кроме `import_1c/` (проверено) — после удаления исчезает весь.
  - [ ] `.gitignore:194-206` — схлопнуть тройной дубль `backend/data/import_1c/` в одну строку, оставить оба пути игнорируемыми, комментарий про правило `data`.
- [ ] **T6. Сторож инварианта** (AC: 11)
  - [ ] Новый модуль `backend/tests/unit/test_onec_data_dir_invariant.py` по образцу `TestCIFilters` (`test_pytest_marker_autotagging.py:622-758`): резолв файлов через `_repo_file`-паттерн, скип только для урезанного окружения.
  - [ ] Проверки: (а) во всех compose-файлах хостовый источник для `/app/data/import_1c` — `../data/import_1c` либо `${ONEC_DATA_HOST_DIR:-…}`; (б) `backend/data/import_1c` не встречается ни в одном compose и в `main.yml`; (в) `main.yml` checkout-путь = `data/import_1c`; (г) в `docker-compose.yml` том есть у всех трёх сервисов — `backend`, `celery`, `celery-beat`; (д) в `backend/tests/` нет строк `/app/data` и `BASE_DIR / "data" / "import_1c"` — **сам модуль-сторож из скана исключить**, иначе он матчит собственный текст.
  - [ ] Дополнить `test_test_compose_mounts_everything_the_guards_read` (`:722-741`), если сторожу нужны новые смонтированные пути.
- [ ] **T7. Документация** (AC: 10)
  - [ ] `CLAUDE.md:21,61` — зафиксировать, что `data/import_1c/` — **единственное** место выгрузок во всех окружениях, включая тесты и CI.
  - [ ] `project-context.md:82` — упоминание `backend/data/import_1c/` в объяснении разрыва покрытия → корневой путь.
  - [ ] `backend/docs/testing-standards.md:112` — то же.
  - [ ] `.claude/skills/import-1c/SKILL.md:31`, `.claude/skills/docker-test-run/SKILL.md:78`, `.agents/skills/docker-test-run/SKILL.md:78` — сверить, поправить где нужно.
  - [ ] `data/import_1c/README.md` (перенесённый) — добавить раздел «Куда выгружает 1С» и явно: `backend/data/import_1c/` больше не используется.
- [ ] **T8. Приёмка** (AC: 4, 6, 12)
  - [ ] `docker compose … exec backend|celery|celery-beat` — печать `settings.ONEC_DATA_DIR` + `ls`, три одинаковых листинга.
  - [ ] `pytest -m data_dependent -rs` в тест-контейнере — ноль скипов «нет данных».
  - [ ] `make test-unit`, `make test-integration` — зелёные, числа не ниже базовой линии.
  - [ ] `npx gitnexus detect-changes --scope all` перед коммитом.
- [ ] **T9. Ручной шаг Alex (вне кода)** — перенастроить выгрузку 1С (расширение БУС на dev-машине) на каталог `<repo>/data/import_1c`. Записать в `sprint-status.yaml → action_items`, а не делать вид, что закрыто кодом.

---

## Dev Notes

### GitNexus pre-flight

Индекс свежий: `npx gitnexus status` → `up-to-date` на `e3fd97e5` (проверено 2026-08-16).

Blast radius **низкий**: правки не меняют ни одного Python-символа продакшен-кода. Единственное
изменение в `backend/` вне тестов — строка-константа `ONEC_DATA_DIR` в `base.py` (модуль настроек,
не символ графа) и удаление мёртвого модуля `backend/backend/settings.py`. Потребители настройки
(`impact` по ним не требуется — сигнатуры не меняются): `apps/integrations/tasks.py:53,166,258`,
`apps/integrations/views.py:229`, `apps/products/management/commands/import_products_from_1c.py:145`,
`import_attributes.py:80`, `import_images_from_1c.py:69`. Все читают через `getattr(settings, …)` —
меняется значение, не контракт.

Перед коммитом обязателен `npx gitnexus detect-changes --scope all`.

### Инвентарь резолверов пути — правится каждый

| Файл:строка | Как резолвит сейчас | Куда указывает вне контейнера |
|---|---|---|
| `freesport/settings/base.py:280` | `BASE_DIR / "data" / "import_1c"` | `backend/data/import_1c` ❌ |
| `backend/backend/settings.py:199` | то же, **мёртвый модуль** | — (удалить) |
| `tests/conftest.py:418-426` | `Path(settings.BASE_DIR) / "data" / "import_1c"` | `backend/data/…` ❌ |
| `tests/integration/test_customers_price_type_detector.py:28-30` | то же | ❌ |
| `tests/unit/test_services/test_customer_processor.py:432` | то же | ❌ |
| `tests/integration/test_import_opt4_prices.py:33-38` | `if exists("/app/data")` → `/app/data/import_1c`, иначе `parents[2]/"data"/"import_1c"` | ❌ |
| `tests/integration/test_link_then_import_1c.py:38-43` | то же (`parents[2]`) | ❌ |
| `tests/integration/test_management_commands/test_import_customers.py:33-40` | то же | ❌ |
| `tests/unit/test_services/test_customer_parser.py:26-46` | то же (`parents[3]`) | ❌ |

Через фикстуру `onec_data_dir` (чинятся сами после правки conftest):
`test_import_role_from_1c.py:85,92`, `test_link_applies_role_from_1c.py:87,95`,
`test_import_customers_price_type.py:71,78`.

**Не трогать:** `test_import_page_integration.py:48` — своя фикстура `onec_data_dir` на `tmp_path`,
синтетический каталог, к канону отношения не имеет.

### Точный код: settings

```python
# backend/freesport/settings/base.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # = <repo>/backend

# Канон каталога выгрузок 1С — КОРЕНЬ репозитория, а не backend/: туда выгружает 1С,
# оттуда читают dev-стек, тест-контейнер, CI и прод. Отсюда .parent у BASE_DIR.
# В контейнере дефолт не участвует — путь приходит из environment литералом
# /app/data/import_1c (все compose-файлы задают его явно, включая тестовый).
ONEC_DATA_DIR = os.environ.get("ONEC_DATA_DIR", str(BASE_DIR.parent / "data" / "import_1c"))
```

### Точный код: том в compose

Один и тот же литерал во всех трёх сервисах `docker-compose.yml` и в `docker-compose.test.yml`:

```yaml
      # Канон: единственный хостовый каталог выгрузок 1С — <repo>/data/import_1c.
      # Сужен до import_1c намеренно: раньше монтировался весь data/ и в контейнер
      # протекали webdata/ и data/prod/*. Ничто в коде к /app/data/<не import_1c> не обращается.
      - ../data/import_1c:/app/data/import_1c
```

Прод:

```yaml
      # ONEC_DATA_HOST_DIR — хостовый источник bind-mount; контейнерный путь задан
      # литералом в environment выше. Дефолт резолвится в <repo>/data/import_1c —
      # ровно тот каталог, что уже лежит на сервере, поэтому .env.prod править не нужно.
      - ${ONEC_DATA_HOST_DIR:-../data/import_1c}:/app/data/import_1c
```

### Мины

- **`${` в `docker-compose.test.yml` запрещён сторожем.** `test_pytest_marker_autotagging.py:713-720`
  падает на любой подстановке: Makefile зовёт тестовый compose без `--env-file`, и подстановка молча
  резолвится в пустую строку. `ONEC_DATA_DIR` там задавать **только литералом**.
- **`BASE_DIR.parent` в тест-контейнере даёт `/`.** `BASE_DIR=/app`, `.parent` = корень ФС. Поэтому
  `environment: ONEC_DATA_DIR=/app/data/import_1c` в `docker-compose.test.yml` — не украшение,
  а обязательное условие T1. Забыть его = все data_dependent-тесты уедут в `/data/import_1c`.
- **Git Bash ломает пути.** `--data-dir /app/data/import_1c` превращается в `C:/Program Files/Git/app/…`.
  Спасает префикс `MSYS_NO_PATHCONV=1` перед `docker compose`.
- **`.gitignore` глушит оба каталога** — новые файлы туда только через `git add -f`.
- **`import_products_from_1c` без `--keep-files` удаляет исходники после успешного импорта.**
  На каноне это теперь удаляет единственную копию — прогонять только с `--keep-files`.
- **`backend/data/import_1c/webdata/«Выгрузка на диск»/` стирается целиком** каждым обменом 1С
  (`УдалитьФайлы(КаталогВыгрузки)` в расширении БУС). Это рабочий каталог, а не хранилище: переносить
  его в канон нельзя, снимок лежит в `snapshots/2026-08-16/`.
- **Данные содержат ПДн** (ФИО, ИНН, расчётные счета) — не переносить в публичные репозитории
  и артефакты, не прикладывать к PR.
- **Прод-каталог принадлежит `1000:1000`** (Story 36.1, `scripts/deploy/deploy.sh` шаг 3.5).
  Стори прод не трогает, но если кто-то решит «заодно» поправить путь на сервере — bind-mount,
  созданный root'ом, даёт PermissionError при первом `mode=file`.

### Что эта стори НЕ трогает

- **Прод-сервер:** ни каталог, ни `.env.prod`, ни `deploy.sh`, ни `docs/deploy/data-upload.md`
  (он уже описывает корневой путь). Решение Alex от 2026-08-16.
- **`ONEC_PRIVATE_DIR`** и рантайм-каталоги HTTP-обмена (`1c_temp`, `1c_import`) — это Story 36.1,
  другой механизм и другой каталог (`data/prod/onec_private`).
- **Порог покрытия 75** — значение не меняется. Если после T5 локальный замер вырастет, порог
  калибруется по CI, а не по локальному прогону (`project-context.md` §4).
- **`scripts/inport_from_1C/*.ps1`** — уже оперируют корневым `data/import_1c` и прод-путём
  `/home/freesport/freesport/data/import_1c`; под каноном B правок не требуют. Проверить, не тронуть.
- **`scripts/dev/setup-dev-environment.ps1:27`, `setup-test-environment.ps1:33`** — уже создают
  `data/import_1c`. Правок не требуют.
- **`docker/docker-compose.build.yml`, `docker/docker-compose-temp.yml`** — секции `volumes` с данными
  1С не содержат вовсе (проверено). Правок не требуют.

### Антипаттерны (НЕ ДЕЛАТЬ)

- ❌ Не «чинить» тесты добавлением второй ветки резолва — цель ровно обратная: убрать ветвление.
- ❌ Не подставлять `${…}` в `docker-compose.test.yml` (сторож, см. Мины).
- ❌ Не удалять `backend/data/import_1c/` до сверки инвентаря — там 228 МБ снимка 16.08, которого
  больше нигде нет.
- ❌ Не генерировать синтетические XML вместо недостающих разделов — правило проекта
  (`CLAUDE.md`, «Интеграция с 1С»). Недостающее берётся из data-репо или из снимка.
- ❌ Не переименовывать `ONEC_DATA_DIR` в контейнере — она остаётся контейнерной и читается кодом.
  Новое имя получает **только** хостовый источник bind-mount.
- ❌ Не трогать прод в этом заходе, даже если «всё равно рядом».

### Project Structure Notes

Новый тест-модуль ложится в `backend/tests/unit/` — маркер `unit` проставится автоматически по
каталогу (`backend/conftest.py`, хук `pytest_collection_modifyitems`); руками маркер не ставить.
Модуль читает файлы вне `backend/` — они уже смонтированы в тест-контейнер
(`docker-compose.test.yml:78-83`: `../docker`, `../.github`, `../pytest.ini`), так что сторож
исполняется и локально, а не только в CI.

### Команды

```bash
# Сверка трёх сервисов dev-стека (Git Bash: префикс обязателен)
MSYS_NO_PATHCONV=1 docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python -c "from django.conf import settings; print(settings.ONEC_DATA_DIR)"
MSYS_NO_PATHCONV=1 docker compose --env-file .env -f docker/docker-compose.yml exec celery ls /app/data/import_1c
MSYS_NO_PATHCONV=1 docker compose --env-file .env -f docker/docker-compose.yml exec celery-beat ls /app/data/import_1c

# data_dependent без скипов (--env-file тестовому compose не передаётся — его нет и он не нужен)
cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend \
  pytest -m data_dependent -rs

# Прод-compose резолвится без пустых источников (локальная проверка синтаксиса)
docker compose --env-file .env.prod.example -f docker/docker-compose.prod.yml config >/dev/null

# Регрессия
make test-unit
make test-integration

# Перед коммитом
npx gitnexus detect-changes --scope all
```

### References

- Задание-источник: `_bmad-output/implementation-artifacts/tasks/dev-task-onec-data-dir-unification.md`
- Дефолт пути: `backend/freesport/settings/base.py:279-280`
- Тома: `docker/docker-compose.yml:81,178,220-222` · `docker-compose.test.yml:68-84` · `docker-compose.prod.yml:59,84,195,211`
- CI: `.github/workflows/main.yml:64-79,143-175` · `sync-to-public.yml:29-31`
- Сторожа-образцы: `backend/tests/unit/test_pytest_marker_autotagging.py:622-758`
- Подготовка data-репо: `scripts/prep-1c-test-data.sh`
- Стандарты тестирования и порог: `backend/docs/testing-standards.md:112` · `project-context.md` §4
- Прецедент приватных каталогов обмена: `_bmad-output/implementation-artifacts/Story/36-1-move-1c-import-files-from-public-media-root.md`

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

---

## Change Log

| Дата | Автор | Изменение |
|---|---|---|
| 2026-08-16 | Amelia (create-story) | Стори создана. Канон — корневой `data/import_1c` (вариант B задания): решение Alex после разбора прод-пути. `docker-compose.dev.yml` удаляется, прод не трогается. |
