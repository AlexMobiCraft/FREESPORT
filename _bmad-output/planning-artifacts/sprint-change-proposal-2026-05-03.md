---
title: "Sprint Change Proposal: публичное дерево категорий после импорта 1С"
date: "2026-05-03"
project: "FREESPORT"
workflow: "bmad-correct-course"
mode: "batch"
status: "approved"
trigger_spec: "_bmad-output/implementation-artifacts/tech-spec/tech-spec-category-tree-root-cause-fix.md"
approved_by: "Alex"
approved_at: "2026-05-03"
---

# Sprint Change Proposal: публичное дерево категорий после импорта 1С

## 1. Issue Summary

### Триггер

Триггером является draft tech-spec `tech-spec-category-tree-root-cause-fix.md`, созданный после проверки пустой локальной БД, залитой из 1С. Витрина показывает некорректное дерево категорий:

- `/catalog` строится от `parent=None`, но среди корней появляются технические категории вида `Категория <uuid>`;
- главная страница через `QuickLinksSection` отображает все корни из `/categories-tree/`;
- якорная категория `СПОРТ` отсутствует в БД, хотя присутствует в `groups.xml`;
- товарный импорт может создать placeholder-категорию по неизвестному `category_id`, и такая категория становится публичной.

### Тип изменения

Категория изменения: failed approach requiring different solution.

Ранее внедрённая спецификация `tech-spec-category-filter-sport-subcategories.md` была основана на допущении, что `СПОРТ` не хранится в БД сайта, а её прямые потомки становятся корнями (`parent=None`). Новые данные показали, что это допущение ломает восстановление полного дерева 1С в пустой БД и смешивает внутреннюю структуру импорта с публичной навигацией витрины.

### Доказательства

Текущий код подтверждает конфликт:

- `backend/apps/products/services/variant_import.py` пропускает корневые категории при активном `ROOT_CATEGORY_NAME` и делает детей `СПОРТ` корнями сайта.
- `backend/apps/products/management/commands/cleanup_root_categories.py` reparent-ит детей `СПОРТ` в `parent=None` и удаляет саму `СПОРТ`.
- `backend/apps/products/views.py` возвращает `/categories-tree/` как `Category.objects.filter(is_active=True, parent__isnull=True)`.
- `frontend/src/components/home/QuickLinksSection.tsx` содержит fallback: если дерево имеет один корень, показать его children, иначе показать все корни.
- `_get_or_create_category()` всё ещё может создать placeholder `Категория {category_id}` для allowed category id, если category id не найден в БД.

## 2. Impact Analysis

### Epic Impact

Текущие активные sprint-status записи относятся к Epic 34 по VAT/sub-orders. Эта корректировка не меняет Epic 34 и не должна смешиваться с заказами/НДС.

Фактически затрагивается завершённый brownfield-пласт каталога и импорта 1С:

- импорт категорий из 1С;
- публичный API дерева категорий;
- главная страница и `/catalog`;
- cleanup/repair существующих данных;
- тесты импорта, API и frontend-потребителей дерева.

Рекомендованное оформление: отдельный bugfix/follow-up story в implementation artifacts, без изменения Epic 34. Если требуется строгий sprint-status учёт, добавить отдельную строку bugfix story в новый или существующий каталоговый follow-up блок после утверждения этого proposal.

### Story Impact

Нужна новая история или dev-task на основе trigger spec:

Story: NEW `category-tree-root-cause-fix`

OLD:
- Предыдущая реализация считает детей `СПОРТ` публичными root categories.
- `cleanup_root_categories` удаляет `СПОРТ`.
- `/categories-tree/` возвращает все активные категории с `parent=None`.

NEW:
- `Category` хранит полное дерево 1С, включая `СПОРТ`.
- Публичное дерево витрины строится не от всех `parent=None`, а от прямых потомков `СПОРТ`.
- Технические fallback-категории и `Без категории` исключаются из публичного дерева.
- Unknown `category_id` не создаёт публичную placeholder-категорию.
- Cleanup command не удаляет `СПОРТ`, а восстанавливает/изолирует данные под новым контрактом.

Rationale:
Полное дерево 1С должно быть источником истины для импорта и восстановления, а публичная навигация должна быть отдельной проекцией этого дерева.

### Artifact Conflicts

PRD/refined PRD:
- Конфликта с MVP нет. Требование поддерживает CR1 `/api/v1/` и CR2 целостности данных при синхронизации с 1С.
- Нужно добавить уточнение к требованиям каталога: публичное дерево категорий является проекцией полного дерева 1С.

