---
phase: 2
title: "API Auth Upload and Status Contracts"
status: pending
priority: P1
dependencies: [1]
---

# Phase 2: API Auth Upload and Status Contracts

## Overview

Mở rộng contract tests cho JWT, multipart upload và status polling, gồm protocol edges, mọi file
type/limit/corruption và transaction rollback không để orphan.

## Context Links

- [Phase 1](./phase-01-coverage-model-fixtures-and-oracles.md)
- `docs/2026-08-30 R.A.V.I.D.md:60`, `docs/2026-08-30 R.A.V.I.D.md:82`
- `apps/documents/views.py:31`, `apps/documents/views.py:74`, `tests/documents/test_api.py:35`

## Requirements

- Functional: JWT positive/negative; exact response/status/schema; owner scope; format/size/parser
  failures; atomic DB + media rollback.
- Non-functional: không leak exception/path/content; polling bounded; không giả định MIME validation
  vì contract hiện tại chỉ kiểm extension và declared size.

## Architecture

DRF tests dùng storage tạm và transaction oracle. Accepted upload commit `Document + IngestionJob +
IngestionDispatch`. Corrupt content có thể nhận `202` rồi async `FAILURE`: test tách upload
acceptance khỏi extraction outcome.

## Related Code Files

| Action | Absolute path | Nội dung | Impact |
| --- | --- | --- | --- |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/accounts/test_auth.py` | JWT matrix | auth |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_api.py` | upload/status/rollback | API |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_upload_file_matrix.py` | formats/limits | inputs |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_health.py` | OpenAPI methods/schema | docs |
| Read | `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/views.py` | transaction contract | oracle |

## Function / Interface Checklist

- [ ] JWT routes (`config/urls.py:9`, `config/urls.py:10`): obtain/refresh token types.
- [ ] `UploadSerializer.validate_file` (`apps/documents/serializers.py:15`): extension/bytes.
- [ ] `DocumentUploadView.post` (`apps/documents/views.py:42`): atomic rows/file cleanup.
- [ ] `document_upload_path` (`apps/documents/models.py:9`): safe basename/owner UUID.
- [ ] `DocumentStatusView.get` (`apps/documents/views.py:92`): required UUID + owner.
- [ ] `format_status_response` (`apps/documents/serializers.py:46`): all states.

## Dependency Map

Phase 1 -> Phase 2 -> Phase 6 HTTP flow. Phase 2 độc lập Phase 3-5.

## Test Scenario Matrix

| ID | Pri | Layer | Precondition / input / fault | Expected oracle | Automation target |
| --- | --- | --- | --- | --- | --- |
| API-01 | P0 | L0 | valid credentials -> refresh | access works; refresh token cannot access API | auth test |
| API-02 | P1 | L0 | expired/malformed/wrong-signature token | `401`; zero side effects | auth test |
| API-03 | P1 | L0 | deleted/disabled user; Basic/empty header | fail closed `401`; no leak | auth test |
| API-04 | P0 | L0 | valid PDF/TXT/MD; uppercase/multi-dot/path filename | `202`; basename safe; 3 rows atomic | upload matrix |
| API-05 | P1 | L0 | unsupported/no/double extension; MIME mismatch | final-extension behavior explicit; rejects have no rows/file | upload matrix |
| API-06 | P0 | L0 | size max/max+1; zero/whitespace | exact accept; over `400`; empty async fails safely | upload matrix |
| API-07 | P1 | L0 | invalid UTF-8; corrupt/encrypted/image-only PDF | `202 -> FAILURE`; no active generation | API/task |
| API-08 | P1 | L0 | page/chars/chunks exact limit and +1 | exact succeeds; over deterministic failure | extraction integration |
| API-09 | P1 | L0 | missing/duplicate file; malformed multipart/JSON | stable `400/415`; zero side effect | protocol matrix |
| API-10 | P0 | L0 | storage/Job/Dispatch exception | DB rollback; file deleted; no orphan | rollback |
| API-11 | P0 | L0 | PENDING/PROCESSING/SUCCESS/FAILURE | exact status-specific schema; DB authoritative | status |
| API-12 | P0 | L0 | missing/malformed/foreign task ID | `400` missing; same `404` malformed/foreign | isolation |
| API-13 | P1 | L0 | unsupported methods/extra fields | documented `405`; field policy fixed | schema |
| API-14 | P1 | L0 | Unicode filename/query boundary | valid UTF-8 JSON; length bound enforced | API matrix |

## Implementation Steps

1. Viết auth/protocol rejects; assert zero side effects.
2. Parameterize file matrix; tách sync acceptance và async terminal oracle.
3. Inject storage/job/dispatch exceptions; assert DB + filesystem cleanup.
4. Poll/serialize mọi state và cross-owner indistinguishability.
5. Validate OpenAPI multipart binary, JWT và response schemas.

## Commands / Gates

```bash
uv run pytest tests/accounts/test_auth.py tests/documents/test_api.py tests/documents/test_upload_file_matrix.py -q
uv run pytest tests/smoke/test_health.py -q
```

## Success Criteria

- [ ] JWT/upload/status matrix pass; rejects không có side effect.
- [ ] Mọi file boundary có HTTP + terminal + DB/media/vector oracle.
- [ ] Rollback không để DB/file orphan.
- [ ] OpenAPI và runtime giữ assignment contract.

## Risk Assessment

File storage không rollback theo DB nên cleanup explicit là oracle bắt buộc. MIME mismatch hiện là
known limitation, không biến test thành behavior mới. Security: foreign/nonexistent task không phân
biệt; response không phản chiếu path, traceback hay parser error thô.
