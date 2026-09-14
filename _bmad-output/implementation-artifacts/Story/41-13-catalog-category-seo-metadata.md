# Story 41.13: SEO-метаданные индексируемых категорий каталога

Status: done
Baseline Revision: 361f0f565f0bea196da31fc3c5a95c6c432fff95
Followup Review Recommended: true

## Story

As a посетитель, который находит спортивные товары через поисковую систему,
I want чтобы каждая публичная категория каталога имела собственные серверные метаданные и canonical,
so that я попадал на релевантную категорию, а служебные фильтры не становились отдельными посадочными страницами.

**Закрывает:** FR-41-29.

## Утверждённые решения владельца

Решения утверждены Alex 14.09.2026 и снимают блокировку исходной постановки:

1. Индексируемыми считаются адреса категорий **публичного дерева** `/api/v1/categories-tree/` — корни витрины (прямые дети якоря «СПОРТ») и все их потомки. Валидность slug и его `name` подтверждаются присутствием узла в ответе дерева; отдельный запрос к `/api/v1/categories/{slug}/` не требуется. Slug вне публичного дерева (неизвестные, неактивные, устаревшие, якорь «СПОРТ» и прочие активные узлы 1С, не показанные в витрине) не получают собственных метаданных и не добавляются в sitemap.
2. Шаблоны метаданных категории утверждены дословно:
   - `title`: `<Название категории> — спортивные товары`;
   - `description`: `Спортивные товары категории «<Название категории>» в каталоге OPTISPORT: информация о товарах, ценах и условиях заказа для розничных и оптовых покупателей.`
   Описание не обещает наличие товаров. Осознанно длиннее типичного SERP-лимита (~160 символов) — шаблон утверждён дословно, усечение в выдаче приемлемо.
3. Собственные метаданные категории формируются только при **ровно одном** непустом параметре `category`, slug которого присутствует в публичном дереве. При повторяющемся параметре (`?category=a&category=b`, включая два одинаковых значения), slug вне дерева или ошибке API используются базовые метаданные каталога и canonical `/catalog`.
4. При одной валидной категории любые остальные query-параметры не входят в canonical: canonical содержит только `category`.
5. Для страницы валидной категории итоговые metadata явно содержат `keywords: null`: это сбрасывает как каталожные, так и глобальные `keywords`, наследуемые из корневого layout. Основной `/catalog` сохраняет утверждённые keywords из AC2.
6. Единый таймаут серверной загрузки дерева для `generateMetadata` и sitemap — `const CATEGORY_TREE_FETCH_TIMEOUT_MS = 3000;`. По истечении 3000 мс применяется fail-soft соответствующей поверхности: metadata AC2 либо sitemap без блока категорий.
7. Проверяющий сервис идентифицирован по production access log как `AuditikBot/1.0`: 10.09.2026 он выполнил обход с `12:09:59` до `12:11:37` UTC, за три секунды до времени отчёта `12:11:40`, с User-Agent `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 AuditikBot/1.0 (+https://auditikk.ru/bot)`. Для `AuditikBot` и штатных HTML-limited ботов Next.js metadata должны формироваться блокирующе и находиться в `<head>`. Обычные браузеры сохраняют streaming metadata. В `htmlLimitedBots` используется объединение полного штатного regex Next.js 15.5.18 с `AuditikBot`; значение `/.*/`, сопоставление общего `Chrome` и regex только из `AuditikBot` запрещены, потому что первое глобально отключает streaming, второе затронет обычные браузеры, а третье заменит и потеряет штатный список Next.js.

## Acceptance Criteria

### AC1 — одна валидная категория

**Given** URL содержит ровно один параметр `category` со slug, присутствующим в ответе `/api/v1/categories-tree/` (узел дерева с непустыми `name` и `slug` — корень витрины или потомок любой глубины)
**When** Next.js формирует метаданные страницы
**Then** серверный HTML содержит утверждённые `title` и `description` с названием категории
**And** canonical равен `/catalog?category=<URL-encoded slug из дерева>` и содержит только этот единственный параметр `category`
**And** `openGraph.url`, Open Graph и Twitter title/description согласованы с canonical и основными метаданными через существующий `buildMetadata`
**And** для страницы категории итоговое поле metadata равно `keywords: null`, поэтому не наследуются ни каталожные, ни глобальные keywords из корневого layout; `image` и `ogType` остаются дефолтами `buildMetadata` (`/image.jpg`, `website`).

### AC2 — основной каталог

**Given** открыт `/catalog` без параметра `category`
**When** Next.js формирует метаданные страницы
**Then** сохраняются существующие значения без символьных изменений:
- title: `Каталог спортивных товаров | OPTISPORT`;
- description: `Каталог спортивных товаров: фитнес и атлетика, единоборства, спортивные игры, плавание, туризм. Оптовые и розничные цены, доставка по России.`;
- keywords: `каталог спортивных товаров, спортинвентарь оптом, спортивная экипировка`;
- image: `/image.jpg`;
- canonical: `/catalog`.

