#!/usr/bin/env zsh
# Structured JSON logging utilities for agent workflows
# Dev: Fanny Price - "Let other pens dwell on guilt and misery."

# Source file locking utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=file-lock.sh
source "${SCRIPT_DIR}/file-lock.sh" 2>/dev/null || true

# Log file location (evaluated dynamically)
_get_log_file() {
    echo "${PROJECT_ROOT:-.}/.session/agent-logs.jsonl"
}

# _log LEVEL MESSAGE [EXTRA_FIELDS]
# Internal function to write structured log entry
#
# Arguments:
#   LEVEL        - Log level (INFO, WARN, ERROR)
#   MESSAGE      - Log message
#   EXTRA_FIELDS - Optional extra JSON fields (must be valid JSON object contents)
#
_log() {
    local level="$1"
    local message="$2"
    local extra="${3:-}"
    local timestamp
    local agent
    local session
    local log_file

    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    agent="${AGENT_NAME:-unknown}"
    session="${SESSION_ID:-}"
    log_file=$(_get_log_file)

    # Ensure directory exists
    mkdir -p "$(dirname "$log_file")"

    # Escape message for JSON (handle quotes and newlines)
    message=$(printf '%s' "$message" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g' | tr '\n' ' ')

    # Build JSON object
    local json="{\"timestamp\":\"${timestamp}\",\"level\":\"${level}\",\"agent\":\"${agent}\",\"message\":\"${message}\""

    # Add session_id if present
    if [[ -n "$session" ]]; then
        json="${json},\"session_id\":\"${session}\""
    fi

    # Add extra fields if provided
    if [[ -n "$extra" ]]; then
        json="${json},${extra}"
    fi

    json="${json}}"

    # Acquire lock, write to log file, release lock
    if lock_acquire "$log_file" "exclusive" 5 2>/dev/null; then
        echo "$json" >> "$log_file"
        lock_release "$log_file"
    else
        # Fallback: write without lock (better than failing)
        echo "$json" >> "$log_file"
    fi

    # Also output to stderr for visibility (with color)
    case "$level" in
        INFO)  echo -e "\033[32m[INFO]\033[0m $message" >&2 ;;
        WARN)  echo -e "\033[33m[WARN]\033[0m $message" >&2 ;;
        ERROR) echo -e "\033[31m[ERROR]\033[0m $message" >&2 ;;
    esac
}

# log_info MESSAGE [EXTRA_FIELDS]
# Log an informational message
#
# Arguments:
#   MESSAGE      - Log message
#   EXTRA_FIELDS - Optional extra JSON fields
#
# Example:
#   log_info "Starting workflow"
#   log_info "File processed" '"file":"src/main.go","lines":42'
#
log_info() {
    _log "INFO" "$1" "${2:-}"
}

# log_warn MESSAGE [EXTRA_FIELDS]
# Log a warning message
#
# Arguments:
#   MESSAGE      - Log message
#   EXTRA_FIELDS - Optional extra JSON fields
#
# Example:
#   log_warn "Context usage high"
#   log_warn "Retry needed" '"attempt":2,"max":3'
#
log_warn() {
    _log "WARN" "$1" "${2:-}"
}

# log_error MESSAGE [EXTRA_FIELDS]
# Log an error message
#
# Arguments:
#   MESSAGE      - Log message
#   EXTRA_FIELDS - Optional extra JSON fields
#
# Example:
#   log_error "Command failed"
#   log_error "Test failure" '"test":"test_auth","exit_code":1'
#
log_error() {
    _log "ERROR" "$1" "${2:-}"
}

# log_list [N]
# List recent log entries
#
# Arguments:
#   N - Number of entries to show (default: 20)
#
# Example:
#   log_list
#   log_list 50
#
log_list() {
    local count=${1:-20}
    local log_file
    log_file=$(_get_log_file)

    if [[ -f "$log_file" ]]; then
        tail -n "$count" "$log_file"
    fi
}

# log_clear
# Remove all log entries
#
# Example:
#   log_clear
#
log_clear() {
    local log_file
    log_file=$(_get_log_file)
    rm -f "$log_file"
}

# log_rotate [MAX_LINES]
# Rotate log file to prevent unbounded growth
#
# Arguments:
#   MAX_LINES - Maximum lines to keep (default: 1000)
#
# Example:
#   log_rotate
#   log_rotate 500
#
log_rotate() {
    local max_lines=${1:-1000}
    local log_file
    log_file=$(_get_log_file)

    if [[ ! -f "$log_file" ]]; then
        return 0
    fi

    # Acquire exclusive lock for rotation
    if lock_acquire "$log_file" "exclusive" 5 2>/dev/null; then
        local current_lines
        current_lines=$(wc -l < "$log_file")

        if ((current_lines > max_lines)); then
            local temp_file
            temp_file=$(mktemp)
            tail -n "$max_lines" "$log_file" > "$temp_file"
            mv "$temp_file" "$log_file"
        fi
        lock_release "$log_file"
    fi
}

# Functions available when sourced
