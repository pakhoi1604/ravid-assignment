# RAVID Backend Skeleton Plan

---
date: 2026-08-30T11:15:00+07:00
type: technical-journal
scope: backend-foundation-planning
---

## Context

RAVID needs a reproducible backend foundation before document ingestion, retrieval, chat, and
billing can be implemented. The planning session translated that need into a three-phase skeleton
plan without changing application code or claiming runtime verification.

## What Happened

The plan defined a Django/DRF modular monolith with `accounts`, `documents`, `rag`, and `common`
apps. It split delivery into application scaffolding, runtime/container wiring, and developer plus
reviewer verification.

The proposed runtime uses PostgreSQL, Redis, Celery, Chroma, and Flower. Python 3.12 dependencies
will be resolved and committed through `uv.lock`, while one application image will serve both the
Django web process and Celery worker. Compose remains a minimal six-service stack: `web`, `celery`,
`db`, `redis`, `chroma`, and `flower`.

## Decisions

- Keep business domains inside one modular Django deployment rather than introducing services
  before feature boundaries require them.
- Use PostgreSQL for relational state, Redis for Celery transport/results, Chroma for later vector
  storage, and Flower for worker visibility.
- Share one locked application image between web and worker, with persistent database, media,
  Chroma, and model-cache volumes where required.
- Expose only liveness, OpenAPI schema, and Swagger documentation in the foundation.
- Verify configuration, imports, routes, migrations, Compose rendering, service readiness, and a
  real worker-broker handshake; startup must not call OpenRouter.
- Omit Loki, Alloy, Grafana, speculative feature APIs, and fake background tasks.

## Deferred Scope

Authentication policy, subscriptions and credits, uploads, ingestion jobs, LangChain retrieval,
OpenRouter requests, HyDE, conversations, SSE, cloud deployment, and centralized logging remain
outside this skeleton plan. Their contracts and behavior require separate implementation work.

## Next

Execute Phase 1 by creating the locked Python environment, Django project and app boundaries,
split settings, and the public health/schema/documentation routes. Keep the plan pending until the
documented checks have actually run and passed.
