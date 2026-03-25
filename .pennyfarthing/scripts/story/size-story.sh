#!/usr/bin/env zsh
# Display story sizing guidelines
# Usage: size-story.sh [points]
#   No args: Show all sizing guidelines
#   points:  Show specific guidance for that point value
#
# Thin wrapper that delegates to Python CLI:
#   python -m pf.story size [points]

set -e

# Source common functions for Python discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
source "${PARENT_DIR}/lib/common.sh"

# Delegate to Python CLI
run_python_module story size "$@"
