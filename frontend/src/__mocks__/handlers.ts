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
 */
export const authHandlers = [
  // GET /auth/me/ - Get current authenticated user
  http.get(`${API_BASE_URL}/auth/me/`, ({ request }) => {
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
