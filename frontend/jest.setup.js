/**
 * Настройка тестового окружения Jest для FREESPORT Frontend
 */

// Подключение дополнительных матчеров для DOM элементов
import '@testing-library/jest-dom'

// Глобальные настройки для всех тестов
beforeEach(() => {
  // Очистка всех моков перед каждым тестом
  jest.clearAllMocks()
})

// Мокирование next/router для тестирования
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
}))

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
}))

// Подавление предупреждений console в тестах (опционально)
global.console = {
  ...console,
  // Подавить логи в тестах, но оставить ошибки и предупреждения
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
}