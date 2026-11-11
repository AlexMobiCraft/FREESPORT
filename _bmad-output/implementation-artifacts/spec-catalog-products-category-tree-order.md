---
title: 'Каталог: товары по умолчанию идут в порядке дерева категорий'
type: 'feature'
created: '2026-11-11'
status: 'done'
baseline_commit: '85d10f644823b07ace365f2fa94916fd7537702f'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На `/catalog` карточки по умолчанию идут по названию (`ordering=name`), а владелец хочет видеть их в том же порядке, что и категории в сайдбаре: Единоборства → Бинты, затем Защита корпуса, Защита ног, Капы, Специальная защита шлема, затем Обувь для бокса, борьбы, тхэквондо и далее по дереву.

**Approach:** Новый режим сортировки `ordering=category_tree` в API товаров: позиция категории товара при обходе дерева в глубину, затем `name`, затем `id`. Фронтенд каталога делает его умолчанием и показывает в селекте как «По категориям».

## Boundaries & Constraints

**Always:**
- Порядок братьев — как в сайдбаре: `sort_order > 0` по возрастанию, затем `sort_order = 0` по `name`, `slug=uncategorized` последней. Правило действует на каждом уровне.
- Обход в глубину: родитель раньше детей; товары, привязанные прямо к родителю, стоят перед товарами его подкатегорий.
- Корни обхода — дети активного якоря `settings.ROOT_CATEGORY_NAME`; при нескольких якорях их дети сливаются в один список братьев и ранжируются вместе, как в сайдбаре.
- Обход не заходит в категории, которые сайдбар исключает на любом уровне (`uncategorized`, `onec-unresolved-category`, «Без категории», имена по `FULL_PLACEHOLDER_CATEGORY_RE_PATTERN`), и в их поддеревья. Их товары и товары вне дерева якоря идут после всех, тоже по `name`, `id`.
- Внутри категории — `name`, затем `id`: страницы пагинации не пересекаются и не теряют товары.
- При фильтре по категории (`category_id`, slug фронт переводит в него же) порядок — это порядок её поддерева; отдельной логики не нужно, глобальная позиция его сохраняет.
- С поиском режим работает так же, как сейчас любая сортировка: `ordering` перекрывает ранжирование поиска (существующее поведение `OrderingFilter`). Фронт всегда шлёт `ordering`, поэтому выдача поиска на `/catalog` станет «по дереву» вместо «по названию» — владелец подтвердил 11.11.2026.
- Остальные значения `ordering` и умолчание API (`-created_at`) не меняются.

