# Story 33.1: Brand Model & Admin Updates

Status: review

## Story

As an Admin,
I want to upload brand logos and mark brands as featured on the homepage,
So that I can highlight key partners and improve navigation.

## Acceptance Criteria

### 1. Brand Model Updates
- **Given** the existing `Brand` model in `apps/products/models.py`,
- **When** the model is updated,
- **Then** it includes an `image` field (`models.ImageField`) allowing uploads to `brands/`.
- **And** it includes an `is_featured` field (`models.BooleanField`, default=`False`).
- **And** the `__str__` method still returns the brand name.

### 2. Admin Interface Updates
- **Given** the Django Admin interface for Brands,
- **When** creating or editing a brand,
- **Then** I see the fields `image` and `is_featured`.
- **And** the list view (`list_display`) shows the `is_featured` status (boolean toggle or icon).
- **And** the list view includes a `list_filter` for `is_featured`.

### 3. Data Validation (Model Level)
- **Given** I check "Show on Homepage" (`is_featured=True`) but do not upload an image,
- **When** I try to save the brand (via Admin or Code),
- **Then** the system raises a `ValidationError`: "Image is required for featured brands" (FR-03).
- **Note**: This validation should be implemented in the model's `clean()` method to ensure integrity across all interfaces.

## Tasks / Subtasks

- [x] Task 1: Update Brand Model
  - [x] Add `image` field to `Brand` model (upload_to='brands/')
  - [x] Add `is_featured` field to `Brand` model (default=False)
  - [x] Create and apply database migration
- [x] Task 2: Implement Validation Logic
  - [x] Override `clean()` method in `Brand` model
  - [x] Implement check: if `is_featured` is True and not `image`, raise `ValidationError`
- [x] Task 3: Update Django Admin
  - [x] Update `BrandAdmin` in `apps/products/admin.py`
  - [x] Add `image` and `is_featured` to `fields` or `fieldsets`
  - [x] Add `is_featured` to `list_display` and `list_filter`
  - [x] (Optional) Add image preview in list view using `utils.admin.image_preview` if available, otherwise skip
- [x] Task 4: Testing
  - [x] Write unit test for model fields existence
  - [x] Write unit test for `clean()` validation (success and failure cases)
  - [x] Write unit test for `is_featured` default value

### Доработки по результатам ревью (AI)
- [x] [MEDIUM] Добавить фильтрацию по `is_featured` в `BrandViewSet` (`apps/products/views.py`).
- [x] [MEDIUM] Исправить опечатку в папке: `frontend/public/images/brends/` -> `brands/`. *(Уже корректно — папка `brands/` существует, `brends/` отсутствует)*
- [x] [LOW] Добавить превью изображений в `BrandAdmin` (`apps/products/admin.py`) для улучшения UX.
- [x] [REVIEW][MEDIUM] Удалить дублирующую логику генерации slug из `BrandSerializer.validate` (уже есть в модели)
- [x] [REVIEW][MEDIUM] Документировать изменения во `frontend/src/types/api.ts` в File List и Dev Notes
- [x] [REVIEW][LOW] Обновить File List: добавить `backend/apps/products/tests/test_brand_model.py` и `frontend/src/types/api.ts`

## Dev Notes

### Architecture & Patterns
- **Module**: `apps/products`
- **Model**: `Brand` (likely in `apps/products/models.py`)
- **Admin**: `BrandAdmin` (likely in `apps/products/admin.py`)
- **Validation**: Use Django's standard `clean()` method for model validation.
- **Image Handling**: Ensure `Pillow` is installed (it should be). Images should be uploaded to `MEDIA_ROOT/brands/`.

### Source Tree Locations
- `backend/apps/products/models.py`
- `backend/apps/products/admin.py`
- `backend/apps/products/tests/test_brand_model.py` — unit tests for Brand model (Story 33.1)
- `frontend/src/types/api.ts` — Brand interface updated: added `image`, `is_featured` fields

### Testing Standards
- Use `pytest` with `pytest-django`.
- Run tests via Docker: `docker compose ... exec backend pytest apps/products/tests/`
- Factories: Update `BrandFactory` in `apps/products/tests/factories.py` (if exists) or create one to support new fields.

### Commands
- Make migrations: `docker compose ... exec backend python manage.py makemigrations`
- Migrate: `docker compose ... exec backend python manage.py migrate`
- Run tests: `docker compose ... exec backend pytest apps/products/`

## References
- [Epics.md: Epic 33](/docs/epics.md#epic-33-brands-block-implementation)
- [Architecture.md: Django Apps Structure](/docs/architecture.md#django-app-structure)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

Нет ошибок — все тесты прошли с первого раза.

### Completion Notes List

- Существующее поле `Brand.logo` переименовано в `Brand.image` (RenameField миграция) — соответствие AC-1 имени поля `image`.
- Добавлено поле `Brand.is_featured` (BooleanField, default=False) — AC-1.
- Реализован `Brand.clean()` с ValidationError при `is_featured=True` без `image` — AC-3.
- `BrandAdmin` обновлён: fieldsets с секциями (Основная информация, Изображение и отображение, Статус и даты), `is_featured` в `list_display` и `list_filter` — AC-2.
- `BrandSerializer` обновлён: `logo` → `image`, добавлен `is_featured` — поддержка API.
- 11 unit-тестов: 5 на поля модели, 6 на валидацию clean() — AC-1, AC-3.
- Полная регрессия: 247 тестов products + 21 тест serializers — все пройдены.
- ✅ Resolved review finding [MEDIUM]: Добавлена фильтрация `?is_featured=true/false` в `BrandViewSet.get_queryset()` + OpenAPI параметр.
- ✅ Resolved review finding [MEDIUM]: Папка `frontend/public/images/brands/` уже корректна — `brends/` не существует.
- ✅ Resolved review finding [LOW]: Добавлен `image_preview()` метод в `BrandAdmin` с img тегом 30x60px в list_display.
- 5 новых тестов: 3 на фильтрацию BrandViewSet (featured=true/false/all), 2 на image_preview (with/without image).
- Полная регрессия: 252 теста products — все пройдены (0 регрессий).
- ✅ Resolved review finding [REVIEW][MEDIUM]: Удалён дублирующий `BrandSerializer.validate()` — slug генерация делегирована `Brand.save()` с транслитерацией. Добавлены 2 теста на корректность slug генерации моделью.
- ✅ Resolved review finding [REVIEW][MEDIUM]: Документированы изменения в `frontend/src/types/api.ts` (Brand interface: `image`, `is_featured`) в Source Tree Locations и File List.
- ✅ Resolved review finding [REVIEW][LOW]: File List обновлён — добавлены `test_brand_model.py` и `api.ts`.

### File List

- `backend/apps/products/models.py` — Brand: renamed logo→image, added is_featured, added clean()
- `backend/apps/products/admin.py` — BrandAdmin: added fieldsets, is_featured in list_display/list_filter, added image_preview()
- `backend/apps/products/views.py` — BrandViewSet: added is_featured query param filtering + OpenAPI parameter
- `backend/apps/products/serializers.py` — BrandSerializer: logo→image, added is_featured, removed duplicate slug validate()
- `backend/apps/products/migrations/0043_rename_logo_to_image_add_is_featured.py` — NEW migration
- `backend/apps/products/tests/test_brand_model.py` — 18 unit tests (11 original + 5 review follow-up + 2 slug delegation)
- `frontend/src/types/api.ts` — Brand interface: added `image`, `is_featured` fields
