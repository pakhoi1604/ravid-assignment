---
title: Refresh Minimal LangChain Dependencies and Revalidate Part 1
description: >-
  Replace the unused LangChain umbrella dependency with current stable
  components, align Chroma, and regression-test Part 1.
status: completed
priority: P1
branch: main
tags:
  - refactor
  - backend
  - tech-debt
  - test
blockedBy: []
blocks:
  - 260830-1525-rag-chat-engine
  - 260830-1608-part-1-endpoint-smoke-tests
created: '2026-08-30T10:40:14.764Z'
createdBy: 'ck:plan'
source: skill
---

# Refresh Minimal LangChain Dependencies and Revalidate Part 1

## Overview

Clean the Part 1 vector-ingestion dependency set before Part 2 begins. Remove the unused
`langchain` umbrella package, declare only the stable LangChain components and concrete runtime
backends the source actually uses, align the Chroma client/server versions, repair compatibility
breaks, and revalidate the complete Part 1 upload-to-vector flow.

"Current stable LangChain" means current stable component packages as of 2026-08-30. The project
must not install `langchain==1.3.18` merely for its version number when no Part 1 source imports it.
Part 2 will add its own chat/retrieval dependencies only when those imports are implemented.

## Scope Challenge

- Existing code: Part 1 imports `langchain_text_splitters`, `langchain_chroma`,
  `langchain_huggingface`, `chromadb`, and `pypdf`; it never imports `langchain` or
  `langchain_core` directly.
- Minimum changes: protect Part 1 contracts, update `pyproject.toml` and `uv.lock`, align the Chroma
  image, adapt only APIs proven incompatible, then run narrow, full, Docker, and live-ingestion
  checks.
- Complexity: three phases, no new services/classes. More than eight files may be touched because
  tests and version-bearing docs must match the dependency and container contract.
- Selected mode: HOLD SCOPE, fast planning. Version research and codebase scouting are complete.

## Dependency Policy

| Purpose | Direct dependency target | Rationale |
| --- | --- | --- |
| Chunking | `langchain-text-splitters>=1.1.2,<2` | Direct import in Part 1. |
| Chroma adapter | `langchain-chroma>=1.1.0,<2` | Direct import in Part 1. |
| Embedding adapter | `langchain-huggingface>=1.2.2,<2` | Direct import in Part 1. |
| Vector client/server | `chromadb==1.5.9` and image `1.5.9` | Direct client import; keep both sides exactly aligned. |
| Local embedding runtime | `sentence-transformers>=5.2,<6` | Required by `HuggingFaceEmbeddings`; stay within the integration's supported line. |
| PDF extraction | `pypdf>=6,<7` | Direct import; unrelated major upgrade excluded. |

Do not declare `langchain`, `langchain-core`, `transformers`, `tokenizers`, or other transitives
unless project source imports them directly or a documented runtime extra requires them.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Baseline Part 1 Contracts](./phase-01-baseline-part-1-contracts.md) | Completed |
| 2 | [Upgrade Minimal LangChain Components](./phase-02-upgrade-minimal-langchain-components.md) | Completed |
| 3 | [Repair and Revalidate Part 1](./phase-03-repair-and-revalidate-part-1.md) | Completed |

## Dependencies

- Completed prerequisite: `plans/260830-1329-document-management-vector-storage/`.
- Blocks `plans/260830-1525-rag-chat-engine/`; Part 2 must use the resolved 1.x component family.
- Blocks `plans/260830-1608-part-1-endpoint-smoke-tests/`; its reusable smoke tooling should be
  built against the refreshed stack.
- Official version metadata: PyPI pages for `langchain-text-splitters`, `langchain-chroma`,
  `langchain-huggingface`, and `chromadb`, checked 2026-08-30.

## Acceptance Criteria

- [x] `pyproject.toml` contains no unused `langchain` umbrella dependency.
- [x] Only source-used LangChain components and required concrete runtime backends are direct deps.
- [x] `uv.lock` resolves one coherent `langchain-core` 1.x family with no prerelease packages.
- [x] Chroma Python client and Docker server are aligned at stable `1.5.9`.
- [x] Part 1 source behavior and public API contracts remain unchanged.
- [x] Focused Part 1, full pytest, lint, Django checks, Compose config, Docker build, and live
  upload/index verification pass.
