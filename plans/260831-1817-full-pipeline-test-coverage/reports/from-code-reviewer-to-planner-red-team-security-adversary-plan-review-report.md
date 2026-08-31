# Red-Team Security Adversary Plan Review

## Scope

- Reviewed `plan.md` and all seven phase files under `plans/260831-1817-full-pipeline-test-coverage/`.
- Fact-checked plan claims against the current Django, Celery, Chroma, Compose, auth, RAG, and settings implementations.
- Review target is the plan only. No code, lint, build, or test execution was performed.

## Findings

### HIGH-01: The plan promises automatic Chroma-outage recovery that the state machine cannot perform

**Plan location:** `phase-06-runnable-compose-end-to-end-and-recovery.md:73`, reinforced by `plan.md:99`.

**Evidence:** Any ingestion exception, including Chroma write/readback failure, is caught and finalized as terminal `FAILURE` in `apps/documents/tasks.py:206-214` and `apps/documents/tasks.py:130-167`. The recovery query only selects stale `PENDING` and expired `PROCESSING` jobs in `apps/documents/recovery.py:15-27`; it never selects `FAILURE`. The periodic task only calls that recovery plus cleanup in `apps/documents/tasks.py:239-244`.

**Failure scenario:** E2E-10 stops Chroma during write. The worker catches the vector error and commits `FAILURE`. Restoring Chroma does nothing: Beat cannot redispatch a terminal failed job. The plan's expected "recoverable" outcome and its release criterion that dependency outages recover without losing intent are false under the current contract.

**Required fix:** Split E2E-10 into the actual contracts: outage before worker claim may recover via stale processing rotation; an observed vector exception terminates in `FAILURE` and requires an explicit retry/reindex operation. Either change the oracle to terminal safe failure and document manual recovery, or explicitly scope and design a product change that requeues retryable dependency failures.

### HIGH-02: The full-Compose deterministic provider does not exist in the proposed topology

**Plan location:** `phase-06-runnable-compose-end-to-end-and-recovery.md:27`, `:31-33`, `:68`, and `:84`; `plan.md:93`.

**Evidence:** The HTTP view constructs `RagService()` directly (`apps/rag/views.py:45-49`). Its defaults are the concrete OpenRouter builder/invoker (`apps/rag/services.py:40-56`), and the builder always creates OpenRouter clients (`apps/rag/llm.py:30-69`). Current Compose supplies only OpenRouter configuration to `web` (`compose.yaml:25-29`); it defines no deterministic provider service or test adapter. Phase 6's related-file list (`phase-06...md:35-44`) does not create a fake-provider service/configuration or identify an OpenRouter-compatible stub.

**Failure scenario:** The claimed one-command E2E reaches chat with no API key and returns `503` from configuration validation, or it uses a real key/network and becomes nondeterministic while sending test context externally. It cannot deterministically prove the known-fact answer and exact quota asserted by E2E-05.

**Required fix:** Specify an OpenRouter-compatible local stub service in the isolated Compose project, route only the E2E `web` container to it with a synthetic key/base URL, define deterministic response and usage payloads, and add a call-ledger oracle. List the concrete service/config/fixture files and verify that the normal Compose profile remains unchanged.

### HIGH-03: The security gate boots and accepts publicly known fallback credentials

**Plan location:** `phase-06-runnable-compose-end-to-end-and-recovery.md:64-65`, `:77`, and `phase-07-security-performance-observability-and-evidence.md:71`; no scenario rejects default secrets.

**Evidence:** Compose injects `SECRET_KEY=change-me-for-local-review-only` and the same PostgreSQL password when unset (`compose.yaml:13`, `:19`), and Flower defaults to `ravid:change-me` (`compose.yaml:231-246`). Production settings only require that secrets are non-empty (`config/settings/production.py:8-16`, `:20-27`), so those known placeholders pass. Phase 7 SEC-06 checks secret placement/redaction, not weak/default-secret rejection.

