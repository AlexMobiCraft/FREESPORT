---
title: 'Первая страница выдачи каталога в серверном HTML'
type: 'feature'
created: '2026-09-25'
status: 'done'
baseline_commit: '9cc11f28'
review_loop_iteration: 0
context:
  - '{project-root}/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В серверном HTML `/catalog` товаров нет: выдачу грузит эффект клиента, поэтому поисковик без JS видит каталог без карточек, цен и ссылок `/product/<slug>`, а SSR на месте выдачи рисует «Товары не найдены».

**Approach:** Серверный `page.tsx` запрашивает первую страницу выдачи по `searchParams` теми же парсерами, что и клиент, и передаёт её в `CatalogPageClient` вместе с ключом фильтров. Клиент рендерит её сразу. Первый запрос товаров он пропускает, если его фильтры совпали с ключом и сохранённой сессии нет. Всё остальное клиент делает как сейчас.

## Boundaries & Constraints

**Always:**
- Серверный запрос анонимный. Если в запросе есть cookie `refreshToken`, сервер товары не грузит и клиент работает как сейчас: вошедший оптовик не должен видеть розничные цены.
- Клиент берёт серверную выдачу только для первого запуска `fetchProducts`, только при точном совпадении ключа и при отсутствии refresh-токена в `localStorage`/cookie. Во всех остальных случаях запрос идёт как раньше.
- Любой сбой серверного запроса (не 2xx, таймаут, сеть, неразрешимая категория в дереве, исключение) приводит к `initialProducts = null` и прежнему поведению. Страница не падает.
- Серверная и клиентская разметка первой отрисовки совпадают: без hydration mismatch и без скелетона поверх готовой выдачи.
- Запросы сайдбара (`visible-categories`, `visible-brands`) при использовании серверной выдачи уходят, как раньше.

**Ask First:** правка бэкенда; изменение логики канонизации URL, гейтов категории и бренда или `requestSeq`; серверный рендер по токену пользователя.

