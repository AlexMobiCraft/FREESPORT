# Epic 10: 1C Sync Admin Integration - Brownfield Enhancement

## Epic Goal

Integrate 1C data synchronization functionality into Django Admin Panel to enable administrators to trigger and monitor catalog and customer imports directly from the web interface, eliminating the need for manual PowerShell script execution.

## Epic Description

### Existing System Context

**Current relevant functionality:**

- 1C data synchronization is performed via PowerShell scripts (`scripts/inport_from_1C/`) that:
  - Sync data files from production server via SSH/SCP
  - Start Docker services (PostgreSQL, Redis)
  - Run Django migrations
  - Execute management commands (`import_catalog_from_1c`, `import_customers_from_1c`)
- Django management commands handle actual data parsing and processing
- `ImportSession` model tracks import operations
- `CustomerSyncLog` and `SyncLog` models log synchronization events
- Celery is configured for asynchronous task execution
- Existing monitoring dashboard at `/admin/monitoring/dashboard/`

**Technology stack:**

- Backend: Django 4.x, Python 3.11+
- Database: PostgreSQL
- Cache/Queue: Redis
- Task Queue: Celery
- Containerization: Docker
- Admin: Django Admin with custom views

**Integration points:**

- Django Admin interface (custom views and actions)
- Celery task queue (asynchronous execution)
- Existing management commands (`import_catalog_from_1c.py`, `import_customers_from_1c.py`)
- `ImportSession` and logging models (`CustomerSyncLog`, `SyncLog`)
- Monitoring infrastructure (`CustomerSyncMonitor`, `IntegrationHealthCheck`)

### Enhancement Details

**What's being added/changed:**

1. **Celery Tasks** for asynchronous execution of import commands
   - `import_catalog_from_1c_task` - triggers catalog import
   - `import_customers_from_1c_task` - triggers customer import
   - Tasks wrap existing management commands using `call_command()`
   - Proper error handling and logging

2. **Django Admin Interface** for triggering synchronization
   - Custom admin view with form for selecting import type and parameters
   - Options: import type (catalog/customers), chunk size, dry-run mode, skip backup
   - Protection against concurrent executions (check active `ImportSession`)
   - Flash messages for success/error feedback
   - Link to monitoring dashboard for status tracking

3. **Enhanced Monitoring** (optional improvement)
   - Display recent `ImportSession` records in admin
   - Real-time status updates for running imports
   - Integration with existing monitoring dashboard

**How it integrates:**

- Extends existing Django Admin with custom view at `/admin/products/import-1c/`
- Leverages existing Celery infrastructure (already configured in `freesport/celery.py`)
- Reuses all existing management commands without modification
- Uses existing `ImportSession` and logging models for tracking
- Follows established patterns from `apps/cart/tasks.py` (Celery task example)
- Maintains separation: file synchronization remains manual/scripted, only import execution is moved to admin

**Success criteria:**

1. Administrators can trigger 1C catalog import from Django Admin
2. Administrators can trigger 1C customer import from Django Admin
3. Import operations run asynchronously via Celery
4. Import status is visible in admin interface
5. Concurrent import protection works correctly
6. Existing PowerShell scripts remain functional (backward compatibility)
7. All imports are logged to `ImportSession` and sync log models
8. No regression in existing import functionality

## Stories

### Story 1: Create Celery Tasks for 1C Import Operations

**Goal:** Implement asynchronous Celery tasks that wrap existing management commands for catalog and customer imports.

**Scope:**

- Create `apps/products/tasks.py` with `import_catalog_from_1c_task`
- Create `apps/users/tasks.py` with `import_customers_from_1c_task`
- Both tasks use `call_command()` to execute existing management commands
- Implement proper error handling and logging
- Update Celery configuration if needed

**Acceptance Criteria:**

- Tasks can be called programmatically and execute successfully
- Parameters (data-dir, chunk-size, dry-run, etc.) are properly passed to commands
- Errors are caught and logged appropriately
- `ImportSession` status is updated correctly

### Story 2: Django Admin Interface for 1C Sync Trigger

**Goal:** Create a user-friendly admin interface for triggering 1C synchronization operations.

**Scope:**

- Create custom admin view at `/admin/products/import-1c/`
- Implement form with fields:
  - Import type (catalog/customers/both)
  - Chunk size (default: 1000 for catalog, 100 for customers)
  - Dry-run mode checkbox
  - Skip backup checkbox
- Add concurrent execution protection (check active `ImportSession`)
- Display flash messages for success/error
- Add link to monitoring dashboard
- Restrict access to superusers or specific permission group

**Acceptance Criteria:**

