#!/usr/bin/env zsh
# Retry utilities with exponential backoff
# Dev: Fanny Price - "We have all a better guide in ourselves, if we would attend to it."

# retry_with_backoff MAX_ATTEMPTS INITIAL_DELAY MAX_DELAY COMMAND...
# Retry a command with exponential backoff
#
# Arguments:
#   MAX_ATTEMPTS   - Maximum number of attempts (default: 3)
#   INITIAL_DELAY  - Initial delay in seconds (default: 1)
#   MAX_DELAY      - Maximum delay cap in seconds (default: 30)
#   COMMAND...     - Command to execute
#
# Returns:
#   0 if command succeeds within attempts
#   1 if all attempts exhausted
#
# Example:
#   retry_with_backoff 3 1 10 curl -s https://api.example.com/health
#
retry_with_backoff() {
    local max_attempts=${1:-3}
    local delay=${2:-1}
    local max_delay=${3:-30}
    shift 3

    local attempt=1
    while true; do
        # Try the command
        if "$@"; then
            return 0
        fi

        # Check if we've exhausted attempts
        if ((attempt >= max_attempts)); then
            return 1
        fi

        # Wait before retry
        sleep "$delay"

        # Exponential backoff with cap
        delay=$((delay * 2))
        if ((delay > max_delay)); then
            delay=$max_delay
        fi

        attempt=$((attempt + 1))
    done
}

# command_with_fallback PRIMARY_CMD FALLBACK_CMD
# Execute primary command, fall back to alternative if it fails
#
# Arguments:
#   PRIMARY_CMD   - Primary command to try (as string)
#   FALLBACK_CMD  - Fallback command if primary fails (as string)
#
# Returns:
#   Exit code of whichever command succeeds (or fallback's exit code)
#
# Example:
#   command_with_fallback "git pull --ff-only" "git pull --no-rebase"
#
command_with_fallback() {
    local primary_cmd="$1"
    local fallback_cmd="$2"

    if eval "$primary_cmd"; then
        return 0
    else
        eval "$fallback_cmd"
    fi
}

# Functions available when sourced - no export needed in zsh
