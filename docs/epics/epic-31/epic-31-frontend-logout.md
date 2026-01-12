# Epic 31: Frontend Logout UI Integration

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-12-13 | 1.0 | Initial Epic Draft for Frontend Logout | John (PM) |

---

## Goals

- Добавить UI кнопку "Выйти" в Header компонент для авторизованных пользователей
- Интегрировать frontend с backend `/auth/logout/` endpoint (Epic 30)
- Обеспечить полную очистку токенов на клиенте и сервере при logout
- Реализовать редирект на главную страницу после успешного выхода

## Background Context

Epic 28 реализовал систему аутентификации с регистрацией и входом. Epic 30 добавил серверный `/auth/logout/` endpoint для инвалидации refresh токенов. Однако в UI отсутствует кнопка "Выйти", и frontend не вызывает backend endpoint при logout.

### Documents & Artifacts

- **Previous Epics:**
  - `docs/epics/epic-28/epic-28-authentication.md` (Epic 28 - Authentication)
  - `docs/epics/epic-30-backend-logout.md` (Epic 30 - Backend Logout)
- **Design System:** `docs/frontend/design-system.json` (Button component)
- **API Spec:** `docs/api-spec.yaml` (/auth/logout/ endpoint)
- **Testing Standards:**
  - `docs/frontend/testing-standards.md`
  - `docs/frontend/testing-typescript-recommendations.md`

### Tech Stack

- **Frontend:** Next.js 15.4.6 + React 19.1.0 + TypeScript 5.0+
- **State Management:** Zustand 4.5.7 (`authStore`)
- **HTTP Client:** Axios 1.11.0
- **UI Components:** Custom Button component + Tailwind CSS 4.0
- **Testing:** Vitest 2.1.5 + React Testing Library 16.3.0 + MSW 2.12.2

---

## Requirements

### Functional Requirements

- **FR1:** Авторизованный пользователь видит кнопку "Выйти" в Header (desktop + mobile)
- **FR2:** При клике на "Выйти" вызывается backend `/auth/logout/` endpoint с refresh токеном
- **FR3:** После успешного logout происходит очистка tokens, cookies, localStorage
- **FR4:** Пользователь перенаправляется на главную страницу `/`
- **FR5:** Header обновляется и показывает "Войти"/"Регистрация" вместо "Профиль"/"Выйти"

### Non-Functional Requirements

- **NFR1:** Fail-safe подход: локальная очистка происходит даже при ошибке backend API
- **NFR2:** UI обновляется мгновенно (optimistic update для UX)
- **NFR3:** Обработка edge cases: network error, backend timeout, invalid token
- **NFR4:** Coverage тестами >= 90%

---

## Epic 31: Frontend Logout Scope

### Story 31.1: Добавление кнопки "Выйти" в Header компонент

**As a** зарегистрированный пользователь,
**I want** to see a logout button in the header,
**so that** I can exit my account.

**Scope:**

- Добавить кнопку "Выйти" в desktop версию Header (после кнопки "Профиль")
- Добавить кнопку "Выйти" в mobile версию Header
- Использовать компонент `Button` с `variant="secondary"` и `size="small"`
- Создать обработчик `handleLogout` (пока без API вызова)
- Визуально отделить кнопку "Выйти" от "Профиль"

**Acceptance Criteria:**

1. Кнопка "Выйти" видна только для авторизованных пользователей (`isAuthenticated === true`)
2. Кнопка НЕ видна для неавторизованных пользователей
3. Desktop версия: кнопка расположена после кнопки "Профиль" в правой части Header
4. Mobile версия: кнопка расположена в мобильном меню после кнопки "Профиль"
5. Использован компонент `Button` с правильными props
6. При клике вызывается обработчик `handleLogout`

---

### Story 31.2: Интеграция authService с backend logout endpoint

**As a** frontend developer,
**I want** to call backend logout API,
**so that** refresh tokens are invalidated on server.

**Scope:**

