---
title: "Каталог — сортировка категорий и скрытие пустых"
type: "bugfix"
created: "2026-04-30"
status: "done"
baseline_commit: "0c898ec9e75236e892c88f3ea90e918a4b658b22"
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** После импорта из 1С в сайдбаре каталога появляется категория «Без категории» (slug `uncategorized`) без видимых товаров — все её товары имеют нулевой остаток. Категории не отсортированы. При активных фильтрах (бренд, цена, наличие) пустые категории остаются видимыми.

**Approach:** Добавить аннотацию `in_stock_count` в CategoryTreeSerializer; добавить backend-action `visible-categories` на ProductViewSet (применяет тот же pipeline фильтрации без `category_id`, возвращает ID видимых категорий + их предков); на фронтенде — рекурсивная сортировка по алфавиту, три состояния видимости sidebar (initial / loading / filtered / fallback) и скрытие категорий без видимых товаров без сброса expanded-state.

## Boundaries & Constraints

**Always:**
- Сортировать все уровни дерева рекурсивно (корень + children)
- Slug `uncategorized` всегда последним независимо от имени
- Родительская категория остаётся видимой если хотя бы один её потомок виден
- `visible-categories` endpoint использует тот же pipeline фильтрации товаров что и список товаров, но **без `category_id`** — чтобы не сужать sidebar до активной ветки
- `in_stock_count` считать по прямым товарам категории (не потомкам), аналогично `products_count`
- При ошибке запроса `visible-categories` (5xx / network) sidebar показывает всё дерево без скрытия категорий и без блокировки навигации
- Scope: только `(blue)` каталог — `(electric)` каталог не поддерживается и будет исключён из проекта; никаких изменений туда не вносить

**Never:**
- Не удалять категорию «Без категории» из базы данных
- Не изменять схему модели `Category`
- Не скрывать категории на основе пагинированных результатов продуктов (ненадёжно)
- Не допускать заметный flash пустых категорий до завершения visibility-запроса
- Не сбрасывать expanded-state дерева при пересчёте видимости

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|---|---|---|---|
| Начальная загрузка, inStock=true | `in_stock_count=0` у «Без категории» | «Без категории» не отображается | — |
| Категория только с нулевым остатком | Любая категория, `in_stock_count=0` | Скрыта из сайдбара | — |
| Начальная загрузка до ответа visible-categories | Дерево загружено, endpoint pending | Пустые категории не мелькают; первичная фильтрация по `in_stock_count` или deferred render | При ошибке endpoint → показать всё дерево |
| Фильтр по бренду, активна категория A | `brand=X` выбран, `category_id` установлен | Скрыты категории без товаров бренда X; sidebar не ограничивается только веткой A | Ошибка endpoint → показать всё дерево |
| Родитель без прямых товаров, дочерняя видима | `parent.in_stock_count=0`, child виден | Родитель остаётся виден | — |
| Все категории скрыты по текущим фильтрам | `visible-categories` вернул пустой набор | Вместо дерева отображается текст «Нет категорий» | — |
| `inStock=false` | Фильтр наличия снят | Категории с товарами (даже нулевой остаток) не скрываются | — |

</frozen-after-approval>

## Code Map

- `backend/apps/products/views.py:227-241` — `CategoryTreeViewSet.get_queryset()` — добавить аннотацию `in_stock_count`
- `backend/apps/products/serializers.py:832-840` — `CategoryTreeSerializer.get_children()` — добавить аннотацию `in_stock_count`
- `backend/apps/products/serializers.py:811-831` — `CategoryTreeSerializer` — добавить поле `in_stock_count`
- `backend/apps/products/views.py` — `ProductViewSet` — добавить action `visible_categories` (без `category_id`)
- `backend/apps/products/urls.py` — роутер продуктов — убедиться, что action зарегистрирован
- `backend/apps/products/tests/` — тесты для `visible-categories` action
- `frontend/src/types/api.ts` — расширить `CategoryTree` полем `in_stock_count?: number`
- `frontend/src/services/categoriesService.ts` — добавить `getVisibleCategories(filters)` (без `category_id`)
- `frontend/src/services/__tests__/categoriesService.test.ts` — тест `getVisibleCategories` и очистки `category_id`
- `frontend/src/app/(blue)/catalog/page.tsx:426-469` — `fetchCategories` — вызов `sortCategoryTree`
- `frontend/src/app/(blue)/catalog/page.tsx:559-610` — `fetchProducts` — вызов `getVisibleCategories` и обновление visibility state
- `frontend/src/app/(blue)/catalog/page.tsx:223-293` — `CategoryTree` — prop `visibleIds` и логика скрытия
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — тесты сортировки, скрытия, fallback, empty-state

