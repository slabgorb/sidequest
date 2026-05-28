# Hooks

Wrapper scripts for Pennyfarthing's Claude Code lifecycle hooks and git hooks.

## Claude Code lifecycle hooks

These are registered in the plugin's own `hooks/hooks.json` (at the plugin root),
**not** in the user's `.claude/settings.json`. Enabling/disabling the Pennyfarthing
plugin toggles them. `hooks.json` registers six events — `SessionStart`, `Stop`,
`PreToolUse`, `PostToolUse`, `SessionEnd`, `PreCompact` — each invoking one of the
wrappers below.

| Script | Purpose |
|--------|---------|
| `session-start.sh` | `SessionStart` wrapper. Launches the Frame server detached (`nohup … & disown` so it survives the hook process-group kill), then `exec`s `pf hooks dispatch SessionStart`. |
| `dispatch.sh` | Wrapper for every other event. `exec`s `pf hooks dispatch "$1"`, where `$1` is the event name passed by `hooks.json`. |

The Python dispatcher (`pf hooks dispatch <Event>`) reads stdin once and runs all
matching handlers in a single process. Tool-name matcher routing (Edit, Write,
Bash, …) is internal to the dispatcher, so `hooks.json` carries no matcher keys.

## Git hooks

Installed into `.git/hooks/` via `pf git install-hooks`. Unrelated to the Claude
Code lifecycle hooks above.

| Script | Purpose |
|--------|---------|
| `pre-commit.sh` | Branch protection, agent validation, sprint YAML validation. |
| `pre-push.sh` | Pre-push validation. |
| `post-merge.sh` | Post-merge actions. |
| `dispatcher-template.sh` | Template for the `.git/hooks/{name}` dispatcher that runs all scripts in `.git/hooks/{name}.d/` in sorted order. |

## Ownership

- **Primary users:** Claude Code (plugin hooks), Git (git hooks)
- **Maintained by:** Core Pennyfarthing team
