---
title: "Part 1 Endpoint Smoke and Chroma Verification"
description: "Add reusable Part 1 test data plus scripts that prove auth, upload, ingestion status, DB, media, and Chroma content/vector behavior against the Docker stack."
status: pending
priority: P2
branch: "main"
tags: [test, backend, api, docker]
blockedBy: [260830-1329-document-management-vector-storage, 260830-1740-langchain-dependency-refresh]
blocks: []
created: "2026-08-30T09:08:19.012Z"
createdBy: "ck:plan"
source: skill
---

# Part 1 Endpoint Smoke and Chroma Verification

## Overview

Create a reviewer-friendly Part 1 test toolkit: a stable test-data folder, a host-level endpoint
smoke script, and a Chroma verification script that compares extracted/split source content against
stored Chroma chunks and confirms embeddings exist.

This plan is limited to Part 1: minimal auth endpoints, document upload, ingestion status, and
vector storage verification. It does not test chat, payment, subscriptions, credits, OpenRouter
answer generation, or HyDE.

## Scope Challenge

- Existing code: `Makefile` already has `smoke` for service health, `load-test-accounts` for seeded
  users, pytest coverage for document internals, and README curl examples for manual upload. Chroma
  chunks already include `document_id`, `task_id`, `chunk_index`, `source_filename`, and `user_id`.
- Minimum changes: add one test-data fixture folder, one host-run smoke script, one Python Chroma
  verification script, Make targets, and README usage docs.
- Complexity: expected 5-7 touched files and no new application services. This is justified because
  content/vector comparison needs Python/Django context while endpoint smoke should remain host-run.
- Selected mode: fast planning. No external research needed.

## Architecture Decisions

- Run the main endpoint flow from the host via `curl` to verify the same path Postman uses.
- Use Docker only for controlled setup and inspection: seed accounts, query DB, inspect media files,
  and query Chroma.
- Keep the endpoint script POSIX shell friendly: `sh`, `curl`, `docker compose`, and Python stdlib
  for JSON parsing. Avoid requiring `jq`.
- Store safe, public test fixtures under `tests/fixtures/part-1-documents/`; do not depend on
  private assignment files.
- Use a Python verifier for Chroma because it needs Django settings, extraction, chunking, metadata
  sorting, and optional embedding inspection.
- Make the script fail fast and print actionable error messages for missing stack, auth failure,
  upload failure, timeout, empty DB side effects, missing media file, or unchanged Chroma count.
- Keep all test credentials local-only and sourced from existing seeded test accounts.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Define Host Smoke Contract](./phase-01-define-host-smoke-contract.md) | Pending |
| 2 | [Implement Script and Make Target](./phase-02-implement-script-and-make-target.md) | Pending |
| 3 | [Validate Reviewer Workflow](./phase-03-validate-reviewer-workflow.md) | Pending |

## Dependencies

- Blocking prerequisite: `plans/260830-1740-langchain-dependency-refresh/` refreshes and validates
  the LangChain/Chroma runtime before reusable endpoint smoke tooling is finalized.
- Completed prerequisite: `plans/260830-1329-document-management-vector-storage/`.
- Coordination only: `plans/260831-1306-harden-docker-reviewer-stack/` also edits `Makefile` and
  `README.md`; whichever plan runs second must preserve the first plan's commands and documentation.
- Existing Docker stack: `docker compose up -d` with `web`, `db`, `redis`, `celery`, and `chroma`.
- Existing seed command: `make load-test-accounts`.
- Existing test account: `reviewer` / `reviewer-password-123`.

## Proposed Commands

```bash
make smoke
make smoke-part-1
make verify-chroma-document DOCUMENT_ID=<document-public-id>
```

`make smoke` remains a service-health check. `make smoke-part-1` should exercise Part 1 business
behavior end to end. `make verify-chroma-document` should compare the source document's expected
chunks with Chroma records for an existing document.

## Test Data Layout

```text
tests/fixtures/part-1-documents/
  valid/
    smoke-sample.md
    smoke-sample.txt
    smoke-sample.pdf
  invalid/
    smoke-sample.csv
    smoke-sample.json
    smoke-sample.html
    smoke-sample.docx
    smoke-sample.png
    smoke-sample.zip
```

Valid fixtures prove accepted formats. Invalid fixtures prove extension rejection. Fixture content
must be safe, synthetic, and small enough for fast repeated reviewer runs.

## Acceptance Criteria

- [ ] Host-level script obtains JWT through `/api/auth/token/`.
- [ ] Script refreshes token through `/api/auth/token/refresh/`.
- [ ] Script uploads a real Markdown fixture through `/api/documents/upload/`.
- [ ] Test-data folder contains valid `.md`, `.txt`, `.pdf` fixtures and several invalid file types.
- [ ] Script polls `/api/documents/status/?task_id=...` until `SUCCESS` or a clear timeout.
- [ ] Script verifies PostgreSQL contains the created `Document` and `IngestionJob`.
- [ ] Script verifies the uploaded file exists under `/app/media/documents/...`.
- [ ] Script verifies Chroma collection count increased or contains chunks for the new document.
- [ ] Chroma verifier compares expected extracted chunks with stored Chroma documents by
      `document_id` and `chunk_index`.
- [ ] Chroma verifier confirms embeddings exist, have consistent dimensions, and are tied to the
      expected chunk ids.
- [ ] Invalid fixture uploads return the expected `400` validation error.
- [ ] Failure output names the failed step and includes enough context for debugging.
- [ ] README documents exact reviewer commands and prerequisites.

## Open Questions

- None. Use existing Docker reviewer path and seeded test account.
