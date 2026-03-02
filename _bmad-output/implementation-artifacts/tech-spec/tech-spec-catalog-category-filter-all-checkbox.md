---
title: "Доработка фильтра Категории на странице каталога — чекбокс Все и responsive поведение"
slug: "catalog-category-filter-all-checkbox"
created: "2026-03-01"
status: "implementation-complete"
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  [
    Next.js App Router,
    React 18,
    TypeScript,
    Tailwind CSS,
    Vitest,
    React Testing Library,
  ]
files_to_modify:
  - frontend/src/app/(blue)/catalog/page.tsx
  - frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx
code_patterns:
  - "Нативный <details> для сворачиваемых секций фильтров → заменить на управляемый div"
  - "Checkbox компонент из @/components/ui/Checkbox — props: label, checked, onChange (React.ChangeEvent)"
  - "activeCategoryId (number|null) + activeCategoryLabel (string) для стейта категории"
  - "CategoryTree инлайн-компонент внутри page.tsx"
  - "Tailwind lg: breakpoint (1024px) для 2-column layout"
test_patterns:
  - "Vitest + React Testing Library"
  - "Моки: categoriesService.getTree(), productsService.getAll(), brandsService.getAll()"
---

# Tech-Spec: Доработка фильтра Категории на странице каталога — чекбокс «Все» и responsive поведение

**Created:** 2026-03-01

## Overview

### Problem Statement

При переходе на `/catalog` автоматически выбирается категория «Спорт» (через `DEFAULT_CATEGORY_LABEL`), из-за чего пользователь видит только товары одной категории вместо всего каталога. Отсутствует возможность быстро сбросить фильтр категории обратно на «все товары». Также фильтры «Категории» и «Бренд» не адаптируются к размеру экрана — всегда свёрнуты.

### Solution

1. Убрать автовыбор категории «Спорт» при первоначальном переходе — по умолчанию `activeCategoryId = null`, показываются все товары.
2. Добавить чекбокс «Все» рядом с заголовком «Категории» с интерактивной логикой переключения.
3. Изменить цвет заголовка h1 с `text-primary` на `text-neutral-900` (`#1F2A44`) — стандартный цвет заголовков по Design System.
4. Сделать фильтры «Категории» и «Бренд» responsive: раскрыты на десктопе (`lg+`), свёрнуты на мобилке (`< lg`).

### Scope

**In Scope:**

- Убрать автовыбор категории «Спорт» при первом визите без URL-параметра `category`
- Чекбокс «Все» = `activeCategoryId === null` → API без `category_id`
- Логика чекбокса «Все»:
  - Клик при снятой галочке → ставит галочку, снимает выбор категории, фильтр не сворачивается
  - Клик при стоящей галочке → разворачивает фильтр если свёрнут, но галочка снимается только при выборе конкретной категории
- Заголовок h1: при «Все» → «Каталог», цвет → `text-neutral-900`
- Хлебные крошки: при «Все» → `Главная / Каталог`
- Кнопка «Сбросить» → ставит «Все» вместо fallback на «Спорт»
- Responsive фильтры: «Категории» и «Бренд» раскрыты на десктопе (`lg+`), свёрнуты на мобилке (`< lg`)

**Out of Scope:**

- Бэкенд API (работает и без `category_id`)
- Другие фильтры (цена, наличие)
- Редизайн UI фильтров
- Мобильная нижняя панель фильтров

## Context for Development

### Codebase Patterns

1. **Фильтр Категории (строки 890–913)**: Нативный `<details>` элемент, без `open` атрибута (всегда свёрнут). Содержит `<CategoryTree>` инлайн-компонент.
2. **Фильтр Бренд (строки 928–948)**: Аналогичный `<details>` без `open`. Содержит список `<Checkbox>` для каждого бренда.
3. **Стейт категории**: `activeCategoryId: number | null` (init: `null`) + `activeCategoryLabel: string` (init: `DEFAULT_CATEGORY_LABEL = 'Спорт'`). **⚠️ init для label нужно изменить на `''`.**
4. **Auto-select логика (строки 437–448)**: В `useEffect` при загрузке дерева категорий — если нет URL-параметра `category` и нет badge-фильтра, автоматически выбирается "Спорт" или первая категория.
5. **Запрос товаров (строка 612)**: `if (activeCategoryId !== null || hasBadgeFilter)` — товары НЕ грузятся если `activeCategoryId === null` и нет badge-фильтра.
6. **Сброс фильтров (строки 671–690)**: `handleResetFilters()` ставит fallback на "Спорт".
7. **Заголовок h1 (строка 848)**: Использует `text-primary` (= `var(--color-primary)`), отображает `activeCategoryLabel || 'Каталог'`.
8. **Хлебные крошки (строки 396–418)**: Строятся из `activePathNodes` — если пустые, показывают `Главная / Каталог`.
9. **Checkbox компонент**: из `@/components/ui/Checkbox` — уже импортирован в `page.tsx`. Props: `label`, `checked`, `onChange`. **⚠️ `onChange` передаёт `React.ChangeEvent<HTMLInputElement>`, а не `() => void` — обработчики нужно оборачивать в лямбду.**
10. **Responsive**: Страница использует `lg:` breakpoint (1024px) для grid layout.

