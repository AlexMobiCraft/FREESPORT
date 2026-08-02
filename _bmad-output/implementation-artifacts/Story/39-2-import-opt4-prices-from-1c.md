---
baseline_commit: 50e49d01aedf03375d03724d2fecfdbdcc402bef
---

# Story 39.2: Импорт цен «Опт 4» из 1С

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Контент-менеджер**,
I want **чтобы цена вида «Опт 4» из выгрузки 1С попадала в поле `opt4_price`**,
so that **портал перестал выбрасывать эти цены и четвёртый уровень наполнялся данными автоматически**.

## Acceptance Criteria

1. **AC1 (NFR-3940-01), предусловие.** Снимки реальных выгрузок в `backend/data/import_1c/` пригодны для тестов:
   - `priceLists/` содержит вид цен `4c1962d2-f8ed-11eb-81f3-00155d3cae02` («Опт 4 (до 50 тыс.руб в квартал)») — **уже выполнено**, снимок переснят 2026-08-02 (см. Dev Notes);
   - `prices/` содержит **хотя бы одно** `<Цена>` с `<ИдТипаЦены>4c1962d2-f8ed-11eb-81f3-00155d3cae02</ИдТипаЦены>` — **на момент создания стори НЕ выполнено**, требуется переснять выгрузку цен (блокирует AC4).
2. **AC2 (FR-39-05).** `XMLDataParser._map_price_type_to_field` (`backend/apps/products/services/parser.py:536`) для наименования, содержащего `"опт 4"` или `"опт4"` в любом регистре, возвращает `"opt4_price"`. Ветка стоит **после** `«опт 3»` и **до** ветки `«тренер»` — то есть раньше любой ветки, способной перехватить строку с «опт», и раньше `else`-fallback'а на `retail_price`.
3. **AC3 (FR-39-05).** Разбор **реального** файла `backend/data/import_1c/priceLists/priceLists_1_1_*.xml` даёт для GUID `4c1962d2-f8ed-11eb-81f3-00155d3cae02` запись с `product_field == "opt4_price"`, а `VariantImportProcessor.process_price_types` записывает это значение в `PriceType`. Тем самым импорт больше не перетирает `product_field` записи «Опт 4» на `retail_price` (дыра, зафиксированная в Dev Notes стори 39.1), а `user_role="wholesale_level4"` остаётся нетронутым.
4. **AC4 (FR-39-05).** На реальном XML из `backend/data/import_1c/prices/`, содержащем цену вида «Опт 4», `VariantImportProcessor.update_variant_prices` заполняет `ProductVariant.opt4_price` значением из выгрузки.
5. **AC5 (FR-39-05).** В обоих местах создания `ProductVariant` внутри `variant_import.py` (`:841-845` — `process_variant_from_offer`, `:999-1003` — `create_default_variants`) в списке начальных значений ценовых полей присутствует `opt4_price=None` наравне с `opt1_price` … `federation_price`.
6. **AC6 (NFR-3940-08).** Повторный прогон того же файла цен не меняет значения `opt4_price` и не создаёт дублирующих `PriceType`/`ProductVariant`.
7. **AC7 (NFR-3940-01, -02).** Тесты, работающие с XML-файлами, используют **только** реальные выгрузки из `backend/data/import_1c/` (синтетические XML запрещены); каждый новый тест помечен `@pytest.mark.unit` либо `@pytest.mark.integration`, тесты на реальных файлах дополнительно — `@pytest.mark.data_dependent` и корректно `skip`-аются при отсутствии датасета.

## Tasks / Subtasks

- [x] **Task 0 (БЛОКИРУЮЩЕЕ, действие Alex): переснять выгрузку цен** (AC: 1, 4)
  - [x] 0.1: Проверить факт: `grep -l 4c1962d2-f8ed-11eb-81f3-00155d3cae02 backend/data/import_1c/prices/*.xml` — сейчас пусто, `ДатаФормирования` файлов = `2025-11-26`
  - [x] 0.2: Выгрузить из 1С свежие `prices_*.xml` (база, где по виду цен «Опт 4» заполнены цены товаров) и положить в `backend/data/import_1c/prices/`, удалив старый снимок — **выполнено Alex 2026-08-02** скриптом `run-opt4-prices-export.ps1`
  - [x] 0.3: Убедиться, что GUID «Опт 4» встречается хотя бы один раз, и записать имя файла-носителя в Dev Agent Record — 7219 вхождений в 8 файлах, носители перечислены в Debug Log
  - [x] 0.4: ⚠️ Проверить, не появился ли в новом снимке GUID вида цен «Партнер» `200a24fe-f07d-11eb-81f3-00155d3cae02` (в старом — 0 вхождений). Если появился — **не чинить здесь**, эскалировать Alex: «Партнер» уходит в `retail_price` через `else`-fallback и затрёт розничную цену (см. Dev Notes → «Мина: вид цен „Партнер“») — ⚠️ **ПОЯВИЛСЯ, 6639 вхождений. Эскалировано, см. Completion Notes → «Дефект на эскалацию»**
  - [x] 0.5: Если переснять выгрузку невозможно — остановиться и сообщить Alex. AC4 без реальных данных не закрывается, обходить синтетическим XML **запрещено** (NFR-3940-01) — не потребовалось, выгрузка получена

