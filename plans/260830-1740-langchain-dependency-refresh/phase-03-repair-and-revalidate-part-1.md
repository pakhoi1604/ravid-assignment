---
phase: 3
title: Repair and Revalidate Part 1
status: completed
priority: P1
dependencies:
  - 2
---

# Phase 3: Repair and Revalidate Part 1

<!-- Updated: Validation Session 1 - reset disposable Docker state and use one Markdown live smoke fixture. -->

## Overview

Run the migrated stack, make only compatibility changes proven necessary, and establish that Part 1
still uploads, extracts, chunks, embeds, stores, and reports ingestion status correctly.

## Requirements

- Functional: preserve the existing upload/status API and vector metadata contract end to end.
- Non-functional: no speculative refactor; repair only demonstrated 1.x API breaks; validate both
  offline tests and a real Docker/Chroma ingestion path.

## Architecture

Production code remains behind the existing `split_text`, `DocumentVectorStore`, and
`run_ingestion_pipeline` boundaries. Tests may require source edits only when current stable APIs
changed. Current Docker application persistence is test-only: resolve and reset only this project's
PostgreSQL, media, and Chroma volumes before starting a fresh validation stack. Preserve the shared
Hugging Face cache to avoid an unnecessary model download.

## Related Code Files

- Modify if required: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/chunking.py` -
  stable splitter API compatibility only.
- Modify if required: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/vector_store.py`
  - stable Chroma/HuggingFace adapter compatibility only.
- Modify if required: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/services.py` and
  `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/tasks.py` - only if regression tests
  expose a real ingestion failure.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md` - record the refreshed runtime
  versions and reviewer validation commands.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docs/system-architecture.md` - update the
  Chroma version and modular LangChain dependency decision.

## Implementation Steps

1. Run focused tests and classify failures as dependency resolution, import/API compatibility,
   behavioral regression, or faulty test assumption.
2. Apply the smallest source adaptation for proven stable API differences. Preserve lazy imports,
   error mapping, settings names, metadata, IDs, and public responses.
3. Run focused tests:
   `uv run pytest tests/documents/test_chunking.py tests/documents/test_vector_store.py tests/documents/test_ingestion_pipeline.py`.
4. Run Part 1 regression:
   `uv run pytest tests/accounts tests/documents tests/smoke`.
5. Run shared gates: Ruff, Django checks, migration drift check, frozen sync, and Compose config.
6. Resolve the exact Compose project and verify the project-owned `postgres_data`, `media_data`,
   and `chroma_data` volumes by Docker Compose labels. Stop the stack, then delete only those
   verified test volumes. Do not delete `hf_cache` or unrelated Docker volumes.
7. Build `web`, `celery`, and `chroma` images from the refreshed lock/image definitions.
8. Start the fresh stack, seed the reviewer account, generate and upload one synthetic Markdown
   document, poll to `SUCCESS`, and verify Chroma holds non-empty embeddings plus the expected
   `user_id`, `document_id`, `task_id`, and `chunk_index` metadata.
9. Stop the validation stack without deleting the newly verified state unless cleanup is explicitly
   requested.
10. Update version-bearing README/architecture statements after validation matches reality.
11. Record migration results and any required source adaptation in the plan completion notes.

## Success Criteria

- [x] Focused and complete Part 1 pytest suites pass.
- [x] Ruff, Django check, migration drift, frozen sync, and Compose config pass.
- [x] Refreshed Docker images build successfully.
- [x] Real upload reaches `SUCCESS` and creates owner-scoped Chroma records with embeddings.
- [x] Upload and ingestion-status HTTP contracts are unchanged.
- [x] No OpenRouter, chat, retriever, subscription, or credit dependency is introduced.
- [x] Only the explicitly resolved project-owned PostgreSQL, media, and Chroma test volumes are
  reset; the Hugging Face cache and unrelated Docker volumes are preserved.

## Risk Assessment

Adapter unit tests can pass while client/server communication fails, so the live fresh-stack
ingestion gate is mandatory. Volume resolution must fail closed if Docker labels do not identify
exactly the expected project-owned test volumes; never broaden deletion with an unverified name or
global prune command.

## Security Considerations

Verify Chroma remains internal-only, containers remain non-root, test fixtures contain no private
assignment/customer content, and logs do not print credentials or document contents.
