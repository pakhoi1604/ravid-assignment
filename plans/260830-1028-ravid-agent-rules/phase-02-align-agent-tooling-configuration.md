---
phase: 2
title: Align Agent Tooling Configuration
status: completed
priority: P1
dependencies:
  - 1
effort: small
---

# Phase 2: Align Agent Tooling Configuration

## Overview

Remove project-specific frontend permissions and formatting behavior that would mislead agents working on a Python backend. Preserve generic ClaudeKit runtime functionality and avoid broad command auto-approvals.

## Requirements

- Functional: eliminate pnpm, Next.js, shadcn, TypeScript, ESLint, and Prettier-only project automation.
- Non-functional: keep ClaudeKit hooks operational, settings JSON valid, and command permissions narrowly scoped.
- Safety: do not grant broad unrestricted `python`, shell, Docker mutation, or destructive Git permissions as part of this cleanup.

## Architecture

`.claude/settings.json` owns hook registration and command allowlists. The current `format-on-save.cjs` assumes a pnpm/Prettier frontend and silently does nothing for Python. The clean interim state is to remove that hook registration and file; formatting can be reintroduced after `pyproject.toml` establishes Ruff and the package manager.

Retain `node` permission where required for ClaudeKit's own JavaScript hooks. Generic framework-detection code and reusable skills are not project residue and must remain untouched.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/.claude/settings.json`
- Delete: `/home/khoipham/Projects/ravid-assignment/Ravid/.claude/hooks/format-on-save.cjs`
- Modify conservatively: `/home/khoipham/Projects/ravid-assignment/Ravid/.claude/.gitignore`
- Do not modify: `/home/khoipham/Projects/ravid-assignment/Ravid/.claude/rules/CLAUDE.md`
- Do not modify: `/home/khoipham/Projects/ravid-assignment/Ravid/.agents/skills/`
- Do not modify: `/home/khoipham/Projects/ravid-assignment/Ravid/.codex/hooks/`

## Implementation Steps

1. Remove frontend-specific allowlist entries from `.claude/settings.json`: pnpm, shadcn, Next.js, TypeScript, and ESLint commands.
2. Preserve `node` access needed by configured ClaudeKit hooks and preserve unrelated safe Git inspection commands.
3. Remove the `format-on-save.cjs` PostToolUse hook registration.
4. Delete `format-on-save.cjs` so no stale pnpm/Prettier implementation remains orphaned.
5. Do not add Python formatter permissions yet; add a Ruff hook later together with `pyproject.toml` so tool invocation has a real source of truth.
6. Remove only explicit Next.js/Vercel/TypeScript entries from `.claude/.gitignore`; preserve generic runtime, secret, lockfile, and Python-cache entries.
7. Parse `.claude/settings.json` after editing and enumerate all configured hook paths.

## Success Criteria

- [ ] No frontend-only commands remain in the project permission allowlist.
- [ ] No configured hook references `format-on-save.cjs`.
- [ ] The obsolete pnpm/Prettier hook file is removed.
- [ ] ClaudeKit's required Node-based hooks remain registered and resolvable.
- [ ] `.claude/settings.json` is valid JSON.
- [ ] Generic shared skills and framework detectors are unchanged.

## Risk Assessment

Removing `node` broadly would break ClaudeKit hooks; retain it. Adding Python auto-approvals before toolchain selection could create overly broad permissions; defer those additions. `.claude/.gitignore` is scoped under `.claude`, so cleanup is cosmetic and must not expand into a repository-wide ignore design.

## Security Considerations

- Avoid wildcard permissions for arbitrary Python execution.
- Do not loosen privacy or destructive-command hooks.
- Do not expose environment files while validating configuration.

## Next Steps

Proceed to Phase 3 after JSON parsing and hook-path checks pass.
