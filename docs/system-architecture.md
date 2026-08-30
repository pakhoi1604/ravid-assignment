# RAVID System Architecture

## Module Boundaries

RAVID is a modular Django monolith. The foundation registers four app packages and keeps feature
behavior out until the owning plans are implemented.

- `apps.accounts`: minimal JWT token endpoints now; subscriptions and daily usage remain future work.
- `apps.documents`: upload, document metadata, ingestion status, extraction, chunking, and vector
  indexing.
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
- `chroma` provides internal vector storage for document ingestion. Its image is based on pinned
  `chromadb/chroma:1.5.9` with `curl` added for health checks; the Python client uses the same
  version.
- `flower` exposes a loopback-only Celery dashboard for reviewers.

The application services share media and Hugging Face cache volumes so upload handling and Celery
ingestion use the same files and downloaded embedding models.

## Persistence

- `postgres_data`: relational database state.
- `media_data`: uploaded files for later document-management work.
- `chroma_data`: vector-store data.
- `hf_cache`: downloaded embedding/model artifacts.

Redis result state is operational only. User-visible ingestion status is stored in PostgreSQL.

Document ingestion extracts text from PDF, TXT, and Markdown files, splits text with LangChain,
embeds chunks, and writes them to one Chroma collection. Vector records carry user and public
document metadata so later retrieval can enforce owner isolation.

Part 1 depends on modular LangChain packages only: `langchain-text-splitters` for chunking,
`langchain-huggingface` for local embeddings, and `langchain-chroma` for vector storage. The
umbrella `langchain` package is not installed because Part 1 does not import it. Shared
`langchain-core` functionality remains transitive until a later module imports it directly. Torch
is pinned to the official CPU-only package index, preserving local embeddings without CUDA runtime
packages and reducing the shared application image from 8.82 GB to 1.19 GB.

## Public Surface

The current public API surface is intentionally limited to:

- `GET /api/health/`
- `GET /api/schema/`
- `GET /api/docs/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `POST /api/documents/upload/`
- `GET /api/documents/status/?task_id=<task_id>`

Future chat, billing, subscription, credit, and HyDE endpoints should add their own serializers,
service boundaries, tests, and contract documentation when implemented.
