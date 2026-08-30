# RAVID Backend

Runnable Django/DRF backend for the RAVID document knowledge-base assignment. This repository
supports authenticated document upload, asynchronous ingestion status, extraction, chunking, and
Chroma vector indexing. It also provides owner-scoped retrieval, a grounded chat endpoint backed by
OpenRouter free-tier models, and local subscription/daily-token enforcement. Billing, payment, and
HyDE are intentionally out of scope.

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
   workstation. Add an OpenRouter API key only when exercising live chat. The configured
   `openrouter/free` router requires an OpenRouter account and API key, but no paid subscription.

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

   Load local-only, non-admin test accounts and obtain a JWT:

   ```bash
   make load-test-accounts
   curl --fail --silent --show-error \
     -X POST http://localhost:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"reviewer","password":"reviewer-password-123"}'
   ```

   Copy the `access` value from the token response. Upload the public-safe synthetic fixture and
   poll until its status is `SUCCESS`:

   ```bash
   curl --fail --silent --show-error \
     -X POST http://localhost:8000/api/documents/upload/ \
     -H "Authorization: Bearer <access-token>" \
     -F "file=@tests/fixtures/rag/reviewer-handbook.md"
   curl --fail --silent --show-error \
     "http://localhost:8000/api/documents/status/?task_id=<task-id>" \
     -H "Authorization: Bearer <access-token>"
   ```

   Query the indexed fact:

   ```bash
   curl --fail --silent --show-error \
     -X POST http://localhost:8000/api/chat/query/ \
     -H "Authorization: Bearer <access-token>" \
     -H "Content-Type: application/json" \
     -d '{"query":"What color is the Atlas emergency binder?"}'
   ```

   The `answer` should identify the binder as cobalt blue. Token accounting remains internal. If no
   owner-scoped context is found, the endpoint returns a fixed safe answer without calling the model
   or consuming local daily quota.

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

The local settings use SQLite and eager Celery, so unit/API tests do not require PostgreSQL, Redis,
Chroma, or an OpenRouter key. Provider and vector-store boundaries are mocked in deterministic
tests. The Docker image installs the vector-ingestion and RAG runtime used by the web and worker
containers.

The `vector-ingestion` extra installs only the LangChain components the source imports:
`langchain-text-splitters`, `langchain-chroma`, `langchain-huggingface`, `langchain-core`, and
`langchain-openrouter`. `openrouter` and `httpx` are also direct because the provider adapter imports
their locked exception types; they were already transitive requirements of the integration. The
unused `langchain` umbrella package is intentionally omitted. Torch resolves from the official
PyTorch CPU-only index because document embeddings do not require a GPU runtime.

Load the same test accounts locally with:

```bash
make load-test-accounts-local
```

JWT access tokens are configured for reviewer convenience and last 7 days by default. Override
`JWT_ACCESS_TOKEN_LIFETIME_DAYS` and `JWT_REFRESH_TOKEN_LIFETIME_DAYS` in `.env` if needed.

`DEFAULT_DAILY_TOKEN_LIMIT` is a local application quota, not OpenRouter billing credit. Seeded
reviewer accounts receive an active local subscription and the configured daily limit. Retrieved
document chunks are sent to the external model provider during live chat, so use only synthetic or
explicitly approved non-sensitive documents. Rotate any key that has previously been exposed.
Synchronous provider requests use a 10-second configured budget with retries disabled so free-tier
outages return a safe `503` without tying up web workers for minutes.

## Checks

`make sync`, `make lint`, `make check`, `make migrations`, `make test`, and
`make compose-config`, and `make load-test-accounts` are thin wrappers around the authoritative
commands used by CI and the reviewer path.

The profile-gated test image includes dev dependencies while normal runtime services do not. The
two infrastructure-backed invariant tests can be run with:

```bash
docker compose --profile test build test
docker compose --profile test up -d db chroma
docker compose --profile test run --rm test \
  pytest --ds=config.settings.production tests/accounts/test_entitlements_postgres.py -q
docker compose --profile test run --rm test \
  pytest --ds=config.settings.production tests/documents/test_vector_retrieval_chroma.py -q
```

## Services

- `web`: Django/DRF served by Gunicorn on `127.0.0.1:8000`.
- `celery`: asynchronous worker using the same application image.
- `db`: PostgreSQL with a named volume.
- `redis`: Celery broker and result backend.
- `chroma`: internal vector store service for document ingestion. The image is derived
  from pinned `chromadb/chroma:1.5.9` only to add `curl` for a real Compose health check. The Python
  client is pinned to the same version.
- `flower`: local Celery dashboard on `127.0.0.1:5555`.
- OpenRouter is called synchronously by `web` only; provider credentials are not forwarded to
  Celery, Flower, or the test service.

PostgreSQL, Redis, and Chroma are not published to external host interfaces.

## Troubleshooting

- If containers need custom secrets or ports, create `.env` from `.env.example` and override the
  placeholder values locally.
- If the web container is unhealthy, inspect startup logs with `docker compose logs web`.
- If the worker is missing from Flower, run `docker compose exec celery celery -A config inspect ping`.
- Do not commit `.env`, uploaded media, local databases, model caches, or generated coverage output.
