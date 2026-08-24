---
baseline_commit: a041e1b0
---

# Story 41.0: Несуществующие адреса отдают настоящий 404

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> 🔴 **Первая стори эпика 41 и предшественник всех SEO-требований.** Гасит пять замечаний аудита одной правкой: из обхода сканера выпадают 14 фантомных адресов, вместе с ними «noindex на 19 страницах», 5 из 9 дублей `title`, ~17 из 19 дублей `description` и «не найдена цена» на `/korzina`, `/basket`, `/order`. Стори 41.6 до неё писать бессмысленно — она меняет исходные данные.
> 🟢 **Blast radius LOW по графу вызовов, HIGH по трафику.** `npx gitnexus impact middleware --direction upstream` → `risk: LOW`, `impactedCount: 0` (middleware вызывает фреймворк, а не код). Но фактически правка стоит на пути **каждого** HTML-запроса сайта: ошибка здесь роняет не одну страницу, а весь фронт. Отсюда жёсткие требования fail-open и кэша (AC7, AC6).
> ⚠️ **Индекс GitNexus устарел** (проиндексирован `606a5de`, HEAD — `a041e1b`). Координаты кода в этой стори проверены **чтением файлов**, не индексом. Перед своим `impact`/`context` выполни `npx gitnexus analyze`.
> ⚠️ **Изменяются `middleware.ts` и `Dockerfile`** → фронт применяется **только полной пересборкой**: `docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend`. `restart frontend` изменения middleware не подхватит.

## Story

As a **поисковый робот и любой внешний сканер**,
I want **получать HTTP 404 на несуществующий адрес**,
so that **несуществующие страницы не попадали в индекс и не учитывались как страницы сайта**.

## Acceptance Criteria

1. **AC1 (FR-41-21).** Запрос к несуществующему адресу **верхнего уровня** (`/offer`, `/terms`, `/korzina`, `/basket`, `/order`, `/product`) отдаёт HTTP-статус **404**, а тело ответа содержит человекочитаемую разметку «Страница не найдена». Реализация — в `frontend/src/middleware.ts`: middleware выполняется до стриминга и статус вернуть может, App Router из `notFound()` — уже нет (`(blue)/[slug]/page.tsx:76-80`, комментарий там объясняет ровно это ограничение).

2. **AC2 (FR-41-21).** Запрос к опубликованной CMS-странице (`/oferta`, любой другой опубликованный slug) отдаёт **200**, метаданные формируются через `buildMetadata` (`[slug]/page.tsx:66-71`), метатег `noindex` отсутствует. `/oferta` — **реальная** опубликованная CMS-запись, ссылка на неё стоит в подвале (`spec-footer-links-oferta.md`); отдать по ней 404 — регрессия, ломающая ссылку в подвале.

3. **AC3 (FR-41-21).** Ни один существующий маршрут Next.js верхнего уровня не начинает отдавать 404. Список известных односегментных маршрутов зафиксирован константой в `middleware.ts` и содержит **ровно** (проверено обходом `frontend/src/app/`; группы маршрутов `(blue)`, `(auth)`, `(coming-soon)`, `(electric)` в URL не входят):
   `about`, `b2b-register`, `blog`, `cart`, `catalog`, `checkout`, `coming-soon`, `delivery`, `design-comparison`, `electric`, `electric-orange`, `electric-orange-test`, `examples`, `home`, `login`, `news`, `partners`, `password-reset`, `privacy-policy`, `profile`, `register`, `requisites`, `search`, `test`.
   ⚠️ `electric-orange` **страницей не является** — это rewrite на статику `public/electric-orange/index.html` (`next.config.ts:81-84`). Rewrites из `next.config.ts` (afterFiles) выполняются **после** middleware, поэтому без записи в списке рабочий адрес превратится в 404. Не удалять «как лишний».
   ⚠️ `/orders` и `/b2b-dashboard` в список **не добавлять**: страниц с такими путями нет, хотя `isProtectedRoute` (`middleware.ts:16-19`) их перечисляет. Поведение для анонима остаётся прежним — редирект на `/login` (AC8); менять его в этой стори не нужно.

