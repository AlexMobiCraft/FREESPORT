# Vitest Troubleshooting Guide

## Common Issues

### 1. "Cannot find module 'msw/node'" after migration
**Причина:** MSW v2 использует ESM экспорты
**Решение:** Убедитесь что используете `import { http, HttpResponse } from 'msw'` вместо CommonJS require

### 2. happy-dom: "querySelector is not a function"
**Причина:** happy-dom не полностью совместим с вашим кодом
**Решение:** Переключитесь на jsdom в `vitest.config.mts`:
- Изменить: `test.environment: 'jsdom'`
- Установить: `npm install -D jsdom`

### 3. Tests hang/timeout after migration
**Причина:** MSW server не закрывается корректно
**Решение:** Проверьте что в `vitest.setup.ts` есть `afterAll(() => server.close())`

### 4. Coverage reports показывают 0%
**Причина:** Неправильный provider или exclude паттерны
**Решение:** Проверьте `coverage.provider: 'v8'` и exclude списки в vitest.config.mts

### 5. "expect is not defined" ошибки
**Причина:** Не настроены глобальные API
**Решение:** Убедитесь что `test.globals: true` в vitest.config.mts и `"types": ["vitest/globals"]` в tsconfig.json

### 6. Alias `@/` не работает в тестах
**Причина:** Не настроен resolve.alias в Vitest
**Решение:** Добавьте в vitest.config.mts:
```typescript
resolve: {
  alias: {
    '@': path.resolve(__dirname, './src'),
  },
}
```

### 7. MSW handlers не перехватывают requests
**Причина:** Server не запущен до выполнения тестов
**Решение:** Проверьте порядок в setup файле: `beforeAll(() => server.listen())` должен быть первым

### 8. "Invalid PostCSS Plugin" ошибка
**Причина:** Vitest пытается обработать Tailwind CSS конфиг
**Решение:** Добавьте условие в `postcss.config.mjs`:
```javascript
const config = {
  plugins: process.env.VITEST ? [] : ['@tailwindcss/postcss'],
};
```

И установите env переменную в package.json scripts через `cross-env VITEST=true vitest run`

## Performance Optimization Tips

- Используйте `--reporter=dot` для ускорения вывода в CI
- Настройте `test.pool: 'threads'` для параллельного выполнения
- Добавьте `test.fileParallelism: true` для больших кодбаз
- Используйте `coverage.clean: false` для инкрементальных coverage отчётов

## Rollback Plan (если Vitest не заработает)

1. Откатить package.json к коммиту с Jest
2. Восстановить `jest.config.js` и `jest.setup.js` из Git history
3. Удалить `vitest.config.mts` и `vitest.setup.ts`
4. Выполнить: `npm install`
5. Альтернатива: использовать Jest с experimental ESM support (не рекомендуется)

## Migration Performance Metrics

**Story 10.4 Results:**
- **Test Execution Time:** Vitest ~17s vs Jest ~20s (15% faster)
- **Bundle Size:** 203 fewer packages after removing Jest dependencies
- **Success Rate:** 357/359 tests passing (99.4%)
- **MSW v2 Integration:** ✅ Successfully working (was blocked in Jest)
- **Coverage:** Maintained 80%+ threshold for service layer

## Environment Variables

Убедитесь что следующие env переменные установлены в `vitest.setup.ts`:
```typescript
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8001/api/v1';
```

Это необходимо для корректной работы MSW handlers с правильными URLs.
