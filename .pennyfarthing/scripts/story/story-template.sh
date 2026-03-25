#!/usr/bin/env zsh
# Show story templates by type
# Usage: story-template.sh [bug|feature|refactor|chore]
#   No args: Show all templates
#   type:    Show specific template
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.story template [type]

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module story template "$@"
