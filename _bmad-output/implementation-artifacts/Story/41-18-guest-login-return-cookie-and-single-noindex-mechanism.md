---
baseline_commit: c43a6499
---

# Story 41.18: Вход гостя без размножения адресов и один механизм исключения из индекса

Status: review
Baseline Revision: c43a6499

## Story

As a владелец сайта,
I want чтобы служебные страницы входа, корзины и оформления заказа не порождали дублей и противоречивых сигналов индексации,
so that отчёт показывал реальные проблемы, а не одну форму входа под четырьмя адресами.

**Закрывает:** FR-41-34. **Решения владельца:** D3, D4 (Alex, 17.09.2026, `sprint-change-proposal-2026-09-16.md` §4, редакция ревью).
**Порядок эпика:** стори последняя. 41.17, 41.19 и 41.20 уже в `done`, поэтому ребейз на 41.19 не нужен: её правки `middleware.ts` и `robots.ts` уже в `develop`.

## Утверждённые решения (дословно, не пересматривать)

- **D3 — cookie в middleware.** Гость на защищённом маршруте (`/profile*`) получает 307 на `/login` без query-параметров и короткоживущую cookie с точкой возврата. Ссылки шапки и подвала не меняются: подвал — серверный компонент, он не знает состояния входа, и разделить в нём ссылки для гостя и для авторизованного нельзя. Приглашение войти на `/checkout` ведёт на `/login` и пишет цель в ту же cookie. `sessionStorage` отклонён: он теряется при открытии в новой вкладке и не решает проблему подвала. Старые ссылки с `?next=` продолжают работать.
- **D4 — вариант B.** С адресов, закрытых `Disallow`, снимается meta `noindex`: для них единственный механизм — robots.txt. `noindex` на адресах вне `Disallow` сохраняется: 404, `/unsubscribe`, неопубликованные страницы и карточки. Инвариант закрепляется тестом. Поисковики, соблюдающие robots.txt, закрытую страницу не запрашивают и её `noindex` не читают, поэтому для них поведение не меняется.
- **Риск из предложения (§3):** «Регресс возврата после входа хуже любого замечания сканера». Поэтому матрица сценариев из раздела Dev Notes обязательна: гость, авторизованный, прямой заход, старые ссылки `?next=`, новая вкладка, устаревшая cookie.

## Acceptance Criteria

### AC1 — гость на защищённом маршруте

**Given** гость без cookie `refreshToken` запрашивает `/profile` или `/profile/favorites` (ссылка шапки, подвала или закладка)
**When** срабатывает middleware
**Then** ответ — 307 на `/login` без query-параметров
**And** ответ ставит cookie точки возврата. Значение — только путь исходного запроса. Атрибуты: `Path=/login`, `Max-Age=600`, `SameSite=Lax`, `Secure` в production. Значение, которое не прошло `isSafeRedirectUrl`, не записывается

### AC2 — выбор адреса после входа

**Given** гость успешно входит на `/login`
**When** выбирается адрес перехода
**Then** порядок такой: `next`/`redirect` из URL (старые ссылки), затем cookie точки возврата, затем `/`. Каждый кандидат проверяется `isSafeRedirectUrl`
**And** cookie удаляется не позже успешного входа, в том числе когда победил параметр URL. Тот же порядок и то же удаление действуют в ветке middleware для авторизованного пользователя на `/login`
**And** тесты open-redirect из 41.12 проходят без изменения ожиданий
**And** cookie действует только на тот заход на `/login`, к которому привели редирект или клик. Страница входа при открытии переносит её значение в свою память и сразу удаляет cookie. Если гость ушёл со страницы, не войдя, а потом сам открыл `/login`, после входа — переход на `/` (решение Alex 18.09.2026, сценарий S8)

### AC3 — приглашение войти на `/checkout`

**Given** гость видит приглашение войти на `/checkout`
**When** отображается ссылка и гость нажимает на неё
**Then** `href` равен `/login`, а клик записывает `/checkout` в cookie точки возврата с теми же атрибутами
**And** если записи не произошло (ссылку открыли в новой вкладке без клика или cookie недоступны), после входа — переход на `/`

### AC4 — шапка и подвал не меняются

**Given** шапка и подвал для гостя и для авторизованного пользователя
**When** они отображаются
**Then** ссылки `/profile`, `/profile/favorites` и `/login` не изменились, а `Header.tsx` и `Footer.tsx` в диффе стори отсутствуют

### AC5 — инвариант D4

**Given** адреса из `disallow` в `robots.ts` и метаданные страниц
**When** выполняется тест инварианта (D4)
**Then** ни одна страница, путь которой закрыт `Disallow`, не отдаёт meta `noindex` (сейчас это `/cart`, `/checkout`, `/login`, `/search`)
**And** ни один адрес из `sitemap.ts` не закрыт `Disallow`
**And** `noindex` на `not-found.tsx`, на `/unsubscribe` и условный `noindex` динамических страниц сохранены

### AC6 — приёмка на проде (NFR-41-08)

**Given** выкат на прод
**When** `curl -I` без cookie запрашивает `/profile`, а `curl` снимает HTML `/home`, `/checkout`, `/cart`, `/login`
**Then** `/profile` отдаёт 307 с `Location: /login` и `Set-Cookie` точки возврата. В HTML нет `/login?next=` и meta `noindex`. В браузере вход гостя через «Избранное» и через приглашение на `/checkout` возвращает на исходную цель. Результат приложен к стори

## Tasks / Subtasks

- [x] **Task 0 — preflight** (все AC)
  - [x] 0.1 Ветка `feature/41-18-guest-login-return-cookie` от актуального `origin/develop`. Прямые коммиты в `develop` запрещены (branch protection).
  - [x] 0.2 `npx gitnexus status`. Если статус `stale`, проверить `git diff --stat <indexed> HEAD`. Если разница только в артефактах стори, тестах и merge-коммитах, индекс годен. Иначе попросить пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [x] 0.3 `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` для `middleware`, `LoginPageContent`, `CheckoutStateView`, `renderContent`. `LoginForm` не меняется (Task 3.2), но его единственный вызывающий — `LoginPageContent`. Сообщить blast radius пользователю. **`isSafeRedirectUrl` — CRITICAL: не менять, только вызывать.**
  - [x] 0.4 Исходный прогон (в `frontend/`): `npx vitest run src/__tests__/middleware.test.ts "src/app/(blue)/(auth)/login" src/components/auth/__tests__/LoginForm.test.tsx src/components/checkout "src/app/(blue)/checkout" src/app/__tests__ src/utils/__tests__/urlUtils.test.ts`. До правок всё должно быть зелёным; число тестов записать в Debug Log.

