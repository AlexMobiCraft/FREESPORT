---
title: 'AuthProvider отдаёт страницу сразу: SSR без спиннера, запросы ждут авторизацию'
type: 'bugfix'
created: '2026-09-24'
status: 'done'
baseline_commit: '15c466d6'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `AuthProvider` возвращает спиннер вместо `children`, пока `isLoading`, а флаг снимается только в `useEffect`. Поэтому сервер отдаёт в `<body>` каждой страницы один спиннер: поисковик без JS не видит ни текста, ни товаров, ни `Product`/`Offer`. Соседний баг: `localStorage` вне try — при заблокированном хранилище `initializeAuth` реджектится и страница висит на спиннере навсегда.

**Approach:** Провайдер всегда рендерит `children` и публикует настоящие `isInitialized`/`isLoading`. Неявная гарантия «к монтированию детей store заполнен» переезжает в `apiClient`: пока идёт восстановление сессии, клиентские запросы ждут его окончания и уходят уже с токеном. Шапка и `/profile/*` сами ждут `isInitialized`. Инициализация всегда завершается, даже при исключении.

## Boundaries & Constraints

**Always:** Первый клиентский рендер совпадает с серверным: `isInitialized=false` на обоих, ветвление по окружению — только в эффектах. Анонимный посетитель без refresh token не ждёт ни одного запроса. Запрос профиля внутри инициализации идёт мимо ожидания. На сервере ожидания нет.

**Ask First:** Правки в `authStore.ts`, `middleware.ts`, серверных fetch'ах страниц. Если в браузере всплывут hydration-ошибки в детях, которые раньше не гидрировались (их чинить — отдельный объём).

**Never:** Не гейтить по одному каждый компонент с запросом (секции главной, каталог, корзина) — это делает ожидание в `apiClient`. Не читать `localStorage`/cookie во время рендера. Не менять логику ретраев и logout при 401/403.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| SSR любой страницы | запрос без JS | в `<body>` содержимое страницы, в шапке нейтральная заглушка вместо кнопок входа | N/A |
| Аноним | нет refresh token | запросы уходят сразу, `isInitialized=true` после первого эффекта | N/A |
| Оптовик на главной | refresh token есть | запросы секций ждут профиль и уходят с `Authorization` — оптовые цены | N/A |
| Сессия истекла | профиль 401/403 | logout, ожидающие запросы уходят анонимно | как сейчас |
| Бэкенд недоступен | профиль падает после ретраев | ожидание снимается, токены сохранены | как сейчас |
| Хранилище заблокировано | `localStorage` бросает | страница работает как для гостя, ожидание снято | исключение ловится, `console.warn` |

</frozen-after-approval>

## Code Map

