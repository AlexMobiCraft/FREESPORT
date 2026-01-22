# Story 1.2: Implement Init Mode Configuration

Status: review

## Story

As a 1C Administrator,
I want the site to report its capabilities (zip support, file limits, session key, protocol version),
so that 1C can optimize the data packet size and maintain secure session.

## Acceptance Criteria

1. **Given** An authenticated session with the 1C Exchange Endpoint
   **When** A GET request is sent to `/api/integration/1c/exchange/` with `?mode=init`
   **Then** The response should contain exactly 4 lines in `text/plain` format:
   - Line 1: `zip=yes` (or `zip=no` if disabled)
   - Line 2: `file_limit=<bytes>` (e.g., 104857600 for 100MB)
   - Line 3: `sessid=<CSRF_session_key>`
   - Line 4: `version=3.1` (CommerceML version)
   **And** The response status code should be 200 OK

2. **Given** An unauthenticated request
   **When** A GET request is sent with `?mode=init`
   **Then** The response should be 401 Unauthorized

3. **Given** A request from a user without `can_exchange_1c` permission
   **When** A GET request is sent with `?mode=init`
   **Then** The response should be 403 Forbidden

## Test Cases

| ID  | Scenario | Expected Result |
|-----|----------|-----------------|
| TC1 | Authenticated `?mode=init` | 200 OK, 4-line response with zip, file_limit, sessid, version |
| TC2 | Unauthenticated `?mode=init` | 401 Unauthorized |
| TC3 | User without `can_exchange_1c` | 403 Forbidden |
| TC4 | POST `?mode=init` | 200 OK (same as GET, 1C compatibility) |
| TC5 | Response contains valid `sessid=` | Non-empty session key |
| TC6 | Response contains `version=3.1` | CommerceML version string |
| TC7 | Content-Type header | `text/plain; charset=utf-8` |

## Tasks / Subtasks

