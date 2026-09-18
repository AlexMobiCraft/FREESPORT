---
baseline_commit: 372b3efb
---

# Story 41.21: Бандл без `example`, тексты без розницы и превосходных степеней, один тег robots на 404

Status: review
Baseline Revision: 372b3efb

## Story

As a владелец магазина,
I want чтобы публичные страницы не обещали розничных продаж и «лучших цен», клиентский код не нёс латинских образцов, а страница 404 отдавала одну директиву robots,
so that сайт описывал только действующее предложение без рекламных преувеличений и не давал повторному сканеру новых срабатываний.

**Закрывает:** FR-41-37; открытый `[Review][Patch]` «Третье ревью 18.09.2026» стори 41.20 (AC5, буквальный ноль `example`).
**Источник:** проверка закрытия отчёта 16.09.2026, выполнена 18.09.2026 — `tmp/audit-2026-09-16-verification-2026-09-18.md`; контент правок — `tasks/intent-audit-2026-09-16-followups.md`, разделы A, C, D.
**Решения владельца (Alex, 18.09.2026):** R1 — розницу из публичных текстов убрать; R2 — тема `/electric` остаётся доступной, меняются только её метаданные; делать A, C и D.

## Утверждённые решения (дословно, не пересматривать)

- **Решение владельца по 41.20 (18.09.2026):** vendor-исключение отменено, AC5 стори 41.20 трактуется буквально — 0 вхождений `example` без учёта регистра. **Охват (Alex, 18.09.2026, Q1): ноль считается в клиентских чанках, которые загружают публичные страницы.** Чанки jsPDF страницы `/profile/orders/[id]` (только для авторизованного, `Disallow: /profile`) — принятое исключение.
- **R1:** розничная регистрация отключена временно (флаг `REGISTRATION_ALLOW_RETAIL`), но метаданные и тексты описывают действующее предложение. Розница, «B2C», «для всех» из публичных текстов удаляются. Когда розницу включат, тексты вернутся вместе с флагом. Логика та же, что в D2 и D7 стори 41.17 и 41.19.
- **R2:** `/electric` — только метаданные. Маршрут, компоненты темы, `robots.ts` (`Disallow: /electric`) и `KNOWN_TOP_LEVEL_ROUTES` не меняются.
- **D4 (контекст, 41.18):** адрес под `Disallow` не несёт meta `noindex`. Поэтому ни `/electric`, ни `/search` robots не получают.
- **38-ФЗ ст. 5 ч. 3 п. 1:** превосходная степень без подтверждения («крупнейший», «ведущих», «лучшие цены», «по лучшим ценам») и непроверяемые числа («более 10 000 товаров») удаляются. Это тот же довод, по которому D7 убрал «Ведущая» из корня.

### Тексты (утверждены Alex 18.09.2026, Q2; вносить дословно)

Длины посчитаны по символам Python `len()`.

| Адрес / файл | Поле | Было | Стало |
|---|---|---|---|
| `/home` — `app/(blue)/home/page.tsx:8` | title | Спортивные товары оптом и в розницу | **Спортивные товары оптом — каталог и условия \| OPTISPORT** (55) |
| `/home` — `:9-10` | description | Платформа для оптовых и розничных продаж спортивных товаров. Широкий ассортимент, выгодные условия для бизнеса. | **Оптовые поставки спортивных товаров для магазинов, спортивных клубов и федераций: каталог, цены для оптовых покупателей, доставка по России.** (140) |
| `/home` — `:11` | keywords | спортивные товары оптом, спортивные товары в розницу, спортивная экипировка | **поле удалить** (как D7) |
| `/coming-soon` — `app/(coming-soon)/coming-soon/page.tsx:12-13` | description | OPTISPORT — оптовые и розничные продажи спортивных товаров. Сайт скоро откроется, по вопросам сотрудничества пишите на info@optisport.ru. | **OPTISPORT — оптовые продажи спортивных товаров. Сайт скоро откроется, по вопросам сотрудничества пишите на info@optisport.ru.** (125) |
| `/coming-soon` — `app/(coming-soon)/coming-soon/page.tsx:11` | title | OPTISPORT скоро откроется — оптовые продажи спорттоваров | **без изменений** |
| `/electric` — `app/(electric)/electric/page.tsx:43-68` | весь объект `metadata` | см. «Текущее состояние» | **`buildMetadata({ title: 'OPTISPORT — спортивные товары оптом', description: 'Оптовые продажи спортивных товаров: каталог, условия для оптовых покупателей, доставка по России.', path: '/electric' })`** — тексты корневого умолчания D7 (35 / 97), без `keywords` и `noIndex` |
| `/search?q=…` — `app/(blue)/search/page.tsx:40` | description при непустом `q` | Результаты поиска по запросу "${query}" в магазине OPTISPORT. Найдите спортивные товары по лучшим ценам. | **Результаты поиска по запросу "${query}" в магазине OPTISPORT.** |

**Карточка `/coming-soon` (`app/ComingSoonClient.tsx`, видимый текст первой страницы обхода сканера):**

| Место | Было | Стало |
|---|---|---|
| Абзац под «МЫ СКОРО ВЕРНЕМСЯ» (`:54-58`) | Платформа для оптовых и розничных `<br />` продаж спортивных товаров | **Оптовые продажи `<br />` спортивных товаров** |
| Преимущество 1, иконка `ShoppingCart` (`:66-67`) | **B2C Магазин** / Розничные продажи для всех | **Оптовые заказы** / Каталог и условия для оптовых покупателей |
| Преимущество 2, иконка `Users` (`:73-74`) | **B2B Решения** / Оптовые поставки для бизнеса | **Для организаций** / Магазины, спортивные клубы и федерации |
| Преимущество 3, иконка `TrendingUp` (`:80-81`) | **Лучшие цены** / Конкурентные предложения | **Скидки от объема закупок** / Размер скидки зависит от объёма заказа |

Title `/home` и заголовки трёх карточек утверждены владельцем дословно; заголовок третьей карточки — формулировка владельца «Скидки от объема закупок» (написание без «ё» — как у владельца и как «МЫ СКОРО ВЕРНЕМСЯ» на той же странице). Подписи под заголовками первых двух карточек предложены create-story и владельцем не оспорены; подпись третьей («Размер скидки зависит от объёма заказа») подобрана create-story к новому заголовку после ответа владельца — если нужна другая, заменить до dev-story. Остальные тексты согласованы с уже утверждёнными: `/register` («Доступ к ценам откроется после проверки заявки»), D7. Заголовок «МЫ СКОРО ВЕРНЕМСЯ», строка «РАЗРАБОТКА ИДЕТ ПО ПЛАНУ!», иконки, вёрстка и анимации не меняются: их закрепляет `ComingSoonClient.test.tsx:90-94`.

