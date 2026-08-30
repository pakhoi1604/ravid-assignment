---
phase: 2
title: Restore Baseline Hook Registry
status: completed
priority: P1
dependencies:
  - 1
---

# Phase 2: Restore Baseline Hook Registry

## Overview

Restore the known-good `.codex/hooks.json` structure from the backup for the hooks already present in `.codex/hooks/`.

## Requirements

- Functional: re-enable baseline `UserPromptSubmit` and `PreToolUse` hooks.
- Functional: keep command paths valid for Codex new sessions.
- Non-functional: minimal JSON-only change where possible.
- Non-functional: preserve generated wrappers only if Codex requires them.

## Architecture

The baseline registry should route Codex events to Codex-side scripts, not Claude-side scripts. Prefer `.codex/hooks/simplify-gate.cjs`, `.codex/hooks/descriptive-name.cjs`, `.codex/hooks/scout-block.cjs`, and `.codex/hooks/privacy-block.cjs` if direct paths are supported. Use generated hash wrappers only when the Codex hook bridge requires those wrappers.

## Related Code Files

- Modify: `.codex/hooks.json`
- Read: `.codex/hooks.json.2026-07-06T17-00-56.bak`
- Read: `.codex/hooks/simplify-gate.cjs`
- Read: `.codex/hooks/descriptive-name.cjs`
- Read: `.codex/hooks/scout-block.cjs`
- Read: `.codex/hooks/privacy-block.cjs`
- Modify only if verification requires: `.codex/hooks/*.cjs`

## Implementation Steps

1. Start from the backup event structure.
2. Replace `"$CLAUDE_PROJECT_DIR"/.codex/...` commands with the path format verified in Phase 1.
3. Register:
   - `UserPromptSubmit` -> `simplify-gate`
   - `PreToolUse` matcher `Write` -> `descriptive-name`
   - `PreToolUse` matcher `Bash|Glob|Grep|Read|Edit|Write` -> `scout-block`, `privacy-block`
4. Validate JSON syntax.
5. Run each hook script manually with representative minimal payloads.
6. Trigger a read/write/tool scenario in a fresh Codex session if feasible.

## Success Criteria

- [x] `.codex/hooks.json` contains the restored baseline event structure.
- [x] Every command points to an existing script.
- [x] `node` can execute each referenced script without module resolution errors.
- [x] Privacy/scout/descriptive-name behavior is observable or manually proven with payloads.

## Risk Assessment

Risk: using `CLAUDE_PROJECT_DIR` in Codex may fail if the variable is absent. Mitigation: use relative paths or a Codex-confirmed project path variable.
