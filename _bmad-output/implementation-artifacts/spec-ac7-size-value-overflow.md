---
title: 'AC7 — size_value не вмещает данные 1С'
type: 'bugfix'
created: '2026-08-27'
status: 'done'
baseline_commit: '6b09ae6c'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/tasks/dev-task-size-value-overflow.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Импорт 1С пишет `ProductVariant.size_value` (`varchar(50)`) напрямую, минуя валидацию Django. Значение длиннее 50 символов роняет `DataError: value too long`, и вариант **не создаётся вообще** — 12 вариантов потеряно 25.08.2026 в окне `offers` 17:20–17:24.

**Approach:** Нормализация на входе (вариант Б по решению Alex 2026-08-27): значение длиннее лимита поля отбрасывается, вариант сохраняется с пустым `size_value`, факт отбрасывания виден в счётчике `report_details` и в текстовом `report` сессии. Схема БД не меняется.

## Boundaries & Constraints

**Always:**
- Порог = `max_length` поля `size_value` (50). Брать из модели, не хардкодить второй раз — рассинхрон порога и колонки недопустим.
- Длинное значение **отбрасывается целиком** (`""`), не усекается: усечённый мусор попал бы в `db_index` и в композитный индекс `idx_variant_characteristics`.
- Отбрасывание видно и в `stats` (→ `report_details`), и в текстовом `report` сессии — не только в логах воркера.
- Нормализация применяется к обоим источникам значения: характеристике 1С (`parse_characteristics`) и fallback из скобок наименования (`extract_size_from_name`).
- Тесты — только Docker + PostgreSQL. Данные для тестов — только реальные XML из `data/import_1c/`.

**Ask First:**
- Любое изменение схемы `ProductVariant` (миграция) — вариант А отклонён, возврат к нему требует решения Alex.
- Понижение порога ниже 50 (например до 20) — затронет 674 существующих значения, решение Alex.

**Never:**
- Не усекать значение. Не менять `max_length`. Не создавать миграции.
- Не изобретать регулярку «настоящего размера» — критерий только по длине.
- Не трогать существующие 674 записи длиной 11–20 — они вне контракта.
- Не генерировать синтетические XML для тестов импорта.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Обычный размер | характеристика `Размер_Бутсы` = `42` | `size_value = "42"`, счётчик не растёт | N/A |
| Fallback из скобок | наименование `... (А5 (2XL))`, характеристики размера нет | `size_value = "А5 (2XL)"` | N/A |
| Длинное из fallback | наименование `Оборудование спортивное уличное (Romana 701.09.00 Боксерская груша подвесная (стандартный))` → 57 символов | вариант **создан**, `size_value = ""`, `size_value_dropped += 1`, запись в `report` | нет исключения |
| Длинное из характеристики | характеристика `Размер` длиной > 50 | то же самое | нет исключения |
| Ровно 50 символов | значение длиной 50 | сохраняется целиком | N/A |
| Обновление варианта | у существующего варианта валидный `size_value`, приехало длинное | `size_value` **не затирается**, счётчик растёт | нет исключения |

</frozen-after-approval>

## Code Map

- `backend/apps/products/services/variant_import.py` — единственное место записи `size_value`. Строки ~135–172 `parse_characteristics`, ~175–194 `extract_size_from_name`, ~774–790 `_update_existing_variant`, ~838–846 `_create_new_variant`, ~289 инициализация `stats`, ~2189 `log_progress` (пишет в текстовый `report`), ~2249 `finalize_session` (`session.report_details = self.stats`).
- `backend/apps/products/models.py:854` — `ProductVariant.size_value`, `max_length=50`, `db_index=True`; композитный индекс `idx_variant_characteristics` по `(color_name, size_value)` — строка ~1103.
- `backend/apps/products/tests/test_import_session_report.py`, `test_import_backup_step.py` — образец объёма и оформления тестов AC5/AC6.
- `data/import_1c/offers/offers_1_14_e934b984-5c19-4e5a-af44-22174913fe9f.xml` — реальный оффер `45d113f2-...#3538958e-...`, fallback даёт 57 символов. Аналог прод-случая.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/products/tests/test_import_size_value_overflow.py` — **сначала** написать тест на реальном оффере из `data/import_1c/offers/`, прогнать и показать RED (`DataError` / вариант `None`) — иначе тест ничего не ловит. Маркер `data_dependent` проставить вручную: каталог под `.gitignore`, на CI теста нет.
- [x] `backend/apps/products/services/variant_import.py` — добавить в `stats` ключ `size_value_dropped: 0` (рядом с `warnings`) — чтобы отличать «не сработало» от «код не задеплоен».
- [x] `backend/apps/products/services/variant_import.py` — метод `VariantImportProcessor._normalize_size_value(value, onec_id) -> str`: длину сверяет с `max_length` поля из `_meta`, при превышении возвращает `""`, растит `size_value_dropped` и `warnings`, пишет `log_progress` с `onec_id` и обрезанным до 60 символов значением. Поток `log_progress` ограничить первыми 50 срабатываниями за сессию — дальше только счётчик, чтобы аномальная выгрузка не устроила лавину UPDATE.
- [x] `backend/apps/products/services/variant_import.py` — вызвать `_normalize_size_value` в `_update_existing_variant` и `_create_new_variant` **до** fallback `extract_size_from_name` (брак характеристики) и **повторно** на результате самого fallback. Порядок принципиален: отбраковка после fallback теряет валидный размер из наименования, когда характеристика занята мусором.

**Acceptance Criteria:**
- Given реальный оффер, чей fallback даёт 57 символов, when `process_variant_from_offer`, then вариант создан, `size_value == ""`, `DataError` не возникает.
- Given отбрасывание произошло, when сессия финализирована, then `report_details["size_value_dropped"] >= 1` и текстовый `report` содержит строку с `onec_id` варианта.
- Given у существующего варианта валидный `size_value`, when приезжает длинное значение, then поле сохраняет прежнее значение.
- Given тест написан, when прогнан на коде **до** правки, then он падает (RED зафиксирован в отчёте).

## Design Notes

Замер на проде 27.08.2026 (пересъёмка подтвердила цифры брифа) плюс разбор реальных выгрузок дал факт, которого в брифе нет: **источник длинных значений — не характеристика «Размер», а fallback из скобок.** В 31 файле `data/import_1c/offers/` характеристик размера длиннее 40 символов **ноль**, а наименований, чьи последние скобки дают >50 символов, — **11 штук в 10 файлах**:

```
131  Благоустройство согласно Договору (Работы по благоустройству детской площадки...)
 77  Комплекс воркаут (3 турника, 2 скамейки для пресса, шведская стенка, канат...)
 57  Оборудование спортивное уличное (Romana 701.09.00 Боксерская груша подвесная (стандартный))
