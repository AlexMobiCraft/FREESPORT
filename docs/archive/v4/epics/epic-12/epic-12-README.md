# Epic 12: Карточка товара - Summary

## Общая информация

**Epic ID:** 12
**Название:** Карточка товара (Product Detail Page)
**Приоритет:** P0 (критичный)
**Длительность:** 2 недели
**Статус:** Draft

## Документы Epic

- **Главный документ:** [epic-12-product-card.md](./epic-12-product-card.md)
- **Базовый план:** [frontend-epics-10-19-plan.md](./frontend-epics-10-19-plan.md) (строки 147-168)

## User Stories

### ✅ Story 12.1: Просмотр детальной информации о товаре

**Файл:** [12.1.product-detail-view.md](../stories/12.1.product-detail-view.md)

**Основная функциональность:**

- Динамический роут `/product/[slug]` с SSR
- Отображение всех данных товара (название, SKU, бренд, описание)
- Ролевое ценообразование (B2C/B2B)
- Breadcrumbs навигация
- SEO метатеги и structured data

**Ключевые компоненты:**

- `src/app/product/[slug]/page.tsx` (SSR страница)
- `src/components/product/ProductInfo.tsx`
- `src/components/product/ProductBreadcrumbs.tsx`
- `src/components/product/ProductSpecs.tsx`
- `src/services/productsService.ts`
- `src/utils/pricing.ts` (ролевое ценообразование)

**API:** `GET /api/v1/products/{id}/`

---

### ✅ Story 12.2: Выбор опций товара (размер, цвет)

**Файл:** [12.2.product-options.md](../stories/12.2.product-options.md)

**Основная функциональность:**

- Селекторы размеров и цветов (Chip компоненты)
- Отключение недоступных опций
- Обновление изображения при выборе цвета
- Валидация обязательных опций перед добавлением в корзину

**Ключевые компоненты:**

- `src/components/product/ProductOptions.tsx`

**TypeScript интерфейсы:**

```typescript
interface ProductOption {
  id: string;
  name: string;
  type: "size" | "color";
  value: string;
  available: boolean;
  image_url?: string;
  color_hex?: string;
}
```

---

### ✅ Story 12.3: Добавление товара в корзину

**Файл:** [12.3.add-to-cart.md](../stories/12.3.add-to-cart.md)

**Основная функциональность:**

- Кнопка "В корзину" с выбором количества
- Интеграция с API `/cart/items/`
- Обновление Zustand cartStore
- Обновление счетчика в Header
- Toast уведомления (success/error)
- Обработка неавторизованных пользователей

**Ключевые компоненты:**

- `src/components/product/ProductSummary.tsx`
- `src/services/cartService.ts`
- `src/stores/cartStore.ts`
- `src/components/layout/Header.tsx` (UPDATE - cart counter)

**API:** `POST /api/v1/cart/items/`

---

### ✅ Story 12.4: Галерея изображений товара

**Файл:** [12.4.product-gallery.md](../stories/12.4.product-gallery.md)

**Основная функциональность:**

- Основное изображение 520x520px
- Вертикальные thumbnails 88x88px
- Lightbox для полноэкранного просмотра
- Навигация стрелками влево/вправо
- Keyboard shortcuts (Arrow keys, Escape)
- Lazy loading изображений

**Ключевые компоненты:**

- `src/components/product/ProductGallery.tsx`
- `src/components/common/Lightbox.tsx`

**Дизайн спецификация:**

- Primary image: 520x520px, radius 16px, shadow-default
- Thumbnails: 88x88px, gap 12px, radius 12px
- Selected: ring-2 ring-primary

---

### ✅ Story 12.5: Блок рекомендаций похожих товаров

**Файл:** [12.5.related-products.md](../stories/12.5.related-products.md)

**Основная функциональность:**

- Секция "Похожие товары" (RecommendationsRow)
- Горизонтальная галерея с 6 карточками товаров
- Scroll-snap навигация
- Hover эффекты на карточках
- Автоматическое скрытие если нет похожих товаров

**Ключевые компоненты:**

- `src/components/product/RelatedProducts.tsx`
- `src/components/product/ProductCard.tsx`

**Data source:** `product.related_products` массив из API

---

### ✅ Story 12.6: Адаптивная верстка карточки товара

**Файл:** [12.6.responsive-layout.md](../stories/12.6.responsive-layout.md)

**Основная функциональность:**

- Responsive layout для desktop/tablet/mobile
- Desktop: 2-колоночный grid (галерея 2/3, сводка 1/3)
- Mobile: вертикальный стек
- Фиксированная кнопка "В корзину" внизу на mobile
- Горизонтальный swipe для галереи на mobile
- Touch targets минимум 44x44px

**Breakpoints:**

