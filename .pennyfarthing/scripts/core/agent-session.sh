#!/usr/bin/env zsh
# Agent session management script
# Usage: agent-session.sh <action> [agent-name] [session-id]
#   start "agent-name" "session-id"  - Register agent session and output persona
#   stop "session-id"                - Remove session for given ID
#   stop-all                         - Remove all agent sessions
#   status                           - Output for Claude Code statusLine (reads JSON from stdin)
#
# Session files stored in .session/agents/<session-id> for multi-session support

# Find package root from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd -P)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"

# Set PYTHONPATH so Python can find pf package (src/ layout)
export PYTHONPATH="${PACKAGE_ROOT}/src:${PYTHONPATH:-}"

# Agents directory for multi-session support
AGENTS_DIR="$PROJECT_ROOT/.session/agents"

# Check if character_voice preference is enabled
# Returns 0 (true) if enabled or not set, 1 (false) if explicitly disabled
is_character_voice_enabled() {
  local prefs_file=""

  # Check for local prefs first, then default
  if [ -f "$PROJECT_ROOT/.claude/pennyfarthing/preferences.local.yaml" ]; then
    prefs_file="$PROJECT_ROOT/.claude/pennyfarthing/preferences.local.yaml"
  elif [ -f "$PROJECT_ROOT/.claude/pennyfarthing/preferences.yaml" ]; then
    prefs_file="$PROJECT_ROOT/.claude/pennyfarthing/preferences.yaml"
  else
    # No preferences file = default to enabled
    return 0
  fi

  # Read character_voice setting (default to true if not set)
  local voice=$(yq '.character_voice' "$prefs_file" 2>/dev/null)
  # If null/empty, default to enabled
  if [ -z "$voice" ] || [ "$voice" = "null" ]; then
    return 0
  fi
  # If explicitly false, return disabled
  if [ "$voice" = "false" ]; then
    return 1
  fi
  return 0
}

# Get agent file path for a session
get_agent_file() {
    local session_id="$1"
    echo "$AGENTS_DIR/$session_id"
}

# Check if theme version matches current Pennyfarthing version
# Only warns on major/minor mismatch, not patch
# Arguments: theme_file, theme_name
check_theme_version() {
  local theme_file="$1"
  local theme_name="$2"

  # Only check custom themes (in .claude/pennyfarthing/themes/)
  if [[ ! "$theme_file" == *".claude/pennyfarthing/themes/"* ]]; then
    return 0
  fi

  # Get theme's pennyfarthing_version
  local theme_version=$(yq '.theme.pennyfarthing_version // ""' "$theme_file" 2>/dev/null)
  if [ -z "$theme_version" ] || [ "$theme_version" = "null" ] || [ "$theme_version" = "" ]; then
    # No version in theme - skip warning (legacy custom theme)
    return 0
  fi

  # Get current version from VERSION file
  local version_file="$PROJECT_ROOT/VERSION"
  if [ ! -f "$version_file" ]; then
    # No VERSION file - skip warning
    return 0
  fi
  local current_version=$(cat "$version_file" 2>/dev/null | tr -d '[:space:]')
  if [ -z "$current_version" ]; then
    return 0
  fi

  # Extract major.minor from both versions
  local theme_major_minor=$(echo "$theme_version" | cut -d. -f1,2)
  local current_major_minor=$(echo "$current_version" | cut -d. -f1,2)

  # Compare major.minor only
  if [ "$theme_major_minor" != "$current_major_minor" ]; then
    echo "" >&2
    echo "Warning: Theme '${theme_name}' was created with Pennyfarthing ${theme_version}" >&2
    echo "         Current version: ${current_version} - agent roles may have changed." >&2
    echo "         Run '/theme maker' to review and update." >&2
    echo "" >&2
  fi

  return 0
}


