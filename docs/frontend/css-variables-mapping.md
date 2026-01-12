# CSS Variables Mapping для FREESPORT Design System v2.1.0

## Цель документа
Этот документ определяет mapping между hardcoded HEX цветами и CSS переменными для обеспечения консистентности дизайн-системы.

---

## Primary Colors (Синяя палитра - основные акценты)

### ❌ НЕПРАВИЛЬНО (Hardcoded):
```tsx
<button className="bg-[#0060FF] hover:bg-[#0047CC] active:bg-[#0037A6]">
```

### ✅ ПРАВИЛЬНО (CSS Variables):
```tsx
<button className="bg-primary hover:bg-primary-hover active:bg-primary-active">
```

**Mapping таблица:**
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#0060FF` | `var(--color-primary)` | `bg-primary` / `text-primary-color` | CTA кнопки, ключевые акценты |
| `#0047CC` | `var(--color-primary-hover)` | `bg-primary-hover` | Hover состояние primary |
| `#0037A6` | `var(--color-primary-active)` | `bg-primary-active` | Active/pressed состояние |
| `#E7F3FF` | `var(--color-primary-subtle)` | `bg-primary-subtle` | Фоновые подсветки primary |

---

## Secondary Colors (Голубая палитра - вторичные акценты)

### ❌ НЕПРАВИЛЬНО:
```tsx
<div className="bg-[#00B7FF] border-[#0095D6]">
```

### ✅ ПРАВИЛЬНО:
```tsx
<div className="bg-secondary border-secondary-hover">
```

**Mapping таблица:**
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#00B7FF` | `var(--color-secondary)` | `bg-secondary` / `text-secondary-color` | Вторичные акценты |
| `#0095D6` | `var(--color-secondary-hover)` | `bg-secondary-hover` | Hover состояние |
| `#0078B3` | `var(--color-secondary-active)` | `bg-secondary-active` | Active состояние |
| `#E1F5FF` | `var(--color-secondary-subtle)` | `bg-secondary-subtle` | Фоновые подсветки |

---

## Accent Colors (Семантические цвета)

### Success (Зеленый)
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#00AA5B` | `var(--color-success)` | `text-success` / `bg-success` | Успех, в наличии |
| `#E0F5E8` | `var(--color-success-bg)` | `bg-success-bg` | Фон success badge |

### Warning (Оранжевый)
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#F5A623` | `var(--color-warning)` | `text-warning` / `bg-warning` | Предупреждение, под заказ |
| `#FFF1CC` | `var(--color-warning-bg)` | `bg-warning-bg` | Фон warning badge |

### Danger (Красный)
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#E53935` | `var(--color-danger)` | `text-danger` / `bg-danger` | Ошибка, нет в наличии |
| `#FFE1E8` | `var(--color-danger-bg)` | `bg-danger-bg` | Фон danger badge |

### Promo (Розовый)
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#FF2E93` | `var(--color-promo)` | `text-promo` / `bg-promo` | Промо-акции |
| `#FFF0F5` | `var(--color-promo-bg)` | `bg-promo-bg` | Фон promo badge |

---

## Neutral Colors (Серо-голубая палитра)

### ❌ НЕПРАВИЛЬНО:
```tsx
<div className="bg-[#FFFFFF] border-[#E3E8F2] text-[#1F2A44]">
```

### ✅ ПРАВИЛЬНО:
```tsx
<div className="bg-neutral-100 border-neutral-300 text-neutral-900">
```

