# Story 32.3: Frontend Carousel Logic (Hook)

Status: ready-for-dev

## Story

As a Developer,
I want a reusable carousel hook with swipe support,
so that I can easily implement the marketing banner slider and potentially refactor the Hero section later.

## Acceptance Criteria

1.  **Hook Implementation**:
    - **Given** a new custom hook `useBannerCarousel` (in `frontend/src/hooks/useBannerCarousel.ts`),
    - **When** initialized with options (loop, speed, autoplay interface),
    - **Then** it returns the necessary `ref` for the carousel container and API methods (scrollNext, scrollPrev, scrollTo).
    - **And** it integrates `embla-carousel-react` as the underlying engine.

2.  **Swipe & Interaction**:
    - **Given** the hook is attached to a DOM element,
    - **When** on a touch device,
    - **Then** swipe gestures are natively supported (1:1 finger tracking).

3.  **Autoplay Logic**:
    - **Given** the hook configuration includes `autoScroll: true` (or defined interval),
    - **When** the carousel is idle,
    - **Then** it cycles automatically.
    - **And** it pauses on user interaction (hover or touch) if configured.
    - **Note**: Use `embla-carousel-autoplay` plugin for this.

4.  **Navigation State**:
    - **Given** the hook usage,
    - **Then** it exposes reactive state for `selectedIndex` and `scrollSnaps` (for dot navigation).
    - **And** it exposes `canScrollPrev` / `canScrollNext` booleans.

5.  **Type Safety**:
    - **Then** the hook is fully typed with TypeScript.

## Tasks / Subtasks

- [ ] **Setup & Dependencies**
    - [ ] Install `embla-carousel-react` (Latest Stable: ^8.x).
    - [ ] Install `embla-carousel-autoplay`.

- [ ] **Implementation: useBannerCarousel**
    - [ ] Create `frontend/src/hooks/useBannerCarousel.ts`.
    - [ ] Implement Embla initialization with options (loop: true, align: 'center'/'start').
    - [ ] Integrate Autoplay plugin with stop-on-interaction logic.
    - [ ] Expose API: `ref`, `scrollNext`, `scrollPrev`, `selectedIndex`, `scrollSnaps`, `onDotButtonClick`.

- [ ] **Testing**
    - [ ] Create unit tests `frontend/src/hooks/__tests__/useBannerCarousel.test.ts` (using `renderHook` from `@testing-library/react`).
    - [ ] Verify initial state and basic API presence.

## Dev Notes

### Architecture & Standards
- **Library Choice**: **Embla Carousel** is chosen for its lightweight nature, hook-first API, and excellent touch support, resolving NFR2 (Performance) and NFR3 (UX).
- **Location**: `frontend/src/hooks/useBannerCarousel.ts`.
- **Styling**: The hook handles *logic*. Styling/Layout will be handled in the Component story (32.4), but the hook must support standard Embla structure (viewport > container > slide).

### Technical Constraints
- **React 19**: Ensure the library is compatible with React 19 (Embla v8+ is compatible).
- **Zustand**: Not needed for this local UI state, use standard React `useState`/`useCallback` inside the hook.
- **Strict Mode**: Ensure Embla cleanup works correctly in React Strict Mode (Next.js dev env).

### Latest Tech Information
- **Embla v8.6**:
    - Use `useEmblaCarousel` hook.
    - Autoplay is a separate plugin: `import Autoplay from 'embla-carousel-autoplay'`.
    - Options should be typed using `EmblaOptionsType`.

### References
- **Documentation**: [Embla Carousel Docs](https://www.embla-carousel.com/get-started/react/)
- **Project Structure**: `frontend/src/hooks/`
- **Epics**: `_bmad-output/planning-artifacts/epics.md`

## Dev Agent Record

### Agent Model Used
Antigravity (Google DeepMind)

### Completion Notes List
- Validated that `embla-carousel-react` is the best fit.
- Defined clear separation: Hook (Logic) vs Section (UI).
- Added specific requirement for Autoplay plugin.

### File List
- frontend/package.json
- frontend/src/hooks/useBannerCarousel.ts
- frontend/src/hooks/__tests__/useBannerCarousel.test.ts
