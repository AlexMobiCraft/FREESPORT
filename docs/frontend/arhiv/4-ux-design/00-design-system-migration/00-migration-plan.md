# План миграции на Electric Orange Design System

**Версия:** 2.0  
**Дата:** 2026-01-13 (обновлено)  
**Автор:** Saga WDS Analyst Agent  
**Статус:** ✅ Route Groups Architecture — DONE

---

> [!IMPORTANT]
> **Обновление 2026-01-13:** Реализована архитектура Route Groups для изоляции тем.
> См. раздел [Реализованная архитектура](#-реализованная-архитектура-route-groups) ниже.

## 📋 Executive Summary

Данный документ описывает стратегию миграции существующего frontend FREESPORT с текущей сине-голубой цветовой схемы на новую дизайн-систему **Electric Orange** (Digital Brutalism & Kinetic Energy).

### Ключевые принципы редизайна

| Аспект         | Текущий дизайн        | Electric Orange                           |
| -------------- | --------------------- | ----------------------------------------- |
| **Тема**       | Light theme (#FFFFFF) | Dark theme (#0F0F0F)                      |
| **Primary**    | Blue (#0060FF)        | Electric Orange (#FF6B00)                 |
| **Стиль**      | Classic Modern        | Digital Brutalism                         |
| **Геометрия**  | Rounded (4-6px)       | Sharp edges + Skew (-12deg)               |
| **Typography** | Inter                 | Roboto Condensed (display) + Inter (body) |

---

## 🗂️ Инвентаризация страниц для миграции

### Приоритет 1: Core Pages (Критический путь пользователя)

| #   | Страница            | Путь              | Компоненты                                    | Сложность  |
| --- | ------------------- | ----------------- | --------------------------------------------- | ---------- |
| 1.1 | **Главная**         | `/` (page.tsx)    | Hero, Categories, ProductSlider, NewsSection  | 🔴 Высокая |
| 1.2 | **Каталог**         | `/catalog`        | Filters, ProductGrid, Pagination, Breadcrumbs | 🔴 Высокая |
| 1.3 | **Карточка товара** | `/product/[slug]` | Gallery, ProductInfo, AddToCart, Related      | 🟡 Средняя |
| 1.4 | **Корзина**         | `/cart`           | CartItems, CartSummary, PromoCode             | 🟡 Средняя |
| 1.5 | **Checkout**        | `/checkout`       | Steps, Forms, OrderSummary                    | 🔴 Высокая |

### Приоритет 2: Account Pages (Личный кабинет)

| #   | Страница            | Путь                 | Компоненты                  | Сложность  |
| --- | ------------------- | -------------------- | --------------------------- | ---------- |
| 2.1 | **Профиль**         | `/profile`           | ProfileForm, PasswordChange | 🟢 Низкая  |
| 2.2 | **История заказов** | `/profile/orders`    | OrderList, OrderCard        | 🟡 Средняя |
| 2.3 | **Адреса доставки** | `/profile/addresses` | AddressCard, AddressForm    | 🟢 Низкая  |
| 2.4 | **Избранное**       | `/profile/favorites` | ProductGrid (reuse)         | 🟢 Низкая  |
| 2.5 | **B2B Профиль**     | `/profile/company`   | CompanyForm, Requisites     | 🟡 Средняя |

### Приоритет 3: Auth Pages

| #   | Страница            | Путь                     | Компоненты      | Сложность  |
| --- | ------------------- | ------------------------ | --------------- | ---------- |
| 3.1 | **Вход**            | `/(auth)/login`          | LoginForm       | 🟢 Низкая  |
| 3.2 | **Регистрация**     | `/(auth)/register`       | RegisterForm    | 🟢 Низкая  |
| 3.3 | **B2B Регистрация** | `/(auth)/register-b2b`   | B2BRegisterForm | 🟡 Средняя |
| 3.4 | **Сброс пароля**    | `/(auth)/reset-password` | ResetForm       | 🟢 Низкая  |

### Приоритет 4: Static & Content Pages

| #   | Страница       | Путь        | Компоненты          | Сложность  |
| --- | -------------- | ----------- | ------------------- | ---------- |
| 4.1 | **О компании** | `/about`    | ContentBlock, Stats | 🟢 Низкая  |
| 4.2 | **Доставка**   | `/delivery` | InfoCards, Teaser   | 🟢 Низкая  |
| 4.3 | **Партнеры**   | `/partners` | PartnersGrid        | 🟢 Низкая  |
| 4.4 | **Новости**    | `/news`     | NewsGrid, NewsCard  | 🟡 Средняя |
| 4.5 | **Блог**       | `/blog`     | BlogGrid, BlogCard  | 🟡 Средняя |

---

## 🧩 Инвентаризация компонентов

### Layout Components (8 файлов)

```
frontend/src/components/layout/
├── Header
├── Footer
├── MobileMenu
├── Sidebar
└── ...
```

### UI Components (81 файл) — ЯДРО РЕДИЗАЙНА

```
frontend/src/components/ui/
├── Button        → Skewed buttons (-12deg)
├── Input         → Rectangular inputs (0deg)
├── Card          → Dark cards (#1A1A1A)
├── Badge         → Skewed badges
├── Checkbox      → Skewed checkboxes
├── Select        → Dark selects
├── Modal         → Dark modals
├── Tabs          → Skewed tab indicators
└── ...
```

### Business Components (59 файлов)

```
frontend/src/components/business/
├── ProductCard   → Square images, skewed prices
├── CategoryCard  → Grayscale → Color hover
├── FilterPanel   → Dark sidebar
└── ...
```

### Home Components (30 файлов)

```
frontend/src/components/home/
├── HeroBanner    → Full redesign
├── CategorySlider
├── ProductSlider
├── NewsSection
└── ...
```

---

## 🎨 Таблица маппинга цветов

### Backgrounds

| Текущий            | Electric Orange |
| ------------------ | --------------- |
| `#FFFFFF` (body)   | `#0F0F0F`       |
| `#F8FAFC` (subtle) | `#1A1A1A`       |
| `#E3E8F2` (muted)  | `#333333`       |

### Primary Colors

| Текущий                    | Electric Orange       |
| -------------------------- | --------------------- |
| `#0060FF` (primary)        | `#FF6B00`             |
| `#E7F3FF` (primary-subtle) | `rgba(255,107,0,0.1)` |

### Text Colors

| Текущий                    | Electric Orange |
| -------------------------- | --------------- |
| `#1B1B1B` (text-primary)   | `#FFFFFF`       |
| `#4B5C7A` (text-secondary) | `#A0A0A0`       |

### Borders

| Текущий                   | Electric Orange |
| ------------------------- | --------------- |
| `#D0D7E6` (border)        | `#333333`       |
| `#0060FF` (border-active) | `#FF6B00`       |

---

## ✅ Реализованная архитектура (Route Groups)

**Дата реализации:** 2026-01-13

Вместо простого feature flag реализована **полная изоляция тем** через Next.js Route Groups:

```
frontend/src/app/
├── layout.tsx                    # Root: fonts + html/body (без Header/Footer)
├── page.tsx                      # Редирект на основе ACTIVE_THEME
├── globals.css                   # Blue Theme CSS
├── globals-electric-orange.css   # Electric Orange CSS
│
├── (coming-soon)/                # Route Group: Coming Soon
│   ├── layout.tsx
│   └── coming-soon/page.tsx
│
├── (blue)/                       # Route Group: Blue Theme
│   ├── layout.tsx                # globals.css + Header/Footer
│   ├── catalog/, product/, cart/, checkout/, profile/
│   ├── news/, blog/, about/, delivery/, partners/, search/
│   └── (auth)/
│
└── (electric)/                   # Route Group: Electric Orange Theme
    ├── layout.tsx                # globals-electric-orange.css + ElectricHeader/ElectricFooter
    └── electric/
```

### Переключение активной темы

Переменная `ACTIVE_THEME` в `.env` контролирует редирект корневого URL (`/`):

| Значение          | Редирект       | Тема            |
| ----------------- | -------------- | --------------- |
| `coming_soon`     | `/coming-soon` | Заглушка        |
| `blue`            | `/catalog`     | Blue Theme      |
| `electric_orange` | `/electric`    | Electric Orange |

### Преимущества реализации

- ✅ **Полная изоляция CSS** — темы не конфликтуют
- ✅ **Раздельные компоненты** — `Header` vs `ElectricHeader`
- ✅ **Простое переключение** — изменение ENV переменной
- ✅ **Параллельная разработка** — обе темы доступны одновременно

---

## 🔧 Техническая стратегия миграции

### Этап 1: CSS Variables Foundation ✅ DONE

**Статус:** Выполнено (2026-01-02)

1. ✅ Создан файл `globals-electric-orange.css`
2. ✅ Определены все CSS-переменные Electric Orange
3. ✅ Настроен Tailwind config
4. ✅ Реализована архитектура Route Groups для переключения тем

```css
/* globals-electric-orange.css */
:root {
  /* Background */
  --color-bg-body: #0f0f0f;
  --color-bg-card: #1a1a1a;
  --color-bg-input: transparent;

  /* Primary */
  --color-primary: #ff6b00;
  --color-primary-hover: #ff8533;

  /* Text */
  --color-text-primary: #ffffff;
  --color-text-secondary: #a0a0a0;
  --color-text-inverse: #000000;

  /* Border */
  --color-border-subtle: #333333;
  --color-border-active: #ff6b00;

  /* Geometry */
  --skew-angle: -12deg;
  --counter-skew: 12deg;
  --border-radius: 0px;
}
```

### Этап 2: Core UI Components

**Срок: 3-5 дней**

Мигрировать компоненты в порядке зависимостей:

1. **Button** — Skewed container + counter-skewed text
2. **Input** — Rectangular (0deg), transparent bg
3. **Card** — Dark bg, subtle border
4. **Badge** — Skewed badges
5. **Checkbox** — Skewed checkbox container
6. **Select/Dropdown** — Dark theme
7. **Modal** — Dark overlay and content

### Этап 3: Layout Components

**Срок: 2-3 дня**

1. **Header** — Dark bg, orange accents
2. **Footer** — Dark bg
3. **Sidebar** — Dark filter panel
4. **MobileMenu** — Dark overlay

### Этап 4: Business Components

**Срок: 5-7 дней**

1. **ProductCard** — Square 1:1 images, skewed prices
2. **CategoryCard** — Grayscale → Color on hover
3. **FilterPanel** — Skewed headers, dark theme
4. **CartItem** — Dark cards
5. **CheckoutForm** — Rectangular inputs

### Этап 5: Page-Level Migration

**Срок: 5-7 дней**

Мигрировать страницы по приоритетам (см. выше).

---

## ✅ Чек-лист миграции компонента

Для каждого компонента:

- [ ] Заменить hardcoded HEX на CSS-переменные
- [ ] Применить геометрию (skew где нужно)
- [ ] Обновить типографику (Roboto Condensed для display)
- [ ] Проверить состояния (hover, focus, active)
- [ ] Проверить адаптивность (mobile, tablet, desktop)
- [ ] Обновить unit-тесты
- [ ] Визуальное сравнение с дизайн-системой

---

## 📊 Оценка трудозатрат

| Этап      | Описание                      | Срок           |
| --------- | ----------------------------- | -------------- |
| 1         | CSS Variables Foundation      | 1 день         |
| 2         | Core UI Components (7 шт)     | 3-5 дней       |
| 3         | Layout Components (4 шт)      | 2-3 дня        |
| 4         | Business Components (~15 шт)  | 5-7 дней       |
| 5         | Page-Level Migration (~20 шт) | 5-7 дней       |
| 6         | QA & Polish                   | 2-3 дня        |
| **ИТОГО** |                               | **18-26 дней** |

---

## 🚀 Рекомендуемый подход

### Option A: Big Bang (Не рекомендуется)

Полная замена всех компонентов за один релиз.

- ❌ Высокий риск
- ❌ Долгое время до value delivery
- ❌ Сложное тестирование

### Option B: Feature Flag (Рекомендуется) ✅

Параллельное существование двух тем с возможностью переключения.

```typescript
// config/theme.ts
export const THEME = {
  current: process.env.NEXT_PUBLIC_THEME || "classic", // 'classic' | 'electric-orange'
};
```

- ✅ Постепенная миграция
- ✅ A/B тестирование
- ✅ Быстрый rollback
- ✅ Параллельная разработка

### Option C: Page-by-Page (Компромисс)

Миграция по одной странице за раз, начиная с некритичных.

- ✅ Минимальный риск
- ⚠️ Временная визуальная несогласованность
- ✅ Быстрый feedback loop

---

## 📁 Доставка документа

Этот файл сохранен в:

```
docs/4-ux-design/00-design-system-migration/
├── 00-migration-plan.md  ← ВЫ ЗДЕСЬ
├── 01-color-mapping.md   (TODO)
├── 02-component-specs.md (TODO)
└── 03-page-specs.md      (TODO)
```

---

## 🔜 Следующие шаги

1. **Утвердить план** — Получить согласование на подход (Feature Flag рекомендуется)
2. **Создать CSS Foundation** — Этап 1
3. **Начать с Button** — Самый используемый компонент
4. **Итеративно мигрировать** — По чек-листу

---

**Готов к следующему шагу?**
