---
title: "Каталог — скрытие брендов без товаров в наличии"
type: "feature"
created: "2026-05-06"
status: "draft"
baseline_commit: "e4f2ae0181a9341c008dae7f0370f37944e20b30"
context:
  - "{project-root}/_bmad-output/implementation-artifacts/tech-spec/tech-spec-catalog-category-sort-and-hide-empty.md"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Фильтр «Бренд» в сайдбаре каталога (`/catalog`) отображает все активные бренды из БД (`BrandViewSet` → `Brand.objects.active()`), включая те, по которым нет ни одного товара в наличии (`Product.is_active=True` + `ProductVariant.stock_quantity > 0`). Пользователь видит «мусорные» бренды, выбор которых либо даёт пустой грид (если включён `inStock=true`), либо показывает out-of-stock товары без возможности заказа. UX-несимметрия с уже реализованным скрытием пустых категорий (`visible-categories` endpoint).

**Approach:** Применить тот же двухуровневый паттерн, что для категорий:

1. **Глобальный гейт** — query-параметр `has_stock=true` в существующий `BrandViewSet.list` (`backend/apps/products/views.py:354-361`). Бренд считается «in-stock» если у него есть хотя бы один `Product.is_active=True` с `ProductVariant.stock_quantity > 0`. Применяется при первичной загрузке списка брендов в `brandsService.getAll(...)`. Бренды без товаров в наличии не попадают в фильтр вообще.
2. **Динамическое сужение по активным фильтрам** — новый action `visible_brands` на `ProductViewSet` (симметричен `visible_categories`). Возвращает `{"brand_ids": [...]}` — ID брендов, имеющих товары при текущих фильтрах каталога. Параметр `brand` намеренно удаляется из запроса (как `category_id` для `visible-categories`), чтобы фильтр не сужал сам себя при множественном выборе. Frontend применяет эти ID для скрытия чекбоксов в сайдбаре по аналогии с `sidebarVisibleIds` для категорий.

Scope — только `(blue)/catalog`. `(electric)/electric/catalog` deprecated и будет исключён из проекта (см. предыдущий tech-spec); никаких изменений туда не вносить.

## Boundaries & Constraints

**Always:**
- «Бренд в наличии» = существует `Product` с `is_active=True` И связанный с этим Product `ProductVariant` с `stock_quantity > 0`. Использовать `Exists` subquery, не `JOIN` через `Count` — иначе декартово произведение `products × variants` испортит результат (см. паттерн в `views.py:102` для `has_stock` аннотации `Product`).
- В `BrandViewSet.get_queryset()` параметр `has_stock` парсить как boolean (`true`/`1` → True, всё остальное → False; отсутствие параметра → не применять фильтр для backward compat).
- `BrandViewSet.has_stock=true` НЕ затрагивает action `featured` (избранные бренды на главной странице) — он остаётся прежним. Гейт применяется только в обычном `list`.
- В `visible_brands` action удалять `brand` параметр из `query_params.copy()` ДО применения `ProductFilter` — симметрично `visible_categories.pop('category_id')`. Возвращать `{"brand_ids": [int, ...]}` через `values_list('brand_id', flat=True).distinct()` — без расширения предками (бренды плоские, не иерархичны).
- На фронтенде: `brandsService.getAll(opts?: { has_stock?: boolean })` — опциональный параметр, по умолчанию `has_stock` НЕ отправляется (backward compat для других потребителей `getAll`).
- На странице каталога `(blue)/catalog/page.tsx`: первичная загрузка через `brandsService.getAll({ has_stock: true })`; в `fetchProducts` **при `filters.in_stock === true`** параллельно с `getVisibleCategories` вызывать `getVisibleBrands(filters)`; результат складывать в `sidebarVisibleBrandIds: Set<number> | null` (null = показывать все). **При `inStock=false` `visible-brands` НЕ запрашивается** — `setSidebarVisibleBrandIds(null)` без сетевого вызова. Обоснование (renegotiated 2026-05-06, v1.2): при выключенном `inStock` грид показывает out-of-stock товары; динамическое сужение чекбоксов брендов через `visible-brands` создавало бы парадокс «фильтр in-stock выключен, но бренды скрыты по in-stock». Симметрия с `getVisibleCategories` нарушена осознанно — категории всегда полные, бренды первично гейтированы.
- Скрытие чекбоксов брендов: если `sidebarVisibleBrandIds !== null && !sidebarVisibleBrandIds.has(brand.id)` → чекбокс не рендерится (по аналогии с `visibleIds` для категорий). НЕ удаляется из `brands` state — только из визуального вывода.
- При ошибке `getVisibleBrands` (5xx / network) → `sidebarVisibleBrandIds = null` (fallback: показать весь загруженный список). Никакой блокировки UI и никаких toast-ошибок.
- При снятии чекбокса «В наличии» (`inStock=false`) → `sidebarVisibleBrandIds = null` мгновенно (зеркально категориям, см. `page.tsx:1080`). При этом базовый список брендов остаётся отфильтрованным через `has_stock=true` — это сознательный компромисс: «нет товара в наличии = нет бренда в фильтре» применяется всегда, независимо от чекбокса `inStock` грида товаров. Если бизнес захочет снимать гейт при `inStock=false`, это отдельное решение и open question.
- Уже выбранный пользователем бренд (`selectedBrandIds`), оказавшийся «невидимым» по visible-brands, остаётся в `selectedBrandIds` (selection не сбрасывается), но чекбокс не рендерится — отображается только пока он находится в `visibleBrandIds` ИЛИ `selectedBrandIds.has(brand.id)`. Это предотвращает «исчезновение» только что выбранного бренда из UI.

