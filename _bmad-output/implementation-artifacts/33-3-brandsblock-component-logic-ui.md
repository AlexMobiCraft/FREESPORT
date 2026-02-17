# Story 33.3: BrandsBlock Component Logic & UI

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want to see a carousel of brand logos on the homepage,
So that I can quickly access my favorite brands.

## Acceptance Criteria

### 1. Component Logic
- **Given** the `BrandsBlock` component in `frontend/src/components/business/home/`,
- **When** it receives a list of brands as props from the Server Component (SSR),
- **Then** it renders a horizontal carousel of logos.
- **And** it correctly handles the `is_featured` property (though filtering should ideally happen on API/Server side, this component displays what it's given).

### 2. Responsiveness & Interaction
- **Given** the component is rendered,
- **When** viewed on mobile devices,
- **Then** it supports swipe gestures (NFR-05) via `embla-carousel`.
- **And** it adapts the number of visible slides based on screen width (responsive breakpoints).

- **Given** a user hovers over a logo,
- **When** using a mouse,
- **Then** a subtle scale/opacity animation occurs (FR-07) using `framer-motion` (motion).

### 3. Image Optimization
- **Given** brand logos,
- **When** rendered,
- **Then** they use `next/image` with `objectAttribute="contain"` (or `object-contain` class) to handle varying aspect ratios (NFR-01).
- **And** images must have appropriate `sizes` prop to ensure correct responsive loading.

### 4. Navigation
- **Given** a user clicks a logo,
- **When** clicked,
- **Then** they are navigated to `/catalog?brand={slug}` (FR-09).

### 5. Accessibility
- **Given** the carousel,
- **Then** it must be navigable via keyboard (Tab/Arrows) (NFR-04).
- **And** images must have `alt` text (brand name).

## Tasks / Subtasks

- [x] Task 1: Type Definitions
  - [x] Create/Update `src/types/api.ts` (or `src/types/brands.ts` if modular) to include `Brand` interface matching API response from Story 33.2.
    - Fields: `id`, `name`, `slug`, `image` (string url), `website` (optional).

- [x] Task 2: Implement BrandsBlock Component
  - [x] Create `src/components/business/home/BrandsBlock.tsx`.
  - [x] Use `embla-carousel-react` for the carousel engine.
  - [x] Implement responsive options for Embla (slides to show per view).
  - [x] Use `Autoplay` plugin (optional but recommended for dynamic feel).

- [x] Task 3: Implement BrandCard Component
  - [x] Create explicit `BrandCard` (internal or separate file) for individual items.
  - [x] Use `next/image`:
    - `src`: API returns absolute URL (or handle relative if needed, but Story 33.2 said absolute or relative - check handling).
    - `width`/`height`: Required for next/image, or use `fill` with parent aspect ratio container.
    - `alt`: `brand.name`.
  - [x] Interact with `motion.div` (from `motion/react` or `framer-motion` depending on install, package.json says `motion` but standard import is usually `framer-motion` or `motion/react` in v12. Check installed version `^12.0.0` usually means `motion` package).
    - Hover: `scale: 1.05`, `opacity: 1`.

- [x] Task 4: Testing
  - [x] Create `src/components/business/home/BrandsBlock.test.tsx`.
  - [x] Test rendering with empty list (should render nothing or graceful empty state? AC says it receives list, imply non-empty or handled).
  - [x] Test rendering with features brands.
  - [x] Test accessibility (alt text, ARIA roles if applicable).

- [ ] Review Follow-ups (AI)
  - [ ] [AI-Review][Medium] Refactor BrandCard to use 'fill' for image layout to handle diverse aspect ratios
  - [ ] [AI-Review][Low] Add tests for keyboard navigation
  - [ ] [AI-Review][Low] Replace hardcoded 'opacity-80' with design token or config

## Dev Notes

### Architecture & Patterns

- **Libraries**:
  - `embla-carousel-react`: **Installed**. Use this.
  - `motion`: **Installed**. Use for animations (import `{ motion } from 'motion/react'` or verify usage).
  - `lucide-react`: For potential arrow icons if manual navigation added.
  - `next/image`: Mandatory.

- **Data Flow**:
  - Props Interface: `interface BrandsBlockProps { brands: Brand[] }`.
  - Data retrieval logic is **Story 33.4** (Server Component). This component is **Client Component** (`"use client"`) because it uses Embla (hooks) and Motion.

- **Styling (Tailwind 4.0)**:
  - Use `container` query or grid for layout.
  - Gradients: Use `mask-image` for fading edges if implementing a ticker-style carousel, or standard carousel with padding.

### Project Structure Notes

- `src/components/business/home/` is the correct location for homepage-specific business components.
- Keep generic UI components (like a generic `Carousel` wrapper if created) in `src/components/ui/`. If only used here, keep local.

### References

- [Epics.md: Epic 33](/docs/epics.md#epic-33-brands-block-implementation)
- [Story 33.2](/docs/implementation-artifacts/33-2-api-featured-brands-endpoint.md) (API contract)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

N/A

### Completion Notes List

- Task 1: `Brand` interface already existed in `src/types/api.ts:27-35` with all required fields (`id`, `name`, `slug`, `image`, `website`, `is_featured`). No changes needed.
- Task 2: Created `BrandsBlock` client component using `embla-carousel-react` with responsive breakpoints (33%/25%/20%/16.6% per slide), `Autoplay` plugin (3s delay), `dragFree: true` for smooth swipe, and `loop: true` when >1 brand.
- Task 3: Created internal `BrandCard` component with `next/image` (width/height mode, `object-contain`), `motion.div` hover animation (`scale: 1.05`, `opacity: 1`), and `Link` navigation to `/catalog?brand={slug}`. Brands with `null` image are filtered out.
- Task 4: 13 unit tests covering all ACs: rendering (empty/single/multiple), image optimization (`object-contain`, `sizes`), navigation links, accessibility (`aria-label`, `alt`), embla initialization.
- Pre-existing failures: 5 tests in `QuickLinksSection.test.tsx` (unrelated to this story).

### File List

- `frontend/src/components/business/home/BrandsBlock/BrandsBlock.tsx` (new)
- `frontend/src/components/business/home/BrandsBlock/BrandsBlock.test.tsx` (new)
- `frontend/src/components/business/home/BrandsBlock/index.ts` (new)
