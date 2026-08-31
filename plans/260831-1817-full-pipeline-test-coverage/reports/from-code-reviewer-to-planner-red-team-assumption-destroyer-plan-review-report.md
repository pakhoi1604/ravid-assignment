# Assumption Destroyer Plan Review

## Scope

- Reviewed `plan.md` and all seven phase files as a plan, not as an implementation.
- Verification role: Scope Auditor, with emphasis on process lifetime, dependency injection, shared state, and cleanup boundaries.
- Fact checks used the current application, test configuration, Compose topology, and existing integration tests. No lint, build, or test commands were run.
- Scout result: the affected state crosses at least four independent lifetimes: pytest runner, two Gunicorn workers, Celery worker child processes, and external PostgreSQL/Redis/Chroma services. Several plan oracles and fault controls are only defined as pytest-local objects.

## Overall Assessment

The plan is not executable as written. It promises a deterministic full-Compose provider, stage-level process fault injection, bounded worker recovery, isolated external state, and reconstructable observability without allocating the production/test-harness work required to create those capabilities. Those are not implementation details that can be deferred: they determine whether the proposed tests exercise the claimed system at all. Phase 1 cannot be treated as a sufficient foundation until the cross-process control plane and namespace contracts are designed explicitly.

## Critical Issues

### C1. The deterministic provider and call ledger do not cross the HTTP process boundary

Phase 5 defines a local deterministic adapter with a call ledger (`phase-05`, lines 30-34), and Phase 6 claims that this provider is attached to the web service while the E2E driver uses HTTP only (`phase-06`, lines 29-34). The actual endpoint constructs `RagService()` directly for every request (`apps/rag/views.py:45-49`); its defaults are bound to `build_openrouter_chat_model` and `invoke_prompt_model` (`apps/rag/services.py:40-57`). Production configuration only offers OpenRouter key/base URL/model settings (`config/settings/base.py:147-166`; `compose.yaml:25-43`). There is no provider selector, fake adapter server, shared ledger, or web-process injection hook.

Consequently, a pytest fixture or monkeypatch cannot affect either Gunicorn worker. With a fake key and the current defaults, the test can accidentally call the real OpenRouter endpoint; with no key, chat terminates at configuration validation (`apps/rag/llm.py:13-21`). The claimed deterministic L2 chat and exact provider call-count oracle are therefore impossible.

Required correction: make the plan choose and scope one real cross-process mechanism, preferably a Compose-local OpenRouter-compatible stub with a queryable/resettable ledger and a per-run authorization token. Add its files/service, readiness, reset/isolation protocol, failure scripting, and privacy assertions to Phases 1, 5, and 6. Do not describe an in-process adapter as an L2 solution.

### C2. Precise ingestion fault injection cannot control a separate Celery worker

Phase 1 says the failure injector remains in an existing test seam and adds no production flag (`phase-01`, lines 30-35). Phase 3 then requires injection around publish, claim, write, verification, activation, and cleanup (`phase-03`, lines 80-86), while L2 uses real process kills (`phase-03`, lines 29-33). There is no such cross-process seam. The pipeline constructs its vector store internally (`apps/documents/ingestion.py:56-62`), and the Celery task imports/calls the pipeline inside the worker process (`apps/documents/tasks.py:11`, `apps/documents/tasks.py:202-216`). Existing tests only succeed by monkeypatching symbols in the pytest process, for example `tests/documents/test_ingestion_pipeline.py:37` and `tests/documents/test_tasks.py:27-28`.

A barrier, monkeypatch, or in-memory call ledger in `tests/pipeline/helpers.py` cannot pause or fault a Celery child. Killing a container is too coarse to distinguish “after Chroma write but before readback” from “after activation.” The plan therefore cannot prove its central crash-boundary invariants.

Required correction: explicitly separate L1 in-process adapter fault tests from L2 crash tests, and stop claiming stage-precise L2 coverage unless a controlled worker harness is scoped. If stage-precise process faults are mandatory, define an external failpoint controller or dependency proxy with run-scoped, authenticated commands and enumerate the required application/harness changes.

## High Priority

### H1. Worker crash recovery is incompatible with the configured lease lifetime

