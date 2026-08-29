---
title: 'Каталог: сохранение номера страницы пагинации в URL'
type: 'bugfix'
created: '2026-08-28'
status: 'review'
review_loop_iteration: 2
baseline_commit: '3cbbf1cfb333effe9fe867e621679aa25af87a99'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В каталоге `(blue)/catalog` номер страницы живёт только в React-состоянии (`useState(1)`), поэтому F5, возврат «назад» из карточки товара и открытие ссылки в новой вкладке всегда сбрасывают пользователя на первую страницу.

**Approach:** Зеркалить номер страницы в query-параметре `?page=N`: читать при монтировании и при внешних изменениях URL, писать при клике по пагинации, удалять при смене любого фильтра. Источником истины для запроса к API остаётся состояние `page`, URL — его зеркало (как в `SearchPageClient`).

## Boundaries & Constraints

**Always:**
- `page=1` в URL не пишется — канонический URL первой страницы без параметра (SEO).
- Смена фильтра (поиск, категория, бренд, цена, сортировка, «в наличии», сброс) удаляет `page` из URL и возвращает состояние на 1 — там же, где сейчас стоит `setPage(1)` (8 мест).
- Смена фильтра вызывает `fetchProducts` **один раз**, а не дважды (старая страница + новая).
- Навигация — `router.push(..., { scroll: false })`; если query-строка не изменилась, push не выполняется.

**Ask First:**
- Вынос в URL других параметров каталога (`ordering`, `price`, `in_stock`) — отдельная задача.
- Замена `router.push` на `router.replace` (меняет поведение кнопки «назад»).

**Never:**
- Не трогать `(electric)/electric/catalog`, страницу поиска, заказы, бонусы, `components/ui/Pagination`.
- Не менять backend — контракт `CustomPageNumberPagination` остаётся как есть.
- Не хранить номер страницы в `localStorage`/`sessionStorage`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Переход на страницу | Клик по «3» на `/catalog` | `page=3`, URL `/catalog?page=3`, один запрос с `page: 3` | N/A |
| Обновление браузера | `/catalog?page=3`, F5 | Начальное состояние `page=3`, товары 3-й страницы | N/A |
| Возврат на первую | Клик по «1» из `?page=3` | URL без `page` | N/A |
| Смена фильтра | `?page=3`, клик по бренду | URL без `page`, состояние `1`, **ровно один** запрос с `page: 1` | N/A |
| Кнопка «назад» | `?page=3` → назад на `?page=2` | Состояние синхронизируется в `2`, грузится 2-я страница | N/A |
| Мусор в параметре | `?page=abc`, `0`, `-1`, `1.5`, пусто | Трактуется как страница 1 | Фолбэк на 1 без ошибки |
| Страница вне диапазона | `?page=999`, товаров на 3 страницы | DRF отдаёт 404 → откат на 1, URL чистится, товары показаны | Не показывать «Не удалось загрузить товары» |
| Сочетание с фильтрами | `?category=obuv&search=nike&page=2` | Все параметры сохраняются, запрос со `search`, категорией и `page: 2` | N/A |

</frozen-after-approval>

## Code Map

`frontend/src/app/(blue)/catalog/page.tsx` — единственный файл правки.

Точки правки: состояние `page` (368), `updateSearchParams` (584), `handleSearchChange` (604),
`fetchProducts` (614) и его зависимости, `setPage(1)` (609, 722, 734, 741, 754, 759, 768, 1114),
`handlePageChange` (781), кнопки «назад»/«вперёд» (1188, 1211).

**Ловушка идентичности `searchParams` — главное в этой задаче.** `useSearchParams()` отдаёт новый
объект при каждой навигации. Пока пагинация не трогала URL, эти места не срабатывали при смене
страницы; после правки будут срабатывать на каждый клик, если не сузить зависимости до примитивов:

- `activeBadge = useMemo(..., [searchParams])` (341–350) возвращает **новый объектный литерал** и
  лежит в зависимостях `fetchProducts` → каждый push страницы даёт **второй** запрос товаров плюс
  повторные `getVisibleCategories` / `getVisibleBrands`.
