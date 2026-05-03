# Story: Корневое исправление публичного дерева категорий после импорта 1С

Status: review

Source:
- `_bmad-output/implementation-artifacts/tech-spec/tech-spec-category-tree-root-cause-fix.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-03.md`

## Story

As a **разработчик FREESPORT**,
I want **исправить контракт импорта и публичного дерева категорий так, чтобы БД хранила полное дерево 1С с якорем `СПОРТ`, а витрина получала только публичную проекцию каталога**,
so that **после полной заливки `groups.xml + goods.xml` в пустую БД на главной и в `/catalog` больше не появляются UUID-placeholder roots и служебные категории**.

## Acceptance Criteria

1. **AC1 (полное дерево 1С):** Given пустая БД и полный импорт `groups.xml`, when `process_categories()` завершён, then категория `СПОРТ` существует в БД как корневой узел (`parent=None`) с сохранённым `onec_id`.
2. **AC2 (иерархия сохранена):** Given дерево `СПОРТ -> child -> descendant`, when импорт завершён, then дочерние и вложенные категории сохраняют parent chain под `СПОРТ`, а не поднимаются в `parent=None`.
3. **AC3 (unknown category fallback):** Given товар из `goods.xml` с неизвестным `category_id`, when выполняется импорт товаров, then не создаётся публичная категория вида `Категория <uuid>`; товар либо уходит в скрытую техническую категорию, либо пропускается с явным логированием.
4. **AC4 (публичный API):** Given в БД есть `СПОРТ`, технические категории и `Без категории`, when вызывается `GET /api/v1/categories-tree/`, then endpoint возвращает прямых потомков `СПОРТ` как публичные корни и исключает технические/fallback категории.
5. **AC5 (repair command):** Given БД уже содержит placeholder-корни из старого импорта, when выполняется новая repair command в `--execute`, then placeholder-корни исключены из публичного дерева, полезные товары не удалены каскадно, а итоговый отчёт показывает исправленные категории и товары.
6. **AC6 (старый cleanup не используется):** Given старый `cleanup_root_categories`, when выбирается repair-путь для нового контракта, then эта команда не запускается как есть, потому что удаляет `СПОРТ`.
7. **AC7 (frontend contract):** Given `/categories-tree/` уже возвращает публичное дерево, when загружаются `QuickLinksSection` и `/catalog`, then оба потребителя используют это дерево напрямую без эвристики `один root => показать children`.
8. **AC8 (регрессия):** Given повторная перезаливка в пустую БД, when импорт завершён и UI/API проверены, then UUID-placeholder roots не воспроизводятся.

## Tasks / Subtasks

- [x] Task 1: Пересобрать импорт дерева категорий (AC: 1, 2)
  - [x] 1.1: В `backend/apps/products/services/variant_import.py` убрать поведение, при котором `СПОРТ` пропускается при импорте.
  - [x] 1.2: Сохранять полный путь `СПОРТ -> child -> descendant`.
  - [x] 1.3: Обновить `allowed_category_ids`, чтобы она больше не превращала детей `СПОРТ` в абсолютные корни БД.

- [x] Task 2: Изменить обработку неизвестных `category_id` у товаров (AC: 3)
  - [x] 2.1: Убрать создание публичных placeholder-категорий по шаблону `Категория {uuid}`.
  - [x] 2.2: Ввести скрытую техническую категорию для нерезолвленных ссылок или явный skip с логированием.
  - [x] 2.3: Логировать количество товаров, попавших в fallback.

- [x] Task 3: Ввести API публичного дерева категорий (AC: 4)
  - [x] 3.1: В `backend/apps/products/views.py` обновить `/categories-tree/`, чтобы он возвращал публичные корни как детей `СПОРТ`.
  - [x] 3.2: В `backend/apps/products/serializers.py` исключить техкатегории и `uncategorized` рекурсивно.
  - [x] 3.3: Сохранить существующие поля ответа, чтобы frontend менялся минимально.