E2E-08 expects a killed `PROCESSING` worker to recover inside a bounded full-Compose suite (`phase-06`, lines 71-72, 98-103). A claimed job receives `lease_expires_at = now + INGESTION_STALE_PROCESSING_SECONDS` (`apps/documents/tasks.py:32-35`), and recovery only rotates jobs whose lease has expired (`apps/documents/recovery.py:15-27`). The default is 2,100 seconds, derived from a 1,800-second Celery hard limit plus 300-second safety margin (`config/settings/base.py:125`, `config/settings/base.py:180-185`), and startup rejects a shorter inconsistent value (`config/settings/base.py:232-233`). Compose passes the 2,100-second stale value but does not pass `CELERY_TASK_TIME_LIMIT` or the safety setting to the worker (`compose.yaml:110-145`).

The test either waits over 35 minutes per crash or changes one variable and makes settings startup fail. Also, no `CELERY_TASK_ACKS_LATE`/worker-lost configuration exists, so the broker is not an alternative recovery oracle.

Required correction: define a coherent test-only timing profile that overrides task hard limit, safety interval, stale-processing interval, cleanup grace, and Beat recovery cadence together. State the bounded recovery deadline and prove the worker has entered `PROCESSING` before killing it.

### H2. L1 does not isolate the Chroma collection from the developer stack

The plan repeatedly promises a unique run namespace and exact cleanup (`plan.md`, lines 87-89; `phase-01`, lines 69-73; `phase-04`, lines 77-84). The production store, however, uses `VECTOR_COLLECTION_NAME`, defaulting to the global `ravid_documents` collection (`config/settings/base.py:175`; `apps/documents/vector_store.py:101-104`, `apps/documents/vector_store.py:458-459`). The Compose `test` service receives host, port, and embedding model but not `VECTOR_COLLECTION_NAME` (`compose.yaml:82-109`). Phase 4 specifically plans raw hostile inserts and interrupted/outage cases; row/ID namespacing is not equivalent to collection isolation, especially when a run is killed before cleanup.

Existing Chroma integration tests avoid this by creating a unique collection per test and deleting that collection (`tests/documents/test_vector_retrieval_chroma.py:35-58`, `tests/documents/test_vector_retrieval_chroma.py:72-110`). The proposed default-store pipeline tests do not inherit that behavior automatically.

Required correction: allocate a unique per-run collection name to every process that touches Chroma, including pytest, web, Celery, and cleanup/recovery commands. Record the collection as a run-owned resource and delete only that collection. Add an interrupted-run janitor policy that cannot match the default production collection.

### H3. “Unique Compose ports” is contradicted by hard-coded host bindings

Phase 6 says the runner creates unique project names, volumes, and ports (`phase-06`, lines 29-32) and warns against touching a developer stack (`phase-06`, lines 105-108). Compose hard-codes web and Flower to `127.0.0.1:8000` and `127.0.0.1:5555` (`compose.yaml:64-65`, `compose.yaml:245-246`). A unique Compose project scopes resource names, but it does not make those host ports unique. Two runs, or a run beside the documented developer stack, collide before the tests start.

Required correction: specify parameterized host-port variables or a dedicated override that lets Docker assign ephemeral ports, and require the runner to discover resolved ports through `docker compose port`. The Make targets and HTTP driver must consume discovered endpoints rather than fixed localhost URLs.

### H4. The plan has no remediation scope for current behavior that already violates its acceptance criteria

The overview says this work changes no application behavior or feature (`plan.md`, lines 19-22), and every phase's file table lists application modules as read-only. Yet Phase 2 requires DB/media rollback for storage, job, and dispatch exceptions (`phase-02`, lines 77-83). In the current upload view, `document` remains `None` until `Document.objects.create(...)` returns; cleanup only runs when `document is not None` (`apps/documents/views.py:47-63`). A failure after the `FileField` storage save but before the database create returns can leave an orphan that this exception handler cannot address. Database transaction rollback itself does not roll back storage.

Similarly, Phase 7 requires correlated structured lifecycle events, but current logging only configures JSON formatting (`config/settings/base.py:235-253`) and the codebase contains a few warnings/errors, not publish/claim/write/activate/recover success-transition events (`apps/documents/tasks.py:44-46`, `apps/documents/tasks.py:194-213`; no lifecycle logging in `apps/documents/dispatch.py` or `apps/documents/recovery.py`). Tests cannot manufacture application behavior from outside the process.

Required correction: add an explicit defect-remediation loop and a bounded list of application files that may change when a P0 oracle fails. If production changes remain out of scope, downgrade the relevant items from success criteria to expected failing evidence; do not claim both “no app changes” and “all P0 pass.”

### H5. Phase 7 observability assertions lack an event contract

