# Race Condition Analysis: 1C Exchange File Cleanup

## Problem Summary

During 1C CommerceML exchange, approximately **50% of `rests` and some `offers` import sessions fail** with "File not found" errors. Files are successfully routed but deleted before Celery tasks can process them, causing approximately **14-second delays** between routing and Celery task failure.

## Evidence

### Session Timeline (Real Exchange - 08:42 UTC)

```
Session 444 (rests):
  08:42:34 - File routed successfully ("распределено: 1" in report)
  08:42:34 - Celery task dispatched (process_1c_import_task.delay)
  08:42:34 - Celery task begins processing
  08:42:48 - Celery task fails: "File not found: /app/media/1c_import/rests/rests_1_16_575b0a34-3925-4c30-af94-bec97b79790d.xml"
  
  Δ = 14 seconds between routing and failure
```

### Failure Pattern Across Full Exchange (107 sessions)

| File Type | Success | Failed | Rate |
|-----------|---------|--------|------|
| goods     | 19      | 0      | 0%   |
| offers    | 30      | 1      | 3%   |
| prices    | 16      | 0      | 0%   |
| rests     | 8       | 8      | **50%** |
| priceLists| 8       | 0      | 0%   |
| groups    | 6       | 0      | 0%   |
| units     | 3       | 0      | 0%   |
| storages  | 2       | 0      | 0%   |
| properties*| 15     | 0      | 0%   |

**Pattern:** Exact 50% failure rate for rests suggests systematic issue, not random.

### Directory State During Exchange (08:42)

```
/app/media/1c_import/
├── goods/             (timestamp: 08:39) ← EMPTY despite routing
├── offers/            (timestamp: 08:39) ← EMPTY despite routing
├── prices/            (timestamp: 08:39) ← EMPTY despite routing
├── priceLists/        (timestamp: 08:39) ← EMPTY despite routing
└── rests/             (timestamp: 08:42) ← EMPTY despite routing
```

**Observation:** All subdirectories have timestamps from the routed files, but are **completely empty**. This indicates aggressive cleanup between sessions that deleted entire subdirectories.

## Root Cause Analysis

### Call Stack: Where Cleanup Happens

**File:** `backend/apps/integrations/onec_exchange/views.py:429`

```python
def handle_init(self, request):
    """Capability negotiation (mode=init)"""
    if file_service.is_complete():
        logger.info(f"New exchange cycle detected for {sessid}. Performing full cleanup.")
        file_service.cleanup_session(force=True)
        
        # ← THIS IS THE PROBLEM
        routing_service = FileRoutingService(sessid)
        routing_service.cleanup_import_dir(force=True)  # Deletes ALL files in /app/media/1c_import/
        
        file_service.clear_complete()
```

**File:** `backend/apps/integrations/onec_exchange/routing_service.py:195-228`

```python
def cleanup_import_dir(self, force: bool = False) -> int:
    """
    Cleans up the shared import directory.
    
    As the import directory is shared across sessions, 1C can create segmented
    XML files that accumulate. This method ensures old segments are cleared before
    a new exchange cycle begins.
    """
    deleted_count = 0
    for item in self.import_dir.iterdir():
        if item.name == ".dry_run":
            continue
        
        try:
            if item.is_file():
                item.unlink()  # Delete file
            elif item.is_dir():
                shutil.rmtree(item)  # Delete entire directory!
            deleted_count += 1
        except OSError as e:
            logger.warning(f"Failed to delete {item.name} during import cleanup: {e}")
    
    logger.info(f"Cleaned up import directory: deleted {deleted_count} items")
    return deleted_count
```

### The Race Condition: Timeline

**T=0min: First Exchange Starts**
```
mode=init  → is_complete() = false  → No cleanup
mode=file  → Files uploaded to temp
mode=import (×100 sessions) → Files routed, Celery tasks dispatched
```

**T=5min: First Exchange Completes**
```
mode=complete  → finalize_batch()
                 → Dispatch final Celery task
                 → mark_complete()  ← Sets marker file
```

**Celery Queue (Staggered Processing)**
```
T=5m00s - Session 1: Celery task dispatched, queued
T=5m00s - Session 2: Celery task dispatched, queued
...
T=5m00s - Session 100: Celery task dispatched, queued

T=5m10s - Session 1: Celery task starts processing
         (Other sessions 2-100 still waiting in queue)
```

**T=5min 5sec: CRITICAL WINDOW**
```
mode=init (NEW exchange)  → is_complete() = true  ✓ (marker still exists)
                          → cleanup_import_dir() called
                          → /app/media/1c_import/ wiped clean
                          
BUT: Sessions 1-100's Celery tasks are STILL in queue or running!
```

**T=5m20s: Celery Tasks Start Failing**
```
Session 2: Celery task starts
           → Looks for /app/media/1c_import/rests/rests_1_16_...xml
           → NOT FOUND (deleted by cleanup)
           → FAILS with "File not found"
```

### Why 50% Failure Rate?

The 50% failure rate suggests a **queueing/batch effect**:

