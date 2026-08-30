---
title: Bound Celery Worker Pool
description: >-
  Limit local Celery ingestion concurrency and recycle worker children to
  control memory usage.
status: completed
priority: P1
branch: main
tags:
  - backend
  - celery
  - docker
  - performance
blockedBy: []
blocks: []
created: '2026-08-30T16:31:00+07:00'
createdBy: 'ck:cook'
source: skill
---

# Bound Celery Worker Pool

## Overview

Change the Docker Compose Celery worker from CPU-count-based prefork concurrency to an autoscaled
pool with one idle worker and two workers under load. Recycle each child after five completed tasks
to limit retained embedding-library memory.

## Phase

| Phase | Name | Status |
| --- | --- | --- |
| 1 | [Configure and verify the worker pool](./phase-01-configure-and-verify-worker-pool.md) | Completed |

## Scope

- Modify the `celery` service command in `compose.yaml`.
- Validate the rendered Compose configuration and live Celery pool statistics.

Out of scope: application task behavior, ingestion APIs, Celery broker/result settings, queues,
Flower configuration, health-check behavior, container resource limits, and production orchestration.

## Acceptance Criteria

- [x] The Celery command includes `--autoscale=2,1`.
- [x] The Celery command includes `--max-tasks-per-child=5`.
- [x] Existing worker hostname and log-level options remain unchanged.
- [x] `docker compose config --quiet` succeeds.
- [x] A recreated Celery container reports a maximum concurrency of two and one idle child.
- [x] Runtime pool statistics report a five-task child recycle limit.

## Completion Evidence

- Rendered Compose command preserves the application, log level, and hostname while adding only
  `--autoscale=2,1` and `--max-tasks-per-child=5`.
- A recreated worker reported autoscaler `min=1`, `max=2`, and `current=1` while idle.
- Celery runtime statistics reported `max-tasks-per-child=5`; the validation stack was stopped
  without deleting persisted volumes.

## Open Questions

None. The user selected a minimum of one worker, maximum of two, five tasks per child, and runtime
verification without a new automated contract test.
