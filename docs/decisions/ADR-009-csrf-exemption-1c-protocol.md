# ADR-009: CSRF Exemption for 1C Exchange Protocol

## Status
Accepted

## Context
The 1C-Bitrix data exchange protocol (CommerceML) is a stateless-like HTTP protocol that uses Basic Authentication for the initial synchronization step (`?mode=checkauth`) and then relies on session cookies for subsequent steps (file upload, import trigger).

1C:Enterprise (the client) does not support CSRF tokens as they are typically used in web applications (extracted from HTML/meta-tags and sent back in headers). Forcing CSRF validation on 1C exchange endpoints would break the integration.

## Decision
We decided to implement a custom authentication class `CsrfExemptSessionAuthentication` that extends DRF's `SessionAuthentication` but overrides the `enforce_csrf` method to bypass CSRF checks.

This class is used strictly on the 1C Exchange API view:
`backend/apps/integrations/onec_exchange/views.py`

## Consequences

### Security
1. **Scope:** The exemption is only applied to the 1C exchange endpoint.
2. **Additional Protections:**
   - **Permission Check:** All requests must still pass `Is1CExchangeUser` permission check, which ensures the user has `can_exchange_1c` permission (and is staff/admin by default).
   - **Authentication:** Requests must be authenticated via either the active session (cookie) established during `checkauth` or valid Basic Auth.
   - **CORS/Origin:** This endpoint is intended for machine-to-machine communication with 1C, not for browser-based access.

### Maintenance
- Developers must ensure that no other general-purpose APIs use `CsrfExemptSessionAuthentication`.
- Any changes to the 1C protocol should be audited against this exemption.

## References
- [1C-Bitrix Protocol Docs](https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php)
- ADR-008: Use Django Session Key for 1C sessid
