---
phase: 4
title: "Validate Docker Workflow"
status: pending
priority: P1
dependencies: [1, 2, 3]
---

# Phase 4: Validate Docker Workflow

## Overview

Turn Docker and environment contracts into repeatable CI/reviewer checks, validate recovery paths,
and align commands and architecture documentation with the single-host reviewer scope.

## Requirements

- Functional: validate rendering, exact service environments, image targets, startup, migration,
  probes, ingestion, restart, shutdown, and persistence.
- Non-functional: retain Python gates and avoid live provider calls or private documents.
- Documentation: fix command drift and state remaining production limitations.

## Architecture

Layer validation from static contracts to image builds to live fault-oriented smoke tests. Extend
the current GitHub Actions workflow without duplicating it. Treat
`260830-1608-part-1-endpoint-smoke-tests` as a coordination-only plan: preserve its smoke targets if
they already exist, but do not wait for that plan before hardening the Docker workflow.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py` — final contracts.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/.github/workflows/ci.yml` — image build and focused verification.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/Makefile` — make documented Docker targets real and phony.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md` — reviewer commands, environment contract, and recovery notes.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docs/system-architecture.md` — topology, probes, durability, limitations.
- Modify: project root environment template under `/home/khoipham/Projects/ravid-assignment/Ravid/` — safe required/optional variable documentation without secret values.
- Create if useful: `/home/khoipham/Projects/ravid-assignment/Ravid/scripts/smoke-docker-recovery.sh` — deterministic recovery matrix.

## Implementation Steps

1. Check whether the endpoint-smoke plan has landed; preserve its Make/README work when present.
2. Require working long Make aliases `compose-config`, `compose-build`, `compose-up`, `compose-down`,
   and `load-test-accounts`; preserve short targets if present and test that aliases invoke real recipes.
3. Add semantic contract tests for exact per-service environment key sets, web-only OpenRouter,
   no global `env_file`, correctly rendered small anchors, missing-required-secret failure, omitted
   optional values/application defaults, forwarded overrides, and Flower argv free of authentication.
4. Verify optional pass-through at both `docker compose config` and container runtime; tests must not
   encode literal RAG defaults owned by Django settings.
5. Add CI image builds with cache; keep heavyweight embedding smoke outside routine PR CI unless budgeted.
6. Run Ruff, Django checks, migration drift, pytest, Compose rendering, contracts, and image metadata checks.
7. Run clean startup, one-shot migration, probes, synthetic upload/ingestion, Flower, and profile tests.
8. Stop/restart DB, Redis, Chroma, web, and worker; recreate Redis without deleting its volume; gracefully stop active work.
9. Use only synthetic reviewer data and no provider key; parse rendered configuration through a
   redacting validator and inspect argv/logs without echoing raw secret-bearing configuration.
10. Update the project root environment template and docs with variable ownership, commands, backup
    caveats, single-host boundary, and deferred idempotency/outbox/HA work.
11. Record final image size, timing, resource evidence, and rollback commands in the implementation report.

## Success Criteria

- [ ] CI builds runtime/test images and fails on Docker/Compose contract drift.
- [ ] Existing tests plus new probe/lifecycle contracts pass.
- [ ] Clean startup runs migration once before web/worker readiness.
- [ ] Redis recreation retains synthetic state; volume deletion is documented as destructive.
- [ ] Dependency failure/recovery matches documented probe behavior.
- [ ] Exact environment ownership and omission/override behavior pass at render and runtime; required
      secret failures and clean Flower argv are regression-tested without exposing values.
- [ ] Long Make aliases `compose-config`, `compose-build`, `compose-up`, `compose-down`, and
      `load-test-accounts` execute real recipes and remain compatible with documented commands.
- [ ] Docs call this single-host reviewer infrastructure, not HA production infrastructure, and the
      project root environment template contains no real secrets.

## Risk Assessment

- Live tests can be slow and need model downloads. Split fast PR gates from cached integration gates.
- Fault tests mutate containers. Target only this named project and never delete volumes by default.
- CI may lack embedding capacity. Keep deterministic contracts/builds mandatory and schedule heavy smoke separately.

## Security Considerations

Never print rendered secret values, provider keys, JWTs, or retrieved chunks in CI artifacts.
Rollback restores image/Compose revisions while preserving named volumes; it does not imply backup guarantees.
