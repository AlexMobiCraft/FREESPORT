# Story 33.2: API Featured Brands Endpoint

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Frontend Developer,
I want to fetch a list of featured brands via API,
So that I can display them on the homepage in a high-performance carousel.

## Acceptance Criteria

### 1. Endpoint Implementation
- **Given** an unauthenticated or authenticated user,
- **When** they request `GET /api/v1/products/brands/featured/` (Recommended over query param for specific caching),
- **Then** the API returns a JSON list of brands where `is_featured=True`.
- **And** the response includes fields: `id`, `name`, `slug`, `image` (absolute URL), `website`.
- **And** the list is ordered by `name` (or `sort_order` if available).

### 2. Performance & Caching (Critical)
- **Given** the featured brands endpoint,
- **When** accessed,
- **Then** the response is **cached for 1 hour (3600 seconds)** in Redis to minimize database hits.
- **And** the cache key is independent of the user (public data).
- **And** if the list of featured brands is updated (in Admin), the cache should ideally be invalidated (or just expire).

### 3. Response Structure
- **Given** the API response,
- **When** serialized,
- **Then** field names are in `snake_case`.
- **And** the `image` field provides a full URL (with domain/protocol) or a relative path handled correctly by the frontend.

## Tasks / Subtasks

- [x] Task 1: Update `BrandViewSet` in `apps/products/views.py`
  - [x] Implement `featured` action (via `@action(detail=False)`) OR optimize `list` with caching.
    - *Recommendation*: Use `@action(detail=False, url_path='featured')` to isolate the homepage logic and caching policy from the general catalog filtering.
  - [x] Decorate the view with `@method_decorator(cache_page(60*60))`.
  - [x] Ensure `pagination_class=None` (or specific large limit) for this action to return a simple list for the carousel (if desired) or standard paginated response.
    - *Decision*: Keep standard pagination but ensure page size is sufficient (100 is likely enough).
- [x] Task 2: Caching Configuration
  - [x] Verify `CACHES` setting in `settings.py` (Redis).
  - [x] Ensure `django.views.decorators.cache.cache_page` is working with DRF (may need `vary_on_cookie` if auth varies, but here it shouldn't).
- [x] Task 3: Testing
  - [x] Create `backend/apps/products/tests/test_brand_api.py`.
  - [x] Test status code 200 for anonymous users.
  - [x] Test that only `is_featured=True` brands are returned.
  - [x] Test response structure (fields).
  - [x] (Optional) Verify caching headers or behavior (mocking cache).

## Dev Notes

### Architecture & Patterns

- **Module**: `apps/products`
- **Class**: `BrandViewSet` (`views.py`)
- **Decorator**: `django.utils.decorators.method_decorator`, `django.views.decorators.cache.cache_page`.
- **Action**: Use `from rest_framework.decorators import action`.

### Source Tree Locations

- `backend/apps/products/views.py` — Location of `BrandViewSet`.
- `backend/apps/products/urls.py` — Router registration (no change needed if using `@action`).
- `backend/apps/products/tests/test_brand_api.py` — New test file.

### Testing Standards

- Use `APIClient` from `rest_framework.test`.
- Use `pytest.mark.django_db`.
- Mocking: `unittest.mock.patch` for cache if needed.

### Project Structure Notes

- Previous story `33.1` already extended `Brand` model and updated `BrandSerializer`.
- `BrandViewSet` currently filters by `is_featured` query param. The new `featured` action is an optimization for the specific homepage use case.

## References

- [Epics.md: Epic 33](/docs/epics.md#epic-33-brands-block-implementation)
- [Architecture.md: Caching Strategy](/docs/architecture.md#cross-cutting-concerns)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Cache isolation fix: added `cache.clear()` in test setup fixture to prevent cross-test cache pollution from `cache_page` decorator.

### Completion Notes List

- ✅ Task 1: Added `featured` action to `BrandViewSet` using `@action(detail=False, url_path='featured')` with `@method_decorator(cache_page(60*60))` for 1-hour caching. Queries `Brand.objects.active().filter(is_featured=True).order_by("name")`. Standard pagination (page_size=100) preserved via `BrandPageNumberPagination`.
- ✅ Task 2: Verified `CACHES` configured with `django_redis.cache.RedisCache` in `base.py`, `production.py`. `cache_page` works correctly with DRF — no `vary_on_cookie` needed since endpoint is public data.
- ✅ Task 3: Created 10 tests in `test_brand_api.py` covering: anonymous access (200), featured-only filtering, inactive exclusion, name ordering, response fields, image URL presence, empty response, pagination structure, cache headers (Cache-Control: max-age), cached response consistency.
- ✅ Full regression: 283 tests passed, 0 failures.

### File List

- `backend/apps/products/views.py` — Modified: added `featured` action with caching to `BrandViewSet`
- `backend/apps/products/tests/test_brand_api.py` — New: 10 tests for featured brands endpoint