**Never:**
- Не вводить `has_stock` или `visible_brands` в `BrandViewSet.featured` action — кэшируется, изменение слома кэша.
- Не реализовывать `has_stock` через `Brand.objects.annotate(Count('products__variants__stock_quantity'))` — это N+1 / декартово произведение. Только `Exists` subquery.
- Не сбрасывать `selectedBrandIds` при изменении `sidebarVisibleBrandIds` — пользователь увидит самопроизвольное снятие фильтров.
- Не добавлять предков (как для категорий) — модель `Brand` плоская, иерархии нет.
- Не вносить никаких изменений в `(electric)/electric/catalog/page.tsx` — модуль исключён из проекта.
- Не менять контракт `BrandFeaturedSerializer` и endpoint `/brands/featured/`.
- Не менять `Brand` модель и не добавлять миграции.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|---|---|---|---|
| Бренд `Nike` имеет 5 товаров, все варианты `stock_quantity=0` | `GET /api/v1/brands/?has_stock=true` | `Nike` НЕ в результате | — |
| Бренд `Adidas` имеет 1 товар c 1 вариантом `stock_quantity=10` | `GET /api/v1/brands/?has_stock=true` | `Adidas` в результате | — |
| `GET /api/v1/brands/` (без `has_stock`) | Backward compat | Все активные бренды (как сейчас) | — |
| `GET /api/v1/brands/?has_stock=false` | Явное отключение гейта | Все активные бренды | — |
| `GET /api/v1/products/visible-brands/?category_id=15` | Активная категория | brand_ids только тех брендов, у которых есть товары в категории 15 (с учётом дочерних) | — |
| `GET /api/v1/products/visible-brands/?brand=nike&min_price=1000` | Параметр `brand` указан, но игнорируется | brand_ids всех брендов с ценой ≥ 1000 (включая `nike`) | — |
| `GET /api/v1/products/visible-brands/` без фильтров | Глобальный запрос | brand_ids всех брендов с активными товарами в каталоге | — |
| `GET /api/v1/brands/featured/` после релиза | Featured бренды на главной | Без изменений (гейт `has_stock` НЕ применяется) | — |
| `/catalog` начальная загрузка, `inStock=true` (default) | Первичный fetch брендов | `brandsService.getAll({ has_stock: true })` → бренды без товаров в наличии не показаны | При ошибке: `brandsError` показан, чекбоксы не рендерятся |
| `/catalog?category=football` | Активная категория «Футбол» | Видны только бренды, имеющие товары категории «Футбол»; бренды только из «Хоккея» скрыты | Ошибка `visible-brands` → показать полный список из `getAll(has_stock=true)` |
| Пользователь выбрал `Nike`, затем сменил категорию на ту, где `Nike` нет | `selectedBrandIds={nike.id}`, `sidebarVisibleBrandIds` не содержит `nike.id` | Чекбокс `Nike` остаётся видимым (selected → принудительно показан); пользователь может снять его | — |
| Пользователь снял `inStock=false` в гриде | `setInStock(false)` | `sidebarVisibleBrandIds = null` (показать всё, что вернул `getAll(has_stock=true)`) | — |
| Активные фильтры исключают все товары | `visible-brands` вернул пустой массив | В сайдбаре показывается только текст «Бренды не найдены» (существующий fallback `page.tsx:1066`) | — |
| Сетевая ошибка `visible-brands` | Promise reject | `sidebarVisibleBrandIds = null`, чекбоксы из `brands` state видны полностью | warn в консоль, без toast |
| Сетевая ошибка `getAll(has_stock=true)` | Первичный fetch упал | `brandsError` показан, чекбоксы не рендерятся (текущее поведение) | — |
| `(electric)/electric/catalog` | Любое состояние | Никаких изменений | — |

