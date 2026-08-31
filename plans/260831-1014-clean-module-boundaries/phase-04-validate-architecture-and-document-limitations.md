---
phase: 4
title: "Validate Architecture and Document Limitations"
status: completed
priority: P1
dependencies: [3]
---

# Phase 4: Validate Architecture and Document Limitations

## Overview

Run full regression and architecture gates, then update maintainer documentation only where module
ownership or stale-vector correction changed. Record deferred production limitations without
expanding implementation scope.

## Requirements

- Preserve API/OpenAPI, document status, owner isolation, HyDE, quota, settings, and Compose behavior.
- Leave no import cycles, stale module names, migration drift, secrets, private content, or
  unsupported production claims.

## Architecture

```text
rag -> accounts.entitlements
rag -> documents.vector_store
documents.tasks -> documents.ingestion -> extraction/chunking/vector_store
leaf modules -> local dependency-free contracts/constants/exceptions
```

Docs must distinguish minimum delete/add replacement from deferred atomic versioning and must not
describe request-local settlement guards as crash-idempotent accounting.

## Related Code Files

| Action | File | Purpose |
| --- | --- | --- |
| Modify | `docs/system-architecture.md` | Record final ownership, explicit policy, limitations. |
| Modify | `README.md` | Update maintainer map only where paths changed. |
| Modify | `tests/documents/test_module_boundaries.py` | Close final dependency-check gaps. |
| Modify | `tests/smoke/test_health.py` | Final OpenAPI gate only. |
| Verify | `apps/accounts/**` | Confirm persistence behavior unchanged. |
| Verify | `config/settings/**`, `compose.yaml` | Confirm runtime contract unchanged. |

## Implementation Steps

1. **Tests Before:** capture a clean Phase 3 baseline; inspect diffs for out-of-scope API, settings,
   migration, or account-ledger edits.
2. Run static boundary checks and clean-process imports for ingestion, Celery task, vector retrieval,
   RAG contracts/accounting, serializers, and views.
3. **Refactor/document:** update architecture and README only for changed ownership and shrinking
   replacement. Keep setup/API examples stable unless they reference moved paths.
4. Document accepted deferred limitations: durable crash-idempotent quota ledger and settlement
   reconciliation; Celery stale-job recovery, duplicate-delivery/concurrency guards, and dispatch
   outbox; atomic/versioned Chroma replacement; synchronous worker concurrency; PDF signature/MIME
   validation plus extracted page/character/chunk caps and batched ingestion; prompt-injection
   hardening for document content and metadata.
5. **Tests After:** run owner-isolation, shrinking re-ingestion, settlement, API, OpenAPI,
   configuration, Django, migration, and Compose gates.
6. **Regression Gate:** run full tests, lint, format, diff checks, and whole-plan consistency review.

## Validation Commands

```bash
uv run pytest tests/documents/test_vector_store.py tests/documents/test_vector_retrieval.py tests/rag/test_hyde_retrieval.py tests/rag/test_services.py tests/rag/test_api.py tests/smoke/test_health.py -q
uv run pytest tests/documents tests/rag tests/accounts tests/smoke -q
uv run pytest -q
uv run ruff check apps config tests
uv run ruff format --check apps config tests
uv run python manage.py check --settings=config.settings.test
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
docker compose config --quiet
rg -n "apps\.documents\.services|class (RagAnswer|RetrievalMetadata)|def normalize_answer_content" apps tests README.md docs
git diff --check
```

## Success Criteria

- [x] Focused and full suites pass; skips are documented infrastructure-only cases.
- [x] Boundary test and clean imports prove no hidden document orchestration cycle.
- [x] Controlled shrinking re-ingestion and two-owner standard/HyDE retrieval pass.
- [x] API/OpenAPI, settings, account models/migrations, and Compose remain unchanged.
- [x] README/architecture describe only verified ownership and behavior.
- [x] Deferred production/security limitations are explicit and remain unimplemented.

## Risk Assessment

- Docs can imply guarantees absent from code. Use verified claims and explicit “deferred” language;
  rollback documentation independently if a claim cannot be proven.
- Environment-only skips can hide defects. Separate PostgreSQL/Compose-Chroma skips and run them in
  the production-settings container when available.
- Inspect diffs for secrets/private documents; no live provider call or private upload is required.
