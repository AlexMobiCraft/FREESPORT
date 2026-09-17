---
baseline_commit: f264d0601550fe7ec0c93dccc00a19112b7a1387
---

# Story 41.17: Метаданные подборок, короткий description категорий и поиск без URL-параметра

Status: review
Baseline Revision: f264d060

## Story

As a владелец магазина,
I want чтобы подборки каталога не дублировали его title и description, description категорий не обрезался в выдаче, а поиск из шапки не создавал отдельный адрес,
so that сканер и поисковик не находили дубли там, где страница отличается только фильтром.

**Закрывает:** FR-41-33. **Решения владельца:** D1, D2 (Alex, 17.09.2026, `sprint-change-proposal-2026-09-16.md` §4, редакция ревью).

## Утверждённые решения (дословно, не пересматривать)

- **D1 — промежуточный вариант.** Подборки `?is_new=true`, `?is_hit=true`, `?is_sale=true` остаются фильтрами-переключателями: canonical `/catalog`, в sitemap не добавляются, ссылки на них (`config/quickLinks.tsx`, «Смотреть все» секций главной) **не меняются**. Получают собственные title и description. Замечание сканера «canonical на другой URL» по ним — принятое исключение (§5.6 предложения), это не дефект стори.
- **D2 — шаблон description категории:** `Товары категории «<Название>» в каталоге OPTISPORT: цены и условия заказа для оптовых покупателей.` Базовый description `/catalog`: «Оптовые и розничные цены» → «Оптовые и рекомендованные розничные цены».

### Тексты подборок (D1)

| Адрес | title | description |
|---|---|---|
| `/catalog?is_new=true` | `Новинки — каталог спортивных товаров \| OPTISPORT` | `Новинки в каталоге OPTISPORT: подборка спортивных товаров с ценами и условиями заказа для оптовых покупателей.` (110) |
| `/catalog?is_hit=true` | `Лидеры продаж — каталог спортивных товаров \| OPTISPORT` | `Лидеры продаж в каталоге OPTISPORT: подборка спортивных товаров с ценами и условиями заказа для оптовых покупателей.` (116) |
| `/catalog?is_sale=true` | `Скидки — каталог спортивных товаров \| OPTISPORT` | `Скидки в каталоге OPTISPORT: подборка спортивных товаров со сниженными ценами и условиями заказа для оптовых покупателей.` (121) |

В таблице `\|` — экранирование Markdown; в коде символ `|` без обратного слэша. Корневой layout **не** задаёт `title.template`, поэтому суффикс `| OPTISPORT` пишется в строке целиком, как в `CATALOG_TITLE`.

## Acceptance Criteria

### AC1 — метаданные подборок

**Given** адрес `/catalog`, у которого единственный query-параметр — `is_new`, `is_hit` или `is_sale` со значением `true`
**When** строятся метаданные страницы
**Then** title и description равны таблице «Тексты подборок (D1)», canonical — `/catalog`, Open Graph и Twitter повторяют title и description, `keywords` нет (как у категорий 41.13)
**And** при любом другом наборе параметров (два флага, флаг вместе с `category`, `page`, сортировкой, значение не `true`) поведение 41.13 не меняется, а `sitemap.ts` подборок не содержит

### AC2 — короткий description категорий

**Given** каждая категория публичного дерева
**When** строится description по шаблону D2
**Then** длина не превышает 160 символов, слов «розничн…» нет, тест проверяет это на фикстуре с самым длинным именем
**And** title категорий, canonical и поведение для неизвестного slug не меняются

### AC3 — поиск из шапки без query-параметра

**Given** три ссылки на поиск в шапке (desktop, mobile, sticky)
**When** посетитель переходит по ним с любой страницы, в том числе уже находясь на `/catalog` (переход, меняющий только фрагмент адреса, не меняет `searchParams`)
**Then** `href` не содержит query-параметра, а поле поиска каталога получает фокус
**And** старый адрес `/catalog?focusSearch=true` из закладок по-прежнему фокусирует поиск, canonical у него `/catalog`

