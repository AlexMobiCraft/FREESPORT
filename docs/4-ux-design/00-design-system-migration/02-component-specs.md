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
  background: var(--color-primary);
  border: none;
  transform: skewX(-12deg);
  
  /* Text */
  color: var(--color-text-inverse);
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  text-transform: uppercase;
  
  /* Inner text container */
  .btn-text {
    transform: skewX(12deg); /* Counter-skew */
  }
}

.btn-primary:hover {
  background: var(--color-text-primary);
  color: var(--color-primary-active);
  box-shadow: var(--shadow-hover);
}

.btn-primary:active {
  background: var(--color-primary-active);
}
```

#### Outline Button

```css
.btn-outline {
  /* Container */
  background: transparent;
  border: 2px solid var(--color-text-primary);
  transform: skewX(-12deg);
  
  /* Text */
  color: var(--color-text-primary);
}

.btn-outline:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
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
  border: 1px solid var(--border-default);
  color: var(--color-text-primary);
  font-family: 'Inter', sans-serif;
  
  /* NO SKEW - inputs are always rectangular */
  transform: none;
  border-radius: 0;
}

.input-default::placeholder {
  color: var(--color-text-muted);
}
```

#### Focus

```css
.input-focus {
  border-color: var(--color-primary);
  outline: none;
  box-shadow: 0 0 0 1px var(--color-primary);
}
```

#### Error

```css
.input-error {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 1px var(--color-danger);
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
  border: 2px solid var(--border-default);
  background: transparent;
  transform: skewX(-12deg);
}

.checkbox-container.checked {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.checkbox-mark {
  transform: skewX(12deg); /* Counter-skew */
  color: var(--color-text-inverse);
}

.checkbox-label {
  font-family: 'Inter', sans-serif;
  color: var(--color-text-primary);
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
  background: var(--color-danger);
  color: var(--color-text-primary);
}

.badge-new {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.badge-hit {
  background: var(--color-success);
  color: var(--color-text-inverse);
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

(Defined in `globals-electric-orange.css`)

```css
.product-card {
  background: var(--bg-card);
  border: 1px solid transparent; /* Starts transparent per reference */
  display: flex;
  flex-direction: column;
  
  /* Strictly defined dimensions */
  width: 100%;
  max-width: 280px;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.product-image-container {
  aspect-ratio: 1 / 1; /* Metric: Strictly Square */
  overflow: hidden;
  position: relative;
  background: #252525; /* Matches reference */
  width: 100%;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s; /* Reference duration */
}

.product-card:hover .product-image {
  transform: scale(1.1); /* Reference scale */
}

/* Typography & Actions */
.product-info {
  padding: 20px;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.product-actions {
  display: flex;
  gap: 10px;
  margin-top: auto; /* Push to bottom */
}

/* Button Size: Flexible but constrained padding */
.product-actions button {
  flex: 1;
  padding: 12px 5px; /* Reference padding */
  white-space: nowrap;
}

/* Price Tag - Skewed -12deg WITHOUT counter-skew on text */
.price-tag {
  transform: skewX(-12deg);
  display: block;
}
```

### Hover Effect

```css
.product-card:hover {
  transform: translateY(-5px);
  border-color: var(--color-primary);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
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

### Размеры

- **Ширина:** 270px
- **Высота:** 270px
- **Соотношение сторон:** 1:1 (квадратная)
- **Сетка:** 4 колонки, gap 20px

### Styles

(Defined in `globals-electric-orange.css`)

```css
.category-card {
  position: relative;
  width: 270px;
  height: 270px;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  cursor: pointer;
  background: var(--bg-card);
}

.category-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: grayscale(100%) contrast(1.2);
  transform: scale(1.01);
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.category-card:hover .category-image {
  filter: grayscale(0%) contrast(1.2);
  transform: scale(1.1);
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
  color: var(--color-text-primary);
  transform: skewX(-12deg);
  text-shadow: 2px 2px 0 #000;
  
  padding: 24px;
}

/* Orange wave overlay on hover */
.category-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 107, 0, 0.4),
    transparent
  );
  transform: skewX(-20deg);
  transition: 1s;
  pointer-events: none;
  z-index: 2;
}

.category-card:hover::after {
  left: 150%;
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
  background: var(--bg-card);
  border: 1px solid var(--border-default);
}

.news-image {
  aspect-ratio: 16 / 9;
  flex-shrink: 0;
  width: 200px;
}

