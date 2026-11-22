---
title: 'Карусели «Лидеры продаж», «Новинки» и «Акция» на главной показывают все отмеченные товары'
type: 'bugfix'
created: '2026-11-22'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '0b25d7d96af50b191d4f8bf5e42e77b6f6b6fe67'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На главной карусели «Лидеры продаж», «Новинки» и «Акция» показывают максимум 8 товаров: `getHits`/`getNew`/`getPromo` запрашивают `page_size: 8`. На проде 22.11.2026 в наличии 29 лидеров, 56 новинок и 186 акционных товаров — большая часть на главную не попадает.

**Approach:** Три секции главной собирают все страницы выдачи `/products/?is_hit|is_new|is_promo=true` и выводят товары в карусели целиком.

**Решения владельца (22.11.2026):**
- Только товары в наличии: фильтр `in_stock: true` сохраняется.
- «Акция» (`PromoSection`) входит в задачу.
- Меняется только главная: `HitsSection` с `variant="electric"` на `/electric` по-прежнему берёт 8 товаров.
- Сбой на странице 2 и дальше (любая ошибка, включая 404 при уменьшившемся `count`) не роняет секцию: она показывает уже загруженное. Ошибка — только при сбое первой страницы.

## Boundaries & Constraints

**Always:** порядок прежний — `-created_at`; товары без повторов по `id`; номер страницы считаем сами, `next` — только признак «есть ещё» (абсолютный URL с хостом бэкенда не используем).

**Never:** не менять тела и дефолты `getHits`/`getNew`/`getSale`/`getPromo`; не трогать бэкенд, `/electric`, `ElectricProductSection`, «Распродажу»; не снимать фильтр наличия.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Несколько страниц | 130 товаров | запросы `page_size=100&page=1`, `page=2`; 130 карточек | N/A |
| Одна страница | 32 товара, `next: null` | один запрос, 32 карточки | N/A |
| Пусто | `count: 0` | секция не рендерится, как сейчас | N/A |
| Повтор на стыке | товар есть на стр. 1 и 2 | одна карточка | N/A |
| Сбой стр. 1 | 500 | вызов отклоняется | сообщение и «Повторить», как сейчас |
| Сбой стр. ≥2 | стр. 1 ок, стр. 2 — 500 или 404 | 100 карточек со стр. 1 | ошибки в UI нет |
| Бесконечная пагинация | `next` всегда не `null` | не больше 10 запросов | отдаётся собранное |

</frozen-after-approval>

## Code Map

