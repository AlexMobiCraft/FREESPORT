# Story 33.4: Integration into Homepage

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want to see the brands block in the correct location on the homepage,
So that I can easily find it and navigate to brand catalogs.

## Acceptance Criteria

1. **Given** the Blue Theme homepage (`src/app/(blue)/home/page.tsx`),
   **When** the page renders,
   **Then** it fetches the featured brands on the server side (SSR) using `brandsService`.

2. **Given** the fetched brands data,
   **When** passed to `HomePage` and then to `BrandsBlock`,
   **Then** the `BrandsBlock` appears immediately below the `MarketingBannersSection`.

3. **Given** the page load process,
   **Then** the brands block has explicit dimensions (defined in `BrandsBlock` component or container) to prevent Layout Shift (CLS) during hydration (NFR-02).

4. **Given** the `brandsService`,
   **Then** it includes a `getFeatured()` method that calls the API endpoint `/api/v1/products/brands/?is_featured=true`.

5. **Given** the `HomePage` component,
   **Then** it accepts a `featuredBrands` prop (typed as `Brand[]`) and passes it to the `BrandsBlock`.

## Tasks / Subtasks

- [x] Task 1: Update Brands Service
  - [x] Modify `frontend/src/services/brandsService.ts`.
  - [x] Add `getFeatured()` method to `BrandsService` class.
  - [x] Implementation: Call `apiClient.get('/brands/', { params: { is_featured: true } })`.
  - [x] Ensure return type is `Promise<Brand[]>`.

- [x] Task 2: Update Home Page Component (Client)
  - [x] Modify `frontend/src/components/home/HomePage.tsx`.
  - [x] Update component props interface to include `featuredBrands: Brand[]`.
  - [x] Import `BrandsBlock` from `@/components/business/home/BrandsBlock/BrandsBlock` (or index).
  - [x] Render `<BrandsBlock brands={featuredBrands} />` immediately after `<MarketingBannersSection />`.
  - [x] Ensure conditional rendering if `featuredBrands` is empty (optional, depending on design, but usually good practice).

- [x] Task 3: Update Blue Theme Page (Server)
  - [x] Modify `frontend/src/app/(blue)/home/page.tsx`.
  - [x] Make `BlueHomePage` an `async` function.
  - [x] Call `brandsService.getFeatured()` to fetch data.
  - [x] Pass result to `<HomePage />` as `featuredBrands` prop.

- [x] Task 4: Verify CLS & SEO
  - [x] Ensure `BrandsBlock` container has height/width constraints (handled in 33.3, but verify container in `HomePage`).
  - [x] Verify SSR output contains brand names/links (View Source).

- [x] Review Follow-ups (AI)
  - [x] [AI-Review][High] Fix API endpoint in brandsService.ts to match AC4 — RESOLVED: Backend routes `apps.products.urls` directly under `/api/v1/`, so actual endpoint is `/api/v1/brands/` (not `/api/v1/products/brands/`). AC4 path is inaccurate; current implementation `/brands/` is correct.
  - [x] [AI-Review][Medium] Add error logging in Home Page SSR catch block (frontend/src/app/(blue)/home/page.tsx)
  - [x] [AI-Review][Medium] Explicitly type `featuredBrands` in `BlueHomePage` (`page.tsx`) to ensure type safety.
  - [x] [AI-Review][Medium] Explicitly set `page_size: 20` in `brandsService.getFeatured()` to ensure carousel has data.
  - [x] [AI-Review][Low] Refactor `brandsService` to use constants for page sizes.

## Dev Notes

### Architecture & Patterns

- **Data Fetching**:
  - Follows "Server Component fetches, Client Component renders" pattern.
  - `page.tsx` (Server) -> `HomePage` (Client) -> `BrandsBlock` (Client).
  - API call logic resides in `services/brandsService.ts`, NOT in component.

- **Types**:
  - Use `Brand` interface from `@/types/api`.

- **Styling**:
  - `HomePage` layout uses a stack of sections. Ensure `BrandsBlock` has consistent margin/padding with other sections (usually handled by the section components themselves, check if `BrandsBlock` needs a wrapper section or if it includes it).
  - Note: `BrandsBlock` from Story 33.3 is likely just the block. `HomePage` uses sections like `HeroSection`. Maybe wrap `BrandsBlock` in a `<section className="container mx-auto py-8">` or similar in `HomePage.tsx`.

### Project Structure Notes

- `src/services/brandsService.ts`: Central location for brand-related API calls.
- `src/app/(blue)/home/page.tsx`: Entry point for Blue Theme Home.
- `src/components/home/HomePage.tsx`: Layout composition for Home.

### References

- [Epics.md: Story 33.4](/docs/planning-artifacts/epics.md)
- [Architecture.md](/docs/planning-artifacts/architecture.md) (ADR-001 BFF)
- [Story 33.3](/docs/implementation-artifacts/33-3-brandsblock-component-logic-ui.md) (Component Implementation)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Full test suite: 132/133 files pass (2174/2179 tests pass, 14 skipped)
- Pre-existing failure: `QuickLinksSection.test.tsx` (5 tests) — unrelated to Story 33.4

### Completion Notes List

- ✅ Task 1: Added `getFeatured()` method to `BrandsService` — calls `/brands/?is_featured=true`, returns `Promise<Brand[]>`. 5 unit tests added.
- ✅ Task 2: Updated `HomePage` — added `featuredBrands: Brand[]` prop, imported `BrandsBlock`, renders conditionally after `MarketingBannersSection`. 5 integration tests (updated existing + 3 new).
- ✅ Task 3: Made `BlueHomePage` async, calls `brandsService.getFeatured()` with try/catch fallback, passes data to `HomePage`. 17 tests (updated existing + 3 new SSR tests).
- ✅ Task 4: CLS verified — `BrandsBlock` has explicit dimensions (`h-20 md:h-24`, `py-6 md:py-8`). SSR verified — brands fetched server-side, rendered with `aria-label="Популярные бренды"` and semantic HTML links.
- ✅ Resolved review finding [High]: API endpoint `/brands/` is correct — backend `apps.products.urls` maps directly under `/api/v1/`, no `/products/` prefix. AC4 path inaccurate.
- ✅ Resolved review finding [Medium]: Added `console.error('[BlueHomePage] Failed to fetch featured brands:', error)` in SSR catch block. Test updated to verify error logging.

### File List

- `frontend/src/services/brandsService.ts` (modified — added `getFeatured()`)
- `frontend/src/services/__tests__/brandsService.test.ts` (new — 5 tests)
- `frontend/src/components/home/HomePage.tsx` (modified — added `featuredBrands` prop, `BrandsBlock` render)
- `frontend/src/components/home/__tests__/HomePage.test.tsx` (modified — 5 tests updated for new prop + BrandsBlock)
- `frontend/src/app/(blue)/home/page.tsx` (modified — async SSR, `brandsService.getFeatured()`)
- `frontend/src/app/(blue)/home/__tests__/page.test.tsx` (modified — 17 tests, async rendering + SSR assertions)
