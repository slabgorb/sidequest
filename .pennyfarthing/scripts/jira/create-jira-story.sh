#!/usr/bin/env zsh
# Create a single Jira story from sprint YAML
# Usage: create-jira-story.sh <epic-jira-key> <story-id> [--dry-run]
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.jira create story <epic-jira-key> <story-id> [--dry-run]

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module jira create story "$@"
