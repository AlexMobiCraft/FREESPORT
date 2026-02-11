---
title: 'Исправление редиректа авторизации на активную тему'
slug: 'fix-auth-redirection'
created: '2026-01-16'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Next.js 15', 'React Hook Form', 'Zod', 'Vitest']
files_to_modify: 
  - 'frontend/src/components/auth/RegisterForm.tsx'
  - 'frontend/src/components/auth/B2BRegisterForm.tsx'
  - 'frontend/src/components/auth/__tests__/RegisterForm.test.tsx'
  - 'frontend/src/components/auth/__tests__/LoginForm.test.tsx'
  - 'frontend/src/__tests__/components/B2BRegisterForm.test.tsx'
  - 'docs/front-end-spec.md'
code_patterns: ['router.push usage', 'Client Components']
test_patterns: ['React Testing Library', 'Vitest']
---

# Техническая спецификация: Исправление редиректа авторизации

## Обзор

### Постановка проблемы
После авторизации (вход или регистрация) пользователей перенаправляет на хардкодный путь `/home`, что игнорирует активную тему приложения (например, `/electric`). Кроме того, `RegisterForm` игнорирует параметры `next`/`redirectUrl`.

### Решение
Стандартизировать логику редиректа во всех формах авторизации:
1. Использовать `redirectUrl` (или `next` query param), если он есть.
2. Если нет, перенаправлять на корень `/`, полагаясь на маппинг тем в `middleware.ts` или `app/page.tsx`.
3. Актуализировать проектную документацию, чтобы отразить это изменение поведения.

### Объем работ (Scope)
**Входит в объем:**
- Модификация `RegisterForm.tsx` и `B2BRegisterForm.tsx`.
- Обновление тестов для всех форм.
- Верификация `middleware.ts`.
- **Проверка и обновление документации по Auth Flow.**

## Контекст разработки

### Технические решения
- **Приоритет редиректа**: `redirectUrl` > `/` (root).

## План реализации

### Разбивка задач

- [ ] Задача 1: Аудит и обновление документации
  - Файл: `docs/front-end-spec.md` (и другие релевантные MD файлы в `docs/`)
  - Действие: Найти упоминания о редиректе на `/home` после регистрации/входа и заменить на "редирект на `/` (активная тема)".
  - Примечание: Проверить также `docs/4-ux-design/00-design-system-migration/00-migration-plan.md` если применимо.

- [ ] Задача 2: Анализ Middleware
  - Файл: `frontend/src/middleware.ts` (или `src/app/page.tsx`)
  - Действие: Проверить логику редиректа для корневого пути `/`.
  - Критерий: Убедиться, что авторизованный пользователь на `/` корректно перенаправляется на `THEME_HOME`.

- [ ] Задача 3: Обновление RegisterForm
  - Файл: `frontend/src/components/auth/RegisterForm.tsx`
  - Действие: 
    - Добавить поддержку пропса `redirectUrl` (по аналогии с `LoginForm`).
    - Изменить редирект по умолчанию: `router.push(redirectUrl || '/')`.

- [ ] Задача 4: Обновление B2BRegisterForm
  - Файл: `frontend/src/components/auth/B2BRegisterForm.tsx`
  - Действие: Заменить `router.push('/home')` на `router.push('/')`.

- [ ] Задача 5: Обновление тестов
  - Файлы: 
    - `frontend/src/components/auth/__tests__/RegisterForm.test.tsx`
    - `frontend/src/__tests__/components/B2BRegisterForm.test.tsx`
  - Действие: Актуализировать тесты под новую логику редиректа.

### Критерии приемки
- [ ] AC 1: `RegisterForm` перенаправляет на `/`, если нет `redirectUrl`.
- [ ] AC 2: `B2BRegisterForm` перенаправляет на `/`.
- [ ] AC 3: Пользователь попадает на главную страницу активной темы.
- [ ] AC 4: Документация описывает актуальное поведение системы.