**Mapping таблица:**
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#FFFFFF` | `var(--color-neutral-100)` | `bg-neutral-100` | Белый фон |
| `#F5F7FB` | `var(--color-neutral-200)` | `bg-neutral-200` | Светлый фон (canvas) |
| `#E3E8F2` | `var(--color-neutral-300)` | `bg-neutral-300` / `border-neutral-300` | Легкие разделители |
| `#B9C3D6` | `var(--color-neutral-400)` | `border-neutral-400` | Бордеры input |
| `#8F9BB3` | `var(--color-neutral-500)` | `text-neutral-500` | Средний текст |
| `#6B7A99` | `var(--color-neutral-600)` | `text-neutral-600` | Вторичный текст |
| `#4B5C7A` | `var(--color-neutral-700)` | `text-neutral-700` | Основной вторичный |
| `#2D3A52` | `var(--color-neutral-800)` | `text-neutral-800` | Темный текст |
| `#1F2A44` | `var(--color-neutral-900)` | `text-neutral-900` | Самый темный |

---

## Text Colors (Типографика)

### ❌ НЕПРАВИЛЬНО:
```tsx
<h1 className="text-[#1F2A44]">Заголовок</h1>
<p className="text-[#4B5C7A]">Вторичный текст</p>
```

### ✅ ПРАВИЛЬНО:
```tsx
<h1 className="text-primary">Заголовок</h1>
<p className="text-secondary">Вторичный текст</p>
```

**Mapping таблица:**
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#1F2A44` | `var(--color-text-primary)` | `text-primary` | Основной текст, заголовки |
| `#4B5C7A` | `var(--color-text-secondary)` | `text-secondary` | Вторичный текст, описания |
| `#7F8CA8` | `var(--color-text-muted)` | `text-muted` | Приглушенный текст, метки |
| `#FFFFFF` | `var(--color-text-inverse)` | `text-inverse` | Белый текст на темном фоне |

---

## Canvas & Backgrounds

### ❌ НЕПРАВИЛЬНО:
```tsx
<div style={{ background: '#F5F7FB' }}>
  <div style={{ background: '#FFFFFF' }}>
    Content
  </div>
</div>
```

### ✅ ПРАВИЛЬНО:
```tsx
<div style={{ background: 'var(--bg-canvas)' }}>
  <div style={{ background: 'var(--bg-panel)' }}>
    Content
  </div>
</div>
```

**Mapping таблица:**
| HEX Code | CSS Variable | Tailwind Class | Usage |
|----------|--------------|----------------|-------|
| `#F5F7FB` | `var(--bg-canvas)` | `bg-canvas` | Основной фон страницы |
| `#FFFFFF` | `var(--bg-panel)` | `bg-panel` | Карточки, панели |

---

## Shadows (Тени)

### ❌ НЕПРАВИЛЬНО:
```tsx
<div style={{ boxShadow: '0 8px 24px rgba(15, 23, 42, 0.08)' }}>
```

### ✅ ПРАВИЛЬНО:
```tsx
<div className="shadow-default">
```

**Mapping таблица:**
| Shadow Value | CSS Variable | Tailwind Class | Usage |
|--------------|--------------|----------------|-------|
| `0 8px 24px rgba(15, 23, 42, 0.08)` | `var(--shadow-default)` | `shadow-default` | Карточки, панели |
| `0 10px 32px rgba(15, 23, 42, 0.12)` | `var(--shadow-hover)` | `shadow-hover` | Hover состояние |
| `0 4px 12px rgba(0, 96, 255, 0.28)` | `var(--shadow-primary)` | `shadow-primary` | Primary кнопки |
| `0 2px 8px rgba(0, 96, 255, 0.16)` | `var(--shadow-secondary)` | `shadow-secondary` | Secondary элементы |
| `0 24px 64px rgba(15, 23, 42, 0.24)` | `var(--shadow-modal)` | `shadow-modal` | Модальные окна |

---

## Badge Variants (Специальные варианты)

### ❌ НЕПРАВИЛЬНО:
```tsx
<span className="bg-[#E0F5E8] text-[#00AA5B]">Hit</span>
<span className="bg-[#E7F3FF] text-[#0060FF]">New</span>
```

### ✅ ПРАВИЛЬНО:
```tsx
<Badge variant="hit">Hit</Badge>
<Badge variant="new">New</Badge>
```