Architecture:
- ADR-002 по 1С остаётся актуальным, но требует уточнения: `onec_id` и дерево 1С сохраняются полностью; UI не обязан отображать всю raw-иерархию.
- API-first контракт `/categories-tree/` должен быть определён как публичное дерево витрины, а не техническое дерево всех root categories.
- Service Layer остаётся правильной границей: импорт/repair в `variant_import.py` и management command, views/serializers только формируют публичную проекцию.

UX/UI:
- UX-спеки уже подразумевают, что `СПОРТ` не показывается как отдельный breadcrumb/root в публичном пути. Это совместимо с новым backend-контрактом: `СПОРТ` хранится в БД, но публичный API отдаёт его детей как корни.
- `QuickLinksSection` и `/catalog` должны одинаково читать уже публичное дерево без эвристики "один root => показать children".

API docs:
- `docs/api/contracts-backend.md` сейчас описывает `GET /categories-tree/` слишком общо как "иерархическое дерево категорий". Нужно уточнить, что endpoint возвращает публичное дерево каталога.

Secondary artifacts:
- Предыдущая spec `tech-spec-category-filter-sport-subcategories.md` должна быть помечена как superseded для части "СПОРТ не создаётся/удаляется".
- Старый `cleanup_root_categories` должен быть заменён или явно deprecated, чтобы его случайный запуск не удалил восстановленный якорь.
- `deferred-work.md` по `visible_categories` остаётся смежным, но не блокирует этот root-cause fix.

## 3. Recommended Approach

### Выбранный путь

Option 1: Direct Adjustment.

### Обоснование

Это не стратегический pivot и не причина пересматривать MVP. Проблема локализована в контракте категорий: импорт, публичная API-проекция, repair-команда и два frontend-потребителя. Откат completed work не нужен, потому что старое решение можно заменить точечным root-cause fix с тестами.

### Оценка

- Scope classification: Moderate.
- Effort: Medium.
- Risk: Medium.
- Timeline impact: 1 focused backend/frontend bugfix story плюс ручная проверка после полной перезаливки 1С.

### Основные риски

- Breadcrumbs и deep links могут начать видеть `СПОРТ` в raw-path, если frontend берёт breadcrumbs не из публичной проекции.
- Cleanup/repair может потерять товары, если повторит старую CASCADE-логику.
- Тесты, закрепляющие старый инвариант `children of СПОРТ => parent=None`, должны быть переписаны осознанно, а не просто удалены.
- API-кэш дерева категорий при наличии кэширования должен инвалидироваться после импорта/repair.

## 4. Detailed Change Proposals

### 4.1 Tech Spec

Artifact: `_bmad-output/implementation-artifacts/tech-spec/tech-spec-category-tree-root-cause-fix.md`

OLD:
- `status: draft`
- План описывает правильное направление, но не фиксирует, что предыдущая `cleanup_root_categories` опасна после смены контракта.

NEW:
- После утверждения proposal перевести spec в `ready-for-dev`.
- Добавить explicit guard: старую `cleanup_root_categories` нельзя запускать как repair для нового контракта; её нужно заменить новой командой или изменить семантику.
- Добавить AC: после repair `СПОРТ` существует в БД и не отображается как публичный root.
- Добавить AC: товары с unknown `category_id` либо изолируются в скрытой техкатегории, либо импортируется skip/error без публичного placeholder.

Rationale:
Сейчас самый опасный operational risk не в frontend, а в старой cleanup-команде, которая прямо удаляет новый якорь.

### 4.2 Previous Tech Spec

Artifact: `_bmad-output/implementation-artifacts/tech-spec/tech-spec-category-filter-sport-subcategories.md`

OLD:
- `status: implemented`
- Solution: children of `СПОРТ` становятся `parent=None`, `СПОРТ` удаляется/не создаётся.

NEW:
- Добавить в начало документа note: "Superseded for category-root contract by `tech-spec-category-tree-root-cause-fix.md` and `sprint-change-proposal-2026-05-03.md`."
- Оставить историческую ценность документа, но запретить использовать его как актуальный контракт импорта.

Rationale:
Без явной пометки будущий агент или разработчик может восстановить старую логику по уже implemented spec.

### 4.3 PRD / Product Requirement

Artifact: `_bmad-output/planning-artifacts/refined-prd.md`

Section: `2. Требования`

OLD:
```md
- **Интеграция с 1С**: Импорт товаров, цен, остатков и клиентов; экспорт заказов и синхронизация статусов.
```

