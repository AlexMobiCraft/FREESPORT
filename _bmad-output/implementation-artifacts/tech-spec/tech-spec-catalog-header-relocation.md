---
title: 'Перенос заголовка категории под строку поиска на странице каталога'
slug: 'catalog-header-relocation'
created: '2026-02-28T08:31:00+01:00'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Next.js', 'React', 'Tailwind CSS', 'Zustand']
files_to_modify: 
  - 'frontend/src/app/(blue)/catalog/page.tsx'
  - 'frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx'
code_patterns: ['CSS Variables Mapping', 'Tailwind CSS Grid', 'A11y Semantic HTML', 'Responsive Typography']
test_patterns: ['DOM Structure Testing', 'A11y Role Testing', 'Async State Testing']
---

# Tech-Spec: Перенос заголовка категории под строку поиска на странице каталога

**Created:** 2026-02-28T08:31:00+01:00

## Overview

### Problem Statement

Сейчас на странице каталога заголовок активной категории (`<h1>`) располагается слева, в одном ряду со строкой поиска. Дизайн требует, чтобы визуально заголовок отображался под строкой поиска, но при этом начинался от левого края (над панелью категорий). При этом необходимо сохранить правильный семантический порядок для скринридеров (H1 должен читаться до формы поиска) и не сломать вертикальный ритм страницы во время загрузки (CLS).

### Solution

Использовать `CSS Grid` с явным указанием строк (`row-start`), чтобы отвязать визуальное представление от физического порядка в DOM. 
Мы создадим единый grid-контейнер для строки поиска и заголовка `<h1>`:
- В DOM первым элементом будет идти `<h1>` (выполняя требования A11y), но через классы `lg:row-start-2 lg:col-span-2` он визуально опустится на вторую строку и займет всю ширину.
- Вторым элементом в DOM пойдет блок поиска, который через классы `lg:row-start-1 lg:col-start-2` визуально поднимется на первую строку в правую колонку.

Для предсказуемости авторазмещения мы задаем `lg:grid-rows-[auto_auto]`. Цвет заголовка будет задан через семантическую переменную `text-primary`. Мы внедряем защиту от Cumulative Layout Shift (CLS), синхронизируя минимальную высоту текста и скелетона адаптивно. В целях максимальной A11y блок поиска получит тег `<search>` с явным атрибутом `role="search"`.

### Scope

**In Scope:**
- Изменение структуры DOM в `frontend/src/app/(blue)/catalog/page.tsx`.
- Внедрение Grid-контейнера для H1 и Поиска с использованием `row-start` и `col-start`.
- Использование семантически корректной адаптивной высоты `Skeleton` (`h-[2rem] md:h-[2.5rem]`) для предотвращения CLS.
- Применение семантической CSS-переменной `text-primary` (`var(--color-primary)`).
- Адаптивная типографика для H1 (`text-2xl md:text-4xl break-words md:break-normal`).
- Обертывание формы поиска в элемент `<search role="search">` для A11y.
- Обновление Unit-тестов: проверка DOM, ролей и симуляция задержки ответа (моки API) для тестирования состояния Skeleton.

**Out of Scope:**
- Изменение функционала компонента `SearchAutocomplete`, кроме обеспечения его 100% ширины внутри обертки.
- Модификация хлебных крошек (Breadcrumbs).
- Рефакторинг глобального стора (Zustand) получения данных категории.

## Context for Development

### Codebase Patterns

Структура после рефакторинга:
```tsx
        {/* Хлебные крошки (вне этого блока, выше) */}

        {/* Единый грид для Поиска и Заголовка */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-[280px_1fr] lg:grid-rows-[auto_auto] gap-x-8 gap-y-4 lg:gap-y-6 items-start">
          
          {/* 1. H1 - первый в DOM, визуально на второй строке.
                 min-h адаптивен (2rem mobile, 2.5rem desktop), совпадая с размером шрифта. */}
          <h1 className="lg:row-start-2 lg:col-span-2 self-start text-2xl md:text-4xl font-semibold text-primary break-words md:break-normal min-h-[2rem] md:min-h-[2.5rem]">
            {isCategoryLoading 
              ? <Skeleton className="h-[2rem] md:h-[2.5rem] w-64" /> 
              : (activeCategoryLabel || 'Каталог')}
          </h1>

          {/* 2. Поиск - второй в DOM, визуально на первой строке в правой колонке. */}
          <search 
            role="search"
            aria-label="Блок поиска по каталогу"
            className="lg:row-start-1 lg:col-start-2 flex flex-col sm:flex-row items-start sm:items-center gap-4 relative z-20 w-full"
          >
            {/* SearchAutocomplete должен растягиваться на w-full если нужно */}
            <SearchAutocomplete  />
            {/* Индикатор результатов */}
          </search>

        </div>

        {/* Основной контент (Категории + Сетка товаров) идёт ниже */}
```