### AC3 — служебные фильтры не создают canonical

**Given** URL содержит `focusSearch`, `page`, сортировку, диапазон цены, наличие, бренд либо другие фильтры каталога
**When** Next.js формирует метаданные
**Then** эти параметры не входят в canonical и не создают собственных метаданных
**And** при ровно одной валидной категории canonical остаётся `/catalog?category=<slug>`
**And** без валидной единственной категории canonical остаётся `/catalog`.

### AC4 — неизвестная или неоднозначная категория

**Given** `category` отсутствует, пуст, повторён, содержит slug вне публичного дерева (включая якорь «СПОРТ» и активные узлы, скрытые из витрины), API вернул невалидное тело либо запрос дерева завершился ошибкой
**When** Next.js формирует метаданные
**Then** категория не получает вымышленного имени и запрос страницы не завершается 500
**And** используются неизменённые базовые метаданные каталога из AC2 и canonical `/catalog`
**And** неизвестные/устаревшие slug не захардкожены и не поддерживаются отдельным локальным реестром.

### AC5 — метаданные доступны без гидратации и видны проверяющему боту в `<head>`

**Given** запрошен `/catalog` или адрес одной валидной категории
**When** запрос отправлен с полным User-Agent `AuditikBot/1.0` из решения №7 либо User-Agent штатного HTML-limited бота Next.js
**Then** исходный серверный HTML до выполнения клиентского JavaScript уже содержит в `<head>` ожидаемые `<title>`, `<meta name="description">` и `<link rel="canonical">`
**And** запрос с обычным Chrome User-Agent, не содержащим `AuditikBot`, не попадает под `htmlLimitedBots` и сохраняет штатную возможность streaming metadata
**And** независимо от режима streaming реализация не вычисляет SEO-метаданные в `useEffect`, Zustand или другом клиентском коде.

### AC6 — каталог и URL-state не меняются

**Given** пользователь открывает каталог и применяет категорию, поиск, бренды, сортировку, пагинацию, цены, наличие или badge-фильтры
**When** работает существующий Client Component каталога
**Then** отображение, запросы товаров, история навигации и синхронизация фильтров с URL остаются прежними
**And** существующий набор тестов `CatalogPage.test.tsx` целиком, включая сценарии категории и неизвестного slug, проходит после переноса компонента без ослабления assertions.

### AC7 — sitemap содержит только подтверждённые категории

