#!/bin/bash
# Drift Detection - Analyze archived sessions for agent behavior drift
# Usage: .pennyfarthing/scripts/health/drift-detection.sh [--verbose] [--path /additional/path]
#
# Checks:
# 1. Reviewer: Substantive comments present (not just "LGTM")
# 2. Dev: Tests run before GREEN declaration
# 3. SM: Handoff markers present
# 4. TEA: Tests written before handoff to Dev

set -euo pipefail

VERBOSE=false
EXTRA_PATHS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --verbose|-v) VERBOSE=true; shift ;;
    --path) EXTRA_PATHS+=("$2"); shift 2 ;;
    *) shift ;;
  esac
done

# Find project root
source "$(dirname "${BASH_SOURCE[0]}")/../lib/find-root.sh"

ARCHIVE_DIR="$PROJECT_ROOT/sprint/archive"
SESSION_DIR="$PROJECT_ROOT/.session/archive"

# Build list of directories to search
SEARCH_DIRS=("$ARCHIVE_DIR" "$SESSION_DIR")
for extra in "${EXTRA_PATHS[@]}"; do
  if [[ -d "$extra/sprint/archive" ]]; then
    SEARCH_DIRS+=("$extra/sprint/archive")
  fi
  if [[ -d "$extra/.session/archive" ]]; then
    SEARCH_DIRS+=("$extra/.session/archive")
  fi
  if [[ -d "$extra" ]] && [[ ! -d "$extra/sprint" ]]; then
    # Direct path to archive directory
    SEARCH_DIRS+=("$extra")
  fi
done

echo "# Agent Behavior Drift Detection Report"
echo ""
echo "Generated: $(date '+%Y-%m-%d %H:%M')"
echo ""

# Counters
TOTAL_SESSIONS=0
REVIEWER_ISSUES=0
DEV_ISSUES=0
SM_ISSUES=0
TEA_ISSUES=0

# Collect session files from all locations
SESSION_FILES=$(find "${SEARCH_DIRS[@]}" -name "*-session.md" -type f 2>/dev/null | sort -u | head -100)

if [[ -z "$SESSION_FILES" ]]; then
  echo "No session files found for analysis."
  exit 0
fi

echo "## Analysis Summary"
echo ""

# Analyze each session
while IFS= read -r session_file; do
  ((TOTAL_SESSIONS++))
  filename=$(basename "$session_file")

  # Check for Reviewer drift: approvals without substantive comments
  if grep -qi "reviewer" "$session_file" 2>/dev/null; then
    if grep -qi "approved" "$session_file" 2>/dev/null; then
      # Look for substantive review content (more than just approval)
      review_lines=$(grep -c -iE "(issue|concern|suggest|fix|change|improve|refactor|test|bug)" "$session_file" 2>/dev/null || echo "0")
      if [[ "$review_lines" -lt 2 ]]; then
        ((REVIEWER_ISSUES++))
        if [[ "$VERBOSE" == "true" ]]; then
          echo "⚠️  Reviewer drift: $filename - approval without substantive feedback"
        fi
      fi
    fi
  fi

  # Check for Dev drift: GREEN without test evidence
  if grep -qi "GREEN\|green phase\|tests pass" "$session_file" 2>/dev/null; then
    if ! grep -qiE "(test.*pass|tests.*ran|npm test|vitest|jest|\d+ passed)" "$session_file" 2>/dev/null; then
      ((DEV_ISSUES++))
      if [[ "$VERBOSE" == "true" ]]; then
        echo "⚠️  Dev drift: $filename - GREEN declared without test evidence"
      fi
    fi
  fi

  # Check for SM drift: handoff sections without proper structure
  # Note: PF:HANDOFF markers are optional - we check for structured handoff content
  if grep -qi "## Handoff\|Handoff to" "$session_file" 2>/dev/null; then
    # Good handoff should mention target agent AND have some context
    if ! grep -qiE "handoff.*(TEA|Dev|Reviewer)|→.*(TEA|Dev|Reviewer)" "$session_file" 2>/dev/null; then
      ((SM_ISSUES++))
      if [[ "$VERBOSE" == "true" ]]; then
        echo "⚠️  SM drift: $filename - handoff section without target agent"
      fi
    fi
  fi

  # Check for TEA drift: handoff to Dev without test files mentioned
  if grep -qi "TEA.*handoff\|handoff.*Dev" "$session_file" 2>/dev/null; then
    if ! grep -qiE "\.test\.(ts|js|tsx)|spec\.(ts|js)|_test\.go|Test\.java" "$session_file" 2>/dev/null; then
      ((TEA_ISSUES++))
      if [[ "$VERBOSE" == "true" ]]; then
        echo "⚠️  TEA drift: $filename - no test files referenced before Dev handoff"
      fi
    fi
  fi

done <<< "$SESSION_FILES"

echo "| Agent | Issues | Total | Rate |"
echo "|-------|--------|-------|------|"
REVIEWER_PCT=$((REVIEWER_ISSUES * 100 / TOTAL_SESSIONS))
DEV_PCT=$((DEV_ISSUES * 100 / TOTAL_SESSIONS))
SM_PCT=$((SM_ISSUES * 100 / TOTAL_SESSIONS))
TEA_PCT=$((TEA_ISSUES * 100 / TOTAL_SESSIONS))
echo "| Reviewer | $REVIEWER_ISSUES | $TOTAL_SESSIONS | ${REVIEWER_PCT}% |"
echo "| Dev | $DEV_ISSUES | $TOTAL_SESSIONS | ${DEV_PCT}% |"
echo "| SM | $SM_ISSUES | $TOTAL_SESSIONS | ${SM_PCT}% |"
echo "| TEA | $TEA_ISSUES | $TOTAL_SESSIONS | ${TEA_PCT}% |"
echo ""

TOTAL_ISSUES=$((REVIEWER_ISSUES + DEV_ISSUES + SM_ISSUES + TEA_ISSUES))

if [[ "$TOTAL_ISSUES" -eq 0 ]]; then
  echo "✅ **No drift detected.** All agents following expected behaviors."
else
  echo "⚠️  **$TOTAL_ISSUES potential drift signals detected.**"
  echo ""
  echo "### Recommendations"
  if [[ "$REVIEWER_ISSUES" -gt 0 ]]; then
    echo "- **Reviewer:** Ensure substantive feedback on all reviews (not just LGTM)"
  fi
  if [[ "$DEV_ISSUES" -gt 0 ]]; then
    echo "- **Dev:** Always include test run output when declaring GREEN"
  fi
  if [[ "$SM_ISSUES" -gt 0 ]]; then
    echo "- **SM:** Use handoff markers (PF:HANDOFF) for GUI integration"
  fi
  if [[ "$TEA_ISSUES" -gt 0 ]]; then
    echo "- **TEA:** Reference specific test files when handing off to Dev"
  fi
fi

echo ""
echo "Run with --verbose to see individual file details."