- [x] **Task 1 — модуль точки возврата** (AC1–AC3)
  - [x] 1.1 NEW `frontend/src/utils/loginReturn.ts`. Модуль исполняется и в edge-runtime middleware, и в браузере. На уровне модуля нельзя обращаться к `document` и `window`: браузерные функции проверяют `typeof document === 'undefined'` внутри себя. Состав модуля:
    - `LOGIN_RETURN_COOKIE = 'loginReturnTo'` — стиль имени как у `refreshToken`;
    - `LOGIN_RETURN_COOKIE_PATH = '/login'`, `LOGIN_RETURN_COOKIE_MAX_AGE = 600`;
    - `loginReturnCookieOptions()` → `{ path: '/login', maxAge: 600, sameSite: 'lax', secure: process.env.NODE_ENV === 'production', httpOnly: false }`. Одна точка правды для middleware и клиента;
    - `resolvePostLoginTarget(urlCandidate, cookieCandidate): string` — первый из `[urlCandidate, cookieCandidate]`, прошедший `isSafeRedirectUrl`, иначе `'/'`. **`urlCandidate` — это `next || redirect`, а не каждый параметр по отдельности.** Прежняя семантика 41.12 сохраняется: опасный непустой `next` не уступает место `redirect` (строка матрицы B `next=https://evil.com&redirect=/profile` → `/`). Без cookie результат совпадает с нынешним поведением во всех строках матриц 41.12;
    - `writeLoginReturnCookie(path)` — пишет, только если `isSafeRedirectUrl(path)`;
    - `readLoginReturnCookie(): string | null` — парсит `document.cookie`, `decodeURIComponent` в `try/catch`: битое значение даёт `null`, а не исключение;
    - `clearLoginReturnCookie()`.
  - [x] 1.2 Строка cookie на клиенте: `` `${name}=${encodeURIComponent(path)}; Path=/login; Max-Age=600; SameSite=Lax${secure ? '; Secure' : ''}` ``. Удаление на клиенте: **одновременно `Max-Age=0` и `Expires=Thu, 01 Jan 1970 00:00:00 GMT`**, с тем же `Path=/login`. Причина — Dev Notes, «Грабли».
  - [x] 1.3 Юнит-тесты NEW `frontend/src/utils/__tests__/loginReturn.test.ts`:
    - `resolvePostLoginTarget` — все строки матриц A и B из 41.12 при `cookieCandidate = null` дают прежний результат. Добавить строки с cookie: URL безопасен → URL; URL опасен или пуст → cookie; оба опасны → `/`; cookie = `/login` → `/`;
    - запись и чтение cookie на документе `/login`, cookie не видна на `/` (`window.history.pushState({}, '', '/login')` до проверки, возврат на `/` в `afterEach`);
    - небезопасный путь (`//evil.com`, `/login`, `https://evil.com`) не записывается;
    - `clearLoginReturnCookie` убирает cookie полностью: имени нет в `document.cookie`, пустое значение не остаётся;
    - `readLoginReturnCookie` на битом `%E0` возвращает `null`.

- [x] **Task 2 — middleware** (AC1, AC2)
  - [x] 2.1 `frontend/src/middleware.ts:391-402` — ветка гостя. `url.pathname = '/login'`, `url.search = ''`. **Query исходного запроса тоже снимается:** иначе `/profile?x=1` уедет на `/login?x=1`. Далее `const response = NextResponse.redirect(url)`; если `isSafeRedirectUrl(pathname)` и запрос не является prefetch-запросом (2.3), то `response.cookies.set(LOGIN_RETURN_COOKIE, pathname, loginReturnCookieOptions())`. Вернуть `response`. Проверку `pathname !== '/login'` удалить вместе с комментарием: `/login` не защищённый маршрут, ветка на нём не срабатывает.
  - [x] 2.2 `:405-416` — ветка авторизованного на auth-route. Цель — `resolvePostLoginTarget(next || redirect, request.cookies.get(LOGIN_RETURN_COOKIE)?.value ?? null)`. Если cookie была в запросе — `response.cookies.delete({ name: LOGIN_RETURN_COOKIE, path: '/login' })`. **`delete('loginReturnTo')` строкой не годится:** Set-Cookie уйдёт без `Path`, и браузер не удалит cookie с `Path=/login`. Для `/register`, `/password-reset`, `/b2b-register` cookie браузером не отправляется (`Path=/login`), поэтому там порядок сводится к URL → `/`, как и сейчас. Редирект на `/` делать через `new URL('/', request.url)`, а не через `clone()` с сохранением query: сейчас `url.pathname = '/'` оставляет `?next=…` в адресе главной, и это тоже вариант адреса.
  - [x] 2.3 Prefetch-запрос cookie не ставит: заголовок `next-router-prefetch` присутствует или `purpose`/`sec-purpose` содержит `prefetch`. 307 на `/login` такой запрос получает как обычно. Все ссылки `/profile*` в шапке и подвале уже с `prefetch={false}` (`Header.tsx:134,168,255,280,317`, `Footer.tsx:140`), так что это защита на будущее: любая новая `<Link href="/profile…">` без `prefetch={false}` иначе ставила бы гостю cookie без клика, и после обычного «Войти» его уводило бы в кабинет.
  - [x] 2.4 JSDoc файла (`:1-9`) дополнить строкой про точку возврата. Остальное в файле (404, CMS-слаги, matcher, `isAuthRoute` с `startsWith`) **не менять**: префиксная проверка auth-маршрутов — отдельная запись `deferred-work.md:55`.
  - [x] 2.5 `frontend/src/__tests__/middleware.test.ts`:
    - мок `next/server` (`:5-15`): `redirect: vi.fn((...args) => actual.NextResponse.redirect(...args))`. Сейчас `redirect` — голый `vi.fn()` и возвращает `undefined`, поэтому `response.cookies.set` упал бы с `TypeError`. `next` и `rewrite` не трогать;
    - `createRequest` и `authRequest` научить отдавать cookie точки возврата и заголовки (`headers: new Headers(...)`), если middleware читает `request.headers`;
    - тест `:80-92` переписать: `redirectUrl.pathname === '/login'`, `redirectUrl.search === ''`, в ответе `Set-Cookie` с `loginReturnTo=%2Fprofile`, `Path=/login`, `Max-Age=600`, `SameSite=lax`; `Secure` нет при `NODE_ENV=test`. Отдельный тест с `vi.stubEnv('NODE_ENV', 'production')` проверяет наличие `Secure`. Проверка «редирект не ходит в сеть» сохраняется;
    - `it.each(['/profile', '/profile/favorites', '/profile/orders/5'])` — значение cookie равно пути; `/profile?tab=1` → `Location` без query, cookie `/profile`;
    - prefetch-запрос (`next-router-prefetch: 1`) → 307 без `Set-Cookie`;
    - авторизованный на `/login` с cookie `/profile/favorites` и без query → `/profile/favorites`, cookie удаляется с `Path=/login`; с `?next=/cart` и cookie → `/cart`, cookie удаляется; с опасным `next` и cookie → cookie-цель; с cookie `//evil.com` → `/`;
    - **блок «усиленный isSafeRedirectUrl (Story 41.12)» (`:1061-1202`) проходит без изменения ожиданий** (AC2). Меняется только фабрика запроса, если нужна.

