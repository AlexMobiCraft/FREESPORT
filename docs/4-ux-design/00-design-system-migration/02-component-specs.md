# Electric Orange Component Specifications

**Версия:** 1.0  
**Дата:** 2026-01-02  
**Автор:** Saga WDS Analyst Agent  
**Статус:** 📋 Reference Document

---

## 📐 Базовые принципы

### Геометрия

```
Skew Angle:      -12deg (для интерактивных элементов)
Counter Skew:    12deg (для текста внутри скошенных контейнеров)
Border Radius:   0px (все углы острые)
```

### Типографика

```
Display Font:    'Roboto Condensed', sans-serif
Body Font:       'Inter', sans-serif
Display Weight:  900 (Black)
Display Style:   Normal (NOT italic) + transform: skewX(-12deg)
```

---

## 🔘 Button

### Структура

```
┌─────────────────────────────────────┐
│ Container (skewed -12deg)           │
│   ┌─────────────────────────────┐   │
│   │ Text (counter-skewed 12deg) │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Variants

#### Primary Button

```css
.btn-primary {
  /* Container */
  background: #FF6B00;
  border: none;
  transform: skewX(-12deg);
  
  /* Text */
  color: #000000;
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  text-transform: uppercase;
  
  /* Inner text container */
  .btn-text {
    transform: skewX(12deg); /* Counter-skew */
  }
}

.btn-primary:hover {
  background: #FF8533;
  box-shadow: 0 0 20px rgba(255, 107, 0, 0.4);
}

.btn-primary:active {
  background: #E55A00;
}
```

#### Outline Button

```css
.btn-outline {
  /* Container */
  background: transparent;
  border: 2px solid #FFFFFF;
  transform: skewX(-12deg);
  
  /* Text */
  color: #FFFFFF;
}

.btn-outline:hover {
  border-color: #FF6B00;
  color: #FF6B00;
}
```

### Sizes

| Size | Height | Padding X | Font Size |
|------|--------|-----------|-----------|
| **Small** | 36px | 16px | 14px |
| **Medium** | 44px | 24px | 16px |
| **Large** | 56px | 32px | 18px |

### React Component

```tsx
interface ButtonProps {
  variant: 'primary' | 'outline' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  fullWidth?: boolean;
}

// Tailwind Classes
const buttonStyles = {
  base: 'transform -skew-x-12 transition-all duration-300',
  primary: 'bg-primary text-black hover:bg-primary-hover hover:shadow-glow',
  outline: 'bg-transparent border-2 border-white text-white hover:border-primary hover:text-primary',
  textWrapper: 'transform skew-x-12 uppercase font-semibold',
};
```

---

## 📝 Input (Text Field)

### Структура

```
┌─────────────────────────────────────┐
│ Container (RECTANGULAR - 0deg)      │
│ Border: 1px solid #333333           │
│ Background: transparent             │
│                                     │
│ Placeholder / Value                 │
└─────────────────────────────────────┘
```

### States

#### Default

```css
.input-default {
  background: transparent;
  border: 1px solid #333333;
  color: #FFFFFF;
  font-family: 'Inter', sans-serif;
  
  /* NO SKEW - inputs are always rectangular */
  transform: none;
  border-radius: 0;
}

.input-default::placeholder {
  color: #666666;
}
```

#### Focus

```css
.input-focus {
  border-color: #FF6B00;
  outline: none;
  box-shadow: 0 0 0 1px #FF6B00;
}
```

#### Error

```css
.input-error {
  border-color: #EF4444;
  box-shadow: 0 0 0 1px #EF4444;
}
```

### Sizes

| Size | Height | Padding | Font Size |
|------|--------|---------|-----------|
| **Small** | 36px | 12px | 14px |
| **Medium** | 44px | 16px | 16px |
| **Large** | 52px | 20px | 18px |

---

## ✅ Checkbox

### Структура

```
╱───╲
│ ✓ │  ← Skewed container (-12deg)
╲───╱   Check mark counter-skewed (12deg)
   Label text (straight, 0deg)
```

### Styles

```css
.checkbox-container {
  width: 20px;
  height: 20px;
  border: 2px solid #333333;
  background: transparent;
  transform: skewX(-12deg);
}

.checkbox-container.checked {
  background: #FF6B00;
  border-color: #FF6B00;
}

.checkbox-mark {
  transform: skewX(12deg); /* Counter-skew */
  color: #000000;
}

