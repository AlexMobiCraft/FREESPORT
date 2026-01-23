# Story 2.1: File Stream Upload

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a System,
I want to accept large binary files via chunked upload without consuming excessive RAM,
so that I can receive the full 1C export archive reliably.

## Acceptance Criteria

1.  **Authenticated Upload Session**
    *   **Given** An authenticated session and a binary file to upload
    *   **When** A POST request is sent to the endpoint with `?mode=file&filename=import.zip&sessid=<session_key>` and binary body
    *   **Then** The file content should be streamed to a temporary file in `MEDIA_ROOT/1c_temp/`
    *   **And** The response should be `success` upon successful write

2.  **Chunked Upload Support**
    *   **Given** Multiple requests are sent with the same filename (representing chunks)
    *   **When** These requests are processed sequentially or concurrently
    *   **Then** The content should be correctly appended to the same physical file in `1c_temp`
    *   **And** The final file size must match the total size of uploaded chunks

3.  **Session Security Validation**
    *   **Given** A POST request with `?mode=file&filename=X&sessid=<key>`
    *   **When** The `sessid` parameter does NOT match `request.session.session_key`
    *   **Then** The response should be 403 Forbidden with body `failure\nInvalid session`

4.  **Missing Parameter Handling**
    *   **Given** A POST request with `?mode=file` without `sessid` parameter
    *   **When** The request is processed
    *   **Then** The response should be 403 Forbidden with body `failure\nMissing sessid`

## Tasks / Subtasks

- [x] Core File Handler Implementation (AC: 1, 2)
  - [x] Update `settings.py` to define `TEMP_DIR` in `ONEC_EXCHANGE` pointing to `MEDIA_ROOT/1c_temp/`
  - [x] Implement `ICExchangeView.post()` handler logic for `mode=file`
  - [x] **Critical:** Create isolated directory for each session: `MEDIA_ROOT/1c_temp/<sessid>/`
  - [x] Create `FileStreamService` with `append_chunk(filename, content)` method
  - [x] Ensure `append_chunk` uses `ab` (append binary) mode for sequential writing

- [x] Security & Validation (AC: 3, 4)
  - [x] Implement `sessid` validation against active request session
  - [x] Ensure 403 responses return the exact expected 1C-compatible text (`failure\n...`)

- [x] Testing & Verification
  - [x] Test TC1: Valid upload with correct sessid (single chunk)
  - [x] Test TC2: Upload with invalid sessid
  - [x] Test TC3: Upload without sessid param
  - [x] Test TC4: Upload 250MB as 3 chunks (simulation)
  - [x] Verify file existence and integrity in `1c_temp` after upload

- [x] Review Follow-ups (AI)
  - [x] [AI-Review][HIGH] Implement streaming request body reading to satisfy NFR2 (remove `request.body` call) [backend/apps/integrations/onec_exchange/views.py:170]
  - [x] [AI-Review][MEDIUM] Implement `FILE_LIMIT_BYTES` validation in the View
  - [x] [AI-Review][MEDIUM] Address reuse/retry risk in `append` mode (consider session cleanup on `init`)
  - [x] [AI-Review][MEDIUM] Update Story File List and Change Log to reflect all modified/deleted files
  - [x] [AI-Review][MEDIUM] Improve tests to verify memory efficiency (e.g. mock read blocks)
  - [x] [AI-Review][LOW] Move local imports in `views.py` to top of file [backend/apps/integrations/onec_exchange/views.py:136]

- [x] Second Review Follow-ups (AI)
  - [x] [AI-Review][HIGH] Fix inefficient I/O loop in `views.py` - use a context manager to open file once per request instead of ensuring dir and opening file for every 64KB chunk.
  - [x] [AI-Review][MEDIUM] Ensure all implementation files (`file_service.py`, tests) are tracked in git.
  - [x] All 36 tests (23 file upload + 13 exchange API) passed with no regressions

- [x] Review Follow-ups (AI)
  - [x] [AI-Review][HIGH] Security: Block public access to `1c_temp` in Nginx configuration [docker/nginx/conf.d/default.conf:45]
  - [x] [AI-Review][MEDIUM] Documentation: Fix Story File List to correctly mark new files as "Added" instead of "Modified"
  - [x] [AI-Review][MEDIUM] Refactor: Use `django.contrib.auth.get_backends()[0]` instead of hardcoded backend path in `handle_checkauth`

- [x] Review Follow-ups (AI) - 4
  - [x] [AI-Review][HIGH] Concurrent Upload Corruption: Fix file corruption risk in interleaved concurrent uploads by using file locking or forcing sequential processing [backend/apps/integrations/onec_exchange/views.py]
  - [x] [AI-Review][HIGH] Information Disclosure: Prevent leaking internal error details in global exception handler [backend/apps/integrations/onec_exchange/views.py]
  - [x] [AI-Review][MEDIUM] Unsafe Test Settings: Use `mock.patch.dict` for `settings.ONEC_EXCHANGE` in tests to ensure thread safety [backend/tests/integration/test_1c_file_upload.py]
  - [x] [AI-Review][MEDIUM] Nginx Config Ambiguity: Simplify `deny all; return 404;` to just `return 404;` for strict compliance [docker/nginx/conf.d/default.conf]
  - [x] [AI-Review][LOW] File Permissions: Explicitly set file permissions in `FileStreamService` (e.g., 0o644) instead of relying on umask [backend/apps/integrations/onec_exchange/file_service.py]

## Dev Notes

### Architecture Patterns & Constraints

