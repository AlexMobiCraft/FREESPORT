---
baseline_commit: a041e1b0
---

# Story 41.0: Несуществующие адреса отдают настоящий 404

Status: done

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

6. **AC6 (FR-41-21).** Список опубликованных слагов кэшируется в памяти модуля. TTL задан **именованной константой с комментарием** (обязательное требование эпика), запрос к API выполняется не чаще одного раза за TTL. Решение по протухшему кэшу **несимметрично** (уточнено в раунде 2 ревью): slug, который в устаревшем списке **есть**, сразу получает 200, а обновление идёт фоном (stale-while-revalidate) — задержки в ответ это не добавляет; slug, которого в устаревшем списке **нет**, обновления **дожидается**, потому что отсутствие в протухшем списке не доказывает, что страницы нет (иначе вновь опубликованная страница получала бы 404 в первом же запросе после TTL). Параллельные промахи кэша схлопываются в один запрос (single-flight): без этого всплеск трафика на холодном кэше даст лавину запросов к бэкенду. После неудачного обращения к API включается **пауза-backoff** именованной константой (`SLUGS_FAILURE_BACKOFF_MS`, 30 с): в течение неё новые запросы к API не создаются, а решение сразу считается «не знаю» → fail-open по AC7. Вновь опубликованный в админке slug отдаёт 200 не позднее TTL.

7. **AC7 (FR-41-21, fail-open).** Если список слагов получить не удалось — бэкенд недоступен, таймаут, статус ≥ 400, ответ не разобрался — middleware **не отдаёт 404 вслепую**, а пропускает запрос дальше по прежнему пути (`NextResponse.next()`), и факт пишется в лог (`console.warn` с путём и причиной). Запрос к API ограничен явным таймаутом: без него недоступный бэкенд подвесит каждый HTML-запрос сайта.

8. **AC8 (регрессия).** Существующее поведение middleware сохранено полностью: редирект неавторизованного с `/profile`, `/orders`, `/b2b-dashboard` на `/login` с параметром `next`; редирект авторизованного с `/login`, `/register`, `/password-reset`, `/b2b-register` на `/` или на безопасный `next`/`redirect` через `isSafeRedirectUrl`. Проверка 404 выполняется **после** auth-веток и только на пути, который иначе вернул бы `NextResponse.next()` — сетевой запрос не должен вклиниваться в редиректы. Существующие тесты `frontend/src/__tests__/middleware.test.ts` продолжают проходить.

9. **AC9 (FR-41-21).** `matcher` по-прежнему исключает `_next/static`, `_next/image`, `favicon.ico`, любые пути с точкой (шаблон `.*\..*` покрывает `/robots.txt`, `/sitemap.xml`, `/media/...`, файлы из `public/`) и `api/`. **Уточнение раунда 3:** к списку исключений добавлен якорь `api$` — ровно путь `/api` без завершающего слэша под `api/` не подпадал, попадал в middleware и перехватывался логикой 404 раньше, чем срабатывал rewrite `/api/:path*` из `next.config.ts`. Других изменений `matcher` не вносится: он трогает маршрутизацию всего сайта.

10. **AC10 (доставка URL API в edge-бандл).** Middleware обращается к API по **внутреннему** адресу Docker-сети. В `frontend/Dockerfile` добавлен `ARG NEXT_PUBLIC_MIDDLEWARE_API_URL` с дефолтом `http://backend:8000/api/v1` и соответствующий `ENV` **до** `RUN npm run build`; в `docker/docker-compose.prod.yml` он передан в `build.args` сервиса `frontend`. Причина обязательна к пониманию: в edge-бандл middleware переменные подставляются **на этапе сборки**, и попадают туда только `NEXT_PUBLIC_*`. Сейчас `INTERNAL_API_URL` и `NEXT_PUBLIC_API_URL_INTERNAL` заданы в проде только в `environment` (runtime) — в собранном middleware они будут `undefined`, и запрос уйдёт по публичному `https://optisport.ru/api/v1` наружу и обратно через nginx либо не уйдёт вовсе. `Dockerfile.dev` не меняется: dev-контейнер компилирует на лету и читает окружение в runtime.

    **Уточнение раунда 6:** переменная сборки — **выделенная** (`NEXT_PUBLIC_MIDDLEWARE_API_URL`), а не общий `NEXT_PUBLIC_API_URL_INTERNAL`. Подстановка на этапе сборки действует не только на middleware: `process.env.NEXT_PUBLIC_*` инлайнится во весь код, включая серверные компоненты. Общее имя в `build.args` переключило бы на внутренний `http://backend:8000` и страницы `/oferta` и `/privacy-policy`, а они не шлют `X-Forwarded-Proto` — при штатном `SECURE_SSL_REDIRECT=True` их запрос уехал бы на `https://backend:8000`, где TLS нет. В цепочке `getApiBaseUrl()` выделенная переменная стоит первой, `NEXT_PUBLIC_API_URL_INTERNAL` остаётся вторым звеном для dev-контейнера (runtime-окружение из `docker/docker-compose.yml`). Контракт закреплён тест-стражем `frontend/src/__tests__/middleware-build-env.test.ts`.

11. **AC11 (границы стори).** **Не изменяются:** `(blue)/[slug]/page.tsx` (ветка `if (!page)` с `noindex` остаётся страховкой на случай fail-open и гонки «slug в списке, но страница уже снята»), `app/not-found.tsx`, `app/robots.ts`, `app/sitemap.ts`, `utils/seo.ts`, `next.config.ts`, `docker/nginx/**` (заголовки — объём стори 41.5). Новых зависимостей в `package.json` нет.

    **Граница расширена решением владельца по итогам ревью** — исходная формулировка запрещала любые правки бэкенда и `openapi.yaml`, но обе находки High оказались именно там: список слагов, на который опирается middleware, приходил неполным и мог воскресать из кэша. Дополнительно изменяются:
    - `backend/apps/pages/views.py`, `backend/apps/pages/signals.py`, `backend/apps/pages/cache_keys.py` — пагинация `?page_size`, версионированный кэш полного списка и его инвалидация;
    - `backend/tests/integration/test_pages_api.py` — тесты на пагинацию, инвалидацию, поздний writer и сортировку;
    - `docs/api/openapi.yaml` и `frontend/src/types/api.generated.ts` — параметр `page_size` у `GET /pages/` и регенерация типов.

    Изменяются, кроме перечисленного: `frontend/src/middleware.ts`, `frontend/src/__tests__/middleware.test.ts`, новые файлы тестов-стражей (`app-routes-allowlist.test.ts`, `middleware-build-env.test.ts` — раунд 6), `frontend/Dockerfile`, `docker/docker-compose.prod.yml`.

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
  - [x] 4.1: `frontend/Dockerfile`: рядом с существующими `ARG NEXT_PUBLIC_API_URL` / `ARG NEXT_PUBLIC_APP_URL` (строки 27-30) добавить `ARG NEXT_PUBLIC_MIDDLEWARE_API_URL=http://backend:8000/api/v1` и `ENV NEXT_PUBLIC_MIDDLEWARE_API_URL=$NEXT_PUBLIC_MIDDLEWARE_API_URL` — обязательно **выше** `RUN npm run build` (строка 39). Имя выделенное, а не общий `NEXT_PUBLIC_API_URL_INTERNAL` (уточнение раунда 6 в AC10)
  - [x] 4.2: `docker/docker-compose.prod.yml`, сервис `frontend`, блок `build.args` (строки 113-117): добавить `NEXT_PUBLIC_MIDDLEWARE_API_URL: http://backend:8000/api/v1`
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

### Review Findings

