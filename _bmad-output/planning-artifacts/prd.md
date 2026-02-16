---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
inputDocuments:
  - project-context.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/epics.md
  - docs/project-overview.md
  - _bmad-output/planning-artifacts/refined-prd.md
  - docs/prd/requirements.md
  - docs/prd/goals-and-background-context.md
  - docs/archive/v4/Brief.md
  - docs/architecture-frontend.md
  - docs/frontend/css-variables-mapping.md
  - docs/frontend/design-system.json
  - docs/frontend/testing-standards.md
  - docs/frontend/testing-typescript-recommendations.md
workflowType: prd
documentCounts:
  briefCount: 1
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 12
classification:
  projectType: Web App Feature Enhancement
  domain: E-commerce / UX (Brand Showcase)
  complexity: Medium (Targeted UI Component)
  projectContext: Brownfield (Implement Brands Block on Blue Theme Homepage)
---

# Product Requirements Document - FREESPORT Brands Block

**Author:** Alex
**Date:** 2026-02-16

## Executive Summary

The objective of this feature is to enhance the FREESPORT homepage (Blue Theme) by adding a "Brands" section immediately below the main marketing banner. This section will feature an interactive carousel of brand logos that allows users to quickly navigate to brand-specific catalogs without using the search function. This feature also includes backend updates to allow content managers to control featured brands via the Django Admin interface.

## Success Criteria

### User Success

*   **Visibility**: User sees a clearly labeled "Brands" section with a carousel of logos immediately below the marketing banner on the homepage.
*   **Interactivity**: The carousel is interactive (scroll/swipe) and supports hover animations for feedback.
*   **Navigation**: Clicking a brand logo navigates the user to the catalog page pre-filtered by that specific brand.
*   **Aesthetics**: The design uses black logos to match the light theme aesthetic.

### Business Success

*   **Brand Exposure**: Increased visibility for key brands on the homepage.
*   **UX Improvement**: Streamlined navigation for brand-loyal customers.
*   **Content Management**: Ability to manage featured brands and their logos directly via the admin panel.

### Technical Success

*   **Frontend**: `BrandsBlock` component implemented in the `(blue)` theme with responsive design and optimized images.
*   **Backend**: `Brand` model updated with `image` and `is_featured` fields, including validation logic.
*   **Performance**: Zero layout shift (CLS) and smooth 60fps animations.

## Product Scope & Roadmap

### MVP - Minimum Viable Product (Phase 1)

**Backend (Django):**
1.  Update `Brand` model in `apps/products` with `image` (ImageField) and `is_featured` (BooleanField).
2.  Implement validation: `is_featured` requires `image`.
3.  Add "Show on Homepage" (`is_featured`) checkbox to Admin.
4.  Expose/Update API endpoint to filter brands by `is_featured=True`.

**Frontend (Next.js):**
1.  Create `BrandsBlock` component in `frontend/src/components/business/home/`.
2.  Implement Server-Side Rendering (SSR) data fetching for featured brands.
3.  Render responsive carousel with `next/image` using black logo images.
4.  Implement subtle hover animation (scale/opacity).
5.  Link logos to `/catalog?brand={slug}`.
6.  Integrate `BrandsBlock` into `src/app/(blue)/page.tsx` (or equivalent layout).

### Growth Features (Post-MVP)

*   **Phase 2**: manual drag-and-drop ordering of brands in the admin panel.
*   **Phase 3**: Support for colored logos on hover (if design requirements change).

## User Journeys

### Journey 1: The Brand-Loyal Customer (Alexey)

**Persona:** Alexey, a father looking for specific gear.
**Goal:** Quickly find products from a specific brand without using search.

1.  **Opening Scene:** Alexey lands on the FREESPORT homepage (Blue Theme). He's in a hurry.
2.  **Rising Action:** Immediately below the main marketing banner, he spots a clean row of brand logos.
3.  **Climax:** He identifies the "Boybo" logo. He hovers over it, seeing a subtle scale animation.
4.  **Resolution:** He clicks the logo and is instantly taken to the catalog page, pre-filtered for "Boybo" products.

### Journey 2: The Content Manager (Maria)

**Persona:** Maria, content manager.
**Goal:** Feature a new brand "Ingame" on the homepage for a promotion.

1.  **Opening Scene:** Maria logs into the Django Admin interface.
2.  **Rising Action:** She navigates to `Products` -> `Brands` and selects "Ingame".
3.  **Climax:** She uploads the specific black logo file to the new **Image** field and checks the **"Показать на главной странице"** box.
4.  **Resolution:** She saves the brand. She opens the homepage in a new tab and confirms "Ingame" is now visible in the carousel.
5.  **Validation:** If she attempts to save without an image, the system effectively blocks her with an error message.

## Functional Requirements

### Brand Management (Admin)

*   **FR-01**: Admin can upload an image (logo) for a `Brand` entity.
*   **FR-02**: Admin can toggle a `Show on Homepage` (`is_featured`) flag for a `Brand`.
*   **FR-03**: System must prevent enabling `Show on Homepage` if no image is uploaded for the brand.
*   **FR-04**: Admin can remove a brand from the homepage by disabling the flag.

### Brand Display (User)

*   **FR-05**: User can view a "Brands" section on the homepage (Blue Theme).
*   **FR-06**: User can view a carousel/list of brands marked as `is_featured`.
*   **FR-07**: User sees a visual hover effect (animation) when interacting with a brand logo.

### Navigation

*   **FR-08**: User can click on a brand logo.
*   **FR-09**: Clicking a logo navigates the user to the catalog page with the brand filter active (`/catalog?brand={slug}`).

### Data Availability

*   **FR-10**: System provides a public API endpoint to retrieve only `is_featured` brands.

## Non-Functional Requirements

### Performance & Optimization

*   **Image Optimization**: All brand logos must be served in next-gen formats (WebP/AVIF) via Next.js Image component and should not exceed 50KB.
*   **CLS (Cumulative Layout Shift)**: The brands block container must define explicit dimensions to prevent layout shift during loading.
*   **SSR**: The list of featured brands must be rendered on the server (SSR) to ensure immediate visibility and SEO indexability.

### Usability & Accessibility

*   **Keyboard Navigation**: The carousel component must be navigable using keyboard controls (Tab to focus, Arrows to scroll).
*   **Touch Support**: The carousel must support swipe gestures on mobile devices.
*   **Contrast**: Background and logo colors must meet WCAG AA contrast standards.

### Implementation & Maintainability

*   **Component Architecture**: `BrandsBlock.tsx` should be a Client Component (for interactivity) receiving data from a Server Component (page).
*   **API Strategy**: GET `/api/v1/products/brands/?is_featured=true` with caching enabled (e.g., 1 hour TTL).
*   **Code Standards**: Code must adhere to project TypeScript, ESLint, and Prettier configurations.
