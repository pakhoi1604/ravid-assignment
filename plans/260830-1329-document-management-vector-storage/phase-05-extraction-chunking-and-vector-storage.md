---
phase: 5
title: Extraction Chunking and Vector Storage
status: completed
priority: P1
dependencies:
  - 1
  - 2
  - 3
  - 4
---

# Phase 5: Extraction Chunking and Vector Storage

## Overview

After the upload/status gate passes, implement the real vector-ingestion pipeline: extract text from PDF/TXT/Markdown, split with LangChain, embed chunks, and store them in Chroma isolated by user and document.

## Requirements

- Functional: extract readable text from `.pdf`, `.txt`, `.md`, and `.markdown` uploads.
- Functional: split text using LangChain `RecursiveCharacterTextSplitter` with settings-backed chunk size and overlap.
- Functional: generate embeddings with `EMBEDDING_MODEL_NAME`.
- Functional: store vectors in Chroma with metadata linking `user_id`, public `document_id`, `job_id`, chunk index, and source filename.
- Functional: mark job `SUCCESS` only after vector storage succeeds.
- Functional: mark job `FAILURE` for empty content, parse errors, embedding errors, or Chroma errors.
- Functional: install the locked vector-ingestion dependencies in the Docker application image before runtime imports are added.
- Non-functional: do not add chat endpoints, retriever/query APIs, OpenRouter answer generation, credits, payment, subscriptions, or HyDE.
- Non-functional: keep pipeline testable with fakes/mocks for embeddings and vector store.

## Architecture

Keep ingestion logic in service modules instead of bloating Celery tasks:

- `apps.documents.extraction` handles file-type-specific text extraction.
- `apps.documents.chunking` or a focused service function wraps LangChain splitter settings.
- `apps.documents.vector_store` owns Chroma client/vector store construction and upsert/delete helpers for Part 1. Later chat/retrieval work can wrap this boundary without changing the Part 1 API contract.
- `apps.documents.services.run_ingestion_pipeline(job)` coordinates extraction, chunking, and vector upsert.

Vector isolation is one Chroma collection for RAVID documents plus mandatory metadata filters containing `user_id` and public `document_id`. Do not switch to per-user collections unless implementation proves the selected LangChain adapter cannot support the metadata strategy.

## Related Code Files

- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/extraction.py` - PDF/TXT/Markdown extraction.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/chunking.py` - LangChain text splitter wrapper if it improves testability.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/services.py` - real ingestion pipeline.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/vector_store.py` - Chroma/LangChain vector storage adapter for ingestion.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py` - add collection name or timeout settings only if required.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docker/django/Dockerfile` - install the vector-ingestion dependency group for runtime web and worker images.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py` - assert the Dockerfile installs vector-ingestion dependencies once Phase 5 imports require them.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_extraction.py` - extraction behavior.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_ingestion_pipeline.py` - pipeline success/failure.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_vector_store.py` - vector adapter metadata/isolation tests.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md` - document Part 1 reviewer workflow.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docs/system-architecture.md` - document ingestion pipeline and vector namespace.

## Implementation Steps

1. Add extraction helpers:
   - PDF: use `pypdf` from locked vector-ingestion dependencies.
   - TXT/Markdown: decode as UTF-8, with clear failure for invalid text.
2. Add empty-content validation before chunking.
3. Wrap `RecursiveCharacterTextSplitter` with the existing chunk size and overlap settings.
4. Define chunk metadata schema:
   - `user_id`
   - `document_id` as `Document.public_id`
   - `ingestion_job_id`
   - `task_id`
   - `chunk_index`
   - `source_filename`
5. Update `docker/django/Dockerfile` so `uv sync` installs the vector-ingestion dependency group in the shared application image.
6. Implement Chroma vector store adapter using `CHROMA_HOST`, `CHROMA_PORT`, and `EMBEDDING_MODEL_NAME`.
7. Add idempotency behavior before upsert: delete existing vectors for the same document or use deterministic IDs like `document-{public_id}-chunk-{index}`.
8. Replace Phase 4 placeholder with real pipeline coordination.
9. Add tests with mocked embedding/vector-store calls for fast local validation.
10. Add an optional Docker smoke test path that exercises Chroma when dependencies and services are available.

## Todo List

- [x] Add file extraction helpers.
- [x] Add chunking wrapper.
- [x] Add Chroma vector store adapter.
- [x] Install vector-ingestion dependencies in the Docker application image.
- [x] Add metadata and deterministic chunk IDs.
- [x] Replace placeholder ingestion service.
- [x] Add extraction, chunking, vector adapter, and pipeline tests.
- [x] Update README and architecture docs.

## Success Criteria

- [x] PDF, TXT, and Markdown uploads produce non-empty chunks.
- [x] Empty or unreadable files mark ingestion `FAILURE` with sanitized error.
- [x] Successful ingestion stores vectors with user/document metadata.
- [x] Re-running ingestion for the same document does not create uncontrolled duplicate chunks.
- [x] Docker web and worker images can import Phase 5 ingestion dependencies.
- [x] Chroma connection details remain configurable through settings/env.
- [x] All Part 1 API/status behavior from Phases 1-4 still passes after vector storage is added.
- [x] No chat endpoint, retriever/query API, OpenRouter completion, HyDE, payment, subscription, or credits code is introduced.

## Risk Assessment

- Risk: sentence-transformers downloads slow CI or reviewer runs. Mitigation: keep unit tests mocked; document Docker/manual path separately.
- Risk: Chroma metadata filtering differs across adapters. Mitigation: keep adapter narrow and test metadata passed to LangChain/Chroma boundary.
- Risk: PDF extraction can return empty text for scanned PDFs. Mitigation: fail clearly; OCR is out of scope.
- Risk: retries duplicate chunks. Mitigation: deterministic vector IDs or delete-before-upsert by document metadata.

<!-- Updated: Validation Session 1 - Docker runtime dependency and vector isolation strategy made explicit. -->
<!-- Updated: Validation Session 2 - Later chat-engine wording replaced with vector-ingestion scope. -->
