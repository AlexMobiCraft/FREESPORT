---
title: 'Один landmark main на страницах темы electric'
type: 'bugfix'
created: '2026-09-12'
status: 'done'
baseline_commit: 'c6c1bbb6'
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `ElectricLayout` (`(electric)/layout.tsx`) оборачивает страницы в `<main>`, а `/electric` и `/electric/catalog` рендерят внутри него второй `<main>`. Вложенный и дублирующийся main нарушает axe-правила `landmark-main-is-top-level` и `landmark-no-duplicate-main`, скринридер видит два «основных содержимых». Маршруты `/electric*` открываются по прямому адресу при любой теме, а при `ACTIVE_THEME=electric_orange` туда уводит и корень сайта. Пункт отложен спекой `spec-blue-nested-main-landmark.md`.

**Approach:** Единственный main страницы — тот, что в `ElectricLayout`. Внутренние `<main>` обеих страниц имени не имеют и становятся `<div>`. Стражем служит новый тест: обе страницы рендерятся внутри настоящего `ElectricLayout`, проверяется `getAllByRole('main')` длины 1 и axe по landmark-правилам.

## Boundaries & Constraints

**Always:** `className` и вёрстка сохраняются, визуально ничего не меняется. Комментарии — на русском. Набор landmark-правил axe тот же, что в `LANDMARK_RULES` blue (`cart/__tests__/accessibility.test.tsx:381`).

**Ask First:** правка `ElectricLayout`, `LayoutWrapper` или визуальное изменение страницы.

**Never:** не трогать `LayoutWrapper` (его ветка `/electric` на реальных маршрутах не срабатывает — он подключён только в `(blue)`), `app/examples`, `electric-orange-test`, остальные страницы electric (`blog`, `news`, `partners` своего `main` не имеют). Не добавлять имена регионам, skip-link, не менять CSS. Не чинить прочие дефекты electric (`openGraph.url`, overflow) — они в `deferred-work.md` отдельно.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Главная electric | `/electric` внутри `ElectricLayout` | Ровно один `main` (из layout), секции внутри него; axe без landmark-нарушений | N/A |
| Каталог electric | `/electric/catalog` внутри `ElectricLayout`, загрузка завершена | Ровно один `main`; `aside` фильтров и сетка товаров внутри него; axe без landmark-нарушений | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/app/(electric)/layout.tsx:11` -- единственный main electric; не меняется
- `frontend/src/app/(electric)/electric/page.tsx:74,126` -- `main` без имени → `div`
- `frontend/src/app/(electric)/electric/catalog/page.tsx:561,631` -- `main` сетки товаров без имени → `div`
- `frontend/src/app/(electric)/electric/catalog/page.tsx:495,558` -- колонка фильтров `aside`: дерево категорий, панель фильтров, «Сбросить фильтры»; остаётся единственным complementary каталога
- `frontend/src/components/ui/Sidebar/ElectricSidebar.tsx:106` -- корневой `aside` панели фильтров, вложен в колонку → `div`; панель живёт ещё в drawer каталога (внутри `dialog`) и на `electric-orange-test` (в обычном `div`)
- `frontend/src/components/cart/__tests__/accessibility.test.tsx:378-428` -- образец стража в layout и `LANDMARK_RULES`
- `frontend/src/app/(blue)/search/__tests__/page.test.tsx` -- образец теста страницы `app/`
- `frontend/src/components/ui/Toast/ToastProvider.tsx:188` -- `useToast` бросает без `ToastProvider`; каталог его вызывает
- `frontend/src/providers/AuthProvider.tsx:55-94` -- на монтировании ходит в `/users/profile/`; в тесте мокается

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/app/(electric)/electric/page.tsx` -- внешний `<main>` → `<div>` с тем же `className`, комментарий про единственный main в layout -- main только в layout
- [x] `frontend/src/app/(electric)/electric/catalog/page.tsx` -- `<main className="flex-1 min-w-0">` → `<div>`, тот же комментарий; колонка фильтров остаётся `aside` -- то же
- [x] `frontend/src/components/ui/Sidebar/ElectricSidebar.tsx` -- корневой `<aside>` → `<div>` с тем же `className`, комментарий: landmark задаёт место использования -- снять вложенный `aside`, не сужая регион колонки
- [x] `frontend/src/app/(electric)/__tests__/landmarks.test.tsx` (новый) -- рендер `ElectricLayout` с каждой страницей: `ElectricHeader`/`ElectricFooter` → заглушки `<header>`/`<footer>`, `AuthProvider` → passthrough, секции главной → заглушки, `categoriesService.getTree`/`brandsService.getAll`/`productsService.getAll` → пустые ответы, `useSearchParams` → пустые параметры. Для каталога дождаться разрешения промиса `productsService.getAll` и искать узлы после него. Утверждения: `getAllByRole('main')` длины 1; на главной внутри `main` все секции; в каталоге единственный `complementary` — колонка, в ней дерево категорий и панель фильтров; axe с `runOnly` по landmark-правилам без нарушений -- страж
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- пункт «Вложенный `<main>` в теме electric» пометить «ЗАКРЫТО» с датой, веткой и спекой -- учёт

