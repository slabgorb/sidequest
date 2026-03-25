#!/usr/bin/env zsh
# Jira vs YAML Reconciliation Report
# Usage: jira-reconcile.sh [--fix]
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.jira reconcile [--fix]

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module jira reconcile "$@"