- [x] [Review][Patch] **[High] Сделать backend-кэш списка страниц зависимым от пагинации и синхронизировать его инвалидацию.** Решение пользователя: расширить границу AC11 и исправить `PageViewSet.list()`, чтобы запрос middleware с `page_size=1000` не мог получить закэшированную выдачу на 20 записей. [`backend/apps/pages/views.py:30-40`, `backend/apps/pages/signals.py:19-23`]
- [x] [Review][Patch] **[High] Протухший allowlist используется для отрицательного решения и обходит fail-open.** После TTL код запускает обновление фоном, но сразу возвращает старый `Set`; отсутствующий в нём вновь опубликованный slug получает 404 в первом запросе после TTL, а при недоступном backend — продолжает получать ложный 404, несмотря на AC6/AC7. Отсутствие slug в stale-кэше нельзя считать доказательством 404. [`frontend/src/middleware.ts:158-165,240-257`]
- [x] [Review][Patch] **[Medium] Частично невалидный или неполный ответ API становится авторитетным allowlist.** Элементы без строкового `slug` молча пропускаются, а пустой/частичный `Set` затем превращает реальные CMS-страницы в 404; это нарушает fail-open для ответа, который не удалось полностью разобрать. Нужно валидировать элементы и признаки полноты (`count`/`next`) и возвращать `null` при несогласованности. [`frontend/src/middleware.ts:116-128`]
- [x] [Review][Patch] **[Low] Single-flight не покрыт тестом параллельных cold misses.** Текущий тест ждёт первый запрос до запуска второго, поэтому ветка `if (inflightSlugsRequest)` не исполняется и обязательное поведение AC6 остаётся непроверенным. [`frontend/src/__tests__/middleware.test.ts:279-298`]

#### Раунд 3 — повторное ревью после исправлений

- [x] [Review][Patch] **[Medium] Добавить 30-секундный backoff после быстрого отказа API.** Решение владельца: после HTTP 500, невалидного JSON или сетевого отказа middleware продолжает fail-open, но в течение 30 секунд не создаёт новые запросы списка CMS-слагов; single-flight остаётся защитой параллельных запросов. [`frontend/src/middleware.ts:105-169,198-212`]
- [x] [Review][Patch] **[Critical] Внутренний HTTP URL не работает при штатном `SECURE_SSL_REDIRECT=True`: backend редиректит запрос на `https://backend:8000`, где TLS нет; middleware уходит в fail-open, а другие потребители нового build-time ENV теряют CMS-страницы.** [`frontend/src/middleware.ts:92-109`, `frontend/Dockerfile:28-44`, `docker/docker-compose.prod.yml:114-120`, `backend/freesport/settings/production.py:30-42`]
- [x] [Review][Patch] **[High] Поздний writer холодного кэша может записать устаревший список после сигнала инвалидации и сохранить ложные 404 на 24 часа.** [`backend/apps/pages/views.py:62-67`, `backend/apps/pages/signals.py:20-29`]
- [x] [Review][Patch] **[Medium] Ответ API без числового `count` и явного признака завершённой пагинации принимается за полный allowlist вместо fail-open.** [`frontend/src/middleware.ts:116-149`, `frontend/src/__tests__/middleware.test.ts:420-501`]
- [x] [Review][Patch] **[Medium] Первый запрос с `ordering` отравляет общий кэш своим порядком, а последующие варианты ordering больше не применяются.** [`backend/apps/pages/views.py:62-73`, `backend/freesport/settings/base.py:163-169`]
- [x] [Review][Patch] **[Medium] Тест-страж не обнаруживает односегментный маршрут, если `page.tsx` лежит в route group после статического сегмента.** [`frontend/src/__tests__/app-routes-allowlist.test.ts:29-47`]
- [x] [Review][Patch] **[Medium] Percent-encoded опубликованный slug сравнивается до декодирования и получает ложный 404.** [`frontend/src/middleware.ts:222-224,284-301`]
- [x] [Review][Patch] **[Medium] Точный `/api` не исключён matcher-ом и перехватывается 404-логикой до существующего rewrite `/api/:path*`.** [`frontend/src/middleware.ts:314-325`, `frontend/next.config.ts:66-76`]
- [x] [Review][Patch] **[Medium] Нормативный AC6 всё ещё обещает немедленный stale-ответ для любого slug, хотя исправленная отрицательная ветка намеренно ждёт refresh.** [`_bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md:37,293-295`]
- [x] [Review][Patch] **[Medium] Нормативный AC11 по-прежнему запрещает backend/OpenAPI-правки, хотя раунд 2 расширил границу story.** [`_bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md:47,287-297,349-354`]
- [x] [Review][Patch] **[Low] File List не содержит реально попавшие в диапазон изменения `AGENTS.md` и `CLAUDE.md`.** [`AGENTS.md`, `CLAUDE.md`, `_bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md:342-356`]
- [x] [Review][Patch] **[High] Перенести инвалидацию кэша Page на `transaction.on_commit`: текущий `post_save` публикует новую версию ключа до commit, поэтому параллельный GET может закэшировать допубликационный список на 24 часа, а middleware — ложно отдавать 404 дольше TTL.** [`backend/apps/pages/signals.py:20-44`, `backend/apps/pages/views.py:86-93`]

#### Раунд 5 — повторное ревью после исправления `on_commit` (2026-08-25)

- [x] [Review][Decision] **[Medium] Определить поведение при количестве опубликованных CMS-страниц больше 1000.** Решение владельца: зафиксировать поддерживаемый предел 1000 и предупреждать заранее (см. Completion Notes → раунд 5). `PagesPagination.max_page_size = 1000`, а middleware намеренно отвергает ответ с непустым `next`; на 1001-й странице allowlist перестаёт обновляться и все неизвестные URL уходят в fail-open. Нужно выбрать контракт: зафиксировать поддерживаемый лимит, обходить все страницы пагинации либо добавить облегчённый endpoint слагов. [`backend/apps/pages/views.py:31-42`, `frontend/src/middleware.ts:70-71,120-185`]
- [x] [Review][Patch] **[Medium] Принимать завершённую пагинацию только при `data.next === null`: сейчас `false`, `0` и пустая строка считаются валидным признаком полного ответа и могут сделать частичный allowlist авторитетным.** [`frontend/src/middleware.ts:154-174`]
- [x] [Review][Patch] **[Medium] Нормализовать завершающий слэш базового URL API: значение `.../api/v1/` формирует путь `.../api/v1//pages/` и переводит middleware в постоянный fail-open.** [`frontend/src/middleware.ts:107-121`]
- [x] [Review][Patch] **[Low] Считать кэш протухшим при возрасте `>= SLUG_CACHE_TTL_MS`, а не только `>`: на точной границе TTL отрицательное решение ещё принимается без refresh, вопреки «не позднее TTL» из AC6.** [`frontend/src/middleware.ts:234-241`]
- [x] [Review][Patch] **[Low] Добавить доказательство части AC2 про метаданные опубликованной CMS-страницы: текущий тест `/oferta` проверяет только `NextResponse.next()`, но не вызов `buildMetadata` и отсутствие `noindex`.** [`frontend/src/__tests__/middleware.test.ts:222-228`, `frontend/src/app/(blue)/[slug]/page.tsx:57-73`]
- [x] [Review][Patch] **[Low] Актуализировать Dev Agent Record: заменить `RESULT_PLACEHOLDER` фактическим результатом либо отметить непройденный gate и убрать устаревшее утверждение первого раунда, что backend не изменялся.** [`_bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md:277,325`]
- [x] [Review][Defer] **[High] Недоступный Redis во время signal/on_commit оставляет уже сохранённое изменение Page с ответом 500 и без гарантированной инвалидации кэша.** [`backend/apps/pages/signals.py:40,57-66`] — deferred, pre-existing

#### Раунд 6 — независимое ревью после исправлений раунда 5 (2026-08-25)