- Эффект дерева категорий `[searchParams, hasBadgeFilter, inStock]` (476–520) заново тянет
  `getTree()` и переустанавливает `activeCategoryId` из slug'а URL → выбор категории в сайдбаре
  откатывается, раскрытые ветки схлопываются (`setExpandedKeys` — replace, не merge).
- Синхронизация бренда `[searchParams, brands]` (558–569) делает `setSelectedBrandIds(new Set([...]))`
  → мультивыбор схлопывается к бренду из URL.
- Эффект `focusSearch` `[searchParams]` (696–705) через `setTimeout(100)` уводит фокус в поиск.
- Чтение `search` из URL `[searchParams]` (523–528) безвредно (ставит то же значение), но зависимость
  сузить заодно.

Ориентиры в проекте:

- `frontend/src/app/(blue)/profile/bonuses/page.tsx:69` (`parsePageNumber`), `:133` (`requestSeq` —
  защита от устаревшего ответа), `:159-166` (откат по 404 через `router.replace`) — ближайший эталон,
  повторить подход.
- `frontend/src/components/business/SearchPageClient/SearchPageClient.tsx:107-127` — зеркалирование
  страницы в URL.
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — моки `next/navigation`
  (`mockPush`, `mockSearchParams`), сервисов и `matchMedia`. `mockPush` — пустышка: он не обновляет
  `useSearchParams`, поэтому в тестах push не имеет последствий и ни одна из ловушек выше не видна.
- `backend/apps/products/views.py:40` — стандартный DRF: страница вне диапазона → 404
  с телом `{"detail": "Invalid page."}`. Не меняем.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — сузить зависимости всех эффектов, завязанных на
  `searchParams`, до примитивов: `activeBadge` мемоизировать по `is_new`/`is_hit`/`is_sale`, эффекты
  категорий, бренда, `focusSearch` и чтения `search` — по соответствующим строковым параметрам.
  Без этого клик по странице перезапускает их все (см. Code Map).
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — `updateSearchParams` принимает
  `Record<string, string | null>` (несколько ключей за вызов) + no-op при неизменной query-строке.
  Держать его в ref для использования внутри `fetchProducts`: прямая зависимость вернула бы
  нестабильность идентичности, которую снимает предыдущая задача.
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — `parsePageNumber` с фолбэком на 1; принимать
  только строку из одних цифр (`3abc`, `1e3`, `2.9` → 1), ленивая инициализация `useState` из него.
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — эффект синхронизации состояния из URL для
  «назад»/«вперёд» по примитивному значению параметра, через функциональный `setPage(prev => ...)`.
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — `handlePageChange` пишет `page` в URL (`null` для 1)
  одновременно с `setPage`; все 8 мест `setPage(1)` перевести на общий `resetPage()`
  (в `handleResetFilters` — одним пушем вместе с очисткой `search`).
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — `searchQuery` инициализировать синхронно из URL,
  как `page`: иначе на `/catalog?search=x&page=3` первый запрос уходит без `search`, ловит 404 и
  сбрасывает страницу у корректной закладки.
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — откат по 404: `router.replace` (решение
  пользователя от 2026-08-28; клики по страницам остаются на `push`) + счётчик запросов, чтобы
  устаревший ответ не выдёргивал пользователя с текущей страницы.
- [x] `frontend/src/app/(blue)/catalog/page.tsx` — `disabled={page <= 1}` / `disabled={page >= totalPages}`
  вместо строгого равенства и `aria-current="page"` на активной кнопке страницы.
- [x] `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — сделать роутер-мок честным:
  `mockPush` обновляет то, что возвращает `useSearchParams`. Без этого ни одна из ловушек Code Map
  не наблюдаема в тестах. Восстановить исходный мок в `afterAll`, утверждения о push делать по
  последнему вызову (`mockPush.mock.calls.at(-1)`), а не через `toHaveBeenCalledWith`.
- [x] `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — describe-блок на строки
  I/O-матрицы плюс регрессии: один запрос товаров на клик по странице, сохранение выбранной
  категории и мультивыбора брендов при пагинации на URL с `category`/`brand`.

### Review Findings

