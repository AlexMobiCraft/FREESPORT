# Epic 26: Страница "Корзина" (/cart) - Frontend Implementation

## Epic Goal

Реализовать полнофункциональную страницу "Корзина" (`/cart`) на фронтенде, обеспечивающую пользователям возможность просматривать добавленные товары, управлять их количеством, применять промокоды и переходить к оформлению заказа.

## Epic Description

### Existing System Context

**Текущая реализованная функциональность:**

- **Backend Cart API (Epic 2, Story 2.6):** Полностью реализованы CRUD операции для корзины:
  - `GET /cart/` — получение содержимого корзины
  - `POST /cart/items/` — добавление товара (с variant_id)
  - `PATCH /cart/items/{id}/` — обновление количества
  - `DELETE /cart/items/{id}/` — удаление товара
  - Поддержка гостевых корзин через session
- **Frontend Cart Infrastructure (Epic 12, Story 12.3):**
  - `cartStore.ts` — Zustand store с async операциями и Optimistic Updates
  - `cartService.ts` — API клиент для работы с корзиной
  - `ProductSummary.tsx` — компонент добавления в корзину
  - Toast уведомления (success/error)
  - Header счётчик товаров в корзине

- **Technology Stack:**
  - Next.js 15.4.6 с App Router
  - React 19.1.0
  - TypeScript 5.0+
  - Zustand 4.5.7 (state management)
  - Tailwind CSS 4.0

**Точки интеграции:**

- `cartStore` — источник данных о корзине
- `cartService` — API клиент для CRUD операций
- Дизайн-система (`design-system.json`) — стили компонентов
- UI-Kit компоненты (`Button`, `Input`, `Toast`)

### Enhancement Details

**Что добавляется:**

1. **Страница корзины (`/cart`):**
   - Список товаров с изображениями, названиями, характеристиками
   - Управление количеством товаров (+/- кнопки, input)
   - Удаление товаров из корзины
   - Подсчёт промежуточных итогов и общей суммы
   - Применение промокода (после согласования API)

2. **UI компоненты:**
   - `CartPage` — основной компонент страницы
   - `CartItemCard` — карточка товара в корзине
   - `CartSummary` — блок итогов и CTA
   - `PromoCodeInput` — поле ввода промокода (заглушка/MSW mock)
   - `EmptyCart` — состояние пустой корзины

3. **Функциональность:**
   - Синхронизация с cartStore (real-time updates)
   - Optimistic Updates при изменении количества
   - Toast уведомления о действиях
   - Валидация min/max quantity
   - Обработка ошибок API
   - Responsive дизайн (mobile/tablet/desktop)

**Как интегрируется:**

- Использует существующий `cartStore` для state management
- Использует существующий `cartService` для API запросов
- Следует паттернам дизайн-системы из `design-system.json`
- Интегрируется с Header через общий `cartStore.totalItems`

**Success Criteria:**

- Пользователь видит все товары в корзине с изображениями и характеристиками
- Пользователь может изменять количество товаров
- Пользователь может удалять товары из корзины
- Итоговая сумма пересчитывается при любых изменениях
- Кнопка "Оформить заказ" ведёт на `/checkout`
- UI соответствует макету из `front-end-spec.md` (строки 610-641)

## Stories

### Story 26.1: Cart Page Component & Layout

**Описание:** Создание основного компонента страницы `/cart` с двухколоночным layout (список товаров + итоги) и интеграцией с cartStore.

**Acceptance Criteria:**

1. Страница `/cart` рендерится корректно
2. Список товаров отображается слева, итоги справа
3. Пустая корзина показывает компонент `EmptyCart` с CTA "В каталог"
4. Responsive дизайн: на mobile колонки становятся вертикальными
5. Данные загружаются из cartStore при монтировании

**Ключевые файлы:**

- `frontend/src/app/cart/page.tsx` (NEW)
- `frontend/src/components/cart/CartPage.tsx` (NEW)
- `frontend/src/components/cart/EmptyCart.tsx` (NEW)

---

### Story 26.2: Cart Item Card Component

