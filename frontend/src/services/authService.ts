/**
 * Auth Service - методы для аутентификации
 *
 * Обрабатывает login, register, logout, refreshToken
 */

import apiClient from './api-client';
import { useAuthStore } from '@/stores/authStore';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  RefreshTokenResponse,
} from '@/types/api';

class AuthService {
  /**
   * Авторизация пользователя
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login/', credentials);

    const { access, refresh, user } = response.data;

    // Сохранить tokens в store
    useAuthStore.getState().setTokens(access, refresh);
    useAuthStore.getState().setUser(user);

    return response.data;
  }

  /**
   * Регистрация нового пользователя
   */
  async register(userData: RegisterRequest): Promise<RegisterResponse> {
    const response = await apiClient.post<RegisterResponse>('/auth/register/', userData);

    const { access, refresh, user } = response.data;

    // Сохранить tokens в store
    useAuthStore.getState().setTokens(access, refresh);
    useAuthStore.getState().setUser(user);

    return response.data;
  }

  /**
   * Выход из системы
   */
  logout(): void {
    useAuthStore.getState().logout();
  }

  /**
   * Обновление access token через refresh token
   * (обычно вызывается автоматически через api-client interceptor)
   */
  async refreshToken(): Promise<RefreshTokenResponse> {
    const refreshToken = useAuthStore.getState().getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await apiClient.post<RefreshTokenResponse>('/auth/refresh/', {
      refresh: refreshToken,
    });

    const { access } = response.data;

    // Обновить access token в store
    useAuthStore.getState().setTokens(access, refreshToken);

    return response.data;
  }
}

const authService = new AuthService();
export default authService;
