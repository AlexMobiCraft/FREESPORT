# Story: Нормализация query-фильтров `BrandViewSet` (`is_featured` / `has_stock`)

Status: ready-for-dev

Source:
- `_bmad-output/implementation-artifacts/tech-spec/tech-spec-brand-viewset-filter-normalization.md`
- `_bmad-output/implementation-artifacts/Story/catalog-hide-out-of-stock-brands.md` (story-предшественник; run 4 ограничил `has_stock` действием `list`, run 5 явно вынес симметричный финдинг по `is_featured` в deferred)
- `_bmad-output/implementation-artifacts/deferred-work.md` (раздел `code review of catalog-hide-out-of-stock-brands run 5 (2026-05-07)`)

Baseline commit: `22520173b89b4374a6c0e0f8fa346e26fc508b52`

## Story

As a **API-консумер FREESPORT (frontend, интеграции, QA), использующий `GET /api/v1/brands/<slug>/`**,
I want **чтобы detail-эндпоинт идентифицировал бренд только по `slug` и не возвращал 404 при наличии «лишних» query-параметров `is_featured` / `has_stock`**,
so that **контракт detail-эндпоинта симметричен (`is_featured` и `has_stock` имеют смысл только для коллекции `list`), не зависит от случайных query-параметров и любые будущие detail-style action на `BrandViewSet` автоматически защищены от рассинхрона фильтров**.

## Acceptance Criteria

1. **AC1 (`retrieve` + `is_featured=true` для не-featured бренда):** Given бренд `Nike` активный с `is_featured=False`, when выполняется `GET /api/v1/brands/nike/?is_featured=true`, then ответ **200 OK** с телом, содержащим `name="Nike"` (не 404).
2. **AC2 (`retrieve` + `is_featured=false` для featured бренда):** Given бренд `Adidas` активный с `is_featured=True`, when выполняется `GET /api/v1/brands/adidas/?is_featured=false`, then ответ **200 OK** с `name="Adidas"`.
3. **AC3 (`list` + `is_featured=true` — backward compat):** Given в БД активные бренды `Nike` (`is_featured=False`) и `Adidas` (`is_featured=True`), when выполняется `GET /api/v1/brands/?is_featured=true`, then в ответе присутствует только `Adidas` (поведение `list` не меняется).
4. **AC4 (`list` + `is_featured=false` — backward compat):** `GET /api/v1/brands/?is_featured=false` возвращает только не-featured бренды (поведение `list` не меняется).
5. **AC5 (`list` без `is_featured` — backward compat):** `GET /api/v1/brands/` без параметра возвращает все активные бренды.
6. **AC6 (`featured` action не затронут):** Given реализована нормализация фильтров, when выполняется `GET /api/v1/brands/featured/` (с любыми query-параметрами, включая `?is_featured=false`, `?has_stock=true`), then возвращается кэшированный набор featured брендов; кэш `FEATURED_BRANDS_CACHE_KEY` не загрязняется и не зависит от query-параметров.
7. **AC7 (`retrieve` + `has_stock=true` — регрессия не вернулась):** Given бренд `Nike` без in-stock товаров, when выполняется `GET /api/v1/brands/nike/?has_stock=true`, then ответ **200 OK** (существующий тест `test_has_stock_does_not_affect_retrieve_action` проходит).
8. **AC8 (нет миграций, нет изменений модели и сериализаторов):** Story не добавляет миграций, не меняет `Brand` model, `BrandSerializer`, `BrandFeaturedSerializer`, `BrandPageNumberPagination`, URLs, frontend-код.
9. **AC9 (OpenAPI описание):** В `@extend_schema` action `list` description параметра `is_featured` явно фиксирует, что фильтр применяется **только** в `list`-action, симметрично текущей формулировке `has_stock`.

## Tasks / Subtasks