- [x] **Task 3 — страница входа забирает cookie при открытии** (AC2, решение S8)
  - [x] 3.1 `frontend/src/app/(blue)/(auth)/login/page.tsx` — в `LoginPageContent` добавить состояние `cookieTarget` (`useState<string | null>(null)`) и эффект: `const value = readLoginReturnCookie(); if (value) { setCookieTarget(value); clearLoginReturnCookie(); }`. **Проверка `if (value)` обязательна.** В dev React StrictMode запускает эффект дважды: второй запуск читает уже пустую cookie и без проверки затёр бы состояние значением `null`. Cookie читается **только в эффекте**, не во время рендера: страница пререндерится на сервере, и `document` там нет.
  - [x] 3.2 Итоговая цель: `const target = resolvePostLoginTarget(urlCandidate, cookieTarget)`, где `urlCandidate = next || redirect` (`:30`). В `<LoginForm redirectUrl={target} />` (`:65`) передать `target`. **`LoginForm.tsx` не менять:** его проверка `isSafeRedirectUrl` (`:62`) повторно пропустит уже проверенную цель, а `LoginForm` уходит из диффа.
  - [x] 3.3 Ветка восстановленной сессии (`:35-40`). Эффект из 3.1 обновит состояние только к следующему рендеру, поэтому здесь cookie читается напрямую: `resolvePostLoginTarget(urlCandidate, cookieTarget ?? readLoginReturnCookie())`, затем `clearLoginReturnCookie()`, затем `router.replace`. Иначе первый запуск эффекта успел бы увести на `/`. Строки 8 и 29 JSDoc дополнить: точка возврата приходит и из cookie, cookie забирается при открытии страницы.
  - [x] 3.4 Последствие, принятое вместе с решением: перезагрузка `/login` после редиректа теряет цель, и после входа будет `/` (S12 в матрице).
  - [x] 3.5 Тесты `login/__tests__/page.test.tsx`:
    - матрицы A и B **без изменения ожиданий** (cookie в них нет). В `beforeEach` — `pushState` на `/login` и очистка cookie, в `afterEach` — очистка;
    - новые строки для обоих режимов (а) и (б): без query и с cookie `/profile/favorites` → `/profile/favorites`; `?next=/cart` и cookie → `/cart`; опасный `next` и cookie `/checkout` → `/checkout`; cookie `//evil.com` → `/`;
    - сразу после рендера страницы (до входа) cookie в `document.cookie` отсутствует;
    - S8: первый рендер забрал cookie, `unmount`, повторный рендер без cookie, вход → `/`;
    - неудачный вход (401), затем успешный в той же сессии страницы → цель из cookie сохранилась;
    - повторный вызов эффекта (StrictMode: рендер в `<React.StrictMode>`) цель не теряет.
  - [x] 3.6 `LoginForm.test.tsx` не меняется и проходит как есть.

- [x] **Task 4 — приглашение на `/checkout`** (AC3)
  - [x] 4.1 `frontend/src/components/checkout/CheckoutStateView.tsx:9-11` — `LOGIN_HREF = '/login'`. Комментарий переписать: адрес один, цель передаётся cookie (D3). `:101-103` — `<Link href="/login" onClick={() => writeLoginReturnCookie('/checkout')} …>`. Файл уже `'use client'`. `prefetch` не трогать: `/login` — публичная страница, cookie ставит клик, а не middleware.
  - [x] 4.2 Средний клик вызывает `auxclick`, а не `click`, поэтому записи нет и после входа гость попадает на `/` — это сценарий AC3 «без клика». `Ctrl`/`Cmd`+клик вызывает `click`, и cookie пишется. Cookie общая для вкладок, так что вход в новой вкладке вернёт на `/checkout` — это допустимо и описано в матрице.
  - [x] 4.3 Тесты: `CheckoutStateView.test.tsx` — ожидание `href` `'/login?next=%2Fcheckout'` → `'/login'`; клик пишет `loginReturnTo=%2Fcheckout` (проверка на документе `/login` или через `vi.spyOn` на `writeLoginReturnCookie`). `checkout/__tests__/page.test.tsx:123-126` → `'/login'`.

- [x] **Task 5 — снять `noindex` с адресов под `Disallow`** (AC5)
  - [x] 5.1 `frontend/src/app/(blue)/cart/page.tsx:16-19` — удалить `robots`.
  - [x] 5.2 `frontend/src/app/(blue)/checkout/page.tsx:12` — удалить `robots: 'noindex, nofollow'`. `checkout/success/[orderId]` robots не задаёт — проверено.
  - [x] 5.3 `frontend/src/app/(blue)/(auth)/login/layout.tsx:13` — удалить `noIndex: true`.
  - [x] 5.4 `frontend/src/app/(blue)/search/page.tsx:34-41` — удалить `noIndex: true` и переписать комментарий.
  - [x] 5.5 В каждом из четырёх файлов оставить русский комментарий по образцу `register/layout.tsx:9-10`: «noindex не ставится: адрес закрыт Disallow в robots.txt, а такие адреса meta noindex не несут (решение D4)». **`buildMetadata`/`utils/seo.ts` не трогать** (HIGH, 17 прямых вызывающих): меняются только аргументы вызова.
  - [x] 5.6 `robots.ts` **не менять**. Снимок в `app/__tests__/robots.test.ts` должен пройти как есть.
  - [x] 5.7 `login/__tests__/layout.test.tsx:48-50` — тест «закрывает страницу от индексации — как /cart и /checkout» заменить на «не задаёт robots: адрес закрыт Disallow (D4)» → `expect(metadata.robots).toBeUndefined()`.

