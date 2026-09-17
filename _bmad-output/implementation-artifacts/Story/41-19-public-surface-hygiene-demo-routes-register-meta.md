---
baseline_commit: e7a19053
---

# Story 41.19: Гигиена публичной поверхности — демо-страницы, метаданные регистрации, корневые умолчания

Status: review
Baseline Revision: e7a19053

## Story

As a оператор сайта,
I want чтобы на проде были только рабочие страницы с осмысленными русскоязычными метаданными,
so that внутренние макеты не утекали, а сканер и поисковик не находили дубли и латиницу по первой же ссылке.

**Закрывает:** FR-41-35; `tech-debt.md` п. 29. **Решения владельца:** D6, D7, D8 (Alex, 17.09.2026, `sprint-change-proposal-2026-09-16.md` §4, редакция ревью).

## Утверждённые решения (дословно, не пересматривать)

- **D6 — удалить из репозитория:** `/examples` и 17 файлов `public/examples`, `/test`, `/design-comparison`, `/electric-orange-test`, статический макет `/electric-orange` (`public/electric-orange/index.html`, `index1.html`, `design.json`, `design_v2.3.0.json` и rewrite в `next.config.ts`). **Каталог `public/electric-orange/img/` не удалять** — его использует тема `/electric` (`ElectricCategorySection.tsx:26-44`). Макеты в `public/` отдаются статикой в обход любых проверок маршрута.
- **D7 — корневые умолчания `app/layout.tsx`:** title «OPTISPORT — спортивные товары оптом»; description «Оптовые продажи спортивных товаров: каталог, условия для оптовых покупателей, доставка по России.» Поле `keywords` корневого умолчания удаляется: поисковики meta keywords не используют.
- **D8 — `expireTime: 86400`** в `next.config.ts`, в той же стори, раз frontend всё равно пересобирается. Все сегменты сейчас `revalidate = 3600`, SWR станет 82800.
- **D4 (контекст, решение 41.18):** адреса, закрытые `Disallow`, meta `noindex` не несут. Поэтому у `/register` и `/b2b-register` robots **не ставится**.

### Тексты метаданных регистрации (утверждены Alex 17.09.2026)

Эпик требовал «собственные русскоязычные title и description», но самих текстов не содержал. Тексты ниже предложены create-story и утверждены владельцем 17.09.2026 без правок — вносить дословно. Стиль повторяет `/login` (`Вход в личный кабинет | OPTISPORT`). Латиницы, кроме названия бренда, нет. «B2B» и превосходных степеней тоже нет. Роли взяты из форм: `RegisterForm.tsx:58-60` — тренер или клуб, оптовик, федерация; `B2BRegisterForm.tsx:345-422` — контактное лицо, реквизиты, ОГРН.

| Адрес | title | description | Длина description |
|---|---|---|---|
| `/register` | Регистрация \| OPTISPORT | Заявка на аккаунт OPTISPORT для оптовых покупателей, тренеров, спортивных клубов и федераций. Доступ к ценам откроется после проверки заявки. | 141 |
| `/b2b-register` | Регистрация компании \| OPTISPORT | Заявка на оптовый аккаунт OPTISPORT для организаций и ИП: контактное лицо и реквизиты компании. Оптовые цены откроются после проверки заявки. | 141 |

Длина корневого title — 35 символов, корневого description — 97.

## Acceptance Criteria

### AC1 — демо-адреса отдают настоящий 404

**Given** продакшен-сборка
**When** запрашиваются `/examples`, любой файл бывшего `public/examples/`, `/test`, `/design-comparison`, `/electric-orange-test`, `/electric-orange`, `/electric-orange/index.html`, `/electric-orange/index1.html`, `/electric-orange/design.json`, `/electric-orange/design_v2.3.0.json`
**Then** ответ — настоящий 404 (механизм стори 41.0)
**And** `public/electric-orange/img/` сохранён, изображения секции категорий на `/electric` отдаются 200

### AC2 — ссылок на удалённые маршруты не осталось

**Given** удалённые маршруты
**When** проверяются ссылки на них
**Then** они убраны из `KNOWN_TOP_LEVEL_ROUTES`, теста `app-routes-allowlist`, `LayoutWrapper.tsx`, rewrite в `next.config.ts` и `robots.ts` (`/electric` в `robots.ts` остаётся); `grep` по `frontend/src` и `next.config.ts` их не находит; тест `app-routes-allowlist` проходит

### AC3 — собственные метаданные регистрации

**Given** страницы `/register` и `/b2b-register`
**When** запрашивается серверный HTML
**Then** у каждой собственные русскоязычные title и description и canonical
**And** meta robots нет — адреса закрыты `Disallow` (D4)

### AC4 — корневые умолчания

**Given** корневые умолчания `app/layout.tsx` (title, description, Open Graph, Twitter)
**When** выполняется тест метаданных
**Then** title — «OPTISPORT — спортивные товары оптом», description — «Оптовые продажи спортивных товаров: каталог, условия для оптовых покупателей, доставка по России.»
**And** поля `keywords` в корневом умолчании нет; текстов «Platform», «B2B», «B2C», «Ведущая» в корневых метаданных нет

### AC5 — `expireTime` (D8)

**Given** HTML-ответ ISR-страницы (D8)
**When** проверяется `Cache-Control`
**Then** `stale-while-revalidate` не превышает `expireTime − revalidate` при `expireTime = 86400`; тест `next-config` закрепляет значение; `tech-debt.md` п. 29 закрыт

### AC6 — приёмка на проде (NFR-41-08)

**Given** выкат на прод (NFR-41-08)
**When** `curl` без cookie снимает перечисленные адреса и `/electric`
**Then** коды и метаданные совпадают с AC выше; снимок приложен к стори