4. **AC4 (FR-41-21, защита от дрейфа).** Vitest-тест-страж сверяет константу из AC3 с фактической структурой `frontend/src/app/`: для каждого каталога, дающего односегментный публичный маршрут (`page.tsx` внутри, группы в скобках раскрыты, динамические сегменты `[...]` пропущены), проверяется наличие в списке. Тест падает, когда разработчик добавит новую страницу верхнего уровня и забудет обновить список — иначе новая страница молча начнёт отдавать 404. Обратное включение (каждый элемент списка = каталог в `app/`) **не проверяется**: `electric-orange` живёт в `public/`.

5. **AC5 (FR-41-21).** Middleware вмешивается **только** когда путь состоит ровно из одного сегмента — это в точности зона перехвата catch-all `(blue)/[slug]`. Многосегментные несуществующие пути (`/foo/bar`) Next отдаёт с 404 сам, и трогать их не нужно. Корень `/` (пустой путь) не затрагивается — там `redirect()` по теме (`app/page.tsx:22-31`).

6. **AC6 (FR-41-21).** Список опубликованных слагов кэшируется в памяти модуля. TTL задан **именованной константой с комментарием** (обязательное требование эпика), запрос к API выполняется не чаще одного раза за TTL. При истёкшем TTL отдаётся прежний список, а обновление идёт фоном (stale-while-revalidate), чтобы протухание кэша не добавляло задержку в запрос пользователя. Параллельные промахи кэша схлопываются в один запрос (single-flight): без этого всплеск трафика на холодном кэше даст лавину запросов к бэкенду. Вновь опубликованный в админке slug отдаёт 200 не позднее TTL.

7. **AC7 (FR-41-21, fail-open).** Если список слагов получить не удалось — бэкенд недоступен, таймаут, статус ≥ 400, ответ не разобрался — middleware **не отдаёт 404 вслепую**, а пропускает запрос дальше по прежнему пути (`NextResponse.next()`), и факт пишется в лог (`console.warn` с путём и причиной). Запрос к API ограничен явным таймаутом: без него недоступный бэкенд подвесит каждый HTML-запрос сайта.

8. **AC8 (регрессия).** Существующее поведение middleware сохранено полностью: редирект неавторизованного с `/profile`, `/orders`, `/b2b-dashboard` на `/login` с параметром `next`; редирект авторизованного с `/login`, `/register`, `/password-reset`, `/b2b-register` на `/` или на безопасный `next`/`redirect` через `isSafeRedirectUrl`. Проверка 404 выполняется **после** auth-веток и только на пути, который иначе вернул бы `NextResponse.next()` — сетевой запрос не должен вклиниваться в редиректы. Существующие тесты `frontend/src/__tests__/middleware.test.ts` продолжают проходить.

9. **AC9 (FR-41-21).** `matcher` по-прежнему исключает `_next/static`, `_next/image`, `favicon.ico`, любые пути с точкой (шаблон `.*\..*` покрывает `/robots.txt`, `/sitemap.xml`, `/media/...`, файлы из `public/`) и `api/`. Расширять или сужать `matcher` в этой стори не требуется — он уже исключает всё нужное; изменение matcher'а без необходимости трогает маршрутизацию всего сайта.

10. **AC10 (доставка URL API в edge-бандл).** Middleware обращается к API по **внутреннему** адресу Docker-сети. В `frontend/Dockerfile` добавлен `ARG NEXT_PUBLIC_API_URL_INTERNAL` с дефолтом `http://backend:8000/api/v1` и соответствующий `ENV` **до** `RUN npm run build`; в `docker/docker-compose.prod.yml` он передан в `build.args` сервиса `frontend`. Причина обязательна к пониманию: в edge-бандл middleware переменные подставляются **на этапе сборки**, и попадают туда только `NEXT_PUBLIC_*`. Сейчас `INTERNAL_API_URL` и `NEXT_PUBLIC_API_URL_INTERNAL` заданы в проде только в `environment` (runtime) — в собранном middleware они будут `undefined`, и запрос уйдёт по публичному `https://optisport.ru/api/v1` наружу и обратно через nginx либо не уйдёт вовсе. `Dockerfile.dev` не меняется: dev-контейнер компилирует на лету и читает окружение в runtime.

11. **AC11 (границы стори).** **Не изменяются:** `(blue)/[slug]/page.tsx` (ветка `if (!page)` с `noindex` остаётся страховкой на случай fail-open и гонки «slug в списке, но страница уже снята»), `app/not-found.tsx`, `app/robots.ts`, `app/sitemap.ts`, `utils/seo.ts`, `next.config.ts`, `docker/nginx/**` (заголовки — объём стори 41.5), любой код бэкенда, `docs/api/openapi.yaml`. Новых зависимостей в `package.json` нет. Изменяются ровно: `frontend/src/middleware.ts`, `frontend/src/__tests__/middleware.test.ts`, новый файл теста-стража, `frontend/Dockerfile`, `docker/docker-compose.prod.yml`.

