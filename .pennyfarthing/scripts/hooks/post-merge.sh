#!/bin/bash
# post-merge.sh - Git hook for automatic sprint YAML updates after PR merge
# Story 8-1: Git Hook for PR Merge Detection
#
# This hook runs after git pull or git merge operations, detecting when a
# story branch is merged and automatically updating the sprint YAML status.
#
# Installation:
#   End-user projects: pf setup (copies to .git/hooks/)
#   Framework/orchestrator: install-git-hooks.sh (symlinks to pennyfarthing-dist/)
#
# Dependencies:
#   - yq (for YAML manipulation)
#   (sprint-common.sh removed — all functions defined locally)

set -uo pipefail

# Find project root
# Try find-root.sh via symlink resolution first, then fall back to .git location
REAL_SCRIPT="$(readlink -f "${BASH_SOURCE[0]:-$0}" 2>/dev/null || realpath "${BASH_SOURCE[0]:-$0}" 2>/dev/null || echo "${BASH_SOURCE[0]:-$0}")"
FIND_ROOT="$(dirname "$REAL_SCRIPT")/../lib/find-root.sh"
if [[ -f "$FIND_ROOT" ]]; then
    source "$FIND_ROOT"
else
    # Running as a copy in .git/hooks/ — derive PROJECT_ROOT from git dir
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
    export PROJECT_ROOT
fi
SESSION_DIR="$PROJECT_ROOT/.session"
SPRINT_FILE="$PROJECT_ROOT/sprint/current-sprint.yaml"

# Note: sprint-common.sh removed — all needed functions are defined locally below

# extract_story_id BRANCH_NAME
# Extract story ID from branch name pattern feat/X-Y-*
# Returns: X-Y (e.g., "8-1" from "feat/8-1-merge-detection")
# Returns empty for non-matching branches
extract_story_id() {
    local branch="$1"

    # Match pattern: feat/EPIC-STORY-description or feat/EPIC-STORY
    if [[ "$branch" =~ ^feat/([0-9]+-[0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
    # Returns empty string for non-matching patterns
}

# update_story_status STORY_ID NEW_STATUS
# Update story status in sprint YAML and add completed date
# Handles both inline stories in current-sprint.yaml and sharded epic files
update_story_status() {
    local story_id="$1"
    local new_status="${2:-done}"
    local completed_date
    completed_date=$(date +%Y-%m-%d)

    if [[ ! -f "$SPRINT_FILE" ]]; then
        return 1
    fi

    if ! command -v yq &>/dev/null; then
        echo "Warning: yq not found, cannot update sprint YAML" >&2
        return 1
    fi

    local sprint_dir
    sprint_dir="$(dirname "$SPRINT_FILE")"

    # Try inline stories in current-sprint.yaml first
    yq eval -i "
        (.stories[] | select(.id == \"$story_id\")).status = \"$new_status\" |
        (.stories[] | select(.id == \"$story_id\")).completed = \"$completed_date\"
    " "$SPRINT_FILE" 2>/dev/null

    # Also try each epic shard file
    for shard in "$sprint_dir"/epic-*.yaml; do
        [[ -f "$shard" ]] || continue
        if yq eval ".stories[] | select(.id == \"$story_id\")" "$shard" 2>/dev/null | grep -q "$story_id"; then
            yq eval -i "
                (.stories[] | select(.id == \"$story_id\")).status = \"$new_status\" |
                (.stories[] | select(.id == \"$story_id\")).completed = \"$completed_date\"
            " "$shard"
            return $?
        fi
    done

    return 0
}

# log_reconciliation STORY_ID MESSAGE
# Log reconciliation event to .session/ directory
log_reconciliation() {
    local story_id="$1"
    local message="${2:-Merge detected}"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    # Ensure session directory exists
    mkdir -p "$SESSION_DIR"

    local log_file="$SESSION_DIR/reconciliation.log"

    echo "[$timestamp] Story $story_id: $message" >> "$log_file"
}

# Main hook logic
main() {
    # Get the current branch after merge
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

    # Only process if we're on develop or main (after a PR merge)
    if [[ "$current_branch" != "develop" && "$current_branch" != "main" ]]; then
        exit 0
    fi

    # Get the branches that were just merged
    # The reflog shows what was merged: the previous HEAD and the merged commit
    local merged_refs
    merged_refs=$(git reflog -1 --format='%gs' 2>/dev/null)

    # Check if this was a merge operation
    if [[ ! "$merged_refs" =~ merge ]]; then
        # Could be a pull with fast-forward - check for merged branches
        # Look at recently merged branches by checking merge commits
        :
    fi

    # Find recently merged feature branches by examining merge commits
    local merge_commits
    merge_commits=$(git log --merges --oneline -10 --since="5 minutes ago" 2>/dev/null)

    # Extract branch names from merge commits
    while IFS= read -r commit_line; do
        # Parse "Merge pull request #X from user/feat/X-Y-description"
        # or "Merge branch 'feat/X-Y-description'"
        local branch_name=""

        if [[ "$commit_line" =~ feat/([0-9]+-[0-9]+[a-zA-Z0-9-]*) ]]; then
            branch_name="feat/${BASH_REMATCH[1]}"
        fi

        if [[ -n "$branch_name" ]]; then
            local story_id
            story_id=$(extract_story_id "$branch_name")

            if [[ -n "$story_id" ]]; then
                # Update sprint YAML
                if update_story_status "$story_id" "done"; then
                    log_reconciliation "$story_id" "Status updated to 'done' after merge (branch: $branch_name)"
                else
                    log_reconciliation "$story_id" "Failed to update status (branch: $branch_name)"
                fi
            fi
        fi
    done <<< "$merge_commits"
}

# Auto-update pf CLI to use this repo's source after pull
update_pf_cli() {
    # Only act if pipx manages pf and pennyfarthing-dist exists here
    if ! command -v pipx &>/dev/null; then
        return 0
    fi

    local dist_dir="$PROJECT_ROOT/pennyfarthing-dist"
    [[ -d "$dist_dir" ]] || return 0

    # Check if pyproject.toml or pf source changed in this merge
    local changed_files
    changed_files=$(git diff --name-only HEAD@{1}..HEAD 2>/dev/null || true)
    local needs_reinstall=false

    if echo "$changed_files" | grep -q "pennyfarthing-dist/pyproject.toml\|pennyfarthing-dist/src/pf"; then
        needs_reinstall=true
    fi

    # Also reinstall if pf currently points at a different location
    if [[ "$needs_reinstall" == "false" ]]; then
        local pkg_location
        pkg_location=$(pipx runpip pennyfarthing-scripts show pennyfarthing-scripts 2>/dev/null \
            | grep -E "^Location:" | awk '{print $NF}')
        # If it's an editable install or points elsewhere, force reinstall
        if pipx runpip pennyfarthing-scripts show pennyfarthing-scripts 2>/dev/null \
            | grep -q "Editable project location"; then
            needs_reinstall=true
        fi
    fi

    if [[ "$needs_reinstall" == "false" ]]; then
        return 0
    fi

    # Non-editable install in background so it doesn't block git operations
    echo "Updating pf CLI in background..."
    (pipx install "$dist_dir" --force >/dev/null 2>&1 || {
        echo "Warning: pf CLI update failed (pipx install $dist_dir)" >&2
    }) &
}

# Only run main when executed directly (not when sourced for testing)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    update_pf_cli
fi