- [ ] **Task 1: Backend — объединить ветку `is_featured` с `has_stock` в `BrandViewSet.get_queryset`** (AC: 1, 2, 6, 7)
  - [ ] 1.1: В `backend/apps/products/views.py` (`BrandViewSet.get_queryset`, ~lines 388–404) заменить структуру с двумя ветками (`if self.action != "featured":` для `is_featured` и `if self.action == "list":` для `has_stock`) на единый блок `if self.action == "list":` с обоими фильтрами внутри. Целевой код:
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
  - [ ] 1.2: Убедиться, что импорты `Exists`, `OuterRef`, `Product` уже присутствуют в `views.py` (см. существующий код run 4). НЕ дублировать импорты.
  - [ ] 1.3: Обновить docstring метода (с «Активные бренды; has_stock применяется только к list action» → «Активные бренды; is_featured и has_stock применяются только к list action»).
  - [ ] 1.4: НЕ затрагивать `featured`-action: новая структура (`if self.action == "list":`) короткозамыкает все detail/featured/future actions автоматически.

- [ ] **Task 2: Backend — обновить `@extend_schema` `BrandViewSet.list` для `is_featured`** (AC: 3, 4, 5, 9)
  - [ ] 2.1: В `backend/apps/products/views.py` (`@extend_schema(... parameters=[...])` на `BrandViewSet.list`, ~lines 406–427) уточнить description параметра `is_featured`, явно зафиксировав, что фильтр применяется **только** в `list`-action. Рекомендуемая формулировка:
    ```python
    OpenApiParameter(
        "is_featured",
        OpenApiTypes.BOOL,
        description=(
            "Фильтр по featured-статусу бренда (true/false). "
            "Применяется только в list-action; для retrieve(slug)-эндпоинта "
            "параметр игнорируется и не влияет на поиск бренда."
        ),
    ),
    ```
  - [ ] 2.2: Сохранить семантику `list`-контракта: `?is_featured=true|false|None` работает как раньше; AC3-AC5 защищают существующее поведение коллекции.
  - [ ] 2.3: Не менять description `has_stock` (он уже корректно описывает gate-семантику после run 3 предыдущей story).

- [ ] **Task 3: Backend — регрессионный тест `is_featured` на `retrieve`** (AC: 1, 2)
  - [ ] 3.1: В `backend/apps/products/tests/test_brand_api.py` добавить тест `test_is_featured_does_not_affect_retrieve_action` в существующий класс `TestBrandsHasStockGate` (рядом с `test_has_stock_does_not_affect_retrieve_action`) — это сохраняет co-location симметричных регрессий, либо завести новый класс `TestBrandRetrieveQueryParams` если так удобнее.
  - [ ] 3.2: Тестовые сценарии (в одном `@pytest.mark.django_db` тесте или двух — на усмотрение реализатора):
    - Создать `BrandFactory(name="Nike", slug="nike", is_featured=False)`. `GET /api/v1/brands/nike/?is_featured=true` → `status_code == 200`, `data["name"] == "Nike"`.
    - Создать `BrandFactory(name="Adidas", slug="adidas", is_featured=True)`. `GET /api/v1/brands/adidas/?is_featured=false` → `status_code == 200`, `data["name"] == "Adidas"`.
  - [ ] 3.3: Тест помечен `@pytest.mark.django_db` + `@pytest.mark.integration` (использует `APIClient`) — соответствует правилу проекта (см. `AGENTS.md` секция «Кастомные маркеры pytest»).
  - [ ] 3.4: Pre-implementation (red): запустить новый тест на текущем коде → ожидать **404** (failure expected), что подтверждает баг и адекватность теста.

