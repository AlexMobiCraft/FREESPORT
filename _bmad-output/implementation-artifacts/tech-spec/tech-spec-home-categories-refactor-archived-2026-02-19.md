---
title: 'Home Page Categories Block Refactor'
slug: 'home-categories-refactor'
created: '2026-02-18'
status: 'review'
stepsCompleted: [1, 2, 3]
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
The current "Popular Categories" block on the 'Blue' theme homepage is a static grid that doesn't fully support the marketing requirement of prioritizing specific categories visually. The client needs flexible control over which categories appear, their order (priority), and their images directly from the Admin panel. The visual presentation needs to change from a Grid to a Carousel.

## Solution
Refactor the "Categories" block to be dynamic and manageable:
1. **Backend**: Leverage existing `Category` fields (`sort_order`, `image`) but expose them in a dedicated "Home Page Categories" admin section for focused management.
2. **Frontend**: Replace the Grid layout in `CategoriesSection` with a Carousel component (similar to Quick Links) that displays root categories sorted by priority.
3. **Data**: Fetch root categories (parent=None) sorted by `sort_order`.

## Scope
- **In Scope**:
  - Backend: Django Admin setup for "Home Categories" (Proxy model).
  - API: Verify `CategoryViewSet` supports sorting by `sort_order`.
  - Frontend: `CategoriesSection` refactor (Grid -> Carousel).
  - Frontend: `CategoryCard` update/creation if needed.
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
- **Backend**: 
  - DO NOT modify `Category` model structure (fields exist).
  - Use `Proxy` model in `admin.py` to create a separate menu item "Категории для главной" without creating a DB table.

## Files to Reference
| File | Relevance |
|------|-----------|
| `backend/apps/products/admin.py` | Create Proxy Admin here. |
| `frontend/src/components/home/CategoriesSection.tsx` | Main component to refactor. |
| `frontend/src/components/home/QuickLinksSection.tsx` | Reference for Carousel logic. |
| `frontend/src/services/categoriesService.ts` | Ensure `getCategories` supports `ordering`. |

## Technical Decisions
- **Admin**: Use a `HompageCategory` proxy model to filter only root categories (`parent__isnull=True`) and expose only relevant fields (`image`, `sort_order`, `is_active`) to simplify the content manager's work.
- **Sorting**: The API already supports ordering. We will enforce `sort_order` sorting for the homepage block.

# Implementation Plan

## Backend Tasks
- [ ] Task 1: Create `HomepageCategory` Proxy Model
  - File: `backend/apps/products/models.py`
  - Action: Define a proxy model inheriting from `Category`.
  - Notes: Set `verbose_name` to "Категория для главной".
- [ ] Task 2: Create Admin for Proxy Model
  - File: `backend/apps/products/admin.py`
  - Action: Register `HomepageCategory` with a custom `ModelAdmin`.
  - Logic: 
    - `list_display`: `image_preview`, `name`, `sort_order`, `is_active`.
    - `list_editable`: `sort_order`, `is_active`.
    - `get_queryset`: Filter `parent__isnull=True`.

## Frontend Tasks
- [ ] Task 3: Update Categories Service
  - File: `frontend/src/services/categoriesService.ts`
  - Action: Ensure `getCategories` accepts an `ordering` parameter or defaults to `sort_order`.
- [ ] Task 4: Refactor CategoriesSection to Carousel
  - File: `frontend/src/components/home/CategoriesSection.tsx`
  - Action: 
    - Fetch categories with `parent_id__isnull=True` and `ordering='sort_order'`.
    - Implement horizontal scroll (carousel) layout.
    - Use `CategoryCard` or similar design inside the carousel.
    - Add navigation arrows (Left/Right) if content overflows.

# Acceptance Criteria

- [ ] AC 1: Admin - "Home Categories" Menu
  - Given I am an admin
  - When I open the main menu
  - Then I see "Категории для главной" under Products app
- [ ] AC 2: Admin - Manage Priorities
  - Given I am in "Home Categories" list
  - When I change the "Priority" (sort_order) of a category and save
  - Then the order is updated in the database
- [ ] AC 3: Frontend - Display Logic
  - Given I am on the Homepage (Blue theme)
  - When the page loads
  - Then I see the "Popular Categories" block as a horizontal carousel
  - And the categories are sorted by the priority defined in Admin
- [ ] AC 4: Frontend - Carousel Interaction
  - Given simple list of categories exceeds screen width
  - When I click Right Arrow
  - Then the list scrolls to show more categories
- [ ] AC 5: Frontend - Navigation
  - Given I see a category card
  - When I click on it
  - Then I am redirected to `/catalog/[slug]`