- [x] [Review][Patch] **[High] Build-time `NEXT_PUBLIC_API_URL_INTERNAL` меняет источник API не только для middleware: production-сборка направляет CMS-страницы на внутренний HTTP backend без `X-Forwarded-Proto`, поэтому при штатном `SECURE_SSL_REDIRECT=True` `/oferta` и `/privacy-policy` перестают получать данные.** [`frontend/Dockerfile:34-44`, `frontend/src/app/(blue)/[slug]/page.tsx:16-49`, `frontend/src/app/(blue)/privacy-policy/page.tsx:23-79`]
- [x] [Review][Patch] **[Medium] Закодированный слэш обходит настоящий 404: `getSingleSegment()` возвращает `null` для `/foo%2Fbar`, но Next всё равно передаёт исходный encoded-сегмент catch-all странице, и живой запрос отдаёт HTTP 200 soft-404.** [`frontend/src/middleware.ts:343-351`]
- [x] [Review][Patch] **[Low] Добавить `deferred-work.md` в File List: файл реально изменён в baseline-diff записью отложенной находки про Redis, но в итоговом перечне отсутствует.** [`_bmad-output/implementation-artifacts/deferred-work.md:1-3`, `_bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md:533-557`]
- [x] [Review][Defer] **[Medium] Префиксная проверка auth-маршрутов редиректит авторизованного с несуществующих `/login-foo`, `/register-old` и `/b2b-register-invalid` вместо 404.** [`frontend/src/middleware.ts:365-367,395-407`] — deferred, pre-existing

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
- **Раунд 6:** `npx vitest run src/__tests__/middleware.test.ts src/__tests__/middleware-build-env.test.ts` — RED-фаза: 7 падений (3 закодированный слэш, 1 приоритет переменной, 3 тест-страж сборки) / 61 зелёный; после реализации 74/74 зелёные вместе с тестом-стражем маршрутов
- **Раунд 6:** `npx vitest run` (полный набор фронта) — 148 файлов, 2524 passed, 16 skipped, регрессий нет; `npm run lint` и `npx prettier --check` по изменённым файлам — чисто
- **Раунд 6:** `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/integration/test_pages_api.py` — 30 passed (бэкенд в этом раунде не менялся, прогон контрольный)
- **Раунд 6:** `npx gitnexus detect-changes --scope unstaged` — risk low, affected processes 0, затронуты только `middleware.ts` и его хелперы
- **Раунд 6:** `npx vitest run src/__tests__/middleware.test.ts src/__tests__/middleware-build-env.test.ts` — RED-фаза: 7 падений (3 закодированный слэш, 1 приоритет переменной, 3 страж переменных сборки); после реализации 74/74 зелёные
- **Раунд 6:** `npx vitest run` (полный набор фронта) — 148 файлов, 2524 passed, 16 skipped, регрессий нет; `npm run lint` и `npx prettier --check` — чисто
- `npx gitnexus detect-changes --scope all` — `Risk level: low`, затронуты только символы `frontend/src/middleware.ts` (правки `AGENTS.md`/`CLAUDE.md` в выводе — чужие незакоммиченные изменения рабочего дерева, к стори не относятся)

**Раунд 2 — правки по ревью (2026-08-24):**

- `npx gitnexus impact PageViewSet|invalidate_page_cache|middleware --direction upstream` — все три `risk: LOW`, `impactedCount` 1/0/0
- `pytest tests/integration/test_pages_api.py::PagesListCachePaginationTest` — RED: `AssertionError: 20 != 25` (кэш отдавал выдачу по умолчанию на запрос `?page_size=1000`)
- `npx vitest run src/__tests__/middleware.test.ts` — RED: 5 падений из 36 (протухший кэш, неполный/невалидный ответ API)
- После правок: `pytest tests/integration/test_pages_api.py apps/pages` — 34 passed; `npx vitest run src/__tests__/middleware.test.ts src/__tests__/app-routes-allowlist.test.ts` — 39 passed
- `npx vitest run` (полный набор фронта) — 146 файлов, 2486 passed, 16 skipped
- `npm run lint` — чисто; `npx prettier --check` по изменённым файлам — чисто; `black --check` + `flake8` по изменённым backend-файлам — чисто (`apps/pages/models.py` и `apps/pages/tests.py` не проходят `black` и **до** правок — не трогал)
- `pytest -m "not performance and not slow"` (полный набор бэкенда, фильтр как в `main.yml`) — **3046 passed, 75 skipped, 35 deselected**, регрессий нет (27:55)
- `npx gitnexus detect-changes --scope all` — `Risk level: low`, `Affected processes: 0`

**Раунд 3 — правки по повторному ревью (2026-08-24):**

- `npx gitnexus impact PageViewSet|invalidate_page_cache --direction upstream` — обе `risk: LOW`, `impactedCount` 1/0
- `pytest tests/integration/test_pages_api.py::PagesListCacheConsistencyTest` — RED: `ImportError: cannot import name 'get_pages_list_version'` (версионирования ключа ещё не было)
- `npx vitest run src/__tests__/middleware.test.ts src/__tests__/app-routes-allowlist.test.ts` — RED: 10 падений из 54 (пауза-backoff, заголовок протокола, строгая проверка `count`/`next`, percent-decoding, `/api` в matcher, группы в тесте-страже)
- После правок: `pytest tests/integration/test_pages_api.py apps/pages` — 38 passed; те же vitest-файлы — 54 passed
- `npx vitest run` (полный набор фронта) — 146 файлов, **2502 passed, 16 skipped**
- `npm run test:coverage` — пороги vitest (65 % по всем метрикам) держатся: All files 78.5 / 71.2 / 73.84 / 79.82; `middleware.ts` — **98.16 lines / 94.52 branches / 87.5 functions / 100 statements**
- `npm run lint` — чисто; `npm run format:check` (Prettier по всему проекту) — чисто (`middleware.ts` пришлось прогнать через `--write`); `black --check` + `flake8` по изменённым backend-файлам — чисто
- `npx gitnexus detect-changes --scope all` — `Risk level: low`, `Affected processes: 0`
- `pytest -m "not performance and not slow"` (полный набор бэкенда, фильтр как в `main.yml`) — **3050 passed, 75 skipped, 35 deselected** за 31:27, регрессий нет (раунд 2 давал 3046 passed — прибавка ровно на 4 новых теста)

**Раунд 4 — правка по последней находке ревью (2026-08-25):**

- `npx gitnexus impact invalidate_page_cache --direction upstream` — `risk: LOW`, `impactedCount: 0` (signal-receiver, прямых вызывающих нет)
- `pytest tests/integration/test_pages_api.py::PagesListCacheConsistencyTest` — RED: `AssertionError: 0 != 1` (сигнал сбрасывал кэш прямо в `post_save`, ни одного отложенного коллбэка на commit не регистрировалось)
- После правки: `pytest tests/integration/test_pages_api.py apps/pages` — **40 passed** (было 38, прибавка ровно на 2 новых теста)
- `npx vitest run` (полный набор фронта) — 146 файлов, **2502 passed, 16 skipped**; фронт в этом раунде не менялся, регрессий нет
- `black --check` + `flake8` по `apps/pages/signals.py` и `tests/integration/test_pages_api.py` — чисто
- `npx gitnexus detect-changes --scope all` — `Risk level: low`, `Affected processes: 0`; затронутые символы — только `invalidate_page_cache`, `_revalidate_nextjs`, `thread` в `apps/pages/signals.py`
- `pytest -m "not performance and not slow"` (полный набор бэкенда, фильтр как в `main.yml`) — **3052 passed, 75 skipped, 35 deselected** за 27:48, регрессий нет (раунд 3 давал 3050 passed — прибавка ровно на 2 новых теста)

**Раунд 5 — правки по повторному ревью (2026-08-25):**

