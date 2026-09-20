---
baseline_commit: f426f572
---

# Story 41.22: Собственный canonical у подборок каталога и подборки в sitemap

Status: done
Baseline Revision: f426f572

## Story

As a владелец магазина,
I want чтобы подборки «Новинки», «Лидеры продаж» и «Скидки» были самостоятельными страницами каталога со своим canonical и присутствовали в sitemap,
so that поисковик мог показывать их в выдаче, а сканер аудита не отмечал «Canonical указывает на другой URL» у `/catalog?is_new=true`, `?is_hit=true`, `?is_sale=true`.

**Закрывает:** FR-41-38. **Решение:** пересмотр D1 (`sprint-change-proposal-2026-09-16.md`) — запрос Alex 19.09.2026 по итогам проверки `tmp/audit-2026-09-10-verification-2026-09-19.md`.

## Утверждённые решения (дословно, не пересматривать)

1. **D1 пересмотрено в части canonical и sitemap.** Подборка — адрес `/catalog` с единственным query-параметром `is_new`, `is_hit` или `is_sale`, равным строке `'true'` (распознавание `findCatalogCollection` из 41.17 не меняется). Её canonical и `og:url` — собственный адрес: `/catalog?is_new=true`, `/catalog?is_hit=true`, `/catalog?is_sale=true`.
2. **Title и description подборок не меняются** — таблица «Тексты подборок (D1)» стори 41.17 остаётся действующей.
3. **Все прочие комбинации параметров не меняются:** `?is_new=true&page=2`, два флага, флаг + `ordering`/`focusSearch`, `is_new=false` и т. п. — базовые метаданные с canonical `/catalog`; флаг + валидная `category` — метаданные категории (41.13).
4. **Sitemap содержит подборку, только если в ней есть товары в наличии** — ровно то, что видит посетитель по умолчанию (клиент каталога шлёт `in_stock=true`, `CatalogPageClient.tsx:1146`). Любая ошибка проверки (сеть, таймаут, не-2xx, нет числового `count`) → подборка в sitemap не попадает, остальной sitemap не страдает.
5. **`noindex` для пустой подборки не вводится** (см. «Открытые вопросы», п. 1). `robots.ts`, `middleware.ts`, ссылки на подборки (`config/quickLinks.tsx`, секции `/home`) не меняются.

## Acceptance Criteria

### AC1 — собственный canonical подборки

**Given** адрес `/catalog`, у которого единственный query-параметр — `is_new`, `is_hit` или `is_sale` со значением `'true'`
**When** строятся метаданные страницы
**Then** `alternates.canonical` и `openGraph.url` равны `/catalog?<ключ>=true`
**And** title, description, Open Graph, Twitter, `keywords: null` и `DEFAULT_OG_IMAGE_META` — как в 41.17 (таблица D1), запрос к API не выполняется

### AC2 — остальные адреса каталога без изменений

**Given** любой другой набор параметров из сценариев `metadata.test.ts` 41.17 («не подборка»: два флага, `false`, `''`, `'TRUE'`, `'1'`, повтор флага, флаг + `page`, флаг + `ordering`, флаг + `focusSearch`, только `focusSearch`), флаг + валидная `category`, базовый `/catalog`, категории
**When** строятся метаданные
**Then** ожидания этих тестов не меняются: базовые — canonical `/catalog`, категория — canonical `/catalog?category=<slug>`

### AC3 — подборки в sitemap

**Given** генерация `sitemap.xml`
**When** API `GET /api/v1/products/?<ключ>=true&in_stock=true&page_size=1` возвращает 2xx с числовым `count > 0`
**Then** sitemap содержит `absoluteUrl('/catalog?<ключ>=true')` для этой подборки ровно один раз — строка совпадает с canonical AC1 (после разворачивания `metadataBase`)
**And** при `count === 0`, не-2xx, сетевой ошибке, таймауте или теле без числового `count` этой подборки в sitemap нет, а статические адреса, категории, товары, статьи, новости и CMS-страницы на месте
**And** адресов с `focusSearch=` и комбинаций подборки с другими параметрами в sitemap нет

