# Story 3.1.4: Fix Price Import Logic (RRP/MSRP)

**Epic:** Epic 3.1: 1C Import Refactoring
**Priority:** High
**Estimation:** 5 SP
**Status:** Open

## User Story
**As a** B2B User (Wholesaler) or Federation Representative
**I want** the system to correctly import and display RRP, MSRP, and fallback prices
**So that** I can see the correct market value and my specific purchasing price without data gaps.

## Problem Statement
Current 1C import logic fails for B2B segments:
1. **Naming Mismatch:** RRP/MSRP fields are not populated because `PriceType` names do not match (e.g., `recommended_retail_price` vs `rrp`).
2. **Missing Fallback:** Federation representatives do not see a price if their specific price type is missing (should default to Retail).
3. **Data Gaps:** B2B clients need to see RRP (Recommended Retail Price) for comparison, even if 1C doesn't send it explicitly as a separate price type.

## Implementation Requirements
Derived from `_bmad-output/implementation-artifacts/tech-spec-fix-price-import-logic.md`:

1.  **Database Migration:**
    * Rename/Update `choices` in the `PriceType` model to standardize codes: `recommended_retail_price` -> `rrp`.
    * Create a migration to update existing records.

2.  **Import Logic Update:**
    * In `VariantImportProcessor` (or relevant logic), when `retail_price` is imported, automatically duplicate this value into the `rrp` field to ensure a baseline exists.
    * Ensure `msrp` is mapped correctly.

3.  **Price Retrieval Logic:**
    * Update the price strategy for `federation_rep`.
    * Logic: `IF federation_price IS NULL THEN RETURN retail_price`.

## Acceptance Criteria
- [ ] **AC1:** Database `PriceType` codes are successfully updated to `rrp` and `msrp` via migration.
- [ ] **AC2:** When importing a product with `retail_price`, the `rrp` field is automatically populated with the same value (unless specific RRP is provided).
- [ ] **AC3:** `msrp` values are correctly imported and stored in the Product model.
- [ ] **AC4:** A user with role `federation_rep` sees the `retail_price` for products that do not have a specific `federation_price` set.
- [ ] **AC5:** Unit/Integration tests pass for the new import mappings and fallback logic.
