#!/usr/bin/env zsh
# Check and claim a story in Jira
# Usage: jira-claim-story.sh <issue-key> [--claim]
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.jira claim <issue-key> [--claim]
#
# Exit codes:
#   0 - Story is available or successfully claimed
#   1 - Story is assigned to someone else
#   2 - Story not found or not synced
#   3 - Error (CLI not installed, Python not found, etc.)

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module jira claim "$@"
