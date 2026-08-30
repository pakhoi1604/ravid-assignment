---
phase: 1
title: Define RAVID Agent Contract
status: completed
priority: P1
dependencies: []
effort: small
---

# Phase 1: Define RAVID Agent Contract

## Overview

Replace the entire SANA/Next.js content in `AGENTS.md` with a project contract grounded in the assessment PDF. Keep the contract concise enough to guide later implementation without prematurely designing unspecified product behavior.

## Requirements

- Functional: identify project objective, mandatory APIs, ingestion workflow, RAG workflow, Docker deliverables, and documentation requirements.
- Non-functional: enforce user data isolation, server-side secrets, durable asynchronous status, validation, idempotent retries, and reproducible verification.
- Scope control: payment gateway implementation and HyDE remain outside the mandatory baseline unless separately requested.
- Assumptions: authentication mechanism, token-credit semantics, file-size limits, and embedding model must be labeled as unresolved until decided.

## Architecture

`AGENTS.md` becomes the project-specific source of truth. `CLAUDE.md` continues importing it, preserving DRY guidance for Claude and Codex. The assignment PDF remains the authoritative external requirement source; future architecture docs may refine but must not silently contradict it.

Recommended contract sections:

1. Project purpose and deadline-sensitive baseline.
2. Selected backend stack and package-management convention.
3. Mandatory API contracts.
4. Service boundaries: API, Celery worker, PostgreSQL/pgvector, Redis, Flower, OpenRouter.
5. Security and privacy invariants.
6. Testing, Docker, and documentation gates.
7. Explicit ambiguities and out-of-scope work.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/AGENTS.md`
- Verify unchanged: `/home/khoipham/Projects/ravid-assignment/Ravid/CLAUDE.md`
- Reference: `/home/khoipham/Projects/ravid-assignment/Ravid/2026-08-30 R.A.V.I.D. Assessment & Evaluation for Back End Candidates.pdf`

## Implementation Steps

1. Remove the generated Next.js agent block and every SANA-specific section from `AGENTS.md`.
2. Add the RAVID objective: private document upload, asynchronous vector ingestion, and authenticated RAG querying.
3. Record exact endpoint contracts and required response states from the PDF.
4. Add architectural boundaries without application-level implementation detail.
5. Add invariants: derive `user_id` from trusted identity, filter every document/job/vector query by owner, never expose API keys, and avoid logging private document content.
6. Require durable ingestion state outside transient Celery result data and idempotent retry behavior.
7. Define baseline-first sequencing; mark HyDE as bonus.
8. Add expected verification commands only after selecting the Python package manager; avoid stale pnpm commands.
9. Confirm `CLAUDE.md` still imports `AGENTS.md` and does not duplicate project rules.

## Success Criteria

- [ ] `AGENTS.md` contains no SANA or Next.js landing-page instructions.
- [ ] Mandatory PDF endpoints and status values are represented accurately.
- [ ] User isolation, secret handling, async durability, and validation are explicit invariants.
- [ ] Undefined authentication, quota, and payment behavior is identified as assumptions.
- [ ] `CLAUDE.md` remains a thin import bridge and needs no duplicate rules.

## Risk Assessment

Main risk: over-specifying architecture before the application scaffold exists. Mitigation: separate assessment requirements, selected conventions, and unresolved assumptions. Do not claim the PDF requires a particular auth protocol, embedding provider, ORM, or package manager.

## Security Considerations

- Never accept `user_id` as an ownership authority directly from request payloads.
- Keep OpenRouter credentials and document data server-side.
- Require file allowlisting, size limits, safe filenames, and parser failure handling.
- Require cross-user isolation tests in the future application plan.

## Next Steps

Proceed to Phase 2 after the agent contract is internally consistent and traceable to the PDF.
