/**
 * Auth Store - управление аутентификацией и пользователем
 *
 * @security
 * - Access token хранится ТОЛЬКО в memory (Zustand store)
 * - Refresh token хранится в localStorage
 * - Tokens очищаются при logout
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { User } from '@/types/api';

interface AuthState {
  accessToken: string | null;
  user: User | null;
  isAuthenticated: boolean;

  // Actions
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  getRefreshToken: () => string | null;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    set => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,

      setTokens: (access: string, refresh: string) => {
        // Refresh token в localStorage для persistence
        localStorage.setItem('refreshToken', refresh);

        // Access token ТОЛЬКО в memory
        set({
          accessToken: access,
          isAuthenticated: true,
        });
      },

      setUser: (user: User) => {
        set({ user });
      },

      logout: () => {
        // Очистить refresh token из localStorage
        localStorage.removeItem('refreshToken');

        // Очистить state
        set({
          accessToken: null,
          user: null,
          isAuthenticated: false,
        });
      },

      getRefreshToken: () => {
        return localStorage.getItem('refreshToken');
      },
    }),
    { name: 'AuthStore' }
  )
);