12. **AC12 (NFR-41-01, NFR-41-03).** Покрытие тестами по AC1–AC8; пороги vitest (`functions/lines/branches/statements ≥ 65`, `vitest.config.mts:36-41`) не снижаются. Комментарии и docstrings нового кода — на русском. **E2E-тест на 404 не добавляется** — обоснование в Dev Notes → «Почему не Playwright».

13. **AC13 (проверка на живом контейнере — обязательна).** Статус ответа подтверждён руками после пересборки фронта; вывод команд приложен в Completion Notes. Без этого AC1 недоказуем: юнит-тест проверяет решение middleware, а не фактический HTTP-статус, который отдаёт Next.

## Tasks / Subtasks

- [x] **Task 1: Список известных маршрутов и разбор пути** (AC: 3, 5, 8, 9)
  - [x] 1.1: В `frontend/src/middleware.ts` добавить константу `KNOWN_TOP_LEVEL_ROUTES: ReadonlySet<string>` с 24 значениями из AC3. Комментарием зафиксировать: список сверяется тестом-стражем, `electric-orange` — rewrite на статику, а не страница
  - [x] 1.2: Добавить хелпер `getSingleSegment(pathname: string): string | null` — возвращает единственный сегмент пути либо `null` для корня и многосегментных путей (AC5)
  - [x] 1.3: Сделать `middleware` асинхронной (`export async function middleware`). Auth-ветки оставить **без изменений и первыми**; проверку 404 разместить непосредственно перед финальным `return NextResponse.next()` (AC8)
  - [x] 1.4: `matcher` не трогать (AC9)

- [x] **Task 2: Кэш опубликованных слагов** (AC: 6, 7, 10)
  - [x] 2.1: Константы с русскими комментариями: `SLUG_CACHE_TTL_MS = 5 * 60 * 1000` и `SLUGS_FETCH_TIMEOUT_MS = 2000`. Обоснование TTL — в Dev Notes → «Почему 5 минут»
  - [x] 2.2: Модульное состояние: `slugCache: { slugs: Set<string>; fetchedAt: number } | null` и `inflight: Promise<Set<string> | null> | null` (single-flight)
  - [x] 2.3: `getApiBaseUrl()` — цепочка `NEXT_PUBLIC_API_URL_INTERNAL` → `NEXT_PUBLIC_API_URL` → литерал `http://backend:8000/api/v1`. **Только `NEXT_PUBLIC_*`**: остальные в edge-бандл не попадают (AC10). Не копировать `getApiUrl()` из `[slug]/page.tsx:17-23` — там первым идёт `INTERNAL_API_URL`, который в middleware не работает
  - [x] 2.4: `fetchPublishedSlugs()` — `GET {api}/pages/?page_size=1000` с `AbortSignal.timeout(SLUGS_FETCH_TIMEOUT_MS)`, разбор `data.results[].slug` с проверками `res.ok`, `Array.isArray(data.results)` и `typeof slug === 'string'`. `page_size=1000` обязателен: DRF по умолчанию отдаёт 20 записей (`PAGE_SIZE`, `backend/freesport/settings/base.py:169`), и 21-я CMS-страница молча начала бы отдавать 404. Ошибку не пробрасывать — вернуть `null` и залогировать `console.warn`
  - [x] 2.5: `getPublishedSlugs()` — свежий кэш отдаётся сразу; протухший отдаётся сразу, обновление запускается фоном без `await`; пустого кэша ждём с таймаутом; параллельные промахи используют общий `inflight`-промис (AC6)
  - [x] 2.6: Фоновое обновление обязано глотать собственные ошибки (`.catch()`), иначе unhandled rejection уронит воркер

- [x] **Task 3: Возврат 404** (AC: 1, 2, 7)
  - [x] 3.1: Слаг не в `KNOWN_TOP_LEVEL_ROUTES` → получить список слагов. `null` (fail-open) → `console.warn` + `NextResponse.next()` (AC7). Слаг в списке → `NextResponse.next()` (AC2). Иначе → `NextResponse.rewrite(new URL('/_not-found', request.url), { status: 404 })`
  - [x] 3.2: Комментарием у `rewrite` зафиксировать механику и запасной вариант — оба разобраны в Dev Notes → «Как middleware отдаёт 404»