## Acceptance Criteria

### AC1 — в клиентских чанках публичных страниц нет `example`

**Given** production-сборка (`next build`)
**When** все JS-чанки, которые загружают публичные страницы (перечень — Task 1.6), проверяются на `example` без учёта регистра
**Then** вхождений 0, в том числе в общем чанке, где сейчас лежит `[zustand devtools middleware] … Example: { "type": "__setState" … }`
**And** middleware `devtools` из `zustand/middleware` в production-сборку не попадает: в `.next/static/chunks/**` нет строки `zustand devtools middleware`

### AC2 — сторы работают как раньше

**Given** сторы `useAuthStore`, `useCartStore`, `useFavoritesStore`, `useOrderStore`
**When** они создаются в production и в development
**Then** публичный API сторов (состояние, действия, `getState`/`setState`/`subscribe`, `persist` у корзины с ключом `cart-storage-v3`) не изменился, существующие тесты сторов проходят без изменения ожиданий
**And** в development `devtools` подключён с прежними именами `AuthStore`, `CartStore`, `FavoritesStore`, `OrderStore`, а в production — нет

### AC3 — метаданные `/home`

**Given** метаданные `app/(blue)/home/page.tsx`
**When** выполняется тест
**Then** title, description и соответствующие поля Open Graph и Twitter равны таблице «Тексты», canonical `/home`, поля `keywords` нет
**And** `revalidate = 3600` и рендер страницы не изменились

### AC4 — `/coming-soon`: метаданные и карточка

**Given** страница `/coming-soon`
**When** строятся метаданные и отображается `ComingSoonClient`
**Then** description и тексты карточки равны таблицам «Тексты», title не изменился, robots по-прежнему не задан
**And** заголовок «МЫ СКОРО ВЕРНЕМСЯ», «РАЗРАБОТКА ИДЕТ ПО ПЛАНУ!», e-mail в подвале, кнопка «Настройки cookie» и строка реестра операторов на месте (тесты 41.3, 41.12 и 41.14 проходят без изменения ожиданий)

### AC5 — метаданные `/electric`

**Given** метаданные `app/(electric)/electric/page.tsx`
**When** выполняется тест
**Then** title «OPTISPORT — спортивные товары оптом», description «Оптовые продажи спортивных товаров: каталог, условия для оптовых покупателей, доставка по России.», canonical и `og:url` — `/electric`, картинка — `DEFAULT_OG_IMAGE_META`, `keywords` и `robots` нет
**And** страница, её секции, `robots.ts` и `KNOWN_TOP_LEVEL_ROUTES` не изменились

### AC6 — страж от возврата розницы и превосходных степеней

**Given** метаданные `/`, `/home`, `/coming-soon`, `/electric`, `/search?q=…` и видимый текст `ComingSoonClient`
**When** выполняется тест-страж
**Then** в title, description, `openGraph.title/description`, `twitter.title/description` и тексте карточки нет совпадений с `/рознич|розниц|B2C|B2B|платформ|ведущ|крупнейш|лучш|10\s?000/i`
**And** description `/catalog` («Оптовые и рекомендованные розничные цены», решение D2) в страж не входит и не меняется

### AC7 — один тег robots на настоящем 404

**Given** адрес, на который приложение отвечает настоящим 404 (`/nonexistent-xyz` — механизм 41.0, `/catalog/zzz`, `/zzz/yyy`)
**When** запрашивается HTML production-сборки
**Then** в ответе ровно один `<meta name="robots">` — `noindex`, его ставит сам Next; `app/not-found.tsx` поле `robots` не задаёт
**And** soft-404 динамических страниц (`/product/…`, `/blog/…`, `/news/…`, `[slug]`), которые отвечают 200, по-прежнему отдают свой `noindex, follow`; тест инварианта D4 из 41.18 обновлён под новый механизм и проходит

### AC8 — приёмка на проде (NFR-41-08)

**Given** выкат на прод (`up -d --build frontend`, затем `restart nginx`)
**When** `curl -A "AuditikBot/1.0"` без cookie снимает `/coming-soon`, `/home`, `/electric`, `/nonexistent-xyz`, `/product/zzz-none`, а чанки публичных страниц проверяются рецептом Task 1.6 против `https://optisport.ru`
**Then** метаданные совпадают с AC3–AC5, на 404 один тег robots, на soft-404 — `noindex, follow`, `example` в чанках — 0; владелец подтверждает карточку `/coming-soon` в браузере без cookie
**And** снимок приложен к стори; стори 41.20 закрыта (`[Review][Patch]` третьего ревью → `[x]`, статус `done`), запись E21 реестра 41.16 дополнена прод-доказательством

## Tasks / Subtasks

- [x] **Task 0 — подготовка** (AC: все)
  - [x] 0.1 Коммит `d64d4909` (стори 41.20 → `in-progress`, открытый `[Review][Patch]`) влит владельцем в локальный `develop` 18.09.2026 (`fbb57041`) и уходит в `origin/develop` вместе с PR create-story этой стори (ветка `docs/story-41-21-create-story`). Перед 0.2 убедиться, что этот PR смёрджен: `git log origin/develop --oneline | grep d64d4909`.
  - [x] 0.2 Ветка `feature/41-21-bundle-example-retail-wording` от свежего `origin/develop`.
  - [x] 0.3 `npx gitnexus status`. При `stale` попросить владельца выполнить `! npx gitnexus analyze --skip-agents-md`. Затем `impact` по символам из раздела «GitNexus» с `-r "C:\Users\1\DEV\FREESPORT"`.

