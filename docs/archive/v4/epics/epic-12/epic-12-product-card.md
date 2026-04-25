# Epic 12: Карточка товара (Product Detail Page)

## Метаданные

| Поле                    | Значение                                                                                                                                                                                                                                              |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Epic ID**             | 12                                                                                                                                                                                                                                                    |
| **Название**            | Карточка товара (Product Detail Page)                                                                                                                                                                                                                 |
| **Приоритет**           | P0 (критичный)                                                                                                                                                                                                                                        |
| **Длительность**        | 2 недели                                                                                                                                                                                                                                              |
| **Статус**              | Draft                                                                                                                                                                                                                                                 |
| **Зависимости**         | Epic 10 (Фундамент и UI Kit), Epic 11 (Каталог товаров)                                                                                                                                                                                               |
| **Связанные документы** | `docs/frontend-development-plan.md` (раздел 3.1, строки 46-47)<br>`docs/frontend/design-system.json` (компоненты: ProductGallery, ProductSummary, Badge, Button)<br>`docs/api-spec.yaml` (эндпоинты: `/products/{id}`, `/cart/add`, `/favorites/add`) |

---

## Описание Epic

Реализация детальной страницы товара с полной информацией о продукте, галереей изображений, выбором опций (размер, цвет), отображением цены с учетом роли пользователя (B2B/B2C), возможностью добавления в корзину и избранное, блоком характеристик и рекомендациями похожих товаров.

**Стратегическая ценность:**

- Критически важная точка конверсии в e-commerce воронке
- Обеспечивает полную информацию для принятия решения о покупке
- Реализует ролевое ценообразование для B2B/B2C клиентов
- Поддерживает SEO через SSR для индексации товаров

**Технологический стек:**

- Next.js 15.4.6 App Router с динамическим роутом `/product/[slug]`
- SSR (Server-Side Rendering) для SEO оптимизации
- TypeScript 5.0+ для типобезопасности
- Zustand для state management (cartStore)
- Axios для API запросов
- Дизайн-система FREESPORT v2.1.0

---

## Цели и метрики успеха

### Бизнес-метрики

- Конверсия "Просмотр карточки → Добавление в корзину": **> 25%**
- Bounce rate на карточке товара: **< 40%**
- Среднее время на странице: **> 90 секунд**
- Количество просмотров галереи: **> 60%** посетителей

### Технические метрики

- PageSpeed Score: **> 70**
- Time to Interactive (TTI): **< 3.5 секунды**
- Lighthouse SEO Score: **> 95**
- Core Web Vitals: все в зеленой зоне
- Unit тесты покрытие: **> 80%**

---

## User Stories

### Story 12.1: Просмотр детальной информации о товаре

**Как** посетитель сайта (B2C/B2B),
**Я хочу** просматривать детальную информацию о товаре с фотографиями и характеристиками,
**Чтобы** принять обоснованное решение о покупке.

**Acceptance Criteria:**

1. ✅ Страница доступна по URL `/product/[slug]` где slug — SEO-friendly идентификатор
2. ✅ Отображается галерея изображений товара с возможностью увеличения
3. ✅ Показывается название товара, артикул (SKU), бренд, описание
4. ✅ Выводится цена согласно роли пользователя (retail для гостей, wholesale_level1-3 для B2B, trainer_price, federation_price)
5. ✅ Отображается информация о наличии товара (в наличии/под заказ/нет в наличии)
6. ✅ Показывается рейтинг товара и количество отзывов (если доступны)
7. ✅ Блок характеристик товара в структурированном виде
8. ✅ Breadcrumbs навигация: Главная > Категория > Подкатегория > Товар
9. ✅ SEO метатеги корректно заполнены (title, description, OG tags)
10. ✅ Страница рендерится через SSR для SEO

---

### Story 12.2: Выбор опций товара (размер, цвет)

**Как** покупатель,
**Я хочу** выбирать размер и цвет товара перед добавлением в корзину,
**Чтобы** заказать именно тот вариант, который мне нужен.

**Acceptance Criteria:**

