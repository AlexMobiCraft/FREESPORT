---
title: 'SSR Authorization and B2B Pricing Display'
slug: 'ssr-auth-b2b-pricing'
created: '2026-01-16 23:55'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Next.js 15 (App Router)'
  - 'Django REST Framework'
  - 'Axios (Server Side)'
files_to_modify:
  - 'frontend/src/services/productsService.ts'
  - 'frontend/src/app/(blue)/product/[slug]/page.tsx'
code_patterns:
  - 'Extract cookies using next/headers in Server Components'
  - 'Pass custom headers to Service methods for SSR context'
  - 'Update TypeScript interfaces for API responses'
test_patterns:
  - 'Manual verification with different user roles'
---

# Overview

## Problem Statement
B2B пользователи (оптовики, тренеры) не видят свои специфические цены (РРЦ, МРЦ) на детальной странице товара при первой загрузке (SSR), так как запрос к API выполняется анонимно. Бэкенд скрывает эти поля для неавторизованных пользователей. Кроме того, в типах фронтенд-сервиса отсутствуют определения для полей `rrp` и `msrp`, хотя они присутствуют в ответе API для B2B ролей.

## Solution
1.  **Обновление `ProductPage` (Server Component)**:
    - Использовать `cookies()` из `next/headers` для извлечения куки авторизации (`sessionid`).
    - Формировать объект заголовков HTTP с этой кукой.
2.  **Рефакторинг `productsService`**:
    - Обновить метод `getProductBySlug` для приема опционального параметра конфигурации axios или заголовков.
    - Пробрасывать эти заголовки в запрос `apiClient`.
3.  **Обновление Типов**:
    - Добавить опциональные поля `rrp` и `msrp` (строкового типа) в интерфейс `ApiProductDetailResponse` в `productsService.ts`.
    - Добавить маппинг этих полей в функции `adaptProductToDetail`.

## In Scope
- Модификация `frontend/src/app/(blue)/product/[slug]/page.tsx` для извлечения и передачи кук.
- Модификация `frontend/src/services/productsService.ts` для поддержки инъекции заголовков и обновления типов.

## Out of Scope
- Визуальный редизайн блока цен.
- Изменения в логике бэкенда.

# Context for Development

## Codebase Patterns
- **Server Components**: Используют `next/headers` для доступа к данным запроса (cookies).
- **Service Layer**: Сервисы (`productsService`) оборачивают вызовы `apiClient`.
- **API Client**: Axios инстанс. Для SSR запросов внутри Docker сети используется внутренний URL, но заголовки авторизации нужно пробрасывать явно.
- **Types**: Интерфейсы API ответов отделены от интерфейсов компонентов (`ProductDetail`).

## Files to Reference
| File Path | Description |
|-----------|-------------|
| `frontend/src/services/productsService.ts` | Сервис для работы с товарами. Требует обновления типов и метода получения товара. |
| `frontend/src/app/(blue)/product/[slug]/page.tsx` | Серверная страница товара. Точка входа SSR запроса. |
| `frontend/src/utils/server-auth.ts` | Пример извлечения кук для получения роли пользователя (reference implementation). |

# Implementation Plan

## Task 1: Update Products Service Types and Mapping
- [x] Update `ApiProductDetailResponse` interface in `frontend/src/services/productsService.ts`
  - **File**: `frontend/src/services/productsService.ts`
  - **Action**: Add optional `rrp` and `msrp` fields to the `variants` array definition within the interface.
- [x] Update `adaptProductToDetail` function
  - **File**: `frontend/src/services/productsService.ts`
  - **Action**: Map `rrp` and `msrp` from the API response to the `ProductDetail` object's variants.

## Task 2: Enhance Products Service for SSR Auth
- [x] Update `getProductBySlug` signature
  - **File**: `frontend/src/services/productsService.ts`
  - **Action**: Add optional `headers` parameter (Record<string, string>) to the method.
- [x] Pass headers to API request
  - **File**: `frontend/src/services/productsService.ts`
  - **Action**: Pass the `headers` object to the `apiClient.get` call options.

### Task 3: Implement SSR Auth Forwarding in Product Page
- [x] Extract Session Cookie
  - **File**: `frontend/src/app/(blue)/product/[slug]/page.tsx`
  - **Action**: Use `cookies()` to get `sessionid` (or fallback to `fs_session`).
- [x] Construct Headers and Call Service
  - **File**: `frontend/src/app/(blue)/product/[slug]/page.tsx`
  - **Action**: Create a headers object `{ Cookie: "sessionid=..." }` if the cookie exists. Pass this object to `productsService.getProductBySlug`.

### Task 4: Documentation Update
- [x] Update Frontend Architecture Documentation
  - **File**: `docs/front-end-spec.md` (or relevant architecture doc)
  - **Action**: Document the SSR Authentication pattern using `next/headers` cookies and `productsService` header injection.
  - **Notes**: Ensure future developers understand how to make authenticated SSR requests.

## Acceptance Criteria

- [x] AC 1: **B2B User SSR**: Given I am logged in as a Wholesale user (e.g., `wholesale_level1`), when I navigate to a product page directly (SSR), then I see the `RRP` and `MSRP` prices in the variant info block.
- [x] AC 2: **Anonymous User SSR**: Given I am not logged in, when I navigate to a product page, then I DO NOT see `RRP` and `MSRP` prices.
- [x] AC 3: **Retail User SSR**: Given I am logged in as a Retail user, when I navigate to a product page, then I DO NOT see `RRP` and `MSRP` prices.
- [x] AC 4: **Type Safety**: The code compiles without TypeScript errors regarding missing `rrp`/`msrp` properties.

# Notes

- **Security**: Пробрасываем только `sessionid`. Не передаем другие чувствительные заголовки без необходимости.
- **Docker Networking**: Убедиться, что внутренние запросы (`http://backend:8000`) корректно принимают `Host` заголовок, если это потребуется (обычно Django доверяет `sessionid` независимо от Host, если `ALLOWED_HOSTS` настроен корректно). В данном случае мы просто пробрасываем Cookie.

## Review Notes
- Adversarial review completed.
- Findings: 2 total, 0 fixed, 2 skipped (Low/Medium severity).
- Resolution approach: Skip (Acceptable for MVP).
- Known Issue: `productsService.test.ts` runs in Node environment, masking potential browser-specific issues.
- Known Issue: Double backend request on product page load (product + user role).
