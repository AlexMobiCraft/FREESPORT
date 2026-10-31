---
title: 'Пагинация плитками по макету и переход к началу страницы'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '6dcdcf50f88f69e1f4a3635d51bb6d0dc9b9d2e3'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Постраничная навигация на сайте выглядит иначе, чем на макете владельца (плитки с заливкой, многоточие, стрелка), а номера в каталоге идут скользящим окном без многоточия. После выбора страницы пользователь остаётся внизу списка: в каталоге, заказах и бонусах прокрутки нет.

**Approach:** Привести общий компонент `Pagination` к макету, перевести на него каталог и добавить переход к началу страницы при выборе страницы. Решения владельца: «10» и «20» на макете — середина и последняя страница; новый вид получают каталог, поиск, заказы и бонусы.

## Boundaries & Constraints

**Always:** Цвета — токены сайта (оранжевый `primary`), а не синий с картинки: активная плитка `bg-primary text-text-inverse`, номера и стрелки `bg-primary-subtle text-primary`, многоточие без плитки. Типографика — `text-sm font-medium` (те же 14/20 px, что `text-body-s`, и шрифт Inter): `twMerge` в `cn()` выбрасывает `text-body-s` рядом с цветом текста. Навигация с клавиатуры, `aria-label`, `aria-current="page"` сохраняются. Адрес страницы (`?page=N`) и SEO-правило «первая страница без параметра» не меняются.