NEW:
```md
- **Интеграция с 1С**: Импорт товаров, цен, остатков, клиентов и полного дерева категорий 1С; экспорт заказов и синхронизация статусов.
- **Каталог**: Публичная навигация каталога является отдельной проекцией полного дерева 1С и не отображает технические или fallback-категории.
```

Rationale:
Это фиксирует продуктовый инвариант без расширения MVP.

### 4.4 Architecture

Artifact: `_bmad-output/planning-artifacts/architecture.md`

Section: `ADR-002: Стратегия интеграции с 1С`

OLD:
```md
Использование `ImportSession` для атомарности. Основной инструмент: `VariantImportProcessor` и команда `import_products_from_1c`.
```

NEW:
```md
Использование `ImportSession` для атомарности. Основной инструмент: `VariantImportProcessor` и команда `import_products_from_1c`. Категории из 1С сохраняются как полное raw-дерево по `onec_id`, включая якорные корни. Публичная навигация каталога строится отдельной API-проекцией и не обязана совпадать со всеми `parent=None` узлами БД.
```

Rationale:
Разделяет storage model и presentation contract.

### 4.5 API Documentation

Artifact: `docs/api/contracts-backend.md`

Section: `Каталог (/products, /categories, /brands)`

OLD:
```md
- `GET /categories-tree/`: Иерархическое дерево категорий.
```

NEW:
```md
- `GET /categories-tree/`: Публичное дерево каталога для витрины. Для 1С-дерева с якорем `СПОРТ` endpoint возвращает прямых потомков `СПОРТ` как публичные корни и исключает технические/fallback-категории.
```

Rationale:
Frontend и тесты должны зависеть от явного API-контракта, а не от текущего устройства БД.

### 4.6 Backend Implementation

Files:
- `backend/apps/products/services/variant_import.py`
- `backend/apps/products/views.py`
- `backend/apps/products/serializers.py`
- `backend/apps/products/management/commands/fix_category_tree_public_roots.py`
- tests under `backend/apps/products/tests/`

OLD:
- `process_categories()` при `ROOT_CATEGORY_NAME` пропускает все root categories и не создаёт `СПОРТ`.
- `_get_or_create_category()` может создать `Категория {category_id}` как активную категорию.
- `CategoryTreeViewSet.get_queryset()` возвращает все active roots.
- `cleanup_root_categories` удаляет `СПОРТ` и другие roots через CASCADE.

NEW:
- `process_categories()` сохраняет `СПОРТ` как root и строит полный parent chain из `groups.xml`.
- `_get_or_create_category()` не создаёт публичный placeholder для unknown `category_id`; fallback должен быть скрытой техкатегорией или controlled skip с логированием.
- `CategoryTreeViewSet` возвращает публичные roots: прямых детей `СПОРТ`; если `СПОРТ` отсутствует, endpoint должен возвращать безопасный empty/error-observable fallback, а не все `parent=None`.
- Serializer исключает технические/fallback узлы рекурсивно.
- Новая repair command работает в `--dry-run` и `--execute`, не удаляет `СПОРТ`, изолирует placeholder-категории и выводит отчёт по категориям/товарам.

Rationale:
Исправление должно убрать саму возможность повторного появления UUID-root категорий на витрине.

### 4.7 Frontend Implementation

Files:
- `frontend/src/services/categoriesService.ts`
- `frontend/src/components/home/QuickLinksSection.tsx`
- `frontend/src/app/(blue)/catalog/page.tsx`
- related tests

OLD:
- `QuickLinksSection` сам решает: если один root, показать children; если много roots, показать roots.
- `/catalog` доверяет дереву как уже пригодному для sidebar, но backend отдаёт все roots.

NEW:
- Frontend считает `/categories-tree/` уже публичным деревом.
- Удалить эвристику `tree.length === 1 && tree[0].children`.
- `/catalog` и home quick links используют один и тот же публичный источник без специальных знаний о `СПОРТ`.
- `getTree()` при необходимости передаёт `page_size`, если backend сохраняет пагинацию.

Rationale:
Знание о technical anchor не должно жить в каждом компоненте витрины.

## 5. Checklist Results

