---
stepsCompleted: ['Define Requirements', 'Design Epics', 'Create Stories']
inputDocuments: ['docs/prd/1c-http-exchange.md', 'docs/integrations/1c/architecture.md']
---

# FREESPORT - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for FREESPORT, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: (Endpoint) Реализовать единую точку входа (endpoint), например `/api/v1/integration/1c/exchange/`.
FR2: (Authentication - checkauth) Поддержка Basic Auth (login/password). Ответ: `success`, `Cookie_Name`, `Cookie_Value`.
FR3: (Initialization - init) Прием параметров `zip=yes/no` и `file_limit`. Ответ: `zip=zip` (если поддерживаем) и `file_limit=<bytes>`.
FR4: (File Upload & Organization - file) Прием бинарного содержимого (chunked upload). Сборка полного файла/архива во временной директории.
FR5: (Unpacking) Если передан ZIP-архив, он разархивируется с сохранением сложной структуры папок 1С (как описано в Architecture.md: `groups/`, `goods/` и т.д.).
FR6: (Persistence) Перемещение файлов из временной директории в целевую `MEDIA_ROOT/1c_import/` с сохранением структуры.
FR7: (Import Trigger - import) Запуск процессинга полученного файла (асинхронно через Celery).
FR8: (Logging) Полное логирование запросов/ответов.

### NonFunctional Requirements

NFR1: (Iterative Dev) Разработка должна вестись **законченными, проверяемыми этапами** (Stories). Нельзя переходить дальше без верификации предыдущего шага.
NFR2: (Performance) Обработка загрузки больших файлов (hundreds of MBs) через stream writing без переполнения памяти.
NFR3: (Security) Доступ к эндпоинту только для пользователей с ролью `admin` или специальным пермишеном.

### Additional Requirements

- **Strict Folder Structure:** The system must respect the CommerceML structure (`goods/`, `offers/`, `propertiesGoods/`, etc.) during unpacking (Source: Architecture.md Appendix A).
- **Session-Based Import:** Use `ImportSession` model for atomicity during import processing (Source: Architecture.md 2.2).
- **Service Layer:** Logic should be split between `DataParser` and `DataProcessor` (Source: Architecture.md 2.2).
- **Response Format:** 1C expects `text/plain` responses separated by newlines, NOT JSON (Source: PRD).

### FR Coverage Map

FR1: Epic 1 - Endpoint setup
FR2: Epic 1 - Authentication logic
FR3: Epic 1 - Initialization response
FR4: Epic 2 - File upload & streaming
FR5: Epic 2 - ZIP unpacking
FR6: Epic 2 - Folder structure persistence
FR7: Epic 3 - Import task triggering
FR8: Epic 3 - Action logging

## Epic List

### Epic 1: 1C Transport & Authentication
**Goal:** Enable 1C Enteprise to establish a secure connection with the platform and perform protocol initialization.
**FRs covered:** FR1, FR2, FR3, NFR3

### Epic 2: Secure Stream Upload & Structure Handling
**Goal:** Enable reliable transfer of large data archives and ensuring they are unpacked into the strict directory structure required by the import engine.
**FRs covered:** FR4, FR5, FR6, NFR2

### Epic 3: Asynchronous Import Triggering
**Goal:** Connect the transport layer to the business logic by triggering specific Celery tasks when import commands are received.
**FRs covered:** FR7, FR8, NFR1

## Epic 1: 1C Transport & Authentication

Enable 1C Enteprise to establish a secure connection with the platform and perform protocol initialization.

### Story 1.1: Setup 1C Exchange Endpoint & Auth

As a 1C Administrator,
I want the website to accept connection credentials via standard protocol,
So that I can establish a secure session for data transfer.

**Acceptance Criteria:**

**Given** The Django application is running and configured with a 1C technical user
**When** A GET request is sent to `/api/integration/1c/exchange/` with `?mode=checkauth` and valid Basic Auth headers
**Then** The response status code should be 200 OK
**And** The response content-type should be `text/plain`
**And** The response body must contain exactly "success" followed by the cookie name and cookie value on separate lines
**And** Invalid credentials should return 401 Unauthorized

### Story 1.2: Implement Init Mode Configuration

As a 1C Administrator,
I want the site to report its capabilities (zip support, file limits),
So that 1C can optimize the data packet size.

**Acceptance Criteria:**

**Given** An authenticated session with the 1C Exchange Endpoint
**When** A GET request is sent with `?mode=init`
**Then** The response should contain `zip=yes` indicating ZIP support
**And** The response should contain `file_limit=<value>` (e.g., 100MB in bytes)
**And** The response format must be `text/plain`

**Test Cases:**

| ID | Scenario | Expected Result |
|----|----------|-----------------|
| TC1 | Authenticated request `?mode=init` | 200 OK, `zip=yes\nfile_limit=104857600` |
| TC2 | Unauthenticated request `?mode=init` | 401 Unauthorized |
| TC3 | Request from user without `can_exchange_1c` permission | 403 Forbidden |