1. ✅ Селектор размеров отображается если товар имеет варианты размеров
2. ✅ Селектор цветов отображается если товар доступен в разных цветах
3. ✅ Недоступные опции (нет в наличии) визуально отключены
4. ✅ При выборе опции обновляется основное изображение товара (если есть)
5. ✅ При выборе опции обновляется информация о наличии
6. ✅ Выбранные опции сохраняются при добавлении в корзину
7. ✅ Валидация: нельзя добавить в корзину без выбора обязательных опций

---

### Story 12.3: Добавление товара в корзину

**Как** авторизованный пользователь,
**Я хочу** добавить товар в корзину с выбранным количеством,
**Чтобы** продолжить покупки или оформить заказ.

**Acceptance Criteria:**

1. ✅ Кнопка "В корзину" видна и доступна для товаров в наличии
2. ✅ Возможность выбрать количество товара (с учетом min_order_quantity)
3. ✅ При клике на "В корзину" товар добавляется через API `/cart/items/`
4. ✅ Показывается уведомление об успешном добавлении
5. ✅ Обновляется счетчик товаров в корзине в Header
6. ✅ Товар добавляется в Zustand cartStore
7. ✅ Обработка ошибок (нет на складе, превышен лимит)
8. ✅ Для неавторизованных пользователей — кнопка "Войти для покупки"

---

### Story 12.4: Галерея изображений товара

**Как** покупатель,
**Я хочу** просматривать все изображения товара и увеличивать их,
**Чтобы** детально рассмотреть продукт перед покупкой.

**Acceptance Criteria:**

1. ✅ Основное изображение отображается в размере 520x520px с радиусом 16px
2. ✅ Вертикальная полоса превью (thumbnails) слева от основного изображения
3. ✅ Thumbnails размером 88x88px с gap 12px и радиусом 12px
4. ✅ Выбранный thumbnail подсвечивается рамкой 2px primary
5. ✅ При клике на thumbnail меняется основное изображение
6. ✅ Возможность открыть полноэкранный режим просмотра (lightbox)
7. ✅ Навигация по изображениям в lightbox (стрелки влево/вправо)
8. ✅ Закрытие lightbox по клику вне изображения или на кнопку X
9. ✅ Lazy loading для изображений
10. ✅ Alt текст для всех изображений (accessibility)

---

### Story 12.5: Блок рекомендаций похожих товаров

**Как** покупатель,
**Я хочу** видеть рекомендации похожих товаров,
**Чтобы** найти альтернативы или дополнить свой заказ.

**Acceptance Criteria:**

1. ✅ Секция "Похожие товары" отображается под основным контентом
2. ✅ Показывается 6 товаров в горизонтальной галерее
3. ✅ Используется компонент RecommendationsRow из дизайн-системы
4. ✅ Карточки товаров содержат: изображение, название, цену, рейтинг
5. ✅ При клике на карточку — переход на страницу товара
6. ✅ Данные загружаются из поля `related_products` API `/products/{id}`
7. ✅ Если похожих товаров нет — секция скрывается

---

### Story 12.6: Адаптивная верстка карточки товара

**Как** пользователь мобильного устройства,
**Я хочу** удобно просматривать карточку товара на смартфоне,
**Чтобы** получить всю информацию без проблем с навигацией.

**Acceptance Criteria:**

1. ✅ Desktop (>1024px): двухколоночный layout (галерея 2/3, сводка 1/3)
2. ✅ Tablet (640-1024px): двухколоночный layout с адаптивными отступами
3. ✅ Mobile (<640px): вертикальный стек всех элементов
4. ✅ Галерея на mobile: горизонтальный swipe для изображений
5. ✅ Кнопка "В корзину" зафиксирована внизу экрана на mobile
6. ✅ Все интерактивные элементы имеют минимальный размер 44x44px
7. ✅ Текст читаем на всех разрешениях (минимум body-m)

---

## Технические требования

### Архитектура компонентов

