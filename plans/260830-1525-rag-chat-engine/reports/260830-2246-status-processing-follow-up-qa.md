---
title: "Status Processing Follow-up QA"
date: "2026-08-30"
agent: "root"
scope: "document-status-contract"
status: "passed"
follow_up_to: "260830-2108-private-pdf-full-flow-qa.md"
---

# Status Processing Follow-up QA

## Summary

PASS. The public document status contract intentionally serializes queued internal `PENDING` jobs
as public `PROCESSING`. This matches the assignment-facing running-state response and is no longer
treated as a QA finding for the current scope.

The private-PDF Lab 9 retrieval miss from the prior full-flow report is explicitly out of scope for
this follow-up and was not changed.

## Evidence

- `apps/documents/serializers.py` maps `IngestionJob.Status.PENDING` to
  `IngestionJob.Status.PROCESSING` in `format_status_response`.
- `tests/documents/test_api.py` asserts that a stored pending job returns
  `{"status": "PROCESSING"}` from the public status API.
- `tests/documents/test_models.py` still asserts that a newly created ingestion job is stored as
  internal `PENDING`, preserving the durable lifecycle source of truth.

## Verification

```text
UV_CACHE_DIR=/tmp/ravid-rag-uv-cache uv run pytest tests/documents/test_api.py tests/documents/test_models.py -q
```

Result:

```text
12 passed in 0.52s
```

## Remaining Scope

- No status-contract blocker remains.
- No retrieval behavior was changed because the Lab 9 semantic top-k miss is out of scope.
