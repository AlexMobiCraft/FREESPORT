---
title: 'Stock Quantity Ranges'
slug: 'stock-quantity-ranges'
created: '2026-02-19'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Django', 'React', 'TypeScript']
files_to_modify: 
  - 'backend/apps/products/serializers.py'
  - 'backend/apps/products/tests/test_serializers.py'
  - 'frontend/src/types/api.ts'
  - 'frontend/src/components/product/ProductSummary.tsx'
code_patterns: ['SerializerMethodField', 'Computed Frontend Logic']
test_patterns: ['pytest']
---

# Overview

## Problem Statement
The user wants to display product stock quantities as ranges (e.g., "1-5", "50+") instead of exact numbers in the product variant details on the Product Page. This prevents exposing exact stock levels while still informing the user about availability.

## Solution
1.  **Backend**: Add a `stock_range` computed field to `ProductVariantSerializer` that maps `available_quantity` to the defined ranges (`1-5`, `6-19`, `20-49`, `50 и более`).
2.  **Frontend**: Update `ProductVariant` type definition to include `stock_range`.
3.  **Frontend**: Update `ProductSummary` component to display this range string instead of "N шт." when a variant is selected.
4.  **Tests**: Update `test_serializers.py` to verify the new field.

## Scope
- **In Scope**:
    - Backend: `ProductVariantSerializer` modification.
    - Test: `test_serializers.py` update.
    - Frontend: Type update in `api.ts`.
    - Frontend: UI update in `ProductSummary.tsx`.
- **Out of Scope**:
    - Catalog list view (quantity/ranges should NOT be shown there).
    - Changes to how "is_in_stock" boolean works.

# Context for Development

## Codebase Patterns
- **Backend**: Use `SerializerMethodField` in DRF serializers for computed presentation logic.
- **Frontend**: TypeScript interfaces in `types/api.ts` must match API response. UI components use `selectedVariant` object to render details.

## Files to Reference
| File | Purpose |
| ---- | ------- |
| `backend/apps/products/serializers.py` | Add `get_stock_range` method to `ProductVariantSerializer`. |
| `backend/apps/products/tests/test_serializers.py` | Add unit tests for `stock_range`. |
| `frontend/src/types/api.ts` | Add `stock_range` to `ProductVariant` interface. |
| `frontend/src/components/product/ProductSummary.tsx` | Use `stock_range` for display. |

## Technical Decisions
- **Range Logic**:
    - 0: (Handled by `is_in_stock=False` logic) -> "Нет в наличии" (Frontend handles this status label separately)
    - 1 - 5: "1 - 5"
    - 6 - 19: "6 - 19"
    - 20 - 49: "20 - 49"
    - 50+: "50 и более"
- **Field Name**: `stock_range` (string).

# Implementation Plan

## Backend Tasks
- [x] Task 1: Update ProductVariantSerializer
  - File: `backend/apps/products/serializers.py`
  - Action: Add `stock_range` field with `SerializerMethodField`. Implement `get_stock_range` using the logic (1-5, 6-19, 20-49, 50+). Use `available_quantity` for calculation.
- [x] Task 2: Add Backend Tests
  - File: `backend/apps/products/tests/test_serializers.py`
  - Action: Add `test_stock_range` cases covering all ranges (0, 3, 10, 30, 60).

## Frontend Tasks
- [x] Task 3: Update Types
  - File: `frontend/src/types/api.ts`
  - Action: Add `stock_range?: string` to `ProductVariant` interface.
- [x] Task 4: Update UI
  - File: `frontend/src/components/product/ProductSummary.tsx`
  - Action: Replace `${selectedVariant.available_quantity} шт.` with `${selectedVariant.stock_range}` in the selected variant info block. Ensure it handles cases where `stock_range` might be missing gracefully (though backend ensures it).

# Acceptance Criteria

- [ ] AC 1: Backend Range Logic 1-5
  - Given a product variant with stock 3
  - When serialized by the API
  - Then the `stock_range` field is "1 - 5"
- [ ] AC 2: Backend Range Logic 50+
  - Given a product variant with stock 100
  - When serialized by the API
  - Then the `stock_range` field is "50 и более"
- [ ] AC 3: Frontend Display
  - Given I am on a product page
  - When I select a variant with stock > 0
  - Then I see the stock range (e.g., "1 - 5") in the variant details
  - And I NEVER see the exact quantity number
- [ ] AC 4: Out of Stock
  - Given a product variant with stock 0
  - When serialized by the API
  - Then the `stock_range` is empty or handled by `is_in_stock` logic (Frontend shows "Нет в наличии")