- [ ] **Task 4: Backend — регрессионные тесты `list + is_featured`** (AC: 3, 4, 5)
  - [ ] 4.1: Проверить покрытие existing `is_featured` поведения для `list`-action в `backend/apps/products/tests/test_brand_api.py` через `grep` по `is_featured`. Если тестов нет — добавить (рядом с `TestBrandsHasStockGate` или в отдельном классе `TestBrandsIsFeaturedFilter`):
    - `test_list_is_featured_true_returns_only_featured_brands` (AC3): два бренда `Nike(False)` и `Adidas(True)` → `?is_featured=true` возвращает только `Adidas`.
    - `test_list_is_featured_false_returns_only_non_featured_brands` (AC4): `?is_featured=false` возвращает только `Nike`.
    - `test_list_without_is_featured_returns_all_active_brands` (AC5): без параметра возвращаются оба активных бренда.
  - [ ] 4.2: Если такие тесты уже существуют — НЕ дублировать; убедиться, что они зелёные после изменения `get_queryset`.
  - [ ] 4.3: Все тесты помечены `@pytest.mark.django_db` + `@pytest.mark.integration`.

- [ ] **Task 5: Backend — подтверждение `featured` action и кэша** (AC: 6)
  - [ ] 5.1: Убедиться, что existing `TestFeaturedBrandsEndpoint` и `TestFeaturedBrandsCaching` (в `test_brand_api.py`) проходят без изменений на новом `get_queryset`.
  - [ ] 5.2: Опционально: если ещё нет — добавить `test_featured_action_ignores_is_featured_query_param` (`?is_featured=false` к `/brands/featured/` не меняет ответ). Этот тест может быть пропущен, если уже косвенно покрыт существующими `featured`-тестами.

- [ ] **Task 6: Verification и docs-sync** (AC: 9)
  - [ ] 6.1: Если description `is_featured` в `@extend_schema` изменён — запустить `make docs-sync-api` для синхронизации OpenAPI-схемы.
  - [ ] 6.2: Запуск targeted suite (Docker через `docker-compose.test.yml`):
    ```bash
    docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
      pytest apps/products/tests/test_brand_api.py -m "unit or integration" -x -q
    ```
  - [ ] 6.3: Запуск products regression:
    ```bash
    docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
      pytest apps/products -m "unit or integration" -x -q
    ```
  - [ ] 6.4: Подтвердить: нет diff'а во `frontend/`, нет новых миграций в `backend/apps/products/migrations/`, не изменены `Brand`-модель, `BrandSerializer`, `BrandFeaturedSerializer`, `BrandPageNumberPagination`, URLs.

## Dev Notes

### Архитектурный паттерн

Story закрывает симметричный pre-existing баг к story `catalog-hide-out-of-stock-brands` run 4 (`has_stock` ограничен `list`). Подход — единая ветка `if self.action == "list":` для всех query-фильтров `BrandViewSet`.

| Action | Применяются `is_featured`/`has_stock`? | Поведение |
|---|---|---|
| `list` | да (оба) | существующая семантика коллекции, backward compat |
| `retrieve(slug)` | **нет** (после фикса) | идентификация только по slug, query игнорируется, 200 OK |
| `featured` | нет (короткое замыкание через `action == "list"` is False) | кэш `FEATURED_BRANDS_CACHE_KEY` неизменен |
| любые будущие detail-style actions | **нет автоматически** | защита от рассинхрона фильтров by design |

### Критические инварианты (developer guardrails)

1. **Структура `if self.action == "list":` — единственная ветка с фильтрами.** Не добавлять новые фильтры в отдельные `if`-блоки с другим условием — это вернёт регрессию по симметрии.
2. **`featured`-action и его кэш не должны быть затронуты.** `get_queryset` для `featured` отрабатывает базовый `Brand.objects.active().order_by("name")`. Это инвариант run 4.
3. **Backward compatibility `list`-контракта.** AC3-AC5 фиксируют, что `?is_featured=true|false|None` для `list` работает как раньше. Тесты `Task 4` гарантируют это даже если изменилась только структура условий.
4. **Расширение, не сужение, для `retrieve`.** До фикса `GET /brands/<slug>/?is_featured=...` мог возвращать 404 для некоторых комбинаций, теперь будет 200. Любой клиент, ожидающий detail-объект по slug, остаётся совместим.
5. **Нет миграций, нет изменений модели, нет изменений frontend.** Scope строго ограничен `views.py` + `tests/test_brand_api.py`. AC8 защищает scope.
6. **Симметрия с `has_stock`-форматом.** Description `is_featured` в OpenAPI должен следовать стилю существующего `has_stock` description (run 3 формулировка: «Применяется только при значении... Любое другое значение... эквивалентно отсутствию параметра»), но с поправкой на семантику фильтра по boolean (для `is_featured` `false` валиден и фильтрует не-featured бренды, в отличие от gate-семантики `has_stock`).

