#!/usr/bin/env bash
# add-short-names.sh - Pre-generate shortName field for theme characters
#
# Usage:
#   add-short-names.sh                    # Dry run - show what would change
#   add-short-names.sh --write            # Actually write changes
#   add-short-names.sh --theme discworld  # Only process one theme

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/add_short_names.py" "$@"
