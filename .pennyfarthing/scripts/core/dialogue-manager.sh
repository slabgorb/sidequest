#!/usr/bin/env bash
# dialogue-manager.sh — Dialogue file management for tandem agent consultation
#
# Creates, appends to, and archives dialogue files recording consultation exchanges
# between tandem agents. Format defined in ADR-0012 (lines 156-195).
#
# Usage:
#   dialogue-manager.sh init <story-id> <workflow> <leader> <partner>
#   dialogue-manager.sh append <story-id> <question> <recommendation> <confidence>
#   dialogue-manager.sh outcome <story-id> <exchange-num> <applied|deferred|rejected> [note]
#   dialogue-manager.sh summarize <story-id>
#   dialogue-manager.sh archive <story-id> [jira-key]

set -euo pipefail

# Self-locate and set up PROJECT_ROOT
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/../lib/find-root.sh"

SESSION_DIR="$PROJECT_ROOT/.session"
ARCHIVE_DIR="$PROJECT_ROOT/sprint/archive"
SUMMARY_MARKER="## Summary"

# =============================================================================
# Helpers
# =============================================================================

usage() {
  echo "Usage:"
  echo "  dialogue-manager.sh init <story-id> <workflow> <leader> <partner>"
  echo "  dialogue-manager.sh append <story-id> <question> <recommendation> <confidence>"
  echo "  dialogue-manager.sh outcome <story-id> <exchange-num> <applied|deferred|rejected> [note]"
  echo "  dialogue-manager.sh summarize <story-id>"
  echo "  dialogue-manager.sh archive <story-id> [jira-key]"
  exit 1
}

dialogue_path() {
  echo "$SESSION_DIR/${1}-dialogue.md"
}

now_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

now_hhmm() {
  date -u +"%H:%M"
}

# Count existing exchanges in a dialogue file
count_exchanges() {
  local file="$1"
  grep -c '^## Exchange ' "$file" 2>/dev/null || echo "0"
}

# =============================================================================
# Commands
# =============================================================================

cmd_init() {
  local story_id="${1:?Missing story-id}"
  local workflow="${2:?Missing workflow}"
  local leader="${3:?Missing leader}"
  local partner="${4:?Missing partner}"
  local file
  file="$(dialogue_path "$story_id")"

  if [[ -f "$file" ]]; then
    echo "Dialogue file already exists: $file"
    exit 0
  fi

  mkdir -p "$SESSION_DIR"

  cat > "$file" <<EOF
# Tandem Dialogue: ${story_id}

**Workflow:** ${workflow}
**Leader:** ${leader} | **Partner:** ${partner}
**Started:** $(now_iso)

---

${SUMMARY_MARKER}
- **Total exchanges:** 0
- **Key decisions:** None
- **Time in tandem:** 0m
EOF

  echo "Created dialogue file: $file"
}

cmd_append() {
  local story_id="${1:?Missing story-id}"
  local question="${2:?Missing question}"
  local recommendation="${3:?Missing recommendation}"
  local confidence="${4:?Missing confidence}"
  local file
  file="$(dialogue_path "$story_id")"

  # Auto-init if file missing
  if [[ ! -f "$file" ]]; then
    echo "Error: Dialogue file not found. Run 'init' first: $file" >&2
    exit 1
  fi

  local num
  num=$(( $(count_exchanges "$file") + 1 ))
  local ts
  ts="$(now_hhmm)"

  # Extract leader and partner from header
  local leader partner
  leader=$(grep '^\*\*Leader:\*\*' "$file" | sed 's/.*\*\*Leader:\*\* \([^ ]*\).*/\1/' | head -1)
  partner=$(grep '^\*\*Leader:\*\*' "$file" | sed 's/.*\*\*Partner:\*\* \([^ ]*\).*/\1/' | head -1)

  # Fallback if parsing fails
  leader="${leader:-leader}"
  partner="${partner:-partner}"

  local exchange_block
  exchange_block="## Exchange ${num}
**[${ts}] ${leader} → ${partner}**

> ${question}

**[${ts}] ${partner}:**

${recommendation}

**Confidence:** ${confidence}

**Outcome:** _pending_

---
"

  # Insert before summary marker
  if grep -q "^${SUMMARY_MARKER}" "$file"; then
    # Use awk to insert before summary
    local tmpfile
    tmpfile="$(mktemp)"
    awk -v block="$exchange_block" -v marker="$SUMMARY_MARKER" '
      $0 == marker { printf "%s\n\n", block }
      { print }
    ' "$file" > "$tmpfile"
    mv "$tmpfile" "$file"
  else
    echo "" >> "$file"
    echo "$exchange_block" >> "$file"
  fi

  echo "Appended exchange #${num} to $file"
}