- Добавить метод `logout(refreshToken: string)` в `authService.ts`
- Метод делает `POST /auth/logout/` с refresh токеном в request body
- Обработать успешный ответ `204 No Content`
- Обработать ошибки: `400 Bad Request`, `401 Unauthorized`, network errors
- Обновить `authStore.logout()` для вызова `authService.logout()` перед очисткой состояния

**Acceptance Criteria:**

1. `authService.logout()` отправляет POST запрос на `/auth/logout/`
2. Request body содержит `{ "refresh": "token_value" }`
3. При успехе (204) возвращается resolved Promise
4. При ошибке (400/401) возвращается rejected Promise с error message
5. `authStore.logout()` вызывает `authService.logout()` с refresh токеном из localStorage
6. Fail-safe: локальная очистка происходит даже при ошибке API
7. Код имеет полную TypeScript типизацию

---

### Story 31.3: Обработчик logout с редиректом

**As a** зарегистрированный пользователь,
**I want** to be redirected to home page after logout,
**so that** I clearly see that I exited my account.

**Scope:**

- Обновить обработчик `handleLogout` в Header компоненте
- Добавить вызов `authStore.logout()` (который вызывает backend API)
- Добавить `useRouter()` для редиректа на главную страницу `/`
- Показывать loading состояние во время logout (опционально)
- Обработать ошибки и показать toast/notification при failure (опционально)

**Acceptance Criteria:**

1. При клике на "Выйти" вызывается `handleLogout`
2. `handleLogout` вызывает `authStore.logout()`
3. После успешного logout вызывается `router.push('/')`
4. Пользователь перенаправляется на главную страницу
5. Header обновляется и показывает "Войти"/"Регистрация"
6. Состояние `isAuthenticated` меняется на `false`
7. Tokens, cookies, localStorage полностью очищены

---

### Story 31.4: Тесты для logout функциональности

**As a** frontend developer,
**I want** to write comprehensive tests for logout,
**so that** functionality is reliable and bug-free.

**Scope:**

- Unit-тесты для `Header.tsx`:
  - Кнопка "Выйти" отображается для авторизованных пользователей
  - Кнопка НЕ отображается для неавторизованных
  - При клике вызывается `handleLogout`
- Integration-тесты для `authStore.logout()`:
  - Вызывается `authService.logout()` с refresh токеном
  - При успехе API очищается state, localStorage, cookies
  - При ошибке API локальная очистка все равно происходит
- MSW mock для `/auth/logout/` endpoint:
  - Успешный ответ 204
  - Ошибка 400 (invalid token)
  - Network error

**Acceptance Criteria:**

1. Unit-тесты покрывают desktop и mobile версии кнопки "Выйти"
2. Тесты проверяют вызов `authStore.logout()` при клике
3. Integration-тесты проверяют вызов backend API через MSW
4. Тесты проверяют очистку tokens, cookies, localStorage
5. Тесты проверяют редирект на главную страницу
6. Coverage для новых функций >= 90%
7. Все тесты проходят в Vitest

---

## Compatibility Requirements

- [x] Существующие auth функции не изменяются (login, register, password reset)
- [x] Header компонент сохраняет существующий layout и стили
- [x] `authStore` API остается backward compatible
- [x] Performance impact минимален (один дополнительный API вызов при logout)
- [x] Graceful degradation: logout работает даже если backend недоступен

---

## Risk Mitigation

**Primary Risk:** Backend logout endpoint недоступен или возвращает ошибку, пользователь застревает в авторизованном состоянии.

**Mitigation:**
1. **Fail-safe подход:** Локальная очистка происходит в любом случае
2. **Optimistic update:** UI обновляется немедленно, API вызов в фоне
3. **Error handling:** Логирование ошибок, но не блокировка logout
4. **Timeout:** API запрос с timeout 5 секунд, после чего локальная очистка

