---
title: 'Порядок категорий в каталоге задаётся владельцем, а не алфавитом'
type: 'feature'
created: '2026-10-09'
status: 'done'
baseline_commit: '02298949'
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Сайдбар `/catalog` показывает категории по алфавиту: `sortCategoryTree` пересортировывает дерево и игнорирует `sort_order`, по которому его уже упорядочил API. Владельцу нужен свой порядок.

**Approach:** Фронтенд перестаёт сортировать дерево сам и сохраняет порядок API; «Без категории» по-прежнему уходит в конец. Data-миграция по `onec_id` проставляет `sort_order` корневым категориям и подкатегориям «Фитнес и атлетика». Фильтр главной `is_homepage` сужается до корней витрины, чтобы подкатегории с `sort_order > 0` не попали на главную.

Корни витрины (дети якоря «СПОРТ»), по порядку: Единоборства, Фитнес и атлетика, Плавание, Спортивные игры, Детский транспорт, «Бассейны, пляж, аксессуары», Туризм, Спортивные комплексы и батуты, Гимнастика и танцы, Зимние товары, Оборудование. Внутри «Фитнес и атлетика»: Фитнес, «Акссесуары для фитнеса и атлетики» (так в 1С), Тяжелая атлетика, «Турники, брусья, упоры для отжимания».

## Boundaries & Constraints

**Always:** категории в миграции находятся по `onec_id`; если категории нет, миграция её пропускает и не падает (в тестовой БД их нет). Новый порядок появится и на главной, владелец согласовал. Корни, которые сейчас на главной (`sort_order > 0`), там и остаются.

**Ask First:** любое изменение модели `Category` (новые поля, смена `Meta.ordering`); правка сортировки в других местах кроме сайдбара `(blue)/catalog`.

**Never:** править прод-БД руками или через SSH; трогать электрическую тему `(electric)`; менять импорт 1С; переименовывать категории (опечатку «Акссесуары» не исправлять).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Порядок API | `getTree` отдаёт [Б, А] | сайдбар показывает Б, затем А | N/A |
| uncategorized | `uncategorized` пришёл первым | показан последним | N/A |
| Подкатегории | children в порядке API | порядок детей сохранён на всех уровнях | N/A |
| Главная, подкатегория | ребёнок корня витрины с `sort_order=3` | не входит в `?is_homepage=true` | N/A |
| Главная, корень | ребёнок «СПОРТ» с `sort_order=1` | входит в `?is_homepage=true` | N/A |
| Миграция, нет записи | `onec_id` нет в БД | запись пропущена, остальные обновлены | без исключения |

</frozen-after-approval>

## Code Map

- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:121` -- `sortCategoryTree`: алфавитная сортировка поверх порядка API, единственный вызов в :658. Impact LOW.
- `backend/apps/products/views.py:317` -- `CategoryTreeViewSet`: корни = дети якоря `settings.ROOT_CATEGORY_NAME`, `order_by("sort_order", "name")`.
- `backend/apps/products/serializers.py:871` -- дети дерева уже `order_by("sort_order", "name")`.
- `backend/apps/products/filters.py:502` -- `filter_is_homepage`: сейчас `sort_order__gt=0` на любом уровне. Impact LOW, единственный потребитель — `frontend/src/components/home/CategoriesSection.tsx:124`.
- `backend/apps/products/migrations/0053_seed_price_type_opt4.py` -- образец data-миграции; последняя миграция — `0056_onec_deleted_and_excluded_items`.
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx:532` -- образец тестов сайдбара через мок `categoriesService.getTree`.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` -- в `sortCategoryTree` убрать `localeCompare`; стабильный ранг: `sort_order > 0` → 0, `sort_order = 0` → 1, `uncategorized` → 2; рекурсию по детям сохранить; `sort_order` взять из ответа дерева (добавить в `CategoryNode` и в тип `Category` в `frontend/src/types/api.ts`) -- сайдбар следует `sort_order`, категории без порядка уходят в конец.
- [x] `backend/apps/products/filters.py` -- `filter_is_homepage`: дополнительно ограничить детьми активного якоря (`parent__name=ROOT_CATEGORY_NAME`, `parent__parent__isnull=True`, `parent__is_active=True`), как в `CategoryTreeViewSet`; условие вынести в helper `homepage_categories_q()` и использовать его же в `IsOnHomepageFilter` (`backend/apps/products/admin.py`) -- подкатегории с порядком не уходят на главную, админка показывает то же, что API.
- [x] `backend/apps/products/migrations/0057_catalog_category_order.py` -- RunPython: словарь `onec_id → sort_order` (корни 1–11, дети «Фитнес и атлетика» 1–4); `filter(onec_id=...).update(sort_order=...)`; reverse — `RunPython.noop` -- воспроизводимо доезжает до прода релизом.
- [x] `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` -- тесты: порядок корней и детей как в API, а не по алфавиту; `uncategorized` последней.
- [x] `backend/apps/products/tests/unit/test_category_homepage_filter.py` -- тесты фильтра: корень с `sort_order>0` входит, подкатегория с `sort_order>0` не входит, корень с `sort_order=0` не входит.

**Acceptance Criteria:**
- Given миграция применена на проде, when открыть `/catalog`, then корни идут в порядке из Intent (скрытые без наличия не показываются), а у «Фитнес и атлетика» дети — Фитнес, Акссесуары…, Тяжелая атлетика, Турники….
- Given миграция применена, when открыть главную, then в блоке категорий только корни витрины в новом порядке, подкатегорий нет.

## Spec Change Log

- **Итерация 1.** Находка ревью: API сортирует по возрастанию `sort_order`, и категории с `sort_order = 0` (новая группа 1С, пятая подкатегория) оказывались выше согласованного порядка. Кроме того, `IsOnHomepageFilter` в админке продолжал считать «на главной» любую категорию с `sort_order > 0`. Изменено: задачи фронтенда (ранг 0 → в конец) и фильтра (общий helper для API и админки). Предотвращено: новая категория из 1С наверху сайдбара; подкатегории фитнеса помечены в админке как выведенные на главную. KEEP: миграция 0057 по `onec_id` с пропуском отсутствующих; сужение `is_homepage` до детей активного якоря; тесты порядка через `#filter-categories`; `settings`-фикстура вместо `override_settings`.

