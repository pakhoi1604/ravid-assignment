# Red-Team Scope & Complexity Plan Review

## Scope

- Reviewed `plan.md` and all seven phase files as a plan/contract audit.
- Verified claims against the current API, RAG, ingestion, recovery, logging, Compose, CI, and existing test contracts.
- Planned surface: 98 scenarios across five runtime lanes, 15 create entries, and 19 modify entries. The repository currently has 30 test modules, so this is a test-program expansion, not a bounded coverage increment.
- No lint, build, or test commands were run, per review instructions.

## Overall Assessment

**BLOCK.** The plan cannot be executed as written without either changing production behavior or weakening several success criteria. Two P0 end-to-end oracles contradict current runtime contracts, and three cross-cutting workstreams lack the production/configuration ownership needed to make their tests pass.

## Critical Issues

### 1. The deterministic full-Compose chat gate has no executable provider contract

Phase 6 requires a deterministic provider by default and says it is “attached only to web” (`phase-06-runnable-compose-end-to-end-and-recovery.md:24-33`), while E2E-05 requires a known-fact answer and exact quota (`:68`). Phase 5 describes a local deterministic adapter (`phase-05-rag-hyde-provider-and-quota.md:30-34`) but owns only test files and reads `apps/rag/services.py` (`:36-45`).

The actual HTTP consumer cannot receive that in-process adapter: `ChatQueryView` constructs `RagService()` directly (`apps/rag/views.py:45-49`), `RagService` binds `build_openrouter_chat_model` as its constructor default (`apps/rag/services.py:40-57`), and the builder always constructs the OpenRouter clients (`apps/rag/llm.py:30-69`). Compose contains no fake provider service and forwards `OPENROUTER_BASE_URL` only as an external URL (`compose.yaml:25-29`). A pytest monkeypatch cannot cross into the Gunicorn process.

**Impact:** E2E-05 is either live-provider dependent, contrary to the merge-gate contract, or requires unplanned production/configuration work.

**Required correction:** Choose and own one viable boundary: add a Compose OpenRouter-protocol stub plus configuration and contract tests, or add an explicit production provider factory seam. List every affected file, including `apps/rag/views.py`/`services.py`/`llm.py`, Compose, and the existing Compose contract tests. Reconcile this with the plan-level promise of no application feature changes (`plan.md:19-22`).

### 2. Chroma write-outage recovery expects behavior the application does not provide

E2E-10 combines Chroma write and retrieval outages and expects the flow to be “recoverable” (`phase-06-runnable-compose-end-to-end-and-recovery.md:73`); the phase success criterion generalizes this to outages not losing durable intent (`:100-102`). On a write failure, however, `ingest_document` catches the exception and calls `_finalize_failure` (`apps/documents/tasks.py:206-214`), which terminally sets the job to `FAILURE` and clears its lease (`apps/documents/tasks.py:130-167`). Recovery selects only stale `PENDING` or expired `PROCESSING` jobs (`apps/documents/recovery.py:15-27`); it never retries `FAILURE`.

**Impact:** Restoring Chroma cannot make that upload succeed. A test that waits for recovery will time out; a test that accepts `FAILURE` does not prove the stated recovery contract.

**Required correction:** Split write outage from retrieval outage. Define the write oracle as terminal failure with no activation, then explicitly identify the supported recovery action (new upload/reindex/manual command) and test that action. If automatic retry is required, move it into a separate product-change plan.

## High Priority

### 3. The observability phase is test-only on paper but requires missing production instrumentation

OBS-01 requires reconstructing success, failure, retry, and recovery via safe IDs, codes, and timestamps; OBS-02 requires actionable dependency/stage codes (`phase-07-security-performance-observability-and-evidence.md:77-78`). Yet Phase 7 creates tests and modifies only `Makefile`; it marks logging configuration read-only (`:37-46`). Current logging config merely selects a JSON formatter (`config/settings/base.py:235-253`). Repository search found no logging at all in `apps/documents/dispatch.py`, `apps/documents/recovery.py`, `apps/documents/ingestion.py`, or the upload/status views. The task logger covers unknown/invalid tasks and unexpected exceptions, not successful transitions, publish retry, activation, or recovery (`apps/documents/tasks.py:44-46`, `:194-213`).

**Impact:** The P0 observability test cannot pass by adding assertions. Passing it requires application instrumentation across multiple state owners, contradicting the stated test-only scope.

