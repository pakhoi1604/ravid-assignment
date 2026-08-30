---
phase: 2
title: Upgrade Minimal LangChain Components
status: completed
priority: P1
dependencies:
  - 1
---

# Phase 2: Upgrade Minimal LangChain Components

<!-- Updated: Validation Session 1 - local Chroma 1.0.15 data is disposable test state. -->

## Overview

Replace the old umbrella-driven dependency graph with stable modular LangChain components and an
aligned Chroma runtime. Regenerate and audit the lockfile as one coherent migration.

## Requirements

- Functional: keep every Part 1 import available under Python 3.12 and preserve the Docker extra.
- Non-functional: use stable releases only; avoid unused umbrella/transitive direct declarations;
  keep the lock reproducible with `uv sync --frozen`.

## Architecture

`pyproject.toml` declares project-owned runtime requirements. `uv.lock` owns transitives such as
`langchain-core`, `transformers`, and `tokenizers`. The Chroma Python client and Docker server use
the same stable release to reduce wire/storage compatibility ambiguity.

Target optional dependency group:

```toml
vector-ingestion = [
    "chromadb==1.5.9",
    "langchain-chroma>=1.1.0,<2",
    "langchain-huggingface>=1.2.2,<2",
    "langchain-text-splitters>=1.1.2,<2",
    "pypdf>=6,<7",
    "sentence-transformers>=5.2,<6",
]
```

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/pyproject.toml` - replace the old group.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/uv.lock` - regenerate and audit.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docker/chroma/Dockerfile` - align the
  server image to `chromadb/chroma:1.5.9` while preserving non-root execution and health tooling.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/compose.yaml` - align the local image tag.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py` -
  assert the stable Chroma version and existing non-root/container contracts.

## Implementation Steps

1. Remove `langchain>=0.3,<0.4`; add `langchain-text-splitters` explicitly.
2. Upgrade `langchain-chroma` and `langchain-huggingface` to the stable 1.x component lines.
3. Keep `sentence-transformers` as a direct concrete embedding runtime on the integration-supported
   `<6` line; do not add the broader `[full]` extra.
4. Do not declare `langchain-core`; let the three LangChain components resolve one compatible 1.x
   core transitively until Part 2 directly imports it.
5. Align the exact `chromadb` constraint, Chroma Docker base image, and Compose image tag to
   `1.5.9`.
6. Regenerate `uv.lock` with upgrades limited to the affected package family.
7. Audit the lock diff: no prereleases, no umbrella `langchain`, one core version, no unrelated
   direct dependency additions, Python 3.12 satisfied.
8. Verify frozen local and Docker dependency installation paths.

## Success Criteria

- [x] `uv lock --check` succeeds.
- [x] `uv sync --all-extras --dev --frozen` succeeds.
- [x] The lock contains `langchain-core` 1.x transitively and does not contain `langchain`.
- [x] The three LangChain component packages resolve at or above the recorded stable lower bounds.
- [x] Chroma client/server version-bearing files all resolve to `1.5.9`.
- [x] Docker still installs only the `vector-ingestion` extra for runtime.

## Risk Assessment

This is a coordinated core-family upgrade. Partial upgrades are forbidden. If resolution or Part 1
compatibility fails, revert the manifest/lock/image set together; do not mix 0.3 and 1.x components.
Local Chroma `1.0.15` persistence is test data and has no backward-compatibility requirement; Phase
3 resets the related application-state volumes together before validation.

## Security Considerations

Preserve the non-root Chroma image and internal-only network exposure. Do not add indexes, tokens,
or credentials while changing dependency configuration.