- [x] **Task 1: Ветка «Опт 4» в `_map_price_type_to_field`** (AC: 2, 3)
  - [x] 1.1: Вставить ветку в `backend/apps/products/services/parser.py` между `«опт 3»` и `«тренер»` (точный код — в Dev Notes)
  - [x] 1.2: Убедиться, что `parse_price_lists_xml` (`parser.py:464`) не требует правок — он берёт значение из маппера

- [x] **Task 2: `opt4_price=None` при создании варианта** (AC: 5)
  - [x] 2.1: `variant_import.py:844` (`process_variant_from_offer`) — добавить `opt4_price=None` после `opt3_price=None`
  - [x] 2.2: `variant_import.py:1002` (`create_default_variants`) — то же самое
  - [x] 2.3: НЕ добавлять никакой логики очистки цен в `update_variant_prices` — см. Dev Notes → «Что на самом деле в строках 843/1001»

- [x] **Task 3: Unit-тест маппера** (AC: 2, 7)
  - [x] 3.1: Расширить существующий `test_map_price_type_to_field` (`backend/tests/unit/test_services/test_xml_parser.py:231`) кейсами: `"Опт 4 (до 50 тыс.руб в квартал)"`, `"ОПТ4"`, `"опт4"` → `"opt4_price"`
  - [x] 3.2: Добавить негативный сторож порядка веток: `"Опт 3"` по-прежнему → `"opt3_price"`, `"Опт 1"` → `"opt1_price"` (регресс на случай перестановки веток)
  - [x] 3.3: Тест оперирует строками, а не XML — запрет на синтетические XML к нему не относится

- [x] **Task 4: Интеграционный тест на реальных выгрузках** (AC: 3, 4, 6, 7)
  - [x] 4.1: Создать `backend/tests/integration/test_import_opt4_prices.py` по образцу `backend/tests/integration/test_link_then_import_1c.py` (фикстура пути + `pytest.skip`, точный код — в Dev Notes)
  - [x] 4.2: Тест A (AC3): распарсить реальный `priceLists_1_1_*.xml`, найти запись с GUID «Опт 4» → `product_field == "opt4_price"`; прогнать `processor.process_price_types(...)` → в БД `PriceType.product_field == "opt4_price"`
  - [x] 4.3: Тест B (AC3, страховка от регресса 39.1): предварительно создать `PriceType(onec_id=GUID, product_field="opt4_price", user_role="wholesale_level4")`, прогнать `process_price_types` на реальном файле → `product_field` остался `"opt4_price"`, `user_role` остался `"wholesale_level4"`
  - [x] 4.4: Тест C (AC4): найти в реальном `prices_*.xml` первое предложение с ценой вида «Опт 4», создать `Product` + `ProductVariant` с его `onec_id`, вызвать `update_variant_prices` → `variant.opt4_price` равен значению из XML — **зелёный на снимке от 2026-08-02**
  - [x] 4.5: Тест D (AC6): вызвать `update_variant_prices` и `process_price_types` на тех же данных **дважды** → `opt4_price` не изменился, `PriceType.objects.filter(onec_id=GUID).count() == 1` — разделён на два теста, **оба зелёные**
  - [x] 4.6: Маркеры: `pytestmark = [pytest.mark.integration, pytest.mark.data_dependent, pytest.mark.django_db]`

- [x] **Task 5: Прогон и регресс** (AC: 7)
  - [x] 5.1: Полный unit-прогон (эквивалент `make test-unit`, команды — в Dev Notes)
  - [x] 5.2: Полный integration-прогон (≈ 27 мин, запускать в фоне)
  - [x] 5.3: `black --check` + `flake8` по изменённым файлам
  - [x] 5.4: `npx gitnexus detect-changes --scope all` перед коммитом

## Dev Notes

### ⚠️ Первое, что нужно знать: состояние снимков данных (проверено 2026-08-02)

| Каталог | Состояние | Вывод |
|---|---|---|
| `backend/data/import_1c/priceLists/priceLists_1_1_6e305b99-b33f-403d-a401-f5aaae62fbc3.xml` | ✅ **Переснят 2026-08-02** (`ДатаФормирования="2026-08-02T09:44:22"`), содержит **8** видов цен: Опт 1/2/3, Тренерская, **Партнер**, **Опт 4**, МРЦ, РРЦ | AC1 в части `priceLists` закрыт. Байт-в-байт совпадает с закоммиченным `data/webdata/Обмен локальный/priceLists/priceLists_1_1_cf9c66b9-*.xml` (коммит `bdd5ec9c`) |
| `backend/data/import_1c/prices/prices_1_1..1_6_*.xml` | ❌ **Старый снимок**, `ДатаФормирования="2025-11-26T12:20:34"`. GUID «Опт 4» — **0 вхождений** во всех шести файлах | AC1 в части `prices` **не закрыт** → AC4 нечем проверить. Task 0 блокирует стори |

**Путь важен: данные лежат в `backend/data/import_1c/`, а не в `data/import_1c/`** (как написано в epics.md и в AC исходной формулировки). Каталога `data/import_1c/` в репозитории не существует. `backend/data/import_1c/` целиком в `.gitignore` (строка 206) — снимки не версионируются, обновляются вручную.

