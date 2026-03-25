#!/usr/bin/env zsh
# Create a Jira epic and its child stories from sprint YAML
# Usage: create-jira-epic.sh <epic-id> [--dry-run]
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.jira create epic <epic-id> [--dry-run]

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module jira create epic "$@"