```

Отсюда два следствия. Первое: тест строится на реальных данных без единого синтетического XML. Второе: `extract_size_from_name` по конструкции берёт **любые** последние скобки — для «услуги по договору» это гарантированно не размер. Чинить сам fallback (сужать паттерн) в рамках AC7 **не нужно** — порог по длине закрывает контракт, а вопрос «что вообще должно попадать в size_value» — это вариант В брифа, разговор с 1С.

Порог 50, а не 20: диапазон 11–20 (674 записи) тоже почти целиком мусор (`в комплекте с сеткой`, `Стойка баскетбольная`, `Услуги комиссионера`), но среди него есть валидные (`40.5 EUR / 7.5 USA`, `70*1,5мм (75 метров)`). Порог 20 вычистил бы все 674 при следующей полной выгрузке — массовое изменение поведения ради дефекта на 9 записях. Контрактом не требуется.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs apps/products/tests/test_import_size_value_overflow.py` — expected: до правки RED, после правки все зелёные.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/integration/test_variant_import.py` — expected: регрессий нет.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend python manage.py makemigrations --check --dry-run` — expected: `No changes detected` (схема не тронута).
- `npx gitnexus detect-changes --scope all` — expected: затронуты только `variant_import.py` и новый тест.

**Manual checks:**
- После выката на прод: `SELECT max(length(size_value)) FROM product_variants` — не больше 50; в логах celery за окно выгрузки нет `Error saving variant`; 12 потерянных вариантов доезжают на следующей полной выгрузке.

## Suggested Review Order

**Сама отбраковка**

- Точка входа: решение о судьбе длинного значения целиком здесь.
  [`variant_import.py:1558`](../../backend/apps/products/services/variant_import.py#L1558)

- Порог снимается из модели один раз — разойтись с колонкой не может.
  [`variant_import.py:330`](../../backend/apps/products/services/variant_import.py#L330)

- Дедупликация по `onec_id`: счётчик считает варианты, а не встречи оффера.
  [`variant_import.py:1583`](../../backend/apps/products/services/variant_import.py#L1583)

- Общий `warnings` намеренно не растёт — иначе постоянный фон каждой выгрузки.
  [`variant_import.py:1588`](../../backend/apps/products/services/variant_import.py#L1588)

**Порядок вызова — самое важное место дифа**

- Брак характеристики до fallback, иначе теряется валидный размер из наименования.
  [`variant_import.py:799`](../../backend/apps/products/services/variant_import.py#L799)

- То же на пути создания нового варианта.
  [`variant_import.py:866`](../../backend/apps/products/services/variant_import.py#L866)

**Видимость в отчёте**

- Счётчик с нуля: отличает «не сработало» от «код не задеплоен».
  [`variant_import.py:299`](../../backend/apps/products/services/variant_import.py#L299)

- Лимит поимённых записей: `log_progress` делает UPDATE на каждый вызов.
  [`variant_import.py:264`](../../backend/apps/products/services/variant_import.py#L264)

**Тесты**

- Главный сценарий AC7 на реальном оффере из корпуса 1С.
  [`test_import_size_value_overflow.py:80`](../../backend/apps/products/tests/test_import_size_value_overflow.py#L80)

- Тот же assert в тесте, который реально идёт в CI.
  [`test_import_size_value_overflow.py:101`](../../backend/apps/products/tests/test_import_size_value_overflow.py#L101)

- Регрессия порядка: мусорная характеристика не съедает `(XL)` из наименования.
  [`test_import_size_value_overflow.py:166`](../../backend/apps/products/tests/test_import_size_value_overflow.py#L166)

- Границы лимита с обеих сторон и повторный оффер.
  [`test_import_size_value_overflow.py:128`](../../backend/apps/products/tests/test_import_size_value_overflow.py#L128)
