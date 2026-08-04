---
baseline_commit: 638d4fb16bec6c5ee2cbe430a5034d99e81df5e6
---

# Story 40.1: Парсер читает вид цен из выгрузки и ловит регресс выгрузки

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> 🚧 **БЛОКИРУЮЩЕЕ ПРЕДУСЛОВИЕ — снимок `backend/data/import_1c/contragents_pricetype/` относится к ПЕРВОЙ редакции патча БУС.**
> Проверено на `638d4fb1` (04.08.2026): в снимке 10 файлов, **4735** контрагентов, из них **485** с блоком `<ЗначенияРеквизитов>`; вхождений `СоглашениеСтатус` — **0**, вхождений `НетСоглашения` — **0**.
> Значит ветка «нет соглашения» второй редакции (`dev-task-bus-agreement-status.md`) **на прод и на тест ещё не наложена**, и AC1, AC3, AC7 на текущих данных физически непроверяемы.
> **Первое действие дева:** выполнить проверку из Task 0. Если `grep -c СоглашениеСтатус` даёт 0 — остановиться и сообщить Alex. Обходить синтетическим XML **запрещено** (NFR-3940-01).
> Код парсера и детектора (Task 1–3) писать можно и нужно: ветки «блок есть с GUID» и «блока нет» закрываются на текущих снимках. Гейтом является только приёмка AC1/AC3/AC7.

## Story

As a **Администратор интеграции с 1С**,
I want **чтобы портал читал вид цен контрагента из выгрузки и громко сообщал, если блок перестал приходить**,
so that **молчаливая поломка выгрузки после обновления модуля БУС была видна в тот же день, а не через месяцы неизменившихся ролей**.

## Acceptance Criteria

1. **AC1 (предохранитель внешней зависимости, часть A).** Контрольная выгрузка контрагентов, снятая **с продуктивной базы** после переноса патча БУС **второй** редакции, содержит:
   - хотя бы один узел `<Контрагент>` с блоком `<ЗначенияРеквизитов>` и непустым `ТипЦенId`;
   - хотя бы один узел с реквизитом `СоглашениеСтатус` = `НетСоглашения`.
   Обе ветки патча проверяются: иначе половина правки может быть накачена вхолостую. **Без выполнения этого AC стори не закрывается** — это единственный артефакт, подтверждающий закрытие внешней зависимости части A. Факт фиксируется числами (всего контрагентов / с `ТипЦенId` / со статусом `НетСоглашения`) в Dev Agent Record.

2. **AC2 (FR-40-01).** `CustomerDataParser._parse_customer_node` (`backend/apps/users/services/parser.py:79`) при наличии блока `<ЗначенияРеквизитов>` кладёт в `customer_data`:
   - `price_type_ids: list[str]` — GUID в нижнем регистре, без пробелов;
   - `price_type_meta: list[dict]` — по одному словарю на каждую четвёрку реквизитов с ключами `price_type_id`, `price_type_name`, `agreement_name`, `agreement_is_standard` (bool из `СоглашениеТиповое`).

3. **AC3 (FR-40-01).** Для узла контрагента без действующего соглашения: `customer_data["agreement_status"] == "НетСоглашения"`, `price_type_ids == []`. Слово-маркер **не попадает** в `price_type_ids` — `ТипЦенId` остаётся полем под GUID, статус живёт отдельным реквизитом.

4. **AC4 (FR-40-01).** Контрагент-маркетплейс, у которого один и тот же `ТипЦенId` приходит дважды (соглашения «Выкуп …» и «Комиссионное …» на виде цен РРЦ), даёт **один** элемент в `price_type_ids`. Дедупликация выполняется **в парсере**, до разрешения роли — иначе 40 контрагентов текущего снимка получат ложный `ambiguous` в стори 40.2. `price_type_meta` при этом сохраняет **обе** четвёрки: это диагностика, а не вход решения.

5. **AC5 (FR-40-01).** Узел контрагента **без** блока `<ЗначенияРеквизитов>` (старая выгрузка либо затёртый патч) разбирается без исключения: `price_type_ids == []`, `price_type_meta == []`, `agreement_status == ""`. Ключи присутствуют в `customer_data` **всегда**, независимо от наличия блока.

6. **AC6 (FR-40-01, регресс).** Разбор элементов `<Роль>` (`parser.py:100`, `_get_all_texts`) не изменён — отбор по значению «Покупатель» работает как прежде. Доказывается существующим тестом `test_role_extracted_for_every_real_contragent` и тестом `test_multiple_role_elements_are_all_collected`.