- [x] **Task 1 — A: `devtools` только вне production** (AC: 1, 2)
  - [x] 1.1 Создать `frontend/src/stores/devtoolsInDev.ts`:
    ```ts
    import { devtools } from 'zustand/middleware';

    /**
     * `devtools` только вне production. В production ветка вырезается при сборке,
     * а вместе с ней и код middleware zustand: в клиентский бандл не попадает
     * подсказка `Example: {…}` (168-ФЗ, стори 41.20/41.21), а состояние сторов,
     * включая токен AuthStore, не отдаётся расширению Redux DevTools.
     */
    export const devtoolsInDev: typeof devtools =
      process.env.NODE_ENV === 'production'
        ? ((initializer => initializer) as typeof devtools)
        : devtools;
    ```
  - [x] 1.2 В `authStore.ts:11,43`, `favoritesStore.ts:2,22`, `orderStore.ts:12,34` заменить импорт `devtools` на `import { devtoolsInDev } from './devtoolsInDev'` и вызов `devtools(` на `devtoolsInDev(`. В `cartStore.ts:12` оставить `import { persist } from 'zustand/middleware'` и заменить только `devtools` (`:55`). Второй аргумент `{ name: '…Store' }` не трогать.
  - [x] 1.3 Проверить, что обращений к API devtools у сторов нет: `grep -rn "\.devtools\b" frontend/src`. Ожидается пусто. Если что-то найдётся, в production оно получит `undefined`: HALT и доложить.
  - [x] 1.4 Юнит-тест `src/stores/__tests__/devtoolsInDev.test.ts`: при `NODE_ENV=production` (`vi.stubEnv` + `vi.resetModules` + динамический импорт) обёртка возвращает переданный инициализатор без изменений; вне production это сам `devtools` из `zustand/middleware`.
  - [x] 1.5 `npm run build` локально. Проверить все чанки, а не только чанки пяти страниц: `grep -rlic example .next/static/chunks`. На `372b3efb` результат такой: `3688-*.js` (zustand devtools), `164f4fb6-*.js` и `4199.*.js` (jsPDF и его зависимость rgbcolor, ключ `example:` в таблице цветов и путь `examples/PDF.js/...`). После правки `3688-*` должен выпасть. **Если строка zustand осталась** (tree-shaking не сработал), запасной вариант: в `next.config.ts` → `webpack(config, { dev })` при `!dev` задать alias `zustand/middleware$` на локальный модуль, который реэкспортирует только `persist` из `zustand/esm/middleware.mjs`. Правка `next.config.ts` требует полного пересбора. Применять только после неудачной проверки.
  - [x] 1.6 Проверка публичных страниц (рецепт 8.7 стори 41.20, исправленный: без учёта регистра, шире охват). Сначала на `next start` локально, затем на проде:
    ```bash
    BASE=${BASE:-http://localhost:3000}
    for page in coming-soon home catalog "catalog?is_hit=true" register b2b-register password-reset login cart checkout partners privacy-policy about delivery requisites electric; do
      curl -s -A "AuditikBot/1.0" "$BASE/$page" -o /tmp/pg.html
      grep -o '/_next/static/[^"]*\.js' /tmp/pg.html | sort -u | while read c; do
        curl -s "$BASE$c" | grep -qi "example" && echo "$page $c: example"
      done
    done
    ```
    Ожидание — пусто. Чанки jsPDF (`164f4fb6-*`, `4199.*`) загружает только `/profile/orders/[id]` (`OrderDetailClient.tsx:14` → `utils/orderPdfExport.ts:6`, серверный `page_client-reference-manifest.js`). Страница доступна только авторизованному и закрыта `Disallow: /profile`. Эти чанки в охват AC1 не входят — решение Alex 18.09.2026 (Q1).
  - [x] 1.7 Если в 1.6 найдётся иной источник `example` в чанках публичных страниц: наш код — исправить в этой стори; сторонняя библиотека без переключателя — HALT, доложить владельцу с контекстом строки.

- [x] **Task 2 — C: `/home`** (AC: 3, 6)
  - [x] 2.1 `app/(blue)/home/page.tsx:7-14`: title и description по таблице, строку `keywords` удалить, `path: '/home'` и комментарий про канонический адрес оставить.
  - [x] 2.2 `app/(blue)/home/__tests__/page.test.tsx:152-186`: точные ожидания title, description, `openGraph.title/description`, `twitter.title/description`; тест «должна содержать keywords» заменить на `expect(metadata.keywords).toBeUndefined()`.

- [x] **Task 3 — C: `/coming-soon`** (AC: 4, 6)
  - [x] 3.1 `app/(coming-soon)/coming-soon/page.tsx:12-13` — description по таблице. Title и комментарий про `noIndex` не менять.
  - [x] 3.2 `app/ComingSoonClient.tsx:54-81` (абзац `:54-58`, карточки `:66-67`, `:73-74`, `:80-81`) — абзац и три карточки по таблице. Иконки, классы и `motion`-обёртки не менять.
  - [x] 3.3 `app/(coming-soon)/coming-soon/__tests__/page.test.tsx:29-33` — новое точное значение description.
  - [x] 3.4 `app/__tests__/ComingSoonClient.test.tsx` — новый `it`: видны «Оптовые продажи», «Оптовые заказы», «Для организаций», «Скидки от объема закупок»; нет текстов «B2C», «B2B», «Розничные», «Лучшие цены», «Платформа». Существующие `it` (строки 48-116) не менять.

- [x] **Task 4 — C: `/electric`** (AC: 5, 6)
  - [x] 4.1 `app/(electric)/electric/page.tsx:40-68` — объект `metadata` заменить вызовом `buildMetadata` по таблице. `DEFAULT_OG_IMAGE`, `DEFAULT_OG_IMAGE_META` из импорта убрать, если они больше не используются. Добавить `buildMetadata`. JSDoc файла (строка 4, «FREESPORT Platform») привести к «OPTISPORT»: это комментарий, не метаданные, но правка в той же строке файла.
  - [x] 4.2 Новый тест `app/(electric)/electric/__tests__/metadata.test.ts` по образцу `app/__tests__/layout-metadata.test.ts`: title, description, `alternates.canonical === '/electric'`, `openGraph.url === '/electric'`, `openGraph.images` = `[DEFAULT_OG_IMAGE_META]`, `keywords` и `robots` — `undefined`. Импорт страницы тянет серверные секции: если импорт в Vitest тяжёл, замокать их, как в `app/(electric)/__tests__/landmarks.test.tsx`.
  - [x] 4.3 `landmarks.test.tsx` проходит без изменений.

