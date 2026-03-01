---
title: 'Уменьшение карточек в "Популярных категориях" для темы BLUE'
slug: 'decrease-category-cards-blue'
created: '2026-02-27T16:35:00+01:00'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4, 5, 6]
tech_stack: ['Next.js', 'React', 'Tailwind CSS']
files_to_modify: ['frontend/src/components/home/CategoriesSection.tsx']
code_patterns: ['Functional React Components', 'Tailwind Utility Classes', 'Responsive Design (mobile-first)']
test_patterns: ['Jest', 'React Testing Library']
---

# Tech-Spec: Уменьшение карточек в "Популярных категориях" для темы BLUE

## Review Notes
- Adversarial review completed
- Findings: 4 total, 3 fixed, 1 skipped
- Resolution approach: walk-through

**Created:** 2026-02-27T16:35:00+01:00

## Overview

### Problem Statement

На главной странице в теме BLUE карточки в блоке "Популярные категории" слишком большие. Их необходимо уменьшить и сделать такими же по размеру, как в блоке "Хиты продаж". Кроме того, кнопки прокрутки в блоке "Популярные категории" должны находиться вне зоны карусели (как в блоке "Хиты продаж"). В мобильной версии размеры карточек тоже должны соответствовать размерам из блока "Хиты продаж".

### Solution

Изменение стилей в `CategoriesSection.tsx` для приведения их в соответствие с `HitsSection.tsx`. Карточки категорий нужно будет подогнать под размеры `w-[calc(50%-4px)] md:w-[200px]`, а также перенести позиционирование кнопок-стрелок так, чтобы они выходили за границы прокручиваемой карусели, назначив общему контейнеру родительский `relative` класс, а не внутренней `.group`.

### Scope

**In Scope:**
- Корректировка ширины карточек `CARD_LAYOUT_CLASSES` в компоненте `CategoriesSection`.
- Изменение верстки контейнера карусели для кнопок-стрелок (вынос их за пределы скорлла, как в `HitsSection.tsx`).
- Соответствующая подгонка ширины и отступов для мобильной версии.

**Out of Scope:**
- Изменение логики получения данных API для категорий.
- Модификация компонента "Хиты продаж".

## Context for Development

### Codebase Patterns

В проекте для стилизации используется Tailwind CSS и мобильно-ориентированный подход к верстке. В компоненте `HitsSection` контейнер карточки использует классы `flex-shrink-0 w-[calc(50%-4px)] md:w-[200px] snap-start`. Это обеспечивает компактное отображение 2-х карточек на мобильных стройствах. В `CategoriesSection` родительский контейнер section должен иметь класс `relative`, а кнопки прокрутки — абсолютное позиционирование с центровкой по вертикали, вынесенное за пределы обертки `.group` для предотвращения наложения на саму карусель.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/components/home/CategoriesSection.tsx` | Основной компонент, подлежащий изменению |
| `frontend/src/components/home/HitsSection.tsx` | Эталон стилей для ширины карточек и позиционирования кнопок |

### Technical Decisions

- Константа `CARD_LAYOUT_CLASSES` будет обновлена на `w-[calc(50%-4px)] md:w-[200px]`
- Структура DOM вокруг кнопок навигации карусели будет перестроена: класс `relative` будет перенесен на уровень элемента `<section>`.

## Implementation Plan

### Tasks

- [x] Task 1: Обновление размеров карточек категорий
  - File: `frontend/src/components/home/CategoriesSection.tsx`
  - Action: Изменить константу `CARD_LAYOUT_CLASSES`. Заменить `flex-shrink-0 w-[80vw] sm:w-[40vw] md:w-[250px]` на `flex-shrink-0 w-[calc(50%-4px)] md:w-[200px]`.

- [x] Task 2: Изменение разметки скелетона (loading state)
  - File: `frontend/src/components/home/CategoriesSection.tsx`
  - Action: В компоненте `CategoriesSkeleton` убедиться, что классы соответствуют новой константе (уже используется `CARD_LAYOUT_CLASSES`) и обновить пропорции.

- [x] Task 3: Рефакторинг кнопок навигации (стрелок)
  - File: `frontend/src/components/home/CategoriesSection.tsx`
  - Action: 
    - Добавить класс `relative` корневому тегу `<section>`.
    - Переместить кнопки навигации (левую и правую стрелки) из `<div className="relative group">` в `<section>`, расположив их на одном уровне с основным заголовком или контейнером списка, для выноса за видимую часть.
    - Изменить классы позиционирования кнопок, чтобы они выступали за пределы списка: использовать `left-0` / `-left-2` и `right-0` / `-right-2` по аналогии с `HitsSection.tsx`. Убедиться, что они имеют `absolute top-1/2 -translate-y-1/2 z-10`.
    - Переместить или убрать класс `relative group` с обертки карусели, чтобы он не ограничивал позиционирование стрелок.

### Acceptance Criteria

- [ ] AC 1: Given пользователь заходит на главную страницу, When блок "Популярные категории" загружается, Then карточки категорий имеют ширину `200px` на десктопе и занимают `~50%` экрана на мобильном устройстве (2 карточки в ряд).
- [ ] AC 2: Given пользователь на десктопе, When отображаются стрелки навигации, Then они расположены за пределами прокручиваемого контейнера с карточками.
- [ ] AC 3: Given пользователь на мобильном устройстве, When он прокручивает "Популярные категории", Then стрелки навигации скрыты, и используется свайп.

## Additional Context

### Dependencies

- Зависимостей от внешних API нет, используются существующие эндпоинты (categoriesService).

### Testing Strategy

- Визуальное UI / E2E тестирование на разных разрешениях экрана (Mobile, Tablet, Desktop) для проверки ширины карточек и позиционирования стрелок.
- Проверка работоспособности кнопок прокрутки (click).

### Notes

- Размеры и позиционирование в мобильной версии должны в точности повторять блок "Хиты продаж", чтобы сохранить визуальное единообразие (consistent UI).