</frozen-after-approval>

## Code Map

### Backend
- `backend/apps/products/views.py:342-361` — `BrandViewSet.get_queryset()` — добавить парсинг `has_stock` и `Exists` фильтр
- `backend/apps/products/views.py:362-376` — `BrandViewSet.list()` `@extend_schema` — добавить параметр `has_stock` в OpenAPI документацию
- `backend/apps/products/views.py:184-232` — `ProductViewSet.visible_categories` — образец для нового action `visible_brands`
- `backend/apps/products/views.py` (после `visible_categories`) — добавить `@action(detail=False, methods=['get'], url_path='visible-brands')`
- `backend/apps/products/tests/test_brand_api.py` — добавить тесты для `?has_stock=true`
- `backend/apps/products/tests/test_visible_categories.py` — образец → добавить рядом `test_visible_brands.py` (новый файл)

### Frontend
- `frontend/src/services/brandsService.ts:46-53` — `getAll()` — добавить опциональный параметр `{ has_stock?: boolean }`
- `frontend/src/services/brandsService.ts` (после `getFeatured`) — добавить `getVisibleBrands(filters: Partial<ProductFilters>): Promise<number[]>`
- `frontend/src/services/__tests__/brandsService.test.ts` — тесты `has_stock` параметра и `getVisibleBrands`
- `frontend/src/app/(blue)/catalog/page.tsx:357-360` — state: добавить `sidebarVisibleBrandIds: Set<number> | null`
- `frontend/src/app/(blue)/catalog/page.tsx:528-553` — `fetchBrands` — заменить `getAll()` на `getAll({ has_stock: true })`
- `frontend/src/app/(blue)/catalog/page.tsx:611-670` — `fetchProducts` — параллельно с `getVisibleCategories` вызвать `getVisibleBrands`
- `frontend/src/app/(blue)/catalog/page.tsx:1069-1079` — рендер чекбоксов брендов — фильтрация по `sidebarVisibleBrandIds` с учётом `selectedBrandIds`
- `frontend/src/app/(blue)/catalog/page.tsx:1086-1094` — чекбокс «В наличии» — добавить `setSidebarVisibleBrandIds(null)` при снятии (зеркально `setSidebarVisibleIds(null)` для категорий)
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — тесты скрытия/fallback/selection-preserve

## Tasks & Acceptance

**Execution:**