**Rollback Plan:**
1. Удалить кнопку "Выйти" из Header компонента
2. Откатить изменения в `authStore.logout()` до версии Epic 28
3. Удалить метод `authService.logout()`
4. Удалить тесты для logout функциональности
5. Откатить package.json dependencies (если добавлялись)

---

## Definition of Done

- [x] Все 4 stories завершены с acceptance criteria
- [x] Кнопка "Выйти" работает на desktop и mobile
- [x] Backend `/auth/logout/` вызывается с refresh токеном
- [x] При успехе API refresh токен инвалидируется на сервере
- [x] Logout очищает tokens, cookies, localStorage
- [x] Редирект на главную страницу после logout
- [x] Header обновляется корректно после logout
- [x] Fail-safe: logout работает даже при ошибке API
- [x] Тесты написаны и проходят (coverage >= 90%)
- [x] Никаких регрессий в Epic 28 функциональности
- [x] Code review пройден
- [x] QA тестирование завершено

---

## Technical Implementation Details

### authService.logout() Implementation

```typescript
// frontend/src/services/authService.ts
import axios from 'axios';

export const authService = {
  // ... существующие методы (login, register, etc.)

  /**
   * Logout пользователя через инвалидацию refresh токена на сервере
   * @param refreshToken - Refresh token для инвалидации
   * @returns Promise<void>
   * @throws Error если backend вернул ошибку
   */
  async logout(refreshToken: string): Promise<void> {
    try {
      await axios.post('/api/v1/auth/logout/', {
        refresh: refreshToken,
      });
    } catch (error) {
      // Логируем ошибку, но не пробрасываем - fail-safe подход
      console.error('Backend logout failed, proceeding with local cleanup:', error);
      // Можно добавить error tracking (Sentry, etc.)
    }
  },
};
```

### authStore.logout() Update

```typescript
// frontend/src/stores/authStore.ts
import { authService } from '@/services/authService';

export const useAuthStore = create<AuthState>()(
  devtools(
    set => ({
      // ... существующие методы

      logout: async () => {
        // Получить refresh token перед очисткой
        const refreshToken = localStorage.getItem('refreshToken');

        // Попытаться инвалидировать на сервере
        if (refreshToken) {
          try {
            await authService.logout(refreshToken);
          } catch (error) {
            // Логируем, но продолжаем локальную очистку (fail-safe)
            console.error('Server logout failed:', error);
          }
        }

        // Локальная очистка ВСЕГДА происходит
        localStorage.removeItem('refreshToken');
        deleteCookie('refreshToken');

        set({
          accessToken: null,
          user: null,
          isAuthenticated: false,
        });
      },

      // ... остальные методы
    }),
    { name: 'AuthStore' }
  )
);
```

### Header Component Update

```typescript
// frontend/src/components/layout/Header.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
// ... другие импорты

const Header: React.FC = () => {
  const router = useRouter();
  const isAuthenticated = authSelectors.useIsAuthenticated();
  const user = authSelectors.useUser();
  const logout = useAuthStore(state => state.logout);

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };

  return (
    <header className="bg-white sticky top-0 z-50">
      {/* ... существующий код ... */}

      {/* Desktop авторизация/профиль */}
      <div className="hidden md:flex items-center gap-2">
        {isAuthenticated && user ? (
          <>
            <span className="text-body-s text-text-secondary">
              Привет, {user.first_name}!
            </span>
            <Link href="/profile">
              <Button variant="secondary" size="small">
                Профиль
              </Button>
            </Link>
            <Button
              variant="secondary"
              size="small"
              onClick={handleLogout}
            >
              Выйти
            </Button>
          </>
        ) : (
          {/* ... кнопки Регистрация/Войти ... */}
        )}
      </div>

      {/* Mobile авторизация */}
      {isMobileMenuOpen && (
        <div className="md:hidden">
          {isAuthenticated && user ? (
            <>
              <span>Привет, {user.first_name}!</span>
              <Link href="/profile">
                <Button variant="secondary" size="small" className="w-full">
                  Профиль
                </Button>
              </Link>
              <Button
                variant="secondary"
                size="small"
                className="w-full"
                onClick={handleLogout}
              >
                Выйти
              </Button>
            </>
          ) : (
            {/* ... кнопки Регистрация/Войти ... */}
          )}
        </div>
      )}
    </header>
  );
};
```

