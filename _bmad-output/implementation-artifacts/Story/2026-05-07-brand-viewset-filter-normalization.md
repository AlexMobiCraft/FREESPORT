# Story: Нормализация query-фильтров `BrandViewSet` (`is_featured` / `has_stock`)

Status: done

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

- [x] **Task 1: Backend — объединить ветку `is_featured` с `has_stock` в `BrandViewSet.get_queryset`** (AC: 1, 2, 6, 7)
  - [x] 1.1: В `backend/apps/products/views.py` (`BrandViewSet.get_queryset`, ~lines 388–404) заменить структуру с двумя ветками (`if self.action != "featured":` для `is_featured` и `if self.action == "list":` для `has_stock`) на единый блок `if self.action == "list":` с обоими фильтрами внутри. Целевой код:
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
  - [x] 1.2: Убедиться, что импорты `Exists`, `OuterRef`, `Product` уже присутствуют в `views.py` (см. существующий код run 4). НЕ дублировать импорты.
  - [x] 1.3: Обновить docstring метода (с «Активные бренды; has_stock применяется только к list action» → «Активные бренды; is_featured и has_stock применяются только к list action»).
  - [x] 1.4: НЕ затрагивать `featured`-action: новая структура (`if self.action == "list":`) короткозамыкает все detail/featured/future actions автоматически.

- [x] **Task 2: Backend — обновить `@extend_schema` `BrandViewSet.list` для `is_featured`** (AC: 3, 4, 5, 9)
  - [x] 2.1: В `backend/apps/products/views.py` (`@extend_schema(... parameters=[...])` на `BrandViewSet.list`, ~lines 406–429) уточнить description параметра `is_featured`, явно зафиксировав, что фильтр применяется **только** в `list`-action. Рекомендуемая формулировка:
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
    Для справки — текущий стиль description `has_stock` (run 3, не менять):
    ```python
    description=(
        "Возвращать только бренды, у которых есть активные товары с вариантами в наличии "
        "(stock_quantity > 0). Применяется только при значении true/1. Любое другое значение "
        "(включая false/0) эквивалентно отсутствию параметра и не возвращает бренды без "
        "in-stock товаров."
    )
    ```
    Семантика `is_featured` отличается (`false` — валидное значение, фильтрующее не-featured бренды), поэтому формулировка симметрична по структуре, но не по содержанию gate-семантики.
  - [x] 2.2: Сохранить семантику `list`-контракта: `?is_featured=true|false|None` работает как раньше; AC3-AC5 защищают существующее поведение коллекции.
  - [x] 2.3: Не менять description `has_stock` (он уже корректно описывает gate-семантику после run 3 предыдущей story).

- [x] **Task 3: Backend — регрессионный тест `is_featured` на `retrieve`** (AC: 1, 2)
  - [x] 3.1: В `backend/apps/products/tests/test_brand_api.py` добавить тест `test_is_featured_does_not_affect_retrieve_action` в существующий класс `TestBrandsHasStockGate` (рядом с `test_has_stock_does_not_affect_retrieve_action`) — это сохраняет co-location симметричных регрессий, либо завести новый класс `TestBrandRetrieveQueryParams` если так удобнее.
  - [x] 3.2: Тестовые сценарии (в одном `@pytest.mark.django_db` тесте или двух — на усмотрение реализатора):
    - Создать `BrandFactory(name="Nike", slug="nike", is_featured=False)`. `GET /api/v1/brands/nike/?is_featured=true` → `status_code == 200`, `data["name"] == "Nike"`.
    - Создать `BrandFactory(name="Adidas", slug="adidas", is_featured=True)`. `GET /api/v1/brands/adidas/?is_featured=false` → `status_code == 200`, `data["name"] == "Adidas"`.
  - [x] 3.3: Тест помечен `@pytest.mark.django_db` + `@pytest.mark.integration` (использует `APIClient`) — соответствует правилу проекта (см. `AGENTS.md` секция «Кастомные маркеры pytest»).
  - [x] 3.4: Pre-implementation (red): запустить новый тест на текущем коде → ожидать **404** (failure expected), что подтверждает баг и адекватность теста.

