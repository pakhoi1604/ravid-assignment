---
phase: 1
title: "Define Test Data and Verification Contract"
status: pending
priority: P2
dependencies: []
---

# Phase 1: Define Test Data and Verification Contract

## Overview

Define the Part 1 endpoint contract, test-data layout, Chroma comparison rules, expected side
effects, and failure behavior before writing scripts.

## Requirements

- Functional: cover auth token obtain, token refresh, document upload, and ingestion status.
- Functional: verify durable side effects in PostgreSQL, `/app/media`, Celery status, and Chroma.
- Functional: include valid upload fixtures for `.md`, `.txt`, and `.pdf`.
- Functional: include invalid fixtures for several unsupported extensions.
- Functional: compare extracted/split source content with stored Chroma chunk documents.
- Functional: confirm embedding vectors exist and are dimensionally consistent.
- Non-functional: run from the host against `http://127.0.0.1:8000`.
- Non-functional: no private assignment document dependency; use safe synthetic fixtures.
- Non-functional: no chat, billing, subscriptions, credits, OpenRouter answer generation, or HyDE.

## Architecture

The script should treat the public API as the primary system boundary:

```text
host script
  -> curl http://127.0.0.1:8000/api/auth/token/
  -> curl http://127.0.0.1:8000/api/auth/token/refresh/
  -> curl multipart upload valid fixtures to /api/documents/upload/
  -> curl multipart upload invalid fixtures expecting 400
  -> curl poll /api/documents/status/?task_id=...
  -> docker compose exec db/web for internal evidence
  -> docker compose exec web python scripts/verify-chroma-document.py
```

The Python Chroma verifier should use the same extraction and chunking services as ingestion, then
query Chroma for records matching `document_id`.

Comparison rules:

- Sort Chroma rows by `metadata.chunk_index`.
- Compare ids exactly: `document-<document_id>-chunk-<index>`.
- Compare stored `documents[]` text to expected chunks from `split_text`.
- Compare metadata fields: `document_id`, `task_id`, `source_filename`, `user_id`, `chunk_index`.
- Request `embeddings` and assert one vector per chunk, non-empty vector, consistent dimension.
- Do not compare raw vector floats unless a future issue proves embedding correctness is suspect.

## Related Code Files

- Read: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md`
- Read: `/home/khoipham/Projects/ravid-assignment/Ravid/Makefile`
- Read: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/views.py`
- Read: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/serializers.py`
- Read: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/tasks.py`
- Read: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/vector_store.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/`

## Implementation Steps

1. Confirm Part 1 public endpoints:
   - `POST /api/auth/token/`
   - `POST /api/auth/token/refresh/`
   - `POST /api/documents/upload/`
   - `GET /api/documents/status/?task_id=...`
2. Define script preconditions:
   - Docker Compose stack is running.
   - `web` is reachable on `127.0.0.1:8000`.
   - Test accounts can be loaded with `make load-test-accounts`.
3. Define expected success evidence:
   - token response has `access` and `refresh`
   - refresh response has new `access`
   - upload response is `202` and has `document_id` plus `task_id`
   - status reaches `SUCCESS`
   - DB row exists for uploaded `document_id`
   - media file exists at the stored path
   - Chroma chunks exactly match extraction/chunking output for that `document_id`
   - Chroma embeddings exist for every stored chunk
4. Define timeout behavior:
   - poll status for a bounded number of attempts
   - print web/celery logs tail on failure
5. Decide fixture strategy:
   - commit stable synthetic fixtures under `tests/fixtures/part-1-documents/`
   - include valid and invalid extension sets
   - keep files small and free of private assignment content

## Success Criteria

- [ ] Endpoint contract is written into the plan before implementation.
- [ ] Test-data directory and fixture matrix are defined.
- [ ] Chroma comparison rules are defined.
- [ ] Script preconditions are explicit and reviewer-friendly.
- [ ] Failure scenarios are listed before code is written.
- [ ] Fixture strategy does not require private assignment files.

## Risk Assessment

- Risk: script becomes flaky if embedding model startup is slow. Mitigation: bounded polling with a
  practical timeout and log tail on failure.
- Risk: relying on `jq` breaks clean machines. Mitigation: parse JSON with Python stdlib.
- Risk: DB/Chroma checks overfit implementation. Mitigation: keep public HTTP checks primary and
  internal checks as evidence only.
- Risk: PDF fixture text extraction is brittle if the fixture is poorly generated. Mitigation: keep
  a tiny known-good PDF fixture with text verified by `extract_text`.
