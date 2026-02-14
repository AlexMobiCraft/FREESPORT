# Story 32.2: API Implementation for Marketing Banners

Status: done

## Story

As a Frontend Developer,
I want to fetch marketing banners via API with filtering and limits,
so that I can display the correct content on the homepage without over-fetching.

## Acceptance Criteria

1. **API Default Behavior (Backward Compatibility)**:
    - **Given** a request to `/api/banners/` without parameters,
    - **Then** the API must return only banners with `type='hero'` (Fixing current behavior which returns all).
    - **And** the cache key used must reflect this default (should use `hero` cache or a distinct default cache, not mixed `all`).

2. **API Marketing Filter**:
    - **Given** a request to `/api/banners/?type=marketing`,
    - **Then** the API must return only active banners with `type='marketing'`.
    - **And** the result count must be limited to **5** (FR12 - Database or Code level limit).

3. **Frontend Integration**:
    - **Given** the `bannersService`,
    - **Then** the `getActive()` method is updated to accept an optional `type: BannerType` parameter.
    - **And** the TypeScript definitions are updated to include the new parameter.

4. **Cache Invalidation Consistency**:
    - **Given** a change to a 'marketing' banner in Admin,
    - **Then** the specific cache for marketing banners is invalidated.
    - **And** the default cache (if it stores hero or all) is NOT invalidated unnecessarily, OR handled correctly if overlapping.

## Tasks / Subtasks

- [x] **Backend: Implementation Fixes**
    - [x] Update `ActiveBannersView.list` in `backend/apps/banners/views.py`:
        - [x] Default `banner_type` to `'hero'` if not provided or invalid.
        - [x] Ensure `build_cache_key` uses the resolved type (e.g. 'hero' instead of 'all').
    - [x] Update `services.py`:
        - [x] Modify `get_active_banners_queryset` or `list` view to apply `[:5]` slicing ONLY when type is 'marketing' (FR12).
    - [x] Verify `compute_cache_ttl` handles the default type correctly.

- [x] **Frontend: Service Update**
    - [x] Update `frontend/src/services/bannersService.ts`:
        - [x] Change `getActive()` signature to `getActive(type?: 'hero' | 'marketing')`.
        - [x] Pass the type param to the API request.
    - [x] Update `frontend/src/types/banners.ts` if needed (e.g., add `BannerType` enum/union).

- [x] **Testing**
    - [x] Add Pytest unit test for `ActiveBannersView` verifying default behavior (no param -> hero only).
    - [x] Add Pytest unit test for `?type=marketing` limit (create 6 banners, verify 5 returned).
    - [x] Verify Frontend service types via `npm run type-check`.

## Dev Notes

### Architecture & Codebase
- **Current State Analysis**:
    - `ActiveBannersView` exists but defaults to returning ALL banners (violates FR6).
    - `services.py` has caching logic but uses `all` key for missing type.
    - `bannersService.ts` on frontend lacks arguments.
- **Limit Logic**: Implement the limit (5) in Python (slicing queryset) or DB (`.filter(...)[:5]`). DB is preferred for performance.

### API Contract (Frontend Consumer)
- Frontend will call:
    - `bannersService.getActive('hero')` (or no arg if default preserved on client side) for Main Hero.
    - `bannersService.getActive('marketing')` for the new section.

### References
- Epics: `_bmad-output/planning-artifacts/epics.md` (Story 32.2)
- Backend Views: `backend/apps/banners/views.py`
- Backend Services: `backend/apps/banners/services.py`
- Frontend Service: `frontend/src/services/bannersService.ts`

## Dev Agent Record

### Agent Model Used
Antigravity (Google DeepMind)

### Completion Notes List
- Confirmed that backend implementation was started but missed critical requirements (FR6 default behavior, FR12 limit).
- Identified exact files to modify.

### File List
- backend/apps/banners/services.py
- backend/apps/banners/views.py
- backend/apps/banners/tests/test_services.py
- backend/apps/banners/tests/test_views.py
- frontend/src/services/bannersService.ts
- frontend/src/types/banners.ts
- frontend/src/__mocks__/api/handlers.ts
- frontend/src/components/home/__tests__/HeroSection.test.tsx
