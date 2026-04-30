# Hooks

Git hooks and Claude Code hooks.

## Scripts

| Script | Purpose |
|--------|---------|
| `pf hooks context-breaker` | Claude hook: halt at context limit |
| `pf hooks context-warning` | Claude hook: warn on high context |
| `otel-auto-config.sh` | Claude hook: configure OTEL |
| `post-merge.sh` | Git hook: post-merge actions |
| `pre-commit.sh` | Git hook: branch protection, agent validation, sprint YAML validation |
| `pf hooks pre-edit-check` | Claude hook: validate before edit |
| `pre-push.sh` | Git hook: pre-push validation |
| `pf hooks session-start` | Claude hook: session start |
| `pf hooks session-stop` | Claude hook: session stop |

## Installation

Git hooks are installed via:

```bash
pf git install-hooks
```

Claude hooks are configured in `.claude/settings.json`.

## Ownership

- **Primary users:** Git, Claude Code
- **Maintained by:** Core Pennyfarthing team