**Acceptance Criteria:**
- Given код до фикса, when запускается новый тест, then он падает на обеих страницах. Мутационная проверка подтверждает, что тест ловит дефект.
- Given локальный стенд, when анонимно открыты `/electric` и `/electric/catalog`, then `document.querySelectorAll('main').length === 1`.
- Given правка, when выполнены проверки, then все Vitest-наборы, lint, format и tsc зелёные, число тестов до и после записано.

## Spec Change Log

- **Итерация 1 (ревью, 2026-09-12).** Находка Blind Hunter и Edge Case Hunter: чтобы снять вложенный `aside` в каталоге, внешний `aside` колонки понизили до `div`, и дерево категорий с кнопкой «Сбросить фильтры» выпали из complementary-региона — остались только бренды и цена. Исправлены Code Map, Tasks и Design Notes: снимается корневой `aside` у `ElectricSidebar`, колонка остаётся `aside`. Избегаемое состояние: complementary каталога покрывает часть фильтров. KEEP: замена `main` → `div` на обеих страницах с комментариями; тест внутри `ElectricLayout` с одним экземпляром `searchParams` через `vi.hoisted`, моками сервисов и категорией «Спорт»; мутационная проверка через `git stash` правок страниц; живая проверка скриптом Playwright через stdin.

## Design Notes

Кроме `main`, в каталоге есть вложенный landmark: колонка фильтров (`catalog/page.tsx:495`) — `aside`, а `ElectricSidebar` внутри неё (`ElectricSidebar.tsx:106`) рендерит свой `aside`. Axe сообщает `landmark-complementary-is-top-level`. Снимается внутренний `aside`, а не внешний: колонка остаётся единственным complementary, и в ней дерево категорий, фильтры и «Сбросить фильтры». Для браузеров семантика не меняется: безымянный `aside` внутри `aside` по HTML-AAM и так generic. В drawer панель живёт внутри `dialog`, отдельный complementary там не нужен. `aside` внутри `main` axe допускает.

## Verification

**Commands:**
- `cd frontend; npm run test -- --run` -- expected: зелёно, без новых skip
- `cd frontend; npm run lint; npm run format:check; npx tsc --noEmit` -- expected: чисто

**Manual checks (if no CLI):**
- После `restart frontend`: временным Playwright-скриптом (`PLAYWRIGHT_BASE_URL=http://localhost:3000`) на `/electric` и `/electric/catalog` — ровно один `main`; скрипт удалить