**Failure scenario:** A reviewer or deployment starts the documented stack without replacing placeholders. Anyone who can reach the web service can forge JWTs using the published Django signing key; anyone with local or forwarded access to Flower has its published Basic Auth credential. The proposed fresh-stack and network tests can all pass while the stack is trivially compromisable.

**Required fix:** Add a P0 production-configuration scenario that startup fails on every published placeholder and weak/empty Flower credential. The isolated runner must generate per-run random credentials without printing them, and the plan must distinguish intentionally insecure local fixtures from a production-settings gate.

### HIGH-04: Authentication abuse is omitted despite an unthrottled public token endpoint

**Plan location:** `phase-02-api-auth-upload-and-status-contracts.md:62-64` and `phase-07-security-performance-observability-and-evidence.md:65-72`.

**Evidence:** `/api/auth/token/` and refresh are public routes (`config/urls.py:9-10`). `REST_FRAMEWORK` config declares authentication, permissions, and schema only (`config/settings/base.py:100-106`); there are no throttle classes/rates. The only rapid-request scenario, SEC-05, covers upload/query/poll, not credential issuance. Access and refresh defaults are seven and thirty days (`config/settings/base.py:108-111`).

**Failure scenario:** An attacker performs unlimited password guessing against the token endpoint, then retains a stolen or replayed access token for seven days. Every listed API/JWT contract test still passes because the plan tests token shape and invalid signatures, not abuse resistance, revocation posture, or issuance limits.

**Required fix:** Add explicit token-obtain and token-refresh burst/brute-force scenarios with a mechanical rate-limit oracle and trusted-proxy/IP assumptions. If throttling and revocation remain out of scope, record them as High residual risks and stop presenting the security lane as complete.

### HIGH-05: The plan claims structured event correlation and metrics without planning the required application instrumentation

**Plan location:** `plan.md:35`; `phase-07-security-performance-observability-and-evidence.md:25-35`, `:43-46`, and OBS-01/OBS-02 at `:77-78`.

**Evidence:** `config/settings/base.py:235-253` configures JSON formatting only; it does not create correlation IDs, metrics, or domain events. Repository logging consists of a few warnings/errors (`apps/documents/tasks.py:44-46`, `:194-213`; `apps/rag/services.py:103-120`; `apps/accounts/entitlements.py:109-112`). Dispatch and recovery state transitions emit no events at all (`apps/documents/dispatch.py:38-131`; `apps/documents/recovery.py:15-60`). Phase 7 lists only new tests/evidence and a Makefile modification, with settings merely marked `Read`; the umbrella plan explicitly says no application feature changes (`plan.md:22`).

**Failure scenario:** OBS-01 attempts to reconstruct success, retry, recovery, and cleanup using safe IDs/codes/timestamps. There are no success/recovery transition events or request correlation key to assert. Tests must either be phantom assertions over DB state, fail permanently, or force unplanned production-code changes.

**Required fix:** Either remove metrics/event-correlation claims and test only current log redaction, or explicitly add an instrumentation phase with a stable event schema, correlation propagation, allowed fields, emission points, and sink/metrics contract. List the application files that must change and make redaction tests precede evidence capture.

### HIGH-06: The upload-abuse lane misses the parser-exhaustion path that current limits do not prevent

**Plan location:** `phase-02-api-auth-upload-and-status-contracts.md:65-70`; `phase-07-security-performance-observability-and-evidence.md:70`, SEC-05.

**Evidence:** Upload validation checks only extension and total byte size (`apps/documents/serializers.py:15-24`). PDF extraction constructs `PdfReader` before enforcing the page limit and then parses pages synchronously (`apps/documents/extraction.py:46-59`). The architecture already records that these limits are not process isolation or tenant backpressure (`docs/system-architecture.md:171-176`). The plan tests corrupt/over-page PDFs and generic rapid requests, but defines no adversarial compressed/object-heavy PDF, CPU/RSS ceiling, per-tenant ingestion quota, queue bound, or worker-kill recovery oracle.

