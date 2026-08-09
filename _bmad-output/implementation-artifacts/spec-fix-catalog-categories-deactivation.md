---
title: 'Каталог: частичная выгрузка 1С гасит всё дерево категорий'
type: 'bugfix'
created: '2026-08-09'
status: 'in-review'
review_loop_iteration: 1
baseline_commit: '6a7e4f506bdd9697e03c8ffce4aac4466c030bae'
context:
  - '{project-root}/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На проде `/catalog` показывает одну категорию — «Единоборства»: в БД активны 5 из 148. `VariantImportProcessor.deactivate_obsolete_categories()` после каждого импорта гасит **все** категории, не встреченные в текущей выгрузке 1С, поэтому любая частичная выгрузка схлопывает витрину.

**Approach:** Два независимых барьера в этой функции: гасить только детей родителей, реально раскрытых в XML, и **для каждого раскрытого родителя отдельно** отменять деактивацию его детей с `logger.error`, если она затронет >30 % его активных детей. Плюс management-команда восстановления и её прогон на проде.

## Boundaries & Constraints

**Always:**
- «Раскрытый» родитель = в текущем XML под ним перечислен хотя бы один прошедший allowed-фильтр ребёнок.
- Предохранитель срабатывает независимо от первого барьера и считается **по каждому раскрытому родителю отдельно**: блокировка детей одного родителя не мешает чистке под другими.
- Порог не применяется к родителям, у которых меньше 4 активных детей: иначе штатное удаление 1 из 3 (33 %) блокировалось бы навсегда, а лог засорялся бы ошибками на каждом импорте.
- Команда восстановления: dry-run по умолчанию, запись только под `--execute`.
- Восстановление активирует потомков якоря `ROOT_CATEGORY_NAME`, **а также сам якорь, если он неактивен** — иначе `CategoryTreeViewSet` отдаст пустое дерево при формально успешном прогоне. Пропускаются placeholder-имена (`FULL_PLACEHOLDER_CATEGORY_RE_PATTERN`), `slug in ('uncategorized','onec-unresolved-category')` и `name='Без категории'` — тот же набор исключений, что в `CategoryTreeViewSet.get_queryset()`.
- Комментарии и docstrings — на русском.

**Ask First:**
- Прогон `--execute` на проде: сперва показать dry-run, дождаться подтверждения.
- Изменение порога 30 %, минимума в 4 ребёнка или отказ от одного из барьеров.

