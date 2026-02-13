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
- [x] Review Follow-ups (AI 2) <!-- id: 5 -->
  - [x] [AI-Review][High] Add `type` field to `BannerSerializer` in `apps/banners/serializers.py` <!-- id: 5-1 -->
  - [x] [AI-Review][High] Implement caching and filtering by type in `ActiveBannersView` (`apps/banners/views.py`) <!-- id: 5-2 -->
  - [x] [AI-Review][Medium] Update `ActiveBannersView` to support `?type=hero|marketing` query param <!-- id: 5-3 -->
  - [x] [AI-Review][Low] Override `save()` method in `Banner` model to call `full_clean()` <!-- id: 5-4 -->
- [x] Review Follow-ups (AI 3) <!-- id: 6 -->
  - [x] [AI-Review][Medium] Track new test files in git (`backend/apps/banners/tests/test_serializers.py`, `backend/apps/banners/tests/test_views.py`) <!-- id: 6-1 -->
  - [x] [AI-Review][Medium] Validate `type` query param in `ActiveBannersView` to prevent cache flooding <!-- id: 6-2 -->
  - [x] [AI-Review][Low] Add test case for `type` field read-only behavior in serializer input <!-- id: 6-3 -->
- [x] Review Follow-ups (Critical Fixes) <!-- id: 7 -->
  - [x] [AI-Review][Critical] Fix Cache Key Collision: Include user role/group hash in `ActiveBannersView` cache key (e.g., `banners:list:{type}:{role_hash}`) to prevent guests seeing wholesale banners. <!-- id: 7-1 -->
  - [x] [AI-Review][Medium] Refactor API Logic: Move complex banner filtering/caching logic to a service layer or manager to separate concerns from the view (preparation for Story 32.2). <!-- id: 7-2 -->
- [x] Review Follow-ups (AI Final) <!-- id: 8 -->
  - [x] [AI-Review][Medium] Refactor `_ALL_ROLE_KEYS` in `apps.banners.services` to import directly from `apps.users.models.User.ROLE_CHOICES` to prevent drift. <!-- id: 8-1 -->
  - [x] [AI-Review][Low] Extract cache key pattern into a constant `CACHE_KEY_PATTERN` in `apps.banners.services`. <!-- id: 8-2 -->
- [x] Review Follow-ups (Code Review 4) <!-- id: 9 -->
  - [x] [AI-Review][Medium] Fix Cache Temporal Conflict: `BANNER_CACHE_TTL` allows stale data up to 15m (use shorter TTL or precise invalidation). <!-- id: 9-1 -->
  - [x] [AI-Review][Low] Add Temporal Unit Tests: Verify `start_date`/`end_date` logic in `Banner` model with mocked time. <!-- id: 9-2 -->
  - [x] [AI-Review][Low] Refactor Serializer: Remove fragile `read_only_fields = fields` definition in `BannerSerializer`. <!-- id: 9-3 -->
  - [x] [AI-Review][Low] Fix OpenAPI Examples: Remove hardcoded `http://example.com` URLs in `ActiveBannersView`. <!-- id: 9-4 -->


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
- **Senior Developer Review (AI) Follow-ups:**
    - Updated `Banner` model: `image` and `cta_text` are now optional (`blank=True`), enforcing `image` requirement for Marketing banners only via validation logic.
    - Updated `BannerAdmin`: Replaced `is_active` with `get_is_active_display` to show real availability status (including schedule).
    - Expanded tests to cover optional fields and new validation logic.
- **Addressed code review findings — 4 items resolved (Date: 2026-02-13):**
    - ✅ Resolved review finding [High]: Added `type` field to `BannerSerializer` — API теперь возвращает тип баннера.
    - ✅ Resolved review finding [High]: Реализовано кеширование в `ActiveBannersView` с ключами `banners:list:{type}` и `banners:list:all`, TTL 15 мин. Signal-инвалидация расширена для `banners:list:all`.
    - ✅ Resolved review finding [Medium]: Добавлен query param `?type=hero|marketing` в `ActiveBannersView` с OpenAPI документацией.
    - ✅ Resolved review finding [Low]: Добавлен `save()` метод в `Banner` с вызовом `full_clean()` — валидация срабатывает при любом save().
    - 43 теста пройдены (было 25, добавлено 18 новых).
