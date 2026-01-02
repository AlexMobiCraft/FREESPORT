# Electric Orange Color Mapping

**Версия:** 1.0  
**Дата:** 2026-01-02  
**Автор:** Saga WDS Analyst Agent  
**Статус:** 📋 Reference Document

---

## 🎨 Философия Electric Orange

**Design Philosophy:** Digital Brutalism & Kinetic Energy

| Принцип | Описание |
|---------|----------|
| **Dark Theme** | Глубокий черный фон создает премиальное ощущение |
| **Electric Accent** | Яркий оранжевый (#FF6B00) как единственный акцент |
| **Sharp Geometry** | Острые углы (0px radius) + skew (-12deg) |
| **High Contrast** | Белый текст на черном фоне для максимальной читаемости |

---

## 📊 Полная таблица маппинга

### 1. Primary Colors

| Назначение | Текущий (Blue) | Electric Orange | CSS Variable |
|------------|----------------|-----------------|--------------|
| **Primary** | `#0060FF` | `#FF6B00` | `--color-primary` |
| **Primary Hover** | `#0047CC` | `#FF8533` | `--color-primary-hover` |
| **Primary Active** | `#0037A6` | `#E55A00` | `--color-primary-active` |
| **Primary Subtle** | `#E7F3FF` | `rgba(255,107,0,0.1)` | `--color-primary-subtle` |

### 2. Secondary Colors (Удаляются)

В Electric Orange нет вторичного цвета — только Primary Orange.

| Назначение | Текущий (Cyan) | Electric Orange | Примечание |
|------------|----------------|-----------------|------------|
| **Secondary** | `#00B7FF` | ❌ Удалить | Использовать Primary |
| **Secondary Hover** | `#0095D6` | ❌ Удалить | — |
| **Secondary Subtle** | `#E1F5FF` | ❌ Удалить | — |

### 3. Background Colors

| Назначение | Текущий (Light) | Electric Orange (Dark) | CSS Variable |
|------------|-----------------|------------------------|--------------|
| **Body BG** | `#FFFFFF` | `#0F0F0F` | `--bg-body` |
| **Canvas BG** | `#F5F7FB` | `#0F0F0F` | `--bg-canvas` |
| **Card BG** | `#FFFFFF` | `#1A1A1A` | `--bg-card` |
| **Input BG** | `#FFFFFF` | `transparent` | `--bg-input` |
| **Overlay** | `rgba(0,0,0,0.5)` | `rgba(0,0,0,0.8)` | `--bg-overlay` |

### 4. Text Colors

| Назначение | Текущий | Electric Orange | CSS Variable |
|------------|---------|-----------------|--------------|
| **Primary Text** | `#1F2A44` | `#FFFFFF` | `--color-text-primary` |
| **Secondary Text** | `#4B5C7A` | `#A0A0A0` | `--color-text-secondary` |
| **Muted Text** | `#7F8CA8` | `#666666` | `--color-text-muted` |
| **Inverse Text** | `#FFFFFF` | `#000000` | `--color-text-inverse` |

### 5. Border Colors

| Назначение | Текущий | Electric Orange | CSS Variable |
|------------|---------|-----------------|--------------|
| **Border Default** | `#E3E8F2` | `#333333` | `--border-default` |
| **Border Subtle** | `#D0D7E6` | `#2A2A2A` | `--border-subtle` |
| **Border Active** | `#0060FF` | `#FF6B00` | `--border-active` |
| **Border Hover** | `#B9C3D6` | `#444444` | `--border-hover` |

### 6. Neutral Scale (Инвертируется)

| Level | Текущий (Light→Dark) | Electric Orange (Dark→Light) | CSS Variable |
|-------|----------------------|------------------------------|--------------|
| **100** | `#FFFFFF` | `#0F0F0F` | `--color-neutral-100` |
| **200** | `#F5F7FB` | `#1A1A1A` | `--color-neutral-200` |
| **300** | `#E3E8F2` | `#2A2A2A` | `--color-neutral-300` |
| **400** | `#B9C3D6` | `#333333` | `--color-neutral-400` |
| **500** | `#8F9BB3` | `#555555` | `--color-neutral-500` |
| **600** | `#6B7A99` | `#777777` | `--color-neutral-600` |
| **700** | `#4B5C7A` | `#999999` | `--color-neutral-700` |
| **800** | `#2D3A52` | `#BBBBBB` | `--color-neutral-800` |
| **900** | `#1F2A44` | `#FFFFFF` | `--color-neutral-900` |

### 7. Semantic Colors (Accent)

| Назначение | Текущий | Electric Orange | CSS Variable |
|------------|---------|-----------------|--------------|
| **Success** | `#00AA5B` | `#22C55E` | `--color-success` |
| **Success BG** | `#E0F5E8` | `rgba(34,197,94,0.15)` | `--color-success-bg` |
| **Warning** | `#F5A623` | `#EAB308` | `--color-warning` |
| **Warning BG** | `#FFF1CC` | `rgba(234,179,8,0.15)` | `--color-warning-bg` |
| **Danger** | `#E53935` | `#EF4444` | `--color-danger` |
| **Danger BG** | `#FFE1E8` | `rgba(239,68,68,0.15)` | `--color-danger-bg` |

### 8. Shadows

| Назначение | Текущий | Electric Orange | CSS Variable |
|------------|---------|-----------------|--------------|
| **Default** | `0 8px 24px rgba(15,23,42,0.08)` | `none` | `--shadow-default` |
| **Hover** | `0 10px 32px rgba(15,23,42,0.12)` | `0 0 20px rgba(255,107,0,0.2)` | `--shadow-hover` |
| **Primary** | `0 4px 12px rgba(0,96,255,0.28)` | `0 0 15px rgba(255,107,0,0.4)` | `--shadow-primary` |
| **Glow** | — | `0 0 30px rgba(255,107,0,0.3)` | `--shadow-glow` |

---

## 🔧 Новые CSS Variables для Electric Orange

```css
/* globals-electric-orange.css */
@theme inline {
  /* === PHILOSOPHY === */
  /* Digital Brutalism & Kinetic Energy */
  /* Dark theme with Electric Orange accent */
  
  /* === GEOMETRY === */
  --skew-angle: -12deg;
  --counter-skew: 12deg;
  --border-radius: 0px;
  
  /* === PRIMARY (Electric Orange) === */
  --color-primary: #FF6B00;
  --color-primary-hover: #FF8533;
  --color-primary-active: #E55A00;
  --color-primary-subtle: rgba(255, 107, 0, 0.1);
  
  /* === BACKGROUNDS === */
  --bg-body: #0F0F0F;
  --bg-canvas: #0F0F0F;
  --bg-card: #1A1A1A;
  --bg-input: transparent;
  --bg-overlay: rgba(0, 0, 0, 0.8);
  
  /* === TEXT === */
  --color-text-primary: #FFFFFF;
  --color-text-secondary: #A0A0A0;
  --color-text-muted: #666666;
  --color-text-inverse: #000000;
  
  /* === BORDERS === */
  --border-default: #333333;
  --border-subtle: #2A2A2A;
  --border-active: #FF6B00;
  --border-hover: #444444;
  
  /* === NEUTRAL SCALE (Dark→Light) === */
  --color-neutral-100: #0F0F0F;
  --color-neutral-200: #1A1A1A;
  --color-neutral-300: #2A2A2A;
  --color-neutral-400: #333333;
  --color-neutral-500: #555555;
  --color-neutral-600: #777777;
  --color-neutral-700: #999999;
  --color-neutral-800: #BBBBBB;
  --color-neutral-900: #FFFFFF;
  
  /* === SEMANTIC COLORS === */
  --color-success: #22C55E;
  --color-success-bg: rgba(34, 197, 94, 0.15);
  --color-warning: #EAB308;
  --color-warning-bg: rgba(234, 179, 8, 0.15);
  --color-danger: #EF4444;
  --color-danger-bg: rgba(239, 68, 68, 0.15);
  
  /* === SHADOWS (Glow-based) === */
  --shadow-default: none;
  --shadow-hover: 0 0 20px rgba(255, 107, 0, 0.2);
  --shadow-primary: 0 0 15px rgba(255, 107, 0, 0.4);
  --shadow-glow: 0 0 30px rgba(255, 107, 0, 0.3);
  --shadow-modal: 0 0 40px rgba(0, 0, 0, 0.5);
  
  /* === TYPOGRAPHY === */
  --font-display: 'Roboto Condensed', sans-serif;
  --font-body: 'Inter', sans-serif;
  
  /* === MOTION === */
  --duration-short: 0.15s;
  --duration-medium: 0.3s;
  --easing: cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
```

---

## 📝 Правила применения геометрии

### Skewed Elements (-12deg)

Элементы, которые ДОЛЖНЫ быть скошены:

- ✅ **Buttons** (container skewed, text counter-skewed)
- ✅ **Badges** (product badges, status badges)
- ✅ **Checkboxes** (container skewed)
- ✅ **Slider tracks & thumbs**
- ✅ **Tab indicators**
- ✅ **Price tags** (display prices)
- ✅ **Section headers** (decorative)

### Rectangular Elements (0deg)

Элементы, которые ДОЛЖНЫ быть прямыми:

- ✅ **Text inputs** (forms)
- ✅ **Textareas**
- ✅ **Search fields**
- ✅ **Cards** (product cards, news cards)
- ✅ **Images** (always square 1:1 for products)
- ✅ **Modals**
- ✅ **Dropdowns**

---

## 🎯 Typography Rules

### Display Text (Headers)

```css
.display-text {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 900;
  font-style: normal; /* NOT italic */
  text-transform: uppercase;
  transform: skewX(-12deg);
}
```

### Body Text

```css
.body-text {
  font-family: 'Inter', sans-serif;
  font-weight: 400;
  font-style: normal;
  transform: none; /* No skew */
}
```

### Price Tags

```css
.price-tag {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 700;
  font-style: normal;
  color: var(--color-primary); /* #FF6B00 */
  transform: skewX(-12deg);
}
```

---

## 📋 Визуальное сравнение

### Before (Blue Light Theme)

```
┌────────────────────────────────────────┐
│  bg: #FFFFFF                           │
│  ┌────────────────────┐                │
│  │ bg: #0060FF        │ ← Primary Blue │
│  │ text: #FFFFFF      │                │
│  │ radius: 6px        │                │
│  └────────────────────┘                │
│  text: #1F2A44 (dark on light)         │
└────────────────────────────────────────┘
```

### After (Electric Orange)

```
┌────────────────────────────────────────┐
│  bg: #0F0F0F                           │
│  ╱────────────────────╲                │
│ ╱ bg: #FF6B00          ╲← Skewed Orange│
│ ╲ text: #000000        ╱               │
│  ╲────────────────────╱                │
│  text: #FFFFFF (light on dark)         │
└────────────────────────────────────────┘
```

---

## 🔄 Tailwind Class Migration

### Background Classes

| Текущий | Electric Orange |
|---------|-----------------|
| `bg-white` | `bg-neutral-100` → `#0F0F0F` |
| `bg-neutral-200` | `bg-neutral-200` → `#1A1A1A` |
| `bg-primary` | `bg-primary` → `#FF6B00` |

### Text Classes

| Текущий | Electric Orange |
|---------|-----------------|
| `text-neutral-900` | `text-neutral-900` → `#FFFFFF` |
| `text-neutral-700` | `text-neutral-700` → `#999999` |
| `text-primary` | `text-primary` → `#FF6B00` |

### Border Classes

| Текущий | Electric Orange |
|---------|-----------------|
| `border-neutral-300` | `border-neutral-400` → `#333333` |
| `border-primary` | `border-primary` → `#FF6B00` |

---

## ✅ Checklist для верификации

При проверке миграции цветов:

- [ ] Все backgrounds темные (`#0F0F0F` или `#1A1A1A`)
- [ ] Primary текст белый (`#FFFFFF`)
- [ ] Акценты только оранжевые (`#FF6B00`)
- [ ] Нет голубых/синих цветов
- [ ] Borders темно-серые (`#333333`)
- [ ] Input backgrounds прозрачные
- [ ] Shadows — это glow эффекты (не классические тени)
- [ ] Контраст WCAG AA соблюден (>4.5:1)

---

## 📁 Связанные документы

- `00-migration-plan.md` — Общий план миграции
- `02-component-specs.md` — Спецификации компонентов (TODO)
- `design_v2.3.0.json` — Официальные токены Electric Orange
- `front-end-spec.md` — Текущая UX спецификация

---

**Следующий шаг:** Создать `02-component-specs.md` с детальными спецификациями каждого компонента в стиле Electric Orange.