.news-category {
  /* Skewed badge */
  transform: skewX(-12deg);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  padding: 4px 12px;
  font-size: 11px;
  text-transform: uppercase;
}

.news-date {
  font-family: 'Inter', sans-serif;
  color: var(--color-text-muted);
  font-size: 12px;
}

.news-title {
  font-family: 'Inter', sans-serif;
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: 600;
}

.news-excerpt {
  font-family: 'Inter', sans-serif;
  color: var(--color-text-secondary);
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
  background: var(--border-default);
  transform: skewX(-12deg);
}

.slider-fill {
  background: var(--color-primary);
}

.slider-thumb {
  width: 20px;
  height: 20px;
  background: var(--color-primary);
  border: 2px solid var(--color-text-inverse);
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
  border-bottom: 1px solid var(--border-default);
}

.tab-trigger {
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  color: var(--color-text-secondary);
  padding-bottom: 12px;
  position: relative;
}

.tab-trigger.active {
  color: var(--color-text-primary);
}

.tab-trigger.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--color-primary);
  transform: skewX(-12deg);
}

.tab-trigger:hover:not(.active) {
  color: var(--color-primary);
}
```

---

## 🗄️ Sidebar Widget

### Структура

```
┌─────────────────────────────────────┐
│ Sidebar Panel (bg: #1A1A1A)         │
│                                     │
│ ╱════════════════════╲              │
│ │ КАТЕГОРИИ          │ ← Skewed -12°│
│ ╲════════════════════╱              │
│ ───────────────────────             │
│                                     │
│ ╱──╲                                │
│ │✓ │ Кроссфит         ← Checkbox    │
│ ╲──╱                                │
│ ╱──╲                                │
│ │  │ Фитнес                         │
│ ╲──╱                                │
│                                     │
│ ╱════════════════════╲              │
│ │ БРЕНД              │              │
│ ╲════════════════════╱              │
│ ───────────────────────             │
│                                     │
│ ╱──╲                                │
│ │✓ │ Nike                           │
│ ╲──╱                                │
│ ╱──╲                                │
│ │  │ Adidas                         │
│ ╲──╱                                │
│                                     │
│ ╱════════════════════╲              │
│ │ ЦЕНА (₽)           │              │
│ ╲════════════════════╱              │
│ ───────────────────────             │
│                                     │
│ ┌──────────┐ ┌──────────┐           │
│ │   1000   │ │  50000   │ Price     │
│ └──────────┘ └──────────┘           │
│                                     │
│ ╱══════════●══════════╲             │
│     Range Slider (skewed)           │
│                                     │
│ ╱─────────────────────╲             │
│ │     ПРИМЕНИТЬ       │ CTA Button  │
│ ╲─────────────────────╱             │
└─────────────────────────────────────┘
```

### Filter Title Styles

```css
.filter-title {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 900;
  font-size: 1.2rem;
  text-transform: uppercase;
  color: var(--color-text-primary);
  
  /* Skewed -12deg */
  transform: skewX(-12deg);
  transform-origin: left;
  
  display: block;
  width: 100%;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-default);
}

.filter-title-text {
  transform: skewX(12deg);
  display: inline-block;
}
```

### Checkbox Row Styles

```css
.checkbox-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  cursor: pointer;
  user-select: none;
}

.checkbox-row input {
  display: none;
}

/* Skewed Checkbox */
.custom-check {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-neutral-500);
  margin-right: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  transform: skewX(-12deg);
}