- [x] **Task 4: Backend — регрессионные тесты `list + is_featured`** (AC: 3, 4, 5)
  - [x] 4.1: Проверить покрытие existing `is_featured` поведения для `list`-action в `backend/apps/products/tests/test_brand_api.py` через `grep` по `is_featured`. Если тестов нет — добавить (рядом с `TestBrandsHasStockGate` или в отдельном классе `TestBrandsIsFeaturedFilter`):
    - `test_list_is_featured_true_returns_only_featured_brands` (AC3): два бренда `Nike(False)` и `Adidas(True)` → `?is_featured=true` возвращает только `Adidas`.
    - `test_list_is_featured_false_returns_only_non_featured_brands` (AC4): `?is_featured=false` возвращает только `Nike`.
    - `test_list_without_is_featured_returns_all_active_brands` (AC5): без параметра возвращаются оба активных бренда.
  - [x] 4.2: Если такие тесты уже существуют — НЕ дублировать; убедиться, что они зелёные после изменения `get_queryset`.
  - [x] 4.3: Все тесты помечены `@pytest.mark.django_db` + `@pytest.mark.integration`.

- [x] **Task 5: Backend — подтверждение `featured` action и кэша** (AC: 6)
  - [x] 5.1: Убедиться, что existing `TestFeaturedBrandsEndpoint` и `TestFeaturedBrandsCaching` (в `test_brand_api.py`) проходят без изменений на новом `get_queryset`.
  - [x] 5.2: Добавить **обязательный** регрессионный тест `test_featured_action_ignores_is_featured_query_param` в `TestFeaturedBrandsEndpoint` (или новый класс), напрямую защищающий AC6:
    - `GET /api/v1/brands/featured/?is_featured=false` возвращает тот же набор featured брендов, что и `GET /api/v1/brands/featured/`.
    - Дополнительно проверить, что `?has_stock=true` к `/brands/featured/` не меняет ответ (симметричная защита AC6 для `has_stock`).
    - Тест помечен `@pytest.mark.django_db` + `@pytest.mark.integration`.
  - [x] 5.3: Подтвердить, что `FEATURED_BRANDS_CACHE_KEY` не загрязняется query-параметрами (cache key namespaced и не зависит от request query).

- [x] **Task 6: Verification и docs-sync** (AC: 9)
  - [x] 6.1: Если description `is_featured` в `@extend_schema` изменён — запустить `make docs-sync-api` для синхронизации OpenAPI-схемы.
  - [x] 6.2: Запуск targeted suite (Docker через `docker-compose.test.yml`):
    ```bash
    docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
      pytest apps/products/tests/test_brand_api.py -m "unit or integration" -x -q
    ```
  - [x] 6.3: Запуск products regression:
    ```bash
    docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
      pytest apps/products -m "unit or integration" -x -q
    ```
  - [x] 6.4: Подтвердить: нет diff'а во `frontend/`, нет новых миграций в `backend/apps/products/migrations/`, не изменены `Brand`-модель, `BrandSerializer`, `BrandFeaturedSerializer`, `BrandPageNumberPagination`, URLs.

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
| 2026-05-07 | 0.2 | Validate-create-story исправления: (1) Task 2.1 диапазон строк `:406–427` → `:406–429`, добавлена цитата текущего `has_stock` description и пояснение асимметрии семантики; (2) Task 5.2 переведён из «опционально» в обязательный регрессионный тест с прямой защитой AC6, добавлен Task 5.3 на изоляцию cache key от query-параметров. | Cascade (bmad-validate-create-story) |
| 2026-05-07 | 1.0 | Реализована нормализация `BrandViewSet`: `is_featured` и `has_stock` применяются только к `list`; добавлены regression-тесты retrieve/list/featured и выполнена валидация. | Codex (bmad-dev-story) |
| 2026-05-07 | 1.1 | Закрыт review patch AC6: тест `featured` теперь очищает кэш между plain/query вызовами и проверяет uncached путь с query-параметрами. Story переведена в review. | Codex (bmad-dev-story) |
| 2026-05-07 | 1.2 | Code review run 2 (Blind Hunter + Edge Case Hunter + Acceptance Auditor): 1 patch (revert `frontend/tsconfig.json`), 2 defer (OpenAPI `has_stock` description, out-of-scope `test_visible_brands` тест), 5 dismissed. Run 1 patch AC6 confirmed RESOLVED. Patch оставлен как action item, story → in-progress. | Cascade (bmad-code-review) |
| 2026-05-07 | 1.3 | Закрыт review patch AC8: `frontend/tsconfig.json` возвращён к baseline-форматированию, итоговый story diff больше не затрагивает frontend. Story переведена в review. | Codex (bmad-dev-story) |
| 2026-05-07 | 1.4 | Code review run 3 (Blind Hunter + Edge Case Hunter + Acceptance Auditor inline): ✅ Clean review, 0 patch / 0 decision-needed / 0 новых defer. Все потенциальные findings — дубликаты defer/dismiss из Run 1/2. Run 1 patch AC6 и Run 2 patch AC8 подтверждены как RESOLVED. Story → done. | Cascade (bmad-code-review) |

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Добавить regression-тест, который воспроизводит 404 на `retrieve(slug)` при несовпадающем `is_featured`.
- Сохранить backward compatibility `list` через отдельные тесты `is_featured=true`, `is_featured=false`, без параметра.
- Защитить `featured` action тестом на игнорирование `is_featured`/`has_stock` query-параметров и стабильность `FEATURED_BRANDS_CACHE_KEY`.
- Свести фильтрацию `BrandViewSet.get_queryset` к единственной ветке `if self.action == "list":` и обновить OpenAPI description `is_featured`.

