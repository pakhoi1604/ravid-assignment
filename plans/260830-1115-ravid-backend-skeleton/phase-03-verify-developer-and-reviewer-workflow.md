---
phase: 3
title: "Verify Developer and Reviewer Workflow"
status: completed
priority: P1
dependencies: [2]
---

# Phase 3: Verify Developer and Reviewer Workflow

## Overview

Add focused automated checks, CI, architecture documentation, and deterministic local/reviewer
commands. Verification must test actual startup boundaries instead of merely asserting files exist.

## Context Links

- [Plan overview](./plan.md)
- [Phase 2](./phase-02-wire-runtime-services-and-containers.md)

## Requirements

- Functional: local commands cover dependency sync, Django checks, migrations, tests, lint, and
  Compose startup.
- Functional: README provides one Docker-first reviewer workflow and one non-Docker workflow.
- Functional: CI runs offline checks without requiring an OpenRouter key.
- Non-functional: tests remain narrow and prove configuration, liveness, and service boundaries.
- Non-functional: no test makes a paid or network LLM request.

## Architecture

Verification layers:

1. Static: Ruff, Django system checks, missing-migration check, Compose rendering.
2. Unit/smoke: health response, settings invariants, Celery configuration, URL/schema generation.
3. Container: image build and six-service readiness, including a real worker-broker handshake.
4. Human reviewer: README commands reproduce the same validated flow.

## Related Code Files

- Create: `tests/__init__.py`, `tests/conftest.py`.
- Create: `tests/smoke/__init__.py`, `tests/smoke/test_health.py`,
  `tests/smoke/test_configuration.py`.
- Create: `tests/integration/__init__.py`, `tests/integration/test_runtime_boundaries.py` only when
  it can exercise real services without duplicating shell smoke commands.
- Create: `Makefile` - thin wrappers around authoritative `uv`, Django, pytest, Ruff, and Compose
  commands.
- Create: `.github/workflows/ci.yml` - dependency sync, lint, checks, migrations, and tests.
- Create: `README.md` - prerequisites, environment setup, Docker reviewer path, local path, service
  URLs, checks, troubleshooting, and deferred scope.
- Create: `docs/system-architecture.md` - module boundaries, service topology, persistence, and
  future feature ownership.
- Modify: `pyproject.toml` pytest/coverage configuration only when checks require correction.
- Modify: `compose.yaml` or Docker files only for failures discovered by real boot verification.

## Implementation Steps

1. Add pytest fixtures for Django test settings without requiring PostgreSQL, Redis, Chroma, or an
   OpenRouter key for unit checks.
2. Test health response, public documentation routes, registered apps, production database engine,
   Celery broker configuration, and absence of provider calls during startup.
3. Add a missing-migration check so the skeleton cannot drift from models.
4. Add Make targets as aliases only; README and CI should call the same underlying commands.
5. Add CI for `uv sync --all-extras --dev --frozen`, Ruff, Django checks, migration consistency,
   and pytest.
6. Write the system architecture document with explicit ownership for future accounts, documents,
   ingestion, and RAG work.
7. Write the README Docker-first flow: copy `.env.example`, set required secrets, build, start,
   check health/docs/Flower, and stop without deleting volumes.
8. Run the complete local check suite.
9. Run `docker compose config --quiet`, build, start, inspect health, verify the worker in Flower,
   and inspect logs for startup errors.
10. Stop containers normally. Test volume destruction only when explicitly requested; do not use
    `down -v` as a routine verification step.

## Verification Commands

```bash
uv sync --all-extras --dev --frozen
uv run ruff check apps config tests
uv run python manage.py check --settings=config.settings.test
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run pytest
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
docker compose exec celery celery -A config inspect ping
```

Use `curl` for `/api/health/` and `/api/schema/`; confirm Flower lists the worker. Exact Chroma
health command must match the pinned image version.

## Security Considerations

- CI uses sentinel values only and never reads developer `.env` files.
- README must warn users not to commit `.env` or expose Flower publicly.
- Logs may include service and request identifiers but not secrets or private payloads.
- Dependency audit findings must be reviewed, not suppressed to force green CI.

## Risk Assessment

- SQLite-based unit tests do not validate PostgreSQL behavior. Mitigation: keep them for skeleton
  speed and require a real Compose startup check before phase completion.
- File-existence tests create false confidence. Mitigation: assert imports, settings, routes, and
  live service handshakes.
- CI container tests can be slow due to ML dependencies. Mitigation: CI runs locked Python checks;
  document the Docker smoke command and add it to CI only if execution time remains acceptable.

## Success Criteria

- [x] Ruff, Django checks, migration check, and pytest pass from the locked environment.
- [x] CI requires no real OpenRouter key and performs no provider request.
- [x] Docker image builds and all six services reach their expected ready state.
- [x] A real Celery worker-broker handshake succeeds.
- [x] README commands match commands actually executed during verification.
- [x] Architecture documentation matches the created modules and Compose topology.
- [x] No feature behavior, unnecessary observability stack, or destructive volume command is added.
