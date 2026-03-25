#!/usr/bin/env zsh
# Generate a story YAML block for adding to sprint
# Usage: create-story.sh <epic-id> "<title>" <points> [options]
#   --type bug|feature|refactor|chore  Story type (default: feature)
#   --workflow <name>                  Workflow override
#   --priority P0|P1|P2|P3             Priority (default: P2)
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.story create <epic-id> "<title>" <points> [options]

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module story create "$@"
