# Electric Orange Component Specifications

**Версия:** 2.3.1  
**Дата:** 2026-01-05  
**Статус:** ✅ Verified Implementation  
**Source:** `design.json` & Codebase Audit

---

## 🔘 Button `(ElectricButton)`

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricButton` | `src/components/ui/Button/ElectricButton.tsx` |
| **Geometry** | Skewed `-12deg` | Container transform |
| **Text** | Counter-skewed `12deg` | To appear upright |
| **Typography** | `Roboto Condensed`, Uppercase | Bold weight |
| **Border Radius** | `0px` | Strict |

### Visual Variants

#### Primary

- **Background:** `var(--color-primary)` (#FF6B00)
- **Text:** Black (Inverse)
- **Hover:** Background White, Text Orange, Shadow Glow

#### Outline

- **Background:** Transparent
- **Border:** 2px Solid White
- **Text:** White
- **Hover:** Border Orange, Text Orange

---

## 📝 Input `(ElectricInput)`

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricInput` | `src/components/ui/Input/ElectricInput.tsx` |
| **Geometry** | **Rectangular (0deg)** | NO skew for readability |
| **Border** | 1px Solid `var(--border-default)` | Dark Gray (#333) |
| **Background** | Transparent | |
| **Focus** | Border `var(--color-primary)` | Orange focus ring |
| **Typography** | `Inter` (Body) | |

---

## ✅ Checkbox `(ElectricCheckbox)`

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricCheckbox` | `src/components/ui/Checkbox/ElectricCheckbox.tsx` |
| **Container** | Skewed `-12deg` | 20x20px |
| **Checkmark** | Counter-skewed `12deg` | Black color |
| **Active State** | Orange Background | Filled when checked |
| **Label** | **Straight (0deg)** | Inter font |

---

## 🎴 Product Card `(ElectricProductCard)`

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricProductCard` | `src/components/ui/ProductCard` |
| **Structure** | Vertical Layout | |
| **Image** | **Strictly Square (1:1)** | `aspect-square`, `object-fit: cover` |
| **Interaction** | **Physical Lift** | `hover:-translate-y-[5px]` |
| **Price Tag** | Skewed `-12deg` | Roboto Condensed, Bold, Orange |
| **Actions** | Always Visible | "Add to Cart" + "Wishlist" |

### Interaction Details

On hover:

1. Border becomes Orange.
2. Shadow appears (Glow).
3. Card lifts up by 5px.
4. Image scales up slightly (105%).

---

## 🍞 Toast Notification `(ElectricToast)`

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricToast` | `src/components/ui/Toast/ElectricToast.tsx` |
| **Geometry** | Skewed `-12deg` | |
| **Animation In** | `slideInRight` (180ms) | From right edge |
| **Animation Out** | `slideOutRight` (280ms) | To right edge |
| **Position** | Top Right | Fixed, z-index 50 |

---

## 🌀 Spinner `(ElectricSpinner)`

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricSpinner` | `src/components/ui/Spinner/ElectricSpinner.tsx` |
| **Structure** | Parallelogram `-12deg` | No border, no background |
| **Animation** | Sequential Bar Fill | Bars appear one by one |
| **Duration** | 1.2s per cycle | Loop |
| **Sizes** | sm, md, lg | Bar count varies (5, 6, 7) |

---

## 🗺️ Breadcrumb `(ElectricBreadcrumbs)`

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricBreadcrumbs` | `src/components/ui/Breadcrumb` |
| **Geometry** | **Rectangular (0deg)** | No skew for links |
| **Typography** | `Inter` 14px | |
| **Colors** | Secondary (Default) | Primary (Hover/Active) |
| **Separator** | Chevron `>` | Gray color |

---

## 📋 General Rules Checklist (Developers)

When creating new components:

1. **Is it interactive?** (Button, Badge, Checkbox, Tab) -> **SKEW IT (-12deg)**.
2. **Is it a container/input?** (Card, Input, Modal window) -> **KEEP IT STRAIGHT (0deg)**.
3. **Border Radius:** ALWAYS 0px.
4. **Fonts:** `Roboto Condensed` for Uppercase Headers; `Inter` for everything else.

---

## 📐 Layout Rules (Critical)

### Flex Child Overflow Fix

When using Flexbox layouts where a flex child contains a CSS Grid or large images:

```css
/* REQUIRED: Prevents content from expanding flex child beyond parent */
.flex-child-with-grid {
  min-width: 0; /* or min-w-0 in Tailwind */
}
```

**Problem:** Flex children have `min-width: auto` by default, which allows intrinsic content (like large images) to expand the container.

**Solution:** Add `min-w-0` to any flex child that contains:

- CSS Grid with `1fr` columns
- Large images (especially product images)
- Any content that could exceed the parent's width

### Grid Container Constraints

Grid containers inside flex layouts require:

1. `min-w-0` on the flex parent (the `<main>` or content area)
2. `w-full` or explicit `max-width` on the grid container

**Example (Catalog Page):**

```tsx
<div className="flex gap-8">
  <aside className="w-[280px] flex-shrink-0">...</aside>
  <main className="flex-1 min-w-0"> {/* <-- CRITICAL */}
    <div className="grid grid-cols-4 gap-2">...</div>
  </main>
</div>
```

---
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

## 🎛️ Sidebar Widget (ElectricSidebar)

### Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Component** | `ElectricSidebar` | `src/components/ui/Sidebar/ElectricSidebar.tsx` |
| **Headers** | Skewed `-12deg` | Uppercase, Border-bottom |
| **Filters** | Checkbox / Price | |
| **Price Slider** | **Dual Thumb** | Skewed `-12deg`. Min/Max configurable. |

### Price Range Detail (PriceRangeSlider)

- **Input Fields:** Rectangular `0deg` (From / To).
- **Slider Track:** Skewed `-12deg`.
- **Thumbs:** Square skewed `-12deg`.
- **Logic:** Dual-thumb (allows selecting both min and max).
- **Default Min:** `1` (Updated from 1000).

### Visual Style

```css
.sidebar-header {
  font-family: 'Roboto Condensed';
  transform: skewX(-12deg);
  border-bottom: 1px solid var(--border-default);
}

.price-slider-track {
  transform: skewX(-12deg);
  /* Thumb styles handled by component */
}
```

---

## 📁 Связанные документы

- `00-migration-plan.md` — Общий план миграции
- `01-color-mapping.md` — Маппинг цветов
- `design_v2.3.0.json` — Официальные токены

---

**Следующий шаг:** Начать имплементацию CSS foundation и миграцию компонентов.
