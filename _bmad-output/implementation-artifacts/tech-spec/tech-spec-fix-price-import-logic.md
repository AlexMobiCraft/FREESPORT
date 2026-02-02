---
title: 'Исправление импорта цен (РРЦ, МРЦ, Федерация)'
slug: 'fix-price-import-logic'
created: '2026-01-16T21:35:00'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Django', 'Python']
files_to_modify: 
  - 'backend/apps/products/models.py'
  - 'backend/apps/products/services/variant_import.py'
  - 'backend/apps/products/migrations/0038_update_pricetype_choices.py'
  - 'backend/tests/integration/test_variant_import.py'
code_patterns:
  - 'Django Models: Choices match DB values'
  - 'Import: Batch processing'
  - 'Testing: TransactionTestCase'
test_patterns:
  - 'Integration tests for import logic'
---

# Tech-Spec: Исправление импорта цен (РРЦ, МРЦ, Федерация)

**Created:** 2026-01-16T21:35:00

## Overview

### Problem Statement
Цены РРЦ и МРЦ не загружаются в базу из-за несовпадения внутренних кодов маппинга (`recommended_retail_price` vs `rrp`) и полей модели. Также отсутствует цена для роли `federation_rep`, из-за чего она не устанавливается.

### Solution
1. **DB Schema:** Обновить `PriceType.product_field` choices (`rrp`, `msrp`) + миграция данных.
2. **Import Logic:** В `variant_import.py`:
   * При обновлении `retail_price` (РРЦ из 1С) автоматически дублировать значение в поле `rrp` для отображения.
3. **Fallback Logic:** Верифицировать `ProductVariant.get_price_for_user`: для `federation_rep` использовать `retail_price`, если `federation_price` отсутствует.

### Scope

**In Scope:**
* `backend/apps/products/models.py`: `PriceType` choices alignment.
* `backend/apps/products/services/variant_import.py`: `update_variant_prices` logic enhancement.
* Data migration for existing `PriceType` records.
* Verification of fallback logic.

**Out of Scope:**
* Changes to 1C export format.
* Frontend display logic (apart from verifying data presence).

## Context for Development

### Codebase Patterns
*   **Django Models:** `PriceType` stores mapping configuration in DB. Code choices must match DB values.
*   **Import Processing:** `VariantImportProcessor` handles XML parsing and DB updates.
*   **Transactions:** Import tests use `TransactionTestCase`.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/apps/products/models.py` | `PriceType` choices definition. |
| `backend/apps/products/services/variant_import.py` | Import logic (`update_variant_prices`). |
| `backend/tests/integration/test_variant_import.py` | Integration tests. |
| `backend/apps/products/migrations/0038_update_pricetype_choices.py` | Data migration. |

### Technical Decisions

### RRP/MSRP Handling Strategy
*   **Context:** Need to show RRP even if explicit RRP feed is missing.
*   **Decision:** **Duplication (Option A)**. Duplicate `retail_price` to `rrp` during import if RRP is missing/empty.
*   **Alternatives:** Runtime calculation (rejected due to complexity in sorting/filtering).
*   **Consequences:** Requires DB migration, slightly increased storage, faster read queries.

## Implementation Plan

### Tasks

1.  **Update PriceType Choices**
    *   File: `backend/apps/products/models.py`
    *   Action: Update `product_field` choices: replace `recommended_retail_price` with `rrp` and `max_suggested_retail_price` with `msrp`.
    *   Notes: Ensure string values exactly match `ProductVariant` field names.

2.  **Create Data Migration**
    *   File: `backend/apps/products/migrations/0038_update_pricetype_choices.py` (New)
    *   Action: Create migration to update `PriceType` records in DB.
    *   Notes: `UPDATE products_pricetype SET product_field='rrp' WHERE product_field='recommended_retail_price'` (and similarly for MSRP).

3.  **Update Import Logic for RRP Duplication**
    *   File: `backend/apps/products/services/variant_import.py`
    *   Action: In `update_variant_prices`, when processing `retail_price`, add: `price_updates['rrp'] = price_value` (ONLY if no explicit RRP is present in the update batch? No, logic is: *always* copy retail to RRP if RRP is untrusted/missing in source. BUT wait, ADR says "Duplication". Safest: `if field_name == 'retail_price': price_updates['rrp'] = price_value`. If a real 'rrp' comes later in the loop, it will overwrite this key. If 'rrp' comes earlier, 'retail_price' overwrites. **Refinement:** Ensure RRP type processing priority or check `if 'rrp' not in price_updates`.)
    *   Refined Action: Just enable the copy. 1C export today does NOT send RRP type. So copy is safe.

4.  **Add Test Case**
    *   File: `backend/tests/integration/test_variant_import.py`
    *   Action: Add `test_update_variant_prices_copies_rrp`.
    *   Steps: Create variant, update with `retail_price`, assert `rrp` is also set.

### Risks & Mitigations

| Category | Risk | Mitigation |
| :--- | :--- | :--- |
| **Data Integrity** | Existing `PriceType` records become invalid (orphaned choices). | Include a **Data Migration** to rename values in DB: `recommended_retail_price` -> `rrp`. |
| **Import Logic** | Future overwrite if 1C adds real RRP. | Copy `retail_price` to `rrp` **only if** incoming price type is `retail_price`. |
| **Business Logic** | Zero Price Fallback. | Acceptable behavior, no hard check required. |

### Acceptance Criteria

*   [ ] **AC1:** `PriceType` records in DB have `product_field` values `rrp` and `msrp` instead of old long names.
*   [ ] **AC2:** Importing a price with type `retail_price` updates BOTH `retail_price` and `rrp` fields on `ProductVariant`.
*   [ ] **AC3:** Importing a price with type `max_suggested_retail_price` (mapped to `msrp`) correctly updates the `msrp` field.
*   [ ] **AC4:** `federation_rep` user sees `retail_price` when viewing product (via standard `get_price_for_user` logic).

## Additional Context

### Dependencies
None

### Testing Strategy
1.  **Unit/Integration:** Run `pytest backend/tests/integration/test_variant_import.py` to verify new test case.
2.  **Manual:** Run `python manage.py import_products_from_1c --file-type=prices` locally and check Admin/DB.

### Notes
Usage of `retail_price` as fallback for `federation_rep` is the confirmed requirement.