**Never:** менять модель `Category`/`Product` и миграции; трогать электрическую тему `(electric)`; менять порядок самого сайдбара; кэшировать позиции дольше запроса (иначе сайдбар и выдача разъедутся после правки `sort_order` в админке).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Обход в глубину | А(sort 1) с детьми А1, А2; Б(sort 2) | товары А, А1, А2, Б | N/A |
| Родитель раньше детей | товар прямо в А и товар в А1 | сначала товар А | N/A |
| Нулевой sort_order | В(sort 0), Б(sort 2) | Б раньше В | N/A |
| Нулевые по имени | «Капы»(0), «Бинты»(0) | Бинты, Капы | N/A |
| Исключённая категория | `uncategorized` или заглушка «Категория <uuid>» внутри ветки А | её товары и товары её детей — в конце выдачи, не посреди А | N/A |
| Вне дерева якоря | товар в категории без пути к якорю | в конце выдачи | без исключения |
| Два якоря | дети якорей X(sort 2) и Y(sort 1) | Y раньше X, общий список братьев | N/A |
| Одинаковые имена | два товара с одним `name` в одной категории | по возрастанию `id` | N/A |
| Фильтр категории | `category_id=А`, `ordering=category_tree` | товары А, А1, А2 | N/A |
| Пустое дерево | категорий нет / якоря нет | выдача по `name`, `id` | без исключения |
| Цикл parent | битая ссылка parent по кругу | обход не зацикливается | узлы цикла — в конец |
| Умолчание фронта | `/catalog` без `?ordering` | запрос с `ordering=category_tree`, в URL параметра нет | N/A |
| Старая ссылка | `/catalog?ordering=name` | по названию, параметр остаётся в URL | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/products/views.py:59` -- `ProductViewSet.filter_backends = [DjangoFilterBackend, filters.OrderingFilter]`; `ordering_fields`, `ordering=["-created_at"]`; описание параметра `ordering` в `extend_schema` (:148). Impact LOW (4 прямых, роутер/тесты).
- `backend/apps/products/views.py:331` -- `CategoryTreeViewSet.get_queryset`: как находятся якоря (`is_active`, `parent__isnull`, `name=ROOT_CATEGORY_NAME`) — повторить для корней обхода.
- `backend/apps/products/serializers.py:910` -- дети дерева: `order_by("sort_order", "name")` — порядок БД, на который опирается сайдбар.
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:127` -- `categoryRank`/`sortCategoryTree`: ранг сайдбара (0 — `sort_order>0`, 1 — ноль, 2 — `uncategorized`), стабильная сортировка поверх порядка API. Бэкенд повторяет то же правило.
- `backend/apps/products/filters.py:235` -- `filter_category_id`: поддерево через `category_id__in` — не трогать.
- `backend/apps/products/filters.py:360` -- `filter_search` ставит `order_by("-rank", …)`, `OrderingFilter` его перекрывает — не трогать.
- `backend/apps/products/category_utils.py` -- место для чистого helper'а порядка категорий.
- `frontend/src/app/(blue)/catalog/catalogQuery.ts:22,38` -- `DEFAULT_ORDERING = 'name'`, белый список `ORDERING_OPTIONS`. `parseOrdering` — risk HIGH по GitNexus (7 зависимых), но все внутри страницы каталога (blue); сигнатура не меняется.
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1853` -- `<select>` сортировки.
- `frontend/src/app/(electric)/electric/catalog/page.tsx:56` -- свой `DEFAULT_ORDERING`, не трогать.
- Тесты фронта с `ordering: 'name'` как умолчанием: `__tests__/CatalogPage.test.tsx` (:1784, 1834, 1895, 1919, 2202), `__tests__/catalogQuery.test.ts` (:22, 73; литерал в :89-90 с умолчанием не связан), `__tests__/page.test.tsx` (:74). `CatalogPage.test.tsx:1809` ждёт, что `?ordering=name` вычищается из URL, — переписать под «Старую ссылку».
- `backend/apps/products/serializers.py:915`, `views.py:353` -- условие исключения категорий сайдбара (дублируется) — вынести в общий `Q`-helper в `category_utils.py` и использовать в обоих местах и в обходе.
- `backend/apps/products/services/onec_admission.py:58` -- `compute_subtree`: образец защиты от циклов.
- `docs/api/openapi.yaml` -- контракт; гейт `check_openapi_sync`. `frontend/src/types/api.generated.ts:4367` -- генерируется из контракта (`npm run generate:types`), гейт `api-contract.yml:163`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/products/category_utils.py` -- `sidebar_excluded_categories_q()` (условие исключения сайдбара) и `catalog_category_order() -> list[int]`: один запрос `Category.objects.exclude(<исключённые>).order_by("sort_order", "name", "id").values_list("id", "parent_id", "sort_order", "slug")`, группировка детей по `parent_id` с сохранением порядка БД, стабильная сортировка по рангу сайдбара (0 — `sort_order > 0`, 1 — ноль; `uncategorized` уже вырезана запросом, ранг 2 фронта здесь не нужен), итеративный DFS от общего списка детей активных якорей с множеством посещённых -- одна точка правды порядка.
- [x] `backend/apps/products/views.py`, `serializers.py` -- `CategoryTreeViewSet` и `CategoryTreeSerializer.get_children` используют `sidebar_excluded_categories_q()` -- условие не расходится с обходом.
- [x] `backend/apps/products/filters.py` -- `CATEGORY_TREE_ORDERING = "category_tree"` и `CatalogOrderingFilter(OrderingFilter)`: если сырой параметр `ordering` равен `category_tree` — `order_by(<array_position(ids, category_id)>.asc(nulls_last=True), "name", "id")` выражением прямо в `order_by` (без `annotate`: алиас не нужен. В `GROUP BY` выражение попадёт в любом варианте — Django 5.2.7, `compiler.py:164-168`; Postgres это принимает, массив просто дважды окажется в тексте SQL, защищаться от этого не нужно); пустой список — `order_by("name", "id")`; иначе `super()` -- режим не ломает валидацию остальных полей.
- [x] `backend/apps/products/views.py` -- `filter_backends` → `CatalogOrderingFilter`; описание `ordering`: реальные значения `name`, `min_retail_price`, `created_at`, `total_stock` (с `-`) и `category_tree` -- API и схема знают режим.
- [x] `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` -- синхронизировать контракт и перегенерировать типы (`npm run generate:types`) -- гейты контракта.
- [x] `backend/apps/products/tests/unit/test_catalog_tree_ordering.py` -- тесты строк матрицы (кроме двух фронтовых) через `GET /api/v1/products/?ordering=category_tree`; DFS-helper — отдельно, включая цикл и пустое дерево.
- [x] `frontend/src/app/(blue)/catalog/catalogQuery.ts` -- `DEFAULT_ORDERING = 'category_tree'`, добавить в `ORDERING_OPTIONS`.
- [x] `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` -- первой опцией `<option value="category_tree">По категориям</option>`.
- [x] `frontend/src/app/(blue)/catalog/__tests__/*` -- обновить ожидания умолчания на `category_tree`; переписать `CatalogPage.test.tsx:1809`: `?ordering=name` остаётся в URL и уходит в запрос; `?ordering=category_tree` вычищается до `/catalog`.

