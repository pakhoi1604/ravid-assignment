# Agent Instructions

This file is the root entrypoint for AI agents working in this repository. Keep it general and
stable. Product requirements, API contracts, architecture decisions, and implementation details
belong in the assignment, project documentation, plans, and source code rather than in this file.

## Instruction Priority

When instructions conflict, follow this order:

1. The user's current request.
2. This `AGENTS.md` file.
3. The applicable files under `.claude/rules/`.
4. Existing project documentation, accepted plans, tests, and established code patterns.

Use the assignment PDF as the source of truth for assessment requirements:
`2026-08-30 R.A.V.I.D. Assessment & Evaluation for Back End Candidates.pdf`.
Do not copy its detailed requirements into this file.

## General Working Rules

- Read the relevant rules, documentation, and nearby code before making changes.
- Search for existing implementations and conventions before creating new files or abstractions.
- Keep changes scoped to the request and preserve unrelated user changes.
- Prefer simple, maintainable solutions and existing project patterns.
- Do not invent product requirements or silently change public contracts.
- Never expose or commit secrets, credentials, private documents, or personal data.
- Use the relevant local skill when the task matches one under `.claude/skills/`.
- Verify changes with the narrowest useful checks, then broaden validation when shared behavior or
  public contracts are affected.
- Update documentation only when behavior, setup, architecture, security, commands, or maintainer
  decisions change.
- Ask the user only when a required decision cannot be resolved from repository context or when an
  action needs explicit approval.

## Rules Map

Read only the rules relevant to the current task:

| Path | Applies when |
| --- | --- |
| `.claude/rules/CLAUDE.md` | Using the ClaudeKit environment or interpreting its operational conventions. |
| `.claude/rules/primary-workflow.md` | Planning, implementing, verifying, or explaining a code change. |
| `.claude/rules/development-rules.md` | Editing code, tests, scripts, or configuration. |
| `.claude/rules/documentation-management.md` | Creating or updating project documentation and plans. |
| `.claude/rules/orchestration-protocol.md` | Delegating to subagents or coordinating parallel work. |
| `.claude/rules/review-audit-self-decision.md` | Reviewing code, applying audit feedback, or reconsidering accepted decisions. |

## Configuration And Hooks Map

| Path | Purpose |
| --- | --- |
| `.claude/settings.json` | Canonical project-level Claude settings, permissions, and active hook registrations. |
| `.claude/settings.local.json` | Machine-local Claude overrides; do not treat them as shared project policy. |
| `.claude/.ck.json` | ClaudeKit feature and workflow configuration. |
| `.claude/.ckignore` | Paths excluded from ClaudeKit scouting and hook processing. |
| `.claude/.mcp.json.example` | Example MCP server configuration; never place credentials in the example. |
| `.claude/hooks/` | Hook implementations referenced by `.claude/settings.json`. |
| `.claude/hooks/managed-hooks.json` | Generated inventory of hooks managed by ClaudeKit; do not edit by hand. |
| `.claude/hooks/docs/README.md` | Hook behavior, setup, and manual verification guidance. |
| `.claude/statusline.cjs` | Claude status-line implementation configured by `.claude/settings.json`. |

Treat `.claude/settings.json` as the source of truth for which hooks are active. A hook file merely
existing under `.claude/hooks/` does not mean it is enabled.

## Agents And Tools Map

| Path | Purpose |
| --- | --- |
| `.claude/agents/` | Specialized subagent roles and their operating instructions. |
| `.claude/skills/` | Task-specific workflows; read the matching `SKILL.md` before using a skill. |
| `.claude/output-styles/` | Optional response styles selected by coding-experience level. |
| `.claude/schemas/` | Schemas for ClaudeKit configuration and skill metadata. |
| `.claude/scripts/` | Maintenance, validation, discovery, and worktree utilities. |

Do not duplicate the contents of these files here. Update the owning rule, hook, agent, skill, or
configuration file when its behavior changes, and keep this map accurate.
