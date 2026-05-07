# Story: Каталог — скрытие брендов без товаров в наличии

Status: in-progress

Source:
- `_bmad-output/implementation-artifacts/tech-spec/tech-spec-catalog-hide-out-of-stock-brands.md`
- `_bmad-output/implementation-artifacts/tech-spec/tech-spec-catalog-category-sort-and-hide-empty.md` (контекст-симметрия паттерна `visible-categories`)

Baseline commit: `e4f2ae0181a9341c008dae7f0370f37944e20b30`

## Story

As a **покупатель FREESPORT, использующий каталог `(blue)/catalog`**,
I want **видеть в фильтре «Бренд» только бренды, у которых реально есть товары в наличии (с учётом активных фильтров каталога)**,
so that **выбор бренда никогда не приводит к пустому гриду или к показу out-of-stock товаров без возможности заказа, а UX фильтра брендов симметричен уже реализованному скрытию пустых категорий**.

## Acceptance Criteria

1. **AC1 (гейт `has_stock=true`, бренд без in-stock товаров):** Given бренд `Nike` имеет ≥1 активный товар, но у всех связанных `ProductVariant.stock_quantity = 0`, when выполняется `GET /api/v1/brands/?has_stock=true`, then `Nike` отсутствует в результате.
2. **AC2 (гейт `has_stock=true`, бренд с in-stock товарами):** Given бренд `Adidas` имеет ≥1 активный товар (`Product.is_active=True`) с ≥1 вариантом, у которого `stock_quantity > 0`, when выполняется `GET /api/v1/brands/?has_stock=true`, then `Adidas` присутствует в результате.
3. **AC3 (backward compatibility списка брендов):** Given `GET /api/v1/brands/` без параметра `has_stock` (либо `has_stock=false`), when запрос делает существующий клиент, then возвращаются все активные бренды (как сейчас) — гейт не применяется.
4. **AC4 (`featured` не затронут):** Given реализован гейт `has_stock`, when выполняется `GET /api/v1/brands/featured/` (с любыми query-параметрами), then ответ идентичен прежнему контракту, кэшируется по существующим правилам и `has_stock` не применяется.
5. **AC5 (новый action `visible-brands`, базовый случай):** Given в каталоге несколько брендов с in-stock товарами в разных категориях, when выполняется `GET /api/v1/products/visible-brands/?category_id=15`, then ответ имеет вид `{"brand_ids": [...]}` и содержит ID только тех брендов, у которых есть активные товары в категории 15 (с учётом дочерних категорий через `filter_category_id`).
6. **AC6 (`visible-brands` игнорирует параметр `brand`):** Given `GET /api/v1/products/visible-brands/?brand=nike&min_price=1000`, when параметр `brand` присутствует в запросе, then он игнорируется backend'ом (удаляется до применения `ProductFilter`); результат содержит ID всех брендов с товарами по фильтру `min_price=1000`, включая `nike`.
7. **AC7 (`visible-brands` исключает товары без бренда):** Given товар без бренда (`brand_id IS NULL`) попадает под текущие фильтры, when выполняется `visible-brands`, then `null` отсутствует в `brand_ids` (только реальные ID).
8. **AC8 (frontend гейт первичной загрузки):** Given пользователь открывает `/catalog`, when выполняется первичный `fetchBrands`, then `brandsService.getAll({ has_stock: true })` вызывается с параметром `has_stock=true`, и в сайдбаре никогда не появляются бренды без товаров в наличии.
9. **AC9 (динамическое сужение по фильтрам, в режиме «В наличии»):** Given пользователь установил `inStock=true` (default) и выбрал категорию «Футбол», when `getVisibleBrands(filters)` вернул `{brand_ids: [Nike.id, Puma.id]}`, then в сайдбаре видны только чекбоксы `Nike` и `Puma`; остальные бренды скрыты, но НЕ удалены из `brands` state. **Note (v1.2):** при `inStock=false` динамическое сужение НЕ выполняется — это сознательный компромисс: первичный гейт `has_stock=true` уже отфильтровал бренды без in-stock товаров, а дальнейшее сужение по `visible-brands` без чекбокса «В наличии» создавало бы парадокс «фильтр in-stock выключен, но бренды скрыты по in-stock». Симметрия с `getVisibleCategories` нарушена осознанно: категории всегда полные (без `has_stock`-гейта), бренды — нет.
10. **AC10 (preserve-selection при смене фильтра):** Given `selectedBrandIds = {Nike.id}`, then пользователь меняет категорию на ту, где `Nike` нет, when `sidebarVisibleBrandIds` не содержит `Nike.id`, then чекбокс `Nike` всё равно отрисован (через условие `selectedBrandIds.has(b.id)`) и `selectedBrandIds` не сбрасывается автоматически.
11. **AC11 (сброс `sidebarVisibleBrandIds` при снятии «В наличии»):** Given пользователь снимает чекбокс «В наличии», when обработчик вызывает `setInStock(false)`, then немедленно устанавливается `sidebarVisibleBrandIds = null` и сайдбар показывает все бренды из первичного `getAll({ has_stock: true })` (зеркально текущему поведению `setSidebarVisibleIds(null)` для категорий).
12. **AC12 (graceful fallback на сетевую ошибку `visible-brands`):** Given сетевая/5xx ошибка `getVisibleBrands`, when promise reject, then `sidebarVisibleBrandIds = null`, чекбоксы из `brands` state видны полностью, никаких toast-ошибок и блокировки UI; в консоль выводится `console.error`/`console.warn`.
13. **AC13 (empty-state):** Given активные фильтры исключают все товары каталога и `selectedBrandIds.size === 0`, when `visible-brands` вернул пустой массив, then в сайдбаре отображается существующий fallback `<p>Бренды не найдены</p>` (`page.tsx:1066`-логика).
14. **AC14 (scope не затрагивает electric-каталог):** Given `frontend/src/app/(electric)/electric/catalog/page.tsx` существует в кодовой базе, when выполнены все задачи спеки, then этот файл и его тесты остаются неизменёнными.
15. **AC15 (модель `Brand` и миграции):** Given реализован гейт `has_stock` и action `visible_brands`, when выполнены все задачи, then ни одной миграции не добавлено и модель `Brand` не изменена; `BrandFeaturedSerializer` и контракт `/brands/featured/` неизменны.

## Tasks / Subtasks

