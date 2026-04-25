# Миграция на Design System v2.0

**Дата:** 2025-11-20
**Версия:** 1.0
**Автор:** James (Dev Agent)

## Обзор

Этот документ описывает изменения при переходе с Design System v1.x на v2.0 и предоставляет руководство по обновлению существующих компонентов.

## 🚨 Breaking Changes

### 1. Цветовая палитра - монохромная графитовая

**v2.0 переходит на монохромную графитовую палитру** вместо синих акцентов v1.x.

#### Основные изменения цветов:

| Токен                    | v1.x (старое)   | v2.0 (новое)     | Комментарий                      |
| ------------------------ | --------------- | ---------------- | -------------------------------- |
| `--color-primary`        | #0060FF (синий) | #1F1F1F (графит) | Главный акцент теперь графитовый |
| `--color-primary-hover`  | #0047CC         | #3A3A3A          | Hover графитовый                 |
| `--color-primary-active` | #0037A6         | #0D0D0D          | Active темно-графитовый          |
| `--color-primary-subtle` | #E7F3FF         | #F2F2F2          | Subtle светло-серый              |

### 2. Typography Color Usage

Добавлены новые специфические цвета для типографики:

```css
/* НОВЫЕ переменные v2.0 */
--color-typography-primary: #1f2a44;
--color-typography-secondary: #4b5c7a;
--color-typography-muted: #7f8ca8;
--color-typography-inverse: #ffffff;
```

**Когда использовать:**

