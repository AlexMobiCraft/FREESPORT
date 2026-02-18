---
title: 'Fix Home Categories Level'
slug: 'fix-home-categories-level'
created: '2026-02-18'
status: 'implementation_complete'
tech_stack: ['Django', 'Next.js']
files_to_modify:
  - 'backend/apps/products/admin.py'
  - 'backend/apps/products/filters.py'
  - 'frontend/src/services/categoriesService.ts'
  - 'frontend/src/components/home/CategoriesSection.tsx'
---

# Fix Home Page Categories Level

## Problem
The "Home Page Categories" functionality is currently restricted to **root categories only** (Level 1).
However, the requirement is to display specific **Level 2** categories (e.g., "Pools", "Martial Arts", "Kids Transport") on the homepage, not just their generic parents ("SPORT").

## Solution
1.  **Admin Panel**: Unlock `HomepageCategory` admin to show ALL categories, not just root ones. Add search and parent column for better navigation.
2.  **API**: Add a filter `is_homepage=true` to `CategoryViewSet` that returns any category where `sort_order > 0`.
3.  **Frontend**: Update the service and component to request `is_homepage=true` instead of relying on root category defaults.

## Implementation Tasks

- [x] **Task 1: Admin Update**
    - File: `backend/apps/products/admin.py`
    - Action: Remove `parent__isnull=True` restriction in `HomepageCategoryAdmin`. Add `parent` to `list_display` and `search_fields`.

- [x] **Task 2: API Filter**
    - File: `backend/apps/products/filters.py`
    - Action: Add `is_homepage` filter to `CategoryFilter` (or viewset) that filters by `sort_order__gt=0`.

- [x] **Task 3: Backend View Update**
     - File `backend/apps/products/views.py`
     - Action: Ensure `CategoryViewSet` uses the filter correctly.

- [x] **Task 4: Frontend Service**
    - File: `frontend/src/services/categoriesService.ts`
    - Action: Add `is_homepage` param to `getCategories`.

- [x] **Task 5: Frontend Component**
    - File: `frontend/src/components/home/CategoriesSection.tsx`
    - Action: Call `getCategories({ is_homepage: true })`.

## Acceptance Criteria
- [ ] Admin can see and edit Level 2 categories in "Home Categories".
- [ ] Setting `sort_order` > 0 on "Pools" (L2) makes it appear in API response.
- [ ] Homepage Carousel displays the specific L2 categories.
