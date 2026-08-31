---
phase: 5
title: "Bound Ingestion Work and Validate"
status: completed
priority: P1
dependencies: [4]
---

# Phase 5: Bound Ingestion Work and Validate

## Overview

Add hard page, extracted-character, and chunk-count ceilings, then validate migration, dispatch,
recovery, indexing, retrieval, API, and Docker contracts. Update docs only after behavior is proven.

## Requirements

- Reject over-limit documents before embedding/vector writes.
- Plain text cannot be fully materialized beyond its character limit.
- PDF stops at page/character bounds and does not process later pages after overflow.
- Exact boundary passes; boundary + 1 fails with the existing sanitized public error.
- Limits are positive, configurable, and forwarded to worker runtime.

## Architecture

Conservative defaults:

```text
INGESTION_MAX_PDF_PAGES=200
INGESTION_MAX_EXTRACTED_CHARS=2000000
INGESTION_MAX_CHUNKS=2500
```

`ingestion.py` passes explicit limits to dependency-light extraction helpers. Text reads
`max_chars + 1`; PDF validates page count before extraction and tracks cumulative characters.
Chunking accepts `max_chunks` and aborts while splitting at `max_chunks + 1`; it never materializes
an unbounded list before checking. Validate `VECTOR_CHUNK_SIZE > VECTOR_CHUNK_OVERLAP >= 0` and
positive limits. No batching/streaming framework beyond these hard bounds.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/extraction.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/chunking.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/ingestion.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/views.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/management/commands/reconcile_orphan_uploads.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/test.py`
- Modify: project root environment template
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/compose.yaml`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_extraction.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_ingestion_pipeline.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_api.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_orphan_uploads.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_configuration.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docs/system-architecture.md`

## Implementation Steps

1. Write exact/over-limit tests for text chars, PDF pages/chars, and bounded splitting. Assert vector
   construction/write is never reached and splitting stops at `max_chunks + 1`.
2. Add positive settings validation and forward values only where runtime needs them.
3. Implement bounded text/PDF extraction and early chunk rejection with sanitized errors.
4. Run focused tests, PostgreSQL claim/outbox tests, and real Chroma generation tests.
5. Add compensating deletion when DB upload transaction fails after file save. Add a bounded,
   grace-period orphan-media reconciliation command for crash leftovers and storage-level tests.
6. Run lint, Django checks, migration drift, Compose config, full pytest, and reviewer smoke.
7. Add a deployment runbook: maintenance/no-chat gate, migrate, reset or restartable legacy reindex,
   verify active counts, enable service, then start Beat. Include rollback before filter activation.
8. Update README with truthful local Celery requirements, recovery/reindex, outbox/Beat, settings,
   and reset/live rollout instructions.
9. Update architecture limitations: no PG-Chroma transaction, eventual cleanup, at-least-once
   dispatch, and limits do not replace MIME/malware validation.

## Tests Before

- Preserve PDF/TXT/Markdown success and generic failures.
- Add failing `limit + 1` cases before each ceiling.

## Tests After

- Exact page/char/chunk limit passes; `+1` fails before vector write.
- Bounded splitter does not allocate the complete over-limit chunk list.
- PDF stops reading pages after cumulative overflow.
- Failed upload transaction deletes its saved file; orphan scan ignores recent/referenced files.
- Settings/Compose contracts cover only services that need values.
- Owner isolation, RAG, HyDE, quota, upload, and status regressions pass.

## Regression Gate

```bash
uv run ruff check .
uv run python manage.py check --settings=config.settings.local
uv run python manage.py check --settings=config.settings.test
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run pytest
docker compose config --quiet
```

## Success Criteria

- [x] All three ceilings reject before embedding/vector writes.
- [x] All five phases have focused failure-path coverage.
- [x] PostgreSQL and Chroma integration gates pass where mocks are insufficient.
- [x] README and architecture docs match actual runtime behavior.
- [x] Live rollout cannot enable generation-only retrieval before reindex/reset verification.
- [x] Full validation passes without unrelated contract changes.

## Risk Assessment

Defaults may reject legitimate large files. Mitigate with configuration and clear docs. Bounds
reduce denial-of-service exposure but do not validate MIME/signature or sandbox parsers.

## Security Considerations

Never log extracted text, chunks, source paths, or raw parser exceptions. Preserve owner filtering
and prompt safety. Limits are not antivirus.
