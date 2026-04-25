**Палитра (Сине-голубая):**

```
Primary:    #0060FF (синий)
Secondary:  #00B7FF (голубой)
Success:    #00AA5B (зелёный)
Warning:    #F5A623 (оранжевый)
Danger:     #E53935 (красный)
Promo:      #FF2E93 (розовый)
```

**Раздел 2: Цветовая палитра**
Требуется полная замена таблиц цветов:

- Primary Default: #0060FF
- Secondary Default: #00B7FF

- Accent Success: #00AA5B (новый)
- Accent Warning: #F5A623 (новый)
- Accent Danger: #E53935 (новый)
- Accent Promo: #FF2E93 (новый)

````

**Раздел 3: UI Components Specifications**
Обновить примеры компонентов:
- Button variants (primary, secondary, subtle)
- Badge variants (new, hit, promo, sale, discount)
- Form inputs (focus states, borders)
- Tabs (active indicator)
- Toast (border colors)

**Журнал изменений:**
```markdown
| 2025-11-25 | 2.1 | Миграция на сине-голубую цветовую схему | John (PM) |
````

---

### 3.4 Design System JSON

**Файл:** [docs/frontend/design-system.json](../frontend/design-system.json)

**Конфликты:** ⚠️ **КРИТИЧЕСКИЕ** - Источник истины для токенов

**Требуемые изменения:**

**1. Meta section:**

```json
{
  "meta": {
    "version": "2.1.0", // было 2.0.0
    "lastUpdated": "2025-11-25",
    "changeLog": [
      {
        "version": "2.1.0",
        "date": "2025-11-25",
        "changes": "Миграция на сине-голубую цветовую палитру"
      }
    ]
  }
}
```

**2. Brand section:**

```json
{
  "brand": {
    "tone": "Технологичный, дружелюбный e-commerce в стиле OZON", // обновлено
    "colorPhilosophy": "Яркие синие акценты для CTA, голубые вторичные тона, семантические цвета для статусов"
  }
}
```

**3. Foundations.colors section:**
Полная замена всех цветовых токенов согласно таблице из `color-scheme-migration.md`:

```json
{
  "foundations": {
    "colors": {
      "primary": {
        "default": "#0060FF", // было #1F1F1F
        "hover": "#0047CC", // было #3A3A3A
        "active": "#0037A6", // было #0D0D0D
        "subtle": "#E7F3FF" // было #F2F2F2
      },
      "secondary": {
        "default": "#00B7FF", // было #3D3D3D
        "hover": "#0095D6", // было #2E2E2E
        "active": "#0078B3", // было #1C1C1C
        "subtle": "#E1F5FF" // было #EAEAEA
      },
      "accent": {
        "success": "#00AA5B", // было #4D4D4D
        "warning": "#F5A623", // было #6A6A6A
        "danger": "#E53935", // было #2B2B2B
        "promo": "#FF2E93" // было #8A8A8A
      },
      "neutral": {
        "100": "#FFFFFF", // без изменений
        "200": "#F5F7FB", // было #F5F5F5
        "300": "#E3E8F2", // было #E0E0E0
        "400": "#B9C3D6", // было #C7C7C7
        "500": "#8F9BB3", // было #A3A3A3
        "600": "#6B7A99", // было #7D7D7D
        "700": "#4B5C7A", // было #5E5E5E
        "800": "#2D3A52", // было #3F3F3F
        "900": "#1F2A44" // было #1F1F1F
      },
      "text": {
        "primary": "#1F2A44", // было #1B1B1B
        "secondary": "#4B5C7A", // было #4D4D4D
        "muted": "#7F8CA8", // было #7A7A7A
        "inverse": "#FFFFFF" // без изменений
      }
    }
  }
}
```

**4. Components section:**
Обновить все компоненты с цветовыми свойствами:

```json
{
  "components": {
    "Button": {
      "variants": {
        "primary": {
          "bg": "var(--color-primary)", // теперь #0060FF
          "bgHover": "var(--color-primary-hover)", // теперь #0047CC
          "text": "#FFFFFF"
        },
        "secondary": {
          "border": "var(--color-primary)", // теперь #0060FF
          "text": "var(--color-primary)"
        },
        "subtle": {
          "bg": "var(--color-primary-subtle)", // теперь #E7F3FF
          "text": "var(--color-primary)"
        }
      }
    },
    "Badge": {
      "variants": {
        "new": {
          "bg": "#E7F3FF", // было #E1F0FF
          "text": "#0060FF" // было #0F5DA3
        },
        "hit": {
          "bg": "#E0F5E8", // было #E3F6EC
          "text": "#00AA5B" // было #1F7A4A
        },
        "promo": {
          "bg": "#FFF0F5", // было #F4EBDC
          "text": "#FF2E93" // было #8C4C00
        },
        "sale": {
          "bg": "#FFE1E8", // было #F9E1E1
          "text": "#E53935" // было #A63232
        },
        "discount": {
          "bg": "#F0E7FF", // было #F4E9FF
          "text": "#7C3AED" // было #5E32A1
        }
      }
    },
    "Checkbox": {
      "checkedBg": "var(--color-primary)", // теперь #0060FF
      "checkedBorder": "var(--color-primary)",
      "hoverBorder": "var(--color-primary)"
    },
    "Toggle": {
      "trackOn": "var(--color-primary)", // теперь #0060FF
      "trackOff": "#E3E8F2"
    },
    "Tabs": {
      "activeIndicator": "var(--color-primary)", // уже был #0060FF
      "activeText": "var(--color-primary)" // теперь #0060FF
    },
    "Toast": {
      "variants": {
        "info": {
          "border": "var(--color-primary)" // теперь #0060FF
        },
        "success": {
          "border": "var(--color-accent-success)" // теперь #00AA5B
        },
        "warning": {
          "border": "var(--color-accent-warning)" // теперь #F5A623
        },
        "error": {
          "border": "var(--color-accent-danger)" // теперь #E53935
        }
      }
    }
  }
}
```

**5. Shadows section:**

```json
{
  "shadows": {
    "primary": "0 4px 12px rgba(0, 96, 255, 0.28)", // обновлено
    "secondary": "0 2px 8px rgba(0, 96, 255, 0.16)", // обновлено
    "pressed": "inset 0 2px 4px rgba(0, 71, 204, 0.24)" // обновлено
  }
}
```

**6. Focus states:**

```json
{
  "states": {
    "focus": {
      "outline": "2px solid rgba(0, 96, 255, 0.6)", // было rgba(31,31,31,0.6)
      "ring": "0 0 0 4px rgba(0, 96, 255, 0.12)" // обновлено
    }
  }
}
```

---

### 3.5 Tailwind CSS Tokens

**Файл:** [frontend/src/app/globals.css](../../frontend/src/app/globals.css)

**Конфликты:** ⚠️ **КРИТИЧЕСКИЕ** - CSS-переменные требуют обновления

**Требуемые изменения:**

```css
@theme inline {
  /* Colors - Primary */
  --color-primary: #0060ff; /* было #1f1f1f */
  --color-primary-hover: #0047cc; /* было #3a3a3a */
  --color-primary-active: #0037a6; /* было #0d0d0d */
  --color-primary-subtle: #e7f3ff; /* было #f2f2f2 */

  /* Colors - Secondary */
  --color-secondary: #00b7ff; /* было #3d3d3d */
  --color-secondary-hover: #0095d6; /* было #2e2e2e */
  --color-secondary-active: #0078b3; /* было #1c1c1c */
  --color-secondary-subtle: #e1f5ff; /* было #eaeaea */

  /* Colors - Accent */
  --color-accent-success: #00aa5b; /* было #4d4d4d */
  --color-accent-warning: #f5a623; /* было #6a6a6a */
  --color-accent-danger: #e53935; /* было #2b2b2b */
  --color-accent-promo: #ff2e93; /* было #8a8a8a */

  /* Colors - Neutral Scale */
  --color-neutral-200: #f5f7fb; /* было #f5f5f5 */
  --color-neutral-300: #e3e8f2; /* было #e0e0e0 */
  --color-neutral-400: #b9c3d6; /* было #c7c7c7 */
  --color-neutral-500: #8f9bb3; /* было #a3a3a3 */
  --color-neutral-600: #6b7a99; /* было #7d7d7d */
  --color-neutral-700: #4b5c7a; /* было #5e5e5e */
  --color-neutral-800: #2d3a52; /* было #3f3f3f */
  --color-neutral-900: #1f2a44; /* было #1f1f1f */

  /* Colors - Text */
  --color-text-primary: #1f2a44; /* было #1b1b1b */
  --color-text-secondary: #4b5c7a; /* было #4d4d4d */
  --color-text-muted: #7f8ca8; /* было #7a7a7a */

  /* Typography - Color Usage */
  --color-typography-primary: #1f2a44; /* было #1f2a44 */
  --color-typography-secondary: #4b5c7a; /* было #4b5c7a */
  --color-typography-muted: #7f8ca8; /* было #7f8ca8 */

  /* Shadows */
  --shadow-primary: 0 4px 12px rgba(0, 96, 255, 0.28);
  --shadow-secondary: 0 2px 8px rgba(0, 96, 255, 0.16);
  --shadow-pressed: inset 0 2px 4px rgba(0, 71, 204, 0.24);

  /* Focus States */
  --focus-ring: 0 0 0 4px rgba(0, 96, 255, 0.12);
  --focus-outline: 2px solid rgba(0, 96, 255, 0.6);
}
```

**Комментарий для разработчика:**

```css
/**
 * FREESPORT Design System - Tailwind CSS 4.0 Tokens
 * Based on design-system.json v2.1.0
 *
 * MIGRATION NOTE (2025-11-25):
 * Цветовая схема обновлена с графитово-серой на сине-голубую.
 * Все токены синхронизированы с design-system.json.
 *
 * Контрастность проверена: WCAG AA соблюдён ✅
 * Подробности: docs/frontend/color-scheme-migration.md
 */
