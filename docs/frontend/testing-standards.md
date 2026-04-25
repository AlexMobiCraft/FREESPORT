# Стандарты тестирования FREESPORT Frontend

## 📁 Структура тестов Frontend

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   └── __tests__/
│   │   │       └── Button.test.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── __tests__/
│   │   │       ├── Header.test.tsx
│   │   │       └── Footer.test.tsx
│   │   └── forms/
│   │       └── __tests__/
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── __tests__/
│   │       └── useAuth.test.ts
│   ├── services/
│   │   ├── api.ts
│   │   └── __tests__/
│   │       └── api.test.ts
│   ├── utils/
│   │   └── __tests__/
│   └── app/
│       ├── (auth)/
│       │   └── __tests__/
│       └── products/
│           └── __tests__/
├── __mocks__/                    # Mock definitions
│   ├── next/
│   │   └── router.js
│   └── api/
├── vitest.config.js               # Vitest конфигурация
├── vitest.setup.js               # Настройка тестового окружения
└── playwright.config.ts        # E2E тесты конфигурация
```

## 🧪 Типы тестов Frontend

### 1. **Unit тесты компонентов** (Vitest + React Testing Library)

- **Назначение**: Тестирование отдельных React компонентов в изоляции
- **Технология**: Vitest + React Testing Library + MSW
- **Запуск**: `npm test` или `npm run test:watch`

**Пример структуры:**

```tsx
// src/components/ui/__tests__/Button.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "../Button";