cmd_outcome() {
  local story_id="${1:?Missing story-id}"
  local exchange_num="${2:?Missing exchange-num}"
  local outcome="${3:?Missing outcome (applied|deferred|rejected)}"
  local note="${4:-}"
  local file
  file="$(dialogue_path "$story_id")"

  if [[ ! -f "$file" ]]; then
    echo "Error: Dialogue file not found: $file" >&2
    exit 1
  fi

  # Validate outcome
  case "$outcome" in
    applied|deferred|rejected) ;;
    *) echo "Error: outcome must be applied, deferred, or rejected" >&2; exit 1 ;;
  esac

  local outcome_text
  if [[ -n "$note" ]]; then
    outcome_text="**Outcome:** ${outcome} - ${note}"
  else
    outcome_text="**Outcome:** ${outcome}"
  fi

  # Find the exchange and update its outcome line
  local in_target=false
  local found=false
  local tmpfile
  tmpfile="$(mktemp)"

  while IFS= read -r line; do
    if [[ "$line" =~ ^##\ Exchange\ ([0-9]+) ]]; then
      if [[ "${BASH_REMATCH[1]}" == "$exchange_num" ]]; then
        in_target=true
      else
        in_target=false
      fi
    fi

    if $in_target && [[ "$line" =~ ^\*\*Outcome:\*\* ]]; then
      echo "$outcome_text" >> "$tmpfile"
      found=true
      in_target=false
    else
      echo "$line" >> "$tmpfile"
    fi
  done < "$file"

  if $found; then
    mv "$tmpfile" "$file"
    echo "Updated exchange #${exchange_num} outcome to: ${outcome}"
  else
    rm -f "$tmpfile"
    echo "Error: Exchange #${exchange_num} not found" >&2
    exit 1
  fi
}

cmd_summarize() {
  local story_id="${1:?Missing story-id}"
  local file
  file="$(dialogue_path "$story_id")"

  if [[ ! -f "$file" ]]; then
    echo "Error: Dialogue file not found: $file" >&2
    exit 1
  fi

  local total
  total="$(count_exchanges "$file")"

  # Collect applied decisions
  local decisions=""
  local in_exchange=false
  local current_outcome=""
  local current_note=""

  while IFS= read -r line; do
    if [[ "$line" =~ ^\*\*Outcome:\*\*\ applied ]]; then
      local note_part="${line#*applied}"
      note_part="${note_part# - }"
      if [[ -n "$note_part" ]]; then
        decisions="${decisions}  - ${note_part}\n"
      fi
    fi
  done < "$file"

  if [[ -z "$decisions" ]]; then
    decisions="None"
  fi

  # Calculate time span from first and last exchange timestamps
  local first_ts last_ts duration="0m"
  first_ts=$(grep -m 1 '^\*\*\[' "$file" | sed 's/.*\*\*\[\([0-9]*:[0-9]*\)\].*/\1/' || echo "")
  last_ts=$(grep '^\*\*\[' "$file" | tail -1 | sed 's/.*\*\*\[\([0-9]*:[0-9]*\)\].*/\1/' || echo "")

  if [[ -n "$first_ts" && -n "$last_ts" ]]; then
    local first_mins last_mins
    first_mins=$(( 10#${first_ts%%:*} * 60 + 10#${first_ts##*:} ))
    last_mins=$(( 10#${last_ts%%:*} * 60 + 10#${last_ts##*:} ))
    local diff=$(( last_mins - first_mins ))
    if (( diff > 0 )); then
      duration="${diff}m"
    fi
  fi

  # Build new summary
  local new_summary="${SUMMARY_MARKER}
- **Total exchanges:** ${total}
- **Key decisions:**
$(echo -e "$decisions")- **Time in tandem:** ${duration}"

  # Replace summary section (everything from marker to end)
  if grep -q "^${SUMMARY_MARKER}" "$file"; then
    local tmpfile
    tmpfile="$(mktemp)"
    awk -v marker="$SUMMARY_MARKER" '
      $0 == marker { found=1; next }
      !found { print }
    ' "$file" > "$tmpfile"
    echo "$new_summary" >> "$tmpfile"
    mv "$tmpfile" "$file"
  else
    echo "" >> "$file"
    echo "$new_summary" >> "$file"
  fi

  echo "Summary refreshed for $file (${total} exchanges)"
}

cmd_archive() {
  local story_id="${1:?Missing story-id}"
  local jira_key="${2:-}"
  local file
  file="$(dialogue_path "$story_id")"

  if [[ ! -f "$file" ]]; then
    echo "No dialogue file to archive: $file"
    exit 0
  fi

  mkdir -p "$ARCHIVE_DIR"

  local prefix="${jira_key:-$story_id}"
  local dest="$ARCHIVE_DIR/${prefix}-dialogue.md"

  cp "$file" "$dest"
  echo "Archived dialogue to: $dest"
}

# =============================================================================
# Dispatch
# =============================================================================

CMD="${1:-}"
shift || true

case "$CMD" in
  init)      cmd_init "$@" ;;
  append)    cmd_append "$@" ;;
  outcome)   cmd_outcome "$@" ;;
  summarize) cmd_summarize "$@" ;;
  archive)   cmd_archive "$@" ;;
  *)         usage ;;
esac
