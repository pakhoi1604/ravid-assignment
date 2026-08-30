---
phase: 1
title: "Audit Hook Parity"
status: pending
priority: P1
dependencies: []
---

# Phase 1: Audit Hook Parity

## Overview

Create an exact inventory of Claude hook intent, current Codex registry coverage, generated wrapper availability, and runtime support evidence. This phase prevents bulk migration from registering hooks that do not fire.

## Requirements

- Functional: map every `.claude/settings.json` hook entry to a Codex target state.
- Functional: identify existing `.codex/hooks/*.cjs` wrappers and original libraries that can be reused.
- Functional: classify each event as proven, unproven, unsupported, or adapter-required.
- Non-functional: no behavior changes in this phase except optional probe files under `/tmp`.
- Non-functional: evidence must distinguish manual payload checks from fresh runtime firing.

## Architecture

Use `.claude/settings.json` as the desired behavior contract and `.codex/hooks.json` as the enforced Codex contract. Runtime support is authoritative: generated files count only as available implementation material, not as proof that Codex will invoke them.

## Related Code Files

- Read: `.claude/settings.json`
- Read: `.codex/hooks.json`
- Read: `.codex/hooks-support.md`
- Read: `.codex/hooks/`
- Read: `.claude/hooks/`
- Create/Modify later phases only: no repo code changes in this phase

## Implementation Steps

1. Extract the Claude hook matrix:
   - `Notification`
   - `SessionStart`
   - `UserPromptSubmit`
   - `SubagentStart`
   - `PreToolUse`
   - `PostToolUse`
   - `SubagentStop`
   - `Stop`
2. Extract current Codex registry coverage from `.codex/hooks.json`.
3. Inventory generated Codex wrappers and identify which Claude hook or library each wraps.
4. Run representative manual payload checks for candidate hooks:
   - `subagent-init`
   - `session-state`
   - `usage-quota-cache-refresh`
   - `plan-format-kanban`
   - `desktop-notify-with-request-detail`
   - `dev-rules-reminder`
5. Run `/tmp` probe workspaces for both Codex modes:
   - `codex exec --json`
   - interactive `codex --no-alt-screen`
6. Record exact payload keys for every event that fires.
7. Update `.codex/hooks-support.md` with a parity table and test date.

## Success Criteria

- [ ] Hook parity table lists every Claude event and hook command.
- [ ] Every Codex candidate has manual payload check result.
- [ ] Fresh runtime probe result exists for `codex exec`.
- [ ] Fresh runtime probe result exists for interactive Codex or a documented blocker explains why not.
- [ ] `.codex/hooks-support.md` distinguishes manual check, exec runtime, and interactive runtime.

## Risk Assessment

Risk: Codex interactive probing may require trust prompts or local state DB writes. Mitigation: use `/tmp` probe workspaces, read-only agent sandbox, and explicit user approval for commands that need local Codex state.

Risk: `codex exec` may differ from interactive runtime. Mitigation: never use exec-only behavior as proof for interactive enforcement.
