#!/usr/bin/env zsh
# Pennyfarthing Release Script
# Merges develop to main and pushes both branches
#
# Usage: ./scripts/release.sh [OPTIONS]
#
# Options:
#   --bump <type>   Bump version before release (major|minor|patch)
#   --dry-run       Show what would happen without executing
#   --help          Show this help message
#
# Examples:
#   ./scripts/release.sh                    # Just merge and push
#   ./scripts/release.sh --bump patch       # Bump patch version, then release
#   ./scripts/release.sh --bump minor       # Bump minor version, then release
#   ./scripts/release.sh --dry-run          # Preview what would happen

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Use exported PROJECT_ROOT from find-root.sh, or detect it
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    _dir="$PWD"
    while [[ ! -d "$_dir/.pennyfarthing" ]] && [[ "$_dir" != "/" ]]; do
        _dir="$(dirname "$_dir")"
    done
    if [[ -d "$_dir/.pennyfarthing" ]]; then
        PROJECT_ROOT="$_dir"
    else
        PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    fi
fi

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DRY_RUN=false
BUMP_TYPE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --bump)
            BUMP_TYPE="$2"
            if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
                echo -e "${RED}[ERROR]${NC} Invalid bump type: $BUMP_TYPE"
                echo "Valid types: major, minor, patch"
                exit 1
            fi
            shift 2
            ;;
        --help|-h)
            head -20 "$0" | tail -18
            exit 0
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

run() {
    if $DRY_RUN; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $*"
    else
        "$@"
    fi
}

if $DRY_RUN; then
    echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# If bump requested, delegate to deploy.sh (which handles everything)
if [[ -n "$BUMP_TYPE" ]]; then
    info "Version bump requested: $BUMP_TYPE"

    # Run deploy.sh which handles version bump + full release
    # deploy.sh is in scripts/ (meta-only, not distributed)
    # This only works when running from the pennyfarthing repo itself
    #
    # Try to find deploy.sh relative to the script location first (for pennyfarthing repo)
    # then fall back to PROJECT_ROOT (for legacy compatibility)
    SCRIPT_PARENT="$(dirname "$(dirname "$SCRIPT_DIR")")"  # Go up from git/ to scripts/ to root
    if [[ -f "$SCRIPT_PARENT/../scripts/deploy.sh" ]]; then
        # We're in pennyfarthing-dist/scripts/git, so go up to repo root
        DEPLOY_SCRIPT="$(cd "$SCRIPT_PARENT/.." && pwd)/scripts/deploy.sh"
    elif [[ -f "$PROJECT_ROOT/scripts/deploy.sh" ]]; then
        DEPLOY_SCRIPT="$PROJECT_ROOT/scripts/deploy.sh"
    else
        error "deploy.sh not found"
        error "Version bumping requires running from the pennyfarthing repo"
        error "Try: cd pennyfarthing && just release --bump patch"
        exit 1
    fi
    if $DRY_RUN; then
        exec "$DEPLOY_SCRIPT" --dry-run "$BUMP_TYPE"
    else
        exec "$DEPLOY_SCRIPT" "$BUMP_TYPE"
    fi
fi

# No version bump - just merge and push
info "=== Release (no version bump) ==="
echo ""

# Pre-flight checks
info "Running pre-flight checks..."

# Check we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    error "Not in a git repository"
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    error "Uncommitted changes detected. Commit or stash before releasing."
fi

