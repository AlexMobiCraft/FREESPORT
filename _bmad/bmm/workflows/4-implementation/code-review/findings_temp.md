**🔥 CODE REVIEW FINDINGS, Alex!**

**Story:** `_bmad-output/implementation-artifacts/5-1-order-status-import-service.md`
**Git vs Story Discrepancies:** 0 found
**Issues Found:** 0 High, 2 Medium, 2 Low

## 🔴 CRITICAL ISSUES
*None found. Implementation closely follows the story.*

## 🟡 MEDIUM ISSUES
- **Logic / Data Integrity**: **Payment Status Regression Risk**. In `_process_order_update`, `payment_status` is forced to `"paid"` if `paid_at` arrives from 1C. If the order was previously `"refunded"` (e.g. via site admin), this logic overwrites it back to `"paid"`, potentially causing financial data confusion.
  - *File*: `backend/apps/orders/services/order_status_import.py:609`
- **Robustness**: **Batch handling crashes on DB error**. The `_bulk_fetch_orders` call inside the `process` loop is not wrapped in `try/except`. If a transient DB error (like a lock timeout) occurs during the `select_for_update` fetch, the entire import process crashes. It should catch `OperationalError`, log it, record a batch error, and continue to the next batch.
  - *File*: `backend/apps/orders/services/order_status_import.py:149`

## 🟢 LOW ISSUES
- **Test Quality**: **N+1 Test lacks assertion**. `test_bulk_fetch_orders_optimization` in `test_order_status_import_db.py` creates orders and calls `process`, but doesn't actually verify that `N` queries weren't executed (missing `self.assertNumQueries` context). It only proves functional correctness, not performance optimization.
  - *File*: `backend/tests/integration/test_order_status_import_db.py:210`
- **Observability**: **Ambiguous 1C timestamp semantics**. `sent_to_1c_at` is only set when `sent_to_1c` changes from `False` to `True`. Subsequent updates from 1C do not update a specific "last synced with 1C" timestamp (only generic `updated_at`), making it harder to debug "when did 1C last touch this order?".
  - *File*: `backend/apps/orders/services/order_status_import.py:649`
