#!/usr/bin/env bash
# check.sh - Quality gate runner for pre-handoff verification
#
# Story 21-1: /check command with dev-handoff integration
#
# Usage: ./scripts/check.sh [OPTIONS]
#
# Options:
#   --skip-check       Skip all checks (emergency bypass)
#   --tests-only       Run only tests, skip lint and typecheck
#   --filter PATTERN   Filter tests by pattern (passed to test runner)
#   --repo REPO        Run checks in specific repo subdirectory
#   --no-lint          Skip lint check
#   --no-typecheck     Skip type check
#   --fast             Skip slow packages (cyclist/Electron) for rapid iteration
#
# Runs lint, type check, and tests. Reports pass/fail status.
# Returns exit code 0 on all passing, non-zero on any failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/check.py" "$@"