**Acceptance Criteria:**
- Given прод-дерево, when открыть `/catalog` и пролистать страницы, then категории карточек идут в том же порядке, что и сайдбар на этой же странице, если раскрыть все ветки сверху вниз (родитель → его дети, по очереди); первая карточка — из первой категории сайдбара. Эталон — сайдбар, а не список из Intent: в нём «Обувь» стоит после «Специальной защиты шлема», хотя для сестёр с `sort_order = 0` алфавит дал бы обратный порядок, а форму прод-дерева при подготовке спеки не сверяли.
- Given выбрано «По цене (возр.)», when сменить страницу, then порядок и URL как раньше.

## Implementation Notes

- Запрос `catalog_category_order` берёт `values_list("id", "parent_id", "sort_order", "name", "is_active")`, а не `slug`: якоря находятся в том же запросе (активный корень с именем `ROOT_CATEGORY_NAME`), второго запроса нет; `slug` не нужен, `uncategorized` вырезает `exclude`. Сам DFS вынесен в чистую `order_category_tree(rows, root_parent_ids)` — её тесты не ходят в БД.
- Дети нескольких якорей берутся из строк в общем порядке запроса (`sort_order, name, id`), а не склейкой групп по якорю — это и есть «один список братьев», как в одном запросе `CategoryTreeViewSet`.
- `CatalogOrderingFilter` включает режим только при точном совпадении `ordering == "category_tree"`; составное `category_tree,name` уходит в `OrderingFilter` и отбрасывается его валидацией, как любое неизвестное поле.
- Описание `ordering` дополнено «По умолчанию -created_at» — это существующее умолчание API.
- Найден существующий дефект вне задачи: `Category.full_name` рекурсирует по `parent` без защиты, поэтому товар в категории с циклом `parent` роняет `GET /products/` с `RecursionError` при любом `ordering` (сериализатор зовёт `str(category)`). Обход цикла не боится — тест проверяет, что узлы цикла выпадают из `catalog_category_order()`, а товаров в самих узлах цикла не создаёт. Строка матрицы «Цикл parent → узлы цикла в конец» для выдачи API поэтому выполнима, только пока починен `full_name`.

## Spec Change Log

- 2026-11-11, разбор спеки в party mode (frozen не тронут): (1) обоснование «`annotate` уйдёт в `GROUP BY`, `order_by` — нет» неверно, `order_by` в Django 5.2.7 тоже попадает в `GROUP BY` — решение оставлено, причина в Task 3 исправлена; (2) AC1 сверяется с сайдбаром, а не со списком из Intent: список нарушает алфавит сестёр, форма прод-дерева не проверялась; (3) ранг `uncategorized` на бэкенде не нужен — её вырезает запрос; (4) в Design Notes добавлено расхождение с `filter_category_id` (только активные, 4 уровня, кэш 5 минут); (5) вместо ссылки на «рецепт из памяти», которого нет у Codex и Devin, в Verification вписана сама команда `check_openapi_sync`; (6) подпись «По категориям» оставлена, как во frozen. Предложение заменить её на «Как в каталоге», потому что внутри листовой категории режим совпадает с сортировкой по названию, отклонено.

## Review Triage Log

Ревью спеки (до утверждения), субагент:

| # | Находка | Вердикт | Что сделано |
|---|---------|---------|-------------|
| 1 | Не перегенерируется `api.generated.ts`, гейт `api-contract.yml` упадёт; в описании `ordering` несуществующие `retail_price` | high | задача контракта + реальные значения в описании |
| 2 | `CatalogPage.test.tsx:1809` ждёт вычистки `?ordering=name` | medium | в Code Map и задачу тестов |
| 3 | Заглушки/`uncategorized` под якорем встанут посреди ветки | medium | обход их пропускает, общий `Q`-helper исключения, строка матрицы |
| 4 | Порядок при нескольких якорях не задан | low | общий список братьев, строка матрицы |
| 5 | `annotate` с массивом уйдёт в `GROUP BY` | low | выражение прямо в `order_by` |
| 6 | Поиск на `/catalog` сменит порядок с названия на дерево | low | явно в Boundaries, владелец подтвердил «по дереву» |