## Tasks & Acceptance

**Execution:**

- [x] `backend/apps/products/serializers.py` -- В `CategoryTreeSerializer` добавить `in_stock_count = serializers.IntegerField(read_only=True)` в `fields` и аннотацию `in_stock_count=Count("products", filter=Q(products__is_active=True) & Q(products__variants__stock_quantity__gt=0), distinct=True)` в `get_children` -- поле нужно на всех уровнях дерева

- [x] `backend/apps/products/views.py` -- В `CategoryTreeViewSet.get_queryset()` добавить `in_stock_count=Count("products", filter=Q(products__is_active=True) & Q(products__variants__stock_quantity__gt=0), distinct=True)` в `.annotate(...)` -- аннотирует корневые категории

- [x] `backend/apps/products/views.py` -- В `ProductViewSet` добавить `@action(detail=False, methods=['get'], url_path='visible-categories')`: взять текущий queryset, применить `ProductFilter` ко всем параметрам **кроме `category_id`**, извлечь `values_list('category_id', flat=True).distinct()`, добавить ancestor ID через цепочку `Category.parent`, вернуть `{"category_ids": [...]}` -- без `category_id` endpoint отражает глобальные фильтры, не сужает sidebar

- [x] `backend/apps/products/tests/` -- Добавить тесты для `visible-categories`: корректная фильтрация по `brand`, `search`, `min_price/max_price`, `in_stock`; ancestor inclusion; поведение при `category_id` в params (должен игнорироваться); пустой результат -- покрывает ключевые ветки действия

- [x] `frontend/src/types/api.ts` -- Расширить тип `CategoryTree` опциональным полем `in_stock_count?: number` -- синхронизация типа с новым полем API

- [x] `frontend/src/services/categoriesService.ts` -- Добавить `getVisibleCategories(filters: Partial<ProductFilters>): Promise<number[]>`: вызывает `GET /api/v1/products/visible-categories/` с теми же query-params что и products list, но **обязательно удаляет `category_id`** перед отправкой -- service инкапсулирует очистку параметра

- [x] `frontend/src/app/(blue)/catalog/page.tsx` -- Добавить `sortCategoryTree(nodes: CategoryNode[]): CategoryNode[]` — рекурсивно сортирует по `label` (`localeCompare 'ru'`), slug `uncategorized` всегда последний; вызвать в `fetchCategories` после `mapCategoryTreeNode` -- исправляет порядок

- [x] `frontend/src/app/(blue)/catalog/page.tsx` -- Добавить state `sidebarVisibility: { state: 'initial' | 'loading' | 'filtered' | 'fallback', ids: Set<number> | null }`; в конце `fetchProducts` вызвать `getVisibleCategories(currentFilters)`: при успехе → `filtered`; при ошибке → `fallback` (ids=null); до первого ответа использовать `in_stock_count` / `products_count` для первичной фильтрации (не допуская flash) -- явно различает состояния, избегает flash и fallback-блокировок

- [x] `frontend/src/app/(blue)/catalog/page.tsx` -- В `CategoryTree` добавить optional prop `visibleIds?: Set<number> | null`; узел скрывается (без удаления из дерева, через `hidden` или `display:none`) если `visibleIds !== null && !visibleIds.has(node.id) && !hasVisibleDescendant(node, visibleIds)`; если нет ни одного видимого root node — рендерить `<p>Нет категорий</p>` вместо дерева -- скрытие без сброса expanded-state

