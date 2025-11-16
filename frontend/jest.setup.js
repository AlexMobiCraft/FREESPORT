/**
 * Настройка тестового окружения Jest для FREESPORT Frontend
 */

// Подключение дополнительных матчеров для DOM элементов
import '@testing-library/jest-dom';

// Настройка MSW для мокирования API запросов
import { server } from './__mocks__/server';

// Запуск MSW server перед всеми тестами
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));

// Глобальные настройки для всех тестов
beforeEach(() => {
  // Очистка всех моков перед каждым тестом
  jest.clearAllMocks();
});

// Сброс handlers после каждого теста
afterEach(() => server.resetHandlers());

// Остановка MSW server после всех тестов
afterAll(() => server.close());

// Мокирование next/router для тестирования
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
}));

// Мокирование next/navigation для тестирования с app router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// Подавление предупреждений console в тестах (опционально)
global.console = {
  ...console,
  // Подавить логи в тестах, но оставить ошибки и предупреждения
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
};
