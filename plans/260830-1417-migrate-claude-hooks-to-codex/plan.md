---
title: "Migrate Missing Claude Hooks to Codex"
description: "Port the remaining Claude-declared hooks to Codex only where runtime support is proven, and build explicit adapters for unsupported lifecycle behavior."
status: pending
priority: P1
branch: "main"
tags: [infra, config, ai-agents]
blockedBy: []
blocks: []
created: "2026-08-30T07:17:05.365Z"
createdBy: "ck:plan"
source: skill
---

# Migrate Missing Claude Hooks to Codex

## Overview

Migrate the hook behavior declared in `.claude/settings.json` into Codex without pretending unsupported lifecycle events are active. The plan preserves the verified Codex baseline, repairs migration/schema gaps first, then adds only hooks or adapters that can be proven in fresh Codex runtime sessions.

This is a follow-up to `plans/260830-1236-repair-codex-hooks/`, which restored `UserPromptSubmit` and `PreToolUse` but documented gaps for `Notification`, `SessionStart`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `PermissionRequest`, and `Stop`.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Audit Hook Parity](./phase-01-audit-hook-parity.md) | Pending |
| 2 | [Repair Migration Schema](./phase-02-repair-migration-schema.md) | Pending |
| 3 | [Implement Supported Codex Hook Adapters](./phase-03-implement-supported-codex-hook-adapters.md) | Pending |
| 4 | [Verify Runtime Enforcement](./phase-04-verify-runtime-enforcement.md) | Pending |

## Dependencies

- Completed prerequisite: `plans/260830-1236-repair-codex-hooks/`.
- Source of truth for Claude hook intent: `.claude/settings.json`.
- Active Codex registry: `.codex/hooks.json`.
- Codex support notes and prior probes: `.codex/hooks-support.md`.
- Existing generated Codex wrappers and libraries: `.codex/hooks/`.
- No unfinished overlapping project plans detected.

## Scope

- Audit every hook event declared in `.claude/settings.json`.
- Classify each hook as directly supported, adapter-required, or unsupported in Codex.
- Repair `ck migrate` output compatibility for Codex CLI v0.151.0 before adding more generated wrappers.
- Add Codex registrations only for events proven to fire in fresh runtime sessions.
- Implement explicit Codex-side adapters for subagent/session behavior when Codex has no matching lifecycle event.
- Update hook support documentation with exact runtime evidence.

Out of scope:

- Changing `.claude/settings.json` behavior.
- Regenerating all wrappers blindly with `ck migrate`.
- Modifying Django/RAVID application code.
- Adding notification providers or storing local notification secrets.
- Claiming parity for `codex exec` if only interactive Codex supports a hook, or vice versa.

## Current Findings

- Current `.codex/hooks.json` registers only `UserPromptSubmit` and `PreToolUse`.
- Current `.claude/settings.json` also declares `Notification`, `SessionStart`, `PostToolUse`, `SubagentStart`, `SubagentStop`, and `Stop`.
- Prior verification proved interactive `PreToolUse` enforcement for ignored dependency reads.
- Prior probe proved `codex exec` can call `spawn_agent` and receive `probe-ok`, but project hook probe did not record `SubagentStart`, `SubagentStop`, `PostToolUse`, `PreToolUse`, or `Stop` events.
- Claude hook tests for `subagent-init`, `session-state`, and `usage-quota-cache-refresh` pass outside the managed sandbox: 39 passed, 0 failed.
- Several generated Codex wrappers were manually patched for Codex v0.151.0 output schema. Regenerating with current `ck migrate` may erase those patches unless the template is fixed first.

## Architecture Decisions

- Treat `.claude/settings.json` as intent, not as a directly executable Codex contract.
- Treat `.codex/hooks.json` as an enforcement registry: every entry must be runtime-proven.
- Prefer thin Codex wrappers around existing hook libraries over duplicating logic.
- For missing lifecycle events, implement explicit controller-side adapters instead of dead registry entries.
- Keep fail-open behavior for advisory/session hooks; keep fail-closed/blocking behavior only for safety hooks already proven under Codex schema.

## Hook Parity Matrix

| Claude event | Claude hooks | Codex target | Initial status |
| --- | --- | --- | --- |
| `Notification` | `desktop-notify-with-request-detail.cjs` | `PermissionRequest` only if fresh approval prompt fires | Adapter/probe required |
| `SessionStart` | `session-init.cjs`, `usage-quota-cache-refresh.cjs` | Codex session-start hook if supported, else startup wrapper/documented gap | Probe required |
| `UserPromptSubmit` | `simplify-gate.cjs`, `dev-rules-reminder.cjs`, quota refresh | Extend existing Codex event after schema fix | Partially migrated |
| `SubagentStart` | `subagent-init.cjs` | Native event if supported, else `spawn_agent` prompt/context adapter | Adapter likely required |
| `PreToolUse` | descriptive/scout/privacy | Existing Codex baseline plus matcher normalization | Migrated baseline |
| `PostToolUse` | plan-format, session-state, quota refresh | Native event if supported, else explicit tool-bound cache refresh where possible | Probe required |
| `SubagentStop` | cook reminder, session-state | Native event if supported, else `wait`/`close_agent` adapter | Adapter likely required |
| `Stop` | session-state | Native event if supported, else explicit shutdown/manual state save | Probe required |

## Acceptance Criteria

- [ ] Every Claude-declared hook event is classified with evidence in `.codex/hooks-support.md`.
- [ ] `ck migrate` output or local wrapper templates preserve Codex v0.151.0 schema requirements.
- [ ] `.codex/hooks.json` includes all and only runtime-proven Codex hook registrations.
- [ ] Unsupported lifecycle behavior is covered by an explicit adapter or documented as unavailable.
- [ ] Subagent context injection works for Codex-spawned agents or the plan documents the exact runtime blocker.
- [ ] Session/task state refresh works for Codex-supported task lifecycle paths or has a clear fallback.
- [ ] Fresh interactive Codex session verifies enforced hooks without manual script invocation.
- [ ] `codex exec` behavior is tested separately and not conflated with interactive behavior.
- [ ] No secrets, credentials, or local notification tokens are added.

## Validation Commands

```bash
node --test .claude/hooks/__tests__/subagent-init.test.cjs \
  .claude/hooks/__tests__/session-state.test.cjs \
  .claude/hooks/__tests__/usage-quota-cache-refresh.test.cjs

node -e "<manual representative payload checks for each registered .codex hook>"

codex exec --json --dangerously-bypass-hook-trust --skip-git-repo-check \
  --sandbox read-only -C /tmp/codex-hook-probe "<spawn_agent probe>"
```

Interactive verification must also be run because prior evidence shows `codex exec` does not reliably fire project hooks.

## Open Questions

- Does Codex interactive runtime expose native `SessionStart`, `PostToolUse`, `SubagentStart`, `SubagentStop`, or `Stop` hooks in `.codex/hooks.json`?
- If native subagent hooks do not exist, where is the smallest maintainable adapter boundary for `spawn_agent`, `wait`, and `close_agent`?
- Should `dev-rules-reminder` and quota refresh be ported to `UserPromptSubmit` now, or kept deferred until migration schema is fixed?