7. **AC7 (NFR-3940-01).** Контрольный снимок `backend/data/import_1c/contragents_pricetype/`, переснятый после второй редакции патча, разобранный целиком, удовлетворяет инвариантам:
   - ни у одного контрагента нет более одного **различного** `ТипЦенId`;
   - каждый контрагент несёт **либо** непустой `price_type_ids`, **либо** `agreement_status == "НетСоглашения"` — контрагентов без блока в выгрузке нет.
   Проверяются именно эти инварианты, а **не** абсолютное число контрагентов: снимок обновляемый, и зашитая константа правилась бы не глядя при каждом переснятии.

8. **AC8 (FR-40-10, детектор регресса).** Если за весь прогон импорта блок `<ЗначенияРеквизитов>` не встретился **ни разу** (при ненулевом числе разобранных контрагентов):
   - `ImportSession.report_details` несёт признак аномалии `attributes_block_anomaly: true` и счётчик `attributes_block_present`;
   - итоговый вывод команды `import_customers_from_1c` печатает предупреждение о вероятной поломке выгрузки (стиль `self.style.WARNING`, текст указывает на затёртый патч расширения БУС).

9. **AC9 (FR-40-10).** Если блок встретился хотя бы у одного контрагента — `attributes_block_anomaly` равен `false`, а `attributes_block_present` показывает фактическое число контрагентов с блоком.

10. **AC10 (FR-40-10).** Число контрагентов **без** блока попадает в отчёт отдельным счётчиком `attributes_block_missing` — после второй редакции блок обязан приходить у каждого, поэтому ненулевое значение есть признак частичного регресса или устаревшего снимка, даже когда общая аномалия не выставлена. Инвариант: `attributes_block_present + attributes_block_missing == total`.

11. **AC11 (NFR-3940-01, -02).** Тесты стори построены **только** на реальных XML из `backend/data/import_1c/` (`contragents/` и `contragents_pricetype/`); синтетические XML для проверки разбора выгрузки запрещены. Каждый тест несёт маркер `unit` либо `integration` (проставляется автоматически по каталогу) и вручную — `@pytest.mark.data_dependent`; при отсутствии датасета тест корректно `skip`-ается.

## Tasks / Subtasks

- [ ] **Task 0 (БЛОКИРУЮЩЕЕ, действие Alex + разработчик 1С): вторая редакция патча и контрольные выгрузки** (AC: 1, 3, 7)
  - [ ] 0.1: Проверить факт на текущем снимке: `grep -c СоглашениеСтатус backend/data/import_1c/contragents_pricetype/*.xml` — на `638d4fb1` даёт 0 во всех 10 файлах
  - [ ] 0.2: Выполнить `dev-task-bus-agreement-status.md` на `test_base` (откат модуля → правка `fragments/03_code.bsl` → повторное наложение патча → пообъектная загрузка)
  - [ ] 0.3: Переснять `backend/data/import_1c/contragents_pricetype/` с `test_base` **второй** редакцией, **удалив старый снимок целиком** (см. Dev Notes → «Куда класть снимки»). Каталог в `.gitignore` (строка 204) — коммитить не нужно
  - [ ] 0.4: Проверить на новом снимке обе ветки: есть контрагенты с непустым `ТипЦенId`, есть со статусом `НетСоглашения`, контрагентов **без** блока — ноль
  - [ ] 0.5: Передать патч второй редакции администратору 1С, получить контрольную выгрузку **с прода**, положить её в `backend/data/import_1c/contragents_pricetype_prod/`, снять на ней ту же тройку показателей → записать в Dev Agent Record (закрывает AC1)
  - [ ] 0.6: Если переснять или получить продовую выгрузку невозможно — остановиться и сообщить Alex. Синтетический XML под `СоглашениеСтатус` **не изготавливать**

- [ ] **Task 1: Парсер читает `<ЗначенияРеквизитов>`** (AC: 2, 3, 4, 5, 6)
  - [ ] 1.1: Добавить в `CustomerDataParser` приватный метод `_extract_attribute_values(customer_node)` → `tuple[list[str], list[dict], str]` (точный код — в Dev Notes). Разместить рядом с `_extract_contact_info` (`parser.py:145`), по образцу его структуры
  - [ ] 1.2: В `_parse_customer_node` вызвать метод и добавить три ключа в словарь `customer_data` (`parser.py:127-141`) — **после** `company_name`, чтобы diff был аддитивным
  - [ ] 1.3: НЕ трогать `role = ",".join(self._get_all_texts(customer_node, "Роль"))` (`parser.py:100`) и `_get_all_texts` (`parser.py:248`)
  - [ ] 1.4: НЕ менять `_validate_customer_data` — новые поля необязательные, контрагент без блока валиден

