/**
 * Настройка тестового окружения Vitest для FREESPORT Frontend
 */

// Установка env переменных для тестов
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8001/api/v1';

// Подключение дополнительных матчеров для DOM элементов (Vitest версия)
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';
import React from 'react';

// Подключение vitest-axe для accessibility тестирования
import 'vitest-axe/extend-expect';

// Импорт глобальных стилей для тестирования CSS переменных
import './src/app/globals.css';

// Настройка MSW для мокирования API запросов
import { server } from './src/__mocks__/api/server';

// Запуск MSW server перед всеми тестами
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));

// Глобальные настройки для всех тестов
beforeEach(() => {
  // Очистка всех моков перед каждым тестом
  vi.clearAllMocks();
  // Очистка localStorage перед каждым тестом
  localStorage.clear();
});

// Сброс handlers после каждого теста
afterEach(() => server.resetHandlers());

// Остановка MSW server после всех тестов
afterAll(() => server.close());

// Мокирование next/router для тестирования
vi.mock('next/router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
}));

// Мокирование next/navigation для тестирования с app router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// Мокирование next/link с правильной forwardRef сигнатурой
vi.mock('next/link', () => {
  const Link = React.forwardRef((props: any, ref: any) => {
    const { children, href, ...rest } = props;
    return React.createElement('a', { href, ref, ...rest }, children);
  });
  Link.displayName = 'Link';
  return { default: Link };
});

// Мокирование authStore для тестов с методом getState()
// Это необходимо для apiClient, который использует useAuthStore.getState().accessToken
vi.mock('@/stores/authStore', async () => {
  const actual = await vi.importActual('@/stores/authStore');
  const mockStore = vi.fn(() => null);

  // Добавляем getState() метод для совместимости с apiClient
  mockStore.getState = vi.fn(() => ({
    accessToken: null,
    refreshToken: null,
    user: null,
    isAuthenticated: false,
  }));

  return {
    ...actual,
    useAuthStore: mockStore,
  };
});

// Подавление предупреждений console в тестах (опционально)
global.console = {
  ...console,
  // Подавить логи в тестах, но оставить ошибки и предупреждения
  log: vi.fn(),
  debug: vi.fn(),
  info: vi.fn(),
};