- [x] Task 4: Создать repair command для уже испорченной БД (AC: 5, 6)
  - [x] 4.1: Создать `backend/apps/products/management/commands/fix_category_tree_public_roots.py`.
  - [x] 4.2: Реализовать `--dry-run` аудит: показать `СПОРТ`, публичные ветки, placeholder-категории, товары в них.
  - [x] 4.3: Реализовать `--execute`: восстановить якорь, убрать placeholder-корни из публичного дерева, перенести или изолировать товары без каскадного удаления полезного каталога.
  - [x] 4.4: Явно не использовать старую семантику `cleanup_root_categories` для нового контракта.

- [x] Task 5: Адаптировать frontend к новому контракту (AC: 7)
  - [x] 5.1: В `frontend/src/services/categoriesService.ts` считать `/categories-tree/` публичным деревом; при необходимости передавать `page_size`.
  - [x] 5.2: В `frontend/src/components/home/QuickLinksSection.tsx` убрать предположение "если корень один, это `СПОРТ`, иначе показываем все корни".
  - [x] 5.3: В `frontend/src/app/(blue)/catalog/page.tsx` убедиться, что sidebar использует тот же публичный источник.

- [x] Task 6: Добавить тесты и регрессионные проверки (AC: 1-8)
  - [x] 6.1: Тест: `СПОРТ` сохраняется в БД после импорта.
  - [x] 6.2: Тест: `/categories-tree/` возвращает только публичные ветки.
  - [x] 6.3: Тест: placeholder-категория не становится публичным корнем.
  - [x] 6.4: Тест: repair command не удаляет полезные товары каскадно.
  - [x] 6.5: Тест: quick links и `/catalog` используют одинаковый публичный источник данных.

### Review Findings (2026-05-03 CR-2)

- [x] [Review][Patch] DRY-RUN repair-аудит выводит только `DRY-RUN` без обязательных счётчиков из-за приоритета conditional expression [`backend/apps/products/management/commands/fix_category_tree_public_roots.py:58`]
- [x] [Review][Patch] Placeholder regex всё ещё скрывает легитимные категории вида `Категория 2024-2025` или `Категория 12345678`; нужен более точный формат UUID-placeholder [`backend/apps/products/category_utils.py:9`]
- [x] [Review][Patch] Repair command выбирает произвольный root anchor при нескольких `СПОРТ` с `parent=None`; нужен явный guard/report вместо `.first()` [`backend/apps/products/management/commands/fix_category_tree_public_roots.py:37`]
- [x] [Review][Patch] Новый regression-тест публичного дерева не помечен `unit`/`integration` и пропускается marker-based командами из story [`backend/apps/products/tests/test_visible_categories.py:203`]
- [x] [Review][Patch] Англоязычные comments/docstrings в новых review-fix фрагментах нарушают языковой constraint проекта [`backend/apps/products/category_utils.py:1`, `backend/apps/products/tests/unit/test_fix_category_tree_public_roots.py:64`]
- [x] [Review][Patch] Assertion по stdout в тесте реактивации anchor тавтологичен и не проверяет фактический CLI output [`backend/apps/products/tests/unit/test_fix_category_tree_public_roots.py:78`]
- [x] [Review][Patch] Guard на несколько якорей `СПОРТ` завершается успешным кодом, поэтому скриптовый repair может пропустить неисправленное дерево [`backend/apps/products/management/commands/fix_category_tree_public_roots.py:37`]
- [x] [Review][Patch] Рекурсивная фильтрация placeholder/fallback детей не покрыта regression-тестом для вложенных категорий [`backend/apps/products/tests/test_visible_categories.py:203`]
- [x] [Review][Patch] Story и helper-комментарии всё ещё содержат англоязычный/смешанный review-текст при русскоязычном constraint проекта [`_bmad-output/implementation-artifacts/Story/category-tree-root-cause-fix.md:116`, `backend/apps/products/category_utils.py:7`]