### Files to Reference

| File                                                             | Purpose                                                                               |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `frontend/src/app/(blue)/catalog/page.tsx`                       | Основной файл — вся логика, CategoryTree, рендер сайдбара                             |
| `frontend/src/components/ui/Checkbox/Checkbox.tsx`               | Checkbox компонент Design System — `onChange` = `React.ChangeEvent<HTMLInputElement>` |
| `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` | Существующие тесты — нужно обновить (конкретные тест-кейсы ниже)                      |
| `docs/frontend/css-variables-mapping.md`                         | Маппинг CSS переменных — `text-neutral-900` для заголовков                            |

### Technical Decisions

1. **Замена `<details>` на управляемые `div`-блоки**: Нативный `<details>` не поддерживает программное управление через React-стейт. Для responsive и программного open/close нужны управляемые компоненты с `useState`.
2. **Responsive — только initial state, без listener** (Fix F1/F7): Инициализируем `isCategoriesOpen`/`isBrandsOpen` как `true` (для SSR-совместимости). В `useEffect` при маунте проверяем `matchMedia`, но **НЕ ставим listener на resize** — чтобы не сбрасывать пользовательский выбор при ресайзе окна. Это предотвращает SSR hydration mismatch и плохой UX при ресайзе.
3. **Чекбокс «Все» — computed state**: Состояние `checked` вычисляется как `activeCategoryId === null`. Не создаём отдельный стейт.
4. **Цвет заголовка**: `text-primary` → `text-neutral-900` (Design System: `var(--color-neutral-900)` = `#1F2A44`).
5. **Анимация open/close фильтров** (Fix F6): Использовать `transition-all` + `max-height` + `opacity` вместо conditional render для плавного UX, аналогично `FilterGroup` компоненту.
6. **Guard для первой загрузки товаров** (Fix F3): Добавить `isCategoriesLoaded` flag, чтобы не делать двойной запрос — первый при маунте (без категории), второй после загрузки категорий.

## Implementation Plan

### Tasks

- [x] **Task 1: Изменить initial state — `activeCategoryLabel` и добавить стейт фильтров**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Изменить init value `activeCategoryLabel`:

    ```tsx
    // БЫЛО:
    const [activeCategoryLabel, setActiveCategoryLabel] = useState(
      DEFAULT_CATEGORY_LABEL,
    );

    // СТАЛО:
    const [activeCategoryLabel, setActiveCategoryLabel] = useState("");
    ```

  - Action: Добавить два useState для open/closed секций фильтров:
    ```tsx
    // Инициализируем как true для SSR-совместимости.
    // На клиенте useEffect скорректирует для мобилки.
    const [isCategoriesOpen, setIsCategoriesOpen] = useState(true);
    const [isBrandsOpen, setIsBrandsOpen] = useState(true);
    ```
  - Action: Добавить `useEffect` для responsive — **только initial check, без listener**:
    ```tsx
    // Responsive: на мобилке сворачиваем фильтры при маунте
    useEffect(() => {
      const isDesktop = window.matchMedia("(min-width: 1024px)").matches;
      if (!isDesktop) {
        setIsCategoriesOpen(false);
        setIsBrandsOpen(false);
      }
    }, []);
    ```
  - Notes: Init `true` → SSR рендерит «раскрыто» → на мобилке `useEffect` мгновенно сворачивает при маунте (до первого paint благодаря synchronous useEffect). Listener на `change` НЕ ставим — пользователь может вручную свернуть/развернуть, и ресайз окна не будет сбрасывать его выбор.