- [x] `frontend/src/services/__tests__/categoriesService.test.ts` -- Тест `getVisibleCategories`: проверить что `category_id` удалён из запроса, что ответ возвращает массив number -- контракт service

- [x] `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` -- Тесты: сортировка А→Я; `uncategorized` последним; скрытие категории с `in_stock_count=0`; сохранение родителя при видимом потомке; graceful degradation при ошибке visible-categories; empty-state «Нет категорий» -- полное покрытие сценариев из матрицы

- [x] Scope confirmation -- Убедиться что `(electric)/catalog/page.tsx` **не затронут**; тема (electric) не поддерживается и будет исключена из проекта -- предотвращает случайное внесение изменений в deprecated-модуль

**Acceptance Criteria:**

- Given `/catalog` загружен с `inStock=true`, when API вернул категорию `uncategorized` с `in_stock_count=0`, then эта категория не видна в сайдбаре
- Given список категорий, when страница загружена, then категории отсортированы А→Я, «Без категории» — последней среди видимых
- Given пользователь применил фильтр бренда, when `visible-categories` вернул список ID без категории X, then категория X скрыта; sidebar не ограничивается только веткой активной категории
- Given выбрана активная категория A и применён фильтр бренда, when sidebar visibility рассчитывается через visible-categories, then список видимых категорий определяется прочими фильтрами и не ограничивается только веткой A
- Given родительская категория с `in_stock_count=0` и хотя бы одной видимой дочерней, when фильтры применены, then родитель остаётся виден
- Given `/catalog` загружается с `inStock=true`, when categories tree загружен раньше ответа `visible-categories`, then пустые категории не должны заметно появляться и затем исчезать в sidebar
- Given текущие фильтры исключают все категории, when visibility logic не находит ни одного видимого root node, then вместо дерева отображается текст «Нет категорий»
- Given `visible-categories` endpoint вернул ошибку, when запрос провалился, then весь sidebar отображается без скрытия категорий и без блокировки навигации по дереву
- Given `inStock=false`, when загрузка или смена фильтров, then категории с товарами (даже нулевой остаток) не скрываются

## Spec Change Log

**2026-04-30** — review by alex: добавлены constraint об исключении `category_id` из `visible-categories`, явные состояния sidebar visibility, no-flash requirement, empty-state «Нет категорий», тесты backend + frontend, уточнён fallback AC, зафиксирован scope (blue only).

## Design Notes

**Ancestor resolution в `visible-categories` (без `category_id`):**
```python
# Исключить category_id перед фильтрацией
params = request.query_params.copy()
params.pop('category_id', None)
filtered_qs = ProductFilter(params, queryset=self.get_queryset()).qs
leaf_ids = set(filtered_qs.values_list('category_id', flat=True))
all_ids = set(leaf_ids)
cats = Category.objects.filter(id__in=leaf_ids).select_related('parent__parent__parent')
for cat in cats:
    c = cat.parent
    while c:
        all_ids.add(c.id)
        c = c.parent
return Response({"category_ids": list(all_ids)})
```

**Frontend sort:**
```typescript
function sortCategoryTree(nodes: CategoryNode[]): CategoryNode[] {
  return [...nodes]
    .sort((a, b) => {
      if (a.slug === 'uncategorized') return 1;
      if (b.slug === 'uncategorized') return -1;
      return a.label.localeCompare(b.label, 'ru');
    })
    .map(n => ({ ...n, children: n.children ? sortCategoryTree(n.children) : undefined }));
}
```

**No-flash стратегия при начальной загрузке:** до получения ответа `visible-categories` использовать первичную фильтрацию дерева по `in_stock_count === 0` (или `products_count === 0`), чтобы категории без товаров не рендерились с первого кадра. После получения ответа переключиться на `filtered` state.

**Скрытие без мутации дерева:** скрывать узлы через CSS `visibility: hidden` / `display: none` (или conditional render без смены ключей), но не пересоздавать массив `nodes` и не изменять `expandedKeys` — иначе пользователь потеряет открытые ветки.

## Verification

