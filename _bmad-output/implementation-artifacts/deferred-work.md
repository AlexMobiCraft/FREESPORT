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
