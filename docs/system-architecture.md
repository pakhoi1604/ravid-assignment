# RAVID System Architecture

## Module Boundaries

RAVID is a modular Django monolith with four domain app packages.

- `apps.accounts`: Django identity/JWT endpoints plus local subscriptions and concurrency-safe daily
  token usage.
- `apps.documents`: upload, document metadata, ingestion status, extraction, chunking, and vector
  indexing, with owner-filtered retrieval.
- `apps.rag`: bounded prompt construction, OpenRouter free-tier integration, quota orchestration,
  and the synchronous chat API.
- `apps.common`: shared liveness and narrowly reusable infrastructure.

Django's built-in user model remains the authentication identity. `Subscription` and
`DailyTokenUsage` extend that identity through related account-domain tables, retaining Django's
password hashing, authentication backends, permissions, sessions, and admin integration without
duplicating credential logic.

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

OpenRouter calls are synchronous and originate only from `web`. Its API key is not forwarded to
Celery, Flower, or the profile-gated test service. `openrouter/free` is the default model router;
live requests need a free-tier account and key, but no paid subscription.

## Persistence

- `postgres_data`: relational database state.
- `media_data`: uploaded files for later document-management work.
- `chroma_data`: vector-store data.
- `hf_cache`: downloaded embedding/model artifacts.

Redis result state is operational only. User-visible ingestion status is stored in PostgreSQL.

Document ingestion extracts text from PDF, TXT, and Markdown files, splits text with LangChain,
embeds chunks, and writes them to one Chroma collection. Vector records carry user and public
document metadata. Retrieval always applies the authenticated user's identifier as a native Chroma
filter before results are returned.

Each worker caches at most eight Chroma/store/embedding configurations in-process and serializes
cold construction. This avoids reloading SentenceTransformer weights for every chat query while
keeping the authenticated owner filter on each independently created retriever.

The application depends on modular LangChain packages only: `langchain-text-splitters` for
chunking, `langchain-huggingface` for local embeddings, `langchain-chroma` for vector storage,
`langchain-core` for document/prompt abstractions, and `langchain-openrouter` for the chat model.
The provider boundary also declares `openrouter` and `httpx` directly because it imports their
locked exception families for narrow error translation; it does not create a second SDK client.
The umbrella `langchain` package is not installed because source code does not import it. Torch is
pinned to the official CPU-only package index, preserving local embeddings without CUDA runtime
packages and reducing the shared application image from 8.82 GB to 1.19 GB.

For chat, the service verifies an active local subscription, validates free-tier provider
configuration, retrieves bounded owner-scoped context, reserves a conservative daily-token bound,
and then calls OpenRouter. Known provider failures refund the reservation; successful calls settle
it against provider usage metadata or a deterministic fallback estimate. A no-context query returns
a fixed answer without provider use or quota consumption. The local quota is an application guard,
not OpenRouter billing credit.

The synchronous OpenRouter client has a 10-second request budget and disables SDK retries. Known
transport/provider failures refund the reservation and return a generic `503`; retry policy remains
with the caller rather than holding both Gunicorn workers during a free-tier outage. The locked
LangChain integration receives one explicitly configured OpenRouter SDK client because its
`max_retries=0` shortcut otherwise falls back to the SDK's default retry policy.

Retrieved chunks leave the application boundary when sent to OpenRouter and its selected free
model provider. Reviewer smoke tests therefore use only the repository's synthetic handbook;
private uploads require explicit approval before live provider use.

## Public Surface

The current public API surface is intentionally limited to:

- `GET /api/health/`
- `GET /api/schema/`
- `GET /api/docs/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `POST /api/documents/upload/`
- `GET /api/documents/status/?task_id=<task_id>`
- `POST /api/chat/query/`

Billing/payment and HyDE remain out of scope. Subscription and daily usage are intentionally local
account-domain state rather than public billing endpoints.