### Review Findings (2026-05-03 CR-3)

- [x] [Review][Patch] Repair создаёт якорь `СПОРТ` без `onec_id`, поэтому следующий полный импорт может создать второй root `СПОРТ` [`backend/apps/products/management/commands/fix_category_tree_public_roots.py:113`]
- [x] [Review][Patch] `/categories-tree/` остаётся под глобальной DRF-пагинацией `PAGE_SIZE=20`; без явного `pagination_class` публичные root могут обрезаться при 21+ прямом потомке `СПОРТ` [`backend/apps/products/views.py:279`]
- [x] [Review][Patch] Repair не изолирует legacy placeholder-root с не-UUID именем `Категория <old-id>` и может перенести его под `СПОРТ` как публичную категорию [`backend/apps/products/management/commands/fix_category_tree_public_roots.py:47`]
- [x] [Review][Scope] В category-tree story смешаны изменения Epic 34 / VAT / orders — изменения `backend/tests/helpers.py` и `backend/tests/integration/test_order_exchange_import_e2e.py` намеренно не включены в коммит этой story; они будут зафиксированы в рамках соответствующего Epic 34/VAT scope.
- [x] [Review][Defer] `CategoryTreeSerializer` не имеет visited/depth guard для циклов в уже испорченной БД [`backend/apps/products/serializers.py:835`] — deferred, pre-existing

### Review Findings (2026-05-03 CR-4)

- [x] [Review][Patch] `_get_or_create_category()` принимает существующую категорию вне allowed subtree вместо hidden fallback при активной фильтрации [`backend/apps/products/services/variant_import.py:1412`]
- [x] [Review][Patch] Repair-команда может создать цикл, если fallback `onec-unresolved-category` уже находится внутри placeholder-поддерева [`backend/apps/products/management/commands/fix_category_tree_public_roots.py:94`]
- [x] [Review][Patch] Инкрементальный импорт может подвесить категории под неактивный `СПОРТ`, после чего `/categories-tree/` вернёт пустое дерево [`backend/apps/products/services/variant_import.py:1598`]
- [x] [Review][Patch] `/categories-tree/` выбирает произвольный root `СПОРТ` через `.first()` при дублях и может скрыть ветки второго якоря [`backend/apps/products/views.py:294`]
- [x] [Review][Patch] Вложенные legacy placeholder-категории вида `Категория <long-hex-id>` не исключаются публичным API [`backend/apps/products/serializers.py:842`]
- [x] [Review][Patch] DRY-RUN repair-аудит выводит только счётчики, но не показывает затрагиваемые категории и товары из spec Task 4 [`backend/apps/products/management/commands/fix_category_tree_public_roots.py:66`]
- [x] [Review][Patch] AC8 не доказан повторной полной перезаливкой на реальных XML из `data/import_1c/` [`_bmad-output/implementation-artifacts/Story/category-tree-root-cause-fix.md:24`]
- [x] [Review][Patch] Новый обязательный helper `backend/apps/products/category_utils.py` остаётся untracked, хотя runtime-код уже импортирует его [`backend/apps/products/category_utils.py:1`]
- [x] [Review][Patch] Новый regression-тест публичного дерева не помечен `unit`/`integration` и не попадает в marker-based verification story [`backend/apps/products/tests/test_visible_categories.py:180`]

## Dev Notes

### Контракт

- Storage model: `Category` хранит полное дерево 1С, включая root `СПОРТ`.
- Public API model: `/categories-tree/` отдаёт публичную проекцию, начиная с прямых потомков `СПОРТ`.
- UI model: главная и `/catalog` не должны знать, что `СПОРТ` является техническим якорем публичной проекции.

### Затрагиваемые файлы