- [x] **Task 6 — тест инварианта D4** (AC5)
  - [x] 6.1 NEW `frontend/src/app/__tests__/robots-noindex-invariant.test.ts`. Предпосылки и защита от ложной зелени:
    - `disallow` читается из `robots()` так же, как в `robots.test.ts`. Тест утверждает, что ни одно правило не содержит `*` и `$`. Тогда семантика `Disallow` — чистый префикс пути, и сравнение `path.startsWith(rule)` корректно. Появится шаблон — тест упадёт и потребует осознанной правки;
    - **(а) скан дерева `src/app`.** Все `page.*` и `layout.*` (кроме `__tests__`). URL-префикс строится так: группы `(x)` прозрачны, сканирование останавливается на первом динамическом сегменте `[x]`. Файл «под Disallow», если его статический префикс начинается с правила `Disallow`. Каталог в корне `[slug]` в выборку не попадает: его путь не определён статически, а условный `noindex` на нём разрешён (AC5, п. 3). В файлах под `Disallow`, после удаления комментариев (`//…`, `/*…*/`), не должно быть `noIndex\s*:\s*true`, `index\s*:\s*false` и строкового литерала с `noindex`. **Комментарии удалять обязательно:** в `register/layout.tsx:9` есть текст «noIndex не ставится», и без удаления тест даст ложное срабатывание. Защита от пустой выборки — утверждение, что в неё попали как минимум `(blue)/cart/page.tsx`, `(blue)/checkout/page.tsx`, `(blue)/(auth)/login/layout.tsx`, `(blue)/search/page.tsx`, `(blue)/profile/layout.tsx`, `(electric)/electric/page.tsx`, `(coming-soon)/coming-soon/page.tsx`. Приём обхода — как в `src/__tests__/app-routes-allowlist.test.ts`;
    - **(б) импорт метаданных четырёх страниц из AC:** `metadata.robots` — `undefined` у `cart/page`, `checkout/page`, `login/layout`; у `search/page` — `(await generateMetadata({ searchParams: Promise.resolve({ q: 'мяч' }) })).robots` — `undefined`. Тяжёлые клиентские импорты замокать (`vi.mock('@/components/cart', …)`, `vi.mock('../(blue)/checkout/CheckoutPageClient', …)`, `SearchPageClient`), как в соседних тестах страниц;
    - **(в) sitemap:** замокать `fetch` по образцу `app/__tests__/sitemap.test.ts`, вернуть по одному элементу каждого типа (товар, статья, новость, CMS `oferta`, категория). Ни один `pathname` из результата не начинается с правила `Disallow`. Отдельно — статические маршруты при недоступном API;
    - **(г) сохранённые `noindex`:** `not-found.tsx` и `(blue)/unsubscribe/page.tsx` — `metadata.robots` равно `{ index: false, follow: false }`. `product/[slug]`, `blog/[slug]`, `news/[slug]`, `(blue)/[slug]` — в исходнике есть `robots: { index: false, follow: true }`. Поведенческий тест сейчас есть только у `[slug]` (`[slug]/__tests__/page.test.tsx:86`), у остальных трёх — нет, поэтому здесь проверяется исходник. Упоминание в комментарии: «поведение закреплено тестом страницы, здесь — страж от удаления».
  - [x] 6.2 Red-фаза: до Task 5 тест (а) и (б) обязан падать ровно на четырёх файлах. Записать это в Debug Log.

- [x] **Task 7 — комментарии и e2e**
  - [x] 7.1 `frontend/src/app/(blue)/profile/layout.tsx:8` — «на `/login?next=/profile`» → «на `/login` с cookie точки возврата (стори 41.18)».
  - [x] 7.2 `frontend/tests/e2e/profile/edit-profile.spec.ts:34-41` — ожидать `url.pathname === '/login'`, `url.search === ''` и cookie `loginReturnTo` в `context.cookies()` со значением `%2Fprofile` или `/profile` (Playwright отдаёт сырое значение).
  - [x] 7.3 `frontend/tests/e2e/checkout.spec.ts:842-845` → `href` `'/login'`.
  - [x] 7.4 Документация: `grep -rn "login?next" docs --include=*.md` без `docs/archive` на `c43a6499` пуст, править нечего. Повторить grep после правок.

- [ ] **Task 8 — проверки и приёмка**
  - [x] 8.1 В `frontend/`: `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check`. Backend и OpenAPI не меняются. **Не гонять тяжёлые прогоны параллельно** (память проекта).
  - [x] 8.2 AC4: `git diff --stat origin/develop -- frontend/src/components/layout/Header.tsx frontend/src/components/layout/Footer.tsx` пуст.
  - [x] 8.3 Dev-стенд: `docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend`, затем `docker compose … restart nginx` (иначе 502). `curl -sI http://localhost:3000/profile` → 307, `location: /login`, `set-cookie: loginReturnTo=%2Fprofile; Path=/login; Max-Age=600; SameSite=lax` (без `Secure` в dev). `curl -s -A "AuditikBot/1.0"` по `/cart`, `/checkout`, `/login`, `/search` → 0 совпадений `<meta name="robots"`. Для контроля `/unsubscribe` и несуществующий адрес → `noindex` есть.
  - [x] 8.4 **Production-сборка** (`next build` + `next start -p 3100`, прецедент 41.5 и 41.19). Там же проверить `Secure` в `Set-Cookie` и браузерную матрицу из Dev Notes: headless Chromium Playwright, чистый контекст на `http://localhost:3100`; `localhost` — безопасный контекст, `Secure`-cookie принимается. Минимум сценарии S1, S2, S3, S5, S7. Результаты — таблицей в Debug Log.
  - [x] 8.5 `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только `middleware`, `LoginPageContent`, `CheckoutStateView`/`renderContent`, метаданные четырёх страниц, новый модуль `loginReturn`. `isSafeRedirectUrl` в списке изменённых быть не должно.
  - [x] 8.6 Dev Agent Record, File List; `sprint-status.yaml` → `review`.
  - [ ] 8.7 **Внешний шаг (после мёрджа, ручной выкат по SSH):** sync `develop` → `main` через PR (5 обязательных контекстов). На сервере: `git fetch origin main && git reset --hard origin/main`, `docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend`, затем **`restart nginx`**. AC6: `curl -sI https://optisport.ru/profile` и `/profile/favorites` → `location: /login`, `set-cookie: loginReturnTo=…; Path=/login; Max-Age=600; Secure; SameSite=lax`. `curl -s -A "AuditikBot/1.0"` по `/home`, `/checkout`, `/cart`, `/login`, `/search` → нет `<meta name="robots"` и нет `/login?next=`. Браузер без cookie: «Избранное» → вход → `/profile/favorites`; `/checkout` → «Войти» → вход → `/checkout` (нужен тестовый аккаунт владельца). Снимок положить в стори в формате раздела «Снимок прода до правки». Повторный прогон сканера — шаг владельца.

## Dev Notes

### Текущее состояние (код `c43a6499`)

- **`frontend/src/middleware.ts`**
  - `isProtectedRoute` (`:366-369`) — `startsWith` по `/profile`, `/orders`, `/b2b-dashboard`.
  - Ветка гостя (`:391-402`): `clone()` + `searchParams.set('next', pathname)` → `NextResponse.redirect` (307).
  - Ветка авторизованного на auth-route (`:405-416`): `next || redirect` → `isSafeRedirectUrl` → редирект на цель, иначе на `/`, **сохраняя исходную query** (`url.pathname = '/'` на клоне).
  - Ниже — `/unsubscribe` и механизм 404 (41.0), их не трогать.
  - `KNOWN_TOP_LEVEL_ROUTES` (`:25-46`, 20 маршрутов) уже очищен стори 41.19.