**Given** sitemap получает дерево категорий из `/api/v1/categories-tree/` — публичные корни и всех их потомков (активность и служебные исключения уже отфильтрованы backend'ом)
**When** формируется `/sitemap.xml`
**Then** рекурсивный обход дерева добавляет для каждого валидного уникального slug адрес `/catalog?category=<URL-encoded slug>`
**And** slug вне дерева (якорь, скрытые активные узлы), дублирующиеся или пустые значения в sitemap отсутствуют
**And** сбой блока категорий не роняет sitemap: статические и остальные динамические адреса сохраняются.

## Tasks / Subtasks

- [x] **Task 0 — GitNexus-гейт перед изменением кода** (AC: все)
  - [x] 0.1 Выполнить `npx gitnexus status`; индекс должен соответствовать текущему commit. При `stale` остановиться и попросить пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [x] 0.2 До правок выполнить `impact --direction upstream` с абсолютным `-r "C:/Users/1/DEV/FREESPORT"` для каждого изменяемого существующего символа, в том числе `buildMetadata`, `CatalogLayout`, текущего default-компонента каталога, `sitemap`/его helper-функций и `nextConfig`.
  - [x] 0.3 Не считать снимок create-story заменой гейта реализации. Снимок 14.09.2026 на `a43b24d`: `buildMetadata` — **HIGH**, 16 прямых вызывающих, 3 процесса, 2 модуля. Сигнатуру и внутренний контракт функции не менять.

- [x] **Task 1 — серверное формирование метаданных каталога** (AC: 1–5)
  - [x] 1.1 Вынести неизменяемую базовую SEO-конфигурацию каталога из `catalog/layout.tsx` в переиспользуемую серверной страницей структуру либо перенести её в `generateMetadata`, сохранив значения AC2 дословно.
  - [x] 1.2 Реализовать в серверном слое разбор Next.js 15 `searchParams: Promise<Record<string, string | string[] | undefined>>`; валидным кандидатом считать только одно непустое после `trim()` строковое значение `category` (whitespace-only — невалидно, без API-запроса). Для повторного параметра не выбирать первое значение.
  - [x] 1.3 Проверять кандидат по публичному дереву: загрузить `/api/v1/categories-tree/` одним серверным запросом (endpoint не пагинирован, ответ — корневой массив с рекурсивными `children`, а не `{results}` — `fetchAll` из sitemap не переиспользовать) и рекурсивно сгладить в `Map<slug, name>`. Использовать серверный приоритет URL окружения, принятый в проекте (семантика `getApiUrl()` из `sitemap.ts`: к `INTERNAL_API_URL` дописывается `/api/v1`, `NEXT_PUBLIC_API_URL*` используются как есть), и единый `const CATEGORY_TREE_FETCH_TIMEOUT_MS = 3000;` в `AbortSignal.timeout(CATEGORY_TREE_FETCH_TIMEOUT_MS)`. Запрос публичный, изменения backend и API-контракта не нужны.
  - [x] 1.4 Кандидат валиден, если его slug присутствует в дереве и узел имеет непустое строковое `name`; title/description строить по утверждённым шаблонам, canonical — из slug узла дерева через `URLSearchParams` (единый энкодер для canonical).
  - [x] 1.5 При отсутствии slug в дереве, повторном/пустом параметре, невалидном JSON, network error, таймауте или 5xx возвращать базовые метаданные AC2. Всё тело `generateMetadata` обернуть в try/catch → fallback; не бросать ошибку и не логировать как ошибку slug вне дерева.
  - [x] 1.6 Для данных дерева категорий использовать fetch-level кэш `next: { revalidate: 3600 }` (как в `sitemap.ts`; у маршрута `/catalog` собственного `revalidate` сейчас нет — route-level export не добавлять, ISR всей страницы не менять). Не вводить новую зависимость и не переносить JWT/client-store в серверный путь.
  - [x] 1.7 Вызывать существующий `buildMetadata({...})` без изменения `PageSeoOptions`, сигнатуры или реализации `buildMetadata`; для валидной категории поверх результата явно установить `keywords: null`, чтобы сбросить metadata, наследуемые из корневого layout.

- [x] **Task 2 — server wrapper и сохранение Client Component** (AC: 5, 6)
  - [x] 2.1 Превратить `frontend/src/app/(blue)/catalog/page.tsx` в Server Component, который экспортирует `generateMetadata` и рендерит клиентский каталог.
  - [x] 2.2 Перенести текущее содержимое Client Component без функционального рефакторинга в соседний файл, например `CatalogPageClient.tsx`, сохранив `'use client'`, `Suspense`, хуки, состояния, API-вызовы и URL-синхронизацию.
  - [x] 2.3 Удалить статический metadata-export из `catalog/layout.tsx`, когда page-level `generateMetadata` станет единственным источником метаданных каталога — иначе layout-поля (например `keywords`) унаследуются на страницы категорий через metadata-merge; pass-through layout можно сохранить. Fallback при непредвиденном сбое `generateMetadata` — metadata корневого `app/layout.tsx`, этого достаточно. Не пытаться получить `searchParams` в layout — layout App Router их не получает.
  - [x] 2.4 Обновить импорт в `CatalogPage.test.tsx` на клиентский компонент. Не переписывать и не сокращать существующую матрицу тестов ради нового wrapper.
  - [x] 2.5 В `frontend/next.config.ts` задать `htmlLimitedBots` как полный штатный regex установленной Next.js 15.5.18, дополненный альтернативой `AuditikBot`. Не импортировать приватный модуль `next/dist/**`, не использовать `/.*/`, не матчить общий `Chrome` и не задавать `/AuditikBot/i` отдельно: пользовательское значение полностью заменяет штатный список Next.js.

- [x] **Task 3 — индексируемые категории в sitemap** (AC: 7)
  - [x] 3.1 Расширить существующий fail-soft `frontend/src/app/sitemap.ts`: загрузить `categories-tree` параллельно с products/blog/news/pages. Endpoint не пагинирован и возвращает вложенное дерево — нужен отдельный fetch с тем же fail-soft (`try/catch`, `next: { revalidate }`) и `AbortSignal.timeout(CATEGORY_TREE_FETCH_TIMEOUT_MS)`, где `CATEGORY_TREE_FETCH_TIMEOUT_MS = 3000`; `fetchAll` не подходит.
  - [x] 3.2 Формировать query-URL категории отдельно от path-prefix helper: `/catalog?category=<encoded slug>`. Не создавать маршрут `/catalog/<slug>`.
  - [x] 3.3 Рекурсивно обойти дерево (корни + все потомки), дедуплицировать slug и игнорировать пустые/нестроковые значения. Не фильтровать категорию по `products_count` или `in_stock_count`: решение владельца относится ко всем узлам публичного дерева, а не только к категориям с остатком.
  - [x] 3.4 Сохранить `revalidate = 3600`, `MAX_PAGES` и graceful degradation остальных секций sitemap.

- [x] **Task 4 — автоматические тесты** (AC: 1–7)
  - [x] 4.1 Добавить unit-тесты `generateMetadata`/чистого metadata-helper для: базового каталога; одной валидной категории из дерева; валидной категории с прочими фильтрами; slug вне дерева (включая активный, но скрытый из витрины); пустого category; повторного category (разные и одинаковые значения); malformed API body; 5xx/network failure/timeout.
  - [x] 4.2 В позитивном сценарии проверять точные утверждённые title/description, canonical, `openGraph.url` и `keywords: null`; в интеграционной проверке итогового HTML доказать отсутствие `<meta name="keywords">` у категории. В fallback-сценариях проверять все неизменяемые поля AC2, а не только canonical.
  - [x] 4.3 Закрепить, что URL API и canonical корректно кодируют slug и что имя берётся только из ответа API, не выводится из slug.
  - [x] 4.4 Добавить тесты `sitemap.ts` с моками `fetch`: категории включаются как query-URL, обход дерева захватывает потомков всех уровней, slug дедуплицируются, ошибка categories-tree не удаляет статические и другие динамические entries.
  - [x] 4.5 Сохранить зелёными все существующие тесты `CatalogPage.test.tsx`; новые моки метаданных не должны скрывать регресс URL-state.
  - [x] 4.6 Добавить тест конфигурации `htmlLimitedBots`: regex совпадает с полным User-Agent `AuditikBot/1.0` из решения №7 и репрезентативными штатными HTML-limited User-Agent (`Bingbot`, `Twitterbot`, `Chrome-Lighthouse`, `Google-InspectionTool`), но не совпадает с обычным Chrome User-Agent без `AuditikBot`. Тест должен предотвращать случайную замену полного списка на `/AuditikBot/i` или `/.*/`.

- [x] **Task 5 — проверки и серверный HTML** (AC: 5–7)
  - [x] 5.1 Выполнить в `frontend/`: `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check`.
  - [x] 5.2 Перезапустить frontend-контейнер по правилам проекта; при изменении структуры/сборки использовать полную пересборку `docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend`.
  - [x] 5.3 На запущенной production-сборке или acceptance-окружении получить `curl`-ом исходный HTML без Cookie для `/catalog`, одной реально существующей категории, неизвестной категории, повторного category и валидной категории с прочими фильтрами. Каждый сценарий выполнить с полным User-Agent `AuditikBot/1.0` из решения №7 и доказать, что title, description и canonical находятся именно между `<head>` и `</head>` до гидратации. Контрольным запросом с обычным Chrome User-Agent без `AuditikBot` подтвердить успешный HTML-ответ; расположение metadata для него не фиксировать, поскольку streaming сохраняется.
  - [x] 5.4 Получить `/sitemap.xml` и доказать наличие проверенной активной категории и отсутствие контрольного неизвестного slug.
  - [x] 5.5 Перед коммитом выполнить `npx gitnexus detect-changes --scope all -r "C:/Users/1/DEV/FREESPORT"`; ожидаются только потоки метаданных каталога, клиентского wrapper и sitemap.
  - [x] 5.6 По завершении обновить sprint-status (`ready-for-dev` → `done` после приёмки) и заполнить Dev Agent Record / File List в этом файле.

## Dev Notes

### Текущее состояние кода

- `frontend/src/app/(blue)/catalog/layout.tsx` сейчас статически вызывает `buildMetadata` и задаёт базовые метаданные `/catalog`; `searchParams` ему недоступны.
- `frontend/src/app/(blue)/catalog/page.tsx` — крупный Client Component. Он читает `category` через `useSearchParams`, получает дерево через `categoriesService.getTree()` и содержит тщательно протестированную URL-синхронизацию. Внутреннюю логику менять не требуется.
- В существующем `CatalogPage.test.tsx` полная матрица сценариев (75 объявлений: `it` + `it.each`-таблицы; точное число проверять на момент реализации). Среди них уже есть одна категория, категория с badge-фильтром, неизвестная категория, канонизация фильтров, пагинация и история навигации. Перенос в клиентский файл не должен превращаться в переписывание этих тестов.
- `frontend/src/utils/seo.ts::buildMetadata` уже формирует title, description, canonical, Open Graph и Twitter. `normalizePath` сохраняет query string, однако query следует собирать через `URLSearchParams`/безопасное кодирование, а не конкатенацией сырого slug.
- `frontend/src/app/sitemap.ts` уже загружает динамические коллекции через server `fetch`, обходит DRF pagination и при ошибке сохраняет доступную часть sitemap. Тестов sitemap сейчас нет.
- `frontend/next.config.ts` сейчас не задаёт `htmlLimitedBots`. Next.js 15.5.18 применяет штатный список HTML-limited ботов, но `AuditikBot` в него не входит; пользовательский regex заменяет штатный список целиком.
- Production access log однозначно связывает отчёт 10.09.2026 12:11:40 с обходом `AuditikBot/1.0`: один IP выполнил 674 GET-запроса с 12:09:59 до 12:11:37 UTC, включая `/catalog?focusSearch=true`, категории каталога, варианты `/login`, `/checkout` и `/privacy-policy`. Это браузерный crawler на Chrome 120: он загружает JS/CSS, RSC и API.
- Публичное дерево — `GET /api/v1/categories-tree/` (`CategoryTreeViewSet`): `AllowAny`, `pagination_class = None` (всё дерево одним ответом), корни — прямые активные дети якоря `ROOT_CATEGORY_NAME` («СПОРТ») без служебных исключений (`uncategorized`, `onec-unresolved-category`, «Без категории», placeholder-имена); `children` рекурсивны и тоже фильтруются по `is_active` и тем же исключениям. Узел `CategoryTreeSerializer` несёт `name`, `slug`, `children[]`.
- `/api/v1/categories/` (`CategoryViewSet`) — это плоский список ВСЕХ активных категорий, включая якорь и узлы вне витрины. Он НЕ является источником индексируемых категорий; detail-endpoint в этой Story не используется.
- Один и тот же кэшируемый fetch дерева может обслуживать и `generateMetadata`, и `sitemap` — fetch-дедупликация Next по URL+revalidate это покрывает.
- OpenAPI фиксирует публичный `GET /categories-tree/` со схемой `CategoryTree` (обязательные `name`, `slug`, рекурсивные `children`).

### Обязательный контракт query-параметров

| URL | Метаданные | Canonical |
|---|---|---|
| `/catalog` | базовые | `/catalog` |
| `/catalog?focusSearch=true` | базовые | `/catalog` |
| `/catalog?category=sportivnye-igry` (slug в дереве) | категории | `/catalog?category=sportivnye-igry` |
| `/catalog?category=sportivnye-igry&page=2&brand=nike` (slug в дереве) | категории | `/catalog?category=sportivnye-igry` |
| `/catalog?category=unknown` (slug вне дерева / ошибка API) | базовые | `/catalog` |
| `/catalog?category=<slug якоря или активного узла вне дерева>` | базовые | `/catalog` |
| `/catalog?category=a&category=b` | базовые, без выбора первого | `/catalog` |
| `/catalog?category=a&category=a` | базовые, параметр всё равно не единственный | `/catalog` |

### Технические ограничения

- **Не менять сигнатуру `buildMetadata`.** Актуальный blast radius HIGH: 16 прямых вызывающих, 3 процесса, 2 модуля.
- **Обязателен server wrapper, которому доступны `searchParams`.** Нельзя вычислять metadata в текущем Client Component или переносить его интерактивную фильтрацию на сервер.
- Не создавать локальную таблицу `slug → name`, не транслитерировать slug в название и не сохранять устаревшие категории «для SEO».
- Не менять backend, OpenAPI, модель Category, фильтры каталога, route shape или electric-каталог: публичного detail endpoint достаточно.
- Не добавлять `noindex` только отдельным фильтровым URL: canonical нормализует их к категории или `/catalog` согласно решениям владельца.
- Не отключать streaming metadata глобально. `htmlLimitedBots` должен блокировать metadata только для полного штатного списка Next.js 15.5.18 и `AuditikBot`; обычный Chrome без маркера `AuditikBot` не должен совпадать с regex.
- Не обещать в description наличие, остаток, конкретную цену или возможность немедленной покупки.

### Архитектура и версии

- Фактический стек: Next.js 15.5.18, React 19.1.0, TypeScript 5.8.2, Vitest 4.x.
- В Next.js 15 `searchParams` страницы асинхронны; использовать `Promise<...>` и `await`, как в `frontend/src/app/(blue)/search/page.tsx`.
- Метаданные должны формироваться в Server Component через `generateMetadata`; Client Component не может экспортировать metadata.
- Начиная с Next.js 15.2 динамические metadata могут стримиться. `htmlLimitedBots` переводит только совпавшие User-Agent в blocking-режим; пользовательское значение заменяет встроенный regex, поэтому Story сохраняет весь штатный список Next.js 15.5.18 и добавляет `AuditikBot`.
- Server fetch для публичных SEO-данных следует существующим паттернам `[slug]/page.tsx` и `sitemap.ts`, с явным `revalidate` и безопасным fallback.
- Новые зависимости не требуются.

### Контракт `htmlLimitedBots`

Для зафиксированной Next.js 15.5.18 штатный regex берётся из `next/dist/shared/lib/router/utils/html-bots.js` и копируется в публичную конфигурацию без импорта приватного модуля, с единственным добавлением `AuditikBot`:

```ts
htmlLimitedBots: /[\w-]+-Google|Google-[\w-]+|Chrome-Lighthouse|Slurp|DuckDuckBot|baiduspider|yandex|sogou|bitlybot|tumblr|vkShare|quora link preview|redditbot|ia_archiver|Bingbot|BingPreview|applebot|facebookexternalhit|facebookcatalog|Twitterbot|LinkedInBot|Slackbot|Discordbot|WhatsApp|SkypeUriPreview|Yeti|googleweblight|AuditikBot/i,
```

При обновлении Next.js regex сверить с новой штатной версией; не продолжать автоматически использовать устаревшую копию.

### Project Structure Notes

Ожидаемые поверхности (точные имена новых файлов разработчик может выбрать по действующим соглашениям):

- UPDATE `frontend/src/app/(blue)/catalog/layout.tsx` — убрать статический источник metadata после переноса;
- UPDATE `frontend/src/app/(blue)/catalog/page.tsx` — server wrapper + `generateMetadata`;
- NEW `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` — неизменённая интерактивная реализация из текущего `page.tsx`;
- UPDATE `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — импорт client-компонента, без сокращения регрессии;
- NEW тест metadata рядом с route либо helper;
- UPDATE `frontend/src/app/sitemap.ts` и NEW тест sitemap;
- UPDATE `frontend/next.config.ts` — штатные HTML-limited боты Next.js 15.5.18 + `AuditikBot`;
- NEW или UPDATE тест `next.config.ts`, закрепляющий bot/non-bot User-Agent.

Не размещать серверный API helper внутри client-файла. Если выделяется общий helper для URL API, не расширять рефакторинг на несвязанные маршруты в этой Story.

### Previous Story Intelligence

- Story 41.12 завершена (`done`), поэтому условие correct-course для добавления новых Story в tracker выполнено.
- Последний зафиксированный полный frontend-прогон 41.12: 3151 passed, 16 skipped, 0 failed. Это историческая база, а не требуемое точное число после 41.13.
- 41.12 показала, что перенос/укрепление общей frontend-логики требует сохранить существующие page-level тесты и выполнить актуальный GitNexus impact, а не полагаться на старый снимок.

### Git Intelligence

- Текущий commit при подготовке: `a43b24d`.
- Недавние изменения Epic 41 документируют завершение 41.12 и создание предварительных постановок 41.13–41.16.
- GitNexus переиндексирован пользователем 14.09.2026 и на момент create-story показывает `up-to-date` для `a43b24d`.

## Источники

- [Одобренное предложение](../../planning-artifacts/sprint-change-proposal-2026-09-13-remaining-audit-items.md), разделы «Story 41.13» и «Влияние на PRD, архитектуру и UX».
- [Epic 41](../../planning-artifacts/epic-41-site-audit.md), Story 41.13 и FR-41-29.
- [Architecture](../../planning-artifacts/architecture.md), ADR-001, Next.js App Router и frontend testing.
- `project-context.md`, разделы 4, 5 и 7.
- `frontend/src/app/(blue)/catalog/layout.tsx` — текущие базовые metadata.
- `frontend/src/app/(blue)/catalog/page.tsx` и `__tests__/CatalogPage.test.tsx` — Client Component и URL-state.
- `frontend/src/app/(blue)/search/page.tsx` — действующий Next.js 15 server wrapper/searchParams pattern.
- `frontend/src/utils/seo.ts` и `frontend/src/utils/__tests__/seo.test.ts` — контракт `buildMetadata`.
- `frontend/src/app/sitemap.ts` — текущий fail-soft sitemap.
- `frontend/src/services/categoriesService.ts` (`getTree`), `backend/apps/products/views.py::CategoryTreeViewSet`, `docs/api/openapi.yaml#/categories-tree/` — контракт публичного дерева категорий.
- Проверка: `tmp/audit-2026-09-10-verification-2026-09-13.md`.
- Исходный отчёт: `tmp/audit-report-https___optisport.ru_-full (1).pdf`.

## Журнал

- 13.09.2026: подготовлена постановка по одобренному расширению; реализация не начиналась.
- 14.09.2026: выполнен полный `bmad-create-story`; зафиксированы решения владельца по индексируемым категориям, шаблонам metadata и нескольким category; статус переведён в `ready-for-dev`.
- 14.09.2026: актуальный GitNexus index `a43b24d`; impact `buildMetadata` — HIGH (16 прямых вызывающих, 3 процесса, 2 модуля). Production-код и тесты не изменялись и не запускались.
- 14.09.2026: по результатам ревью владелец уточнил источник индексируемых категорий — только публичное дерево `/api/v1/categories-tree/` (корни витрины и все потомки); якорь «СПОРТ» и активные узлы вне витрины не индексируются. Обновлены решение №1, AC1/AC4/AC7, Tasks 1.3–1.6, 3.1–3.3, 4.1, 4.4, контрактная таблица и Dev Notes. Туда же внесены мелкие находки ревью: `keywords`/`image`/`ogType` для категорий (AC1), `trim()` для параметра (1.2), причина удаления metadata из layout и fallback на корневой layout (2.3), шаг обновления sprint-status/File List (5.6), пометка о длине description.
- 14.09.2026: владелец утвердил явный `keywords: null` для валидной категории и единый `CATEGORY_TREE_FETCH_TIMEOUT_MS = 3000` для metadata и sitemap.
- 14.09.2026: production access log за 10.09.2026 идентифицировал проверяющий сервис как `AuditikBot/1.0`; его обход завершился за три секунды до времени отчёта. Владелец выбрал точечный blocking metadata через полный штатный `htmlLimitedBots` Next.js 15.5.18 + `AuditikBot`, без глобального отключения streaming для обычных браузеров. Обновлены решение №7, AC5, Tasks 0.2, 2.5, 4.6, 5.3, Dev Notes и ожидаемые файлы.
- 14.09.2026: реализованы server metadata каталога, client wrapper, категории sitemap и `htmlLimitedBots`; после review-патчей полный frontend-прогон — 3194 passed, 16 skipped, проверки lint/typecheck/format/build зелёные. Production HTML и sitemap проверены локально с реальным публичным деревом; Story завершена автоматическим review workflow.

## Dev Agent Record

### Agent Model Used

Devin

### Debug Log References

- `npx gitnexus status` и обязательные upstream impact-проверки выполнены до правок; индекс соответствовал `361f0f5`.
- `npm test`: 179 файлов, 3194 passed, 16 skipped.
- `npm run lint`, `npx tsc --noEmit`, `npm run format:check`, `npm run build`: успешно.
- `docker compose --env-file ../.env -f ../docker/docker-compose.yml up -d --build frontend`: frontend пересобран и запущен.
- Production `curl` на порту 3001 с полным User-Agent AuditikBot подтвердил metadata в `<head>` для базового каталога, валидной категории, фильтров, unknown и повторного category; Chrome получил HTTP 200.
- Production `/sitemap.xml` содержит `bassejny`, сохраняет статический `/catalog` и не содержит `unknown-seo-control`.
- `npx gitnexus detect-changes --scope all -r "C:/Users/1/DEV/FREESPORT"`: medium, ожидаемые потоки catalog metadata/client wrapper и sitemap.

### Completion Notes List

- Интерактивный каталог без функционального рефакторинга перенесён в Client Component; route стал Server Component.
- Metadata валидируются исключительно по публичному дереву категорий, используют утверждённые шаблоны, безопасный canonical и fail-soft fallback.
- Категории публичного дерева рекурсивно и без дублей добавлены в sitemap с независимым fail-soft.
- Полный штатный regex HTML-limited ботов Next.js 15.5.18 дополнен `AuditikBot`; обычный Chrome не совпадает.
- Добавлены регрессионные тесты metadata, sitemap и конфигурации ботов; существующие 85 тестов CatalogPage сохранены зелёными.
- Review workflow завершён: Story и sprint-status переведены в `done`, пункт 5.6 закрыт.

### File List

- `_bmad-output/implementation-artifacts/Story/41-13-catalog-category-seo-metadata.md` — чек-лист и Dev Agent Record.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story 41.13 переведена в `done`.
- `frontend/next.config.ts` — полный `htmlLimitedBots` Next.js 15.5.18 + `AuditikBot`.
- `frontend/src/__tests__/next-config-headers.test.ts` — тест bot/non-bot User-Agent.
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` — сохранённый интерактивный каталог.
- `frontend/src/app/(blue)/catalog/page.tsx` — server wrapper и `generateMetadata`.
- `frontend/src/app/(blue)/catalog/layout.tsx` — pass-through layout без metadata.
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — импорт Client Component.
- `frontend/src/app/(blue)/catalog/__tests__/metadata.test.ts` — тесты metadata и fail-soft.
- `frontend/src/app/sitemap.ts` — публичные категории в sitemap.
- `frontend/src/app/__tests__/sitemap.test.ts` — тесты рекурсивных категорий и graceful degradation.

## Review Triage Log

### 2026-09-14 — Review pass
- verdicts: 19 findings — high 0, medium 4, low 3, false 12, maybe-false 0
- findings:
  - `[low]` `[reject]` Логика `getApiUrl()` продублирована в metadata и sitemap — семантика намеренно совпадает с требованием Story; общий helper расширил бы рефакторинг без пользовательской пользы.
  - `[false]` `[reject]` Категорийные metadata полагаются на дефолты `buildMetadata` — это прямо предписано AC1 и Task 1.7; контракт helper подтверждает `/image.jpg` и `website`.
  - `[medium]` `[patch]` Позитивный metadata-тест не фиксировал точные social-image поля — добавлены точные проверки `DEFAULT_OG_IMAGE_META`, `openGraph.type`, `twitter.images` и `twitter.card`.
  - `[false]` `[reject]` Заголовочный JSDoc Client Component называет его страницей каталога — компонент по-прежнему реализует всю интерактивную страницу, неверного поведения нет.
  - `[false]` `[reject]` Альтернатива `AuditikBot` без границ якобы слишком широка — контракт требует распознавать маркер AuditikBot внутри полного Chrome User-Agent, что regex и делает.
  - `[low]` `[reject]` Нет автоматической сверки regex при обновлении Next.js — Story требует ручную сверку версии и запрещает импорт приватного `next/dist/**`; автоматизация добавила бы запрещённую связанность.
  - `[false]` `[reject]` Тесты не покрывают production User-Agent — полный production User-Agent AuditikBot уже присутствовал в таблице; полнота штатных альтернатив рассмотрена отдельным finding.
  - `[low]` `[patch]` Невалидные slug в sitemap-моке не имели прямых assertions — добавлены проверки отсутствия whitespace-only и нестрокового slug.
  - `[false]` `[reject]` Sitemap не логирует fail-soft ошибки — молчаливое сохранение остальных секций является утверждённым контрактом Story, обязательной телеметрии нет.
  - `[false]` `[reject]` `generateMetadata` не логирует fallback — Story требует fail-soft и запрещает error-логирование slug вне дерева; отсутствие лога не нарушает наблюдаемое поведение.
  - `[false]` `[reject]` Sitemap должен требовать непустой `name` — AC7 и Task 3.3 определяют валидность sitemap-узла по непустому строковому slug; backend-контракт гарантирует name.
  - `[medium]` `[patch]` Spot-check `htmlLimitedBots` не защищал весь штатный список Next.js 15.5.18 — таблица расширена до всех штатных альтернатив и AuditikBot без приватных импортов.
  - `[medium]` `[patch]` Точные Open Graph/Twitter image defaults не были закреплены — исправлено тем же точным metadata assertion, что и соответствующий blind finding.
  - `[false]` `[reject]` Нет автоматического runtime-HTML теста — Story предписывает production curl-проверку, она выполнена; обязательного нового E2E harness нет.
  - `[false]` `[reject]` Runtime `<head>` для AuditikBot якобы не проверен — он проверен production curl по Task 5.3, включая title, description и canonical до гидратации.
  - `[medium]` `[patch]` Полнота штатного bot-regex не была закреплена тестом — исправлено той же полной таблицей альтернатив, что и finding verification-gap.
  - `[false]` `[reject]` Отсутствие `keywords` проверено только на объекте — production curl дополнительно подтвердил отсутствие `<meta name="keywords">` в итоговом `<head>` категории.
  - `[false]` `[reject]` Нельзя подтвердить неизменность `buildMetadata` — `frontend/src/utils/seo.ts` отсутствует в diff от baseline, а его существующий контракт и тесты прочитаны и прошли.
  - `[false]` `[reject]` Разные требования name для metadata и sitemap названы расхождением — это две явно разные поверхности AC1 и AC7, и сам аудитор отметил соответствие спецификации.

## Auto Run Result

Status: success
Summary: реализованы серверные SEO-метаданные категорий каталога, сохранён Client Component, категории добавлены в sitemap, штатный `htmlLimitedBots` дополнен AuditikBot.
Files changed: server wrapper и metadata каталога; перенесённый client-каталог; pass-through layout; sitemap; Next.js config; тесты metadata, sitemap и bot regex; Story и sprint-status.
Review findings: 19 всего; применены 3 patch-группы (2 medium, 1 low), deferred 0, отклонены 12 false и 2 low как не требующие усложнения.
Follow-up review recommendation: true — два medium patch-entry усилили защиту полного bot-regex и точных social metadata; рекомендуется свежий review-pass этих контрактных assertions.
Verification: `npm test` — 179 файлов, 3194 passed, 16 skipped; `npm run lint`, `npx tsc --noEmit`, `npm run format:check`, `git diff --check` — успешно; production build, Docker restart, runtime HTML и sitemap проверены.
Residual risks: при недоступности categories-tree или таймауте 3000 мс намеренно применяется fail-soft; runtime HTML подтверждён ручным production curl, а не отдельным E2E-тестом.
