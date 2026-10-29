---
title: 'Кнопка «Выбрать» вместо «В корзину» на карточках списка товаров'
type: 'feature'
created: '2026-10-29'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На маленьких карточках товаров есть кнопка «В корзину». В каталоге она молча добавляет первый доступный вариант (размер, цвет), а покупатель его не выбирал.

**Approach:** На карточках списка кнопку «В корзину» заменить на «Выбрать», которая ведёт на страницу товара. В корзину товар добавляется только со страницы товара (`ProductSummary`), где покупатель выбирает вариант.

Решения агента (пользователь их не заметит или они следуют из запроса):
- «Выбрать» показывается там же и при тех же условиях, что раньше «В корзину»: в каталоге (сетка и список) у товаров в наличии и в избранном профиля у доступных товаров. В поиске и на главной кнопки как не было, так и нет. Строка «Нет в наличии» и кнопка «Сообщить о поступлении» остаются.
- Тема `/electric` (`ElectricProductCard`) не меняется: это отдельная демо-тема, а не основной сайт.
- В `ProductCard` вся карточка уже обёрнута в `<Link>` на товар, поэтому «Выбрать» — не `<button>`, а `<span>` в стиле кнопки: интерактивный элемент внутри `<a>` — недопустимый HTML. В `FavoriteProductCard` контент вне ссылки, там «Выбрать» — `<Link>` в стиле кнопки.

</frozen-after-approval>

## Implementation Notes

- `ProductCard.tsx`: проп `onAddToCart` заменён на `showSelectButton?: boolean`, `handleAddToCart` удалён.
- `CatalogPageClient.tsx`: удалены `handleAddToCart` и импорты, которые стали лишними.
- `FavoriteProductCard` / `FavoritesList` / `profile/favorites/page.tsx`: удалены `onAddToCart`, `isAddingToCart`, `addingToCartId` и обработчик добавления в корзину.
- GitNexus: у `ProductCard` риск `HIGH` (7 прямых вызывающих, 4 процесса). Проп передаёт только `CatalogContent`, у остальных потребителей разметка не меняется. У `FavoriteProductCard` и `FavoritesList` риск `LOW`.
- В `profile/favorites/page.tsx` старый обработчик вызывал `addItem(favorite.product, 1)`: ID товара передавался как ID варианта. Ошибка ушла вместе с обработчиком.
- `e2e/profile/favorites.spec.ts`: проверки «В корзину» заменены проверками ссылки «Выбрать» и перехода на страницу именно этого товара.
- Проверено: `format:check`, `lint`, `tsc --noEmit`, vitest (27 файлов, 678 тестов). `gitnexus detect-changes` задел только ожидаемые символы, `check --cycles` — два цикла базовой линии. Глазами в браузере не смотрели: в локальном стеке не поднят контейнер `db`, backend отвечает 502.

## Review Triage Log

- Blind Hunter: в `SELECT_BUTTON_STYLES` нет `active:` из `Button`, классы скопированы в двух файлах — low. `active:` у `<span>` в ссылке не нужен; общий хелпер классов означал бы новое API у `Button` (риск HIGH) — отклонено.
- Blind Hunter: у ссылки «Выбрать» в избранном нет имени товара для скринридера — medium, patch: `aria-label="Выбрать {название}"`.
- Blind Hunter: подсветка «Выбрать» не совпадает с кликабельной зоной, подъём `-translate-y` двойной — low, patch: `group` на `Link`, `group-hover:`, без собственного подъёма.
- Blind Hunter: `<button>` избранного внутри `<Link>` — real, low, было до спеки — defer.
- Blind Hunter: в `CatalogPage.test.tsx` остался мок `cartStore`, нет теста страницы — low: мок безвреден, регрессию ловят юнит-тесты `ProductCard` — отклонено.
- Blind Hunter: нет проверки, что у недоступного товара нет «Выбрать» — low, patch.
- Blind Hunter: e2e сверяет только `/product/` — low, patch: сверка с `href` карточки.
- Blind Hunter: устаревший комментарий `// Cart integration` — low, patch.
- Blind Hunter: в спеке нет AC и проверки, нет записи о теме electric — оформление oneshot допускает без AC; запись про electric — defer.
- Blind Hunter: `docs/architecture/coding-standards.md` показывает старый API `ProductCard` — real, low — defer.
- graph-impact: слой остановился — индекс `stale` из-за незакоммиченного diff (Indexed = HEAD). Компенсировано: impact до правок на свежем индексе, `git grep` удалённых пропсов (остатков нет), `detect-changes` и `check --cycles` перед коммитом.