- **`frontend/src/utils/urlUtils.ts`** — `isSafeRedirectUrl` (41.12): отсекает обратный слэш, чужой origin и auth-маршруты (`/login`, `/register`, `/b2b-register`, `/password-reset` и их подпути). Edge-совместим. **CRITICAL в GitNexus — не менять.**
- **`login/page.tsx`** (`'use client'`, Suspense): `redirectUrl = next || redirect` (`:30`); восстановленная сессия → `router.replace` (`:35-40`); `<LoginForm redirectUrl>` (`:65`).
- **`LoginForm.tsx:62`** — `redirectUrl && isSafeRedirectUrl(redirectUrl) ? redirectUrl : '/'` → `router.push`. Единственный потребитель — `login/page.tsx` (проверено cypher).
- **`CheckoutStateView.tsx:11`** — `LOGIN_HREF = '/login?next=%2Fcheckout'` (41.10), ссылка в ветке `anonymous` (`:101-103`).
- **Meta robots под `Disallow`**: `cart/page.tsx:16-19` (`index: false, follow: true`), `checkout/page.tsx:12` (строка), `login/layout.tsx:13` (`noIndex: true`), `search/page.tsx:40` (`noIndex: true`). У остальных страниц под `Disallow` robots нет: `profile/**`, `electric/**`, `coming-soon`, `password-reset/**`, `portal-link/**`, `register`, `b2b-register`, `checkout/success/**`. Проверено grep.
- **Вне `Disallow`, сохраняется:** `not-found.tsx:8`, `unsubscribe/page.tsx:10`, `product/[slug]:50`, `blog/[slug]:44`, `news/[slug]:44`, `[slug]:66`.
- **Корневой `app/layout.tsx`** robots не задаёт. После снятия у четырёх страниц `<meta name="robots">` в HTML не будет вообще — это и требуется.
- **`robots.ts`** — одно правило `*`, 13 префиксов `disallow`, без `*` и `$`. Снимок — `app/__tests__/robots.test.ts`.
- **Cookie на сайте:** `refreshToken` (Path=/, клиентская, `authStore.ts:20`); согласие на cookie хранится в `localStorage`. Баннер (`CookieConsentBanner.tsx:46`) говорит: «Технически необходимые нужны для работы сайта». Cookie точки возврата — технически необходимая, ПДн не содержит, согласия не требует.
- **Вне объёма, не трогать:** `services/api.ts:102` (`window.location.href = '/login'` при провале refresh — возврата нет, как и было); `isAuthRoute` с `startsWith` (`deferred-work.md:55`); страницы регистрации с `next`/`redirect` (`register/page.tsx:25`, `b2b-register/page.tsx:20`) — cookie с `Path=/login` им не отправляется.

### Снимок прода до правки (18.09.2026, `curl` без cookie)

| Запрос | Результат |
|---|---|
| `curl -sI /profile` | `307`, `location: /login?next=%2Fprofile`, `Set-Cookie` нет |
| `curl -sI /profile/favorites` | `307`, `location: /login?next=%2Fprofile%2Ffavorites` |
| `/checkout` (`-A AuditikBot/1.0`) | `<meta name="robots" content="noindex, nofollow"/>` |
| `/cart` | `<meta name="robots" content="noindex, follow"/>` |
| `/login` | `<meta name="robots" content="noindex, nofollow"/>` |
| `/search` | `<meta name="robots" content="noindex, nofollow"/>` |
| `/home` | robots нет, `/login?next=` в серверном HTML нет |

Next отдаёт `Location` относительным (`/login?…`), поэтому после правки ожидается `location: /login`. Приглашение на `/checkout` рендерится на клиенте: в серверном HTML `/checkout` ссылки нет ни до, ни после (урок 41.20). Для AC3 и AC6 доказательство — `href` в DOM браузера, а не `curl`.

### Матрица сценариев (обязательна, риск §3 предложения)

| # | Сценарий | Ожидание |
|---|---|---|
| S1 | Гость → «Избранное» в шапке → вход | `/profile/favorites`; cookie удалена уже при открытии `/login` |
| S2 | Гость → «Личный кабинет» в подвале → вход | `/profile` |
| S3 | Гость на `/checkout` → «Войти» (клик) → вход | `/checkout` |
| S4 | Гость на `/checkout` → «Войти» средней кнопкой (новая вкладка без клика) → вход в новой вкладке | `/` (AC3) |
| S5 | Прямой заход на `/login` без cookie → вход | `/` |
| S6 | Старая ссылка `/login?next=/cart` (cookie `/profile` тоже есть) → вход | `/cart`, cookie удалена |
| S7 | Авторизованный открывает `/login` с cookie `/profile/favorites` | middleware → `/profile/favorites`, cookie удалена |
| S8 | Устаревшая цель: гость открыл `/profile`, попал на `/login`, ушёл, не войдя, и через 5 минут нажал «Войти» в шапке → вход | `/` — cookie забрана первым заходом на `/login` (решение Alex 18.09.2026, AC2) |
| S9 | Cookie отключены | вход → `/` (AC3) |
| S10 | Подменённая cookie `//evil.com` или `/login` | `/` (`isSafeRedirectUrl`) |
| S11 | Неудачный вход (401), затем успешный на той же странице | цель из памяти страницы сохраняется → исходная цель |
| S12 | Перезагрузка `/login` после редиректа → вход | `/` (cookie забрана первым открытием; принятое следствие S8) |

### Грабли (проверено при create-story)

- **Удаление в middleware.** `ResponseCookies.delete('name')` пишет Set-Cookie без `Path` (`next/dist/compiled/@edge-runtime/cookies/index.js:302-305`). Для запроса к `/login` путь по умолчанию — `/`, и cookie с `Path=/login` останется. Только `delete({ name, path: '/login' })`.
- **Кодирование.** `stringifyCookie` делает `encodeURIComponent` значения (`:45`), `parseCookie` — `decodeURIComponent` в `try/catch` и молча пропускает битые значения (`:58-61`). Поэтому `request.cookies.get(...)?.value` уже декодирован, а в заголовке ожидается `loginReturnTo=%2Fprofile`. `SameSite` выводится как передан: `'lax'` → `SameSite=lax` (регистр по RFC 6265 не важен).
- **happy-dom 20.9.0 (Vitest) не удаляет cookie по `Max-Age=0`**: остаётся `a=` с пустым значением. `Expires` в прошлом и `Max-Age=-1` удаляют. Браузеры удаляют по любому из них, поэтому клиентское удаление пишет оба атрибута (Task 1.2). Проверено `node -e` на `happy-dom`.
- **Видимость cookie в тестах.** Cookie с `Path=/login` не видна документу на `/`. Окружение тестов — happy-dom с документом `http://localhost:3000/`. Перед проверками — `window.history.pushState({}, '', '/login')`, после — возврат и очистка, иначе утечёт в соседние тесты.
- **Мок `NextResponse.redirect`** в `middleware.test.ts` возвращает `undefined`, см. Task 2.5.
- **`Secure` и протокол.** Решение принимается по `process.env.NODE_ENV === 'production'`, а не по `request.nextUrl.protocol`: за nginx Next видит `http`, и на проде `Secure` не проставился бы. `NODE_ENV` в edge-бандл и клиентский бандл подставляется на этапе сборки. Dev-контейнер — `development`, без `Secure`. Локальная prod-сборка на `http://localhost` — `Secure` есть, и Chromium её принимает (localhost — безопасный контекст).
- **`HttpOnly` нельзя:** cookie читает клиентская страница входа (`LoginPageContent`). Значение — несекретный путь, при каждом чтении проходит `isSafeRedirectUrl`.
- **Prefetch.** Middleware исполняется и для RSC-prefetch-запросов. См. Task 2.3.
- **Клиентская навигация на `/login`** (клик по `<Link>` в `CheckoutStateView`) идёт RSC-запросом, и middleware его видит. Cookie записана до навигации синхронно, в `onClick`, а `next/link` вызывает пользовательский `onClick` раньше перехода. Страница входа монтируется уже после записи, и её эффект забирает cookie (Task 3.1).
- **Ветка middleware для авторизованного на `/login`** (Task 2.2) читает cookie, только если та ещё не забрана страницей: пользователь с живой `refreshToken` открыл `/login` сразу после редиректа, в другой вкладке. Удалять её там по-прежнему обязательно.