```
src/app/product/[slug]/
├── page.tsx                    # Главная серверная страница (SSR)
├── loading.tsx                 # Skeleton loader
└── error.tsx                   # Error boundary

src/components/product/
├── ProductGallery.tsx          # Галерея изображений
├── ProductSummary.tsx          # Блок цены и CTA
├── ProductOptions.tsx          # Выбор размера/цвета
├── ProductSpecs.tsx            # Таблица характеристик
├── ProductBreadcrumbs.tsx      # Навигационная цепочка
└── __tests__/
    ├── ProductGallery.test.tsx
    ├── ProductSummary.test.tsx
    └── ProductOptions.test.tsx
```

### API Интеграция

**Endpoint:** `GET /api/v1/products/{id}/`

**Response Schema:**

```typescript
interface ProductDetail {
  id: number;
  name: string;
  slug: string;
  sku: string;
  description: string;
  full_description: string;
  category: CategoryBreadcrumb;
  brand: string;
  price: {
    retail: number;
    wholesale: {
      level1: number;
      level2: number;
      level3: number;
    } | null;
    currency: string;
    current: number;
    discount_percent: number | null;
  };
  stock_quantity: number;
  min_order_quantity: number;
  images: ProductImage[];
  rating: number | null;
  reviews_count: number;
  is_available: boolean;
  specifications: Record<string, string>;
  related_products: Product[];
  created_at: string;
}
```

**Add to Cart:** `POST /api/v1/cart/items/`

```typescript
interface CartItemCreate {
  product_id: number;
  quantity: number;
}
```

### Компоненты дизайн-системы

**ProductGallery:**

- `primaryImage`: 520x520px, radius 16px, shadow-default
- `thumbnails`: vertical, 88x88px, gap 12px, radius 12px
- `selectedBorder`: ring-2 ring-primary
- `viewerControls`: lightbox с навигацией

**ProductSummary:**

- `priceBlock`: background bg-panel, radius 20px, shadow-modal, padding 24px
- `ctaPrimary`: background bg-primary, hover bg-primary-hover, radius 16px, height 56px
- `ctaSecondary`: border border-primary, radius 16px, height 56px
- `promoBadge`: background bg-promo, radius 999px

**Badge варианты:**

- `new`: background bg-primary-bg, textColor text-primary
- `hit`: background bg-success-bg, textColor text-success
- `sale`: background bg-danger-bg, textColor text-danger
- `discount`: background bg-neutral-100, textColor text-secondary

### SEO Требования

```typescript
// Метаданные для SSR
export async function generateMetadata({ params }): Promise<Metadata> {
  const product = await fetchProduct(params.slug);

  return {
    title: `${product.name} - ${product.brand} | FREESPORT`,
    description: product.description.substring(0, 160),
    openGraph: {
      title: product.name,
      description: product.description,
      images: [product.images[0].image],
      type: "product",
    },
    alternates: {
      canonical: `/product/${product.slug}`,
    },
  };
}
```

### Состояния и обработка ошибок

**Loading States:**

- Skeleton для галереи и контента
- Shimmer эффект для плейсхолдеров
- Loading spinner для кнопки "В корзину"

**Error States:**

- 404: Товар не найден → показать похожие товары
- 500: Ошибка сервера → показать retry кнопку
- Network error: проверить соединение

**Empty States:**

- Нет изображений → показать placeholder
- Нет характеристик → скрыть блок
- Нет похожих товаров → скрыть секцию

---

## Тестирование

### Unit тесты (Vitest + React Testing Library)

**ProductGallery.test.tsx:**

```typescript
describe("ProductGallery", () => {
  it("renders primary image with correct dimensions", () => {});
  it("renders thumbnails vertically with gap", () => {});
  it("highlights selected thumbnail with border", () => {});
  it("changes primary image on thumbnail click", () => {});
  it("opens lightbox on primary image click", () => {});
  it("navigates through images in lightbox", () => {});
  it("closes lightbox on X button click", () => {});
  it("lazy loads images", () => {});
});
```

**ProductSummary.test.tsx:**

```typescript
describe("ProductSummary", () => {
  it("displays correct price based on user role", () => {});
  it("shows retail price for guest users", () => {});
  it("shows wholesale price for B2B users", () => {});
  it("disables add to cart if out of stock", () => {});
  it("validates minimum order quantity", () => {});
  it("updates cart store on add to cart", () => {});
  it("shows success notification after adding", () => {});
});
```