- [x] **Task 5 — C: `/search`** (AC: 6)
  - [x] 5.1 `app/(blue)/search/page.tsx:40` — убрать предложение «Найдите спортивные товары по лучшим ценам.». Ветка без `q` не меняется. Комментарий D4 (`:34-36`) сохранить.
  - [x] 5.2 В `app/(blue)/search/__tests__/page.test.tsx` проверить ожидания description и поправить, если есть; добавить `it` на отсутствие «лучш».

- [x] **Task 6 — C: страж** (AC: 6)
  - [x] 6.1 Новый `src/app/__tests__/public-copy-no-retail-superlatives.test.ts`. Для `@/app/layout`, `(blue)/home/page`, `(coming-soon)/coming-soon/page`, `(electric)/electric/page` и `generateMetadata` страницы поиска с `q='мяч'` собрать строки title, description, `openGraph.title/description`, `twitter.title/description` и проверить их регуляркой из AC6. Шрифты `next/font/google` замокать, как в `coming-soon/__tests__/page.test.tsx:20-23`.
  - [x] 6.2 В тот же файл добавить рендер `ComingSoonClient` и проверку `container.textContent` той же регуляркой. `og:image:alt` («OPTISPORT — платформа продаж спортивных товаров», `utils/seo.ts:47`) в страж не входит, см. «Не делать».

- [x] **Task 7 — D: один тег robots на 404** (AC: 7)
  - [x] 7.1 `app/not-found.tsx:6-9` — удалить `robots` из `metadata`, `title` оставить. Комментарий над `metadata`: «`noindex` на ответ 404 Next ставит сам (`app-render.js`, условие `is404Page`); собственный `robots` давал второй, противоречивый тег `noindex, nofollow`. На soft-404 со статусом 200 метаданные этого файла не применяются — там `noindex` задаёт `generateMetadata` страницы».
  - [x] 7.2 `app/__tests__/robots-noindex-invariant.test.ts:233-237`: тест «404 — noindex, nofollow» заменить на «404 — `robots` не задан, `noindex` ставит Next» (`expect(metadata.robots).toBeUndefined()`). Комментарий со ссылкой на эту стори и на AC7. Остальные блоки инварианта (`/unsubscribe`, `it.each` динамических страниц) не менять.
  - [x] 7.3 Проверка на локальной production-сборке (`next start`): `/nonexistent-xyz`, `/catalog/zzz`, `/zzz/yyy` → 404 и ровно один `<meta name="robots" content="noindex"/>`; `/product/zzz-none`, `/blog/zzz-none`, `/news/zzz-none` → 200 и один `noindex, follow`. Команда: `curl -s -o /tmp/r.html -w '%{http_code}' URL; grep -o '<meta name="robots"[^>]*>' /tmp/r.html`.

- [ ] **Task 8 — проверки, приёмка, трекер** (AC: все)
  - [x] 8.1 `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check` — всё зелёное. Backend не затрагивается.
  - [x] 8.2 `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"`. Ожидаемо затронуты четыре стора, `devtoolsInDev`, `NotFound` (только metadata), `ComingSoonClient`, `generateMetadata` поиска, метаданные трёх страниц. `buildMetadata` меняться не должен.
  - [x] 8.3 Dev Agent Record, File List; `sprint-status.yaml` → `review`.
  - [ ] 8.4 **Внешний шаг (после мёрджа, ручной выкат по SSH):** sync `develop` → `main` через PR (5 обязательных контекстов). На сервере: `git fetch origin main && git reset --hard origin/main`, `docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend`, затем **`restart nginx`**. AC8: рецепт 1.6 с `BASE=https://optisport.ru`, curl метаданных (`/coming-soon`, `/home`, `/electric`, `/search?q=мяч`), рецепт 7.3 против прода. Владелец смотрит `/coming-soon` в браузере без cookie. Снимок положить в стори.
  - [ ] 8.5 После AC8: в стори 41.20 отметить `[Review][Patch]` третьего ревью `[x]` со ссылкой на 41.21, статус → `done` (стори и `sprint-status.yaml`). В реестре 41.16, запись E21: одной строкой добавить прод-доказательство — 0 `example` в чанках публичных страниц, дата, коммит.

### Review Findings

- [x] [Review][Patch] Добавить fail-closed CI-проверку production-чанков публичных страниц на `example` без учёта регистра и `zustand devtools middleware` после `npm run build` [`.github/workflows/frontend-ci.yml:86`]
- [x] [Review][Patch] Закрепить точными ожиданиями все три подписи карточек `/coming-soon`, а не только их заголовки и отсутствие запрещённых слов [`frontend/src/app/__tests__/ComingSoonClient.test.tsx:118`]
- [x] [Review][Patch] Добавить автоматическую проверку собранного приложения: настоящий HTTP 404, ровно один `robots=noindex` и сохранение `noindex, follow` у soft-404 [`frontend/src/app/__tests__/robots-noindex-invariant.test.ts:236`]

#### Rejected

