#!/usr/bin/env zsh
# Sync a single story between sprint YAML and Jira
# Usage: jira-sync-story.sh <story_key> [--transition] [--points] [--comment "message"]
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.jira create story <story_key> [options]
#
# Note: The subcommand is 'create story' but it handles sync, not creation.

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module jira create story "$@"