- [ ] **Task 2: Счётчики блока в процессоре** (AC: 8, 9, 10)
  - [ ] 2.1: В `CustomerDataProcessor.process_customers` (`processor.py:183`) добавить в `stats` (`processor.py:194-200`) ключи `attributes_block_present` и `attributes_block_missing` — целые, по умолчанию 0
  - [ ] 2.2: Считать их в цикле `for i, customer_data in enumerate(...)` (`processor.py:202`) **до** вызова `process_customer` и **независимо** от фильтра `is_buyer`: детектор измеряет здоровье выгрузки, а не бизнес-результат импорта. Признак наличия блока — `bool(customer_data.get("price_type_ids")) or bool(customer_data.get("agreement_status"))`
  - [ ] 2.3: Флаг аномалии в процессоре **не вычислять** — он определяется по всем файлам разом, это ответственность команды
  - [ ] 2.4: Обновить docstring `process_customers` (перечень возвращаемых ключей) — комментарии на русском

- [ ] **Task 3: Отчёт и предупреждение в команде** (AC: 8, 9, 10)
  - [ ] 3.1: В `import_customers_from_1c.Command.handle` добавить оба новых ключа в инициализацию `total_stats` (`import_customers_from_1c.py:116-122`). ⚠️ Без этого суммирование `for key in total_stats.keys()` (`:142-143`) молча их отбросит — см. Dev Notes → «Мина: суммирование по ключам»
  - [ ] 3.2: После цикла по файлам вычислить `anomaly = total_stats["total"] > 0 and total_stats["attributes_block_present"] == 0` и положить в `report_details` ключом `attributes_block_anomaly`
  - [ ] 3.3: Добавить три строки в итоговый вывод (`:177-192`): контрагентов с блоком, без блока, признак аномалии
  - [ ] 3.4: Печатать предупреждение `self.style.WARNING(...)` при `anomaly` — **в обоих режимах**, включая `--dry-run` (в dry-run итоговый блок не печатается, `:167-168`), иначе dry-run перед прогоном на проде не покажет поломку
  - [ ] 3.5: НЕ менять места создания/переиспользования `ImportSession` (`:89-108`) и обработку ошибок (`:194-211`)

- [ ] **Task 4: Unit-тесты парсера** (AC: 2, 4, 5, 6, 11)
  - [ ] 4.1: Расширить `backend/tests/unit/test_services/test_customer_parser.py` новым классом `TestCustomerParserPriceType`; путь к данным брать через фикстуру `onec_data_dir` из `backend/tests/conftest.py:419` — **не копировать** сломанный локальный путь из фикстуры `real_xml_file` (см. Dev Notes → «Мина: путь к данным»)
  - [ ] 4.2: Тест A (AC2): на `contragents_pricetype/*.xml` найти контрагента с непустым `price_type_ids` → GUID в нижнем регистре, `price_type_meta` содержит все четыре ключа, `agreement_is_standard is True`
  - [ ] 4.3: Тест B (AC4): найти контрагента, у которого в блоке `ТипЦенId` повторяется, → `len(price_type_ids) == len(set(price_type_ids)) == 1`, а `len(price_type_meta) == 2`. На снимке 2026-08-01 таких контрагентов 40 (вид цен РРЦ)
  - [ ] 4.4: Тест C (AC5): на старом снимке `contragents/*.xml` (блока нет ни у кого) — у каждого контрагента ключи присутствуют и пусты, исключений нет
  - [ ] 4.5: Тест D (AC3): контрагент со статусом → `agreement_status == "НетСоглашения"`, `price_type_ids == []`, и ни один элемент `price_type_ids` во всём снимке не равен `"нетсоглашения"`. **Требует снимка второй редакции (Task 0)**
  - [ ] 4.6: Маркеры: каталог `tests/unit/` даёт `unit` автоматически; добавить `@pytest.mark.data_dependent` вручную

- [ ] **Task 5: Тест инвариантов снимка и интеграционный тест детектора** (AC: 7, 8, 9, 10, 11)
  - [ ] 5.1: Создать `backend/tests/integration/test_customers_price_type_detector.py`
  - [ ] 5.2: Тест инвариантов снимка (AC7): разобрать все файлы `contragents_pricetype/`, проверить два инварианта из AC7. **Абсолютных чисел не зашивать** — снимок обновляемый. **Требует снимка второй редакции**
  - [ ] 5.3: Тест детектора «блок есть» (AC9, AC10): прогнать `call_command("import_customers_from_1c", data_dir=<tmp с contragents/ → симлинк/копия файлов contragents_pricetype>)` → `report_details["attributes_block_anomaly"] is False`, `attributes_block_present > 0`, `present + missing == total`. Команда ищет подкаталог **`contragents/`** — см. Dev Notes → «Мина: имя подкаталога»
  - [ ] 5.4: Тест детектора «блока нет ни у кого» (AC8): прогнать команду на старом снимке `contragents/` → `attributes_block_anomaly is True`, `attributes_block_present == 0`, в stdout есть предупреждение
  - [ ] 5.5: Маркеры: каталог `tests/integration/` даёт `integration` автоматически; добавить `@pytest.mark.data_dependent`; `pytest.mark.django_db` обязателен