### AC4 — инварианты индексации

**Given** `robots.ts` и тест инварианта D4 (`src/app/__tests__/robots-noindex-invariant.test.ts`)
**When** выполняются тесты
**Then** они проходят без изменений: `/catalog` не закрыт `Disallow`, у подборок нет `robots`

### AC5 — регрессия и проверки

**Given** итоговая версия ветки
**When** в `frontend/` выполняются `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check`, а также `npm run build` + `npm run check:build` (гейт 41.21)
**Then** всё зелёное; изменены только ожидания тестов, прямо названные в Task 3

### AC6 — приёмка на проде (NFR-41-08)

**Given** выкат на прод
**When** `curl -s -A "AuditikBot/1.0"` запрашивает `/catalog?is_new=true`, `?is_hit=true`, `?is_sale=true`, `/catalog?is_new=true&page=2`, `/catalog` и `/sitemap.xml`
**Then** у трёх подборок `<link rel="canonical">` и `og:url` — `https://optisport.ru/catalog?<ключ>=true`, title и description по таблице D1; у `?is_new=true&page=2` и `/catalog` canonical `https://optisport.ru/catalog`; в sitemap есть непустые подборки (на 19.09.2026 все три: 5 / 4 / 5 товаров в наличии)
**And** снимок приложен к стори

## Tasks / Subtasks