# Check workspace dependency version parity
# Catches stale pnpm links where node_modules points to old store version
if [[ -f "pnpm-workspace.yaml" ]] && [[ -d "packages" ]]; then
    STALE_DEPS=()
    for pkg_dir in packages/*/; do
        [[ -f "$pkg_dir/package.json" ]] || continue
        pkg_name=$(node -e "console.log(JSON.parse(require('fs').readFileSync('$pkg_dir/package.json','utf8')).name)" 2>/dev/null) || continue
        source_version=$(node -e "console.log(JSON.parse(require('fs').readFileSync('$pkg_dir/package.json','utf8')).version)" 2>/dev/null) || continue

        # Check all other packages that depend on this one
        for consumer_dir in packages/*/; do
            [[ "$consumer_dir" == "$pkg_dir" ]] && continue
            resolved="$consumer_dir/node_modules/$pkg_name/package.json"
            [[ -f "$resolved" ]] || continue
            resolved_version=$(node -e "console.log(JSON.parse(require('fs').readFileSync('$resolved','utf8')).version)" 2>/dev/null) || continue
            if [[ "$resolved_version" != "$source_version" ]]; then
                consumer_name=$(basename "$consumer_dir")
                STALE_DEPS+=("$consumer_name → $pkg_name: resolved $resolved_version, workspace has $source_version")
            fi
        done
    done
    if [[ ${#STALE_DEPS[@]} -gt 0 ]]; then
        echo -e "${RED}[ERROR]${NC} Stale workspace dependencies detected:"
        for dep in "${STALE_DEPS[@]}"; do
            echo -e "  ${RED}✗${NC} $dep"
        done
        error "Run 'pnpm install' from monorepo root to fix workspace links"
    fi
    info "Workspace dependency versions match"
fi

# Validate changelog comparison links
LINKS_SCRIPT="$(cd "$(dirname "$0")" && pwd)/changelog-links.sh"
if [[ -x "$LINKS_SCRIPT" ]]; then
    if ! "$LINKS_SCRIPT" --validate; then
        error "CHANGELOG.md comparison links are invalid. Run: changelog-links.sh --fix"
    else
        info "CHANGELOG.md comparison links valid"
    fi
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
info "Current branch: $CURRENT_BRANCH"

# Determine main branch name
if git show-ref --verify --quiet refs/heads/main; then
    MAIN_BRANCH="main"
elif git show-ref --verify --quiet refs/heads/master; then
    MAIN_BRANCH="master"
else
    error "No main or master branch found"
fi
info "Main branch: $MAIN_BRANCH"

# Check develop exists
if ! git show-ref --verify --quiet refs/heads/develop; then
    error "No develop branch found"
fi

# Get version
VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
info "Current version: $VERSION"

# Show what will be merged
COMMITS_TO_MERGE=$(git log --oneline "$MAIN_BRANCH"..develop 2>/dev/null | wc -l | tr -d ' ')
if [[ "$COMMITS_TO_MERGE" == "0" ]]; then
    info "No new commits to merge. Branches are already in sync."
    exit 0
fi
info "Commits to merge: $COMMITS_TO_MERGE"

echo ""
info "=== Starting Release Process ==="
echo ""

# Step 1: Ensure we're on develop and it's up to date
info "Step 1: Updating develop branch..."
run git checkout develop
run git pull origin develop 2>/dev/null || true

# Step 2: Switch to main and update
info "Step 2: Updating $MAIN_BRANCH branch..."
run git checkout "$MAIN_BRANCH"
run git pull origin "$MAIN_BRANCH" 2>/dev/null || true

# Step 3: Merge develop into main
info "Step 3: Merging develop into $MAIN_BRANCH..."
if $DRY_RUN; then
    echo -e "${YELLOW}[DRY-RUN]${NC} git merge develop --no-edit"
else
    git merge develop --no-edit
fi

# Step 4: Push main
info "Step 4: Pushing $MAIN_BRANCH to origin..."
run git push origin "$MAIN_BRANCH"

# Step 5: Switch back to develop and push
info "Step 5: Pushing develop to origin..."
run git checkout develop
run git push origin develop

# Step 6: Push tags (in case any were created manually)
info "Step 6: Pushing tags..."
run git push origin --tags

echo ""
info "=== Release Complete ==="
echo ""
info "Version $VERSION released!"
info "  - develop and $MAIN_BRANCH are in sync"
info "  - All changes pushed to origin"

# Return to original branch if different
if [[ "$CURRENT_BRANCH" != "develop" && "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]]; then
    info "Returning to original branch: $CURRENT_BRANCH"
    run git checkout "$CURRENT_BRANCH"
fi