- [x] Task 1: Backend — гейт `has_stock` в `BrandViewSet` (AC: 1, 2, 3, 4, 15)
  - [x] 1.1: В `backend/apps/products/views.py` (`BrandViewSet.get_queryset`, ~line 354–361) после существующего `is_featured` фильтра добавить парсинг `has_stock` через `self.request.query_params.get("has_stock")`. Boolean-семантика: `"true"`/`"1"` (lowercase) → True; всё остальное (включая `"false"`/`"0"`) и `None` → False (без применения фильтра, backward compat).
  - [x] 1.2: Реализовать фильтр через `Exists` subquery (НЕ через `Count`/`distinct`):
    ```python
    in_stock_products = Product.objects.filter(
        brand=OuterRef("pk"),
        is_active=True,
        variants__stock_quantity__gt=0,
    )
    qs = qs.filter(Exists(in_stock_products))
    ```
    `Exists` гарантирует один subquery без декартова произведения `products × variants` (паттерн в `views.py:102` для аннотации `has_stock` у `Product`). Импорты `Exists`, `OuterRef`, `Product` уже есть в файле — проверить и не дублировать.
  - [x] 1.3: Гейт применяется ТОЛЬКО когда `self.action != "featured"` (внутри существующей ветки `if self.action != "featured":`) — featured-кэш не должен ломаться через query-параметр.
  - [x] 1.4: Обновить `@extend_schema(parameters=[...])` действия `list` (~`views.py:362–376`): добавить `OpenApiParameter("has_stock", OpenApiTypes.BOOL, description="Возвращать только бренды, у которых есть активные товары с вариантами в наличии (stock_quantity > 0). По умолчанию параметр не применяется (backward compat).")`.

- [x] Task 2: Backend — action `visible_brands` на `ProductViewSet` (AC: 5, 6, 7)
  - [x] 2.1: В `backend/apps/products/views.py` после `visible_categories` (~`views.py:200–232`) добавить новый action:
    ```python
    @extend_schema(
        summary="Видимые бренды по фильтрам",
        description=(
            "Возвращает ID брендов, у которых есть товары по текущим фильтрам каталога. "
            "Параметр brand игнорируется — endpoint отражает глобальные фильтры, "
            "не сужая sidebar до уже выбранных брендов."
        ),
        parameters=[
            OpenApiParameter("category_id", OpenApiTypes.INT, description="ID категории (включая дочерние)"),
            OpenApiParameter("min_price", OpenApiTypes.NUMBER, description="Минимальная цена"),
            OpenApiParameter("max_price", OpenApiTypes.NUMBER, description="Максимальная цена"),
            OpenApiParameter("in_stock", OpenApiTypes.BOOL, description="Товары в наличии"),
            OpenApiParameter("search", OpenApiTypes.STR, description="Поисковый запрос"),
        ],
        tags=["Products"],
    )
    @action(detail=False, methods=["get"], url_path="visible-brands")
    def visible_brands(self, request: Request) -> Response:
        params = request.query_params.copy()
        params.pop("brand", None)  # симметрично visible_categories.pop("category_id")
        filterset = self.filterset_class(params, queryset=self.get_queryset())
        filtered_qs = filterset.qs
        brand_ids = list(
            filtered_qs.exclude(brand_id__isnull=True)
                       .values_list("brand_id", flat=True)
                       .distinct()
        )
        return Response({"brand_ids": brand_ids})
    ```
  - [x] 2.2: URL генерируется автоматически через `DefaultRouter` → `products:product-visible-brands` (zero-config, симметрично `products:product-visible-categories` в `products/urls.py:12`).
  - [x] 2.3: Без расширения предками (бренд — плоская модель, не иерархия) и без сортировки (порядок не важен; на frontend применяется существующий порядок брендов из `getAll`).

- [x] Task 3: Backend — тесты `has_stock` (AC: 1, 2, 3, 4)
  - [x] 3.1: Дополнить `backend/apps/products/tests/test_brand_api.py` новым классом `TestBrandsHasStockGate` (или add module-level test cases) с фикстурами `Brand`, `Product`, `ProductVariant` (по образцу `apps.products.factories` из `test_visible_categories.py`).
  - [x] 3.2: Тесты:
    - `test_has_stock_true_excludes_brand_without_stock` (AC1): `Nike` с 5 товарами и всеми вариантами `stock_quantity=0` НЕ в результате при `?has_stock=true`.
    - `test_has_stock_true_includes_brand_with_stock` (AC2): `Adidas` с ≥1 товаром и ≥1 вариантом `stock_quantity>0` присутствует.
    - `test_has_stock_absent_returns_all_active_brands` (AC3): `GET /api/v1/brands/` без `has_stock` возвращает все активные бренды.
    - `test_has_stock_false_returns_all_active_brands` (AC3): `?has_stock=false` эквивалент отсутствию параметра.
    - `test_has_stock_does_not_affect_featured_action` (AC4): `?has_stock=true` к `/api/v1/brands/featured/` НЕ меняет ответ; кэш `FEATURED_BRANDS_CACHE_KEY` не загрязняется.
    - `test_has_stock_uses_exists_subquery_no_duplicates` (производительность/корректность): бренд с 3 товарами, у каждого по 2 варианта `stock>0` — возвращается ровно 1 раз без `distinct()` (`Exists` исключает декартово произведение).
    - `test_has_stock_excludes_inactive_products` (граничный): бренд имеет товары с `is_active=False` и `stock>0` — НЕ попадает в результат при `?has_stock=true`.
  - [x] 3.3: Все новые тесты помечены `@pytest.mark.unit` или `@pytest.mark.integration` согласно правилу проекта (см. `AGENTS.md` — кастомные маркеры pytest). Для тестов через `APIClient` + `@pytest.mark.django_db` используется маркер `integration`.

- [x] Task 4: Backend — тесты `visible_brands` (AC: 5, 6, 7)
  - [x] 4.1: Создать новый файл `backend/apps/products/tests/test_visible_brands.py` по образцу `test_visible_categories.py` (структура `TestVisibleBrandsAction` с APIClient-фикстурой, `reverse("products:product-visible-brands")`).
  - [x] 4.2: Тесты:
    - `test_returns_brand_ids_for_in_stock_products` (AC5): два бренда с in-stock товарами в разных категориях — оба ID в ответе.
    - `test_filter_by_category_id_returns_only_relevant_brands` (AC5): `?category_id=<football_id>` → только бренды с товарами в «Футбол» (с дочерними).
    - `test_ignores_brand_param` (AC6): `?brand=nike&min_price=1000` → ID всех брендов с товарами цена≥1000, включая nike.
    - `test_filter_by_min_price` / `test_filter_by_max_price` / `test_filter_by_in_stock` / `test_filter_by_search`: каждый ProductFilter параметр работает.
    - `test_excludes_brand_id_null_for_products_without_brand` (AC7): товар с `brand=None` не приводит к появлению `null` в `brand_ids`.
    - `test_empty_result_when_filters_exclude_all_products`: пустой массив при исключающих фильтрах.
    - `test_returns_distinct_brand_ids_no_duplicates`: бренд с N товарами появляется ровно один раз (через `.distinct()`).
  - [x] 4.3: Все тесты помечены `@pytest.mark.integration` (используют `APIClient`, реальный `ProductFilter`). При желании — отдельные unit-тесты с маркером `unit` для проверки логики `pop("brand")` без HTTP-обёртки.

