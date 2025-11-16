/**
 * Конфигурация Jest для тестирования Next.js приложения
 */
import createJestConfig from 'next/jest.js';

const nextJestConfig = createJestConfig({
  // Путь к Next.js приложению для загрузки next.config.js и файлов .env
  dir: './',
});

// Дополнительная конфигурация Jest
const customJestConfig = {
  // Среда выполнения тестов
  testEnvironment: 'jsdom',

  // Файлы настройки тестового окружения
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Паттерны для поиска тестовых файлов
  testMatch: [
    '<rootDir>/tests/**/*.(test|spec).(ts|tsx|js|jsx)',
    '<rootDir>/src/**/__tests__/**/*.(ts|tsx|js|jsx)',
    '<rootDir>/src/**/*.(test|spec).(ts|tsx|js|jsx)',
  ],

  // Псевдонимы модулей
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },

  // Трансформация модулей (включая MSW)
  transformIgnorePatterns: ['node_modules/(?!(msw)/)'],

  // Файлы для игнорирования при покрытии кода
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '/coverage/',
    'next.config.ts',
    'tailwind.config.ts',
    'postcss.config.mjs',
  ],

  // Пороговые значения покрытия кода
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },

  // Директория для отчета о покрытии
  coverageDirectory: 'coverage',

  // Формат отчета о покрытии
  coverageReporters: ['text', 'lcov', 'html'],

  // Игнорировать файлы при сборе покрытия
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{ts,tsx}',
    '!src/**/index.{ts,tsx}',
  ],
};

export default nextJestConfig(customJestConfig);
