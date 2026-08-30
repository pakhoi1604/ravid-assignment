---
date: 2026-08-30
session: langchain-dependency-refresh-implementation
---

# Journal: 2026-08-30 — LangChain Dependency Refresh Implementation

## Context

Part 1 needed a supported, minimal LangChain dependency set without changing the document-ingestion API. The refresh also aligned the Python Chroma client and Docker Chroma server before rerunning unit, integration, and live-stack checks.

## What Happened

- Replaced the umbrella `langchain` dependency with only the modules used by ingestion: `langchain-chroma` 1.1.0, `langchain-huggingface` 1.2.2, and `langchain-text-splitters` 1.1.2. The lock resolves their shared `langchain-core` dependency to 1.6.1.
- Kept the other direct ingestion dependencies constrained to the required stable lines: `chromadb` 1.5.9, `pypdf` 6.x, and `sentence-transformers` 5.x (resolved to 5.7.0).
- Aligned the Chroma Docker image with the Python client at 1.5.9. No production API source code changes were necessary.
- Expanded tests for chunk overlap and blank input, vector-store constructor wiring, ingestion metadata and chunk IDs, and the exact Chroma client/server version contract.
- With explicit user authorization for disposable test data, reset only the project-owned PostgreSQL, media, and Chroma volumes. The Hugging Face cache volume was preserved.
- The live Docker upload completed with `SUCCESS`; Chroma contained one 384-dimensional embedding record with the expected metadata.

## Verification

- 16 focused dependency, ingestion, and Compose contract tests passed.
- 56 full tests passed.
- Ruff, Django system checks, migration drift check, and Compose configuration validation passed.
- The rebuilt live stack completed authentication, upload, asynchronous ingestion, and direct Chroma record verification.

## Reflection

Using module-level LangChain packages keeps the dependency surface tied to code the project actually imports. Matching Chroma at both sides removed an avoidable client/server compatibility variable while preserving the existing public behavior.

The rebuilt `ravid-app` image is approximately 8.82 GB because the PyPI `torch` 2.13 dependency path includes CUDA transitive packages. This does not block correctness, but it is an operational cost that should be handled separately instead of broadening this dependency refresh.

## Decisions Made

| Decision | Rationale | Impact |
| --- | --- | --- |
| Use modular LangChain dependencies only | The ingestion path uses specific integrations and splitters, not the umbrella package | Smaller, clearer dependency contract and no unused top-level `langchain` package |
| Pin Chroma client and server to 1.5.9 | Keep the runtime protocol boundary aligned and reproducible | Focused and live-stack checks run against the same version |
| Preserve `hf_cache` during the data reset | Cached model artifacts are not application test records | Avoids an unnecessary model download while PostgreSQL, media, and vector data start clean |
| Defer CPU image optimization | Image slimming is independent from the correctness scope of this refresh | Follow-up can evaluate CPU-only Torch packaging without delaying Part 1 validation |

## Next Steps

- Create a separate CPU-image optimization plan for the Torch/CUDA dependency footprint.
- Keep the Chroma version contract test updated whenever either client or server is upgraded.