case "$1" in
  start)
    if [ -z "$2" ]; then
      echo "Usage: agent-session.sh start \"agent-name\" [session-id]" >&2
      exit 1
    fi
    # Use provided session ID, fall back to SESSION_ID env var, then generate one
    session_id="${3:-$SESSION_ID}"
    if [ -z "$session_id" ]; then
      # Generate a session ID if not provided (for fresh sessions)
      session_id=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || date +%s)
    fi
    mkdir -p "$AGENTS_DIR"

    # Clean up old session files (older than 7 days) to prevent accumulation
    find "$AGENTS_DIR" -type f -mtime +7 -delete 2>/dev/null || true

    AGENT_FILE=$(get_agent_file "$session_id")
    echo "$2" > "$AGENT_FILE"
    echo "Session: $session_id -> $2"

    # Prime v2: Unified Python entry point handles everything
    # - Workflow state detection
    # - Agent definition loading
    # - Persona (if character_voice enabled)
    # - Behavior guide
    # - Sidecars
    # - Session/sprint context
    PRIME_ARGS=(--agent "$2" --session-id "$session_id")

    # Pass persona preference to prime
    if ! is_character_voice_enabled; then
      PRIME_ARGS+=(--no-persona)
    fi

    pf prime "${PRIME_ARGS[@]}"
    ;;
  stop)
    # Use provided session ID, fall back to SESSION_ID env var
    session_id="${2:-$SESSION_ID}"
    if [ -z "$session_id" ]; then
      echo "Usage: agent-session.sh stop [session-id]" >&2
      exit 1
    fi

    # Get current agent for this session
    AGENT_FILE=$(get_agent_file "$session_id")
    CURRENT_AGENT=""
    if [ -f "$AGENT_FILE" ]; then
      CURRENT_AGENT=$(cat "$AGENT_FILE")
    fi

    # Validate handoff was spawned (Story 31-16: Enforce handoff subagent spawning)
    # Only check for agents that require handoff (tea, dev, reviewer)
    if [[ "$CURRENT_AGENT" =~ ^(tea|dev|reviewer)$ ]]; then
      # Find active session file
      SESSION_DIR="$PROJECT_ROOT/.session"
      ACTIVE_SESSION=$(find "$SESSION_DIR" -maxdepth 1 -name "*-session.md" -type f ! -name "context-*" 2>/dev/null | head -1)

      if [ -n "$ACTIVE_SESSION" ] && [ -f "$ACTIVE_SESSION" ]; then
        # Map agent to expected assessment section
        case "$CURRENT_AGENT" in
          tea) EXPECTED_SECTION="TEA Assessment" ;;
          dev) EXPECTED_SECTION="Dev Assessment" ;;
          reviewer) EXPECTED_SECTION="Reviewer Assessment" ;;
        esac

        # Check if assessment exists
        HAS_ASSESSMENT=$(grep -q "## $EXPECTED_SECTION" "$ACTIVE_SESSION" 2>/dev/null && echo "yes" || echo "no")

        # Check if handoff was recorded in Handoff History table
        # Table format: | From | To | Phase | Gate | Timestamp |
        # Agent must appear in "From" column (first data column) to indicate they completed handoff
        HAS_HANDOFF="no"

        # Check for agent in "From" column (starts with "| agent |")
        # Case-insensitive match for the agent name at start of row
        if grep -Ei "^\| *$CURRENT_AGENT *\|" "$ACTIVE_SESSION" 2>/dev/null; then
          HAS_HANDOFF="yes"
        fi

        # Also check for PF:HANDOFF marker (handoff output)
        if [ "$HAS_HANDOFF" = "no" ] && grep -qE "PF:HANDOFF" "$ACTIVE_SESSION" 2>/dev/null; then
          HAS_HANDOFF="yes"
        fi

        # Warn if assessment exists but handoff is missing
        if [ "$HAS_ASSESSMENT" = "yes" ] && [ "$HAS_HANDOFF" = "no" ]; then
          echo "" >&2
          echo "WARNING: Handoff subagent was not spawned!" >&2
          echo "" >&2
          echo "  Agent: $CURRENT_AGENT" >&2
          echo "  Assessment: Found ($EXPECTED_SECTION)" >&2
          echo "  Handoff: NOT FOUND" >&2
          echo "" >&2
          echo "  You MUST spawn handoff before stopping:" >&2
          echo "" >&2
          echo "    Task tool:" >&2
          echo "      subagent_type: \"handoff\"" >&2
          echo "      prompt: |" >&2
          echo "        STORY_ID: {story-id}" >&2
          echo "        WORKFLOW: {workflow}" >&2
          echo "        CURRENT_PHASE: {phase}" >&2
          echo "        ..." >&2
          echo "" >&2
          echo "  Session: $(basename "$ACTIVE_SESSION")" >&2
          echo "" >&2
          # Exit non-zero to signal incomplete handoff
          exit 1
        fi
      fi
    fi

    # Clear the agent file for this session
    rm -f "$AGENT_FILE" 2>/dev/null
    echo "Agent session closed: $session_id"
    ;;
  stop-all)
    rm -rf "$AGENTS_DIR" 2>/dev/null
    echo "All agent sessions closed."
    ;;
  status)
    # Read JSON from stdin (Claude Code statusLine passes context)
    input=$(cat)

    # Get session ID from input
    session_id=""
    if command -v jq &>/dev/null && [ -n "$input" ]; then
      session_id=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null)
    fi

    # Get agent name for this session
    if [ -n "$session_id" ]; then
      AGENT_FILE=$(get_agent_file "$session_id")
      if [ -f "$AGENT_FILE" ]; then
        AGENT=$(cat "$AGENT_FILE")
      else
        AGENT=""
      fi
    else
      AGENT=""
    fi

    # Output just the agent name (statusline.sh handles the rest)
    echo "$AGENT"
    ;;
  list)
    # List all active agent sessions
    if [ -d "$AGENTS_DIR" ]; then
      for f in "$AGENTS_DIR"/*; do
        [ -f "$f" ] && echo "$(basename "$f"): $(cat "$f")"
      done
    else
      echo "No active sessions"
    fi
    ;;
  refresh)
    # Re-output persona for current agent (after theme change)
    # Usage: agent-session.sh refresh [session-id]
    session_id="${2:-$SESSION_ID}"
    if [ -z "$session_id" ]; then
      echo "Usage: agent-session.sh refresh [session-id]" >&2
      exit 1
    fi

    AGENT_FILE=$(get_agent_file "$session_id")
    if [ ! -f "$AGENT_FILE" ]; then
      echo "No active session: $session_id" >&2
      exit 1
    fi

    CURRENT_AGENT=$(cat "$AGENT_FILE")
    echo "Use 'pf agent start $CURRENT_AGENT' to refresh persona" >&2
    ;;
  *)
    echo "Usage: agent-session.sh <start|stop|stop-all|status|list|refresh> [args]" >&2
    echo "  start \"agent\" \"session-id\"  - Register agent for session" >&2
    echo "  stop \"session-id\"            - Remove agent for session" >&2
    echo "  stop-all                      - Remove all agent sessions" >&2
    echo "  status                        - Get agent for session (reads JSON stdin)" >&2
    echo "  list                          - List all active sessions" >&2
    echo "  refresh \"session-id\"         - Re-output persona after theme change" >&2
    exit 1
    ;;
esac
