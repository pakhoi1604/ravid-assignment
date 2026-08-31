---
date: 2026-08-31
session: swagger-file-upload-implementation
type: journal
---

# Journal: 2026-08-31 — Swagger File Upload Implementation

## Context

Swagger UI described `POST /api/documents/upload/` as accepting a URI string, so it rendered a
text box and submitted the selected path as text instead of a multipart file. The runtime endpoint
already used DRF's `FileField` and multipart parsers; the fault was confined to the generated
OpenAPI request schema.

The implementation followed
`plans/260831-1200-fix-swagger-file-upload-input/plan.md`.

## What Happened

- Used a TDD red-green cycle: first extended the OpenAPI smoke test to require
  `UploadRequest.file` as a required `string/binary` field, observed the old schema fail, then
  enabled request-component splitting and reran the test successfully.
- Added `COMPONENT_SPLIT_REQUEST = True` to `config/settings/base.py`.
- Updated `tests/smoke/test_health.py` to lock the multipart upload request reference, binary file
  shape, required field, and the resulting `ChatQueryRequest` component name.
- Rebuilt and recreated the Docker `web` image so the running service used the new settings.
- Verified the live schema exposes `UploadRequest.file` with `format: binary`; Swagger can now
  render a native file chooser and submit file content rather than a path string.

## Verification

- Full suite: 240 passed, 3 skipped.
- Focused schema tests, Ruff lint, Django checks, migration drift check, Compose validation, and
  live OpenAPI schema verification passed.
- Code review result: `PASS_WITH_RISK` (9.2/10), with no critical findings.

## Reflection

The smallest correct fix was at the OpenAPI configuration boundary. Serializer, view, storage,
authentication, and response behavior did not need changes, so runtime API behavior remains
unchanged.

Enabling request splitting is global by design. Request component names now use the
`*Request` suffix, including `ChatQueryRequest` and JWT-related request schemas. No internal
consumer depends on the previous names, but external generated clients may need regeneration.

## Decisions Made

| Decision | Rationale | Impact |
| --- | --- | --- |
| Enable global request-component splitting | drf-spectacular needs separate request and response representations for `FileField` | Swagger receives the correct binary upload contract; request component names intentionally change globally |
| Keep runtime upload code untouched | Existing DRF multipart handling was already correct | No endpoint payload, response, storage, or business-logic behavior changes |
| Rebuild the Docker image before browser validation | Application source is copied into the image and the running service does not reload it | Live Swagger and schema checks exercise the implemented configuration rather than a stale image |

## Next Steps

- Regenerate any external OpenAPI-derived clients that bind directly to component names.
- Keep the schema smoke assertions as the regression guard for Swagger file selection.