describe("Button Component", () => {
  test("renders button with text", () => {
    render(<Button>Click me</Button>);
    expect(
      screen.getByRole("button", { name: /click me/i }),
    ).toBeInTheDocument();
  });

  test("calls onClick handler when clicked", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

### 2. **Hook тесты** (React Testing Library)

- **Назначение**: Тестирование custom React hooks
- **Технология**: `@testing-library/react-hooks`

**Пример структуры:**

```tsx
// src/hooks/__tests__/useAuth.test.ts
import { renderHook, act } from "@testing-library/react";
import { useAuth } from "../useAuth";

describe("useAuth Hook", () => {
  test("should initialize with null user", () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.user).toBeNull();
  });

  test("should login user", async () => {
    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.login("test@example.com", "password");
    });

    expect(result.current.user).toBeTruthy();
  });
});
```

### 3. **Integration тесты** (Vitest + MSW)

- **Назначение**: Тестирование взаимодействия компонентов с API
- **Технология**: Mock Service Worker (MSW) для API mocking

**Пример структуры:**

```tsx
// src/services/__tests__/api.test.ts
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { fetchProducts } from "../api";

const server = setupServer(
  http.get("/api/products", () => {
    return HttpResponse.json([{ id: 1, name: "Test Product", price: 100 }]);
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("API Service", () => {
  test("fetchProducts returns products", async () => {
    const products = await fetchProducts();
    expect(products).toHaveLength(1);
    expect(products[0].name).toBe("Test Product");
  });
});
```

### 4. **E2E тесты** (Playwright)

- **Назначение**: Тестирование критических пользовательских сценариев
- **Технология**: Playwright для браузерного тестирования
- **Запуск**: `npx playwright test`

**Пример структуры:**

```typescript
// tests/e2e/auth.spec.ts
import { test, expect } from "@playwright/test";

test.describe("Authentication Flow", () => {
  test("user can login and logout", async ({ page }) => {
    await page.goto("/login");

    await page.fill('[data-testid="email"]', "test@example.com");
    await page.fill('[data-testid="password"]', "password");
    await page.click('[data-testid="login-button"]');

    await expect(page).toHaveURL("/dashboard");
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();

    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL("/login");
  });
});
```

## 🔧 Конфигурация Vitest

```javascript
// vitest.config.js
const nextVitest = require("next/jest");

const createVitestConfig = nextVitest({
  dir: "./",
});

const customVitestConfig = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/vitest.setup.js"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  collectCoverageFrom: [
    "src/**/*.{js,jsx,ts,tsx}",
    "!src/**/*.d.ts",
    "!src/**/*.stories.{js,jsx,ts,tsx}",
    "!src/**/index.{js,jsx,ts,tsx}",
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  testPathIgnorePatterns: [
    "<rootDir>/.next/",
    "<rootDir>/node_modules/",
    "<rootDir>/tests/e2e/",
  ],
};

module.exports = createVitestConfig(customVitestConfig);
```

## 🎭 Настройка тестового окружения

```javascript
// vitest.setup.js
import "@testing-library/jest-dom";
import { server } from "./src/__mocks__/server";

// Mock Next.js router
jest.mock("next/router", () => ({
  useRouter() {
    return {
      route: "/",
      pathname: "/",
      query: {},
      asPath: "/",
      push: vi.fn(),
      replace: vi.fn(),
      reload: vi.fn(),
      back: vi.fn(),
      prefetch: vi.fn(),
      beforePopState: vi.fn(),
      events: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
      },
    };
  },
}));

// Setup MSW
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
```

## 🏭 Mock стратегия Frontend

### MSW (Mock Service Worker)

```typescript
// src/__mocks__/handlers.ts
// MSW 2.x API - используйте http и HttpResponse вместо устаревших rest и ctx
import { http, HttpResponse } from "msw";

export const handlers = [
  // Auth endpoints
  http.post("/api/auth/login", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      user: { id: 1, email: "test@example.com" },
      token: "mock-jwt-token",
    });
  }),

  // Products endpoints
  http.get("/api/products", () => {
    return HttpResponse.json([
      { id: 1, name: "Test Product", price: 100 },
      { id: 2, name: "Another Product", price: 200 },
    ]);
  }),

  // Cart endpoints
  http.get("/api/cart", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  // Cart item update
  http.patch("/api/v1/cart/items/:id/", async ({ request, params }) => {
    const { quantity } = (await request.json()) as { quantity: number };
    return HttpResponse.json({ id: params.id, quantity });
  }),

  // Cart item delete
  http.delete("/api/v1/cart/items/:id/", () => {
    return new HttpResponse(null, { status: 204 });
  }),
];
```

### Component Mocks

```typescript
// __mocks__/next/image.js
import React from "react";

const MockedImage = ({ src, alt, ...props }) => {
  return React.createElement("img", { src, alt, ...props });
};

export default MockedImage;
```

## 🚀 Команды запуска

### Unit и Integration тесты

```bash
# Запуск всех тестов
npm test

# Запуск в watch режиме
npm run test:watch

# Запуск с покрытием
npm run test:coverage

# Запуск конкретного теста
npm test -- Button.test.tsx

# Запуск тестов в CI режиме
npm run test:ci
```

### E2E тесты

```bash
# Запуск всех E2E тестов
npx playwright test

# Запуск в headed режиме
npx playwright test --headed

# Запуск конкретного теста
npx playwright test auth.spec.ts

# Запуск в debug режиме
npx playwright test --debug
```

## 📊 Целевое покрытие кода

- **Branches**: 80% ✅
- **Functions**: 80% ✅
- **Lines**: 80% ✅
- **Statements**: 80% ✅

## 📝 Соглашения по именованию

### Файлы тестов

- **Unit тесты**: `ComponentName.test.tsx`
- **Hook тесты**: `useHookName.test.ts`
- **Service тесты**: `serviceName.test.ts`
- **E2E тесты**: `feature.spec.ts`

### Test IDs

- **Формат**: `data-testid="component-action"`
- **Примеры**:
  - `data-testid="login-button"`
  - `data-testid="product-card"`
  - `data-testid="user-menu"`

### Тестовые данные

- **Email Pattern**: `test.{feature}@example.com`
- **User Pattern**: `Test {Feature} User`
- **Product Pattern**: `Test Product {Number}`

## 🔧 Настройка Playwright

```typescript
// playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
});
```

## ⚡ Быстрый старт

### Создание нового unit теста

1. Создать файл: `src/components/__tests__/ComponentName.test.tsx`
2. Использовать шаблон с `render` и `screen`
3. Запустить: `npm test ComponentName`

### Создание нового E2E теста

1. Создать файл: `tests/e2e/feature.spec.ts`
2. Использовать `test` и `expect` из Playwright
3. Запустить: `npx playwright test feature.spec.ts`

### Добавление нового mock

1. Добавить handler в `src/__mocks__/handlers.ts`
2. Перезапустить тесты для применения изменений

---

**Дата создания**: 18 августа 2025  
**Версия**: 1.0  
**Статус**: ✅ УТВЕРЖДЕНО - Соответствует архитектурным принципам FREESPORT
