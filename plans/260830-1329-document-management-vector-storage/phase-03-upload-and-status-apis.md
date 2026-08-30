---
phase: 3
title: Upload and Status APIs
status: completed
priority: P1
dependencies:
  - 1
  - 2
---

# Phase 3: Upload and Status APIs

## Overview

Implement the assignment-facing document upload and ingestion status endpoints with validation, user isolation, and OpenAPI coverage.

This phase defines the upload/status API contract and durable job creation. Phase 4 wires real Celery dispatch and lifecycle transitions before the extraction/vector-storage work begins.

## Requirements

- Functional: `POST /api/documents/upload/` accepts authenticated multipart upload with field `file`.
- Functional: support PDF, TXT, and Markdown extensions only: `.pdf`, `.txt`, `.md`, `.markdown`.
- Functional: return `202 Accepted` with exact assignment fields: `message`, `document_id`, `task_id`.
- Functional: `GET /api/documents/status/?task_id=...` returns status for the authenticated owner only.
- Functional: return assignment-compatible failure shape for invalid file format.
- Functional: serialize internal queued `PENDING` jobs as external `PROCESSING`.
- Non-functional: enforce `MAX_UPLOAD_SIZE_MB` from settings.
- Non-functional: avoid parsing files inside the request thread.

## Architecture

Add document API code inside `apps.documents`:

- `serializers.py` for upload validation and status response formatting.
- `views.py` for DRF API views or viewsets.
- `urls.py` for app-local routes.
- a dispatch seam that Phase 4 backs with Celery.

The upload view creates `Document` and `IngestionJob` rows in one transaction, saves the file, and returns `202` with `Document.public_id` as `document_id`. Phase 4 adds the post-commit Celery dispatch using the pre-created task UUID.

## Related Code Files

- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/serializers.py` - upload/status serializers.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/views.py` - upload and status views.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/urls.py` - document route definitions.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/urls.py` - include document URLs at `/api/documents/`.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_api.py` - upload/status API tests.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docs/system-architecture.md` - update public surface when endpoints exist.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md` - add reviewer curl examples after endpoint behavior is implemented.

## Implementation Steps

1. Create upload serializer that validates required file, extension, and size.
2. Use a small allowlist helper for extensions; do not trust browser content type.
3. Create status serializer that maps durable model state to assignment response shapes:
   - `PROCESSING`: `{"task_id": "...", "status": "PROCESSING"}`
   - `SUCCESS`: include success message.
   - `FAILURE`: include sanitized error.
   - `PENDING`: normalize to `PROCESSING` for the API response.
4. Implement upload view with `IsAuthenticated`, multipart parsers, transaction handling, model creation, and a dispatch seam for Phase 4.
5. Implement status view with `task_id` query parameter validation and owner-scoped lookup.
6. Include document URLs under `/api/documents/`.
7. Add OpenAPI schema assertions where useful.
8. Add API tests for success, auth failure, invalid extension, missing file, oversized file, unknown task ID, and cross-user isolation.

## Todo List

- [x] Add upload serializer validation.
- [x] Add status response serializer.
- [x] Add upload view.
- [x] Add status view.
- [x] Wire document URLs.
- [x] Add API tests for happy path and failures.
- [x] Update docs after behavior exists.

## Success Criteria

- [x] Authenticated upload returns `202` with `message`, `document_id`, and `task_id`.
- [x] Invalid extension returns `400` with `error: "Invalid file format. Only PDF, TXT, and Markdown files are allowed."`
- [x] Missing or oversized file returns `400`.
- [x] Unauthenticated upload/status requests return `401`.
- [x] User cannot retrieve another user's ingestion status.
- [x] Queued internal `PENDING` state is returned externally as `PROCESSING`.
- [x] Request thread does not parse, chunk, embed, or call Chroma.

## Risk Assessment

- Risk: API contract lands before real Celery dispatch. Mitigation: Phase 4 is part of the required pre-vector gate and owns dispatch/status transition acceptance.
- Risk: leaking file paths or internal exceptions. Mitigation: response serializers expose only assignment fields.
- Risk: internal `PENDING` status is not shown in assignment examples. Mitigation: keep internal `PENDING`, but return external `PROCESSING` for queued and running jobs.

<!-- Updated: Validation Session 1 - Status serialization contract made deterministic. -->