- [ ] `backend/apps/products/views.py` — В `BrandViewSet.get_queryset()` после существующего `is_featured` фильтра добавить парсинг `has_stock` (`request.query_params.get("has_stock")`, `.lower() in ("true", "1")`); при `True` применить `qs.filter(Exists(Product.objects.filter(brand=OuterRef("pk"), is_active=True, variants__stock_quantity__gt=0)))` — `Exists` исключает декартово произведение `products × variants`, это критично для производительности. Обновить `@extend_schema(parameters=[...])` действия `list` — добавить `OpenApiParameter("has_stock", OpenApiTypes.BOOL, ...)`.
- [ ] `backend/apps/products/views.py` — В `ProductViewSet` добавить action `@action(detail=False, methods=["get"], url_path="visible-brands")` с реализацией: скопировать `request.query_params`, вызвать `params.pop("brand", None)`, применить `self.filterset_class(params, queryset=self.get_queryset()).qs`, извлечь `values_list("brand_id", flat=True).distinct()`, отфильтровать `None` (товары без бренда), вернуть `Response({"brand_ids": list(brand_ids)})`. Обернуть `@extend_schema(...)` с описанием параметров (brand игнорируется, остальные применяются).
- [ ] `backend/apps/products/tests/test_brand_api.py` — Добавить тесты: бренд с 0 in-stock товарами не возвращается при `has_stock=true`; бренд с in-stock товарами возвращается; `has_stock=false` или отсутствие параметра — все активные бренды (backward compat); `has_stock=true` не нарушает `featured` action.
- [ ] `backend/apps/products/tests/test_visible_brands.py` — Новый файл по образцу `test_visible_categories.py`: фильтрация по `category_id`, `search`, `min_price/max_price`, `in_stock`; игнорирование `brand` параметра; пустой результат при исключающих фильтрах; `None` brand_id (товары без бренда) исключён.
- [ ] `frontend/src/services/brandsService.ts` — Расширить сигнатуру `getAll(opts?: { has_stock?: boolean }): Promise<Brand[]>`. Если `opts?.has_stock` определён — добавить в `params` (`has_stock: opts.has_stock`). Backward compat: вызовы без аргумента работают как сейчас. Обновить тип-аннотацию.
- [ ] `frontend/src/services/brandsService.ts` — Добавить метод `getVisibleBrands(filters: Partial<ProductFilters>): Promise<number[]>` по образцу `categoriesService.getVisibleCategories`: копировать `filters`, удалить `brand` (`delete filtersWithoutBrand.brand`), вызвать `apiClient.get<{ brand_ids: number[] }>("/products/visible-brands/", { params: filtersWithoutBrand })`, вернуть `response.data.brand_ids`.
- [ ] `frontend/src/services/__tests__/brandsService.test.ts` — Тесты: `getAll({ has_stock: true })` отправляет параметр; `getAll()` НЕ отправляет (backward compat); `getVisibleBrands` удаляет `brand` из URL; возвращает `number[]`; throws на network error.
- [ ] `frontend/src/app/(blue)/catalog/page.tsx` — Добавить state `const [sidebarVisibleBrandIds, setSidebarVisibleBrandIds] = useState<Set<number> | null>(null);` рядом с `sidebarVisibleIds`.
- [ ] `frontend/src/app/(blue)/catalog/page.tsx` — В `fetchBrands` заменить `brandsService.getAll()` на `brandsService.getAll({ has_stock: true })`. Это первичный гейт.
- [ ] `frontend/src/app/(blue)/catalog/page.tsx` — В `fetchProducts` параллельно в том же `Promise.all` добавить **conditional dispatch (v1.2)**: `filters.in_stock ? brandsService.getVisibleBrands(filters).then(ids => setSidebarVisibleBrandIds(new Set(ids))).catch(error => { console.warn(...); setSidebarVisibleBrandIds(null); }) : Promise.resolve(setSidebarVisibleBrandIds(null))`. При выключенном `inStock` сетевой запрос НЕ выполняется. Не блокировать рендер на этом запросе (как сейчас для visible-categories).
- [ ] `frontend/src/app/(blue)/catalog/page.tsx` — В рендере чекбоксов брендов (`page.tsx:1069-1079`) добавить filter: `brands.filter(b => sidebarVisibleBrandIds === null || sidebarVisibleBrandIds.has(b.id) || selectedBrandIds.has(b.id))`. Это сохраняет видимость чекбокса для уже выбранного бренда даже если он отсутствует в visible-brands. Добавить fallback-сообщение «Бренды не найдены» если итоговый список пуст и `!isBrandsLoading && !brandsError` (текущая логика уже есть, но нужно проверить, что она корректно работает после фильтрации).
- [ ] `frontend/src/app/(blue)/catalog/page.tsx` — В обработчике чекбокса «В наличии» (`page.tsx:1086-1094`) при `!e.target.checked` дополнительно вызвать `setSidebarVisibleBrandIds(null)` (зеркально `setSidebarVisibleIds(null)`).
- [ ] `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — Тесты: бренд без товаров в наличии скрыт при первичной загрузке; бренд скрыт при активной категории, где его нет; уже выбранный бренд НЕ исчезает при изменении фильтра; при ошибке `visible-brands` показаны все бренды из первичного `getAll`; при пустом visible-brands и пустом selection — fallback «Бренды не найдены»; снятие `inStock` сбрасывает `sidebarVisibleBrandIds = null`.
- [ ] Scope confirmation — Убедиться что `(electric)/electric/catalog/page.tsx` НЕ затронут; модуль deprecated и будет исключён из проекта.

**Acceptance Criteria:**

- Given бренд `Nike` имеет 0 товаров с `variant.stock_quantity > 0`, when `/catalog` загружен с дефолтными фильтрами, then `Nike` НЕ отображается в фильтре брендов сайдбара.
- Given бренд `Adidas` имеет ≥1 товар с `variant.stock_quantity > 0`, when `/catalog` загружен, then `Adidas` отображается в фильтре брендов.
- Given пользователь выбрал категорию «Футбол», when `visible-brands` вернул только `[Nike, Puma]`, then в сайдбаре видны только `Nike` и `Puma`; остальные бренды скрыты, но не удалены из state.
- Given пользователь выбрал бренд `Nike`, then сменил категорию на ту, где у `Nike` нет товаров, when `sidebarVisibleBrandIds` не содержит `Nike.id`, then чекбокс `Nike` всё равно отрисован и `selectedBrandIds` не сбрасывается.
- Given пользователь снял чекбокс «В наличии», when `setInStock(false)`, then `sidebarVisibleBrandIds === null` и в сайдбаре отображены все бренды из первичного `getAll(has_stock=true)`.
- Given сетевая ошибка `visible-brands`, when promise reject, then `sidebarVisibleBrandIds = null` и сайдбар отображает полный список из первичного `getAll`.
- Given `GET /api/v1/brands/featured/`, when запрос на главной странице, then ответ не зависит от `has_stock` гейта (поведение неизменно).
- Given `GET /api/v1/brands/` без `has_stock`, when запрос делает другой клиент API, then возвращены все активные бренды (backward compat).
- Given `GET /api/v1/products/visible-brands/?brand=nike&category_id=15`, when параметр `brand` явно указан, then он игнорируется backend'ом — результат содержит ID всех брендов с товарами в категории 15.
- Given активные фильтры исключают все товары каталога, when `visible-brands` вернул пустой массив и нет выбранных брендов, then в сайдбаре отображено «Бренды не найдены».
- Given `(electric)/electric/catalog/page.tsx` существует в кодовой базе, when выполнены все задачи спеки, then файл не изменён, тесты electric-каталога не затронуты.

## Spec Change Log

**2026-05-06** — initial draft (alex): гибридный подход (has_stock гейт + visible-brands action), scope=(blue), preserve-selection поведение, симметрия с visible-categories.

## Design Notes

### Backend — `BrandViewSet.has_stock` через `Exists`

```python
from django.db.models import Exists, OuterRef
from .models import Product

