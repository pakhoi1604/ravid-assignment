---
phase: 1
title: "Protect Contracts and Break Document Cycles"
status: completed
priority: P1
dependencies: []
---

# Phase 1: Protect Contracts and Break Document Cycles

## Overview

Protect current ingestion and upload behavior, then give the ingestion workflow explicit ownership
and remove imports from leaf modules back into the orchestrator. This is an internal refactor only.

## Requirements

- Functional: preserve accepted extensions, error text, chunk IDs/metadata, task lifecycle, upload
  and status payloads, and pipeline return values.
- Non-functional: dependency-free contracts/errors/constants; normal top-level imports; no new
  Django app or generic utility package.

## Architecture

```text
tasks -> ingestion -> extraction
                   -> chunking
                   -> vector_store

constants/contracts/exceptions <- imported by all; import no workflow modules
```

`Chunk` becomes a frozen document-internal contract. `IngestionError` becomes a document-domain
error independent of orchestration. `run_ingestion_pipeline` moves from generic `services.py` to
explicit `ingestion.py`. Supported upload extensions and the existing public validation message
have one dependency-free owner shared by serializer and extractor.

## Related Code Files

| Action | File | Purpose |
| --- | --- | --- |
| Create | `apps/documents/contracts.py` | Own frozen `Chunk` DTO. |
| Create | `apps/documents/exceptions.py` | Own document-domain errors independently of orchestration. |
| Create | `apps/documents/constants.py` | Own upload extensions and stable invalid-format message. |
| Create | `apps/documents/ingestion.py` | Own `run_ingestion_pipeline` and top-level step imports. |
| Modify | `apps/documents/chunking.py` | Import error from dependency-free module. |
| Modify | `apps/documents/extraction.py` | Reuse extension constants and independent error. |
| Modify | `apps/documents/serializers.py` | Reuse extension constants without changing API errors. |
| Modify | `apps/documents/tasks.py` | Import workflow/error from their explicit owners. |
| Modify | `apps/documents/vector_store.py` | Import `Chunk`/errors without orchestration dependency. |
| Delete | `apps/documents/services.py` | Remove ambiguous workflow owner after all imports move. |
| Modify | `tests/documents/test_ingestion_pipeline.py` | Protect pipeline contract and update import path. |
| Modify | `tests/documents/test_chunking.py` | Protect transformation and expected failure type. |
| Modify | `tests/documents/test_extraction.py` | Protect extension/error contracts. |
| Modify | `tests/documents/test_api.py` | Protect extension validation and response shapes. |
| Modify | `tests/documents/test_tasks.py` | Protect task translation/import seam. |
| Modify | `tests/documents/test_vector_retrieval.py` | Update the moved error import without changing retrieval behavior. |
| Create | `tests/documents/test_module_boundaries.py` | Assert leaf modules do not import ingestion. |

## Implementation Steps

1. **Tests Before:** add an AST/import-boundary test encoding the allowed dependency matrix for
   `tasks`, `ingestion`, `extraction`, `chunking`, `vector_store`, contracts, constants, and
   exceptions; strengthen existing tests to assert `Chunk` is frozen, upload and extraction accept
   the same extension set, and stable errors remain unchanged.
2. Run the focused suite and record the expected failing boundary/contract tests before moving code.
3. **Refactor:** create dependency-free modules; move `Chunk`, `IngestionError`, constants, and
   pipeline without behavior edits; replace lazy imports with module-qualified top-level imports so
   test seams remain explicit; update every monkeypatch target plus task/test imports; remove
   `services.py` only after `rg` finds no consumers.
4. **Tests After:** add direct import tests in clean subprocess/module order and rerun upload,
   ingestion, extraction, chunking, vector-store, and task tests.
5. **Regression Gate:** run lint/format and all document tests before Phase 2.

## Validation Commands

```bash
rg -n "apps\.documents\.services|from apps\.documents\.ingestion" apps tests
uv run pytest tests/documents/test_module_boundaries.py tests/documents/test_ingestion_pipeline.py tests/documents/test_chunking.py tests/documents/test_extraction.py tests/documents/test_api.py tests/documents/test_tasks.py tests/documents/test_vector_store.py -q
uv run pytest tests/documents -q
uv run ruff check apps/documents tests/documents
uv run ruff format --check apps/documents tests/documents
```

## Success Criteria

- [x] Tests fail first for the intended cycle/shared-contract gaps, then pass after extraction.
- [x] No application or test import references `apps.documents.services`.
- [x] The allowed-import matrix proves leaf modules cannot recreate orchestration cycles.
- [x] Upload/status schemas, messages, chunk IDs, metadata, and task behavior are unchanged.
- [x] Document test suite, lint, and formatting pass.

## Risk Assessment

- Risk: import-path migration can break Celery startup. Mitigate with clean-process imports and task
  tests; rollback by restoring `services.py` and old imports as one atomic revert.
- Risk: centralizing constants accidentally changes API text. Lock exact strings before refactor.
- Security: preserve path sanitization and owner metadata on every chunk; filename/content prompt
  injection and extraction resource bounds remain explicit accepted limitations in Phase 4.