- [x] [Review][Patch] Прямая ссылка на первую или невалидную страницу сохраняет неканонический `page` [`frontend/src/app/(blue)/catalog/page.tsx:663`] — `parsePageNumber()` корректно переводит `page=1`, `page=01` и мусор в состояние `1`, однако query-параметр остаётся в адресной строке. Это противоречит требованию канонического URL первой страницы без `page`; нужен безопасный `router.replace` с удалением только `page` и регрессионные тесты.
  **Исправлено (итерация 2):** sync-эффект после `setPage` канонизирует URL — при `pageParam !== null && urlPage === 1` делает `updateSearchParamsRef.current({ page: null }, { replace: true })`. Удаляется только `page`, остальные параметры сохраняются; `replace`, а не `push` — чистка внешней ссылки не плодит записи в истории. Через ref, чтобы не вернуть в зависимости нестабильный `updateSearchParams`.
- [x] [Review][Patch] Роутер-мок не отвечает критериям из задачи [`frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx:139`] — `afterAll` сбрасывает только query-состояние, проверки старых тестов продолжают использовать историю вызовов, а `lastNavigation()` склеивает массивы `push` и `replace`, теряя хронологию. Восстановить исходные реализации моков после блока и проверять последний релевантный вызов напрямую.
  **Исправлено (итерация 2):** честная навигация стала opt-in — `mockPush`/`mockReplace` по умолчанию пустышки (исходное поведение), блок пагинации включает её через `enableRouterNavigation()` в `beforeEach` и возвращает исходные реализации через `restoreRouterMocks()` в `afterAll`; старые describe-блоки снова работают на беспоследственном push. Заведён хронологический `navigationLog` (`{ type, url }`), `lastNavigation()` отдаёт последнюю запись по времени, `lastNavigationUrl()` — её URL; тип навигации (`push` vs `replace`) проверяется явно.
- [x] [Review][Defer] Внешнее удаление `search` не очищает поисковое состояние [`frontend/src/app/(blue)/catalog/page.tsx:553`] — deferred, pre-existing. При возврате браузера с `?search=term` на URL без `search` эффект не вызывает `setSearchQuery('')`, поэтому API продолжает получать прежний поисковый фильтр. Та же условная ветка была в baseline.
- [x] [Review][Defer] Устаревшие ответы видимости могут перезаписать сайдбар [`frontend/src/app/(blue)/catalog/page.tsx:718`] — deferred, pre-existing. `requestSeq` защищает товары, но `getVisibleCategories` и `getVisibleBrands` меняют state внутри `.then/.catch` до проверки последовательности; тот же шаблон присутствовал в baseline.

**Acceptance Criteria:**
- Given пользователь на третьей странице каталога, when он обновляет браузер, then он остаётся на
  третьей странице с теми же товарами.
- Given ссылка `/catalog?category=obuv&page=2`, when её открывают в новой вкладке, then применяются
  и категория, и вторая страница.
- Given `/catalog?category=obuv&page=2`, when пользователь выбирает в сайдбаре другую категорию,
  then выбор сохраняется и не откатывается к категории из URL.
- Given любой клик по номеру страницы, when он обработан, then `productsService.getAll` вызывается
  ровно один раз и дерево категорий не перезапрашивается.
- Given `npm run lint` и `npm run test` после правки, when они запускаются, then проходят без новых
  ошибок и без предупреждений `react-hooks/exhaustive-deps`.

## Spec Change Log

### Итерация 1 — 2026-08-28

**Находка:** состязательное ревью (Blind Hunter + Edge Case Hunter) показало, что реализация,
корректная по прежней спеке, вносит регрессии: два запроса товаров на клик по странице
(`activeBadge` пересоздаёт `fetchProducts`), откат выбранной категории и мультивыбора брендов,
перезагрузка дерева категорий, кража фокуса при `focusSearch=true`, ловушка кнопки «назад» после
отката по 404. Все подтверждены чтением кода.

**Что исправлено в спеке:** Code Map получил раздел про ловушку идентичности `searchParams` с
перечнем всех завязанных на неё мест; в задачи добавлены сужение зависимостей, честный роутер-мок,
`router.replace` для 404, счётчик запросов, синхронная инициализация `searchQuery`, строгий разбор
номера страницы и правки доступности пагинации.

**Известно-плохое состояние, которого избегаем:** зелёные тесты при сломанном поведении — прежний
тестовый мок `mockPush` не обновлял `useSearchParams`, поэтому push в тестах не имел последствий,
и ни одна из перечисленных регрессий не была наблюдаема.