### MSW Mock for Testing

```typescript
// frontend/src/__mocks__/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  // ... существующие handlers

  // Logout endpoint - успех
  http.post('/api/v1/auth/logout/', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Logout endpoint - ошибка (invalid token)
  http.post('/api/v1/auth/logout/', () => {
    return HttpResponse.json(
      { error: 'Invalid or expired token' },
      { status: 400 }
    );
  }),
];
```

### Test Example

```typescript
// frontend/src/components/layout/__tests__/Header.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useAuthStore } from '@/stores/authStore';
import Header from '../Header';

describe('Header - Logout Functionality', () => {
  beforeEach(() => {
    // Setup authenticated user
    useAuthStore.setState({
      isAuthenticated: true,
      user: { first_name: 'Иван', role: 'retail' },
      accessToken: 'test-access-token',
    });
    localStorage.setItem('refreshToken', 'test-refresh-token');
  });

  it('shows logout button for authenticated users', () => {
    render(<Header />);
    expect(screen.getByText('Выйти')).toBeInTheDocument();
  });

  it('calls logout and redirects on logout button click', async () => {
    const user = userEvent.setup();
    const mockPush = jest.fn();
    jest.spyOn(require('next/navigation'), 'useRouter').mockReturnValue({
      push: mockPush,
    });

    render(<Header />);

    const logoutButton = screen.getByText('Выйти');
    await user.click(logoutButton);

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(localStorage.getItem('refreshToken')).toBeNull();
      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });
});
```

---

## Next Steps

### Dependencies

- **Blocking:** Epic 30 должен быть завершен (backend `/auth/logout/` endpoint работает)
- **Blocking:** Epic 28 функциональность не должна иметь регрессий

### Future Enhancements

1. **UX Improvements:**
   - Показывать loading spinner во время logout
   - Toast notification при успешном logout
   - Confirmation dialog перед logout (опционально)

2. **Security Enhancements:**
   - Auto-logout при истечении refresh token
   - Logout всех сессий (если пользователь залогинен с нескольких устройств)
   - Показывать список активных сессий в профиле

3. **Analytics:**
   - Трекинг logout событий в analytics
   - Мониторинг частоты logout для UX insights
   - A/B тестирование различных logout flows

---

## Story Manager Handoff

**Используйте этот Epic для создания детальных User Stories.**

**Ключевые соображения:**

- Это frontend интеграция с backend logout (Epic 30) на **Next.js 15.4.6 + React 19.1.0 + Zustand 4.5.7**
- **Integration points:**
  - `frontend/src/components/layout/Header.tsx` - добавление кнопки "Выйти"
  - `frontend/src/stores/authStore.ts` - обновление метода `logout()`
  - `frontend/src/services/authService.ts` - добавление метода `logout()`
  - Backend API endpoint `/auth/logout/` (Epic 30)
- **Существующие паттерны:**
  - Использование компонента `Button` из UI kit
  - Zustand store для state management
  - Axios для API вызовов
  - Vitest + RTL + MSW для тестирования
- **Критические compatibility requirements:**
  - **Fail-safe подход:** локальная очистка ВСЕГДА происходит
  - Обратная совместимость с Epic 28
  - Graceful degradation при ошибках API
  - Минимальное изменение существующих компонентов
- **Каждая story должна включать:**
  - Полное покрытие тестами (>= 90%)
  - Проверку отсутствия регрессий в Epic 28
  - TypeScript строгую типизацию
  - Error handling для всех edge cases

Epic должен обеспечить **полноценный logout с UI кнопкой, серверной инвалидацией токенов и fail-safe локальной очисткой**.