- `npx vitest run src/__tests__/middleware.test.ts` — RED: 5 падений из 55 (строгая проверка `next`, завершающий слэш базового URL, граница TTL)
- После правок: те же файлы — 58 passed (включая 3 теста на поддерживаемый предел числа CMS-страниц); новый `src/app/(blue)/[slug]/__tests__/page.test.tsx` — 3 passed
- `npm run test:coverage` (полный набор фронта) — 147 файлов, **2514 passed, 16 skipped**; пороги vitest (65 %) держатся: All files 78.42 / 71.21 / 73.8 / 79.83, `middleware.ts` — 98.24 lines / 94.8 branches / 87.5 functions / 100 statements
- `npm run lint` — чисто; `npm run format:check` (Prettier по всему проекту) — чисто; `npx tsc --noEmit` — чисто
- `pytest tests/integration/test_pages_api.py apps/pages` — 40 passed; `black --check` + `flake8` по `apps/pages/views.py` — чисто (изменение комментарное)
- `pytest -m "not performance and not slow"` (полный набор бэкенда) — **3052 passed, 75 skipped, 35 deselected** за 29:20, регрессий нет

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

**Границы соблюдены (на момент первого раунда).** `(blue)/[slug]/page.tsx`, `not-found.tsx`, `robots.ts`, `sitemap.ts`, `seo.ts`, `next.config.ts` и nginx не изменялись; новых зависимостей нет.

> ⚠️ **Актуализировано после раундов 2–4:** утверждение «бэкенд не изменялся» с раунда 2 неверно. Границу AC11 расширил владелец — обе находки High лежали в бэкенде, поэтому изменены `backend/apps/pages/{views,signals,cache_keys}.py`, `backend/tests/integration/test_pages_api.py` и `docs/api/openapi.yaml`. Полный перечень — в File List; список неизменяемых файлов (`[slug]/page.tsx`, `not-found.tsx`, `robots.ts`, `sitemap.ts`, `seo.ts`, `next.config.ts`, nginx) соблюдён до конца.

**Работа велась в ветке `feature/story-41-0-real-404`** (от `develop`, коммит не делался — по правилу проекта коммит/пуш только по явной просьбе).

---

## Раунд 2 — устранение находок ревью (2026-08-24)

✅ **Resolved review finding [High]: backend-кэш списка страниц не зависел от пагинации.** Граница AC11 расширена решением пользователя. `PageViewSet.list()` кэширует теперь **полный сериализованный список** опубликованных страниц под одним ключом, а пагинация применяется к нему на каждом запросе. Имя ключа сменено на `pages_list_serialized` намеренно: под старым `pages_list` в проде лежит готовый пагинированный ответ (dict), и после выката нового кода такое значение сломало бы пагинацию — старые записи просто истекут по TTL. Ключ и TTL вынесены в общий модуль `apps/pages/cache_keys.py`, чтобы имя во view и в сигнале инвалидации не могло разъехаться. Один ключ на всю выдачу выбран сознательно: он не даёт размножать записи кэша произвольными `page_size` и оставляет инвалидацию точечной.

🔴 **Побочная находка при написании RED-теста, важная сама по себе: `?page_size=1000` вообще не работал.** `PAGE_SIZE_QUERY_PARAM` в `backend/freesport/settings/base.py:170` — не настройка DRF, а атрибут класса пагинации (в проекте это уже знали, см. комментарий в `apps/bonuses/views.py:30`). Выдача обрезалась до `PAGE_SIZE` = 20, то есть middleware видел только первые 20 CMS-слагов, и **21-я опубликованная страница молча отдавала бы 404** — ровно та беда, которую стори должна была предотвратить. Добавлен `PagesPagination` (`page_size_query_param = "page_size"`, `max_page_size = 1000`) на `PageViewSet`. Глобальную настройку не трогал: это изменило бы пагинацию всего API. Живая проверка: `GET /api/v1/pages/?page_size=1000` → `count 3, results 3, next None`.

✅ **Resolved review finding [High]: протухший allowlist использовался для отрицательного решения и обходил fail-open.** Решение в `isPublishedSlug()` стало намеренно несимметричным: положительное принимается и по протухшему кэшу (stale-while-revalidate, обновление фоном — задержки в ответ не добавляется), а отрицательное — только по свежему списку; протухший кэш обязан дождаться обновления, и неудача снова означает `null` → fail-open. AC6 в части «протухший отдаётся сразу» сузился до положительных решений — отсутствие слага в устаревшем списке не доказательство того, что страницы нет.

✅ **Resolved review finding [Medium]: неполный или частично невалидный ответ API становился авторитетным allowlist-ом.** `fetchPublishedSlugs()` возвращает `null` (fail-open + `console.warn`), если выдача обрезана пагинацией (`next` не пуст), если `count` не совпадает с числом полученных записей или если хоть один элемент не имеет непустого строкового `slug`. Пустой список при `count: 0` остаётся валидным ответом и по-прежнему даёт 404.

✅ **Resolved review finding [Low]: single-flight не был покрыт тестом параллельных cold miss'ов.** Добавлен тест с «зависшим» запросом к API: два вызова middleware стартуют, пока первый запрос в полёте, — ветка `if (inflightSlugsRequest)` исполняется, `fetch` вызывается ровно один раз.

**Живая проверка правок на контейнерах.** Статусы после `restart frontend` (Dockerfile в этом раунде не менялся, dev-контейнер компилирует middleware на лету):

```
=== 404 ===                    === 200 ===
/offer   /terms   /korzina     /oferta  /requisites1  /privacy-policy
/basket  /order   /product     /about   /catalog      /home
/aaa                           /login   /coming-soon  /electric-orange

=== через nginx :80 ===
/offer 404  /terms 404  /korzina 404  /foo/bar 404  /profile 307
/oferta 200 /requisites1 200 /about 200 /catalog 200 /robots.txt 200
```

`/requisites1` — CMS-страница, которой нет в списке маршрутов: 200 через список слагов, то есть новая валидация ответа работает. Тело `/offer`: `<title>Страница не найдена | OPTISPORT</title>`.

**Главная правка (протухший кэш) проверена вживую, а не только юнит-тестом.** Прогрев кэша → `stop backend` → ожидание 320 с (TTL 5 мин) → запрос:

```
warm      /aaa    -> 404   (свежий кэш, backend жив)
stale     /aaa    -> 200   (протухший кэш + мёртвый backend: fail-open вместо ложного 404)
stale     /oferta -> 200
recovered /aaa    -> 404   (после start backend + restart nginx)
recovered /oferta -> 200
```

В логах контейнера при этом:

```
[middleware] Не удалось получить список CMS-слагов: TimeoutError: The operation was aborted due to timeout
[middleware] Проверка адреса /aaa пропущена: список слагов недоступен
```

До правки шаг `stale /aaa` дал бы **404** — ложный, из устаревшего списка.

**Наблюдение вне объёма находок (код не менялся).** При недоступном backend каждый запрос к неизвестному адресу платит 2 с таймаута. Так было и раньше для холодного кэша; правка Finding 2 распространила это на протухший. Лечится паузой-backoff после неудачи (в течение неё сразу возвращать `null`), но это код вне задач стори — вынесено на решение владельца.

---

## Раунд 3 — устранение находок повторного ревью (2026-08-24)

✅ **Resolved review finding [Critical]: внутренний HTTP-запрос не работал при штатном `SECURE_SSL_REDIRECT=True`.** Django на проде редиректил `http://backend:8000/api/v1/pages/` на `https://backend:8000/...`, где TLS нет: запрос из middleware падал бы по таймауту, и стори тихо выродилась бы в вечный fail-open — 404 не вернулся бы на проде **никогда**, а в логах остались бы только `warn`. Доверенный признак протокола Django берёт из `SECURE_PROXY_SSL_HEADER` (`HTTP_X_FORWARDED_PROTO`), поэтому запрос из middleware теперь идёт с заголовком `X-Forwarded-Proto: https` — ровно так же, как его ставит nginx. Модель доверия не меняется: заголовок отправляет контейнер внутри той же Docker-сети, что и nginx, снаружи он не подделывается. Дополнительно у запроса стоит `redirect: 'manual'` и отдельная ветка логирования редиректа: если конфигурация протокола когда-нибудь снова разъедется, в логе будет внятная причина, а не молчаливый двухсекундный таймаут. `SECURE_SSL_REDIRECT` и настройки прода не трогались.