OBS-01 claims success, failure, retry, and recovery can be reconstructed via safe identifiers, codes, and time (`phase-07`, lines 77-89). No event names, required fields, propagation rules, ordering guarantees, or correlation-key lifetime are defined. A `JsonFormatter` only changes serialization; it does not create events or correlate an HTTP request, outbox dispatch, Celery delivery ID, job generation, Chroma write, and recovery generation. Those identifiers also change at different boundaries: `enqueue_ingestion` generates a fresh delivery UUID (`apps/documents/tasks.py:23-29`), while recovery rotates the generation and creates a new dispatch (`apps/documents/recovery.py:40-59`).

Required correction: define a lifecycle event schema before tests: stable run/document/job identifiers, per-attempt generation and delivery identifiers, event names, allowed fields, and causal links. Allocate production instrumentation changes and specify whether assertions read captured stdout, a log sink, or an API. Without this, “reconstructable” is subjective and cannot be a P0 gate.

## Medium Priority

### M1. The vector-store cache budget is per process, not per stack

Phase 4 proposes a cache-across-configs/threads test (`phase-04`, lines 73-75), and Phase 7 expects the cache to remain `<= 8` under a soak (`phase-07`, line 76). `_build_cached_store` is an in-memory `lru_cache(maxsize=8)` (`apps/documents/vector_store.py:76-98`). It is therefore bounded to eight entries per Python process, not eight for the deployment. Compose runs two Gunicorn workers (`compose.yaml:8-10`) plus Celery autoscale children that recycle every five tasks (`compose.yaml:110-112`), each with an independent cache and embedding model lifetime.

A single-process unit assertion can pass while the stack holds many stores/models or repeatedly reloads them during Celery child churn. The stated oracle does not measure the resource behavior it claims.

Required correction: split the invariant into per-process cache correctness and stack-level RSS/model-load/connection churn. Define expected process count, sampling source, and aggregate budget. Do not report `cache <= 8` as a deployment-wide bound.

### M2. The L1/L2 lane boundary is blurred enough to permit false “real pipeline” evidence

The L1 commands execute pytest inside a one-off `test` container with production settings (`phase-03`, lines 89-94; `phase-05`, lines 90-95). That container depends only on PostgreSQL/Chroma and has neither Redis configuration nor a Celery worker (`compose.yaml:82-109`). Direct calls from that process can validly test PostgreSQL locking and real Chroma, but they cannot establish Redis delivery, Celery child lifetime, shared media, or worker recovery. Phase 3 nevertheless describes L1/L2 together for duplicate delivery and crash-boundary scenarios (`phase-03`, lines 62-78).

Required correction: attach every scenario ID to one executable topology and state which process owns each action/oracle. Reserve “real delivery” and “worker race/crash” claims for L2; label direct task/function invocation as L1 component integration. The evidence report must not aggregate both under a generic “pipeline passed” label.

## Recommended Actions

1. Block plan approval until the cross-process deterministic provider/ledger and ingestion fault-control designs are explicit.
2. Add a test-topology contract covering process lifetimes, shared stores, per-run identifiers, ports, collection/database/media ownership, and cleanup after interruption.
3. Add a coherent accelerated timing profile for recovery tests and list every validated setting it overrides.
4. Permit scoped production fixes/instrumentation, or reclassify currently unmet P0 assertions as defect-discovery outputs.
5. Define the observability event schema and stack-level resource metrics before Phase 7 implementation.
6. Rewrite the scenario-to-lane mapping so no one-off pytest container can be reported as Redis/Celery/HTTP E2E evidence.

## Unresolved Questions

- Is a Compose-local OpenRouter protocol stub acceptable, or is changing `RagService` construction to use a configured provider adapter an intended application change?
- Must crash recovery tests complete in normal PR time, and if so, what maximum deadline is acceptable?
- May L1 create and delete whole per-run Chroma collections, including after interrupted runs, or must it share `ravid_documents`?
- Is Phase 7 authorized to add production lifecycle instrumentation, or is it only supposed to document missing observability?

Status: REJECT - plan is not executable without scope and topology corrections.

Summary: Nine verified flaws were found: two critical, five high, and two medium. The dominant failure is confusing pytest-local controls with state visible to independent web/Celery processes.

Concerns: An implementation following the current plan can produce polished passing L0/L1 evidence while never exercising deterministic HTTP chat, precise worker crash boundaries, isolated Chroma state, or reconstructable production events.
