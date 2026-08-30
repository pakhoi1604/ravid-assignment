# RAVID Backend

Runnable Django/DRF backend for the RAVID document knowledge-base assignment. This repository
supports authenticated document upload, asynchronous ingestion status, extraction, chunking, and
Chroma vector indexing. Chat, credits, billing, subscriptions, HyDE, and LLM answer generation are
intentionally deferred.

## Prerequisites

- Docker Compose v2 for the reviewer workflow.
- Python 3.12 and `uv` for local development without Docker.

## Docker Reviewer Path

1. Prepare local environment values:

   ```bash
   cp .env.example .env
   ```

   The example file contains local-only placeholders. Replace `SECRET_KEY`,
   `POSTGRES_PASSWORD`, and `FLOWER_BASIC_AUTH` before sharing or running outside a private
   workstation.

2. Build and start the stack:

   ```bash
   docker compose build
   docker compose up -d
   ```

3. Verify the public reviewer URLs:

   ```bash
   curl --fail --silent --show-error http://localhost:8000/api/health/
   curl --fail --silent --show-error --output /dev/null http://localhost:8000/api/schema/
   curl --fail --silent --show-error --output /dev/null http://localhost:8000/api/docs/
   docker compose exec db pg_isready -U ravid -d ravid
   docker compose exec redis redis-cli ping
   docker compose exec chroma curl --fail --silent http://localhost:8000/api/v2/heartbeat
   docker compose exec celery celery -A config inspect ping
   curl --fail --silent --show-error --output /dev/null --user ravid:change-me http://localhost:5555/api/workers
   ```

   Swagger UI is available at `http://localhost:8000/api/docs/`. Flower is bound to loopback at
   `http://localhost:5555/`.

   Load local-only, non-admin test accounts and exercise document upload:

   ```bash
   make load-test-accounts
   curl --fail --silent --show-error \
     -X POST http://localhost:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"reviewer","password":"reviewer-password-123"}'
   curl --fail --silent --show-error \
     -X POST http://localhost:8000/api/documents/upload/ \
     -H "Authorization: Bearer <access-token>" \
     -F "file=@docs/2026-08-30 R.A.V.I.D.md"
   curl --fail --silent --show-error \
     "http://localhost:8000/api/documents/status/?task_id=<task-id>" \
     -H "Authorization: Bearer <access-token>"
   ```

4. Stop containers without deleting persisted data:

   ```bash
   docker compose down
   ```

## Local Development Path

```bash
uv sync --all-extras --dev --frozen
uv run python manage.py check --settings=config.settings.local
uv run python manage.py check --settings=config.settings.test
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run pytest
uv run python manage.py runserver
```

The local settings use SQLite and eager Celery, so unit tests do not require PostgreSQL, Redis,
Chroma, or an OpenRouter key. The Docker image installs the vector-ingestion runtime used by the web
and worker containers.

The `vector-ingestion` extra installs only the LangChain components Part 1 imports:
`langchain-text-splitters`, `langchain-chroma`, and `langchain-huggingface`. The unused `langchain`
umbrella package is intentionally omitted; shared packages such as `langchain-core` remain
transitive until application source imports them directly. Torch resolves from the official
PyTorch CPU-only index because document embeddings do not require a GPU runtime.

Load the same test accounts locally with:

```bash
make load-test-accounts-local
```

JWT access tokens are configured for reviewer convenience and last 7 days by default. Override
`JWT_ACCESS_TOKEN_LIFETIME_DAYS` and `JWT_REFRESH_TOKEN_LIFETIME_DAYS` in `.env` if needed.

## Checks

`make sync`, `make lint`, `make check`, `make migrations`, `make test`, and
`make compose-config`, and `make load-test-accounts` are thin wrappers around the authoritative
commands used by CI and the reviewer path.

## Services

- `web`: Django/DRF served by Gunicorn on `127.0.0.1:8000`.
- `celery`: asynchronous worker using the same application image.
- `db`: PostgreSQL with a named volume.
- `redis`: Celery broker and result backend.
- `chroma`: internal vector store service for document ingestion. The image is derived
  from pinned `chromadb/chroma:1.5.9` only to add `curl` for a real Compose health check. The Python
  client is pinned to the same version.
- `flower`: local Celery dashboard on `127.0.0.1:5555`.

PostgreSQL, Redis, and Chroma are not published to external host interfaces.

## Troubleshooting

- If containers need custom secrets or ports, create `.env` from `.env.example` and override the
  placeholder values locally.
- If the web container is unhealthy, inspect startup logs with `docker compose logs web`.
- If the worker is missing from Flower, run `docker compose exec celery celery -A config inspect ping`.
- Do not commit `.env`, uploaded media, local databases, model caches, or generated coverage output.