## Tasks / Subtasks

- [x] **Task 0 — preflight** (все AC)
  - [x] 0.1 Ветка `feature/41-19-public-surface-hygiene` от актуального `develop`. Прямые коммиты в `develop` запрещены.
  - [x] 0.2 `npx gitnexus status`. При `stale` проверить `git diff --stat <indexed> HEAD`: если разница только в merge-коммитах без изменений кода, индекс годен; иначе попросить пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [x] 0.3 `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` для `KNOWN_TOP_LEVEL_ROUTES`, `middleware`, `LayoutWrapper`, `robots`, `RootLayout`, `RegisterPage`, `B2BRegisterPage`. Сообщить пользователю blast radius. Снимок create-story — в Dev Notes, раздел «GitNexus».
  - [x] 0.4 Зафиксировать исходный прогон (в `frontend/`): `npx vitest run src/__tests__/app-routes-allowlist.test.ts src/__tests__/middleware.test.ts src/__tests__/next-config-headers.test.ts "src/app/(blue)/(auth)/login" "src/app/(coming-soon)"` — до правок всё зелёное.

- [x] **Task 1 — удалить демо-маршруты и макеты** (AC1)
  - [x] 1.1 `git rm -r`: `frontend/src/app/examples/` (`page.tsx`, `PaginationWrapper.tsx`), `frontend/src/app/design-comparison/`, `frontend/src/app/electric-orange-test/` (`layout.tsx`, `page.tsx`), `frontend/src/app/(blue)/test/`, `frontend/public/examples/` (17 файлов: `1.html`…`16-limit.html`, `17-.txt`).
  - [x] 1.2 `git rm` четырёх файлов макета: `frontend/public/electric-orange/index.html`, `index1.html`, `design.json`, `design_v2.3.0.json`. **`frontend/public/electric-orange/img/` не трогать** — после правки в `public/electric-orange/` остаётся только `img/` (7 файлов).
  - [x] 1.3 Компоненты, которые импортировала только `electric-orange-test`, **не удалять** (`ElectricTabs`, `ElectricHeroBanner`, `ElectricModal`, `ElectricToast`, `ElectricAccordion`, `ElectricTooltip`, `ElectricTable`, `ElectricFeaturesBlock`, `ElectricCartWidget`, `ElectricSearchResults` и др.). Это UI-библиотека темы (своих тестов у этих компонентов нет, держатся реэкспортом в `index.ts`). Её чистка расширяет blast radius и в D6 не входит; вынесена в `deferred-work.md` (решение Alex 17.09.2026). `Pagination` тоже остаётся: `PaginationWrapper` удаляется, а сам компонент используется в других местах.
  - [x] 1.4 `globals-electric-orange.css` не удалять: его импортирует `(electric)/layout.tsx:1`.

- [x] **Task 2 — убрать ссылки на удалённые маршруты** (AC2)
  - [x] 2.1 `frontend/next.config.ts:85-89` — удалить третий элемент `rewrites()` (`/electric-orange` → `/electric-orange/index.html`). Rewrites `/api/:path*` и `/media/:path*` не трогать.
  - [x] 2.2 `frontend/src/middleware.ts`:
    - из `KNOWN_TOP_LEVEL_ROUTES` (`:30-56`) убрать `design-comparison`, `electric-orange`, `electric-orange-test`, `examples`, `test`;
    - из JSDoc (`:15-29`) убрать абзац про `electric-orange` (`:22-25`). Абзац про `/product`, `/orders`, `/b2b-dashboard` сохранить;
    - **больше ничего в файле не менять.** Ветки редиректа гостя и авторизованного (`:400-426`) переписывает 41.18, которая ребейзится на эту стори. Лишний дифф в этих участках даст ей конфликт.
  - [x] 2.3 `frontend/src/components/layout/LayoutWrapper.tsx:18,21` — удалить `isElectricTestPage` и упростить условие до `if (isHomePage)`. Остальное поведение (`/`, `/electric*`, обычная тема) не меняется.
  - [x] 2.4 `frontend/src/app/robots.ts` — из `disallow` убрать `'/electric-orange-test'`, `'/design-comparison'`, `'/examples'`, `'/test'`. `'/electric'` оставить; комментарий над ним переписать под одну витрину альтернативной темы. **Форму объекта не менять** (одно правило `userAgent: '*'`, массив `disallow`): тест инварианта D4 в 41.18 читает этот список. Префикс `/electric` по-прежнему закрывает и `/electric-orange/img/*` — это ожидаемо.
  - [x] 2.5 `frontend/src/app/globals-electric-orange.css:565, 1096` — в двух комментариях, ссылающихся на удалённый макет, убрать упоминание адреса. Пример: `/* Product Card — по макету дизайн-системы Electric Orange (удалён в 41.19, см. git history) */`. Стили не трогать.
  - [x] 2.6 **Не менять:** имя темы `'electric-orange'` в `config/theme.ts` и комментарий `UnifiedButton.tsx:43` (это название темы, а не маршрут), пути `/electric-orange/img/...` в `ElectricCategorySection.tsx`, имя файла `globals-electric-orange.css`.
  - [x] 2.7 Проверка AC2 (из корня репозитория; каждая команда должна вернуть пусто):
    ```bash
    grep -rnE "electric-orange-test|design-comparison|/examples\b|electric-orange/(index|design)|['\"]/electric-orange['\"]|reference /electric-orange" frontend/src frontend/next.config.ts
    grep -nE "'(test|examples|electric-orange)'" frontend/src/middleware.ts frontend/src/app/robots.ts
    grep -n "'/test'" frontend/src/app/robots.ts
    ```
    Совпадения по `'test'` в других тестах (`slug: 'test'`, `cta_link: '/test'`, `NODE_ENV`) к маршруту отношения не имеют, поэтому общий grep по `test` не делать.
  - [x] 2.8 `docs/.wds-project-outline.yaml:108,193,220` ссылается на `design_v2.3.0.json`. Не править: это исторический outline дизайн-воркшопа. В Completion Notes указать, что файл доступен в истории git на `e7a19053`. Архив `docs/frontend/arhiv/**` тоже не трогать.

