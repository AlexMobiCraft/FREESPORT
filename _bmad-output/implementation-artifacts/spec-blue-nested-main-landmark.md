---
title: 'Один landmark main на страницах темы blue'
type: 'bugfix'
created: '2026-09-12'
status: 'done'
baseline_commit: 'ab276e41'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `LayoutWrapper` темы blue уже оборачивает страницу в `<main>`, а 7 мест рендерят внутри него второй `<main>`: 4 состояния корзины, `/home`, `/profile/*`, `/search`. Вложенный и дублирующийся main нарушает axe-правила `landmark-main-is-top-level` и `landmark-no-duplicate-main`, скринридер видит два «основных содержимых». Изолированные axe-тесты этого не ловят (находка R2 ревью стори 41.10, `deferred-work.md`).

**Approach:** Единственный main страницы — тот, что в `LayoutWrapper`. Внутренние `<main>` заменить: без доступного имени → `<div>`, с именем → `<section aria-label>` с тем же именем. Добавить axe-тест состояний корзины внутри настоящего `LayoutWrapper`.

## Boundaries & Constraints

**Always:** `className`, `data-testid`, `aria-busy` и вёрстка сохраняются, визуально ничего не меняется. Лишний `role="main"` удаляется. Комментарии — на русском.

**Ask First:** любая правка `LayoutWrapper` или визуальное изменение страницы.