## Epic 2: Secure Stream Upload & Structure Handling

Enable reliable transfer of large data archives and ensuring they are unpacked into the strict directory structure required by the import engine.

### Story 2.1: File Stream Upload

As a System,
I want to accept large binary files via chunked upload without consuming excessive RAM,
So that I can receive the full 1C export archive reliably.

**Acceptance Criteria:**

**Given** An authenticated session and a binary file to upload
**When** A POST request is sent to the endpoint with `?mode=file&filename=import.zip` and binary body
**Then** The file content should be streamed to a temporary file in `MEDIA_ROOT/1c_temp/`
**And** If multiple requests are sent with the same filename (chunked), the content should be appended correctly
**And** The response should be `success` upon successful write

**Test Cases:**

| ID | Scenario | Expected Result |
|----|----------|-----------------|
| TC6 | Upload interrupted at 50%, then resumed | Temp file preserved, next chunk appends correctly |
| TC7 | Upload started but no more chunks (timeout) | Temp file cleaned up after configurable TTL |

### Story 2.2: Zip Unpacking with Structure

As a Backend Developer,
I want the system to unpack the uploaded ZIP and distribute files into the specific folders required by the architecture,
So that the parsing logic can find `goods.xml` in `goods/` and images in their correct paths.

**Acceptance Criteria:**

**Given** A fully uploaded file in the temporary directory
**When** The filename ends with `.zip` extension (case-insensitive)
**Then** The archive must be automatically unpacked upon upload completion
**And** Files must be moved to `MEDIA_ROOT/1c_import/` PRESERVING the folder structure from the archive
**And** Existing files in `1c_import/` should be cleaned up or overwritten as per policy
**And** `goods/goods.xml` should end up at `MEDIA_ROOT/1c_import/goods/goods.xml`

**Given** A fully uploaded file with non-archive extension (e.g., `.xml`)
**When** The upload completes
**Then** The file should be moved to the appropriate folder in `MEDIA_ROOT/1c_import/` based on filename:
- `goods.xml` → `1c_import/goods/goods.xml`
- `offers.xml` → `1c_import/offers/offers.xml`
- `prices.xml` → `1c_import/prices/prices.xml`
- `rests.xml` → `1c_import/rests/rests.xml`
- `groups.xml` → `1c_import/groups/groups.xml`
- Other files → `1c_import/<filename>`

**Test Cases (from Party Mode Review):**

| ID | Input | Expected Result |
|----|-------|-----------------|
| TC1 | `import.zip` (valid ZIP) | Unpacked to `1c_import/` with folder structure |
| TC2 | `import.ZIP` (uppercase) | Should also unpack (case-insensitive) |
| TC3 | `goods.xml` | Moved directly to `1c_import/goods/goods.xml` |
| TC4 | `fake.zip` (not a valid ZIP) | Error handling, log warning, cleanup temp |
| TC5 | Corrupted ZIP archive | Graceful failure, cleanup temp, return error |



## Epic 3: Asynchronous Import Triggering

Connect the transport layer to the business logic by triggering specific Celery tasks when import commands are received.

### Story 3.1: Async Import Orchestration

As a System,
I want to trigger the import process asynchronously when 1C sends the import command,
So that the 1C connection doesn't timeout while we process the data.

**Acceptance Criteria:**

**Given** Files are successfully uploaded and unpacked in `MEDIA_ROOT/1c_import/`
**When** A GET request is sent with `?mode=import&filename=<any_filename>`
**Then** An `ImportSession` record should be created with status `pending`
**And** A single universal Celery task `process_1c_import_task` should be dispatched
**And** The task should analyze `1c_import/` directory and process all available files
**And** The HTTP response should immediately return `success`
**And** A log entry should be created recording the import start

**Given** The import task completes successfully
**Then** The `ImportSession` status should be updated to `completed`

**Given** The import task fails with an error
**Then** The `ImportSession` status should be updated to `failed` with error details
**And** Partial changes should be rolled back to maintain data consistency

**Test Cases:**

| ID | Scenario | Expected Result |
|----|----------|-----------------|
| TC1 | `mode=import` with valid files in `1c_import/` | 200 success, ImportSession created, task dispatched |
| TC2 | `mode=import` but `1c_import/` is empty | 200 success, task logs "no files to process" |
| TC3 | Import task fails mid-process | ImportSession status = `failed`, partial rollback executed |
| TC4 | Concurrent `mode=import` requests | Each request creates separate ImportSession |

**Architecture Decision (from Party Mode Review):**
- **Single Task Pattern:** One universal `process_1c_import_task()` analyzes `1c_import/` contents
- The task orchestrates sub-imports based on files found (goods → offers → prices → rests)
- **ImportSession** ensures atomicity — all changes can be rolled back on failure
- This aligns with existing `apps/products/services/import_1c/` architecture (Source: architecture.md 2.2)
