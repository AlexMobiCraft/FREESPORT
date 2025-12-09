# Import Commands Migration Guide

## Overview

Starting from Epic 27, the legacy `import_catalog_from_1c` command has been
**removed**. Use `import_products_from_1c` instead.

## Timeline

| Milestone | Status |
|-----------|--------|
| **Story 27.4** | `import_catalog_from_1c` deprecation warning added |
| **Story 27.5** | ✅ `import_catalog_from_1c` **REMOVED** |

## Command Mapping

| Old Command | New Command |
|------------|-------------|
| `import_catalog_from_1c --file-type=all` | `import_products_from_1c --file-type=all` |
| `import_catalog_from_1c --file-type=goods` | `import_products_from_1c --file-type=goods` |
| `import_catalog_from_1c --file-type=offers` | `import_products_from_1c --file-type=offers` |
| `import_catalog_from_1c --file-type=rests` | `import_products_from_1c --file-type=rests` |
| `import_catalog_from_1c --file-type=prices` | `import_products_from_1c --file-type=prices` |

## Parameter Compatibility

All parameters from the legacy command are supported in the new command:

| Parameter | Description |
|-----------|-------------|
| `--data-dir` | Path to 1C data directory |
| `--file-type` | Type of import (all, goods, offers, prices, rests) |
| `--celery-task-id` | Celery task ID for linking to import session |
| `--skip-validation` | Skip data validation for faster import |
| `--skip-images` | Skip image import |
| `--chunk-size` | Batch size for bulk operations (default: 1000) |
| `--dry-run` | Test run without writing to database |
| `--clear-existing` | Clear existing data before import |
| `--skip-backup` | Skip backup creation before import |

## Migration Steps

### 1. Update Management Command Calls

Replace all calls to `import_catalog_from_1c` with `import_products_from_1c`:

```bash
# Before
python manage.py import_catalog_from_1c --data-dir /path/to/data

# After
python manage.py import_products_from_1c --data-dir /path/to/data
```

### 2. Update Scripts and Cron Jobs

Update any scripts in `scripts/inport_from_1C/`:

```powershell
# Before (in run_catalog_import.ps1)
python manage.py import_catalog_from_1c --data-dir $DATA_DIR

# After
python manage.py import_products_from_1c --data-dir $DATA_DIR
```

### 3. Update Celery Tasks

Celery tasks in `apps/integrations/tasks.py` have been updated in Story 27.3:

```python
# Before
call_command("import_catalog_from_1c", ...)

# After
call_command("import_products_from_1c", ...)
```

### 4. Test Migration

Before removing the legacy command, test your migration:

```bash
# Run new command in dry-run mode
python manage.py import_products_from_1c --data-dir /path/to/data --dry-run

# Run full import with backup
python manage.py import_products_from_1c --data-dir /path/to/data
```

## Key Differences

The new `import_products_from_1c` command:

1. **Uses VariantImportProcessor** - More efficient product variant handling with internal variant import logic
2. **Better image path normalization** - Unified `normalize_image_path()` function
3. **Improved type safety** - Uses TypedDict for structured data
4. **Same CLI interface** - All parameters work identically

## Breaking Changes

None. The new command is a drop-in replacement with identical parameter interface.

## Support

If you encounter issues during migration, check:

1. Data directory structure is correct
2. Database migrations are up to date
3. Celery tasks are using the new command

## Related Stories

- **Story 27.1**: Migrate methods to VariantImportProcessor
- **Story 27.2**: Unify image path normalization
- **Story 27.3**: Update Celery tasks integration
- **Story 27.4**: Deprecate legacy import command (this migration)
- **Story 27.5**: Remove legacy command (planned)
- **Story 27.6**: Documentation audit and update
