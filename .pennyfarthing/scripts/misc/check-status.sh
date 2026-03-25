#!/usr/bin/env zsh
# Enhanced multi-repo git status with color and summaries
# Usage: ./check-status.sh [repos]

set -e

# Load environment
if [ -f .env ]; then
    set -a; source .env; set +a
elif [ -f ../.env ]; then
    set -a; source ../.env; set +a
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

show_help() {
    cat << 'EOF'
Check Status - Enhanced multi-repo status

Usage: ./check-status.sh [repos]

Arguments:
  repos    Which repos to check (default: all)
           Options: api, ui, all

Features:
  - Color-coded status output
  - Shows uncommitted changes
  - Shows unpushed commits
  - Shows branch sync status
  - Summary of all repos
  - Highlights issues requiring attention
  - Worktree-aware

Examples:
  # Check all repos
  ./check-status.sh

  # Check specific repo
  ./check-status.sh api

EOF
}

REPOS="all"

# Parse arguments
for arg in "$@"; do
    case $arg in
        -h|--help)
            show_help
            exit 0
            ;;
        api|ui|all)
            REPOS="$arg"
            ;;
        *)
            echo "❌ Unknown argument: $arg"
            show_help
            exit 1
            ;;
    esac
done

# Detect if we're in a worktree
CURRENT_DIR=$(pwd)
if [[ "$CURRENT_DIR" == *"/worktrees/"* ]]; then
    WORKTREE_NAME=$(echo "$CURRENT_DIR" | sed -E 's|.*/worktrees/([^/]+).*|\1|')
    REPO_BASE="$PROJECT_ROOT/worktrees/$WORKTREE_NAME"
    echo -e "${CYAN}📂 Worktree: $WORKTREE_NAME${NC}"
else
    REPO_BASE="$PROJECT_ROOT"
    echo -e "${CYAN}📂 Main checkout${NC}"
fi

declare -a CLEAN_REPOS=()
declare -a DIRTY_REPOS=()
declare -a AHEAD_REPOS=()
declare -a BEHIND_REPOS=()

# Check status of a repo
check_repo_status() {
    local repo_path=$1
    local repo_name=$2

    if [ ! -d "$repo_path" ]; then
        return
    fi

    cd "$repo_path"

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📦 $repo_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Get current branch
    CURRENT_BRANCH=$(git branch --show-current)

    if [ -z "$CURRENT_BRANCH" ]; then
        echo -e "   ${RED}⚠️  Detached HEAD${NC}"
        return
    fi

    echo -e "   Branch: ${CYAN}$CURRENT_BRANCH${NC}"

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        echo -e "   Status: ${YELLOW}⚠️  Uncommitted changes${NC}"
        DIRTY_REPOS+=("$repo_name")

        # Show what's changed
        MODIFIED=$(git diff --name-only | wc -l | tr -d ' ')
        STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')

        if [ "$STAGED" -gt 0 ]; then
            echo -e "   ${GREEN}Staged: $STAGED files${NC}"
        fi
        if [ "$MODIFIED" -gt 0 ]; then
            echo -e "   ${YELLOW}Modified: $MODIFIED files${NC}"
        fi

        # Show short status
        echo ""
        git status --short | sed 's/^/   /'
    else
        echo -e "   Status: ${GREEN}✓ Clean${NC}"
        CLEAN_REPOS+=("$repo_name")
    fi

    # Check remote tracking
    UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "none")

    if [ "$UPSTREAM" = "none" ]; then
        echo -e "   Remote: ${YELLOW}⚠️  Not tracking remote${NC}"
    else
        echo -e "   Remote: ${CYAN}$UPSTREAM${NC}"

        # Fetch to get latest remote info
        git fetch origin "$CURRENT_BRANCH" --quiet 2>/dev/null || true

        # Check sync status
        LOCAL=$(git rev-parse @ 2>/dev/null)
        REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "none")

        if [ "$REMOTE" = "none" ]; then
            echo -e "   Sync:   ${YELLOW}⚠️  No remote branch${NC}"
        elif [ "$LOCAL" = "$REMOTE" ]; then
            echo -e "   Sync:   ${GREEN}✓ Up to date${NC}"
        else
            AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")
            BEHIND=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo "0")

            if [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -gt 0 ]; then
                echo -e "   Sync:   ${RED}⚠️  Diverged ($AHEAD ahead, $BEHIND behind)${NC}"
            elif [ "$AHEAD" -gt 0 ]; then
                echo -e "   Sync:   ${YELLOW}⬆️  $AHEAD commit(s) ahead${NC}"
                AHEAD_REPOS+=("$repo_name ($AHEAD ahead)")
            elif [ "$BEHIND" -gt 0 ]; then
                echo -e "   Sync:   ${YELLOW}⬇️  $BEHIND commit(s) behind${NC}"
                BEHIND_REPOS+=("$repo_name ($BEHIND behind)")
            fi
        fi
    fi

    # Show last commit
    LAST_COMMIT=$(git log -1 --format="%h - %s" 2>/dev/null)
    echo -e "   Last:   ${CYAN}$LAST_COMMIT${NC}"
}

echo ""
echo "🔍 Checking repository status..."
echo "   Repos: $REPOS"

# Check repos
case "$REPOS" in
    api)
        check_repo_status "$REPO_BASE/Pennyfarthing-api" "Pennyfarthing-api"
        ;;
    ui)
        check_repo_status "$REPO_BASE/Pennyfarthing-ui" "Pennyfarthing-ui"
        ;;
    all)
        check_repo_status "$REPO_BASE/Pennyfarthing-api" "Pennyfarthing-api"
        check_repo_status "$REPO_BASE/Pennyfarthing-ui" "Pennyfarthing-ui"
        ;;
esac

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "📊 Summary"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ${#CLEAN_REPOS[@]} -gt 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Clean (${#CLEAN_REPOS[@]}):${NC}"
    for repo in "${CLEAN_REPOS[@]}"; do
        echo -e "   ${GREEN}✓${NC} $repo"
    done
fi

if [ ${#DIRTY_REPOS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Uncommitted Changes (${#DIRTY_REPOS[@]}):${NC}"
    for repo in "${DIRTY_REPOS[@]}"; do
        echo -e "   ${YELLOW}•${NC} $repo"
    done
fi

if [ ${#AHEAD_REPOS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⬆️  Ahead of Remote (${#AHEAD_REPOS[@]}):${NC}"
    for repo in "${AHEAD_REPOS[@]}"; do
        echo -e "   ${YELLOW}⬆${NC} $repo"
    done
    echo -e "   ${CYAN}Tip: Run ./scripts/commit-and-push.sh or git push${NC}"
fi

if [ ${#BEHIND_REPOS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⬇️  Behind Remote (${#BEHIND_REPOS[@]}):${NC}"
    for repo in "${BEHIND_REPOS[@]}"; do
        echo -e "   ${YELLOW}⬇${NC} $repo"
    done
    echo -e "   ${CYAN}Tip: Run git pull to update${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

TOTAL_REPOS=$((${#CLEAN_REPOS[@]} + ${#DIRTY_REPOS[@]}))

if [ ${#DIRTY_REPOS[@]} -eq 0 ] && [ ${#AHEAD_REPOS[@]} -eq 0 ] && [ ${#BEHIND_REPOS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All repositories are clean and in sync!${NC}"
else
    echo -e "${YELLOW}⚠️  ${#DIRTY_REPOS[@]} repo(s) with changes, ${#AHEAD_REPOS[@]} ahead, ${#BEHIND_REPOS[@]} behind${NC}"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