- [ ] **Task 6: Прогон, регресс и pre-commit** (AC: 6, 11)
  - [ ] 6.1: `pytest -q backend/tests/unit/test_services/test_customer_parser.py backend/tests/integration/test_customers_price_type_detector.py` в тест-контейнере (команда — в Dev Notes)
  - [ ] 6.2: Регресс существующих тестов импорта контрагентов: `tests/unit/test_services/test_customer_processor.py`, `tests/integration/test_management_commands/test_import_customers.py`, `tests/integration/test_link_then_import_1c.py`
  - [ ] 6.3: `black` + `flake8` на изменённых файлах
  - [ ] 6.4: `npx gitnexus detect-changes --scope all` — убедиться, что затронуты только `_parse_customer_node`, новый `_extract_attribute_values`, `process_customers`, `Command.handle`

## Dev Notes

### ⚠️ Первое, что нужно знать: состояние снимков данных (замерено 04.08.2026 на `638d4fb1`)

| Каталог | Состояние | Вывод |
|---|---|---|
| `backend/data/import_1c/contragents/` | 7 файлов, снимок 11.04.2026, блока `<ЗначенияРеквизитов>` нет **ни у кого** | Идеальные данные для AC5 и AC8 (ветка «блока нет») |
| `backend/data/import_1c/contragents_pricetype/` | 10 файлов, снимок 01.08.2026, **первая** редакция патча | Ветка «блок с GUID» закрывается. Ветка `НетСоглашения` — **нет** |

Замеры по `contragents_pricetype/` (скрипт разбора — в Debug Log при исполнении):

| Показатель | Значение |
|---|---|
| Контрагентов всего | 4735 |
| С блоком `<ЗначенияРеквизитов>` | 485 |
| С `СоглашениеСтатус` / `НетСоглашения` | **0 / 0** |
| С повторяющимся `ТипЦенId` внутри блока | **40** |
| С более чем одним **различным** `ТипЦенId` | **0** |

Распределение `ТипЦенId` (контрагентов):

| GUID | Наименование | Контрагентов |
|---|---|---|
| `c05f0e2b-b3f2-11ea-81c3-00155d3cae02` | Опт 3 (50-150 тыс.руб в квартал) | 176 |
| `4c1962d2-f8ed-11eb-81f3-00155d3cae02` | Опт 4 (до 50 тыс.руб в квартал) | 123 |
| `a91bdb02-b3f2-11ea-81c3-00155d3cae02` | Опт 2 (150-300 тыс.руб в квартал) | 78 |
| `90d2c899-b3f2-11ea-81c3-00155d3cae02` | Опт 1 (300-600 тыс.руб в квартал) | 64 |
| `3d1482c4-bd77-11e4-afc8-20cf3073dde3` | РРЦ | 42 (из них 40 — с дублем GUID) |
| `28049309-b6be-11ec-a301-04421a23d8e8` | Детский мир Залоговая | 2 |

Последний GUID **записи `PriceType` на портале не имеет** — в стори 40.2 он даст `unknown_price_type`. Здесь, в 40.1, ничего с ним делать не нужно: парсер отдаёт GUID как есть, справочник не читает.

### Куда класть снимки и как они называются

Имена файлов задаёт 1С, а не разработчик: выгрузка БУС пишет пакеты шаблоном `contragents_<номер пакета>_<GUID пакета>.xml`, где GUID генерируется заново при каждой выгрузке. Имена нового снимка **не совпадут** со старыми — поэтому тесты обязаны искать файлы глобом `contragents*.xml` и **никогда** не зашивать имя.

| Что | Каталог | Кто читает |
|---|---|---|
| Снимок с `test_base`, вторая редакция | `backend/data/import_1c/contragents_pricetype/` | тесты AC2–AC5, AC7 |
| Контрольная выгрузка **с прода** (AC1) | `backend/data/import_1c/contragents_pricetype_prod/` | никто; артефакт приёмки, показатели переносятся в Dev Agent Record |
| Старый снимок без блока (11.04.2026) | `backend/data/import_1c/contragents/` — **не трогать** | тесты AC5 и AC8 (ветка «блока нет») |