- [x] **Task 4: Доставка URL API в сборку** (AC: 10)
  - [x] 4.1: `frontend/Dockerfile`: рядом с существующими `ARG NEXT_PUBLIC_API_URL` / `ARG NEXT_PUBLIC_APP_URL` (строки 27-30) добавить `ARG NEXT_PUBLIC_API_URL_INTERNAL=http://backend:8000/api/v1` и `ENV NEXT_PUBLIC_API_URL_INTERNAL=$NEXT_PUBLIC_API_URL_INTERNAL` — обязательно **выше** `RUN npm run build` (строка 39)
  - [x] 4.2: `docker/docker-compose.prod.yml`, сервис `frontend`, блок `build.args` (строки 113-117): добавить `NEXT_PUBLIC_API_URL_INTERNAL: http://backend:8000/api/v1`
  - [x] 4.3: `Dockerfile.dev` и `docker/docker-compose.yml` не трогать — dev читает окружение в runtime, `NEXT_PUBLIC_API_URL_INTERNAL` там уже задан (`docker-compose.yml:115`)

- [x] **Task 5: Тесты middleware** (AC: 1, 2, 3, 5, 6, 7, 8, 12)
  - [x] 5.1: В `frontend/src/__tests__/middleware.test.ts` дополнить мок `next/server`: к `next` и `redirect` добавить `rewrite: vi.fn()` (сейчас его нет — новые тесты упадут на «не функция»)
  - [x] 5.2: Существующие четыре теста перевести на `await middleware(req)` — функция стала асинхронной
  - [x] 5.3: **Сбрасывать модульное состояние между тестами**: `vi.resetModules()` в `beforeEach` и импорт middleware динамически (`const { middleware } = await import('../middleware')`). Иначе кэш слагов протечёт из теста в тест и результат станет зависеть от порядка выполнения
  - [x] 5.4: Мок `global.fetch` (`vi.stubGlobal('fetch', ...)`), ответ вида `{ results: [{ slug: 'oferta' }] }`; в `afterEach` — `vi.unstubAllGlobals()`
  - [x] 5.5: Кейсы: `/offer` → `rewrite` с `/_not-found` и `{ status: 404 }`; `/oferta` → `next()`; `/about` и `/electric-orange` → `next()` **без обращения к fetch**; `/foo/bar` и `/` → `next()` без fetch; fetch reject → `next()` + `console.warn`; `res.ok === false` → `next()`; два запроса подряд → ровно один fetch; после истечения TTL (фейковые таймеры) — повторный fetch; `/profile` без токена → `redirect` на `/login`, fetch не вызывался
  - [x] 5.6: Новый файл `frontend/src/__tests__/app-routes-allowlist.test.ts` — тест-страж (AC4). Обходит `src/app` через `node:fs`, собирает односегментные публичные маршруты (каталоги в скобках раскрывает, `[...]` пропускает, требует наличия `page.tsx`), сверяет со списком. Путь к `src/app` строить от `import.meta.url`, не от `process.cwd()`

- [x] **Task 6: Проверка на живом контейнере** (AC: 12, 13)
  - [x] 6.0: Локальные гейты CI перед пересборкой: `npm run lint`, `npm run format:check` (или `npx prettier --check`), `npm run test` — `frontend-ci.yml` гоняет ESLint и Prettier до тестов, и падение форматирования блокирует PR
  - [x] 6.1: `docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend` (выполнено; backend пересоздался вместе с фронтом → дополнительно `restart nginx`)
  - [x] 6.2: Прогнать проверочный набор из Dev Notes → «Ручная проверка», вывод приложить в Completion Notes
  - [x] 6.3: Убедиться, что `/oferta` отдаёт 200 с текстом оферты, а ссылка в подвале рабочая

## Dev Notes

### Как middleware отдаёт 404

Основной вариант — `NextResponse.rewrite(new URL('/_not-found', request.url), { status: 404 })`. Механика подтверждена по исходникам установленного Next **15.5.18** (`frontend/package.json:36`):

