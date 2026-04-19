## Deferred from: code review of 34-2-sub-order-creation-logic-and-api.md (2026-04-19)

- Определить consume-snapshot контракт корзины во время checkout — текущая защита лочит только строку `Cart`, но не сериализует параллельные изменения `cart_items`; в дальнейшем создать отдельную спеку для реализации этой функции.
- `clearCartLocal` намеренно не сбрасывает promo-state (promoCode/discountType/discountValue) — design decision; риск покрыт patch-находкой о try-finally в orderStore.
- Двойной submit при `isSubmitting: true` не защищён в orderStore — pre-existing.
- Validation coverage PromoCodeInput деградирована (удалены тесты Min Order Amount / Apply Error) — восстановить при реализации серверной promo-системы.
- error path тесты в `orderStore.test.ts` помечены `.skip` — pre-existing, не вызвано текущим diff.
