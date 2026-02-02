---
title: 'Исправление ошибки 401 при обновлении токена после регистрации'
slug: 'fix-registration-tokens-401'
created: '2026-01-16T09:55:41+01:00'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Django', 'DRF', 'SimpleJWT', 'Next.js', 'Zustand']
files_to_modify: ['backend/apps/users/views/authentication.py', 'frontend/src/services/authService.ts', 'frontend/src/services/api-client.ts', 'frontend/src/stores/authStore.ts']
code_patterns: ['JWT Authentication', 'Interceptors', 'Service Pattern', 'Defensive Programming']
test_patterns: ['Integration Tests', 'Vitest']
---

# Tech-Spec: Исправление ошибки 401 при обновлении токена после регистрации

**Created:** 2026-01-16T09:55:41+01:00

## Overview

### Problem Statement

При регистрации нового пользователя бэкенд (`UserRegistrationView`) не возвращает JWT-токены (`access` и `refresh`). Фронтенд (`AuthService.register`) ожидает их наличие и пытается сохранить, что приводит к записи строки `"undefined"` в `localStorage` и `cookies`. При последующих запросах (например, загрузке профиля в `ProfileForm`) срабатывает логика обновления токена, которая отправляет `"undefined"` на эндпоинт `/auth/refresh/`, вызывая ошибку 401 Unauthorized.

### Solution

1.  **Backend:** Обновить `UserRegistrationView`, чтобы он генерировал и возвращал JWT-токены сразу после успешного создания пользователя, аналогично `UserLoginView`.
2.  **Frontend Auth Service:** Добавить строгую проверку на наличие токенов (`access` и `refresh`) в `AuthService` перед их сохранением.
3.  **Frontend API Client:** Добавить защиту в `api-client.ts` для предотвращения отправки запросов с токеном равным строке `"undefined"`.

### Scope

**In Scope:**
- Модификация `UserRegistrationView` в `backend/apps/users/views/authentication.py`.
- Обновление `AuthService` в `frontend/src/services/authService.ts`.
- Усиление `api-client.ts` в `frontend/src/services/api-client.ts`.
- (Опционально) обновление документации API через drf-spectacular.

**Out of Scope:**
- Изменение логики входа (Login).
- Изменение времени жизни JWT-токенов.

## Context for Development

### Codebase Patterns