- `frontend/src/providers/AuthProvider.tsx` -- инициализация сессии, спиннер `:164-173`, `localStorage` без try `:66-73`
- `frontend/src/services/api-client.ts` -- request interceptor `:111-127`, добавляет `Authorization` из store
- `frontend/src/components/layout/Header.tsx` -- кнопки входа по `isAuthenticated && user` `:161`, `:234`
- `frontend/src/app/(blue)/profile/layout.tsx` -- серверный layout `/profile/*`, оборачивает в клиентский `ProfileLayout`
- `frontend/src/app/(blue)/checkout/CheckoutPageClient.tsx` -- единственный потребитель `useAuth().isInitialized`, уже умеет ждать
- `frontend/src/components/home/*Section.tsx`, `CatalogPageClient.tsx`, `components/cart/CartPage.tsx` -- грузят цены/корзину на монтировании: сервер режет оптовые цены по токену (`serializers.py:575`)
- `frontend/src/providers/__tests__/AuthProvider.test.tsx` -- тест `shows loading state during initialization` закрепляет спиннер

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/services/authReadyGate.ts` -- новый модуль: `holdUntilAuthReady()` создаёт ожидающий промис (или переиспользует текущий) и возвращает функцию освобождения; `waitForAuthReady()` отдаёт текущий промис или resolved -- одна точка синхронизации без циклического импорта
- [x] `frontend/src/services/api-client.ts` -- request interceptor в браузере `await waitForAuthReady()` перед чтением токена, кроме запросов с `skipAuthWait: true` (объявить в `declare module 'axios'`) -- запросы детей уходят с токеном
- [x] `frontend/src/providers/AuthProvider.tsx` -- убрать спиннер, всегда рендерить Provider с `children`; запуск инициализации в `useLayoutEffect` (все layout-эффекты коммита идут раньше passive-эффектов детей); при найденном refresh token — `holdUntilAuthReady()`; профиль с `skipAuthWait: true`; чтение/запись `localStorage` в try; тело в try/finally, finally снимает ожидание и выставляет флаги -- SSR с содержимым, без вечного спиннера
- [x] `frontend/src/components/auth/AuthGate.tsx` -- клиентский компонент: до `isInitialized` показывает прежний спиннер, затем `children` -- поведение `/profile/*` не меняется
- [x] `frontend/src/app/(blue)/profile/layout.tsx` -- обернуть содержимое в `AuthGate`
- [x] `frontend/src/components/layout/Header.tsx` -- до `isInitialized` в зонах авторизации (desktop и мобильное меню) нейтральная заглушка того же размера вместо «Войти/Регистрация» -- без мигания кнопок у залогиненного
- [x] тесты: `AuthProvider.test.tsx` (дети рендерятся сразу, `isInitialized` false→true, заблокированный `localStorage`, ожидание снимается при 401 и при исключении), `authReadyGate` + interceptor (запрос ждёт, `skipAuthWait` не ждёт, без hold не ждёт), `Header` (заглушка до инициализации) -- матрица I/O
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- закрыть обе записи (SSR-спиннер и `localStorage`) ссылкой на эту спеку

**Acceptance Criteria:**
- Given production-сборка фронтенда, when `curl` страницы товара, `/home`, `/catalog`, then в `<body>` вне скриптов есть содержимое страницы (название товара, `"@type":"Offer"` на странице товара), а не «Загрузка...».
- Given залогиненный оптовик, when открывает `/home` и `/catalog`, then запросы товаров несут `Authorization` и цены оптовые.
- Given любые страницы `(blue)` и `(electric)`, when открыты в браузере, then в консоли нет hydration-ошибок, вызванных этой правкой.

## Design Notes

Почему ожидание в `apiClient`, а не `isInitialized` в каждом компоненте: цено-зависимые запросы на монтировании есть в пяти секциях, каталоге, корзине и `/profile/*`; любой пропущенный отдаст оптовику розничные цены или устроит второй параллельный refresh (ротация refresh token → logout). Точка в interceptor закрывает всех разом, включая будущих. Цена: до окончания инициализации ждут и публичные запросы — у залогиненного это один запрос профиля, раньше ждала вся страница.

```ts
// interceptor
if (!isServer && !config.skipAuthWait) await waitForAuthReady();
```

Дети раньше не гидрировались (сервер и клиент рендерили спиннер) — теперь гидрируются впервые, отсюда AC про консоль.

## Verification

**Commands:**
- `cd frontend && npx vitest run src/providers src/services src/components/layout src/app` -- expected: зелёные
- `cd frontend && npx tsc --noEmit && npm run lint` -- expected: без ошибок
- `cd frontend && npm run build` -- expected: сборка проходит

**Manual checks:**
- `docker compose` стенд: `curl -s http://localhost/product/<slug>` содержит название в `<body>`; в браузере `/home`, `/catalog`, `/product/<slug>`, `/electric`, `/cart`, `/checkout`, `/profile` без hydration-ошибок; под оптовиком запросы товаров с `Authorization`.

## Suggested Review Order

**Провайдер больше не блокирует рендер**

- Точка входа: дети рендерятся всегда, флаги идут через контекст, спиннера нет.
  [`AuthProvider.tsx:201`](../../frontend/src/providers/AuthProvider.tsx#L201)

- Layout-эффект, а не обычный: удержание встаёт раньше passive-эффектов детей.
  [`AuthProvider.tsx:65`](../../frontend/src/providers/AuthProvider.tsx#L65)

- Удержание ставится только при найденном refresh token, аноним не ждёт.
  [`AuthProvider.tsx:183`](../../frontend/src/providers/AuthProvider.tsx#L183)

- Блок finally всегда снимает удержание и флаги: не будет вечной «Загрузки».
  [`AuthProvider.tsx:189`](../../frontend/src/providers/AuthProvider.tsx#L189)

- Заблокированный localStorage: чтение в try, дальше по cookie или как гость.
  [`AuthProvider.tsx:81`](../../frontend/src/providers/AuthProvider.tsx#L81)

**Запросы ждут восстановления сессии**

- Одна точка в interceptor закрывает все загрузки с ценами и корзиной.
  [`api-client.ts:125`](../../frontend/src/services/api-client.ts#L125)

- Профиль самой инициализации идёт мимо удержания, иначе была бы взаимоблокировка.
  [`AuthProvider.tsx:117`](../../frontend/src/providers/AuthProvider.tsx#L117)

- Счётчик держателей: StrictMode и перемонтирование не отпускают запросы раньше времени.
  [`authReadyGate.ts:24`](../../frontend/src/services/authReadyGate.ts#L24)

**Потребители, которым нужен заполненный store**

- Шапка берёт isInitialized, тот же флаг сервер рендерит в SSR.
  [`Header.tsx:28`](../../frontend/src/components/layout/Header.tsx#L28)

- Кнопки входа невидимы и inert, но держат место: шапка не прыгает.
  [`Header.tsx:190`](../../frontend/src/components/layout/Header.tsx#L190)

- Кабинет сохраняет прежнее поведение: спиннер до восстановления сессии.
  [`layout.tsx:30`](../../frontend/src/app/(blue)/profile/layout.tsx#L30)

- Сам AuthGate: спиннер высотой в полэкрана внутри шапки и футера.
  [`AuthGate.tsx:21`](../../frontend/src/components/auth/AuthGate.tsx#L21)

**Тесты**

- Главный интеграционный: запрос ребёнка уходит после профиля и с новым токеном.
  [`AuthProvider.test.tsx:315`](../../frontend/src/providers/__tests__/AuthProvider.test.tsx#L315)

- Заблокированный localStorage завершается как гость, а не зависанием.
  [`AuthProvider.test.tsx:259`](../../frontend/src/providers/__tests__/AuthProvider.test.tsx#L259)

- Ожидание в interceptor и счётчик держателей.
  [`authReadyGate.test.ts:42`](../../frontend/src/services/__tests__/authReadyGate.test.ts#L42)

- Шапка до и после инициализации.
  [`Header.test.tsx:199`](../../frontend/src/components/layout/__tests__/Header.test.tsx#L199)
