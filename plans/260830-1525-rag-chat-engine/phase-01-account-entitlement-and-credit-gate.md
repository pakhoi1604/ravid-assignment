---
phase: 1
title: "Account Entitlement and Credit Gate"
status: completed
priority: P1
dependencies: []
effort: "L"
---

# Phase 1: Account Entitlement and Credit Gate

## Context Links

- Assignment gate: `docs/2026-08-30 R.A.V.I.D.md`
- Existing seed command: `apps/accounts/management/commands/load_test_accounts.py`
- Existing seed tests: `tests/accounts/test_load_test_accounts.py`
- Existing fixture: `mockdata/test-accounts.json`

## Overview

Add explicit local subscription state before vector retrieval and concurrency-safe daily token
accounting before any OpenRouter request. Continue using Django's built-in User for identity/login.

## Requirements

- Functional: missing or inactive subscription fails closed before retrieval/LLM work.
- Functional: reserve, refund, and finalize a conservative daily token budget.
- Functional: `load_test_accounts` explicitly provisions reviewer subscriptions and limits without
  a payment flow or dated usage rows.
- Non-functional: PostgreSQL concurrency cannot overspend quota during simultaneous requests.
- Non-functional: subscription state is independent from Django `User.is_active`.

## Architecture

Create exactly two account-domain models:

- `Subscription`: one-to-one `settings.AUTH_USER_MODEL`; `ACTIVE`/`INACTIVE` status;
  positive `daily_token_limit`; timestamps; default status `INACTIVE`.
- `DailyTokenUsage`: user, UTC `usage_date`, non-negative `used_tokens`; unique
  `(user, usage_date)`.

This is an application entitlement, not a payment/provider subscription. Remaining credits are
derived as `max(0, subscription.daily_token_limit - usage.used_tokens)`.

Create `apps.accounts.entitlements`:

```python
@dataclass(frozen=True)
class TokenReservation:
    usage_id: int
    reserved_tokens: int

def ensure_active_subscription(user) -> Subscription: ...
def reserve_daily_tokens(user, estimated_tokens: int) -> TokenReservation: ...
def finalize_daily_tokens(reservation: TokenReservation, actual_tokens: int) -> None: ...
def refund_daily_tokens(reservation: TokenReservation) -> None: ...
```

Reservation/finalization are at-most-once operations within one synchronous request. A persistent
reservation ledger and crash recovery are intentionally deferred. The reserved amount is a
provider-independent conservative bound: UTF-8 bytes for the fully formatted prompt, plus explicit
chat framing overhead, plus the provider-enforced maximum output tokens. Do not use `len(text) / 4`
for admission control. If metadata still reports a larger value, record the full actual amount,
raise an accounting alert, and block subsequent requests rather than undercounting.

## Related Code Files

- Modify: `apps/accounts/models.py` - add `Subscription` and `DailyTokenUsage`.
- Modify: `apps/accounts/admin.py` - register both models for local operator inspection.
- Create: `apps/accounts/entitlements.py` - gate and accounting service.
- Create: `apps/accounts/migrations/0001_initial.py` - first account-domain migration.
- Modify: `apps/accounts/management/commands/load_test_accounts.py` - atomic subscription seeding.
- Modify: `mockdata/test-accounts.json` - explicit `subscription_active` and
  `daily_token_limit` fixture fields.
- Modify: `config/settings/base.py` - add `DEFAULT_DAILY_TOKEN_LIMIT`.
- Modify: environment example template and `compose.yaml` - document/forward the setting.
- Modify: `docker/django/Dockerfile` and `compose.yaml` - add a profile-gated test image stage and
  Compose runner with locked dev dependencies while keeping runtime images dev-tool-free.
- Create: `tests/accounts/test_entitlements.py` - model, quota, and transaction behavior.
- Create: `tests/accounts/test_entitlements_postgres.py` - real row-lock/race integration test.
- Modify: `tests/accounts/test_load_test_accounts.py` - subscription schema/security/idempotency.