**ProductOptions.test.tsx:**

```typescript
describe("ProductOptions", () => {
  it("renders size selector if sizes available", () => {});
  it("renders color selector if colors available", () => {});
  it("disables unavailable options", () => {});
  it("updates image on option selection", () => {});
  it("validates required options before add to cart", () => {});
});
```

### Integration тесты (MSW моки)

**product-page.integration.test.tsx:**

```typescript
describe("Product Page Integration", () => {
  it("loads product data from API", () => {});
  it("adds product to cart via API", () => {});
  it("handles 404 for non-existent product", () => {});
  it("shows error on API failure", () => {});
});
```

### E2E тесты (Playwright)

**product-purchase-flow.spec.ts:**

```typescript
test("complete product purchase flow", async ({ page }) => {
  await page.goto("/product/nike-air-max-2025");
  await page.click('[data-testid="size-option-42"]');
  await page.click('[data-testid="color-option-black"]');
  await page.fill('[data-testid="quantity-input"]', "2");
  await page.click('[data-testid="add-to-cart-button"]');
  await expect(page.locator('[data-testid="cart-count"]')).toHaveText("2");
  await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
});
```

### Accessibility тесты

- WCAG 2.1 AA compliance
- Keyboard navigation (Tab, Enter, Escape)
- Screen reader support (ARIA labels)
- Color contrast > 4.5:1
- Focus indicators visible

---

## Definition of Done

### Обязательные критерии

- [ ] ✅ Все user stories завершены и acceptance criteria выполнены
- [ ] ✅ Динамический роут `/product/[slug]` работает с SSR
- [ ] ✅ Компоненты ProductGallery, ProductSummary, ProductOptions реализованы
- [ ] ✅ Интеграция с API `/products/{id}` и `/cart/items/` протестирована
- [ ] ✅ Ролевое ценообразование работает корректно для всех типов пользователей
- [ ] ✅ Галерея изображений с lightbox функционирует
- [ ] ✅ Добавление в корзину обновляет cartStore и Header counter
- [ ] ✅ SEO метатеги корректно генерируются для всех товаров
- [ ] ✅ Breadcrumbs навигация работает
- [ ] ✅ Блок похожих товаров отображается

### Качество кода

- [ ] ✅ TypeScript без `as any` и с полной типизацией
- [ ] ✅ ESLint/Prettier проверки пройдены (0 ошибок)
- [ ] ✅ Code review завершен и замечания устранены
- [ ] ✅ Компоненты соответствуют design-system.json v2.1.0
- [ ] ✅ Нет дублирования кода (DRY принцип)

### Тестирование

- [ ] ✅ Unit тесты: покрытие **> 80%**
- [ ] ✅ Integration тесты с MSW написаны и проходят
- [ ] ✅ E2E тест purchase flow работает
- [ ] ✅ Accessibility тесты пройдены (axe-core)
- [ ] ✅ CI/CD pipeline зелёный

### UX/UI

- [ ] ✅ Адаптивная верстка desktop/tablet/mobile работает
- [ ] ✅ Все интерактивные состояния (hover, active, disabled) реализованы
- [ ] ✅ Loading/Error/Empty states обработаны
- [ ] ✅ Анимации плавные (duration 120-180ms)
- [ ] ✅ PageSpeed Score > 70
- [ ] ✅ Lighthouse SEO Score > 95

### Документация

- [ ] ✅ README обновлён с примерами использования
- [ ] ✅ API интеграция задокументирована
- [ ] ✅ Компоненты имеют JSDoc комментарии
- [ ] ✅ Props интерфейсы задокументированы

### Регрессия

- [ ] ✅ Существующий функционал не сломан
- [ ] ✅ Smoke тесты главной страницы и каталога пройдены
- [ ] ✅ Нет критических багов
- [ ] ✅ Performance не ухудшилась

---

## Риски и митигация

