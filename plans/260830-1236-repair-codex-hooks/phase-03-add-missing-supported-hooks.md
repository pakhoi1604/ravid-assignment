---
phase: 3
title: Add Missing Supported Hooks
status: completed
priority: P1
dependencies:
  - 1
  - 2
---

# Phase 3: Add Missing Supported Hooks

## Overview

Add Codex equivalents for missing Claude-side hook behavior only where Codex supports the trigger or a simple adapter can make the trigger explicit.

## Requirements

- Functional: evaluate missing Claude events one by one: `Notification`, `SessionStart`, `SubagentStart`, `PostToolUse`, `SubagentStop`, and `Stop`.
- Functional: add direct registrations only for supported Codex events.
- Functional: for unsupported agent events, design a wrapper around agent orchestration rather than silent dead hooks.
- Non-functional: fail open for notification/status hooks; block only privacy/scout safety violations.

## Architecture

Missing hooks fall into three categories:

| Event | Desired Codex behavior | Likely implementation |
| --- | --- | --- |
| `Notification` | Notify when approval/idle/decision attention is needed | Direct Codex event if supported; otherwise explicit notifier wrapper |
| `SessionStart` | Inject or refresh session-level context/cache | Direct event if supported; otherwise document unsupported |
| `SubagentStart` | Inject plan/report/context baseline into spawned agents | Direct event if supported; otherwise wrapper before `spawn_agent` |
| `PostToolUse` | Update session state/cache after edits/tasks | Direct event if supported |
| `SubagentStop` | Update session state or notify on subagent completion | Direct event if supported; otherwise controller-side handling |
| `Stop` | Persist final session state | Direct event if supported |

## Related Code Files

- Modify: `.codex/hooks.json`
- Create only if needed: `.codex/hooks/subagent-init.cjs`
- Create only if needed: `.codex/hooks/desktop-notify-with-request-detail.cjs` or a smaller Codex notifier wrapper
- Modify only if needed: `.codex/hooks/notifications/notify.cjs`
- Read/reference: `.claude/hooks/subagent-init.cjs`
- Read/reference: `.claude/hooks/desktop-notify-with-request-detail.cjs`
- Read/reference: `.claude/hooks/session-state.cjs`
- Read/reference: `.claude/hooks/usage-quota-cache-refresh.cjs`

## Implementation Steps

1. For each missing event, confirm whether Codex supports the event name and payload shape.
2. If supported, add a `.codex/hooks.json` entry pointing to a Codex-side script.
3. If no Codex-side script exists, copy/adapt only the minimal logic needed from `.claude/hooks/`, replacing `.claude` assumptions with `.codex` paths.
4. For `SubagentStart`, verify whether Codex can inject `hookSpecificOutput.additionalContext`. If not, do not register a fake hook; document that controller prompts or a spawn wrapper must inject context.
5. For `Notification`, decide provider:
   - desktop notification for local terminal attention, or
   - `.codex/hooks/notifications/notify.cjs` for Telegram/Discord/Slack env-based providers.
6. Keep provider credentials out of git; update `.env.example` only if new safe placeholder variables are required.
7. Add comments or docs only where needed to prevent future accidental overwrite.

## Success Criteria

- [x] Every added event has a confirmed trigger in Codex or is deferred out of the active registry.
- [x] `Notification` behavior is documented as unsupported by the verified Codex runtime.
- [x] `SubagentStart` context injection is implemented or documented as requiring controller/wrapper injection.
- [x] No `.claude`-only environment assumptions remain in Codex hook commands.
- [x] Missing unsupported hooks are listed plainly instead of hidden behind dead config.

## Risk Assessment

Risk: over-porting Claude hooks may create false confidence. Mitigation: unsupported events must remain documented gaps until a runtime-level trigger is proven.

## Verification Notes

- `PermissionRequest` and `Stop` were evaluated but removed from the active Codex registry because fresh-session firing was not proven.
- The only active added runtime adaptation is the `command_execution` matcher for `PreToolUse`, which was verified in the interactive Codex CLI.