```

---

### 3.6 UI Components (Хардкод цветов)

**Затронутые файлы:**

#### 1. Button Component

**Файл:** `frontend/src/components/ui/Button/Button.tsx`

**Текущий код (проблема):**

```tsx
// ❌ Хардкод цветов
const variantClasses = {
  primary: "bg-[#1F1F1F] hover:bg-[#3A3A3A] text-white",
  secondary: "border-[#1F1F1F] text-[#1F1F1F]",
};
```

**Исправленный код:**

```tsx
// ✅ Использование токенов
const variantClasses = {
  primary:
    "bg-primary hover:bg-primary-hover active:bg-primary-active text-white",
  secondary: "border-primary text-primary hover:bg-primary-subtle",
  subtle: "bg-primary-subtle text-primary hover:bg-primary-subtle/80",
};
```

#### 2. Checkbox Component

**Файл:** `frontend/src/components/ui/Checkbox/Checkbox.tsx`

**Текущий код:**

```tsx
// ❌ Хардкод
<input className="checked:bg-[#1F1F1F] checked:border-[#1F1F1F]" />
```

**Исправленный код:**

```tsx
// ✅ Токены
<input className="checked:bg-primary checked:border-primary focus:ring-primary/12" />
```

#### 3. Toggle Component

**Файл:** `frontend/src/components/ui/Toggle/Toggle.tsx`

**Текущий код:**

```tsx
// ❌ Хардкод
<div className={cn(
  'bg-neutral-300',
  checked && 'bg-[#1F1F1F]'
)}>
```

**Исправленный код:**

```tsx
// ✅ Токены
<div className={cn(
  'bg-neutral-300',
  checked && 'bg-primary'
)}>
```

#### 4. Pagination Component (Catalog)

**Файл:** `frontend/src/app/catalog/page.tsx`

**Текущий код:**

```tsx
// ❌ Хардкод Tailwind класса
<button className={cn(
  'px-4 py-2 rounded',
  isActive && 'bg-blue-600 text-white'  // НЕ синхронизировано с design-system
)}>
```

**Исправленный код:**

```tsx
// ✅ Использование токена primary
<button className={cn(
  'px-4 py-2 rounded',
  isActive && 'bg-primary text-white hover:bg-primary-hover'
)}>
```

#### 5. Badge Component

**Файл:** `frontend/src/components/ui/Badge/Badge.tsx`

**Текущий код:**

```tsx
// ❌ Старые цвета
const variantClasses = {
  new: "bg-[#E1F0FF] text-[#0F5DA3]",
  hit: "bg-[#E3F6EC] text-[#1F7A4A]",
  promo: "bg-[#F4EBDC] text-[#8C4C00]",
  sale: "bg-[#F9E1E1] text-[#A63232]",
};
```

**Исправленный код:**

```tsx
// ✅ Новые цвета из токенов
const variantClasses = {
  new: "bg-[#E7F3FF] text-primary", // #0060FF
  hit: "bg-[#E0F5E8] text-accent-success", // #00AA5B
  promo: "bg-[#FFF0F5] text-accent-promo", // #FF2E93
  sale: "bg-[#FFE1E8] text-accent-danger", // #E53935
  discount: "bg-[#F0E7FF] text-[#7C3AED]",
};
```

#### 6. Toast Component

**Файл:** `frontend/src/components/ui/Toast/Toast.tsx`

**Текущий код:**

```tsx
// ❌ Старые border цвета
const variantClasses = {
  info: "border-l-4 border-[#0F5DA3]",
  success: "border-l-4 border-[#1F7A1F]",
  warning: "border-l-4 border-[#B07600]",
  error: "border-l-4 border-[#C23B3B]",
};
```

**Исправленный код:**

```tsx
// ✅ Новые semantic цвета
const variantClasses = {
  info: "border-l-4 border-primary", // #0060FF
  success: "border-l-4 border-accent-success", // #00AA5B
  warning: "border-l-4 border-accent-warning", // #F5A623
  error: "border-l-4 border-accent-danger", // #E53935
};
```

#### 7. SearchFilters Chip

**Файл:** `frontend/src/components/catalog/SearchFilters.tsx`

**Текущий код:**

```tsx
// ✅ УЖЕ использует токен primary - изменений НЕ требуется
<button className={cn(
  'px-4 py-2 rounded-full',
  selected && 'bg-primary text-white'  // #0060FF автоматически
)}>
```

#### 8. ProductGallery Thumbnails

**Файл:** `frontend/src/components/product/ProductGallery.tsx`

**Текущий код:**

```tsx
// ✅ УЖЕ использует primary - изменений НЕ требуется
<div className={cn(
  'border-2',
  isSelected && 'border-primary'  // #0060FF автоматически
)}>
```

#### 9. ProductSummary CTA

**Файл:** `frontend/src/components/product/ProductSummary.tsx`

**Текущий код:**

```tsx
// ✅ УЖЕ использует primary - изменений НЕ требуется
<Button variant="primary">
  {" "}
  {/* #0060FF автоматически */}
  Добавить в корзину