**Результаты (2026-09-12, реализация после итерации 1):**
- Мутация через `git stash`: при откате всех трёх файлов тест падает на обеих страницах на `getAllByRole('main')` (2 вместо 1); при откате только `ElectricSidebar` каталог падает на двух `complementary`.
- Полный Vitest: до — 172 файла, 2895 passed, 16 skipped; после — 173 файла, 2897 passed, 16 skipped (+2 теста landmarks).
- `npm run lint`, `npm run format:check`, `npx tsc --noEmit` — чисто.
- Живой стенд после `restart frontend` + `restart nginx`, аноним, 1440×900, `http://localhost:3000`: `/electric` — HTTP 200, `main` 1, `aside` 0; `/electric/catalog` — HTTP 200, `main` 1, `aside` 1 (колонка внутри `main`), вложенных `main` и `aside` нет. Скрипт шёл через stdin, файлов не оставил.
- Ревью, раунд 1 (Blind Hunter + Edge Case Hunter): 1 bad_spec — сужение complementary-региона каталога — дало итерацию 1. 2 patch вошли в повторную реализацию: ожидание ответа `getAll` через `act` и проверка всех 9 секций главной. Остальное отклонено: историю моков сбрасывает `vitest.setup.ts:35`, заглушки шапки и подвала повторяют стража blue, настоящие секции главной landmarks не содержат, общий страж уже отложен.
- Ревью, раунд 2: bad_spec и patch нет. 1 defer: общего стража одного `main` нет и для `(electric)`. Остальное отклонено проверкой кода: `ElectricDrawer` — `role="dialog"` с `aria-modal`, тестов и stories у `ElectricSidebar` нет, `main`/`aside` в UI-компонентах есть только у него. `electric-orange-test` теряет `complementary` панели — демо-страница без landmarks, учтено в Code Map.

## Suggested Review Order

**Единственный main — в ElectricLayout**

- Точка входа: этот `main` остаётся единственным на любой странице `/electric*`
  [`layout.tsx:11`](<../../frontend/src/app/(electric)/layout.tsx#L11>)

**Замена внутреннего main**

- Главная: безымянный контейнер секций — `div`, `className` прежний
  [`electric/page.tsx:75`](<../../frontend/src/app/(electric)/electric/page.tsx#L75>)

- Каталог: сетка товаров — `div` внутри `main` из layout
  [`catalog/page.tsx:561`](<../../frontend/src/app/(electric)/electric/catalog/page.tsx#L561>)

**Вложенный aside каталога**

- Колонка фильтров остаётся `aside`: единственный complementary с деревом, фильтрами и сбросом
  [`catalog/page.tsx:495`](<../../frontend/src/app/(electric)/electric/catalog/page.tsx#L495>)

- Общий компонент отдаёт `div`: landmark задаёт место использования; единственная правка вне страниц
  [`ElectricSidebar.tsx:108`](../../frontend/src/components/ui/Sidebar/ElectricSidebar.tsx#L108)

**Страж в настоящем layout**

- Каталог ждёт ответ `getAll`: пустое состояние видно и до запроса
  [`landmarks.test.tsx:137`](<../../frontend/src/app/(electric)/__tests__/landmarks.test.tsx#L137>)

- Единственный complementary — колонка; дерево категорий и фильтры внутри неё
  [`landmarks.test.tsx:146`](<../../frontend/src/app/(electric)/__tests__/landmarks.test.tsx#L146>)

- Главная: все 9 секций внутри одного `main`
  [`landmarks.test.tsx:117`](<../../frontend/src/app/(electric)/__tests__/landmarks.test.tsx#L117>)

- Стабильный `searchParams`: новый объект на каждый рендер зациклил бы загрузку категорий
  [`landmarks.test.tsx:30`](<../../frontend/src/app/(electric)/__tests__/landmarks.test.tsx#L30>)

- Набор landmark-правил тот же, что у стража blue
  [`landmarks.test.tsx:68`](<../../frontend/src/app/(electric)/__tests__/landmarks.test.tsx#L68>)

**Периферия**

- Учёт: пункт electric закрыт, общий страж для electric отложен
  [`deferred-work.md:1106`](deferred-work.md#L1106) · [`deferred-work.md:1098`](deferred-work.md#L1098)
