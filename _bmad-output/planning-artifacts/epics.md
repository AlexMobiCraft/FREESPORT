---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
---

# FREESPORT - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for FREESPORT (Brands Block Feature), decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-01: Admin can upload an image (logo) for a `Brand` entity.
FR-02: Admin can toggle a `Show on Homepage` (`is_featured`) flag for a `Brand`.
FR-03: System must prevent enabling `Show on Homepage` if no image is uploaded for the brand.
FR-04: Admin can remove a brand from the homepage by disabling the flag.
FR-05: User can view a "Brands" section on the homepage (Blue Theme).
FR-06: User can view a carousel/list of brands marked as `is_featured`.
FR-07: User sees a visual hover effect (animation) when interacting with a brand logo.
FR-08: User can click on a brand logo.
FR-09: Clicking a logo navigates the user to the catalog page with the brand filter active (`/catalog?brand={slug}`).
FR-10: System provides a public API endpoint to retrieve only `is_featured` brands.

### NonFunctional Requirements

NFR-01: **Image Optimization**: All brand logos must be served in next-gen formats (WebP/AVIF) via Next.js Image component and should not exceed 50KB.
NFR-02: **CLS (Cumulative Layout Shift)**: The brands block container must define explicit dimensions to prevent layout shift during loading.
NFR-03: **SSR**: The list of featured brands must be rendered on the server (SSR) to ensure immediate visibility and SEO indexability.
NFR-04: **Keyboard Navigation**: The carousel component must be navigable using keyboard controls (Tab to focus, Arrows to scroll).
NFR-05: **Touch Support**: The carousel must support swipe gestures on mobile devices.
NFR-06: **Contrast**: Background and logo colors must meet WCAG AA contrast standards.
NFR-07: **Code Standards**: Code must adhere to project TypeScript, ESLint, and Prettier configurations.
NFR-08: **Isolation**: The `BrandsBlock` must be a self-contained component with minimal external dependencies.

### Additional Requirements

- **Backend**: Update `Brand` model in `apps/products` (Brownfield context).
- **Backend**: API payloads must use `snake_case`.
- **Frontend**: Component architecture: `BrandsBlock` (Client) receiving data from Page (Server).
- **Frontend**: Use `next/image` with `object-contain`.
- **Architecture**: Follow "Service Layer" pattern if complex validation logic is needed (though validation here is simple).
- **Integration**: Use `GET /api/v1/products/brands/?is_featured=true` with caching strategy (1h TTL).

### FR Coverage Map

FR-01: Epic 1 - Admin can manage brand images
FR-02: Epic 1 - Admin can toggle featured status
FR-03: Epic 1 - System validates image presence
FR-04: Epic 1 - Admin can remove featured status
FR-05: Epic 1 - User sees brands section
FR-06: Epic 1 - User sees featured brands
FR-07: Epic 1 - User sees hover effects
FR-08: Epic 1 - User can click brand logo
FR-09: Epic 1 - User navigates to catalog
FR-10: Epic 1 - API provides featured brands

## Epic List

### Epic 33: Brands Block Implementation
Enable users to quickly navigate to popular brand catalogs from the homepage and allow admins to manage this content.
**FRs covered:** FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10.
**NFRs covered:** NFR-1 to NFR-8.

## Epic 133: Brands Block Implementation
**Goal:** Enable users to quickly navigate to popular brand catalogs from the homepage and allow admins to manage this content.

### Story 33.1: Brand Model & Admin Updates

As an Admin,
I want to upload brand logos and mark brands as featured on the homepage,
So that I can highlight key partners and improve navigation.

**Acceptance Criteria:**

**Given** the existing `Brand` model in `apps/products/models.py`,
**When** the model is updated,
**Then** it includes an `image` field (ImageField) and `is_featured` field (BooleanField, default=False).

**Given** the Django Admin interface for Brands,
**When** creating or editing a brand,
**Then** I can upload a logo image and check "Show on Homepage".

**Given** I check "Show on Homepage" but do not upload an image,
**When** I try to save,
**Then** the system prevents saving and shows a validation error: "Image is required for featured brands" (FR-03).

**Given** the Brand list in Admin,
**When** viewed,
**Then** I can see which brands are featured.

### Story 33.2: API Featured Brands Endpoint

As a Frontend Developer,
I want to fetch a list of featured brands via API,
So that I can display them on the homepage.

**Acceptance Criteria:**

**Given** unauthenticated users,
**When** they request `GET /api/v1/products/brands/?is_featured=true`,
**Then** the API returns a JSON list of brands where `is_featured=True`.
**And** the response includes fields: `id`, `name`, `slug`, `image` (URL).

**Given** the API response,
**When** serialized,
**Then** field names are in `snake_case` (e.g. `is_featured`, `company_name` if applicable).

**Given** the endpoint configuration,
**Then** responses are cached for 1 hour to reduce DB load (NFR-Integration).

### Story 33.3: BrandsBlock Component Logic & UI

As a User,
I want to see a carousel of brand logos on the homepage,
So that I can quickly access my favorite brands.

**Acceptance Criteria:**

**Given** the `BrandsBlock` component in `frontend/src/components/business/home/`,
**When** it receives a list of brands as props from the Server Component (SSR),
**Then** it renders a horizontal list/carousel of logos.

**Given** the component is rendered,
**When** viewed on different screen sizes,
**Then** it adapts responsively (e.g., swiper/scrollable on mobile).

**Given** brand logos,
**When** rendered,
**Then** they use `next/image` with `object-contain` style to handle varying aspect ratios (NFR-01).

**Given** a user hovers over a logo,
**When** using a mouse,
**Then** a subtle scale/opacity animation occurs (FR-07).

**Given** a user clicks a logo,
**When** clicked,
**Then** they are navigated to `/catalog?brand={slug}` (FR-09).

### Story 33.4: Integration into Homepage

As a User,
I want to see the brands block in the correct location on the homepage,
So that I can easily find it.

**Acceptance Criteria:**

**Given** the Blue Theme homepage (`src/app/(blue)/page.tsx`),
**When** the page renders,
**Then** it fetches the featured brands on the server side (SSR).

**Given** the fetched data,
**When** passed to `BrandsBlock`,
**Then** the block appears immediately below the main marketing banner section.

**Given** the page load process,
**Then** the brands block has explicit dimensions to prevent Layout Shift (CLS) during hydration (NFR-02).
