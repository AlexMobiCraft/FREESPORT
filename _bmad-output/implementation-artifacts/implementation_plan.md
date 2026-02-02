# Implementation Plan - Review Fixes Story 4.3

Addressing code review findings for Story 4.3 (View Handlers).

## User Review Required

> [!IMPORTANT]
> **Guest Data Sources:**
> We will use `order.customer_name` -> `Наименование` / `ПолноеНаименование`
> `order.customer_email` -> `Контакты/Контакт[Тип=Почта]`
> `order.customer_phone` -> `Контакты/Контакт[Тип=Телефон]`
> `user-{order.id}` will be used as the `Ид` for guest counterparties since they have no `onec_id` or `tax_id`.

## Proposed Changes

### Backend

#### [MODIFY] [order_export.py](file:///c:/Users/1/DEV/FREESPORT/backend/apps/orders/services/order_export.py)
- **Guest Order Support**: Update `_create_counterparties_element`.
  - If `order.user` is None:
    - Use `order.customer_name` for Name.
    - Use `order.customer_email/phone` for Contacts.
    - Generate ID as `guest-{order.id}` or `email-hash`.

#### [MODIFY] [import_orchestrator.py](file:///c:/Users/1/DEV/FREESPORT/backend/apps/integrations/onec_exchange/import_orchestrator.py)
- **New Method**: Add `finalize_batch(request)` to `ImportOrchestratorService` (or similar name).
- **Move Logic**: Move the complex transaction/session/file routing logic from `ICExchangeView.handle_complete` here.

#### [MODIFY] [views.py](file:///c:/Users/1/DEV/FREESPORT/backend/apps/integrations/onec_exchange/views.py)
- **Refactor**: Simplify `handle_complete` to just call `ImportOrchestratorService.finalize_batch()`.
- **Imports**: Fix the local import issue in `handle_import` (move `ImportOrchestratorService` to top-level if not already done, though previous step said it was done, the review finding said it resolved one but finding text says it's still there? Wait, the finding text says "Стиль кода: handle_import импортирует...". I need to check if it's already fixed or not. The review finding said `ImportOrchestratorService` moved to top level in `views.py` file list, but let's double check).

## Verification Plan

### Automated Tests
- **Enhance Guest Test**: Update `test_mode_query_includes_guest_orders` in `backend/tests/integration/test_onec_export.py`.
  - Assert that `customer_name`, `email`, and `phone` appear in the generated XML.
- **Regression**: Run all `test_onec_export.py` tests.
  ```bash
  pytest backend/tests/integration/test_onec_export.py
  ```

### Manual Verification
- None required (Backend logic covered by integration tests).