- `node_modules/next/dist/server/lib/router-utils/resolve-routes.js:344` — `res.statusCode = middlewareRes.status;`: статус, заданный в middleware, переносится на ответ до дальнейшей маршрутизации;
- `node_modules/next/dist/server/base-server.js:1166-1170` — путь `/_not-found` (константа `UNDERSCORE_NOT_FOUND_ROUTE`, `shared/lib/constants.js:326`) нормализуется в `/404`, и `is404Page` замыкает рендер на 404-ветку;
- `base-server.js:1646-1660` — при `res.statusCode === 404` App Router рендерит свой not-found entry, то есть `frontend/src/app/not-found.tsx`.

Статический сегмент `_not-found` побеждает динамический `[slug]` в приоритете маршрутизации, поэтому rewrite **не** уходит обратно в catch-all.

**Запасной вариант, если ручная проверка (AC13) покажет 200:** rewrite на заведомо несуществующий **двухсегментный** путь, например `new URL('/__404__/not-found', request.url)`. Маршрута нет → Next отдаёт 404 естественным путём. Двухсегментный обязателен: односегментный перехватит catch-all `(blue)/[slug]` и вернёт 200. Выбранный вариант зафиксировать комментарием в коде и отметить в Completion Notes.

Тело 404 после правки — глобальный `app/not-found.tsx` (минималистичная разметка: `404`, «Страница не найдена», ссылка на главную), а не `NotFoundView` внутри blue-layout с шапкой и подвалом, как отдаёт catch-all сейчас. Это ожидаемо и делает все 404 сайта одинаковыми; переделывать разметку в этой стори не нужно.

### Почему нельзя починить это в `[slug]/page.tsx`

`(blue)/[slug]/page.tsx:57-64` уже содержит обход: в ветке `if (!page)` ставится `robots: { index: false, follow: true }`, а `:76-80` рендерит `<NotFoundView />` вместо `notFound()` — с комментарием, что `notFound()` отдал бы 200 и при этом потерял бы `noindex`. Ограничение App Router: статус фиксируется до вызова `notFound()` при стриминге. Middleware выполняется **до** стриминга и статус вернуть может — отсюда выбор слоя в FR-41-21. Ветку `if (!page)` **не удалять** (AC11): при fail-open (AC7) и при гонке «slug ещё в кэше, но страница уже снята с публикации» она остаётся единственной защитой от индексации.

### Читаемое состояние кода, которое меняется

`frontend/src/middleware.ts` (86 строк) сейчас:

- `isProtectedRoute` (`:16-19`) — `/profile`, `/orders`, `/b2b-dashboard`;
- `isAuthRoute` (`:24-27`) — `/login`, `/register`, `/password-reset`, `/b2b-register`;
- `middleware` (`:32-67`) — синхронная: читает `refreshToken` из cookies, редиректит неавторизованного с защищённых маршрутов на `/login?next=…`, авторизованного — с auth-маршрутов на `/` либо на безопасный `next`/`redirect` (через `isSafeRedirectUrl` из `@/utils/urlUtils`); иначе `NextResponse.next()`;
- `config.matcher` (`:74-85`) — исключает `_next/static`, `_next/image`, `favicon.ico`, пути с точкой и `api/`.

Что должно сохраниться нетронутым: обе auth-ветки, их порядок и `matcher`. Что добавляется: список маршрутов, кэш слагов, ветка 404 перед финальным `next()`. Функция становится `async` — это единственное изменение её сигнатуры, и именно из-за него правятся существующие тесты (Task 5.2).

### Источник списка слагов

Эндпоинт `GET /api/v1/pages/` — `PageViewSet` (`backend/apps/pages/views.py:14-40`), `AllowAny`, отдаёт только `is_published=True`, кэшируется на бэкенде 24 часа под ключом `pages_list` с инвалидацией сигналом при `post_save`/`post_delete` (`backend/apps/pages/signals.py:19-30`). То есть публикация страницы в админке сбрасывает серверный кэш немедленно, и единственная задержка видимости — TTL кэша в middleware.

Ответ пагинирован (`PageNumberPagination`, `PAGE_SIZE: 20`, `PAGE_SIZE_QUERY_PARAM: "page_size"` — `backend/freesport/settings/base.py:168-170`), поэтому `?page_size=1000` обязателен. Обход пагинации не нужен: CMS-страниц единицы. Образец работы с этим API — `frontend/src/app/sitemap.ts:44-70` (`fetchAll`), но копировать его целиком не надо: там Data Cache через `next: { revalidate }`, которого в middleware **нет** — отсюда собственный кэш в памяти модуля.

