---
description: Detect and run CI locally
args: "[run] [--detect-only] [--dry-run]"
---

# CI Operations

<purpose>
Run CI locally by detecting the project's CI system and executing appropriate commands.
</purpose>

## Commands

### `/pf-ci run`

Run CI locally (auto-detects CI system).

```bash
# Run CI
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/run-ci.sh

# Detect only
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/run-ci.sh --detect-only

# Dry run
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/run-ci.sh --dry-run
```

## CI System Detection

| Priority | System | Detection | Command |
|----------|--------|-----------|---------|
| 1 | Justfile | `just --list` shows `ci` recipe | `just ci` |
| 2 | GitHub Actions | `.github/workflows/*.yml` | `act` |
| 3 | GitLab CI | `.gitlab-ci.yml` | `gitlab-runner exec` |
| 4 | npm fallback | `package.json` | `npm run build && npm test && npm run lint` |

## Related

- `/pf-check` — Run quality gates before handoff