.checkbox-label {
  font-family: 'Inter', sans-serif;
  color: #FFFFFF;
  transform: none; /* Straight text */
}
```

---

## 🏷️ Badge

### Структура

```
╱─────────────╲
│ SALE -20%   │  ← Skewed badge
╲─────────────╱
```

### Variants

```css
/* Base */
.badge {
  transform: skewX(-12deg);
  padding: 4px 12px;
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 12px;
}

.badge-text {
  transform: skewX(12deg);
}

/* Variants */
.badge-sale {
  background: #EF4444;
  color: #FFFFFF;
}

.badge-new {
  background: #FF6B00;
  color: #000000;
}

.badge-hit {
  background: #22C55E;
  color: #000000;
}
```

---

## 🎴 Product Card

### Структура

```
┌─────────────────────────────────────┐
│ ┌─────────────────────────────────┐ │
│ │                                 │ │
│ │      IMAGE (Square 1:1)         │ │
│ │      Object-fit: cover          │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Brand Name (Inter, gray)            │
│ Product Title (Inter, white)        │
│                                     │
│ ╱─────────╲                         │
│ │ 7 990 ₽ │ ← Skewed price tag     │
│ ╲─────────╱                         │
│                                     │
│ ╱─────────────────╲ ╱─────────────╲ │
│ │  ADD TO CART    │ │     ♡       │ │
│ ╲─────────────────╱ ╲─────────────╱ │
└─────────────────────────────────────┘
```

### Styles

```css
.product-card {
  background: #1A1A1A;
  border: 1px solid #333333;
  /* NO SKEW - card is rectangular */
}

.product-image {
  aspect-ratio: 1 / 1;
  object-fit: cover;
  filter: grayscale(0);
  transition: filter 0.3s ease;
}

.product-card:hover .product-image {
  filter: brightness(1.1);
}

.product-brand {
  font-family: 'Inter', sans-serif;
  color: #A0A0A0;
  font-size: 12px;
  text-transform: uppercase;
}

.product-title {
  font-family: 'Inter', sans-serif;
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 500;
}

.product-price {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 700;
  font-size: 24px;
  color: #FF6B00;
  transform: skewX(-12deg);
}

.product-price-text {
  transform: skewX(12deg);
}

.product-actions {
  display: flex;
  gap: 8px;
}
```

### Hover Effect

```css
.product-card:hover {
  border-color: #FF6B00;
  box-shadow: 0 0 20px rgba(255, 107, 0, 0.15);
}
```

---

## 🗂️ Category Card

### Структура

```
┌─────────────────────────────────────┐
│                                     │
│      IMAGE (Grayscale → Color)      │
│                                     │
│ ╱─────────────────────────────────╲ │
│ │       CATEGORY TITLE            │ │
│ ╲─────────────────────────────────╱ │
└─────────────────────────────────────┘
```

### Styles

```css
.category-card {
  position: relative;
  aspect-ratio: 1 / 1;
  overflow: hidden;
}

.category-image {
  filter: grayscale(100%);
  transition: filter 0.3s ease;
}

.category-card:hover .category-image {
  filter: grayscale(0);
}

.category-title {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 900;
  font-size: 1.8rem;
  text-transform: uppercase;
  color: #FFFFFF;
  transform: skewX(-12deg);
  
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  padding: 20px;
}

.category-title-text {
  transform: skewX(12deg);
}

/* Flash overlay on hover */
.category-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    transparent 40%,
    rgba(255, 107, 0, 0.3) 50%,
    transparent 60%
  );
  transform: translateX(-100%);
  transition: transform 0.5s ease;
}

.category-card:hover::after {
  transform: translateX(100%);
}
```

---

## 📰 News Card

### Структура

```
┌─────────────────────────────────────────────────┐
│ ┌───────────────┐                               │
│ │               │  ╱──────────╲                 │
│ │    IMAGE      │  │ CATEGORY │ ← Skewed badge │
│ │   (16:9)      │  ╲──────────╱                 │
│ │               │                               │
│ └───────────────┘  15 января 2026               │
│                                                 │
│                    Заголовок новости            │
│                    (Inter, white)               │
│                                                 │
│                    Краткое описание...          │
│                    (Inter, gray)                │
└─────────────────────────────────────────────────┘
```

### Styles

```css
.news-card {
  display: flex;
  gap: 20px;
  background: #1A1A1A;
  border: 1px solid #333333;
}

.news-image {
  aspect-ratio: 16 / 9;
  flex-shrink: 0;
  width: 200px;
}

