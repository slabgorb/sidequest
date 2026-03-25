#!/usr/bin/env zsh
# Pennyfarthing Repo Scanning Utilities
# Provides functions for scanning git status and PRs across repos
#
# Usage: source scripts/utils/repo-scan.sh
#
# Functions:
#   scan_repo_git_status REPO  - Get git status for a repo (repo|branch|uncommitted|ahead)
#   scan_all_repos_status      - Get git status for all configured repos
#   check_repo_pr REPO BRANCH  - Check for open PR on branch (returns URL or "none")

# Don't exit on error - we want to handle errors gracefully
set +e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Source repo-utils for multi-repo iteration
source "$CLAUDE_PROJECT_DIR/scripts/repo-utils.sh" 2>/dev/null || true

# ============================================================================
# Git Status Functions
# ============================================================================

# Scan git status for a single repo
# Returns: repo|branch|uncommitted_count|ahead_count
scan_repo_git_status() {
    local repo="$1"
    local repo_path

    # Handle both repo name (from config) and direct path
    if [[ -d "$CLAUDE_PROJECT_DIR/$repo" ]]; then
        repo_path="$CLAUDE_PROJECT_DIR/$repo"
    elif declare -f get_repo_path &>/dev/null; then
        repo_path=$(get_repo_full_path "$repo" 2>/dev/null)
    else
        repo_path="$CLAUDE_PROJECT_DIR/$repo"
    fi

    # If repo path doesn't exist, try PROJECT_ROOT itself (for pennyfarthing)
    if [[ ! -d "$repo_path/.git" && -d "$CLAUDE_PROJECT_DIR/.git" && "$repo" == "pennyfarthing" ]]; then
        repo_path="$CLAUDE_PROJECT_DIR"
    fi

    if [[ ! -d "$repo_path" ]]; then
        echo "$repo|||"
        return 1
    fi

    local branch uncommitted ahead

    # Get current branch
    branch=$(git -C "$repo_path" branch --show-current 2>/dev/null || echo "")

    # Count uncommitted changes (staged + unstaged + untracked)
    uncommitted=$(git -C "$repo_path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

    # Count commits ahead of upstream
    ahead=$(git -C "$repo_path" rev-list --count @{u}..HEAD 2>/dev/null || echo "0")

    echo "$repo|$branch|$uncommitted|$ahead"
}

# Scan git status for all configured repos
# Returns: one line per repo in scan_repo_git_status format
scan_all_repos_status() {
    # If repo-utils is available, use it
    if declare -f get_repos &>/dev/null; then
        for repo in $(get_repos); do
            scan_repo_git_status "$repo"
        done
    else
        # Fallback: scan common repo patterns
        for dir in "$CLAUDE_PROJECT_DIR"/*; do
            if [[ -d "$dir/.git" ]]; then
                local repo_name
                repo_name=$(basename "$dir")
                scan_repo_git_status "$repo_name"
            fi
        done

        # Also check PROJECT_ROOT itself
        if [[ -d "$CLAUDE_PROJECT_DIR/.git" ]]; then
            local root_name
            root_name=$(basename "$CLAUDE_PROJECT_DIR")
            scan_repo_git_status "$root_name"
        fi
    fi
}

# ============================================================================
# PR Functions
# ============================================================================

# Check for open PR on a branch
# Returns: PR URL or "none"
check_repo_pr() {
    local repo="$1"
    local branch="$2"
    local repo_path

    # Handle both repo name (from config) and direct path
    if [[ -d "$CLAUDE_PROJECT_DIR/$repo" ]]; then
        repo_path="$CLAUDE_PROJECT_DIR/$repo"
    elif declare -f get_repo_path &>/dev/null; then
        repo_path=$(get_repo_full_path "$repo" 2>/dev/null)
    else
        repo_path="$CLAUDE_PROJECT_DIR/$repo"
    fi

    # If repo path doesn't exist, try PROJECT_ROOT itself
    if [[ ! -d "$repo_path/.git" && -d "$CLAUDE_PROJECT_DIR/.git" && "$repo" == "pennyfarthing" ]]; then
        repo_path="$CLAUDE_PROJECT_DIR"
    fi

    if [[ ! -d "$repo_path" ]]; then
        echo "none"
        return 0
    fi

    # Check if branch exists
    if ! git -C "$repo_path" rev-parse --verify "$branch" &>/dev/null; then
        echo "none"
        return 0
    fi

    # Check for open PR using gh CLI
    if command -v gh &>/dev/null; then
        local pr_url
        pr_url=$(cd "$repo_path" && gh pr view "$branch" --json url -q .url 2>/dev/null || echo "")
        if [[ -n "$pr_url" ]]; then
            echo "$pr_url"
        else
            echo "none"
        fi
    else
        echo "none"
    fi

    return 0
}