**KEEP (сохранить при переписывании):**
- Мультиключевой `updateSearchParams(Record<string, string | null>)` с no-op-гардом — верный примитив.
- `parsePageNumber` + ленивая инициализация `useState(() => ...)`.
- Эффект синхронизации URL→состояние через функциональный `setPage(prev => ...)`.
- Единая точка сброса `resetPage()` вместо восьми россыпью.
- Состояние как источник истины для запроса (не производное от URL) — обоснование в Design Notes.
- Правку двух существующих тестов поиска (`AC 3`, `AC 5`): URL предзаполняется `search=`, иначе
  no-op-гард законно гасит push. Правка корректна, переделывать не нужно.
- Ref для `updateSearchParams` внутри `fetchProducts` — нужен, но сам по себе недостаточен.

### Итерация 2 — 2026-08-29 (закрытие находок ревью)

**Что сделано:** закрыты оба `[Review][Patch]`. Оба `[Review][Defer]` перенесены в
`_bmad-output/implementation-artifacts/deferred-work.md` как предсуществующие в baseline `3cbbf1cf`.

**Файлы:**
- `frontend/src/app/(blue)/catalog/page.tsx` — канонизация URL первой страницы в sync-эффекте.
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — opt-in честного роутер-мока
  с восстановлением в `afterAll`, хронологический `navigationLog`, 6 новых регрессий
  (`it.each` на `page=1|01|abc|0|` пусто, «удаляется только `page`», негативный контроль
  «канонична — URL не трогаем»).

**Red-green:** без правки `page.tsx` 5 из 6 новых проверок падают, негативный контроль проходит.

**Верификация (2026-08-29):** `npx tsc --noEmit` — 0 ошибок; `npm run lint` (`--max-warnings=0`) —
чисто; `npx vitest run "src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx"` — 48/48;
`npx vitest run` — 148 файлов, 2550 passed, 16 skipped, 0 failed (базовая линия 2536 → +14 проверок).

## Design Notes

Почему состояние, а не значение, производное от URL: `router.push` в App Router обновляет
`searchParams` асинхронно (transition). При производном `page` смена фильтра дала бы промежуточный
рендер «новый фильтр + старая страница» и второй лишний запрос. `setPage(1)` рядом с
`setSelectedBrandIds(...)` в одном обработчике батчится в один рендер.

Обратная сторона того же механизма и главный источник находок ревью: **`useSearchParams()` возвращает
новый объект при каждой навигации**. Любой `useMemo`/`useEffect` с зависимостью `[searchParams]`
сработает на каждом клике по странице. Лечится сужением до примитивов:

```ts
const categorySlug = searchParams?.get('category') ?? null;
useEffect(() => { /* ... */ }, [categorySlug, hasBadgeFilter, inStock]);

const activeBadge = useMemo(
  () => ({ is_new: isNew === 'true' || undefined, /* ... */ }),
  [isNew, isHit, isSale]   // примитивы, а не searchParams
);
```

Гонка, которую no-op-гард создаёт сам: клик «страница 3» (push в полёте) и сразу клик по фильтру —
`resetPage` считает от устаревшего `searchParams`, строка совпадает, push гасится, прилетевший
`?page=3` через sync-эффект возвращает страницу 3. Сужение зависимостей её не снимает; допустимо
оставить (редкий сценарий), но не маскировать: sync-эффект обязан оставаться единственным местом,
где URL побеждает состояние.

## Verification

**Commands:**
- `cd frontend; npx vitest run "src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx"` — expected:
  весь файл зелёный, включая новый блок регрессий.
- `cd frontend; npx vitest run` — expected: полный набор без падений (базовая линия — 2536 тестов).
- `cd frontend; npm run lint` — expected: чисто при `--max-warnings=0`.
- `cd frontend; npx tsc --noEmit` — expected: без ошибок.

**Manual checks:**
- `/catalog` → 3-я страница → в адресной строке `?page=3`; F5 → остались на 3-й; «назад» → 2-я
  подгрузилась; клик по бренду → `page` исчез, список с первой страницы.
- `/catalog?category=obuv` → выбрать в сайдбаре другую категорию → кликнуть страницу 2 → выбранная
  категория сохранилась, дерево категорий не мигнуло.