**Never:** SSR выдачи на ссылках с непустым `brand` (сервер отдаёт `null`); правка `/electric/catalog`; SSR заголовка H1 и дерева категорий; `fetch` кэш данных для выдачи (только `no-store`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Аноним, базовый каталог | `/catalog`, без cookie | В HTML 12 карточек со ссылками `/product/<slug>`, «Показано 12 из N»; клиент не зовёт `productsService.getAll` при загрузке | — |
| Категория / подборка / страница | `?category=obuv&page=2`, `?is_new=true` | Сервер берёт `category_id` из `categories-tree` и грузит выдачу; ключ совпадает с клиентским | slug нет в дереве → фильтр без `category_id` (как у клиента) |
| Вошедший пользователь | cookie `refreshToken` | `initialProducts = null`, поведение прежнее | — |
| Сессия только в localStorage | ключ совпал, refresh-токен есть | Клиент перезапрашивает выдачу с токеном | — |
| Бренд в URL | `?brand=nike` | `initialProducts = null` | — |
| Сбой бэкенда | 404 на `page=99`, 500, таймаут 3 с | `initialProducts = null`, клиент делает прежнее, включая сброс на 1-ю страницу | исключение глушится |
| Расхождение фильтров на клиенте | дерево категорий у клиента не загрузилось | Ключи разные → клиентский запрос; до его ответа видна серверная выдача | — |

</frozen-after-approval>

## Code Map

- `frontend/src/app/(blue)/catalog/page.tsx` — серверная страница: метаданные и `categories-tree` (`collectCategories`, `fetchCategoryNames`), сейчас рендерит `<CatalogPageClient />` без данных.
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` — `CatalogContent`: парсеры URL (`parsePageNumber`, `parseOrdering`, `parsePriceRange`, `parseInStock`), константы, `productFilters` (~1126), `fetchProducts` (~1177), эффект запуска (~1243), `renderProducts`.
- `frontend/src/services/productsService.ts` — тип `ProductFilters`. Axios шлёт фильтры как query и отбрасывает `undefined`.
- `frontend/src/stores/authStore.ts` — `getRefreshToken()` читает `localStorage`, cookie `refreshToken`/`accessToken`.
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx`, `metadata.test.ts` — существующие тесты: моки сервисов и `fetch`.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/app/(blue)/catalog/catalogQuery.ts` (новый, без `'use client'`) — перенести сюда из клиента `PAGE_SIZE`, `PRICE_MIN/MAX`, `DEFAULT_PRICE_RANGE`, `DEFAULT_ORDERING`, `ORDERING_OPTIONS`, тип `PriceRange` и парсеры. Добавить `buildInitialProductFilters(params, categoryId)` (повторяет `productFilters` клиента для состояния из URL) и `productFiltersKey(filters)` (стабильный ключ по отсортированным определённым полям). Тип `CatalogInitialProducts = { key, results, count }`. Цель — единый разбор на сервере и клиенте.
- [x] `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` — импортировать перенесённое. Принять проп `initialProducts?: CatalogInitialProducts | null` и пробросить его в `CatalogContent`. Инициализировать им `products`/`totalProducts`, хранить в ref. В `fetchProducts` забирать ref один раз: при совпадении ключа и отсутствии сохранённой сессии не ставить `isProductsLoading` и не звать `getAll`, сайдбар запрашивать как обычно.
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — `collectCategories` запоминает и `id`, метаданные не меняются. Добавить `fetchInitialProducts(params)`: cookie `refreshToken` или непустой `brand` → `null`; при `category` берётся id из дерева; `fetch` `/products/?…` с `cache: 'no-store'` и таймаутом 3000 мс; всё в try/catch → `null`. Страница становится `async` и передаёт `initialProducts`.
- [x] `frontend/src/app/(blue)/catalog/__tests__/catalogQuery.test.ts` (новый) — парсеры, `buildInitialProductFilters` (бейджи, `in_stock=false`, поиск короче 2 символов, категория), стабильность ключа.
- [x] `frontend/src/app/(blue)/catalog/__tests__/page.test.tsx` (новый) — строки матрицы на сервере: URL запроса, пропуск по cookie и бренду, `null` при не-2xx, сбое и таймауте, разрешение категории.
- [x] `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — добавить: совпавший ключ → карточки видны сразу, `getAll` не вызван, `getVisibleCategories` вызван; несовпавший ключ → `getAll` вызван; refresh-токен в localStorage → `getAll` вызван. Существующие тесты без правок.

**Acceptance Criteria:**
- Given собранный фронтенд и бэкенд с товарами, when `curl -s http://localhost:3000/catalog` без cookie, then в `<body>` есть названия товаров первой страницы и ссылки `/product/<slug>`.
- Given анонимный переход на `/catalog` в браузере, when страница гидрирована, then в консоли нет ошибок гидрации, скелетон выдачи не мигает, а `GET /api/v1/products/` из браузера не уходит до первого действия с фильтрами. Исключение — подборки (`is_new`/`is_hit`/`is_sale`): давний повторный запуск эффекта после загрузки дерева категорий шлёт второй запрос. Решение Alex от 2026-09-25 — оставить, запись в deferred-work.
- Given серверная выдача, when пользователь меняет фильтр, страницу или жмёт «назад» к исходному URL, then выдача грузится клиентом как сейчас.

## Design Notes

Ключ — единственный контракт между сервером и клиентом. Сервер строит фильтры из URL теми же парсерами, клиент сравнивает с ключом свой `productFilters` на момент первого `fetchProducts`, то есть уже после разрешения категории по дереву. Любое расхождение (кривой URL, упавшее дерево, StrictMode со вторым прогоном эффектов) безопасно откатывает на клиентский запрос.

```ts
// fetchProducts
const initial = initialProductsRef.current;
initialProductsRef.current = null;
const reuse = initial && initial.key === productFiltersKey(filters) && !hasStoredSession();
if (!reuse) setIsProductsLoading(true);
const [response] = await Promise.all([reuse ? initial : productsService.getAll(filters), /* сайдбар */]);
```

Итоги ревью (patch, 2026-09-25):

- Динамическая страница выполняется заново и на каждой клиентской навигации: `router.push` фильтров, переход по ссылке, префетч. Серверный запрос выдачи там только удваивал нагрузку и задерживал смену фильтра, поэтому он идёт лишь для документа. Next 15.5 вырезает `RSC` из `headers()`, так что признак — `Sec-Fetch-Dest`: у браузерного документа `document`, у fetch роутера `empty`, у ботов заголовка нет.
- «Назад» перемонтирует каталог с выдачей из кэша роутера. У выдачи есть одноразовый `token`, клиент хранит потраченные токены на уровне модуля и повторно их не использует.

## Verification

**Commands:**
- `cd frontend; npx vitest run "src/app/(blue)/catalog"` — expected: все тесты зелёные, существующие без правок
- `cd frontend; npm run lint; npx tsc --noEmit` — expected: без ошибок
- `docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend`, затем `curl -s http://localhost:3000/catalog` — expected: в ответе ≥1 `href="/product/`

**Manual checks (if no CLI):**
- Открыть `/catalog?category=<slug>` и `/catalog?is_new=true` анонимно: карточки видны сразу, в консоли нет hydration-warning, на вкладке Network нет запроса `products/` при загрузке.

## Suggested Review Order

**Серверная выдача: когда грузится**

- Точка входа: анонимная первая страница только для документа, любой сбой даёт null.
  [`page.tsx:164`](<../../frontend/src/app/(blue)/catalog/page.tsx#L164>)

- Навигации роутера отсекаются по Sec-Fetch-Dest, потому что RSC Next вырезает из headers().
  [`page.tsx:176`](<../../frontend/src/app/(blue)/catalog/page.tsx#L176>)

- Сессия в cookie и бренд в URL: сервер не рендерит.
  [`page.tsx:180`](<../../frontend/src/app/(blue)/catalog/page.tsx#L180>)

- Категория по slug берётся из того же кэшированного дерева, что и метаданные.
  [`page.tsx:191`](<../../frontend/src/app/(blue)/catalog/page.tsx#L191>)

- Ответ: ключ фильтров и одноразовый токен.
  [`page.tsx:219`](<../../frontend/src/app/(blue)/catalog/page.tsx#L219>)

**Контракт сервер ↔ клиент**

- Фильтры первого запроса по URL повторяют клиентский productFilters.
  [`catalogQuery.ts:109`](<../../frontend/src/app/(blue)/catalog/catalogQuery.ts#L109>)

- Стабильный ключ: сортировка полей, undefined отброшены, как в axios.
  [`catalogQuery.ts:140`](<../../frontend/src/app/(blue)/catalog/catalogQuery.ts#L140>)

**Клиент: использование выдачи**

- Решение о повторном использовании: свежий токен, совпавший ключ, нет сессии.
  [`CatalogPageClient.tsx:1161`](<../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L1161>)

- При повторном использовании нет скелетона и запроса getAll, сайдбар запрашивается как обычно.
  [`CatalogPageClient.tsx:1169`](<../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L1169>)

- Серверная выдача — начальное состояние, поэтому SSR и гидрация совпадают.
  [`CatalogPageClient.tsx:437`](<../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L437>)

- Потраченные токены на уровне модуля: «назад» из кэша роутера делает запрос.
  [`CatalogPageClient.tsx:106`](<../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L106>)

- Признак сессии тот же, что у AuthProvider: localStorage или cookie.
  [`CatalogPageClient.tsx:92`](<../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L92>)

**Тесты**

- Сторож согласованности ключа сервера и клиента на наборе URL.
  [`CatalogPage.test.tsx:2191`](<../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L2191>)

- Серверная часть: навигация, cookie, бренд, сбои, токен.
  [`page.test.tsx:45`](<../../frontend/src/app/(blue)/catalog/__tests__/page.test.tsx#L45>)

- Парсеры и ключ.
  [`catalogQuery.test.ts:17`](<../../frontend/src/app/(blue)/catalog/__tests__/catalogQuery.test.ts#L17>)