**Badge Mapping:**
| Variant | Background HEX | Text HEX | CSS Variables |
|---------|----------------|----------|---------------|
| `hit` | `#E0F5E8` | `#00AA5B` | `--badge-hit-bg`, `--badge-hit-text` |
| `new` | `#E7F3FF` | `#0060FF` | `--badge-new-bg`, `--badge-new-text` |
| `sale` | `#FFE1E8` | `#E53935` | `--badge-sale-bg`, `--badge-sale-text` |
| `promo` | `#FFF0F5` | `#FF2E93` | `--badge-promo-bg`, `--badge-promo-text` |
| `discount` | `#F0E7FF` | `#7C3AED` | `--badge-discount-bg`, `--badge-discount-text` |
| `premium` | `#F6F0E4` | `#6D4C1F` | `--badge-premium-bg`, `--badge-premium-text` |

---

## Практические примеры замены

### Пример 1: Кнопка "В корзину"

❌ **До (hardcoded):**
```tsx
<button
  className="h-14 bg-[#0060FF] hover:bg-[#0047CC] text-white rounded-lg"
  onClick={addToCart}
>
  В корзину
</button>
```

✅ **После (CSS variables):**
```tsx
<button
  className="h-14 bg-primary hover:bg-primary-hover text-inverse rounded-lg"
  onClick={addToCart}
>
  В корзину
</button>
```

### Пример 2: ProductGallery thumbnail border

❌ **До:**
```tsx
<button
  className={`
    w-[88px] h-[88px] rounded-xl
    ${idx === selectedImage ? 'ring-2 ring-[#0060FF]' : 'ring-1 ring-[#E3E8F2]'}
  `}
>
```

✅ **После:**
```tsx
<button
  className={`
    w-[88px] h-[88px] rounded-xl
    ${idx === selectedImage ? 'ring-2 ring-primary' : 'ring-1 ring-neutral-300'}
  `}
>
```

### Пример 3: Toast уведомления

❌ **До:**
```tsx
// Success toast
<div className="bg-[#E0F5E8] border-l-4 border-[#00AA5B]">
  <CheckCircle className="text-[#00AA5B]" />
  <p className="text-[#1F2A44]">Товар добавлен в корзину</p>
</div>

// Error toast
<div className="bg-[#FFE1E8] border-l-4 border-[#E53935]">
  <XCircle className="text-[#E53935]" />
  <p className="text-[#1F2A44]">Ошибка добавления</p>
</div>
```

✅ **После:**
```tsx
// Success toast
<div className="bg-success-bg border-l-4 border-success">
  <CheckCircle className="text-success" />
  <p className="text-primary">Товар добавлен в корзину</p>
</div>

// Error toast
<div className="bg-danger-bg border-l-4 border-danger">
  <XCircle className="text-danger" />
  <p className="text-primary">Ошибка добавления</p>
</div>
```

### Пример 4: Lightbox компонент

❌ **До:**
```tsx
<div className="fixed inset-0 bg-black/80">
  <button className="bg-[#E3E8F2] hover:bg-[#B9C3D6]">
    <X size={24} className="text-[#1F2A44]" />
  </button>
</div>
```

✅ **После:**
```tsx
<div className="fixed inset-0 bg-black/80">
  <button className="bg-neutral-300 hover:bg-neutral-400">
    <X size={24} className="text-neutral-900" />
  </button>
</div>
```

---

## Tailwind Config Setup