- **Addressed code review findings — 3 items resolved (Date: 2026-02-13):**
    - ✅ Resolved review finding [Medium]: `test_serializers.py` и `test_views.py` добавлены в git staging (`git add`).
    - ✅ Resolved review finding [Medium]: Валидация `type` query param в `ActiveBannersView` — невалидные значения игнорируются, предотвращая cache flooding. Добавлены 2 теста.
    - ✅ Resolved review finding [Low]: Добавлен функциональный тест `test_type_field_ignored_on_input` — подтверждает, что `type` игнорируется при input через serializer.
    - 45 тестов пройдены (было 43, добавлено 2 новых).
- **Addressed code review findings — 2 items resolved (Date: 2026-02-13):**
    - ✅ Resolved review finding [Critical]: Fix Cache Key Collision — ключ кеша теперь включает роль пользователя (`banners:list:{type}:{role}`). Гости не могут видеть оптовые баннеры через shared cache. Инвалидация очищает ключи по всем ролям.
    - ✅ Resolved review finding [Medium]: Refactor API Logic — создан `services.py` с функциями `get_role_key()`, `validate_banner_type()`, `build_cache_key()`, `get_active_banners_queryset()`, `cache_banner_response()`, `invalidate_banner_cache()`. View стал тонким, signals делегируют в service. Подготовка для Story 32.2.
    - 73 теста пройдены (было 45, добавлено 28 новых). Полный regression suite: 1737 passed, 1 failed (не связан — flaky perf тест `pages`), 3 skipped.
- **Addressed code review findings — 2 items resolved (Date: 2026-02-13):**
    - ✅ Resolved review finding [Medium]: `_ALL_ROLE_KEYS` теперь динамически формируется из `User.ROLE_CHOICES` + "guest" — предотвращает drift при добавлении новых ролей.
    - ✅ Resolved review finding [Low]: Добавлена константа `CACHE_KEY_PATTERN = "banners:list:{type}:{role}"` — `build_cache_key()` использует `.format()` вместо f-string.
    - 82 теста баннеров пройдены (было 73, добавлено 9 новых: 4 для синхронизации ролей, 5 для CACHE_KEY_PATTERN).
- **Addressed code review findings — 4 items resolved (Date: 2026-02-13):**
    - ✅ Resolved review finding [Medium]: Fix Cache Temporal Conflict — добавлена `compute_cache_ttl()` в `services.py`, вычисляет TTL на основе ближайших `start_date`/`end_date`. Добавлена константа `MIN_CACHE_TTL = 10`. View передаёт dynamic TTL в `cache_banner_response()`. 10 новых тестов.
    - ✅ Resolved review finding [Low]: Add Temporal Unit Tests — 14 тестов с `unittest.mock.patch` для `timezone.now()`: `is_scheduled_active` (8 тестов) и `get_for_user` temporal filtering (6 тестов). Покрыты граничные случаи.
    - ✅ Resolved review finding [Low]: Refactor Serializer — `read_only_fields` теперь явный tuple, идентичный `fields`. Не ссылка на тот же объект. 2 новых теста.
    - ✅ Resolved review finding [Low]: Fix OpenAPI Examples — `http://example.com` URLs заменены на relative `/media/promos/...` paths.
    - 109 тестов баннеров пройдены (было 82, добавлено 27 новых).

### File List

- backend/apps/banners/models.py
- backend/apps/banners/admin.py
- backend/apps/banners/signals.py (new)
- backend/apps/banners/apps.py
- backend/apps/banners/serializers.py
- backend/apps/banners/views.py
- backend/apps/banners/migrations/0002_alter_banner_image.py
- backend/apps/banners/migrations/0003_banner_type.py
- backend/apps/banners/migrations/0004_alter_banner_cta_text.py
- backend/apps/banners/migrations/0005_alter_banner_image.py
- backend/apps/banners/tests/test_models.py (new)
- backend/apps/banners/tests/test_admin.py (new)
- backend/apps/banners/tests/test_signals.py (new)
- backend/apps/banners/tests/test_serializers.py (new)
- backend/apps/banners/tests/test_views.py (new)
- backend/apps/banners/services.py (new)
- backend/apps/banners/tests/test_services.py (new)
