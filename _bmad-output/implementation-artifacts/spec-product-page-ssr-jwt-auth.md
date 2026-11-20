---
title: 'Страница товара: цена роли по JWT, а не по сессии Django'
type: 'bugfix'
created: '2026-11-20'
status: 'draft'
route: 'dispatch'
baseline_commit: '365bc35221c3ec3d37abaac4936892b60fceee4d'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** SSR страницы товара узнаёт пользователя только по cookie `sessionid`. Сессия Django живёт 14 дней с последнего ввода пароля, а JWT продлевается ротацией бесконечно. После истечения сессии страница товара показывает B2B-клиенту розницу, а каталог и корзина — цену роли. Так случилось у ИП Бадальянц (VIP, `id 4630`): сессия истекла 19.11.2026 в 11:43 UTC.

**Approach:** SSR проверяет авторизацию по цепочке «непросроченный `accessToken` как Bearer → `sessionid` → аноним». Если SSR остался анонимным, а у браузера есть cookie `refreshToken`, сервер вместо блока цены отдаёт скелетон. Цену роли клиент получает перезапросом, когда восстановится сессия. Сервер решает о сессии по той же cookie, что и каталог (`catalog/page.tsx`).

## Boundaries & Constraints

**Always:**
- Цену на экране и в JSON-LD по-прежнему считает `getProductDisplayPrice` из ответа backend.
- Решение о скелетоне принимает **сервер** (роль `guest` + cookie `refreshToken`) и передаёт его пропсом `isPricePending`. Скелетон есть уже в SSR-HTML, поэтому розница не появляется ни до гидрации, ни после. Скелетон закрывает **весь блок цены**: сумму, бейдж «Акция», зачёркнутую цену, РРЦ. Кнопка «В корзину» и количество скрыты.
- Скелетон снимается при любом исходе перезапроса: успех, ошибка, отвергнутая сессия, `hasStoredSession()` на клиенте false, потолок 15 с. Без ответа остаются SSR-данные и `console.warn`. Роль берётся из `useAuthStore().user?.role ?? 'guest'`.
- Выбранный вариант после перезапроса ищется по `id` в новых `variants`. Состояние перезапроса сбрасывается при смене `product.slug` или нового `product` из пропсов (`router.refresh`).
- Токен в cookie, который просрочен (поле `exp` из payload без проверки подписи, запас 30 с) или равен `"undefined"`, `"null"` или пустой строке, на backend не отправляется.
- На сервере ответ 401 не запускает refresh-flow в `api-client`.

**Never:**
- Не трогать backend: сессию Django, `SESSION_COOKIE_AGE`, сроки JWT, `login()` в `LoginView`.
- Не слать Bearer и `sessionid` в одном запросе: DRF первым проверяет JWT и на плохой токен отвечает 401.
- Не обходить `productsService` через `fetch`: адаптер `adaptProductToDetail` остаётся единственным.

## I/O & Edge-Case Matrix

| Сценарий | Cookie | SSR | Клиент |
|---|---|---|---|
| Живой JWT | `accessToken` не просрочен | Цена роли и роль по Bearer | Перезапроса нет |
| JWT просрочен, сессия жива | `accessToken` просрочен, `sessionid` есть | Цена роли по `sessionid` (как сейчас) | Перезапроса нет |
| Bearer отвергнут (401) | `accessToken` валиден по `exp`, но в blacklist | Повтор по `sessionid`, если она есть, иначе аноним | По строкам ниже |
| JWT просрочен, сессии нет | `accessToken` просрочен, `refreshToken` есть | Аноним + скелетон | Перезапрос → цена роли; неудача → SSR-данные + `console.warn` |
| Гость | Ничего нет | Розница, скелетона нет | Перезапроса нет |
| Мусор в cookie | `accessToken=undefined` | Как без токена | — |
| Товар не найден | Любые | `notFound()` на 404 | — |

</frozen-after-approval>

## Code Map