- [x] **Task 2: Убрать автовыбор категории «Спорт» при первом визите**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: В `useEffect` загрузки категорий (строки 437–448) **удалить** блок auto-select:
    ```tsx
    // УДАЛИТЬ этот блок целиком:
    if (!initialCategory && !hasBadgeFilter) {
      initialCategory =
        findCategoryByLabel(mapped, DEFAULT_CATEGORY_LABEL) ??
        mapped[0] ??
        null;
    }
    ```
  - Action: Оставить блок `if (categorySlug) { ... }` — выбор из URL параметра должен работать.
  - Notes: После этого `activeCategoryId` останется `null` при переходе `/catalog` без параметров.

- [x] **Task 3: Добавить guard для первой загрузки товаров**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Добавить флаг `isCategoriesLoaded` чтобы избежать двойного запроса:
    ```tsx
    const [isCategoriesLoaded, setIsCategoriesLoaded] = useState(false);
    ```
  - Action: В `useEffect` загрузки категорий, в `finally` добавить:
    ```tsx
    setIsCategoriesLoaded(true);
    ```
  - Action: Изменить `useEffect` запроса товаров (строка 612):

    ```tsx
    // БЫЛО:
    if (activeCategoryId !== null || hasBadgeFilter) {
      fetchProducts();
    }

    // СТАЛО:
    // Ждём пока категории загрузятся (чтобы URL-параметр category успел установить activeCategoryId),
    // затем загружаем товары. При badge-фильтре грузим сразу.
    if (isCategoriesLoaded || hasBadgeFilter) {
      fetchProducts();
    }
    ```

  - Action: Добавить `isCategoriesLoaded` в массив зависимостей useEffect:
    ```tsx
    }, [fetchProducts, isCategoriesLoaded, hasBadgeFilter]);
    ```
  - Notes: Это предотвращает двойной запрос: без guard запрос стрельнёт при маунте (без категории), а потом повторно после загрузки категорий из URL. С guard'ом — ждём загрузки категорий, потом один запрос.

- [x] **Task 4: Обновить `handleResetFilters` — сбрасывать категорию в «Все» + очистить expandedKeys**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: В `handleResetFilters()` (строки 671–690) заменить fallback на "Спорт":

    ```tsx
    // БЫЛО:
    if (categoryTree.length) {
      const fallbackCategory =
        findCategoryByLabel(categoryTree, DEFAULT_CATEGORY_LABEL) ??
        categoryTree[0] ??
        null;
      if (fallbackCategory) {
        setActiveCategoryId(fallbackCategory.id);
        setActiveCategoryLabel(fallbackCategory.label);
      }
    }

    // СТАЛО:
    setActiveCategoryId(null);
    setActiveCategoryLabel("");
    setExpandedKeys(new Set()); // Очищаем развёрнутые подкатегории
    ```

  - Notes: `expandedKeys` очищается чтобы при следующем выборе категории не оставались «призрачные» развёрнутые узлы дерева.

- [x] **Task 5: Добавить обработчик `handleSelectAllCategories`**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Добавить новый обработчик после `handleSelectCategory`:
    ```tsx
    const handleSelectAllCategories = () => {
      if (activeCategoryId === null) {
        // Галочка «Все» уже стоит — при клике разворачиваем фильтр если свёрнут
        setIsCategoriesOpen(true);
      } else {
        // Галочка «Все» не стоит — ставим галочку, снимаем категорию
        setActiveCategoryId(null);
        setActiveCategoryLabel("");
        setExpandedKeys(new Set()); // Очищаем развёрнутые подкатегории
        setPage(1);
        // Фильтр НЕ сворачиваем
      }
    };
    ```
  - Notes: Логика из ТЗ: клик при стоящей галочке → разворачивает; клик при снятой → ставит галочку, снимает категорию, не сворачивает. `handleSelectCategory` менять не нужно — он уже корректно устанавливает `activeCategoryId` и `activeCategoryLabel`, что автоматически снимает чекбокс «Все».

