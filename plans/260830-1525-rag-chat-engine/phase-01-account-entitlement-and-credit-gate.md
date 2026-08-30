---
phase: 1
title: "Account Entitlement and Credit Gate"
status: pending
priority: P1
dependencies: []
effort: "M"
---

# Phase 1: Account Entitlement and Credit Gate

## Overview

Add the minimal account-side state needed to enforce Part 2's active subscription and daily token
credit requirements before any retrieval or LLM call happens.

## Requirements

- Functional: every chat request can determine whether `request.user` has an active entitlement.
- Functional: every chat request can reserve, refund, and reconcile daily token credits.
- Functional: existing local reviewer users get usable default entitlements without manual admin
  setup.
- Non-functional: credit checks must be race-aware enough for concurrent requests by the same user.
- Non-functional: no external billing or payment provider in this phase.

## Architecture

Create two account models:

- `AccountEntitlement`: one row per user, `status`, `daily_token_limit`, timestamps.
- `DailyTokenUsage`: one row per user per UTC date, `used_tokens`, unique `(user, usage_date)`.

Use a service layer in `apps.accounts.entitlements`:

```python
@dataclass(frozen=True)
class TokenReservation:
    usage_id: int
    reserved_tokens: int

def ensure_active_entitlement(user) -> AccountEntitlement:
    raise NotImplementedError

def reserve_daily_tokens(user, estimated_tokens: int) -> TokenReservation:
    raise NotImplementedError

def finalize_daily_tokens(reservation: TokenReservation, actual_tokens: int) -> None:
    raise NotImplementedError

def refund_daily_tokens(reservation: TokenReservation) -> None:
    raise NotImplementedError
```

`reserve_daily_tokens` runs inside `transaction.atomic()`, locks or creates today's
`DailyTokenUsage`, and rejects if `used_tokens + estimated_tokens > daily_token_limit`.
The RAG service calls this gate before retrieving context or invoking OpenRouter.

## Related Code Files

- Modify: `apps/accounts/models.py` - add entitlement and usage models.
- Create: `apps/accounts/entitlements.py` - subscription and credit service API.
- Create: `apps/accounts/migrations/0001_initial.py` or next migration - persist models.
- Modify: `apps/accounts/management/commands/load_test_accounts.py` - create active reviewer
  entitlements.
- Modify: `config/settings/base.py` - add `DEFAULT_DAILY_TOKEN_LIMIT` and date/credit defaults.
- Modify: environment example template - document local token limit default.
- Create: `tests/accounts/test_entitlements.py` - model and reservation behavior.
- Modify: `tests/accounts/test_load_test_accounts.py` - prove seeded users can chat by default.

## Implementation Steps

1. Add `DEFAULT_DAILY_TOKEN_LIMIT = env_int("DEFAULT_DAILY_TOKEN_LIMIT", 20000)` in base settings.
2. Define `AccountEntitlement.Status` as `ACTIVE`, `INACTIVE`; default status is `ACTIVE` for local
   assignment ergonomics.
3. Define `DailyTokenUsage` with indexes on `user, -usage_date` and a unique constraint on
   `user, usage_date`.
4. Generate and review migrations with Django's migration tooling.
5. Implement `EntitlementError`, `InsufficientCreditsError`, and the reservation/finalization
   functions in `apps/accounts/entitlements.py`.
6. In reservation logic, use `timezone.now().date()` and `select_for_update()` for existing usage
   rows. For SQLite tests, keep behavior deterministic even though row locks are limited.
7. Update the test-account management command to `get_or_create` active entitlements with the
   configured default limit.
8. Add tests:
   - active entitlement passes;
   - missing entitlement is created active with default limit;
   - inactive entitlement raises before usage changes;
   - insufficient remaining credits raises before usage changes;
   - refund subtracts only the reserved amount and never goes below zero;
   - finalize adjusts reserved amount to actual provider usage.

## Tests Before

- Add failing tests in `tests/accounts/test_entitlements.py` before implementing service behavior.
- Expected initial failure: imports from `apps.accounts.entitlements` do not exist.

## Tests After

- `uv run pytest tests/accounts/test_entitlements.py`
- `uv run pytest tests/accounts/test_load_test_accounts.py`

## Success Criteria

- [ ] Entitlement and daily usage migrations are generated.
- [ ] Active subscription gate has deterministic errors for inactive users.
- [ ] Daily token reservation rejects over-limit requests before RAG work starts.
- [ ] Reservation refund/finalization are covered by tests.
- [ ] Reviewer/test accounts are active by default.

## Risk Assessment

- Risk: local entitlement model could be mistaken for real billing. Mitigation: name docs clearly as
  Part 2 local entitlement gate; keep payment gateway out of scope.
- Risk: token counts from providers vary by model. Mitigation: reserve a conservative estimate, then
  reconcile if response metadata includes actual token usage.
- Risk: concurrent SQLite tests do not prove PostgreSQL locking. Mitigation: design service with
  `transaction.atomic()` and row-level locking; rely on PostgreSQL in Docker reviewer path.

## Security Considerations

- Do not expose daily usage IDs or entitlement internals in chat API responses.
- Do not let inactive or over-limit users trigger vector retrieval or outbound LLM requests.
- Keep default active entitlement a local assignment choice; production would require payment-backed
  activation.
