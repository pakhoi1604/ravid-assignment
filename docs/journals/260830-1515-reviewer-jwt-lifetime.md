---
title: "Reviewer JWT Lifetime"
created: "2026-08-30"
type: journal
---

# Reviewer JWT Lifetime

## Context

Access tokens were expiring during manual Postman testing.

## What Changed

- Added SimpleJWT lifetime settings with reviewer-friendly defaults.
- Exposed `JWT_ACCESS_TOKEN_LIFETIME_DAYS` and `JWT_REFRESH_TOKEN_LIFETIME_DAYS` through
  Docker/local env examples.
- Documented the default 7-day access-token lifetime in README.
- Lengthened the test settings secret key to avoid JWT signing warnings during auth tests.

## Decision

Do not remove JWT expiration entirely. Keep standard `exp` claims and make lifetimes long enough for
reviewer testing: 7 days for access tokens and 30 days for refresh tokens by default.

## Verification

- `uv run pytest` - 52 passed.
- `uv run ruff check apps config tests` - passed.
- `uv run ruff format --check apps config tests` - passed.
- `uv run python manage.py check --settings=config.settings.test` - passed.
- `docker compose config --quiet` - passed.
- `git diff --check` - passed.