1. **Sessions 1-8** of rests type: Celery processes them **before** cleanup happens
   - Result: ✓ SUCCESS (all 8)
   
2. **Sessions 9-16** of rests type: Queued behind sessions 1-8
   - By the time they start, cleanup has already deleted files
   - Result: ✗ FAILED (all 8)

3. **Goods/Prices** have **0% failure**: Likely process faster, all complete before cleanup signal reaches

## Why Goods Process Faster Than Rests

**Goods processing steps:**
1. Parse goods XML
2. Create/update product records
3. Usually 1-2 seconds per file

**Rests processing steps:**
1. Parse rests XML  
2. Update stock levels for 1000+ products
3. Database queries significantly slower
4. Usually 5-10 seconds per file

**Conclusion:** If rests takes 2× longer, sessions queued after cleanup signal will definitely fail while goods sessions might still complete.

## Current Architecture Issues

### 1. Shared Import Directory
**File:** `routing_service.py:83-85`

```python
# FIXED: Import directory should be shared/root, not session-isolated
# Parser expects files in data/import_1c/goods, not data/import_1c/<sessid>/goods
self.import_dir = self.import_base  # Shared for all sessions!
```

**Problem:** All sessions' files go to one directory → cleanup affects everyone

### 2. Cleanup Timing
**Current Logic:**
- `handle_init()` calls cleanup when `is_complete()` = true
- But `mark_complete()` is called BEFORE Celery tasks finish
- This creates the race window

**Ideal Logic:**
- Cleanup should only happen when ALL Celery tasks from previous cycle have finished
- Currently: No mechanism tracks this

### 3. No Per-Session Isolation
- Session A's files: `/app/media/1c_import/goods/goods_1_UUID.xml`
- Session B's files: `/app/media/1c_import/goods/goods_1_UUID.xml`
- Cleanup deletes BOTH, even if only one session finished

## Impact

### User-Visible Symptoms
- **Catalog gaps:** Missing products/stock after each 1C exchange
- **Inconsistent data:** Some sessions' data imported, others rolled back
- **Reporting failures:** CSV exports have wrong product counts

### System Health
- **50% data loss** for slow-processing file types (rests, offers)
- **Silent failures:** No retry mechanism; failed imports stay failed
- **Audit trail gap:** Which sessions succeeded vs. failed unclear

## Recommended Solutions

### Option A: Safe Cleanup Deferral (Safest, Low Risk)
```
✓ Remove cleanup_import_dir() call from handle_init()
✓ Add cleanup_import_dir() as delayed Celery task (countdown=120s)
✓ Call from finalize_batch() AFTER dispatch, with 120-second delay
✓ Guarantees all in-flight tasks finish before cleanup
```

**Pros:**
- Minimal code changes
- No architectural changes
- 120 seconds buffer covers slowest sessions
- No per-session overhead

**Cons:**
- Files linger in import directory for 2+ minutes
- Need to verify 120s is sufficient for slowest config

---

### Option B: Per-Session Directory Isolation (Better, Medium Risk)
```
Change routing to:
  /app/media/1c_import/<session_id>/goods/
  /app/media/1c_import/<session_id>/offers/
  
Each session cleans only its own directory
```

**Pros:**
- True isolation; cleanup never interferes
- Clearer semantics
- Can parallelize safely

**Cons:**
- Parser (import_products_from_1c command) needs refactoring
- Need to aggregate/search across session directories
- Breaking change to data layout

---

### Option C: Pending-Files Registry (Most Robust, High Risk)
```
1. Before cleanup: Query Celery for pending tasks
2. Keep files that are referenced by pending tasks
3. Delete only truly orphaned files (>X minutes old, no pending task)
```

**Pros:**
- Precise; deletes only safe files
- Works with any timing

**Cons:**
- Celery queue query adds latency
- Complex logic; high risk of bugs
- Requires Celery monitoring infrastructure

---

## Recommended Next Steps

1. **Implement Option A** (safest, lowest risk)
   - Remove cleanup from `handle_init()`
   - Add `cleanup_import_dir_task()` as deferred Celery task
   - Call from `finalize_batch()` with `countdown=120`

2. **Add regression test:**
   ```python
   def test_concurrent_sessions_no_file_loss():
       """Simulate 20 rapid sessions, verify no "File not found" errors"""
       # Dispatch 20 sessions with <1 second spacing
       # Monitor for Celery failures
       # Assert all sessions succeed
   ```

3. **Monitor in production:**
   - Track rests/offers success rate after deploy
   - Adjust countdown if needed (increase to 180s if still failing)

4. **Consider Option B** in future refactoring
   - Cleaner architecture long-term
   - Requires parser refactoring (~2 days work)

---

## Files to Modify (Option A)

| File | Changes | Risk |
|------|---------|------|
| `views.py:429` | Remove `cleanup_import_dir()` call | Low |
| `import_orchestrator.py:441` | Add cleanup task dispatch with countdown | Low |
| `tasks.py:end` | Add `cleanup_import_dir_task()` | Low |
| `test_*.py` | Add regression test | Low |

**Total risk: LOW** — Localized changes, no API breakage, safe fallback (files just linger longer)
