---
title: "Private PDF Full-Flow QA"
date: "2026-08-30"
agent: "root"
scope: "upload-status-ingestion-retrieval-openrouter"
status: "partial"
---

# Private PDF Full-Flow QA

## Summary

The real Docker flow completed upload, Celery extraction, chunking, local embedding, Chroma
indexing, owner-scoped retrieval, and two live OpenRouter calls. Infrastructure and accounting
worked. The run is partial rather than fully passed because the public status API hides the stored
`PENDING` state, and the second requested question missed a relevant indexed Lab 09 chunk in top-4
retrieval.

The source PDF and provider answer bodies are intentionally not copied into this report.

## Test Results

| Stage | Result | Evidence |
| --- | --- | --- |
| Authentication | PASS | Reviewer JWT endpoint returned 200; token was not printed or persisted. |
| Upload | PASS | PDF upload returned 202; stored size was 590,504 bytes. |
| Pending state | PARTIAL | DB stored `PENDING` while Celery was stopped; API returned `PROCESSING`. |
| Processing state | PASS | After worker start, DB and API both reported `PROCESSING`. |
| Completion | PASS | DB and API reached `SUCCESS`; processing took about 24 seconds. |
| Chunking/indexing | PASS | The document produced 243 owner-tagged Chroma chunks. |
| OpenRouter configuration | PASS after runtime override | Existing container used rejected `openrouter/auto`; recreation with `openrouter/free` passed the free-only gate. |
| Live question 1 | PASS | Chat returned 200; daily usage increased from 0 to 2,628 tokens. |
| Live question 2 | PARTIAL | Chat returned 200 and remained grounded, but said Lab 9 was unavailable. |
| Provider transport | PASS | Two redacted `POST /chat/completions` log entries returned HTTP 200. |
| Accounting | PASS | Daily usage increased to 5,068 tokens after the second response. |

## Status Timeline

1. Celery stopped before upload: database `PENDING`; status API `PROCESSING`.
2. Celery restarted: database `PROCESSING`; status API `PROCESSING`.
3. Ingestion completed: database `SUCCESS`; status API `SUCCESS` with the documented success
   message.
4. Final database state remained `SUCCESS` after both chat requests.

## Findings

### Public API does not expose `PENDING`

`format_status_response` maps stored `PENDING` to public `PROCESSING`. Persistence and task
transition are correct, but a client cannot distinguish queued work from active processing. This
does not meet the requested observability of all stages.

### Lab 09 exists but top-4 semantic retrieval missed it

The indexed document contains one literal Lab 09 chunk describing the HTTP/2 CONNECT lab. For the
question about Lab 9 structure, the native owner-scoped top-4 retriever selected four other chunks
and omitted that chunk. The LLM therefore correctly refused to invent an answer from its supplied
context, but the end-to-end answer did not satisfy the requested question.

Likely improvement areas are query normalization (`Lab 9` versus `Lab 09`), hybrid lexical/vector
retrieval, or a larger/reranked candidate set. No retrieval behavior was changed during this
diagnostic run.

## Environment Note

The Compose source currently overrides the repository default with `openrouter/auto`. The free-only
guard correctly rejected it without debiting quota. The live run recreated only the web container
with a temporary `openrouter/free` environment override; the secret value was never read or logged.

## Recommendations

1. Decide whether the status contract should expose `PENDING` instead of mapping it to
   `PROCESSING`.
2. Add a regression fixture/query for `Lab 9`/`Lab 09`, then improve retrieval without weakening
   owner isolation.
3. Update the local environment override to `openrouter/free` before the next container recreation;
   otherwise it will revert to the rejected model.

## Unresolved Questions

- Should queued and actively processing jobs be separate public states?
- Is exact-number lookup expected to use lexical/hybrid retrieval, or should semantic top-k alone
  be tuned for this assignment?
