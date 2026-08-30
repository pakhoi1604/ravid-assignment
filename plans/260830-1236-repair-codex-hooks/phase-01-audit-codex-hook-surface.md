---
phase: 1
title: Audit Codex Hook Surface
status: completed
priority: P1
dependencies: []
---

# Phase 1: Audit Codex Hook Surface

## Overview

Confirm what Codex actually loads from `.codex/` during a new session, and identify which Claude-style hook events can be registered directly.

## Requirements

- Functional: list every hook event supported by the current Codex runtime or available local bridge.
- Functional: map current `.codex/hooks.json`, backup `.bak`, and `.claude/settings.json` event sets.
- Non-functional: avoid changing config during audit.
- Non-functional: produce evidence from files, command behavior, or runtime docs available locally.

## Architecture

Codex should treat `.codex/hooks.json` as the active registry. `.claude/settings.json` is a reference source only unless a Codex bridge imports it. The audit determines whether missing Claude events are first-class Codex events or require adapters.

## Related Code Files

- Read: `.codex/hooks.json`
- Read: `.codex/hooks.json.2026-07-06T17-00-56.bak`
- Read: `.codex/config.toml`
- Read: `.codex/hooks/*.cjs`
- Read: `.claude/settings.json`
- Read: `.claude/hooks/*.cjs` only for reference behavior
- Modify: none

## Implementation Steps

1. Diff current `.codex/hooks.json` against `.codex/hooks.json.2026-07-06T17-00-56.bak`.
2. Build a table of hook events in `.claude/settings.json` and whether an equivalent script exists in `.codex/hooks/`.
3. Inspect Codex hook docs or local plugin metadata if available; otherwise test with harmless hook registrations in a disposable branch/change set.
4. Verify whether Codex command payload shape matches the existing `.codex/hooks/*.cjs` scripts: `hook_event_name`, `tool_name`, `tool_input`, `cwd`, transcript fields.
5. Decide which events are safe to register directly and which need wrappers.
6. Record findings in this phase file before implementation begins.

## Success Criteria

- [x] Supported Codex hook events are explicitly listed.
- [x] Unsupported or unknown events are not added blindly.
- [x] Payload compatibility is known for `UserPromptSubmit` and `PreToolUse`.
- [x] Gaps for `Notification` and `SubagentStart` are classified as direct, wrapper-needed, or unsupported.

## Risk Assessment

Main risk: copying `.claude/settings.json` into `.codex/hooks.json` may create dead config that looks active but never fires. Mitigation: every event must have a verification path before being marked supported.