**Never:** не трогать `ReturnsAndSupportNotice` (HIGH blast radius), тему `(electric)` и `app/examples` — они вне `LayoutWrapper` blue, их вложенный main идёт в `deferred-work.md`. Не добавлять skip-link и не менять CSS. Не править story-файл 41.10.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Корзина: загрузка, пусто, ошибка, товары | `/cart` внутри `LayoutWrapper` | Ровно один `main` (из layout); axe без landmark-нарушений | N/A |
| Скелетон корзины | `CartSkeleton` | `region` «Загрузка корзины» с `aria-busy="true"`, внутри — регион «Условия возврата и поддержка» | N/A |
| Поиск | `/search?q=…` | `region` «Результаты поиска», собственного `main` нет | N/A |
| Главная, кабинет | `/home`, `/profile/*` | Собственного `main` нет, контент и навигация на месте | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/layout/LayoutWrapper.tsx:36-41` -- единственный main для blue; не меняется
- `frontend/src/components/cart/{EmptyCart,CartError,CartPage}.tsx` -- `<main role="main">` без имени → `div`
- `frontend/src/components/cart/CartSkeleton.tsx:65-102` -- `main` с `aria-label`/`aria-busy` → `section`
- `frontend/src/app/(blue)/search/page.tsx:55` -- `main aria-label="Результаты поиска"` → `section`
- `frontend/src/components/layout/ProfileLayout.tsx:164`, `frontend/src/components/home/HomePage.tsx:48` -- `main` без имени → `div`
- `frontend/src/components/cart/__tests__/*.test.tsx` -- ~11 утверждений `getByRole('main')`
- `frontend/tests/e2e/checkout.spec.ts:470-473` -- `getByRole('main')` на success-странице; её main — из layout, не затрагивается

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/cart/{EmptyCart,CartError,CartPage,CartSkeleton}.tsx` -- заменить внутренний `main` по правилу Approach -- main только в layout
- [x] `frontend/src/app/(blue)/search/page.tsx`, `frontend/src/components/layout/ProfileLayout.tsx`, `frontend/src/components/home/HomePage.tsx` -- то же -- охват всей темы blue
- [x] `frontend/src/components/cart/__tests__/{EmptyCart,CartError,CartPage,CartSkeleton}.test.tsx` -- утверждения про `main` перевести на `data-testid`/`region` и добавить «собственного `main` нет» -- тесты не должны закреплять дефект
- [x] `frontend/src/components/cart/__tests__/accessibility.test.tsx` -- `CartSkeleton` ищется как `region`; новый `describe` рендерит 4 состояния внутри `LayoutWrapper` (`usePathname` → `/cart`): `getAllByRole('main')` длины 1 и axe с `runOnly` по landmark-правилам без нарушений -- находка R2
- [x] `frontend/src/components/home/__tests__/HomePage.test.tsx`, `frontend/src/components/layout/__tests__/ProfileLayout.test.tsx` -- «собственного `main` нет» -- регресс-страж
- [x] `frontend/src/app/(blue)/search/__tests__/page.test.tsx` (новый) -- `render(await SearchPage({ searchParams }))` с замоканным `SearchPageClient`: `main` нет, `region` «Результаты поиска» есть -- страж
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- пункт R2 про вложенный main пометить «ЗАКРЫТО»; добавить пункт про вложенный main в `(electric)` (`layout.tsx:11`, `electric/page.tsx:74`, `electric/catalog/page.tsx:561`) -- учёт вне охвата

**Acceptance Criteria:**
- Given код до фикса, when запускается новый landmark-тест внутри `LayoutWrapper`, then он падает. Мутационная проверка подтверждает, что тест ловит дефект.
- Given `/cart` (пусто и с товаром), `/home`, `/search?q=nike` анонимом, when страница отрендерена в браузере, then `document.querySelectorAll('main').length === 1`. `/profile` требует входа, его закрывает юнит-страж `ProfileLayout`.
- Given правка, when выполнены проверки, then все Vitest-наборы, lint, format и tsc зелёные, число тестов до и после записано.

## Design Notes

Правило выбора элемента: у `div` без роли `aria-label` запрещён (axe `aria-prohibited-attr`), поэтому имя сохраняется только через `section`. Именованный `section` становится `region`, а вложенный `region` внутри `main` допустим. Тег `section` без имени `region` не создаёт и ничего не даёт, поэтому для безымянных контейнеров нужен `div`.

## Verification

**Commands:**
- `cd frontend; npm run test -- --run` -- expected: зелёно, без новых skip
- `cd frontend; npm run lint; npm run format:check; npx tsc --noEmit` -- expected: чисто

**Manual checks (if no CLI):**
- После `restart frontend` + `restart nginx`: временным Playwright-скриптом на `/cart` (пусто и с товаром), `/home`, `/search?q=nike` — ровно один `main`; скрипт удалить

**Результаты (2026-09-12, реализация):**
- Мутация: новый landmark-тест на старом коде падает во всех 4 состояниях корзины. Сначала на `getAllByRole('main')` (2 вместо 1); с отключённым счётчиком — на axe (2–3 нарушения).
- Затрагиваемые наборы (cart, home, layout, `(blue)/home`): до — 35 файлов, 635 passed, 3 skipped. Полный Vitest: до — 171 файл, 2889 passed, 16 skipped (Debug Log 41.10 на `dccc638a`, фронт с тех пор не менялся); после — 172 файла, 2895 passed, 16 skipped (+4 landmark, +1 `/search`, +1 `HomePage`).
- `npm run lint`, `npm run format:check`, `npx tsc --noEmit` — чисто.
- Живой стенд, реальный бэкенд, аноним, `PLAYWRIGHT_BASE_URL=http://localhost:3000`: `/cart` пустая, `/cart` с товаром (гостевая корзина, вариант 56), `/home`, `/search?q=nike` — везде один `main`, 4 passed. Временный спек удалён.
- Ревью (Blind Hunter + Edge Case Hunter): 4 patch применены — стражи `HomePage` и `ProfileLayout` переведены с тега на роль, тест `CartPage` ждёт именно `cart-page`, в `LANDMARK_RULES` добавлены три `*-is-top-level`, уточнена запись electric. 2 defer: `landmark-unique` у навигаций кабинета, общий страж от нового `<main>`. Остальное отклонено, в том числе проверкой axe: `aside` в `main` не нарушает `landmark-complementary-is-top-level`; `div aria-label` с содержимым даёт «incomplete», а не нарушение. После патчей полный Vitest: 172 файла, 2895 passed, 16 skipped; lint, format, tsc — чисто.

## Suggested Review Order

**Единственный main — в layout**

- Точка входа: этот `main` остаётся единственным на любой странице темы blue
  [`LayoutWrapper.tsx:39`](../../frontend/src/components/layout/LayoutWrapper.tsx#L39)

**Замена внутреннего main**

- Контейнер загрузки с именем — `section`: имя и `aria-busy` живут в `region`
  [`CartSkeleton.tsx:68`](../../frontend/src/components/cart/CartSkeleton.tsx#L68)

- Имя «Результаты поиска» сохранено через `section`: у `div` `aria-label` запрещён
  [`search/page.tsx:56`](<../../frontend/src/app/(blue)/search/page.tsx#L56>)

- Безымянные контейнеры корзины — `div`, `className` и `data-testid` прежние
  [`EmptyCart.tsx:22`](../../frontend/src/components/cart/EmptyCart.tsx#L22) · [`CartError.tsx:27`](../../frontend/src/components/cart/CartError.tsx#L27) · [`CartPage.tsx:64`](../../frontend/src/components/cart/CartPage.tsx#L64)

- Контент кабинета и обёртка секций главной — `div` внутри `main` из layout
  [`ProfileLayout.tsx:164`](../../frontend/src/components/layout/ProfileLayout.tsx#L164) · [`HomePage.tsx:49`](../../frontend/src/components/home/HomePage.tsx#L49)

**Страж в настоящем layout**

- Состояния корзины внутри `LayoutWrapper`: один `main` и axe без landmark-нарушений
  [`accessibility.test.tsx:378`](../../frontend/src/components/cart/__tests__/accessibility.test.tsx#L378)

- Только landmark-правила: полный axe упирается в известный heading-order `CartItemCard`
  [`accessibility.test.tsx:381`](../../frontend/src/components/cart/__tests__/accessibility.test.tsx#L381)

- Подменённый `fetchCart` восстанавливается после каждого теста файла
  [`accessibility.test.tsx:145`](../../frontend/src/components/cart/__tests__/accessibility.test.tsx#L145)

**Периферия**

- Стражи «своего `main` нет» — по роли, ловят и `div role="main"`
  [`HomePage.test.tsx:67`](../../frontend/src/components/home/__tests__/HomePage.test.tsx#L67) · [`ProfileLayout.test.tsx:259`](../../frontend/src/components/layout/__tests__/ProfileLayout.test.tsx#L259) · [`CartPage.test.tsx:370`](../../frontend/src/components/cart/__tests__/CartPage.test.tsx#L370)

- Скелетон ищется как именованный регион, поиск — новым тестом страницы
  [`CartSkeleton.test.tsx:70`](../../frontend/src/components/cart/__tests__/CartSkeleton.test.tsx#L70) · [`search/__tests__/page.test.tsx:19`](<../../frontend/src/app/(blue)/search/__tests__/page.test.tsx#L19>)

- Учёт: пункт R2 закрыт, electric и две находки ревью отложены
  [`deferred-work.md:1096`](deferred-work.md#L1096)
