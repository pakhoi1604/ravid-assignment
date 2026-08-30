---
title: "RAVID Backend Skeleton Implementation"
date: "2026-08-30T12:33:00+07:00"
plan: "../../plans/260830-1115-ravid-backend-skeleton/plan.md"
---

# RAVID Backend Skeleton Implementation

## Context

Implemented the approved backend foundation plan for the RAVID document RAG assignment. Scope was
limited to runnable infrastructure, configuration, liveness, OpenAPI documentation, and developer
workflow wiring.

## What Happened

- Created a Django/DRF project with split local/test/production settings and app boundaries for
  `accounts`, `documents`, `rag`, and `common`.
- Added `/api/health/`, `/api/schema/`, and `/api/docs/` as the only public skeleton endpoints.
- Locked Python 3.12 dependencies with `uv.lock`, including a deferred RAG extra for later
  LangChain/Chroma/OpenRouter work.
- Added Docker Compose services for web, Celery, PostgreSQL, Redis, Chroma, and Flower.
- Added tests, CI, Make targets, README reviewer/local paths, architecture documentation, and a PM
  completion report.

## Decisions

- Kept the Docker runtime image on core skeleton dependencies only. The all-extras lock is verified
  locally, but the image avoids multi-GB Torch/CUDA packages until runtime feature code imports RAG
  libraries.
- Derived the Chroma image from pinned `chromadb/chroma:1.0.15` only to add `curl` for an actual
  internal health check.
- Removed `.env` from Git tracking while leaving the local file on disk, then anchored runtime-data
  ignore patterns so source files under `docker/chroma/` remain trackable.
- Switched both application and Chroma containers to non-root runtime users.

## Verification

- `uv sync --all-extras --dev --frozen`
- `uv run ruff check apps config tests`
- `uv run python manage.py check --settings=config.settings.local`
- `uv run python manage.py check --settings=config.settings.test`
- `uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test`
- `uv run pytest`
- `docker compose config --quiet`
- `docker compose build`
- `docker compose up -d`
- `make smoke`

## Next

Feature plans can now add authentication/subscriptions, document upload and ingestion, RAG chat, and
HyDE without changing the skeleton startup contract.
