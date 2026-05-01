## Deferred from: review of tech-spec-catalog-category-sort-and-hide-empty (2026-04-30)

- **N+1 / глубина `select_related` в `visible_categories`**: цепочка `select_related("parent__parent__parent__parent")` ограничена 4 уровнями; иерархия глубже вызовет N+1. Рассмотреть замену на рекурсивный CTE или MPTT-запрос. [backend/apps/products/views.py — `visible_categories` action]
- **Race condition `getVisibleCategories` без AbortController**: при быстрой смене фильтров устаревший ответ может перезаписать актуальный `sidebarVisibleIds`. Добавить счётчик версий или AbortController по аналогии с основным списком продуктов. [frontend/src/app/(blue)/catalog/page.tsx — `fetchProducts`]
- **`products_count` без `distinct=True`**: при нескольких вариантах у товара `products_count` завышается (JOIN inflation). Pre-existing. [backend/apps/products/serializers.py — `CategoryTreeSerializer.get_children`]
- **`visible_categories` без лимита**: `values_list("category_id", flat=True).distinct()` грузит все ID в память. При большом каталоге рассмотреть лимит или агрегацию на стороне БД. [backend/apps/products/views.py — `visible_categories`]
- **Утечка пагинации в `getVisibleCategories`**: параметры `page`, `page_size`, `ordering` передаются в `/products/visible-categories/` — бэкенд их игнорирует, но стоит явно исключить. [frontend/src/services/categoriesService.ts — `getVisibleCategories`]
- **Pre-fill flash для глубоких деревьев**: начальная фильтрация по `in_stock_count` не добавляет предков явно в `initialVisible` — для 3+ уровней flash до ответа `visible-categories` не устранён. `hasVisibleDescendant` корректирует рендер, но краткий flash возможен. Pre-existing ограничение дизайна. [frontend/src/app/(blue)/catalog/page.tsx — `fetchCategories`]

## Deferred from: Fortieth Follow-up code review of 34-2-sub-order-creation-logic-and-api.md (2026-04-19)

- Двойной вызов `trim()` в `isButtonDisabled` — косметика, извлечь `trimmedCode` переменную. [frontend/src/components/cart/PromoCodeInput.tsx:139]
- Нет негативного теста OrderDetail для `discount_amount=0` — title теста обещает «только при > 0», но проверяется только положительный кейс. [frontend/src/components/business/OrderDetail/OrderDetail.test.tsx:165]
- `clearCartLocal()` не обнуляет promo-поля — design decision; риск покрыт try-finally в orderStore. [frontend/src/stores/cartStore.ts:260-262]
- `handleApply()` не проверяет результат `validateCode()` перед `applyPromo()` — некорректный код может быть сохранён. [frontend/src/components/cart/PromoCodeInput.tsx:82-93]

## Deferred from: code review of 34-2-sub-order-creation-logic-and-api.md (2026-04-19)

- Определить consume-snapshot контракт корзины во время checkout — текущая защита лочит только строку `Cart`, но не сериализует параллельные изменения `cart_items`; в дальнейшем создать отдельную спеку для реализации этой функции.
- `clearCartLocal` намеренно не сбрасывает promo-state (promoCode/discountType/discountValue) — design decision; риск покрыт patch-находкой о try-finally в orderStore.
- Двойной submit при `isSubmitting: true` не защищён в orderStore — pre-existing.
- Validation coverage PromoCodeInput деградирована (удалены тесты Min Order Amount / Apply Error) — восстановить при реализации серверной promo-системы.
- error path тесты в `orderStore.test.ts` помечены `.skip` — pre-existing, не вызвано текущим diff.

## Deferred from: dev-task-order-status-mode-info review (2026-05-01)

- **`errors="xmlcharrefreplace"` при кодировании в windows-1251** — для текущего набора (`STATUS_MAPPING.keys()` + `Не согласован`) ни один символ не выходит за пределы cp1251. Если когда-нибудь в `ONEC_EXCHANGE.ORDER_DEFAULTS.STATUS` попадёт unicode за пределами cp1251 (эмодзи, редкая латиница), он молча превратится в `&#NNN;`, что 1С может не распарсить как имя статуса. Рассмотреть валидацию настроек или fail-loud режим. [backend/apps/integrations/onec_exchange/views.py — `handle_info`]
- **Throttling `OneCExchangeThrottle` применяется к `mode=info`** — кнопка "Загрузить с сайта" в 1С вызывается редко, риск минимален. При лимите запросов 1С получит `429` с JSON-телом, что не соответствует протоколу обмена. Pre-existing для всех режимов, не специфично для этой истории. [backend/apps/integrations/onec_exchange/views.py — `ICExchangeView.throttle_classes`]
- **Дублирование dispatch-таблицы в `get`/`post`** — добавление нового режима требует правки в двух местах (`mode == "info"` добавлен в обе ветки). Pre-existing паттерн, не созданный этой историей. Рефакторинг в общий dispatch dict — отдельная задача. [backend/apps/integrations/onec_exchange/views.py — `get`/`post`]
- **AC6 (manual): `Загрузить с сайта` в 1С** — после деплоя нужна ручная проверка из 1С: открыть настройки обмена заказами, перейти к таблице сопоставления статусов, нажать "Загрузить с сайта", убедиться, что таблица заполняется без ошибки "Не удалось прочитать данные, загруженные с сервера".

## Deferred from: checkout-address-ux-improvements review (2026-04-29)

- `orderId === 0` или `orderId === ""` (falsy) в CheckoutForm.onSubmit — нет редиректа на success, хотя заказ создан. Pre-existing, не вызвано текущим diff. Риск минимален (PostgreSQL serial начинает с 1), но стоит добавить guard `if (orderId != null && orderId !== '')` в будущем рефакторинге. [frontend/src/components/checkout/CheckoutForm.tsx:253]
- `orderStore.currentOrder` может содержать stale id после failed `createOrder` — при повторном submit возможен ложный редирект на старый заказ. Pre-existing, зависит от реализации orderStore. Рассмотреть сброс `currentOrder` при ошибке в orderStore. [frontend/src/stores/orderStore.ts]
- Контактные поля (firstName, lastName, phone) перезаписываются при автозаполнении из Address.full_name — если адрес оформлен на другого получателя (B2B склад), имя подменяется. Спека намеренно включает контактные поля в маппинг (Address хранит full_name+phone). Если потребуется разделение «контакт заказчика» vs «получатель» — отдельная задача. [frontend/src/utils/checkout/addressMapping.ts]
