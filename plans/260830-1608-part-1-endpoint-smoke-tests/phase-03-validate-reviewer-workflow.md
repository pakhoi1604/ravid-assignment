---
phase: 3
title: "Validate Reviewer Workflow"
status: pending
priority: P2
dependencies: [2]
---

# Phase 3: Validate Reviewer Workflow

## Overview

Run the fixture-backed smoke script and the Chroma verifier against the Docker stack, while keeping
existing automated checks green.

## Requirements

- Functional: validate the script against a real Docker Compose stack.
- Functional: verify both success and at least one clear failure mode.
- Functional: prove invalid fixture uploads are rejected.
- Functional: prove stored Chroma chunk content matches extracted/split source text.
- Non-functional: keep existing pytest and lint checks passing.
- Non-functional: do not push or publish artifacts unless separately requested.

## Architecture

Validation should run in layers:

```text
static checks
  -> shell syntax check
  -> python syntax check
  -> Make target check
  -> existing pytest
  -> docker compose config
  -> live Docker smoke run
  -> direct Chroma verifier run
```

Live smoke validation is intentionally slower because it exercises Redis, Celery, PostgreSQL, media
storage, HuggingFace embedding runtime, and Chroma.

## Related Code Files

- Validate: `/home/khoipham/Projects/ravid-assignment/Ravid/scripts/smoke-part-1-endpoints.sh`
- Validate: `/home/khoipham/Projects/ravid-assignment/Ravid/scripts/verify-chroma-document.py`
- Validate: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/`
- Validate: `/home/khoipham/Projects/ravid-assignment/Ravid/Makefile`
- Validate: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md`

## Implementation Steps

1. Run shell syntax check:

   ```bash
   sh -n scripts/smoke-part-1-endpoints.sh
   ```

2. Run Python syntax check:

   ```bash
   uv run python -m py_compile scripts/verify-chroma-document.py
   ```

3. Run existing fast checks:

   ```bash
   uv run ruff check apps config tests
   uv run ruff format --check apps config tests
   uv run pytest
   docker compose config --quiet
   ```

4. Start or reuse Docker stack:

   ```bash
   docker compose up -d
   ```

5. Run baseline health smoke:

   ```bash
   make smoke
   ```

6. Run new Part 1 endpoint smoke:

   ```bash
   make smoke-part-1
   ```

7. Capture the uploaded `document_id` from script output, then run direct verifier:

   ```bash
   make verify-chroma-document DOCUMENT_ID=<document-public-id>
   ```

8. Verify failure clarity by temporarily using a bad password through environment override:

   ```bash
   SMOKE_PASSWORD=wrong scripts/smoke-part-1-endpoints.sh
   ```

   Expected: non-zero exit and clear auth failure message.

9. Verify invalid fixtures are rejected by the smoke script:
   - `.csv`, `.json`, `.html`, `.docx`, `.png`, `.zip` should return `400`
   - failure if any unsupported extension returns success
10. Capture final evidence in the implementation final response:
   - token obtain passed
   - token refresh passed
   - upload returned `202`
   - status reached `SUCCESS`
   - DB/media/Chroma checks passed
   - expected chunks matched stored Chroma documents
   - embedding count and dimensions verified

## Success Criteria

- [ ] `sh -n` passes.
- [ ] `uv run python -m py_compile scripts/verify-chroma-document.py` passes.
- [ ] `uv run ruff check apps config tests` passes.
- [ ] `uv run ruff format --check apps config tests` passes.
- [ ] `uv run pytest` passes.
- [ ] `docker compose config --quiet` passes.
- [ ] `make smoke` passes.
- [ ] `make smoke-part-1` passes from the host.
- [ ] `make verify-chroma-document DOCUMENT_ID=...` passes for the uploaded document.
- [ ] Invalid fixture uploads fail with expected validation errors.
- [ ] Bad-credential run fails clearly.

## Risk Assessment

- Risk: live smoke depends on network if model cache is cold and embedding model must be fetched.
  Mitigation: document first run may take longer; inspect Celery logs on timeout.
- Risk: local Docker database keeps previous test data. Mitigation: verify by new `document_id`, not
  by collection count alone.
- Risk: Chroma API shape changes. Mitigation: query through the Django runtime where the pinned
  application dependencies already match production code.