- [x] **Task 0 — preflight** (все AC)
  - [x] 0.1 Ветка `feature/41-22-collections-self-canonical` от актуального `develop` (прямые коммиты в `develop` запрещены).
  - [x] 0.2 `npx gitnexus status`. Если `stale` и между индексированным и текущим коммитом есть изменения в `frontend/src` — попросить пользователя `! npx gitnexus analyze --skip-agents-md`.
  - [x] 0.3 `npx gitnexus impact <UID> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по UID (имя `generateMetadata` неоднозначно): `Function:frontend/src/app/(blue)/catalog/page.tsx:generateMetadata`, `Function:frontend/src/app/sitemap.ts:sitemap`, `Function:frontend/src/app/sitemap.ts:toCategoryEntries`. Сообщить blast radius пользователю. Снимок на create-story — Dev Notes «GitNexus».
  - [x] 0.4 Исходный прогон до правок: `npx vitest run "src/app/(blue)/catalog" src/app/__tests__/sitemap.test.ts src/app/__tests__/robots-noindex-invariant.test.ts` — зелёный.

- [x] **Task 1 — canonical подборки** (AC1, AC2)
  - [x] 1.1 `frontend/src/app/(blue)/catalog/page.tsx`, ветка `if (collection)` в `generateMetadata`: `path: '/catalog'` → путь подборки. Строить его так же, как путь категории, — через `URLSearchParams`: `` `/catalog?${new URLSearchParams({ [collection]: 'true' }).toString()}` ``.
  - [x] 1.2 Обновить комментарий над `CATALOG_COLLECTIONS` (`page.tsx:13-14`): подборки — самостоятельные страницы со своим canonical, в sitemap попадают непустые (41.22, пересмотр D1). Комментарии на русском (NFR-41-03).
  - [x] 1.3 `findCatalogCollection`, `CATALOG_COLLECTIONS`, `buildCatalogMetadata`, ветку `category` и `utils/seo.ts` **не менять** (`buildMetadata` — HIGH, 17 вызывающих).

- [x] **Task 2 — подборки в sitemap** (AC3)
  - [x] 2.1 `frontend/src/app/sitemap.ts`: константа ключей подборок `['is_new', 'is_hit', 'is_sale'] as const` (порядок = порядок в sitemap). Не импортировать из `(blue)/catalog/page.tsx` — файл страницы не экспортирует служебные константы, sitemap живёт отдельно (как дублируется `getApiUrl`).
  - [x] 2.2 Функция `fetchNonEmptyCollections(): Promise<CollectionKey[]>` по образцу `fetchCategorySlugs`: для каждого ключа `fetch(`${getApiUrl()}/products/?${key}=true&in_stock=true&page_size=1`, { next: { revalidate }, signal: AbortSignal.timeout(CATEGORY_TREE_FETCH_TIMEOUT_MS) })`; запросы параллельно (`Promise.all`), ошибка одной подборки не влияет на другие; подборка включается только при `res.ok` и `typeof count === 'number' && count > 0`. Исключения не выпускать наружу.
  - [x] 2.3 `toCollectionEntries(keys)`: `url: absoluteUrl(`/catalog?${new URLSearchParams({ [key]: 'true' })}`)`, `changeFrequency: 'daily'`, `priority: 0.7`. Добавить в `Promise.all` функции `sitemap()` и в итоговый массив сразу после `toCategoryEntries(...)`.
  - [x] 2.4 Обновить JSDoc файла: sitemap включает непустые подборки каталога.

- [x] **Task 3 — тесты** (AC1–AC4)
  - [x] 3.1 `src/app/(blue)/catalog/__tests__/metadata.test.ts`, `it.each` по трём подборкам (`:76-102`): название теста → «…с собственным canonical»; `alternates.canonical` и `openGraph.url` → `` `/catalog?${key}=true` ``. Остальные ожидания файла не менять.
  - [x] 3.2 `src/app/__tests__/sitemap.test.ts`:
    - Мок `fetch` в `beforeEach` сейчас отвечает на любой `url.includes('/products/')` телом без `count` — после правки это значит «подборки нет». Добавить **перед** веткой `/products/` ветку для запросов подборок (`url.includes('in_stock=true')` или разбор `searchParams`) с числовым `count`.
    - Тест `'не содержит подборок каталога и адреса фокуса поиска'` (`:66-72`) заменить: `focusSearch=` отсутствует; каждая подборка присутствует ровно один раз в виде `/catalog?<ключ>=true`; комбинаций подборки с `page=`/`category=` нет.
    - Новые сценарии: `count: 0` у одной подборки → её нет, две другие есть; не-2xx; `fetch` бросает; тело без `count` / `count: '5'` → подборки нет, при этом `/catalog`, `/catalog?category=games` и `/product/ball` на месте.
    - Проверить аргументы запроса: `http://backend:8000/api/v1/products/?is_new=true&in_stock=true&page_size=1` c `next: { revalidate: 3600 }` и `signal: expect.any(AbortSignal)`.
  - [x] 3.3 `robots-noindex-invariant.test.ts`, `robots.test.ts` — прогнать без изменений (AC4).

