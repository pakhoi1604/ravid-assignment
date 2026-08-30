---
phase: 5
title: "Validation Documentation and Reviewer Workflow"
status: pending
priority: P2
dependencies: [1, 2, 3, 4]
effort: "M"
---

# Phase 5: Validation Documentation and Reviewer Workflow

## Overview

Broaden validation, update reviewer documentation, and keep the architecture docs aligned with the
new Part 2 public API and runtime configuration.

## Requirements

- Functional: README gives a deterministic reviewer path for authenticating, uploading, waiting for
  ingestion, and querying `/api/chat/query/`.
- Functional: environment docs list required OpenRouter and RAG settings without secrets.
- Functional: Docker image installs the dependencies needed by the RAG runtime.
- Non-functional: local unit tests pass without network, Chroma, Redis, or OpenRouter.
- Non-functional: Docker Compose validation still protects web/worker/db/redis/chroma/flower shape.

## Architecture

Documentation should describe the current system as a modular Django monolith:

- `apps.accounts`: JWT auth plus local subscription/credit gate.
- `apps.documents`: upload, ingestion, extraction, chunking, vector writes.
- `apps.rag`: owner-scoped retrieval, OpenRouter RAG prompt, and chat endpoint.

README should separate:

- local no-network test path;
- Docker reviewer path;
- optional OpenRouter-backed manual query path.

Do not commit runtime env files or any real provider key.

## Related Code Files

- Modify: `README.md` - add Part 2 setup, curl examples, and test commands.
- Modify: `docs/system-architecture.md` - update module boundaries and public API list.
- Modify: environment example template - add safe placeholders for RAG settings.
- Modify: `docker/django/Dockerfile` - confirm RAG/vector extra is installed in app image.
- Modify: `tests/smoke/test_compose_contracts.py` - only if dependency install or env contract changes.
- Potentially create: `docs/journals/<timestamp>-rag-chat-engine.md` after implementation.

## Implementation Steps

1. Run focused tests from phases 1-4.
2. Run broader local checks:

   ```bash
   uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
   uv run python manage.py check --settings=config.settings.test
   uv run pytest
   docker compose config --quiet
   ```

3. If dependency lock changes, run the repository's lock/sync command and commit lockfile changes
   with `pyproject.toml`.
4. Update the environment example template with safe placeholders:
   - `DEFAULT_DAILY_TOKEN_LIMIT=20000`
   - `RAG_RETRIEVAL_K=4`
   - `RAG_MAX_CONTEXT_CHARS=6000`
   - `RAG_MAX_OUTPUT_TOKENS=800`
   - `RAG_TEMPERATURE=0`
   - `OPENROUTER_APP_TITLE=RAVID Backend`
   - `OPENROUTER_HTTP_REFERER=`
5. Update README with manual flow:

   ```bash
   curl --fail --silent --show-error \
     -X POST http://localhost:8000/api/chat/query/ \
     -H "Authorization: Bearer <access-token>" \
     -H "Content-Type: application/json" \
     -d '{"query":"What is the cancellation policy mentioned in the employee handbook?"}'
   ```

6. State that local tests mock provider calls and that real answer generation needs provider
   credentials.
7. Update `docs/system-architecture.md` public surface with `POST /api/chat/query/` and explain
   local entitlement/token usage.
8. Run final smoke commands and capture exact failures if any external services are unavailable.

## Tests Before

- Add/adjust docs and smoke assertions after endpoint behavior exists.
- Expected initial failure before implementation: OpenAPI schema and README references do not match
  the new route.

## Tests After

- `uv run pytest`
- `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test`
- `uv run python manage.py check --settings=config.settings.test`
- `docker compose config --quiet`

## Success Criteria

- [ ] README clearly documents Part 2 query flow and OpenRouter requirement.
- [ ] Architecture doc lists chat, subscription/credit gate, and RAG responsibilities accurately.
- [ ] Environment template contains no secrets and includes all new settings.
- [ ] Full local test suite passes without outbound network calls.
- [ ] Compose config remains valid after dependency/env changes.
- [ ] No real secrets, uploaded files, provider responses, or local databases are committed.

## Risk Assessment

- Risk: reviewer expects real OpenRouter manual test. Mitigation: README separates mocked CI tests
  from real provider run and names the exact required credential variable.
- Risk: Docker dependency install misses the new LLM package. Mitigation: smoke Docker build if time
  permits; at minimum verify Dockerfile installs the extra containing `langchain-openai`.
- Risk: docs overpromise bonus behavior. Mitigation: explicitly mark HyDE and retrieval metadata as
  Part 3 out of scope.

## Security Considerations

- Never include real OpenRouter keys in docs, examples, logs, or commits.
- Curl examples should use `<access-token>` placeholder only.
- Do not document private uploaded filenames or local absolute paths in public-facing docs.