**Failure scenario:** An authenticated user repeatedly uploads sub-25 MB PDFs engineered for expensive object/xref/decompression parsing. Each passes upload validation and occupies the bounded Celery pool until its hard task limit, starving other tenants and repeatedly cold-starting workers. SEC-05 can pass with ordinary oversized files while this denial-of-service path remains untested.

**Required fix:** Add a hostile-PDF corpus and P0 resource-abuse scenarios with wall-time, peak RSS, worker survival/replacement, queue-depth, and cross-tenant progress oracles. If per-tenant backpressure/process isolation is not being implemented, explicitly classify the demonstrated denial-of-service exposure as an accepted release risk rather than asserting that the worker remains healthy.

### HIGH-07: The privacy lane avoids the actual external-data boundary and cannot validate its stated policy

**Plan location:** `plan.md:34`, `:41`, `:100`; `phase-05-rag-hyde-provider-and-quota.md:78`, `:87`; `phase-07-security-performance-observability-and-evidence.md:71`.

**Evidence:** Production sends retrieved document context to OpenRouter (`apps/rag/services.py:205-224`, `:298-302`; `apps/rag/llm.py:74-80`). Architecture states that private uploads require explicit approval before live-provider use (`docs/system-architecture.md:139-142`), but the chat API accepts only `query` and `use_hyde` (`apps/rag/serializers.py:23-25`) and performs no consent/classification check before provider dispatch (`apps/rag/services.py:241-244`). The plan's live lane deliberately uses synthetic content only, so it never verifies the claimed approval boundary.

**Failure scenario:** An authenticated user queries a private uploaded document without any approval flag or policy decision. Its chunks leave the application boundary. All proposed privacy tests pass because they prove only that the test suite itself used synthetic data, not that production enforces the documented policy.

**Required fix:** Separate fixture hygiene from the production privacy contract. Add a P0 test proving unapproved/private documents cannot reach the provider, which requires designing an enforceable consent/classification boundary, or explicitly record that approval is operational-only and that the application cannot prevent private-data egress.

### MEDIUM-01: The P0 prompt-injection oracle is non-mechanical and overclaims a known limitation

**Plan location:** `phase-07-security-performance-observability-and-evidence.md:67`, `:84`, `:107`.

**Evidence:** SEC-02's expected result is "rejected or treated as data; no escalation," which permits opposite behaviors and defines no observable pass condition. Current prompt construction interpolates attacker-controlled source filename and content directly into one context string (`apps/rag/prompts.py:62-80`, `:98-103`); the raw filename originates from the upload (`apps/documents/views.py:49-56`) and is stored in vector metadata (`apps/documents/ingestion.py:39-49`). The architecture explicitly says stronger structural prompt-injection isolation is future work (`docs/system-architecture.md:177-178`).

**Failure scenario:** A filename or chunk contains delimiter text and instructions to disclose another excerpt or ignore policy. A deterministic fake returns the expected answer regardless of prompt contents, so the test passes without exercising instruction following. A live model may follow the injection, but the plan excludes external-provider adversarial testing.

**Required fix:** Replace the vague oracle with deterministic structural assertions: attacker data remains only in the context value, cannot create additional messages/roles, delimiters are escaped or encoded, and the provider call ledger receives an exact bounded prompt. Keep model obedience as a documented residual risk; do not claim "no escalation" from a fake-provider test.

## Recommended Decision

Do not approve this plan for implementation as a production-readiness security test strategy. Revise the phase contracts before creating tests; otherwise the suite will either fail against correct current behavior or pass while preserving known exploitable boundaries.

## Status

BLOCKED

## Summary

Seven High and one Medium plan defects were verified. The largest blockers are false recovery semantics, a missing deterministic E2E provider, acceptance of published default secrets, omitted auth abuse, and security/observability claims that cannot be proven by the scoped changes.

## Concerns

The plan repeatedly treats synthetic fixture hygiene, generic fault tests, and JSON log formatting as evidence of production privacy, resilience, and observability. Those are different contracts. Until the oracles match actual runtime guarantees and the missing security boundaries are either implemented or explicitly accepted, the final evidence artifact would overstate readiness.