## Implementation Steps

1. Add `DEFAULT_DAILY_TOKEN_LIMIT = env_int("DEFAULT_DAILY_TOKEN_LIMIT", 20000)` and forward it to
   the web service. Do not treat this app quota as OpenRouter credits.
2. Define both models with database checks for `daily_token_limit > 0` and `used_tokens >= 0`, plus
   the daily unique constraint. Make the migration use
   `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`.
3. Register both models in admin for an operator. Seeded reviewer users remain non-staff and are not
   promised admin access.
4. Implement `InactiveSubscriptionError` and `InsufficientCreditsError`. Reject non-positive
   estimates and negative actual usage.
5. Use `timezone.localdate()` for the current UTC-configured application day.
6. Inside `transaction.atomic()`, obtain today's usage row with `select_for_update()`. On first use,
   create inside an inner savepoint; if the unique key races, recover outside the failed savepoint
   and refetch with `select_for_update()`.
7. Lock the subscription/usage rows, enforce the limit, and update counters with `F()` expressions.
   Refund/finalize must never drive usage negative.
8. Extend `load_test_accounts` instead of creating a second seed flow. Validate explicit
   `subscription_active` and optional positive `daily_token_limit`, then update User and
   Subscription in one `transaction.atomic()` block. Never infer subscription from `is_active`.
9. Keep both checked-in reviewer accounts active with a reasonable daily limit so manual owner
   isolation is possible. Create inactive/over-limit users directly in tests.
10. Add tests first, then implement: active/missing/inactive states, quota exhaustion, first-row
    race behavior, refund/finalize, actual-over-bound alerting, UTC rollover, changed limit,
    adversarial Unicode/punctuation admission near the limit, fixture validation, rollback, and
    seed idempotency.
11. Add a Dockerfile `test` stage with the locked dev group and a profile-gated Compose `test`
    runner using production PostgreSQL settings. Keep web/celery runtime stages `--no-dev`.
12. Add a PostgreSQL-backed concurrency test through that runner; SQLite unit tests alone do not
    prove row-lock behavior.

## Tests Before

- Add failing `tests/accounts/test_entitlements.py` before model/service implementation.
- Extend existing seed tests before changing the command or fixture contract.

## Tests After

- `uv run pytest tests/accounts/test_entitlements.py tests/accounts/test_load_test_accounts.py`
- PostgreSQL integration: two simultaneous reservations cannot exceed one user's daily limit.
- `docker compose --profile test build test`
- `docker compose --profile test up -d db`
- `docker compose --profile test run --rm test pytest --ds=config.settings.production tests/accounts/test_entitlements_postgres.py -q`
- `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test`

## Success Criteria

- [x] Explicit `Subscription` and `DailyTokenUsage` migration exists with database constraints.
- [x] Seeded users each have one explicit active subscription; reruns update without duplicates.
- [x] Seeding is transactional and creates no dated usage rows.
- [x] Missing/inactive subscriptions stop before retrieval; exhausted quota stops before OpenRouter.
- [x] UTC rollover creates a new usage row; prior-day usage remains unchanged.
- [x] UTF-8-byte-bound admission, refund, finalization, and unexpected-over-bound cases never
      undercount or underflow.
- [x] PostgreSQL concurrency test proves quota cannot be overspent.

## Risk Assessment

- Process death after reservation can strand quota until the next UTC day. Accept for the
  assignment; a durable reservation ledger is outside scope.
- Provider token metadata varies. Reserve a bounded worst-case amount and use deterministic
  fallback accounting.
- SQLite cannot validate PostgreSQL locks. Keep fast unit tests, plus one real-Postgres race gate.

## Security Considerations

- Chat traffic cannot create or activate subscriptions.
- `User.is_active` controls authentication; `Subscription.status` controls RAG access.
- Never expose usage row IDs, quota internals, or operator controls in the chat response.
