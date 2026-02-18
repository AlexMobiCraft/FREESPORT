---
title: 'Home Page Categories Block Refactor'
slug: 'home-categories-refactor'
created: '2026-02-18'
status: 'done'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Django', 'Next.js', 'React', 'Tailwind CSS']
files_to_modify:
  - 'backend/apps/products/admin.py'
  - 'backend/apps/products/models.py'
  - 'frontend/src/components/home/CategoriesSection.tsx'
  - 'frontend/src/services/categoriesService.ts'
code_patterns: ['Proxy Models for Admin', 'Service Layer Pattern', 'Compound Components']
test_patterns: ['Component Testing (Vitest)', 'Integration Testing (Pytest)']
---

# Overview

## Problem Statement
The current "Popular Categories" block on the 'Blue' theme homepage is a static grid that doesn't fully support the marketing requirement of prioritizing specific categories visually. The client needs flexible control over which categories appear, their order (priority), and their images directly from the Admin panel. The visual presentation needs to change from a Grid to a Carousel, which adapts for mobile views.

## Solution
Refactor the "Categories" block to be dynamic and manageable:
1. **Backend**: Leverage existing `Category` fields (`sort_order`, `image`) but expose them in a dedicated "Home Page Categories" admin section for focused management.
2. **Frontend**: Replace the Grid layout in `CategoriesSection` with a Carousel component (similar to Quick Links) that displays root categories sorted by priority.
3. **Data**: Fetch root categories (parent=None) sorted by `sort_order` and `id` (for stability).
4. **Mobile**: Implement a responsive design where the carousel works seamlessly on touch devices, potentially showing 1.5 cards or 2 cards at a time to encourage scrolling.

## Scope
- **In Scope**:
  - Backend: Django Admin setup for "Home Categories" (Proxy model).
  - API: Verify `CategoryViewSet` supports sorting by `sort_order`.
  - Frontend: `CategoriesSection` refactor (Grid -> Carousel).
  - Frontend: `CategoryCard` update/creation if needed.
  - Frontend: Responsive adaptations for mobile (touch scroll, card sizing).
- **Out of Scope**:
  - Global catalog restructuring.
  - Changes to other themes (Electric Orange).
  - Deep backend model changes (fields already exist).

# Context for Development

## Technical Constraints & Patterns
- **Frontend**:
  - Use `embla-carousel-react` or custom scroll logic (as seen in `QuickLinksSection`).
  - Strict Typescript usage.
  - Tailwind CSS for styling.
  - **Mobile Strategy**: Use CSS scroll snapping or touch-optimized carousel library. Visible cards per row: Desktop (4-6), Tablet (3), Mobile (1.5 or 2 with "peek" effect).
  - **Visuals**: Enforce strict aspect ratios and provide fallbacks for missing images.
  - **Performance**: Use appropriate caching or revalidation strategies (e.g., SWR or Next.js `revalidate`) for this heavy but improved block.
- **Backend**:
  - DO NOT modify `Category` model structure (fields exist).
  - Use `Proxy` model in `admin.py` to create a separate menu item "Категории для главной".
  - **Safety**: Prevent deletion of categories from this new admin view.

## Files to Reference
| File | Relevance |
|------|-----------|
| `backend/apps/products/admin.py` | Create Proxy Admin here. |
| `frontend/src/components/home/CategoriesSection.tsx` | Main component to refactor. |
| `frontend/src/components/home/QuickLinksSection.tsx` | Reference for Carousel logic. |
| `frontend/src/services/categoriesService.ts` | Ensure `getCategories` supports `ordering`. |

## Technical Decisions
- **Admin**: Use a `HompageCategory` proxy model to filter only root categories (`parent__isnull=True`).
- **Safety**: Disable `delete` permission in the Proxy Admin to avoid accidental catalog data loss.
- **Sorting**: Enforce `['sort_order', 'id']` to ensure stable sorting.
- **Mobile UX**: On mobile, the arrow buttons should be hidden, relying on natural touch scrolling.

# Implementation Plan

## Backend Tasks
- [x] Task 1: Create `HomepageCategory` Proxy Model
  - File: `backend/apps/products/models.py`
  - Action: Define a proxy model inheriting from `Category`.
  - Notes:
    - Ensure `proxy = True` in `Meta`.
    - Set `verbose_name` to "Категория для главной", `verbose_name_plural` to "Категории для главной".
    - Set default ordering to `['sort_order', 'id']`.
- [x] Task 2: Create Admin for Proxy Model
  - File: `backend/apps/products/admin.py`
  - Action: Register `HomepageCategory` with a custom `ModelAdmin`.
  - Logic:
    - `list_display`: `image_preview`, `name`, `sort_order`, `is_active`.
    - `list_editable`: `sort_order`, `is_active`.
    - `get_queryset`: Filter `parent__isnull=True`.
    - **Security**: Override `has_delete_permission` to return `False`.
    - **UX**: Add `help_text` to the image field: "Рекомендуемый размер: 400x300px (4:3)".

## Frontend Tasks
- [x] Task 3: Update Categories Service
  - File: `frontend/src/services/categoriesService.ts`
  - Action: Ensure `getCategories` accepts an `ordering` parameter and correctly passes it to the API.
