/**
 * Auth Service Tests
 */
import authService from '../authService';
import { useAuthStore } from '@/stores/authStore';
import { server } from '../../../__mocks__/server';

// Setup MSW для этих тестов
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('authService', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  test('login successfully authenticates user', async () => {
    const result = await authService.login({
      email: 'test@example.com',
      password: 'password123',
    });

    expect(result.access).toBe('mock-access-token');
    expect(result.user.email).toBe('test@example.com');
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(localStorage.getItem('refreshToken')).toBe('mock-refresh-token');
  });

  test('login fails with invalid credentials', async () => {
    await expect(
      authService.login({
        email: 'wrong@example.com',
        password: 'wrong',
      })
    ).rejects.toThrow();
  });

  test('logout clears tokens and store', () => {
    // Setup: login first
    useAuthStore.getState().setTokens('test-access', 'test-refresh');

    authService.logout();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });

  test('refreshToken updates access token', async () => {
    // Setup: set refresh token
    localStorage.setItem('refreshToken', 'mock-refresh-token');

    const result = await authService.refreshToken();

    expect(result.access).toBe('new-mock-access-token');
    expect(useAuthStore.getState().accessToken).toBe('new-mock-access-token');
  });
});