**Описание:** Создание компонента `CartItemCard` для отображения отдельного товара в корзине с изображением, характеристиками, управлением количеством и кнопкой удаления.

**Acceptance Criteria:**

1. Отображается изображение товара (88x88px, radius 12px)
2. Название товара, артикул, цвет, размер
3. Цена за единицу и сумма по позиции
4. Кнопки +/- для изменения количества
5. Удаление товара по клику на 🗑 icon
6. Optimistic Updates при изменении quantity
7. Toast уведомление при удалении

**Ключевые файлы:**

- `frontend/src/components/cart/CartItemCard.tsx` (NEW)
- `frontend/src/components/cart/__tests__/CartItemCard.test.tsx` (NEW)

---

### Story 26.3: Cart Summary & Checkout CTA

**Описание:** Создание компонента `CartSummary` с подсчётом итогов, полем промокода и кнопкой перехода к оформлению заказа.

**Acceptance Criteria:**

1. Отображается "Итоги заказа" с товарной суммой
2. Скидка по промокоду (если применён)
3. Итоговая сумма к оплате
4. Поле ввода промокода с кнопкой "Применить"
5. Кнопка "Оформить заказ" (primary CTA, height 56px)
6. Кнопка disabled если корзина пуста
7. Sticky позиционирование на desktop (stickyOffset: 96px)

**Ключевые файлы:**

- `frontend/src/components/cart/CartSummary.tsx` (NEW)
- `frontend/src/components/cart/PromoCodeInput.tsx` (NEW)
- `frontend/src/components/cart/__tests__/CartSummary.test.tsx` (NEW)

---

### Story 26.4: Promo Code Integration (MSW Mock)

**Описание:** Реализация функционала применения промокода с использованием MSW mock для API эндпоинта (до согласования backend API).

**Acceptance Criteria:**

1. POST `/cart/apply-promo/` API endpoint (MSW mock)
2. Валидация формата промокода (frontend)
3. Success: промокод применяется, скидка отображается
4. Error: "Промокод недействителен" Toast
5. Возможность удалить примененный промокод
6. Loading state при проверке промокода

**Ключевые файлы:**

- `frontend/src/services/promoService.ts` (NEW)
- `frontend/src/stores/cartStore.ts` (UPDATE - добавить promoCode state)
- `frontend/src/__mocks__/api/handlers.ts` (UPDATE - добавить promo endpoint)

---

### Story 26.5: Cart Page Unit & Integration Tests

**Описание:** Комплексное покрытие тестами страницы корзины и всех связанных компонентов.

**Acceptance Criteria:**

1. Unit тесты для CartItemCard (render, quantity change, delete)
2. Unit тесты для CartSummary (totals, promo, checkout button)
3. Unit тесты для EmptyCart
4. Integration тест: добавление товара → отображение в корзине → изменение quantity → удаление
5. MSW моки для всех Cart API endpoints
6. Покрытие >= 80% для cart компонентов

**Ключевые файлы:**

- `frontend/src/components/cart/__tests__/CartPage.test.tsx` (NEW)
- `frontend/src/components/cart/__tests__/CartItemCard.test.tsx` (NEW)
- `frontend/src/components/cart/__tests__/CartSummary.test.tsx` (NEW)
- `frontend/src/components/cart/__tests__/cart.integration.test.tsx` (NEW)

## Compatibility Requirements

- [x] Existing APIs remain unchanged (используем существующие Cart API endpoints)
- [x] Database schema changes are backward compatible (изменений нет)
- [x] UI changes follow existing patterns (дизайн-система)
- [x] Performance impact is minimal (Optimistic Updates)

## Design System Compliance

> [!IMPORTANT]
> Все компоненты Epic 26 должны использовать CSS переменные из `globals.css`:

