---
phase: 1
title: Configure and Verify Worker Pool
status: completed
priority: P1
dependencies: []
---

# Phase 1: Configure and Verify Worker Pool

## Requirements

- Keep the existing Celery application, log level, hostname, health check, and service dependencies.
- Autoscale the prefork pool between one and two child processes.
- Replace a child process after it completes five tasks.
- Preserve all HTTP, database, task, and environment contracts.

## Related Files

- Modify: `compose.yaml` - add the two worker lifecycle flags.

## Implementation Steps

1. Add `--autoscale=2,1` and `--max-tasks-per-child=5` to the Celery service command.
2. Run `docker compose config --quiet` and inspect the rendered Celery command.
3. Recreate the Celery container so it loads the new command.
4. Inspect live Celery pool statistics for autoscale and recycle settings.
5. Review the diff for unrelated changes and contract regressions.

## Success Criteria

- [x] Idle worker count is configured as one and burst capacity as two.
- [x] Each worker child is configured to recycle after five completed tasks.
- [x] Existing Compose contracts remain valid.
- [x] No application or public API behavior changes.
