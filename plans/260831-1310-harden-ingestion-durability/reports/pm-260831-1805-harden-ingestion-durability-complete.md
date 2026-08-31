# Plan Complete: Harden Ingestion Durability and Resource Bounds

## Summary

| Item | Result |
| --- | --- |
| Status | Completed |
| Phases | 5/5 completed |
| Main code areas | documents models, ingestion, tasks, vector store, retrieval, dispatch, recovery |
| Public API change | Status endpoint now returns `PENDING` truthfully |
| Dispatch semantics | PostgreSQL outbox, at-least-once broker publication |
| Retrieval semantics | PostgreSQL active generation plus Chroma owner/generation filtering |

## Delivered

- Added `Document.active_generation`, `IngestionJob.generation`, durable generation manifests, and ingestion dispatch outbox rows.
- Replaced delete-before-add ingestion with generation-qualified Chroma writes and exact readback before activation.
- Added active-generation retrieval facade and fail-closed direct vector retrieval requiring a non-empty generation allowlist.
- Added fenced Celery task claim/finalize flow, stale pending/processing recovery, legacy reindex reset, and exact-generation cleanup.
- Added bounded page, extracted-character, and chunk ceilings before embedding/vector writes.
- Added Beat/outbox/recovery/cleanup settings, Compose service wiring, operator commands, and docs.

## Verification

| Gate | Result |
| --- | --- |
| `uv --cache-dir /tmp/uv-cache run ruff check apps config tests` | Pass |
| `uv --cache-dir /tmp/uv-cache run python manage.py check --settings=config.settings.local` | Pass |
| `uv --cache-dir /tmp/uv-cache run python manage.py check --settings=config.settings.test` | Pass |
| `uv --cache-dir /tmp/uv-cache run python manage.py makemigrations --check --dry-run --settings=config.settings.test` | Pass |
| `uv --cache-dir /tmp/uv-cache run pytest` | Pass, 274 passed / 3 skipped |
| `docker compose config --quiet` | Pass |

Subagent verification also passed Docker-backed checks, including Chroma production tests, rebuilt Compose stack smoke, and management command import/runtime smoke. Repo-wide `ruff check .` still fails on pre-existing `.agents/` and `.claude/` lint debt; scoped application lint passes.

## Review Closure

- Code-review findings fixed: chunk preflight before LangChain splitting, stale recovery queryset filtering, expired outbox claim exhaustion to `DEAD`, bounded cleanup retry exhaustion, direct vector retrieval generation requirement, processing lease setting use, and docs corrections.
- Docs-manager findings fixed: cleanup command documented, Beat wording corrected, stale pending recovery documented, and missing ingestion knobs added.

## Residual Risks

- Chroma and PostgreSQL are still not in one distributed transaction; cleanup remains eventual.
- Duplicate delivery is fenced for activation but can still waste worker CPU.
- Parser limits are not MIME/signature validation, antivirus, PDF sandboxing, or tenant quotas.
- Some Docker verification emitted warnings but passed; warnings were not expanded in this session.