- [x] **Task 4 — проверки и документация** (AC5)
  - [x] 4.1 В `frontend/`: `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check`.
  - [x] 4.2 Гейт 41.21: `NEXT_PUBLIC_API_URL=http://localhost:18001/api/v1 npm run build`, затем `NEXT_PUBLIC_API_URL=http://localhost:18001/api/v1 npm run check:build` (локально порт 8001 занят backend из Docker — см. шапку `scripts/check-production-build.mjs`).
  - [x] 4.3 Локальная приёмка (аноним, без cookie): `docker compose --env-file .env -f docker/docker-compose.yml restart frontend`, затем `curl -s -A "AuditikBot/1.0"` по адресам AC6 на `http://localhost`; проверить `<link rel="canonical">`, `og:url`, `<title>`, `meta description`, отсутствие `meta keywords` и `meta robots`; `curl -s http://localhost/sitemap.xml | grep -o '<loc>[^<]*catalog?is_[^<]*'`.
  - [x] 4.4 `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только `generateMetadata` каталога и символы `sitemap.ts`.
  - [x] 4.5 Dev Agent Record, File List; `sprint-status.yaml` → `review`.
  - [x] 4.6 **Внешний шаг (после мёрджа, ручной выкат по SSH):** sync `develop` → `main` через PR; на сервере rebuild frontend и **`restart nginx`** (память: после пересборки nginx держит старый IP upstream). Приёмка AC6, снимок в стори. Повторный прогон сканера — шаг владельца.

### Review Findings

- [x] [Review][Patch] Сценарий отказа проверки подборки не доказывает сохранность статей, новостей и CMS-страниц [frontend/src/app/__tests__/sitemap.test.ts:112]
- [x] [Review][Patch] Тесты не закрепляют параллельный старт трёх запросов подборок через `Promise.all` [frontend/src/app/__tests__/sitemap.test.ts:99]
- [x] [Review][Patch] Тесты не закрепляют размещение подборок сразу после категорий и перед товарами [frontend/src/app/__tests__/sitemap.test.ts:84]
- [x] [Review][Patch] Проверка таймаута допускает один collection-запрос с неверным значением, если остальные вызовы используют 3000 мс [frontend/src/app/__tests__/sitemap.test.ts:99]

#### Rejected

- `false` — статус `review` не заявляет выполнение AC6: внешний шаг 4.6 явно оставлен открытым до мёрджа и выката.
- `false` — «Непокрытых требований нет» в Epic означает наличие Story для каждого FR, а не production-приёмку всех Story.
- `false` — историческое решение D1 датировано 17.09, а отдельная запись 19.09 явно фиксирует его пересмотр; одновременно действующих правил нет.
- `false` — `baseline_commit: f426f572` корректно охватывает создание Story, а `f503221b` — более поздняя точка ответвления implementation-ветки от `develop`; противоречия нет.
- `low`, отклонено — File List не перечисляет изменённый Epic и называет новую Story изменённой; исправление затрагивает только проверяемую спецификацию и не меняет продукт или проверяемость кода.
- `false` — значения 5 / 4 / 5 в AC6 помечены датой 19.09.2026 и являются снимком, а условие включения задано актуальным `count > 0`.
- `false` — Task 4.3 требует выполнить локальную проверку, но не требует отдельного приложенного снимка; обязательный снимок относится к ещё открытому production AC6.
- `false` — имя `CATEGORY_TREE_FETCH_TIMEOUT_MS` не создаёт текущего дефекта: обе проверки по утверждённому контракту используют одинаковые 3000 мс, отдельная настройка не требуется.
- `false` — Acceptance Auditor повторно отметил открытый AC6, но Story прямо фиксирует его как невыполненный внешний шаг и не заявляет production-приёмку завершённой.
- `medium`, дедуплировано — повторное замечание Verification Gap Reviewer о параллельном запуске объединено с одноимённым patch finding выше.

## Dev Notes

### Текущее состояние (код `f426f572`)

- `(blue)/catalog/page.tsx:107-138` — `generateMetadata`. Ветка подборки (`:111-117`) возвращает `{ ...buildMetadata({ ...CATALOG_COLLECTIONS[collection], path: '/catalog' }), keywords: null }`. Это единственная строка, которую меняет Task 1.
- `findCatalogCollection` (`:68-75`) — подборка только при одном ключе со значением `!== undefined`, ключ из трёх, значение строго `'true'`. Не трогать: этим уже обеспечен AC2.
- `buildMetadata` (`utils/seo.ts:125-169`) ставит `alternates.canonical` и `openGraph.url` из `normalizePath(path)`. `normalizePath` query не трогает (срезает только хвостовой `/` у строки), поэтому `/catalog?is_new=true` проходит как есть — так же работают категории (`/catalog?category=…`).
- `sitemap.ts` — статические разделы, категории из `/categories-tree/` (`toCategoryEntries`), товары, блог, новости, CMS. Подборок нет по D1; это фиксирует тест `sitemap.test.ts:66-72`.
- Ссылки на подборки: `config/quickLinks.tsx:31,38` (+ «Скидки»), `components/home/HitsSection.tsx:88`. Не меняются. `(electric)` каталог (`/electric/catalog?is_*`) закрыт `Disallow: /electric` — вне объёма.
- Клиентская канонизация URL (`CatalogPageClient.tsx:1015-1075`) чистит `page`, `ordering`, цены, `in_stock`, неизвестные бренды и категории; `is_*` не трогает — адрес подборки в адресной строке остаётся `?is_new=true`.

### Почему в sitemap проверяется `in_stock=true`

Прод 19.09.2026: без фильтра наличия подборки содержат 8 / 7 / 10 товаров, с `in_stock=true` — 5 / 4 / 5. Посетитель по умолчанию видит только товары в наличии (`CatalogPageClient.tsx:1146`), поэтому подборка, где все товары закончились, для него пустая. Фильтры `is_new`, `is_hit`, `is_sale` — `django_filters.BooleanFilter` (`backend/apps/products/filters.py:174-176`), `in_stock` — существующий параметр того же эндпоинта; backend не меняется.

### Технические ограничения

- Только frontend. Backend, OpenAPI, `next.config.ts`, `robots.ts`, `middleware.ts`, тексты подборок — вне объёма.
- Не вводить общий модуль «ключи подборок» для страницы и sitemap: две короткие константы дешевле связки между route-файлом и sitemap (Next запрещает произвольные экспорты из `page.tsx`).
- `generateMetadata` не делает запросов к API для подборок (AC1) — проверка наполненности только в sitemap.
- Комментарии — на русском (NFR-41-03).

### Архитектура и версии

Next.js 15.5.18, React 19.1.0, TypeScript 5.8, Vitest 4.x (`npm test`). `searchParams` — `Promise`. `MetadataRoute.Sitemap` — тип из `next`. Новые зависимости не нужны. Деплой: только `frontend/src/` — локально restart контейнера, на прод — rebuild образа frontend по ручному протоколу (память: CI-деплой всегда skipped).

### GitNexus (create-story, индекс `b15ba8b`, 19.09.2026)

Индекс помечен `stale` (HEAD `f426f572`), но `b15ba8b..f426f572` меняет только два docs-файла (стори 41.21, `sprint-status.yaml`) — граф кода актуален.

| Символ | Risk | Прямых вызывающих | Примечание |
|---|---|---|---|
| `generateMetadata` (`(blue)/catalog/page.tsx`) | LOW | 0 | точка входа Next; только по UID |
| `sitemap` (`app/sitemap.ts`) | LOW | 0 | точка входа Next |
| `toCategoryEntries` | LOW | 1 | только `sitemap` |
| `buildMetadata` (`utils/seo.ts`) | **HIGH** | 17 | не менять, только вызывать |

### Project Structure Notes

- UPDATE `frontend/src/app/(blue)/catalog/page.tsx` — ветка подборки и комментарий
- UPDATE `frontend/src/app/sitemap.ts` — подборки
- UPDATE `frontend/src/app/(blue)/catalog/__tests__/metadata.test.ts`
- UPDATE `frontend/src/app/__tests__/sitemap.test.ts`
- Документы: `_bmad-output/planning-artifacts/epic-41-site-audit.md` (FR-41-38 и раздел стори уже добавлены при create-story)

### Previous Story Intelligence (41.17, 41.21)

- 41.17 ввела подборки и зафиксировала canonical `/catalog` в тестах — эти ожидания и меняются (Task 3.1, 3.2); остальные сценарии 41.17 — страховка AC2.
- Метаданные каталога сканер видит в `<head>` только благодаря `htmlLimitedBots` с `AuditikBot` (41.13) — приёмку снимать `curl` именно с `-A "AuditikBot/1.0"`.
- 41.21 добавила гейт `npm run check:build` в frontend-ci: он поднимает `next start` на заглушке backend и обходит `PUBLIC_URLS` (включая `/catalog?is_hit=true`). Canonical гейт не проверяет, но сборка и обход должны остаться зелёными. Порт по умолчанию 3100, переопределяется `CHECK_BUILD_PORT`.
- Память: `vi.restoreAllMocks()` не снимает `stubGlobal`/`stubEnv` — в `sitemap.test.ts` моки пересоздаются в `beforeEach`, сохранить этот паттерн; не запускать тяжёлые прогоны параллельно.

### Git Intelligence

Последние коммиты `develop` (`f426f572`, `c6d84124`, `60974bf3`, `b15ba8bd`, `562e97b2`) — гейт production-сборки и документы 41.21; файлы этой стори ими не менялись. Формат коммитов: `feat(seo): … (стори 41.22)`.

### References

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-09-16.md` — D1 (исходное решение), §5.2 тексты
- `_bmad-output/implementation-artifacts/Story/41-17-catalog-collections-meta-descriptions-focus-search.md` — AC1, Task 1, тексты D1
- `_bmad-output/planning-artifacts/epic-41-site-audit.md` — FR-41-38, Story 41.22
- `tmp/audit-2026-09-10-verification-2026-09-19.md` — матрица, п. 12
- `tmp/audit-report-https___optisport.ru_-full (1).pdf`, стр. 9–10 — «Canonical на другой URL»
- `frontend/src/app/(blue)/catalog/page.tsx`, `frontend/src/app/sitemap.ts`, `frontend/src/utils/seo.ts`