**Never:** Не трогать `ElectricPagination`, страницы `(electric)`, блог и новости. Не менять размер страницы и API. `Pagination` не прокручивает при «Назад/Вперёд» браузера и при смене фильтров; существующую прокрутку при выборе подборки в каталоге не менять.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Начало ряда | 1 из 20; 1 из 138 | `1 2 3 4 5 … 10 20 >`; `1 2 3 4 5 … 69 138 >` | N/A |
| Середина ряда | 70 из 138 | `< 1 … 68 69 70 71 72 … 138 >` | N/A |
| Конец ряда | 138 из 138 | `< 1 … 69 … 134 135 136 137 138` | N/A |
| Мало страниц | Всего не больше 7 | Все номера без многоточия | N/A |
| Пропущена одна страница | 5 из 138 | Вместо многоточия номер: `< 1 2 3 4 5 6 7 … 138 >` | N/A |
| Выбор страницы | Клик по номеру или стрелке | `onPageChange` и плавная прокрутка к верху (`top: 0`, `smooth`) | N/A |
| Клик по текущей | Номер активной страницы | Ни смены страницы, ни прокрутки | N/A |
| Первая страница | `currentPage=1` | Стрелки «назад» нет, как на макете | N/A |
| Последняя страница | `currentPage=totalPages` | Стрелки «вперёд» нет | N/A |
| Одна страница | `totalPages=1` | Пагинация не показывается | N/A |
| Невалидные значения | `currentPage>totalPages`, `totalPages<=0` | Компонент не рендерится, как сейчас | N/A |
| Узкий экран | Ширина 375 px | Плитки переносятся по центру, горизонтальной прокрутки нет | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/ui/Pagination/Pagination.tsx` -- общий компонент; `generatePageNumbers` строит ряд, кнопки держат стили
- `frontend/src/components/ui/Pagination/__tests__/Pagination.test.tsx` -- тесты; проверки disabled-стрелок заменить на отсутствие стрелок
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:70,1501,1509,1881` -- `MAX_VISIBLE_PAGES`, `handlePageChange`, `visiblePages`, своя разметка; `router.push` с `scroll: false`
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx:1036-1395` -- ищут кнопки по имени `'3'`; после перевода имя станет «Страница 3»
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1456` -- прокрутка при выборе подборки; не трогать, её проверяет тест
- `frontend/src/components/business/SearchPageClient/SearchPageClient.tsx:116,119` -- `router.push` со `scroll: true` и свой `scrollTo`; мгновенная прокрутка Next оборвала бы плавную
- `frontend/src/components/business/OrdersList/OrdersList.tsx`, `frontend/src/app/(blue)/profile/bonuses/page.tsx` -- потребители `Pagination`, правок не требуют
- `frontend/src/app/globals.css:15-18` -- токены `primary`, `primary-subtle`

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/ui/Pagination/Pagination.tsx` -- новый ряд номеров, плитки, скрытие стрелок на краях, `flex flex-wrap items-center justify-center gap-2` на `ul`, прокрутка в `handlePageChange` с учётом `prefers-reduced-motion`, перевод фокуса со стрелки на плитку (см. Design Notes) -- прокрутка в одном месте для всех потребителей
- [x] `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` -- заменить свою разметку и `visiblePages` на `Pagination`, удалить `MAX_VISIBLE_PAGES` -- один компонент вместо двух, иначе неиспользуемая константа роняет `--max-warnings=0`
- [x] `frontend/src/components/business/SearchPageClient/SearchPageClient.tsx` -- убрать `window.scrollTo`, в `router.push` поставить `scroll: false` -- иначе две прокрутки и рывок от Next
- [x] Тесты: `frontend/src/components/ui/Pagination/__tests__/Pagination.test.tsx`, `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx`, `frontend/src/components/business/SearchPageClient/__tests__/SearchPageClient.test.tsx` -- обновить под матрицу и новые имена кнопок; проверить класс `text-sm`. Ряд проверять точным составом ячеек: нынешние тесты многоточия ждут только `length > 0` и пройдут на неверном ряду. В тесте поиска вместо `expect.any(Object)` проверить `{ scroll: false }`. Добавить в каталог тест: клик по плитке вызывает `window.scrollTo({ top: 0, behavior: 'smooth' })` один раз. Добавить в `Pagination`: Enter на стрелке перед крайней страницей переводит фокус на плитку цели с `preventScroll: true`, клик мышью фокус не переводит, при `prefers-reduced-motion: reduce` прокрутка идёт с `behavior: 'auto'` -- покрытие матрицы и AC

**Acceptance Criteria:**
- Given каталог из 20 страниц, when открыта первая страница, then ряд — плитки `1 2 3 4 5`, многоточие без плитки, плитки `10 20` и плитка со стрелкой вперёд.
- Given пользователь внизу списка, when выбирает страницу, then страница плавно поднимается к началу и показывает новую выдачу.
- Given каталог на предпоследней странице и фокус на стрелке вперёд, when пользователь нажимает Enter, then фокус стоит на плитке последней страницы, а подъём к началу не обрывается.
- Given в системе включено уменьшение движения, when пользователь выбирает страницу, then подъём к началу идёт без анимации.

## Implementation Notes

## Spec Change Log

## Review Triage Log

Ревью 2026-10-31: Blind Hunter и Edge Case Hunter, 1 круг, loopback не потребовался.

- **patch (2):** `window.matchMedia?.()` в `handlePageChange` (страховка окружений без `matchMedia`); тест фокуса проверяет реальный `document.activeElement` и после перерисовки с `currentPage=20`.
- **reject (решения замороженной части спеки):** скрытие стрелок и сдвиг ряда; многоточие только на первый разрыв начальной ветки; прокрутка в общем компоненте для заказов и бонусов; `Pagination` снимается на время загрузки в поиске; `showFirstLast` без переноса фокуса (не используется).
- **reject (шум):** NaN в `currentPage`, чётные и малые `maxVisiblePages`, `aria-label="Pagination"`, липкий hover, утечка спаев (тот же приём в соседнем тесте каталога), форматирование (`format:check` зелёный), e2e и сторис со старыми именами (в репозитории не найдены).
- **defer:** нет.

## Design Notes

Ряд — множество номеров (`W = maxVisiblePages`, по умолчанию 5; `mid = ceil(N/2)`), разрывы от двух страниц заменяются многоточием: `N ≤ W+2` — все; `c ≤ W-1` — `1..W, mid, N`; `c ≥ N-W+2` — `1, mid, N-W+1..N`; иначе — `1, c-⌊W/2⌋..c+⌊W/2⌋, N`. Разрыв в одну страницу заполняется её номером. Исключение — начальная ветка: многоточие только на первый разрыв, разрыв `mid→N` не помечается, как на макете. Контроль начальной ветки: N=8 `1 2 3 4 5 … 8`; N=11 `1 2 3 4 5 6 … 11`; N=13 `1 2 3 4 5 6 7 … 13`; N=15 `1 2 3 4 5 … 8 15`.

Размер плитки `h-10 min-w-10 sm:min-w-12 px-2`: от `sm` повторяет пропорции макета, трёхзначные номера вмещает за счёт `px-2`. Стрелки и ячейка многоточия того же размера. Узкая ширина на телефоне нужна из-за длины ряда: в нём до 11 ячеек, а поиск на 375 px даёт 327 px. Шесть плиток `min-w-12` занимают 328 px, ряд распался бы на три строки; с `min-w-10` их две. Hover: номера и стрелки `hover:bg-primary hover:text-text-inverse`, активная `hover:bg-primary-hover`. `showFirstLast` в коде не используется: поведение оставляем, стили общие.

Фокус со стрелки. На крайней странице стрелка исчезает, и фокус клавиатуры упал бы на `body`. Поэтому при нажатии стрелки с клавиатуры (`event.detail === 0`), если цель — первая или последняя страница, фокус до `onPageChange` переводится на плитку цели: `event.currentTarget.closest('ul')?.querySelector<HTMLButtonElement>('[data-page="N"]')?.focus({ preventScroll: true })`, для этого у плиток появляется `data-page`. Плитки первой и последней страницы есть в любом ряду и остаются в DOM по ключу `page-N`, поэтому хуки и `'use client'` не нужны. Без `preventScroll` браузер вернёт страницу вниз к плитке и оборвёт подъём. Для мыши фокус не переводим: ring `focus:` появился бы на плитке, по которой не кликали. В поиске, заказах и бонусах `Pagination` снимается на время загрузки, и фокус теряется при любом клике; это старое поведение, здесь не меняем.

Уменьшение движения. Правило `prefers-reduced-motion` в `globals.css` не действует на `window.scrollTo`, поэтому `Pagination` проверяет его сам: `window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'`. Строка матрицы про `smooth` описывает обычный случай; исключение согласовано владельцем 2026-10-31. Прокрутку при выборе подборки в каталоге не трогаем, как и требует Never. Мок `matchMedia` в тестах каталога возвращает `true` только для `(min-width: 1024px)`, поэтому там остаётся `smooth`.

