---
title: 'Quick Links on Homepage'
slug: 'quick-links-homepage'
created: '2026-02-12'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['React', 'Next.js', 'Tailwind CSS']
files_to_modify: ['frontend/src/components/home/HomePage.tsx', 'frontend/src/components/home/index.ts', 'frontend/src/services/categoriesService.ts', 'frontend/src/config/quickLinks.ts', 'frontend/src/components/home/QuickLinksSection.tsx']
code_patterns: ['Component Composition', 'Service Layer Pattern', 'Design System Tokens']
test_patterns: ['Unit Testing (Vitest)', 'React Testing Library']
---

# Tech-Spec: Quick Links on Homepage

**Created:** 2026-02-12

## Overview

### Problem Statement

Пользователям необходим быстрый доступ к ключевым разделам магазина (Новинки, Хиты продаж, Скидки) и основным категориям товаров непосредственно с главной страницы, чтобы улучшить навигацию и пользовательский опыт.

### Solution

Реализовать компонент `QuickLinksSection`, размещаемый под главным баннером (`HeroSection`). Компонент представляет собой горизонтально прокручиваемый список ссылок. Первые три элемента — фиксированные ссылки на спецразделы, стилизованные как основные кнопки. Остальные элементы — динамически подгружаемые корневые категории товаров.
**Desktop:** Добавить кнопки-стрелки для прокрутки списка.
**Mobile:** Использовать нативный скролл.

### Scope

**In Scope:**
- Создание React-компонента `QuickLinksSection` в `frontend/src/components/home`.
- Интеграция компонента в `HomePage` сразу после `HeroSection`.
- Получение списка корневых категорий через существующий `categoriesService`.
- Реализация горизонтальной прокрутки (scroll snap) для списка ссылок.
- Добавление кнопок навигации (стрелки) для десктопной версии.
- Вынос конфигурации статических ссылок в отдельный файл.
- Обработка ошибок API (показ только статических ссылок).
- Адаптивная верстка (Mobile First).

**Out of Scope:**
- Создание административного интерфейса для управления статическими ссылками.
- Изменение API категорий (используем существующий эндпойнт).

## Context for Development

### Codebase Patterns

