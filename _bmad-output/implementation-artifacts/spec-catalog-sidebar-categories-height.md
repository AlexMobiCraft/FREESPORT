---
title: 'Каталог: раскрытое дерево категорий в сайдбаре не обрезается'
type: 'bugfix'
created: '2026-10-25'
status: 'done'
route: 'oneshot'
baseline_revision: '10f529164fe1b1e853515b50cf1f2c4431b48c34'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На `/catalog` раскрытый список «Категории» в сайдбаре ограничен высотой `max-h-[1000px]` (`CATEGORY_MAX_HEIGHT`) с `overflow-hidden`. Если раскрыть несколько веток (например, «Плавание», «Спортивные игры», «Детский транспорт»), нижние пункты, в том числе «Бассейны, пляж, аксессуары», обрезаются, а прокрутки нет. Пользователь предложил два варианта: прокрутка внутри блока или рост блока со сдвигом всего, что под ним.

**Approach:** Блок растёт по высоте содержимого и сдвигает вниз блок «Фильтры». Прокрутку внутри блока не делаем: сайдбар не липкий, и вложенная прокрутка внутри прокручиваемой страницы неудобна. Сворачивание секции убирает потолок высоты: анимация идёт через `grid-template-rows` от `0fr` к `1fr` вместо `max-height`. Тот же приём применяется к «Торговой марке» (`max-h-[500px]`): у неё тот же дефект, хотя он ещё не проявился — сейчас 14 брендов. Разметка до гидратации (`lg:`-классы, свёрнутое состояние на мобилке) и поведение `aria-expanded` не меняются.

</frozen-after-approval>

## Implementation Notes

- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` — константы `CATEGORY_MAX_HEIGHT` и `BRANDS_MAX_HEIGHT` удалены. Контейнеры `#filter-categories` и `#filter-brands` теперь `grid` и переключают `grid-rows-[0fr]` ↔ `grid-rows-[1fr]`. Ветка до гидратации — `grid-rows-[0fr] lg:grid-rows-[1fr]`. `overflow-hidden` перенесён во внутреннюю обёртку `min-h-0 overflow-hidden`. `id`, `aria-*`, `opacity-*`, `mt-*` на внешнем контейнере не менялись.
- Внутренняя обёртка нужна без внешних отступов: margin элемента сетки входит во вклад трека, и при `0fr` свёрнутая секция оставила бы щель. Поэтому `mt-2` у списка брендов остался на вложенном `div`, а не на обёртке.
- `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` — в существующих проверках классы `max-h-*` заменены на `grid-rows-*`. Добавлен регрессионный тест: у раскрытых секций нет `max-h-` и `overflow-hidden`, обёртка — `min-h-0 overflow-hidden` без отступов.
- Проверено: `vitest` каталога — 234/234; `format:check`, `lint`, `tsc` — чисто. Компиляция `globals.css` через `@tailwindcss/postcss` выдаёт `grid-rows-[0fr]`, `grid-rows-[1fr]` и `lg:grid-rows-[1fr]` (`@media (width >= 64rem)`). Chromium (Playwright) на той же разметке с содержимым 1500px: раскрытая — 1500, свёрнутая — 0, до гидратации — 1500 на 1280px и 0 на 390px. На живой странице не смотрели: dev-стек не поднят.

## Review Triage Log

### 2026-10-25 — Review pass (Blind Hunter + graph-impact)

- graph-impact — слой остановился по правилу: при незакоммиченном diff `status` показывает `stale`, хотя коммит индекса совпадает с HEAD. Его процедуру выполнили вручную. `impact CatalogContent --direction upstream`, снятый до правок на коммите индекса 10f5291: LOW, 1 прямой вызывающий (`CatalogPage`), 0 процессов. `git grep` по удалённым `CATEGORY_MAX_HEIGHT`/`BRANDS_MAX_HEIGHT` пуст. `check --cycles`: базовый цикл `HomePage.tsx` и цикл `users/models.py ↔ staff_roles.py` — backend, diff его не трогает, цикл уже есть в develop.
- `[medium]` `[defer]` Свёрнутое содержимое доступно с Tab — старый дефект, уже отложенный в `spec-catalog-sidebar-expanded-default.md`; `max-h-0 opacity-0` до правки вёл себя так же.
- `[low]` `[reject]` `overflow-hidden` у раскрытой секции режет кольцо фокуса — до правки `overflow-hidden` стоял на раскрытом контейнере точно так же; правка поведение не изменила.
- `[low]` `[patch]` Регрессионный тест не ловит потолок высоты на внутренних элементах и не проверяет раскрытость — добавлены `aria-expanded="true"`, `grid-rows-[1fr]` и поиск любого `max-h-` внутри секции; мутация (`max-h-[1000px]` на обёртке) роняет тест.
- `[low]` `[patch]` Проверка «без отступов» ловила только `m-/mt-/my-` — заменена на точное равенство класса обёртки `min-h-0 overflow-hidden`.
- `[low]` `[defer]` Тот же потолок `max-h-[1000px]` в `components/ui/FilterGroup/FilterGroup.tsx` — компонент вне `(blue)`-каталога (`SidebarFilters`, `ElectricSidebar`), правкой не затронут.
- `[false]` `[reject]` На мобилке дерево растёт без предела — именно это попросил пользователь («блок растягивался … со смещением всего, что под ним»); на мобилке секции свёрнуты по умолчанию.
- `[low]` `[reject]` Литералы `grid-rows-*` повторены в двух секциях без константы, комментарий «осиротел» — комментарий описывает соглашение секций и стоит у связанных констант; вынос секции в компонент — уже существующий TODO F9.
- `[low]` `[reject]` Нет e2e-теста раскладки — jsdom раскладку не считает; приём проверен в Chromium через Playwright на той же разметке (Implementation Notes). Отдельный e2e потребовал бы поднятого стека ради одного класса.
- `[low]` `[reject]` Нет `motion-reduce` и анимации в старых браузерах — `transition-all` без `motion-reduce` был и до правки; браузер без анимации `grid-template-rows` раскрывает секцию без анимации, раскладка верна.
- `[low]` `[patch]` Две строки теста длиннее 100 символов после замены классов — перенесены (тесты исключены из prettier через `.prettierignore`, поэтому `format:check` их не видел).