Ответ включает поле `content` (полный HTML каждой страницы) — при десятке CMS-страниц это десятки килобайт раз в 5 минут, приемлемо. Заводить облегчённый эндпоинт `/pages/slugs/` в этой стори не нужно: это правка бэкенда, выходящая за границы FR-41-21.

### Почему 5 минут

Нижняя граница задаётся ценой промаха: каждый промах — сетевой запрос на пути HTML-ответа. Верхняя — AC6: вновь опубликованная страница обязана открыться «не позднее TTL», и ждать час редактор не должен. Пять минут дают ~12 запросов в час независимо от трафика и приемлемую задержку публикации. Значение вынести константой и снабдить этим обоснованием в комментарии — эпик требует явного значения с комментарием.

### Переменные окружения в middleware — главная мина стори

Middleware собирается в edge-бандл, и `process.env.X` в нём **подставляется значением на этапе сборки**, причём в бандл попадают только переменные с префиксом `NEXT_PUBLIC_`. Практические следствия для этого проекта:

- прод (`frontend/Dockerfile` + `docker/docker-compose.prod.yml:110-126`) собирает образ с build-args `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_URL`, `NODE_ENV`. `INTERNAL_API_URL=http://backend:8000` и `NEXT_PUBLIC_MEDIA_URL_INTERNAL` заданы только в `environment` — **в собранном middleware их не будет**;
- поэтому `getApiUrl()` из `[slug]/page.tsx:17-23` и `sitemap.ts:20-27` в middleware не переиспользуется: обе функции начинают цепочку с `INTERNAL_API_URL`, что для серверных компонентов (Node runtime, runtime env) верно, а для middleware — нет;
- отсюда AC10: `ARG`/`ENV` в `Dockerfile` и `build.args` в prod-compose. Без этой правки middleware в проде уйдёт на публичный `https://optisport.ru/api/v1` — наружу из контейнера и обратно через nginx, либо не уйдёт вовсе, и стори тихо выродится в fail-open: 404 не вернётся никогда, а в логах останутся только `warn`;
- dev-контейнер (`Dockerfile.dev`, `npm run dev`) компилирует на лету и читает окружение в runtime, поэтому `NEXT_PUBLIC_API_URL_INTERNAL=http://backend:8000/api/v1` (`docker/docker-compose.yml:115`) там уже работает;
- при запуске `npm run dev` на хосте вне Docker бэкенд доступен на `http://localhost:8001/api/v1` — это и есть `NEXT_PUBLIC_API_URL` из `.env.local`, второе звено цепочки.

### Почему не Playwright

E2E-прогон в CI (`.github/workflows/e2e-tests.yml`) поднимает **только** фронт (`webServer: npm run dev`, `playwright.config.ts:76-84`) — бэкенда в этом job нет. Запрос списка слагов упадёт, сработает fail-open (AC7), и тест на 404 будет падать в CI, оставаясь зелёным локально. Поэтому автоматическое покрытие — vitest с моком `fetch` (Task 5), а фактический HTTP-статус подтверждается ручной проверкой на живом контейнере (AC13).

### Ручная проверка

После `up -d --build frontend`, из PowerShell:

```powershell
"/offer","/terms","/korzina","/basket","/order","/product" | ForEach-Object {
  "$_ -> " + (Invoke-WebRequest "http://localhost:3000$_" -SkipHttpErrorCheck).StatusCode
}   # ожидается 404 на каждом

"/oferta","/about","/catalog","/home","/login","/coming-soon","/electric-orange" | ForEach-Object {
  "$_ -> " + (Invoke-WebRequest "http://localhost:3000$_" -SkipHttpErrorCheck).StatusCode
}   # ожидается 200 на каждом
```

Отдельно проверить, что `/offer` возвращает именно 404 **с телом**, а не пустой ответ, и что `/robots.txt` и `/sitemap.xml` по-прежнему 200 (matcher их исключает — AC9).

Проверка через nginx (`http://localhost/offer`) тоже должна давать 404: в `docker/nginx/conf.d/default.conf:214-235` у `location /` включён `proxy_intercept_errors on`, но `error_page` объявлен только для 502/503/504, поэтому 404 проходит насквозь. Если через nginx придёт не 404 — не «чинить» это в middleware, а зафиксировать находкой для стори 41.5.

### Blast radius

