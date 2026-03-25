#!/usr/bin/env zsh
# File locking utilities for session file concurrency protection
# Dev: Fanny Price - "We have all a better guide in ourselves."

# Default timeout in seconds
DEFAULT_LOCK_TIMEOUT=10

# Stale lock threshold in seconds (5 minutes)
STALE_LOCK_THRESHOLD=300

# _get_lock_dir
# Internal function to get lock directory (evaluated at call time)
_get_lock_dir() {
    echo "${PROJECT_ROOT:-.}/.session/.locks"
}

# _get_lock_file FILEPATH
# Internal function to derive lock file path from target file
#
# Arguments:
#   FILEPATH - Path to the file to lock
#
# Returns:
#   Outputs the lock file path
#
_get_lock_file() {
    local filepath="$1"
    local filename
    local lock_dir
    filename=$(basename "$filepath")
    lock_dir=$(_get_lock_dir)
    echo "${lock_dir}/.${filename}.lock"
}

# _check_stale_lock LOCKFILE
# Internal function to check and remove stale locks
#
# Arguments:
#   LOCKFILE - Path to lock file to check
#
# Returns:
#   0 if lock was stale and removed, 1 if lock is valid
#
_check_stale_lock() {
    local lockfile="$1"

    if [[ ! -f "$lockfile" ]]; then
        return 1
    fi

    # Get lock file age in seconds
    local now lock_mtime age
    now=$(date +%s)

    # macOS stat vs Linux stat differ
    if [[ "$(uname)" == "Darwin" ]]; then
        lock_mtime=$(stat -f %m "$lockfile" 2>/dev/null || echo 0)
    else
        lock_mtime=$(stat -c %Y "$lockfile" 2>/dev/null || echo 0)
    fi

    age=$((now - lock_mtime))

    if ((age > STALE_LOCK_THRESHOLD)); then
        # Log warning about stale lock
        echo "[WARN] Removing stale lock: $lockfile (age: ${age}s)" >&2
        rm -f "$lockfile"
        return 0
    fi

    return 1
}

# lock_acquire FILEPATH [LOCK_TYPE] [TIMEOUT]
# Acquire a lock on a file
#
# Arguments:
#   FILEPATH  - Path to the file to lock
#   LOCK_TYPE - "exclusive" (default) or "shared"
#   TIMEOUT   - Timeout in seconds (default: 10)
#
# Returns:
#   0 on success, 1 on timeout/failure
#
# Example:
#   lock_acquire ".session/checkpoints.log"
#   lock_acquire ".session/agent-logs.jsonl" "exclusive" 5
#
lock_acquire() {
    local filepath="$1"
    local lock_type="${2:-exclusive}"
    local timeout="${3:-$DEFAULT_LOCK_TIMEOUT}"
    local lockfile
    local flock_opts
    local start_time
    local elapsed

    lockfile=$(_get_lock_file "$filepath")
    local lock_dir
    lock_dir=$(_get_lock_dir)

    # Ensure lock directory exists
    mkdir -p "$lock_dir"

    # Check for stale lock first (ignore return value)
    _check_stale_lock "$lockfile" || true

    # Set flock options based on lock type
    case "$lock_type" in
        shared)
            flock_opts="-s"
            ;;
        exclusive|*)
            flock_opts="-x"
            ;;
    esac

    # Try to acquire lock with timeout
    start_time=$(date +%s)
    local my_pid="$$"

    while true; do
        # Try to create lock file atomically using ln (atomic on POSIX)
        # Create a temp file with our PID, then try to hard-link it
        local temp_lock="${lockfile}.${my_pid}"
        echo "$my_pid" > "$temp_lock"

        if ln "$temp_lock" "$lockfile" 2>/dev/null; then
            rm -f "$temp_lock"
            return 0
        fi
        rm -f "$temp_lock"

        # Check if we've exceeded timeout
        elapsed=$(( $(date +%s) - start_time ))
        if ((elapsed >= timeout)); then
            echo "[WARN] Lock timeout on $filepath after ${timeout}s" >&2
            return 1
        fi

        # Check for stale lock
        if _check_stale_lock "$lockfile" 2>/dev/null; then
            continue  # Try again now that stale lock is removed
        fi

        # Wait a bit before retrying (100ms)
        sleep 0.1
    done
}

# lock_release FILEPATH
# Release a lock on a file
#
# Arguments:
#   FILEPATH - Path to the file to unlock
#
# Returns:
#   0 on success
#
# Example:
#   lock_release ".session/checkpoints.log"
#
lock_release() {
    local filepath="$1"
    local lockfile

    lockfile=$(_get_lock_file "$filepath")

    # Only remove if we own the lock (PID matches)
    if [[ -f "$lockfile" ]]; then
        local lock_pid
        lock_pid=$(cat "$lockfile" 2>/dev/null || echo "")
        if [[ "$lock_pid" == "$$" ]]; then
            rm -f "$lockfile"
        fi
    fi

    return 0
}

# with_lock FILEPATH LOCK_TYPE COMMAND...
# Execute a command while holding a lock
#
# Arguments:
#   FILEPATH  - Path to the file to lock
#   LOCK_TYPE - "exclusive" or "shared"
#   COMMAND   - Command and arguments to execute
#
# Returns:
#   Exit code of the command, or 1 if lock failed
#
# Example:
#   with_lock ".session/checkpoints.log" "exclusive" echo "data" >> file
#   with_lock ".session/data.json" "shared" cat file
#
with_lock() {
    local filepath="$1"
    local lock_type="$2"
    shift 2

    if ! lock_acquire "$filepath" "$lock_type"; then
        return 1
    fi

    # Execute command and capture exit code
    local exit_code
    "$@"
    exit_code=$?

    lock_release "$filepath"

    return $exit_code
}

# lock_status FILEPATH
# Check if a file is currently locked
#
# Arguments:
#   FILEPATH - Path to the file to check
#
# Returns:
#   0 if locked, 1 if not locked
#   Outputs lock holder PID if locked
#
# Example:
#   if lock_status ".session/checkpoints.log"; then
#       echo "File is locked"
#   fi
#
lock_status() {
    local filepath="$1"
    local lockfile

    lockfile=$(_get_lock_file "$filepath")

    if [[ -f "$lockfile" ]]; then
        # Check for stale lock
        if _check_stale_lock "$lockfile"; then
            return 1
        fi
        cat "$lockfile"
        return 0
    fi

    return 1
}

# lock_cleanup
# Remove all stale locks in the lock directory
#
# Example:
#   lock_cleanup
#
lock_cleanup() {
    local lock_dir
    lock_dir=$(_get_lock_dir)

    if [[ ! -d "$lock_dir" ]]; then
        return 0
    fi

    local lockfile
    for lockfile in "$lock_dir"/.*.lock; do
        [[ -f "$lockfile" ]] || continue
        _check_stale_lock "$lockfile"
    done
}

# Functions available when sourced
