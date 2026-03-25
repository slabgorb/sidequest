#!/usr/bin/env zsh
# Session checkpointing utilities
# Dev: Fanny Price - "I was quiet, but I was not blind."

# Source file locking utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=file-lock.sh
source "${SCRIPT_DIR}/file-lock.sh" 2>/dev/null || true

# Checkpoint file location (evaluated dynamically)
_get_checkpoint_file() {
    echo "${PROJECT_ROOT:-.}/.session/checkpoints.log"
}

# checkpoint_save LABEL DATA
# Save a checkpoint with timestamp
#
# Arguments:
#   LABEL - Identifier for this checkpoint
#   DATA  - Data to save (string)
#
# Format: ISO_TIMESTAMP|LABEL|DATA
#
# Example:
#   checkpoint_save "story_phase" "dev"
#   checkpoint_save "last_file" "src/main.go:42"
#
checkpoint_save() {
    local label="$1"
    local data="$2"
    local timestamp
    local checkpoint_file
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    checkpoint_file=$(_get_checkpoint_file)

    # Ensure directory exists
    mkdir -p "$(dirname "$checkpoint_file")"

    # Acquire exclusive lock, append checkpoint, release lock
    if lock_acquire "$checkpoint_file" "exclusive" 5 2>/dev/null; then
        echo "${timestamp}|${label}|${data}" >> "$checkpoint_file"
        lock_release "$checkpoint_file"
    else
        # Fallback: append without lock (better than failing)
        echo "${timestamp}|${label}|${data}" >> "$checkpoint_file"
    fi
}

# checkpoint_restore LABEL
# Restore the most recent checkpoint with given label
#
# Arguments:
#   LABEL - Identifier to look up
#
# Returns:
#   Outputs the data portion of the most recent matching checkpoint
#   Empty if no match found
#
# Example:
#   phase=$(checkpoint_restore "story_phase")
#
checkpoint_restore() {
    local label="$1"
    local checkpoint_file
    checkpoint_file=$(_get_checkpoint_file)

    if [[ ! -f "$checkpoint_file" ]]; then
        return 0
    fi

    # Find entries with matching label, take the last one, extract data field
    # Use || true to handle case where grep finds no matches
    grep "|${label}|" "$checkpoint_file" 2>/dev/null | tail -1 | cut -d'|' -f3- || true
}

# checkpoint_list
# List recent checkpoints (last 20)
#
# Example:
#   checkpoint_list
#
checkpoint_list() {
    local checkpoint_file
    checkpoint_file=$(_get_checkpoint_file)

    if [[ -f "$checkpoint_file" ]]; then
        tail -20 "$checkpoint_file"
    fi
}

# checkpoint_clear
# Remove all checkpoints
#
# Example:
#   checkpoint_clear
#
checkpoint_clear() {
    local checkpoint_file
    checkpoint_file=$(_get_checkpoint_file)
    rm -f "$checkpoint_file"
}

# checkpoint_rotate MAX_LINES
# Rotate checkpoint file to prevent unbounded growth
#
# Arguments:
#   MAX_LINES - Maximum lines to keep (default: 1000)
#
# Example:
#   checkpoint_rotate 500
#
checkpoint_rotate() {
    local max_lines=${1:-1000}
    local checkpoint_file
    checkpoint_file=$(_get_checkpoint_file)

    if [[ ! -f "$checkpoint_file" ]]; then
        return 0
    fi

    # Acquire exclusive lock for rotation
    if lock_acquire "$checkpoint_file" "exclusive" 5 2>/dev/null; then
        local current_lines
        current_lines=$(wc -l < "$checkpoint_file")

        if ((current_lines > max_lines)); then
            local temp_file
            temp_file=$(mktemp)
            tail -n "$max_lines" "$checkpoint_file" > "$temp_file"
            mv "$temp_file" "$checkpoint_file"
        fi
        lock_release "$checkpoint_file"
    fi
}

# Functions available when sourced