.checkbox-row input:checked + .custom-check {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

.checkbox-row input:checked + .custom-check::after {
  content: '✓';
  color: var(--color-text-inverse);
  font-weight: 900;
  font-size: 14px;
  transform: skewX(12deg);
}

.checkbox-row:hover .custom-check {
  border-color: var(--color-primary);
}

.checkbox-text {
  font-family: 'Inter', sans-serif;
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  transition: color 0.15s ease;
}

.checkbox-row:hover .checkbox-text {
  color: var(--color-text-primary);
}
```

### Price Range Styles

```css
.price-inputs-row {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.price-input {
  width: 50%;
  background: transparent;
  border: 1px solid var(--border-default);
  padding: 8px;
  color: var(--color-text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
}

.price-input:focus {
  border-color: var(--color-primary);
  outline: none;
}

/* Skewed Range Slider */
.range-container {
  width: 100%;
  margin: 20px 0;
  transform: skewX(-12deg);
}

input[type='range']::-webkit-slider-thumb {
  height: 18px;
  width: 18px;
  background: var(--color-primary);
  border: 2px solid var(--color-text-inverse);
  cursor: pointer;
}

input[type='range']::-webkit-slider-thumb:hover {
  background: var(--color-text-primary);
}
```

### React Component

```tsx
interface FilterOption {
  id: string;
  label: string;
  count?: number;
}

interface FilterGroup {
  id: string;
  title: string;
  options: FilterOption[];
  type: 'checkbox' | 'price';
}

interface PriceRange {
  min: number;
  max: number;
}

interface ElectricSidebarProps {
  filterGroups: FilterGroup[];
  selectedFilters?: Record<string, string[]>;
  priceRange?: PriceRange;
  currentPrice?: PriceRange;
  onFilterChange?: (groupId: string, optionId: string, checked: boolean) => void;
  onPriceChange?: (range: PriceRange) => void;
  onApply?: () => void;
  className?: string;
}

// Usage Example
<ElectricSidebar
  filterGroups={[
    {
      id: 'categories',
      title: 'КАТЕГОРИИ',
      type: 'checkbox',
      options: [
        { id: 'crossfit', label: 'Кроссфит', count: 24 },
        { id: 'fitness', label: 'Фитнес', count: 156 },
      ],
    },
    {
      id: 'brands',
      title: 'БРЕНД',
      type: 'checkbox',
      options: [
        { id: 'nike', label: 'Nike', count: 45 },
        { id: 'adidas', label: 'Adidas', count: 38 },
      ],
    },
    {
      id: 'price',
      title: 'ЦЕНА (₽)',
      type: 'price',
      options: [],
    },
  ]}
  priceRange={{ min: 1000, max: 50000 }}
  onApply={() => console.log('Apply filters')}
/>
```

### Checkbox Behavior (Updated 2026-01-02)

**State Management:**

- Компонент поддерживает **два режима работы**:
  1. **Controlled Mode** — когда передан `onFilterChange`, состояние управляется внешне через `selectedFilters`
  2. **Uncontrolled Mode** — когда `onFilterChange` не передан, компонент использует внутренний `localSelectedFilters` state

**Визуальное поведение при клике:**

- ✅ Чекбокс **заполняется** оранжевым цветом (#FF6B00)
- ✅ Появляется **галочка** ✓ (чёрного цвета, counter-skewed на 12deg)
- ✅ Граница меняется на оранжевую (#FF6B00)
- ✅ Состояние сохраняется до повторного клика

**Пример внутренней реализации:**

```tsx
// Local state for checkboxes when no external handler is provided
const [localSelectedFilters, setLocalSelectedFilters] = useState<Record<string, string[]>>(
  selectedFilters
);

const handleCheckboxChange = (groupId: string, optionId: string, checked: boolean) => {
  if (onFilterChange) {
    // Use external handler if provided
    onFilterChange(groupId, optionId, checked);
  } else {
    // Use local state
    setLocalSelectedFilters(prev => {
      const currentGroup = prev[groupId] || [];
      if (checked) {
        return { ...prev, [groupId]: [...currentGroup, optionId] };
      } else {
        return { ...prev, [groupId]: currentGroup.filter(id => id !== optionId) };
      }
    });
  }
};
```

### Component File Location

```
frontend/src/components/ui/Sidebar/
├── ElectricSidebar.tsx    # Main component (с локальным state management)
└── index.ts               # Exports
```

---

## 🔖 Section Header

Специальный заголовок для разграничения секций на страницах.

### Visual Style

- **Font:** Roboto Condensed, Bold/Black, Uppercase
- **Geometry:** Skewed container (-12deg), Counter-skewed text (12deg)
- **Decoration:** Orange underline (#FF6B00, 3px)
- **Optional Label:** Small text above main title (Inter, Straight)

### React Component

```tsx
import ElectricSectionHeader from '@/components/ui/SectionHeader/ElectricSectionHeader';

// Basic Usage
<ElectricSectionHeader title="Популярные товары" />

// With Label
<ElectricSectionHeader
  title="Хиты продаж"
  label="Топ выбор"
/>

// Centered
<ElectricSectionHeader
  title="О нас"
  align="center"
/>
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `title` | `string` | - | Main heading text |
| `label` | `string` | - | Small label above title |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | Text size |
| `align` | `'left' \| 'center'` | `'left'` | Alignment |
| `showUnderline` | `boolean` | `true` | Visibility of orange underline |

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

## 🧭 Breadcrumbs (ElectricBreadcrumbs)

### Структура

```
Главная > Каталог > Категория > Товар
   ↑         ↑          ↑         ↑
 Link      Link       Link    Current (bold)
```

### Стилизация

```css
.electric-breadcrumbs {
  font-family: var(--font-body);  /* Inter */
  font-size: 14px;
  /* NO SKEW - breadcrumbs stay straight for readability */
}

.electric-breadcrumbs a {
  color: var(--color-text-secondary);
  transition: color 0.2s;
}

.electric-breadcrumbs a:hover {
  color: var(--color-primary);
}

.electric-breadcrumbs .current {
  color: var(--foreground);
  font-weight: 500;
}
```

### Особенности

- Home иконка для первого элемента (опционально)
- Chevron разделители
- Collapse при > 5 элементов (ellipsis)

---

## 📄 Pagination (ElectricPagination)

### Структура

```
┌────────────────────────────────────────┐
│ [<] [1] [...] [3] [4] [5] [...] [10] [>] │
│      ↑              ↑                    │
│   Skewed       Active (glow)             │
└────────────────────────────────────────┘
```

### Стилизация

```css
.pagination-btn {
  width: 40px;
  height: 40px;
  transform: skewX(-12deg);
  border: 1px solid var(--border-default);
  background: transparent;
  transition: all 0.2s;
}

.pagination-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.pagination-btn.active {
  background: var(--color-primary);
  color: black;
  box-shadow: var(--shadow-glow);
}

.pagination-btn .text {
  transform: skewX(12deg); /* Counter-skew */
}
```

---

## 🪟 Modal (ElectricModal)

### Структура

```
┌─ Overlay (rgba(15,15,15,0.9)) ─────────────────────┐
│                                                     │
│   ┌─ Modal Container (#1A1A1A) ─────────────────┐  │
│   │ ┌─ Header ─────────────────────────────────┐│  │
│   │ │ SKEWED TITLE          [X] (skewed btn)   ││  │
│   │ └──────────────────────────────────────────┘│  │
│   │ ┌─ Content ────────────────────────────────┐│  │
│   │ │ Body text (Inter, straight)              ││  │
│   │ └──────────────────────────────────────────┘│  │
│   │ ┌─ Footer ─────────────────────────────────┐│  │
│   │ │ [Cancel]  [Confirm] ← skewed buttons     ││  │
│   │ └──────────────────────────────────────────┘│  │
│   └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Стилизация

- Overlay: `rgba(15,15,15,0.9)` + `backdrop-blur`
- Container: `bg: #1A1A1A`, `border: 1px solid #333333`
- Title: Roboto Condensed, Bold, Uppercase, `skewX(-12deg)`
- Close button: Skewed box with X icon

---

## 🔔 Toast (ElectricToast)

### Структура

```
┌─────────────────────────────────────────────┐
│ [colored left border]  [Icon] Title     [X] │  ← Skewed container
│                              Message        │
└─────────────────────────────────────────────┘
```

### Variants

| Variant | Border Color | Icon |
|---------|--------------|------|
| success | `--color-success` | CheckCircle |
| error | `--color-danger` | XCircle |
| warning | `--color-warning` | AlertTriangle |
| info | `--color-primary` | Info |

### Стилизация

```css
.electric-toast {
  transform: skewX(-12deg);
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-left: 4px solid; /* color from variant */
}

.electric-toast .content {
  transform: skewX(12deg); /* Counter-skew */
}
```

---

## 🪗 Accordion (ElectricAccordion)

### Структура

```
┌─────────────────────────────────────────┐
│ SKEWED TITLE                        [▼] │ ← Click to expand
├─────────────────────────────────────────┤
│ Content (visible when expanded)         │
│ Inter, regular, straight text           │
└─────────────────────────────────────────┘
```

### Стилизация

- Header: Roboto Condensed, Bold, Uppercase, `skewX(-12deg)`
- Chevron: Orange, rotates 180° when open
- Content: Fade-in animation

---

## 📋 Select (ElectricSelect)

### Структура

```
┌─────────────────────────────────────────┐
│ Placeholder / Selected value        [▼] │ ← Rectangular (0deg)
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Option 1                                │
│ Option 2                            [✓] │ ← Selected
│ Option 3                                │
└─────────────────────────────────────────┘
```

### Особенности

- Trigger: Rectangular (как inputs — 0deg)
- Dropdown: Dark background, hover highlight
- Selected: Checkmark icon

---

## 🔘 RadioButton (ElectricRadioButton)

### Структура

```
[✓] Label    ← Skewed checkbox style (like Sidebar)
```

### Стилизация

```css
.electric-radio {
  width: 20px;
  height: 20px;
  transform: skewX(-12deg);
  border: 2px solid var(--color-neutral-500);
}

.electric-radio.checked {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.electric-radio .checkmark {
  color: black;
  font-weight: bold;
  transform: skewX(12deg); /* Counter-skew */
}
```

### Особенности

- Стиль идентичен checkbox в Sidebar (ElectricSidebar)
- При выборе: оранжевый фон + чёрная галочка
- При hover: оранжевая граница

---

## 💬 Tooltip (ElectricTooltip)

### Позиции

- top, bottom, left, right

### Стилизация

```css
.electric-tooltip {
  transform: skewX(-12deg);
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  padding: 8px 12px;
  font-size: 12px;
}

.electric-tooltip .text {
  transform: skewX(12deg); /* Counter-skew */
}
```

---

## 📊 Table (ElectricTable)

### Структура

```
┌──────────────────────────────────────────────────┐
│ АРТИКУЛ │ НАИМЕНОВАНИЕ │ КОЛ-ВО │    ЦЕНА       │ ← Skewed headers
├──────────────────────────────────────────────────┤
│ BX-001  │ Перчатки     │   2    │ 3 500 ₽       │ ← Alternating rows
│ KM-042  │ Кимоно       │   1    │ 4 200 ₽       │
└──────────────────────────────────────────────────┘
```

### Стилизация

- Headers: Roboto Condensed, Bold, Uppercase, `skewX(-12deg)`
- Rows: Alternating `#0F0F0F` / `#1A1A1A`
- Hover: Left orange border

---

## ⏳ Spinner (ElectricSpinner)

### Структура

```
┌───┐
│   │  ← Skewed square, spinning
└───┘
```

### Sizes

| Size | Dimensions |
|------|------------|
| sm | 20px × 20px |
| md | 32px × 32px |
| lg | 48px × 48px |

### Стилизация

```css
.electric-spinner {
  transform: skewX(-12deg);
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  animation: spin 1s linear infinite;
}
```

---

## ⭐ Features Block (ElectricFeaturesBlock)

### Структура

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    [📦]     │  │    [🛡️]     │  │    [↩️]     │  │    [🎧]     │
│   SKEWED    │  │   SKEWED    │  │   SKEWED    │  │   SKEWED    │
│   TITLE     │  │   TITLE     │  │   TITLE     │  │   TITLE     │
│ Description │  │ Description │  │ Description │  │ Description │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### Стилизация

- Icon container: Skewed border with orange
- Title: Roboto Condensed, Bold, Orange, Skewed
- Description: Inter, Secondary color

---

## 🛒 Cart Widget (ElectricCartWidget)

### Структура

```
┌───────┐
│ 🛒 [3]│ ← Skewed badge with count
└───┬───┘
    │
    ▼
┌─────────────────────────────────┐
│ КОРЗИНА                     [X] │
├─────────────────────────────────┤
│ [img] Товар 1        3 500 ₽ 🗑 │
│ [img] Товар 2        2 800 ₽ 🗑 │
├─────────────────────────────────┤
│ Итого:               6 300 ₽    │
│ [В корзину] [Оформить]          │ ← Skewed buttons
└─────────────────────────────────┘
```

---

## 🔍 Search Results (ElectricSearchResults)

### Структура

```
┌─────────────────────────────────────┐
│ 🔍 Поиск товаров...             [X] │ ← Rectangular input
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ [◇] Перчатки боксерские   [Товар]  │ ← Skewed type badge
│ [img] Шлем для бокса      [Товар]  │
│ [◇] Единоборства       [Категория] │
│ [◇] BOYBO                 [Бренд]  │
└─────────────────────────────────────┘
```

### Особенности

- Input: Rectangular (0deg)
- Keyboard navigation: ArrowUp/Down, Enter, Escape
- Type badges: Skewed

---

## 📁 Связанные документы

- `00-migration-plan.md` — Общий план миграции
- `01-color-mapping.md` — Маппинг цветов
- `design_v2.3.0.json` — Официальные токены

---

**Следующий шаг:** Начать имплементацию CSS foundation и миграцию компонентов.
