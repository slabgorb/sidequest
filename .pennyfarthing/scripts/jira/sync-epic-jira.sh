#!/usr/bin/env zsh
# Sync an epic and its stories to Jira
# Usage: sync-epic-jira.sh <epic-id> [--dry-run] [--transition] [--points] [--all]
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.jira sync <epic-id> [options]

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module jira sync "$@"
