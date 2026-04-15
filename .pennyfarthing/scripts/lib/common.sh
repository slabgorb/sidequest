#!/usr/bin/env zsh
# Common utility functions for Pennyfarthing scripts
# Source this file: source "${SCRIPT_DIR}/lib/common.sh"
#
# Provides:
#   - Output helpers: success, info, warn, error
#   - Dry-run check: dry_run_check
#   - JQL escaping: escape_for_jql
#   - Jira JSON helpers: get_issue_json, get_jira_field

#############################################
# Output Helpers
#############################################

# Color codes
_RED='\033[31m'
_GREEN='\033[32m'
_YELLOW='\033[33m'
_BLUE='\033[34m'
_NC='\033[0m'  # No Color

# success MESSAGE
# Print a success message in green (to stderr for visibility)
success() {
    echo -e "${_GREEN}[OK]${_NC} $1" >&2
}

# info MESSAGE
# Print an info message in blue (to stderr for visibility)
info() {
    echo -e "${_BLUE}[INFO]${_NC} $1" >&2
}

# warn MESSAGE
# Print a warning message in yellow (to stderr for visibility)
warn() {
    echo -e "${_YELLOW}[WARN]${_NC} $1" >&2
}

# error MESSAGE
# Print an error message in red (to stderr, does NOT exit)
error() {
    echo -e "${_RED}[ERROR]${_NC} $1" >&2
}

#############################################
# Dry-Run Support
#############################################

# dry_run_check ACTION
# Check if DRY_RUN is enabled and print a warning
# Returns 0 if dry-run is active (caller should skip the action)
# Returns 1 if dry-run is NOT active (caller should proceed)
#
# Usage:
#   if dry_run_check "create epic: $summary"; then
#       echo "DRYRUN-EPIC-001"
#       return
#   fi
#   # ... actual implementation
#
dry_run_check() {
    local action="$1"
    if [ "$DRY_RUN" = true ]; then
        warn "[DRY-RUN] Would ${action}"
        return 0
    fi
    return 1
}

#############################################
# JQL Helpers
#############################################

# escape_for_jql STRING
# Escape a string for use in JQL queries
# Escapes double quotes and other special characters
#
# Usage:
#   local escaped=$(escape_for_jql "$summary")
#   jira issue list --jql "summary~'${escaped}'"
#
escape_for_jql() {
    echo "$1" | sed 's/"/\\"/g'
}

#############################################
# Jira JSON Helpers
#############################################

# get_issue_json ISSUE_KEY
# Fetch Jira issue as JSON with error handling
# Returns empty object {} if issue not found
# Sets exit code 1 if fetch failed
#
# Usage:
#   local json=$(get_issue_json "PROJ-123")
#   if [ -z "$json" ] || [ "$json" = "{}" ]; then
#       warn "Could not fetch issue"
#   fi
#
get_issue_json() {
    local key="$1"
    local json
    json=$(jira issue view "$key" --raw 2>/dev/null)
    if [ -z "$json" ]; then
        echo "{}"
        return 1
    fi
    echo "$json"
}

# get_jira_field JSON FIELD_PATH [DEFAULT]
# Extract a field from Jira issue JSON using jq
#
# Arguments:
#   JSON        - The JSON string to parse
#   FIELD_PATH  - jq path expression (e.g., '.fields.summary')
#   DEFAULT     - Optional default value if field is null/empty
#
# Usage:
#   local summary=$(get_jira_field "$json" '.fields.summary')
#   local points=$(get_jira_field "$json" '.fields.customfield_10031' '0')
#
get_jira_field() {
    local json="$1"
    local field_path="$2"
    local default="${3:-}"

    if [ -n "$default" ]; then
        echo "$json" | jq -r "${field_path} // \"${default}\""
    else
        echo "$json" | jq -r "${field_path} // empty"
    fi
}

#############################################
# Dependency Checks
#############################################

# check_dependencies
# Check for common required tools
# Can be extended with optional checks
check_dependencies() {
    local missing=()

    # Check for jq (required for JSON parsing)
    if ! command -v jq &> /dev/null; then
        missing+=("jq")
        error "jq not found - install with: brew install jq"
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        return 1
    fi
    return 0
}

#############################################
# Python Execution
#############################################

# get_python
# Find the best Python interpreter (venv preferred, fallback to system)
# Sets PYTHON_CMD variable
#
# Priority:
#   1. PROJECT_ROOT/.venv/bin/python (project venv)
#   2. python3 (system)
#   3. python (legacy fallback)
#
# Usage:
#   get_python
#   $PYTHON_CMD -m pf.jira view <PROJECT-KEY>
#
get_python() {
    # Find project root if not set
    if [[ -z "${PROJECT_ROOT:-}" ]]; then
        local d="$PWD"
        while [[ ! -d "$d/.pennyfarthing" ]] && [[ "$d" != "/" ]]; do
            d="$(dirname "$d")"
        done
        PROJECT_ROOT="$d"
    fi

    # Check for project venv first
    if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
        PYTHON_CMD="${PROJECT_ROOT}/.venv/bin/python"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        error "Python not found. Install Python 3.11+ or create .venv"
        return 1
    fi
}

# run_python_module MODULE [ARGS...]
# Run a pf Python module with proper venv handling
#
# Usage:
#   run_python_module jira view <PROJECT-KEY>
#   run_python_module sprint status
#   run_python_module story size 3
#
run_python_module() {
    get_python || return 1
    local module="$1"
    shift
    exec $PYTHON_CMD -m "pf.${module}" "$@"
}
