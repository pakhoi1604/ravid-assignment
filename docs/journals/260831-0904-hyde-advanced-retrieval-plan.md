---
date: 2026-08-31
session: hyde-advanced-retrieval-plan
type: journal
---

# Journal: 2026-08-31 - HyDE Advanced Retrieval Plan

## Context

Planned the optional Part 3 HyDE extension for the existing authenticated RAG endpoint. The work
reuses the current owner-scoped Chroma retrieval adapter, ChatOpenRouter/LCEL boundary, bounded
prompts, safe error translation, and atomic quota reservation model. This session produced planning
artifacts only; no application implementation was performed.

## What Happened

- Ran the plan in hard mode with repository research, adversarial review, factual validation, and a
  final cross-file consistency sweep.
- Kept the public switch narrow: omitted or strict boolean `false` preserves standard retrieval,
  while strict boolean `true` requests HyDE without accepting coercible JSON values.
- Defined a bounded HyDE sequence: generate and validate one hypothetical passage, retrieve
  owner-scoped real chunks with it, then synthesize from only those real chunks and the original
  query. The hypothetical passage is retrieval input, never evidence.
- Restricted expected HyDE failures to a generic `hyde_unavailable` fallback that retries retrieval
  with the original query and exposes no provider details.
- Added bounded, grading-visible retrieved chunks to successful metadata, with count and order
  matching the exact real context supplied to synthesis.
- Required a controlled-embedding Chroma evaluation that exercises actual similarity selection
  without claiming universal improvement for production embeddings.

## Reflection

The existing RAG boundaries support HyDE without a new service, vector API, provider integration,
dependency, or persistence model. Hard-mode review was most valuable around quota settlement: a
simple fallback design was insufficient until dispatch ambiguity, malformed usage, later-stage
failure, and the limits of the aggregate reservation model were stated explicitly.

## Decisions Made

| Decision | Rationale | Impact |
| --- | --- | --- |
| Default the strict `use_hyde` toggle to `false` | Preserve baseline latency, cost, and behavior | Standard requests make no HyDE provider call |
| Bound generation by timeout, token cap, character cap, and zero retries | Limit experimental-provider cost and failure duration | Invalid or unavailable output follows one narrow fallback contract |
| Retrieve with the hypothetical but answer with the original query and real chunks only | HyDE should improve retrieval recall, not become evidence | Keeps grounding and owner isolation on the existing trusted path |
| Settle conservatively after dispatch and exactly once per in-process path | Provider work may have occurred even when the response is ambiguous | HyDE usage remains charged across fallback or later failure; pre-dispatch failures refund |
| Return bounded owner-scoped chunks in additive metadata | The assignment requires retrieval visibility for grading | Successful responses expose only the exact bounded synthesis context |
| Evaluate with controlled embeddings and real Chroma retrieval | Deterministic ranking differences are testable without model-quality claims | Validation proves orchestration and selection behavior, not universal accuracy gains |

## Next Steps

- Implement the three plan phases in order: bounded generation, orchestration/accounting, then API
  metadata and repository-wide validation.
- Preserve the current threshold/MMR working-tree changes while extracting shared retrieval-setting
  validation.
- Run focused RAG, retrieval, configuration, schema, lint, full-suite, and Compose checks before
  considering the plan complete.

## Status

Plan complete and pending implementation.

## Summary

The accepted design adds optional, bounded HyDE through existing RAG components, safely falls back
to original-query retrieval, and exposes bounded real retrieval evidence for grading.

## Concerns

The current aggregate quota model cannot provide durable exactly-once settlement. An in-process
guard limits each path to one settlement action, but worker death after reservation can still strand
a conservative charge; a persisted reservation ledger remains explicitly out of scope.