**Never:**
- Не трогать фронтенд (`(blue)/catalog/page.tsx`, `categoriesService`) — дефекта там нет.
- Не менять `CategoryTreeViewSet` и его фильтр `is_active=True`.
- Не менять логику фильтрации по якорю в шагах 1-2 `process_categories` — только собрать дополнительное множество.
- Не править `is_active` на проде прямым SQL в обход команды.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Полная выгрузка | Всё дерево в XML; в БД есть категория, удалённая в 1С | Удалённая гаснет, прочие активны | N/A |
| Частичная ветка | СПОРТ без вложенных `<Группы>`; Единоборства → Защита → Шлема | Дети СПОРТа не тронуты; внутри Единоборств гаснут только не пришедшие | N/A |
| Ветка выгружена целиком | СПОРТ с 1 ребёнком в XML (в БД 12 детей); под Единоборствами все 30 детей пришли | Дети СПОРТа не тронуты (11/12 = 92 %), `logger.error` по СПОРТу; под Единоборствами чистка проходит штатно | Предохранитель по СПОРТу |
| Малый родитель | Раскрыт родитель с 3 активными детьми, 1 удалён в 1С | Ребёнок гаснет, `logger.error` нет | Порог не применяется (<4 детей) |
| Категорий нет | `_valid_category_onec_ids` пуст | Ранний `return` | N/A |
| Нет раскрытых родителей | Плоский список групп без вложенности | Ранний `return` | N/A |
| Восстановление dry-run | Активны 5 из 148 | Список к активации + счётчик, БД не тронута | N/A |
| Восстановление, якорь погашен | `СПОРТ.is_active=False` | Якорь и потомки активированы, дерево видимо | N/A |
| Восстановление повторно | Дерево уже восстановлено | 0 изменений, успешный выход | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/products/services/variant_import.py` — `__init__` (кэши 296-311), `process_categories` (1577-1830: фильтрация по якорю 1608-1715 с `root_ids`/`anchor_id`, ШАГ 1 1717-1785, ШАГ 2 1787-1822 с guard `parent_id in root_ids and parent_id != anchor_id`), `deactivate_obsolete_categories` (1832-1845, целевой дефект), `log_progress` (2040-2065: пишет в `ImportSession.report`), `finalize_session` (2067-2076: зовёт деактивацию **до** сохранения `self.stats` в `report_details`, глушит исключения).
- `backend/apps/products/management/commands/import_products_from_1c.py` — `_import_categories` (329-349): один процессор на сессию, `process_categories` вызывается **по каждому** `groups*.xml`, поэтому множества накапливаются между файлами.
- `backend/apps/products/views.py` — `CategoryTreeViewSet.get_queryset()` (335-372): эталон исключений; якорь берётся с `is_active=True` (343), поэтому погашенный якорь = пустое дерево. `CategoryViewSet.get_queryset()` (~286): плоский список фильтрует только `is_active`, без исключения технических имён.
- `backend/apps/products/category_utils.py` — `FULL_PLACEHOLDER_CATEGORY_RE_PATTERN`, `REPAIR_ANCHOR_ONEC_ID`.
- `backend/apps/products/management/commands/fix_category_tree_public_roots.py` — образец repair-команды (`--execute`, `--root-name`, `transaction.atomic`, `SUMMARY`); реактивирует якорь (94-96), но падает `CommandError` при дублях якоря (39-43).
- `backend/apps/products/services/parser.py` — `parse_groups_xml` (492-538): `parent_id` проставляется **только** по вложенности `<Группы>`.
- `backend/apps/products/tests/unit/test_variant_import_migrated.py` — фикстуры `import_session`/`processor`, `get_unique_suffix()`, `pytestmark = [django_db, unit]`.
- `backend/apps/products/tests/unit/test_fix_category_tree_public_roots.py` — образец теста команды: `call_command(..., stdout=io.StringIO())`, `CategoryFactory`.
- `_bmad-output/implementation-artifacts/deferred-work.md` — отложенные находки ревью (в этой стори не чинятся).

## Tasks & Acceptance

**Execution:**
- [x] `variant_import.py` — константы модуля `MAX_CATEGORY_DEACTIVATION_RATIO = 0.3` и `MIN_CHILDREN_FOR_DEACTIVATION_RATIO = 4` рядом с `logger`; в `__init__` — `self._expanded_parent_onec_ids: set[str] = set()` рядом с `_valid_category_onec_ids`.
- [x] `variant_import.py` — в `process_categories` отдельным циклом перед ШАГ 1 наполнить множество `parent_id` записей, чей `id` прошёл allowed-фильтр, **повторив guard ШАГ 2**: пропускать `pid`, если `filtering_active and pid in root_ids and pid != anchor_id` (иначе чужой корень попадёт в зону деактивации). Логику фильтрации не трогать.
- [x] `variant_import.py` — переписать `deactivate_obsolete_categories` по схеме из Design Notes: ранний `return` при пустом `_valid_category_onec_ids` **или** `_expanded_parent_onec_ids`; **одним** запросом получить `(pk, onec_id, parent__onec_id)` активных детей раскрытых родителей; сгруппировать по родителю; для каждого применить порог с минимумом в 4 ребёнка; всё чтение и запись — внутри `transaction.atomic()`.
- [x] `variant_import.py` — наблюдаемость: при срабатывании предохранителя, помимо `logger.error`, писать `self.stats["categories_deactivation_skipped"]` (число незаглушенных кандидатов) и звать `self.log_progress(...)`, чтобы факт отмены попал в `ImportSession.report` — иначе при фоновом Celery-импорте оператор его не увидит.
- [x] `backend/apps/products/management/commands/reactivate_catalog_categories.py` — новая команда: якорь по `ROOT_CATEGORY_NAME` (`--root-name` override; пустое/`None` имя → `CommandError` про конфигурацию, а не про «категория не найдена»); при нескольких якорях — `WARNING` и обработка всех (union-семантика витрины); обход потомков **итеративный, с множеством посещённых pk** (self-FK допускает циклы, `RecursionError` недопустим); активируются неактивные потомки кроме технических **и кроме тех, у кого в цепочке предков есть исключённая категория** (иначе получим активную сироту под скрытой ветвью, видимую в плоском `/api/v1/categories/`); неактивный якорь активируется вместе с потомками; dry-run по умолчанию, запись под `--execute` в `transaction.atomic`; финальный `SUMMARY`.
- [x] `backend/apps/products/tests/unit/test_category_deactivation.py` — новый файл: все строки I/O-матрицы по деактивации, плюс изоляция родителей (один заблокирован — под другим чистка прошла), граница ровно 30 % (проходит) и 30 %+1 (блокируется), накопление множеств между `groups*.xml`, попадание отмены в `stats`/`report`. **Минимум один тест в anchored-режиме** (`ROOT_CATEGORY_NAME='СПОРТ'`, `filtering_active=True`) — это единственный режим, который реально работает на проде. Ранние `return` проверять счётчиком записей в БД, а не только «категория осталась активной»; аргументы `logger.error` сверять позиционно.
- [x] `backend/apps/products/tests/unit/test_reactivate_catalog_categories.py` — новый файл: dry-run не пишет; `--execute` активирует витрину и не трогает placeholder/`Без категории`/технические slug; неактивный якорь активируется; сирота под технической ветвью не активируется; несколько якорей → union + `WARNING`; цикл в дереве не роняет команду; повторный запуск идемпотентен; отсутствие якоря → `CommandError`. Slug и имена — через `get_unique_suffix()`, хардкод запрещён (`backend/CLAUDE.md`, `docs/testing-standards.md` разд. 8.5).
- [ ] Прод: dry-run → подтверждение пользователя → `--execute` → проверка `GET https://optisport.ru/api/v1/categories-tree/`.

