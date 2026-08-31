---
title: Fix Swagger Document File Upload Input
description: >-
  Correct the OpenAPI upload request schema so Swagger UI renders a file
  chooser.
status: completed
priority: P2
branch: main
tags:
  - bugfix
  - backend
  - api
blockedBy: []
blocks: []
created: '2026-08-31T05:00:08.419Z'
createdBy: 'ck:plan'
source: skill
---

# Fix Swagger Document File Upload Input

## Overview

`POST /api/documents/upload/` already accepts multipart files at runtime, but the generated OpenAPI
component describes `file` as `string($uri)`. Swagger UI therefore renders a text field instead of
a file chooser. Enable request/response component splitting, then lock the binary upload contract
with the existing schema smoke test.

## Root Cause

- `UploadSerializer.file` is a valid DRF `FileField`.
- `DocumentUploadView` already uses `MultiPartParser` and `FormParser`.
- `drf-spectacular` cannot express the request/response duality of `FileField` in one component.
- Current generated schema: `Upload.file = {type: string, format: uri}`.
- Required generated request schema: `UploadRequest.file = {type: string, format: binary}`.

Reference: https://drf-spectacular.readthedocs.io/en/latest/faq.html#filefield-imagefield-is-not-handled-properly-in-the-schema

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Correct and verify upload schema](./phase-01-correct-and-verify-upload-schema.md) | Completed |

## Dependencies

- No package, migration, or cross-plan dependency.
- Existing pending Part 1 smoke-test plan does not block this schema-only correction.

## Scope

- Modify `config/settings/base.py` and `tests/smoke/test_health.py` only.
- Preserve endpoint paths, authentication, multipart parsing, validation, storage, and responses.
- Do not change `apps/documents/serializers.py` or `apps/documents/views.py`.

## Acceptance Criteria

- Schema advertises `multipart/form-data` for the upload endpoint.
- The required `file` request property is `type: string`, `format: binary`.
- Swagger UI renders a browser file picker after the app/schema is reloaded.
- Existing API, schema, and document tests pass.
