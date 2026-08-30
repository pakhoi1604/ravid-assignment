---
title: Repair Codex Hooks
date: '2026-08-30'
tags:
  - codex
  - hooks
  - claudekit
---

# Repair Codex Hooks

## Context

Codex hook configuration had drifted from the known-good backup. The active registry only loaded
`UserPromptSubmit`, while the backup also included baseline `PreToolUse` safety hooks.

## What Happened

Restored the Codex hook registry to include `UserPromptSubmit` and `PreToolUse`, then verified the
interactive Codex CLI runtime. Fresh-session testing showed `PreToolUse` loaded from
`.codex/hooks.json` and blocked an ignored dependency-path shell command before execution.

The first runtime proof exposed a Codex v0.151.0 schema mismatch: old wrapper output using
`permissionDecision: "deny"` was rejected as invalid pre-tool-use JSON. The hash-named wrappers now
normalize blocking output to `decision: "block"`, and the descriptive-name wrapper emits
`additional_context`.

## Decisions

- Keep active registry limited to proven `UserPromptSubmit` and `PreToolUse` events.
- Defer `PermissionRequest`, `Stop`, `SessionStart`, `SubagentStart`, `PostToolUse`, and
  `SubagentStop` until fresh-session triggers are proven.
- Document that `codex exec --json` did not fire project `PreToolUse` in the verified scenario.
- Treat the hash-named wrappers as manually patched over `ck migrate` output until the migration
  template emits the v0.151.0-compatible schema.

## Next

Future work should verify whether newer Codex versions fire project hooks in `codex exec` and
whether lifecycle events can be registered directly without dead config.
