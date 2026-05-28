#!/bin/bash
# handoff-cli.sh - Shell wrapper for handoff-cli.js
# Story 31-10: CLI interface for workflow handoff operations
#
# All logic is implemented in handoff-cli.js (Node.js)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec node "$SCRIPT_DIR/handoff-cli.js" "$@"