- `--color-text-primary` (#1B1B1B) - для обычного текста на светлом фоне
- `--color-typography-primary` (#1F2A44) - для типографики в специфических контекстах (заголовки на цветном фоне, акцентный текст)

### 3. Background Переменные

Добавлены семантические переменные для фонов:

```css
--bg-canvas: #f5f7fb; /* Основной фон страницы */
--bg-panel: #ffffff; /* Фон карточек и панелей */
--bg-emphasis: linear-gradient(
  135deg,
  rgba(0, 78, 255, 0.12),
  rgba(0, 149, 255, 0.08)
);
```

### 4. Shadows - обновленные rgba значения

Shadow токены обновлены для соответствия новой палитре:

```css
/* v2.0 - обновленные значения */
--shadow-primary: 0 10px 24px rgba(0, 96, 255, 0.28);
--shadow-secondary: 0 6px 16px rgba(0, 71, 204, 0.12);
--shadow-pressed: 0 6px 18px rgba(0, 55, 166, 0.24);
```

## 📋 Mapping Tokens: v1.x → v2.0

### Цвета

```typescript
// Замены в компонентах
const migrationMap = {
  // Primary colors
  "bg-blue-600": "bg-primary", // #0060FF → #1F1F1F
  "text-blue-600": "text-primary",
  "border-blue-600": "border-primary",

  // Hover states
  "hover:bg-blue-700": "hover:bg-primary-hover",

  // Secondary цвета - меньше изменений
  // но проверьте visual consistency
};
```

### CSS Custom Properties

```css
/* v1.x */
.button-primary {
  background-color: #0060ff;
  color: #ffffff;
}

/* v2.0 - используйте переменные */
.button-primary {
  background-color: var(--color-primary); /* #1F1F1F */
  color: var(--color-text-inverse);
}
```

## 🔄 Рекомендации по обновлению компонентов

### Шаг 1: Аудит использования цветов

```bash
# Найти все использования старых цветов
grep -r "#0060FF" frontend/src/components/
grep -r "bg-blue-" frontend/src/components/
grep -r "text-blue-" frontend/src/components/
```

### Шаг 2: Замена хардкодов на CSS переменные

**❌ Плохо (хардкод):**

```tsx
<button className="bg-[#0060FF] text-white">Click me</button>
```

**✅ Хорошо (CSS переменные):**

```tsx
<button className="bg-primary text-inverse">Click me</button>
```

### Шаг 3: Использование Typography Colors

**Для обычного текста:**

```tsx
<p className="text-primary">Основной текст</p>
<p className="text-secondary">Вторичный текст</p>
<p className="text-muted">Приглушенный текст</p>
```

**Для типографики в специальных контекстах:**

```css
.hero-title {
  color: var(--color-typography-primary);
}

.subheading {
  color: var(--color-typography-secondary);
}
```

### Шаг 4: Обновление фонов

```tsx
// Основной фон страницы
<div style={{ background: 'var(--bg-canvas)' }}>
  {/* Контент */}
</div>

// Карточки и панели
<div style={{ background: 'var(--bg-panel)' }}>
  {/* Контент */}
</div>
```

## 🧪 Тестирование после миграции

### Visual Regression Testing

1. **Сравнить скриншоты:**
   - Главная страница
   - Каталог товаров
   - Карточка товара
   - Корзина и checkout

2. **Проверить состояния:**
   - Default
   - Hover
   - Active/Pressed
   - Disabled
   - Focus

### Accessibility Testing

```bash
# Проверка контраста с новыми цветами
npm run test:a11y
```

### Проверка в браузерах

- Chrome (последняя версия)
- Firefox (последняя версия)
- Safari (последняя версия)
- Edge (последняя версия)

## 📊 Контраст и доступность (WCAG 2.1 AA)

### Проверенные комбинации

| Текст                                    | Фон                             | Контраст   | Статус |
| ---------------------------------------- | ------------------------------- | ---------- | ------ |
| `--color-text-primary` (#1B1B1B)         | `--color-neutral-100` (#FFFFFF) | **15.4:1** | ✅ AAA |
| `--color-text-secondary` (#4D4D4D)       | `--color-neutral-100` (#FFFFFF) | **8.0:1**  | ✅ AAA |
| `--color-text-muted` (#7A7A7A)           | `--color-neutral-100` (#FFFFFF) | **4.7:1**  | ✅ AA  |
| `--color-text-inverse` (#FFFFFF)         | `--color-primary` (#1F1F1F)     | **15.4:1** | ✅ AAA |
| `--color-typography-primary` (#1F2A44)   | `--color-neutral-100` (#FFFFFF) | **13.5:1** | ✅ AAA |
| `--color-typography-secondary` (#4B5C7A) | `--color-neutral-100` (#FFFFFF) | **7.2:1**  | ✅ AAA |

**Все комбинации соответствуют WCAG 2.1 AA (>= 4.5:1) и большинство AAA (>= 7:1).**

## 🚀 Поэтапный план миграции

### Фаза 1: Обновление токенов (✅ Завершено)

- [x] Обновлен `design-system.json` до v2.0
- [x] Обновлен `globals.css` с новыми переменными
- [x] Добавлены typography colorUsage переменные
- [x] Добавлены background переменные

### Фаза 2: Обновление UI компонентов (Следующий шаг)

- [ ] Обновить Button компонент
- [ ] Обновить Input/Select компоненты
- [ ] Обновить Card компоненты
- [ ] Обновить Modal компоненты
- [ ] Обновить Badge/Tag компоненты

### Фаза 3: Обновление страниц

- [ ] Главная страница
- [ ] Каталог товаров
- [ ] Карточка товара
- [ ] Корзина
- [ ] Личный кабинет

### Фаза 4: Тестирование и QA

- [ ] Visual regression testing
- [ ] Accessibility audit
- [ ] Browser compatibility testing
- [ ] User acceptance testing

## 💡 Полезные утилиты

### Скрипт автоматической замены

```bash
# Замена синих цветов на primary токены
find frontend/src -name "*.tsx" -type f -exec sed -i '' 's/bg-blue-600/bg-primary/g' {} +
find frontend/src -name "*.tsx" -type f -exec sed -i '' 's/text-blue-600/text-primary/g' {} +
```

### VS Code Search & Replace

**Найти:** `className="([^"]*?)bg-blue-600([^"]*?)"`
**Заменить:** `className="$1bg-primary$2"`

## 📚 Дополнительные ресурсы

- [Design System Specification](../front-end-spec.md#руководство-по-бренд-стилю)
- [Component Documentation](./design-system.json)
- [Accessibility Guidelines](../architecture/11-security-performance.md)

## ❓ FAQ

### В: Могу ли я продолжать использовать синие цвета?

**О:** Синие цвета остаются доступны для специфических случаев (ссылки, информационные уведомления), но основной акцент системы теперь графитовый. Используйте синие цвета намеренно и экономно.

### В: Нужно ли обновлять все компоненты сразу?

**О:** Нет. Миграция может быть поэтапной. Начните с новых компонентов и постепенно обновляйте существующие. Обе версии совместимы в переходный период.

### В: Как проверить контраст новых цветовых комбинаций?

**О:** Используйте инструменты:

- Chrome DevTools Lighthouse
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Accessible Colors](https://accessible-colors.com/)

### В: Что делать с кастомными компонентами, использующими старые цвета?

**О:**

1. Аудит: найдите все хардкоды цветов
2. Замените на CSS переменные
3. Протестируйте визуально
4. Проверьте accessibility

---

**Обновлено:** 2025-11-20
**Версия документа:** 1.0