### Anti-patterns (что НЕ делать)

- **Не возвращать `400 Bad Request` или warning-header при `?is_featured=...` на retrieve-URL.** Текущая рекомендация tech-spec — молча игнорировать, симметрично существующему `has_stock`-поведению, чтобы не ломать существующие интеграции (см. Open Questions tech-spec).
- **Не вводить новые ветки `if self.action != "featured":` для `is_featured`.** Использовать строго `if self.action == "list":` (whitelist для list-only фильтров) — это паттерн, защищающий future actions от регрессии.
- **Не менять модель `Brand`, не добавлять миграции, не трогать сериализаторы и URLs.**
- **Не трогать frontend.** Frontend сейчас не отправляет `is_featured` на retrieve-URL, контракт `list` не меняется — клиентских правок не требуется.
- **Не использовать `featured`-action для тестирования retrieve-логики `is_featured`.** `featured` — отдельный action с собственным кэшем; тесты должны бить именно `/api/v1/brands/<slug>/`.

### Затрагиваемые файлы (File List preview)

**Backend:**
- `backend/apps/products/views.py` — реструктуризация `BrandViewSet.get_queryset` (объединение веток `is_featured` и `has_stock` в общую `if self.action == "list":`); уточнение description `is_featured` в `@extend_schema(list)`.
- `backend/apps/products/tests/test_brand_api.py` — добавить регрессионный тест `test_is_featured_does_not_affect_retrieve_action`; при необходимости — тесты на `list + is_featured` (AC3-AC5), если они отсутствуют.

**НЕ затрагивается (AC8):**
- Frontend (никаких изменений).
- Миграции, модель `Brand`, `BrandSerializer`, `BrandFeaturedSerializer`, `BrandPageNumberPagination`, URLs.
- `featured`-action и его кэш.
- `visible_brands`-action на `ProductViewSet`.

### Backward compatibility и риски

- **Контракт `list` неизменён:** `?is_featured=true|false` работает как раньше; AC3-AC5 явно защищают семантику.
- **Контракт `retrieve` строго расширяется:** до фикса некоторые комбинации возвращали 404, теперь будут 200. Совместимо с любым клиентом, ожидающим detail-объект по slug.
- **`featured`-кэш:** изменение находится только в ветке `if self.action == "list":`; для `featured`-action `get_queryset` отрабатывает базовый `Brand.objects.active().order_by("name")` — поведение и кэш сохраняются.
- **OpenAPI:** description `is_featured` уточняется (применимость к `list`-action). После изменений — `make docs-sync-api`.
- **Будущие action на `BrandViewSet`:** новый паттерн (`if self.action == "list":`) явно ограничивает фильтры коллекцией. Любые будущие detail-style action автоматически защищены от рассинхрона.

### Тестовые стандарты

- Backend: `pytest` с маркерами `@pytest.mark.django_db` + `@pytest.mark.integration` (через `APIClient`). Размещение — `backend/apps/products/tests/test_brand_api.py` рядом с существующим `TestBrandsHasStockGate::test_has_stock_does_not_affect_retrieve_action` (этот тест — образец стиля и структуры).
- Локализация: comments / docstrings новых тестов и docstring `get_queryset` — на русском языке (см. `AGENTS.md` `document_output_language: Russian`).
- Pre-implementation (red): запуск нового `test_is_featured_does_not_affect_retrieve_action` на текущем коде → должен возвращать 404 (failure expected).
- Post-implementation (green): targeted suite + products regression.