## Открытые вопросы (не блокируют реализацию)

1. **Пустая подборка.** Если все товары подборки закончатся, страница с собственным canonical останется доступной по ссылкам с `/home` и может попасть в индекс пустой. Sitemap её уже не предлагает (решение 4). `noindex` при пустой выдаче потребовал бы запроса к API в `generateMetadata`; решено не делать до появления реального случая.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), Claude Code, dev-story.

### Debug Log References

- Preflight: ветка `feature/41-22-collections-self-canonical` от `origin/develop` (`f503221b`). GitNexus `stale` (индекс `5d9bb9f`), но `git diff 5d9bb9f f503221` пуст (только merge) — граф актуален.
- Impact (upstream, по UID): `generateMetadata` каталога — LOW, 0 вызывающих; `sitemap` — LOW, 0; `toCategoryEntries` — LOW, 1 (`sitemap`).
- Исходный прогон 0.4: 4 файла, 140 тестов — зелёный.
- RED: после правки тестов упали 3 сценария подборок в `metadata.test.ts` и 10 новых сценариев `sitemap.test.ts`; GREEN после реализации — 5 файлов (с `robots.test.ts`), 157 тестов.
- `npm test`: 197 файлов, 3468 passed / 16 skipped. `npm run lint`, `npx tsc --noEmit`, `npm run format:check` — чисто.
- Гейт 41.21: `NEXT_PUBLIC_API_URL=http://localhost:18001/api/v1 npm run build` + `npm run check:build` — «Проверка production-сборки пройдена».
- Review findings (20.09.2026): правки только в `sitemap.test.ts`, прод-код не тронут. RED-проверка каждой новой проверки мутацией `sitemap.ts` (последовательный обход вместо `Promise.all`; подборки в конец массива; `AbortSignal.timeout(2999)` в `isCollectionNonEmpty`; убран блок блога) — каждая мутация роняет свой тест, после `git checkout` прогон зелёный. `npm test`: 197 файлов, 3470 passed / 16 skipped; `npm run lint`, `npx tsc --noEmit`, `npm run format:check` чисто; повторный гейт 41.21 (`build` + `check:build`) — «Проверка production-сборки пройдена». `detect-changes --scope all` — `No changes detected` (тестовые файлы вне графа), прод-символы не затронуты.
- `detect-changes --scope all`: 5 файлов, символы только в `(blue)/catalog/page.tsx` и `sitemap.ts`. `getApiUrl`, `toEntries`, `toCategoryEntries`, `staticRoutes`, `now` помечены из-за сдвига строк — по `git diff` их тела не менялись. Risk `high` посчитан по числу процессов (7), все потоки начинаются в `sitemap` и `generateMetadata`.

