/**
 * Vitest Setup File
 * Настройка MSW и тестового окружения
 */

import { beforeAll, afterEach, afterAll, vi } from 'vitest';
import React from 'react';
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
server.close();
});

// Mock Next.js Image component
vi.mock('next/image', () => ({
  default: (props: any) => {
    // eslint-disable-next-line @next/next/no-img-element
    return React.createElement('img', { ...props, alt: props.alt });
  },
}));
