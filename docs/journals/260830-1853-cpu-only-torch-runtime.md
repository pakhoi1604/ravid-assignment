---
date: 2026-08-30
session: cpu-only-torch-runtime
---

# Journal: 2026-08-30 — CPU-only Torch Runtime

## Context

The document-ingestion image was 8.82 GB because PyPI Torch pulled unused CUDA, NVIDIA, and GPU Triton packages into a CPU-only deployment. The goal was to remove that payload without changing the embedding model, application APIs, or Docker service contracts.

## What Happened

- Added Torch as a direct vector-ingestion dependency and mapped only it to the official explicit PyTorch CPU index; all other packages remain on PyPI.
- Regenerated the lock, removing accelerator dependencies while preserving the LangChain 1.x and Chroma 1.5.9 stack.
- Rebuilt and verified the image with `torch==2.13.0+cpu`, 0 accelerator packages, and CUDA unavailable.

## Measured Impact

- Image size fell from 8.82 GB to 1.19 GB, about an 86.5% reduction.
- All 8 focused document tests passed.
- A real `all-MiniLM-L6-v2` smoke test produced one non-zero 384-dimensional embedding.

## Decisions Made

| Decision | Rationale | Impact |
| --- | --- | --- |
| Pin Torch through an explicit CPU-only index | The assignment runtime does not require GPU execution | Prevents CUDA packages from re-entering the Linux dependency graph |
| Preserve the existing embedding and service contracts | Image size was a packaging issue, not an application-design issue | No source, API, database, model, or Compose contract changes |

## Residual Limitations

The locked wheel set targets the assignment's Debian-based Linux runtime; Intel macOS and musl Linux are unsupported. The Docker base image and installed `uv` version also remain floating pre-existing inputs.

## Next Steps

- Resume the RAG chat-engine plan now that the CPU runtime optimization no longer blocks it.