**Acceptance Criteria:**
- Given импорт с частичной выгрузкой, when он завершается со статусом `completed`, then категории, чей родитель не раскрыт в выгрузке, сохраняют `is_active=True`.
- Given под раскрытым родителем с ≥4 активными детьми деактивация затронет >30 % из них, when вызывается `deactivate_obsolete_categories`, then дети именно этого родителя не меняются, в лог уходит `logger.error` с onec_id родителя, числом кандидатов и числом детей, а под остальными родителями чистка выполняется.
- Given отмена сработала хотя бы по одному родителю, when сессия импорта финализируется, then факт отмены виден в `ImportSession.report` и в `report_details`, а не только в файловом логе.
- Given прод после `--execute`, when клиент запрашивает `/api/v1/categories-tree/`, then возвращается 12 корневых категорий витрины.
- Given восстановленный прод, when проходит очередной штатный импорт 1С, then число активных **корневых категорий витрины** (прямых детей якоря) не уменьшается. Общее число активных категорий уменьшиться может — этого требует строка «Полная выгрузка» I/O-матрицы.

## Spec Change Log

- **2026-08-09, planning:** frozen-intent не определял знаменатель порога 30 %. Прогон реального сценария прода (`СПОРТ → Единоборства → Защита → Шлема`, 148 категорий) показал: при знаменателе «все активные с `onec_id`» барьер 1 оставляет ~22 кандидата, 22/148 = 15 % < 30 % — предохранитель не срабатывает, 11 корней витрины гаснут, инцидент повторяется, а строка 3 I/O-матрицы становится ложной. Alex выбрал знаменатель **«зона кандидатов»** (активные дети раскрытых родителей): 22/25 = 88 % — отмена срабатывает. Frozen-блок не менялся, уточнение зафиксировано в Design Notes и AC.

- **2026-08-09, review loop 1 (intent_gap):** Blind Hunter и Edge Case Hunter независимо показали, что «зона кандидатов» суммируется по всем раскрытым родителям и разваливается на самой типичной форме частичной выгрузки — **одна ветка целиком**: раскрыты СПОРТ (12 детей, пришёл 1) и Единоборства (30 детей, пришли все) → зона 42, кандидатов 11, 11/42 = 26 % < 30 %, предохранитель молчит, 11 корней витрины гаснут, инцидент воспроизводится. Тест итерации 0 использовал плоскую конструкцию (11/12 = 92 %) и этот режим отказа обходил. Alex перезаключил frozen-блок: порог считается **по каждому родителю отдельно** и **не применяется при <4 активных детях** (иначе штатное удаление 1 из 3 = 33 % блокировалось бы навсегда с error в логе на каждый импорт). Вторым решением: команда восстановления активирует и сам якорь — иначе при погашенном СПОРТе она печатает `reactivated=147` и выходит успешно, а витрина остаётся пустой (`CategoryTreeViewSet` фильтрует якорь по `is_active=True`), то есть AC про 12 корней не выполняется.

  **KEEP (сохранить при повторной генерации):** цикл сбора раскрытых родителей перед ШАГ 1 и накопление множества между файлами `groups*.xml`; ранние `return` при пустых множествах; обновление через `QuerySet.update()` по явному списку pk (сохраняет неизменным `auto_now`-поле `updated_at`); `--root-name`, `SUMMARY` и union-обработка нескольких якорей в команде; сопоставление тестов строкам I/O-матрицы; фикстура-настройка `ROOT_CATEGORY_NAME` через `settings`, а не `@override_settings` на классе (Django запрещает декорировать классы вне `SimpleTestCase`); проверка `logger.error` через `patch`, а не `caplog` (логгер `import_products` объявлен с `propagate: False`).