- `frontend/src/app/(blue)/product/[slug]/page.tsx:66-97` — `ProductPage`: сейчас `Cookie: sessionid`, а `catch` вызывает `notFound()` на любую ошибку, в том числе 401. GitNexus: у `getUserRole` единственный вызывающий — этот файл, risk LOW.
- `frontend/src/utils/server-auth.ts` `getUserRole` — `/users/profile/` по `sessionid`/`fs_session`; на 401 отдаёт `guest`. Fallback `fs_session` сохранить в цепочке.
- `frontend/src/app/(blue)/catalog/page.tsx:259-260` — образец серверного признака сессии (`refreshToken`).
- `frontend/src/services/productsService.ts:296` `getProductBySlug(slug, headers?)` — переиспользовать; анонимный вызов из `generateMetadata` не трогать.
- `frontend/src/services/api-client.ts:43` (`isServer`), `:147-221` (ветка 401). Мина: `:168` ставит `isRefreshing = true`, а `:170` бросает ReferenceError вне `try`.
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:100-107` `hasStoredSession` — вынести в общий модуль.
- `frontend/src/components/product/ProductPageClient.tsx` — `selectedVariant` в state; JSON-LD.
- `frontend/src/components/product/ProductInfo.tsx:143-200` — блок цены: сумма, бейдж «Акция» (`:147`), зачёркнутая (`:180`), РРЦ (`:186`).
- `frontend/src/components/product/ProductSummary.tsx:364, 410-466` — `ProductInfo` и блок количества и кнопки. `selectedVariant` здесь — memo от `variants`, пересчитается сам.
- `frontend/src/providers/AuthProvider.tsx:113-173` — `restoreSession` до 3 попыток; клиентские запросы ждут `waitForAuthReady`.
- Тесты, которые придётся менять: `product/[slug]/__tests__/page.test.tsx:57, 235`, `page.session.test.tsx:45, 133`, `utils/__tests__/server-auth.test.ts`.

## Tasks & Acceptance

**Execution:**
- [ ] `frontend/src/utils/storedSession.ts` — перенести сюда `hasStoredSession()` из каталога, каталог импортирует его без изменения поведения.
- [ ] `frontend/src/utils/server-auth.ts` — `getServerAuthCandidates()`: упорядоченный список заголовков (Bearer из годного `accessToken`, затем `Cookie: sessionid`/`fs_session`) и флаг `hasRefreshCookie`; `getUserRole(headers)` — роль по выбранному заголовку.
- [ ] `frontend/src/services/api-client.ts` — `!isServer` в условии ветки 401.
- [ ] `frontend/src/app/(blue)/product/[slug]/page.tsx` — перебрать кандидатов: на 401 следующий, в конце аноним. Роль запрашивать с тем заголовком, на котором сработал запрос товара. `isPricePending = role === 'guest' && hasRefreshCookie`. `notFound()` — только на 404 и сбои, не на 401.
- [ ] `frontend/src/components/product/ProductPageClient.tsx` — при `isPricePending` после монтирования проверить `hasStoredSession()`, затем `getProductBySlug(slug)` с потолком 15 с. Снять ожидание в `finally`, подставить product/role, пересобрать `selectedVariant` по `id`. Состояние сбрасывается по новому `product`.
- [ ] `frontend/src/components/product/ProductSummary.tsx`, `ProductInfo.tsx` — проброс `isPricePending`: скелетон блока цены, кнопка и количество скрыты.
- [ ] Тесты: строки матрицы; фильтр мусорного и просроченного токена; скелетон есть в SSR-разметке; снятие при ошибке, logout и таймауте; ветка 401 в `api-client` под `@vitest-environment node` — второй 401 подряд не висит и `/auth/refresh/` не вызывается; обновить перечисленные тесты.

**Acceptance Criteria:**
- Given VIP с непросроченным JWT и без `sessionid`, when он открывает страницу товара, then в серверном HTML VIP-цена, равная `price_snapshot` после добавления в корзину.
- Given VIP с просроченным JWT, без `sessionid` и с `refreshToken`, when страница загружается, then розница не появляется ни в HTML, ни на экране, а после восстановления сессии показана VIP-цена.
- Given гость, when он открывает страницу товара, then HTML и JSON-LD такие же, как до правки.

## Design Notes

Просроченный токен отсекается по `exp`, без запроса к backend: access живёт 1 час, а cookie — 30 дней, так что просроченный Bearer — обычный случай. Без этой проверки каждый такой заход стоил бы лишних 401 и повтора. На валидный по `exp`, но отвергнутый токен остаётся повтор по цепочке.

Вне скоупа (замечено на ревью): `ordersService.server.ts:31-52` шлёт Bearer вместе со всеми cookie; `authService.ts:131-138` после refresh держит старый refresh-токен; неверифицированный B2B видит РРЦ, потому что профиль отдаёт роль как есть.

## Verification

**Commands:**
- `cd frontend && npx vitest run "src/app/(blue)/product" src/utils src/services src/components/product "src/app/(blue)/catalog"` — expected: всё зелёное.
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit` — expected: без ошибок.

**Manual checks:**
- Локально под B2B: удалить `sessionid`, оставить свежий `accessToken` — цена роли сразу. Подставить просроченный `accessToken` — в исходнике страницы скелетон, затем цена роли.

## Implementation Notes

## Spec Change Log

## Review Triage Log

| # | Находка ревью | Вердикт | Что сделано |
|---|---|---|---|
| 1 | Скелетон на клиенте → розница в SSR-HTML или ошибка гидрации | high | Решает сервер по cookie `refreshToken` |
| 2 | Просроченный Bearer ломает живую сессию | high | Фильтр `exp` + цепочка Bearer → sessionid → аноним |
| 3 | Скелетон закрывает только сумму | medium | Весь блок цены |
| 4 | Скелетон может висеть ~40 с и дольше | medium | `finally`, потолок 15 с, роль `user?.role ?? 'guest'` |
| 5 | `"undefined"` в cookie | medium | Фильтр |
| 6 | Тест мины в happy-dom не поймает ветку | low | `@vitest-environment node` |
| 7 | Копия `product` в state после `router.refresh` | low | Сброс по новому `product` |
| 8 | Ломающиеся тесты, `fs_session` | low | Перечислены; `fs_session` сохранён |
| 9 | Номера строк | low | Исправлены |
| 10 | Вне скоупа | — | В Design Notes |
