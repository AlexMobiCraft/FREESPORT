# Catalog Page (Scenario 02) Specification

**Версия:** 1.0.0
**Дата:** 2026-01-06
**Статус:** Draft (Retroactive Spec)
**URL:** `/electric/catalog`
**Связанный код:** `frontend/src/app/electric/catalog/page.tsx`

---

## 1. Общее описание

Страница каталога товаров, позволяющая пользователям просматривать, фильтровать и добавлять товары в корзину. Дизайн соответствует стилистике Electric Orange (Digital Brutalism).

## 2. Структура макета (Layout)

### Сетка

Используется **Two-Column Layout**:

* **Sidebar (Left):** Фиксированная ширина **240px**.
* **Product Grid (Right):** Занимает оставшееся пространство (`flex-1 min-w-0`).
* **Контейнер:** Макс. ширина `1400px`, центрирован.

### Зоны страницы

#### 2.1 Header Zone

* **Breadcrumbs:** Компонент `ElectricBreadcrumbs`.
  * Формат: Главная → Каталог → [Путь к категории].
  * Все уровни (кроме последнего) кликабельны.
  * **Исключение:** Категория "СПОРТ" не отображается в пути.
* **Section Header:** `ElectricSectionHeader` (size="lg") — название текущей категории.
* **Meta:** Счетчик найденных товаров ("Найдено X товаров").
* **Сортировка:** `SortSelect` (справа, min-width: 200px).

#### 2.2 Sidebar Zone

Структура сайдбара разделена на два блока:

1. **Дерево Категорий:** Компонент `ElectricCategoryTree`.
    * Рекурсивное дерево с раскрытием/сворачиванием.
    * **Свернуто по умолчанию** — пользователь раскрывает вручную.
    * **Клик по названию** — выбирает категорию И раскрывает подкатегории.
    * Стилизация: скошенный заголовок (-12deg), оранжевые акценты.
2. **Фильтры:** Компонент `ElectricSidebar`.
    * Ширина: 280px.
    * **Бренды:** Чекбоксы (ElectricCheckbox style).
    * **Цена:** `PriceRangeSlider` (Dual thumb). Диапазон 1 - 50,000.

#### 2.3 Product Grid Zone

* **Сетка:**
  * Responsive: 2 колонки (mobile) -> 3 колонки (md) -> 4 колонки (lg).
  * **Gap:** 20px (`gap-5`).
* **Компонент карточки:** `ElectricProductCard`.
* **Состояния:**
  * **Загрузка:** Сетка из 8 скелетонов с `ElectricSpinner` внутри (аспект 1:1).
  * **Ошибка:** Блок с сообщением об ошибке (красный бордер).
  * **Пусто:** Сообщение "Товары не найдены".

#### 2.4 Pagination Zone

Компонент: `ElectricPagination`

* **Расположение:** Центрировано под сеткой товаров.
* **Отступ сверху:** 64px (`mt-16`).
* **Логика:** Отображает по 12 товаров на странице (`PAGE_SIZE = 12`).

---

## 3. Компоненты и Данные

### 3.1 ElectricProductCard

| Prop      | Источник данных/Значение               | Примечание                            |
| --------- | -------------------------------------- | ------------------------------------- |
| `image`   | `product.main_image`                   | Fallback: placeholder                 |
| `title`   | `product.name`                         | Truncate lines: 2                     |
| `brand`   | `product.brand.name`                   | Uppercase                             |
| `price`   | `product.retail_price`                 | Формат: 1 500 ₽                       |
| `badge`   | `is_sale`, `is_hit`, `is_new`          | Приоритет: Sale > Hit > New           |
| `inStock` | `product.is_in_stock`                  | Влияет на opacity и кнопку            |
| `actions` | Primary: "В КОРЗИНУ", Outline: "ЗАПОМНИТЬ" | Padding кнопки `sm` = `px-2.5`    |

### 3.2 Интерактивность

* **Навигация по категориям:** Клик по категории в дереве → обновление Breadcrumbs и списка товаров.
* **Breadcrumbs:** Клик по любому уровню → переход на эту категорию.
* **Сортировка:** Выбор из `SortSelect` → сброс страницы на 1.
* **Быстрые фильтры:** Табы "Все товары" / "Новинки" / "Акция" для фильтрации по `is_new` / `is_sale`.
* **Фильтрация:** При изменении чекбоксов или цены обновление происходит на клиенте.
* **Пагинация:** Полная перезагрузка списка (client-side fetch).
* **Добавление в корзину:** Вызов `addItem(variantId, 1)`. Toast уведомление (Success/Error).