Убедитесь, что `tailwind.config.ts` содержит правильные CSS переменные:

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
          active: 'var(--color-primary-active)',
          subtle: 'var(--color-primary-subtle)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          hover: 'var(--color-secondary-hover)',
          active: 'var(--color-secondary-active)',
          subtle: 'var(--color-secondary-subtle)',
        },
        success: 'var(--color-success)',
        'success-bg': 'var(--color-success-bg)',
        warning: 'var(--color-warning)',
        'warning-bg': 'var(--color-warning-bg)',
        danger: 'var(--color-danger)',
        'danger-bg': 'var(--color-danger-bg)',
        promo: 'var(--color-promo)',
        'promo-bg': 'var(--color-promo-bg)',
        neutral: {
          100: 'var(--color-neutral-100)',
          200: 'var(--color-neutral-200)',
          300: 'var(--color-neutral-300)',
          400: 'var(--color-neutral-400)',
          500: 'var(--color-neutral-500)',
          600: 'var(--color-neutral-600)',
          700: 'var(--color-neutral-700)',
          800: 'var(--color-neutral-800)',
          900: 'var(--color-neutral-900)',
        },
        canvas: 'var(--bg-canvas)',
        panel: 'var(--bg-panel)',
      },
      boxShadow: {
        default: 'var(--shadow-default)',
        hover: 'var(--shadow-hover)',
        primary: 'var(--shadow-primary)',
        secondary: 'var(--shadow-secondary)',
        modal: 'var(--shadow-modal)',
      },
    },
  },
};

export default config;
```

---

## globals.css Setup

```css
/* globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Primary Colors */
    --color-primary: #0060FF;
    --color-primary-hover: #0047CC;
    --color-primary-active: #0037A6;
    --color-primary-subtle: #E7F3FF;

    /* Secondary Colors */
    --color-secondary: #00B7FF;
    --color-secondary-hover: #0095D6;
    --color-secondary-active: #0078B3;
    --color-secondary-subtle: #E1F5FF;

    /* Accent Colors */
    --color-success: #00AA5B;
    --color-success-bg: #E0F5E8;
    --color-warning: #F5A623;
    --color-warning-bg: #FFF1CC;
    --color-danger: #E53935;
    --color-danger-bg: #FFE1E8;
    --color-promo: #FF2E93;
    --color-promo-bg: #FFF0F5;

    /* Neutral Colors */
    --color-neutral-100: #FFFFFF;
    --color-neutral-200: #F5F7FB;
    --color-neutral-300: #E3E8F2;
    --color-neutral-400: #B9C3D6;
    --color-neutral-500: #8F9BB3;
    --color-neutral-600: #6B7A99;
    --color-neutral-700: #4B5C7A;
    --color-neutral-800: #2D3A52;
    --color-neutral-900: #1F2A44;

    /* Text Colors */
    --color-text-primary: #1F2A44;
    --color-text-secondary: #4B5C7A;
    --color-text-muted: #7F8CA8;
    --color-text-inverse: #FFFFFF;

    /* Backgrounds */
    --bg-canvas: #F5F7FB;
    --bg-panel: #FFFFFF;

    /* Shadows */
    --shadow-default: 0 8px 24px rgba(15, 23, 42, 0.08);
    --shadow-hover: 0 10px 32px rgba(15, 23, 42, 0.12);
    --shadow-primary: 0 4px 12px rgba(0, 96, 255, 0.28);
    --shadow-secondary: 0 2px 8px rgba(0, 96, 255, 0.16);
    --shadow-modal: 0 24px 64px rgba(15, 23, 42, 0.24);
  }
}
```

---

## Checklist для аудита кода

При проверке компонентов на hardcoded цвета:

- [ ] ✅ Заменить все `bg-[#XXXXXX]` на `bg-{semantic-name}`
- [ ] ✅ Заменить все `text-[#XXXXXX]` на `text-{semantic-name}`
- [ ] ✅ Заменить все `border-[#XXXXXX]` на `border-{semantic-name}`
- [ ] ✅ Заменить все `ring-[#XXXXXX]` на `ring-{semantic-name}`
- [ ] ✅ Заменить все inline `style={{ color: '#XXX' }}` на CSS variables
- [ ] ✅ Заменить все `rgba()` значения на CSS переменные для shadows
- [ ] ✅ Проверить что Badge компоненты используют variants, а не hardcoded цвета
- [ ] ✅ Убедиться что Toast уведомления используют семантические цвета

---

**Дата создания:** 2025-11-30
**Версия:** 1.0
**Автор:** Sarah (Product Owner)
**Статус:** ✅ Готов к использованию
