---
phase: 4
title: "Vector Retrieval Isolation and Data Integrity"
status: pending
priority: P1
dependencies: [1, 3]
---

# Phase 4: Vector Retrieval Isolation and Data Integrity

## Overview

Sửa và mở rộng production Chroma gate để chứng minh exact write/readback, active-generation
visibility, owner isolation, native filters và fail-closed metadata trên dữ liệu thật.

## Context Links

- [Phase 3](./phase-03-durable-ingestion-and-failure-injection.md)
- `docs/system-architecture.md:46`, `docs/system-architecture.md:61`
- `apps/documents/vector_store.py:166`, `:273`, `:311`, `:382`
- Gap hiện tại: `tests/documents/test_vector_retrieval_chroma.py:51` thiếu `active_generations`.

## Requirements

- Functional: write generation, readback exact IDs/metadata/count, active pair filtering, owner and
  document isolation, stale/legacy/forged data rejection, exact deletion.
- Non-functional: real Chroma + PostgreSQL lane; no shared collection collisions; retrieval bounds
  respected; corrupted metadata fails closed instead of partial leak.

## Architecture

PostgreSQL resolves owner active map trước; Chroma native filter narrows candidates; adapter
revalidates every `user_id/document_id/generation`. Tests seed both trusted API writes and hostile
raw Chroma records. Mỗi run truyền `VECTOR_COLLECTION_NAME` riêng tới pytest/web/Celery/commands và
xóa nguyên collection thuộc run; không chạy hostile insert trên `ravid_documents`. DB active pointer
là visibility authority, không phải newest vector timestamp.

## Related Code Files

| Action | Absolute path | Nội dung | Impact |
| --- | --- | --- | --- |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_vector_retrieval_chroma.py` | current API + matrix | prod gate |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_vector_store.py` | validation/readback/delete | adapter |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_retrieval.py` | active map/pair checks | facade |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/pipeline/test_vector_integrity.py` | PostgreSQL+Chroma | integration |
| Read | `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/vector_store.py` | trusted boundary | oracle |

## Function / Interface Checklist

- [ ] `build_search_kwargs_for_user` (`apps/documents/vector_store.py:43`): integer owner + active pairs.
- [ ] `DocumentVectorStore.write_document_generation` (`apps/documents/vector_store.py:166`): IDs/metadata.
- [ ] retrieve path (`apps/documents/vector_store.py:273`): native filter + result validation.
- [ ] write verification (`apps/documents/vector_store.py:311`, `apps/documents/vector_store.py:382`): exact readback.
- [ ] `retrieve_active_documents_for_user` (`apps/documents/retrieval.py:25`): DB map first.
- [ ] `get_vector_store` (`apps/documents/vector_store.py:458`): cached configs do not mix owner filters.

## Dependency Map

Phase 1 fixtures + Phase 3 generation states -> Phase 4 -> Phase 5 real retrieval -> Phase 6 E2E.

## Test Scenario Matrix

| ID | Pri | Layer | Precondition / input / fault | Expected oracle | Automation target |
| --- | --- | --- | --- | --- | --- |
| VEC-01 | P0 | L1 | write N chunks one generation | exact IDs, text, index, owner/doc/gen, count | Chroma test |
| VEC-02 | P0 | L1 | two owners share same fact/query | each owner gets only own chunks | isolation |
| VEC-03 | P0 | L1 | owner has two documents/active pairs | both allowed; no other pair | integration |
| VEC-04 | P0 | L1 | same document old/new generation | only DB-active generation visible | generation |
| VEC-05 | P0 | L1 | stale, WRITING, failed, generation-less records | none returned | hostile seed |
| VEC-06 | P0 | L1 | forged string user ID/wrong doc/wrong gen metadata | entire untrusted result rejected safely | fail closed |
| VEC-07 | P0 | L1 | partial/missing/duplicate IDs on readback | write fails; generation not active | integrity fault |
| VEC-08 | P1 | L1 | empty active map / deleted DB document | no Chroma query or empty result | facade |
| VEC-09 | P1 | L1 | exact cleanup one stale generation amid live data | only target IDs removed | cleanup |
| VEC-10 | P1 | L1 | search type/k/threshold/fetch_k boundaries | validated kwargs, bounded ordered output | settings |
| VEC-11 | P1 | L1 | Chroma timeout/unavailable/malformed result | safe domain error; no cross-owner fallback | degradation |
| VEC-12 | P2 | L1 | concurrent write/retrieve around activation | old or new complete view, never mixed partial | race |
| VEC-13 | P1 | L1 | cache across configs/threads | store reuse bounded; no owner predicate cached | cache test |
| VEC-14 | P0 | L1/L2 | interrupted run leaves collection | janitor matches exact run manifest; default collection untouched | isolation |

## Implementation Steps

1. Repair stale production Chroma tests to pass mandatory active-generation map.
2. Seed two owners/two docs/two generations qua real write API; assert raw collection and retrieval.
3. Insert hostile raw records to exercise metadata/type/pair fail-closed validation.
4. Inject readback mismatch and Chroma outage; connect oracle to activation state.
5. Test exact cleanup and activation race with barriers.
6. Propagate unique collection name tới mọi process; cleanup/janitor xóa exact collection và từ chối
   pattern có thể match default production collection.

## Commands / Gates

```bash
uv run pytest tests/documents/test_vector_store.py tests/documents/test_retrieval.py -q
docker compose --profile test up -d db chroma
docker compose --profile test run --rm test pytest --ds=config.settings.production tests/documents/test_vector_retrieval_chroma.py tests/pipeline/test_vector_integrity.py -q
```

## Success Criteria

- [ ] Existing skipped Chroma gate chạy đúng current interface.
- [ ] Two-owner/two-generation hostile matrix không leak một chunk nào.
- [ ] Write/readback mismatch không activate; exact cleanup không xóa live data.
- [ ] Chroma unavailable trả safe failure và DB visibility không bị thay đổi.

## Risk Assessment

Similarity ranking có thể khác theo model/version: assert membership/isolation/order invariants thay
vì brittle score exact. Raw hostile inserts bypass adapter có chủ ý và phải namespace riêng.
Security: vector text/metadata là untrusted; filter cộng post-validation đều bắt buộc, không log chunks.