- [x] **Task 3 — метаданные `/register` и `/b2b-register`** (AC3)
  - [x] 3.1 NEW `frontend/src/app/(blue)/(auth)/register/layout.tsx` по образцу `login/layout.tsx`. Страница регистрации — Client Component (`'use client'`), экспортировать из неё `metadata` нельзя. Содержимое: `export const metadata: Metadata = buildMetadata({ title, description, path: '/register' })` с утверждёнными текстами из таблицы (дословно), **без `noIndex`**; `export default function RegisterLayout({ children }) { return children; }` без обёртки (на это рассчитывает `LayoutWrapper`). Комментарий на русском: почему layout и почему нет robots (D4, адрес закрыт `Disallow`).
  - [x] 3.2 NEW `frontend/src/app/(blue)/(auth)/b2b-register/layout.tsx` — то же с `path: '/b2b-register'`.
  - [x] 3.3 `buildMetadata` и `utils/seo.ts` **не трогать**: 17 прямых вызывающих, HIGH по 41.17. Только вызывать. `keywords` не передавать: после Task 4 корневых `keywords` нет, наследовать нечего.
  - [x] 3.4 `page.tsx` обеих страниц не менять.

- [x] **Task 4 — корневые умолчания** (AC4)
  - [x] 4.1 `frontend/src/app/layout.tsx:22-24` — `title` и `description` дословно по D7.
  - [x] 4.2 Удалить строку `keywords` (`:29`). `metadataBase`, `openGraph` (siteName, locale, type, images), `twitter`, `revalidate = 3600`, импорты шрифтов и `RootLayout` не менять.
  - [x] 4.3 Изменение затрагивает все страницы без собственных метаданных: они наследуют корневые title и description, а без своего `openGraph` — ещё og и twitter. Замер прода 17.09 (раздел «Кто наследует корневые умолчания») показывает, что title в `<title>` из списка страниц наследовали только `/register` и `/b2b-register`, но корневые og и twitter могут приходить на другие страницы. Это ожидаемо и входит в D7.

- [x] **Task 5 — `expireTime`** (AC5)
  - [x] 5.1 `frontend/next.config.ts` — добавить на верхнем уровне `expireTime: 86400` с комментарием на русском: SWR = `expireTime − revalidate`; умолчание Next 15.5.18 — год (`config-shared.js:88`); значение задаёт только заголовок `Cache-Control` для общих кэшей (`base-server.js:1042`, `build/templates/app-page.js:672`, `server/lib/cache-control.js`), на ISR-кэш самого Next не влияет; D8, `tech-debt.md` п. 29.
  - [x] 5.2 Комментарий над `headers()` (`:113-115`: «Cache-Control здесь НЕ задаётся…») дополнить одной фразой: срок SWR задаёт `expireTime` выше. Комментарий `revalidate` в `app/layout.tsx:48-64` при желании дополнить ссылкой на `expireTime`, логику не менять.
  - [x] 5.3 `_bmad-output/planning-artifacts/tech-debt.md` п. 29 — пометить закрытым: дата, стори 41.19, значение 86400, фактический заголовок `s-maxage=3600, stale-while-revalidate=82800`. **Числа — только измеренные.** Локальный замер из Task 7.3 — в этом же коммите; прод-замер добавляется в стори на шаге AC6, не в `tech-debt.md` заранее.