В Docker (`docker/docker-compose.test.yml:72`) каталог примонтирован как `/app/data/import_1c`.

### Blast radius (обязательный pre-flight выполнен)

`npx gitnexus impact _map_price_type_to_field --direction upstream` → **risk: LOW**

- Прямых вызывающих: **1** — `XMLDataParser.parse_price_lists_xml` (`parser.py:464`)
- Глубина 2: `Command._import_price_types` и `Command._dry_run_import` в `backend/apps/products/management/commands/import_products_from_1c.py`
- Затронутых процессов: 1 (`handle` команды импорта), модулей: 2 (Services, Commands)

Изменение аддитивное — новая ветка `elif` перед fallback'ом; ни одна из точек вызова правок не требует.

⚠️ Индекс GitNexus на момент создания стори помечен `stale` (проиндексирован `65ab060`, HEAD `50e49d0`), но расхождение — единственный docs-коммит. Если `context`/`impact` вернёт `{"error": "Symbol ... not found"}` на заведомо существующий символ — попроси Alex выполнить `! npx gitnexus analyze`.

### Точный код: ветка в `_map_price_type_to_field`

`backend/apps/products/services/parser.py`, метод начинается на строке 536. Вставить между веткой `«опт 3»` и веткой `«тренер»`:

```python
        elif "опт 4" in name_lower or "опт4" in name_lower:
            return "opt4_price"
```

Итоговый порядок веток: `опт 1` → `опт 2` → `опт 3` → **`опт 4`** → `тренер` → `ррц` (внутри: `рекоменд` → `rrp`, иначе `retail_price`) → `мрц` → `рознич` → `else: retail_price`.

Обобщающей ветки «опт» без цифры сегодня в коде нет — перехватить строку может только `else`-fallback. Требование «до общих веток» из AC выполняется автоматически при вставке в указанное место; не переписывать метод на словарь/регулярку — правка должна быть однострочной по образцу соседей.

Наименование в выгрузке — `Опт 4 (до 50 тыс.руб в квартал)`; `name_lower = onec_name.lower()` уже применён в первой строке метода, поэтому регистр обрабатывается сам.

### Точный код: `opt4_price=None` при создании варианта

Два места, оба — **конструктор `ProductVariant(...)`**, а не сброс:

`variant_import.py:841-845` (`process_variant_from_offer`):

```python
            retail_price=Decimal("0"),
            opt1_price=None,
            opt2_price=None,
            opt3_price=None,
            opt4_price=None,          # ← добавить
            trainer_price=None,
            federation_price=None,
```

`variant_import.py:999-1003` (`create_default_variants`) — тот же блок с отступом на 4 пробела больше.

### Что на самом деле в строках 843/1001 (расхождение с формулировкой AC в epics.md)

Исходная формулировка AC говорит про «сбросы цен … перед обновлением» и обосновывает их тем, что «снятая в 1С цена останется на портале навсегда». Это **неточно**, и дев не должен пытаться реализовать несуществующее поведение:

- Строки 841-845 и 999-1003 — **начальные значения при создании нового `ProductVariant`**. Поле nullable, `None` там и так был бы по умолчанию. Правка **семантически no-op** и делается ради консистентности блока (чтобы следующий читатель не решил, что уровень 4 забыли).
- Механизма «сброса цен перед обновлением» в коде **нет**: `update_variant_prices` (`variant_import.py:1039-1105`) строит `price_updates` только из тех `<Цена>`, что пришли в XML, и делает `variant.save(update_fields=...)` строго по ним. Цена, снятая в 1С, на портале действительно остаётся — но это **предсуществующее поведение для всех уровней 1-3 и `trainer`**, и в объём эпика 39 оно не входит.
- **НЕ реализовывать** очистку отсутствующих в выгрузке цен. Это изменило бы поведение всех ценовых полей сразу, затронуло бы каждый частичный обмен и вышло бы далеко за рамки стори.

### Как цена доезжает до поля: полная цепочка

1. `import_products_from_1c.py:378` → `parser.parse_price_lists_xml(file)` → для каждого `<ТипЦены>` вызывает `_map_price_type_to_field(<Наименование>)` → `PriceTypeData{onec_id, onec_name, product_field, currency}`.
2. `import_products_from_1c.py:380` → `processor.process_price_types([price_type])` → `PriceType.objects.update_or_create(onec_id=..., defaults={onec_name, product_field, is_active})` (`variant_import.py:1521-1548`).
3. Позже, при обработке `prices_*.xml`: `update_variant_prices` находит `PriceType.objects.filter(onec_id=price_type_id, is_active=True).first()`, берёт `price_type.product_field` как имя поля (`variant_import.py:1081`) и пишет туда значение.

**Ключевое следствие для этой стори:** `user_role` **отсутствует** в `defaults` у `process_price_types` — значение `"wholesale_level4"`, записанное data-миграцией `0053_seed_price_type_opt4.py` из стори 39.1, импорт не затирает никогда. А вот `product_field` затирается, и именно это чинит Task 1.

### Наследство стори 39.1 (закрывается здесь)

