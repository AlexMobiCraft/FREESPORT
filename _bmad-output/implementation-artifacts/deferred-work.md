## Deferred from: code review of 34-2-sub-order-creation-logic-and-api.md (2026-04-19)

- Определить consume-snapshot контракт корзины во время checkout — текущая защита лочит только строку `Cart`, но не сериализует параллельные изменения `cart_items`; в дальнейшем создать отдельную спеку для реализации этой функции.