- [x] Task 5: Frontend — `brandsService.getAll` опциональный `has_stock` (AC: 8, 3)
  - [x] 5.1: В `frontend/src/services/brandsService.ts` (~line 46) расширить сигнатуру:
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
  - [x] 5.2: Backward compat: вызовы `brandsService.getAll()` (без аргумента) работают как сейчас — параметр `has_stock` НЕ отправляется. Это ВАЖНО, потому что `getAll()` могут вызывать другие потребители помимо catalog/page.tsx.
  - [x] 5.3: Тип-аннотация для `opts?.has_stock` — строго `boolean | undefined`. Не отправлять `false` явно: если консумер хочет старое поведение, он не передаёт ничего.

- [x] Task 6: Frontend — `brandsService.getVisibleBrands` (AC: 9, 10, 12)
  - [x] 6.1: В `frontend/src/services/brandsService.ts` после `getFeatured` добавить метод по образцу `categoriesService.getVisibleCategories` (`categoriesService.ts:87`):
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
  - [x] 6.2: Импорт `ProductFilters` из `@/services/productsService` (тип уже экспортируется, см. `productsService.ts:152`).
  - [x] 6.3: Удаление `brand` на frontend ВАЖНО для согласованности: бекенд тоже игнорирует `brand`, но удаление на клиенте делает контракт явным и предотвращает путаницу при чтении network-логов.

- [x] Task 7: Frontend — тесты `brandsService` (AC: 8, 9)
  - [x] 7.1: В `frontend/src/services/__tests__/brandsService.test.ts` дополнить describe `getAll`:
    - `test('sends has_stock=true when opts.has_stock=true')`: проверка query string.
    - `test('omits has_stock when opts is undefined or empty (backward compat)')`: URL без `has_stock`.
    - `test('sends has_stock=false when opts.has_stock=false')`: явная передача.
  - [x] 7.2: Добавить новый describe `getVisibleBrands`:
    - `test('returns brand_ids array on success')`.
    - `test('does not send brand param to backend')` — проверка отсутствия `brand` в query string.
    - `test('throws on network error')` (по образцу `getFeatured handles network error`).

- [x] Task 8: Frontend — state и первичный fetch на `/catalog` (AC: 8, 11)
  - [x] 8.1: В `frontend/src/app/(blue)/catalog/page.tsx` рядом со state `sidebarVisibleIds` (~line 355) добавить:
    ```typescript
    const [sidebarVisibleBrandIds, setSidebarVisibleBrandIds] = useState<Set<number> | null>(null);
    ```
    Семантика: `null` = «показывать всё» (initial / fallback), `Set<number>` = whitelist для фильтрации чекбоксов.
  - [x] 8.2: В `fetchBrands` (~line 530) заменить `brandsService.getAll()` на `brandsService.getAll({ has_stock: true })`. Это первичный гейт — бренды без товаров в наличии не попадают даже в `brands` state.
  - [x] 8.3: Если `getAll({ has_stock: true })` падает с network/5xx, `brandsError` уже устанавливается existing-логикой — никаких новых веток обработки не требуется.

- [x] Task 9: Frontend — условный fetch `getVisibleBrands` в `fetchProducts` (AC: 9, 12)
  - [x] 9.1 **(v1.2 — ратифицировано)**: В `fetchProducts` (~line 643) `Promise.all` вызывает `getVisibleBrands` ТОЛЬКО при `filters.in_stock === true`; при `inStock=false` сразу `setSidebarVisibleBrandIds(null)` без сетевого запроса:
    ```typescript
    const [response] = await Promise.all([
      productsService.getAll(filters),
      categoriesService
        .getVisibleCategories(filters)
        .then(ids => setSidebarVisibleIds(new Set(ids)))
        .catch(() => setSidebarVisibleIds(null)),
      filters.in_stock
        ? brandsService
            .getVisibleBrands(filters)
            .then(ids => setSidebarVisibleBrandIds(new Set(ids)))
            .catch(error => {
              console.warn('Не удалось загрузить видимые бренды', error);
              setSidebarVisibleBrandIds(null);
            })
        : Promise.resolve(setSidebarVisibleBrandIds(null)),
    ]);
    ```
    **Обоснование:** при `inStock=false` грид показывает out-of-stock товары, и динамическое сужение брендов через `visible-brands` (который применяет `ProductFilter` к товарам) создавало бы парадокс между визуально присутствующими товарами и скрытыми чекбоксами их брендов. Решение: при выключенном `inStock` показываем все бренды из первичного `getAll({has_stock:true})` без сужения.
  - [x] 9.2: `visible-brands` запрос НЕ блокирует рендер товаров — он обновляет только sidebar visibility state (структура такая же, как для `getVisibleCategories`).
  - [x] 9.3: Сетевые ошибки `getVisibleBrands` приводят к `setSidebarVisibleBrandIds(null)` и `console.warn` (без toast-уведомлений, без блокировки UI).