> Фактические три ссылки в `Header.tsx` на `f264d060`: desktop (`:122`), мобильное меню авторизованного (`:241`), мобильное меню гостя (`:300`). Отдельной sticky-шапки в коде нет: `Header` целиком sticky. Все три ссылки — объём AC3.

### AC4 — регрессия тестов 41.13

**Given** базовый `/catalog` и адреса категорий
**When** выполняются тесты стори 41.13
**Then** они проходят без изменения ожиданий, кроме description категорий по D2 и description базового `/catalog`
**And** description базового `/catalog` (`CATALOG_DESCRIPTION`, повторён в `catalog/__tests__/metadata.test.ts`) — «Каталог спортивных товаров: фитнес и атлетика, единоборства, спортивные игры, плавание, туризм. Оптовые и рекомендованные розничные цены, доставка по России.» (157 символов)

### AC5 — приёмка на проде (NFR-41-08)

**Given** выкат на прод (NFR-41-08)
**When** `curl` с User-Agent `AuditikBot/1.0` запрашивает три подборки, две категории с самыми длинными именами и `/catalog?focusSearch=true`
**Then** у подборок title и description по таблице «Тексты подборок (D1)» и canonical `/catalog`, description категорий укладывается в 160 символов, у `focusSearch` метаданные базового `/catalog`; снимок приложен к стори

## Tasks / Subtasks