| Токен             | CSS Variable                  | Значение                           | Использование                              |
| ----------------- | ----------------------------- | ---------------------------------- | ------------------------------------------ |
| Primary           | `var(--color-primary)`        | #0060FF                            | CTA кнопки, акценты                        |
| Primary Hover     | `var(--color-primary-hover)`  | #0047CC                            | Hover states                               |
| Primary Subtle    | `var(--color-primary-subtle)` | #E7F3FF                            | Фон вторичных кнопок                       |
| Text Primary      | `var(--color-text-primary)`   | #1F2A44                            | Основной текст                             |
| Text Secondary    | `var(--color-text-secondary)` | #4B5C7A                            | Вторичный текст                            |
| Text Inverse      | `var(--color-text-inverse)`   | #FFFFFF                            | Текст на primary фоне                      |
| Success           | `var(--color-accent-success)` | #00AA5B                            | Скидки, промокод                           |
| Danger            | `var(--color-accent-danger)`  | #E53935                            | Удаление, ошибки                           |
| Panel Background  | `var(--bg-panel)`             | #FFFFFF                            | Фон карточек                               |
| Neutral 300       | `var(--color-neutral-300)`    | #E3E8F2                            | Dividers, hover backgrounds                |
| Neutral 400       | `var(--color-neutral-400)`    | #B9C3D6                            | Borders                                    |
| Shadow Default    | `var(--shadow-default)`       | 0 8px 24px rgba(15, 23, 42, 0.08)  | Карточки                                   |
| Shadow priceBlock | (custom)                      | 0 18px 40px rgba(0, 55, 166, 0.12) | CartSummary (из ProductSummary.priceBlock) |
| Radius SM         | `var(--radius-sm)`            | 6px                                | Кнопки, inputs                             |
| Radius MD         | `var(--radius-md)`            | 16px                               | Карточки, CTA                              |
| Radius LG         | `var(--radius-lg)`            | 20px                               | Summary блок                               |
| Radius Default    | `var(--radius)`               | 12px                               | Изображения                                |
| Focus Ring        | `var(--focus-ring)`           | 0 0 0 4px rgba(0, 96, 255, 0.12)   | Focus states                               |

**Пример использования:**

```tsx
// CartItemCard - правильное использование CSS переменных
<div
  className="flex gap-4 p-6 bg-[var(--bg-panel)] rounded-[var(--radius-md)] 
               shadow-[var(--shadow-default)]"
>
  <h3 className="text-body-l font-semibold text-[var(--color-text-primary)]">
    {item.product.name}
  </h3>
  <button className="hover:text-[var(--color-accent-danger)]">
    <Trash2 size={20} />
  </button>
</div>
```

## Risk Mitigation

**Primary Risk:** Promo Code API не готов на backend

**Mitigation:** Использовать MSW mock для полной эмуляции API. Флаг `NEXT_PUBLIC_PROMO_ENABLED=false` для отключения функционала в production до готовности backend.

**Rollback Plan:**

- Страница `/cart` может быть скрыта через redirects в `next.config.js`
- Все изменения в отдельных компонентах, не затрагивают существующий функционал

## Definition of Done

- [x] Все stories completed с acceptance criteria met
- [x] Existing functionality verified through testing
- [x] Integration points working correctly
- [x] Documentation updated appropriately
- [x] No regression in existing features
- [ ] Code review passed
- [ ] QA review passed

## Technical References

**Документация:**

- [front-end-spec.md, строки 610-641](../front-end-spec.md#L610-L641) — макет страницы корзины
- [design-system.json](../frontend/design-system.json) — токены дизайн-системы
- [api-spec.yaml](../api-spec.yaml) — Cart API schemas
- [testing-standards.md](../frontend/testing-standards.md) — стандарты тестирования
- [testing-typescript-recommendations.md](../frontend/testing-typescript-recommendations.md) — TypeScript в тестах

**Зависимости от предыдущих эпиков:**

- Epic 2, Story 2.6: Cart API (backend) ✅ Done
- Epic 12, Story 12.3: Add to Cart (frontend) ✅ Done
- Epic 13: ProductVariant System ✅ Done

## Change Log

| Date       | Version | Description                      | Author     |
| ---------- | ------- | -------------------------------- | ---------- |
| 2025-12-07 | 1.0     | Initial brownfield epic creation | Sarah (PO) |
