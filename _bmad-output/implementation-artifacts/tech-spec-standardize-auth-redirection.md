---
title: 'Стандартизация редиректа авторизации под активную тему'
slug: 'standardize-auth-redirection'
created: '2026-01-16'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4, 5, 6]
tech_stack: ['Next.js 15', 'React Hook Form', 'Zod', 'TypeScript']
files_to_modify: 
  - 'frontend/src/app/(blue)/(auth)/register/page.tsx'
  - 'frontend/src/app/(blue)/(auth)/b2b-register/page.tsx'
  - 'frontend/src/components/auth/B2BRegisterForm.tsx'
  - 'frontend/src/components/auth/RegisterForm.tsx'
  - 'frontend/src/middleware.ts'
  - 'frontend/src/utils/urlUtils.ts'
  - 'frontend/src/__tests__/middleware.test.ts'
code_patterns: ['useSearchParams', 'Client Components', 'router.push', 'Suspense Boundary']
test_patterns: ['Vitest', 'React Testing Library']
---

## Обзор

### Постановка проблемы
В настоящее время формы аутентификации (вход, регистрация, B2B-регистрация) содержат противоречивую логику редиректа. В частности, страницы `RegisterPage` и `B2BRegisterPage` не извлекают и не передают параметр запроса `next` в соответствующие формы. Это приводит к потере контекста навигации пользователя (например, при попытке вернуться в корзину в конкретной теме) — пользователь всегда попадает на корень `/` или на главную страницу темы по умолчанию. Кроме того, в B2B-регистрации захардкожен редирект на `/`.

### Решение
Внедрить единую стратегию перенаправления для всех компонентов аутентификации:
1.  **Уровень страниц:** Обновить страницы регистрации для извлечения параметров `next`/`redirect` из `searchParams` и передачи их в компоненты форм. Обернуть контент в `Suspense` для безопасной обработки параметров поиска на стороне клиента в Next.js 15.
2.  **Уровень компонентов:** Обновить `B2BRegisterForm`, чтобы она принимала проп `redirectUrl` и использовала его. Обновить `RegisterForm`, чтобы обеспечить безопасную обработку этого пропа.
3.  **Безопасность:** Валидировать все URL-адреса редиректа для предотвращения уязвимостей типа Open Redirect.
4.  **Роутинг:** Использовать `src/app/page.tsx` как "единый источник истины" для роутинга на основе тем, когда конкретный пункт назначения не указан (фоллбек на `/`).

### Объем работ (Scope)
**Входит в объем:**
- `frontend/src/app/(blue)/(auth)/register/page.tsx`
- `frontend/src/app/(blue)/(auth)/b2b-register/page.tsx`
- `frontend/src/components/auth/B2BRegisterForm.tsx`
- `frontend/src/components/auth/RegisterForm.tsx`
- `frontend/src/middleware.ts` (проверка целостности)

**Не входит в объем (перенесено в бэклог):**
- Изменения в логике бэкенда аутентификации.
- Рефакторинг структуры группы маршрутов `(blue)`.
- Миграция на Server Actions.

## План реализации

### Задача 1: Обновление страницы регистрации (передача контекста)
- **Файл:** `frontend/src/app/(blue)/(auth)/register/page.tsx`
- **Действие:** Извлечь `searchParams`, получить `redirectUrl`, обернуть в `<Suspense>` и передать в форму.

### Задача 2: Обновление страницы B2B-регистрации (передача контекста)
- **Файл:** `frontend/src/app/(blue)/(auth)/b2b-register/page.tsx`
- **Действие:** Аналогично Задаче 1 для B2B флоу.

### Задача 3: Обновление формы B2B-регистрации (обработка контекста)
- **Файл:** `frontend/src/components/auth/B2BRegisterForm.tsx`
- **Действие:** Добавить проп `redirectUrl`, использовать `router.push(redirectUrl || '/')`.

### Задача 4: Усиление безопасности формы регистрации
- **Файл:** `frontend/src/components/auth/RegisterForm.tsx`
- **Действие:** Добавить валидацию `redirectUrl` (должен начинаться с `/`).

### Задача 5: Проверка Middleware и циклов редиректа
- **Файл:** `frontend/src/middleware.ts`
- **Действие:** Убедиться, что `next` сохраняется, и нет цикличных редиректов на корне.

## Критерии приемки

- [x] **AC 1: Сохранение контекста на странице регистрации**
- [x] **AC 2: Сохранение контекста при B2B-регистрации**
- [x] **AC 3: Фоллбек по умолчанию на `/`**
- [x] **AC 4: Защита от Open Redirect (блокировка внешних доменов)**

## Стратегия тестирования
- Обновить unit-тесты для форм, мокнуть `router.push`.
- Ручная проверка в разных темах (`ACTIVE_THEME`).
- **Update:** Добавлены тесты для middleware (`frontend/src/__tests__/middleware.test.ts`).

## Review Notes
- Adversarial review completed.
- Findings: 4 total, 3 fixed, 1 skipped (F4 - Low severity magic numbers in CSS fallbacks).
- Resolution approach: Walk-through.
- Critical fix: Added middleware tests and unified URL validation via `isSafeRedirectUrl`.

## Примечания и риски
- Обязательно использование `Suspense` для `useSearchParams` в Next.js 15.
- Сохраняем клиентский роутинг для консистентности с текущим состоянием Auth Store.
