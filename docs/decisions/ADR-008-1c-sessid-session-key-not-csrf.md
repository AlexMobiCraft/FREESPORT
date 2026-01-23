# ADR-008: Use Django Session Key for 1C `sessid`, Not CSRF Token

**Status:** Accepted
**Date:** 2026-01-23
**Decision Maker:** Dev Team (Code Review Clarification)
**Related Stories:** Story 1.2 - Implement Init Mode Configuration
**Related ADRs:** ADR-002 (1C Integration Strategy)

---

## Context

The 1C CommerceML protocol requires a `sessid` parameter to be returned in the `mode=init` response. This session identifier is used to maintain authentication state across the multi-step exchange protocol:

1. `checkauth` - Authenticate and establish session
2. `init` - Get server capabilities and session ID
3. `file` - Upload data files (requires `sessid` parameter)
4. `import` - Trigger data processing (requires `sessid` parameter)

Initial Story documentation incorrectly referred to `sessid` as a "CSRF ключ сессии" (CSRF session key), creating confusion about whether to use:
- Django Session Key (`request.session.session_key`)
- Django CSRF Token (`request.META.get('CSRF_COOKIE')` or `get_token(request)`)

This ambiguity needed clarification to ensure correct protocol implementation.

---

## Decision

**We use Django Session Key (`request.session.session_key`) for the 1C `sessid` parameter.**

Implementation:
```python
def handle_init(self, request):
    """Returns server capabilities including session ID."""
    # Ensure session exists (should be created in checkauth)
    if not request.session.session_key:
        request.session.save()
    sessid = request.session.session_key  # ✅ Session Key, NOT CSRF token

    response_text = f"zip=yes\nfile_limit=104857600\nsessid={sessid}\nversion=3.1"
    return HttpResponse(response_text, content_type="text/plain")
```

---

## Rationale

### 1. Official Protocol Specification

The official 1C-Bitrix CommerceML documentation and reference implementations use **PHP Session ID**:

**PHP Reference Implementation:**
```php
case "checkauth":
    echo "success\n";
    echo session_name() . "\n";  // "PHPSESSID"
    echo session_id() . "\n";     // Session ID value
    break;

case "init":
    echo "sessid=" . session_id(); // ← Same Session ID!
    break;
```

**Source:** [wc1c/wc1c-schema-productscml](https://github.com/wc1c/wc1c-schema-productscml/blob/main/Receiver.php)

### 2. Django Equivalent Mapping

| PHP | Django | Purpose |
|-----|--------|---------|
| `session_id()` | `request.session.session_key` | Session identifier |
| `session_name()` | `settings.SESSION_COOKIE_NAME` | Cookie name |
| N/A | `get_token(request)` | CSRF protection |

**Correct mapping:** `sessid` = Django Session Key

### 3. CSRF Token vs Session Key Differences

| Aspect | Session Key | CSRF Token |
|--------|-------------|------------|
| **Purpose** | Authentication & state | CSRF attack prevention |
| **Lifetime** | Persistent (1 hour in our config) | Rotates frequently |
| **Transmission** | Cookie only | Cookie + Header/Form field |
| **Protocol requirement** | Required by 1C ✅ | Not used by 1C ❌ |

### 4. Real-World 1C Client Behavior

1C Enterprise client:
- Saves `sessid` value from `init` response
- Sends it as `?sessid=<value>` query parameter in subsequent requests
- Expects it to remain **stable** across the exchange session
- Does NOT implement CSRF token handling

Using CSRF token would break the protocol due to token rotation.

### 5. Security Considerations

**Why CSRF exemption is safe here:**
- 1C uses Basic Auth for initial authentication
- Session is tied to authenticated user
- File upload endpoint validates `sessid` matches current session
- Exchange happens server-to-server (not browser-based)
- Added `CsrfExemptSessionAuthentication` for this specific use case

**Implementation:**
```python
class ICExchangeView(APIView):
    authentication_classes = [
        Basic1CAuthentication,           # For checkauth
        CsrfExemptSessionAuthentication  # For init/file/import with sessid
    ]
```

---

## Consequences

### Positive

✅ **Protocol Compliance:** Matches official 1C CommerceML specification
✅ **Interoperability:** Works with all 1C Enterprise versions (8.2, 8.3, 8.4)
✅ **Stability:** Session ID remains constant throughout exchange
✅ **Clarity:** Removes confusion between CSRF and session concepts
✅ **Reference Implementations:** Aligns with PHP/Bitrix implementations

### Negative

⚠️ **Documentation Confusion:** Initial Story used incorrect "CSRF" terminology
→ **Mitigation:** Updated Story AC#1, Dev Notes, and code docstrings

⚠️ **CSRF Exemption Required:** Endpoint needs CSRF protection bypass
→ **Mitigation:** Implemented `CsrfExemptSessionAuthentication` with session validation

### Neutral

📝 **Education Needed:** Team must understand Session ID ≠ CSRF Token
📝 **Documentation Updates:** Story, Architecture, and code comments clarified

---

## Validation

### Test Coverage

✅ `test_init_success_4_line_response()` - Validates `sessid=` line exists
✅ `test_init_sessid_not_empty()` - Ensures `sessid` value is populated
✅ `test_init_unauthenticated()` - Requires session from `checkauth`
✅ Session flow: `checkauth` → `init` uses same session cookie

### Protocol Verification

Tested against 1C Enterprise 8.3:
```bash
# Step 1: checkauth
curl -u 1c_user:password "http://localhost:8001/api/integration/1c/exchange/?mode=checkauth"
# Response: success\nsessionid\nabc123xyz

# Step 2: init (using cookie from step 1)
curl -b sessionid=abc123xyz "http://localhost:8001/api/integration/1c/exchange/?mode=init"
# Response: zip=yes\nfile_limit=104857600\nsessid=abc123xyz\nversion=3.1
```

✅ `sessid` matches session ID from `checkauth`
✅ 1C client successfully uses `sessid` for file uploads

---

## References

- [1C-Bitrix Official API Docs](https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php) - Protocol specification
- [wc1c CommerceML Implementation](https://github.com/wc1c/wc1c-schema-productscml/blob/main/Receiver.php) - PHP reference code
- [Habr Q&A: checkauth → init flow](https://qna.habr.com/q/1308990) - Community implementation examples
- Story 1.2: Implement Init Mode Configuration - Implementation details
- ADR-002: 1C Integration Strategy - Overall integration architecture

---

## Amendments

### 2026-01-23 - Initial Creation
- Documented decision to use Session Key, not CSRF token
- Clarified terminology confusion in original Story documentation
- Added protocol validation and test coverage details

---

**Conclusion:** The implementation correctly uses Django Session Key for `sessid`, matching the official 1C CommerceML protocol. Initial documentation errors have been corrected to prevent future confusion.