.news-category {
  /* Skewed badge */
  transform: skewX(-12deg);
  background: #FF6B00;
  color: #000000;
  padding: 4px 12px;
  font-size: 11px;
  text-transform: uppercase;
}

.news-date {
  font-family: 'Inter', sans-serif;
  color: #666666;
  font-size: 12px;
}

.news-title {
  font-family: 'Inter', sans-serif;
  color: #FFFFFF;
  font-size: 18px;
  font-weight: 600;
}

.news-excerpt {
  font-family: 'Inter', sans-serif;
  color: #A0A0A0;
  font-size: 14px;
}
```

---

## 🎚️ Range Slider

### Структура

```
╱═══════════════●═══════════════╲
   ↑ Track      ↑ Thumb
   Skewed       Skewed
```

### Styles

```css
.slider-track {
  height: 6px;
  background: #333333;
  transform: skewX(-12deg);
}

.slider-fill {
  background: #FF6B00;
}

.slider-thumb {
  width: 20px;
  height: 20px;
  background: #FF6B00;
  border: 2px solid #000000;
  transform: skewX(-12deg);
  cursor: pointer;
}

.slider-thumb:hover {
  box-shadow: 0 0 10px rgba(255, 107, 0, 0.5);
}
```

---

## 🏷️ Tabs

### Структура

```
┌────────────────────────────────────────────────┐
│ [ОПИСАНИЕ]  [ХАРАКТЕРИСТИКИ]  [ОТЗЫВЫ (12)]    │
│  ╱═══════╲                                     │
│  Active indicator (skewed)                     │
└────────────────────────────────────────────────┘
```

### Styles

```css
.tabs-list {
  display: flex;
  gap: 32px;
  border-bottom: 1px solid #333333;
}

.tab-trigger {
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  color: #A0A0A0;
  padding-bottom: 12px;
  position: relative;
}

.tab-trigger.active {
  color: #FFFFFF;
}

.tab-trigger.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 3px;
  background: #FF6B00;
  transform: skewX(-12deg);
}

.tab-trigger:hover:not(.active) {
  color: #FF6B00;
}
```

---

## 🧭 Header

### Структура

```
┌─────────────────────────────────────────────────────────────────┐
│ ╱═══════════╲                                                   │
│ │ FREESPORT │  КАТАЛОГ  БРЕНДЫ  НОВОСТИ  [🔍] [♡] [🛒3] [👤]   │
│ ╲═══════════╱                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Styles

```css
.header {
  background: #0F0F0F;
  border-bottom: 1px solid #333333;
  padding: 16px 0;
}

.header-logo {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 900;
  font-size: 24px;
  color: #FFFFFF;
  text-transform: uppercase;
  transform: skewX(-12deg);
}

.header-logo-text {
  transform: skewX(12deg);
}

.header-nav-link {
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  color: #A0A0A0;
  text-transform: uppercase;
  font-size: 14px;
}

.header-nav-link:hover,
.header-nav-link.active {
  color: #FF6B00;
}

.header-icon {
  color: #FFFFFF;
  width: 24px;
  height: 24px;
}

.header-icon:hover {
  color: #FF6B00;
}

.header-cart-badge {
  background: #FF6B00;
  color: #000000;
  font-size: 10px;
  font-weight: 700;
  border-radius: 50%;
  min-width: 18px;
  height: 18px;
}
```

---

## 📱 Mobile Considerations

### Touch Targets

- Minimum touch target: **44x44px**
- Button padding увеличивается на mobile

### Skew на Mobile

- Skew angle сохраняется (`-12deg`)
- Размеры элементов адаптируются
- Touch feedback: glow effect

---

## ✅ Component Migration Checklist

Для каждого компонента:

- [ ] Background: dark colors (`#0F0F0F` / `#1A1A1A`)
- [ ] Primary accent: `#FF6B00`
- [ ] Text: white on dark
- [ ] Borders: `#333333`
- [ ] Skew applied where needed
- [ ] Counter-skew for inner text
- [ ] Hover states with glow
- [ ] Focus states visible
- [ ] Mobile responsive
- [ ] Accessibility (contrast, focus)

---

## 📁 Связанные документы

- `00-migration-plan.md` — Общий план миграции
- `01-color-mapping.md` — Маппинг цветов
- `design_v2.3.0.json` — Официальные токены

---

**Следующий шаг:** Начать имплементацию CSS foundation и миграцию компонентов.
