#!/bin/bash
# sidecar-health.sh - Check sidecar files for bloat and staleness
#
# Usage: sidecar-health.sh [--fix]
#   --fix    Offer to archive bloated files
#
# Thresholds:
#   gotchas.md: 50 lines max
#   patterns.md: 50 lines max
#   decisions.md: 40 lines max

set -euo pipefail

# Find project root
source "$(dirname "${BASH_SOURCE[0]}")/../lib/find-root.sh"

SIDECAR_DIR="$PROJECT_ROOT/.pennyfarthing/sidecars"
FIX_MODE="${1:-}"

# Thresholds
GOTCHAS_MAX=50
PATTERNS_MAX=50
DECISIONS_MAX=40

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Sidecar Health Check"
echo "===================="
echo ""

issues_found=0

check_file() {
  local file="$1"
  local max_lines="$2"
  local agent=$(basename "$(dirname "$file")")
  local filename=$(basename "$file")

  if [[ ! -f "$file" ]]; then
    return
  fi

  local lines=$(wc -l < "$file" | tr -d ' ')

  if [[ $lines -gt $max_lines ]]; then
    echo -e "${RED}BLOATED${NC}: $agent/$filename ($lines lines, max $max_lines)"
    issues_found=$((issues_found + 1))

    if [[ "$FIX_MODE" == "--fix" ]]; then
      local archive_dir="$PROJECT_ROOT/.pennyfarthing/sidecars/.archive"
      local timestamp=$(date +%Y%m%d)
      mkdir -p "$archive_dir"

      echo "  → Archiving to .archive/${agent}-${filename%.md}-${timestamp}.md"
      cp "$file" "$archive_dir/${agent}-${filename%.md}-${timestamp}.md"
      echo "  → Original preserved. Manually prune $file to <$max_lines lines."
    fi
  elif [[ $lines -gt $((max_lines * 80 / 100)) ]]; then
    echo -e "${YELLOW}WARNING${NC}: $agent/$filename ($lines lines, approaching $max_lines limit)"
  else
    echo -e "${GREEN}OK${NC}: $agent/$filename ($lines lines)"
  fi
}

# Check all agent sidecars
for agent_dir in "$SIDECAR_DIR"/*/; do
  if [[ -d "$agent_dir" ]]; then
    agent=$(basename "$agent_dir")
    [[ "$agent" == ".archive" ]] && continue

    check_file "$agent_dir/gotchas.md" $GOTCHAS_MAX
    check_file "$agent_dir/patterns.md" $PATTERNS_MAX
    check_file "$agent_dir/decisions.md" $DECISIONS_MAX
  fi
done

echo ""
if [[ $issues_found -gt 0 ]]; then
  echo "Found $issues_found bloated file(s)."
  if [[ "$FIX_MODE" != "--fix" ]]; then
    echo "Run with --fix to archive and prepare for pruning."
  fi
  exit 1
else
  echo "All sidecar files within limits."
  exit 0
fi