- [x] **Task 0 — preflight** (все AC)
  - [x] 0.1 Ветка `feature/41-17-catalog-collections-meta` от актуального `develop` (прямые коммиты в `develop` запрещены).
  - [x] 0.2 `npx gitnexus status` → `up-to-date`, иначе попросить пользователя `! npx gitnexus analyze --skip-agents-md`.
  - [x] 0.3 `impact --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по UID (имена `generateMetadata` и `Header` неоднозначны): `Function:frontend/src/app/(blue)/catalog/page.tsx:generateMetadata`, `Function:frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:CatalogContent`, `Function:frontend/src/components/layout/Header.tsx:Header`. Сообщить blast radius пользователю. Снимок на create-story — в Dev Notes «GitNexus».
  - [x] 0.4 Зафиксировать исходный прогон: `npx vitest run "src/app/(blue)/catalog" src/app/__tests__/sitemap.test.ts src/components/layout/__tests__/Header.test.tsx` — всё зелёное до правок.

- [x] **Task 1 — метаданные подборок в `generateMetadata`** (AC1)
  - [x] 1.1 В `frontend/src/app/(blue)/catalog/page.tsx` добавить константы трёх подборок (ключ параметра → title, description) — дословно из таблицы D1.
  - [x] 1.2 Распознавание подборки — **до** ветки `category`, без запроса к API: учитываются только ключи со значением `!== undefined`; ключ ровно один; он из `is_new | is_hit | is_sale`; значение — строка, строго равная `'true'` (массив `['true','true']`, `'TRUE'`, `'1'`, `''` — не подборка). Сравнение с `'true'` совпадает с клиентом (`CatalogPageClient.tsx:431-433`).
  - [x] 1.3 Возврат: `{ ...buildMetadata({ title, description, path: '/catalog' }), keywords: null }`. `keywords: null` обязателен: без него унаследуются `keywords` корневого `app/layout.tsx`. `image` не передавать — дефолт `buildMetadata` (`/image.jpg`) как у базы и категорий.
  - [x] 1.4 Все прочие комбинации идут в существующую логику 41.13 без изменений: `is_new=true&category=<валидный>` → метаданные категории; `is_new=true&page=2`, `is_new=true&is_hit=true`, `is_new=true&ordering=…`, `is_new=true&focusSearch=true`, `is_new=false` → базовые.
  - [x] 1.5 Сигнатуру `buildMetadata` и `utils/seo.ts` **не трогать** (HIGH).

- [x] **Task 2 — шаблон description категорий и базовый description** (AC2, AC4)
  - [x] 2.1 `page.tsx:88` → шаблон D2 дословно. Title категории (`${name} — спортивные товары`), canonical и fallback не менять.
  - [x] 2.2 `CATALOG_DESCRIPTION` (`page.tsx:10`) → текст AC4 дословно.
  - [x] 2.3 Обрезку имени, многоточие или альтернативный шаблон **не добавлять** — см. «Открытые вопросы», п. 1.

- [x] **Task 3 — поиск из шапки** (AC3)
  - [x] 3.1 NEW `frontend/src/utils/catalogSearchFocus.ts`: `CATALOG_SEARCH_HASH = 'search'`, `CATALOG_SEARCH_HREF = '/catalog#search'`, имя события (`'optisport:catalog-search-focus'`) и функция `requestCatalogSearchFocus()` (`window.dispatchEvent(new Event(...))`, безопасна на сервере). Комментарии на русском, с объяснением, зачем событие (см. Dev Notes «Почему не только хэш»).
  - [x] 3.2 `Header.tsx:122, 241, 300`: `href={CATALOG_SEARCH_HREF}`; `onClick` вызывает `requestCatalogSearchFocus()`. В мобильных ссылках сохранить `setIsMobileMenuOpen(false)`. Классы, `aria-label="Поиск"`, иконки и **прочие ссылки шапки не менять** (41.18 требует, чтобы ссылки `/profile*`, `/login` остались как есть).
  - [x] 3.3 `CatalogPageClient.tsx`: на `<search role="search">` (`:1549`) добавить `id={CATALOG_SEARCH_HASH}` — цель штатной прокрутки Next к фрагменту. Проверить `grep -rn 'id="search"' frontend/src` — других элементов с этим id нет на `f264d060`.
  - [x] 3.4 Заменить эффект `:1265-1273` одной функцией фокуса (сохранить `setTimeout(…, 100)` и очистку таймера) и тремя триггерами:
    - при монтировании: `window.location.hash === '#search'`;
    - legacy: `focusSearchParam === 'true'` (зависимость остаётся примитивом — см. комментарий `:403-408`);
    - подписка на событие из 3.1 (`addEventListener`/`removeEventListener` в cleanup).
  - [x] 3.5 Хэш из адреса **не** удалять и `focusSearch` из URL **не** вычищать: `updateSearchParams` (`:846-880`) сам сбрасывает фрагмент при смене фильтра, а переписывание URL сломало бы тесты URL-state 41.13 (AC6 той стори).
  - [x] 3.6 Не трогать `(electric)` каталог и его ссылки `/electric/catalog?is_*` — адрес закрыт `Disallow`, вне объёма.

- [x] **Task 4 — тесты** (AC1–AC4)
  - [x] 4.1 `src/app/(blue)/catalog/__tests__/metadata.test.ts`:
    - `BASE_DESCRIPTION` → текст AC4; description категории `Настольный теннис` → шаблон D2. Остальные ожидания 41.13 не менять.
    - `it.each` по трём подборкам: точные title/description, `alternates.canonical === '/catalog'`, `openGraph.{title,description,url:'/catalog'}`, `twitter.{title,description}`, `keywords: null`, `fetch` не вызван.
    - `it.each` «не подборка → базовые метаданные»: два флага; `is_new=false`; `is_new=['true','true']`; `is_new=true&page=2`; `is_hit=true&ordering=-name`; `is_sale=true&focusSearch=true`.
    - флаг + валидная `category` → метаданные категории (дерево из мока).
    - `focusSearch=true` → базовые, `fetch` не вызван.
    - D2-инвариант: фикстура дерева с самым длинным реальным именем «Форма для кикбоксинга и тайского бокса» (38 симв. → 126 симв.) и граничным синтетическим именем из 72 символов (→ ровно 160); `description.length <= 160`, `not.toMatch(/розничн/i)`. Базовый description: длина 157.
  - [x] 4.2 `src/app/__tests__/sitemap.test.ts`: ни один URL не содержит `is_new=`, `is_hit=`, `is_sale=`, `focusSearch=`.
  - [x] 4.3 `src/components/layout/__tests__/Header.test.tsx`: у всех ссылок «Поиск» (desktop; мобильное меню гостя; мобильное меню авторизованного — по паттернам существующих тестов меню и auth-стора) `href === '/catalog#search'` и нет `?`; клик вызывает событие фокуса (spy на `window.dispatchEvent` или слушатель); мобильный клик закрывает меню.
  - [x] 4.4 `src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` (моки `useSearchParams`/`resetSearchParams` уже есть, `:136-193`) — фокус поля с `aria-label="Поиск товаров в каталоге"` при: (а) `window.location.hash = '#search'` на монтировании; (б) `resetSearchParams('focusSearch=true')`; (в) уже смонтированный каталог без параметров + `requestCatalogSearchFocus()` — ключевой случай «уже на `/catalog`»; (г) без хэша, параметра и события фокуса нет. Использовать fake timers или `waitFor` под задержку 100 мс; хэш восстанавливать в `afterEach` (память: `vi.restoreAllMocks()` не снимает всё — восстанавливать явно).
  - [x] 4.5 Существующие ~75+ сценариев `CatalogPage.test.tsx` проходят без изменения ожиданий.

- [ ] **Task 5 — проверки и документация**
  - [x] 5.1 Frontend: `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check` (в `frontend/`). Backend не меняется — pytest и OpenAPI не требуются (NFR-41-02 не затронут).
  - [x] 5.2 Локальная приёмка по NFR-41-08 (аноним, без cookie): после `docker compose --env-file .env -f docker/docker-compose.yml restart frontend` снять `curl -s -A "AuditikBot/1.0"` для `/catalog?is_new=true`, `?is_hit=true`, `?is_sale=true`, `?focusSearch=true`, двух длинных категорий; проверить `<title>`, `meta description`, `link rel=canonical`, `og:*`, отсутствие `meta keywords`. В приватном окне браузера: клик «Поиск» с `/home` и повторно с `/catalog` → фокус в поле.
  - [x] 5.3 `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только `generateMetadata` каталога, `CatalogContent`, `Header` и новый util.
  - [x] 5.4 Dev Agent Record, File List; `sprint-status.yaml` → `review`.
  - [ ] 5.5 **Внешний шаг (после мёрджа и ручного выката по SSH):** AC5 на `https://optisport.ru` с `AuditikBot/1.0`, снимок в стори. Повторный прогон сканера — шаг владельца после 41.17–41.20.