- **Старый `contragents_pricetype/` перед копированием удалить целиком.** Смешение файлов двух редакций в одном каталоге завалит AC7 («контрагентов без блока в выгрузке нет») на старых файлах, и выглядеть это будет как неналоженный патч.
- Промежуточная точка при выгрузке с `test_base`: локальный обмен пишет в `C:\Users\1\DEV\FREESPORT\data\webdata\Обмен локальный\contragents\` (рядом с уже существующими `priceLists/` и `prices/`); оттуда файлы копируются в `contragents_pricetype/`.
- Разделение test/prod нужно только чтобы продовая выгрузка не попала в тестовый глоб. Оба каталога в `.gitignore` — коммит не требуется.

**Путь важен: данные лежат в `backend/data/import_1c/`, а не в `data/import_1c/`** (как написано в `epics.md` и в задании). Каталог `data/import_1c/` в корне репозитория существует, но **пуст**. `backend/data/import_1c/` целиком в `.gitignore` (строка 204) — снимки не версионируются. В Docker примонтирован как `/app/data/import_1c` (`docker/docker-compose.test.yml:72`).

### Blast radius (обязательный pre-flight выполнен)

```
npx gitnexus impact _parse_customer_node --direction upstream  → risk: LOW, impacted: 2
npx gitnexus impact process_customers    --direction upstream  → risk: LOW, impacted: 1
```

- `_parse_customer_node` ← `CustomerDataParser.parse` (`parser.py:64`) ← `Command.handle` (`import_customers_from_1c.py:133`)
- `process_customers` ← `Command.handle` (`import_customers_from_1c.py:139`)
- Затронутых процессов: 0, модулей: 1 (Services)

Изменение **аддитивное**: три новых ключа в возвращаемом словаре, два новых ключа в `stats`. Ни один существующий ключ не меняет смысла, ни одна сигнатура не меняется.

**Единственная точка входа в импорт контрагентов — эта команда.** Celery и вью вызывают её же:
`apps/integrations/tasks.py:170` и `apps/products/tasks.py:215` → `call_command("import_customers_from_1c", ...)`. Отдельных путей, минующих `process_customers`, нет — счётчики в процессоре покрывают все режимы запуска.

### Формат блока в реальной выгрузке

```xml
<Контрагент>
  <Ид>…</Ид>
  <Роль>Покупатель</Роль>
  …
  <Контакты/>
  <ЗначенияРеквизитов>
    <ЗначениеРеквизита>
      <Наименование>ТипЦенId</Наименование>
      <Значение>4c1962d2-f8ed-11eb-81f3-00155d3cae02</Значение>
    </ЗначениеРеквизита>
    <ЗначениеРеквизита>
      <Наименование>ТипЦенНаименование</Наименование>
      <Значение>Опт 4 (до 50 тыс.руб в квартал)</Значение>
    </ЗначениеРеквизита>
    <ЗначениеРеквизита>
      <Наименование>СоглашениеНаименование</Наименование>
      <Значение>Опт 4</Значение>
    </ЗначениеРеквизита>
    <ЗначениеРеквизита>
      <Наименование>СоглашениеТиповое</Наименование>
      <Значение>true</Значение>
    </ЗначениеРеквизита>
  </ЗначенияРеквизитов>
</Контрагент>
```

Вторая редакция добавляет для контрагента **без** соглашения единственную пару:

```xml
<ЗначенияРеквизитов>
  <ЗначениеРеквизита>
    <Наименование>СоглашениеСтатус</Наименование>
    <Значение>НетСоглашения</Значение>
  </ЗначениеРеквизита>
