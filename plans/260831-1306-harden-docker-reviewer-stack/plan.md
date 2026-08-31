---
title: "Harden Docker Reviewer Stack"
description: "Harden the single-host Docker reviewer stack without claiming multi-host or production guarantees."
status: pending
priority: P1
branch: "main"
tags: [infra, docker, security, reliability, tech-debt]
blockedBy: []
blocks: [260831-1310-harden-ingestion-durability]
created: "2026-08-31T06:07:26.408Z"
createdBy: "ck:plan"
source: skill
---

# Harden Docker Reviewer Stack

## Overview

Improve image reproducibility, container least privilege, Compose startup ordering, Redis durability,
shutdown behavior, probes, environment ownership, and automated verification. Preserve the documented
single-host reviewer workflow, public API contracts, loopback bindings, and non-root users.

## Scope

- Harden the existing single-host reviewer topology with measured, test-backed changes.
- Keep one fail-fast base Compose contract for the documented single-host reviewer workflow; do not
  present it as production-ready or introduce a second ambiguous hardened override.
- Use small mapping anchors for PostgreSQL credentials, Django topology/bootstrap, broker, and vector
  settings while retaining explicit per-service environment allowlists and web-only OpenRouter access.
- Defer HA/multi-host deployment, managed services, object storage, Kubernetes, transactional
  outbox, and exactly-once task settlement.
- Do not enable Celery late acknowledgement or redelivery until ingestion has an idempotency or
  generation guard; Redis persistence alone does not solve in-flight task recovery.

## Cross-Plan Dependencies

| Relationship | Plan | Reason |
|---|---|---|
| Coordinates with | `260830-1608-part-1-endpoint-smoke-tests` | Both plans edit `Makefile` and `README.md`; preserve whichever changes land first. No technical output from either plan is a prerequisite for the other. |
| Blocks | `260831-1310-harden-ingestion-durability` | Establishes the broker, worker, environment, and validation contract that durability work extends. |

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Harden Container Images](./phase-01-harden-container-images.md) | Pending |
| 2 | [Separate Startup and Secure Compose](./phase-02-separate-startup-and-secure-compose.md) | Pending |
| 3 | [Strengthen Probes and Runtime Controls](./phase-03-strengthen-probes-and-runtime-controls.md) | Pending |
| 4 | [Validate Docker Workflow](./phase-04-validate-docker-workflow.md) | Pending |

## Dependencies

- Phase 2 depends on Phase 1 so Compose hardening targets the final image contract.
- Phase 3 depends on Phase 2 so probes match the final service topology and migration lifecycle.
- Phase 4 validates all implementation phases and preserves any endpoint-smoke commands already present.
- The ingestion durability plan starts only after Phase 4 establishes the Compose environment contract.

## Overall Acceptance Criteria

- Reviewer startup, upload/ingestion, chat, Flower, and profile-gated tests remain usable.
- Application source is not writable by runtime; required media/cache/temp paths are writable.
- Migration is a one-shot dependency; Redis survives ordinary container recreation; long-running
  services have explicit restart and shutdown policies.
- Environment ownership is exact by service: no global `env_file`, no mega-anchor, provider secrets
  stay web-only, Flower stays minimal, required secrets fail fast, and unset optional knobs defer to
  Django defaults without duplicated RAG literals.
- Liveness stays dependency-free; readiness has bounded dependency checks and distinct semantics.
- Compose contracts, image builds, focused tests, and a live recovery smoke matrix pass.
- Documentation states residual task-loss, single-host persistence, backup, and HA limitations.

## Validation Log

- Baseline Compose rendering passed on 2026-08-31.
- Baseline `tests/smoke/test_compose_contracts.py` passed 12/12 before implementation.
- Planner fact-check: all planned existing paths and referenced settings were verified in-repo.
- Dependency audit on 2026-08-31: endpoint-smoke work is coordination-only, so this plan is
  unblocked and ready to start; implementation status remains pending.
- Implementation must verify actual Compose render/runtime semantics for null or single-key optional
  pass-through before relying on omission and application defaults.
