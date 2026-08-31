---
phase: 1
title: Correct and verify upload schema
status: completed
priority: P2
dependencies: []
---

# Phase 1: Correct and verify upload schema

## Overview

Correct the generated OpenAPI request component and prove Swagger receives the binary file
contract. Runtime upload behavior is already correct and remains unchanged.

## Context Links

- `config/settings/base.py`: global DRF and drf-spectacular settings.
- `apps/documents/serializers.py`: existing `UploadSerializer.file = FileField()`.
- `apps/documents/views.py`: existing multipart/form parsers and upload schema annotation.
- `tests/smoke/test_health.py`: existing public OpenAPI schema assertions.
- Official guidance: https://drf-spectacular.readthedocs.io/en/latest/faq.html#filefield-imagefield-is-not-handled-properly-in-the-schema

## Requirements

- Functional: Swagger UI must show a file chooser for `POST /api/documents/upload/`.
- Contract: upload request remains required `multipart/form-data` with field name `file`.
- Compatibility: no changes to endpoint URLs, status codes, auth, validation, or storage.
- Regression safety: schema tests must fail if `file` returns to URI/string form.

## Architecture

Set `SPECTACULAR_SETTINGS["COMPONENT_SPLIT_REQUEST"] = True`. drf-spectacular then emits a
request-specific `UploadRequest` component with `format: binary`; Swagger UI maps that shape to a
native file input. The setting applies schema-wide, so other request serializers, including
`ChatQuery`, become `*Request` components without changing runtime APIs.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py` — enable request
  component splitting.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_health.py` — update the
  expected `ChatQueryRequest` name and assert the resolved upload request schema.
- Create: None.
- Delete: None.

## Implementation Steps

1. In `SPECTACULAR_SETTINGS`, add `"COMPONENT_SPLIT_REQUEST": True`.
2. Update the existing chat request-component lookup from `ChatQuery` to `ChatQueryRequest`.
3. In the schema smoke test, inspect the upload operation's `multipart/form-data` request schema.
4. Assert it references `#/components/schemas/UploadRequest`.
5. Assert `UploadRequest.file` equals `{type: string, format: binary}` and `file` is required.
6. Generate the schema with `uv run python manage.py spectacular --file /tmp/ravid-schema.yml` and
   confirm no schema warnings.
7. Run focused schema and document tests, then the full test suite and lint.

## Todo List

- [x] Enable split request components.
- [x] Update schema-name assertion affected by the global setting.
- [x] Add binary multipart upload schema assertions.
- [x] Run focused and broad validation.

## Success Criteria

- [x] `/api/documents/upload/` advertises `multipart/form-data`.
- [x] `UploadRequest.file` is a required binary string.
- [x] Swagger UI receives the binary schema required for a native file picker after reload/restart.
- [x] `uv run pytest tests/smoke/test_health.py tests/documents/test_api.py` passes.
- [x] `uv run pytest` passes.
- [x] `uv run ruff check apps config tests` passes (the CI-authoritative lint scope).

## Risk Assessment

- Global component split renames request components and may affect generated-client consumers.
  Mitigation: assert the known rename and inspect the generated schema diff before completion.
- Swagger may display a cached schema after code changes. Mitigation: restart/reload the Django
  process and hard-refresh `/api/docs/` before judging the UI.

## Security Considerations

- No auth or file-validation behavior changes.
- Keep the existing JWT requirement, extension allowlist, and upload-size limit intact.

## Rollback

Remove `COMPONENT_SPLIT_REQUEST` and revert only the matching schema-test assertions. No database or
stored-file rollback is required.
