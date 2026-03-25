#!/usr/bin/env zsh
# Log skill invocations to .session/skill-usage.log
# Usage: log-skill-usage.sh <skill-name> [agent-name] [session-id]
#
# Creates JSON Lines entries in .session/skill-usage.log:
#   {"ts":"2026-01-11T10:30:45Z","skill":"testing","agent":"dev","session":"abc123"}
#
# Environment:
#   PROJECT_ROOT - Set by find-root.sh (required)

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="${0:A:h}"
source "${SCRIPT_DIR}/common.sh" 2>/dev/null || true

# --- Argument parsing ---
SKILL_NAME="${1:-}"
AGENT_NAME="${2:-unknown}"
SESSION_ID="${3:-}"

if [[ -z "$SKILL_NAME" ]]; then
    echo "Usage: log-skill-usage.sh <skill-name> [agent-name] [session-id]" >&2
    exit 1
fi

# --- Find project root ---
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    # Fallback: find project root ourselves
    dir="$PWD"
    while [[ ! -d "$dir/.pennyfarthing" ]] && [[ "$dir" != "/" ]]; do
        dir="$(dirname "$dir")"
    done
    if [[ -d "$dir/.pennyfarthing" ]]; then
        PROJECT_ROOT="$dir"
    else
        echo "Error: Could not find project root" >&2
        exit 1
    fi
fi

# --- Ensure session directory exists ---
SESSION_DIR="$PROJECT_ROOT/.session"
mkdir -p "$SESSION_DIR"

LOG_FILE="$SESSION_DIR/skill-usage.log"

# --- Build JSON entry ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Auto-detect session ID from active agent sessions if not provided
if [[ -z "$SESSION_ID" ]]; then
    if [[ -d "$SESSION_DIR/agents" ]]; then
        # Use the most recent session file
        SESSION_FILE=$(ls -t "$SESSION_DIR/agents/" 2>/dev/null | head -1)
        if [[ -n "$SESSION_FILE" ]]; then
            SESSION_ID="${SESSION_FILE}"
        fi
    fi
fi

# Use jq for proper JSON escaping
JSON_ENTRY=$(jq -nc \
    --arg ts "$TIMESTAMP" \
    --arg skill "$SKILL_NAME" \
    --arg agent "$AGENT_NAME" \
    --arg session "${SESSION_ID:-none}" \
    '{ts: $ts, skill: $skill, agent: $agent, session: $session}')

# --- Append to log ---
echo "$JSON_ENTRY" >> "$LOG_FILE"

# Silent success (don't interfere with skill output)
exit 0
