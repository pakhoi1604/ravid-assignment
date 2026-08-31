---
phase: 3
title: "Strengthen Probes and Runtime Controls"
status: pending
priority: P1
dependencies: [2]
---

# Phase 3: Strengthen Probes and Runtime Controls

## Overview

Give liveness/readiness distinct contracts, make worker health target the local worker, and set
resource controls from measured workload behavior rather than arbitrary limits.

## Requirements

- Functional: preserve `GET /api/health/` as cheap dependency-free liveness.
- Functional: add internal readiness with bounded DB, Redis, and Chroma checks and no secret leakage.
- Functional: Celery health verifies the current worker, not any broadcast respondent.
- Non-functional: resource/shutdown budgets cover normal upload and embedding workflows.

## Architecture

Add a readiness view/route or management command under `apps.common`; return generic status while
logging only safe dependency names. Compose uses the chosen probe with `start_period`. Target Celery
inspection at a deterministic hostname. Measure RSS, CPU, and cold model load before changing
limits, concurrency, or recycle settings. Do not add late acknowledgement: ingestion has no
generation guard and vector replacement is delete-then-add.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/common/views.py` — bounded readiness.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/common/urls.py` — readiness route.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/compose.yaml` — probes, start periods, measured limits.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py` — timeout/resource settings if needed.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_health.py` — liveness/readiness behavior.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py` — probe/budget contracts.

## Implementation Steps

1. Define semantics, response codes, dependency list, and per-check/total timeout budgets.
2. Add tests first: liveness ignores dependencies; readiness fails generically per unavailable dependency.
3. Implement readiness with narrow queries, no retries, and guaranteed cleanup.
4. Point Compose at the chosen health contract and add startup grace periods.
5. Give Celery a deterministic hostname and destination-scoped ping; prove another worker cannot mask failure.
6. Measure memory/CPU during cold load, one upload, repeated ingestion, and chat.
7. Set limits/concurrency/recycle/shutdown only from measurements, with reviewer overrides.
8. Run dependency-stop and graceful-stop cases; document automatic versus manual recovery.

## Success Criteria

- [ ] Liveness stays fast and green when dependencies are unavailable.
- [ ] Readiness becomes non-ready within budget for DB, Redis, or Chroma failure and recovers.
- [ ] Probe responses/logs contain no credentials, secret URLs, document text, or provider details.
- [ ] Celery health verifies the addressed local worker.
- [ ] Reviewer workflows stay within measured limits without OOM or premature SIGKILL.
- [ ] Late acknowledgement remains disabled and residual stuck-task risk is documented.

## Risk Assessment

- Deep readiness can cascade load. Use minimal operations, tight timeouts, and no retries.
- Docker does not restart a merely unhealthy container. Document probe versus restart semantics.
- Hardware varies. Store rationale and allow overrides instead of unexplained ceilings.

## Security Considerations

Readiness exposes availability only. Roll it back independently if it causes load; never replace
liveness with an unbounded dependency fan-out.