-   **Memory Efficiency:** (NFR2 from Epics) Do NOT read the entire request body into memory. Use Django's `streaming_content` or read chunks from `request` directly if possible, or rely on standard Django file upload handlers but ensure they are configured for large files.
-   **Directory Structure:** Temporary files MUST go to `1c_temp` (as defined in `architecture.md` implied flow). Do not process or unpack them yet (that is Story 2.2).
-   **Response Format:** 1C expects `text/plain` with `success` or `failure\nMessage`. DO NOT return JSON.
-   **Idempotency:** Re-uploading a chunk (if 1C retries) might append duplicates if not handled carefully, but standard 1C behavior assumes sequential confirmed uploads. We assume "append" logic. *Clarification: Standard Django upload handling typically overwrites or creates new. For "append" behavior across multiple requests, we need explicit handling or we assume 1C sends one request per file if not strictly "chunked" in the HTTP sense.*
    *   *Correction based on 1C protocol:* 1C sends the file in parts using standard POST requests, expecting the server to append them. `mode=file` often implies we just write what we get to the file named `filename`. If the file exists, we *append*.
-   **Session Isolation:** (From Party Mode) Store files in `1c_temp/<sessid>/` to prevent collisions between concurrent sessions or stuck previous uploads.
-   **Cleanup Strategy:** (From Party Mode) We implement TTL cleanup as a separate Tech Debt task. For this story, rely on session isolation to prevent "stuck" files from blocking new imports.

### Project Structure Notes

-   **New Service:** `apps/products/services/import_1c/file_service.py` (or similar) recommended for file operations.
-   **View:** Continue modifying `apps/products/views/integration_1c.py` (`ICExchangeView`).

## Dev Agent Record

### Agent Model Used

Antigravity (Google Deepmind) / Dev Agent Mode

### Debug Log References

N/A

### Completion Notes List

-   [x] Confirmed `1c_temp` directory creation (via `FileStreamService._ensure_session_dir()`)
-   [x] Verified `sessid` check logic (403 for missing/invalid sessid)
-   [x] Tested multi-chunk append behavior (TC4 with 3 chunks passed)
-   [x] Added security: filename sanitization prevents directory traversal attacks
-   [x] 15 new tests passed + 13 existing tests passed (no regressions)
-   [x] **[AI-Review]** Implemented streaming body reading using `wsgi_request.read(chunk_size)` - 64KB chunks
-   [x] **[AI-Review]** Added `FILE_LIMIT_BYTES` validation with 413 response on exceeded limit
-   [x] **[AI-Review]** Added `cleanup_session()` method to `FileStreamService`, called during `init` mode
-   [x] **[AI-Review]** Moved local imports to module level in `views.py`
-   [x] **[AI-Review]** Added tests for FILE_LIMIT_BYTES (test_file_limit_exceeded), streaming (test_streaming_upload_uses_chunked_reads), cleanup_session
-   [x] All 33 tests (20 file upload + 13 exchange API) passed with no regressions
-   [x] **[Second AI-Review]** Added `FileWriter` class and `open_for_write()` context manager for efficient I/O
-   [x] **[Second AI-Review]** Refactored `views.py` to use context manager - file opens once per request instead of per chunk
-   [x] **[Second AI-Review]** Verified all files tracked in git (file_service.py, test_1c_file_upload.py)
-   [x] All 36 tests (23 file upload + 13 exchange API) passed with no regressions
-   [x] **[Third AI-Review]** Added Nginx security rule to block public access to /media/1c_temp/ (returns 404)
-   [x] **[Third AI-Review]** Fixed File List to correctly mark new files as "Added" instead of "Modified"
-   [x] **[Third AI-Review]** Refactored handle_checkauth to use get_backends()[0] instead of hardcoded backend path
-   [x] All 36 tests (23 file upload + 13 exchange API) passed with no regressions after third review fixes
-   [x] **[Fourth AI-Review]** Added FileLock class with cross-platform lock file pattern (O_EXCL atomic creation)
-   [x] **[Fourth AI-Review]** Integrated file locking into open_for_write() context manager
-   [x] **[Fourth AI-Review]** Added explicit file permissions (0o644) via os.open() in open_for_write()
-   [x] **[Fourth AI-Review]** Fixed information disclosure - generic "Internal server error" instead of str(e)
-   [x] **[Fourth AI-Review]** Added FileLockError handler returning 503 "File busy - retry later"
-   [x] **[Fourth AI-Review]** Refactored tests to use monkeypatch.setitem and mock.patch.dict for thread safety
-   [x] **[Fourth AI-Review]** Simplified Nginx 1c_temp location to just `return 404;`
-   [x] All 26 file upload tests passed with no regressions after fourth review fixes

### File List

-   `backend/freesport/settings/base.py` (Modified: added `TEMP_DIR` to `ONEC_EXCHANGE`)
-   `backend/apps/integrations/onec_exchange/views.py` (Modified: streaming body read, FILE_LIMIT_BYTES validation, session cleanup in init, dynamic auth backend)
-   `backend/apps/integrations/onec_exchange/file_service.py` (Added: FileStreamService with append_chunk, cleanup_session, open_for_write context manager)
-   `backend/tests/integration/test_1c_file_upload.py` (Added: 23 tests for file upload, streaming, cleanup, context manager)
-   `docker/nginx/conf.d/default.conf` (Modified: block public access to /media/1c_temp/)

## Change Log

- 2026-01-23: Addressed 6 code review findings (1 HIGH, 4 MEDIUM, 1 LOW) - all items resolved
- 2026-01-23: Addressed 2 second code review findings (1 HIGH, 1 MEDIUM) - efficient I/O with context manager
- 2026-01-23: Addressed 3 third code review findings (1 HIGH, 2 MEDIUM) - Nginx security, File List fix, auth backend refactor
- 2026-01-23: Addressed 5 fourth code review findings (2 HIGH, 2 MEDIUM, 1 LOW) - file locking, info disclosure, test safety, nginx simplification, file permissions

