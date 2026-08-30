# RAVID Agent Rules Cleanup

---
date: 2026-08-30T10:41:00+07:00
type: technical-journal
scope: agent-config
---

## Context

The project directory contained agent rules for an unrelated SANA landing page and frontend stack.
The current assignment is a Python backend RAG chatbot assessment for RAVID.

## What Happened

`AGENTS.md` was replaced with a RAVID-specific backend contract covering document upload,
asynchronous ingestion status, RAG query, optional HyDE, Docker Compose, documentation, and security
invariants.

Claude project configuration was cleaned so it no longer auto-suggests frontend commands or runs a
pnpm/Prettier-only save hook. ClaudeKit's generic Node-based hooks remain active.

## Decisions

- Keep backend implementation choices unresolved until scaffold planning.
- Prefer FastAPI by default, but leave Django valid because the assessment permits both.
- Treat HyDE as bonus only; baseline upload, ingestion, status, and chat come first.
- Keep generic toolkit files and lockfile ignore patterns even when they mention frontend ecosystems.

## Verification

Static checks passed for JSON syntax, hook path resolution, hook JavaScript syntax, active-context
keyword cleanup, plan validation, and plan completion. Reviewer and tester subagents reported no
blocking findings.

## Next

Create the backend scaffold plan and implement the assignment baseline.