- **Адаптивный CLS Защитник**: Высота текста на мобильных устройствах (`text-2xl`) равна `2rem`, а на десктопах (`text-4xl`) — `2.5rem`. Классы `min-h-[2rem] md:min-h-[2.5rem]` на обертке H1 и спинере `<Skeleton>` обеспечивают пиксель-перфектную загрузку без вертикальных рывков интерфейса.
- **A11y**: Комбинация HTML5 тега `<search>` и атрибута `role="search"` гарантирует совместимость как со старыми, так и с новыми скринридерами.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/app/(blue)/catalog/page.tsx` | Основной компонент |
| `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx` | Тесты компонента каталога |
| `docs/frontend/css-variables-mapping.md` | CSS Guides |

## Implementation Plan

### Tasks

- [x] Task 1: Внедрение Grid Rows Layout и тегов
  - File: `frontend/src/app/(blue)/catalog/page.tsx`
  - Action: Заменить родительский `div` заголовка и поиска на новый: `<div className="mt-6 grid grid-cols-1 lg:grid-cols-[280px_1fr] lg:grid-rows-[auto_auto] gap-x-8 gap-y-4 lg:gap-y-6 items-start">`.
  - Action: Разместить внутри первым элементом `<h1>`, установив классы: `lg:row-start-2 lg:col-span-2 self-start text-2xl md:text-4xl font-semibold text-primary break-words md:break-normal min-h-[2rem] md:min-h-[2.5rem]`. Убедиться, что `isCategoryLoading` соответствует реальному флагу загрузки компонента.
  - Action: Разместить форму поиска под `<h1>` в DOM, использовав: `<search role="search" aria-label="Блок поиска по каталогу" className="lg:row-start-1 lg:col-start-2 flex flex-col sm:flex-row items-start sm:items-center gap-4 relative z-20 w-full">`.

- [x] Task 2: Расширенное обновление Unit-тестов
  - File: `frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx`
  - Action: Добавить тест проверки состояния загрузки `Skeleton`, **замокав API с задержкой (delay)**, чтобы не пропустить рендер загрузчика.
  - Action: Обновить тесты для проверки A11y-семантики: наличие `<search role="search">` и порядка DOM (сначала H1, затем поиск).
  - Action: Проверить успешное прохождение тестов: `npm run test:frontend -- CatalogPage.test.tsx`. При расхождении снапшотов обновить их, выполнив с флагом `-u`.

### Acceptance Criteria

- [x] AC 1: Given десктопное разрешение, When загружается страница, Then блок `<search>` занимает правую колонку, а `<h1>` располагается под ним (слева на всю ширину).
- [x] AC 2: Given мобильное устройство, When страница загружена, Then `<h1>` перед поиском, а очень длинные слова (`break-words`) переносятся без появления горизонтального скролла. Отступы сверху и снизу текста идеально вписываются в `2rem` высоту без пустых полос.
- [x] AC 3: Given инструменты доступности или Screen Reader, When анализируется секция, Then она объявлена как `search` landmark, а `<h1>` читается до нее.
- [x] AC 4: Given асинхронная загрузка, When данные грузятся, Then отображается `<Skeleton className="h-[2rem] md:h-[2.5rem] ...">`, высота которого идеально совпадает с итоговым текстом, предотвращая Cumulative Layout Shift (CLS).
- [x] AC 5: Given CSS-свойства `<h1>`, When проверяются вычисленные цвета, Then применяется CSS-переменная `--color-primary` через класс `text-primary`.

### Testing Strategy
- Выравнивание и баг авторазмещения Grid (Safari iOS 14+) проверяются вручную (**Manual Visual QA**).
- DOM семантика (роль `search`, порядок H1, класс `text-primary`) и состояния `Skeleton` проверяются автоматически через Jest/RTL с асинхронными моками.

## Additional Context
- Стилизуется внешний лейаут; внутренняя структура компонентов `<SearchAutocomplete>` не изменяется, но необходимо убедиться, что внутренний `input` тянется на 100% ширины, если это предполагалось дизайном.

## Review Notes
- Adversarial review completed
- Findings: 4 total, 3 fixed, 1 skipped
- Resolution approach: [F] Fix automatically