- `frontend/src/services/productsService.ts:227-289` -- `getHits`/`getNew`/`getPromo`: дефолты `is_*`, `ordering: '-created_at'`, `page_size: 8`, `in_stock: true`. Сюда — новые методы.
- `frontend/src/types/api.ts:138` -- `PaginatedResponse<T>` (`next`, `results`).
- `frontend/src/components/home/HitsSection.tsx:125` -- `fetchHits` → `getHits()`; есть проп `variant`.
- `frontend/src/components/home/NewArrivalsSection.tsx:59`, `PromoSection.tsx:58` -- вызывают `getNew()`/`getPromo()`; используются только на главной.
- `frontend/src/components/home/ElectricProductSection.tsx:59-65,92` -- берёт `productsService.getHits` и др. без привязки и вызывает как `fetchFn()`: `this` в этих методах недоступен.
- `backend/apps/products/views.py:42-44,65` -- `max_page_size = 100`; `ordering = ["-created_at"]` без второго ключа (поле `id` не в `ordering_fields`, добавить через параметр нельзя) — отсюда дедупликация.
- `frontend/src/components/home/__tests__/HitsSection.test.tsx:113-142`, `NewArrivalsSection.test.tsx:115` -- проверяют `page_size=8`.
- `frontend/src/__mocks__/api/handlers.ts:597-611` -- общий дефолт для всех непойманных запросов `/products/` (в том числе `is_promo`): `count: 100`, `next: null`, один товар; отдельной ветки для `is_promo` нет — тестам «Акции» нужен свой `server.use`.
- `frontend/src/services/api-client.ts:224-233` -- на 500/503 и сетевые ошибки клиент сам повторяет запрос (паузы 1, 2, 4 с, ~7 с в сумме); на 404 повторов нет.
- `frontend/src/services/__tests__/productsService.test.ts` -- тесты сервиса на MSW.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/services/productsService.ts` -- функция уровня модуля `fetchAllPages(params)`: `page_size: 100`, `page` 1…10, стоп по `next === null`; ошибка на стр. 1 пробрасывается, на стр. ≥2 — цикл останавливается; дедуп по `id` с сохранением порядка. Методы `getAllHits()`/`getAllNew()`/`getAllPromo()` — однострочные обёртки с фильтрами как у `getHits`/`getNew`/`getPromo`.
- [x] `frontend/src/components/home/HitsSection.tsx` -- `variant === 'electric' ? getHits() : getAllHits()`; у `fetchHits` (`useCallback`, сейчас `[]`) зависимости `[variant]` — иначе `exhaustive-deps` даёт warning, а `npm run lint` идёт с `--max-warnings=0`.
- [x] `frontend/src/components/home/NewArrivalsSection.tsx`, `PromoSection.tsx` -- звать `getAllNew()`/`getAllPromo()`.
- [x] `frontend/src/services/__tests__/productsService.test.ts` -- по строке на каждый сценарий матрицы. Сбой стр. ≥2 проверять ответом 404 (без повторов `api-client`). Ответ 500 на стр. 2 — один отдельный тест с `{ timeout: 20000 }`, как в `HitsSection.test.tsx:68`: повторы идут ~7 с, а дефолтный таймаут vitest — 5 с.
- [x] `frontend/src/components/home/__tests__/HitsSection.test.tsx`, `NewArrivalsSection.test.tsx`, новый `PromoSection.test.tsx` -- `page_size=100`; MSW с 12 товарами → 12 карточек; для `HitsSection variant="electric"` — по-прежнему `page_size=8`.

**Acceptance Criteria:**
- Given API отдаёт 12 отмеченных товаров, when рендерится секция главной, then в ней 12 карточек.
- Given `SearchPageClient` и `/electric`, when они загружают товары, then параметры запросов прежние.

## Implementation Notes

- `fetchAllPages` останавливается по `!next` (не только `=== null`): ответ без поля `next` тоже считается последней страницей. Сбой стр. ≥2 пишется в `console.warn` с номером страницы.
- В компонентных тестах (jsdom) обработчик MSW срабатывает на один запрос дважды — так было и до правки (вариант `electric` идёт через неизменённый `getHits`). Поэтому тест `variant="electric"` проверяет параметры каждого вызова, а не их число; точное число запросов проверяют тесты сервиса (`@vitest-environment node`).
- Ручные проверки (DevTools на локальном стенде: запросы `page_size=100&page=1`, число карточек, ленивые картинки) не выполнялись.

## Spec Change Log

## Review Triage Log

Итерация 0 (слои: blind-hunter, edge-case-hunter, verification-gap, graph-impact).

| # | Слой | Находка | Вердикт | Маршрут | Обоснование |
|---|------|---------|---------|---------|-------------|
| 1 | edge | Равные `created_at` без второго ключа — товар может выпасть на стыке страниц | low | reject | Риск принят владельцем 22.11.2026 (Design Notes): на проде совпадений нет; `id` не в `ordering_fields`, фикс — правка бэкенда (Never). |
| 2 | edge, blind | Товар теряет флаг/наличие между запросами страниц — соседний молча пропускается | low | reject | Реально, но окно — доли секунды между запросами; фикс (сверка с `count`, перезапрос) — новая логика. |
| 3 | edge, blind | После 10 страниц обрезка выдачи без `console.warn` | low | reject | Максимум на проде 186 товаров (2 страницы); до 1000 отмеченных далеко; фикс — новая ветка. |
| 4 | edge (+claim) | Тело стр. ≥2 `null`/без итерируемого `results` бросает TypeError вне try | false | reject | DRF-пагинатор всегда отдаёт объект с `results`; `data.results ?? []` уже есть; некорректное тело 2xx от нашего API недостижимо. |
| 5 | edge | 5xx/зависание стр. 2 держит скелетон ~7–30 с | medium | reject | Решение владельца 22.11.2026 (вариант A, Design Notes): прогрессивная подгрузка не делается. |
| 6 | edge, blind | Нет отмены при смене `variant`/размонтировании, поздний `setProducts` | low | reject | `variant` — статичный проп в обоих местах использования; setState после unmount в React 18 безвреден; фикс — новый guard. |
| 7 | blind | Тест «500 на стр. 2» не проверяет, что стр. 2 запрашивалась | low | patch | Добавлены проверки `page=1` и `page=2` в запросах. |
| 8 | blind | Строка матрицы «ошибки в UI нет» не проверена в компонентах | low | reject | Сервис возвращает resolved-массив, компонент обрабатывает его как обычный успех; строка покрыта тестами сервиса. |
| 9 | blind | Нет тестов на ответ без `next` / без `results` | low | reject | Недостижимо для DRF-ответа; это защитные ветки, а не контракт. |
| 10 | blind | Тесты с 500 ждут реальные паузы повторов (~20 с к прогону) | low | reject | Тест с 500 на стр. 2 предписан спекой; фейковые таймеры — новая инфраструктура теста. |
| 11 | blind | `makeFlaggedProducts` в трёх копиях, две — длиннее printWidth | low | patch | Сигнатура перенесена как в `PromoSection.test.tsx`; вынос в общий модуль отклонён (лишняя структура). |
| 12 | blind | Названия тестов «8 products» и JSDoc секций устарели | false | reject | «8» — число товаров в моке `handlers.ts`, названия верны; JSDoc секций не утверждает лимит. |
| 13 | blind | Проверки URL подстрокой (`page=1` совпадёт с `page=10`) | low | patch | Проверки параметров переведены на `searchParams.get` с равенством. |
| 14 | blind | JSDoc `fetchAllPages` не называет пропуск товара при сдвиге выдачи | low | reject | Комментарий не утверждает обратного; риск описан в Design Notes. |
| 15 | graph-impact | Индекс GitNexus `stale` (незакоммиченные правки этих же 4 файлов) — слой не выполнен | — | переиндексация | Перед правками `impact`: `HitsSection`/`NewArrivalsSection`/`PromoSection` — LOW, вызыватели `HomePage`, `/electric`. Слой повторен после `analyze --force`: несогласованных вызывающих, непроверенных символов, неназванных рисков и новых циклов нет (`check --cycles` — два цикла базовой линии). |

## Design Notes

Известные риски, принятые владельцем: в «Акции» ~186 карточек, стрелка листает по 2 (`HitsSection.tsx:168`) — ~93 клика до конца; два последовательных запроса — скелетон держится дольше. Картинки ленивые (`ProductCard.tsx:309`), секции клиентские — SSR/SEO не затронуты. Без второго ключа сортировки товар на стыке страниц может выпасть (дубли убирает дедуп) — при одной дате создания у пачки из импорта 1С; принимаем. Второй ключ `ordering=-created_at,name` (`name` есть в `ordering_fields`) рассмотрен и отклонён владельцем 22.11.2026: на проде среди 29/56/186 отмеченных товаров совпадений `created_at` нет.

Сбой стр. 2 с ответом 500/503 при живой стр. 1: `api-client` повторяет запрос ~7 с, всё это время секция показывает скелетон, хотя стр. 1 уже загружена. Владелец принял риск 22.11.2026 (вариант A): метод возвращает товары одним массивом, прогрессивная подгрузка (сначала стр. 1, потом дописать хвост) не делается.

Замер прода 22.11.2026: стр. 1 и 2 «Акции» — по ~0,72 с и ~227/194 КБ JSON; у хитов и новинок стр. 2 отвечает 404; `next` — абсолютный URL с хостом прода.

## Verification

**Commands:**
- `cd frontend && npx vitest run src/services/__tests__/productsService.test.ts src/components/home/__tests__ src/components/business/SearchPageClient` -- expected: все зелёные.
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit` -- expected: без ошибок.

**Manual checks (if no CLI):**
- Главная на локальном стенде: в DevTools запросы `/products/?…&page_size=100&page=1`; число карточек в каждой карусели = `count` выдачи.
- DevTools → Network → Img при открытии главной без прокрутки: число запросов картинок товаров примерно равно числу видимых карточек, а не всем ~270 карточкам трёх каруселей (`next/image` с `loading="lazy"` внутри горизонтального `overflow`). Если грузятся все — записать в Implementation Notes и сообщить владельцу, не чинить в этой задаче.