- **Компоненты главной страницы:** Расположены в `frontend/src/components/home`. Экспортируются через `index.ts`.
- **Сервисы:** `frontend/src/services/*Service.ts`. `categoriesService` уже имеет метод `getCategories` но требует использования `parent_id__isnull=true`.
- **UI Kit:** Использовать существующие примитивы, но специфика дизайна требует кастомной верстки списка с прокруткой.
- **Design System:** Строгое использование CSS переменных (`var(--color-primary)`, `var(--bg-canvas)` и т.д.) вместо HEX кодов.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/components/home/HomePage.tsx` | Главная страница, точка входа. |
| `frontend/src/services/categoriesService.ts` | Сервис для получения данных категорий. |
| `frontend/src/components/home/index.ts` | Баррель файл для экспорта нового компонента. |
| `frontend/src/config/quickLinks.ts` | [NEW] Конфигурация статических ссылок. |
| `frontend/src/app/globals.css` | Источник CSS переменных. |
| `docs/frontend/css-variables-mapping.md` | Правила маппинга цветов. |

### Technical Decisions

- **Данные:**
    - Динамические: `categoriesService.getCategories({ parent_id__isnull: true, limit: 100 })`.
    - Статические: Вынести в `frontend/src/config/quickLinks.ts`.
        - Новинки: `{ label: "Новинки", icon: <Sparkles />, link: "/catalog?sort=new", variant: "new" }`
        - Хиты: `{ label: "Хиты продаж", icon: <Flame />, link: "/catalog?sort=popular", variant: "hit" }`
        - Скидки: `{ label: "Скидки", icon: <Percent />, link: "/catalog?is_discounted=true", variant: "sale" }`
- **Error Handling:** Если `categoriesService` возвращает ошибку, `QuickLinksSection` должен отловить её и отобразить только статические ссылки (без падения UI).
- **Скролл:**
    - Mobile: CSS `overflow-x-auto` + `snap-x`.
    - Desktop: Скрыть скроллбар, добавить кнопки `<` и `>` для прокрутки (scrollBy).
- **Стилизация:**
    - Контейнер: `bg-canvas` (var(--bg-canvas)).
    - Элементы: `bg-panel` (var(--bg-panel)), shadow-sm, rounded-full или rounded-lg.
    - Текст: `text-primary` (var(--color-text-primary)).
- **Icons:** Использовать `lucide-react` (стандарт проекта).

## Implementation Plan

### Tasks

#### 1. Конфигурация и Типы
- [ ] Задача 1.1: Создать конфигурацию статических ссылок
    - Файл: `frontend/src/config/quickLinks.tsx` (tsx нужен для иконок)
    - Действие: Экспортировать константу `STATIC_QUICK_LINKS` с массивом объектов (label, link, variant, icon).
    - Примечание: Иконки импортировать из `lucide-react`.

#### 2. Реализация Компонента
- [ ] Задача 2.1: Создать скелет компонента и логику
    - Файл: `frontend/src/components/home/QuickLinksSection.tsx`
    - Действие: Реализовать структуру компонента, `useEffect` для загрузки данных через `categoriesService`, состояния для категорий и обработки загрузки/ошибок.
    - Примечание: Корректно обработать состояние ошибки (показывать только статические ссылки).

- [ ] Задача 2.2: Реализовать верстку и скролл
    - Файл: `frontend/src/components/home/QuickLinksSection.tsx`
    - Действие: Добавить горизонтальный контейнер с прокруткой (`snap-x`). Рендерить статические ссылки, затем динамические категории.
    - Примечание: Использовать классы Tailwind (`flex`, `overflow-x-auto`, `gap-4`). Использовать `ref` для контейнера скролла.

- [ ] Задача 2.3: Реализовать контролы для десктопа
    - Файл: `frontend/src/components/home/QuickLinksSection.tsx`
    - Действие: Добавить кнопки-стрелки (Влево/Вправо). Логика `scrollBy` при клике. Скрывать/показывать в зависимости от позиции скролла (опционально) или типа устройства.
    - Примечание: Стилизовать как круглые кнопки с иконками и тенью (`shadow-md`).

#### 3. Интеграция
- [ ] Задача 3.1: Экспорт компонента
    - Файл: `frontend/src/components/home/index.ts`
    - Действие: Экспортировать `QuickLinksSection`.

- [ ] Задача 3.2: Добавить на Главную страницу
    - Файл: `frontend/src/components/home/HomePage.tsx`
    - Действие: Импортировать и разместить `QuickLinksSection` сразу после `HeroSection`.

#### 4. Тестирование
- [ ] Задача 4.1: Unit-тесты
    - Файл: `frontend/src/components/home/__tests__/QuickLinksSection.test.tsx`
    - Действие: Написать тесты для рендера статических ссылок, загрузки категорий, обработки ошибок и моки взаимодействия со скроллом.

### Acceptance Criteria

- [ ] AC 1: Компонент отображает статические ссылки (Новинки, Хиты, Скидки) с корректными иконками и цветами.
- [ ] AC 2: Компонент загружает и отображает корневые категории из API.
- [ ] AC 3: При ошибке API компонент не падает, а отображает только статические ссылки.
- [ ] AC 4: На мобильных устройствах список прокручивается горизонтально (тач-скролл).
- [ ] AC 5: На десктопе есть кнопки-стрелки для прокрутки списка влево/вправо.
- [ ] AC 6: Клик по статической ссылке ведет на корректный URL каталога с фильтрами.
- [ ] AC 7: Клик по категории ведет на страницу этой категории.
- [ ] AC 8: Компонент использует цвета Design System (CSS переменные) и соответствует визуальному стилю.

## Additional Context

### Dependencies

- `categoriesService`
- `lucide-react`
- `next/link`

### Testing Strategy

- **Unit Tests:** Verify rendering of mixed static/dynamic content and error state.
- **Manual:** verify Scroll Snap on mobile and Arrow clicks on desktop.
- **Design:** Check contrast and shadows against BG.

### Notes

- Ensure `QuickLinksSection` has `use client` directive.
- Check `z-index` of arrows to ensure they are above content.