- [x] **Task 6: Заменить `<details>` категорий на управляемый div с чекбоксом «Все» и анимацией**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Заменить блок `<details>` категорий (строки 889–914) на:

    ```tsx
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
      {/* Заголовок «Категории» + чекбокс «Все» */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsCategoriesOpen((prev) => !prev)}
          className="flex items-center gap-2 cursor-pointer text-base font-semibold text-gray-900"
          aria-expanded={isCategoriesOpen}
          aria-controls="filter-categories"
        >
          <ChevronDown
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform duration-[180ms]",
              isCategoriesOpen && "rotate-180",
            )}
          />
          <span>Категории</span>
        </button>
        <Checkbox
          label="Все"
          checked={activeCategoryId === null}
          onChange={() => handleSelectAllCategories()}
        />
      </div>

      {/* Содержимое — CategoryTree с анимацией */}
      <div
        id="filter-categories"
        className={cn(
          "overflow-hidden transition-all duration-[180ms]",
          isCategoriesOpen
            ? "max-h-[2000px] opacity-100 mt-4"
            : "max-h-0 opacity-0 mt-0",
        )}
      >
        {isCategoriesLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <div
                key={index}
                className="h-4 bg-gray-100 rounded animate-pulse"
              />
            ))}
          </div>
        ) : categoriesError ? (
          <p className="text-sm text-red-600">{categoriesError}</p>
        ) : (
          <CategoryTree
            nodes={categoryTree}
            activeId={activeCategoryId}
            expandedKeys={expandedKeys}
            onToggle={handleToggle}
            onSelect={handleSelectCategory}
          />
        )}
      </div>
    </div>
    ```

  - Notes:
    - **Fix F2**: `onChange={() => handleSelectAllCategories()}` — лямбда-обёртка, т.к. `Checkbox.onChange` ожидает `React.ChangeEvent<HTMLInputElement>`, а наш обработчик — `() => void`.
    - **Fix F6**: Анимация через `transition-all` + `max-h` + `opacity` вместо conditional render `{isOpen && ...}`. Паттерн скопирован из `FilterGroup` компонента. `max-h-[2000px]` — достаточно для дерева категорий.

- [x] **Task 7: Заменить `<details>` бренда на управляемый div с анимацией**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Заменить блок `<details>` бренда (строки 927–949) на:
    ```tsx
    <div className="space-y-2 text-sm text-gray-600">
      <button
        type="button"
        onClick={() => setIsBrandsOpen((prev) => !prev)}
        className="cursor-pointer font-medium text-gray-900 flex items-center gap-2 w-full"
        aria-expanded={isBrandsOpen}
        aria-controls="filter-brands"
      >
        <ChevronDown
          className={cn(
            "w-4 h-4 text-gray-500 transition-transform duration-[180ms]",
            isBrandsOpen && "rotate-180",
          )}
        />
        <span>Бренд</span>
      </button>
      <div
        id="filter-brands"
        className={cn(
          "overflow-hidden transition-all duration-[180ms]",
          isBrandsOpen ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <div className="mt-2 flex flex-col gap-1">
          {isBrandsLoading && (
            <p className="text-xs text-gray-400">Загрузка...</p>
          )}
          {brandsError && <p className="text-xs text-red-500">{brandsError}</p>}
          {!isBrandsLoading && !brandsError && brands.length === 0 && (
            <p className="text-xs text-gray-400">Бренды не найдены</p>
          )}
          {!isBrandsLoading &&
            !brandsError &&
            brands.map((brand) => (
              <div key={brand.id}>
                <Checkbox
                  label={brand.name}
                  checked={selectedBrandIds.has(brand.id)}
                  onChange={() => handleBrandToggle(brand.id)}
                />
              </div>
            ))}
        </div>
      </div>
    </div>
    ```
  - Notes: Анимация аналогична Task 6 — `transition-all` + `max-h` + `opacity`.

- [x] **Task 8: Изменить цвет заголовка h1 и текст**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: В h1 (строка 848) заменить `text-primary` на `text-neutral-900`:

    ```tsx
    // БЫЛО:
    className =
      "lg:row-start-2 lg:col-span-2 self-start text-2xl md:text-4xl font-semibold text-primary break-words md:break-normal min-h-[2rem] md:min-h-[2.5rem]";

    // СТАЛО:
    className =
      "lg:row-start-2 lg:col-span-2 self-start text-2xl md:text-4xl font-semibold text-neutral-900 break-words md:break-normal min-h-[2rem] md:min-h-[2.5rem]";
    ```

  - Action: Обновить отображаемый текст:

    ```tsx
    // БЫЛО:
    activeCategoryLabel || "Каталог";

    // СТАЛО:
    activeCategoryId !== null ? activeCategoryLabel : "Каталог";
    ```

  - Notes: `text-neutral-900` = `var(--color-neutral-900)` = `#1F2A44` — стандартный цвет заголовков по css-variables-mapping.md.

- [x] **Task 9: Добавить импорт `ChevronDown` и `cn`**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Добавить `ChevronDown` в существующий lucide-react import:

    ```tsx
    // БЫЛО:
    import { Grid2x2, List } from "lucide-react";

    // СТАЛО:
    import { Grid2x2, List, ChevronDown } from "lucide-react";
    ```

  - Action: Проверить наличие `cn` import и добавить если отсутствует:
    ```tsx
    import { cn } from "@/utils/cn";
    ```

