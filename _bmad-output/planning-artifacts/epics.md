---
stepsCompleted:
  - step-01-validate-prerequisites
inputDocuments:
  - _bmad-output/implementation-artifacts/marketing-banners-story.md
  - _bmad-output/planning-artifacts/refined-prd.md
---

# FREESPORT - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for FREESPORT, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Admin interface must allow creating banners with a distinct 'Marketing' type.
FR2: Admin interface must allow filtering banners list by type (Hero vs Marketing).
FR3: API endpoint `/api/banners/` must support `type` query parameter.
FR4: API must return only Marketing banners when `type=marketing` is requested.
FR5: API must return only Hero banners when `type=hero` is requested.
FR6: API must default to returning Hero banners if no type is specified (backward compatibility).
FR7: All existing banners in the database must be migrated to type 'Hero', and the `type` field must be set to **non-nullable**.
FR8: Frontend must display a new "Marketing Banners" section on the Home page, located below "Quick Links".
FR9: Marketing Banners section must implement auto-scrolling carousel behavior.
FR10: Marketing Banners section must be hidden if no active marketing banners are returned.
FR11: Frontend must support swipe gestures for carousel on mobile devices.
FR12: API must limit the number of active marketing banners returned (max 5) to prevent over-loading.
FR13: Admin Interface must enforce that the 'Image' field is mandatory when 'Marketing' type is selected.

### NonFunctional Requirements

NFR1: **Backward Compatibility**: Existing Hero section integration must remain functional without modification to consumer code (default API behavior).
NFR2: **Performance**: Carousel logic must be optimized (reusable hook) to avoid unnecessary re-renders.
NFR3: **UX**: Design must align with the existing Design System (fonts, spacing, carousel behavior).
NFR4: **Performance**: Images must be optimized using `Next/Image` with WebP support to ensure fast LCP.
NFR5: **UX**: Layout Stability (CLS) must be protected using Skeleton loading or fixed aspect ratio containers.
NFR6: **Reliability**: Frontend section must be wrapped in an Error Boundary to prevent page crashes on component failure.
NFR7: **Data Integrity**: The `type` field must be mandatory at the database level to prevent invalid states.
NFR8: **UX**: Images must handle loading errors gracefully (hide slide or show placeholder).
NFR9: **Performance/Admin**: Banner API response must be cached using explicit keys (e.g., `banners:list:{type}`), and invalidated immediately upon changes in Admin.

### Additional Requirements

- **Backend**: Extend `Banner` model with `type` field (choices: HERO, MARKETING). **Database migration must set default=HERO**.
- **Backend**: Update `ActiveBannersView` to handle filtering logic.
- **Frontend**: Extract carousel logic into `useBannerCarousel` custom hook for reusability.
- **Frontend**: Create `MarketingBannersSection` component using the new hook. **Implementation must use a proven library (e.g., Embla/Swiper)**.
- **Architecture**: Follow standard "Service Layer" pattern if complex logic arises.

### FR Coverage Map

FR1: Epic 32 - Admin: Create Marketing banners
FR2: Epic 32 - Admin: Filter banners
FR3: Epic 32 - API: Type parameter
FR4: Epic 32 - API: Marketing filter
FR5: Epic 32 - API: Hero filter
FR6: Epic 32 - API: Default behavior
FR7: Epic 32 - Data: Migration
FR8: Epic 32 - Frontend: New section
FR9: Epic 32 - Frontend: Auto-scroll
FR10: Epic 32 - Frontend: Hide if empty
FR11: Epic 32 - Frontend: Mobile swipe
FR12: Epic 32 - API: Limit active banners
FR13: Epic 32 - Admin: Mandatory image

## Epic List

### Epic 32: Управление маркетинговыми баннерами

Маркетологи могут управлять дополнительными рекламными баннерами для продвижения акций, а пользователи видят их в удобном формате карусели на главной странице (с поддержкой мобильных устройств и быстрой загрузкой).

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13
**NFRs covered:** NFR1, NFR2, NFR3, NFR4, NFR5, NFR6, NFR7, NFR8, NFR9