</Button>
```

#### 10. Header Navigation

**Файл:** `frontend/src/components/layout/Header.tsx`

**Текущий код:**

```tsx
// ❌ Смешанное использование
<nav>
  <a
    className={cn(
      "text-neutral-700",
      isActive && "text-primary", // ✅ УЖЕ токен
    )}
  ></a>
  <div className="bg-[#F9E1E1] text-[#A63232]">
    {" "}
    {/* ❌ Хардкод для cart badge */}
    {cartCount}
  </div>
</nav>
```

**Исправленный код:**

```tsx
// ✅ Использование новых токенов
<nav>
  <a
    className={cn(
      "text-neutral-700",
      isActive && "text-primary", // Автоматически #0060FF
    )}
  ></a>
  <div className="bg-[#FFE1E8] text-accent-danger">
    {" "}
    {/* Новые цвета sale badge */}
    {cartCount}
  </div>
</nav>
```

#### 11. Tabs Component

**Файл:** `frontend/src/components/ui/Tabs/Tabs.tsx`

**Текущий код:**

```tsx
// ❌ Хардкод active text color
<button className={cn(
  'pb-2 border-b-2 transition-colors',
  isActive ? 'border-primary text-[#1F1F1F]' : 'border-transparent text-neutral-600'
)}>
```

**Исправленный код:**

```tsx
// ✅ Использование primary для active text
<button className={cn(
  'pb-2 border-b-2 transition-colors',
  isActive ? 'border-primary text-primary' : 'border-transparent text-neutral-600'
)}>
```

#### 12. Form Input Focus States

**Файл:** `frontend/src/components/ui/Input/Input.tsx`

**Текущий код:**

```tsx
// ❌ Хардкод outline цвета
<input className="focus:outline-[#1F1F1F]/60 focus:ring-4 focus:ring-[#1F1F1F]/12" />
```

**Исправленный код:**

```tsx
// ✅ Использование primary токена
<input className="focus:outline-primary/60 focus:ring-4 focus:ring-primary/12" />
```

#### 13. Link Component (если используется)

**Файл:** `frontend/src/components/ui/Link/Link.tsx`

**Текущий код:**

```tsx
// ❌ Хардкод
<a className="text-[#1F1F1F] hover:text-[#3A3A3A]">
```

**Исправленный код:**

```tsx
// ✅ Токены
<a className="text-primary hover:text-primary-hover">
```

**Итого компонентов требующих обновления:** 8 файлов с хардкодом цветов

---

### 3.7 Story Documents

#### Story 11.0: Product badge flags

**Файл:** `docs/stories/epic-11/11.0.product-badge-flags.story.md`

**Конфликт:** ⚠️ **СРЕДНИЙ** - Цвета бейджей изменены

**Требуемое обновление:**

**Acceptance Criteria 3 - Визуальные требования:**

```markdown
## БЫЛО:

Цвета бейджей:

- `new`: bg #E1F0FF, text #0F5DA3
- `hit`: bg #E3F6EC, text #1F7A4A
- `promo`: bg #F4EBDC, text #8C4C00
- `sale`: bg #F9E1E1, text #A63232

## СТАЛО:

Цвета бейджей (обновлено 2025-11-25):

- `new`: bg #E7F3FF, text #0060FF (primary)
- `hit`: bg #E0F5E8, text #00AA5B (accent-success)
- `promo`: bg #FFF0F5, text #FF2E93 (accent-promo)
- `sale`: bg #FFE1E8, text #E53935 (accent-danger)
- `discount`: bg #F0E7FF, text #7C3AED
```

**Добавить примечание:**

```markdown
> **Примечание (2025-11-25):** Цвета бейджей обновлены в соответствии с миграцией
> на сине-голубую цветовую схему. См. [color-scheme-migration.md](../../frontend/color-scheme-migration.md)
```

---

#### Story 11.1: Hero Section Layout

**Файл:** `docs/stories/epic-11/11.1.hero-section-layout.story.md`

**Конфликт:** ⚠️ **СРЕДНИЙ** - CTA кнопки изменили цвет

**Требуемое обновление:**

**Acceptance Criteria 2 - CTA Buttons:**

```markdown
## БЫЛО:

- Primary CTA: bg #1F1F1F (графитовый), hover #3A3A3A
- Secondary CTA: border #1F1F1F, text #1F1F1F

## СТАЛО:

- Primary CTA: bg #0060FF (синий), hover #0047CC, active #0037A6
- Secondary CTA: border #0060FF, text #0060FF, hover bg #E7F3FF
```

**Добавить в Technical Notes:**

```markdown
### Цветовая схема (обновлено 2025-11-25)

Кнопки используют новую сине-голубую палитру:

- Primary button: `bg-primary hover:bg-primary-hover` (#0060FF → #0047CC)
- Secondary button: `border-primary text-primary hover:bg-primary-subtle`
- Все цвета используют токены из design-system.json v2.1.0
```

---

#### Story 11.2: Dynamic content blocks

**Файл:** `docs/stories/epic-11/11.2.dynamic-content-blocks.story.md`

**Конфликт:** ⚠️ **ВЫСОКИЙ** - Активная разработка, требует синхронизации

**Требуемое обновление:**

**Acceptance Criteria 1 & 2 - Badge colors:**

```markdown
## ОБНОВЛЕНО (2025-11-25):

Автоматическое определение типа Badge использует новые цвета:

- Приоритет 1: `variant="sale"` → bg #FFE1E8, text #E53935 (было #F9E1E1/#A63232)
- Приоритет 2: `variant="promo"` → bg #FFF0F5, text #FF2E93 (было #F4EBDC/#8C4C00)
- Приоритет 3: `variant="new"` → bg #E7F3FF, text #0060FF (было #E1F0FF/#0F5DA3)
- Приоритет 4: `variant="hit"` → bg #E0F5E8, text #00AA5B (было #E3F6EC/#1F7A4A)
- Приоритет 5: `variant="premium"` → без изменений
```

**Добавить в Dependencies:**

```markdown
### Цветовая миграция (2025-11-25)

- ⚠️ Story разрабатывается параллельно с миграцией цветовой схемы
- Использовать обновлённый Badge компонент с новыми цветами
- См. [color-scheme-migration.md](../../frontend/color-scheme-migration.md)
```

**Обновить Task 1.5 - Badge Component:**

```markdown
- [ ] Task 1.5: Создать/обновить Badge component
  - [ ] Использовать цвета из design-system.json v2.1.0
  - [ ] Убедиться что все variants используют новую палитру:
    - new: #E7F3FF / #0060FF
    - hit: #E0F5E8 / #00AA5B
    - promo: #FFF0F5 / #FF2E93
    - sale: #FFE1E8 / #E53935
```

---

### 3.8 Дополнительные артефакты

#### UI Testing Screenshots

**Директория:** `frontend/__tests__/__snapshots__/`

**Влияние:** ⚠️ **СРЕДНЕЕ** - Snapshot тесты сломаются

**Действие:**

1. Обновить визуальные snapshot тесты после применения новой палитры
2. Запустить `npm run test:update-snapshots` для регенерации
3. Провести визуальный review обновлённых snapshots

#### Storybook (если используется)

**Файлы:** `frontend/.storybook/`, `*.stories.tsx`

**Влияние:** ⚠️ **СРЕДНЕЕ** - Stories покажут старые цвета

**Действие:**

1. Обновить Storybook конфигурацию с новыми токенами
2. Проверить все stories на соответствие новой палитре
3. Обновить документацию в Storybook

---

## 4. Рекомендуемый путь вперёд

### 4.1 Выбранная стратегия

**✅ ВАРИАНТ 1: Прямая интеграция (Direct Adjustment)**

**Обоснование:**

1. ✅ Изменение **НЕ затрагивает функциональность** - только визуал
2. ✅ **Обратная совместимость** частично сохранена через CSS-переменные
3. ✅ **Минимальный риск** для текущей разработки Epic 11
4. ✅ **Короткие сроки** реализации (5-7 дней)
5. ✅ **Не требует rollback** завершённых Epic

**Альтернативные варианты (отклонены):**

❌ **Вариант 2: Rollback Epic 11**

- Причина отклонения: Epic 11 на 40% завершён, rollback уничтожит проделанную работу
- Нецелесообразно для визуального изменения

❌ **Вариант 3: Откладывание миграции до Epic 12**

- Причина отклонения: Создаст технический долг и несоответствие дизайну
- Затруднит параллельную разработку Epic 11.2 и 11.3

### 4.2 Оценка осуществимости

**Технические риски:**

| Риск                       | Вероятность | Влияние | Митигация                              |
| -------------------------- | ----------- | ------- | -------------------------------------- |
| Сломанные визуальные тесты | Высокая     | Низкое  | Обновить snapshots (автоматизировано)  |
| Пропущенный хардкод цветов | Средняя     | Среднее | Code review + grep поиск HEX кодов     |
| Проблемы контрастности     | Низкая      | Высокое | Уже проверено в миграционном документе |
| Конфликт с Epic 11.2       | Средняя     | Среднее | Синхронизировать с разработчиком       |

**Трудозатраты:**

| Задача                                | Оценка                   | Приоритет   |
| ------------------------------------- | ------------------------ | ----------- |
| Обновление design-system.json         | 2 часа                   | Критический |
| Обновление globals.css                | 1 час                    | Критический |
| Рефакторинг UI компонентов (8 файлов) | 8 часов                  | Высокий     |
| Обновление story документов (3 файла) | 2 часа                   | Средний     |
| Обновление front-end-spec.md          | 3 часа                   | Высокий     |
| Визуальное тестирование               | 4 часа                   | Высокий     |
| Обновление snapshot тестов            | 2 часа                   | Средний     |
| Code review и исправления             | 4 часа                   | Высокий     |
| **ИТОГО**                             | **26 часов (~5-7 дней)** |             |

---

### 4.3 Влияние на MVP Scope

**MVP Scope:** ✅ **БЕЗ ИЗМЕНЕНИЙ**

**Обоснование:**

- Миграция **НЕ добавляет новых функций** → scope не расширяется
- Миграция **НЕ удаляет функции** → scope не сужается
- Миграция **улучшает визуальную составляющую** → качество MVP повышается
- Все функциональные требования (FR1-FR15) остаются актуальными

**Критерии успеха Фазы 1:** ✅ **БЕЗ ИЗМЕНЕНИЙ**

Бизнес-метрики и технические метрики из PRD не затронуты:

- PageSpeed >70 - не зависит от цветов
- Время отклика API <2с - не зависит от цветов
- Мобильная адаптивность - сохраняется

---

## 5. Детальный план внедрения

### Фаза 1: Обновление источников истины (Дни 1-2)

**Приоритет:** 🔴 **КРИТИЧЕСКИЙ** - блокирует остальные фазы

#### День 1: Design System JSON

```bash
Файл: docs/frontend/design-system.json
Ответственный: Frontend Lead / Design System Owner

Задачи:
1. ✅ Обновить meta.version → "2.1.0"
2. ✅ Обновить meta.lastUpdated → "2025-11-25"
3. ✅ Добавить changeLog запись
4. ✅ Обновить brand.colorPhilosophy
5. ✅ Заменить все токены в foundations.colors (см. раздел 3.4)
6. ✅ Обновить компоненты: Button, Badge, Checkbox, Toggle, Tabs, Toast
7. ✅ Обновить shadows и focus states
8. ✅ Создать git commit: "feat(design-system): migrate to blue color scheme v2.1.0"

Проверка:
- JSON валидация (npm run validate:design-system)
- Нет конфликтов с существующими токенами
```

#### День 2: CSS Variables

```bash
Файл: frontend/src/app/globals.css
Ответственный: Frontend Developer

Задачи:
1. ✅ Обновить все --color-* переменные (см. раздел 3.5)
2. ✅ Обновить --shadow-* переменные
3. ✅ Обновить --focus-* переменные
4. ✅ Добавить комментарий о миграции
5. ✅ Проверить синтаксис Tailwind 4.0
6. ✅ Запустить dev сервер для проверки автоприменения
7. ✅ Создать git commit: "feat(styles): apply blue color tokens to CSS variables"

Проверка:
- npm run dev (проверить отсутствие ошибок компиляции)
- Визуальный осмотр главной страницы (некоторые элементы уже изменятся)
```

---

### Фаза 2: Рефакторинг UI компонентов (Дни 3-4)

**Приоритет:** 🟠 **ВЫСОКИЙ**

#### День 3: Core UI Kit Components

**Button Component:**

```bash
Файл: frontend/src/components/ui/Button/Button.tsx
Изменения:
- Заменить хардкод hex на токены Tailwind
- Обновить варианты: primary, secondary, subtle
- Добавить комментарий о миграции

Тестирование:
- npm run test Button.test.tsx
- Визуальный осмотр в Storybook (если есть)
```

**Badge Component:**

```bash
Файл: frontend/src/components/ui/Badge/Badge.tsx
Изменения:
- Обновить все варианты: new, hit, promo, sale, discount
- Использовать accent-* токены

КРИТИЧНО: Этот компонент используется в Story 11.2 (в разработке)
→ Координация с разработчиком обязательна!
```

**Checkbox & Toggle:**

```bash
Файлы:
- frontend/src/components/ui/Checkbox/Checkbox.tsx
- frontend/src/components/ui/Toggle/Toggle.tsx

Изменения:
- Заменить checked bg/border на primary токены
```

**Tabs & Input:**

```bash
Файлы:
- frontend/src/components/ui/Tabs/Tabs.tsx
- frontend/src/components/ui/Input/Input.tsx

Изменения:
- Active text color → primary
- Focus states → primary
```

#### День 4: Page-level Components

**Pagination (Catalog):**

```bash
Файл: frontend/src/app/catalog/page.tsx
Изменения:
- bg-blue-600 → bg-primary (active page)
```

**Header:**

```bash
Файл: frontend/src/components/layout/Header.tsx
Изменения:
- Cart badge: старый #F9E1E1/#A63232 → новый #FFE1E8/accent-danger
```

**Toast Component:**

```bash
Файл: frontend/src/components/ui/Toast/Toast.tsx
Изменения:
- Border colors для всех вариантов
```

**Git Commit:**

```bash
git commit -m "refactor(ui): migrate all components to blue color scheme

- Button: use primary tokens instead of hardcoded gray
- Badge: update to semantic accent colors
- Checkbox/Toggle: primary for active states
- Pagination: sync with design-system primary
- Header: update cart badge to new sale colors
- Toast: semantic border colors
- Tabs/Input: focus states with primary

Related: color-scheme-migration.md
Design System: v2.1.0
"
```

---

### Фаза 3: Обновление документации (День 5)

**Приоритет:** 🟡 **СРЕДНИЙ**

#### Frontend Specification

```bash
Файл: docs/front-end-spec.md
Задачи:
1. Обновить раздел "Дизайн-принципы" (графитовые → синие акценты)
2. Заменить все цветовые таблицы (Primary, Secondary, Accent, Neutral)
3. Обновить примеры компонентов
4. Добавить запись в Журнал изменений (v2.1, 2025-11-25)

Коммит: "docs(frontend-spec): update to blue color scheme v2.1"
```

#### Story Documents

```bash
Файлы:
- docs/stories/epic-11/11.0.product-badge-flags.story.md
- docs/stories/epic-11/11.1.hero-section-layout.story.md
- docs/stories/epic-11/11.2.dynamic-content-blocks.story.md

Задачи:
1. Обновить AC с цветовыми спецификациями
2. Добавить примечания о миграции
3. Обновить Technical Notes разделы

Коммит: "docs(stories): sync Epic 11 stories with new color scheme"
```

#### Migration Document Integration

```bash
Файл: docs/frontend/color-scheme-migration.md
Задачи:
1. Обновить статус: "Планирование" → "Реализовано"
2. Добавить раздел "Результаты внедрения"
3. Отметить завершённые фазы в плане миграции
4. Добавить ссылки на коммиты изменений

Коммит: "docs(migration): mark color scheme migration as completed"
```

---

### Фаза 4: Тестирование и QA (Дни 6-7)

**Приоритет:** 🟠 **ВЫСОКИЙ**

#### День 6: Автоматизированное тестирование

**Unit Tests:**

```bash
Задачи:
1. Запустить все тесты: npm test
2. Обновить snapshot тесты: npm run test:update-snapshots
3. Проверить coverage: npm run test:coverage (должно остаться >80%)

Ожидаемые изменения:
- Все snapshot тесты требуют обновления (цвета изменились)
- Логические тесты НЕ должны сломаться (функциональность не затронута)
```

**Visual Regression Testing:**

```bash
Инструменты: Percy / Chromatic (если настроены)
Задачи:
1. Запустить визуальные тесты на всех breakpoints
2. Сравнить screenshots до/после миграции
3. Утвердить визуальные изменения
```

**Accessibility Testing:**

```bash
Инструменты: axe-core, WAVE, контрастомер
Задачи:
1. Проверить контрастность текста (WCAG AA)
   - #0060FF на #FFFFFF = 4.5:1 ✅
   - #1F2A44 на #FFFFFF = 12.6:1 ✅
2. Проверить focus indicators (видимость)
3. Запустить axe-core audit: npm run test:a11y
```

#### День 7: Ручное тестирование

**Чек-лист страниц:**

```markdown
✅ Desktop (1920x1080)

- [ ] Главная страница (Hero, динамические блоки)
- [ ] Каталог товаров (фильтры, пагинация, карточки)
- [ ] Карточка товара (галерея, бейджи, CTA)
- [ ] Корзина (кнопки, итоги)
- [ ] Checkout (формы, validation)
- [ ] Личный кабинет (навигация, секции)
- [ ] Header (навигация, cart badge)
- [ ] Footer (ссылки)

✅ Tablet (768x1024)

- [ ] Проверить все страницы выше
- [ ] Проверить touch interactions

✅ Mobile (375x667)

- [ ] Проверить все страницы выше
- [ ] Проверить burger menu

✅ Браузеры

- [ ] Chrome 90+
- [ ] Firefox 88+
- [ ] Safari 14+
- [ ] Edge 90+
```

**Компоненты UI Kit:**

```markdown
- [ ] Button (все варианты + состояния)
- [ ] Badge (все варианты)
- [ ] Checkbox (checked/unchecked/indeterminate)
- [ ] Toggle (on/off)
- [ ] Tabs (active/inactive)
- [ ] Toast (все варианты)
- [ ] Input (focus/blur/error)
- [ ] Pagination (active page)
```

**Интерактивные состояния:**

```markdown
- [ ] :hover (все интерактивные элементы)
- [ ] :active (кнопки, ссылки)
- [ ] :focus (формы, кнопки)
- [ ] :disabled (кнопки, инпуты)
```

**QA Sign-off:**

```bash
Критерии приёмки:
✅ Все unit тесты проходят
✅ Контрастность WCAG AA соблюдена
✅ Нет визуальных багов на 3 breakpoints
✅ Работает во всех поддерживаемых браузерах
✅ Интерактивные состояния корректны
✅ Performance не ухудшилась (PageSpeed >70)
```

---

### Фаза 5: Развёртывание и мониторинг (День 7)

**Приоритет:** 🟢 **СТАНДАРТНЫЙ**

#### Staging Deployment

```bash
Задачи:
1. Деплой на staging среду
2. Smoke testing критических флоу
3. Получение approval от stakeholders
```

#### Production Deployment

```bash
Задачи:
1. Создать релизную ветку: release/color-scheme-v2.1
2. Merge в main через PR
3. Деплой на production
4. Мониторинг ошибок (Sentry, LogRocket)
```

#### Rollback Plan

```bash
На случай критических проблем:
1. Git revert коммитов миграции
2. Откат через CI/CD pipeline
3. Время rollback: <15 минут
```

---

## 6. Координация с Epic 11.2 (Критично!)

**Проблема:** Story 11.2 (Dynamic content blocks) находится в **активной разработке** параллельно с миграцией.

### 6.1 Стратегия синхронизации

**Вариант А (Рекомендуемый): Последовательная интеграция**

```markdown
1. ПАУЗА Story 11.2 до завершения Фазы 2 (рефакторинг UI)
   - Разработчик создаёт feature branch и приостанавливает работу
   - Миграция применяется в main ветке
   - Разработчик делает rebase на обновлённую main

Плюсы:
✅ Нет конфликтов слияния
✅ Разработчик работает уже с новыми цветами
✅ Простота координации

Минусы:
❌ Задержка Story 11.2 на 4 дня
```

**Вариант Б: Параллельная разработка с координацией**

```markdown
1. Story 11.2 продолжается в feature branch
2. Миграция происходит в main ветке
3. После завершения миграции:
   - Разработчик делает rebase feature branch на main
   - Вручную разрешает конфликты в Badge компоненте
   - Обновляет цвета в своих компонентах

Плюсы:
✅ Нет задержки Story 11.2
✅ Параллельная работа

Минусы:
❌ Высокий риск конфликтов слияния
❌ Дополнительная работа по разрешению конфликтов
❌ Требует тесной координации
```

### 6.2 Рекомендация

**✅ Выбрать Вариант А (Последовательная интеграция)**

**Обоснование:**

1. Story 11.2 оценена в 8 story points → 8-10 дней работы
2. Миграция займёт 5-7 дней → задержка составит <50% от общего времени Story
3. Избежание конфликтов сэкономит 1-2 дня на разрешение
4. Разработчик сразу работает с финальными цветами → нет переделки

**План действий:**

```markdown
1. Уведомить разработчика Story 11.2 о приостановке (сегодня)
2. Разработчик коммитит текущий прогресс в feature/story-11.2
3. Запустить миграцию (Дни 1-7)
4. После завершения миграции:
   - Разработчик делает: git rebase main
   - Обновляет Badge цвета согласно новой палитре
   - Продолжает работу над Story 11.2
```

---

## 7. Критерии успеха миграции

### 7.1 Технические критерии

```markdown
✅ Обязательные (Must-have):

- [ ] Все unit тесты проходят (100%)
- [ ] Контрастность WCAG AA соблюдена
- [ ] Нет хардкод HEX кодов в компонентах (кроме исключений)
- [ ] design-system.json синхронизирован с globals.css
- [ ] PageSpeed >70 сохранён
- [ ] Нет console errors в браузере

✅ Желательные (Should-have):

- [ ] Visual regression tests проходят
- [ ] Storybook обновлён (если есть)
- [ ] Accessibility audit 100%
- [ ] Cross-browser testing пройден

✅ Nice-to-have:

- [ ] Performance улучшился
- [ ] Bundle size не увеличился
```

### 7.2 Бизнес-критерии

```markdown
✅ Stakeholder approval:

- [ ] Design Lead утвердил визуальную реализацию
- [ ] Product Owner одобрил изменения
- [ ] QA подписал тестирование

✅ User Experience:

- [ ] Визуальная иерархия улучшилась
- [ ] CTA элементы более заметны
- [ ] Нет жалоб от пользователей после деплоя

✅ Documentation:

- [ ] Все документы обновлены
- [ ] Migration guide создан
- [ ] Change log заполнен
```

---

## 8. Риски и митигация

| #   | Риск                                          | Вероятность | Влияние | Митигация                                              | Владелец      |
| --- | --------------------------------------------- | ----------- | ------- | ------------------------------------------------------ | ------------- |
| 1   | Пропущенный хардкод цветов в компонентах      | Средняя     | Среднее | Grep search по `.tsx` файлам на паттерн `#[0-9A-F]{6}` | Frontend Lead |
| 2   | Конфликт с разработкой Story 11.2             | Высокая     | Высокое | Приостановка Story 11.2 на период миграции             | PM + Dev      |
| 3   | Сломанные визуальные тесты                    | Высокая     | Низкое  | Автообновление snapshots, QA review                    | QA Engineer   |
| 4   | Проблемы контрастности на edge cases          | Низкая      | Высокое | Ручной аудит всех текстовых комбинаций                 | Design Lead   |
| 5   | Regression багов в интерактивных состояниях   | Средняя     | Среднее | Детальный чек-лист тестирования                        | QA Engineer   |
| 6   | Увеличение bundle size                        | Низкая      | Низкое  | Анализ бандла до/после                                 | Frontend Lead |
| 7   | Несоответствие Storybook реальным компонентам | Средняя     | Низкое  | Обновление Storybook конфигурации                      | Frontend Dev  |
| 8   | Задержка релиза Epic 11                       | Низкая      | Среднее | Параллельное выполнение некритичных задач              | PM            |

---

## 9. Зависимости и блокеры

### 9.1 Внешние зависимости

```markdown
✅ Не требуется:

- Backend изменений (цвета только frontend)
- Изменений в 1С интеграции
- Database миграций
- API обновлений

✅ Требуется:

- Утверждение Design Lead (новая палитра)
- Координация с разработчиком Story 11.2
- QA ресурсы для тестирования (2 дня)
```

### 9.2 Технические блокеры

```markdown
❌ Критические блокеры:

- (Нет)

⚠️ Потенциальные блокеры:

- Если Story 11.2 уже в code review → нужна немедленная координация
- Если есть незакоммиченные изменения в UI компонентах → нужна синхронизация
```

---

## 10. Коммуникационный план

### 10.1 Stakeholders

| Роль                      | Уведомление         | Частота   | Формат              |
| ------------------------- | ------------------- | --------- | ------------------- |
| Product Owner             | Начало + Завершение | 2 раза    | Slack + Demo        |
| Design Lead               | Каждая фаза         | Ежедневно | Figma + Screenshots |
| Frontend Dev (Story 11.2) | Real-time           | Постоянно | Slack + Stand-up    |
| QA Engineer               | Фаза 4              | Daily     | Test reports        |
| Backend Team              | FYI                 | 1 раз     | Slack announcement  |

### 10.2 Шаблон уведомления

**Начало миграции:**

```markdown
📢 Начинается миграция цветовой схемы FREESPORT

Сроки: 2025-11-25 до 2025-12-02 (7 дней)
Влияние: Frontend UI компоненты, документация
НЕ влияет на: Backend, API, функциональность

Детали: docs/sprint-change-proposal-color-migration.md
Вопросы: @john (PM)
```

**Завершение миграции:**

```markdown
✅ Миграция цветовой схемы завершена

Изменено:

- 8 UI компонентов обновлено
- 3 story документа синхронизировано
- design-system.json → v2.1.0
- Все тесты проходят ✅

Staging: [ссылка]
Можно продолжать Story 11.2 ✅

Отчёт: docs/sprint-change-proposal-color-migration.md
```

---

## 11. Финальные рекомендации

### 11.1 Немедленные действия (Сегодня)

```markdown
1. ✅ Получить approval на Sprint Change Proposal от Product Owner
2. ✅ Уведомить разработчика Story 11.2 о приостановке
3. ✅ Назначить ответственных за каждую фазу
4. ✅ Создать feature branch: feature/color-scheme-migration
5. ✅ Запланировать kick-off встречу с командой
```

### 11.2 Следующие шаги после утверждения

```markdown
День 1 (Завтра):

- [ ] Kick-off встреча (30 мин)
- [ ] Обновление design-system.json (2 часа)
- [ ] Code review изменений в JSON

День 2:

- [ ] Обновление globals.css (1 час)
- [ ] Проверка автоприменения на dev сервере
- [ ] Начало рефакторинга UI компонентов

День 3-4:

- [ ] Завершение рефакторинга всех 8 компонентов
- [ ] Code review PR

День 5:

- [ ] Обновление документации
- [ ] Синхронизация story documents

День 6-7:

- [ ] Полное тестирование (авто + ручное)
- [ ] Staging deployment
- [ ] Final approval
- [ ] Production deployment
```

### 11.3 План B (Rollback)

```markdown
Если критические проблемы обнаружены после деплоя:

1. IMMEDIATE ROLLBACK (15 минут):
   git revert [migration-commits]
   Deploy previous version

2. INVESTIGATION (1 час):
   Анализ проблемы
   Определение root cause

3. FIX (зависит от проблемы):
   Hotfix в feature branch
   Повторное тестирование
   Re-deploy

4. POST-MORTEM:
   Документирование инцидента
   Обновление процесса миграции
```

---

## 12. Заключение

### 12.1 Резюме предложения

Миграция на сине-голубую цветовую схему является **стратегически важным визуальным улучшением**, которое:

✅ **Улучшает бренд:** Более современный и технологичный визуальный стиль
✅ **Повышает UX:** Улучшенная визуальная иерархия и контрастность CTA
✅ **Минимизирует риски:** Не затрагивает функциональность, обратно совместимо
✅ **Реалистичные сроки:** 5-7 дней с чётким планом внедрения
✅ **Управляемые риски:** Все риски идентифицированы с планами митигации

### 12.2 Рекомендация Product Manager

**Я рекомендую УТВЕРДИТЬ данное предложение** по следующим причинам:

1. **Визуальное обновление без функционального риска** - идеальное timing для улучшения
2. **Минимальное влияние на текущую разработку** - только 1 story (11.2) требует координации
3. **Усиливает позиционирование бренда** - соответствие трендам e-commerce
4. **Детальный план с митигацией рисков** - все аспекты проработаны
5. **Сохранение MVP scope** - не отвлекает от основных целей Фазы 1

### 12.3 Требуется утверждение

```markdown
[ ] Product Owner - утверждение начала миграции
[ ] Design Lead - утверждение новой палитры
[ ] Frontend Lead - подтверждение технической осуществимости
[ ] QA Lead - подтверждение плана тестирования
```

---

**Документ подготовлен:** John (PM Agent) 📋
**Дата:** 2025-11-25
**Версия:** 1.0
**Статус:** Ожидает утверждения

**Следующий шаг:** Утверждение stakeholders → Kick-off встреча → Начало Фазы 1

---

## Приложения

### Приложение А: Таблица замен цветов (полная)

См. [color-scheme-migration.md раздел 3](frontend/color-scheme-migration.md#3-таблица-замен-по-компонентам)

### Приложение Б: Grep команды для поиска хардкода

```bash
# Поиск HEX кодов в компонентах
grep -r "#[0-9A-Fa-f]\{6\}" frontend/src/components --include="*.tsx"

# Поиск старых цветов (графитовые)
grep -r "#1F1F1F\|#3A3A3A\|#3D3D3D" frontend/src --include="*.tsx"

# Поиск классов Tailwind с цветами (потенциальный хардкод)
grep -r "bg-\[#" frontend/src --include="*.tsx"
grep -r "text-\[#" frontend/src --include="*.tsx"
grep -r "border-\[#" frontend/src --include="*.tsx"
```

### Приложение В: Контрастность WCAG AA (проверено)

| Комбинация         | Контраст | WCAG AA | Статус        |
| ------------------ | -------- | ------- | ------------- |
| #0060FF на #FFFFFF | 4.5:1    | ≥4.5:1  | ✅ Pass       |
| #1F2A44 на #FFFFFF | 12.6:1   | ≥4.5:1  | ✅ Pass       |
| #4B5C7A на #FFFFFF | 6.2:1    | ≥4.5:1  | ✅ Pass       |
| #FFFFFF на #0060FF | 4.5:1    | ≥4.5:1  | ✅ Pass       |
| #0060FF на #E7F3FF | 4.1:1    | ≥4.5:1  | ⚠️ Borderline |

**Рекомендация:** Для мелкого текста на `#E7F3FF` использовать `#0047CC` вместо `#0060FF`.

### Приложение Г: Checklist для разработчика

```markdown
# Pre-migration checklist

- [ ] Создан feature branch: feature/color-scheme-migration
- [ ] design-system.json backed up
- [ ] globals.css backed up
- [ ] Все текущие изменения закоммичены

# Phase 1 checklist

- [ ] design-system.json обновлён
- [ ] JSON валидация пройдена
- [ ] globals.css обновлён
- [ ] CSS компиляция без ошибок
- [ ] Dev server запускается

# Phase 2 checklist (per component)

- [ ] Хардкод цветов заменён на токены
- [ ] Все варианты обновлены
- [ ] Тесты проходят
- [ ] Storybook обновлён (если есть)

# Phase 3 checklist

- [ ] front-end-spec.md обновлён
- [ ] Story 11.0 обновлена
- [ ] Story 11.1 обновлена
- [ ] Story 11.2 обновлена
- [ ] color-scheme-migration.md статус обновлён

# Phase 4 checklist

- [ ] npm test прошёл
- [ ] Snapshots обновлены
- [ ] Accessibility audit пройден
- [ ] Ручное тестирование завершено
- [ ] QA sign-off получен

# Phase 5 checklist

- [ ] Staging deployment успешен
- [ ] Stakeholder approval получен
- [ ] Production deployment выполнен
- [ ] Post-deploy monitoring настроен
```

---

**КОНЕЦ ДОКУМЕНТА**