Dev Notes 39.1 фиксировали дыру: «`PriceType.product_field` для „Опт 4“ перетирается импортом на `retail_price`, и цены вида „Опт 4“ пишутся в розничную цену; **не запускать импорт цен между 39.1 и 39.2**». После Task 1 запрет снимается — маппер начнёт возвращать то же значение, что записала миграция.

Если импорт всё-таки прогоняли на локальной БД до этой правки: `product_field` записи «Опт 4» сбит на `retail_price`, а `retail_price` части вариантов испорчен. Починка записи справочника — повторный вызов идемпотентной `seed_opt4_price_type` из миграции `0053`; испорченные `retail_price` чинятся только переимпортом цен.

Что 39.1 уже сделала и переделывать **не нужно**: поле `ProductVariant.opt4_price` + `CheckConstraint products_opt4_price_positive`, choice `("opt4_price", "Оптовая цена уровень 4")` в `PriceType.product_field` (`models.py:725`), data-миграция `PriceType` «Опт 4», роль `wholesale_level4` в `User`, `get_price_for_user`, `ONEC_EXCHANGE`.

### ⚠️ Мина: вид цен «Партнер» в новом снимке

Переснятый `priceLists` содержит **8** видов цен вместо ожидавшихся семи — вместе с «Опт 4» в выгрузку попал **«Партнер»** (`200a24fe-f07d-11eb-81f3-00155d3cae02`). Задание (`dev-task-role-from-1c-agreement.md`, §2.3) утверждает, что «Партнер» на портал не выгружается и записи `PriceType` не имеет — **это утверждение устарело**.

Последствие: первый же импорт priceLists заведёт `PriceType(«Партнер») → product_field="retail_price"` (через `else`-fallback маппера). Пока в `prices_*.xml` нет цен этого вида (в старом снимке — 0 вхождений), вреда нет. Если после Task 0 они появятся — партнёрская цена уедет в `retail_price` и затрёт розничную.

**В объём стори 39.2 это не входит.** Действие дева: выполнить проверку 0.4 и, при обнаружении, эскалировать Alex отдельным дефектом. Не добавлять ветку «партнер» в маппер самовольно — маппинг на роль `federation_rep` затрагивает `federation_price` и решения эпика 40 (FR-40-13 явно исключает `federation_rep`).

### Точный код: фикстура пути к реальному датасету

Образец — `backend/tests/integration/test_link_then_import_1c.py:36-46`. Для нового файла:

```python
import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.data_dependent, pytest.mark.django_db]

OPT4_PRICE_TYPE_GUID = "4c1962d2-f8ed-11eb-81f3-00155d3cae02"


def _import_1c_dir() -> Path:
    """Каталог реальных выгрузок 1С: в Docker примонтирован в /app/data."""
    if os.path.exists("/app/data"):
        return Path("/app/data/import_1c")
    # backend/tests/integration/<file>.py → parents[2] == backend/
    return Path(__file__).resolve().parents[2] / "data" / "import_1c"


@pytest.fixture
def price_lists_file() -> str:
    matches = sorted(_import_1c_dir().glob("priceLists/priceLists_*.xml"))
    if not matches:
        pytest.skip("Реальный снимок priceLists из 1С не найден")
    return str(matches[0])
```

⚠️ В существующем `test_link_then_import_1c.py:42` для локальной ветки используется `parents[3]` — это указывает на корень репозитория, где каталога `data/import_1c` нет, и тест локально просто скипается. В **новом** файле бери `parents[2]` (= `backend/`). Существующий файл при этом **не править** — вне объёма стори.

Для файла цен фильтруй по содержимому, а не по имени: файлов шесть по ~2.8 МБ, GUID «Опт 4» будет не во всех.

```python
@pytest.fixture
def prices_file_with_opt4() -> str:
    for path in sorted(_import_1c_dir().glob("prices/prices_*.xml")):
        if OPT4_PRICE_TYPE_GUID in path.read_text(encoding="utf-8"):
            return str(path)
    pytest.skip(f"В снимке prices нет цен вида «Опт 4» ({OPT4_PRICE_TYPE_GUID}) — переснимите выгрузку")
```

Скип с внятным текстом обязателен: пока Task 0 не выполнен, тест AC4 должен объяснять причину, а не падать.

### Как построить кейс AC4 экономно

`parse_prices_xml` на одном реальном файле возвращает ~4700 предложений. Не создавай под них варианты — возьми первое подходящее:

```python
parsed = XMLDataParser().parse_prices_xml(prices_file_with_opt4)
entry = next(
    item for item in parsed
    if any(p["price_type_id"] == OPT4_PRICE_TYPE_GUID for p in item["prices"])
)
```

Дальше: создать `PriceType(onec_id=OPT4_PRICE_TYPE_GUID, product_field="opt4_price", user_role="wholesale_level4", is_active=True)`, создать `Product` + `ProductVariant(onec_id=entry["id"], retail_price=Decimal("0"))`, вызвать `processor.update_variant_prices(entry)`, перечитать вариант из БД и сравнить `opt4_price` с ожидаемым значением из `entry`.

`ProductVariant` ищется по `onec_id` (`_get_variant_by_onec_id`); при отсутствии варианта метод вернёт `False` и запишет warning — не создав вариант заранее, получишь молча зелёный `assert result is False`, а не проверку AC.

