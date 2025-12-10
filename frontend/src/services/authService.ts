/**
 * Auth Service - методы для аутентификации
 *
 * Обрабатывает login, register, logout, refreshToken
 * Story 28.2: Добавлен метод registerB2B для регистрации B2B пользователей
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
   * Регистрация нового пользователя (B2C)
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
   * Регистрация B2B пользователя (бизнес-партнер)
   * Story 28.2 - AC 4: Интеграция с Backend API
   *
   * @param userData - данные для регистрации B2B пользователя
   * @returns Promise с данными зарегистрированного пользователя и токенами
   *
   * Отличия от B2C:
   * - Обязательные поля: company_name, tax_id
   * - User может иметь is_verified: false (требуется модерация)
   * - Не происходит автоматический редирект (обрабатывается в компоненте)
   */
  async registerB2B(userData: RegisterRequest): Promise<RegisterResponse> {
    const response = await apiClient.post<RegisterResponse>('/auth/register/', userData);

    const { access, refresh, user } = response.data;

    // Story 28.2 - AC 6: Сохранение токенов даже для непроверенных пользователей
    // Пользователь может войти, но функционал будет ограничен до is_verified: true
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
