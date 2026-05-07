---
title: "Нормализация query-фильтров BrandViewSet (is_featured / has_stock)"
slug: "brand-viewset-filter-normalization"
created: "2026-05-07"
status: "draft"
baseline_commit: "22520173b89b4374a6c0e0f8fa346e26fc508b52"
tech_stack: ["Django", "DRF", "drf-spectacular"]
files_to_modify:
  - "backend/apps/products/views.py"
  - "backend/apps/products/tests/test_brand_api.py"
context:
  - "_bmad-output/implementation-artifacts/Story/catalog-hide-out-of-stock-brands.md"
  - "_bmad-output/implementation-artifacts/deferred-work.md"
related_story_predecessor: "catalog-hide-out-of-stock-brands"
---

# Tech Spec: Нормализация query-фильтров `BrandViewSet`

## Контекст и предыстория

В рамках story `catalog-hide-out-of-stock-brands` (run 4) был обнаружен баг: query-параметр `has_stock=true` применялся не только к `list`-action, но и к `retrieve(slug)`. Для бренда без in-stock товаров `GET /api/v1/brands/<slug>/?has_stock=true` возвращал **404** вместо **200**. Фикс ограничил `has_stock` действием `self.action == "list"`.

В run 5 ревью обнаружена **симметричная pre-existing проблема** для `is_featured`: фильтр всё ещё применяется ко всем action кроме `featured`, что включает `retrieve`. Эта проблема существовала до story `catalog-hide-out-of-stock-brands` и явно вынесена в `deferred-work.md`.

Текущий код (`backend/apps/products/views.py:388-404`):

```python
def get_queryset(self):
    """Активные бренды; has_stock применяется только к list action."""
    qs = Brand.objects.active().order_by("name")
    if self.action != "featured":          # <-- включает list, retrieve, и future actions
        is_featured = self.request.query_params.get("is_featured")
        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured.lower() in ("true", "1"))
    if self.action == "list":               # <-- ограничено list (фикс run 4)
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

## Проблема

`?is_featured=...` сужает базовый queryset **до** того, как DRF выбирает объект по `slug`. Сценарий:

- Бренд `Nike` существует, активный, но `is_featured=False`.
- Запрос: `GET /api/v1/brands/nike/?is_featured=true`.
- DRF queryset: `Brand.active().filter(is_featured=True)` — `Nike` отфильтрован.
- Поиск по `slug=nike` в этом queryset → пусто → **404 Not Found**.

UX/контракт: detail-эндпоинт должен идентифицироваться **только slug**. Query-фильтры `is_featured`/`has_stock` имеют смысл только для коллекции (`list`).

## Решение

Объединить `is_featured` и `has_stock` в общую ветку `if self.action == "list"`. Это:
- симметрично уже принятому решению по `has_stock`,
- защищает `retrieve(slug)` от 404 при «лишнем» query-параметре,
- сохраняет backward compatibility для `list` (контракт API не меняется),
- не затрагивает `featured`-action (короткое замыкание сохранено).

### Целевой код

```python
def get_queryset(self):
    """Активные бренды; is_featured и has_stock применяются только к list action."""
    qs = Brand.objects.active().order_by("name")
    if self.action == "list":
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

## Acceptance Criteria

