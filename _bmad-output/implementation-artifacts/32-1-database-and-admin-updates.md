# Story 32.1: Database and Admin Updates

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Admin,
I want to create banners with a specific 'Marketing' type and mandatory image,
so that I can manage promotional content separately from Hero banners.

## Acceptance Criteria

1. **Database Migration**:
   - `Banner` model has a `type` field with choices `HERO` and `MARKETING`.
   - `type` field is non-nullable (`null=False`).
   - Existing records are migrated with `type=HERO`.

2. **Admin Interface**:
   - `BannerAdmin` includes a 'Type' selector in the form.
   - 'Image' field is **mandatory** when 'Marketing' type is selected (can be optional for Hero if legacy logic allows, or strictly required for Marketing).
   - 'Target URL' field is available for Marketing banners.
   - Sidebar filter by 'Type' is available in the list view.

3. **Caching**:
   - Saving or deleting a banner invalidates the API cache for that specific banner type (key pattern: `banners:list:{type}`).

## Tasks / Subtasks

- [x] Update Banner Model <!-- id: 1 -->
  - [x] Add `type` field (Choices: HERO, MARKETING) to `apps/banners/models.py`.
  - [x] Generate migration with default=HERO for existing records.
  - [x] Enforce `null=False` on the database level.
- [x] Update Banner Admin <!-- id: 2 -->
  - [x] Add `list_filter = ["type", ...]` to `BannerAdmin`.
  - [x] Customize `get_form` or `clean` method to enforce mandatory Image for Marketing type.
  - [x] Ensure `target_url` is accessible/editable for Marketing type.
- [x] Implement Cache Invalidation <!-- id: 3 -->
  - [x] Identify where caching is currently handled (signals or model `save` method).
  - [x] Ensure invalidation logic targets `banners:list:{type}` based on the instance type.
- [x] Verify Changes <!-- id: 4 -->
  - [x] Run migration.
  - [x] Test creating Hero banner (should work as before).
  - [x] Test creating Marketing banner (without image -> fail, with image -> success).
  - [x] Check sidebar filter.

## Dev Notes

- **Architecture**:
  - `apps/banners/models.py`: Standard Django model.
  - `apps/banners/admin.py`: Standard `ModelAdmin`.
  - **Caching**: Check `apps/banners/signals.py` or `models.py` `save()` method. Using `django.core.cache` or specific utility. Review `apps/common/services.py` if there's a shared caching service.
- **Source Tree**:
  - `backend/apps/banners/`
- **Testing Standards**:
  - Unit tests in `backend/apps/banners/tests/` using `pytest`.
  - Test model constraints and Admin form validation (if possible, or at least model validation).

### Project Structure Notes

- Follow Project Conventions: `snake_case` for fields.
- Use `TextChoices` for the `Type` enum in `models.py`.

### References

- [Source: planning-artifacts/epics.md](file:///c:/Users/1/DEV/FREESPORT/_bmad-output/planning-artifacts/epics.md) - Story 32.1
- [Source: planning-artifacts/architecture.md](file:///c:/Users/1/DEV/FREESPORT/_bmad-output/planning-artifacts/architecture.md) - Caching Strategy (Redis)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 2.0 Pro)

### Debug Log References

- None

### Completion Notes List

- Verified `apps/banners` structure.
- **Implemented AC1:** `Banner` model updated with `type` field (Hero/Marketing). Migration `0003` verified.
- **Implemented AC2:** Added `clean()` method to `Banner` model to enforce mandatory image for Marketing banners. Verified Admin filters and fields.
- **Implemented AC3:** Created `apps/banners/signals.py` to handle cache invalidation for `banners:list:{type}` on save/delete. Registered signals in `apps.py`.
- **Created Comprehensive Tests:**
    - `tests/test_models.py`: Model fields, defaults, constraints.
    - `tests/test_admin.py`: Admin validation logic (clean method), filters.
    - `tests/test_signals.py`: Cache invalidation logic.
    - 25 tests passed successfully.

### File List

- backend/apps/banners/models.py
- backend/apps/banners/admin.py
- backend/apps/banners/signals.py (new)
- backend/apps/banners/apps.py
- backend/apps/banners/tests/test_models.py (new)
- backend/apps/banners/tests/test_admin.py (new)
- backend/apps/banners/tests/test_signals.py (new)
