---
title: "Test Account Seeding"
created: "2026-08-30"
type: journal
---

# Test Account Seeding

## Context

Added a reviewer-friendly way to create API test users without opening a public registration
endpoint.

## What Changed

- Added `mockdata/test-accounts.json` with local-only non-admin test accounts.
- Added `load_test_accounts` Django management command for idempotent account creation and updates.
- Added an explicit `ALLOW_TEST_ACCOUNT_SEED=true` guard so direct command use cannot seed accounts
  accidentally.
- Added Makefile targets for Docker and local account loading.
- Updated README upload flow to use the seeded `reviewer` account.

## Verification

- `uv run pytest` - 51 passed.
- `uv run ruff check apps config tests` - passed.
- `uv run ruff format --check apps config tests` - passed.
- `uv run python manage.py check --settings=config.settings.test` - passed.
- `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test` - passed.
- `uv run python manage.py help load_test_accounts --settings=config.settings.test` - passed.
- `docker compose config --quiet` - passed.
- `git diff --check` - passed.

## Notes

- The default mock data intentionally does not create a superuser with a committed password.
- Public auth API scope is unchanged; users still obtain JWTs through `/api/auth/token/`.
