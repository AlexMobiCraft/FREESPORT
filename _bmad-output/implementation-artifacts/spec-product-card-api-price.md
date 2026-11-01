---
title: 'Карточка товара показывает цену из API, а не свою цепочку опта'
type: 'bugfix'
created: '2026-11-01'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Без акции плитка считает цену сама: у клиента «Опт 2–4» без цены своего уровня она спускается на младшие опты, а корзина и заказ по `ProductVariant.get_price_for_user` берут розницу. Клиент видит на плитке одну сумму, а платит другую, большую.

**Approach:** Плитка показывает `current_price` из API, если он больше нуля, — это та же сумма, что в корзине и заказе. Запасной расчёт для ответа без `current_price` повторяет правило бэкенда: цена уровня, иначе розница, без спуска по младшим оптам.

</frozen-after-approval>

## Implementation Notes

- `frontend/src/components/business/ProductCard/ProductCard.tsx`: приоритет `current_price > 0` для всех ролей, кроме `guest`; из `getProductPrice` убраны цепочка опта и откат федерации на тренера, чтобы запасной расчёт совпал с `pricing_policy.py`; убрана недостижимая ветка `current_price` у `vip`/`special_price`.
- Гостю `current_price` не берётся: `HitsSection`, `NewArrivalsSection`, `PromoSection` и `SaleSection` грузят товары один раз, а выход на `/home` их не перемонтирует. Без проверки гость видел бы цену прошлой сессии. Секции передают `userRole` из `authStore`, поэтому проверки в карточке достаточно.
- Тесты `ProductCard.test.tsx`: две проверки старого поведения переписаны, добавлены опт без цены уровня, тренер и федерация без акции, гость, `current_price = 0.00`.
- Клиент «Опт 2–4» без цены уровня теперь видит на плитке розницу вместо младшего опта: это та сумма, которую он и платит. Цены заказов не меняются.

## Review Triage Log

- medium, patch — после выхода на `/home` гость видит цену прошлой сессии: секции не перезапрашивают товары, регрессия этой правки. Исправлено проверкой `userRole === 'guest'`.
- low, patch — запасной расчёт федерации откатывался на тренера, в отличие от `pricing_policy.py`. Убрано.
- low, patch — недостижимый `current_price` в ветке `vip`/`special_price`. Убрано.
- low, patch — тестовые комментарии описывали удалённую цепочку. Исправлены.
- low, patch — комментарий «та же сумма, что в корзине» неточен: цена считается по первому варианту. Уточнён.
- low, defer — зачёркнутая розница рядом с такой же ценой при `discount_percent > 0`. Старое поведение: так же у розницы и тренера.
- medium, defer — страница товара без варианта показывает тренеру и федерации розницу (`getProductDisplayPrice`). Старый дефект соседнего экрана.
- medium, defer — `ElectricProductCard`, `RecommendationsRow`, `SearchAutocomplete` показывают голую `retail_price`. Старый дефект вне `ProductCard`.
- low, rejected — новые тесты только в `grid`: цена считается один раз до разметки, все три вида читают одну переменную.
- false — «спека не завершена»: маршрут `oneshot` намеренно содержит только Intent и Implementation Notes.