✅ **Resolved review finding [High]: поздний writer холодного кэша воскрешал устаревший список на 24 часа.** Между `cache.get` (промах) и `cache.set` во view укладывается публикация страницы: сигнал удалял ключ, а начавший раньше запрос дописывал в него список **без** новой страницы — и она отдавала ложный 404 сутки. Удаления ключа для этой гонки принципиально недостаточно, поэтому кэш **версионирован**: ключ данных теперь `pages_list_serialized_v{N}`, а инвалидация увеличивает счётчик `pages_list_version` (`bump_pages_list_version`). Поздняя запись ложится под старый ключ, который уже никто не читает, и истекает по своему TTL. Счётчик хранится без срока жизни (`timeout=None`) — он обязан пережить данные, которые версионирует; создаётся через `cache.add`, чтобы не затирать значение, поднятое параллельным процессом.

**Что это означает при выкате.** Ключ данных сменил имя ещё раз (`pages_list_serialized` → `pages_list_serialized_v{N}`), поэтому первый запрос после деплоя видит промах и пересобирает список — это одна лишняя сериализация трёх CMS-страниц, не операция. Осиротевшее значение под старым именем никто не читает, и оно истекает по собственному TTL в течение суток; чистить Redis руками не нужно. Счётчик `pages_list_version` создаётся сам при первом обращении.

✅ **Resolved review finding [Medium]: пауза-backoff после быстрого отказа API.** Реализовано ровно по решению владельца: после сетевого отказа, таймаута, HTTP ≥ 400 или неразобранного ответа middleware 30 секунд (`SLUGS_FAILURE_BACKOFF_MS`) не создаёт новых запросов к API — `refreshSlugCache()` сразу возвращает `null`, то есть «не знаю» → fail-open по AC7. Single-flight остаётся защитой параллельных запросов и работает поверх паузы. Успешный ответ паузу снимает. Тридцать секунд выбраны сознательно короче TTL кэша: поднявшийся backend возвращает настоящие 404 почти сразу.

✅ **Resolved review finding [Medium]: ответ без числового `count` и явного признака завершённой пагинации принимался за полный allowlist.** Теперь `fetchPublishedSlugs()` требует обоих признаков DRF: ключ `next` обязан присутствовать и быть пустым, `count` — быть числом и совпадать с числом полученных записей. Любое расхождение → `console.warn` + `null` → fail-open. Ответ неизвестной формы больше не может стать авторитетным списком и превратить реальные CMS-страницы в 404.

✅ **Resolved review finding [Medium]: первый запрос с `ordering` отравлял общий кэш своим порядком.** `PageViewSet.list()` обслуживает из общего кэша только запросы, параметры которых не меняют ни состав, ни порядок выдачи (`page`, `page_size`, `format` — константа `CACHE_NEUTRAL_QUERY_PARAMS`). Запрос с `ordering`, `search` или фильтром идёт обычным путём DRF (`super().list()`) и общий ключ не наполняет. Сам кэш строится от `get_queryset()`, а не `filter_queryset()`, — в нём лежит канонический порядок `Page.Meta.ordering`.

✅ **Resolved review finding [Medium]: тест-страж не видел маршрут с `page.tsx` в группе после статического сегмента.** `app/oferta/(blue)/page.tsx` даёт URL `/oferta`, но сборщик проверял только `oferta/page.tsx` — такая страница молча начинала бы отдавать 404, то есть страж не защищал ровно от того, ради чего написан. Добавлен `hasOwnPage()`: он спускается через любое число вложенных групп и распознаёт все варианты имени файла страницы (`page.tsx|ts|jsx|js|mdx`). Поведение зафиксировано тремя тестами на временных каталогах-фикстурах.

✅ **Resolved review finding [Medium]: percent-encoded slug сравнивался до декодирования.** В `pathname` кириллический адрес приходит как `/%D0%BE%D1%84%D0%B5%D1%80%D1%82%D0%B0`, а в списке из API лежит обычная строка — опубликованная страница с нелатинским slug получала ложный 404. `getSingleSegment()` декодирует сегмент (`decodeSegment` глотает битую percent-последовательность и возвращает исходную строку) и не вмешивается, если после декодирования в сегменте оказался слэш — такой путь зоной catch-all уже не является.

✅ **Resolved review finding [Medium]: точный `/api` не был исключён matcher-ом.** Шаблон `api/` не покрывает путь `/api` без завершающего слэша: он попадал в middleware и перехватывался логикой 404 раньше, чем срабатывал rewrite `/api/:path*` из `next.config.ts`. В отрицательный lookahead добавлен якорь `api$`. Намерение зафиксировано юнит-тестом, который собирает регулярку из самой константы `config.matcher[0]` и проверяет `/api`, `/api/v1/pages/`, `/robots.txt`, `/_next/static/...`, `/offer` и `/apiary` (последний обязан остаться под действием middleware).

✅ **Resolved review finding [Medium]: AC6 обещал немедленный stale-ответ для любого slug.** Формулировка приведена в соответствие с реализацией раунда 2: несимметричность решения описана явно — положительное принимается по протухшему кэшу (обновление фоном), отрицательное обновления дожидается. Туда же добавлена пауза-backoff.

✅ **Resolved review finding [Medium]: AC11 запрещал backend/OpenAPI-правки.** Граница стори переписана: расширение зафиксировано как решение владельца с причиной (обе находки High лежали в backend — списке слагов, на который опирается middleware), и перечислены конкретные файлы. AC9 дополнен уточнением про `api$`.

✅ **Resolved review finding [Low]: File List не содержал `AGENTS.md` и `CLAUDE.md`.** Оба файла попали в диапазон коммитов стори (`a041e1b0..HEAD`) и внесены в список с пометкой о происхождении правки.

### Живая проверка раунда 3

Статусы после `restart backend frontend` + `restart nginx` (dev-контейнер компилирует middleware на лету, Dockerfile в этом раунде не менялся):

```
=== 404 ===                       === 200 ===
/offer  /terms  /korzina          /oferta  /requisites1  /privacy-policy
/basket /order  /product          /about   /catalog      /home
/aaa                              /login   /coming-soon  /electric-orange
                                  /blog    /news

=== через nginx :80 ===
/offer 404  /terms 404  /foo/bar 404  /profile 307
/oferta 200 /requisites1 200 /about 200 /catalog 200 /robots.txt 200
```

Тело `/offer`: `<title>Страница не найдена | OPTISPORT</title>`, текст «Страница не найдена».

**Точный `/api` (Critical-соседняя находка Medium) проверен вживую:** `http://localhost:3000/api` → **301** (уходит по rewrite к backend), а не 404 от middleware. `GET /api/v1/pages/?page_size=1000` через nginx → `count 3, next null, results 3`.

**Сортировка (Medium) проверена вживую:** `?ordering=-title` → `['requisites1', 'privacy-policy', 'oferta']`, обычный запрос → `['oferta', 'privacy-policy', 'requisites1']`. До правки второй запрос получал бы порядок первого.

**Percent-decoding (Medium) проверено вживую на настоящей CMS-записи.** Временно создана опубликованная страница со слагом `аренда-инвентаря`; запрос `/%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0-%D0%B8%D0%BD%D0%B2%D0%B5%D0%BD%D1%82%D0%B0%D1%80%D1%8F` вернул **200** после истечения TTL кэша слагов (первые четыре попытки — 404 из ещё свежего кэша, это штатное «не позднее TTL» по AC6). Страница удалена, в базе снова три опубликованных слага.

**Пауза-backoff (Medium) проверена вживую по логам.** `stop backend` + `restart frontend` (холодный кэш), затем семь запросов к разным несуществующим адресам подряд:

```
[middleware] Не удалось получить список CMS-слагов: TimeoutError: The operation was aborted due to timeout
[middleware] Проверка адреса /aaa-backoff-2 пропущена: список слагов недоступен
[middleware] Проверка адреса /aaa-backoff-3 пропущена: список слагов недоступен
[middleware] Проверка адреса /aaa-backoff-4 пропущена: список слагов недоступен
[middleware] Не удалось получить список CMS-слагов: TimeoutError: The operation was aborted due to timeout
[middleware] Проверка адреса /aaa-backoff-5 пропущена: список слагов недоступен
[middleware] Проверка адреса /aaa-backoff-6 пропущена: список слагов недоступен
[middleware] Проверка адреса /aaa-backoff-7 пропущена: список слагов недоступен
```

Видно ровно ожидаемое: попытка достучаться до API одна на ~30 секунд, между ними решение принимается мгновенно и без сети, все семь запросов — fail-open (200). До правки каждый из них платил бы свои 2 секунды таймаута и создавал свой запрос. После `start backend` + `restart nginx`: `/offer` → **404**, `/oferta` → 200, `/about` → 200 — восстановление немедленное, пауза короче TTL.

---

## Раунд 4 — устранение последней находки ревью (2026-08-25)

✅ **Resolved review finding [High]: инвалидация кэша выполнялась до commit.** `post_save`/`post_delete` срабатывают **внутри** открытой транзакции, поэтому старый код поднимал версию кэша до фиксации данных. Между этими двумя моментами укладывается параллельный GET: новую страницу он ещё не видит (она не закоммичена), но уже читает **новую** версию ключа, промахивается и записывает туда допубликационный список — на сутки (`PAGES_LIST_CACHE_TTL`). После commit сбрасывать уже нечего: свежий ключ занят устаревшими данными, и middleware отдаёт по новой странице ложный 404 намного дольше собственного TTL в 5 минут. Версионирование ключа (раунд 3) эту гонку не закрывает — оно спасает от позднего writer'а, пишущего под **старый** ключ, а здесь writer пишет под новый.

Теперь `invalidate_page_cache` только регистрирует коллбэк: `transaction.on_commit(lambda: _invalidate_page_cache_now(slug))`. Сам сброс (удаление данных текущей версии, `bump_pages_list_version`, удаление `page_detail_{slug}` и фоновая ревалидация ISR Next.js) вынесен в `_invalidate_page_cache_now` и выполняется после фактического commit; вне транзакции (autocommit) — немедленно, как и раньше. Побочный выигрыш: при **откате** транзакции кэш больше не сбрасывается вовсе — раньше неудавшаяся публикация всё равно обнуляла список и заставляла пересобирать его на ровном месте. Slug захватывается в момент сигнала, а не читается из `instance` внутри коллбэка: к тому времени объект мог быть изменён вызывающим кодом.

**Тесты.** Добавлены два: `test_invalidation_is_deferred_until_commit` (RED до правки — `0 != 1`: воспроизводит ровно окно «сигнал сработал, commit не прошёл», читатель кладёт старый список под текущий ключ) и `test_rollback_does_not_invalidate_cache` (откат не трогает ни версию, ни данные). Четыре существующих теста инвалидации переведены на `self.captureOnCommitCallbacks(execute=True)`: `TestCase` держит тест в транзакции, которая никогда не коммитится, поэтому отложенные коллбэки нужно исполнять явно — это стандартный способ Django и заодно фиксирует в тестах новый контракт «после commit».

**Живая проверка на контейнерах** (`restart backend`, dev-контейнер):

```
версия до: 3 | данные v3 в кэше: True
внутри транзакции -> версия: 3 | данные v3 в кэше: True     <- до правки здесь было бы 4
после commit  -> версия: 4
GET /api/v1/pages/?page_size=1000 -> count 4  ['oferta','privacy-policy','oncommit-check','requisites1']

версия до отката:    4
версия после отката: 4 | страница в базе: False              <- откат кэш не сбрасывает
после удаления тестовой страницы -> версия: 5
GET /api/v1/pages/?page_size=1000 -> count 3  ['oferta','privacy-policy','requisites1']
```

Видимость публикации не пострадала: страница появляется в выдаче сразу после commit, тестовая запись удалена, в базе снова три опубликованных слага.

---

## Раунд 5 — устранение находок повторного ревью (2026-08-25)

✅ **Resolved review finding [Medium]: признак завершённой пагинации принимался слишком мягко.** Проверка была на «истинность» (`if (data.next)`), поэтому `false`, `0` и пустая строка сходили за «страниц больше нет». DRF кладёт в `next` только строку-URL или `null`, так что любое другое значение — ответ неизвестной формы, а принять его за полный список значит сделать частичный allowlist авторитетным и вернуть ложные 404. Теперь принимается только явный `data.next === null`; строка трактуется как «обрезан пагинацией», всё остальное — как «признак неизвестной формы», и оба случая уводят в fail-open с внятной записью в лог. Покрыто тремя кейсами (`false`, `0`, `''`) плюс тестом, что `null` по-прежнему даёт нормальный 404.

✅ **Resolved review finding [Medium]: завершающий слэш в базовом URL API ломал запрос.** Значение вида `http://backend:8000/api/v1/` (легко получить из `.env`) давало путь `.../api/v1//pages/`, которого backend не обслуживает: middleware уходил бы в **постоянный** fail-open — 404 не отдавался бы вообще, и заметить это можно было бы только по логам. `getApiBaseUrl()` теперь срезает хвостовые слэши (`base.replace(/\/+$/, '')`).

✅ **Resolved review finding [Low]: граница TTL считалась свежей.** Возраст кэша сравнивался строго (`> SLUG_CACHE_TTL_MS`), поэтому ровно на границе отрицательное решение (404) ещё принималось по старому списку без обновления — вопреки «не позднее TTL» из AC6. Сравнение стало нестрогим (`>=`); тест на точной границе (фейковые таймеры, ровно 5 минут) требует повторного запроса к API.

✅ **Resolved review finding [Low]: не было доказательства части AC2 про метаданные.** Тест `/oferta` в `middleware.test.ts` подтверждал только то, что middleware пропускает запрос дальше, но не то, что пропущенный запрос получает нормальные метаданные. Добавлен `frontend/src/app/(blue)/[slug]/__tests__/page.test.tsx` (3 теста): опубликованная страница получает ровно результат `buildMetadata` с каноническим `/oferta` и **без** `robots`; без `seo_title` заголовок собирается из названия и `noindex` всё равно не появляется; несуществующая страница остаётся с `robots: { index: false, follow: true }` — страховка на случай fail-open. Сам `(blue)/[slug]/page.tsx` не изменялся (AC11), добавлен только тест рядом с ним.

✅ **Resolved review finding [Low]: Dev Agent Record был неактуален.** `RESULT_PLACEHOLDER` заменён фактическим результатом полного прогона бэкенда раунда 4 (3052 passed, 75 skipped, 35 deselected, 27:48). Утверждение первого раунда «бэкенд не изменялся» помечено как относящееся только к первому раунду и снабжено поправкой: с раунда 2 граница AC11 расширена решением владельца, перечень изменённых backend-файлов — в File List; список неизменяемых файлов соблюдён до конца.

✅ **Resolved review finding [Decision, Medium]: поведение при более чем 1000 опубликованных CMS-страницах.** Решение владельца — **зафиксировать поддерживаемый предел 1000 и сделать деградацию заметной**, а не усложнять путь HTML-ответа обходом всей пагинации. Что сделано:

- `SLUGS_PAGE_SIZE = 1000` в `middleware.ts` описан как поддерживаемый предел числа CMS-страниц, а не только размер страницы выдачи; в комментарии зафиксировано, что значение продублировано в `PagesPagination.max_page_size` и менять его нужно в обоих местах;
- то же зафиксировано с backend-стороны — комментарием у `max_page_size` в `backend/apps/pages/views.py`;
- добавлен порог предупреждения `SLUGS_COUNT_WARN_THRESHOLD` (90 % предела, то есть 900): при приближении к пределу middleware пишет `console.warn` с фактическим количеством и предупреждением, что после превышения список станет неполным и настоящие 404 пропадут. Предупреждение срабатывает **до** поломки — после превышения заметить её можно было бы только по отсутствию 404, а не по ошибке;
- сообщение об обрезанной пагинацией выдаче теперь называет предел и подсказывает выход (облегчённый endpoint слагов либо обход всей пагинации).

Поведение за пределом не изменилось и остаётся корректным по AC7: список считается неполным → fail-open, ложных 404 не появляется. Покрыто тремя тестами: предупреждение на 900 страницах (решение при этом принимается как обычно), отсутствие лишних предупреждений при обычном количестве, fail-open с упоминанием предела на выдаче в 1001 страницу.

**Живая проверка на контейнерах** (`restart frontend`, dev-контейнер компилирует middleware на лету):

```
/offer 404  /terms 404  /korzina 404  /foo/bar 404  /profile 307
/oferta 200 /about 200  /catalog 200  /requisites1 200  /electric-orange 200
```

---

## Раунд 6 — устранение находок независимого ревью (2026-08-25)

✅ **Resolved review finding [High]: build-time `NEXT_PUBLIC_API_URL_INTERNAL` менял источник API всему фронтенду, а не только middleware.** Правка AC10 добавляла переменную в сборку прод-образа, но подстановка на этапе сборки действует не на один edge-бандл: `process.env.NEXT_PUBLIC_*` инлайнится во **весь** код, включая серверные компоненты. До стори в проде эта переменная не задавалась нигде, поэтому `(blue)/[slug]/page.tsx` и `(blue)/privacy-policy/page.tsx` уходили по публичному `NEXT_PUBLIC_API_URL` через nginx — который и ставит `X-Forwarded-Proto`. После правки они получили бы внутренний `http://backend:8000/api/v1` **без** этого заголовка, и при штатном `SECURE_SSL_REDIRECT=True` Django увёл бы их запрос на `https://backend:8000`, где TLS нет: `/oferta` (ссылка в подвале) и `/privacy-policy` остались бы без данных. Заголовок протокола ставит только запрос из middleware (раунд 3) — на серверные компоненты он не распространяется.

Исправлено разделением переменных: в сборку идёт **выделенная** `NEXT_PUBLIC_MIDDLEWARE_API_URL`, которую читает только `getApiBaseUrl()` в middleware. Общий `NEXT_PUBLIC_API_URL_INTERNAL` из `Dockerfile` и `docker/docker-compose.prod.yml` убран, поэтому источник API для всего остального фронтенда вернулся к дособытийному состоянию. В цепочке `getApiBaseUrl()` выделенная переменная стоит первой, `NEXT_PUBLIC_API_URL_INTERNAL` — вторым звеном: в dev-контейнере middleware компилируется на лету и читает её из runtime-окружения (`docker/docker-compose.yml:115`), там ничего менять не пришлось. Правку прикрывает новый тест-страж `frontend/src/__tests__/middleware-build-env.test.ts`: он требует `ARG`/`ENV` выделенной переменной **до** `RUN npm run build` и запрещает `NEXT_PUBLIC_API_URL_INTERNAL` в `Dockerfile` и в `build.args` прод-compose — то есть ловит именно возврат этой находки, а не её симптом.

Нормативный текст приведён в соответствие: AC10 дополнен уточнением раунда 6, Task 4.1/4.2 названы новой переменной.

✅ **Resolved review finding [Medium]: закодированный слэш обходил настоящий 404.** `%2F` разделителем сегментов для Next не является: `/foo%2Fbar` остаётся односегментным путём и попадает в тот же catch-all `(blue)/[slug]`. Введённая в раунде 3 проверка «после декодирования в сегменте оказался слэш → не наша зона» опиралась на неверную посылку и отдавала такие адреса на soft-404 со статусом **200** — ровно то, что стори должна устранять. Теперь декодированный сегмент возвращается всегда и проверяется на общих основаниях; в allowlist он не попадёт никогда, потому что `Page.slug` — это `SlugField`, слэша в нём быть не может. Fail-open при недоступном backend сохраняется: решение по-прежнему принимается через `isPublishedSlug()`. Покрыто тремя кейсами (`/foo%2Fbar`, `/%2F`, `/foo%2f`) плюс тестом, что настоящий многосегментный путь `/foo/bar` middleware не трогает и в сеть не ходит.

✅ **Resolved review finding [Low]: `deferred-work.md` отсутствовал в File List.** Файл действительно изменён в диапазоне стори — в него вынесены две отложенные находки (недоступный Redis при инвалидации кэша Page; префиксная проверка auth-маршрутов). Внесён в раздел «Инфраструктура и документация».

### Живая проверка раунда 6

Dev-контейнер (`restart frontend`; middleware компилируется на лету, `Dockerfile` в dev не участвует), напрямую на `:3000` и через nginx на `:80`:

```
=== 404 ===                              === 200 ===
/foo%2Fbar   /%2F   /foo%2f              /oferta   /about       /catalog
/offer       /terms /foo/bar             /privacy-policy /requisites1
                                         /electric-orange /robots.txt /sitemap.xml

=== через nginx :80 ===
/foo%2Fbar 404  /offer 404  /oferta 200  /about 200
```

Тело `/foo%2Fbar`: `<title>Страница не найдена | OPTISPORT</title>` — то есть настоящий 404 с разметкой, а не пустой ответ. `/oferta` отдаёт `<title>ОФЕРТА И ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ ПЛАТФОРМЫ OPTISPORT.RU</title>` — ссылка в подвале жива. Предупреждений `[middleware]` в логах фронта нет: список слагов получен, то есть цепочка `getApiBaseUrl()` в dev работает через `NEXT_PUBLIC_API_URL_INTERNAL` из runtime-окружения.

**Что проверить на проде после выката.** Находка [High] воспроизводится только в собранном прод-образе, поэтому после `up -d --build frontend` на сервере обязательны две проверки: `/oferta` и `/privacy-policy` отдают 200 **с содержимым страницы** (а не пустой каркас), и `/offer` отдаёт 404. Первая доказывает, что серверные компоненты остались на прежнем источнике API, вторая — что middleware получил внутренний адрес из выделенной переменной.

**Тесты и гейты раунда 6.** `npx vitest run` — 148 файлов, 2524 passed, 16 skipped, регрессий нет (было 2478 passed до раунда 5 включительно + новые тесты). `npm run lint` (`eslint . --max-warnings=0`) — чисто, `npx prettier --check` по изменённым файлам — чисто.

### Change Log