### Completion Notes List

- **Task 1 (AC1, AC2).** В ветке подборки `generateMetadata` путь строится через `URLSearchParams`, так же как для категории: `/catalog?<ключ>=true`. `buildMetadata` ставит его в `alternates.canonical` и `openGraph.url`. `findCatalogCollection`, тексты D1, ветка категории и `utils/seo.ts` не менялись. Комментарий над `CATALOG_COLLECTIONS` обновлён.
- **Task 2 (AC3).** В `sitemap.ts` появились `COLLECTION_KEYS`, `isCollectionNonEmpty` (один запрос `products/?<ключ>=true&in_stock=true&page_size=1` с `revalidate` и `AbortSignal.timeout(3000)`), `fetchNonEmptyCollections` (параллельно, по одной подборке) и `toCollectionEntries` (`daily`, `0.7`). Результат стоит сразу после категорий. Подборка включается только при `res.ok` и числовом `count > 0`; ошибки сети, таймаут, не-2xx и невалидный JSON исключают только её. Проверку одной подборки я вынес в `isCollectionNonEmpty`, чтобы `try/catch` на каждый ключ давал изоляцию ошибок.
- **Task 3.** В `metadata.test.ts` изменено только `it.each` подборок: название и canonical/og:url. В `sitemap.test.ts` мок подборок стоит перед веткой `/products/` (разбор `searchParams`). Тест «не содержит подборок» заменён на «каждая подборка ровно один раз, без `focusSearch=`». Добавлены: проверка аргументов запроса, 7 сценариев отказа одной подборки (`count: 0`, не-2xx, сетевая ошибка, таймаут, нет `count`, `count: '5'`, невалидный JSON) — остальной sitemap на месте; проверка, что подборки не сочетаются с другими параметрами. Ожидаемый URL задан через `absoluteUrl`, потому что `SITE_URL` в тестах зависит от env. `robots-noindex-invariant.test.ts` и `robots.test.ts` прошли без изменений (AC4).
- **Task 4.3, локальная приёмка (`http://localhost`, `AuditikBot/1.0`, аноним).** `/catalog?is_new=true`, `?is_hit=true`, `?is_sale=true`: canonical и `og:url` — собственный адрес, title и description по D1, нет `meta keywords` и `meta robots`. `/catalog?is_new=true&page=2` и `/catalog`: canonical `http://localhost/catalog`, базовые метаданные. `sitemap.xml` содержит `catalog?is_new=true`, `?is_hit=true`, `?is_sale=true`; локальный API с `in_stock=true` отдаёт 5 / 7 / 6.
- **Review findings (4 шт., все [Patch], 20.09.2026)** — закрыты правками только в `sitemap.test.ts`:
  - Сохранность остального sitemap при отказе подборки: мок `beforeEach` теперь отдаёт содержимое для `/blog/`, `/news/` и `/pages/`, а сценарий отказа дополнительно требует `/blog/post`, `/news/item` и `/contacts`.
  - Параллельный старт: новый тест «запускает проверки всех подборок параллельно» отвечает на collection-запросы только после старта всех трёх (барьер `allStarted`) и выигрывает гонку у таймера 50 мс. При последовательном обходе первый ответ не приходит никогда — тест падает.
  - Порядок блоков: новый тест «размещает подборки сразу после категорий и до товаров» сверяет индексы — подборки идут подряд, начиная со следующего за последней категорией, в порядке `COLLECTION_KEYS`, и раньше `/product/ball`.
  - Таймаут: `expect(timeoutSpy).toHaveBeenCalledTimes(4)` заменён на `expect(timeoutSpy.mock.calls).toEqual([[3000], [3000], [3000], [3000]])` — счётчик пропускал один запрос с другим значением.