## Dev Notes

### Текущее состояние (код `f264d060`)

- **`frontend/src/app/(blue)/catalog/page.tsx`** — server wrapper из 41.13. `generateMetadata` (`:74-97`): нет `category` → `buildCatalogMetadata()` (без запроса к API); иначе `fetchCategoryNames()` (`/categories-tree/`, `revalidate: 3600`, таймаут 3000 мс) → при валидном slug метаданные категории с `keywords: null`, canonical `/catalog?category=<slug>` через `URLSearchParams`; любое исключение → базовые. Подборки сейчас получают базовые метаданные — источник дублей title/description в отчёте 16.09.
  - Сохранить: fail-soft `try/catch`, отсутствие запроса к API без `category`, `CATEGORY_TREE_FETCH_TIMEOUT_MS`, `CATALOG_KEYWORDS` у базы, экспорт `default CatalogPage`.
- **`layout.tsx`** — только `return children` (метаданные из него убраны в 41.13). Не трогать.
- **`CatalogPageClient.tsx`** (`CatalogContent`) — URL-state на примитивах `searchParams.get(...)` (`:403-420`); `focusSearchParam` → эффект `:1265-1273` с `setTimeout(100)` без очистки; `searchInputRef` передаётся `SearchAutocomplete` (`:1554`, `forwardRef` → `HTMLInputElement`). `updateSearchParams` строит `pathname?query` и сохраняет чужие ключи, в том числе `focusSearch`; фрагмент при этом теряется.
- **`Header.tsx`** — Client Component, sticky. Три `Link` на `/catalog?focusSearch=true`; мобильные с `onClick={() => setIsMobileMenuOpen(false)}`. Тесты шапки ищут ссылку по `name: /Поиск/i` и проверяют классы фокуса (`Header.test.tsx:453-466`) — не ломать.
- **`sitemap.ts`** — статические маршруты + категории дерева `/catalog?category=<slug>`; подборок нет и не будет. Правка кода не нужна, только тест-страж.
- **Корневой `app/layout.tsx`** — `title` строкой без шаблона, `keywords: 'спорт, товары, оптом, B2B, B2C…'`. Эти умолчания меняет 41.19 (D7), не эта стори.
- **Ссылки на подборки** (не менять, D1): `config/quickLinks.tsx:31, 38, 45`; `components/home/HitsSection.tsx:88` и аналогичные «Смотреть все».

