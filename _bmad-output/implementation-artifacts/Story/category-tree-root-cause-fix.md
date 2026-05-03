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
| 2026-05-03 | 1.0 | Story created from approved Correct Course proposal. | Codex |
| 2026-05-03 | 1.1 | Реализован новый контракт хранения/публичной проекции дерева категорий, fallback для неизвестных category_id, repair command и frontend-адаптация. | Codex |

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

### File List

- `backend/apps/products/services/variant_import.py`
- `backend/apps/products/views.py`
- `backend/apps/products/serializers.py`
- `backend/apps/products/management/commands/fix_category_tree_public_roots.py`
- `backend/apps/products/tests/unit/test_variant_import_migrated.py`
- `backend/apps/products/tests/unit/test_fix_category_tree_public_roots.py`
- `backend/apps/products/tests/test_visible_categories.py`
- `frontend/src/services/categoriesService.ts`
- `frontend/src/services/__tests__/categoriesService.test.ts`
- `frontend/src/components/home/QuickLinksSection.tsx`
- `frontend/src/components/home/__tests__/QuickLinksSection.test.tsx`