**Commands:**

- `cd frontend && npm run test -- src/services/__tests__/categoriesService.test.ts` -- expected: all tests pass
- `cd frontend && npm run test -- "src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx"` -- expected: all tests pass
- `cd frontend && npm run build` -- expected: no TypeScript errors
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest apps/products -m "unit or integration" -x -q` -- expected: all tests pass

**Manual checks:**

- `/catalog` default (inStock=true): «Без категории» не видна, остальные отсортированы А→Я
- `/catalog?brand=X`: sidebar скрывает категории без товаров бренда X, активная категория не сужает список
- `/catalog` с inStock=false: все категории с товарами видны
- Фильтр исключающий все товары: отображается «Нет категорий»
- Simulate 500 от `visible-categories`: sidebar показывает полное дерево, навигация не сломана

## Suggested Review Order

**Backend API — видимые категории**

- Главная точка входа: action полностью изолирует sidebar от `category_id` через двойное удаление
  [`views.py:196`](../../../backend/apps/products/views.py#L196)

- Аннотация `in_stock_count` корневых категорий с `distinct=True` для корректного счёта
  [`views.py:284`](../../../backend/apps/products/views.py#L284)

- Сериализатор: поле `in_stock_count` и та же аннотация для дочерних категорий
  [`serializers.py:818`](../../../backend/apps/products/serializers.py#L818)

- Рекурсивный обход предков через `select_related` (до 4 уровней), расширяет `all_ids`
  [`views.py:210`](../../../backend/apps/products/views.py#L210)

**Frontend — слой данных**

- `getVisibleCategories`: удаляет `category_id` деструктуризацией до отправки запроса
  [`categoriesService.ts:86`](../../../frontend/src/services/categoriesService.ts#L86)

- Тип `CategoryTree` расширен опциональным `in_stock_count` для маппинга на фронте
  [`api.ts:120`](../../../frontend/src/types/api.ts#L120)

**Frontend — логика видимости sidebar**

- `sortCategoryTree`: рекурсивная сортировка А→Я, slug `uncategorized` всегда последний
  [`page.tsx:79`](../../../frontend/src/app/(blue)/catalog/page.tsx#L79)

- `hasVisibleDescendant`: рекурсивный хелпер — родитель виден если потомок в `visibleIds`
  [`page.tsx:88`](../../../frontend/src/app/(blue)/catalog/page.tsx#L88)

- `sidebarVisibleIds` state: `null` = показывать всё (fallback и начальное состояние)
  [`page.tsx:347`](../../../frontend/src/app/(blue)/catalog/page.tsx#L347)

- No-flash pre-fill: до ответа `visible-categories` прячем категории с `inStockCount=0`
  [`page.tsx:462`](../../../frontend/src/app/(blue)/catalog/page.tsx#L462)

- Параллельный вызов в `fetchProducts`: `getVisibleCategories` идёт рядом с `getAll`
  [`page.tsx:635`](../../../frontend/src/app/(blue)/catalog/page.tsx#L635)

- `CategoryTree`: фильтрует по `visibleIds`, "Нет категорий" при пустом root, рекурсивно передаёт `visibleIds`
  [`page.tsx:247`](../../../frontend/src/app/(blue)/catalog/page.tsx#L247)

- Patch: чекбокс «В наличии» мгновенно сбрасывает `sidebarVisibleIds` при выключении
  [`page.tsx:1080`](../../../frontend/src/app/(blue)/catalog/page.tsx#L1080)

**Тесты**

- Backend тесты: фильтрация по бренду, цене, `in_stock`, игнорирование `category_id`, предки
  [`test_visible_categories.py:20`](../../../backend/apps/products/tests/test_visible_categories.py#L20)

- Service тесты: `category_id` не попадает в URL, ответ возвращает массив чисел
  [`categoriesService.test.ts:118`](../../../frontend/src/services/__tests__/categoriesService.test.ts#L118)

- UI тесты: скрытие пустых, «Нет категорий», graceful degradation, видимость родителя
  [`CatalogPage.test.tsx:451`](../../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L451)
