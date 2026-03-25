#!/usr/bin/env bash
# migrate-bmad-workflow.sh - Migrate BMAD workflows to Pennyfarthing format
#
# Usage: ./scripts/migrate-bmad-workflow.sh [--dry-run] <source-dir> [target-dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/migrate_bmad_workflow.py" "$@"