- [x] **Task 6 — тесты** (AC1–AC5)
  - [x] 6.1 `frontend/src/__tests__/app-routes-allowlist.test.ts`:
    - шапку JSDoc (`:9-10`) переписать: обратное включение теперь проверяется;
    - тест `:85-89` «содержит electric-orange» заменить на `it.each(['design-comparison','electric-orange','electric-orange-test','examples','test'])` «не содержит удалённого демо-маршрута %s»;
    - **добавить обратную сверку:** каждый элемент `KNOWN_TOP_LEVEL_ROUTES` — реальная страница из `collectTopLevelRoutes(APP_DIR)`. После удаления `electric-orange` список совпадает с деревом ровно: 20 маршрутов (проверено на `e7a19053`, раздел «Состав `KNOWN_TOP_LEVEL_ROUTES` после правки»). Это страж от повторного «висячего» элемента. Если обратная сверка упадёт на каком-то маршруте — остановиться и выяснить причину, а не ослаблять тест.
  - [x] 6.2 `frontend/src/__tests__/middleware.test.ts`:
    - `:230` — из `it.each` известных маршрутов убрать `'/electric-orange'`, поставить `'/electric'`;
    - добавить `it.each(['/examples','/test','/design-comparison','/electric-orange-test','/electric-orange'])` «отдаёт 404 на удалённый демо-маршрут %s». Мок слагов `['oferta']` из `beforeEach`; ожидание — `NextResponse.rewrite` на `/_not-found` со `{ status: 404 }`, как в тесте `:200-210`.
  - [x] 6.3 NEW `frontend/src/__tests__/public-demo-assets.test.ts` — страж статики. `public/` обходит middleware (matcher исключает пути с точкой), поэтому 404 для `/examples/1.html` и файлов макета доказывается только отсутствием файлов:
    - `public/examples` не существует;
    - в `public/electric-orange` ровно один элемент — каталог `img`;
    - все пути `/electric-orange/img/...` из `ElectricCategorySection.tsx` существуют на диске (прочитать файл и выбрать пути регэкспом, чтобы тест не дублировал список);
    - `nextConfig.rewrites()` не содержит `source`, начинающегося с `/electric-orange`. Учесть, что `rewrites` может вернуть массив или объект `{ beforeFiles, afterFiles, fallback }`: сейчас это массив.
  - [x] 6.4 NEW `frontend/src/app/__tests__/robots.test.ts`: `disallow` не содержит четырёх удалённых путей; содержит `/electric`, `/register`, `/b2b-register`. Остальной список — снимком `toEqual`, чтобы 41.18 видела осознанное изменение.
  - [x] 6.5 NEW `frontend/src/app/(blue)/(auth)/register/__tests__/layout.test.tsx` и `.../b2b-register/__tests__/layout.test.tsx` по образцу `login/__tests__/layout.test.tsx` (мок `next/font/google` для импорта корневого layout):
    - title и description дословно из таблицы;
    - отличаются от корневых **и друг от друга**;
    - `alternates.canonical`, `openGraph.url` равны своему пути, `openGraph.title === title`;
    - `metadata.robots` — `undefined` (D4);
    - `metadata.keywords` — `undefined`;
    - layout рендерит `children` без обёртки.
  - [x] 6.6 NEW `frontend/src/app/__tests__/layout-metadata.test.ts` (мок `next/font/google`, импорт `metadata` из `@/app/layout`; `.ts`, если без JSX):
    - `title` и `description` дословно по D7;
    - `openGraph.title/description` и `twitter.title/description` совпадают с ними;
    - `'keywords' in metadata === false`;
    - `JSON.stringify(metadata)` не матчит `/Platform|B2B|B2C|Ведущая/`. Регистр важен: `DEFAULT_OG_IMAGE_META.alt` содержит кириллическое «платформа» (`utils/seo.ts:46`) — это не нарушение AC4, и `alt` в объём стори не входит (`seo.ts` — HIGH).
  - [x] 6.7 NEW `frontend/src/__tests__/next-config-cache.test.ts` (отдельно от `next-config-headers.test.ts`: у того другой предмет):
    - `nextConfig.expireTime === 86400`;
    - сканирование `src/app/**/*.{ts,tsx}` (кроме `__tests__`) на `export const revalidate = <число>`: каждое значение `> 0` и `< 86400`. Иначе Next не выдаст SWR (`revalidate < expire` в `cache-control.js`);
    - `getCacheControlHeader({ revalidate: 3600, expire: 86400 })` из `next/dist/server/lib/cache-control` равен `'s-maxage=3600, stale-while-revalidate=82800'`. Если импорт внутреннего модуля не резолвится в Vitest, заменить проверку на арифметику `86400 - 3600 === 82800` и указать это в Completion Notes.
  - [x] 6.8 Существующие тесты `login/__tests__/layout.test.tsx:36-40` и `coming-soon/__tests__/page.test.tsx:37-38` (сравнение с `rootMetadata`) проходят без изменений.

