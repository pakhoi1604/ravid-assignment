---
title: "RAG Chat Engine Offline QA"
date: "2026-08-30"
agent: tester
scope: "plans/260830-1525-rag-chat-engine"
status: passed
---

# Test Report — 2026-08-30 — RAG Chat Engine Offline QA

## Summary

All required offline, static, schema, unit, integration, image, runtime-import, and service-smoke
gates passed. PostgreSQL concurrency and Chroma owner isolation were exercised against healthy
Docker services rather than skipped local substitutes. No credentialed OpenRouter request ran and
no dotenv file, API key, JWT, or expanded Compose configuration was inspected or printed.

## Test Results Overview

| Scope | Passed | Failed | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: |
| Focused pytest | 114 | 0 | 2 | 4.91s |
| Full pytest | 114 | 0 | 2 | 4.12s |
| PostgreSQL entitlement race | 1 | 0 | 0 | 0.96s |
| Chroma owner isolation | 1 | 0 | 0 | 1.81s |

The two local skips were the PostgreSQL and real-Chroma tests; both passed separately in the
profile-gated Docker test image.

## Findings

### Dependency and Static Gates

- `uv lock --check`: passed; 172 packages resolved.
- `uv sync --all-extras --dev --frozen`: passed; 169 packages checked.
- Ruff check: passed.
- Ruff format check: passed; 76 files already formatted.
- Django system check: passed with zero issues.
- Migration drift check: passed; no changes detected.
- OpenAPI generation/validation with `--fail-on-warn`: passed with no warnings.
- `docker compose config --quiet`: passed without rendering configuration.

The first Ruff invocations hit the sandbox's read-only default uv cache. Re-running the exact gates
with `UV_CACHE_DIR=/tmp/ravid-rag-uv-cache` passed; this was a QA-environment issue, not a product
or dependency failure.

### Build and Runtime Gates

- Runtime image `ravid-app:local`: built successfully.
- Profile-gated image `ravid-app:test`: built successfully with pytest and Ruff available.
- Runtime imports passed for `langchain_openrouter.ChatOpenRouter`,
  `langchain_core.documents.Document`, `ChatPromptTemplate`, and `BaseRetriever`.
- Runtime image check confirmed pytest is absent.
- Locked Docker installation resolved CPU-only `torch==2.13.0+cpu`,
  `langchain-core==1.6.1`, and `langchain-openrouter==0.2.8`.

Docker Compose warned that the buildx plugin is unavailable and used the classic builder. Both
images still completed successfully; this is a local tooling warning, not a build failure.

### Docker Integration and Smoke Gates

- PostgreSQL and Chroma reached healthy state before integration execution.
- Two simultaneous quota reservations respected the real PostgreSQL row-lock invariant.
- Real Chroma retrieval returned only the authenticated owner's documents.
- Full stack reached healthy state: web, PostgreSQL, Redis, Chroma, Celery, and Flower.
- `make smoke` passed health, OpenAPI schema, docs, database readiness, Redis ping, Chroma
  heartbeat, Celery worker ping, and Flower worker API checks.
- The healthy review stack remains running; no volumes or user data were removed.

## Coverage Metrics

Coverage percentages were not collected because the accepted plan requires full pytest and the two
Docker invariants but defines no coverage command or threshold. Test execution did not suppress
coverage failures.

## Critical Issues

None.

## Recommendations

1. Low priority: install Docker buildx to remove the classic-builder warning and improve build
   output/performance.
2. Run the documented OpenRouter free-tier smoke only with an explicitly rotated reviewer key and
   network authorization; do not reuse or expose an existing local credential.

## Unresolved Questions

- Credentialed OpenRouter behavior remains intentionally unverified by this offline QA run.