- **Task 4.6 / AC6 — приёмка на проде выполнена 20.09.2026.** Выкат сделал Alex (sync `develop` → `main`, rebuild frontend, `restart nginx`). Снимок снят `curl -s -A "AuditikBot/1.0"` с `https://optisport.ru`, аноним, без cookie — см. «Снимок приёмки AC6» ниже. Все три подборки отдают собственный canonical и `og:url`, тексты по таблице D1, без `meta keywords` и `meta robots`; `?is_new=true&page=2` и `/catalog` — canonical `https://optisport.ru/catalog` с базовыми метаданными; sitemap содержит три подборки ровно по одному разу, адресов с `focusSearch=` нет. Прод-счётчики `in_stock=true` — 5 / 4 / 5, совпадают со значениями AC6 от 19.09.2026.

### Снимок приёмки AC6 (прод, 20.09.2026, `curl -s -A "AuditikBot/1.0" https://optisport.ru/...`)

| Адрес | HTTP | `<title>` | canonical / `og:url` |
|---|---|---|---|
| `/catalog?is_new=true` | 200 | Новинки — каталог спортивных товаров \| OPTISPORT | `https://optisport.ru/catalog?is_new=true` |
| `/catalog?is_hit=true` | 200 | Лидеры продаж — каталог спортивных товаров \| OPTISPORT | `https://optisport.ru/catalog?is_hit=true` |
| `/catalog?is_sale=true` | 200 | Скидки — каталог спортивных товаров \| OPTISPORT | `https://optisport.ru/catalog?is_sale=true` |
| `/catalog?is_new=true&page=2` | 200 | Каталог спортивных товаров \| OPTISPORT | `https://optisport.ru/catalog` |
| `/catalog` | 200 | Каталог спортивных товаров \| OPTISPORT | `https://optisport.ru/catalog` |