- [Rejected][false] Решение владельца 18.09.2026: AC6 проверяет редакционный шаблон; пользовательский `q` не является рекламным обещанием, поэтому `generateMetadata` сохраняет запрос дословно и отдельная фильтрация запрещённых фраз не требуется.
- [Rejected][false] Статус `review` при открытых 8.4–8.5 не выдаёт AC8 за завершённый: Task 8.3 прямо требует перевести Story в review перед post-merge production-приёмкой, а Completion Notes явно фиксируют незавершённые внешние шаги.
- [Rejected][low] В старой записи третьего ревью Story 41.20 рядом остались исторические фразы `in-progress` и «Статус done сохранить», но действующее решение однозначно задано открытым Patch, текущим статусом Story 41.20 и Task 8.5; исправление было бы только переписыванием review-истории.
- [Rejected][low] Заголовок таблицы называет тексты утверждёнными, а примечание различает явно утверждённые заголовки и неоспоренные подписи; реализация дословно соответствует самой таблице, а устранение редакционной неоднозначности требует менять спецификацию.
- [Rejected][false] Перечень публичных страниц для AC1 нормативно задан самой Task 1.6; отсутствующие в списке маршруты нельзя объявить нарушением реализации без изменения утверждённого scope.
- [Rejected][medium] `curl -s` действительно допускает ложный зелёный результат при сетевой ошибке или пустом HTML, но предложенное исправление меняет acceptance-рецепт спецификации; отдельный исполняемый CI-гейт сохранён как Patch выше.
- [Rejected][medium] Рецепт Task 1.6 печатает совпадения, но сам не является fail-closed командой; исправление текста Story отклонено, а тот же риск покрыт отдельным Patch на CI-гейт.
- [Rejected][false] Ленивые чанки после произвольных действий не входят в явно заданный маршрутный рецепт Task 1.6; доказательств, что запрещённый общий zustand-чанк скрыт только за таким действием, нет.
- [Rejected][false] Helper-тест `devtoolsInDev` проверяет ровно контракт Task 1.4, существующие store-тесты покрывают состояние и действия, а имена DevTools и `cart-storage-v3` сохранены буквально; реальный пробел production bundle вынесен в отдельный Patch.
- [Rejected][false] Регулярка `\s` в JavaScript охватывает обычный, неразрывный и узкий неразрывный пробел, а реализация дословно повторяет утверждённую `/10\s?000/i`; вариант с несколькими пробелами не доказывает нарушение текущего AC.
- [Rejected][false] Известный soft-404 `/privacy-policy` предсуществует, явно исключён из 41.21 и уже записан в `deferred-work.md`; общая цель Epic про непротиворечивые заголовки безопасности не превращает этот meta-robots пробел в регрессию Story.
- [Rejected][false] R1 не требует автоматического переключения текстов frontend по backend-флагу `REGISTRATION_ALLOW_RETAIL`; фраза «вернутся вместе с флагом» описывает будущий согласованный выпуск, а не runtime-контракт этой Story.
- [Rejected][false] Охват стража AC6 прямо ограничен Task 6.1–6.2 пятью наборами metadata и карточкой, а `og:image:alt` явно исключён; тексты login и остальные публичные поверхности не являются пропущенной реализацией этого AC.
- [Rejected][false] Acceptance Auditor продублировал тезис о незавершённом AC8: Story находится на предусмотренном промежуточном этапе `review`, а не в `done`, и открытые production-шаги отражены явно.

## Dev Notes

### Текущее состояние (код `372b3efb`, прод 18.09.2026)

**A — источник `example`.** Общий чанк `3688-912aa751a9ddbcb4.js` одинаковый на проде и в локальной сборке. Его загружают все публичные страницы. Единственное вхождение `example` в нём — текст ошибки middleware devtools zustand 4.5.7 (`node_modules/zustand/esm/middleware.mjs`):
```
[zustand devtools middleware] Unsupported __setState action format. … Example: { "type": "__setState", "state": { "abc123Store": { "foo": "bar" } } }
```
В Completion Notes 41.20 это вхождение ошибочно названо предупреждением `[DEPRECATED] The 'destroy' method…`. На самом деле это строка из `devtools`. `devtools` безусловно оборачивает четыре стора, поэтому попадает в production.

| Стор | Импорт / вызов | Имя | Потребителей (prod / тесты) |
|---|---|---|---|
| `stores/authStore.ts` | `:11` / `:43` | `AuthStore` | 21 / 13 |
| `stores/cartStore.ts` | `:12` (вместе с `persist`) / `:55`, снаружи `persist` | `CartStore` | 17 / 13 |
| `stores/favoritesStore.ts` | `:2` / `:22` | `FavoritesStore` | 3 / 0 |
| `stores/orderStore.ts` | `:12` / `:34` | `OrderStore` | 2 / 4 |

**Почему обёртка должна сработать.** `next build` здесь webpack (`package.json` → `"build": "next build"`). `DefinePlugin` заменяет `process.env.NODE_ENV` литералом. Webpack сворачивает условное выражение с константным условием, и импорт `devtools` становится неиспользуемым. `zustand` объявляет `"sideEffects": false` (`node_modules/zustand/package.json:186`), поэтому неиспользуемый экспорт выпадает при минификации, а `persist` из того же модуля остаётся. Это рассуждение, а не замер: подтверждает его только Task 1.5.

**Типы.** `typeof devtools` сохраняет мутатор `['zustand/devtools', never]` в типе стора. Поэтому `create<AuthState>()(devtoolsInDev(...))` типизируется так же, как сейчас. Тождественная функция в production возвращает инициализатор без `devtools`-расширения API (`store.devtools`), а его никто не использует (Task 1.3).

**Другие вхождения `example` в сборке (`grep -rlic example .next/static/chunks`, 18.09.2026):**

| Чанк | Источник | Кто загружает |
|---|---|---|
| `3688-912aa751a9ddbcb4.js` | zustand devtools | все страницы — **устраняется этой стори** |
| `164f4fb6-cafca3d180b7eab5.js` | jsPDF 4.2.1: rgbcolor (`example:["rgb(123, 234, 45)"…]`), путь `examples/PDF.js/web/viewer.html` | только `/profile/orders/[id]` |
| `4199.52b11f53afb6f733.js` | rgbcolor (зависимость jsPDF/canvg), `getHelpXML`, id `rgbcolor-examples` | только `/profile/orders/[id]` |

**C — тексты, которые меняются** (прод 18.09.2026, `curl -A "AuditikBot/1.0"`):
- `/home`: `<title>Спортивные товары оптом и в розницу</title>`, description «Платформа для оптовых и розничных продаж…», keywords «…в розницу…».
- `/coming-soon`: сюда ведёт `/` (307), сканер начинает обход с этой страницы. Description «оптовые и розничные продажи». В видимой карточке «Платформа для оптовых и розничных продаж», «B2C Магазин / Розничные продажи для всех», «B2B Решения», «Лучшие цены / Конкурентные предложения».
- `/electric` (закрыт `Disallow`, ссылок из синей темы нет, отдаёт 200): title «OPTISPORT - Спортивные товары оптом и в розницу»; description «Крупнейший интернет-магазин спортивной одежды и экипировки в России. Более 10 000 товаров от ведущих брендов. Выгодные цены для B2B клиентов.»; keywords с «B2B спорттовары»; `og:url` — корень сайта (canonical нет); twitter «Более 10 000 товаров от ведущих брендов».
- `/search?q=…`: «…Найдите спортивные товары по лучшим ценам.»

**D — два тега robots.** Прод 18.09.2026:

| Адрес | Код | robots |
|---|---|---|
| `/nonexistent-xyz`, `/catalog/zzz`, `/zzz/yyy` | 404 | `noindex` **и** `noindex, nofollow` |
| `/product/zzz-none`, `/blog/zzz-none`, `/news/zzz-none` | 200 | только `noindex, follow` |