### Почему не только хэш

Next.js 15.5.18, `navigate-reducer.js:112-119, 226-233`: переход, у которого отличается только фрагмент, помечается `onlyHashChange`. Роутер прокручивает к `document.getElementById(hash)` (`layout-router.js:124-132`), но `useSearchParams` не меняется, компонент не перемонтируется, а `pushState` не порождает `hashchange`. Поэтому:
- с другой страницы на `/catalog#search` — сработает проверка хэша при монтировании;
- уже на `/catalog` (или на `/catalog#search` — повторный клик) — ни монтирования, ни смены параметров; фокус даёт только событие из `onClick`;
- с `/catalog?category=x` — обычная мягкая навигация на `/catalog#search`; `CatalogContent` не перемонтируется, фокус тоже даёт событие.

Слушатель `hashchange` не нужен, `window.navigation` (Navigation API) не использовать — неполная поддержка браузерами. Прецедент чтения `window.location.hash` в `useEffect` — `(blue)/unsubscribe/UnsubscribeClient.tsx:35` (41.15).

### Контракт query-параметров (дополняет таблицу 41.13)

| URL | Метаданные | Canonical | API-запрос |
|---|---|---|---|
| `/catalog?is_new=true` / `is_hit=true` / `is_sale=true` | подборки D1 | `/catalog` | нет |
| `/catalog?is_new=true&is_hit=true` | базовые | `/catalog` | нет |
| `/catalog?is_new=false`, `?is_new=`, `?is_new=true&is_new=true` | базовые | `/catalog` | нет |
| `/catalog?is_sale=true&page=2` / `&ordering=…` / `&focusSearch=true` | базовые | `/catalog` | нет |
| `/catalog?is_new=true&category=<валидный>` | категории (D2) | `/catalog?category=<slug>` | да |
| `/catalog?focusSearch=true` | базовые | `/catalog` | нет |
| `/catalog#search` | базовые (фрагмент на сервер не приходит) | `/catalog` | нет |

### D2: запас длины

Шаблон без имени — 88 символов, значит имя до **72** символов даёт ≤ 160. Прод 16.09 (`/api/v1/categories-tree/`, 85 узлов): максимум 38 символов («Форма для кикбоксинга и тайского бокса» → 126), далее 33, 31, 31, 30. Старый шаблон давал 173. Длина в JS — `String.length` (UTF-16); кириллица и «ёлочки» — по одной единице, как у сканера.

### Технические ограничения

- Только фронтенд. Backend, OpenAPI, `next.config.ts` (`htmlLimitedBots` из 41.13 уже включает `AuditikBot`), `robots.ts`, `middleware.ts` — вне объёма (последние два правят 41.18/41.19).
- Не делать подборки посадочными страницами: без собственного canonical, без sitemap, без `noindex` (D1).
- Не вводить общий helper «разбора параметров каталога» для клиента и сервера — клиентская логика URL-state остаётся нетронутой.
- Не обещать в текстах наличие, остатки или конкретные цены; тексты — только утверждённые.
- React 19: новый `ref`-код без `forwardRef`; существующий `SearchAutocomplete` не переписывать.
- Комментарии — на русском (NFR-41-03).

### Архитектура и версии

Next.js 15.5.18, React 19.1.0, TypeScript 5.8, Vitest 4.x (`npm run test`, не Jest). `searchParams` страницы — `Promise`, как уже сделано в `page.tsx`. Новые зависимости не нужны. Деплой: правки только в `frontend/src/` — локально хватает restart контейнера; на прод — полный rebuild образа frontend по обычному ручному протоколу.

### GitNexus (create-story, индекс `f264d06`, 17.09.2026)