## Design Notes

Компаратор — разность рангов (`sort_order > 0` → 0, `0` → 1, `uncategorized` → 2). `Array.prototype.sort` стабилен, поэтому внутри ранга сохраняется порядок API (`sort_order, name`).

`onec_id` (прод): Единоборства `3d148366-bd77-11e4-afc8-20cf3073dde3`; Фитнес и атлетика `3d148353-bd77-11e4-afc8-20cf3073dde3`; Плавание `442337ff-bd77-11e4-afc8-20cf3073dde3`; Спортивные игры `44233835-bd77-11e4-afc8-20cf3073dde3`; Детский транспорт `812018c4-bd77-11e4-afc8-20cf3073dde3`; Бассейны `3d148351-bd77-11e4-afc8-20cf3073dde3`; Туризм `3d148347-bd77-11e4-afc8-20cf3073dde3`; Спорт. комплексы `4a88ea7e-bd77-11e4-afc8-20cf3073dde3`; Гимнастика `4423384a-bd77-11e4-afc8-20cf3073dde3`; Зимние товары `4a88eab9-bd77-11e4-afc8-20cf3073dde3`; Оборудование `442337f8-bd77-11e4-afc8-20cf3073dde3`. Дети: Фитнес `9c5bad99-a802-11e7-8151-00155d87f90d`; Акссесуары `fbbe1b5c-bd77-11e4-afc8-20cf3073dde3`; Тяжелая атлетика `9c5bad95-a802-11e7-8151-00155d87f90d`; Турники `4a88e9f4-bd77-11e4-afc8-20cf3073dde3`.

«Сувенирная продукция» (неактивна, `sort_order=11`) миграцией не трогается: на витрину и главную она не попадает из-за `is_active=false`.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/products/tests/unit/test_category_homepage_filter.py apps/products/tests/test_visible_categories.py` -- expected: всё зелёное, миграция применилась при сборке тестовой БД.
- `cd frontend && npx vitest run "src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx"; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок.

## Suggested Review Order

**Порядок в сайдбаре каталога**

- Вход: ранг вместо алфавита — заданный порядок, потом без порядка, «Без категории» последней.
  [`CatalogPageClient.tsx:124`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L124)

- Стабильная сортировка сохраняет порядок API внутри ранга, рекурсивно по детям.
  [`CatalogPageClient.tsx:134`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L134)

- `sort_order` из ответа дерева попадает в узел сайдбара.
  [`CatalogPageClient.tsx:119`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L119)

**Данные порядка**

- Корни витрины 1–11 по `onec_id`; отсутствующие в БД пропускаются.
  [`0057_catalog_category_order.py:6`](../../backend/apps/products/migrations/0057_catalog_category_order.py#L6)

- Дети «Фитнес и атлетика» 1–4; на главную не уходят благодаря фильтру ниже.
  [`0057_catalog_category_order.py:21`](../../backend/apps/products/migrations/0057_catalog_category_order.py#L21)

**Главная не получает подкатегории**

- Единое правило главной: дети активного якоря с `sort_order > 0`.
  [`filters.py:486`](../../backend/apps/products/filters.py#L486)

- API `?is_homepage=true` использует правило.
  [`filters.py:526`](../../backend/apps/products/filters.py#L526)

- Фильтр админки «На главной» показывает то же, что API.
  [`admin.py:309`](../../backend/apps/products/admin.py#L309)

**Тесты и типы**

- Порядок корней и детей, нулевой `sort_order` и «Без категории» в конце.
  [`CatalogPage.test.tsx:633`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L633)

- Правило главной: корень, подкатегория, нулевой порядок, неактивный якорь.
  [`test_category_homepage_filter.py:30`](../../backend/apps/products/tests/unit/test_category_homepage_filter.py#L30)

- Админка «Да/Нет» совпадает с правилом главной.
  [`test_category_homepage_filter.py:78`](../../backend/apps/products/tests/unit/test_category_homepage_filter.py#L78)

- Опциональное `sort_order` в типе категории.
  [`api.ts:120`](../../frontend/src/types/api.ts#L120)
