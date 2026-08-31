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

Within `apps.documents`, `ingestion.py` owns the workflow and depends on the leaf extraction,
chunking, and vector-store adapters. Dependency-free `constants.py`, `contracts.py`, and
`exceptions.py` hold shared document-domain definitions; leaf modules do not import the
orchestrator. Within `apps.rag`, `services.py` remains the query-use-case orchestrator while
`contracts.py`, `provider_responses.py`, and `accounting.py` own result DTOs, provider parsing, and
request-local quota settlement respectively. These are internal module boundaries, not additional
Django apps or services.

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
document metadata. Re-ingestion resolves every prior vector using a trusted owner-plus-document
filter before replacement, so shrinking documents do not retain stale tail chunks and corrupted
cross-owner metadata is not deleted. Incoming owner/document metadata and deterministic chunk IDs
are validated at the adapter boundary. Retrieval always applies the authenticated user's identifier
as a native Chroma filter and then validates returned owner metadata before results leave the
adapter.

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

For chat, the service verifies an active local subscription and validates free-tier provider and
retrieval configuration before either retrieval mode runs. The optional `use_hyde` request field is
a strict JSON boolean and defaults to `false`. Omitted/false requests retrieve with the original
query. A true request first asks OpenRouter for a bounded hypothetical passage and uses that passage
only as the owner-scoped vector-retrieval query. The hypothetical is not evidence: final synthesis
always receives the original user question plus only real, owner-filtered chunks.

Both paths bound the selected chunks by `RAG_MAX_CONTEXT_CHARS`. Every successful response returns
the exact excerpts supplied to final synthesis, in order, as `retrieved_chunks`, with the matching
`retrieved_chunks_count`. Standard results use `mode: "standard"` with null hypothetical and
fallback fields. HyDE success uses `mode: "hyde"` and returns the bounded hypothetical passage. An
expected HyDE timeout/transport or empty, invalid, or oversized output falls back to original-query
retrieval and reports `mode: "standard"`, `hypothetical_passage: null`, and
`fallback_reason: "hyde_unavailable"`. Provider-specific details are not exposed. Configuration
errors still fail closed with `503`, and unrelated programming failures are not converted into a
fallback.

HyDE and final synthesis use independent quota reservations. Before each provider dispatch, the
service reserves a conservative prompt/output bound. A pre-dispatch configuration failure refunds
that stage. Once HyDE is dispatched, timeout/transport failure settles the full reserved bound;
returned messages settle bounded provider usage or the deterministic fallback estimate before the
passage is validated. That charge remains if retrieval is empty or final synthesis later fails.
When real chunks exist, final synthesis makes a second reservation, so it can accurately return
`429` after HyDE usage. Final-answer transport failure before a response refunds the final
reservation and returns the existing generic `503`; a returned message is settled before answer
content validation, so invalid returned content can retain bounded usage and still return `503`.
Empty standard retrieval costs no quota; empty retrieval after HyDE returns the fixed no-context
answer while retaining only the HyDE stage's settled usage.

Each provider stage receives a request-local reservation handle that permits at most one terminal
finalize or refund call during that service execution. Provider messages are normalized in the
provider-response module, and each stage's dispatched prompt and accounting serialization come from
the same bound prompt specification. This guard prevents duplicate calls inside one request; it is
not durable exactly-once settlement across process crashes or ambiguous database outcomes.

The synchronous provider boundary uses `RAG_HYDE_TIMEOUT_MS=3000` for HyDE and
`RAG_PROVIDER_TIMEOUT_MS=10000` for final synthesis. `RAG_HYDE_MAX_OUTPUT_TOKENS=256` and the
independent `RAG_HYDE_MAX_OUTPUT_CHARS=2000` bound the hypothetical; final context/output use
`RAG_MAX_CONTEXT_CHARS=6000` and `RAG_MAX_OUTPUT_TOKENS=800`. SDK retries are disabled at both the
injected OpenRouter client and LangChain model boundary, and `RAG_PROVIDER_MAX_RETRIES` must remain
`0`; HyDE's standard-retrieval fallback is not a provider retry.

Retrieved chunks leave the application boundary when sent to OpenRouter and its selected free
model provider. The same chunks are returned only to the authenticated owner as bounded grading
metadata and must not be logged. Reviewer smoke tests therefore use only the repository's synthetic
handbook; private uploads require explicit approval before live provider use.

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

HyDE is an optional mode of the existing chat endpoint, not a separate endpoint or service.
Billing/payment remain out of scope. Subscription and daily usage are intentionally local
account-domain state rather than public billing endpoints.

## Known Production Limitations

- Chroma replacement is delete-then-add rather than atomic/versioned. An add failure after deletion
  requires restoring the service and re-queuing ingestion for the affected document.
- Quota reservations have no durable per-stage settlement ledger or reconciliation worker; a crash
  or ambiguous finalize/refund failure can retain the conservative reservation.
- Celery ingestion has no stale-job recovery, dispatch outbox, or duplicate/concurrent-delivery
  generation guard.
- Extraction is synchronous inside a worker and does not yet enforce PDF signature/MIME, page,
  extracted-character, or chunk-count ceilings beyond the upload byte limit; chunk embedding and
  vector writes are not batched.
- Embedding and provider work are synchronous and do not yet have workload-specific concurrency or
  backpressure controls.
- Document text and metadata are explicitly framed as untrusted in prompts, but stronger structural
  prompt-injection isolation remains future hardening.