- Admin view is accessible at `/admin/products/import-1c/`
- Form validates input correctly
- Concurrent execution is prevented with clear error message
- Success message includes link to monitoring dashboard
- Only authorized users can access the view
- UI follows Django Admin design patterns

### Story 3: Enhanced Import Monitoring and Documentation

**Goal:** Improve visibility of import operations and document the new functionality.

**Scope:**

- Add recent `ImportSession` list to admin view
- Display current import status (if any running)
- Update `README_SERVER_SYNC.md` with admin interface usage
- Create admin user guide section in docs
- Add inline help text in admin form

**Acceptance Criteria:**

- Recent imports (last 10) are visible in admin view with status
- Running imports are clearly indicated
- Documentation explains when to use admin vs. PowerShell scripts
- Help text guides users on parameter selection
- Screenshots/examples included in documentation

## Compatibility Requirements

- [x] Existing PowerShell scripts remain unchanged and functional
- [x] Management commands (`import_catalog_from_1c`, `import_customers_from_1c`) are not modified
- [x] Database schema changes: None required (uses existing models)
- [x] UI changes follow Django Admin patterns and conventions
- [x] Performance impact: Minimal (async execution via Celery)
- [x] Existing monitoring dashboard remains functional
- [x] No breaking changes to import/sync workflow

## Risk Mitigation

**Primary Risk:** Concurrent import executions causing data conflicts or system overload

**Mitigation:**

- Implement active session check before starting new import
- Use existing `ImportSession` status field (`started`, `in_progress`) for locking
- Display clear error message if import is already running
- Add database-level constraints if needed (unique constraint on active sessions)

**Secondary Risk:** Incorrect parameter passing leading to failed imports

**Mitigation:**

- Validate all form inputs before task creation
- Use sensible defaults for all parameters
- Add dry-run mode for testing without data changes
- Comprehensive error logging and user feedback

**Rollback Plan:**

- Admin view can be disabled via URL configuration
- Celery tasks can be removed without affecting management commands
- PowerShell scripts remain as fallback method
- No database migrations required, so no schema rollback needed

## Definition of Done

- [x] All 3 stories completed with acceptance criteria met
- [x] Existing import functionality verified through testing
  - PowerShell scripts still work
  - Management commands execute correctly
  - ImportSession tracking functions properly
- [x] Integration points working correctly
  - Celery tasks execute management commands
  - Admin view triggers tasks successfully
  - Monitoring dashboard displays import status
- [x] Documentation updated appropriately
  - README_SERVER_SYNC.md includes admin usage
  - Admin interface has inline help
  - User guide created
- [x] No regression in existing features
  - All existing tests pass
  - Manual testing of PowerShell workflow
  - Import logging and monitoring unchanged

## Dependencies

**Technical Dependencies:**

- Celery must be running (already configured)
- Redis must be available (already configured)
- Docker environment must be set up (already required)
- Data files must be synced to local directory (existing PowerShell process)

**Process Dependencies:**

- File synchronization from production server remains manual/scripted
- Administrators must understand when to use admin vs. scripts
- Proper permissions must be configured for admin users

## Notes

- This enhancement does NOT replace PowerShell scripts for file synchronization
- File sync (`sync_import_data.ps1`) remains a prerequisite step
- Admin interface only triggers import of already-synced data
- Suitable for brownfield epic (3 focused stories, low architectural impact)
- Maintains backward compatibility with existing workflows
- Low risk to existing system functionality

---

## Story Manager Handoff

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing Django-based e-commerce system (FREESPORT)
- Integration points:
  - Django Admin (custom views following existing patterns like `monitoring_dashboard_view`)
  - Celery task queue (follow pattern from `apps/cart/tasks.py`)
  - Existing management commands (`import_catalog_from_1c`, `import_customers_from_1c`)
  - Models: `ImportSession`, `CustomerSyncLog`, `SyncLog`
- Existing patterns to follow:
  - Celery shared tasks with `call_command()` for management commands
  - Django Admin custom views with forms
  - `ImportSession` for tracking and concurrent execution protection
  - Flash messages for user feedback
- Critical compatibility requirements:
  - Do NOT modify existing management commands
  - Do NOT modify PowerShell scripts
  - Maintain existing `ImportSession` and logging behavior
  - Ensure backward compatibility with script-based workflow
- Each story must include verification that existing functionality remains intact

The epic should maintain system integrity while delivering a user-friendly admin interface for triggering 1C data synchronization."

---

**Created:** 2025-11-02  
**Status:** Draft  
**Epic Type:** Brownfield Enhancement  
**Estimated Stories:** 3  
**Priority:** Medium  
**Target Release:** TBD
