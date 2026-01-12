/**
 * Vitest Setup File
 * Настройка MSW и тестового окружения
 */

import { beforeAll, afterEach, afterAll } from 'vitest';
import { server } from '@/__mocks__/api/server';

// Запускаем MSW server перед всеми тестами
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' });
});

// Сбрасываем handlers после каждого теста
afterEach(() => {
  server.resetHandlers();
});

// Закрываем server после всех тестов
afterAll(() => {
  server.close();
});