### Story 32.1: Database and Admin Updates

As an Admin,
I want to create banners with a specific 'Marketing' type and mandatory image,
So that I can manage promotional content separately from Hero banners.

**Acceptance Criteria:**

**Given** the existing `Banner` model,
**When** a database migration is executed,
**Then** a `type` field is added with choices (HERO, MARKETING), default set to HERO for existing records.
**And** the `type` field is made non-nullable at the database level (NFR7).

**Given** the Django Admin interface for Banners,
**When** creating or editing a banner,
**Then** a selector for 'Type' is available.
**And** if 'Marketing' type is selected, the 'Image' field becomes mandatory (FR13).
**And** if 'Marketing' type is selected, a 'Target URL' field is available.

**Given** the Banner list view in Admin,
**When** viewing the list,
**Then** a filter by 'Type' is available in the sidebar (FR2).

**Given** the caching mechanism,
**When** a banner is saved or deleted in Admin,
**Then** the API cache for that banner type (`banners:list:{type}`) is invalidated immediately (NFR9).

### Story 32.2: API Implementation for Marketing Banners

As a Frontend Developer,
I want to fetch marketing banners via API with filtering and limits,
So that I can display the correct content on the homepage without over-fetching.

**Acceptance Criteria:**

**Given** the `/api/banners/` endpoint,
**When** a GET request is made with `?type=marketing`,
**Then** only active banners with type='Marketing' are returned.
**And** the results are limited to the 5 most recent active banners (FR12).

**When** a GET request is made with `?type=hero`,
**Then** only active banners with type='Hero' are returned.

**When** a GET request is made without a `type` parameter,
**Then** active banners with type='Hero' are returned (Backward Compatibility - NFR1).

**Given** the API response,
**When** requested,
**Then** the response headers or behavior indicate that the result is cached using the key `banners:list:{type}`.

### Story 32.3: Frontend Carousel Logic (Hook)

As a Developer,
I want a reusable carousel hook with swipe support,
So that I can easily implement the marketing banner slider and potentially refactor the Hero section later.

**Acceptance Criteria:**

**Given** a new custom hook `useBannerCarousel`,
**When** initialized with a list of items and options,
**Then** it provides state and refs for a carousel library implementation (e.g., Embla Carousel or Swiper).

**Given** the carousel implementation,
**When** viewed on a mobile device,
**Then** swipe gestures (touch events) are supported for navigating slides (FR11).

**Given** the carousel configuration,
**When** `autoScroll` is enabled,
**Then** the slides cycle automatically after a set interval.
**And** the auto-scrolling pauses on user interaction (hover/touch).

**Given** the component structure,
**Then** the logic is isolated from the UI rendering, allowing it to be reused in other sections.

### Story 32.4: Marketing Banners UI Section

As a User,
I want to see a carousel of marketing offers below Quick Links,
So that I can learn about current promotions without them interfering with the main Hero banner.

**Acceptance Criteria:**

**Given** the Homepage structure,
**When** the page renders,
**Then** a new `MarketingBannersSection` is displayed immediately below the "Quick Links" section (FR8).

**Given** the Marketing Banners section,
**When** the API returns no active marketing banners,
**Then** the section is explicitly hidden (renders nothing) (FR10).

**Given** the section is displayed,
**When** an image is loading,
**Then** a Skeleton loader or fixed aspect-ratio container prevents Layout Shift (CLS) (NFR5).
**And** the image is rendered using `Next/Image` with `quality` and `format` optimization (NFR4).

**Given** a banner image fails to load (404/Error),
**When** the error occurs,
**Then** that specific slide is hidden or replaced with a placeholder (NFR8).

**Given** a critical render error in the component,
**When** the component crashes,
**Then** an Error Boundary catches it and hides the section instead of crashing the entire page (NFR6).

**Given** a marketing banner,
**When** clicked,
**Then** the user is navigated to the configured `target_url`.