| Символ | Risk | Прямых вызывающих | Примечание |
|---|---|---|---|
| `generateMetadata` (`(blue)/catalog/page.tsx`) | LOW | 0 | точка входа Next; имя неоднозначно (8 символов) — только по UID |
| `buildCatalogMetadata` | LOW | 1 | только `generateMetadata` |
| `CatalogContent` | LOW | 1 | `CatalogPageClient` |
| `Header` (`components/layout/Header.tsx`) | LOW по графу | 0 | в предложении помечен CRITICAL по ширине: рендерится на всех страницах `(blue)` через `(blue)/layout.tsx` — меняются только три ссылки поиска |
| `buildMetadata` (`utils/seo.ts`) | **HIGH** | 17, 4 процесса, 2 модуля | не менять, только вызывать |

### Project Structure Notes

- UPDATE `frontend/src/app/(blue)/catalog/page.tsx`
- UPDATE `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` — только эффект фокуса и `id` у `<search>`
- UPDATE `frontend/src/components/layout/Header.tsx` — три ссылки поиска
- NEW `frontend/src/utils/catalogSearchFocus.ts` (+ при желании `utils/__tests__/catalogSearchFocus.test.ts`)
- UPDATE тесты: `catalog/__tests__/metadata.test.ts`, `catalog/__tests__/CatalogPage.test.tsx`, `app/__tests__/sitemap.test.ts`, `components/layout/__tests__/Header.test.tsx`

Общих файлов с 41.19 и 41.20 нет (§5.7 предложения): `Header.tsx` и `catalog/page.tsx` правит только 41.17.

### Previous Story Intelligence (41.13, 41.16)

- 41.13 перенесла клиентский каталог в `CatalogPageClient.tsx` и ввела server `generateMetadata`; из-за стриминга метаданных в Next 15.2+ сканер мог не увидеть их в `<head>` — решено `htmlLimitedBots` + `AuditikBot` (по access log прода). Проверять приёмку `curl` именно с этим UA, иначе метаданные могут прийти в `<body>`.
- В 41.13 длина description осознанно превышала 160 — ровно это D2 и отменяет; тест 41.13 с полной строкой description категории обязан обновиться, остальные ожидания — нет.
- Полный frontend-прогон после 41.13: 3194 passed, 16 skipped — ориентир, не требование.
- Память проекта: `vi.restoreAllMocks()` не снимает `spyOn` на браузерных API — восстанавливать явно; параллельные тяжёлые прогоны мешают таймингозависимым тестам.

### Git Intelligence