- [x] Task 10: Frontend — рендер чекбоксов с preserve-selection (AC: 9, 10, 13)
  - [x] 10.1: В рендере чекбоксов брендов (`page.tsx:1069–1079`) внедрить filter с тройным условием:
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
        <div key={brand.id}>
          <Checkbox
            label={brand.name}
            checked={selectedBrandIds.has(brand.id)}
            onChange={() => handleBrandToggle(brand.id)}
          />
        </div>
      ));
    })()}
    ```
  - [x] 10.2: Условие `|| selectedBrandIds.has(b.id)` КРИТИЧНО — без него выбранный бренд исчезнет из UI при смене фильтра (ломает preserve-selection).
  - [x] 10.3: Существующий fallback `<p>Бренды не найдены</p>` (`page.tsx:1066–1068`) для случая `brands.length === 0` сохранить, либо консолидировать с новым empty-state внутри IIFE — ОДИН источник истины для empty-state. Рекомендация: убрать дублирующий `brands.length === 0` блок, оставить только новый внутри IIFE, поскольку `visibleBrands.length === 0` покрывает оба случая.

- [x] Task 11: Frontend — сброс `sidebarVisibleBrandIds` при снятии «В наличии» (AC: 11)
  - [x] 11.1: В обработчике чекбокса «В наличии» (`page.tsx:1086–1094`, `onChange`) при `!e.target.checked` дополнительно вызвать:
    ```typescript
    if (!e.target.checked) {
      setSidebarVisibleIds(null);
      setSidebarVisibleBrandIds(null);
    }
    ```
    Зеркально текущему сбросу `setSidebarVisibleIds(null)` для категорий.
  - [x] 11.2: При этом базовый список брендов из `brandsService.getAll({ has_stock: true })` остаётся отфильтрованным гейтом (это сознательный компромисс — см. Open Questions в tech-spec).

- [x] Task 12: Frontend — тесты CatalogPage (AC: 8, 9, 10, 11, 12, 13)
  - [x] 12.1: В `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` добавить тесты:
    - `test('hides out-of-stock brands at initial load')`: мок `getAll({has_stock:true})` возвращает только in-stock бренды → в DOM нет `Nike` если он out-of-stock.
    - `test('hides brands not in visible-brands when category filter active')`: мок `getVisibleBrands` возвращает `[Nike.id]`, выбор категории → `Adidas` checkbox не рендерится.
    - `test('preserves selected brand checkbox even when not in visible-brands')`: выбран `Nike`, фильтр меняется так, что `visible-brands` не содержит `Nike.id` → checkbox `Nike` остаётся видимым (AC10).
    - `test('falls back to full brands list on visible-brands network error')` (AC12): мок `getVisibleBrands` rejects → все бренды из `brands` state видны.
    - `test('shows "Бренды не найдены" when visible-brands empty and no selection')` (AC13).
    - `test('resets sidebarVisibleBrandIds to null when in-stock checkbox unchecked')` (AC11).
  - [x] 12.2: Использовать существующий MSW-сервер (`__mocks__/api/server.ts`), моки на endpoints `/brands/`, `/brands/featured/`, `/products/visible-brands/`, `/products/visible-categories/`, `/products/`.

- [x] Task 13: Scope verification (AC: 14, 15)
  - [x] 13.1: Подтвердить отсутствием diff'а в `frontend/src/app/(electric)/electric/catalog/**` после всех изменений (`git status` / `git diff --stat`).
  - [x] 13.2: Подтвердить отсутствием новых миграций `backend/apps/products/migrations/` и неизменностью `Brand` модели.
  - [x] 13.3: Подтвердить неизменность `BrandFeaturedSerializer`, `FEATURED_BRANDS_CACHE_KEY`, и поведения `/brands/featured/` (см. AC4).

## Dev Notes

### Архитектурный паттерн

Стратегия двухуровневого фильтра брендов **полностью симметрична** уже работающему фильтру категорий:

| Уровень | Категории (существующий) | Бренды (новый) |
|---|---|---|
| **Глобальный гейт** | (нет — категории всегда полные) | `GET /brands/?has_stock=true` (первичный fetch) |
| **Динамическое сужение** | `GET /products/visible-categories/?...` (без `category_id`) | `GET /products/visible-brands/?...` (без `brand`) |
| **State (frontend)** | `sidebarVisibleIds: Set<number> \| null` | `sidebarVisibleBrandIds: Set<number> \| null` |
| **Семантика `null`** | показать всё (fallback) | показать всё (fallback) |
| **Preserve-selection** | (категория выбирается одна, нет проблемы) | `selectedBrandIds.has(b.id)` принудительно показывает чекбокс |
| **Reset при `!inStock`** | `setSidebarVisibleIds(null)` | `setSidebarVisibleBrandIds(null)` |

### Критические инварианты (developer guardrails)

1. **`Exists` subquery, не `Count` / `JOIN` через `annotate(Count('products__variants'))`.** Иначе декартово произведение `products × variants` испортит результат и/или потребует `distinct()`. Паттерн уже использован в `views.py:102` для аннотации `has_stock` у `Product` — копировать его форму.
2. **Гейт `has_stock` НЕ применяется в `featured` action.** Внутри `BrandViewSet.get_queryset` уже есть условие `if self.action != "featured":` — добавлять парсинг `has_stock` ВНУТРИ этого if-блока (после `is_featured`). Кэш `FEATURED_BRANDS_CACHE_KEY` не должен зависеть от query-параметров.
3. **`visible_brands` удаляет `brand` из `query_params.copy()` ДО применения `ProductFilter`.** Симметрично `visible_categories.pop("category_id")` (`views.py:208–209`). Без этого фильтр сужает сам себя при множественном выборе брендов.
4. **`exclude(brand_id__isnull=True)` ДО `values_list("brand_id", flat=True).distinct()`.** Товары без бренда (в каталоге FREESPORT встречаются) приведут к `null` в `brand_ids` и сломают `Set<number>` на frontend.
5. **Frontend `getAll` без аргумента остаётся backward-compat.** Если `opts === undefined` или `opts.has_stock === undefined` — параметр НЕ отправляется. Это критично, т.к. `brandsService.getAll()` могут вызывать другие компоненты.
6. **Preserve-selection через `|| selectedBrandIds.has(b.id)`.** Это единственная защита от UX-disaster'а: пользователь выбрал бренд → фильтр изменился → бренд исчез → пользователь не может снять выбор. Это требование AC10.
7. **`null` vs пустой `Set` в `sidebarVisibleBrandIds`.** `null` = «показать все». Пустой `Set` = «нет видимых брендов» (валидное состояние при исключающих фильтрах). НЕ нормализовать пустой Set к `null` — empty-state требует показа `<p>Бренды не найдены</p>`.

### Anti-patterns (что НЕ делать)

- **Не использовать `Brand.objects.annotate(Count('products__variants__stock_quantity'))`** — это N+1 / декартово произведение. Только `Exists`.
- **Не вводить `has_stock` или `visible_brands` в `BrandViewSet.featured` action** — кэшируется, изменение сломает кэш и tests `TestFeaturedBrandsEndpoint`.
- **Не сбрасывать `selectedBrandIds` при изменении `sidebarVisibleBrandIds`** — пользователь увидит самопроизвольное снятие фильтров.
- **Не добавлять «предков» как для категорий** — модель `Brand` плоская, иерархии нет.
- **Не вносить никаких изменений в `(electric)/electric/catalog/page.tsx`** — модуль deprecated.
- **Не менять контракт `BrandFeaturedSerializer` и endpoint `/brands/featured/`.**
- **Не менять модель `Brand` и не добавлять миграции** (Story предполагает no-migration scope).
- **Не передавать `request` в `getVisibleBrands` filters** — фильтры берутся из текущего `fetchProducts` filters, а они формируются из URL-state catalog page.

### Затрагиваемые файлы (File List preview)

**Backend:**
- `backend/apps/products/views.py` — изменить `BrandViewSet.get_queryset` (~line 354), добавить `OpenApiParameter("has_stock", ...)` в `BrandViewSet.list @extend_schema` (~line 362), добавить `ProductViewSet.visible_brands` action (после `visible_categories`, ~line 232).
- `backend/apps/products/tests/test_brand_api.py` — расширить новым классом `TestBrandsHasStockGate`.
- `backend/apps/products/tests/test_visible_brands.py` — НОВЫЙ файл по образцу `test_visible_categories.py`.

**Frontend:**
- `frontend/src/services/brandsService.ts` — расширить `getAll(opts?: { has_stock?: boolean })`, добавить `getVisibleBrands(filters)`.
- `frontend/src/services/__tests__/brandsService.test.ts` — расширить тесты.
- `frontend/src/app/(blue)/catalog/page.tsx` — добавить state `sidebarVisibleBrandIds`, обновить `fetchBrands`, `fetchProducts`, рендер чекбоксов брендов, обработчик `inStock`.
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — добавить тесты visibility/preserve-selection/fallback/empty-state/reset.

### Backward compatibility и риски

- **OpenAPI / spec sync:** добавление `has_stock` в `@extend_schema` обновит OpenAPI schema. Если в проекте есть docs-sync (см. `make docs-sync-api`), запустить после изменений.
- **Кэш `FEATURED_BRANDS_CACHE_KEY`:** если кэш уже прогрет на проде, инвалидация не нужна — `featured` action не меняется.
- **DRF pagination для `/brands/`:** `BrandPageNumberPagination.page_size = 100`. Если каталог имеет 100+ брендов с in-stock товарами, гейт `has_stock=true` уменьшит набор — page_size не нужно увеличивать.
- **Race condition при быстрой смене фильтров:** `getVisibleBrands` БЕЗ AbortController. Уже зафиксировано в `deferred-work.md` для `getVisibleCategories` как известный риск; решение — отдельная story с AbortController/счётчиком версий. В рамках текущей story НЕ требуется (DEFERRED, симметрично категориям).

### Тестовые стандарты

- Backend: `pytest` с маркерами `@pytest.mark.unit` (без БД, чистая логика) и `@pytest.mark.integration` (`@pytest.mark.django_db`, `APIClient`). См. `AGENTS.md` — секция «Кастомные маркеры pytest».
- Frontend: Jest + Testing Library + MSW. Для service-тестов использовать `__mocks__/api/server.ts` (паттерн в `brandsService.test.ts`).
- Verification: см. секцию `Verification` ниже.

### References

- Tech-spec: [`_bmad-output/implementation-artifacts/tech-spec/tech-spec-catalog-hide-out-of-stock-brands.md`](../tech-spec/tech-spec-catalog-hide-out-of-stock-brands.md)
- Симметричный tech-spec категорий: [`_bmad-output/implementation-artifacts/tech-spec/tech-spec-catalog-category-sort-and-hide-empty.md`](../tech-spec/tech-spec-catalog-category-sort-and-hide-empty.md)
- Образец backend action: `backend/apps/products/views.py:184-232` (`visible_categories`)
- Образец backend `Exists`-аннотации: `backend/apps/products/views.py:102`
- Образец frontend service метода: `frontend/src/services/categoriesService.ts:87-97` (`getVisibleCategories`)
- Образец frontend state и filter: `frontend/src/app/(blue)/catalog/page.tsx:355` (`sidebarVisibleIds`)
- Образец backend тестов: `backend/apps/products/tests/test_visible_categories.py`
- Project info: [`docs/PROJECT_INFO.md`](../../../docs/PROJECT_INFO.md)
- Deferred risks (контекст): [`_bmad-output/implementation-artifacts/deferred-work.md`](../deferred-work.md)

### Project Structure Notes

Этот story не вносит изменений в структуру проекта:
- Backend: добавляет ОДИН action в существующий ViewSet (`ProductViewSet`) и ОДИН parsing-блок в `BrandViewSet.get_queryset`. Никаких новых модулей/папок.
- Frontend: расширяет существующий `brandsService` двумя методами и одну страницу `catalog/page.tsx`. Никаких новых компонентов.
- Тесты: один новый файл `test_visible_brands.py` рядом с симметричным `test_visible_categories.py`.

## Testing

### Pre-Implementation (red tests)

Запустить ДО реализации, чтобы убедиться, что новые тесты падают на текущем коде:

```bash
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
  pytest apps/products/tests/test_brand_api.py::TestBrandsHasStockGate \
         apps/products/tests/test_visible_brands.py \
         -m "unit or integration" -x -v
```

### Post-Implementation (green)

```bash
# Backend (targeted)
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
  pytest apps/products/tests/test_brand_api.py \
         apps/products/tests/test_visible_brands.py \
         -m "unit or integration" -x -q

# Backend (regression — весь products)
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
  pytest apps/products -m "unit or integration" -x -q

# Frontend (targeted)
cd frontend
npm run test -- src/services/__tests__/brandsService.test.ts
npm run test -- "src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx"

# Frontend (build)
npm run build  # должен пройти без TypeScript ошибок
```

### Manual checks (smoke)

- `/catalog` default (`inStock=true`): бренды без товаров в наличии не видны; бренды с товарами видны.
- `/catalog?category=football`: видны только бренды с товарами в «Футболе».
- `/catalog?brand=nike` затем смена категории на ту, где `Nike` нет → чекбокс `Nike` остаётся видимым.
- Снятие чекбокса «В наличии» → весь список из первичного `getAll(has_stock=true)` восстанавливается; другие бренды НЕ появляются (гейт всегда применяется в первичном fetch).
- Активная комбинация фильтров, исключающая все товары → «Бренды не найдены».
- Симуляция 500 от `/products/visible-brands/` → сайдбар показывает полный список из `getAll(has_stock=true)`, навигация не сломана.
- `/api/v1/brands/featured/` (главная) → содержимое без изменений.
- `/electric/catalog` → визуальная регрессия не наблюдается (модуль deprecated, но проверить не сломан).

## Change Log

| Date | Version | Description | Author |
|---|---:|---|---|
| 2026-05-06 | 1.0 | История создана из утверждённого tech-spec `tech-spec-catalog-hide-out-of-stock-brands.md` (status=draft, baseline_commit=e4f2ae0). | Cascade (bmad-create-story) |
| 2026-05-06 | 1.1 | Реализованы backend `has_stock`/`visible-brands`, frontend-сужение брендов каталога и тестовое покрытие. | GPT-5 Codex |
| 2026-05-06 | 1.2 | Code review: AC9 переформулирован под conditional fetch (`getVisibleBrands` зовётся только при `inStock=true`); Task 9.1 переписан с обоснованием компромисса. Findings — 1 ratified, 1 patch pending, 5 deferred. | Claude Opus 4.7 (bmad-code-review) |
| 2026-05-06 | 1.3 | Исправлен review patch по Task 5.3: `brandsService.getAll({ has_stock: false })` больше не отправляет `has_stock=false`; story переведена в review. | GPT-5 Codex |
| 2026-05-06 | 1.4 | Исправлен review patch по AC7: тест `visible-brands` теперь реально валидирует исключение `brand_id IS NULL`; story переведена в review. | GPT-5 Codex |
| 2026-05-07 | 1.5 | Code review run 3 (post-v1.4): 6 patch findings оставлены как action items (option 2), 3 deferred, 3 dismissed. Status переведён в in-progress. | Cascade (bmad-code-review) |
| 2026-05-07 | 1.6 | Исправлены 6 patch findings run 3: cache isolation, OpenAPI wording, async reset ветки `inStock=false`, defensive `brand_ids`, `tsconfig` scope; story переведена в review. | GPT-5 Codex |
| 2026-05-07 | 1.7 | Code review run 4 (post-v1.6): 2 patch findings (MEDIUM — `BrandViewSet.retrieve` неявное поведение `has_stock`, coverage gap для несуществующего `category_id`), 3 defer (повторы run 3), 1 dismissed. Outcome — выбор пользователя. | Cascade (bmad-code-review) |

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-06: BMAD dev-story workflow started; story and sprint status moved to in-progress.
- 2026-05-06: Red backend check failed as expected on `TestBrandsHasStockGate::test_has_stock_true_excludes_brand_without_stock`.
- 2026-05-06: Backend targeted tests passed: 17 passed.
- 2026-05-06: Frontend service tests passed: 14 passed; CatalogPage tests passed: 22 passed.
- 2026-05-06: Backend products regression passed: 179 passed, 199 deselected.
- 2026-05-06: Frontend build passed; scoped ESLint on changed files passed. Full `npm run lint` is blocked by existing generated `frontend/next-env.d.ts` triple-slash rule outside this story diff.
- 2026-05-06: Red frontend service check failed as expected after updating the Task 5.3 test: `has_stock=false` was still present in the query string.
- 2026-05-06: Review patch fixed; frontend service tests passed: 14 passed; CatalogPage tests passed: 22 passed; frontend build passed; scoped ESLint on changed files passed.
- 2026-05-06: Full frontend Vitest regression suite passed (`npm run test`, exit code 0).
- 2026-05-06: Review patch AC7 fixed; `test_visible_brands.py` targeted test passed, file suite passed (10 passed), backend targeted suite passed (17 passed), products regression passed (179 passed, 199 deselected).
- 2026-05-07: Review patch run 3 fixed; backend targeted tests passed (47 passed), backend products regression passed (378 passed), frontend targeted tests passed (37 passed), full frontend Vitest passed, Black check passed, Flake8 passed, scoped ESLint passed, `npm run build` passed.

### Completion Notes List

- Добавлен backend-гейт `GET /api/v1/brands/?has_stock=true` через `Exists` subquery; `featured` action и кэш `FEATURED_BRANDS_CACHE_KEY` не затронуты.
- Добавлен `GET /api/v1/products/visible-brands/`, который применяет `ProductFilter`, игнорирует `brand`, исключает `brand_id IS NULL` и сбрасывает ordering перед `distinct()`.
- `brandsService.getAll` получил опциональный `has_stock`, добавлен `getVisibleBrands` с удалением `brand` на клиенте.
- Review patch Task 5.3 закрыт: `brandsService.getAll` отправляет `has_stock` только при `has_stock === true`; `false`, `{}` и `undefined` сохраняют backward-compatible URL без `has_stock`.
- Review patch AC7 закрыт: тест `test_excludes_brand_id_null_for_products_without_brand` больше не является тривиально-зелёным и проверяет удаление `None` через fake queryset, потому что текущая `Product.brand` в модели и миграции не nullable.
- Review patch run 3 закрыт: `visible-brands` тесты изолированы от Django cache, OpenAPI явно описывает gate-семантику `has_stock`, reset `sidebarVisibleBrandIds` в `inStock=false` ветке стал асинхронным внутри `Promise.all`, `getVisibleBrands` защищён от malformed payload без `brand_ids`, форматирование `frontend/tsconfig.json` возвращено к baseline.
- `/catalog` теперь первично загружает только бренды с товарами в наличии, динамически сужает sidebar по `visible-brands`, сохраняет выбранный бренд видимым и делает graceful fallback при ошибке.
- Scope AC14/AC15 подтверждён: нет diff в electric-каталоге, миграциях, `Brand` model, `BrandFeaturedSerializer`, constants.

### File List

- `_bmad-output/implementation-artifacts/Story/catalog-hide-out-of-stock-brands.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/apps/products/views.py`
- `backend/apps/products/tests/test_brand_api.py`
- `backend/apps/products/tests/test_visible_brands.py`
- `frontend/src/services/brandsService.ts`
- `frontend/src/services/__tests__/brandsService.test.ts`
- `frontend/src/app/(blue)/catalog/page.tsx`
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx`
- `frontend/tsconfig.json`

### Review Findings (run 4 — 2026-05-07, post-v1.6)

_Source: bmad-code-review (четвёртый прогон после v1.6 patch), reviewers: Blind Hunter + Edge Case Hunter + Acceptance Auditor. Baseline: `e4f2ae0`. HEAD: `2b736b3` + uncommitted v1.6 patch._

- [ ] [Review][Patch] **`BrandViewSet.retrieve(slug)?has_stock=true` начинает возвращать 404 для брендов без in-stock товаров — поведение не определено в spec и не покрыто тестами** [`backend/apps/products/views.py:391-402`] — `BrandViewSet.get_queryset()` применяет `has_stock` гейт во ВСЕХ action != "featured", включая `retrieve`. Spec (AC1-AC3) описывает только list endpoint `GET /api/v1/brands/?has_stock=true`; AC4 явно изолирует только `featured`. Если внешний клиент или будущий код дёрнет `GET /api/v1/brands/nike/?has_stock=true` для бренда без stock, получит 404 вместо 200 — это новое неявное поведение, не задокументированное в spec и не покрытое тестом. Решения: (a) ограничить гейт `if self.action == "list":` (более узкий контракт, симметрично list-only intent spec'и); (b) явно зафиксировать в spec, что гейт применяется к list+retrieve, и добавить тест `test_has_stock_does_not_affect_retrieve_action` либо `test_retrieve_returns_404_for_filtered_brand_with_has_stock`. Рекомендация: (a) — `if self.action == "list":` гарантирует, что гейт работает только там, где описан AC.
- [ ] [Review][Patch] **Coverage gap: нет теста на несуществующий `category_id` в `visible_brands`** [`backend/apps/products/tests/test_visible_brands.py`] — `ProductFilter.filter_category_id` корректно возвращает `queryset.none()` для несуществующего `category_id` (`filters.py:225`), но `test_visible_brands.py` не верифицирует контракт ответа в этом кейсе. Ожидаемое поведение: `GET /api/v1/products/visible-brands/?category_id=999999` → `200 OK` с `{"brand_ids": []}`. Добавить `test_returns_empty_brand_ids_for_nonexistent_category_id` с маркером `@pytest.mark.integration`. Защищает от регрессий, если кто-то заменит `filter_category_id` на raise/404.
- [x] [Review][Defer] **AC11 race manifest: stale `getVisibleBrands` ответ может перезаписать null после reset** [`frontend/src/app/(blue)/catalog/page.tsx:653-661, 1109-1116`] — Уже зафиксировано в run 3 deferred-section. Решать единой story по race-protection visible-* запросов с AbortController/version-counter.
- [x] [Review][Defer] **`visible_brands` тащит heavy annotations через `get_queryset()` (Sum/Min/Exists + GROUP BY products.id)** [`backend/apps/products/views.py:67-104, 260-264`] — Уже зафиксировано в run 3. Решать в общей story по оптимизации visible-* endpoints.
- [x] [Review][Defer] **`getVisibleBrands` отправляет `page`/`page_size`/`ordering`/marketing badges в URL (OpenAPI mismatch)** [`frontend/src/services/brandsService.ts:83-90`] — Уже зафиксировано в run 3. Решение — явно whitelist-ить разрешённые поля.

_Run 4 dismissed: 1 finding (стиль `Promise.resolve().then(() => setSidebarVisibleBrandIds(null))` — v1.6 patch decision принят как симметричный Promise.all)._

### Review Findings (run 3 — 2026-05-07, post-v1.4)

_Source: bmad-code-review (третий прогон после v1.4 patch), reviewers: Blind Hunter + Edge Case Hunter + Acceptance Auditor. Baseline: `e4f2ae0`. HEAD: `2b736b3`. Working tree clean._

- [x] [Review][Patch][Resolved 2026-05-07] **`TestVisibleBrandsAction` setup без `cache.clear()` — flaky-test risk** [`backend/apps/products/tests/test_visible_brands.py:23-29`] — Исправлено: добавлена autouse fixture `clear_cache()` в `TestVisibleBrandsAction`, чтобы `ProductFilter` и category descendants cache не протекали между тестами.
- [x] [Review][Patch][Resolved 2026-05-07] **Синхронный side-effect в `Promise.all` для `inStock=false`-ветки** [`frontend/src/app/(blue)/catalog/page.tsx:653-661`] — Исправлено: reset переведён в `Promise.resolve().then(() => setSidebarVisibleBrandIds(null))`, ветка стала асинхронной и симметричной остальным элементам `Promise.all`.
- [x] [Review][Patch][Resolved 2026-05-07] **`frontend/tsconfig.json` cosmetic-formatting вне `File List` (scope leak)** [`frontend/tsconfig.json`] — Исправлено: форматирование массивов возвращено к baseline `e4f2ae0`; файл добавлен в File List как затронутый patch-исправлением.
- [x] [Review][Patch][Resolved 2026-05-07] **OpenAPI `has_stock` description не объясняет gate-семантику (≠ `is_featured`)** [`backend/apps/products/views.py:414-421`] — Исправлено: description теперь явно фиксирует, что `has_stock` применяется только при `true`/`1`, а `false`/`0` эквивалентны отсутствию параметра и не означают «бренды без наличия».
- [x] [Review][Patch][Resolved 2026-05-07] **Defensive check для `response.data.brand_ids` в `getVisibleBrands`** [`frontend/src/services/brandsService.ts:83-90`] — Исправлено: сервис возвращает `[]`, если `brand_ids` отсутствует или не массив; добавлен Vitest на payload `{}`.
- [x] [Review][Patch][Resolved 2026-05-07] **Описание `BrandViewSet.list @extend_schema` сократилось до generic** [`backend/apps/products/views.py:407`] — Исправлено: list description снова явно перечисляет фильтрацию по `is_featured` и/или `has_stock`.
- [x] [Review][Defer] **Race-manifest при снятии `inStock=false`: stale `getVisibleBrands` ответ перезаписывает `null`** [`frontend/src/app/(blue)/catalog/page.tsx:653-661, 1109-1116`] — При быстром снятии чекбокса «В наличии» в полёте может быть `getVisibleBrands(filters_v1)` от предыдущего рендера. После reset (`setSidebarVisibleBrandIds(null)`) и re-fire `fetchProducts` с `inStock=false` старый ответ всё ещё применяется через `.then(ids => setSidebarVisibleBrandIds(new Set(ids)))` — UI вернётся к narrowed списку, нарушая AC11 в окне race. Это специфичный manifest уже-deferred общей race-проблемы (run 1, run 2). Решать единой story по race-protection visible-* запросов с AbortController/version-counter.
- [x] [Review][Defer] **`getVisibleBrands` отправляет `page`/`page_size`/`ordering`/marketing badges (OpenAPI mismatch)** [`frontend/src/services/brandsService.ts:83-90`] — Метод копирует `Partial<ProductFilters>` минус `brand`, не вычищая параметры пагинации/ordering и маркетинговые badges (`is_hit`, `is_new`, `is_sale`, `is_promo`, `is_premium`, `has_discount`). Backend документирует только 5 параметров в `@extend_schema(visible_brands)`, бейджи фильтруют (через `ProductFilter`), pagination/ordering игнорируются. Симметрично pre-existing проблеме `getVisibleCategories` (уже зафиксировано в run 1/2). Стоит явно whitelist-ить разрешённые поля.
- [x] [Review][Defer] **`visible_brands` тащит heavy annotations через `get_queryset`** [`backend/apps/products/views.py:67-104, 260-264`] — `self.get_queryset()` добавляет `Sum("variants__stock_quantity")`, `Min("variants__retail_price")`, `Exists(...)` annotations + `select_related("brand", "category")` + `prefetch_related(category__parent, attributes, variants)`. После `.values_list("brand_id", flat=True).distinct()` prefetch/select_related отбрасываются, но aggregation-annotations форсируют `GROUP BY products.id` с JOIN к `variants` до DISTINCT brand_id. На каталоге 10K+ products × N variants — заметная нагрузка. Симметрично `visible_categories`. Решать в общей story по оптимизации visible-* endpoints.

_Run 3 dismissed: 3 finding (IIFE без `useMemo` — overengineering, ratified в run 2 как dismissed; AC7 mock-test — ratified в run 2; deep-link к out-of-stock бренду через URL — dismissed в run 2 как валидное поведение)._

### Review Findings (run 2 — 2026-05-06, post-v1.3)

_Source: bmad-code-review (повторный прогон после v1.3 patch), reviewers: Blind Hunter + Edge Case Hunter + Acceptance Auditor. Baseline: `e4f2ae0`. Diff включает 2 коммита + uncommitted v1.3 fix._

- [x] [Review][Decision][Resolved 2026-05-06: dismissed] **Deep-link `/catalog?brand=<slug>` для out-of-stock бренда — невидимый фильтр** [`frontend/src/app/(blue)/catalog/page.tsx:529-568`] — Решение: dismissed как валидное поведение. Пользователь явно указал out-of-stock бренд через URL — отсутствие чекбокса в sidebar симметрично pre-existing поведению deep-link к скрытым категориям. Спека не требует обработки этого сценария.
- [x] [Review][Patch][Resolved 2026-05-06] **Тест `test_excludes_brand_id_null_for_products_without_brand` тривиально-зелёный** [`backend/apps/products/tests/test_visible_brands.py:230-243`] — Исправлено: тест теперь подменяет `ProductViewSet.filterset_class` fake queryset с `[brand_id, None, brand_id]` и проверяет, что `visible_brands` возвращает только `[brand_id]`. Это реально валидирует `exclude(brand_id__isnull=True)` и дедупликацию; прямой `ProductFactory(brand=None)` не используется, потому что текущая `Product.brand` в Django-модели и миграции `0001_initial.py` не nullable.
- [x] [Review][Defer] **AbortController / race для `getVisibleBrands` (включая reset при `setInStock(false)`)** [`frontend/src/app/(blue)/catalog/page.tsx:649-661, 1111-1116`] — Уже зафиксировано в `deferred-work.md` (run 1). При быстром переключении фильтров stale-ответ может перезаписать актуальный sidebar; reset на onChange чекбокса «В наличии» не отменяет in-flight `getVisibleBrands` от предыдущего `fetchProducts`. Решать единой story по race-protection visible-* запросов.
- [x] [Review][Defer] **Race с unmount — нет `isMounted`-guard в `fetchProducts`** [`frontend/src/app/(blue)/catalog/page.tsx:649-661`] — Симметрично pre-existing паттерну `getVisibleCategories`. Setter может вызваться на размонтированном компоненте при быстрой навигации.
- [x] [Review][Defer] **`variant.is_active=True` не проверяется в Exists-subquery `has_stock`** [`backend/apps/products/views.py:397-401`] — Уже зафиксировано в run 1, симметрично существующему паттерну `Product.has_stock` (`views.py:102`).
- [x] [Review][Defer] **`featured` action: латентный риск кэш-poisoning** [`backend/apps/products/views.py`] — Уже зафиксировано в run 1.
- [x] [Review][Defer] **`BrandPageNumberPagination.page_size=100` ограничение пагинации** [`frontend/src/services/brandsService.ts`] — Pre-existing, уже зафиксировано в run 1.
- [x] [Review][Defer] **`visible_brands` использует role-dependent pricing через `ProductFilter`** [`backend/apps/products/views.py:250-266`] — `min_price`/`max_price` в `ProductFilter` зависят от `request.user.role` (B2B vs гость). Один и тот же URL даст разные `brand_ids` для разных ролей. Симметрично pre-existing поведению `ProductViewSet`/`visible_categories`. Решать единой story по role-aware shareable URLs.
- [x] [Review][Defer] **`getVisibleBrands` отправляет `page`/`page_size`/`ordering` в URL** [`frontend/src/services/brandsService.ts:84-92`] — Backend их игнорирует, но создают мусор в URL и теоретически ломают cache на CDN. Симметрично pre-existing проблеме `getVisibleCategories` (уже задеферрено).

_Run 2 dismissed: ~30 (false-positive coverage gaps в стилистических тестах, theoretical multi-value query params, парсинг boolean — соответствует спеке, IIFE без useMemo — performance overengineering, conditional dispatch v1.2 уже снимает заявленные проблемы с in_stock=false и т.д.)._

### Review Findings

_Source: bmad-code-review (2026-05-06), reviewers: Blind Hunter + Edge Case Hunter + Acceptance Auditor. Baseline: `e4f2ae0`._

- [x] [Review][Decision][Resolved 2026-05-06: ratified] **AC9: `getVisibleBrands` вызывается условно (`filters.in_stock`)** — Решение: ратифицировать реализацию как намеренный компромисс. AC9 обновлён (precondition `inStock=true`); Task 9.1 переписан под conditional dispatch с обоснованием; tech-spec обновлён в Change Log v1.2. Симметрия с `getVisibleCategories` нарушена осознанно (категории всегда полные, бренды — гейтированы по `has_stock`).
- [x] [Review][Patch][Resolved 2026-05-06] **`brandsService.getAll` отправляет `has_stock=false` явно — нарушает Task 5.3** [`frontend/src/services/brandsService.ts:49`, `frontend/src/services/__tests__/brandsService.test.ts`] — Исправлено: условие изменено на `if (opts?.has_stock === true)`, тест переименован в `omits has_stock when opts.has_stock=false` и проверяет отсутствие query-параметра. Проверки: service tests 14 passed, CatalogPage tests 22 passed, `npm run build` passed, scoped ESLint passed.
- [x] [Review][Defer] **Race condition / отсутствие AbortController в `getVisibleBrands`** [`frontend/src/app/(blue)/catalog/page.tsx:653`] — deferred, спека явно фиксирует это в "Backward compatibility и риски": «Race condition при быстрой смене фильтров: getVisibleBrands БЕЗ AbortController. Уже зафиксировано в deferred-work.md для getVisibleCategories … В рамках текущей story НЕ требуется (DEFERRED, симметрично категориям)».
- [x] [Review][Defer] **`Promise.all` failure mode: visibility setters срабатывают, даже если `productsService.getAll` падает** [`frontend/src/app/(blue)/catalog/page.tsx:645`] — deferred, pre-existing паттерн (тот же эффект у `getVisibleCategories`). При 500 от продуктов sidebar остаётся обновлённым по новым фильтрам, а основной грид показывает ошибку — рассинхронизация. Решать вместе с AbortController-стори.
- [x] [Review][Defer] **`featured` action: латентный риск кэш-poisoning при будущем расширении** [`backend/apps/products/views.py`] — deferred, не активный баг. `FEATURED_BRANDS_CACHE_KEY` не имеет измерения по query-параметрам; если кто-то когда-нибудь свяжет `has_stock` или иную фильтрацию с `featured`, кэш начнёт отдавать устаревший payload. Сейчас `get_queryset` корректно short-circuit'ит для `featured` (AC4 и тест подтверждают). Зафиксировать как замечание для будущих расширений `featured`.
- [x] [Review][Defer] **Variant `is_active=True` не проверяется в `Exists`-subquery** [`backend/apps/products/views.py:397-401`] — deferred, соответствует существующему паттерну `views.py:102` для `Product.has_stock`-аннотации. Бренд с активными продуктами и активными вариантами в наличии корректен; кейс «активный продукт + неактивный вариант с stock>0» технически попадает в результат, но это консистентно с продуктовым фильтром. Изменение требует отдельной story (потенциально миграционно затрагивает сериализатор `is_in_stock`/`can_be_ordered`).
- [x] [Review][Defer] **Тестовые пробелы: невалидный `category_id`, multi-value `?brand=1&brand=2`, пагинация >100 брендов** [`backend/apps/products/tests/test_visible_brands.py`, `frontend/src/services/brandsService.ts`] — deferred, coverage-gap, не функциональный баг. `MultiValueDict.pop("brand", None)` корректно удаляет все значения, но тест покрывает только single-value кейс. Пагинация `page_size=100` — pre-existing ограничение `BrandPageNumberPagination`, не введено этой story.