</ЗначенияРеквизитов>
```

**Блок — плоский список пар, а не список четвёрок.** Соглашений может быть несколько, и тогда четвёрки идут подряд одна за другой. Группировать по началу новой четвёрки — по появлению `ТипЦенId`.

### Точный код: `_extract_attribute_values`

Разместить в `CustomerDataParser` после `_extract_contact_info` (`parser.py:145-175`). Комментарии и docstring — на русском (NFR-3940-10):

```python
    # Наименования реквизитов в блоке <ЗначенияРеквизитов> выгрузки контрагентов.
    # Формирует патч расширения БУС (см. docs/integrations/1c/bus-extension-patch/).
    ATTR_PRICE_TYPE_ID = "ТипЦенId"
    ATTR_PRICE_TYPE_NAME = "ТипЦенНаименование"
    ATTR_AGREEMENT_NAME = "СоглашениеНаименование"
    ATTR_AGREEMENT_IS_STANDARD = "СоглашениеТиповое"
    ATTR_AGREEMENT_STATUS = "СоглашениеСтатус"

    # Значения, которые 1С отдаёт как истину в булевом реквизите.
    TRUE_VALUES = frozenset({"true", "истина", "1", "да"})

    def _extract_attribute_values(self, customer_node: ET.Element) -> tuple[list[str], list[dict[str, Any]], str]:
        """
        Разбирает блок <ЗначенияРеквизитов> узла <Контрагент>.

        Блок — плоский список пар Наименование/Значение. У контрагента может
        быть несколько соглашений, тогда четвёрки реквизитов идут подряд:
        новая четвёрка начинается с ТипЦенId.

        Returns:
            tuple: (price_type_ids, price_type_meta, agreement_status)
                price_type_ids — GUID в нижнем регистре, без пробелов, без
                    повторов, в порядке появления. Дедупликация обязательна:
                    у маркетплейсов два соглашения («Выкуп …» и
                    «Комиссионное …») висят на одном виде цен, и повтор GUID
                    не является конфликтом видов цен.
                price_type_meta — диагностика, по словарю на каждую четвёрку;
                    НЕ дедуплицируется, обе четвёрки маркетплейса видны.
                agreement_status — значение СоглашениеСтатус или "".
        """
        attributes_node = customer_node.find("cml:ЗначенияРеквизитов", self.COMMERCEML_NS)
        if attributes_node is None:
            attributes_node = customer_node.find("ЗначенияРеквизитов")

        if attributes_node is None:
            return [], [], ""

        price_type_ids: list[str] = []
        price_type_meta: list[dict[str, Any]] = []
        agreement_status = ""
        current: dict[str, Any] | None = None

        items = attributes_node.findall("cml:ЗначениеРеквизита", self.COMMERCEML_NS)
        if not items:
            items = attributes_node.findall("ЗначениеРеквизита")

        for item in items:
            name = self._get_text(item, "Наименование")
            value = self._get_text(item, "Значение")

            if name == self.ATTR_PRICE_TYPE_ID:
                if not value:
                    # Пустой GUID соглашения не описывает: вторая редакция
                    # патча отдаёт в этом случае СоглашениеСтатус.
                    current = None
                    continue
                guid = value.lower()
                if guid not in price_type_ids:
                    price_type_ids.append(guid)
                current = {
                    "price_type_id": guid,
                    "price_type_name": "",
                    "agreement_name": "",
                    "agreement_is_standard": False,
                }
                price_type_meta.append(current)
            elif name == self.ATTR_AGREEMENT_STATUS:
                agreement_status = value
            elif current is not None:
                if name == self.ATTR_PRICE_TYPE_NAME:
                    current["price_type_name"] = value
                elif name == self.ATTR_AGREEMENT_NAME:
                    current["agreement_name"] = value
                elif name == self.ATTR_AGREEMENT_IS_STANDARD:
                    current["agreement_is_standard"] = value.strip().lower() in self.TRUE_VALUES

        return price_type_ids, price_type_meta, agreement_status
```

Затем в `_parse_customer_node`, перед формированием словаря:

```python
        # Вид цен из соглашения об условиях продаж (патч расширения БУС).
        price_type_ids, price_type_meta, agreement_status = self._extract_attribute_values(customer_node)
```

и три ключа в `customer_data` (`parser.py:127-141`), после `"company_name": company_name,`:

```python
            "price_type_ids": price_type_ids,
            "price_type_meta": price_type_meta,
            "agreement_status": agreement_status,
```

**Чего не делать:**
- НЕ фильтровать `ТипЦенId` по форме GUID (регуляркой). Значение приходит из 1С как есть; фильтр по форме молча съест данные при малейшем изменении формата на стороне 1С. Защита от слова-маркера в поле GUID — это тест AC3 на реальном снимке, а не фильтр в коде.
- НЕ приводить `agreement_status` к нижнему регистру и не переводить в enum. Здесь он хранится как есть; сравнение делает `resolve_role_from_price_types` в стори 40.2.
- НЕ дедуплицировать `price_type_meta`.
- НЕ трогать `_get_all_texts` и разбор `<Роль>` — AC6.

### Точный код: счётчики в `process_customers`

`processor.py:194-200`, словарь `stats`:

```python
        stats = {
            "total": len(customers_data),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            # Детектор регресса выгрузки: блок <ЗначенияРеквизитов> формирует
            # патч тиражного расширения БУС и теряется при его обновлении.
            # Отказ тихий — файлы приходят, блока в них нет.
            "attributes_block_present": 0,
            "attributes_block_missing": 0,
        }
