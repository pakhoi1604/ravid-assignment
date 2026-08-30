---
phase: 2
title: Document Metadata Models
status: completed
priority: P1
dependencies:
  - 1
---

# Phase 2: Document Metadata Models

## Overview

Add durable relational state for uploaded documents and ingestion jobs. This is the source of truth for the upload and status APIs.

## Requirements

- Functional: persist each uploaded file with owner, original filename, file path, content type, byte size, and timestamps.
- Functional: persist a public document UUID and one ingestion job per upload with public `task_id`, status, timestamps, and failure message.
- Functional: status API must be resolvable without reading Celery result backend state.
- Non-functional: migrations must be deterministic and pass `makemigrations --check --dry-run` after creation.
- Non-functional: model names and indexes should stay simple and assignment-focused.

## Architecture

Use two models in `apps.documents`:

```python
class Document(models.Model):
    public_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class IngestionJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"

    document = models.OneToOneField(Document, on_delete=models.CASCADE)
    task_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Prefer UUID public IDs generated before Celery dispatch so the API can return stable `document_id` and `task_id` values immediately and look them up durably.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/models.py` - add `Document` and `IngestionJob`.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/admin.py` - register read-oriented admin views.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/migrations/0001_initial.py` - generated migration.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_models.py` - model defaults, ownership, status transitions.

## Implementation Steps

1. Define a safe `document_upload_path(instance, filename)` that scopes storage by user ID and `Document.public_id`, not raw user input alone.
2. Add `Document` model fields and indexes for owner and created time.
3. Add `IngestionJob` status enum, one-to-one document link, unique task ID, and timestamp fields.
4. Add minimal `__str__` methods that avoid leaking file contents.
5. Register models in admin with list display and read-only timestamp fields.
6. Generate and inspect migrations.
7. Add model tests for status defaults, unique public IDs, owner relationship, and cascade behavior.

## Todo List

- [x] Add document upload path helper.
- [x] Add `Document` model.
- [x] Add `IngestionJob` model.
- [x] Register admin metadata.
- [x] Generate migration.
- [x] Add model tests.

## Success Criteria

- [x] Models migrate cleanly on test SQLite and production PostgreSQL settings.
- [x] `IngestionJob.task_id` is unique and API-safe.
- [x] `Document.public_id` is unique and used for API-facing `document_id`.
- [x] A document belongs to exactly one owner.
- [x] Deleting a user cascades documents and ingestion jobs.
- [x] No vector, chat, payment, subscription, or credit models are added.

## Risk Assessment

- Risk: upload paths expose unsafe filenames. Mitigation: normalize basename and scope by stable IDs.
- Risk: relying on Celery result backend for status. Mitigation: model status is authoritative.
- Risk: future vector cleanup needs document identity. Mitigation: keep document primary key and task ID available for vector metadata.
