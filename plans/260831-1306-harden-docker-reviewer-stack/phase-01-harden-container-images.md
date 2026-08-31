---
phase: 1
title: "Harden Container Images"
status: pending
priority: P1
dependencies: []
---

# Phase 1: Harden Container Images

## Overview

Make Django and Chroma builds reproducible enough for reviewed releases, reduce unnecessary runtime
content, and keep executable code immutable to the non-root process.

## Requirements

- Functional: preserve `runtime` and `test` targets, CPU-only Torch, Chroma `1.5.9`, and entrypoints.
- Non-functional: pin build tools and release base-image digests through a documented update flow.
- Security: runtime users may write only media, model cache, and required temporary paths.

## Architecture

Keep the two-target Django Dockerfile. Pin `uv`; use BuildKit cache mounts for downloads without
retaining package caches in the final layer. Keep source root-owned and chown only writable
directories. Use selective `COPY` or a tightened `.dockerignore`; test may include tests while
runtime excludes tests, mock data, local config, and planning artifacts. Resolve image digests
during implementation; do not invent stale values in the plan.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docker/django/Dockerfile` — tool pinning, cache, ownership, selective runtime copy.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/docker/chroma/Dockerfile` — immutable base reference and minimal ownership.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/.dockerignore` — exclude runtime-irrelevant and sensitive-local artifacts.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py` — protect image/user/version invariants.

## Implementation Steps

1. Capture current image sizes, users, entrypoints, and cold/warm timings as baseline.
2. Select and pin a supported `uv` version; verify frozen sync in both targets.
3. Resolve Python and Chroma base digests, retain readable tags, and document refresh procedure.
4. Add BuildKit cache mounts; ensure download caches are absent from runtime.
5. Replace recursive `/app` ownership with root-owned code and narrowly writable directories.
6. Separate runtime/test copy sets; verify management commands, migrations, and entrypoint remain.
7. Add contracts for users, pins, required files, and excluded artifacts.
8. Build both targets cold and warm; compare behavior, time, and size with baseline.

## Success Criteria

- [ ] Runtime and test images build from the frozen lockfile.
- [ ] `app` cannot modify source but can write media, Hugging Face cache, and temp files.
- [ ] Runtime contains no tests, mock data, `.env`, plans, or agent configuration.
- [ ] Chroma starts as `chroma` and persists `/data`.
- [ ] Base/tool versions are immutable for a release and have an update path.
- [ ] Image size has no unexplained material regression.

## Risk Assessment

- Selective copy may omit runtime assets. Gate with imports, Django check, migrations, and live start.
- Digest pins become stale. Refresh through Dependabot/manual review, never floating silently.
- BuildKit may exclude old Docker versions. Document the minimum supported Compose version.

## Security Considerations

Never copy `.env` or caches into an image. Inspect the final filesystem, not only build context.
Rollback may restore copy/ownership logic but must retain non-root execution.
