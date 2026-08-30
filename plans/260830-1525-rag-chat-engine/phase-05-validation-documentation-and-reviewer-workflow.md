---
phase: 5
title: "Validation Documentation and Reviewer Workflow"
status: completed
priority: P2
dependencies: [1, 2, 3, 4]
effort: "M"
---

# Phase 5: Validation Documentation and Reviewer Workflow

## Context Links

- Reviewer guide: `README.md`
- Architecture: `docs/system-architecture.md`
- Compose contracts: `tests/smoke/test_compose_contracts.py`
- Related optional tooling plan: `../260830-1608-part-1-endpoint-smoke-tests/plan.md`

## Overview

Run the full offline and container gates, document a reproducible synthetic reviewer workflow, and
separate deterministic CI validation from a credentialed free-tier OpenRouter smoke.

## Requirements

- README covers auth, synthetic upload, ingestion polling, chat query, and expected grounded answer.
- Runtime configuration is forwarded correctly without exposing provider secrets to unnecessary
  services.
- Unit/API tests never call OpenRouter, Chroma, Redis, or Celery.
- Live testing uses only a rotated key and non-sensitive synthetic content.

## Architecture

Document the implemented modular monolith:

- `apps.accounts`: built-in Django identity plus local `Subscription`/daily usage gate.
- `apps.documents`: upload, Celery ingestion, extraction, LangChain splitting, vector writes, and
  owner-scoped vector retrieval.
- `apps.rag`: bounded prompt/model chain, OpenRouter free-tier client, accounting orchestration, and
  chat API.

The local daily token limit is application quota, not OpenRouter billing credit. A free-tier account
and API key are still required for a live request; no paid subscription is required.

## Related Code Files

- Modify: `README.md` - Part 2 setup, synthetic reviewer flow, privacy/free-tier notes.
- Modify: `docs/system-architecture.md` - current account, retrieval, RAG, and API boundaries.
- Modify: repository environment example template - set safe free-tier/RAG defaults.
- Modify: `compose.yaml` - forward settings and add a profile-gated `test` service.
- Create: `tests/fixtures/rag/reviewer-handbook.md` - deterministic non-confidential source.
- Create: `tests/accounts/test_entitlements_postgres.py` and
  `tests/documents/test_vector_retrieval_chroma.py` - Docker-backed invariant gates.
- Modify: `tests/smoke/test_configuration.py` and `tests/smoke/test_compose_contracts.py` - defaults,
  env forwarding, and dependency contracts.
- Modify: `tests/smoke/test_health.py` - chat OpenAPI assertions if not completed in Phase 4.
- Verify: `docker/django/Dockerfile` - lean runtime and Phase 1's profile-gated test stage remain
  separated.

## Implementation Steps

1. Add a tiny synthetic handbook with a unique fact and query. Do not use the assignment PDF,
   private uploads, or filenames from a developer machine as reviewer data.
2. Update safe defaults and docs:
   - `OPENROUTER_MODEL=openrouter/free`;
   - `DEFAULT_DAILY_TOKEN_LIMIT=20000`;
   - `RAG_RETRIEVAL_K=4`, `RAG_MAX_CONTEXT_CHARS=6000`;
   - `RAG_MAX_OUTPUT_TOKENS=800`, `RAG_CHAT_OVERHEAD_TOKENS=256`, `RAG_TEMPERATURE=0`;
   - `RAG_PROVIDER_TIMEOUT_MS=10000`, `RAG_PROVIDER_MAX_RETRIES=0`;
   - blank `OPENROUTER_APP_URL` and non-secret `OPENROUTER_APP_TITLE`.
3. Forward shared non-secret settings where needed. Forward `OPENROUTER_API_KEY`, base URL, model,
   and app metadata to web only because Part 2 calls the model synchronously; do not expand or print
   resolved Compose configuration.
4. Extend configuration/Compose tests to prove free default, direct packages, web secret ownership,
   and container env contracts.
5. Update README reviewer flow: seed accounts, obtain JWT, upload synthetic document, poll ingestion
   to `SUCCESS`, query a known fact, and show the expected answer shape.
6. Explain that retrieved chunks are sent to an external model provider. Require synthetic or
   approved non-sensitive content for the free-tier smoke.
7. Update architecture docs and remove statements that chat/subscription/credits/LLM are deferred.
8. Run lock, lint, format, Django, migration, OpenAPI, focused, full-test, and Compose gates.
9. Rebuild the web image and verify imports for `ChatOpenRouter` and directly imported core APIs.
   Then run `make smoke` to protect the existing service baseline.
10. Verify Phase 1's Compose test runner still uses the dev-dependency image stage, production
    database settings, and healthy PostgreSQL/Chroma dependencies while runtime services stay lean.
11. Build the test image, start `db` and `chroma`, then rerun the PostgreSQL race and two-user
    direct retriever test through `docker compose --profile test run --rm test ...`. These gates are
    required, have pytest available, and do not use OpenRouter.
12. If a rotated OpenRouter key is available, run the synthetic upload/status/query flow with
    `openrouter/free`. Never echo JWTs or keys. If the free router is unavailable/rate-limited,
    record it as an external live-smoke limitation; offline acceptance must remain green.
13. If plan `260830-1608-part-1-endpoint-smoke-tests` is implemented first, reuse compatible helper
    conventions but keep this plan's synthetic RAG fixture and Part 2 assertions self-contained.

## Tests Before

- Add configuration/Compose/schema assertions before updating docs and environment contracts.

## Tests After

```bash
UV_CACHE_DIR=/tmp/ravid-rag-uv-cache uv lock --check
UV_CACHE_DIR=/tmp/ravid-rag-uv-cache uv sync --all-extras --dev --frozen
uv run ruff check apps config tests
uv run ruff format --check apps config tests
uv run python manage.py check --settings=config.settings.test
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run python manage.py spectacular --settings=config.settings.test --file /tmp/ravid-openapi.yaml --validate
uv run pytest tests/accounts tests/documents tests/rag tests/smoke
uv run pytest
docker compose config --quiet
docker compose build web
docker compose --profile test build test
docker compose --profile test up -d db chroma
docker compose --profile test run --rm test pytest --ds=config.settings.production tests/accounts/test_entitlements_postgres.py -q
docker compose --profile test run --rm test pytest --ds=config.settings.production tests/documents/test_vector_retrieval_chroma.py -q
make smoke
```

## Success Criteria

- [x] README provides an accurate synthetic Part 2 reviewer journey.
- [x] Architecture docs no longer describe implemented Part 2 boundaries as deferred.
- [x] Free-router default and all RAG settings are documented and forwarded correctly.
- [x] Provider key is available only to web and is never printed, logged, or committed.
- [x] Direct dependency, Docker import, OpenAPI, focused, full-test, and Compose gates pass.
- [x] Real PostgreSQL concurrency and two-user Chroma isolation gates pass.
- [x] Runtime image remains dev-tool-free; only the profile-gated test target installs pytest.
- [x] Credentialed smoke uses a rotated key plus synthetic content, or records only the external
      free-tier availability limitation.

## Risk Assessment

- Free-tier availability is externally unstable. Keep live smoke separate from offline correctness.
- Compose expansion can render secrets. Use `docker compose config --quiet` only in recorded output.
- Documentation can accidentally normalize private assignment material as fixtures. Keep the new
  fixture synthetic and public-safe.

## Security Considerations

- Rotate previously exposed OpenRouter credentials before a live call.
- Never commit keys, JWTs, uploaded files, provider responses, local databases, or resolved env.
- Explicitly disclose that selected chunks are sent to OpenRouter/free model providers.
