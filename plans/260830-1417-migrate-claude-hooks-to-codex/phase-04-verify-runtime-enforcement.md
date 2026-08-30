---
phase: 4
title: "Verify Runtime Enforcement"
status: pending
priority: P1
dependencies: [1, 2, 3]
---

# Phase 4: Verify Runtime Enforcement

## Overview

Prove that every migrated Codex hook or adapter works in the runtime mode where it is expected to protect users. Manual script success is necessary but not sufficient.

## Requirements

- Functional: verify registered hooks with manual payload checks.
- Functional: verify fresh interactive Codex runtime behavior.
- Functional: verify `codex exec` separately and document divergence.
- Functional: verify subagent spawn context/state path end to end.
- Non-functional: tests must not rely on secrets or private notification tokens.
- Non-functional: verification must leave no probe files in the repo unless they are intentional test fixtures.

## Architecture

Validation has three layers:

1. Static: registry JSON is valid and command files exist.
2. Manual: representative payloads produce expected Codex-compatible output.
3. Runtime: fresh Codex sessions invoke hooks/adapters without direct script calls.

Only layer 3 proves enforcement.

## Related Code Files

- Read/Verify: `.codex/hooks.json`
- Read/Verify: `.codex/hooks-support.md`
- Verify: `.codex/hooks/*.cjs`
- Use temp files only: `/tmp/codex-hook-probe-*`

## Implementation Steps

1. Static validation:
   - parse `.codex/hooks.json`
   - confirm every command file exists
   - confirm no local secret paths are referenced
2. Manual payload validation:
   - `UserPromptSubmit`
   - `PreToolUse`
   - every newly registered event
   - every adapter helper
3. Regression tests:
   - run hook unit tests related to migrated behavior
   - add focused tests only if new shared helpers are introduced
4. Runtime probe: `codex exec`
   - spawn a child agent
   - trigger safe command/tool calls
   - record whether hooks fire
5. Runtime probe: interactive Codex
   - trust fresh `/tmp` workspace
   - trigger each expected event
   - verify hook output changes behavior or logs evidence
6. Enforcement checks:
   - ignored dependency read is blocked before shell execution
   - sensitive dotenv read is blocked
   - context injection reaches subagent or adapter prompt
   - session/task state refresh runs after task/subagent completion
7. Update `.codex/hooks-support.md` with final support matrix, exact commands, and residual gaps.
8. Run `git diff --check` on changed hook/config/docs files.

## Success Criteria

- [ ] Static registry validation passes.
- [ ] Manual payload checks pass for all registered hooks.
- [ ] Fresh interactive Codex proves every safety hook that claims enforcement.
- [ ] Subagent behavior is proven by actual `spawn_agent` execution, not only manual payloads.
- [ ] `codex exec` support or limitation is recorded separately.
- [ ] `.codex/hooks-support.md` reflects final verified state.
- [ ] No probe artifacts remain in tracked repo paths.

## Risk Assessment

Risk: runtime probes require local Codex DB writes or hook trust prompts. Mitigation: request explicit escalation only for Codex runtime commands and keep agent sandbox read-only where possible.

Risk: tests pass manually but hooks do not fire. Mitigation: acceptance criteria require fresh runtime evidence before claiming support.