### Архитектура и версии

Next.js 15.5.18 (проверено `node_modules/next/package.json`), React 19.1, TypeScript 5.8, Vitest 4.x на happy-dom 20.9.0, Playwright 1.57. Новых зависимостей нет. Middleware — edge-runtime: только Web API, модуль `loginReturn.ts` обязан быть edge-безопасным, как `urlUtils.ts`. Cookie из middleware ставится через `NextResponse.redirect(...).cookies.set` — штатный API Next 15. Metadata API: у дочернего сегмента без `robots` robots не наследуется, если его нет у родителя; у корневого и `(blue)/layout.tsx` robots нет.

### GitNexus (create-story, индекс `59dce537`, HEAD `c43a6499`, 18.09.2026)

`status` — формально `stale`. `git diff --stat 59dce53 c43a649` — только артефакты стори 41.16/41.20, `sprint-status.yaml` и `backend/apps/common/tests/test_consent_texts.py`. Продакшен-кода в разнице нет, индекс годен.

| Символ | Risk | Прямых | Примечание |
|---|---|---|---|
| `middleware` | LOW | 0 | точка входа фреймворка, исполняется на каждом HTML-запросе — матрица S1–S11 |
| `LoginPageContent` | LOW | 1 (`LoginPage`) | |
| `LoginForm` | ambiguous → LOW | 1 | cypher: единственный внешний вызов — `LoginPageContent` |
| `CheckoutStateView` | LOW | 1 | `CheckoutPageClient` → `CheckoutPage` |
| `renderContent` | LOW | 1 | |
| `isSafeRedirectUrl` | **CRITICAL** | 6 (8 затронутых) | `RegisterPage`, `LoginPage`, `onSubmit` ×2 (Register/B2BRegister), `middleware`… — **не менять**, только вызывать |
| `buildMetadata` | **HIGH** (41.17: 17 прямых) | — | не менять, только убрать аргумент `noIndex` в двух вызовах |
| `generateMetadata` (search) | ambiguous | — | меняется одно поле аргумента |

### Project Structure Notes

- NEW `frontend/src/utils/loginReturn.ts`, `frontend/src/utils/__tests__/loginReturn.test.ts`
- NEW `frontend/src/app/__tests__/robots-noindex-invariant.test.ts`
- UPDATE `frontend/src/middleware.ts` (две auth-ветки и JSDoc)
- UPDATE `frontend/src/app/(blue)/(auth)/login/page.tsx`, `frontend/src/app/(blue)/(auth)/login/layout.tsx`
- UPDATE `frontend/src/components/checkout/CheckoutStateView.tsx`
- UPDATE `frontend/src/app/(blue)/cart/page.tsx`, `frontend/src/app/(blue)/checkout/page.tsx`, `frontend/src/app/(blue)/search/page.tsx`
- UPDATE `frontend/src/app/(blue)/profile/layout.tsx` (комментарий)
- UPDATE тесты: `src/__tests__/middleware.test.ts`, `login/__tests__/page.test.tsx`, `login/__tests__/layout.test.tsx`, `components/checkout/__tests__/CheckoutStateView.test.tsx`, `app/(blue)/checkout/__tests__/page.test.tsx`, e2e `tests/e2e/profile/edit-profile.spec.ts`, `tests/e2e/checkout.spec.ts`
- **НЕ трогать:** `Header.tsx`, `Footer.tsx` (AC4), `LoginForm.tsx` (цель ему передаёт страница, Task 3.2), `robots.ts`, `sitemap.ts`, `utils/urlUtils.ts`, `utils/seo.ts`, `KNOWN_TOP_LEVEL_ROUTES`, страницы регистрации.

### Previous Story Intelligence (41.20, 41.19, 41.12, 41.10)

- **41.19:** прецедент layout-метаданных без robots с комментарием D4 (`register/layout.tsx:9-10`); снимок `robots.test.ts` сделан специально для этой стори. Prod-сборка для проверок (`next build` + `next start -p 3100`). Выкат: PR `develop` → `main`, `reset --hard origin/main`, `up -d --build frontend`, `restart nginx`. `tsc` может упасть на устаревшем `.next/types` — это локальный артефакт.
- **41.20:** клиентские формы в серверном HTML отсутствуют — приёмка браузером; `detect-changes` перед коммитом; итоговый прогон 3318 passed / 16 skipped (ориентир).
- **41.12:** матрицы open-redirect (middleware, страница входа, `LoginForm`) — AC2 требует их неизменности. `/login-foo` — осознанный deferred.
- **41.10:** `LOGIN_HREF` вводился как «тот же вид, что у middleware». Теперь оба источника дают один `/login`.
- **41.17:** метаданные проверять `curl -A "AuditikBot/1.0"` (стриминг метаданных Next 15.2+); после `restart frontend` — `restart nginx`.
- Память проекта: `vi.restoreAllMocks()` не снимает `spyOn` на браузерных API — восстанавливать явно; тяжёлые прогоны не запускать параллельно; прод-деплой только вручную.

### Git Intelligence