Первый тег на 404 Next 15.5.18 ставит сам: `node_modules/next/dist/server/app-render/app-render.js:160-164`, `if (!isPossibleServerAction && (is404Page || isInvalidStatusCode)) → <meta name="robots" content="noindex"/>`. Второй идёт из `app/not-found.tsx:8`. Снимок soft-404 доказывает, что на ответах 200 метаданные `not-found.tsx` **не применяются**: иначе там был бы второй тег. Значит, `robots` в `not-found.tsx` влияет только на настоящие 404, где Next уже ставит `noindex`, и его удаление безопасно.

**Пересмотр AC 41.18.** AC5 стори 41.18 требует: «`noindex` на `not-found.tsx`… сохранены». Ответ 404 по-прежнему несёт `noindex`, меняется только его источник: Next вместо метаданных файла. Тест инварианта (`robots-noindex-invariant.test.ts:234`) обновляется в Task 7.2. Решение владельца «делать D» от 18.09.2026 это покрывает.

### Не делать

- **`buildMetadata` и `DEFAULT_OG_IMAGE_META` (`utils/seo.ts`) не менять.** Риск HIGH по графу. `og:image:alt` «OPTISPORT — платформа продаж спортивных товаров» стоит на всех страницах, но нарушением не является: русское слово, без превосходной степени, без розницы.
- Description `/catalog` «Оптовые и рекомендованные розничные цены» — решение D2, не трогать.
- `components/home/AboutTeaser.tsx:20` («…для розничных магазинов…») — розничные магазины являются оптовыми клиентами, текст корректен.
- `robots.ts`, `KNOWN_TOP_LEVEL_ROUTES`, секции темы `/electric` — R2.
- Не удалять `devtools` из сторов совсем: в development он нужен.
- Не обновлять `zustand` до v5 и не менять `jspdf`: вне охвата (Q1 — ноль только в чанках публичных страниц).
- `privacy-policy/page.tsx:101` при отсутствии страницы в CMS отдаёт soft-404 без `noindex` (`generateMetadata` не ставит robots для `!page`). Это существующий пробел, не связанный с D: метаданные `not-found.tsx` на soft-404 и сейчас не применяются. Записать в `deferred-work.md`, не чинить здесь.

### Технические ограничения

- Frontend в Docker: после правки `src/` — `restart frontend`; для проверки чанков нужна production-сборка (`next build` + `next start` или `up -d --build frontend`), dev-сервер чанки не минифицирует и `NODE_ENV` у него `development`.
- PowerShell 5.1: команды с `&&` не работают — рецепты с `curl`/`grep` выполнять через Bash-инструмент (Git Bash). Для HTTP-проверок — `curl`, не `Invoke-WebRequest` (память проекта).
- `vi.restoreAllMocks()` не снимает `spyOn` на `localStorage` (память проекта) — в тесте `devtoolsInDev` использовать `vi.stubEnv`/`vi.unstubAllEnvs()` и `vi.resetModules()`.

### Архитектура и версии

Next 15.5.18 (App Router, сборка webpack), React 19, zustand 4.5.7 (ESM, `sideEffects: false`), jsPDF 4.2.1, Vitest. Веб-исследование не потребовалось: поведение подтверждено по `node_modules` установленных версий. Миграций БД нет, backend и `openapi.yaml` не затрагиваются.

### GitNexus (create-story, индекс `5524d3e`, HEAD `372b3efb`, 18.09.2026)

`status` = stale формально, но `git diff 5524d3e 372b3ef` пуст (merge-коммит без изменений кода) — граф соответствует коду.

| Символ | Риск | Замечание |
|---|---|---|
| `useAuthStore`, `useCartStore`, `useFavoritesStore`, `useOrderStore` | LOW (граф: 0 прямых) | Граф не видит вызовов хуков. Импортёров по `cypher` (`IMPORTS` → `src/stores/*`): auth 22, cart 17, favorites 3, order 2. Фактический охват широкий, но API сторов не меняется — страховка AC2 и существующие тесты |
| `NotFound` | LOW | меняется только объект `metadata` |
| `ComingSoonClient` | не найден в графе | default-export компонента; один потребитель — `coming-soon/page.tsx` (+ тест) |
| `buildMetadata` | HIGH | **не менять**, только новый вызов в `/electric` |

### Project Structure Notes

- Новые файлы: `src/stores/devtoolsInDev.ts`, `src/stores/__tests__/devtoolsInDev.test.ts`, `src/app/(electric)/electric/__tests__/metadata.test.ts`, `src/app/__tests__/public-copy-no-retail-superlatives.test.ts`.
- Изменяемые: 4 стора, `app/(blue)/home/page.tsx`, `app/(coming-soon)/coming-soon/page.tsx`, `app/ComingSoonClient.tsx`, `app/(electric)/electric/page.tsx`, `app/(blue)/search/page.tsx`, `app/not-found.tsx`; тесты `home/__tests__/page.test.tsx`, `coming-soon/__tests__/page.test.tsx`, `app/__tests__/ComingSoonClient.test.tsx`, `search/__tests__/page.test.tsx`, `app/__tests__/robots-noindex-invariant.test.ts`.
- Документы: стори 41.20 (Task 8.5), реестр 41.16 (E21), `deferred-work.md` (privacy-policy soft-404), `sprint-status.yaml`.

### Previous Story Intelligence (41.20, 41.19, 41.18, 41.17)

- **41.20:** рецепт проверки чанков (8.7) был регистрозависимым (`grep -q "example"`) и проверял только чанки пяти страниц. Из-за этого `Example` из zustand прошёл первую приёмку и всплыл на третьем ревью. Здесь — `grep -qi` и расширенный список страниц (Task 1.6). Формы клиентские, в серверном HTML их нет: приёмка текстов форм идёт браузером и по чанкам.
- **41.19:** метаданные через `buildMetadata` без `noIndex` и `keywords` для адресов под `Disallow`. Тесты — точные значения title, description, og, twitter (`layout-metadata.test.ts`). Правка `next.config.ts` требует полного rebuild. Sync `develop` → `main` только через PR.
- **41.18:** инвариант D4 (`robots-noindex-invariant.test.ts`) — пересматривается в Task 7.2. Прод-снимок кладётся в стори в формате «Снимок прода».
- **41.17:** точные тексты и длины в таблице, тест 41.13 с изменёнными ожиданиями перечислен явно — так же здесь (Task 2.2, 3.3).

