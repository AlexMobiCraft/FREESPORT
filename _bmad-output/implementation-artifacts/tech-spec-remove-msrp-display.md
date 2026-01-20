---
title: 'Remove MSRP Display'
slug: 'remove-msrp-display'
created: '2026-01-20'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: 
  - Next.js
  - React
  - TypeScript
files_to_modify: 
  - frontend/src/components/business/ProductCard/ProductCard.tsx
  - frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx
  - frontend/src/components/ui/ProductCard/ElectricProductCard.tsx
  - frontend/src/components/product/ProductInfo.tsx
  - frontend/src/components/product/ProductSummary.tsx
code_patterns: 
  - 'Conditional rendering with canSeeRrpMsrp logic'
  - 'Props showMSRP in ProductCard'
  - 'Props msrp in ElectricProductCard'
test_patterns: 
  - 'Existing component tests in __tests__ folders'
---

# Overview

## Problem Statement
Отображение цены МРЦ (Максимальная Розничная Цена / MSRP) в интерфейсе фронтенда создает нежелательный визуальный шум или противоречит новым бизнес-требованиям. Необходимо полностью скрыть это поле для всех пользователей B2B.

## Solution
Удалить условный рендеринг поля `msrp` (МРЦ) и соответствующие пропсы из всех компонентов отображения товара (карточки, детальные страницы, списки). Поле `rrp` (РРЦ) оставить без изменений.

## Scope

### In Scope
- Компонент `ProductCard` + Тесты
- Компонент `ElectricProductCard`
- Компонент `ProductInfo`
- Компонент `ProductSummary`

### Out of Scope
- Backend / Database changes
- RRP logic changes

# Context for Development
- **ProductCard.tsx**: Условный рендеринг и проп `showMSRP`. Тесты в `ProductCard.test.tsx`.
- **ElectricProductCard.tsx**: Проп `msrp` и рендеринг.
- **ProductInfo.tsx** / **ProductSummary.tsx**: Использование переменных `canSeeRrpMsrp` и смешанных условий.

# Implementation Plan

- [ ] Task 1: Update `ProductCard` Component
  - File: `frontend/src/components/business/ProductCard/ProductCard.tsx`
  - Action: 
    - Remove `showMSRP` from `ProductCardProps`.
    - Remove default value `showMSRP = false` from component arguments.
    - Remove the conditional rendering block `{product.msrp && product.msrp > 0 && ...}` inside the B2B price block.
    - **CRITICAL**: Update the outer condition `(mode === 'b2b' || userRole !== 'retail') && (product.rrp || product.msrp)` to ONLY check `product.rrp`.
      - Example: `(mode === 'b2b' || userRole !== 'retail') && product.rrp && product.rrp > 0`.
      - This prevents rendering empty containers if MSRP was present but RRP was not.

- [ ] Task 2: Update `ProductCard` Tests
  - File: `frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx`
  - Action: 
    - Remove the test case `'displays MSRP for B2B users when showMSRP is true'`.
    - Ensure other tests (specifically RRP) pass.

- [ ] Task 3: Update `ElectricProductCard` Component
  - File: `frontend/src/components/ui/ProductCard/ElectricProductCard.tsx`
  - Action: 
    - Remove `msrp` from `ElectricProductCardProps` interface.
    - Remove destructuring of `msrp`.
    - Remove rendering of `{msrp && <div>МРЦ: {formatPrice(msrp)} ₽</div>}`.
    - **CRITICAL**: Clean up the container logic. Check if `rrp || msrp` condition needs simplification to just `rrp`.
      - If `rrp` is missing/zero, do NOT render the container div `mb-2 space-y-0.5 ...`.

- [ ] Task 4: Update `ProductInfo` Component
  - File: `frontend/src/components/product/ProductInfo.tsx`
  - Action: 
    - Inside `render()`: Remove the conditional block checking for `msrp` inside the `canSeeRrpMsrp` area.
    - **Refactor**: Rename variable `canSeeRrpMsrp` to `canSeeRrp` to reflect new reality.
    - Update all usages to `canSeeRrp`.

- [ ] Task 5: Update `ProductSummary` Component
  - File: `frontend/src/components/product/ProductSummary.tsx`
  - Action: 
    - Remove the JSX block rendering "МРЦ" inside the selected variant info section.
    - **Refactor**: Rename `canSeeRrpMsrp` to `canSeeRrp` here as well.
    - Keep "РРЦ" rendering intact, using the new variable name.

# Acceptance Criteria

- [ ] AC 1: MSRP is NOT visible in `ProductCard`
  - Given I am a B2B user (wholesale/trainer)
  - When I view the catalog or list
  - Then I see the RRP (if applicable) but NOT the MSRP
  - And `showMSRP` prop is no longer available in code

- [ ] AC 2: MSRP is NOT visible in `ElectricProductCard`
  - Given I am browsing the Electric Theme
  - When I view a product card
  - Then I see no "МРЦ" label or price

- [ ] AC 3: MSRP is NOT visible in Product Details (`ProductInfo`/`ProductSummary`)
  - Given I am on a product page
  - When I view product details
  - Then I see "РРЦ" (if applicable) but NOT "МРЦ"

# Verification Plan

### Automated Tests
- Run `ProductCard` tests to ensure no regressions:
  ```bash
  cd frontend
  npm test src/components/business/ProductCard/__tests__/ProductCard.test.tsx
  ```
- Run full build to check for type errors (missing props):
  ```bash
  cd frontend
  npm run build
  ```

### Manual Verification
1.  Set `NEXT_PUBLIC_API_MOCKING=enabled` (if needed) or use real data.
2.  Log in as a B2B user (e.g., `wholesale_level1`).
3.  Navigate to Catalog (Blue Theme).
    - [ ] Check Product Item: Verify no MSRP is shown. Check RRP is shown (if data exists).
4.  Navigate to Product Detail Page.
    - [ ] Check Product Info: Verify no MSRP.
    - [ ] Select a variant: Verify no MSRP in summary.
5.  Switch to Electric Theme (`/electric`).
    - [ ] Check Product Cards.
    - [ ] **Ghost Element Check**: Verify there are no empty white spaces or weird reserved heights where MSRP used to be.
    - [ ] Verify RRP is still shown if applicable.