### Debug Log References

- `docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml up -d backend` → тестовый backend-контейнер поднят.
- RED: `pytest apps/products/tests/test_brand_api.py::TestBrandsHasStockGate::test_is_featured_does_not_affect_retrieve_action -m "unit or integration" -x -v` → ожидаемо упал: `404 == 200`.
- GREEN: тот же targeted test → `1 passed`.
- Targeted suite: `pytest apps/products/tests/test_brand_api.py -m "unit or integration" -x -q` → `13 passed, 30 deselected`.
- Products regression: `pytest apps/products -m "unit or integration" -x -q` → `186 passed, 199 deselected`.
- `make -C .. docs-sync-api` → не выполнен: `make` не установлен в Windows-среде.
- Эквивалент target: `python ..\scripts\docs\docs_sync.py api-sync` → успешно, рассинхрона не найдено.
- `black --check apps/products/views.py apps/products/tests/test_brand_api.py` → passed.
- `flake8 apps/products/views.py apps/products/tests/test_brand_api.py` → passed.
- Scope-check: `git diff --name-only -- ..\frontend ..\backend\apps\products\migrations apps\products\models.py apps\products\serializers.py apps\products\urls.py` → пустой вывод.
- Review patch baseline: `pytest apps/products/tests/test_brand_api.py::TestFeaturedBrandsEndpoint::test_featured_action_ignores_is_featured_and_has_stock_query_params -m "unit or integration" -x -v` → `1 passed` до усиления теста (подтверждена слабость проверки из review finding).
- Review patch green: тот же targeted test после `cache.clear()` между plain/query вызовами → `1 passed`.
- Targeted suite после review patch: `pytest apps/products/tests/test_brand_api.py -m "unit or integration" -x -q` → `13 passed, 30 deselected`.
- Products regression после review patch: `pytest apps/products -m "unit or integration" -x -q` → `186 passed, 199 deselected`.
- Container docs-sync attempt: `docker compose ... exec -T backend python ../scripts/docs/docs_sync.py api-sync` → не выполнен: `/app/../scripts/docs/docs_sync.py` не найден в test-контейнере.
- Эквивалент target после review patch: `python ..\scripts\docs\docs_sync.py api-sync` → успешно, рассинхрона не найдено.
- `black --check apps/products/views.py apps/products/tests/test_brand_api.py` → passed после review patch.
- `flake8 apps/products/views.py apps/products/tests/test_brand_api.py` → passed после review patch.
- Scope-check после review patch: `git diff --name-only -- ..\frontend ..\backend\apps\products\migrations apps\products\models.py apps\products\serializers.py apps\products\urls.py` → пустой вывод.
- Review patch AC8: `frontend/tsconfig.json` возвращён к baseline `22520173`; `git diff 22520173 -- ..\frontend\tsconfig.json` → пустой вывод.
- Targeted suite после AC8 patch: `pytest apps/products/tests/test_brand_api.py -m "unit or integration" -x -q` → `13 passed, 30 deselected`.
- Products regression после AC8 patch: `pytest apps/products -m "unit or integration" -x -q` → `186 passed, 199 deselected`.
- `black --check apps/products/views.py apps/products/tests/test_brand_api.py` → passed после AC8 patch.
- `flake8 apps/products/views.py apps/products/tests/test_brand_api.py` → passed после AC8 patch.
- `python ..\scripts\docs\docs_sync.py api-sync` → успешно после AC8 patch, рассинхрона не найдено.
- Scope-check после AC8 patch: `git diff --name-only 22520173 -- ..\frontend ..\backend\apps\products\migrations apps\products\models.py apps\products\serializers.py apps\products\urls.py` → пустой вывод.