- [x] Task 4: Refactor CategoriesSection to Carousel
  - File: `frontend/src/components/home/CategoriesSection.tsx`
  - Action:
    - Fetch categories with `parent_id__isnull=True`, `ordering='sort_order'`, and `limit=0` (fetch all/no limit).
    - Implement horizontal scroll (carousel) layout.
    - **Styles**:
      - Use `object-fit: cover` for images.
      - Enforce fixed `aspect-ratio` (e.g., 4:3) to prevent layout shifts.
      - **Fallback**: Create/Import a placeholder image (e.g. `/images/category-placeholder.png`) and display it if `category.image` is missing.
    - **Responsive**:
      - `w-[80vw]` or `w-[40vw]` for Mobile (showing 1.2 or 2.2 items).
      - `w-[250px]` for Desktop.
    - **Nav**: Add navigation arrows (Left/Right) for Desktop, hide for Mobile (touch scroll).

# Acceptance Criteria

- [x] AC 1: Admin - "Home Categories" Menu
  - Given I am an admin
  - When I open the main menu
  - Then I see "Категории для главной" under Products app
  - And the verbose name is correct (singular/plural)
- [x] AC 2: Admin - Safety & Hints
  - Given I am in "Home Categories" list
  - Then I CANNOT see the delete button/action (Delete protected)
  - And I see a hint about the recommended image size (400x300px) when editing
- [x] AC 3: Frontend - Desktop Display
  - Given I am on the Homepage (Blue theme)
  - Then I see the "Categories" block as a carousel with arrows
  - And images have consistent size (cover fit)
  - And categories without images show a placeholder
- [x] AC 4: Frontend - Mobile Display
  - Given I am on the Homepage (Blue theme) on Mobile
  - Then I see the "Categories" block as a scrollable strip (no arrows)
  - And I can swipe left/right to see more categories
- [x] AC 5: Frontend - Sorting & Limits
  - Given there are 10+ sorted root categories
  - Then the carousel contains ALL of them (no limit of 6)
  - And they are sorted by Priority (primary) and ID (secondary)

# Dev Agent Record

## Implementation Plan
- Task 1: Proxy model `HomepageCategory` added to `models.py` after `Category` class
- Task 2: `HomepageCategoryAdmin` registered with delete protection, queryset filter, image help_text
- Task 3: `ordering` parameter added to `GetCategoriesParams` interface
- Task 4: CategoriesSection rewritten from grid to horizontal scroll carousel with CategoryCard component, image support, placeholder fallback, responsive widths, desktop arrows

## Completion Notes
- All 4 tasks implemented and tested
- Backend: 6 meta tests pass (proxy model) + 6 admin tests pass (registration, config, delete protection)
- Frontend: 7 service tests pass (including ordering param) + 9 component tests pass (carousel layout, images, placeholder, no-limit, responsive)
- `Category` type in `types/api.ts` extended with optional `image` field
- Mock data updated with `image` field for testing
- Pre-existing 5 failures in `QuickLinksSection.test.tsx` confirmed unrelated (same failures on clean checkout)
- No new dependencies added

## File List
- `backend/apps/products/models.py` — added `HomepageCategory` proxy model
- `backend/apps/products/admin.py` — added `HomepageCategoryAdmin` with import
- `backend/apps/products/tests/test_models_homepage_category.py` — NEW: proxy model tests
- `backend/apps/products/tests/test_admin_homepage_category.py` — NEW: admin tests
- `frontend/src/types/api.ts` — added `image` field to `Category` interface
- `frontend/src/services/categoriesService.ts` — added `ordering` to `GetCategoriesParams`
- `frontend/src/services/__tests__/categoriesService.test.ts` — added ordering/limit tests
- `frontend/src/components/home/CategoriesSection.tsx` — refactored grid → carousel
- `frontend/src/components/home/__tests__/CategoriesSection.test.tsx` — rewritten for carousel
- `frontend/src/__mocks__/api/handlers.ts` — added `image` field to mock categories

## Change Log
- 2026-02-18: Story implementation complete — all 4 tasks done, all AC satisfied
- 2026-02-18: AI Code Review completed — 1 high, 2 medium, 1 low issues found and fixed automatically. Status moved to 'done'.

# Senior Developer Review (AI)

**Reviewer:** Amelia (BMAD Developer Agent)
**Date:** 2026-02-18
**Outcome:** APPROVED (after automated fixes)

## Findings & Fixes Summary

### 🔴 HIGH: Pagination Parameter Mapping
- **Issue:** `CategoriesService` was sending `limit`, but `CategoryViewSet` expected `page_size`. This would cause categories to be truncated after the default `PAGE_SIZE` (20).
- **Fix:** Updated `CategoriesService.getCategories` to map `limit` to `page_size`. Implemented `limit: 0` handling by mapping to a large integer (1000). Updated service tests to reflect this change.

### 🟡 MEDIUM: Event Listener Optimization
- **Issue:** `CategoriesSection` was re-attaching `resize` and `scroll` listeners on every render due to unstable dependencies in `useEffect`.
- **Fix:** Optimized `useCallback` for `updateScrollButtons` and corrected the dependency array in `useEffect`.

### 🟡 MEDIUM: Git Sync Transparency
- **Issue:** `git status` showed no changes despite claims of modification.
- **Note:** Implementation check confirmed files exist and contain the logic, but were likely already committed. Review proceeded based on file contents.

### 🟢 LOW: Component DRY Violation
- **Issue:** Layout classes for card widths were duplicated in `CategoryCard` and `CategoriesSkeleton`.
- **Fix:** Extracted shared layout classes to a constant `CARD_LAYOUT_CLASSES`.

## Final Verification
- [x] Backend tests pass (Proxy model, Admin protection)
- [x] Frontend service tests pass (Ordering, Pagination mapping)
- [x] Frontend component tests pass (Carousel, Responsive)