---

## 4. Сортировка и Фильтрация

### 4.1 Сортировка (`SortSelect`)

Компонент использует `ElectricSelect` с опциями, соответствующими API:

| Опция              | API Value            |
|--------------------|----------------------|
| Цена: по возрастанию | `min_retail_price`   |
| Цена: по убыванию    | `-min_retail_price`  |
| По названию (А-Я)    | `name`               |
| По названию (Я-А)    | `-name`              |

**Примечание:** "Новинки" и "Акция" — это **фильтры API** (`is_new`, `is_sale`), а не сортировка!

### 4.2 Быстрые Фильтры (Quick Filter Tabs)

Расположены между заголовком секции и основным контентом:

| Таб          | API Параметр  | Описание                    |
|--------------|---------------|-----------------------------|
| Все товары   | —             | Без дополнительной фильтрации |
| Новинки      | `is_new=true` | Товары с флагом "новинка"   |
| Акция        | `is_sale=true`| Товары на распродаже        |

**Стилизация:** Скошенные кнопки (`skewX(-12deg)`) в стиле Electric Orange.

---

## 5. Используемые токены (Design Compliance)

### Цвета

* Background: `var(--bg-body)`
* Text Main: `var(--color-text-primary)`
* Text Secondary: `var(--color-text-secondary)`
* Primary Accent: `var(--color-primary)`

### Типографика

* Body: `Inter` (из переменной `--font-body`)
* Headers/Numbers: `Roboto Condensed` (из `font-display`)

---

## 6. Компоненты страницы

1. **ElectricBreadcrumbs:** Навигационная цепочка с полным путем категории (без "СПОРТ").
2. **SortSelect:** Сортировка товаров (использует `ElectricSelect`).
3. **Quick Filter Tabs:** Кнопки "Все товары" / "Новинки" / "Акция".
4. **ElectricCategoryTree:** Рекурсивный компонент дерева категорий.
5. **ElectricSidebar:** Фильтры по брендам и цене.
6. **ElectricProductCard:** Карточка товара.
7. **ElectricPagination:** Пагинация.
8. **ElectricDrawer:** Мобильная шторка для фильтров (только `< lg`).

---

## 7. Mobile Adaptation

### 7.1 Breakpoints

| Breakpoint | Ширина | Поведение |
|------------|--------|-----------|
| Mobile | `< 768px` | 2 колонки товаров, drawer для фильтров |
| Tablet | `768px - 1023px` | 3 колонки товаров, drawer для фильтров |
| Desktop | `≥ 1024px` | 4 колонки товаров, sidebar виден |

### 7.2 Mobile Layout

**Sidebar скрыт** на экранах `< lg` (1024px):

```css
aside { @apply hidden lg:block; }
```

**Кнопка «Фильтры»** появляется вместо sidebar:
* Видима только на `lg:hidden`
* Иконка `SlidersHorizontal` + текст "Фильтры"
* Бейдж с количеством активных фильтров

**ElectricDrawer** — slide-in панель слева:
* Содержит: ElectricCategoryTree + ElectricSidebar
* Footer с кнопкой "Сбросить фильтры" (если есть активные)
* Ширина: `max-w-[320px]`

### 7.3 Responsive Typography

| Элемент | Desktop | Mobile |
|---------|---------|--------|
| Section Header (lg) | `text-4xl` | `text-3xl` |
| Счётчик товаров | `text-base` | `text-sm` |
| Кнопка «Фильтры» | `text-sm`, `px-4 py-2` | `text-xs`, `px-3 py-1.5` |
| Quick Filter Tabs | `text-sm`, `px-4 py-2` | `text-xs`, `px-3 py-1.5` |
| ElectricButton (sm) | `h-9 px-2.5 text-sm` | `h-8 px-2 text-xs` |
| ElectricButton (md) | `h-11 px-6 text-base` | `h-10 px-4 text-sm` |

### 7.4 Quick Filter Tabs (Mobile)

* **Горизонтальный скролл:** `overflow-x-auto scrollbar-hide`
* **Без переноса:** `whitespace-nowrap`
* **Padding внизу** для touch-области: `pb-2`

### 7.5 Компоненты Mobile

| Компонент | Файл |
|-----------|------|
| ElectricDrawer | `components/ui/Drawer/ElectricDrawer.tsx` |
| ElectricButton (responsive) | `components/ui/Button/ElectricButton.tsx` |
