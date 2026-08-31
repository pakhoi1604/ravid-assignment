---
date: 2026-08-31
session: swagger-file-upload-plan
type: journal
---

# Journal: 2026-08-31 — Swagger File Upload Plan

## Context

Swagger UI rendered `POST /api/documents/upload/` with a plain text field labeled
`string($uri)`, so the browser offered no file chooser. Repository inspection confirmed that the
runtime endpoint already uses a DRF `FileField` with multipart parsers; the defect is limited to the
generated OpenAPI contract.

## What Happened

- Confirmed the generated component currently describes `Upload.file` as
  `{type: string, format: uri}`.
- Identified drf-spectacular's `FileField` request/response duality as the root cause: one shared
  component cannot represent both an uploaded binary request and a URI-style response correctly.
- Found that `SPECTACULAR_SETTINGS` does not enable `COMPONENT_SPLIT_REQUEST`, which is required for
  a request-specific `UploadRequest.file` with `format: binary`.
- Created the one-phase plan at
  `plans/260831-1200-fix-swagger-file-upload-input/plan.md`.
- Performed planning only; no application code, settings, or tests were changed in this session.

## Reflection

The screenshot looks like an upload implementation failure, but the existing serializer and parser
configuration already support file uploads. Keeping the correction at the schema boundary avoids
unnecessary changes to authentication, validation, storage, endpoint behavior, or response
contracts.

## Decisions

| Decision | Rationale | Impact |
| --- | --- | --- |
| Enable `COMPONENT_SPLIT_REQUEST` in the implementation phase. | drf-spectacular needs separate request components to emit `FileField` as binary input. | Swagger can render a native file picker; request components such as `ChatQuery` will gain `*Request` names. |
| Limit implementation to configuration and the existing schema smoke test. | Runtime upload handling is already correct. | No serializer, view, URL, storage, migration, or dependency changes are planned. |
| Use one phase with focused and broad verification. | The fix is small but the setting affects schema generation globally. | The smoke test will lock the multipart `UploadRequest.file` binary contract and account for known component renames. |

## Next

- Implement the pending phase in
  `plans/260831-1200-fix-swagger-file-upload-input/phase-01-correct-and-verify-upload-schema.md`.
- Regenerate the OpenAPI schema, run focused schema/document tests and the full validation suite,
  then reload Swagger UI and confirm the file chooser appears.
