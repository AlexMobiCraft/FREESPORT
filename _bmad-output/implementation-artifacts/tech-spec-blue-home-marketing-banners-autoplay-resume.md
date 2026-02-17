---
title: 'BLUE Home: возобновление autoplay маркетинговых баннеров после hover/focus'
slug: 'blue-home-marketing-banners-autoplay-resume'
created: '2026-02-17T17:24:28'
status: 'Implementation Complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Next.js'
  - 'React 19'
  - 'TypeScript'
  - 'Embla Carousel'
files_to_modify:
  - 'frontend/src/hooks/useBannerCarousel.ts'
  - 'frontend/src/components/home/MarketingBannersSection.tsx'
  - 'frontend/src/hooks/__tests__/useBannerCarousel.test.ts'
  - 'frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx'
code_patterns:
  - 'Custom Hook (useBannerCarousel) + Embla Autoplay plugin'
  - 'Container/Presenter pattern в MarketingBannersSection'
test_patterns:
  - 'Vitest + React Testing Library'
  - 'Mock-based тестирование Embla/Autoplay'
---

# Tech-Spec: BLUE Home: возобновление autoplay маркетинговых баннеров после hover/focus

**Created:** 2026-02-17T17:24:28

## Overview

### Problem Statement

В теме BLUE на главной странице в секции `MarketingBannersSection` автопрокрутка баннеров корректно останавливается при `hover/focus`, но после ухода курсора/потери фокуса не возобновляется. Это ломает ожидаемый UX карусели и снижает видимость промо-баннеров.

### Solution

Сделать минимальный root-cause фикс в текущем стеке (`useBannerCarousel` + `MarketingBannersSection`) без миграции на другой UI-блок. Обеспечить детерминированное поведение: пауза только во время `hover/focus`, автоматическое возобновление после ухода курсора/blur, с сохранением текущих AC Story 32.4.

### Scope

**In Scope:**
- Исправление логики autoplay pause/resume в `frontend/src/hooks/useBannerCarousel.ts`.
- Точечные правки интеграции в `frontend/src/components/home/MarketingBannersSection.tsx` (только при необходимости).
- Регрессионные тесты для hover/focus resume в:
  - `frontend/src/hooks/__tests__/useBannerCarousel.test.ts`
  - `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx`
- Проверка обратной совместимости с текущими AC Story 32.4.

**Out of Scope:**
- Изменения в `HeroSection` и `ElectricHeroSection`.
- Backend/API/контракты баннеров.
- Рефакторинг или замена кастомной карусели на другой framework-block.
- Визуальный редизайн секции.

## Context for Development

### Codebase Patterns