- [x] **Task 1: Implement `handle_init()` method** (AC: #1)
  - [x] 1.1: Add `handle_init()` method to `ICExchangeView`
  - [x] 1.2: Read `ZIP_SUPPORT` and `FILE_LIMIT_BYTES` from `settings.ONEC_EXCHANGE`
  - [x] 1.3: Get session key from `request.session.session_key` (CSRF token)
  - [x] 1.4: Add `COMMERCEML_VERSION` to settings (default: "3.1")
  - [x] 1.5: Return 4-line `text/plain` response

- [x] **Task 2: Add mode routing for `init`** (AC: #1)
  - [x] 2.1: Update `get()` to route `mode=init` → `handle_init()`
  - [x] 2.2: Update `post()` to route `mode=init` → `handle_init()` (1C compatibility)

- [x] **Task 3: Update Settings** (AC: #1)
  - [x] 3.1: Add `COMMERCEML_VERSION: "3.1"` to `ONEC_EXCHANGE` dict in `base.py`

- [x] **Task 4: Write Tests** (AC: #1, #2, #3)
  - [x] 4.1: Test successful init with 4-line response format
  - [x] 4.2: Test 401 on unauthenticated request
  - [x] 4.3: Test 403 for user without permission
  - [x] 4.4: Verify `sessid=` contains valid session key
  - [x] 4.5: Verify `version=3.1` is present
  - [x] 4.6: Test POST method works same as GET
  - [x] 4.7: Verify Content-Type is `text/plain`

## Dev Notes

### Response Format (CRITICAL - Updated from Official Docs)

> [!IMPORTANT]
> **Source:** [1С-Битрикс официальная документация](https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php)

1С ожидает **4 строки** в формате `text/plain`:
```
zip=yes
file_limit=104857600
sessid=abc123xyz
version=3.1
```

| Поле | Описание |
|------|----------|
| `zip` | `yes` если сайт принимает ZIP-архивы, иначе `no` |
| `file_limit` | Максимальный размер одного **чанка** в байтах |
| `sessid` | CSRF ключ сессии для последующих запросов |
| `version` | Версия CommerceML (текущая: 3.1) |

### Implementation Pattern (Updated)

```python
def handle_init(self, request):
    """
    Returns server capabilities for 1C data exchange.
    Protocol: https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php
    """
    zip_support = settings.ONEC_EXCHANGE.get('ZIP_SUPPORT', True)
    file_limit = settings.ONEC_EXCHANGE.get('FILE_LIMIT_BYTES', 100 * 1024 * 1024)
    version = settings.ONEC_EXCHANGE.get('COMMERCEML_VERSION', '3.1')
    
    # Ensure session exists
    if not request.session.session_key:
        request.session.save()
    sessid = request.session.session_key
    
    zip_value = 'yes' if zip_support else 'no'
    response_text = f"zip={zip_value}\nfile_limit={file_limit}\nsessid={sessid}\nversion={version}"
    return HttpResponse(response_text, content_type="text/plain")
```

### Settings Update Required

В `backend/freesport/settings/base.py` добавить:
```python
ONEC_EXCHANGE = {
    'SESSION_COOKIE_NAME': 'FREESPORT_1C_SESSION',
    'SESSION_LIFETIME_SECONDS': 3600,
    'FILE_LIMIT_BYTES': 100 * 1024 * 1024,  # 100MB per chunk
    'ZIP_SUPPORT': True,
    'COMMERCEML_VERSION': '3.1',  # ← NEW
}
```

### Protocol Flow Context

```mermaid
sequenceDiagram
    participant 1C as 1С:Предприятие
    participant API as Django API
    
    1C->>API: GET ?mode=checkauth (Basic Auth)
    API-->>1C: success, cookie_name, cookie_value, csrf_key, timestamp
    
    1C->>API: GET ?mode=init (Cookie header)
    API-->>1C: zip=yes, file_limit=104857600, sessid=X, version=3.1
    
    loop For each file chunk
        1C->>API: POST ?mode=file&filename=X (body: chunk data)
        API-->>1C: success
    end
    
    1C->>API: GET ?mode=import&filename=X
    API-->>1C: progress / success / failure
```

### Existing Code Context

**Файл:** `backend/apps/integrations/onec_exchange/views.py`

Session уже создаётся в `handle_checkauth()`:
```python
login(request._request, request.user)
# session.session_key доступен после login()
```

### References

- [Source: 1C-Bitrix Official Docs](https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php) - Protocol specification
- [Source: epics.md#Story-1.2] - Init mode requirements
- [Source: 1-1-setup-1c-exchange-endpoint-and-auth.md] - Previous story patterns
- [Source: settings/base.py#L272-277] - ONEC_EXCHANGE configuration

## Verification

```bash
# 1. Run tests
docker compose exec backend pytest apps/integrations/tests/integration/test_onec_exchange_api.py -v -k init

# 2. Manual verification
curl -v -u 1c_user:password "http://localhost:8001/api/integration/1c/exchange/?mode=init"
# Expected: 200 OK, Content-Type: text/plain
# zip=yes
# file_limit=104857600
# sessid=<session_key>
# version=3.1
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4 (Anthropic)

### Debug Log References

- All 12 tests passed (5 checkauth + 7 init)
- Red-Green-Refactor cycle completed successfully

### Completion Notes List

- ✅ Implemented `handle_init()` method per 1C-Bitrix protocol specification
- ✅ Returns 4-line text/plain response: zip, file_limit, sessid, version
- ✅ Added `COMMERCEML_VERSION: '3.1'` to ONEC_EXCHANGE settings
- ✅ Both GET and POST routed to handle_init() for 1C compatibility
- ✅ Session key retrieved from existing session (created in checkauth)
- ✅ All 7 test cases implemented and passing
- ✅ No regressions in Story 1.1 tests (5 checkauth tests still pass)

### File List

- `backend/apps/integrations/onec_exchange/views.py` — Added handle_init() method, updated get/post routing
- `backend/freesport/settings/base.py` — Added COMMERCEML_VERSION to ONEC_EXCHANGE dict
- `backend/tests/integration/test_onec_exchange_api.py` — Added Test1CInitMode class with 7 test cases (correct location per testing-strategy.md)

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-22 | Story 1.2 implemented: mode=init endpoint with 4-line response | Dev Agent (Claude Sonnet 4) |