`c43a6499` (develop) — merge 41.20: `128bc989` (формулировка согласия), `59dce537`/`6785fd67` (review-фиксы). До этого — 41.19 (PR #197/#198). Файлов этой стори после 41.19 никто не трогал. Конвенция сообщений: `feat(frontend): …`, `test(frontend): …` на русском.

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.18], FR-41-34
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-16.md#3 (риски), #4 (D3, D4), #5.3]
- [Source: _bmad-output/implementation-artifacts/tasks/intent-site-audit-2026-09-16.md] — CC-3, CC-4, таблица noindex
- [Source: _bmad-output/implementation-artifacts/Story/41-19-public-surface-hygiene-demo-routes-register-meta.md] — D4 у регистрации, снимок robots, выкат
- [Source: _bmad-output/implementation-artifacts/Story/41-12-registry-wording-login-notice-breadcrumb.md] — open-redirect
- [Source: _bmad-output/implementation-artifacts/Story/41-10-checkout-and-cart-for-anonymous.md] — приглашение войти
- [Source: _bmad-output/implementation-artifacts/deferred-work.md:55] — `isAuthRoute` вне объёма
- [Source: project-context.md#2, #4, #5, #7]
- `frontend/node_modules/next/dist/compiled/@edge-runtime/cookies/index.js:32-62, 296-306` — формат Set-Cookie и удаление

## Решения по вопросам create-story (Alex, 18.09.2026)

1. **Имя cookie `loginReturnTo`** — утверждено. Владелец добавил его в политику ПДн в админке. Имя не менять: при переименовании придётся править политику.
2. **S8 (устаревшая цель)** — прежнее поведение признано некорректным: после обычного «Войти» гость не должен попадать в кабинет из-за давнего захода на `/profile`. Исправление несложное, поэтому оно внесено в стори, а не в tech-debt: страница входа забирает cookie при открытии (AC2, последний пункт; Task 3). Принятое следствие — S12.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (claude-opus-5), dev-story 18.09.2026.

### Debug Log References

- **0.1** Ветка `feature/41-18-guest-login-return-cookie` от `origin/develop` = `aab02cd8` (пустой merge PR #202 поверх `c43a6499`).
- **0.2** GitNexus `stale` (индекс `59dce53`, HEAD `aab02cd`); разница — артефакты стори, `sprint-status.yaml`, `test_consent_texts.py`. Индекс годен.
- **0.3** impact upstream: `middleware` LOW (0), `LoginPageContent` LOW (1 — `LoginPage`), `CheckoutStateView` LOW (2), `renderContent` LOW (3). `isSafeRedirectUrl` (CRITICAL) не менялся.
- **0.4** Исходный прогон: 19 файлов, 531 passed / 1 skipped.
- **Red-фазы:** `loginReturn.test.ts` — модуль отсутствует; `middleware.test.ts` — 13 падений (все новые ожидания, блок 41.12 зелёный); `login/page.test.tsx` — 11 падений новых тестов; `CheckoutStateView`/`checkout page` — 3 падения.
- **6.2** Red тест инварианта D4 до Task 5: (а) нарушители ровно `(blue)/(auth)/login/layout.tsx`, `(blue)/cart/page.tsx`, `(blue)/checkout/page.tsx`, `(blue)/search/page.tsx`; (б) 4 падения `metadata.robots`. После Task 5 — 17/17.
- **8.1** `npm test`: 193 файла, **3412 passed / 16 skipped**; `npm run lint` — 0; `npx tsc --noEmit` — 0; `npm run format:check` — чисто.
- **8.2** `git diff --stat origin/develop -- Header.tsx Footer.tsx` — пусто. Также пусто по `urlUtils.ts`, `seo.ts`, `robots.ts`, `sitemap.ts`, `LoginForm.tsx`.
- **8.3** Dev-стенд (`up -d --build frontend` + `restart nginx`): `curl -sI :3000/profile` → `307`, `location: /login`, `set-cookie: loginReturnTo=%2Fprofile; Path=/login; Expires=…; Max-Age=600; SameSite=lax` (без `Secure`); `/profile/favorites?tab=1` → `location: /login`, cookie `%2Fprofile%2Ffavorites`. `-A AuditikBot/1.0`: `/cart`, `/checkout`, `/login`, `/search` — meta robots нет; `/unsubscribe` — `noindex, nofollow`; несуществующий адрес — `noindex`. `/home` — 0 вхождений `login?next`.
- **8.4** Production-сборка (`next build` + `next start -p 3100`, backend :8001): `/profile` → `set-cookie: loginReturnTo=%2Fprofile; Path=/login; …; Max-Age=600; Secure; SameSite=lax`; meta robots на четырёх страницах нет, `/unsubscribe` — есть. `/login` в сборке теперь `ƒ` (динамическая).
- **8.4 — найденный дефект.** Первый прогон браузерной матрицы: S3 → `/` вместо `/checkout`, S1 (после исправления селектора) — тоже `/`. Трассировка в Chromium: клик по `<Link>` и редирект middleware на RSC-запрос дают **мягкую навигацию**; `history.pushState('/login')` проходит до эффекта страницы, но `document.cookie` на `/login` **не показывает** cookie с `Path=/login` (cookie при этом в браузере есть и уходит в запросах). Страница не забирала cookie, и после входа — `/`. happy-dom так себя не ведёт, поэтому юнит-тесты были зелёными. Исправление — Completion Notes, п. 3.
- **8.4 — браузерная матрица после исправления** (headless Chromium 1.57, чистый контекст на `http://localhost:3100`, `POST /auth/login/` подменён `page.route`, остальной API — живой backend):

| # | Сценарий | Ожидание | Факт |
|---|---|---|---|
| S1 | «Избранное» в шапке → вход | `/profile/favorites`, cookie удалена при открытии `/login` | PASS, cookie после открытия — нет |
| S2 | «Личный кабинет» в подвале → вход | `/profile` | PASS |
| S3 | `/checkout` → «Войти» (клик) → вход | `/checkout`, `href=/login` | PASS |
| S5 | Прямой заход на `/login` → вход | `/` | PASS |
| S6 | `/login?next=/cart` + cookie `/profile` → вход | `/cart`, cookie удалена | PASS |
| S7 | Авторизованный на `/login` с cookie `/profile/favorites` | 307 → `/profile/favorites`, cookie удалена | PASS |
| S8 | `/profile` → `/login` → ушёл → «Войти» в шапке → вход | `/` | PASS |
| S10 | Подменённая cookie `//evil.com` | `/` | PASS |
| S12 | Перезагрузка `/login` после редиректа → вход | `/` | PASS |

- **8.5** `detect-changes --scope all`: изменены `middleware`, `renderContent`/`LOGIN_HREF`/`CTA_CLASS` (`CheckoutStateView`), `metadata` у `login/layout`, `cart/page`, `checkout/page`, `generateMetadata` у `search/page`, `url` в e2e; `segment`/`isPublished` — сдвиг строк в `middleware.ts`. Risk medium (процессы `GenerateMetadata → …`). `isSafeRedirectUrl` в списке нет. Новые `login/page.tsx`, `LoginPageClient.tsx`, `loginReturn.ts` в индекс не попали — индекс stale.
- **7.4** `grep -rn "login?next" docs --include=*.md` без `docs/archive` — пусто.

### Completion Notes List

1. **Модуль `utils/loginReturn.ts`** (edge-безопасный): имя, путь, срок cookie; `loginReturnCookieOptions()` — одна точка правды для middleware и клиента; `resolvePostLoginTarget(next || redirect, cookie)` без cookie повторяет матрицы A и B 41.12; запись только безопасного пути; удаление с `Max-Age=0` и `Expires` в прошлом.
2. **Middleware:** гость на `/profile*` → 307 `/login` без query (query исходного запроса снимается), cookie ставится, если путь безопасен и запрос не prefetch (`next-router-prefetch`, `purpose`/`sec-purpose`). Авторизованный на auth-route: URL → cookie → `/`, редирект на главную через `new URL('/', request.url)` без исходной query; cookie из запроса удаляется `delete({ name, path: '/login' })`. Мок `NextResponse.redirect` в тесте возвращает настоящий ответ.
3. **Отступление от Task 3.1/3.3 (обязательное, найдено в 8.4).** Стори предполагала чтение cookie из `document.cookie` в эффекте страницы. В Chromium после клиентской навигации (все основные сценарии — S1, S2, S3) cookie с `Path=/login` в `document.cookie` не видна, и возврат ломался. Поэтому `login/page.tsx` стал серверным компонентом: читает `cookies()` из запроса (запрос на `/login` несёт cookie при любой навигации) и передаёт значение пропом `returnCookie` в клиентскую часть. Прежнее содержимое страницы перенесено без изменений разметки в `login/LoginPageClient.tsx` (`git mv`). Клиент запоминает первое значение (`useState(returnCookie)` — память страницы, S11) и при монтировании удаляет cookie (S8); удаление с явным `Path=/login` работает с любого адреса документа, это проверено в браузере. Ref и повторное чтение cookie в ветке восстановленной сессии больше не нужны: цель известна с первого рендера. Следствие: `/login` динамическая (`ƒ`), а не статическая; для страницы входа это приемлемо. Решения D3/D4 и атрибуты cookie из AC1 не менялись. `readLoginReturnCookie` остался в модуле по Task 1.1, в продакшен-коде теперь не вызывается (используется тестами).
4. **Страница входа:** цель `resolvePostLoginTarget(urlCandidate, cookieTarget)` передаётся в `LoginForm`, сам `LoginForm.tsx` не менялся. Тесты страницы рендерят серверный компонент (`await LoginPage()`) с моком `next/headers`, который отдаёт cookie документа на `/login`; матрицы A и B без изменения ожиданий. Добавлены строки с cookie для режимов (а) и (б), удаление при открытии, S8, S11 (401 → успех), StrictMode и тест «документ cookie не видит, значение пришло с сервера». В тесте режима (б) проверяется, что **каждый** `router.replace` ведёт на цель: мок `useRouter` отдаёт новый объект на рендер, и эффект может сработать повторно.
5. **`/checkout`:** `LOGIN_HREF = '/login'`, клик пишет `/checkout` в cookie; `auxclick` (средний клик) не пишет.
6. **D4:** `noindex` снят с `/cart`, `/checkout`, `/login`, `/search` с комментарием по образцу `register/layout.tsx`. `buildMetadata`, `robots.ts` не менялись. Тест инварианта: скан `src/app` (плюс layout-предки адресов под `Disallow`, включая корневой), метаданные четырёх страниц, sitemap по одному элементу каждого типа и при недоступном API, сохранённые `noindex` вне `Disallow`.
7. **E2E (7.2, уточнение):** проверка `context.cookies()` после `goto('/profile')` противоречила бы S8 — страница входа сразу забирает cookie. Поэтому `Set-Cookie` проверяется на 307-ответе из цепочки редиректа, а затем — что в браузере cookie уже нет.
8. **Грабли среды:** правки через Python на Windows дали CRLF в 15 файлах — возвращено в LF до проверки формата. `TaskStop` фонового `next start` не убивает процесс node: порт 3100 держал старый сервер поверх пересобранного `.next`, пришлось останавливать по PID.
9. **Не выполнено:** 8.7 — внешний шаг после мёрджа (PR `develop` → `main`, ручной выкат по SSH, `restart nginx`, приёмка AC6 на `optisport.ru` и снимок в стори).

- 18.09.2026: create-story. Проанализированы эпик, предложение 16.09 (D3, D4, риски) и триаж третьего аудита; код на `c43a6499`; GitNexus impact (`isSafeRedirectUrl` — CRITICAL, не меняется; остальное — LOW). Семантика cookie в Next 15.5.18 сверена по `node_modules`, удаление в happy-dom проверено опытом. Снят прод-снимок до правки. Ultimate context engine analysis completed - comprehensive developer guide created. Код не менялся.

### File List

- `frontend/src/utils/loginReturn.ts` — NEW
- `frontend/src/utils/__tests__/loginReturn.test.ts` — NEW
- `frontend/src/app/__tests__/robots-noindex-invariant.test.ts` — NEW
- `frontend/src/app/(blue)/(auth)/login/page.tsx` — NEW (серверная часть; прежний файл переименован)
- `frontend/src/app/(blue)/(auth)/login/LoginPageClient.tsx` — RENAMED из `page.tsx`, изменён
- `frontend/src/middleware.ts`
- `frontend/src/app/(blue)/(auth)/login/layout.tsx`
- `frontend/src/app/(blue)/cart/page.tsx`
- `frontend/src/app/(blue)/checkout/page.tsx`
- `frontend/src/app/(blue)/search/page.tsx`
- `frontend/src/app/(blue)/profile/layout.tsx`
- `frontend/src/components/checkout/CheckoutStateView.tsx`
- `frontend/src/__tests__/middleware.test.ts`
- `frontend/src/app/(blue)/(auth)/login/__tests__/page.test.tsx`
- `frontend/src/app/(blue)/(auth)/login/__tests__/layout.test.tsx`
- `frontend/src/components/checkout/__tests__/CheckoutStateView.test.tsx`
- `frontend/src/app/(blue)/checkout/__tests__/page.test.tsx`
- `frontend/tests/e2e/profile/edit-profile.spec.ts`
- `frontend/tests/e2e/checkout.spec.ts`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/41-18-guest-login-return-cookie-and-single-noindex-mechanism.md`

### Change Log

- 18.09.2026 — create-story: стори создана, статус ready-for-dev.
- 18.09.2026 — решения Alex: имя cookie `loginReturnTo` утверждено и внесено в политику ПДн; S8 исправляется в объёме стори — cookie забирается при открытии `/login`, `LoginForm.tsx` выведен из диффа.
- 18.09.2026 — dev-story: модуль `loginReturn`, middleware (cookie вместо `?next=`, prefetch-защита, удаление с `Path=/login`), приглашение на `/checkout`, снят `noindex` с четырёх адресов под `Disallow`, тест инварианта D4. В браузерной проверке найден дефект чтения cookie после клиентской навигации; `/login` разделена на серверную часть (читает cookie) и `LoginPageClient`. Матрица S1–S12 (9 сценариев) пройдена в Chromium на prod-сборке. Статус review; 8.7 (выкат и AC6) — после мёрджа.