**Required correction:** Either narrow OBS-01/02 to events that exist, or explicitly add production logging ownership for dispatch, task transitions, recovery, and request correlation, with an event schema and redaction contract.

### 4. The “isolated Compose project/ports” design omits existing consumers that will break

Phase 6 promises unique project, volumes, and ports (`phase-06-runnable-compose-end-to-end-and-recovery.md:29-33`) but only lists `compose.yaml`, `Makefile`, and README as modified non-test consumers (`:35-44`). The current Compose contract fixes web and Flower to `127.0.0.1:8000` and `127.0.0.1:5555` (`compose.yaml:64-65`, `:245-246`), and `tests/smoke/test_compose_contracts.py` asserts those exact strings (`tests/smoke/test_compose_contracts.py:36-43`). The existing smoke target also hardcodes both ports (`Makefile:41-49`). A unique Compose project name namespaces volumes, not fixed host ports.

**Impact:** The runner collides with a developer stack unless ports are parameterized; parameterizing them silently breaks an existing contract test not owned by the phase.

**Required correction:** Add `tests/smoke/test_compose_contracts.py` to ownership, define the exact port-variable contract, and make every host consumer use the resolved base URLs. Test concurrent/default-stack coexistence, not merely project-name uniqueness.

### 5. P0 production invariants remain optional because no CI lane owns L1/L2

The plan says L1 runs on each PR only “if Docker is available” and L2 only before release/submission (`plan.md:45-51`), while Phase 7 says completion requires every P0 to pass (`phase-07-security-performance-observability-and-evidence.md:57-60`, `:104-109`). Current CI runs SQLite pytest and `docker compose config --quiet`; it does not start PostgreSQL, Chroma, Redis, Celery, or Beat (`.github/workflows/ci.yml:8-35`). No phase lists `.github/workflows/ci.yml` as modified.

**Impact:** The concurrency, native-filter, and process-recovery P0s can remain skipped indefinitely while the ordinary merge gate is green. “Docker unavailable” has no owner, expiry, or enforcement mechanism.

**Required correction:** Assign CI ownership and define mandatory jobs for L1 and the P0 subset of L2, including timeout and artifact policy. Otherwise downgrade these from completion criteria and state who runs them, where, and what evidence blocks release.

## Medium Priority

### 6. The dependency and ownership model is internally contradictory for a 98-scenario program

The master plan and Phase 1 say Phases 2-5 can run in parallel immediately after Phase 1 (`plan.md:72-73`; `phase-01-coverage-model-fixtures-and-oracles.md:56-59`). Actual frontmatter makes Phase 4 depend on Phase 3 (`phase-04-vector-retrieval-isolation-and-data-integrity.md:1-7`) and Phase 5 depend on Phase 4 (`phase-05-rag-hyde-provider-and-quota.md:1-7`). Separately, the plan calls the endpoint-smoke plan “non-blocking” even though both plans create fixtures/scripts and modify `Makefile` and README (`plan.md:67-69`; `plans/260830-1608-part-1-endpoint-smoke-tests/phase-02-implement-script-and-make-target.md:61-75`). No phase has an owner, delivery budget, or merge responsibility for those shared artifacts.

**Impact:** Parallel execution will begin work before prerequisites exist and will produce competing runner/fixture/Makefile contracts. With 98 scenarios across L0-L4, this is not recoverable through informal “coordinate/reuse” language.

**Required correction:** Replace prose with one authoritative DAG and explicit artifact owners. Make the smoke-plan integration a blocking prerequisite or absorb it. Split delivery into independently shippable gates: deterministic L0, mandatory PostgreSQL/Chroma L1, minimal deterministic L2, then optional live/performance/evidence work.

## Recommended Actions

1. Resolve the deterministic provider and Chroma recovery contracts before implementation.
2. Add the missing production/config/CI consumers to file ownership or remove unsupported acceptance criteria.
3. Publish one dependency DAG and one canonical fixture/runner owner shared with the endpoint-smoke plan.
4. Reduce the first landing target to a small mandatory P0 subset; track L3/L4 and broad abuse/observability work separately.

## Status

**BLOCKED — major plan revision required.**

## Summary

The plan is broad but not executable under its own “tests only, no contract change” constraint. Its deterministic E2E provider is absent, its write-outage recovery oracle contradicts application state transitions, and critical instrumentation/CI/Compose consumers have no ownership.

## Concerns

Do not begin parallel phase execution from the current dependency map. Doing so will create false-green P0 gates, port and Makefile conflicts, and tests whose only route to passing is an undeclared production change.
