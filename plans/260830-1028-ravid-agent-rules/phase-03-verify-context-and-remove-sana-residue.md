---
phase: 3
title: Verify Context and Remove SANA Residue
status: completed
priority: P1
dependencies:
  - 2
effort: small
---

# Phase 3: Verify Context and Remove SANA Residue

## Overview

Run focused static checks proving that active project-level agent context describes RAVID, all referenced hooks exist, and no SANA-specific assumptions remain. Document accepted generic matches rather than modifying reusable toolkit internals.

## Requirements

- Functional: verify text cleanup, config syntax, hook references, and Claude-to-AGENTS import behavior.
- Non-functional: checks must be repeatable, read-only, and scoped to project configuration rather than bundled skills or generic framework detectors.
- Evidence: record command outcomes in the implementation handoff; do not claim success from visual inspection alone.

## Architecture

Validation distinguishes active project context from reusable tool catalogs:

- Active context: `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, registered hooks.
- Generic toolkit: `.agents/skills/**`, `.claude/skills/**`, framework detectors, and test fixtures.

Only stale matches in active context block completion. Words such as `Asana`, generic Next.js skill descriptions, and multi-framework detector fixtures are expected and must not trigger unrelated edits.

## Related Code Files

- Verify: `/home/khoipham/Projects/ravid-assignment/Ravid/AGENTS.md`
- Verify: `/home/khoipham/Projects/ravid-assignment/Ravid/CLAUDE.md`
- Verify: `/home/khoipham/Projects/ravid-assignment/Ravid/.claude/settings.json`
- Verify: `/home/khoipham/Projects/ravid-assignment/Ravid/.claude/hooks/`
- Verify: `/home/khoipham/Projects/ravid-assignment/Ravid/.claude/.gitignore`

## Implementation Steps

1. Search active project context for `SANA`, investment landing-page language, Google Sheets, Turnstile, lead collection, `LeadRepository`, Next.js routes, shadcn, and pnpm.
2. Review each remaining match and classify it as stale active context or accepted generic toolkit content.
3. Parse `.claude/settings.json` with a JSON parser.
4. Resolve every hook command path configured in `.claude/settings.json` and confirm each file exists.
5. Run `node --check` on remaining JavaScript hook files touched by the cleanup, if any.
6. Confirm `CLAUDE.md` contains the single `@AGENTS.md` import and no copied project rules.
7. Read the final `AGENTS.md` once end to end and compare mandatory claims against the assessment PDF.
8. Report unresolved assignment questions separately; they do not block the agent-rule cleanup unless they were accidentally encoded as facts.

## Success Criteria

- [ ] No SANA-specific text remains in active project agent context.
- [ ] No Next.js/frontend command or hook assumption remains active.
- [ ] All registered hook files exist.
- [ ] Settings JSON and touched JavaScript files pass syntax checks.
- [ ] `CLAUDE.md` imports the rewritten `AGENTS.md` exactly once.
- [ ] RAVID requirements in `AGENTS.md` are traceable to the PDF.
- [ ] Generic toolkit files remain unchanged.

## Risk Assessment

A repository-wide keyword search produces false positives from bundled skills and framework tests. Mitigation: validate active files first and explicitly whitelist generic toolkit matches. Do not delete reusable capabilities merely because they mention React, Next.js, pnpm, or Asana.

## Security Considerations

- Verification must not read `.env` files or print secrets.
- Do not execute application services during this configuration-only cleanup.
- Preserve privacy-block and destructive-command safeguards.

## Next Steps

After all gates pass, mark phases complete through `ck plan check` and hand off to the separate backend scaffold plan.
