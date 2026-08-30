---
phase: 1
title: "Pin, Build, and Verify CPU-only Torch"
status: completed
priority: P1
dependencies: []
---

# Phase 1: Pin, Build, and Verify CPU-only Torch

## Requirements

- Preserve the current stable LangChain and Chroma dependency versions.
- Use an explicit index so only Torch resolves from the PyTorch CPU repository.
- Keep all other packages on PyPI.
- Preserve Python 3.12, frozen Docker installation, and existing embedding APIs.

## Related Files

- Modify: `pyproject.toml` - direct CPU Torch requirement, source mapping, and explicit index.
- Modify: `uv.lock` - regenerated CPU-only dependency graph.

## Implementation Steps

1. Add a compatible direct Torch requirement to the `vector-ingestion` extra.
2. Add an explicit `pytorch-cpu` index and map only `torch` to it.
3. Regenerate `uv.lock` and audit the graph for CUDA/NVIDIA/GPU Triton packages.
4. Run lock, frozen-sync, focused document-test, Django, and Compose checks.
5. Build the shared `ravid-app:local` image from the frozen lock.
6. Inspect image size and installed package directories.
7. Run Torch CPU and real MiniLM embedding smoke checks inside the rebuilt image.
8. Review the final diff for dependency drift and public-contract changes.

## Success Criteria

- [x] CPU-only Torch replaces the current `2.13.0+cu130` runtime.
- [x] CUDA/NVIDIA payloads are absent from the rebuilt Linux image.
- [x] Part 1 document behavior remains green.
- [x] No application source, API, database, or Docker service contract changes.

## Verification Results

- `uv lock --check`: passed with 169 packages.
- `uv sync --all-extras --dev --frozen`: passed; 20 GPU-related packages removed.
- Focused document tests: 8 passed.
- Django system check: passed; Docker Compose config: passed.
- Image runtime: `torch==2.13.0+cpu`, CUDA unavailable, no NVIDIA/CUDA/Triton distributions.
- Embedding smoke: 384 dimensions and non-zero values.
- Image size: 1.19 GB versus 8.82 GB baseline.