`bg-primary-subtle` + `text-primary` дают контраст ниже AA для мелкого текста (около 2,7:1), но цифры того же цвета уже стоят в текущем `Pagination`, и макет показывает именно такую схему.

## Verification

**Commands:**
- `cd frontend; npx vitest run src/components/ui/Pagination "src/app/(blue)/catalog" "src/app/(blue)/profile/bonuses" src/components/business/SearchPageClient src/components/business/OrdersList` -- expected: все тесты зелёные
- `cd frontend; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок

**Manual checks (if no CLI):**
- Каталог в браузере: вид ряда на первой, средней и последней странице, ширины 360 и 375 px, прокрутка наверх после клика. С клавиатуры: Tab до стрелки вперёд на предпоследней странице, Enter, фокус виден на последней плитке.
- Поиск, заказы, бонусы: прокрутка наверх после клика, в поиске ряд на 375 px не больше двух строк. Здесь `Pagination` на время загрузки снимается, проверить, что подъём не обрывается рывком.

## Suggested Review Order

**Ряд номеров и плитки (точка входа)**

- Ряд как множество номеров: ветки начала, конца и середины, разрыв в одну страницу заполняется номером.
  [`Pagination.tsx:50`](../../frontend/src/components/ui/Pagination/Pagination.tsx#L50)

- Единый вид плитки: `text-sm` вместо `text-body-s`, чтобы `twMerge` не выбросил класс.
  [`Pagination.tsx:32`](../../frontend/src/components/ui/Pagination/Pagination.tsx#L32)

**Прокрутка к началу и фокус**

- Прокрутка в одном месте для всех потребителей, с учётом `prefers-reduced-motion`.
  [`Pagination.tsx:119`](../../frontend/src/components/ui/Pagination/Pagination.tsx#L119)

- Стрелка исчезает на краю: фокус переводится на плитку цели с `preventScroll`.
  [`Pagination.tsx:135`](../../frontend/src/components/ui/Pagination/Pagination.tsx#L135)

**Потребители**

- Каталог переведён на общий компонент вместо своей разметки.
  [`CatalogPageClient.tsx:1869`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L1869)

- Поиск: `scroll: false`, прокрутку делает `Pagination`, иначе рывок Next оборвёт плавную.
  [`SearchPageClient.tsx:117`](../../frontend/src/components/business/SearchPageClient/SearchPageClient.tsx#L117)

**Тесты**

- Точный состав ячеек ряда по матрице спеки.
  [`Pagination.test.tsx:313`](../../frontend/src/components/ui/Pagination/__tests__/Pagination.test.tsx#L313)

- Прокрутка: плавная, `auto` при уменьшении движения, не при клике по текущей.
  [`Pagination.test.tsx:209`](../../frontend/src/components/ui/Pagination/__tests__/Pagination.test.tsx#L209)

- Перенос фокуса на плитку крайней страницы с клавиатуры, не мышью.
  [`Pagination.test.tsx:253`](../../frontend/src/components/ui/Pagination/__tests__/Pagination.test.tsx#L253)

- Каталог: один вызов `scrollTo` на клик по плитке.
  [`CatalogPage.test.tsx:1063`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L1063)
