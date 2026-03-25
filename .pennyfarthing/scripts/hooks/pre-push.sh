#!/bin/bash
# pre-push.sh - Git hook to remind about Jira sync before push
#
# Checks if sprint files were modified and reminds to sync to Jira.
#
# Installation:
#   End-user projects: pf setup (copies to .git/hooks/)
#   Framework/orchestrator: install-git-hooks.sh (symlinks to pennyfarthing-dist/)

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

SPRINT_FILE="$PROJECT_ROOT/sprint/current-sprint.yaml"

# Check if there are uncommitted changes to sprint file
if git diff --name-only | grep -q "sprint/current-sprint.yaml"; then
    echo "Warning: current-sprint.yaml has uncommitted changes"
    echo "   Consider committing before pushing"
    echo ""
fi

# Get the range of commits being pushed
REMOTE="$1"
URL="$2"

while read local_ref local_sha remote_ref remote_sha; do
    if [ "$local_sha" != "0000000000000000000000000000000000000000" ]; then
        # Check if sprint file changed in this push
        if git diff --name-only "$remote_sha..$local_sha" 2>/dev/null | grep -q "sprint/current-sprint.yaml"; then
            echo "Sprint changes detected in push"
            echo "   Reminder: Sync to Jira if story statuses changed"
            echo ""
        fi
    fi
done

exit 0
