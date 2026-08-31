---
phase: 2
title: "Implement Fixtures Scripts and Make Targets"
status: pending
priority: P2
dependencies: [1]
---

# Phase 2: Implement Fixtures Scripts and Make Targets

## Overview

Add synthetic Part 1 test fixtures, a host-level endpoint smoke script, a Python Chroma verifier,
and Make targets.

## Requirements

- Functional: create reusable valid and invalid upload fixtures.
- Functional: create a smoke script for Part 1 endpoint behavior.
- Functional: create a Chroma verifier that compares source chunks to Chroma documents.
- Functional: add Make targets for smoke and targeted Chroma verification.
- Functional: seed test accounts before login.
- Functional: fail non-zero on any failed check.
- Non-functional: avoid new Python package dependencies and avoid external services.
- Non-functional: keep output concise but diagnostic.

## Architecture

Recommended file layout:

```text
tests/fixtures/part-1-documents/
  valid/
  invalid/
scripts/smoke-part-1-endpoints.sh
scripts/verify-chroma-document.py
Makefile target: smoke-part-1
Makefile target: verify-chroma-document
README section: Part 1 endpoint smoke test
```

The shell script should use small functions for repeated behavior:

```text
require_command
json_value
wait_for_status
die
```

The Python verifier should initialize Django, load `Document`, run `extract_text` and `split_text`,
then query Chroma by metadata filter:

```text
where = {"document_id": "<public-id>"}
include = ["metadatas", "documents", "embeddings"]
```

Use `curl --fail --silent --show-error` where possible, but capture response body for API errors.

## Related Code Files

- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/valid/smoke-sample.md`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/valid/smoke-sample.txt`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/valid/smoke-sample.pdf`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/invalid/smoke-sample.csv`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/invalid/smoke-sample.json`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/invalid/smoke-sample.html`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/invalid/smoke-sample.docx`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/invalid/smoke-sample.png`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/part-1-documents/invalid/smoke-sample.zip`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/scripts/smoke-part-1-endpoints.sh`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/scripts/verify-chroma-document.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/Makefile`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md`

## Implementation Steps

1. Create fixture directories:

   ```text
   tests/fixtures/part-1-documents/valid/
   tests/fixtures/part-1-documents/invalid/
   ```

2. Add small synthetic valid fixtures:
   - Markdown with unique marker text, headings, and repeated content enough to produce multiple
     chunks.
   - TXT with unique marker text.
   - PDF with extractable text and a short known marker.
3. Add invalid fixtures with harmless content and unsupported extensions:
   - `.csv`, `.json`, `.html`, `.docx`, `.png`, `.zip`
4. Add `scripts/verify-chroma-document.py`:
   - arguments: `--document-id`, optional `--task-id`, optional `--show-chunks`
   - call `django.setup()`
   - load `Document` by `public_id`
   - extract source text with `extract_text(document.file.path, document.original_filename)`
   - compute expected chunks with `split_text`
   - query Chroma collection by `where={"document_id": str(document.public_id)}`
   - sort records by metadata `chunk_index`
   - assert count, ids, chunk text, metadata, and embedding presence
   - print a concise summary: document id, expected chunks, stored chunks, embedding dimension
5. Add `scripts/smoke-part-1-endpoints.sh` with:
   - `set -eu`
   - configurable `BASE_URL=${BASE_URL:-http://127.0.0.1:8000}`
   - configurable test credentials defaulting to seeded reviewer account
   - fixture path defaulting to `tests/fixtures/part-1-documents/valid/smoke-sample.md`
   - login request
   - refresh request
   - valid upload request
   - status polling
   - invalid fixture rejection loop
   - DB/media/Chroma verification
   - call Chroma verifier for uploaded document id/task id
6. Parse JSON with Python stdlib instead of `jq`, for example:

   ```text
   python -c 'import json,sys; print(json.load(sys.stdin)["access"])'
   ```

7. Use `docker compose exec -T` in scripts where stdin behavior matters.
8. Add Make targets:

   ```make
   smoke-part-1:
   	scripts/smoke-part-1-endpoints.sh

   verify-chroma-document:
   	docker compose exec -T web python scripts/verify-chroma-document.py --document-id "$(DOCUMENT_ID)"
   ```

9. Update `.PHONY`.
10. Update README with:
   - `docker compose up -d`
   - `make smoke`
   - `make smoke-part-1`
   - `make verify-chroma-document DOCUMENT_ID=<document-public-id>`
   - what the script validates
11. Keep `make smoke` unchanged unless a tiny shared helper is clearly needed.

## Success Criteria

- [ ] `tests/fixtures/part-1-documents/` exists with valid and invalid fixtures.
- [ ] `scripts/smoke-part-1-endpoints.sh` exists and is executable.
- [ ] `scripts/verify-chroma-document.py` exists and runs inside the web container.
- [ ] `make smoke-part-1` runs the script.
- [ ] `make verify-chroma-document DOCUMENT_ID=...` runs the verifier.
- [ ] Script logs each major step.
- [ ] Script exits non-zero with a useful message on auth/upload/status/internal-check failure.
- [ ] Script does not require `jq` or private assignment files.
- [ ] Verifier detects missing chunk, mismatched chunk text, wrong metadata, and missing embeddings.
- [ ] README documents the command and expected outcome.

## Risk Assessment

- Risk: shell quoting around JSON is fragile. Mitigation: centralize JSON extraction in one helper.
- Risk: polling may pass while internal vector write lags. Mitigation: poll status first, then query
  Chroma by `document_id`.
- Risk: script mutates local DB by uploading documents. Mitigation: use deterministic filename prefix
  and document that it creates test data in the Docker dev database.
- Risk: committed invalid fixtures look like real binary assets. Mitigation: keep them tiny and
  clearly synthetic; they exist to test extension validation, not content parsing.