- [ ] **Task 7 — проверки и приёмка**
  - [x] 7.1 Frontend (в `frontend/`): `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check`. Backend и OpenAPI не меняются, NFR-41-02 не затронут.
  - [x] 7.2 Локально в dev-контейнере (`docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend`: изменён `next.config.ts`, restart не хватит; затем `restart nginx`, иначе 502) выполнить `curl -s -o /dev/null -w '%{http_code}'` по всем адресам AC1 на `http://localhost:3000` → 404; `/electric` и `/electric-orange/img/bags.jpg` → 200; `curl -s http://localhost:3000/register` и `/b2b-register` → `<title>`, `meta description`, `link rel=canonical`, **нет** `meta name="robots"` и `meta name="keywords"`. Для метаданных в `<head>` использовать `-A "AuditikBot/1.0"` (`htmlLimitedBots`, 41.13).
  - [x] 7.3 `Cache-Control` в dev не проверяется: dev-режим отдаёт `no-store`. Проверять на production-сборке по прецеденту 41.5 (`next build` + `next start -p 3100` при живом backend) либо в прод-подобном контейнере: `curl -sI http://localhost:3100/about` → `s-maxage=3600, stale-while-revalidate=82800`; для `/coming-soon` — то же. Результат записать в Debug Log.
  - [x] 7.4 NFR-41-08: приватное окно браузера, без cookie — `/electric` с картинками секции категорий, `/register`, `/b2b-register` отображаются; `/examples`, `/electric-orange` → страница «Страница не найдена».
  - [x] 7.5 `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только ожидаемые символы: `KNOWN_TOP_LEVEL_ROUTES`, `LayoutWrapper`, `robots`, корневой `metadata`, новые layouts, удалённые демо-страницы. `middleware` может появиться из-за сдвига строк — его код не меняется.
  - [x] 7.6 Dev Agent Record, File List; `sprint-status.yaml` → `review`.
  - [ ] 7.7 **Внешний шаг (после мёрджа и ручного выката по SSH):** полный rebuild frontend (`up -d --build frontend`, затем `restart nginx`); AC6 — `curl` без cookie по всем адресам AC1, `/electric`, `/electric-orange/img/bags.jpg`, `/register`, `/b2b-register`, `curl -I /about`; снимок положить в стори (формат — раздел «Снимок прода до правки»). Повторный прогон сканера — шаг владельца после 41.17–41.20.

## Dev Notes

### Текущее состояние (код `e7a19053`)

- **`frontend/src/middleware.ts`** (стори 41.0). `KNOWN_TOP_LEVEL_ROUTES` — allowlist односегментных маршрутов. Односегментный путь не из списка проверяется по списку опубликованных CMS-слагов `/api/v1/pages/`; если слага нет — `rewrite('/_not-found', { status: 404 })` (`:437-458`). Если список недоступен, срабатывает fail-open. Matcher (`:483`) исключает пути с точкой, поэтому `public/*` middleware не видит.
  - **После правки:** `/examples`, `/test`, `/design-comparison`, `/electric-orange-test`, `/electric-orange` — односегментные пути вне списка. Middleware отдаёт на них 404, пока нет CMS-страницы с таким слагом. Прод-слаги 17.09: `oferta`, `privacy-policy`, `requisites` (3 шт.). Многосегментные `/examples/1.html`, `/electric-orange/design.json` в middleware не попадают: без файла в `public/` и без маршрута Next отдаёт свой 404.
  - **Fail-open (осознанный риск 41.0):** если backend недоступен, `/test` и `/examples` уйдут в catch-all `(blue)/[slug]`, а тот ответит soft-404 с `noindex`. Это уже принятое поведение, не дефект стори.
  - **Сохранить:** весь остальной файл без изменений (см. Task 2.2).
- **`frontend/next.config.ts`** — rewrite `/electric-orange` → `/electric-orange/index.html` (`:85-89`). В комментарии middleware сказано, что rewrites (afterFiles) идут после middleware, поэтому `electric-orange` держался в allowlist. После удаления rewrite запись становится лишней. `expireTime` не задан → умолчание 31536000.
- **`frontend/src/app/robots.ts`** — одно правило `*`, `disallow` из 17 путей, в том числе 4 удаляемых демо-пути; после правки — 13.
- **`frontend/src/components/layout/LayoutWrapper.tsx`** — рендерится в `(blue)/layout.tsx`. Ветка `isElectricTestPage` мертва: `/electric-orange-test` лежит вне группы `(blue)`.
- **`frontend/src/app/layout.tsx`** — корневые `title`/`description` с «Platform», «B2B/B2C», «Ведущая»; `keywords` с `B2B, B2C`; og и twitter повторяют title и description. `revalidate = 3600` (41.5).
- **`/register`, `/b2b-register`** — `page.tsx` с `'use client'`, собственного layout нет. На проде отдают корневые title, description и keywords; canonical нет.
- **`(blue)/test/page.tsx`** — `redirect('/catalog')`. На проде 17.09 отвечает 200.

### Состав `KNOWN_TOP_LEVEL_ROUTES` после правки

`about, b2b-register, blog, cart, catalog, checkout, coming-soon, delivery, electric, home, login, news, partners, password-reset, privacy-policy, profile, register, requisites, search, unsubscribe` — 20 маршрутов. У каждого есть `page.tsx` в дереве `src/app` (проверено на `e7a19053`), поэтому обратная сверка в Task 6.1 выполнима.

### Кто наследует корневые умолчания (прод 17.09, `<title>`)

Собственный title есть у `/`, `/home`, `/catalog`, `/about`, `/delivery`, `/partners`, `/blog`, `/news`, `/cart`, `/checkout`, `/search`, `/login`, `/password-reset`, `/coming-soon`, `/electric`, `/unsubscribe`, `/requisites`, CMS-страниц и 404. Корневой title отдавали `/register` и `/b2b-register`. Вложенные страницы без собственного title (например `password-reset/confirm/...`, `portal-link/confirm/...`) после D7 получат новый корневой — это желаемо.

### Снимок прода до правки (17.09.2026, `curl` без cookie)

| Адрес | Код |
|---|---|
| `/examples`, `/examples/1.html`, `/examples/17-.txt` | 200 |
| `/test`, `/design-comparison`, `/electric-orange-test` | 200 |
| `/electric-orange`, `/electric-orange/index.html`, `/electric-orange/index1.html`, `/electric-orange/design.json`, `/electric-orange/design_v2.3.0.json` | 200 |
| `/electric-orange/img/bags.jpg`, `/electric`, `/register`, `/b2b-register` | 200 |

`/register`: `<title>OPTISPORT Platform | B2B/B2C спортивные товары</title>`, description «Ведущая платформа…», `keywords` с `B2B, B2C`, canonical и robots нет.
`/about`: `Cache-Control: s-maxage=3600, stale-while-revalidate=31532400`.

Ожидаемо после выката: первые три строки — 404, четвёртая — 200; у `/register` и `/b2b-register` title и description из таблицы, canonical есть, robots и keywords нет; `/about` — `stale-while-revalidate=82800`.

### D8: как `expireTime` доходит до заголовка (Next 15.5.18, проверено по `node_modules`)

- `next/dist/server/lib/cache-control.js` — `s-maxage=${revalidate}, stale-while-revalidate=${expire - revalidate}`, SWR выводится только при `revalidate < expire`.
- `expire` берётся из `nextConfig.expireTime`, если сегмент не задал свой (`base-server.js:1042`, `build/templates/app-page.js:672`).
- Умолчание `expireTime: 31536000` (`config-shared.js:88`); год − 3600 = 31532400 — ровно то, что видно на проде.
- Все `revalidate` в `src/app` равны 3600 (`layout.tsx:65`, `(blue)/home/page.tsx:16`, `(electric)/electric/page.tsx:40`, `sitemap.ts:14`). `force-dynamic` у `app/page.tsx` и `unsubscribe` даёт `no-store` и SWR не касается. Каталог динамический из-за `searchParams`, у него `private, no-cache, no-store`.
- Общего кэша (CDN) перед сайтом нет, поэтому эффект пока «на будущее» — как и сказано в `tech-debt.md` п. 29.

### Технические ограничения

- Только фронтенд и конфигурация. Backend, OpenAPI, nginx не меняются. Проверено: в `docker/` ссылок на демо-маршруты нет.
- `next.config.ts` менять → локально `up -d --build frontend`, на проде — полный rebuild образа. Частичное копирование `.next/` запрещено (`Failed to find Server Action`).
- `buildMetadata`/`utils/seo.ts` — HIGH, только вызывать.
- Не трогать `Header.tsx`, `Footer.tsx`, `(blue)/catalog/**` (41.17), формы подписки и регистрации (41.20), ветки auth в `middleware.ts` и `login/layout.tsx` (41.18).
- Не ставить `noindex` на `/register` и `/b2b-register` (D4) и не добавлять их в `sitemap.ts`.
- Комментарии — на русском (NFR-41-03).

### Архитектура и версии

Next.js 15.5.18, React 19.1, TypeScript 5.8, Vitest 4.x (`npm run test`), Playwright 1.57. Новые зависимости не нужны. Metadata API App Router: `metadata` экспортируется только из серверного модуля, поэтому для клиентских страниц используется layout (приём `login/layout.tsx`, 41.6). Дочерний `metadata` без `keywords` наследует `keywords` родителя. После D7 в корне их нет, поэтому новые layouts `keywords: null` не нужен (в каталоге 41.17 он остаётся и вреда не несёт).

### GitNexus (create-story, индекс `3beb751`, HEAD `e7a19053`, 17.09.2026)

`status` — формально `stale`, но `git diff --stat 3beb751 e7a19053` пуст: между ними только merge-коммит PR #192. Индекс соответствует коду.

| Символ | Risk | Прямых вызывающих | Примечание |
|---|---|---|---|
| `KNOWN_TOP_LEVEL_ROUTES` (`middleware.ts`) | LOW | 0 | читают `middleware` и тест allowlist |
| `middleware` | LOW по графу | 0 | точка входа фреймворка, исполняется на каждом HTML-запросе. Меняется только набор, логика — нет; матрица 404/200 в Task 6.2 и 7.2 |
| `LayoutWrapper` | LOW | 0 | рендерится `(blue)/layout.tsx` на всех страницах blue |
| `robots` | LOW | 0 | в 41.18 его читает тест D4 |
| `RootLayout` (`app/layout.tsx`) | LOW | 0 | `metadata` наследуют все страницы без своих |
| `RegisterPage`, `B2BRegisterPage` | LOW | 0 | не меняются, рядом добавляется layout |
| `TestPage` (`(blue)/test`) | LOW | 0 | удаляется |
| `buildMetadata` (`utils/seo.ts`) | **HIGH** (41.17: 17 прямых) | — | не менять |

### Project Structure Notes

- DELETE `frontend/src/app/examples/**`, `frontend/src/app/design-comparison/**`, `frontend/src/app/electric-orange-test/**`, `frontend/src/app/(blue)/test/**`, `frontend/public/examples/**`, `frontend/public/electric-orange/{index.html,index1.html,design.json,design_v2.3.0.json}`
- UPDATE `frontend/next.config.ts` (rewrite, `expireTime`, комментарий)
- UPDATE `frontend/src/middleware.ts` (только набор и JSDoc)
- UPDATE `frontend/src/components/layout/LayoutWrapper.tsx`
- UPDATE `frontend/src/app/robots.ts`
- UPDATE `frontend/src/app/layout.tsx`
- UPDATE `frontend/src/app/globals-electric-orange.css` (два комментария)
- NEW `frontend/src/app/(blue)/(auth)/register/layout.tsx`, `frontend/src/app/(blue)/(auth)/b2b-register/layout.tsx`
- UPDATE тесты: `src/__tests__/app-routes-allowlist.test.ts`, `src/__tests__/middleware.test.ts`
- NEW тесты: `src/__tests__/public-demo-assets.test.ts`, `src/__tests__/next-config-cache.test.ts`, `src/app/__tests__/robots.test.ts`, `src/app/__tests__/layout-metadata.test.ts`, `src/app/(blue)/(auth)/register/__tests__/layout.test.tsx`, `src/app/(blue)/(auth)/b2b-register/__tests__/layout.test.tsx`
- UPDATE `_bmad-output/planning-artifacts/tech-debt.md` п. 29

**Общие файлы с другими стори (§5.7 предложения):** `middleware.ts` и `robots.ts` потом правит 41.18 — держать дифф минимальным. С 41.17 (`Header.tsx`, каталог) и 41.20 (формы, реестр согласий) пересечений нет. Каталоги `(auth)/register` и `(auth)/b2b-register` 41.20 не трогает: её плейсхолдеры живут в `RegisterForm.tsx` и `B2BRegisterForm.tsx`, а эта стори кладёт рядом со страницами только `layout.tsx`.

### Previous Story Intelligence (41.17, 41.13, 41.6, 41.5, 41.0)

- **41.17** (PR #192 смёржен в `e7a19053`; в трекере пока `review`): метаданные проверять `curl` с `-A "AuditikBot/1.0"`, иначе из-за стриминга метаданных Next 15.2+ они могут прийти в `<body>`. Грабли стенда: после `restart frontend` nginx на :80 отдаёт 502 до `restart nginx`; hot reload в контейнере правок из Windows не видит. Полный прогон после 41.17 — 184 файла, 3260 passed, 16 skipped: ориентир, не требование.
- **41.6:** приём «метаданные клиентской страницы — в соседнем layout» и тест с `rootMetadata` (`login/__tests__/layout.test.tsx`).
- **41.5:** `Cache-Control` HTML задаётся не заголовком в конфиге (Next его перезаписывает), а `revalidate`; проверка — только на production-сборке (`next build` + `next start -p 3100`).
- **41.0:** механизм 404, тест-страж allowlist, `vi.resetModules()` в тестах middleware (кэш слагов в модуле).
- Память проекта: `vi.restoreAllMocks()` не снимает `spyOn` на браузерных API — восстанавливать явно; не гонять тяжёлые прогоны параллельно.

### Git Intelligence

`e7a19053` (develop) — merge PR #192 (41.17): `9d9e8373` (метаданные подборок, фокус поиска), `3beb7516` (e2e-мок `/banners/`). До этого — PR #190 (фильтр «Торговая марка»). Файлов этой стори последние коммиты не касались. Конвенция сообщений: `feat(frontend): …`, `test(frontend): …` на русском.

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.19], FR-41-35
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-16.md#4 (D4, D6–D8), #5.4, #5.7]
- [Source: _bmad-output/implementation-artifacts/tasks/intent-site-audit-2026-09-16.md] — F1, F2, CC-6, CC-8
- [Source: _bmad-output/planning-artifacts/tech-debt.md#29]
- [Source: _bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md] — механизм 404, allowlist
- [Source: _bmad-output/implementation-artifacts/Story/41-5-security-headers-single-source-all-locations.md] — `revalidate`, проверка на prod-сборке
- [Source: _bmad-output/implementation-artifacts/Story/41-17-catalog-collections-meta-descriptions-focus-search.md] — `AuditikBot`, грабли стенда
- [Source: project-context.md#1, #5, #7]
- `frontend/node_modules/next/dist/server/lib/cache-control.js`, `server/config-shared.js:88`, `server/base-server.js:1042`, `build/templates/app-page.js:672` — семантика `expireTime` в 15.5.18

## Решения по вопросам create-story (Alex, 17.09.2026)

1. **Тексты title и description для `/register` и `/b2b-register`** — утверждены в редакции таблицы «Тексты метаданных регистрации».
2. **Осиротевшие компоненты Electric** после удаления `/electric-orange-test` — в стори не удаляются; заведена запись в `deferred-work.md` («Deferred from: create-story 41.19»).

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (claude-opus-5), bmad-dev-story, 17.09.2026

### Debug Log References

- **Preflight.** Локальный `develop` разошёлся с `origin/develop`: 1 неотправленный коммит `2dbb1fe` со skill-доками, на origin 3 новых коммита, в том числе `8b418e53` — закрытие 41.17. Ветка `feature/41-19-public-surface-hygiene` взята от `origin/develop` `64ea2248`; локальный `develop` и `2dbb1fe` не тронуты. Незакоммиченные артефакты create-story перенесены: запись в `deferred-work.md` — как есть, блок 41.19 в `sprint-status.yaml` — поверх версии origin; устаревшая локальная правка стори 41.17 отброшена (на origin более полная). Исходное состояние сохранено в `git stash` «41-19 create-story artifacts». Frontend-код между `e7a19053` и `64ea2248` не менялся.
- **GitNexus.** Индекс `2dbb1fe` — up-to-date. `impact --direction upstream`: `KNOWN_TOP_LEVEL_ROUTES`, `LayoutWrapper`, `robots`, `RootLayout`, `RegisterPage`, `B2BRegisterPage` — LOW, 0 затронутых. `detect-changes --scope all`: risk low, 0 процессов; символы `nextConfig`, `headers` (только комментарий), `description` и `revalidate` корневого layout (у `revalidate` только комментарий), `robots`, `LayoutWrapper`.
- **0.4, исходный прогон:** 6 файлов, 307 passed.
- **Red-фаза:** до реализации Task 3–5 новые тесты дали 6 падений (`next-config-cache` ×2, `layout-metadata` ×4), файлы тестов layouts падали на отсутствующем модуле; тесты Task 1–2 зелёные после удаления.
- **7.1:** `npm test` — 190 файлов, 3303 passed, 16 skipped; `npm run lint` — 0; `npm run format:check` — 0; `npx tsc --noEmit` — 0. До `next build` `tsc` падал на устаревшем `.next/types/validator.ts` со ссылками на удалённые страницы: это локальный артефакт прошлой сборки, в CI `.next` нет.
- **7.2 (dev-стенд, `up -d --build frontend` + `restart nginx`, :3000):** `/examples`, `/examples/1.html`, `/examples/17-.txt`, `/test`, `/design-comparison`, `/electric-orange-test`, `/electric-orange`, `/electric-orange/index.html`, `/electric-orange/index1.html`, `/electric-orange/design.json`, `/electric-orange/design_v2.3.0.json` — 404; `/electric`, `/electric-orange/img/bags.jpg`, `/register`, `/b2b-register` — 200; `/electric` через nginx :80 — 200. С `-A "AuditikBot/1.0"`: `/register` — `<title>Регистрация | OPTISPORT</title>`, description по таблице, `canonical` и `og:url` = `…/register`; `/b2b-register` — `Регистрация компании | OPTISPORT`, description по таблице, canonical `…/b2b-register`; `meta robots` и `meta keywords` во всём HTML — 0 у обеих.
- **7.3 (локальная production-сборка `next build` + `next start -p 3100`, backend :8001):** `/about`, `/coming-soon`, `/home`, `/electric` — `Cache-Control: s-maxage=3600, stale-while-revalidate=82800`. Там же `/examples`, `/test`, `/electric-orange`, `/electric-orange/design.json` — 404, `/electric-orange/img/bags.jpg` — 200; в `robots.txt` 13 `Disallow`, `/electric` на месте.
- **7.4 (NFR-41-08):** вместо приватного окна — чистый контекст headless Chromium (Playwright проекта, 0 cookie) на :3000. `/electric` — 200, все 4 картинки секции категорий загружены (`naturalWidth > 0`); `/register` — 200, h1 «Регистрация»; `/b2b-register` — 200, h1 «Регистрация для бизнеса»; `/examples` и `/electric-orange` — 404, title «Страница не найдена | OPTISPORT», на скриншоте страница 404 темы blue.

### Completion Notes List

- 17.09.2026: create-story — анализ эпика, предложения (D4, D6–D8), триажа 16.09, стори 41.0/41.5/41.6/41.17; код на `e7a19053`; GitNexus impact (всё LOW, `buildMetadata` HIGH не затрагивается); семантика `expireTime` сверена по `node_modules` Next 15.5.18; снимок прода до правки; длины текстов пересчитаны. Ultimate context engine analysis completed - comprehensive developer guide created. Код не менялся.
- 17.09.2026: dev-story — реализованы AC1–AC5, AC6 ждёт выката.
  - **D6:** удалено 27 файлов: страницы `/examples` (с `PaginationWrapper`), `/design-comparison`, `/electric-orange-test` (layout и page), `(blue)/test`, 17 файлов `public/examples`, 4 файла макета `public/electric-orange`. `public/electric-orange/img/` (7 файлов) сохранён. Компоненты Electric, `Pagination` и `globals-electric-orange.css` не удалялись (Task 1.3–1.4, `deferred-work.md`).
  - **Ссылки (AC2):** убраны rewrite `/electric-orange` из `next.config.ts`; 5 записей и абзац JSDoc из `KNOWN_TOP_LEVEL_ROUTES` (ветки auth в `middleware.ts` не тронуты); `isElectricTestPage` из `LayoutWrapper`; 4 демо-пути из `robots.ts` (форма объекта прежняя, комментарий над `/electric` переписан). Все три grep из 2.7 пусты. **Отклонение от 2.5:** в `globals-electric-orange.css` исправлено три комментария, а не два. Третий (`:139`, «Strict from design_v2.3.0.json») тоже ссылался на удалённый файл; стили не менялись. По 2.8: `docs/.wds-project-outline.yaml:108,193,220` ссылается на `design_v2.3.0.json` и не правился — файл доступен в истории git на `e7a19053`; `docs/frontend/arhiv/**` не трогался.
  - **AC3:** `register/layout.tsx` и `b2b-register/layout.tsx` — `buildMetadata` с утверждёнными текстами, без `noIndex` и `keywords`, `children` без обёртки. `page.tsx` и `utils/seo.ts` не менялись.
  - **AC4:** корневые title и description по D7, `keywords` удалён; og и twitter берут те же константы.
  - **AC5:** `expireTime: 86400` в `next.config.ts` с комментарием; комментарии над `headers()` и `revalidate` дополнены ссылкой на `expireTime`. `tech-debt.md` п. 29 закрыт с локальным замером.
  - **Тесты:** allowlist — обратная сверка (список совпадает с деревом `src/app`, 20 маршрутов) и `it.each` на 5 удалённых записей; middleware — `/electric` вместо `/electric-orange` в известных маршрутах, `it.each` на 404 для 5 демо-адресов. Новые: `public-demo-assets` (4), `next-config-cache` (3; импорт `next/dist/server/lib/cache-control` в Vitest резолвится, запасная арифметика не понадобилась), `robots` (8), `layout-metadata` (4), layouts `/register` и `/b2b-register` (по 7). Тесты `login/layout` и `coming-soon/page` со сверкой с `rootMetadata` проходят без изменений.
  - **Открыт только 7.7** — внешний шаг после мёрджа и ручного выката: AC6 на `https://optisport.ru`, снимок в стори.

### File List

**Удалены:**

- `frontend/src/app/examples/page.tsx`
- `frontend/src/app/examples/PaginationWrapper.tsx`
- `frontend/src/app/design-comparison/page.tsx`
- `frontend/src/app/electric-orange-test/layout.tsx`
- `frontend/src/app/electric-orange-test/page.tsx`
- `frontend/src/app/(blue)/test/page.tsx`
- `frontend/public/examples/` — 17 файлов: `1.html` … `16-limit.html`, `17-.txt`
- `frontend/public/electric-orange/index.html`
- `frontend/public/electric-orange/index1.html`
- `frontend/public/electric-orange/design.json`
- `frontend/public/electric-orange/design_v2.3.0.json`

**Изменены:**

- `frontend/next.config.ts`
- `frontend/src/middleware.ts`
- `frontend/src/components/layout/LayoutWrapper.tsx`
- `frontend/src/app/robots.ts`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/globals-electric-orange.css`
- `frontend/src/__tests__/app-routes-allowlist.test.ts`
- `frontend/src/__tests__/middleware.test.ts`
- `_bmad-output/planning-artifacts/tech-debt.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/deferred-work.md` (запись create-story 41.19)

**Новые:**

- `frontend/src/app/(blue)/(auth)/register/layout.tsx`
- `frontend/src/app/(blue)/(auth)/b2b-register/layout.tsx`
- `frontend/src/app/(blue)/(auth)/register/__tests__/layout.test.tsx`
- `frontend/src/app/(blue)/(auth)/b2b-register/__tests__/layout.test.tsx`
- `frontend/src/app/__tests__/layout-metadata.test.ts`
- `frontend/src/app/__tests__/robots.test.ts`
- `frontend/src/__tests__/public-demo-assets.test.ts`
- `frontend/src/__tests__/next-config-cache.test.ts`
- `_bmad-output/implementation-artifacts/Story/41-19-public-surface-hygiene-demo-routes-register-meta.md`

### Change Log

- 17.09.2026 — create-story: стори создана, статус ready-for-dev.
- 17.09.2026 — решения Alex: тексты метаданных регистрации утверждены; чистка осиротевших компонентов Electric вынесена в `deferred-work.md`.
- 17.09.2026 — dev-story: удалены демо-маршруты и макеты (D6), ссылки на них убраны, у `/register` и `/b2b-register` собственные метаданные, корневые умолчания по D7, `expireTime: 86400` (D8), тесты-стражи; `tech-debt.md` п. 29 закрыт; статус → review. Открыт только внешний шаг 7.7 (AC6 на проде).