- **JWT Auth:** `simplejwt` используется для генерации и валидации токенов.
- **Frontend Service:** `AuthService` инкапсулирует логику общения с API аутентификации.
- **Interceptor:** `apiClient` перехватывает 401 ошибки и пытается обновить токен.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/apps/users/views/authentication.py` | Вьюхи аутентификации. Цель изменений: `UserRegistrationView.post`. |
| `frontend/src/services/authService.ts` | Сервис аутентификации. Цель изменений: методы `register` и `registerB2B`. |
| `frontend/src/services/api-client.ts` | Axios клиент. Цель изменений: response interceptor. |

### Technical Decisions

- **Token Generation:** Использовать `RefreshToken.for_user(user)` только для активных пользователей.
- **Defensive Check:** В `api-client.ts` добавить проверку `if (!refreshToken || refreshToken === 'undefined')` перед попыткой рефреша.

## Implementation Plan

### Tasks

1.  **Backend: Update Registration View**
    -   [x] В `UserRegistrationView.post` после успешного сохранения пользователя (`serializer.save()`):
        -   Проверить `user.is_active` и `user.verification_status`.
        -   Если `is_active=True` (B2C retail), сгенерировать токены: `refresh = RefreshToken.for_user(user)`.
        -   Добавить `access` и `refresh` в ответ `201 Created`.
    -   [x] Обновить `extend_schema` декоратор для `UserRegistrationView`, добавив токены в пример ответа (201).

2.  **Frontend: Harden Auth Service**
    -   [x] В `frontend/src/services/authService.ts`:
        -   В методе `register`: добавить проверку `if (access && refresh)` перед вызовом `setTokens`.
        -   В методе `registerB2B`: аналогично добавить проверку. Учесть, что для B2B токенов может и не быть (ожидаемое поведение).

3.  **Frontend: Secure API Client**
    -   [x] В `api-client.ts` (response interceptor):
        -   Найти место получения `refreshToken`.
        -   Добавить условие: если токен равен строке `"undefined"`, считать его отсутствующим и делать logout.

### Acceptance Criteria

1.  **B2C Registration:**
    -   Регистрация -> ответ 201 с токенами -> токены сохранены -> профиль загружается без 401.
2.  **B2B Registration (Pending):**
    -   Регистрация -> ответ 201 без токенов -> сторадж чист (нет `"undefined"`) -> редирект/сообщение пользователю.
3.  **Undefined Token Protection:**
    -   Если вручную записать `"undefined"` в localStorage и вызвать API -> происходит logout, нет запроса на `/auth/refresh/` с невалидным токеном.

## Additional Context

### Testing Strategy

- **Manual Verification:**
    -   Регистрация розничного пользователя.
    -   Регистрация оптового пользователя.
    -   Проверка DevTools (Network, Application).

---

## Hotfix 2026-01-16: Глобальные 401 на публичных эндпоинтах

### Симптомы

После первоначальной имплементации спеки обнаружена регрессия:
- **ВСЕ публичные эндпоинты** (`/banners/`, `/products/`, `/blog/`, `/news/`) возвращали 401 Unauthorized.
- Ошибка возникала даже для неаутентифицированных пользователей.
- Backend views имели `permission_classes = [AllowAny]`, но 401 всё равно возвращался.

### Root Cause Analysis

1. **Request Interceptor не проверял токен на `"undefined"`:**
   ```typescript
   // БЫЛО (api-client.ts, строка 97-99):
   const token = useAuthStore.getState().accessToken;
   if (token && config.headers) {
     config.headers.Authorization = `Bearer ${token}`;
   }
   ```
   Если `token = "undefined"` (строка, не `undefined`), условие `if (token)` = `true`, и отправлялся невалидный header `Authorization: Bearer undefined`.

2. **SimpleJWT возвращает 401 при невалидном токене ДО проверки permissions:**
   Даже если View имеет `AllowAny`, SimpleJWT сначала пытается валидировать токен из `Authorization` header. Если токен невалиден — возвращается 401.

3. **`getRefreshToken()` возвращал строку `"undefined"`:**
   ```typescript
   // БЫЛО (authStore.ts):
   getRefreshToken: () => {
     return localStorage.getItem('refreshToken'); // Может вернуть "undefined"
   }
   ```

### Исправления

#### 1. Request Interceptor (`api-client.ts`)

```diff
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
-   if (token && config.headers) {
+   // Fix: проверяем на строку "undefined", которая могла попасть из localStorage
+   if (token && token !== 'undefined' && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);
```

#### 2. getRefreshToken (`authStore.ts`)

```diff
getRefreshToken: () => {
- return localStorage.getItem('refreshToken');
+ const token = localStorage.getItem('refreshToken');
+ // Fix: фильтруем невалидные значения, которые могли попасть ранее
+ if (!token || token === 'undefined' || token === 'null' || token.trim() === '') {
+   return null;
+ }
+ return token;
},
```

### Verification

- ✅ Публичные эндпоинты загружаются без 401.
- ✅ Баннеры, продукты, новости, блог отображаются корректно.
- ✅ localStorage очищен от невалидных значений.

### Lessons Learned

> [!IMPORTANT]
> При работе с токенами всегда проверяйте на строковые `"undefined"` и `"null"` — они могут попасть из localStorage, если ранее сохранялись невалидные значения.

> [!TIP]
> SimpleJWT валидирует токен ДО проверки permission_classes. Невалидный `Authorization` header = 401, даже для `AllowAny` endpoints.

