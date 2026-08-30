---
phase: 1
title: Minimal Auth Endpoints
status: completed
priority: P1
dependencies: []
---

# Phase 1: Minimal Auth Endpoints

## Overview

Expose the smallest useful authentication surface for protected document APIs: JWT obtain and refresh endpoints backed by Django's built-in user model.

Do not implement registration, password reset, profiles, subscriptions, credits, social login, or custom user fields.

## Requirements

- Functional: add token obtain and refresh endpoints under `/api/auth/`.
- Functional: keep document APIs protected by DRF's existing default `IsAuthenticated`.
- Functional: tests can create users directly; no registration API is required.
- Non-functional: use `djangorestframework-simplejwt`, already present in `pyproject.toml`.
- Non-functional: keep API schema generation accurate through DRF URL routing.

## Architecture

DRF already defaults to authenticated access in `config/settings/base.py`. This phase only wires SimpleJWT authentication classes into REST framework settings and exposes SimpleJWT views from URL configuration.

Auth flow:

1. Test or reviewer creates a user through Django admin, shell, fixture, or management command.
2. Client posts username/password to `/api/auth/token/`.
3. Client sends `Authorization: Bearer <access>` to document endpoints.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py` - add JWT authentication class.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/urls.py` - add `/api/auth/token/` and `/api/auth/token/refresh/`.
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/accounts/test_auth.py` - token obtain/refresh and protected endpoint behavior.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/README.md` - add minimal reviewer auth note only if needed for manual testing.

<!-- Updated: Validation Session 1 - Auth tests moved under the accounts test boundary. -->

## Implementation Steps

1. Add `rest_framework_simplejwt.authentication.JWTAuthentication` to `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`.
2. Import `TokenObtainPairView` and `TokenRefreshView` in `config/urls.py`.
3. Add paths:
   - `/api/auth/token/`
   - `/api/auth/token/refresh/`
4. Add tests for valid credentials, invalid credentials, token refresh, and unauthenticated access to a future protected placeholder if needed.
5. Confirm `/api/health/`, `/api/schema/`, and `/api/docs/` remain public.

## Todo List

- [x] Configure JWT authentication class.
- [x] Add token and refresh URLs.
- [x] Add focused auth tests.
- [x] Verify public schema/docs/health permissions still work.

## Success Criteria

- [x] Valid user credentials return access and refresh tokens.
- [x] Refresh token returns a new access token.
- [x] Invalid credentials return `401`.
- [x] Public endpoints remain accessible without a token.
- [x] No registration, subscription, credit, payment, or chat behavior exists.

## Risk Assessment

- Risk: accidentally changing public health/schema permissions. Mitigation: keep existing `AllowAny` overrides and test them.
- Risk: overbuilding auth. Mitigation: use SimpleJWT stock views only.