| Риск                                       | Вероятность | Влияние | Митигация                                                           |
| ------------------------------------------ | ----------- | ------- | ------------------------------------------------------------------- |
| **API /products/{id} не готов**            | Низкая      | Высокое | Использовать MSW моки для разработки, параллельная работа backend   |
| **Сложность SSR с динамическими данными**  | Средняя     | Среднее | Использовать generateMetadata для SEO, кэшировать запросы           |
| **Проблемы с производительностью галереи** | Средняя     | Среднее | Lazy loading изображений, оптимизация размеров, WebP формат         |
| **Ролевое ценообразование не работает**    | Низкая      | Высокое | Покрыть тестами все роли, использовать middleware для проверки прав |
| **Превышение сроков (2 недели)**           | Средняя     | Высокое | Декомпозировать на stories, ежедневный трекинг прогресса            |

---

## Зависимости

### От других Epic'ов

- **Epic 10 (Фундамент):** требуется UI Kit (Button, Badge, Card, Modal)
- **Epic 11 (Каталог):** используются компоненты фильтрации и навигации
- **Epic 2 (Backend API):** необходимы эндпоинты `/products/{id}`, `/cart/items/`

### Для других Epic'ов

- **Epic 15 (Корзина):** предоставляет функционал добавления товаров
- **Epic 13 (Поиск):** карточки товаров из результатов поиска ведут сюда
- **Epic 17 (Личный кабинет):** история заказов ссылается на карточки товаров

---

## Следующие шаги

1. ✅ **Утвердить Epic** с заказчиком и командой
2. 🔄 **Декомпозировать на tasks** для каждой story
3. 🔄 **Создать feature branch** `feature/epic-12-product-card`
4. 🔄 **Настроить MSW моки** для `/products/{id}`
5. 🔄 **Начать разработку** со Story 12.1 (базовая структура страницы)
6. 🔄 **Еженедельный review** прогресса с PM

---

## Change Log

| Date       | Version | Description                                             | Author     |
| ---------- | ------- | ------------------------------------------------------- | ---------- |
| 2025-11-30 | 1.0     | Создание Epic 12 на основе frontend-epics-10-19-plan.md | Sarah (PO) |

---

## Приложения

### Пример URL структуры

```
/product/nike-air-max-2025
/product/adidas-ultraboost-22-black
/product/reebok-crossfit-nano-x3
```

### Пример TypeScript типов

```typescript
// src/types/product.ts
export interface ProductDetailProps {
  product: ProductDetail;
  userRole: UserRole;
}

export type UserRole =
  | "retail"
  | "wholesale_level1"
  | "wholesale_level2"
  | "wholesale_level3"
  | "trainer"
  | "federation_rep"
  | "admin";

export interface ProductImage {
  id: number;
  image: string;
  alt_text: string;
  is_primary: boolean;
}
```

### Пример компонента ProductGallery

```typescript
// src/components/product/ProductGallery.tsx
'use client';

import { useState } from 'react';
import Image from 'next/image';
import { ProductImage } from '@/types/product';

interface ProductGalleryProps {
  images: ProductImage[];
  productName: string;
}

export default function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [selectedImage, setSelectedImage] = useState(0);
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);

  return (
    <div className="flex gap-3">
      {/* Thumbnails */}
      <div className="flex flex-col gap-3">
        {images.map((img, idx) => (
          <button
            key={img.id}
            onClick={() => setSelectedImage(idx)}
            className={`
              w-[88px] h-[88px] rounded-xl overflow-hidden
              ${idx === selectedImage ? 'ring-2 ring-primary' : ''}
            `}
          >
            <Image
              src={img.image}
              alt={img.alt_text}
              width={88}
              height={88}
              className="object-cover"
            />
          </button>
        ))}
      </div>

      {/* Primary Image */}
      <div
        className="w-[520px] h-[520px] rounded-2xl shadow-default overflow-hidden cursor-pointer"
        onClick={() => setIsLightboxOpen(true)}
      >
        <Image
          src={images[selectedImage].image}
          alt={images[selectedImage].alt_text}
          width={520}
          height={520}
          className="object-cover"
          priority
        />
      </div>

      {/* Lightbox (Modal) */}
      {isLightboxOpen && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center">
          {/* Implementation */}
        </div>
      )}
    </div>
  );
}
```

---

**Документ готов к использованию для начала разработки Epic 12.**