Описания подборок (D1) в ответе прода:

- `is_new` — «Новинки в каталоге OPTISPORT: подборка спортивных товаров с ценами и условиями заказа для оптовых покупателей.»
- `is_hit` — «Лидеры продаж в каталоге OPTISPORT: подборка спортивных товаров с ценами и условиями заказа для оптовых покупателей.»
- `is_sale` — «Скидки в каталоге OPTISPORT: подборка спортивных товаров со сниженными ценами и условиями заказа для оптовых покупателей.»

У трёх подборок нет `<meta name="keywords">` и `<meta name="robots">`; у `/catalog` и `/catalog?is_new=true&page=2` базовые `keywords` присутствуют, как и до стори.

`sitemap.xml` (HTTP 200, 3362 `<url>`):

```
<loc>https://optisport.ru/catalog?is_new=true</loc>
<loc>https://optisport.ru/catalog?is_hit=true</loc>
<loc>https://optisport.ru/catalog?is_sale=true</loc>
```

`grep -o 'catalog?is_[a-z]*=true' | sort | uniq -c` → по 1 на каждую подборку; адресов с `focusSearch=` — 0.

Прод-API, наполненность подборок (`GET /api/v1/products/?<ключ>=true&in_stock=true&page_size=1`): `is_new` — `count: 5`, `is_hit` — `count: 4`, `is_sale` — `count: 5`.

### File List

- `frontend/src/app/(blue)/catalog/page.tsx` — изменён
- `frontend/src/app/sitemap.ts` — изменён
- `frontend/src/app/(blue)/catalog/__tests__/metadata.test.ts` — изменён
- `frontend/src/app/__tests__/sitemap.test.ts` — изменён
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — изменён
- `_bmad-output/implementation-artifacts/Story/41-22-catalog-collections-self-canonical-sitemap.md` — изменён

### Change Log

- 2026-09-19 — create-story: стори создана, статус `ready-for-dev`.
- 2026-09-19 — реализация 41.22: собственный canonical подборок `/catalog?<ключ>=true`, непустые подборки (в наличии) в sitemap, тесты; статус → review. Открыт 4.6 (выкат и приёмка AC6 на проде).
- 2026-09-20 — закрыты findings ревью: 4 items resolved (тесты sitemap — сохранность блога/новостей/CMS при отказе подборки, параллельный старт, порядок блоков, таймаут каждого запроса). Прод-код не менялся; статус → review.
- 2026-09-20 — выкат на прод (Alex) и приёмка AC6: canonical подборок, тексты D1 и три подборки в sitemap подтверждены на `https://optisport.ru`; снимок приложен. Task 4.6 закрыт, открытых задач нет.
