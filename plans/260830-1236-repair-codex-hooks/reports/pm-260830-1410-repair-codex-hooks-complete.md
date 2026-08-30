## Plan Complete: Repair Codex Hook Registry

### Summary

| Metric | Result |
| --- | --- |
| Status | completed |
| Phases | 4/4 completed |
| Active Codex events | `UserPromptSubmit`, `PreToolUse` |
| Runtime proof | Fresh interactive Codex CLI blocked an ignored dependency-path shell command through `PreToolUse` |

### Achievements

- Restored `.codex/hooks.json` baseline structure from the backup for `UserPromptSubmit` and `PreToolUse`.
- Added Codex `command_execution` matching for shell actions observed in Codex CLI v0.151.0.
- Patched referenced Codex wrappers to emit v0.151.0-compatible `decision: "block"` output.
- Patched descriptive-name wrapper to emit Codex `additional_context`.
- Deferred `PermissionRequest`, `Stop`, `SessionStart`, `SubagentStart`, `PostToolUse`, and `SubagentStop` from active registry until runtime triggers are proven.

### Verification

| Check | Result |
| --- | --- |
| `.codex/hooks.json` parse and command paths | pass, 4 commands |
| Referenced wrapper syntax | pass |
| Wrapper behavior harness outside sandbox | pass |
| `git diff --check` | pass |
| `ck plan status` | done, 4/4 |
| Code review | completed; feedback applied |

### Known Limitations

- `UserPromptSubmit` is registered and manually verified, but fresh-session blocking was not proven because simplify gate thresholds are not enabled in project config.
- `codex exec --json` did not fire project `PreToolUse` in the verified ignored-path scenario.
- Hash-named wrappers are manually patched over generated `ck migrate` output; do not regenerate until the migration template emits the same Codex schema.

### Documentation Updates

- Added `.codex/hooks-support.md`.
- Updated plan and phase files with final event matrix, verification evidence, and limitations.