### Completion Notes List

- `BrandViewSet.get_queryset` теперь применяет оба query-фильтра (`is_featured`, `has_stock`) только для `list`, поэтому `retrieve(slug)` идентифицирует бренд только по slug.
- OpenAPI description для `is_featured` уточняет, что параметр является list-only и игнорируется на retrieve-эндпоинте.
- Добавлены integration regression-тесты для `retrieve + is_featured`, `list + is_featured=true|false|None`, `featured + is_featured/has_stock`.
- `featured` action и кэш не менялись; тест подтверждает стабильный `FEATURED_BRANDS_CACHE_KEY` при query-параметрах.
- Review patch AC6 закрыт: тест `featured` теперь очищает кэш между plain и query запросами, поэтому query-вызов проверяет uncached обработку `self.action == "featured"`, а не short-circuit из первого ответа.
- Review patch AC8 закрыт: `frontend/tsconfig.json` восстановлен к baseline-форматированию, поэтому итоговый story diff больше не затрагивает frontend.
- Миграции, модели, сериализаторы, пагинация и URLs не изменялись.

### File List

- `backend/apps/products/views.py`
- `backend/apps/products/tests/test_brand_api.py`
- `frontend/tsconfig.json` (revert к baseline; в итоговом baseline-diff отсутствует)
- `_bmad-output/implementation-artifacts/Story/2026-05-07-brand-viewset-filter-normalization.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Review Findings

_Source: bmad-code-review (2026-05-07), reviewers: Blind Hunter + Edge Case Hunter + Acceptance Auditor (выполнены вручную в основной сессии — все три subagent упали с API 529 Overloaded). Baseline: `22520173` (run 4 catalog-hide-out-of-stock-brands). HEAD: `c37ad0b8` + uncommitted v1.0 patch._

- [x] [Review][Patch] **AC6 cache short-circuit ослабляет верификацию: второй GET в `test_featured_action_ignores_is_featured_and_has_stock_query_params` обслуживается из кэша первого GET** [`backend/apps/products/tests/test_brand_api.py:168-181`] — После `cache.clear()` первый `self.client.get(FEATURED_URL)` заполняет `FEATURED_BRANDS_CACHE_KEY`. Второй GET с `{"is_featured": "false", "has_stock": "true"}` обслуживается из кэша (handler `featured` имеет `cache.get → Response(cached)` short-circuit), поэтому `assert response_filtered.data == response_plain.data` тривиально true и не проверяет, что `get_queryset()` для `self.action == "featured"` действительно игнорирует query-параметры. AC6 формально met (cache key не зависит от query, что подтверждается), но spec-инвариант («`get_queryset` для `featured` отрабатывает базовый querysset» Dev Notes §2) защищён слабее — регрессия в queryset-обработчике для featured могла бы пройти. Усиление: вставить `cache.clear()` между двумя GET; или сделать два независимых вызова с `cache.clear()` перед каждым и сравнить payload. Resolved: добавлен `cache.clear()` между plain/query вызовами; query-вызов теперь заново строит payload и снова заполняет `FEATURED_BRANDS_CACHE_KEY`.
- [x] [Review][Defer] **Парсинг `is_featured` принимает только `"true"|"1"`; любые другие значения (включая `""`, `"yes"`, `"on"`, `"FALSE"`) тихо мапятся в `False` и фильтруют не-featured бренды** [`backend/apps/products/views.py:392-394`] — Pre-existing: введено до этой story (run 4 ограничил `has_stock` действием list, но парсинг `is_featured` остался прежним). Симметрично pre-existing поведению `has_stock`-парсинга, но семантика `is_featured` не gate-типа и невалидное значение не должно тихо превращаться в `False`. Не покрыто тестами на noncanonical input. Решать единой story по валидации/нормализации query-параметров `BrandViewSet` (`is_featured`/`has_stock`/будущие).
- [x] [Review][Defer] **`@pytest.mark.integration` применён только к новому тесту `test_featured_action_ignores_is_featured_and_has_stock_query_params`, а не ко всему `TestFeaturedBrandsEndpoint`** [`backend/apps/products/tests/test_brand_api.py:167`] — Маркер на новом тесте корректен по spec Task 5.2 (явное требование). Несогласованность сидит в pre-existing тестах класса `TestFeaturedBrandsEndpoint`, которые помечены только `@pytest.mark.django_db` без `@pytest.mark.integration`, хотя используют `APIClient` + кэш + БД — это integration. Не введено этим diff. Решать при общем рефакторинге test-маркировок класса (поднять маркер на класс, как сделано в `TestBrandsHasStockGate` / `TestBrandsIsFeaturedFilter`).

_Run 1 dismissed: 3 findings (1) OpenAPI `is_featured` description не документирует loose-parsing — описание обновлено по рекомендованной spec формулировке Task 2.1, явно одобрено spec; (2) `BrandFactory` не задаёт `is_featured` по умолчанию — out-of-scope, тесты явно передают значение; (3) `_brand_names` не валидирует pagination structure — в новых тестах создаётся 2 бренда, pagination не делит, reasonable assumption._

_Run 2: bmad-code-review (2026-05-07), reviewers: Blind Hunter + Edge Case Hunter + Acceptance Auditor (general-purpose subagents, all three completed). Baseline `22520173` (run 4 catalog-hide-out-of-stock-brands). HEAD `265a2862` + uncommitted v1.1 patch (`cache.clear()` в featured-тесте). Run 1 patch AC6 confirmed RESOLVED аудитором._

- [x] [Review][Patch] **`frontend/tsconfig.json` cosmetic reformat нарушает AC8 «не трогать frontend»** [`frontend/tsconfig.json`] — Diff baseline → HEAD содержит переформатирование multi-line arrays в single-line (lib, types, paths, exclude). Без функциональных изменений, но AC8 + Anti-patterns story («Не трогать frontend») явно запрещают любые изменения во `frontend/`. Также делает Debug Log claim Task 6.4 (`scope-check ... → пустой вывод`) формально неверным. Реверт: `git checkout 22520173 -- frontend/tsconfig.json`. Resolved: файл восстановлен к baseline-форматированию через обратную правку; `git diff 22520173 -- ..\frontend\tsconfig.json` и общий scope-check по `..\frontend` дают пустой вывод.
- [x] [Review][Defer] **OpenAPI description `has_stock` самопротиворечив** [`backend/apps/products/views.py:421-426`] — Текст «Любое другое значение (включая false/0) эквивалентно отсутствию параметра и не возвращает бренды без in-stock товаров» содержит противоречие: «эквивалентно отсутствию параметра» подразумевает возврат всех брендов, а «не возвращает бренды без in-stock товаров» — применение фильтра. Реальное поведение (тест `test_has_stock_false_returns_all_active_brands`): `?has_stock=false` возвращает все активные бренды. Pre-existing (введено в run 3 предшественника `catalog-hide-out-of-stock-brands`, не модифицировано этой story). Корректная формулировка: «...эквивалентно отсутствию параметра — фильтр не применяется и возвращаются все активные бренды». Решать единой правкой OpenAPI описаний BrandViewSet.
- [x] [Review][Defer] **`test_visible_brands.py::test_returns_empty_brand_ids_for_nonexistent_category_id` out-of-scope для текущей story** [`backend/apps/products/tests/test_visible_brands.py:84-89`] — Тест добавлен в коммит `265a2862` brand-viewset-filter-normalization, но защищает поведение `visible_brands` action на `ProductViewSet`, явно в `НЕ затрагивается` секции story (line 161). Тест функционально корректен и защищает реальное поведение (`?category_id=999999` возвращает 200 OK с пустым `brand_ids`). Удалять не нужно — добавить в File List предшественника `catalog-hide-out-of-stock-brands` при ретроспективе для traceability.

_Run 2 dismissed: 5 findings:_

_(1) **Forward-compat regression на `if self.action == "list":`** (blind+edge) — намеренный дизайн-выбор, явно одобренный Dev Notes §1 critical invariants и Anti-patterns story («Использовать строго `if self.action == "list":` (whitelist для list-only фильтров) — это паттерн, защищающий future actions от регрессии»). Будущие detail-style actions должны opt-OUT по умолчанию by design._

_(2) **`cache.clear()`-патч ослабил cache short-circuit верификацию** (blind+edge) — AC6 требует именно: «кэш не загрязняется и не зависит от query-параметров». Тест после run 1 fix проверяет оба инварианта: (a) cache key одинаковый для plain/query (финальное `cache.get == cached_payload_plain`); (b) get_queryset для featured игнорирует query (equality payload после fresh build). Cache short-circuit при warm cache — отдельное property, не входящее в AC6._

_(3) **`is_featured` парсинг silent-tolerance (`""`, `"yes"`, `"on"`, `"FALSE"`)** (blind+edge) — duplicate с уже зафиксированным run 1 defer #2 («Парсинг `is_featured` принимает только `"true"|"1"`...»). Не дублируем._

_(4) **`_brand_names` paginated assumption vs flat list в featured-тестах** (blind) — false positive. `/api/v1/brands/` (paginated, response.data["results"]) и `/api/v1/brands/featured/` (flat list, response.data) — разные endpoints с разной формой ответа. Тесты обращаются к разным URL, противоречия нет._

_(5) **Fixture name `setup` collision с pytest hook** (blind) — pre-existing project pattern (используется в `TestBrandsHasStockGate`, `TestFeaturedBrandsEndpoint`, `TestBrandSearch` уже). Не введено этим diff. Если бы было реальной проблемой — существующие тесты падали бы._

_Run 3: bmad-code-review (2026-05-07), reviewers: Blind Hunter + Edge Case Hunter + Acceptance Auditor (inline в основной сессии — параллельные субагенты недоступны в Cascade-окружении). Baseline `22520173`, scope: baseline → working tree (включает коммиты `265a2862` + `4d31448e` и uncommitted v1.3 AC8 patch). HEAD `4d31448e`._

**Outcome: ✅ Clean review.** 0 patch findings, 0 decision-needed, 0 новых defer. Все потенциальные findings — дубликаты уже зафиксированных в Run 1/2:

- silent parsing tolerance `is_featured` (`"yes"`, `"FALSE"`, whitespace) — дубликат Run 1 defer #2 / Run 2 dismissed #3;
- description `has_stock` self-contradictory — дубликат Run 2 defer #2;
- `test_returns_empty_brand_ids_for_nonexistent_category_id` out-of-scope — дубликат Run 2 defer #3;
- `@pytest.mark.integration` не на классе `TestFeaturedBrandsEndpoint` — дубликат Run 1 defer #3;
- forward-compat whitelist `if self.action == "list":` — дубликат Run 2 dismissed #1 (intended design);
- `cache.clear()` патч ослабил cache short-circuit verification — дубликат Run 2 dismissed #2 (AC6 защищает cache key + payload identity, не short-circuit).

**Подтверждены как RESOLVED аудитором:**
- Run 1 patch AC6: `cache.clear()` между plain/query вызовами в `test_featured_action_ignores_is_featured_and_has_stock_query_params` корректно проверяет, что `get_queryset()` для `featured` action игнорирует query-параметры (uncached путь).
- Run 2 patch AC8: `git diff 22520173 -- frontend/tsconfig.json` пуст; общий scope-check `frontend backend/apps/products/migrations models.py serializers.py urls.py` пуст.

**Acceptance verdict:** AC1–AC9 покрыты регрессионными тестами; targeted suite `13 passed`, products regression `186 passed`; lint (`black --check`, `flake8`) passed; OpenAPI sync через `python scripts/docs/docs_sync.py api-sync` (эквивалент `make docs-sync-api` в Windows) — нет рассинхрона.