### Git Intelligence

Последние коммиты: `5524d3e7` (41.18, cookie точки возврата и единый noindex), `6785fd67` / `59dce537` / `128bc989` (41.20, формулировка согласия и плейсхолдеры), merge PR #202–#204. Стиль сообщений: `feat(scope): … (стори 41.NN)`, `test(scope): …`, на русском.

### References

- `tmp/audit-2026-09-16-verification-2026-09-18.md` — проверка закрытия отчёта 16.09, раздел «Незакрытые пункты» и B1–B2.
- `_bmad-output/implementation-artifacts/tasks/intent-audit-2026-09-16-followups.md` — разделы A, C, D.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-09-16.md` — D2, D4, D7.
- `_bmad-output/planning-artifacts/epic-41-site-audit.md` — FR-41-37, Story 41.21.
- Ветка `docs/story-41-20-reopen`, `Story/41-20-…md` — «Третье ревью 18.09.2026».
- `Story/41-19-…md`, `Story/41-18-…md`, `Story/41-16-editorial-audit-decision-register.md` (E21).
- `node_modules/next/dist/server/app-render/app-render.js:160-164`; `node_modules/zustand/esm/middleware.mjs`; `node_modules/zustand/package.json:186`.

## Решения по вопросам create-story (Alex, 18.09.2026)

- **Q1 — охват нуля `example`:** считать ноль в чанках публичных страниц. Чанки jsPDF/rgbcolor (`/profile/orders/[id]`, авторизованный, `Disallow`) — принятое исключение, замена jsPDF вне охвата.
- **Q2 — тексты:** title `/home` — «Спортивные товары оптом — каталог и условия | OPTISPORT»; карточки `/coming-soon` — «Оптовые заказы», «Для организаций», «Скидки от объема закупок» (третья заменяет предложенную «Цены по вашей роли»).

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), dev-story 18.09.2026.

### Debug Log References

- Сборки: `npm run build` (webpack) трижды — после Task 1, после Task 7 и с `NEXT_PUBLIC_MIDDLEWARE_API_URL=http://localhost:8001/api/v1` для проверки 7.3. Логи — в scratchpad сессии, в репозиторий не входят.
- `grep -rlic example .next/static/chunks` после правки: только `164f4fb6-cafca3d180b7eab5.js` и `4199.52b11f53afb6f733.js` (jsPDF/rgbcolor, исключение Q1); `3688-*` выпал; `grep -rl "zustand devtools middleware" .next/static/chunks` — пусто.
- Первая проверка 7.3 дала на `/nonexistent-xyz` 200 и `noindex, follow`: локальная сборка без `.env` инлайнит в middleware умолчание `http://backend:8000/api/v1`, с хоста недоступное, и механизм 41.0 уходит в fail-open (soft-404 через `[slug]`). С адресом backend хоста — 404. Код не менялся, это свойство локального окружения.

### Completion Notes List

- 18.09.2026 dev-story, ответ на code review. Все три `[Review][Patch]` закрыты:
  - ✅ Resolved review finding [Patch]: fail-closed CI-гейт production-чанков. `frontend/scripts/check-production-build.mjs` (`npm run check:build`) — шаг «Проверка production-сборки (чанки и robots)» в `frontend-ci.yml` сразу после `npm run build`, в required-контексте «Фронтенд: тесты». Скрипт поднимает `next start` (порт 3100) и заглушку backend по цепочке `getApiBaseUrl` middleware. Заглушка отдаёт пустой полный список CMS-слагов, на остальное 404. Проверяются чанки из двух источников: фактические ссылки из HTML 16 адресов рецепта 1.6 и шести адресов 404/soft-404 плюс манифест сборки (все страницы App Router, кроме `/profile/**` — Q1). Нарушение — `example` без учёта регистра в этих чанках или `zustand devtools middleware` в любом файле `.next/static/chunks/**`. Fail-closed: нет манифеста, чанка на диске или ссылок на чанки в HTML; страница не 200 и не редирект; middleware не обратился к заглушке — всё это ошибка с кодом 1. Манифест-набор по отдельности оказался неполным: HTML ссылается на layout соседней группы маршрутов и общие чанки сторов вне набора предков. Поэтому основной источник — HTML.
  - ✅ Resolved review finding [Patch]: подписи карточек `/coming-soon` закреплены дословно. В `ComingSoonClient.test.tsx` — `it.each` «заголовок h3 → соседний `<p>` с точной подписью» и проверка, что карточек ровно три. Мутация «объёма» → «объема» роняет тест.
  - ✅ Resolved review finding [Patch]: HTTP-проверка собранного приложения. Тот же скрипт: `/nonexistent-xyz`, `/catalog/zzz`, `/zzz/yyy` → 404 и ровно `["noindex"]`; `/product|blog|news/zzz-none` → 200 и ровно `["noindex, follow"]`. В тесте инварианта D4 комментарий ссылается на этот шаг.
  - Доказательства (локально, сборка с `NEXT_PUBLIC_API_URL=http://localhost:18001/api/v1`, плюс `.env.local` как в CI с `NODE_ENV=test`): гейт зелёный, проверено 75 чанков. Мутации: `Example` в чанке сторов → код 1 с указанием чанка; `robots` возвращён в `not-found.tsx` и пересобрано → код 1, `["noindex","noindex, nofollow"]` на трёх 404; расхождение адреса заглушки со сборкой → код 1 («middleware не запрашивал список CMS-слагов»).
  - Чистые функции гейта покрыты `src/__tests__/check-production-build.test.ts` (8 тестов). `npm test` — 197 файлов, 3440 passed, 16 skipped; `npm run lint`, `npx tsc --noEmit`, `npm run format:check` — зелёные. `detect-changes` — «No changes detected»: продуктовый код не менялся, правки только в тестах, скрипте и CI.
  - Внешние шаги 8.4–8.5 по-прежнему открыты.

