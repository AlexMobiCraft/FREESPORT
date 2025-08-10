/**
 * Zustand store для управления аутентификацией
 * Состояние пользователя и JWT токенов
 */
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { User, AuthTokens } from '@/types';
import { tokenStorage } from '@/services/api';

interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthActions {
  // Авторизация пользователя
  login: (user: User, tokens: AuthTokens) => void;
  
  // Выход из системы
  logout: () => void;
  
  // Обновление данных пользователя
  updateUser: (user: Partial<User>) => void;
  
  // Обновление токенов
  updateTokens: (tokens: AuthTokens) => void;
  
  // Инициализация состояния из localStorage
  initializeAuth: () => void;
  
  // Установка состояния загрузки
  setLoading: (loading: boolean) => void;
}

type AuthStore = AuthState & AuthActions;

// Начальное состояние
const initialState: AuthState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: true,
};

// Создание Zustand store
export const useAuthStore = create<AuthStore>()(
  devtools(
    (set, get) => ({
      ...initialState,
      
      login: (user: User, tokens: AuthTokens) => {
        // Сохранение токенов в localStorage
        tokenStorage.set(tokens);
        
        set({
          user,
          tokens,
          isAuthenticated: true,
          isLoading: false,
        }, false, 'auth/login');
      },
      
      logout: () => {
        // Очистка localStorage
        tokenStorage.clear();
        
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          isLoading: false,
        }, false, 'auth/logout');
      },
      
      updateUser: (userData: Partial<User>) => {
        const { user } = get();
        
        if (user) {
          set({
            user: { ...user, ...userData },
          }, false, 'auth/updateUser');
        }
      },
      
      updateTokens: (tokens: AuthTokens) => {
        // Обновление токенов в localStorage
        tokenStorage.set(tokens);
        
        set({
          tokens,
        }, false, 'auth/updateTokens');
      },
      
      initializeAuth: () => {
        try {
          const storedTokens = tokenStorage.get();
          
          if (storedTokens) {
            set({
              tokens: storedTokens,
              isAuthenticated: true,
              isLoading: false,
            }, false, 'auth/initialize');
            
            // TODO: Здесь можно добавить запрос для получения данных пользователя
            // из backend по токену
          } else {
            set({
              isLoading: false,
            }, false, 'auth/initialize');
          }
        } catch (error) {
          console.error('Ошибка инициализации аутентификации:', error);
          
          set({
            user: null,
            tokens: null,
            isAuthenticated: false,
            isLoading: false,
          }, false, 'auth/initializeError');
        }
      },
      
      setLoading: (loading: boolean) => {
        set({
          isLoading: loading,
        }, false, 'auth/setLoading');
      },
    }),
    {
      name: 'auth-store',
      // Сериализация только публичных полей для devtools
      serialize: {
        options: {
          user: true,
          isAuthenticated: true,
          isLoading: true,
          // Не сериализуем токены для безопасности
          tokens: false,
        },
      },
    }
  )
);

// Селекторы для удобного доступа к состоянию
export const authSelectors = {
  // Текущий пользователь
  useUser: () => useAuthStore((state) => state.user),
  
  // Статус аутентификации
  useIsAuthenticated: () => useAuthStore((state) => state.isAuthenticated),
  
  // Состояние загрузки
  useIsLoading: () => useAuthStore((state) => state.isLoading),
  
  // Роль пользователя
  useUserRole: () => useAuthStore((state) => state.user?.role),
  
  // Проверка роли B2B
  useIsB2BUser: () => useAuthStore((state) => {
    const role = state.user?.role;
    return role ? ['wholesale_level1', 'wholesale_level2', 'wholesale_level3', 'trainer', 'federation_rep'].includes(role) : false;
  }),
  
  // Проверка роли админа
  useIsAdmin: () => useAuthStore((state) => state.user?.role === 'admin'),
};