def get_queryset(self):
    qs = Brand.objects.active().order_by("name")
    if self.action != "featured":
        is_featured = self.request.query_params.get("is_featured")
        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured.lower() in ("true", "1"))

        has_stock = self.request.query_params.get("has_stock")
        if has_stock is not None and has_stock.lower() in ("true", "1"):
            in_stock_products = Product.objects.filter(
                brand=OuterRef("pk"),
                is_active=True,
                variants__stock_quantity__gt=0,
            )
            qs = qs.filter(Exists(in_stock_products))
    return qs
```

`Exists` гарантирует один subquery без `JOIN` и без декартова произведения `products × variants`. Distinct не нужен, поскольку `Exists` возвращает boolean.

### Backend — `visible_brands` action

```python
@action(detail=False, methods=["get"], url_path="visible-brands")
def visible_brands(self, request: Request) -> Response:
    params = request.query_params.copy()
    params.pop("brand", None)  # симметрично visible_categories.pop('category_id')
    filterset = self.filterset_class(params, queryset=self.get_queryset())
    filtered_qs = filterset.qs
    brand_ids = list(
        filtered_qs.exclude(brand_id__isnull=True)
                   .values_list("brand_id", flat=True)
                   .distinct()
    )
    return Response({"brand_ids": brand_ids})