| Дата | Изменение |
|---|---|
| 2026-08-24 | Реализована стори 41.0: настоящий HTTP 404 для несуществующих адресов верхнего уровня (middleware + кэш CMS-слагов + fail-open), `ARG NEXT_PUBLIC_API_URL_INTERNAL` в сборку фронта, тест-страж списка маршрутов. Статус → review |
| 2026-08-24 | Устранены находки code review — 4 пункта (2 High, 1 Medium, 1 Low): backend-кэш списка страниц перестроен на полный список + локальная пагинация, отрицательное решение о 404 больше не принимается по протухшему кэшу, неполный/невалидный ответ API уводит в fail-open, добавлен тест single-flight. Попутно починен `?page_size` на `/pages/` (`PagesPagination`), синхронизированы `openapi.yaml` и `api.generated.ts` |
| 2026-08-24 | Устранены находки повторного (третьего) ревью — 11 пунктов (1 Critical, 1 High, 8 Medium, 1 Low): внутренний запрос помечается `X-Forwarded-Proto: https` (иначе `SECURE_SSL_REDIRECT` уводил его в несуществующий TLS), кэш списка страниц версионирован (поздний writer больше не воскрешает устаревший список), добавлена пауза-backoff 30 с после отказа API, ужесточена проверка полноты ответа, percent-encoded слаги декодируются, точный `/api` исключён из matcher, тест-страж видит группы внутри сегмента; нормативные AC6/AC9/AC11 приведены в соответствие с реализацией, File List дополнен |
| 2026-08-25 | Устранена находка ревью [High]: инвалидация кэша страниц переведена на `transaction.on_commit` — сигнал больше не сбрасывает кэш до commit, поэтому параллельный GET не может закэшировать допубликационный список на сутки. Существующие тесты инвалидации переведены на `captureOnCommitCallbacks` |
| 2026-08-25 | Устранены находки раунда 5 — 5 пунктов (2 Medium, 3 Low): признак `next` принимается только как явный `null`, базовый URL API нормализуется от завершающего слэша, граница TTL считается протухшей, добавлен тест метаданных CMS-страницы (AC2), актуализирован Dev Agent Record. По решению владельца закрыта находка [Decision]: предел 1000 CMS-страниц зафиксирован явно с обеих сторон и снабжён предупреждением при приближении |
| 2026-08-25 | Устранены находки раунда 6 — 3 пункта (1 High, 1 Medium, 1 Low): адрес API для middleware доставляется в сборку выделенной переменной `NEXT_PUBLIC_MIDDLEWARE_API_URL` (общее имя переключало на внутренний HTTP-адрес и серверные компоненты CMS-страниц, у которых нет `X-Forwarded-Proto`), закодированный слэш больше не обходит настоящий 404, File List дополнен `deferred-work.md`. Добавлен тест-страж переменных сборки |

### File List

**Фронтенд**

- `frontend/src/middleware.ts` — изменён: список известных маршрутов, кэш слагов, ветка 404, функция стала async; **раунд 2** — `isPublishedSlug()`/`readSlugCache()` вместо `getPublishedSlugs()` (асимметрия положительного и отрицательного решения), проверка полноты и валидности ответа API; **раунд 3** — заголовок `X-Forwarded-Proto` и `redirect: 'manual'` у запроса к API, пауза-backoff `SLUGS_FAILURE_BACKOFF_MS`, обязательные `count`/`next` в ответе, `decodeSegment()` для percent-encoded слагов, якорь `api$` в matcher; **раунд 5** — строгий `data.next === null`, нормализация завершающего слэша в `getApiBaseUrl()`, нестрогая граница TTL в `readSlugCache()`, поддерживаемый предел числа CMS-страниц и порог предупреждения `SLUGS_COUNT_WARN_THRESHOLD`; **раунд 6** — выделенная переменная сборки `NEXT_PUBLIC_MIDDLEWARE_API_URL` первым звеном `getApiBaseUrl()`, закодированный слэш больше не выводит путь из зоны проверки (`getSingleSegment()`)
- `frontend/src/__tests__/middleware.test.ts` — изменён: async-вызовы, мок `NextResponse.rewrite` и `fetch`, изоляция модульного состояния, 21 новый тест; **раунд 2** — ещё 8 тестов (протухший кэш, неполный/невалидный ответ, single-flight на параллельных cold miss'ах); **раунд 3** — ещё 10 тестов (пауза-backoff, заголовок протокола, отсутствующие `count`/`next`, percent-encoding, matcher); **раунд 5** — ещё 5 тестов (три формы невалидного `next`, завершающий слэш базового URL, точная граница TTL) и ещё 3 теста на поддерживаемый предел числа CMS-страниц; **раунд 6** — ещё 7 тестов (четыре на закодированный слэш и настоящий многосегментный путь, три на источник адреса API)
- `frontend/src/__tests__/app-routes-allowlist.test.ts` — добавлен: тест-страж соответствия списка маршрутов структуре `src/app`; **раунд 3** — `hasOwnPage()` раскрывает группы внутри сегмента, три теста на временных фикстурах
- `frontend/src/app/(blue)/[slug]/__tests__/page.test.tsx` — **добавлен (раунд 5)**: доказательство части AC2 — метаданные опубликованной CMS-страницы собираются `buildMetadata` без `noindex`, ветка «страницы нет» остаётся закрытой от индексации
- `frontend/src/__tests__/middleware-build-env.test.ts` — **добавлен (раунд 6)**: тест-страж переменных сборки — выделенная переменная объявлена до `npm run build`, а общий `NEXT_PUBLIC_API_URL_INTERNAL` в `Dockerfile` и `build.args` прод-compose запрещён
- `frontend/src/types/api.generated.ts` — **изменён (раунд 2)**: регенерирован из openapi (`npm run generate:types`)

**Бэкенд**

- `backend/apps/pages/cache_keys.py` — **добавлен (раунд 2)**: общий ключ и TTL кэша списка страниц для view и сигнала; **раунд 3** — версионирование ключа (`get_pages_list_version`, `pages_list_cache_key`, `bump_pages_list_version`)
- `backend/apps/pages/views.py` — **изменён (раунд 2)**: `PagesPagination` с `page_size_query_param`, кэширование полного списка + локальная пагинация; **раунд 3** — версионированный ключ и обход кэша для запросов с `ordering`/`search`/фильтрами (`CACHE_NEUTRAL_QUERY_PARAMS`); **раунд 5** — комментарий, фиксирующий `max_page_size = 1000` как поддерживаемый предел числа CMS-страниц
- `backend/apps/pages/signals.py` — **изменён (раунд 2)**: инвалидация по общему ключу из `cache_keys`; **раунд 3** — инвалидация переводом кэша на новую версию; **раунд 4** — сброс отложен до commit через `transaction.on_commit`, вынесен в `_invalidate_page_cache_now`
- `backend/tests/integration/test_pages_api.py` — **изменён (раунд 2)**: класс `PagesListCachePaginationTest` (5 тестов); **раунд 3** — класс `PagesListCacheConsistencyTest` (4 теста: поздний writer, варианты `ordering`, отравление общего кэша сортировкой и поиском); **раунд 4** — 2 теста на отложенную инвалидацию (commit и откат), четыре существующих переведены на `captureOnCommitCallbacks`
- `docs/api/openapi.yaml` — **изменён (раунд 2)**: параметр `page_size` у `GET /pages/`

**Инфраструктура и документация**

- `frontend/Dockerfile` — изменён: `ARG`/`ENV NEXT_PUBLIC_MIDDLEWARE_API_URL` до `npm run build`; **раунд 6** — переменная переименована из общей `NEXT_PUBLIC_API_URL_INTERNAL` в выделенную, чтобы сборка не переключала на внутренний HTTP-адрес серверные компоненты CMS-страниц
- `docker/docker-compose.prod.yml` — изменён: `NEXT_PUBLIC_MIDDLEWARE_API_URL` в `build.args` сервиса `frontend` (**раунд 6** — вместо общей `NEXT_PUBLIC_API_URL_INTERNAL`)
- `AGENTS.md`, `CLAUDE.md` — изменены: автогенерируемый блок GitNexus между маркерами `<!-- gitnexus:start -->` обновлён счётчиками символов при `npx gitnexus analyze`, который выполнялся по требованию стори. Содержательных правил не меняли; файлы попали в диапазон коммитов стори и внесены сюда по находке ревью [Low]
- `_bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md` — изменён: чекбоксы задач и находок ревью, Dev Agent Record, статус; **раунд 3** — нормативные AC6/AC9/AC11 приведены в соответствие с реализацией
- `_bmad-output/implementation-artifacts/deferred-work.md` — изменён: вынесены две отложенные находки ревью — недоступный Redis при инвалидации кэша `Page` и префиксная проверка auth-маршрутов (обе pre-existing). Внесён сюда по находке ревью [Low] раунда 6
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — изменён: статус стори `ready-for-dev` → `in-progress` → `review`
