---
title: Replace SANA Agent Rules with RAVID Backend Rules
description: >-
  Remove stale SANA/Next.js agent context and align project instructions with
  the RAVID Python RAG backend assessment.
status: completed
priority: P1
branch: ''
tags:
  - config
  - backend
  - ai-agents
blockedBy: []
blocks: []
created: '2026-08-30T03:29:04.834Z'
createdBy: 'ck:plan'
source: skill
---

# Replace SANA Agent Rules with RAVID Backend Rules

## Overview

Replace project-specific SANA landing-page instructions with a concise RAVID backend contract derived from the assessment PDF. Align agent permissions and formatting hooks with the Python backend workflow, then verify that project-level agent context contains no stale SANA assumptions.

This plan changes agent guidance only. It does not scaffold FastAPI, Celery, PostgreSQL, Redis, LangChain, Docker, or application tests.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Define RAVID Agent Contract](./phase-01-define-ravid-agent-contract.md) | Completed |
| 2 | [Align Agent Tooling Configuration](./phase-02-align-agent-tooling-configuration.md) | Completed |
| 3 | [Verify Context and Remove SANA Residue](./phase-03-verify-context-and-remove-sana-residue.md) | Completed |

## Dependencies

- Source of truth: `2026-08-30 R.A.V.I.D. Assessment & Evaluation for Back End Candidates.pdf`
- No unfinished project-local plans detected.
- No Git repository or application scaffold currently exists.

## Scope

- Rewrite `AGENTS.md` for the RAVID Python backend assignment.
- Keep `CLAUDE.md` as the single import bridge to `AGENTS.md`.
- Remove stale frontend command permissions from `.claude/settings.json`.
- Remove or replace the pnpm/Prettier-only formatting hook.
- Clean only clearly project-specific Next.js entries from `.claude/.gitignore`.
- Preserve generic ClaudeKit rules, hooks, skills, schemas, and multi-framework detection code.

## Acceptance Criteria

- Project-level instructions contain no SANA, investment landing-page, lead, Google Sheets, Turnstile, or Next.js requirements.
- `AGENTS.md` accurately describes the required RAVID APIs, asynchronous ingestion, user isolation, RAG, Docker services, security boundaries, and quality commands.
- Ambiguous assignment areas remain documented assumptions, not invented mandatory behavior.
- Claude still loads `AGENTS.md` through `CLAUDE.md`.
- Every configured hook path exists and configuration files remain syntactically valid.