- **2026-08-09, review loop 1 → патчи без лупбэка.** Повторное адверсариальное ревью и ревью краевых случаев не нашли дефектов, требующих пересборки кода. Применены точечные патчи: (1) сбор «раскрытых» родителей перенесён **после** ШАГ 1 и завязан на `category_map` — раньше битая строка XML (например, без `name`) раскрывала родителя, но сама не попадала в валидные, то есть открывала зону деактивации и одновременно становилась кандидатом на гашение; (2) множество корней копится в `self._root_category_onec_ids` между файлами — корень может прийти в одном `groups*.xml`, а его дети в другом; (3) `.exclude(onec_id="")` в зоне кандидатов — пустой `onec_id` был вечным кандидатом; (4) сравнение `len(doomed) > len(kids) * RATIO` вместо деления — граница «ровно 30 %» больше не зависит от округления double; (5) `categories_deactivation_skipped` инициализируется в `__init__` наравне с остальными счётчиками, чтобы отличать «предохранитель не сработал» от «код не задеплоен»; (6) в `logger.error`/`logger.warning` добавлено имя родителя — по одному GUID оператор ничего не найдёт; (7) новый `logger.warning`, когда малая ветка (<4 детей) теряет большинство — порог там не применяется, но молча терять 2 из 3 недопустимо; (8) в команде — `deque.popleft()` вместо `pop()` (комментарий обещал обход в ширину, код делал в глубину), `re.fullmatch` вместо `match` (Postgres-оператор `~` не считает совпадением имя с висящим `\n`, а `re.match` с `$` — считает), защита от `KeyError` при удалении якоря между двумя запросами. Тесты: добавлены покрытие guard чужого корня (задача спеки, ранее не покрытая ни одним тестом — её удаление не роняло набор), граница ровно 4 ребёнка и предупреждение о потере большинства в малой ветке; проверка идемпотентности сужена с всей таблицы до созданных тестом категорий; хелперы разбора лога защищены от `IndexError`. AC про «число активных категорий не уменьшается» переформулирован: в абсолютной форме он был невыполним и противоречил строке «Полная выгрузка» I/O-матрицы. Итог: 23 новых теста + 64 регрессионных зелёные, `black`/`flake8` чистые.

## Design Notes

Сбор «раскрытости» — отдельный цикл перед ШАГ 1, с тем же guard по чужим корням, что в ШАГ 2:

```python
for cat in categories_data:
    pid, cid = cat.get("parent_id"), cat.get("id")
    if not pid or not cid:
        continue
    if filtering_active and cid not in self._allowed_category_ids:
        continue
    if filtering_active and pid in root_ids and pid != anchor_id:
        continue
    self._expanded_parent_onec_ids.add(pid)
```

Предохранитель — по каждому родителю, одним запросом без N+1:

```python
rows = scope_qs.values_list("pk", "onec_id", "parent__onec_id")
by_parent: dict[str, list[tuple[int, str]]] = defaultdict(list)
for pk, onec_id, parent_onec_id in rows:
    by_parent[parent_onec_id].append((pk, onec_id))

for parent_onec_id, kids in by_parent.items():
    doomed = [pk for pk, oid in kids if oid not in self._valid_category_onec_ids]
    if doomed and len(kids) >= MIN_CHILDREN_FOR_DEACTIVATION_RATIO \
            and len(doomed) / len(kids) > MAX_CATEGORY_DEACTIVATION_RATIO:
        logger.error(...)  # onec_id родителя, len(doomed), len(kids)
        continue
    to_deactivate.extend(doomed)
```

