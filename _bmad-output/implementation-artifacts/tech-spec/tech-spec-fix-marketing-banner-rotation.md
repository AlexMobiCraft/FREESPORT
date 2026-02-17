---
title: 'Fix Marketing Banner Rotation'
slug: 'fix-marketing-banner-rotation'
created: '2026-02-17T15:45:08'
status: 'completed'
stepsCompleted: [1, 2, 3, 4, 5]
tech_stack: ['Next.js', 'React 19', 'Embla Carousel', 'TypeScript']
files_to_modify: ['frontend/src/components/home/MarketingBannersSection.tsx', 'frontend/src/hooks/useBannerCarousel.ts']
code_patterns: ['Custom Hook (useBannerCarousel)', 'Service Layer (bannersService)', 'Container/Presenter']
test_patterns: ['Vitest', 'React Testing Library', 'Mocking (vi.mock)']
---

# Tech-Spec: Fix Marketing Banner Rotation

**Created:** 2026-02-17T15:45:08

## Overview

### Problem Statement

Marketing banners (located below QuickLinks) are not rotating automatically, or the rotation interval is perceived as too long (5s). Users report "no rotation at all" in some cases, suggesting a potential initialization issue with the Autoplay plugin when banners load dynamically.

### Solution

1.  Reduce rotation interval to **3000ms** (3 seconds).
2.  Strengthen `useBannerCarousel` hook to ensure Autoplay plugin is correctly initialized and started when banners are loaded dynamically.

### Scope

**In Scope:**
- `frontend/src/components/home/MarketingBannersSection.tsx`
- `frontend/src/hooks/useBannerCarousel.ts`
- Implementation of rotation fix and robustness improvements.

**Out of Scope:**
- Hero Section.
- Backend API.

## Context for Development

### Codebase Patterns

- **Component:** `MarketingBannersSection.tsx` uses `useBannerCarousel`.
- **Hook:** `useBannerCarousel.ts` wraps `useEmblaCarousel` with `embla-carousel-autoplay`.
- **State:** Banners load async. `shouldAnimate` toggles `loop` and `autoplay` options.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/components/home/MarketingBannersSection.tsx` | Main component. |
| `frontend/src/hooks/useBannerCarousel.ts` | Carousel logic hook. |
| `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx` | Tests to verify. |

### Technical Decisions

- **Interval:** 3000ms.
- **Autoplay Logic:** Add explicit `useEffect` to reset/play Autoplay when plugin is re-initialized, to handle React 19 strict mode edge cases.

## Implementation Plan

### Tasks

- [x] Task 1: Robust Autoplay Initialization
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Add a `useEffect` that listens for `autoplay` and `emblaApi`. If `autoplay` is true, check `emblaApi.plugins().autoplay`. If present, call `.play()`. This ensures that even if the plugin was added dynamically, it is explicitly started.
  - Notes: Ensure we don't conflict with `stopOnInteraction`.
  - Status: ✅ Already implemented (lines 274-281)

- [x] Task 2: Update Interval and Config
  - File: `frontend/src/components/home/MarketingBannersSection.tsx`
  - Action: Change `autoplayDelay` prop from `5000` to `3000`.
  - Action: Verify `stopOnMouseEnter` is handled correctly (default is true).
  - Status: ✅ Already implemented (line 100)

### Acceptance Criteria

- [x] AC1: Given the Marketing Banners section with >1 banners, when viewed, then the banners DO rotate automatically every 3 seconds.
- [x] AC2: Given the banners are rotating, when the user hovers over the carousel, then the rotation stops.
- [x] AC3: Given the banners are rotating, when the user interacts (swipes/clicks dots), then the rotation stops (if configured to do so) or resumes after interaction.
- [x] AC4: Given the page loads and banners fetch asynchronously, when banners appear, then rotation starts automatically without user interaction.

## Additional Context

### Dependencies

- `embla-carousel-react`: ^8.6.0
- `embla-carousel-autoplay`: ^8.6.0

### Testing Strategy

- **Manual Verification:**
    1.  Open Homepage.
    2.  Scroll to Marketing Banners.
    3.  Count 3 seconds -> Slide change.
    4.  Hover -> Stop.
    5.  Refresh page -> Immediate start (after load).
- **Unit Tests:**
    - Update `MarketingBannersSection.test.tsx` if it assertions on specific timeout values.
    - Since `useBannerCarousel` is mocked in component tests, logic changes in the hook won't be covered by component tests. We might need to verify the hook separately or trust manual verification for the hook internals.

### Notes

- React 19 Strict Mode can cause double-mount effects, which might reset Embla plugins unexpectedly. The explicit `.play()` call should mitigate this.