Структура элемента: `{"id": <onec_id предложения>, "prices": [{"price_type_id": ..., "value": Decimal, ...}, ...]}`.

### Куда класть тесты

| Что | Файл | Маркеры |
|---|---|---|
| Строковый маппинг «Опт 4» (AC2) | `backend/tests/unit/test_services/test_xml_parser.py` — расширить `TestXMLDataParser.test_map_price_type_to_field` (строка 231) | уже `@pytest.mark.unit` на классе |
| `process_price_types` на реальном priceLists, сохранность `user_role`, импорт цены, идемпотентность (AC3, 4, 6) | `backend/tests/integration/test_import_opt4_prices.py` — **новый** | `integration` + `data_dependent` + `django_db` |

Не добавляй новые синтетические XML в `backend/tests/integration/test_variant_import.py` — там есть предсуществующие `SAMPLE_*_XML` константы, но расширять их под «Опт 4» запрещено NFR-3940-01. Существующие тесты в `test_xml_parser.py` (`test_parse_price_lists_xml`, `test_parse_prices_xml_with_role_mapping`) тоже построены на синтетике — это предсуществующий долг, не трогать и не «исправлять».

Уникальные строковые данные (SKU, slug, onec_id) — через `get_unique_suffix()` из `backend/tests/conftest.py`. Автоиспользуемая фикстура `clear_db_before_test` (`conftest.py:671`) делает каждый тест в `backend/tests/` транзакционным с последующим flush — на данные из data-миграций (в т.ч. на запись `PriceType` «Опт 4» из `0053`) в тестах **не рассчитывать**, создавать их явно.

### Команды

```bash
# Точечный прогон нового теста
cd /c/Users/1/DEV/FREESPORT/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs tests/integration/test_import_opt4_prices.py

# Эквивалент make test-unit (make в оболочке недоступен, таргеты ищут несуществующий docker/.env)
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend pytest -q -m unit
# Эквивалент make test-integration (≈27 мин — в фоне)
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend pytest -q -m integration
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down

# Линтеры — в dev-контейнере, из корня репозитория
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  flake8 apps/products/services/parser.py apps/products/services/variant_import.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  black --check apps/products/services/parser.py apps/products/services/variant_import.py
```

Ориентиры длительности: unit ≈ 8 мин, integration ≈ 27 мин. PostgreSQL обязателен, SQLite не поддерживается.

### Релизное правило эпика

Стори эпика 39 **на прод по одной не выкатываются** (решение Alex, 2026-08-02): релиз собирается после 39.1 → 39.2 → 39.3 → 39.4 целиком. Промежуточная несогласованность, живущая в релизной ветке после этой стори: роль `wholesale_level4` уже видна в публичном `user_roles_view`, но `UserRegistrationSerializer.SELF_SERVICE_ROLES` её не принимает → самостоятельная регистрация с ней даёт 400. Чинится стори **39.3**, здесь не трогать.

### Антипаттерны (НЕ ДЕЛАТЬ)

- **НЕ** создавать синтетические XML для тестов импорта 1С — только реальные файлы из `backend/data/import_1c/` (NFR-3940-01, `project-context.md` §4, `CLAUDE.md`).
- **НЕ** обходить блокировку Task 0 подделкой файла цен «на основе реального» — это тот же синтетический XML.
- **НЕ** реализовывать очистку цен, отсутствующих в выгрузке, — предсуществующее поведение для всех уровней, вне объёма.
- **НЕ** трогать `products/filters.py`, `products/serializers.py`, `products/views.py`, `products/admin.py`, `products/factories.py`, `users/serializers.py`, `users/admin.py`, `banners/services.py`, `docs/api/openapi.yaml` — это стори **39.3**.
- **НЕ** трогать `frontend/` — это стори **39.4**.
- **НЕ** трогать `products/models.py`, миграции и `ONEC_EXCHANGE` — сделано в **39.1**.
- **НЕ** заполнять `user_role` у остальных записей `PriceType` — это стори **40.3**.
- **НЕ** добавлять ветку «партнер» в маппер (см. «Мина: вид цен „Партнер“»).
- **НЕ** рефакторить `_map_price_type_to_field` в словарь/регулярку — правка однострочная, по образцу соседних веток.
- **НЕ** править `parents[3]` в `test_link_then_import_1c.py`.

### Project Structure Notes