`parent__onec_id__in` — join, поэтому считаем и обновляем по явным спискам pk, а не `qs.update()` по join-фильтру. `QuerySet.update()` не трогает `auto_now`-поле `updated_at` (из-за этого инцидент не удалось датировать по БД) — поведение сохраняем намеренно. `transaction.atomic()` вокруг чтения и записи достаточно; `select_for_update()` не берём — с join-фильтром он лочит и родительские строки, а импорт и так однопоточный.

**Осознанный компромисс:** корневые категории (`parent IS NULL`) выпадают из зоны деактивации, хотя старый код их гасил. Это прямое следствие барьера 1. На витрину не влияет (`CategoryTreeViewSet` отдаёт только детей якоря), устаревший корень может всплыть лишь в плоском `/api/v1/categories/`. Записано в `deferred-work.md`, в этой стори не чинится.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest apps/products/tests/unit/test_category_deactivation.py apps/products/tests/unit/test_reactivate_catalog_categories.py -v` — expected: зелёные.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest apps/products/tests/unit/test_variant_import_migrated.py apps/products/tests/test_visible_categories.py apps/products/tests/unit/test_fix_category_tree_public_roots.py` — expected: без регрессий (55 passed на baseline).
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend sh -c "black --check <изменённые файлы>; flake8 apps/products"` — expected: exit 0. Пять предсуществующих black-замечаний по `apps/products` целиком относятся к файлам вне diff — не трогать.

**Manual checks:**
- `curl -s https://optisport.ru/api/v1/categories-tree/` — ожидается 12 корней после `--execute` (сейчас 1).

## Suggested Review Order

**Барьер 1 — граница зоны деактивации**

- Точка входа: два барьера целиком, читать первым — здесь весь замысел фикса
  [`variant_import.py:1882`](../../backend/apps/products/services/variant_import.py#L1882)

- Сбор «раскрытых» родителей: после ШАГ 1 и только по реально записанным детям
  [`variant_import.py:1813`](../../backend/apps/products/services/variant_import.py#L1813)

- Накопление корней между файлами выгрузки — питает guard чужого корня выше
  [`variant_import.py:333`](../../backend/apps/products/services/variant_import.py#L333)

**Барьер 2 — предохранитель по каждому родителю**

- Порог без деления: граница «ровно 30 %» не зависит от округления double
  [`variant_import.py:1938`](../../backend/apps/products/services/variant_import.py#L1938)

- Константы порога и минимума ветки с обоснованием каждой
  [`variant_import.py:39`](../../backend/apps/products/services/variant_import.py#L39)

- Наблюдаемость: отмена уходит в ImportSession, а не только в файловый лог
  [`variant_import.py:1983`](../../backend/apps/products/services/variant_import.py#L1983)

**Команда восстановления**

- Одна выборка дерева, обход в ширину с visited: self-FK допускает циклы
  [`reactivate_catalog_categories.py:99`](../../backend/apps/products/management/commands/reactivate_catalog_categories.py#L99)

- Защита от исчезновения якоря между двумя запросами — внятная ошибка вместо KeyError
  [`reactivate_catalog_categories.py:83`](../../backend/apps/products/management/commands/reactivate_catalog_categories.py#L83)

- Единственная точка записи: только под --execute и в транзакции
  [`reactivate_catalog_categories.py:131`](../../backend/apps/products/management/commands/reactivate_catalog_categories.py#L131)

- fullmatch, а не match: иначе расхождение с Postgres-регуляркой витрины
  [`reactivate_catalog_categories.py:142`](../../backend/apps/products/management/commands/reactivate_catalog_categories.py#L142)

**Тесты**

- Сценарий прода в anchored-режиме — тот самый режим отказа, что пропустила итерация 0
  [`test_category_deactivation.py:177`](../../backend/apps/products/tests/unit/test_category_deactivation.py#L177)

- Guard чужого корня: без этого теста его удаление не роняло набор
  [`test_category_deactivation.py:375`](../../backend/apps/products/tests/unit/test_category_deactivation.py#L375)

- Граница ровно 4 ребёнка: ловит подмену `>=` на `>`
  [`test_category_deactivation.py:409`](../../backend/apps/products/tests/unit/test_category_deactivation.py#L409)

- Потеря большинства в малой ветке фиксируется, хотя порог не применяется
  [`test_category_deactivation.py:431`](../../backend/apps/products/tests/unit/test_category_deactivation.py#L431)

- Погашенный якорь активируется вместе с потомками — иначе витрина остаётся пустой
  [`test_reactivate_catalog_categories.py:79`](../../backend/apps/products/tests/unit/test_reactivate_catalog_categories.py#L79)
