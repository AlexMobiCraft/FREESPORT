---
title: 'Fix Marketing Banner Rotation - Issues Resolution'
slug: 'fix-marketing-banner-rotation-issues'
created: '2026-02-17T16:18:00'
status: 'completed'
stepsCompleted: ['implementation', 'testing', 'documentation']
tech_stack: ['Next.js', 'React 19', 'Embla Carousel', 'TypeScript']
files_to_modify: ['frontend/src/hooks/useBannerCarousel.ts', 'frontend/src/components/home/MarketingBannersSection.tsx']
code_patterns: ['Custom Hook (useBannerCarousel)', 'Service Layer (bannersService)', 'Container/Presenter']
test_patterns: ['Vitest', 'React Testing Library', 'Mocking (vi.mock)']
---

# Tech-Spec: Fix Marketing Banner Rotation - Issues Resolution

**Created:** 2026-02-17T16:18:00

## Overview

### Problem Statement

Adversarial code review identified 12 issues in the marketing banner rotation implementation that need to be addressed for production readiness.

### Solution

Address all identified issues ranging from critical error handling to code quality improvements.

### Scope

**In Scope:**
- `frontend/src/hooks/useBannerCarousel.ts` - Critical fixes for autoplay logic
- `frontend/src/components/home/MarketingBannersSection.tsx` - Configuration improvements
- Tests for new functionality
- Documentation updates

**Out of Scope:**
- Hero Section.
- Backend API.

## Context for Development

### Issues from Adversarial Review

**Critical Issues:**
1. **Error Handling:** No error handling when accessing `emblaApi.plugins().autoplay`
2. **Race Conditions:** useEffect for autoplay may have race conditions

**High Priority Issues:**
3. **Hardcoded Values:** 3000ms is hardcoded instead of configurable
4. **Missing Tests:** New useEffect logic is not covered by tests
5. **Performance Issues:** useEffect fires on every emblaApi change

**Medium Priority Issues:**
6. **Logic Duplication:** Multiple useEffect instances
7. **Incomplete Implementation:** Only play() called, no stop/pause handling
8. **Missing Documentation:** New useEffect not documented

**Low Priority Issues:**
9. **Style Changes:** Unnecessary formatting changes in diff
10. **Method Validation:** No validation that play() method exists
11. **Memory Leaks:** Potential leaks when emblaApi is destroyed
12. **UX Justification:** 3000ms value lacks UX research backing

## Implementation Plan

### Tasks

- [x] Task 1: Add Error Handling for Autoplay Plugin
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Wrap autoplay plugin access in try-catch
  - Add null checks before calling methods
  - Priority: Critical

- [x] Task 2: Fix Race Conditions in useEffect
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Add proper dependency management
  - Use useCallback for stable references
  - Priority: Critical

- [x] Task 3: Make Autoplay Delay Configurable
  - File: `frontend/src/components/home/MarketingBannersSection.tsx`
  - Action: Extract 3000ms to a constant or configuration
  - Add fallback to default value
  - Priority: High

- [x] Task 4: Add Tests for Autoplay Logic
  - File: `frontend/src/hooks/__tests__/useBannerCarousel.test.ts`
  - Action: Create unit tests for new useEffect
  - Test autoplay plugin interaction
  - Priority: High

- [x] Task 5: Optimize useEffect Performance
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Reduce unnecessary re-renders
  - Optimize dependency array
  - Priority: High

- [x] Task 6: Consolidate useEffect Logic
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Merge related useEffect instances where possible
  - Reduce duplication
  - Priority: Medium

- [x] Task 7: Complete Autoplay Control Implementation
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Add stop() and pause() methods
  - Implement full autoplay lifecycle
  - Priority: Medium

- [x] Task 8: Update Documentation
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Add JSDoc for new useEffect
  - Document autoplay behavior
  - Priority: Medium

- [x] Task 9: Clean Up Style Changes
  - File: `frontend/src/components/home/MarketingBannersSection.tsx`
  - Action: Remove unnecessary formatting changes
  - Keep only functional changes
  - Priority: Low

- [x] Task 10: Add Method Validation
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Validate play() method exists before calling
  - Add type guards
  - Priority: Low

- [x] Task 11: Prevent Memory Leaks
  - File: `frontend/src/hooks/useBannerCarousel.ts`
  - Action: Add cleanup in useEffect
  - Handle emblaApi destruction
  - Priority: Low

- [x] Task 12: Document UX Decision
  - File: `frontend/src/components/home/MarketingBannersSection.tsx`
  - Action: Add comment explaining 3000ms choice
  - Reference user experience requirements
  - Priority: Low

### Acceptance Criteria

- [x] AC1: Given autoplay plugin is unavailable, when useEffect runs, then no errors are thrown
- [x] AC2: Given rapid emblaApi changes, when useEffect triggers, then no race conditions occur
- [x] AC3: Given configuration needs change, when delay is modified, then it's easily configurable
- [x] AC4: Given new autoplay logic, when tests run, then all edge cases are covered
- [x] AC5: Given performance monitoring, when component renders, then unnecessary re-renders are minimized
- [x] AC6: Given code review, when useEffect logic is examined, then it's consolidated and clean
- [x] AC7: Given autoplay control, when user interacts, then full play/pause/stop lifecycle works
- [x] AC8: Given documentation review, when hook is used, then all behavior is documented
- [x] AC9: Given git diff, when changes are reviewed, then only functional changes are present
- [x] AC10: Given plugin interaction, when methods are called, then they exist and are valid
- [x] AC11: Given memory profiling, when component unmounts, then no memory leaks occur
- [x] AC12: Given UX review, when delay value is questioned, then justification is documented

## Additional Context

### Dependencies

- `embla-carousel-react`: ^8.6.0
- `embla-carousel-autoplay`: ^8.6.0

### Testing Strategy

- **Unit Tests:** Create comprehensive tests for useBannerCarousel hook
- **Integration Tests:** Verify autoplay behavior with mock Embla API
- **Error Scenario Tests:** Test error handling paths
- **Performance Tests:** Verify no unnecessary re-renders

### Implementation Notes

- Maintain backward compatibility
- Follow existing code patterns
- Use TypeScript strict mode
- Add proper error boundaries
- Document all public APIs

### Risk Mitigation

- **Breaking Changes:** Ensure API compatibility
- **Performance:** Monitor render cycles
- **Error Handling:** Comprehensive try-catch blocks
- **Testing:** Full coverage before merge

## Success Metrics

- All 12 issues addressed
- 100% test coverage for new code
- No performance regressions
- Zero error scenarios unhandled
- Complete documentation