- Реальные выгрузки 1С: `backend/data/import_1c/` (gitignored, `.gitignore:206`), в Docker — `/app/data/import_1c`. В epics.md путь указан как `data/import_1c/` — это сокращение, каталога в корне нет.
- Комментарии и docstrings нового кода — на русском (NFR-3940-10, `project-context.md` §6).
- Типизация полей и возвратов — как в окружающем коде (`cast()`, аннотации на сигнатурах).
- Покрытие: `products` — критический модуль, ≥ 90 %; общее ≥ 70 % (NFR-3940-03).
- Django 5.2.7, Python 3.14 (см. `backend/requirements.txt`). Новых зависимостей стори не вводит.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 39.2: Импорт цен «Опт 4» из 1С — AC в BDD-формате]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 39 — порядок стори, релизное решение, атомарность выката]
- [Source: _bmad-output/planning-artifacts/epics.md#Requirements Inventory — FR-39-05, NFR-3940-01, -02, -03, -08, -10]
- [Source: _bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md#2.3 Виды цен — GUID и наименования]
- [Source: _bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md#B2 Прикладной код — parser.py:546, variant_import.py:843,1001]
- [Source: _bmad-output/implementation-artifacts/Story/39-1-wholesale-level4-role-and-opt4-price-model.md#Почему product_field нельзя считать декоративной колонкой]
- [Source: backend/apps/products/services/parser.py:464 — parse_price_lists_xml; :536-558 — _map_price_type_to_field]
- [Source: backend/apps/products/services/variant_import.py:841-845, :999-1003 — начальные значения цен при создании ProductVariant]
- [Source: backend/apps/products/services/variant_import.py:1039-1105 — update_variant_prices, маршрутизация по product_field]
- [Source: backend/apps/products/services/parser.py:382 — parse_prices_xml, структура PriceData]
- [Source: backend/apps/products/services/variant_import.py:1521-1548 — process_price_types, user_role не в defaults]
- [Source: backend/apps/products/management/commands/import_products_from_1c.py:370-386 — _import_price_types]
- [Source: backend/apps/products/models.py:693-757 — PriceType, choices product_field]
- [Source: backend/data/import_1c/priceLists/priceLists_1_1_6e305b99-b33f-403d-a401-f5aaae62fbc3.xml — снимок от 2026-08-02, 8 видов цен]
- [Source: backend/tests/integration/test_link_then_import_1c.py:36-46 — образец фикстуры реального датасета со skip]
- [Source: backend/tests/unit/test_services/test_xml_parser.py:231 — test_map_price_type_to_field]
- [Source: backend/tests/conftest.py:671 — autouse clear_db_before_test на transactional_db]
- [Source: docker/docker-compose.test.yml:70-72 — монтирование backend/data/import_1c в /app/data/import_1c]
- [Source: backend/pytest.ini:5-9 — маркеры unit / integration / data_dependent / slow]
- [Source: project-context.md §3, §4, §5, §6 — role-based pricing, тестирование, GitNexus-дисциплина, язык кода]

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, bmad-dev-story)

### Debug Log References

**Pre-flight GitNexus (2026-08-02).** Индекс `stale` (проиндексирован `65ab060`, HEAD `50e49d0` — единственный расходящийся коммит docs-only), символы находятся корректно, переиндексация не потребовалась.

`npx gitnexus impact _map_price_type_to_field --direction upstream` — **risk: LOW**:

- depth 1: `XMLDataParser.parse_price_lists_xml` (`parser.py:464`)
- depth 2: `Command._import_price_types`, `Command._dry_run_import` (`import_products_from_1c.py`)
- depth 3: `Command.handle`

`npx gitnexus detect-changes --scope all` — 4 файла, 6 символов, risk **medium**, 2 затронутых потока:

- `XMLDataParser`, `_map_price_type_to_field` (`parser.py`)
- `VariantImportProcessor`, `_create_new_variant`, `create_default_variants`, `variant` (`variant_import.py`)
- потоки: `Process_variant_from_offer → _ensure_unique_sku`, `Process_variant_from_offer → _log_error`

Неожиданных символов нет. Примечание: конструктор из AC5, названный в стори `process_variant_from_offer`, фактически расположен в приватном методе `_create_new_variant` — правка сделана именно там (`variant_import.py:844`).

**Состояние снимков данных — прогон 1 (до Task 0.2), 2026-08-02.**

- `priceLists/` — фактическое имя файла `priceLists_1_1_cf9c66b9-08cc-4b54-97c8-f5390a466841.xml` (в Dev Notes указано `…6e305b99…`); содержимое совпадает — 8 видов цен, `ДатаФормирования="2026-08-02T09:44:22"`, GUID «Опт 4» присутствует. Фикстура берёт файл по glob-маске, расхождение имени на тест не влияет.
- `prices/` — старый снимок `ДатаФормирования="2025-11-26T12:20:34"`, 6 файлов. GUID «Опт 4» — **0 вхождений** во всех шести (Task 0.1 подтверждён). AC4 не проверяем → блокировка.
- Task 0.4 на старом снимке: GUID «Партнер» — 0 вхождений, эскалация не требовалась.

**Состояние снимков данных — прогон 2 (после Task 0.2), 2026-08-02.**

Alex переснял выгрузку скриптом `run-opt4-prices-export.ps1`. Диагноз причины, по которой прежний `run-price-list-export.ps1` не давал файлов цен: он регистрировал в `БУС_ТаблицаИзменений` только тип `Прайс` (справочник видов цен), но не `Цена` (значения). Новый скрипт регистрирует `Цена` для 3318 товаров с ценами «Опт 4» (по `РегистрСведений.ЦеныНоменклатуры.СрезПоследних`) + `Прайс`, затем вызывает `БУС_ОбменССайтомВызовСервера.ВыполнитьОбмен`. COM-компонент `V83.COMConnector` 32-битный → запуск через `C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe`.

- `priceLists/priceLists_1_1_5d241e67-0df1-443b-9401-0c89df624701.xml` — `ДатаФормирования="2026-08-02T16:56:54"`, 8 видов цен (состав прежний).
- `prices/` — **8 файлов** вместо 6, `ДатаФормирования` 16:57:46 … 16:58:54, суммарно ~28 МБ:
  `prices_1_1_fbdb877c-…`, `1_2_216461b9-…`, `1_3_de2b154d-…`, `1_4_ff5067af-…`, `1_5_7b3d6156-…`, `1_6_8a537456-…`, `1_7_92c9e4eb-…`, `1_8_d74a852e-…`
- **Task 0.3 ✅** — GUID «Опт 4» встречается **7219 раз** в `prices/` (961/963/975/958/965/965/957/475 по файлам) + 1 раз в `priceLists`. Носителем для теста AC4 служит первый по сортировке файл — `prices_1_1_fbdb877c-a1a8-4bf4-ba19-07f11ded74bf.xml` (961 вхождение).
- **Task 0.4 ⚠️** — GUID «Партнер» `200a24fe-f07d-11eb-81f3-00155d3cae02` в новом снимке **ПОЯВИЛСЯ**: 6639 вхождений. Проведён количественный анализ, дефект эскалирован — см. Completion Notes → «Дефект на эскалацию».

**Прогоны тестов (Docker + PostgreSQL, project `freesport-test`).**

| Прогон | Результат |
|---|---|
| RED: `pytest -q tests/unit/test_services/test_xml_parser.py -k map_price_type` до правки | 2 failed — `assert 'retail_price' == 'opt4_price'` |
| GREEN: тот же после правки `parser.py` | 2 passed |
| `pytest -q -rs tests/integration/test_import_opt4_prices.py` — **старый** снимок prices | 3 passed, 2 skipped (скип с текстом «В снимке prices нет цен вида „Опт 4“ … — переснимите выгрузку») |
| `pytest -q -m unit` (полный) | **1037 passed**, 1 skipped, 1596 deselected, 6:56 |
| `pytest -q -m integration` (полный) — старый снимок | **729 passed**, 4 skipped, 1901 deselected, 26:24 |
| `pytest -q -rs tests/integration/test_import_opt4_prices.py` — **новый** снимок prices | **5 passed, 0 skipped**, 27 с — без единой правки кода |
| `pytest -q -rs -m integration` (полный) — **новый** снимок, регресс всего датасета | **731 passed**, 2 skipped, 1901 deselected, 26:47 |
| `black --check` по `parser.py`, новому тесту, `test_xml_parser.py` | чисто |
| `flake8` по всем четырём изменённым файлам | чисто |

Оба скипа финального прогона — предсуществующие и к 1С не относятся: `test_auth_api.py:43` (генерация схемы падает на импорте `Decimal`), `test_auth_api.py:72` (Swagger UI не сконфигурирован в тестовом окружении). Прирост 729 → 731 — это ровно два теста «Опт 4», позеленевших после смены снимка.

Предсуществующий долг (**не мой diff, не исправлял**): `black --check apps/products/services/variant_import.py` падает на строке ~1739 (`logger.info(f"Repair-якорь …")` в `process_categories`) — форматирование сломано до этой стори, правка вне объёма 39.2. `flake8` на этот файл при этом чист.

### Completion Notes List

**Реализовано и проверено:**

- **AC2 ✅** — ветка `elif "опт 4" in name_lower or "опт4" in name_lower: return "opt4_price"` вставлена в `_map_price_type_to_field` строго между `«опт 3»` и `«тренер»` (`parser.py:547-548`). Метод не рефакторился, правка однострочная по образцу соседей. `parse_price_lists_xml` правок не потребовал (Task 1.2).
- **AC3 ✅** — подтверждено на **реальном** `priceLists_1_1_cf9c66b9-*.xml`: запись GUID `4c1962d2-f8ed-11eb-81f3-00155d3cae02` парсится в `product_field == "opt4_price"`, `process_price_types` пишет это значение в `PriceType`. Отдельным тестом закрыт регресс 39.1: при предсуществующей записи с `user_role="wholesale_level4"` импорт не сбивает ни `product_field`, ни `user_role`. Запрет «не запускать импорт цен между 39.1 и 39.2» снят.
- **AC5 ✅** — `opt4_price=None` добавлен в оба конструктора `ProductVariant`: `variant_import.py:844` (`_create_new_variant`) и `variant_import.py:1003` (`create_default_variants`). Логику очистки цен в `update_variant_prices` **не добавлял** (Task 2.3, Dev Notes).
- **AC1 ✅** — оба снимка пригодны для тестов: `priceLists` содержит вид цен «Опт 4» (переснят 09:44), `prices` содержит 7219 цен этого вида (переснят 16:57-16:58, Task 0.2 выполнена Alex).
- **AC4 ✅** — на реальном `prices_1_1_fbdb877c-*.xml` `update_variant_prices` заполняет `ProductVariant.opt4_price` значением из выгрузки. Тест `test_real_prices_fill_variant_opt4_price` зелёный.
- **AC6 ✅** — обе части: повторный прогон `process_price_types` не плодит `PriceType` (`count() == 1`) и не меняет `product_field`/`user_role`; повторный прогон `update_variant_prices` не меняет `opt4_price` и не создаёт дублирующих `ProductVariant`.
- **AC7 ✅** — синтетических XML не создавал. Unit-тест маппера оперирует строками; интеграционный файл работает только с реальными выгрузками, помечен `[integration, data_dependent, django_db]` и корректно скипается с внятным текстом при отсутствии данных (проверено эмпирически: на старом снимке скипался, на новом позеленел без правок).

**Отклонение от буквы стори (осознанное):** Task 4.5 (тест D) разделён на два теста вместо одного — `test_price_types_import_is_idempotent` (только `priceLists`) и `test_repeated_price_import_keeps_opt4_price_stable` (нужен `prices`). Мотив: на момент написания единый тест целиком скипался бы вместе с частью AC6, которую данные позволяли проверить сразу. Разделение оставлено и после получения данных — оно точнее локализует падение.

### ⚠️ Дефект на эскалацию (вне объёма 39.2): вид цен «Партнер» в выгрузке цен

Проверка Task 0.4 на новом снимке **сработала**. Предупреждение из Dev Notes подтвердилось: GUID `200a24fe-f07d-11eb-81f3-00155d3cae02` («Партнер») в новой выгрузке цен присутствует — 6639 вхождений. В маппере ветки «партнер» нет, поэтому `_map_price_type_to_field("Партнер")` уходит в `else`-fallback и возвращает `retail_price`.

Количественный анализ всех 8 файлов (`<Предложение>` — 7274 шт.):

| Категория | Кол-во | Последствие |
|---|---|---|
| Предложений с ценой «Партнер» | 6639 | — |
| … из них «РРЦ» присутствует **после** «Партнера» | 6608 | безвредно: `price_updates["retail_price"]` перезаписывается значением РРЦ, побеждает последний |
| … из них «Партнер» идёт **после** «РРЦ» | 0 | — |
| … из них «РРЦ» отсутствует вовсе | **31** | **`retail_price` получает партнёрскую цену** |

**Итог: 31 вариант получит испорченный `retail_price` при первом же полном импорте цен.**

Критично, что 6608 предложений спасает **только порядок элементов в XML** — оба вида цен маппятся в одно поле `retail_price`, и в `update_variant_prices` (`variant_import.py:1082`) применяется `price_updates[field_name] = price_value`, где побеждает последний по порядку. Если 1С когда-нибудь изменит порядок `<Цена>` внутри `<Предложение>`, порча мгновенно расширится с 31 варианта до 6639.

Чинить в этой стори **запрещено** явным указанием Dev Notes: маппинг «Партнера» затрагивает роль `federation_rep` / поле `federation_price` и пересекается с решениями эпика 40 (FR-40-13 явно исключает `federation_rep`). Требуется отдельный дефект и решение Alex о целевом поле для «Партнера».

**До принятия решения не запускать полный импорт цен на проде** — иначе 31 товар получит партнёрскую цену вместо розничной.

### Замечание по артефактам выгрузки в git

`data/webdata/Обмен локальный/` **не** в `.gitignore` (в отличие от `backend/data/import_1c/`). После выгрузки там появились `prices/` (~28 МБ, 8 файлов) и новый `priceLists`, а старый `priceLists_1_1_cf9c66b9-*.xml` удалён. В File List этой стори они не включены и мной не коммитились — решение о судьбе 28 МБ XML в истории репозитория за Alex.

### File List

- `backend/apps/products/services/parser.py` — изменён (ветка «Опт 4» в `_map_price_type_to_field`)
- `backend/apps/products/services/variant_import.py` — изменён (`opt4_price=None` в двух конструкторах `ProductVariant`)
- `backend/tests/unit/test_services/test_xml_parser.py` — изменён (кейсы «Опт 4» + новый `test_map_price_type_to_field_branch_order`)
- `backend/tests/integration/test_import_opt4_prices.py` — **новый** (5 тестов: AC3 ×2, AC4, AC6 ×2)
- `_bmad-output/implementation-artifacts/Story/39-2-import-opt4-prices-from-1c.md` — изменён (frontmatter, чекбоксы, Dev Agent Record, Change Log)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — изменён (`39-2-…: ready-for-dev → in-progress`)

## Change Log

| Дата | Изменение |
|---|---|
| 2026-08-02 | Task 1-5 выполнены: маппинг «Опт 4» → `opt4_price` в парсере 1С, `opt4_price=None` в конструкторах `ProductVariant`, unit-тест маппера + сторож порядка веток, интеграционный тест на реальных выгрузках. AC2, AC3, AC5, AC7 закрыты; AC6 закрыт частично. Полный регресс: unit 1037 passed, integration 729 passed. |
| 2026-08-02 | AC1 (часть `prices/`) и AC4 заблокированы Task 0 — требуется свежая выгрузка цен из 1С от Alex. Тесты написаны и скипаются с диагностикой. |
| 2026-08-02 | Task 0 закрыта: Alex переснял выгрузку цен (8 файлов, 7219 вхождений GUID «Опт 4»). Тесты «Опт 4» — 5 passed, 0 skipped, без правок кода. Полный интеграционный регресс на новом датасете — 731 passed, 2 skipped (предсуществующие). **AC1-AC7 закрыты полностью**, стори переведена в `review`. |
| 2026-08-02 | Проверка Task 0.4 сработала: вид цен «Партнер» появился в выгрузке цен (6639 вхождений), 31 вариант под порчей `retail_price`. Дефект эскалирован Alex отдельно, в объём 39.2 не входит. |