```

### Frontend — `brandsService.getAll` с опциональным `has_stock`

```typescript
async getAll(opts?: { has_stock?: boolean }): Promise<Brand[]> {
  const params: Record<string, unknown> = { page_size: DEFAULT_PAGE_SIZE };
  if (opts?.has_stock !== undefined) {
    params.has_stock = opts.has_stock;
  }
  const response = await apiClient.get<PaginatedResponse<Brand>>('/brands/', { params });
  return response.data.results.map(this.normalizeBrand);
}
```

### Frontend — `brandsService.getVisibleBrands`

```typescript
async getVisibleBrands(filters: Partial<ProductFilters>): Promise<number[]> {
  const filtersWithoutBrand = { ...filters };
  delete filtersWithoutBrand.brand;
  const response = await apiClient.get<{ brand_ids: number[] }>(
    '/products/visible-brands/',
    { params: filtersWithoutBrand }
  );
  return response.data.brand_ids;
}
```

### Frontend — preserve-selection при рендере чекбоксов

```typescript
{!isBrandsLoading && !brandsError && (() => {
  const visibleBrands = brands.filter(b =>
    sidebarVisibleBrandIds === null
    || sidebarVisibleBrandIds.has(b.id)
    || selectedBrandIds.has(b.id)
  );
  if (visibleBrands.length === 0) {
    return <p className="text-xs text-gray-400">Бренды не найдены</p>;
  }
  return visibleBrands.map(brand => (
    <Checkbox key={brand.id} ... />
  ));
})()}
```

Логика `|| selectedBrandIds.has(b.id)` критична: без неё пользователь, выбравший `Nike` и сменивший категорию, увидит исчезновение чекбокса — это плохой UX и нарушение принципа preserved-selection.

### Параллельный fetch в `fetchProducts`

```typescript
const [response] = await Promise.all([
  productsService.getAll(filters),
  categoriesService.getVisibleCategories(filters)
    .then(ids => setSidebarVisibleIds(new Set(ids)))
    .catch(() => setSidebarVisibleIds(null)),
  brandsService.getVisibleBrands(filters)
    .then(ids => setSidebarVisibleBrandIds(new Set(ids)))
    .catch(() => setSidebarVisibleBrandIds(null)),
]);
```

Оба visibility-запроса не блокируют рендер товаров: они обновляют только sidebar visibility state.

### Open Questions (вне scope этого тех-спека)

- Должен ли гейт `has_stock=true` сниматься при `inStock=false` в гриде товаров? Сейчас спека фиксирует «гейт всегда применяется в сайдбаре, независимо от чекбокса грида». Альтернатива — повторно вызывать `getAll({ has_stock: false })` при снятии `inStock`. Решение отложено до feedback от UX.
- Кэширование `visible-brands` ответа (например, 60 сек по фильтрам) — оптимизация на будущее, не входит в первую итерацию.

## Verification

**Commands:**

- `cd frontend && npm run test -- src/services/__tests__/brandsService.test.ts` — все тесты проходят
- `cd frontend && npm run test -- "src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx"` — все тесты проходят
- `cd frontend && npm run build` — нет TypeScript ошибок
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest apps/products/tests/test_brand_api.py apps/products/tests/test_visible_brands.py -m "unit or integration" -x -q` — все тесты проходят
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest apps/products -m "unit or integration" -x -q` — регрессий нет

**Manual checks:**

- `/catalog` default (`inStock=true`): бренды без товаров в наличии не видны; бренды с товарами видны
- `/catalog?category=football`: видны только бренды с товарами в «Футболе»
- `/catalog?brand=nike` затем смена категории на ту, где `Nike` нет → чекбокс `Nike` остаётся
- Снятие `inStock` → весь список из первичного `getAll(has_stock=true)` восстанавливается
- Активная комбинация фильтров, исключающая все товары → «Бренды не найдены»
- Simulate 500 от `/products/visible-brands/` → сайдбар показывает полный список, навигация не сломана
- `/api/v1/brands/featured/` (главная) — содержимое без изменений

## Suggested Review Order

**Backend API — гейт has_stock и visible_brands**

- Ключевая точка: `Exists` subquery на `Brand.products` исключает декартово произведение. [`views.py:354`](../../../backend/apps/products/views.py#L354)
- `visible_brands` action: симметрия с `visible_categories`, удаление `brand` из params. [`views.py:200`](../../../backend/apps/products/views.py#L200) (образец)
- OpenAPI документация `has_stock` в `@extend_schema`. [`views.py:362`](../../../backend/apps/products/views.py#L362)

**Frontend — слой данных**

- `brandsService.getAll` с опциональным `has_stock`. [`brandsService.ts:46`](../../../frontend/src/services/brandsService.ts#L46)
- `brandsService.getVisibleBrands`: удаляет `brand` до отправки. [`categoriesService.ts:87`](../../../frontend/src/services/categoriesService.ts#L87) (образец)

**Frontend — логика видимости sidebar**

- `sidebarVisibleBrandIds` state: `null` = показывать всё. [`page.tsx:355`](../../../frontend/src/app/(blue)/catalog/page.tsx#L355) (образец `sidebarVisibleIds`)
- Параллельный fetch в `fetchProducts`. [`page.tsx:643`](../../../frontend/src/app/(blue)/catalog/page.tsx#L643)
- Preserve-selection при рендере чекбоксов. [`page.tsx:1069`](../../../frontend/src/app/(blue)/catalog/page.tsx#L1069)
- Сброс `sidebarVisibleBrandIds` при снятии `inStock`. [`page.tsx:1086`](../../../frontend/src/app/(blue)/catalog/page.tsx#L1086)

**Тесты**

- Backend: `?has_stock=true` фильтрация, backward compat, featured неизменён. `tests/test_brand_api.py`
- Backend: `visible-brands` фильтры/игнорирование brand/пустой результат. `tests/test_visible_brands.py` (новый файл)
- Service тесты: `has_stock` параметр, `getVisibleBrands` без `brand` в URL. `__tests__/brandsService.test.ts`
- UI тесты: скрытие out-of-stock, preserve-selection, fallback на ошибку, empty-state. `__tests__/CatalogPage.test.tsx`

## Change Log

| Date | Version | Description | Author |
|---|---:|---|---|
| 2026-05-06 | 1.0 | Tech-spec составлен и утверждён (status=draft, baseline_commit=e4f2ao). | Cascade |
| 2026-05-06 | 1.2 | Renegotiated frozen block по итогам code review: `getVisibleBrands` зовётся ТОЛЬКО при `inStock=true` (conditional dispatch). Симметрия с `getVisibleCategories` нарушена осознанно — обоснование добавлено в Boundaries. Обновлён Tasks-чеклист `fetchProducts`. | Claude Opus 4.7 (bmad-code-review) |
