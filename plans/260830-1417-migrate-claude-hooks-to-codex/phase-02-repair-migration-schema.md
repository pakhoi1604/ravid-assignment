---
phase: 2
title: "Repair Migration Schema"
status: pending
priority: P1
dependencies: [1]
---

# Phase 2: Repair Migration Schema

## Overview

Fix or wrap `ck migrate` output so newly migrated Codex hooks preserve Codex CLI v0.151.0 schema semantics. This phase must happen before regenerating or trusting additional wrappers.

## Requirements

- Functional: preserve `decision: "block"` for blocking `PreToolUse` hooks.
- Functional: preserve `additional_context` for Codex context injection.
- Functional: avoid overwriting manually patched wrappers unless replacement output is proven equivalent.
- Functional: define schema treatment for `PermissionRequest`, `Stop`, and advisory hooks.
- Non-functional: generated wrappers remain small, readable, and fail-open except for proven safety blocks.

## Architecture

The migration layer should be a compatibility boundary:

Claude hook output -> wrapper sanitizer/translator -> Codex-supported JSON output.

Do not modify original `.claude/hooks/*` scripts for Codex concerns. Codex-specific output translation belongs in `.codex/hooks/*` wrappers or a shared `.codex/hooks/lib/*` helper.

## Related Code Files

- Modify: `.codex/hooks/*` generated wrappers as needed
- Modify/Create: `.codex/hooks/lib/codex-output-schema.cjs` if a shared translator reduces duplication
- Read: `.codex/hooks-support.md`
- Read: `.codex/hooks/ddbf865c-simplify-gate.cjs`
- Read: `.codex/hooks/e3f4e6fe-descriptive-name.cjs`
- Read: `.codex/hooks/d3d5933f-scout-block.cjs`
- Read: `.codex/hooks/27a4d5f4-privacy-block.cjs`

## Implementation Steps

1. Run `ck migrate` only in a disposable worktree or `/tmp` checkout to inspect current output.
2. Diff generated wrappers against the manually patched Codex v0.151.0 wrappers.
3. Identify required translator rules:
   - Claude `permissionDecision: "deny"` or exit-code block -> Codex `decision: "block"` where applicable.
   - Claude `hookSpecificOutput.additionalContext` -> Codex `additional_context` when Codex event supports context injection.
   - Unsupported fields stripped only when the target Codex event rejects them.
4. Add focused wrapper tests or manual checks for:
   - blocking `PreToolUse`
   - advisory `UserPromptSubmit`
   - context injection output
   - no-op fail-open hooks
5. Regenerate or patch wrappers only after tests prove output equivalence.
6. Document the migration template limitation and safe regeneration rule.

## Success Criteria

- [ ] Existing patched wrappers are not regressed.
- [ ] New wrapper output uses Codex v0.151.0-compatible JSON.
- [ ] Manual payload checks pass for every wrapper considered for registry inclusion.
- [ ] The plan documents whether `ck migrate` is safe to rerun directly or only in a disposable diff workflow.

## Risk Assessment

Risk: bulk `ck migrate` may erase manual schema fixes. Mitigation: never run it directly against the working tree until diffed output is proven compatible.

Risk: schema rules may change in future Codex versions. Mitigation: keep version notes in `.codex/hooks-support.md` and test against `codex --version` during verification.
