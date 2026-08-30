---
phase: 4
title: Celery Ingestion Lifecycle
status: completed
priority: P1
dependencies:
  - 2
  - 3
---

# Phase 4: Celery Ingestion Lifecycle

## Overview

Add a real Celery task boundary and durable status transitions before adding parsing or vector writes. This creates the first passable delivery gate for upload/status behavior.

## Requirements

- Functional: upload endpoint enqueues a Celery task with the same public `task_id` returned to the client.
- Functional: task sets `PROCESSING` when it starts, `SUCCESS` when lifecycle work completes, and `FAILURE` on exceptions.
- Functional: status endpoint reads persisted job state only.
- Functional: Celery dispatch uses the persisted `IngestionJob.task_id` as the Celery task ID when practical.
- Non-functional: task must be idempotent enough that a retry does not corrupt status or duplicate document rows.
- Non-functional: test settings use eager Celery safely.

## Architecture

Create `apps.documents.tasks.ingest_document`. The task accepts `job_id` or `task_id`, loads the owner-scoped document through the job, and calls a service boundary.

Phase 4 service boundary can be a no-op `run_ingestion_pipeline(job)` placeholder that validates the file exists and returns. Phase 5 replaces the placeholder internals with extraction, chunking, embeddings, and vector storage. This keeps upload/status acceptance testable before adding LangChain complexity.

## Related Code Files

- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/tasks.py` - Celery task and status transition handling.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/services.py` - ingestion service boundary placeholder.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/views.py` - dispatch task after job creation.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_tasks.py` - lifecycle transition tests.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_api.py` - assert upload enqueues/updates under eager mode.

## Implementation Steps

1. Add `ingest_document` as a shared Celery task.
2. Make task lookup durable job state by `task_id` or primary key; prefer `apply_async(task_id=str(job.task_id))` for reviewer traceability.
3. Add helper methods or service functions to mark `PROCESSING`, `SUCCESS`, and `FAILURE` with timestamps.
4. Catch expected ingestion exceptions, store a sanitized `error`, and re-raise only when appropriate for eager tests.
5. Add placeholder service that confirms the uploaded file exists and is readable.
6. Dispatch task from upload after model creation; prefer `transaction.on_commit`.
7. Add tests for success transition, failure transition, missing job handling, repeated execution, and status API response after task completion.
8. Run Docker-level Celery smoke check only after local tests pass.

## Todo List

- [x] Add Celery task.
- [x] Add status transition helpers.
- [x] Add placeholder ingestion service boundary.
- [x] Dispatch task after upload commit.
- [x] Add task lifecycle tests.
- [x] Verify eager and non-eager settings assumptions.

## Success Criteria

- [x] Upload creates a job and dispatches exactly one task.
- [x] Celery task ID matches or is traceably linked to `IngestionJob.task_id`.
- [x] Status moves through durable states and the status API reflects them.
- [x] Failure stores sanitized error text and returns assignment-compatible failure response.
- [x] Running with test eager mode does not require Redis.
- [x] Running in Docker registers `apps.documents.tasks.ingest_document` with the worker.
- [x] Extraction, chunking, embeddings, and vector storage remain behind the Phase 5 service boundary.

## Risk Assessment

- Risk: eager tests hide serialization bugs. Mitigation: include a Celery task registration/import assertion and Docker smoke check.
- Risk: status races between upload response and task start. Mitigation: persist `PENDING`, then serialize queued and running states as external `PROCESSING`.
- Risk: duplicate vector writes on retry later. Mitigation: Phase 4 defines idempotency expectations before Phase 5 writes vectors.

<!-- Updated: Validation Session 1 - Celery task ID linkage and external status behavior clarified. -->
