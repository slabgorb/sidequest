---
description: Run quality gates (lint, type check, tests) before handoff
---

<purpose>
Run all quality gates before handing off to Reviewer. Ensures code meets quality standards.
</purpose>

<when-to-use>
- Before creating a PR
- Before handoff to Reviewer
- After implementing a feature
- To verify codebase health
</when-to-use>

<execution>

## Running Quality Checks

Use the check.sh script:

```bash
# Run all checks (lint, typecheck, tests)
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh

# Run checks in a specific repo subdirectory
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --repo api
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --repo ui

# Run only tests (skip lint and typecheck)
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --tests-only

# Run tests with a filter pattern
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --filter "TestUserLogin"

# Run filtered tests in a specific repo
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --repo api --filter "TestUserLogin"

# Run only filtered tests (no lint/typecheck)
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --tests-only --filter "TestUserLogin"

# Skip individual checks
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --no-lint
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --no-typecheck

# Skip all checks (emergencies only)
$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/check.sh --skip-check
```

## Options

| Option | Description |
|--------|-------------|
| `--skip-check` | Skip all checks (emergency bypass) |
| `--tests-only` | Run only tests, skip lint and typecheck |
| `--filter PATTERN` | Filter tests by pattern |
| `--repo REPO` | Run checks in a specific repo subdirectory |
| `--no-lint` | Skip lint check |
| `--no-typecheck` | Skip type check |

## What Gets Checked

The script automatically detects project type and runs appropriate checks:

### For Node/TypeScript Projects:
| Check | Command | Condition |
|-------|---------|-----------|
| Lint | `just lint` or `npm run lint` | If configured |
| Type Check | `just typecheck` or `tsc --noEmit` | If tsconfig.json exists |
| Tests | `just test` or `npm test` | If configured |

### For Go Projects:
| Check | Command | Condition |
|-------|---------|-----------|
| Lint | `just lint` or `golangci-lint run` | If available |
| Tests | `just test` or `go test ./...` | Always |

### Justfile Preference
If both justfile and npm scripts exist, justfile recipes take priority.

</execution>

<output-format>

```
Quality Gate Check
==================
Project: /path/to/project

Lint
========================================
  [PASS] Lint (npm run lint)

Type Check
========================================
  [PASS] Type Check (tsc --noEmit)

Tests
========================================
  [PASS] Tests (npm test)

Summary
========================================

Checks run:    3
Checks passed: 3
Checks failed: 0

PASSED - All checks passed
```

Exit codes:
- `0` - All checks passed (or --skip-check used)
- `1` - One or more checks failed

</output-format>

<skip-check>

## Emergency Skip

Use `--skip-check` only in emergencies:

```bash
./scripts/check.sh --skip-check
```

This will:
- Skip all quality checks
- Show a warning message
- Return exit code 0

**Use sparingly.** Skipped checks should pass before PR merge.

</skip-check>

<integration>

## dev-handoff Integration

The dev-handoff subagent runs `/check` automatically before handoff to Reviewer:

1. Dev completes implementation
2. dev-handoff runs `check.sh`
3. If checks fail: handoff is blocked
4. If checks pass: proceed to Reviewer

To bypass (emergencies): pass `--skip-check` to dev-handoff.

</integration>

<reference>
- **Script:** `pennyfarthing-dist/scripts/check.sh`
- **Called by:** dev-handoff subagent
- **Blocks:** Handoff to Reviewer on failure
</reference>
