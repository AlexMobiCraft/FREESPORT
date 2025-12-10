# Epic 28: Authentication System Implementation

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-12-10 | 1.0 | Initial Epic Draft based on Frontend Plan | John (PM) |

---

## Change Management

> [!IMPORTANT]
> This Epic was originally planned as **Epic 14** in `docs/epics/frontend-epics-10-19-plan.md`. It has been renumbered to **Epic 28** to fit the current project roadmap sequence.

---

## Goals

- Реализовать безопасную и удобную систему аутентификации и авторизации.
- Обеспечить поддержку всех типов пользователей (B2C, B2B уровни 1-3, Тренеры, Федерации).
- Реализовать процессы регистрации, входа, восстановления пароля и верификации B2B.
- Обеспечить безопасность маршрутов через Middleware и JWT токены.

## Background Context

Платформа FREESPORT требует гибкой ролевой модели. Frontend должен поддерживать разграничение доступа и отображение контента в зависимости от роли пользователя. Фундамент для работы с состоянием (`authStore`) был заложен в Эпике 10, но UI и бизнес-логика аутентификации еще не реализованы.

### Documents & Artifacts

- **Plan:** `docs/epics/frontend-epics-10-19-plan.md` (Epic 14)
- **Design System:** `frontend/docs/design-system.json` (Input, Button, Modal, InfoPanel)
- **API Spec:** `docs/api-spec.yaml` (/auth/* endpoints)
- **UX Spec:** `docs/front-end-spec.md` (B2B Client Verification, Registration, Onboarding)

### Tech Stack

- **Frontend:** Next.js 14 App Router, TypeScript, Tailwind CSS
- **State Management:** Zustand (`authStore`)
- **API Client:** Axios (Interceptors for JWT)
- **Auth:** JWT (Access + Refresh tokens)
- **Validation:** React Hook Form + Zod

---

## Requirements

### Functional Requirements

- **FR1:** Пользователь (B2C) может зарегистрироваться (`/register`) и войти в систему (`/login`).
- **FR2:** Пользователь (B2B) может подать заявку на регистрацию с указанием ИНН/ОГРН (`/b2b-register`).
- **FR3:** Система поддерживает сброс и восстановление пароля (`/password-reset`).
- **FR4:** Frontend автоматически обрабатывает обновление JWT токенов (refresh token rotation).
- **FR5:** Защищенные маршруты (например, Личный Кабинет) недоступны для неавторизованных пользователей.
- **FR6:** Ролевая модель корректно обрабатывается: разные роли могут иметь разные перенаправления и доступный UI.

### Non-Functional Requirements

- **NFR1:** Безопасное хранение токенов (HttpOnly cookies для refresh, in-memory/closure для access - согласно текущей архитектуре).
- **NFR2:** Валидация всех полей форм на клиенте (email, password strength, INN format).
- **NFR3:** Мгновенная реакция UI на состояние загрузки и ошибки.

---

## Epic 28: Authentication Scope

### Story 28.1: Core Auth & B2C Registration

**As a** B2C customer,
**I want** to register and log in,
**so that** I can access my profile and order history.

**Scope:**

- Страница `/login` (Email + Password)
- Страница `/register` (Name, Email, Password, Confirm Password)
- Интеграция с `authService` (login, register endpoints)
- Обработка ошибок валидации и ответов сервера (400, 401, 409)
- Обновление `authStore` при успешном входе

**Acceptance Criteria:**

1. Форма входа работает, при успехе редирект на главную или сохраненный URL.
2. Форма регистрации создает пользователя B2C.
3. Валидация полей (email format, password min length).
4. Unit-тесты для форм.

---

### Story 28.2: B2B Registration Flow

**As a** Business Partner (B2B),
**I want** to register with my company details,
**so that** I can get wholesale pricing.

**Scope:**

- Страница `/b2b-register`
- Поля: Название компании, ИНН, ОГРН, Юридический адрес, Контактное лицо
- Валидация формата ИНН/ОГРН
- Индикация статуса "На рассмотрении" после регистрации

**Acceptance Criteria:**

1. Форма отправляет данные на специфичный B2B эндпоинт (или флаг в общей регистрации согласно API).
2. Валидация специфичных полей работает корректно.
3. UI отличается от B2C регистрации (акцент на бизнес-данные).

---

### Story 28.3: Password Reset Flow

**As a** user,
**I want** to reset my password if I forget it,
**so that** I can regain access to my account.

**Scope:**

- Страница `/password-reset` (запрос ссылки)
- Страница `/password-reset/confirm` (ввод нового пароля с токеном)
- Интеграция с API восстановления

**Acceptance Criteria:**

1. Пользователь может запросить сброс на email.
2. Пользователь может установить новый пароль, перейдя по ссылке.
3. Обработка устаревших или невалидных ссылок.

---

### Story 28.4: Protected Routes & Session Management

**As a** developer,
**I want** to protect routes and handle sessions globally,
**so that** unauthorized users cannot access restricted pages.

**Scope:**

- Next.js Middleware для проверки наличия токенов/сессии.
- Логика редиректов в `middleware.ts` на основе путей (public vs protected).
- Axios Interceptors для автоматического обновления токена (Refresh Token).
- Синхронизация состояния `authStore` между вкладками (опционально) или при инициализации приложения.

**Acceptance Criteria:**

1. Попытка входа на `/profile` без авторизации редиректит на `/login`.
2. Истекший Access token автоматически обновляется прозрачно для пользователя.
3. При ошибке Refresh token происходит полный логаут и редирект на вход.

---

## Next Steps

### PO/Architect Handover
>
> Используйте этот Эпик для создания детальных User Stories. Убедитесь, что API для B2B регистрации полностью готов и соответствует полям формы.

### Dependencies

- **Blocking:** Epic 10 (Set up `src/services/authService.ts` and `src/store/authStore.ts`).
- **Blocking:** Backend API Endpoints availability.