- [x] **Task 10: Cleanup — удалить неиспользуемый `DEFAULT_CATEGORY_LABEL` и связанный код**
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Удалить константу:
    ```tsx
    // УДАЛИТЬ:
    const DEFAULT_CATEGORY_LABEL = "Спорт";
    ```
  - Action: Проверить, остались ли ссылки на `DEFAULT_CATEGORY_LABEL` после Tasks 1–4. Если `findCategoryByLabel` тоже больше не используется — удалить и её.
  - Action: Проверить `useEffect` на строке 517–527 — он обновляет `activeCategoryLabel` из `activePathNodes` с fallback на `DEFAULT_CATEGORY_LABEL`. Заменить fallback:

    ```tsx
    // БЫЛО:
    setActiveCategoryLabel(
      pathNodes[pathNodes.length - 1]?.label ?? DEFAULT_CATEGORY_LABEL,
    );

    // СТАЛО:
    setActiveCategoryLabel(pathNodes[pathNodes.length - 1]?.label ?? "");
    ```

  - Notes: Чистим deadcode чтобы не вводить в заблуждение будущих разработчиков.

- [x] **Task 11: Обновить существующие тесты**
  - File: `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx`
  - Action: **Тест 1** (строка ~358) — заменить ожидание h1 "Спорт" на "Каталог":

    ```tsx
    // БЫЛО:
    expect(
      screen.getByRole("heading", { level: 1, name: "Спорт" }),
    ).toBeInTheDocument();

    // СТАЛО:
    expect(
      screen.getByRole("heading", { level: 1, name: "Каталог" }),
    ).toBeInTheDocument();
    ```

  - Action: **Тест 2** (строка ~177–206, "AC 2, AC 4") — убрать ожидание `category_id` при initial load. Initial load теперь идёт без `category_id`:

    ```tsx
    // БЫЛО:
    expect(productsService.default.getAll).toHaveBeenCalledWith(
      expect.objectContaining({
        search: "nike",
        category_id: expect.any(Number),
      }),
    );

    // СТАЛО:
    expect(productsService.default.getAll).toHaveBeenCalledWith(
      expect.objectContaining({
        search: "nike",
      }),
    );
    // И убедиться, что category_id НЕ передаётся при default load
    ```

  - Action: **Все тесты** — пройтись по всем `expect` вызовам `productsService.default.getAll` и убрать ожидание `category_id: expect.any(Number)` если оно было привязано к auto-select "Спорт".
  - Action: **Mock matchMedia** — добавить mock для `window.matchMedia` в `beforeEach`:
    ```tsx
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: query === "(min-width: 1024px)", // Симулируем desktop
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    ```

### Acceptance Criteria

- [x] **AC 1:** Given пользователь переходит на `/catalog` без параметров, when страница загружается, then ни одна категория не выбрана, чекбокс «Все» имеет галочку, заголовок h1 показывает «Каталог», и отображаются товары всех категорий.

- [x] **AC 2:** Given чекбокс «Все» имеет галочку (ни одна категория не выбрана), when пользователь кликает на конкретную категорию в дереве, then галочка «Все» снимается, заголовок h1 обновляется на имя категории, товары фильтруются по выбранной категории.

- [x] **AC 3:** Given выбрана конкретная категория (чекбокс «Все» без галочки), when пользователь кликает на чекбокс «Все», then галочка «Все» устанавливается, подсветка категории снимается, заголовок h1 показывает «Каталог», фильтр «Категории» НЕ сворачивается, отображаются все товары.

- [x] **AC 4:** Given чекбокс «Все» имеет галочку и фильтр «Категории» свёрнут, when пользователь кликает на чекбокс «Все», then фильтр «Категории» разворачивается, галочка остаётся.

- [x] **AC 5:** Given пользователь перешёл на `/catalog?category=sport`, when страница загружается, then выбрана категория «Спорт», чекбокс «Все» без галочки, заголовок h1 показывает «Спорт».

- [x] **AC 6:** Given любые фильтры применены (категория, бренд, цена), when пользователь нажимает «Сбросить», then чекбокс «Все» ставится (категория сбрасывается), заголовок h1 показывает «Каталог», все фильтры сбрасываются, expandedKeys очищаются.

- [x] **AC 7:** Given страница открыта на десктопе (ширина ≥ 1024px), when страница загружается, then фильтры «Категории» и «Бренд» раскрыты по умолчанию.

