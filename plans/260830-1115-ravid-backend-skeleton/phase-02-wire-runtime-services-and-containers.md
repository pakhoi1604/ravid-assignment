---
phase: 2
title: "Wire Runtime Services and Containers"
status: completed
priority: P1
dependencies: [1]
---

# Phase 2: Wire Runtime Services and Containers

## Overview

Wire PostgreSQL, Redis, Celery, Chroma, and Flower into Django and package the foundation as a
six-service Docker Compose stack. The stack must be reproducible for reviewers and remain minimal.

## Context Links

- [Plan overview](./plan.md)
- [Phase 1](./phase-01-scaffold-django-application.md)
- Assignment Docker requirement: `2026-08-30 R.A.V.I.D.md`, Part 4.

## Requirements

- Functional: production Django connects to PostgreSQL and Redis using service DNS names.
- Functional: a Celery worker boots, discovers Django tasks, and appears in Flower.
- Functional: web and worker can access the same media, Chroma, and Hugging Face model cache.
- Functional: Chroma is available as an internal HTTP service for later LangChain integration.
- Non-functional: Compose health checks gate dependent services where supported.
- Non-functional: infrastructure ports are internal or bound to loopback; only reviewer UIs are
  intentionally published.
- Non-functional: the application image runs as a non-root user.

## Architecture

| Service | Responsibility | Persistence | Published port |
| --- | --- | --- | --- |
| `web` | Django/DRF through Gunicorn | shared media/model cache | `8000` |
| `celery` | asynchronous ingestion worker | shared media/model cache | none |
| `db` | PostgreSQL relational state | `postgres_data` | none by default |
| `redis` | Celery broker/result backend | ephemeral for local demo | none by default |
| `chroma` | shared vector storage | `chroma_data` | none by default |
| `flower` | Celery dashboard | none | `5555` on loopback |

The web container applies migrations before Gunicorn starts. The worker never runs migrations.
Celery result state is operational only; later ingestion jobs must persist public status in
PostgreSQL.

## Related Code Files

- Create: `.env.example` - safe placeholders and documented environment contract.
- Create: `.dockerignore` - exclude Git data, plans, docs not needed at runtime, caches, media,
  secrets, and local virtual environments.
- Create: `compose.yaml` - six services, networks, health checks, dependencies, and volumes.
- Create: `docker/django/Dockerfile` - reproducible non-root application image.
- Create: `docker/django/entrypoint.sh` - execute the supplied container command without embedding
  secrets or service-specific branching.
- Create: `config/celery.py` - Celery application using the `CELERY_` settings namespace.
- Modify: `config/__init__.py` - export the Celery application for autodiscovery.
- Modify: `config/settings/base.py` - Redis/Celery, Chroma, embedding, OpenRouter, upload, chunk, and
  retrieval configuration defaults.
- Modify: `config/settings/production.py` - required PostgreSQL and container service settings.
- Modify: `.gitignore` - Docker/runtime volumes and downloaded model artifacts.
- Modify: `pyproject.toml` and `uv.lock` only if container verification exposes a missing runtime
  dependency; regenerate the lock after any change.

## Environment Contract

- Django: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE`.
- PostgreSQL: database, user, password, host, and port.
- Redis/Celery: one Redis URL used consistently as broker/result configuration.
- Chroma: host and port.
- OpenRouter: API key placeholder, base URL, and model name; no call during skeleton startup.
- RAG tuning: embedding model, upload limit, chunk size, overlap, and retrieval top-k.
- Flower: optional local basic-auth credentials, documented as local-only defaults.

## Implementation Steps

1. Add Celery initialization and settings without creating a fake task.
2. Create `.env.example`; ensure `.env` remains ignored and Compose can render with placeholders.
3. Build one application image from the locked environment. Use a non-root runtime user and retain
   only OS libraries required at runtime.
4. Define PostgreSQL, Redis, and Chroma with pinned image versions and health checks.
5. Define `web` and `celery` from the same image; mount shared media and Hugging Face cache volumes.
6. Define Flower against the same Redis broker; do not add Grafana, Loki, or Alloy.
7. Configure startup ordering. Apply migrations only in the web startup path, then launch Gunicorn.
8. Add named volumes for PostgreSQL, media, Chroma, and Hugging Face cache.
9. Validate `docker compose config --quiet`, build the image, and start the stack.
10. Verify Django health, PostgreSQL readiness, Redis ping, Chroma heartbeat, Celery inspect ping,
    and Flower worker visibility.

## Security Considerations

- Use safe placeholders in `.env.example`; never add a real `.env` to Git.
- Do not publish PostgreSQL, Redis, or Chroma to all host interfaces.
- Do not mount the Docker socket or run containers as root.
- Avoid returning infrastructure connection details from the health endpoint.
- Keep development credentials clearly labeled as local-only and overridable.

## Risk Assessment

- Chroma client/server mismatch can prevent startup. Mitigation: pin both sides to a tested
  compatible release and validate the exact heartbeat endpoint.
- Runtime model downloads can occur twice. Mitigation: mount one `hf_cache` volume into web and
  worker; document first-run behavior.
- Automatic migrations can race if web replicas increase. Mitigation: acceptable for one local web
  container; document a separate release migration step for real deployment.
- Compose `depends_on` does not prove application readiness forever. Mitigation: include service
  health checks and explicit smoke verification.

## Success Criteria

- [x] Compose renders and builds from a clean checkout.
- [x] All six required services start without manual container edits.
- [x] Web, PostgreSQL, Redis, and Chroma health checks pass.
- [x] Celery responds to inspection and is visible in Flower.
- [x] Web and worker share media and Hugging Face cache volumes.
- [x] Infrastructure services are not publicly exposed.
- [x] Stopping and starting Compose preserves PostgreSQL and Chroma data.