### References

- Tech-spec: `_bmad-output/implementation-artifacts/tech-spec/tech-spec-brand-viewset-filter-normalization.md`
- Story-предшественник: `_bmad-output/implementation-artifacts/Story/catalog-hide-out-of-stock-brands.md` (run 4 фикс `has_stock`, run 5 finding по `is_featured` в Review Findings).
- Образец регрессионного теста: `backend/apps/products/tests/test_brand_api.py::TestBrandsHasStockGate::test_has_stock_does_not_affect_retrieve_action`.
- Целевой код (фрагмент `views.py`): `backend/apps/products/views.py:388-404` (`BrandViewSet.get_queryset`) и `:406-429` (`BrandViewSet.list @extend_schema`).
- Deferred work контекст: `_bmad-output/implementation-artifacts/deferred-work.md` → раздел `code review of catalog-hide-out-of-stock-brands run 5 (2026-05-07)`.
- Project info: `docs/PROJECT_INFO.md` (стек, команды запуска тестов).
- AGENTS guide: `AGENTS.md` (русский язык документации, кастомные маркеры `unit`/`integration`, команды `make docs-sync-api`, тестирование через Docker).

### Project Structure Notes

Story не вносит структурных изменений:
- Backend: реструктуризация ОДНОГО метода `BrandViewSet.get_queryset` и уточнение ОДНОГО description в `@extend_schema`. Никаких новых модулей/папок.
- Тесты: расширение существующего `test_brand_api.py` ОДНИМ-двумя тестами в существующем (или новом одиночном) классе.
- Frontend / миграции / модели: не затрагиваются (AC8).

## Testing

### Pre-Implementation (red)

Запустить ДО реализации, чтобы убедиться, что новый тест падает на текущем коде:

```bash
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
  pytest apps/products/tests/test_brand_api.py::TestBrandsHasStockGate::test_is_featured_does_not_affect_retrieve_action \
         -m "unit or integration" -x -v
```

Ожидаемый результат: тест падает (404 вместо 200). Если тест зелёный на текущем коде — баг не воспроизведён, проверить корректность фикстур (`is_featured=False` для `Nike`, `is_featured=True` для `Adidas`).

### Post-Implementation (green)

```bash
# Backend (targeted: brand API)
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
  pytest apps/products/tests/test_brand_api.py -m "unit or integration" -x -q

# Backend (regression — весь products)
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
  pytest apps/products -m "unit or integration" -x -q

# OpenAPI sync (если description is_featured изменён)
make docs-sync-api
```

### Manual checks (smoke)

- `GET /api/v1/brands/nike/?is_featured=true` для бренда `Nike` с `is_featured=False` → **200 OK**, `name="Nike"`.
- `GET /api/v1/brands/adidas/?is_featured=false` для бренда `Adidas` с `is_featured=True` → **200 OK**, `name="Adidas"`.
- `GET /api/v1/brands/?is_featured=true` → только featured бренды (backward compat).
- `GET /api/v1/brands/?is_featured=false` → только не-featured (backward compat).
- `GET /api/v1/brands/` → все активные (backward compat).
- `GET /api/v1/brands/featured/?is_featured=false&has_stock=true` → стандартный кэшированный ответ featured-эндпоинта (не зависит от query).
- `GET /api/v1/brands/nike/?has_stock=true` для `Nike` без in-stock товаров → **200 OK** (регрессия run 4 не вернулась).

## Change Log

| Дата | Версия | Описание | Автор |
|---|---:|---|---|
| 2026-05-07 | 0.1 | Story создана из tech-spec `tech-spec-brand-viewset-filter-normalization.md` (run 5 deferred-finding по story `catalog-hide-out-of-stock-brands`). Baseline `22520173`. | Cascade (bmad-create-story) |

## Dev Agent Record

### Agent Model Used

_To be filled during implementation_

### Debug Log References

### Completion Notes List

### File List