1. **AC1 (`retrieve` + `is_featured=true` для не-featured бренда):** Given бренд `Nike` активный с `is_featured=False`, when выполняется `GET /api/v1/brands/nike/?is_featured=true`, then ответ **200 OK** с телом, содержащим `name="Nike"` (НЕ 404).
2. **AC2 (`retrieve` + `is_featured=false` для featured бренда):** Given бренд `Adidas` активный с `is_featured=True`, when выполняется `GET /api/v1/brands/adidas/?is_featured=false`, then ответ **200 OK** с `name="Adidas"`.
3. **AC3 (`list` + `is_featured=true` — backward compat):** Given в БД активные бренды `Nike` (`is_featured=False`) и `Adidas` (`is_featured=True`), when выполняется `GET /api/v1/brands/?is_featured=true`, then в ответе присутствует только `Adidas` (поведение `list` не меняется).
4. **AC4 (`list` + `is_featured=false` — backward compat):** `GET /api/v1/brands/?is_featured=false` возвращает только не-featured бренды (поведение `list` не меняется).
5. **AC5 (`list` без `is_featured` — backward compat):** `GET /api/v1/brands/` без параметра возвращает все активные бренды.
6. **AC6 (`featured` action не затронут):** `GET /api/v1/brands/featured/` (с любыми query-параметрами, включая `?is_featured=false`, `?has_stock=true`) возвращает кэшированный набор featured брендов; кэш `FEATURED_BRANDS_CACHE_KEY` не загрязняется и не зависит от query-параметров.
7. **AC7 (`retrieve` + `has_stock=true` — регрессия не вернулась):** Given бренд `Nike` без in-stock товаров, when выполняется `GET /api/v1/brands/nike/?has_stock=true`, then ответ **200 OK** (существующий тест `test_has_stock_does_not_affect_retrieve_action` проходит).
8. **AC8 (нет миграций, нет изменений модели):** Story не добавляет миграций, не меняет `Brand` model, `BrandSerializer`, `BrandFeaturedSerializer`, `BrandPageNumberPagination`, URLs.

## Implementation Tasks

- [ ] **Task 1: Backend — объединить ветку `is_featured` с `has_stock` в `BrandViewSet.get_queryset`** (AC: 1, 2, 6)
  - Файл: `backend/apps/products/views.py` (~line 388-404).
  - Action: заменить `if self.action != "featured":` для `is_featured` на единый блок `if self.action == "list":` с обоими фильтрами внутри.
  - Подтвердить, что импорты `Exists`, `OuterRef`, `Product` уже присутствуют (не добавлять повторно).

- [ ] **Task 2: Backend — обновить `@extend_schema` `BrandViewSet.list`** (AC: 3, 4, 5)
  - Файл: `backend/apps/products/views.py` (~line 406-427).
  - Action: уточнить description у `is_featured` параметра, явно зафиксировав, что он применяется **только** в list-action, симметрично текущей формулировке `has_stock` («Применяется только при значении true/1...»). Сохранить семантику list backward-compatible.

- [ ] **Task 3: Backend — регрессионный тест `is_featured` на `retrieve`** (AC: 1, 2)
  - Файл: `backend/apps/products/tests/test_brand_api.py`.
  - Action: добавить тест `test_is_featured_does_not_affect_retrieve_action` в класс `TestBrandsHasStockGate` (или новый класс `TestBrandRetrieveQueryParams`):
    - Создать `BrandFactory(name="Nike", slug="nike", is_featured=False)`.
    - `GET /api/v1/brands/nike/?is_featured=true` → 200, `data["name"] == "Nike"`.
    - Создать `BrandFactory(name="Adidas", slug="adidas", is_featured=True)`.
    - `GET /api/v1/brands/adidas/?is_featured=false` → 200, `data["name"] == "Adidas"`.
  - Помечен `@pytest.mark.django_db` + `@pytest.mark.integration` (использует `APIClient`).

- [ ] **Task 4: Backend — регрессионные тесты `list + is_featured`** (AC: 3, 4, 5)
  - Файл: `backend/apps/products/tests/test_brand_api.py`.
  - Action: проверить покрытие existing `is_featured` поведения для `list`. Если тестов нет — добавить:
    - `test_list_is_featured_true_returns_only_featured_brands` (AC3).
    - `test_list_is_featured_false_returns_only_non_featured_brands` (AC4).
    - `test_list_without_is_featured_returns_all_active_brands` (AC5).
  - Если тесты уже существуют — проверить, что они зелёные после изменения `get_queryset`.

