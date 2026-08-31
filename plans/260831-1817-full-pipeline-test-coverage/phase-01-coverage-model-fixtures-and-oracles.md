---
phase: 1
title: "Coverage Model Fixtures and Oracles"
status: pending
priority: P1
dependencies: []
---

# Phase 1: Coverage Model Fixtures and Oracles

## Overview

Tạo nền kiểm thử dùng chung: taxonomy, fixture synthetic, factory, fault injector, polling helper,
oracle và test markers cho L0-L4. Không dùng assignment PDF/private upload làm provider input.

## Context Links

- [Inventory](./research/codebase-pipeline-inventory.md)
- [Assignment](../../docs/2026-08-30%20R.A.V.I.D.md)
- [Architecture](../../docs/system-architecture.md)
- `config/settings/test.py:7`, `config/settings/test.py:16`, `pyproject.toml:55`

## Requirements

- Functional: fixture PDF/TXT/MD valid và invalid; factories cho owner/subscription/job/generation;
  oracle đọc HTTP, DB, media, Chroma, quota; fault hook deterministic theo stage.
- Non-functional: hermetic, seeded/repeatable, parallel-safe, bounded timeout, cleanup idempotent;
  secret/private text không xuất hiện trong log/report.

## Architecture

`pytest` fixtures tạo run namespace và synthetic fact duy nhất. L0 inject adapter fake có call ledger;
L1 dùng PostgreSQL/Chroma thật; L2 driver gọi HTTP và poll DB-backed status. Oracle không lấy Celery
result backend làm nguồn sự thật. Failure injector chỉ nằm trong test seam hiện có, không thêm flag
test vào production code.

## Related Code Files

| Action | Absolute path | Nội dung | Impact |
| --- | --- | --- | --- |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/fixtures/pipeline/` | safe fixtures + corrupt generators | mọi phase |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/conftest.py` | factories, markers, cleanup | toàn suite |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/pipeline/helpers.py` | polling/oracles/fault ledger | L1-L3 |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/pyproject.toml` | test marker config | test collection |
| Read | `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/test.py` | SQLite/eager baseline | lane split |

## Function / Interface Checklist

- [ ] `UploadSerializer.validate_file` (`apps/documents/serializers.py:15`): exact size/extension fixture.
- [ ] `extract_text` (`apps/documents/extraction.py:7`): real file dispatch.
- [ ] `split_text` (`apps/documents/chunking.py:4`): exact/over char-chunk bounds.
- [ ] `run_ingestion_pipeline` (`apps/documents/ingestion.py:9`): stage fault ledger.
- [ ] `retrieve_active_documents_for_user` (`apps/documents/retrieval.py:25`): owner/pair oracle.
- [ ] `RagService` (`apps/rag/services.py:40`): provider/retriever/accounting call ledger.

## Dependency Map

`Phase 1 -> {Phase 2, Phase 3, Phase 4, Phase 5} -> Phase 6 -> Phase 7`.
Phối hợp fixture/script với `260830-1608-part-1-endpoint-smoke-tests`, không blocking.

## Test Scenario Matrix

| ID | Pri | Layer | Precondition / input / fault | Expected oracle | Automation target |
| --- | --- | --- | --- | --- | --- |
| FX-01 | P0 | L0 | synthetic MD chứa fact + Unicode | byte-stable; expected chunks/fact known | `tests/fixtures/pipeline/` |
| FX-02 | P0 | L0 | TXT/MD/PDF cùng semantic content | extractor output normalized, non-empty | fixture contract test |
| FX-03 | P1 | L0 | zero byte, whitespace, invalid UTF-8 | classified fixture; no accidental decode | fixture contract test |
| FX-04 | P1 | L0 | corrupt/encrypted/image-only/over-page PDF | generator deterministic; no private data | fixture contract test |
| FX-05 | P0 | L1 | two owners, documents, generations | unique IDs; cleanup exact namespace | PostgreSQL/Chroma fixture |
| FX-06 | P0 | L0 | injected fail before/after each stage | call ledger proves exact boundary | fake adapter fixture |
| FX-07 | P1 | L2 | poll never reaches terminal | deadline error includes last safe state | pipeline helper test |
| FX-08 | P0 | L0-L2 | test rerun/xdist | no shared rows/files/collections | isolation self-test |
| FX-09 | P0 | all | secret-like canary/private phrase | absent from logs/JUnit/evidence | redaction assertion |
| FX-10 | P2 | L4 | monotonic timing + resource snapshot | comparable JSON schema | evidence helper test |

## Implementation Steps

1. Ghi test manifest: requirement -> scenario ID -> lane -> command -> evidence.
2. Tạo fixture bằng dữ liệu synthetic; PDF generator đặt page/text/crypto/corruption chính xác.
3. Xây factories và unique run namespace; cleanup chỉ xóa resource do test sở hữu.
4. Xây bounded poller, DB/media/vector/quota oracle và provider/fault call ledger.
5. Đăng ký markers `unit`, `postgres`, `chroma`, `compose`, `live_provider`, `performance`.
6. Thêm self-tests cho fixtures/helpers trước khi phase sau dùng.

## Commands / Gates

```bash
uv run pytest tests/pipeline/test_fixture_contracts.py -q
uv run pytest --collect-only -q
uv run ruff check tests pyproject.toml
```

## Success Criteria

- [ ] Fixture manifest bao phủ mọi format/limit/fault và không chứa confidential content.
- [ ] Helper không phụ thuộc timing ngẫu nhiên; timeout hữu hạn và output redacted.
- [ ] Resource isolation/cleanup chạy lại hai lần không đổi kết quả.
- [ ] Mọi scenario phase 2-7 trỏ tới fixture/oracle cụ thể.

## Risk Assessment

Fixture PDF quá lớn làm suite chậm: sinh theo test và cache artifact safe. Fake quá xa production:
giới hạn fake ở fault/call ledger, bắt buộc L1/L2 cho invariant. Security: không dump JWT, API key,
prompt hoặc chunks; chmod temp artifact và redact trước khi lưu evidence.

## Implementation Steps

<!-- Detailed steps -->

## Success Criteria

- [ ] ...