```

и в начале тела цикла (`processor.py:202`), **до** `process_customer`:

```python
            if customer_data.get("price_type_ids") or customer_data.get("agreement_status"):
                stats["attributes_block_present"] += 1
            else:
                stats["attributes_block_missing"] += 1
```

Счёт идёт по **всем** разобранным контрагентам, включая не-покупателей: детектор измеряет здоровье выгрузки, а не результат импорта. Отсюда инвариант `present + missing == total` (AC10).

### Точный код: команда

`import_customers_from_1c.py:116-122` — инициализация:

```python
            total_stats = {
                "total": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
                "attributes_block_present": 0,
                "attributes_block_missing": 0,
            }
```

После цикла по файлам, до записи `report_details` (`:173`):

```python
            # Блок <ЗначенияРеквизитов> приходит у каждого контрагента начиная
            # со второй редакции патча БУС. Ноль за весь прогон означает не
            # «ни у кого нет соглашения», а затёртую правку расширения.
            attributes_anomaly = total_stats["total"] > 0 and total_stats["attributes_block_present"] == 0
            total_stats["attributes_block_anomaly"] = attributes_anomaly
```

Предупреждение печатать **до** ветвления на dry-run (`:167`), чтобы оно выводилось в обоих режимах:

```python
            if attributes_anomaly:
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️  Блок <ЗначенияРеквизитов> не встретился ни у одного из "
                        f"{total_stats['total']} контрагентов. Вероятная причина — правка "
                        "расширения ОбменСБитриксУправлениеСайтомУТ затёрта обновлением модуля БУС. "
                        "См. docs/integrations/1c/bus-extension-patch/README.md"
                    )
                )
```

Три строки в итоговый блок (`:184-189`):

```python
                        f"  Контрагентов с видом цен из 1С: {total_stats['attributes_block_present']}\n"
                        f"  Контрагентов без блока реквизитов: {total_stats['attributes_block_missing']}\n"
                        f"  Аномалия выгрузки: {'ДА' if attributes_anomaly else 'нет'}\n"
```

### Мина: суммирование по ключам

`import_customers_from_1c.py:142-143`:

```python
                        for key in total_stats.keys():
                            total_stats[key] += result.get(key, 0)
```

Суммируются **только те ключи, что уже объявлены** в `total_stats`. Если добавить счётчики в `stats` процессора, но забыть про инициализацию в команде, они молча исчезнут, а тесты AC8-AC10 покажут нули — и выглядеть это будет как аномалия, которой нет. Это же место объясняет, почему `attributes_block_anomaly` (bool) кладётся в `total_stats` **после** цикла: `bool += int` в этом цикле сложился бы в число.

### Мина: путь к данным в тестах

Фикстура `real_xml_file` в существующем `test_customer_parser.py:26-47` считает локальный путь как `Path(__file__).parent × 5` → корень репозитория `/data/import_1c/contragents/`. Этот каталог **пуст**, поэтому локально все тесты класса молча `skip`-аются, а зелёными они бывают только в Docker (где `/app/data` смонтирован). **Не копировать этот паттерн.**

Правильный источник пути — фикстура `onec_data_dir` из `backend/tests/conftest.py:419`: она берёт `Path(settings.BASE_DIR) / "data" / "import_1c"`, где `BASE_DIR` — каталог `backend/`. Работает и локально, и в контейнере. Альтернативный рабочий образец — `_import_1c_dir()` в `backend/tests/integration/test_import_opt4_prices.py:36`.

### Мина: имя подкаталога в команде

`Command.handle` жёстко требует подкаталог **`contragents/`** внутри `--data-dir` (`import_customers_from_1c.py:68-73`) и глоб `contragents*.xml`. Каталог `contragents_pricetype/` командой напрямую не читается. Для интеграционного теста (Task 5.3) собрать временную структуру:

```python
    data_dir = tmp_path / "import_1c"
    (data_dir / "contragents").mkdir(parents=True)
    for src in sorted((Path(onec_data_dir) / "contragents_pricetype").glob("contragents*.xml")):
        shutil.copy(src, data_dir / "contragents" / src.name)