## Design Notes

Позиции считаются в Python (сотни–тысячи категорий, один лёгкий запрос), а сортирует Postgres через `array_position(ARRAY[...], category_id)` — без новой колонки и без огромного `CASE`. Порядок БД `sort_order, name` + стабильный ранг дают ровно порядок сайдбара, в том числе collation имён. Неактивные категории в обходе остаются: видимые категории между собой упорядочены так же, а товар в скрытой категории остаётся в своей ветке. Исключённые сайдбаром заглушки, наоборот, вырезаются вместе с поддеревом. Psycopg2 2.9.9 превращает список в `ARRAY[...]`, Postgres 15 сравнивает `int[]` с `bigint category_id` без явного приведения.

Известное расхождение, не регрессия этой задачи: `filter_category_id` (`filters.py:257-268`) берёт поддерево только из активных категорий, не глубже 4 уровней, и кэширует его на 5 минут. Поэтому товар из неактивной подкатегории без фильтра стоит в своей ветке, а при выборе её родителя в сайдбаре пропадает. После правки дерева в админке фильтр может до 5 минут отдавать старое поддерево. Строка матрицы «Фильтр категории» подразумевает, что А1 и А2 активны. Фильтр по задаче не трогаем.

```python
position = Func(Value(ids, output_field=ArrayField(IntegerField())), F("category_id"),
                function="array_position", output_field=IntegerField())
```

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/products/tests/unit/test_catalog_tree_ordering.py tests/integration/test_catalog_api.py tests/integration/test_search_api.py` -- expected: всё зелёное.
- `cd docker && MSYS_NO_PATHCONV=1 docker compose -p freesport-test -f docker-compose.test.yml run --rm --no-deps -T -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml` -- expected: синхронно. В тестовом контейнере смонтирован только `backend/`, поэтому контракт подключается томом; в CI тот же гейт — шаг «Сверка openapi.yaml с кодом» в `.github/workflows/api-contract.yml`.
- `cd frontend && npx vitest run "src/app/(blue)/catalog"; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок.

## Suggested Review Order

**Порядок категорий (одна точка правды)**

- Вход: обход дерева от детей якорей, один запрос, без кэша.
  [`category_utils.py:120`](../../backend/apps/products/category_utils.py#L120)

- Чистый DFS: общий список братьев, стабильный ранг, защита от циклов.
  [`category_utils.py:76`](../../backend/apps/products/category_utils.py#L76)

- Общее условие исключения сайдбара — обход и дерево не расходятся.
  [`category_utils.py:54`](../../backend/apps/products/category_utils.py#L54)

**Режим `ordering=category_tree` в API**

- Фильтр: точное совпадение параметра, иначе стандартный `OrderingFilter`.
  [`filters.py:545`](../../backend/apps/products/filters.py#L545)

- `array_position` по `bigint[]` прямо в `order_by`, затем `name`, `id`.
  [`filters.py:564`](../../backend/apps/products/filters.py#L564)

- Подключение фильтра и реальные значения `ordering` в схеме.
  [`views.py:59`](../../backend/apps/products/views.py#L59)

- Сайдбар переведён на общий `Q`-helper.
  [`views.py:357`](../../backend/apps/products/views.py#L357)
  [`serializers.py:916`](../../backend/apps/products/serializers.py#L916)

**Фронтенд каталога**

- Новое умолчание и белый список значений.
  [`catalogQuery.ts:22`](../../frontend/src/app/(blue)/catalog/catalogQuery.ts#L22)

- Первая опция селекта «По категориям».
  [`CatalogPageClient.tsx:1854`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L1854)

**Контракт и тесты**

- Описание `ordering` в контракте и сгенерированных типах.
  [`openapi.yaml:1255`](../../docs/api/openapi.yaml#L1255)
  [`api.generated.ts:4367`](../../frontend/src/types/api.generated.ts#L4367)

- Контрактный тест: обход равен развёрнутому `/categories-tree/`.
  [`test_catalog_tree_ordering.py:133`](../../backend/apps/products/tests/unit/test_catalog_tree_ordering.py#L133)

- Строки матрицы через API.
  [`test_catalog_tree_ordering.py:161`](../../backend/apps/products/tests/unit/test_catalog_tree_ordering.py#L161)

- Фронтовые строки матрицы: старая ссылка `?ordering=name` остаётся в URL.
  [`CatalogPage.test.tsx:1822`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L1822)