| ID | Статус | Результат |
|---|---|---|
| 1.1 | Done | Trigger artifact: `tech-spec-category-tree-root-cause-fix.md`; triggering issue: сломанное публичное дерево после полной заливки 1С в пустую БД. |
| 1.2 | Done | Тип: failed approach requiring different solution. |
| 1.3 | Done | Evidence собрано из trigger spec, previous spec и текущих code paths. |
| 2.1 | Done | Epic 34 не затрагивается; категория относится к отдельному catalog/1C import bugfix. |
| 2.2 | Action-needed | После утверждения создать/зарегистрировать отдельную bugfix story/dev-task. |
| 2.3 | Done | Будущие эпики не инвалидируются. |
| 2.4 | Done | Новый стратегический epic не обязателен; достаточно follow-up story. |
| 2.5 | Done | Приоритет высокий относительно дальнейших импортов 1С; не смешивать с VAT/order work. |
| 3.1 | Done | PRD требует уточнения, MVP не меняется. |
| 3.2 | Done | Architecture/API contract требует уточнения storage vs public projection. |
| 3.3 | Done | UX совместим: `СПОРТ` не показывается как отдельный публичный root. |
| 3.4 | Action-needed | Обновить API docs и пометить previous tech spec как superseded. |
| 4.1 | Viable | Direct Adjustment: effort Medium, risk Medium. |
| 4.2 | Not viable | Rollback старой работы не даёт пользы; нужна замена инварианта. |
| 4.3 | Not viable | MVP review не нужен. |
| 4.4 | Done | Recommended path: Direct Adjustment. |
| 5.1 | Done | Issue summary подготовлен. |
| 5.2 | Done | Epic/artifact impacts подготовлены. |
| 5.3 | Done | Recommended path подготовлен. |
| 5.4 | Done | MVP не меняется; action plan определён. |
| 5.5 | Done | Handoff: Developer для implementation, PO/SM для story/status registration. |
| 6.1 | Done | Checklist завершён для batch proposal. |
| 6.2 | Done | Proposal проверен на связность. |
| 6.3 | Done | Proposal утверждён пользователем 2026-05-03. |
| 6.4 | Done | `sprint-status.yaml` обновлён: добавлена story `category-tree-root-cause-fix: ready-for-dev`. |
| 6.5 | Done | Handoff зафиксирован: Developer agent получает story `category-tree-root-cause-fix.md`. |

## 6. Implementation Handoff

### Scope Classification

Moderate.

Изменение достаточно большое для отдельной story/dev-task, но не требует PM/Architect replan. Нужна координация PO/SM только для регистрации работы в sprint artifacts, если команда ведёт её через `sprint-status.yaml`.

### Route

- Product Owner / Scrum Master: зарегистрировать follow-up story/dev-task после approval.
- Developer agent: выполнить backend/frontend изменения по approved spec.
- Reviewer/QA: проверить импорт на пустой БД, API, UI `/catalog` и главную quick links.

### Success Criteria

- После полного импорта `groups.xml + goods.xml` категория `СПОРТ` существует в БД как root.
- `/api/v1/categories-tree/` возвращает публичные категории как детей `СПОРТ`, без самого `СПОРТ`, placeholder и `Без категории`.
- Unknown `category_id` не создаёт публичную `Категория <uuid>`.
- Repair command в dry-run показывает повреждения, а в execute исправляет их без CASCADE-удаления полезных товаров.
- Главная и `/catalog` показывают одинаковый публичный набор разделов.
- Повторная перезаливка в пустую БД не воспроизводит UUID-root категории.

### Verification Plan

Backend:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest apps/products -m unit
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest apps/products -m integration
```

Manual/API:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend python manage.py fix_category_tree_public_roots --dry-run
curl http://localhost:8001/api/v1/categories-tree/
curl "http://localhost:8001/api/v1/products/visible-categories/?in_stock=true"
```

Frontend:

```bash
docker compose --env-file .env -f docker/docker-compose.yml restart frontend
```

Проверить:

- `/catalog`
- главная quick links
- переходы по `?category={slug}`
- breadcrumbs, где `СПОРТ` должен оставаться скрытым в публичном UI.

## 7. Approval Gate

Статус proposal: approved.

После approval выполнены workflow-артефакты маршрутизации:

- `sprint-status.yaml` обновлён;
- trigger spec переведена в `ready-for-dev`;
- previous spec помечена как superseded;
- создана story/dev-task `category-tree-root-cause-fix.md`;
- кодовые изменения не выполнялись в рамках approval gate.

Утверждённое решение: Direct Adjustment, передать в Developer agent как отдельную moderate bugfix story.

## 8. Workflow Completion

- Issue addressed: публичное дерево категорий после полной заливки 1С в пустую БД показывает UUID-placeholder roots и не хранит `СПОРТ`.
- Change scope: Moderate.
- Artifacts modified: sprint change proposal, trigger tech spec, superseded previous tech spec, new story/dev-task, sprint status.
- Routed to: Developer agent for implementation; PO/SM tracking через `sprint-status.yaml`.
