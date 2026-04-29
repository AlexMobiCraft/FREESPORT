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

## Deferred from: checkout-address-ux-improvements review (2026-04-29)

- `orderId === 0` или `orderId === ""` (falsy) в CheckoutForm.onSubmit — нет редиректа на success, хотя заказ создан. Pre-existing, не вызвано текущим diff. Риск минимален (PostgreSQL serial начинает с 1), но стоит добавить guard `if (orderId != null && orderId !== '')` в будущем рефакторинге. [frontend/src/components/checkout/CheckoutForm.tsx:253]
- `orderStore.currentOrder` может содержать stale id после failed `createOrder` — при повторном submit возможен ложный редирект на старый заказ. Pre-existing, зависит от реализации orderStore. Рассмотреть сброс `currentOrder` при ошибке в orderStore. [frontend/src/stores/orderStore.ts]
- Контактные поля (firstName, lastName, phone) перезаписываются при автозаполнении из Address.full_name — если адрес оформлен на другого получателя (B2B склад), имя подменяется. Спека намеренно включает контактные поля в маппинг (Address хранит full_name+phone). Если потребуется разделение «контакт заказчика» vs «получатель» — отдельная задача. [frontend/src/utils/checkout/addressMapping.ts]
