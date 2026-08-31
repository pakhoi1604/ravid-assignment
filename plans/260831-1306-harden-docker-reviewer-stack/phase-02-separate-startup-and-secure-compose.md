---
phase: 2
title: "Separate Startup and Secure Compose"
status: pending
priority: P1
dependencies: [1]
---

# Phase 2: Separate Startup and Secure Compose

## Overview

Separate schema migration from web startup and make the single-host reviewer Compose lifecycle,
durability, network access, and environment contract explicit and fail-fast.

## Requirements

- Functional: one migration service completes before web and worker start.
- Functional: Redis queue/result state survives ordinary recreation through AOF and a named volume.
- Non-functional: long-running services have restart/shutdown behavior; one-shot/test services do not restart.
- Configuration: non-secret semantic defaults remain in Django settings; unset optional operator knobs
  are omitted so application defaults apply, while required secrets fail during Compose interpolation.
- Security: keep loopback bindings, explicit per-service allowlists, web-only provider access, minimal
  Flower credentials, and no secrets in commands or rendered logs.

## Architecture

Add one-shot `migrate` using `ravid-app:local`; web runs Gunicorn only and web/worker depend on
successful migration and healthy infrastructure. Give Redis AOF storage. Define only network
segments justified by real flows. Apply least-privilege controls after Phase 1 proves writable paths.

Keep one base Compose file explicitly scoped to a single-host reviewer, not production. Compose uses
small YAML mapping extensions for PostgreSQL credentials, Django bootstrap/topology, broker, and
vector connectivity; it does not use a global `env_file` or a mega-anchor. Each service merges only
the small groups it needs and keeps an explicit role-specific allowlist: web owns HTTP/JWT/provider/
RAG/retrieval, Celery owns DB/broker/vector/ingestion, test owns DB/vector, and Flower owns broker/auth
plus only bootstrap variables proven necessary by import-time execution.

Required secrets use fail-fast interpolation in the base file. Optional operator knobs use verified
null or single-key pass-through so an unset value is absent from the container and Django remains the
single source of semantic defaults. Do not repeat literal RAG defaults in Compose or contract tests.
Move Flower authentication out of argv into a file-backed mechanism verified against the installed
Flower version. Do not replace argv exposure with another value that raw Compose output prints.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/compose.yaml` — migration, persistence, restart, shutdown, networks, credentials, hardening.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py` — lifecycle and isolation contracts.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py` — retain canonical non-secret semantic defaults where ownership is currently duplicated.
- Modify: project root environment template under `/home/khoipham/Projects/ravid-assignment/Ravid/` — document required secrets and optional knobs without real values.

## Implementation Steps

1. Inventory every current environment key and its consumer; prove any Django import-time variables
   Flower needs before removing DB, vector, or other bootstrap settings.
2. Define small mapping extensions for PostgreSQL credentials, Django bootstrap/topology, broker, and
   vector connectivity. Merge them selectively and keep role-specific keys explicit; add no global
   `env_file` and no all-service mega-anchor.
3. Make required secrets fail during base Compose interpolation. Express optional operator knobs as
   null or single-key pass-through, then verify both rendered Compose and actual container environments:
   unset means omitted/application default, set means the exact override is forwarded.
4. Remove duplicated non-secret RAG literals from Compose and tests, preserving Django settings as
   the semantic default source. Update the project root environment template without secret values.
5. Remove Flower authentication from argv and adopt an installed-version-supported file-backed
   mechanism; ensure process argv and captured logs do not reveal the credential.
6. Add `migrate` with no restart and successful-completion dependencies; remove migration from web.
7. Add Redis AOF, compatible healthcheck, `redis_data`, restart policies, and shutdown budgets; state
   that persistence is not exactly-once delivery.
8. Segment networks and apply capability drop, no-new-privileges, read-only roots, and explicit
   writable paths without breaking web, worker, migration, Flower, test, DB, broker, or Chroma.
9. Add semantic contracts for exact per-service key sets, web-only OpenRouter access, optional omission
   and forwarding, missing-secret failure, absence of global `env_file`, rendered anchor values, clean
   Flower argv, lifecycle ordering, persistence, ports, networks, and container controls.

## Success Criteria

- [ ] Web contains no migration command and waits for successful one-shot migration.
- [ ] Recreating Redis preserves a synthetic queued item; volume deletion remains documented as destructive.
- [ ] Only web and Flower bind host ports, both on `127.0.0.1`.
- [ ] Rendered and runtime environments match exact role-owned key sets; OpenRouter is web-only,
      Flower is broker/auth-minimal, and test receives only DB/vector configuration.
- [ ] Required secrets fail fast; an unset optional knob is omitted and uses the Django default, while
      a supplied override is forwarded unchanged; Compose/tests contain no duplicated RAG defaults.
- [ ] Small anchors render correctly; no global `env_file`, mega-anchor, or secret-bearing argv/log exists.
- [ ] Read-only/no-new-privileges controls pass startup and write-path tests.
- [ ] Base Compose is documented as a fail-fast single-host reviewer contract, not production.

## Risk Assessment

- Successful-completion ordering is not a distributed migration lock; multi-replica rollout stays out of scope.
- Redis AOF changes disk use/startup time. Measure and document recovery.
- Network/read-only controls can break imports or caches. Apply and verify incrementally.
- Null/single-key pass-through behavior may differ between Compose parsing and runtime injection;
  validate both layers before adopting the pattern or choose an equally omission-safe supported form.

## Security Considerations

Never place real secrets in Compose, templates, tests, image history, command arguments, or logs.
Rollback controls independently while retaining loopback binding and non-root execution.