```

⚠️ Прогон команды на всех 10 файлах — это 4735 контрагентов и создание такого же числа `User` + `CustomerSyncLog`. Для теста детектора **достаточно одного файла** — счётчики линейны, а инвариант `present + missing == total` проверяется на любом объёме. Копировать один файл, а не весь снимок.

### Что уже есть и переиспользуется (не изобретать)

| Нужное | Где уже есть |
|---|---|
| Безопасное чтение текста узла с namespace и без | `CustomerDataParser._get_text` (`parser.py:225`) |
| Чтение повторяющихся элементов | `_get_all_texts` (`parser.py:248`) — для `<Роль>`, здесь не нужен |
| Образец разбора вложенного блока пар «Тип/Значение» | `_extract_contact_info` (`parser.py:145`) — та же форма, что `<ЗначенияРеквизитов>` |
| Путь к реальным выгрузкам в тестах | фикстура `onec_data_dir` (`backend/tests/conftest.py:419`) |
| Образец теста на реальных XML со `skip` | `backend/tests/integration/test_import_opt4_prices.py` (стори 39.2) |
| Образец интеграционного теста команды | `backend/tests/integration/test_management_commands/test_import_customers.py` |

### Границы стори (что делают следующие стори — здесь НЕ делать)

- **40.2** — `resolve_role_from_price_types`, `PriceType.user_role`, data-миграция, админка справочника. Парсер справочник `PriceType` **не читает** и ролей не разрешает.
- **40.3** — поле `User.onec_price_type_id`, запись вида цен на пользователя, отображение в админке. Миграций `users` здесь нет.
- **40.4** — применение роли, `AuditLog`, счётчики `roles_*`. Роль в этой стори не меняется **никогда**.
- **40.5** — перенос вида цен при привязке.

Стори 40.1 и 40.2 независимы и могут идти параллельно — общих файлов у них нет.

### Тестирование: как запускать

`make` на машине недоступен, а таргеты `test-*` ищут несуществующий `docker/.env`. Рабочий эквивалент:

```bash
cd /c/Users/1/DEV/FREESPORT/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -q tests/unit/test_services/test_customer_parser.py tests/integration/test_customers_price_type_detector.py
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down
```

Линтеры — в dev-контейнере из корня репозитория:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend black apps/users/services/parser.py apps/users/services/processor.py apps/users/management/commands/import_customers_from_1c.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend flake8 apps/users/
```

Маркеры `unit`/`integration` проставляются **автоматически по каталогу** теста (`backend/conftest.py:88`); `@pytest.mark.data_dependent` ставится вручную. Ориентир по длительности: unit ≈ 8 мин, integration ≈ 27 мин на полном наборе — точечный прогон быстрее.

### Project Structure Notes

Изменяемые файлы (все — UPDATE, новых модулей приложения нет):

| Файл | Что |
|---|---|
| `backend/apps/users/services/parser.py` | Новый метод `_extract_attribute_values` + 5 констант + 3 ключа в `customer_data` |
| `backend/apps/users/services/processor.py` | 2 ключа в `stats`, счёт в цикле, docstring |
| `backend/apps/users/management/commands/import_customers_from_1c.py` | 2 ключа в `total_stats`, флаг аномалии, предупреждение, 3 строки отчёта |
| `backend/tests/unit/test_services/test_customer_parser.py` | Новый класс тестов |
| `backend/tests/integration/test_customers_price_type_detector.py` | **NEW** |

Миграций нет. Изменений API-контракта нет: `openapi.yaml` и типы фронта не трогаются (NFR-3940-07 к эпику 40 неприменим). Frontend не затрагивается.

### API-контракт и внешние зависимости

Новых библиотек не требуется: разбор XML — штатный `xml.etree.ElementTree` (стандартная библиотека, уже используется в `parser.py:8`). `lxml`, `xmltodict` и подобные **не подключать** — весь импорт 1С в проекте построен на `ElementTree`, и смена парсера вышла бы далеко за рамки стори.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story 40.1` — AC в BDD-форме, FR-40-01, FR-40-10]
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic 40`] — порядок стори, внешняя блокирующая зависимость, отложенный эффект (`roles_updated = 0` в день выката)
- [Source: `_bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md` §2.3, §2.4, §6, §8 C1, §11] — виды цен и GUID, устройство выгрузки, формат блока, риск затирания патча
- [Source: `_bmad-output/implementation-artifacts/tasks/dev-task-bus-agreement-status.md` §2, §4, §8] — вторая редакция, `СоглашениеСтатус`, запрет писать маркер в `ТипЦенId`
- [Source: `docs/integrations/1c/bus-extension-patch/README.md`] — патч расширения, контрольная выгрузка, процедура применения
- [Source: `project-context.md` §4] — реальные XML в тестах, автоматическая разметка маркеров, покрытие
- [Source: `backend/docs/testing-standards.md`] — стандарты тестирования, раздел «Маркеры pytest»
- [Source: `_bmad-output/implementation-artifacts/Story/39-2-import-opt4-prices-from-1c.md`] — образец стори импорта на реальных выгрузках, паттерн Task 0 с блокирующим предусловием

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