```
npx gitnexus impact middleware --direction upstream
→ { "risk": "LOW", "impactedCount": 0, "affected_processes": [], "affected_modules": [] }
```

Ноль вызывающих — middleware вызывает фреймворк. Реальный риск не в графе, а в трафике: функция стоит на пути каждого HTML-запроса. Отсюда обязательность fail-open (AC7), таймаута (Task 2.1) и кэша (AC6): необработанная ошибка или синхронный поход в сеть здесь деградируют весь сайт, а не одну страницу. Перед коммитом — `npx gitnexus detect-changes --scope all`; ожидаемые символы — только `middleware` и новые хелперы в том же файле.

### Project Structure Notes

- Тесты фронта — Vitest (`npm run test`), не Jest; файлы ищутся по `src/**/__tests__/**/*.{test,spec}.{ts,tsx}` (`vitest.config.mts:30`), поэтому новый тест-страж кладём в `src/__tests__/`.
- Пороги покрытия vitest — 65 % по всем четырём метрикам (`vitest.config.mts:36-41`); правка небольшая, но новый код обязан быть покрыт.
- Комментарии и docstrings — на русском (NFR-41-03, `project-context.md` §6).
- Ветка от `develop`, `feature/*`; прямые коммиты в `develop` запрещены.
- Правки `middleware.ts` и `Dockerfile` требуют **полной пересборки** контейнера (`up -d --build frontend`); `restart frontend` недостаточно.
- Деплой на прод ручной по SSH; после рестарта backend на проде обязателен дополнительный `docker compose restart nginx`.

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.0] — user story, AC-скелет, контекст
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Functional Requirements] — FR-41-21, порядок стори эпика
- [Source: _bmad-output/implementation-artifacts/intent-site-audit-2026-08-24.md#1] — триаж аудита: 14 фантомных адресов, поправка про `/oferta`
- [Source: frontend/src/middleware.ts] — текущая auth-логика и `matcher`
- [Source: frontend/src/app/(blue)/[slug]/page.tsx:38-80] — catch-all, `fetchPage`, обход soft-404
- [Source: frontend/src/app/not-found.tsx] — разметка 404
- [Source: frontend/src/app/sitemap.ts:20-70] — образец обращения к `/pages/` из фронта
- [Source: backend/apps/pages/views.py:14-40] — `PageViewSet`, фильтр `is_published`, кэш `pages_list`
- [Source: backend/apps/pages/signals.py:19-30] — инвалидация кэша при публикации
- [Source: backend/freesport/settings/base.py:168-170] — пагинация DRF и `page_size`
- [Source: frontend/next.config.ts:81-97] — rewrite `/electric-orange`, redirect `/promotions`
- [Source: frontend/Dockerfile:27-39] — build-args и момент сборки
- [Source: docker/docker-compose.prod.yml:110-126] — build-args и environment прод-фронта
- [Source: docker/nginx/conf.d/default.conf:214-235] — `location /` и `proxy_intercept_errors`
- [Source: _bmad-output/implementation-artifacts/spec-footer-links-oferta.md] — `/oferta` как опубликованная CMS-запись и ссылка в подвале
- [Source: project-context.md#7] — фронтенд-специфика Next 15 / React 19, протокол пересборки контейнера

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, dev-story)

### Debug Log References

- `npx vitest run src/__tests__/middleware.test.ts src/__tests__/app-routes-allowlist.test.ts` — RED-фаза: 16 падений / 15 существующих зелёных; после реализации 31/31 зелёные
- `npx vitest run` (полный набор фронта) — 146 файлов, 2478 passed, 16 skipped, регрессий нет
- `npm run lint` (`eslint . --max-warnings=0`) — чисто; `npx prettier --check` по изменённым файлам — чисто
- `npx gitnexus detect-changes --scope all` — `Risk level: low`, затронуты только символы `frontend/src/middleware.ts` (правки `AGENTS.md`/`CLAUDE.md` в выводе — чужие незакоммиченные изменения рабочего дерева, к стори не относятся)

### Completion Notes List

**Реализация.** `frontend/src/middleware.ts` стал асинхронным: после существующих auth-веток (они не изменены и по-прежнему первые) добавлена проверка односегментного пути. Сегмент не из `KNOWN_TOP_LEVEL_ROUTES` и не из списка опубликованных CMS-слагов → `NextResponse.rewrite(new URL('/_not-found', request.url), { status: 404 })`. Список слагов кэшируется в памяти модуля (TTL 5 минут, stale-while-revalidate, single-flight, таймаут запроса 2 с) и на любую неудачу отвечает fail-open с `console.warn`.

**Механика 404 подтверждена на живом сервере — запасной вариант не понадобился.** Основной вариант (`rewrite` на `/_not-found` со `status: 404`) отдаёт настоящий 404, как и предполагал разбор исходников Next 15.5.18.

**AC13 — проверено дважды: на локальной production-сборке и в Docker.** Сначала (Docker-демон был недоступен) — `next build` + `next start -p 3100` против живого backend; затем, после запуска Docker, — штатным путём: `up -d --build frontend`, `restart nginx` (backend пересоздался вместе с фронтом, nginx иначе держит старый IP апстрима). Результаты обоих прогонов совпали.

Фактический вывод в Docker (контейнер `:3000` и через nginx `:80`):

```
=== должны быть 404 ===        === должны быть 200 ===
/offer       404               /oferta            200
/terms       404               /about             200
/korzina     404               /catalog           200
/basket      404               /home              200
/order       404               /login             200
/product     404               /coming-soon       200
/aaa         404               /electric-orange   200
                               /privacy-policy    200
=== через nginx :80 ===        /requisites        200
/offer         404             /blog              200
/terms         404             /news              200
/korzina       404
/oferta        200
/about         200
/catalog       200
/robots.txt    200
/sitemap.xml   200  (94 с в dev-режиме — генерация обходит API; к стори не относится)
/foo/bar       404  (Next сам, middleware не вмешивался)
/profile       307  (редирект анонима на /login — регрессии нет)
```

Тело `/offer` и через контейнер, и через nginx: `<title>Страница не найдена | OPTISPORT</title>`, заголовок «404», текст «Страница не найдена» — AC1 по телу выполнен. nginx статус не подменяет: `proxy_intercept_errors on` объявляет `error_page` только для 502/503/504.

**Fail-open (AC7) проверен вживую, а не только тестами.** `stop backend` + `restart frontend` (холодный кэш) → `/offer` и `/oferta` отдали **200** (запрос пропущен дальше по прежнему пути), в логах контейнера:

```
[middleware] Не удалось получить список CMS-слагов: TimeoutError: The operation was aborted due to timeout
[middleware] Проверка адреса /offer пропущена: список слагов недоступен
```

Таймаут 2 с сработал — недоступный backend сайт не подвесил. После `start backend` + `restart nginx` `/offer` немедленно вернулся к 404, `/oferta` — 200.

**Кэш (AC6) проверен по логам backend:** пять обращений к разным несуществующим адресам подряд дали **0** запросов `GET /api/v1/pages/?page_size=1000` — список брался из кэша.

**Границы соблюдены.** `(blue)/[slug]/page.tsx`, `not-found.tsx`, `robots.ts`, `sitemap.ts`, `seo.ts`, `next.config.ts`, nginx и бэкенд не изменялись; новых зависимостей нет.

**Работа велась в ветке `feature/story-41-0-real-404`** (от `develop`, коммит не делался — по правилу проекта коммит/пуш только по явной просьбе).

### Change Log

| Дата | Изменение |
|---|---|
| 2026-08-24 | Реализована стори 41.0: настоящий HTTP 404 для несуществующих адресов верхнего уровня (middleware + кэш CMS-слагов + fail-open), `ARG NEXT_PUBLIC_API_URL_INTERNAL` в сборку фронта, тест-страж списка маршрутов. Статус → review |

### File List

- `frontend/src/middleware.ts` — изменён: список известных маршрутов, кэш слагов, ветка 404, функция стала async
- `frontend/src/__tests__/middleware.test.ts` — изменён: async-вызовы, мок `NextResponse.rewrite` и `fetch`, изоляция модульного состояния, 21 новый тест
- `frontend/src/__tests__/app-routes-allowlist.test.ts` — добавлен: тест-страж соответствия списка маршрутов структуре `src/app`
- `frontend/Dockerfile` — изменён: `ARG`/`ENV NEXT_PUBLIC_API_URL_INTERNAL` до `npm run build`
- `docker/docker-compose.prod.yml` — изменён: `NEXT_PUBLIC_API_URL_INTERNAL` в `build.args` сервиса `frontend`
- `_bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md` — изменён: чекбоксы задач, Dev Agent Record, статус
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — изменён: статус стори `ready-for-dev` → `in-progress` → `review`