`f264d060` (develop): последний PR — #190 «фильтр каталога Бренд → Торговая марка» (`167551ab`: 4 строки `CatalogPageClient.tsx` + 8 строк `CatalogPage.test.tsx`), #187–#189 — служебные мёрджи. Тот же клиентский файл и его тест — дифф стори ограничить эффектом фокуса и `<search>`. Мобильное меню в тестах шапки открывается кнопкой `name: 'Открыть меню'` (`Header.test.tsx:221-237`).

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.17] и FR-41-33
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-16.md#4, #5.2, #5.6, #5.7]
- [Source: _bmad-output/implementation-artifacts/tasks/intent-site-audit-2026-09-16.md] — триаж, CC-1/CC-2
- [Source: _bmad-output/implementation-artifacts/Story/41-13-catalog-category-seo-metadata.md] — контракт метаданных категорий, `htmlLimitedBots`
- [Source: project-context.md#4, #5, #7]
- `frontend/node_modules/next/dist/client/components/router-reducer/reducers/navigate-reducer.js`, `layout-router.js` — поведение переходов по фрагменту в 15.5.18

## Открытые вопросы (не блокируют реализацию)

1. **Имя категории длиннее 72 символов.** Сейчас таких нет (максимум 38), но AC2 требует ≤ 160 для каждой категории. Стори закрепляет границу тестом и не вводит обрезку. Если в 1С появится длинное имя, варианты: (а) укороченный шаблон без «: цены и условия заказа для оптовых покупателей»; (б) базовые метаданные; (в) принять превышение. Нужно решение владельца, если требуется гарантия на будущее.
2. **«sticky» в AC3** — в коде нет третьей, sticky-копии ссылки; третья ссылка — мобильное меню гостя. Стори трактует AC3 как «все три ссылки поиска в `Header.tsx`».

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (claude-opus-5), bmad-dev-story, 17.09.2026

### Debug Log References

- Preflight: ветка `feature/41-17-catalog-collections-meta` от `f264d060`; `gitnexus status` — up-to-date; impact upstream: `generateMetadata` каталога LOW/0, `CatalogContent` LOW/1 (`CatalogPage`), `Header` LOW/0 (по ширине — все страницы `(blue)`). Исходный прогон 4 файлов: 146 passed.
- RED: `metadata.test.ts` — 28 failed до правки `page.tsx`; `CatalogPage.test.tsx` (фокус) — 3 failed до правки клиента; `Header.test.tsx` и util-тест — падали на отсутствующем модуле.
- `tsc --noEmit` поймал тип `vi.fn()` в слушателе теста шапки → `vi.fn<() => void>()`.
- 17.09.2026, ответ на ручную проверку владельца («фокус не срабатывает»): расширение Claude in Chrome не подключено, браузер вели через установленный в проекте Playwright 1.57 (Chromium 1200 и настоящий Chrome, видимое окно). `document.activeElement` во всех 21 комбинации (desktop/mobile, `/home`, `/catalog`, категория, товар, :80/:3000) — поле поиска. Но скриншот показал: после перехода на `#search` Next вызывает `domNode.scrollIntoView()` (`layout-router.js:197`), `scrollY = 144`, `<search>` встаёт в `top: 0` под sticky-шапку высотой 60 px — поле в фокусе, но невидимо. Исправление: `scroll-mt-24` на `<search>` (приём проекта: `delivery/page.tsx:130`, `partners/page.tsx:155`). E2E `catalog-search-focus.spec.ts` до правки — 3 failed (центр поля перекрыт `A`/`IMG` шапки), после — 3 passed на Docker-стенде (`PLAYWRIGHT_BASE_URL=http://localhost`). Попытка повторить условия CI локально (`next dev` без backend) не удалась: там падает и существующий `search-history.spec.ts`, зелёный в CI, — окружение Windows не показательно; spec мокает API так же, как `search-history`.
- Грабли стенда: после `restart frontend` nginx на :80 отдаёт 502 до `restart nginx`; hot reload в контейнере правки из Windows не видит — нужен `restart frontend`.
- Итог: `npm test` — 184 файла, 3260 passed, 16 skipped; `npm run lint`, `npx tsc --noEmit`, `npm run format:check` — 0.
- `detect-changes --scope all`: 10 файлов; символы — `generateMetadata`/`buildCatalogMetadata`/`fetchCategoryNames`/`getApiUrl` и типы `page.tsx` (сдвиг строк), `CatalogContent` (+ соседние `handleToggle`, `handleSelectCategory`, `handleSelectAllCategories` — задеты сдвигом хунка, код не менялся), `Header`. Risk «high» — от числа процессов по сдвинутым строкам, лишних символов нет.

### Completion Notes List

- 17.09.2026: create-story — полный анализ контекста: эпик, предложение, стори 41.13, код на `f264d060`, GitNexus (индекс `f264d06`), длины текстов пересчитаны, поведение Next 15.5.18 при переходе по фрагменту проверено по исходникам. Код не менялся.

### File List
- 17.09.2026: dev-story — реализация.
  - **AC1:** `findCatalogCollection` в `page.tsx` распознаёт подборку до ветки `category`, без API: единственный определённый ключ из `is_new|is_hit|is_sale` (проверка `Object.hasOwn`, не `in` — ключи прототипа не проходят) со строкой `'true'`. Возврат `buildMetadata({title, description, path: '/catalog'})` + `keywords: null`. Прочие комбинации — логика 41.13 без изменений. Тексты — дословно D1.
  - **AC2/AC4:** шаблон D2 и новый `CATALOG_DESCRIPTION` (157). Тесты: имя 38 симв. → 126, синтетическое 72 → 160, без «розничн». Остальные ожидания 41.13 не менялись.
  - **AC3:** новый `utils/catalogSearchFocus.ts` (hash, href, событие, `requestCatalogSearchFocus`). Три ссылки `Header.tsx` → `/catalog#search` + событие в `onClick` (мобильные по-прежнему закрывают меню). `CatalogContent`: общий `focusSearchInput` (задержка 100 мс, таймер в ref, очистка при размонтировании), триггеры — хэш при монтировании, событие window, legacy `focusSearch=true` (отдельный эффект на примитиве). `<search id="search">`; других `id="search"` в `src` нет. URL не переписывается.
  - **Тесты:** metadata +19 сценариев (29 всего); sitemap — страж на `is_new=`/`is_hit=`/`is_sale=`/`focusSearch=`; Header — desktop, мобильное меню гостя и авторизованного (href без `?`, событие, закрытие меню); CatalogPage — хэш, legacy-параметр, событие на смонтированном каталоге, негатив, снятие подписки; util — 3 теста.
  - **5.2 (локально, `AuditikBot/1.0`, :3000, после restart frontend):** три подборки — title/description по D1 (110/116/121), canonical, `og:url` = `/catalog`, `og:*`/`twitter:*` совпадают, `keywords` нет. `?focusSearch=true` и `?is_new=true&page=2` — базовые метаданные (157). Две самые длинные категории **локальной** БД (120 узлов): «Обувь для тхеквондо, кикбоксинга, рукопашного боя, самбо» (56) → 144, «Инвентарь для туризма и отдыха на природе» (41) → 129; `keywords` нет. Локально имя длиннее прод-максимума (38) — запас до 72 подтверждён. **Не выполнено:** ручной клик «Поиск» в браузере (с `/home` и с `/catalog`) — браузерных инструментов в сессии нет; сценарии закрыты юнит-тестами, ручная проверка за владельцем. Поэтому 5.2 не отмечен.
  - **Дефект, найденный владельцем при ручной проверке, исправлен:** фокус ставился, но поле после прокрутки к `#search` оказывалось под sticky-шапкой. `scroll-mt-24` на `<search>`; добавлен e2e `tests/e2e/catalog-search-focus.spec.ts` (с главной, повторный клик на прокрученном каталоге, мобильное меню) — проверяет фокус **и** что центр поля не перекрыт. Скриншот в Chrome после правки: переход с прокрученной категории → поле видно под шапкой с оранжевой рамкой фокуса. Этим закрыт 5.2 (ручная часть выполнена через Playwright). После правки: `tsc`, `lint`, `format:check` — 0; vitest каталога, шапки и util — 9 файлов, 264 passed.
  - **5.5** — внешний шаг после мёрджа и ручного выката, не отмечен.
  - Замечание, вне объёма: ctrl/cmd-клик по «Поиск», когда вкладка уже на `/catalog`, тоже шлёт событие — поле в текущей вкладке получит фокус. Безвредно, не исправлялось.

### File List

- `frontend/src/app/(blue)/catalog/page.tsx` (M)
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` (M)
- `frontend/src/components/layout/Header.tsx` (M)
- `frontend/src/utils/catalogSearchFocus.ts` (A)
- `frontend/src/utils/__tests__/catalogSearchFocus.test.ts` (A)
- `frontend/tests/e2e/catalog-search-focus.spec.ts` (A)
- `frontend/src/app/(blue)/catalog/__tests__/metadata.test.ts` (M)
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` (M)
- `frontend/src/app/__tests__/sitemap.test.ts` (M)
- `frontend/src/components/layout/__tests__/Header.test.tsx` (M)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (M)
- `_bmad-output/implementation-artifacts/Story/41-17-catalog-collections-meta-descriptions-focus-search.md` (M)

### Change Log

- 17.09.2026 — реализация 41.17: метаданные подборок (D1), шаблон description категорий и базовый description (D2), поиск из шапки через `/catalog#search` + событие фокуса; тесты; статус → review. Открыты 5.2 (ручной клик в браузере) и 5.5 (приёмка на проде).
- 17.09.2026 — исправлено: поле поиска после перехода на `#search` пряталось под sticky-шапкой (`scroll-mt-24`); e2e-страж видимости фокуса; 5.2 закрыт. Открыт только 5.5.
