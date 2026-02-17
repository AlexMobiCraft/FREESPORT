# Story 33.4: Integration into Homepage

Status: ready-for-dev

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

- [ ] Task 1: Update Brands Service
  - [ ] Modify `frontend/src/services/brandsService.ts`.
  - [ ] Add `getFeatured()` method to `BrandsService` class.
  - [ ] Implementation: Call `apiClient.get('/brands/', { params: { is_featured: true } })`.
  - [ ] Ensure return type is `Promise<Brand[]>`.

- [ ] Task 2: Update Home Page Component (Client)
  - [ ] Modify `frontend/src/components/home/HomePage.tsx`.
  - [ ] Update component props interface to include `featuredBrands: Brand[]`.
  - [ ] Import `BrandsBlock` from `@/components/business/home/BrandsBlock/BrandsBlock` (or index).
  - [ ] Render `<BrandsBlock brands={featuredBrands} />` immediately after `<MarketingBannersSection />`.
  - [ ] Ensure conditional rendering if `featuredBrands` is empty (optional, depending on design, but usually good practice).

- [ ] Task 3: Update Blue Theme Page (Server)
  - [ ] Modify `frontend/src/app/(blue)/home/page.tsx`.
  - [ ] Make `BlueHomePage` an `async` function.
  - [ ] Call `brandsService.getFeatured()` to fetch data.
  - [ ] Pass result to `<HomePage />` as `featuredBrands` prop.

- [ ] Task 4: Verify CLS & SEO
  - [ ] Ensure `BrandsBlock` container has height/width constraints (handled in 33.3, but verify container in `HomePage`).
  - [ ] Verify SSR output contains brand names/links (View Source).

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
