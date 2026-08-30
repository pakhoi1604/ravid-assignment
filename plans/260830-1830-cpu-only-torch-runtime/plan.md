---
title: "Use CPU-only Torch Runtime"
description: "Remove unused CUDA payloads from the RAVID application image while preserving local Hugging Face embeddings."
status: completed
priority: P1
branch: "main"
tags: [dependencies, docker, pytorch, performance]
blockedBy: []
blocks: [260830-1525-rag-chat-engine]
created: "2026-08-30T18:30:00+07:00"
createdBy: "ck:cook"
source: skill
---

# Use CPU-only Torch Runtime

## Overview

Pin Torch to the official CPU-only PyTorch package index. Keep the current
`sentence-transformers`/`HuggingFaceEmbeddings` design and the completed LangChain 1.x dependency
refresh while removing CUDA, NVIDIA, and GPU Triton payloads from the Linux application image.

## Phase

| Phase | Name | Status |
| --- | --- | --- |
| 1 | [Pin, build, and verify CPU-only Torch](./phase-01-pin-build-and-verify-cpu-torch.md) | Completed |

## Scope

- Declare Torch as a direct `vector-ingestion` runtime dependency.
- Pin Torch to the official explicit CPU-only index through `tool.uv.sources`.
- Regenerate and audit `uv.lock` without discarding the completed LangChain refresh.
- Build the shared application image and verify CPU embedding behavior.

Out of scope: changing the embedding model, using a remote embedding API, enabling GPU support,
rewriting the ingestion pipeline, Dockerfile layer optimization, and public API changes.

## Acceptance Criteria

- [x] `torch` resolves from `https://download.pytorch.org/whl/cpu`.
- [x] Linux runtime resolution no longer installs NVIDIA, CUDA, or GPU Triton packages.
- [x] `uv lock --check` and frozen sync succeed.
- [x] Existing focused document tests pass.
- [x] The rebuilt image reports a CPU Torch build and `torch.cuda.is_available() == False`.
- [x] A real `HuggingFaceEmbeddings` call returns a non-empty embedding.
- [x] The rebuilt image is materially smaller than the current 8.82 GB baseline.

## Open Questions

None. The assignment does not require GPU execution and the selected MiniLM embedding model remains
local and CPU-backed.

## Completion Notes

- Locked Linux to `torch==2.13.0+cpu` on the explicit official PyTorch CPU index.
- Removed 18 NVIDIA/CUDA packages plus CUDA bindings/toolkit and GPU Triton from the lock and local
  environment.
- Focused document tests passed: 8/8; Django system check and Compose rendering also passed.
- Rebuilt `ravid-app:local` at 1.19 GB, down from 8.82 GB (about 86.5%).
- Container verification reported CUDA unavailable and no accelerator distributions.
- Real MiniLM smoke produced one non-zero 384-dimensional embedding.
