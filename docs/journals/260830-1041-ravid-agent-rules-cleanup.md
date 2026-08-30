# RAVID Agent Rules Cleanup

---
date: 2026-08-30T10:41:00+07:00
type: technical-journal
scope: agent-config
---

## Context

The project directory contained agent rules for an unrelated SANA landing page and frontend stack.
That stale product-specific guidance was removed during the earlier cleanup.

## What Happened

`AGENTS.md` is now a general agent entrypoint. It defines instruction priority and working rules,
then maps agents to the owning `.claude` rules, configuration, hooks, agents, skills, schemas, and
scripts without duplicating their contents.

Claude project configuration was cleaned so it no longer auto-suggests frontend commands or runs a
pnpm/Prettier-only save hook. ClaudeKit's generic Node-based hooks remain active.

## Decisions

- Keep product requirements, API contracts, architecture decisions, and stack choices out of
  `AGENTS.md`; their owning assignment, documentation, plans, tests, and source remain authoritative.
- Keep `AGENTS.md` stable and update the owning rule, hook, agent, skill, or configuration file when
  operational behavior changes.
- Keep generic toolkit files and lockfile ignore patterns even when they mention frontend ecosystems.

## Verification

Static checks passed for JSON syntax, hook path resolution, hook JavaScript syntax, active-context
keyword cleanup, plan validation, and plan completion. Reviewer and tester subagents reported no
blocking findings. The current `AGENTS.md` contains no RAVID, API, or stack requirements.

## Next

Use `AGENTS.md` as the repository entrypoint and follow its map to task-specific `.claude` guidance.