- Mobile: 0-639px
- Tablet: 640-1023px
- Desktop: 1024px+

**Адаптированные компоненты:**

- `ProductGallery` - swipe на mobile
- `ProductSummary` - фиксированная кнопка на mobile
- `Breadcrumbs` - truncate на mobile
- `ProductSpecs` - вертикальный стек на mobile

---

## Технический Stack

### Frontend

- Next.js 15.4.6 App Router (SSR)
- TypeScript 5.0+
- Zustand 4.5.7 (cartStore)
- Tailwind CSS 4.0
- Lucide React (иконки)

### Testing

- Vitest 2.1.5
- React Testing Library 16.3.0
- MSW 2.12.2 (API моки)
- Playwright (E2E тесты)

### API Endpoints

- `GET /api/v1/products/{id}/` - детали товара
- `POST /api/v1/cart/items/` - добавление в корзину

---

## Структура файлов

```
frontend/src/
├── app/
│   └── product/
│       └── [slug]/
│           ├── page.tsx          # SSR страница (Story 12.1)
│           ├── loading.tsx       # Skeleton loader
│           └── error.tsx         # Error boundary
├── components/
│   ├── product/
│   │   ├── ProductGallery.tsx    # Story 12.4
│   │   ├── ProductSummary.tsx    # Story 12.3
│   │   ├── ProductOptions.tsx    # Story 12.2
│   │   ├── ProductInfo.tsx       # Story 12.1
│   │   ├── ProductSpecs.tsx      # Story 12.1
│   │   ├── ProductBreadcrumbs.tsx # Story 12.1
│   │   ├── ProductCard.tsx       # Story 12.5
│   │   ├── RelatedProducts.tsx   # Story 12.5
│   │   └── __tests__/
│   │       ├── ProductGallery.test.tsx
│   │       ├── ProductSummary.test.tsx
│   │       ├── ProductOptions.test.tsx
│   │       └── ...
│   ├── common/
│   │   ├── Lightbox.tsx          # Story 12.4
│   │   └── __tests__/
│   │       └── Lightbox.test.tsx
│   └── layout/
│       └── Header.tsx            # UPDATE - cart counter (Story 12.3)
├── services/
│   ├── productsService.ts        # Story 12.1
│   └── cartService.ts            # Story 12.3
├── stores/
│   └── cartStore.ts              # Story 12.3
├── utils/
│   └── pricing.ts                # Story 12.1 (ролевое ценообразование)
└── types/
    ├── product.ts                # ProductDetail, ProductOption interfaces
    └── cart.ts                   # CartItem interfaces
```

---

## Definition of Done

### Функциональность

- [x] Все 6 user stories завершены
- [ ] Все acceptance criteria выполнены
- [ ] API интеграция протестирована
- [ ] Ролевое ценообразование работает для всех типов пользователей

### Качество кода

- [ ] TypeScript без `as any`
- [ ] ESLint/Prettier проверки пройдены
- [ ] Code review завершён
- [ ] Компоненты соответствуют design-system.json v2.1.0

### Тестирование

- [ ] Unit тесты покрытие > 80%
- [ ] Integration тесты с MSW
- [ ] E2E тест purchase flow (Playwright)
- [ ] Accessibility тесты (axe-core)

### UX/UI

- [ ] Адаптивная верстка работает на всех устройствах
- [ ] PageSpeed Score > 70
- [ ] Lighthouse SEO Score > 95
- [ ] Core Web Vitals в зелёной зоне

---

## Метрики успеха

**Бизнес-метрики:**

- Конверсия "Просмотр → Добавление в корзину": **> 25%**
- Bounce rate: **< 40%**
- Среднее время на странице: **> 90 секунд**

**Технические метрики:**

- PageSpeed Score: **> 70**
- Time to Interactive: **< 3.5 секунды**
- Lighthouse SEO: **> 95**
- Unit тесты coverage: **> 80%**

---

## Зависимости

**Требуется от:**

- Epic 10 (Фундамент и UI Kit)
- Epic 11 (Каталог товаров)
- Epic 2 (Backend API)

**Блокирует:**

- Epic 15 (Корзина) - использует функционал добавления товаров
- Epic 13 (Поиск) - карточки товаров из результатов поиска
- Epic 17 (Личный кабинет) - история заказов ссылается на карточки

---

## Следующие шаги

1. ✅ Epic 12 создан
2. ✅ Stories 12.1-12.6 созданы
3. 🔄 **Утвердить Epic** с заказчиком
4. 🔄 **Создать feature branch** `feature/epic-12-product-card`
5. 🔄 **Настроить MSW моки** для `/products/{id}`
6. 🔄 **Начать разработку** со Story 12.1

---

**Дата создания:** 2025-11-30
**Автор:** Sarah (Product Owner)
**Статус:** ✅ Готов к разработке