- [x] **AC 8:** Given страница открыта на мобильном устройстве (ширина < 1024px), when страница загружается, then фильтры «Категории» и «Бренд» свёрнуты по умолчанию.

- [x] **AC 9:** Given ни одна категория не выбрана (чекбокс «Все» активен), when проверяются хлебные крошки, then они показывают `Главная / Каталог` без подкатегории.

- [x] **AC 10:** Given страница каталога загружена, when проверяется заголовок h1, then его цвет — `text-neutral-900` (`#1F2A44`), а не `text-primary` (`#0060FF`).

- [x] **AC 11:** Given пользователь вручную свернул фильтр «Категории» на десктопе, when он ресайзит окно (пересекая 1024px и обратно), then состояние фильтра НЕ сбрасывается — остаётся свёрнутым (пользовательский выбор сохраняется).

- [x] **AC 12:** Given фильтры «Категории» и «Бренд» открыты/закрыты, when пользователь кликает на chevron или заголовок секции, then секция плавно анимируется (180ms transition).

## Additional Context

### Dependencies

- Нет внешних зависимостей — все компоненты уже в проекте
- `Checkbox` компонент из `@/components/ui/Checkbox` уже импортирован в `page.tsx`
- `ChevronDown` из `lucide-react` — добавить в существующий import (`Grid2x2`, `List` уже оттуда)
- `cn` из `@/utils/cn` — проверить наличие импорта, добавить если нет
- API `productsService.getAll()` без `category_id` корректно возвращает все товары

### Testing Strategy

**Обновление существующих тестов:**

- Тест h1 "Спорт" → "Каталог" (строка ~358)
- Тесты с `category_id: expect.any(Number)` → убрать для initial load без категории
- Добавить mock `window.matchMedia` в `beforeEach`

**Ручное тестирование:**

1. Перейти на `/catalog` — проверить: «Все» с галочкой, h1 = «Каталог» (цвет `#1F2A44`), товары всех категорий
2. Кликнуть категорию — проверить: галочка «Все» снялась, h1 обновился, товары отфильтрованы
3. Кликнуть «Все» — проверить: галочка вернулась, подсветка категории снята, фильтр открыт
4. На мобилке (< 1024px) — проверить: фильтры свёрнуты
5. На десктопе (≥ 1024px) — проверить: фильтры раскрыты
6. Перейти на `/catalog?category=sport` — проверить: категория «Спорт» выбрана
7. Нажать «Сбросить» — проверить: всё сброшено, «Все» с галочкой
8. Анимация: свернуть/развернуть фильтр — плавная 180ms анимация
9. Ресайз окна через 1024px — пользовательский выбор НЕ сбрасывается

### Notes

- `DEFAULT_CATEGORY_LABEL` удаляется полностью (Task 10) — больше не используется после изменений
- Если `findCategoryByLabel` тоже стала deadcode — удалить
- В будущем можно вынести `useMediaQuery` хук в `@/hooks/` если паттерн понадобится повторно
- Нативный `<details>` заменяется на div с transition — улучшает как UX (плавная анимация), так и тестируемость (стейт управляемый)

### Adversarial Review Fixes Applied

| Fix | Finding                             | Решение                                                                   |
| --- | ----------------------------------- | ------------------------------------------------------------------------- |
| F1  | SSR hydration mismatch              | Init `true`, useEffect корректирует для mobile. Без listener.             |
| F2  | Checkbox onChange type mismatch     | `onChange={() => handleSelectAllCategories()}` — лямбда-обёртка           |
| F3  | Двойной запрос товаров              | `isCategoriesLoaded` flag — ждём загрузку категорий перед первым запросом |
| F4  | Task 5 «ничего не делать»           | Удалён как отдельная задача, перенесён в Notes                            |
| F5  | activeCategoryLabel init = 'Спорт'  | Изменён на `useState('')`                                                 |
| F6  | Нет анимации open/close             | `transition-all` + `max-h` + `opacity` (паттерн FilterGroup)              |
| F7  | matchMedia handler сбрасывает выбор | Убран listener, только initial check                                      |
| F8  | expandedKeys не очищаются           | `setExpandedKeys(new Set())` в handleReset и handleSelectAll              |
| F9  | Task 11 слишком поверхностный       | Детализированы конкретные тесты + mock matchMedia                         |
| F10 | DEFAULT_CATEGORY_LABEL deadcode     | Task 10 — cleanup                                                         |
