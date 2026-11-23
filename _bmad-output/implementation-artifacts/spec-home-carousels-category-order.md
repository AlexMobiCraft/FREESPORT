---
title: 'Карусели главной упорядочены по дереву категорий, как каталог'
type: 'feature'
created: '2026-11-23'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
baseline_commit: '73f4f79427fe5844c6759d460ddc765e04665452'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Карусели главной «Лидеры продаж», «Новинки» и «Акция» показывают товары по дате создания (`ordering=-created_at`), поэтому карточки разных категорий перемешаны. Владелец хочет тот же порядок, что на странице каталога: по категориям в порядке сайдбара.

**Approach:** `getAllHits`/`getAllNew`/`getAllPromo` запрашивают `ordering=category_tree` — режим API, который уже использует `/catalog` по умолчанию (позиция категории при обходе дерева сайдбара, затем `name`, затем `id`). Бэкенд не меняется. Сортировка по алфавиту (запасной вариант владельца) не нужна: внутри категории товары и так идут по `name`.

</frozen-after-approval>

## Implementation Notes

- `frontend/src/services/productsService.ts` — в трёх `getAll*` `ordering: '-created_at'` → `'category_tree'`, JSDoc обновлён. `getHits`/`getNew`/`getSale`/`getPromo` (8 товаров, `/electric`, `ElectricProductSection`) не тронуты — у них по-прежнему `-created_at`.
- Комментарий к `fetchAllPages` переписан: сортировка должна заканчиваться уникальным ключом (у `category_tree` — `id`); при сдвиге выдачи между запросами товар может задвоиться (убирает дедуп) или выпасть на стыке.
- «Распродажа» (`SaleSection` → `getSale`, 8 товаров, `-created_at`) не меняется: прошлой задачей исключена сознательно, `getSale` общий с `/electric`, а на проде 23.11.2026 товаров распродажи 0 — секция не рендерится.
- Проверка на проде 23.11.2026: `ordering=category_tree` вместе с `is_hit|is_new|is_promo` и `in_stock=true` отвечает 200; каждая категория идёт одним блоком (хиты — 13 блоков на 13 категорий, новинки — 18 на 18, акция стр. 1 — 6 на 6), первыми — «Единоборства».
- Проверки: vitest `productsService.test.ts` + `components/home/__tests__` — 350 тестов зелёные; `format:check`, `lint`, `tsc --noEmit` — чисто.
- Тесты: ожидания `ordering` в `productsService.test.ts` и в `HitsSection`/`NewArrivalsSection`/`PromoSection` тестах переведены на `category_tree`.
- GitNexus `impact` по трём методам: вызывающих в графе 0 (`UNKNOWN`), по `git grep` — только `HitsSection`, `NewArrivalsSection`, `PromoSection` (главная).

## Review Triage Log

Oneshot, слой blind-hunter.

| # | Находка | Вердикт | Маршрут | Обоснование |
|---|---------|---------|---------|-------------|
| 1 | Литерал `category_tree` дублирует `DEFAULT_ORDERING` каталога, связи нет | low | reject | Имя режима — контракт API, а не настройка каталога; общая константа между `(blue)/catalog` и сервисом — новый публичный экспорт ради редкого переименования. |
| 2 | Комментарий `fetchAllPages` не называет выпадение товара на стыке при сдвиге выдачи | low | patch | Комментарий дополнен. Сам риск принят владельцем в прошлой задаче (spec-home-carousels-all-flagged, #2). |
| 3 | Из комментария пропало требование уникального последнего ключа сортировки | low | patch | Добавлено в комментарий. |
| 4 | «Распродажа» на главной осталась по дате | low | patch | Исключение записано в Implementation Notes: на проде 0 товаров, `getSale` общий с `/electric`. |
| 5 | Нет теста бэкенда на `category_tree` вместе с `is_*` и `in_stock` | false | reject | Комбинация проверена на проде: ответ 200, порядок блочный (Implementation Notes). |
| 6 | Нагрузка: запрос к `Category` на каждый запрос `/products/` | low | reject | На проде главная шлёт 4 запроса (1+1+2 страницы); каталог делает то же на каждой странице; без кэша — требование прошлой спеки (сайдбар и выдача не должны расходиться). |
| 7 | В UI не видно границ категорий, все карусели начинаются с «Единоборств» | false | reject | Это и есть запрошенное поведение: порядок как в каталоге. |
| 8 | Нет теста, что компонент сохраняет порядок API | low | reject | Компоненты рендерят массив как есть, клиентской сортировки нет; тест — новая проверка ради гипотетической будущей правки. |