- 18.09.2026 dev-story, итог. Ветка `feature/41-21-bundle-example-retail-wording` от `origin/develop` (`0b034416`, содержит `d64d4909`). GitNexus: индекс свежий (`0b03441`); impact — сторы и `NotFound` LOW (0 по графу), `ComingSoonClient` в графе нет, `generateMetadata` поиска — ambiguous, это точка входа Next без вызывающих в коде; HIGH/CRITICAL среди изменяемых нет, `buildMetadata` не тронут.
- **A (AC1, AC2).** `stores/devtoolsInDev.ts` — дословно по 1.1; четыре стора переведены на обёртку, имена `…Store` и `persist` корзины не тронуты. `.devtools` в `src` не используется (1.3 — пусто). Tree-shaking сработал: запасной alias в `next.config.ts` не понадобился. Рецепт 1.6 на `next start` (16 публичных страниц, `grep -qi`) — пусто. Иных источников `example` нет (1.7). Тесты сторов — без изменения ожиданий.
- **C (AC3–AC6).** Тексты внесены дословно по таблицам (длины 55 / 140 сверены `len()`); `keywords` у `/home` и `/electric` удалены; `/electric` — `buildMetadata` с текстами D7, `DEFAULT_OG_IMAGE*` из импорта убраны, JSDoc → «OPTISPORT». Prettier перенёс три подписи карточки на отдельные строки внутри `<p>` — рендер тот же. В `home/__tests__/page.test.tsx` добавлен `it` на canonical `/home` (AC3 требует, а проверки не было). В тесте поиска ожиданий description не было — добавлен `it` на точное значение и отсутствие «лучш». Страж AC6 проверен на откате пяти исходников к базе: падают все пять регрессов, `/` проходит (исправлен в 41.19).
- **D (AC7).** `robots` из `not-found.tsx` удалён, комментарий по 7.1; тест инварианта D4 — по 7.2, остальные блоки не тронуты. Production-сборка: `/nonexistent-xyz`, `/catalog/zzz`, `/zzz/yyy` → 404 и ровно один `<meta name="robots" content="noindex"/>`; `/product|blog|news/zzz-none` → 200 и один `noindex, follow`.
- Локальная приёмка метаданных (`curl -A "AuditikBot/1.0"`, `next start`): `/coming-soon`, `/home`, `/electric`, `/search?q=мяч` совпадают с таблицами, у `/electric` canonical и `og:url` — `/electric`; в HTML `/coming-soon` есть все четыре новых текста карточки и нет `B2C`, `B2B`, «Лучшие цены», «Розничные».
- Проверки 8.1: `npm test` — 196 файлов, 3428 passed, 16 skipped; `npm run lint`, `npx tsc --noEmit`, `npm run format:check` — зелёные. `detect-changes`: 16 файлов, 11 символов — четыре стора, `NotFound` + `metadata`, `ComingSoon`, `generateMetadata` поиска, `metadata` трёх страниц; `buildMetadata` не изменён; риск medium — за счёт потоков `generateMetadata → normalizePath/withDefaultImageMeta`.
- `deferred-work.md`: записан пробел `/privacy-policy` (soft-404 без `noindex`), как требует «Не делать».
- **Не выполнено:** 8.4 и 8.5 — внешние шаги после мёрджа (PR `develop` → `main`, ручной выкат по SSH, `restart nginx`, приёмка AC8 на `optisport.ru` со снимком в стори, затем закрытие 41.20 и запись E21 реестра 41.16). AC8 до выката не проверяется.

- 18.09.2026: create-story — анализ проверки закрытия отчёта 16.09 и intent-хвостов; код на `372b3efb`; прод снят `curl` (метаданные, 404/soft-404, чанки); локальная production-сборка просканирована на `example`: найдено три чанка, источники установлены (zustand devtools, jsPDF/rgbcolor); механизм `noindex` Next на 404 сверен по `node_modules`; GitNexus impact и cypher по импортёрам сторов. Ultimate context engine analysis completed - comprehensive developer guide created. Код не менялся.

### File List

- `frontend/src/stores/devtoolsInDev.ts` (новый)
- `frontend/src/stores/__tests__/devtoolsInDev.test.ts` (новый)
- `frontend/src/stores/authStore.ts`
- `frontend/src/stores/cartStore.ts`
- `frontend/src/stores/favoritesStore.ts`
- `frontend/src/stores/orderStore.ts`
- `frontend/src/app/(blue)/home/page.tsx`
- `frontend/src/app/(blue)/home/__tests__/page.test.tsx`
- `frontend/src/app/(coming-soon)/coming-soon/page.tsx`
- `frontend/src/app/(coming-soon)/coming-soon/__tests__/page.test.tsx`
- `frontend/src/app/ComingSoonClient.tsx`
- `frontend/src/app/__tests__/ComingSoonClient.test.tsx`
- `frontend/src/app/(electric)/electric/page.tsx`
- `frontend/src/app/(electric)/electric/__tests__/metadata.test.ts` (новый)
- `frontend/src/app/(blue)/search/page.tsx`
- `frontend/src/app/(blue)/search/__tests__/page.test.tsx`
- `frontend/src/app/__tests__/public-copy-no-retail-superlatives.test.ts` (новый)
- `frontend/src/app/not-found.tsx`
- `frontend/src/app/__tests__/robots-noindex-invariant.test.ts`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `frontend/scripts/check-production-build.mjs` (новый, code review)
- `frontend/src/__tests__/check-production-build.test.ts` (новый, code review)
- `frontend/package.json` (скрипт `check:build`, code review)
- `.github/workflows/frontend-ci.yml` (шаг проверки production-сборки, code review)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/41-21-bundle-example-retail-wording-single-404-robots.md`

### Change Log

- 18.09.2026 — create-story: стори заведена по решениям Alex 18.09.2026 (A, C, D; R1 — убрать розницу; R2 — `/electric` только метаданные). Статус: ready-for-dev.
- 18.09.2026 — ответы владельца на Q1 и Q2 внесены: охват нуля `example` — чанки публичных страниц; третья карточка `/coming-soon` — «Скидки от объема закупок».
- 18.09.2026 — dev-story: `devtools` только вне production (в чанках публичных страниц 0 `example`), тексты `/home`, `/coming-soon`, `/electric`, `/search` без розницы и превосходных степеней, страж AC6, один тег robots на 404; запись в `deferred-work.md`. Статус → review. Открыты только внешние шаги 8.4–8.5 (AC8 на проде, закрытие 41.20).
- 18.09.2026 — Addressed code review findings - 3 items resolved: CI-гейт production-сборки (`check-production-build.mjs`: чанки публичных страниц и robots на 404/soft-404), точные подписи карточек `/coming-soon`. Статус → review.
