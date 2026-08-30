---
title: "Scaffold RAVID Backend Foundation"
description: "Create a runnable, containerized Django foundation for the RAVID document RAG assignment."
status: completed
priority: P1
branch: "main"
tags: [backend, infra, database, api]
blockedBy: []
blocks: []
created: "2026-08-30T04:15:15.200Z"
createdBy: "ck:plan"
source: skill
---

# Scaffold RAVID Backend Foundation

## Overview

Create a modular Django/DRF foundation that boots locally and through Docker Compose with
PostgreSQL, Redis, Celery, Chroma, and Flower. Establish configuration and operational wiring only;
document ingestion, chat, billing, and HyDE remain follow-up work.

## Architecture Decisions

- Modular monolith: `accounts`, `documents`, `rag`, and `common` Django apps.
- DRF/drf-spectacular for APIs; PostgreSQL for relational state.
- Redis/Celery for async work; Chroma through its later LangChain adapter for vectors.
- Flower for the task dashboard; no Loki, Alloy, or Grafana.
- `uv` lockfile and one application image shared by web and worker.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Scaffold Django Application](./phase-01-scaffold-django-application.md) | Completed |
| 2 | [Wire Runtime Services and Containers](./phase-02-wire-runtime-services-and-containers.md) | Completed |
| 3 | [Verify Developer and Reviewer Workflow](./phase-03-verify-developer-and-reviewer-workflow.md) | Completed |

## Dependencies

- Requirement source: `2026-08-30 R.A.V.I.D.md`.
- Prior agent-rules plan is completed and does not block this plan.
- Host prerequisites: Docker Compose v2; Python 3.12 and `uv` for non-Docker work.
- OpenRouter is configured for later work; skeleton startup makes no provider request.

## Scope

- Python/Django dependency and configuration foundation.
- Django app packages, liveness, OpenAPI, and Swagger routes.
- `web`, `celery`, `db`, `redis`, `chroma`, and `flower` Compose services.
- Health checks plus persistent database, media, Chroma, and model-cache volumes.
- Lint, Django checks, tests, Compose validation, CI, and reviewer documentation.

Out of scope: feature endpoints/models, authentication, payment/subscriptions, ingestion tasks, RAG,
OpenRouter calls, credits, HyDE, conversations/SSE, cloud deployment, and centralized logging.

## Acceptance Criteria

- [x] `uv sync --all-extras --dev --frozen` installs a locked Python 3.12 environment.
- [x] `uv run python manage.py check` and `uv run pytest` pass.
- [x] `docker compose config --quiet` succeeds without requiring a real secret file.
- [x] Compose starts healthy web, PostgreSQL, Redis, Chroma, worker, and Flower services.
- [x] Web and worker share one image plus media and model-cache volumes.
- [x] `/api/health/`, `/api/schema/`, and `/api/docs/` are reachable from the web container.
- [x] PostgreSQL/Redis connectivity, Celery registration, and Flower visibility are verified.
- [x] `.env.example` contains safe placeholders; runtime secrets and data remain ignored.
- [x] README gives one deterministic Docker reviewer path and one local development path.

## Open Questions

None for the skeleton. Feature-level ambiguities remain deferred to their owning plans.
