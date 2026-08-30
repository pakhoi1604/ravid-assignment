---
title: 'Part 1: Document Management & Vector Storage'
description: >-
  Implement authenticated document upload, ingestion status, and
  LangChain-backed vector indexing for the RAVID Part 1 assignment.
status: completed
priority: P1
branch: main
tags:
  - feature
  - backend
  - api
  - auth
  - database
blockedBy: []
blocks: []
created: '2026-08-30T06:29:52.354Z'
createdBy: 'ck:plan'
source: skill
---

# Part 1: Document Management & Vector Storage

## Overview

Implement Part 1 of the RAVID assignment on top of the completed Django skeleton. The first delivery gate is authenticated upload plus durable ingestion status; extraction, chunking, embeddings, and Chroma vector storage start only after that gate passes.

Out of scope: payment, subscriptions, credits, chat endpoints, retriever/query APIs, OpenRouter answer generation, and HyDE.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Minimal Auth Endpoints](./phase-01-minimal-auth-endpoints.md) | Completed |
| 2 | [Document Metadata Models](./phase-02-document-metadata-models.md) | Completed |
| 3 | [Upload and Status APIs](./phase-03-upload-and-status-apis.md) | Completed |
| 4 | [Celery Ingestion Lifecycle](./phase-04-celery-ingestion-lifecycle.md) | Completed |
| 5 | [Extraction Chunking and Vector Storage](./phase-05-extraction-chunking-and-vector-storage.md) | Completed |

## Cross-Plan Dependencies

- Completed prerequisite: `plans/260830-1115-ravid-backend-skeleton/`.
- No blocking relationship with unfinished `plans/260830-1236-repair-codex-hooks/`; it only affects Codex hook configuration.
- Requirement source: `docs/2026-08-30 R.A.V.I.D.md`.

## Architecture Decisions

- Use Django's built-in `User` model and SimpleJWT endpoints for minimal assignment authentication.
- Store durable document and ingestion status in PostgreSQL; do not depend on Celery result state for API responses.
- Keep uploaded files under Django `MEDIA_ROOT` through a `FileField`.
- Return public UUIDs for `document_id` and `task_id`; keep database primary keys internal.
- Keep ingestion status values assignment-facing: `PENDING`, `PROCESSING`, `SUCCESS`, `FAILURE`.
- Serialize internal `PENDING` as API `PROCESSING` so external status responses match the assignment's running-state contract.
- Use LangChain text splitting and Chroma vector storage through the already locked vector-ingestion dependencies.
- Install the locked vector-ingestion dependencies in the Docker application image before importing LangChain, Chroma, `pypdf`, or embedding libraries at runtime.
- Isolate vector records in one Chroma collection using required metadata filters for uploading user and public document ID.

## Acceptance Criteria

- [x] `/api/auth/token/` and `/api/auth/token/refresh/` issue and refresh JWTs for existing users.
- [x] `/api/documents/upload/` accepts authenticated `multipart/form-data` with `file`.
- [x] Upload rejects unauthenticated requests, unsupported extensions, missing files, and oversized files.
- [x] Successful upload returns `202 Accepted` with `message`, `document_id`, and `task_id`.
- [x] `/api/documents/status/?task_id=...` returns durable ingestion status scoped to the owning user.
- [x] Celery task transitions are persisted and failure errors are returned without leaking internals.
- [x] PDF, TXT, and Markdown files are extracted, chunked, embedded, and stored in Chroma after the API/status gate passes.
- [x] User A cannot see or query User B's document or ingestion job state.
- [x] Docker web and worker images include the dependencies needed by the Phase 5 ingestion imports.
- [x] Focused API, model, task, extraction, and vector-storage tests pass.

## Validation Commands

```bash
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run python manage.py check --settings=config.settings.test
uv run pytest
docker compose config --quiet
```

## Open Questions

None. Use conservative defaults from existing settings and defer non-Part-1 product behavior.

## Validation Log

### Session 1 - 2026-08-30
**Trigger:** User requested `$ck:plan --validate`.
**Questions asked:** 0. No unresolved user decision remained after repository verification; ambiguous implementation choices were resolved conservatively inside Part 1 scope.

#### Verification Results

- **Tier:** Full
- **Claims checked:** 39
- **Verified:** 29 | **Failed:** 0 | **Unverified:** 10
- **Unverified note:** all unverified claims are planned future code surfaces or future imports, not contradictions in existing code.

#### Verified Claims

- `djangorestframework-simplejwt` exists in `pyproject.toml`.
- DRF default permission is currently `IsAuthenticated` in `config/settings/base.py`.
- Public health/schema/docs overrides already use `AllowAny`.
- Upload size, chunk-size, chunk-overlap, Chroma host/port, and embedding model settings exist in settings and the example environment template.
- Celery eager test mode exists in `config/settings/test.py`.
- `web` and `celery` share `media_data` and Hugging Face cache volumes in `compose.yaml`.
- Chroma service exists and is private to the Compose network.

#### Validation Decisions

- API status decision: internal `PENDING` serializes as external `PROCESSING`.
- Vector isolation decision: use one Chroma collection with mandatory `user_id` and public `document_id` metadata.
- Runtime dependency decision: Phase 5 must update `docker/django/Dockerfile` to install the locked vector-ingestion dependency group for web and worker.
- Test location decision: auth tests belong under `tests/accounts/`, matching the app boundary.

#### Action Items

- [x] Update Phase 1 auth test path to `tests/accounts/test_auth.py`.
- [x] Update Phase 3 status response contract to remove the unresolved `PENDING` option.
- [x] Update Phase 3 sequencing so API/job contract precedes Phase 4 Celery dispatch.
- [x] Update Phase 5 vector strategy and Dockerfile scope.
- [x] Re-read all plan files after edits and run `ck plan status`.

#### Impact on Phases

- Phase 1: auth test path corrected.
- Phase 3: status serialization contract made deterministic; Celery dispatch ownership moved to Phase 4.
- Phase 5: vector namespace and runtime dependency work made explicit.

### Session 2 - 2026-08-30
**Trigger:** User asked why this phase sounded like later chat-engine work and requested a correction.
**Questions asked:** 0.

#### Confirmed Decisions

- Phase 5 is vector indexing only: extraction, chunking, embeddings, and Chroma storage.
- Do not plan chat/retrieval APIs, OpenRouter completion, HyDE, credits, subscriptions, or payment in this plan.
- Use "vector-ingestion" wording for dependency/runtime scope so implementation does not drift into the later chat engine.

#### Action Items

- [x] Replace confusing chat-engine wording with vector-ingestion wording.
- [x] Keep actual existing setting names as implementation details, not feature scope.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md`, `phase-01-minimal-auth-endpoints.md`, `phase-02-document-metadata-models.md`, `phase-03-upload-and-status-apis.md`, `phase-04-celery-ingestion-lifecycle.md`, `phase-05-extraction-chunking-and-vector-storage.md`.
- Decision deltas checked: 7.
- Reconciled stale references: 8.
- Unresolved contradictions: 0.
