# Tech Spec WIP: Product Page Price & SKU Enhancements

## Core Understanding

**Problem Statement:**
B2B users (opt1, opt2, opt3, trainer) need to see Recommended Retail Price (RRP) and Manufacturer Suggested Retail Price (MSRP) for product variants to manage their business effectively. Additionally, the product page currently displays a generic product SKU which is less relevant than the specific variant SKU. The placement of the variant's price also needs refinement to improve the visual hierarchy of the product detail page.

**High-Level Solution:**
1.  **Backend:** Expose `rrp` and `msrp` fields in the `ProductVariantSerializer`. Implement role-based visibility to ensure only authorized B2B roles (opt1-3, trainer) can see these fields.
2.  **Frontend:** 
    *   Update API types to include `rrp` and `msrp`.
    *   Modify `ProductInfo` to display the price of the *selected variant* and hide the base product SKU.
    *   Modify `ProductSummary` to manage the price display in `ProductInfo` and update the "selected variant info" block to show RRP/MSRP while removing the price from that block.
3.  **Documentation:** Update relevant design and frontend specification documents.

**In-Scope:**
*   Backend: `ProductVariantSerializer` modifications in `backend/apps/products/serializers.py`.
*   Frontend:
    *   Type definitions in `frontend/src/types/api.ts`.
    *   `ProductInfo` component in `frontend/src/components/product/ProductInfo.tsx`.
    *   `ProductSummary` component in `frontend/src/components/product/ProductSummary.tsx`.
    *   `ProductPageClient` component in `frontend/src/components/product/ProductPageClient.tsx` (if needed for coordination).
*   Documentation:
    *   `docs/front-end-spec.md`
    *   `docs/4-ux-design/00-design-system-migration/03-page-specs.md`

**Out-of-Scope:**
*   Changes to the Product List/Catalog page visibility logic (already implemented, but we will ensure consistency).
*   Any changes to the cart or checkout flow logic.
*   Changes to how `federation_rep`, `retail`, or guests see prices (they remain unchanged).

## Proposed Changes

### Backend
- Update `ProductVariantSerializer` to include `rrp` and `msrp`.
- Override `to_representation` in `ProductVariantSerializer` to `pop` these fields if the user's role is not in `['wholesale_level1', 'wholesale_level2', 'wholesale_level3', 'trainer']`.

### Frontend
- Update `ProductVariant` interface in `frontend/src/types/api.ts` to include `rrp?: string` and `msrp?: string`.
- **ProductInfo.tsx**:
    - Add `selectedVariant` to props.
    - If `selectedVariant` is provided, use `selectedVariant.current_price` instead of `product.price`.
    - If `selectedVariant` is provided, use `selectedVariant.sku` instead of `product.sku`.
    - Remove the hardcoded "Артикул: {product.sku}" from the top if it's the base product SKU.
- **ProductSummary.tsx**:
    - Pass `selectedVariant` down to `ProductInfo`.
    - In `selected-variant-info` block:
        - Remove the "Цена" row.
        - Add "РРЦ" and "МРЦ" rows for non-guest roles (opt1-3, trainer).
        - Format prices using `formatPrice`.

## Checklist
- [ ] Backend: Serializer update & role-based filter.
- [ ] Frontend: Type updates.
- [ ] Frontend: `ProductInfo` modification (Price at top, variant SKU).
- [ ] Frontend: `ProductSummary` modification (RRP/MSRP rows, remove price row).
- [ ] Documentation: Blue theme spec.
- [ ] Documentation: Electric Orange theme spec.
- [ ] Verification: Test with different user roles in MSW or real backend.
