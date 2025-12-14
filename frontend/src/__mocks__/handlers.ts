/**
 * MSW (Mock Service Worker) Handlers
 * Story 28.3 - Восстановление пароля
 * Story 28.4 - Защищенные маршруты и управление сессиями
 *
 * Mock API handlers для тестирования auth flow
 */

import { http, HttpResponse } from 'msw';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1';

/**
 * Auth Handlers - Session Management
 * Story 28.4 - AC 2: MSW моки для /auth/me/
 * Story 31.2: Logout endpoint
 */
export const authHandlers = [
  // Story 31.2: POST /auth/logout/ - Logout endpoint
  http.post('*/auth/logout/', async ({ request }) => {
    const body = (await request.json()) as { refresh?: string };

    if (!body.refresh) {
      return HttpResponse.json({ error: 'Refresh token is required' }, { status: 400 });
    }

    if (body.refresh === 'invalid-refresh-token') {
      return HttpResponse.json({ error: 'Invalid or expired token' }, { status: 400 });
    }

    if (body.refresh === 'missing-auth') {
      return HttpResponse.json(
        { detail: 'Authentication credentials were not provided.' },
        { status: 401 }
      );
    }

    if (body.refresh === 'network-error') {
      return HttpResponse.error();
    }

    // Успешный logout - 204 No Content
    return new HttpResponse(null, { status: 204 });
  }),

  // GET /auth/me/ - Get current authenticated user
  http.get('*/auth/me/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    // Проверка наличия Bearer token
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    // Mock: всегда возвращаем test user
    return HttpResponse.json({
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      role: 'retail',
      is_verified: true,
      company_name: null,
    });
  }),

  // POST /auth/refresh/ - Refresh endpoint (used by axios interceptor)
  http.post('*/auth/refresh/', async ({ request }) => {
    const body = (await request.json()) as { refresh?: string };

    if (!body.refresh) {
      return HttpResponse.json({ detail: 'Missing refresh token' }, { status: 400 });
    }

    // Возвращаем новый access token
    return HttpResponse.json({ access: 'mock-access-token' });
  }),

  // GET /users/profile/ - Profile endpoint (AuthProvider)
  http.get('*/users/profile/', ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    return HttpResponse.json({
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      role: 'retail',
      is_verified: true,
      company_name: null,
    });
  }),
];

/**
 * Password Reset Handlers
 * Story 28.3 - AC 8, 9: MSW моки для тестирования
 */
export const passwordResetHandlers = [
  // POST /auth/password-reset/ - Request password reset
  http.post(`${API_BASE_URL}/auth/password-reset/`, async () => {
    // AC 1: Всегда возвращает success (security best practice)
    return HttpResponse.json({
      detail: 'Password reset email sent.',
    });
  }),

  // POST /auth/password-reset/validate-token/ - Validate reset token
  http.post(`${API_BASE_URL}/auth/password-reset/validate-token/`, async ({ request }) => {
    const body = (await request.json()) as { uid: string; token: string };

    // Mock: token "expired-token" считается истёкшим
    if (body.token === 'expired-token') {
      return HttpResponse.json({ detail: 'Token expired' }, { status: 410 });
    }

    // Mock: token "invalid-token" считается невалидным
    if (body.token === 'invalid-token') {
      return HttpResponse.json({ detail: 'Invalid token' }, { status: 404 });
    }

    // Все остальные токены считаются валидными
    return HttpResponse.json({ valid: true });
  }),

  // POST /auth/password-reset/confirm/ - Confirm password reset
  http.post(`${API_BASE_URL}/auth/password-reset/confirm/`, async ({ request }) => {
    const body = (await request.json()) as {
      uid: string;
      token: string;
      new_password: string;
    };

    // Mock: expired token
    if (body.token === 'expired-token') {
      return HttpResponse.json({ detail: 'Token expired' }, { status: 410 });
    }

    // Mock: invalid token
    if (body.token === 'invalid-token') {
      return HttpResponse.json({ detail: 'Invalid token' }, { status: 404 });
    }

    // Mock: weak password validation
    if (body.new_password === 'weak') {
      return HttpResponse.json({ new_password: ['Password is too weak'] }, { status: 400 });
    }

    // Success response
    return HttpResponse.json({
      detail: 'Password has been reset successfully.',
    });
  }),
];

// Export all handlers
export const handlers = [...authHandlers, ...passwordResetHandlers];
