# Рекомендации по настройке TypeScript для тестирования в FREESPORT Platform

## Проблема

При выполнении linting в GitHub Actions возникали ошибки:

1. `@typescript-eslint/no-explicit-any` - использование `as any` в тестах
2. Отсутствие типов для матчеров из `@testing-library/jest-dom`

## Решение

### 1. Использование явных типов вместо `any`

Вместо использования `as any` для приведения типов в параметризованных тестах, следует определять явные типы:

```typescript
// Плохо
render(<Button variant={variant as any}>Кнопка</Button>)

// Хорошо
type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
render(<Button variant={variant as ButtonVariant}>Кнопка</Button>)
```

### 2. Расширение типов Jest для @testing-library/jest-dom

Для корректной работы TypeScript с матчерами из `@testing-library/jest-dom`, необходимо расширить глобальные типы Jest:

```typescript
import '@testing-library/jest-dom'

// Расширяем типы Jest для включения матчеров из @testing-library/jest-dom
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R
      toHaveClass(className: string | string[]): R
      toBeDisabled(): R
      toHaveAttribute(attr: string, value?: string): R
    }
  }
}
```

### 3. Правильное использование `toHaveClass`

Матчер `toHaveClass` может принимать либо строку, либо массив строк, но не несколько аргументов:

```typescript
// Плохо
expect(button).toHaveClass('opacity-50', 'cursor-not-allowed')

// Хорошо
expect(button).toHaveClass('opacity-50')
expect(button).toHaveClass('cursor-not-allowed')

// Или альтернативно
expect(button).toHaveClass(['opacity-50', 'cursor-not-allowed'])
```

## Рекомендации для проекта

### 1. Создание глобального файла типов

Рекомендуется создать файл `types/jest.d.ts` в корне проекта с определением типов для Jest:

```typescript
import '@testing-library/jest-dom'

declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R
      toHaveClass(className: string | string[]): R
      toBeDisabled(): R
      toHaveAttribute(attr: string, value?: string): R
      toHaveStyle(style: Record<string, string>): R
      toBeVisible(): R
      toContainElement(element: HTMLElement | null): R
      toBeEmptyDOMElement(): R
      toHaveFocus(): R
      toBeChecked(): R
      toHaveFormValues(values: Record<string, any>): R
     toHaveTextContent(text: string | RegExp, options?: { normalizeWhitespace: boolean }): R
      toHaveValue(value: string | string[] | number): R
      toHaveDisplayValue(value: string | RegExp): R
      toBeRequired(): R
      toBeInvalid(): R
      toBeValid(): R
      toHaveDescription(text: string | RegExp): R
      toHaveRole(role: string): R
      // Добавьте другие матчеры по мере необходимости
    }
  }
}

export {}
```

### 2. Обновление tsconfig.json

Добавить ссылку на глобальные типы Jest в `tsconfig.json`:

```json
{
  "compilerOptions": {
    // ... другие опции
    "types": ["jest", "@testing-library/jest-dom"]
  }
}
```

### 3. Стандарты для тестовых файлов

При создании новых тестовых файлов для компонентов:

1. Всегда импортировать `@testing-library/jest-dom`
2. Определять типы для пропсов компонента, если они используются в параметризованных тестах
3. Избегать использования `as any`
4. Следовать паттерну Given-When-Then для структурирования тестов

### 4. Пример шаблона для теста компонента

```typescript
/**
 * Тесты компонента [ComponentName] для FREESPORT Platform
 */
import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import [ComponentName] from '@/components/[path]/[ComponentName]'
import '@testing-library/jest-dom'

// Определение типов для пропсов, если необходимо
type [ComponentName]Variant = 'primary' | 'secondary'
type [ComponentName]Size = 'sm' | 'md' | 'lg'

describe('[ComponentName]', () => {
  // Тесты здесь
})
```

## Заключение

Следование этим рекомендациям поможет избежать ошибок TypeScript и ESLint в тестах, улучшит читаемость кода и обеспечит лучшую типобезопасность в проекте.