- BLUE homepage использует `HomePage` и рендерит `MarketingBannersSection` сразу после `QuickLinksSection`: `frontend/src/components/home/HomePage.tsx`.
- `MarketingBannersSection` использует `useBannerCarousel` и включает autoplay только когда `visibleBanners.length > 1`.
- В `useBannerCarousel` используется Embla + `embla-carousel-autoplay`, где по умолчанию активны `stopOnMouseEnter: true` и `stopOnInteraction: true`.
- Root cause для текущего бага: дефолт `stopOnInteraction: true` в generic hook конфликтует с UX-ожиданием этой секции (временная пауза на hover/focus с обязательным авто-возобновлением).
- Для Story 32.4 уже реализованы security и resilience механики (safe link guard, image failover, error boundary); их поведение нельзя ломать.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/app/(blue)/home/page.tsx` | Точка входа BLUE homepage |
| `frontend/src/components/home/HomePage.tsx` | Порядок секций, включая MarketingBannersSection |
| `frontend/src/components/home/MarketingBannersSection.tsx` | UI/интеграция карусели маркетинговых баннеров |
| `frontend/src/hooks/useBannerCarousel.ts` | Ядро логики Embla autoplay |
| `frontend/src/hooks/__tests__/useBannerCarousel.test.ts` | Unit/regression тесты хука autoplay |
| `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx` | Тесты поведения секции и интеграции с хуком |
| `_bmad-output/implementation-artifacts/Story/32-4-marketing-banners-ui.md` | Базовые AC и ограничения совместимости |

### Technical Decisions

- Сохраняем текущий стек Embla и существующий кастомный hook.
- Предпочитаем минимальный upstream fix root-cause вместо workaround в рендере.
- Дефолты generic `useBannerCarousel` не меняем, чтобы не создавать side-effects в других потребителях хука.
- Для `MarketingBannersSection` применяем локальную настройку autoplay interaction (`stopOnInteraction: false`) при сохранении pause на hover/focus.
- Фикс ограничивается BLUE-маркетинговой секцией.
- Все текущие AC Story 32.4 должны остаться неизменными по поведению (без регрессий).

## Implementation Plan

### Tasks

- [x] Task 1: Локализовать root-cause в `useBannerCarousel` - подтвердить что `stopOnInteraction: true` блокирует resume
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Проанализировать логику autoplayOptions и interaction handling в Embla Autoplay
  - Notes: Убедиться что проблема именно в `stopOnInteraction: true` по умолчанию

- [x] Task 2: Добавить поддержку опции `stopOnInteraction` в `MarketingBannersSection`
  - File: `frontend/src/components/home/MarketingBannersSection.tsx`
  - Action: Передать `stopOnInteraction: false` в вызов `useBannerCarousel`
  - Notes: Сохранить `stopOnMouseEnter: true` для паузы на hover

- [x] Task 3: Добавить unit-тесты для pause/resume lifecycle в `useBannerCarousel`
  - File: `frontend/src/hooks/__tests__/useBannerCarousel.test.ts`
  - Action: Написать тесты на `stopOnInteraction: false` поведение и resume после interaction
  - Notes: Использовать существующие mock-паттерны для Embla/Autoplay

- [x] Task 4: Добавить интеграционные тесты в `MarketingBannersSection`
  - File: `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx`
  - Action: Протестировать что секция передает правильные опции в hook
  - Notes: Проверить что `stopOnInteraction: false` применяется только для этой секции

- [x] Task 5: Прогнать регрессионные тесты для AC Story 32.4
  - File: `frontend/src/hooks/__tests__/useBannerCarousel.test.ts`, `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx`
  - Action: Запустить существующие тесты и убедиться в отсутствии регрессий
  - Notes: Особое внимание на security, error-handling, dots sync, single-banner optimization

### Acceptance Criteria

- [x] **AC1 (Hover Resume):**
  - Given в `MarketingBannersSection` более 1 баннера и autoplay активен,
  - When пользователь наводит курсор на баннер,
  - Then autoplay ставится на паузу,
  - And When курсор уходит (`mouseleave`), autoplay автоматически возобновляется.

- [x] **AC2 (Focus Resume):**
  - Given autoplay активен,
  - When баннер/контрол карусели получает фокус,
  - Then autoplay ставится на паузу,
  - And When фокус уходит (`blur`), autoplay автоматически возобновляется.

- [x] **AC3 (Backward Compatibility):**
  - Given текущая реализация Story 32.4,
  - When внедрен фикс,
  - Then поведение security, error-handling, dots sync и single-banner optimization остаются без изменений.

- [x] **AC4 (Scope Guard):**
  - Given область задачи,
  - When изменения завершены,
  - Then изменены только `MarketingBannersSection`/`useBannerCarousel` и их тесты (без изменений Hero/Electric).

## Additional Context

### Dependencies

- `embla-carousel-react` - основная библиотека карусели
- `embla-carousel-autoplay` - плагин автопрокрутки с опциями `stopOnInteraction` и `stopOnMouseEnter`
- `react` / `next` - React 19 в Next.js окружении
- `vitest` + `@testing-library/react` - фреймворк тестирования
- Существующие тесты Story 32.4 - для регрессионного покрытия

### Testing Strategy

**Unit-тесты (useBannerCarousel.test.ts):**
- Тест на `stopOnInteraction: false` опцию
- Тест на resume поведения после mouseleave/blur
- Тест на сохранение pause на hover/focus
- Тест на дефолтные значения опций

**Интеграционные тесты (MarketingBannersSection.test.tsx):**
- Тест на передачу `stopOnInteraction: false` в hook
- Тест на изоляцию изменений (другие секции не затронуты)
- Регрессионные тесты AC Story 32.4:
  - Security: safe link guard для небезопасных URL
  - Error-handling: image failover и error boundary
  - Dots sync: корректная синхронизация навигации
  - Single-banner optimization: отключение autoplay/loop для 1 баннера

**Manual тестирование:**
- Проверить hover/resume поведение в браузере
- Проверить focus/resume поведение через Tab-навигацию
- Убедиться что Hero/Electric секции не изменились

### Notes

**Root Cause Analysis:**
- Проблема: `stopOnInteraction: true` в generic `useBannerCarousel` блокирует autoplay resume после любого взаимодействия
- Решение: Локальный override `stopOnInteraction: false` только для `MarketingBannersSection`
- Сохраняем: `stopOnMouseEnter: true` для паузы на hover (требование пользователя)

**Constraints:**
- НЕ изменять дефолты generic `useBannerCarousel` (чтобы не затронуть Hero/Electric)
- НЕ изменять поведение AC Story 32.4 (security, error-handling, dots sync, single-banner)
- Минимальные изменения - только локальная опция в одной секции

**Future Considerations:**
- Если другие секции потребуют аналогичного поведения,可以考虑 вынести в конфигурацию темы
- Мониторинг производительности autoplay с новым interaction режимом

**User Confirmations:**
- ✅ Пауза на hover/focus должна сохраняться
- ✅ Обязательное автовозобновление после ухода
- ✅ Минимальный root-cause fix без миграции на framework-block
- ✅ Обратная совместимость с AC Story 32.4