- [ ] **Task 5: Backend — подтверждение `featured` action и кэша** (AC: 6)
  - Action: убедиться, что existing `TestFeaturedBrandsEndpoint` / `TestFeaturedBrandsCaching` проходят без изменений. Дополнительный тест `test_featured_action_ignores_is_featured_query_param` (если ещё нет) — проверка, что `?is_featured=false` к `/brands/featured/` не меняет ответ.

- [ ] **Task 6: Verification и docs-sync**
  - `make docs-sync-api` (если описание `is_featured` изменено) — синхронизация OpenAPI.
  - Запуск targeted suite: `pytest apps/products/tests/test_brand_api.py -m "unit or integration" -x -q`.
  - Запуск products regression: `pytest apps/products -m "unit or integration" -x -q`.

## Затрагиваемые файлы

**Backend:**
- `backend/apps/products/views.py` — реструктуризация `BrandViewSet.get_queryset` (объединение веток), уточнение `@extend_schema` description.
- `backend/apps/products/tests/test_brand_api.py` — добавить регрессионные тесты на `retrieve` + query-параметры; при необходимости — тесты на `list + is_featured`.

**НЕ затрагивается:**
- Frontend (фронтенд не отправляет `is_featured` на retrieve, контракт `list` не меняется).
- Миграции, модель `Brand`, сериализаторы, URLs.
- `featured`-action и его кэш.
- `visible_brands`-action на `ProductViewSet`.

## Backward compatibility и риски

- **Контракт `list` неизменён:** `?is_featured=true|false` работает как раньше; AC3-AC5 защищают семантику.
- **Контракт `retrieve` строго расширяется:** до фикса некоторые комбинации возвращали 404, теперь будут возвращать 200. Это совместимо с любым клиентом, ожидающим detail-объект по slug.
- **`featured`-кэш:** изменение находится только в ветке `if self.action == "list":`, для `featured`-action `get_queryset` отрабатывает базовый `Brand.objects.active().order_by("name")` — поведение и кэш сохраняются.
- **OpenAPI:** description `is_featured` уточняется (применимость к `list`-action). `make docs-sync-api` после изменения.
- **Будущие action на `BrandViewSet`:** новый паттерн (`if self.action == "list":`) явно ограничивает фильтры коллекцией. Любые будущие detail-style action автоматически защищены от рассинхрона.

## Тестовая стратегия

- Backend: `pytest` с маркерами `@pytest.mark.django_db` + `@pytest.mark.integration` (через `APIClient`). Размещение — `backend/apps/products/tests/test_brand_api.py` рядом с существующим `TestBrandsHasStockGate`.
- Pre-implementation (red): запуск нового `test_is_featured_does_not_affect_retrieve_action` на текущем коде → должен возвращать 404 (failure expected).
- Post-implementation (green): targeted suite + products regression.

## References

- Story-предшественник: `_bmad-output/implementation-artifacts/Story/catalog-hide-out-of-stock-brands.md` (run 4 фикс `has_stock`, run 5 finding по `is_featured`).
- Deferred work: `_bmad-output/implementation-artifacts/deferred-work.md` → раздел `code review of catalog-hide-out-of-stock-brands run 5 (2026-05-07)`.
- Существующий регрессионный тест-образец: `backend/apps/products/tests/test_brand_api.py::TestBrandsHasStockGate::test_has_stock_does_not_affect_retrieve_action`.
- Project info: `docs/PROJECT_INFO.md`.

## Open Questions

- (открыто) Нужно ли в этой story также вернуть `BadRequest 400` или `warning header` при отправке `is_featured`/`has_stock` на `retrieve`-URL (defensive contract), или достаточно молча игнорировать (текущее предлагаемое поведение)? Рекомендация — молча игнорировать, симметрично существующему `has_stock`-поведению, чтобы не ломать существующие интеграции.

## Change Log

| Дата | Версия | Описание | Автор |
|---|---:|---|---|
| 2026-05-07 | 0.1 | Создана из run 5 deferred-finding story `catalog-hide-out-of-stock-brands`. Baseline `22520173`. | Cascade |