- [x] Local Docker application state is treated as disposable test data and reset before live
  verification; deletion is restricted to the resolved project-owned PostgreSQL, media, and Chroma
  volumes, while the Hugging Face model cache is preserved.

## Completion Notes

- Resolved modular components: `langchain-chroma==1.1.0`,
  `langchain-huggingface==1.2.2`, `langchain-text-splitters==1.1.2`, and one transitive
  `langchain-core==1.6.1`; the `langchain` umbrella package is absent.
- Independent verification passed: 16 focused tests, 56 full tests, Ruff, Django system check,
  migration drift, frozen lock/sync, Compose config, Docker build, and `git diff --check`.
- Fresh-stack upload reached `SUCCESS`; direct Chroma inspection found one non-empty 384-dimensional
  embedding with the expected owner, document, task, ingestion-job, chunk-index, and filename
  metadata. No production application source or public API contract changed.
- Reset was limited to the label-verified `ravid_postgres_data`, `ravid_media_data`, and
  `ravid_chroma_data` volumes under explicit user authorization. `ravid_hf_cache` was preserved,
  and the validation stack was stopped without deleting the newly verified state.
- Non-blocking follow-up: evaluate a reproducible CPU-only Torch source and avoid recursively
  changing ownership of the full virtual-environment layer; the current application image is
  approximately 8.82 GB.

## Open Questions

None. Use modular stable components; defer chat/OpenRouter packages to Part 2.

## Validation Log

### Session 1 — 2026-08-30

**Trigger:** `/ck:plan validate plans/260830-1740-langchain-dependency-refresh`
**Questions asked:** 1

#### Verification Results

- **Tier:** Standard — Fact Checker + Contract Verifier
- **Claims checked:** 30
- **Verified:** 28 | **Failed:** 0 | **Unverified:** 2
- Official metadata confirms stable, non-yanked releases and Python 3.12 support for
  `langchain-text-splitters==1.1.2`, `langchain-chroma==1.1.0`,
  `langchain-huggingface==1.2.2`, and `chromadb==1.5.9`.
- Dependency constraints intersect on one `langchain-core>=1.2.31,<2` family; none of the selected
  components requires the `langchain` umbrella package.
- Docker Hub confirms `chromadb/chroma:1.5.9` exists. Current source still pins server/image
  `1.0.15`, so Phase 2 targets real version-bearing files.
- Current Part 1 import/caller paths, metadata fields, vector IDs, lazy integration imports,
  non-root Docker contracts, and `vector-ingestion` install path were verified against source.
- Baseline checks passed: 5 focused document tests, 52 Part 1/account/smoke tests,
  `uv lock --check`, and `docker compose config --quiet`.

#### Questions & Answers

1. **[Data migration]** Must vectors stored in the current Chroma `1.0.15` test volume remain
   readable after upgrading to `1.5.9`, or may the local test data be recreated?
   - **Answer:** Delete and recreate it because it is test data.
   - **Rationale:** Avoid a legacy Chroma storage migration that has no assignment value.

#### Confirmed Decisions

- Current local Docker application data is disposable. Reset the project-owned PostgreSQL, media,
  and Chroma test volumes together so relational status, uploaded files, and vectors cannot become
  inconsistent. Preserve the Hugging Face cache.
- Live Docker validation uses one generated synthetic Markdown document to prove the complete
  upload-to-vector dependency path. Unit tests retain PDF/TXT/MD behavior coverage; the blocked
  endpoint-smoke plan owns the later reusable all-format fixture suite.

#### Impact on Phases

- Phase 2: no persisted Chroma `1.0.15` compatibility requirement.
- Phase 3: add an explicit, narrowly targeted test-state reset before fresh-stack validation and
  replace the ambiguous PDF/TXT/MD fixture wording with one generated Markdown fixture.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all three `phase-*.md` files.
- Decision deltas checked: 2 — disposable local state and one-format live smoke scope.
- Reconciled stale references: 5.
- Unresolved contradictions: 0.