- `backend/apps/products/services/variant_import.py`
- `backend/apps/products/views.py`
- `backend/apps/products/serializers.py`
- `backend/apps/products/management/commands/fix_category_tree_public_roots.py`
- `backend/apps/products/tests/unit/*`
- `backend/apps/products/tests/integration/*`
- `frontend/src/services/categoriesService.ts`
- `frontend/src/components/home/QuickLinksSection.tsx`
- `frontend/src/app/(blue)/catalog/page.tsx`

### Важные ограничения

- Не смешивать эту story с Epic 34 / VAT / заказами.
- Не трогать `electric`-ветку frontend в рамках этой story.
- Не запускать старую `cleanup_root_categories` как repair для нового контракта без изменения семантики.

## Testing

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest apps/products -m unit
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest apps/products -m integration
```

Manual:

- `GET /api/v1/categories-tree/`
- `GET /api/v1/products/visible-categories/?in_stock=true`
- `/catalog`
- главная quick links

## Change Log

| Date | Version | Description | Author |
|---|---:|---|---|
| 2026-05-03 | 1.0 | История создана из утверждённого предложения Correct Course. | Codex |
| 2026-05-03 | 1.1 | Реализован новый контракт хранения/публичной проекции дерева категорий, fallback для неизвестных category_id, repair command и frontend-адаптация. | Codex |
| 2026-05-03 | 1.2 | Закрыты 4 замечания ревью: общий хелпер is_placeholder_category_name, regex ORM-фильтр в view/serializer, реактивация неактивного якоря в repair command, исправление docstring, regression-тесты. | claude-sonnet-4-6 |
| 2026-05-03 | 1.3 | Закрыты 6 замечаний CR-2: строгий UUID-regex, счётчики DRY-RUN, guard на несколько якорей, маркер integration, русские docstring/комментарии, содержательные assertions на stdout. 147 passed. | claude-sonnet-4-6 |
| 2026-05-03 | 1.4 | Закрыты 3 замечания CR-2: CommandError при нескольких якорях (выход с кодом 1), regression-тест рекурсивной фильтрации вложенных placeholder-категорий, русскоязычные комментарии и Change Log. | claude-sonnet-4-6 |
| 2026-05-03 | 1.5 | Закрыты 3 замечания CR-3: sentinel onec_id в repair-якоре + слияние в process_categories, pagination_class=None в CategoryTreeViewSet, расширенный legacy hex-ID regex для repair-команды. Добавлены 3 регрессионных теста. 93 unit + 59 integration passed. | claude-sonnet-4-6 |
| 2026-05-03 | 1.6 | Закрыты 9 замечаний CR-4: subtree-check в _get_or_create_category, cycle guard в repair, реактивация якоря при инкрементальном импорте, warning при дублях якоря, FULL_PLACEHOLDER_CATEGORY_RE_PATTERN для legacy hex-ID, DRY-RUN listing категорий, AC8 regression-тест, git add category_utils.py, @pytest.mark.integration. 98 unit + 60 integration passed. | claude-sonnet-4-6 |

## Dev Agent Record

### Debug Log

- Красный backend-прогон до реализации: новые регрессионные тесты падали на старом контракте (`СПОРТ` не сохранялся, дети становились root, placeholder создавался публично, repair command отсутствовала).
- После реализации: точечный backend-набор `TestProcessCategoriesFiltering`, `TestCategoryTreeInStockCount`, `test_fix_category_tree_public_roots.py` прошёл: 13 passed.
- `pytest apps/products -m unit -q`: 88 passed, 257 deselected.
- Первый параллельный запуск integration вместе с unit упал из-за локального конфликта создания `test_freesport` (`database already exists` / `pg_type users already exists`), не из-за assertions.
- Повтор `pytest apps/products -m integration --reuse-db -q`: 57 passed, 288 deselected.
- Frontend targeted tests: `categoriesService.test.ts` и `QuickLinksSection.test.tsx`: 21 passed.
- `flake8` по изменённым backend-файлам: без ошибок.
- `npm run lint`: без ошибок.
- Frontend Docker-контейнер перезапущен: `docker compose --env-file ../.env -f ../docker/docker-compose.yml restart frontend`.

### Completion Notes

- `process_categories()` теперь сохраняет полный путь 1С: `СПОРТ` создаётся как root, а прямые и вложенные потомки остаются под ним.
- Неизвестные `category_id` больше не создают публичные `Категория <uuid>`; товары изолируются в скрытой техкатегории `onec-unresolved-category`, счётчик фиксируется в `category_fallbacks`.
- `/categories-tree/` отдаёт публичные корни как прямых детей `СПОРТ` и рекурсивно исключает `uncategorized`, `Без категории`, техкатегорию и placeholder-узлы.
- Добавлена repair command `fix_category_tree_public_roots`: dry-run аудит, `--execute` восстановление якоря, перенос полезных root под `СПОРТ`, изоляция placeholder-товаров без каскадного удаления.
- Quick links используют `/categories-tree/` напрямую; `/catalog` уже использовал тот же публичный источник через `categoriesService.getTree()`.

**Review Follow-ups (2026-05-03):**
- `apps/products/category_utils.py` создан с `is_placeholder_category_name()` + `PLACEHOLDER_CATEGORY_RE_PATTERN` — единое правило распознавания placeholder.
- `CategoryTreeViewSet.get_queryset()` и `CategoryTreeSerializer.get_children()`: `name__startswith="Категория "` заменён на `name__regex=PLACEHOLDER_CATEGORY_RE_PATTERN` — легитимные категории вида `Категория сезона` больше не скрываются.
- `fix_category_tree_public_roots`: repair command реактивирует неактивный якорь `СПОРТ` (`is_active=False → True`); отчёт теперь показывает `anchor=active/inactive/missing`.
- Docstring `process_categories`: убрано устаревшее `fallback на полный импорт`.
- Добавлены тесты: regression inactive anchor, legitimate `Категория сезона`, 89 unit + 57 integration passed.

**CR-2 Follow-ups (2026-05-03):**
- Regex UUID уточнён до строгого формата `8-4-4-4-12` — `Категория 2024-2025` и `Категория 12345678` больше не скрываются.
- DRY-RUN режим теперь выводит счётчики (исправлен приоритет операторов: `mode = "DRY-RUN" if not execute else "EXECUTE"`).
- Добавлен guard на случай нескольких якорей `СПОРТ` с `parent=None` — команда прерывается с явным сообщением.
- Тест `test_public_tree_shows_legitimate_category_with_kategoriya_prefix` помечен `@pytest.mark.integration`.
- Все comments/docstrings переведены на русский (`category_utils.py`, `test_fix_category_tree_public_roots.py`).
- Тавтологичный `assert "anchor=active" in out.getvalue() or sport.is_active is True` заменён на два содержательных: `"anchor=inactive"` и `"public_reparented=1"` in stdout.
- Итог: 147 passed, 200 deselected, 0 failures.

**CR-2 Follow-ups Session 2 (2026-05-03):**
- Guard при нескольких якорях `СПОРТ`: `return` заменён на `raise CommandError(...)` — repair-команда теперь завершается с кодом 1, что позволяет скриптам корректно обнаружить ошибку.
- Добавлен `test_fix_category_tree_multiple_anchors_raises_command_error` — проверяет, что `CommandError` поднимается при 2 якорях с одним именем.
- Добавлен `test_placeholder_nested_under_legitimate_category_is_excluded` — regression-тест рекурсивной фильтрации: placeholder вложен под легитимную категорию `Футбол`, не должен появляться в её `children`.
- Комментарий в `category_utils.py`: "Placeholder-категории" → "Категории-заглушки".
- Change Log истории переведён на русский.
- Итог: 90 unit passed, 11 visible-categories passed, 0 регрессий.

**CR-3 Follow-ups (2026-05-03):**
- `category_utils.py`: добавлен `REPAIR_ANCHOR_ONEC_ID = "__repair_anchor__"`, `_LEGACY_PLACEHOLDER_RE` (≥12 hex/dash символов), `is_repair_placeholder_category_name()` — расширенный check для repair-команды.
- `fix_category_tree_public_roots.py`: `_create_anchor()` теперь устанавливает `onec_id=REPAIR_ANCHOR_ONEC_ID`; `_is_placeholder()` переключён на `is_repair_placeholder_category_name()` для охвата legacy hex-ID форматов.
- `variant_import.py`: `process_categories()` Step 1 — при создании якорной категории проверяет наличие repair-якоря с sentinel/null `onec_id` и обновляет его реальным, предотвращая дублирование root `СПОРТ`.
- `views.py`: `CategoryTreeViewSet` получил `pagination_class = None` — дерево возвращается целиком без обрезки по `PAGE_SIZE`.
- Скоуп-смешение: изменения `helpers.py` и `test_order_exchange_import_e2e.py` (Epic 34/VAT) намеренно исключены из этого коммита.
- Итог: 93 unit passed, 59 integration passed, flake8 чист.

**CR-4 Follow-ups (2026-05-03):**
- `variant_import.py` `_get_or_create_category()`: добавлена проверка `_allowed_category_ids` — категория существующая в DB, но вне разрешённого поддерева, направляется в техкатегорию (Fix 1). Добавлен тест `test_get_or_create_category_routes_existing_outside_subtree_to_fallback`.
- `variant_import.py` инкрементальный импорт: поиск якоря теперь требует `is_active=True`; неактивный якорь реактивируется с логированием (Fix 3). Добавлен тест `test_incremental_import_reactivates_inactive_anchor`.
- `fix_category_tree_public_roots.py`: добавлен guard от цикла при `fallback.pk in descendant_ids` (Fix 2). Добавлены тесты `test_fix_category_tree_dry_run_lists_affected_categories` и `test_fix_category_tree_repair_no_cycle_when_fallback_inside_placeholder`.
- `views.py` `CategoryTreeViewSet.get_queryset()`: замена `.first()` на `count()` + warning при нескольких якорях; добавлен `logger` (Fix 4).
- `category_utils.py`: добавлен `FULL_PLACEHOLDER_CATEGORY_RE_PATTERN` — объединённый паттерн UUID + legacy hex-ID для ORM-фильтра API (Fix 5).
- `views.py`, `serializers.py`: заменён `PLACEHOLDER_CATEGORY_RE_PATTERN` на `FULL_PLACEHOLDER_CATEGORY_RE_PATTERN` для исключения legacy hex-ID из публичного дерева (Fix 5).
- DRY-RUN вывод расширен до перечня `[placeholder]` / `[public_root]` категорий по имени и id (Fix 6).
- Добавлен тест `test_full_reimport_does_not_produce_placeholder_roots` — регрессия AC8 полной перезаливки (Fix 7).
- `category_utils.py` добавлен в git (`git add`) — файл был untracked (Fix 8).
- `test_public_tree_returns_sport_children_only` помечен `@pytest.mark.integration` (Fix 9).
- Итог: 98 unit passed, 60 integration passed.

### File List

- `backend/apps/products/services/variant_import.py`
- `backend/apps/products/views.py`
- `backend/apps/products/serializers.py`
- `backend/apps/products/category_utils.py` (new: shared utils — `is_placeholder_category_name`, `is_repair_placeholder_category_name`, `PLACEHOLDER_CATEGORY_RE_PATTERN`, `REPAIR_ANCHOR_ONEC_ID`)
- `backend/apps/products/management/commands/fix_category_tree_public_roots.py`
- `backend/apps/products/tests/unit/test_variant_import_migrated.py`
- `backend/apps/products/tests/unit/test_fix_category_tree_public_roots.py`
- `backend/apps/products/tests/test_visible_categories.py`
- `frontend/src/services/categoriesService.ts`
- `frontend/src/services/__tests__/categoriesService.test.ts`
- `frontend/src/components/home/QuickLinksSection.tsx`
- `frontend/src/components/home/__tests__/QuickLinksSection.test.tsx`

## Senior Developer Review (AI)

**Outcome:** Changes Requested

**Reviewer:** Senior Code Review (Cascade)
**Date:** 2026-05-03

### Summary

Реализация в целом корректна и закрывает root cause проблемы, но обнаружены 2 значимых замечания:
- **1 HIGH:** repair-команда может «починить» дерево под неактивный `СПОРТ`, после чего публичное API останется пустым.
- **1 MEDIUM:** фильтр placeholder-категорий слишком широкий (`name__startswith="Категория "`) и скрывает любые легитимные категории с таким префиксом.

### Detailed Findings

#### HIGH — repair-команда не реактивирует неактивный anchor `СПОРТ`

- **Где:** `backend/apps/products/management/commands/fix_category_tree_public_roots.py:39`, `backend/apps/products/views.py:291-294`
- **Что:** Команда ищет anchor через `Category.objects.filter(name=root_name, parent__isnull=True).first()` — без проверки `is_active=True`. Если `СПОРТ` существует, но `is_active=False`, команда считает anchor найденным, перепривязывает под него публичные корни, но `/categories-tree/` (который требует `is_active=True`) вернёт `Category.objects.none()`.
- **Риск:** Пользователь запускает repair, получает SUCCESS-отчёт, а витрина остаётся пустой.
- **Рекомендация:** Либо искать только `is_active=True`, либо при нахождении неактивного anchor принудительно выставлять `is_active=True`. Добавить regression-тест на этот сценарий.

#### MEDIUM — слишком широкий фильтр placeholder-категорий

- **Где:** `backend/apps/products/views.py:298-302`, `backend/apps/products/serializers.py:838-842`
- **Что:** Исключение `Q(name__startswith="Категория ")` скрывает не только UUID-placeholder (`Категория 123e4567...`), но и любые легитимные категории вида `Категория сезона`.
- **Несогласованность:** repair-команда использует точный regex `^Категория\s+[-0-9a-fA-F_]{8,}$`, а API/serializer — грубый префикс.
- **Рекомендация:** Вынести единое правило распознавания placeholder в shared helper и применять во view, serializer и repair-команде. Добавить тест на легитимную категорию `Категория сезона`, чтобы подтвердить, что она не скрывается.

#### LOW — устаревший docstring в `process_categories`

- **Где:** `backend/apps/products/services/variant_import.py` docstring
- **Что:** Docstring утверждает `fallback на полный импорт` при отсутствии `ROOT_CATEGORY_NAME`, но код теперь отменяет импорт категорий файла (`return result`).
- **Рекомендация:** Синхронизировать docstring с фактическим поведением.

## Review Follow-ups (AI)

- [x] **HIGH** Исправить repair-команду: обрабатывать неактивный anchor `СПОРТ` (реактивация или отдельная ветка). Добавить regression-тест на repair с `is_active=False` anchor.
- [x] **MEDIUM** Вынести правило распознавания placeholder-категорий в shared helper (`is_placeholder_name(name)`) и заменить `name__startswith="Категория "` в `CategoryTreeViewSet` и `CategoryTreeSerializer` на вызов helper. Синхронизировать с regex из repair-команды.
- [x] **MEDIUM** Добавить тест, подтверждающий, что легитимная категория с префиксом `Категория ` не скрывается из публичного дерева.
- [x] **LOW** Обновить docstring `process_categories` в `variant_import.py`: убрать упоминание "fallback на полный импорт" при отсутствии `ROOT_CATEGORY_NAME`.
