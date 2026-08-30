# RAVID System Architecture

## Module Boundaries

RAVID is a modular Django monolith. The foundation registers four app packages and keeps feature
behavior out until the owning plans are implemented.

- `apps.accounts`: future identity, subscriptions, and daily usage ownership.
- `apps.documents`: future uploads, document metadata, and ingestion status.
- `apps.rag`: future LangChain retrieval, OpenRouter integration, and HyDE flow.
- `apps.common`: shared liveness and narrowly reusable infrastructure.

Django's built-in user model is used for the foundation. A custom user model is deferred until an
authentication plan defines the required policy.

## Service Topology

Docker Compose defines one application image used by both `web` and `celery`.

- `web` applies migrations and serves Django through Gunicorn.
- `celery` starts a worker and autodiscovers Django tasks.
- `db` stores relational state in PostgreSQL.
- `redis` provides the Celery broker and result backend.
- `chroma` provides internal vector storage for later LangChain work. Its image is based on pinned
  `chromadb/chroma:1.0.15` with `curl` added for health checks.
- `flower` exposes a loopback-only Celery dashboard for reviewers.

The application services share media and Hugging Face cache volumes so later ingestion and query
work can use the same uploaded files and downloaded embedding models.

## Persistence

- `postgres_data`: relational database state.
- `media_data`: uploaded files for later document-management work.
- `chroma_data`: vector-store data.
- `hf_cache`: downloaded embedding/model artifacts.

Redis result state is operational only. Future ingestion status that users depend on must be stored
in PostgreSQL.

## Public Surface

The current public API surface is intentionally limited to:

- `GET /api/health/`
- `GET /api/schema/`
- `GET /api/docs/`

Future document, chat, billing, and HyDE endpoints should add their own serializers, service
boundaries, tests, and contract documentation when implemented.
