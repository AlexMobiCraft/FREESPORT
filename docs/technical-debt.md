# Technical Debt Registry

This document tracks technical debt items identified during development and review, which are deferred for future resolution.

## 2026-02-02

### [MEDIUM] Data Accuracy in Order Export
- **Description:** `OrderExportService` ignores `order.customer_email` for registered users, using only `user.email`. If a B2B user provides a specific contact email for an order that differs from their account email, it is not exported to 1C.
- **Affected Component:** `backend/apps/orders/services/order_export.py`
- **Impact:** 1C may send notifications to the wrong email address if the B2B buyer intended a different contact for a specific order.
- **Source:** Code Review (Cycle 5) for Story 4.3
