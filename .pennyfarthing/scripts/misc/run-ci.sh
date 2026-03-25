#!/usr/bin/env bash
# run-ci.sh - Detect and run CI locally
#
# Story 21-4: /run-ci thin wrapper command
#
# Usage: ./scripts/run-ci.sh [OPTIONS]
#
# Options:
#   --help          Show this help message
#   --detect-only   Show detected CI system without running
#   --dry-run       Show what would run without executing
#
# Detection Order:
#   1. justfile with 'ci' recipe → just ci
#   2. .github/workflows/*.yml → act (if installed)
#   3. .gitlab-ci.yml → gitlab-runner exec
#   4. Fallback: npm/pnpm test && lint && build

set -uo pipefail

# Parse arguments
DETECT_ONLY=false
DRY_RUN=false
SHOW_HELP=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        --detect-only)
            DETECT_ONLY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: run-ci.sh [--help] [--detect-only] [--dry-run]"
            exit 1
            ;;
    esac
done

# Show help
if $SHOW_HELP; then
    cat << 'EOF'
run-ci - Detect and run CI locally

Usage: run-ci.sh [OPTIONS]

Options:
  --help, -h      Show this help message
  --detect-only   Show detected CI system without running
  --dry-run       Show what would run without executing

Detection Order:
  1. justfile with 'ci' recipe → just ci
  2. .github/workflows/*.yml → act (if installed)
  3. .gitlab-ci.yml → gitlab-runner exec
  4. Fallback: npm/pnpm test && lint && build

Examples:
  run-ci.sh              # Run CI locally
  run-ci.sh --dry-run    # Show what would run
  run-ci.sh --detect-only # Just detect CI system
EOF
    exit 0
fi

# Colors (if terminal supports them)
if [[ -t 1 ]]; then
    CYAN='\033[0;36m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m'
else
    CYAN=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Self-locate and set up PROJECT_ROOT
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/../lib/find-root.sh"
cd "$PROJECT_ROOT" || exit 1

# Detection functions

# Check for justfile with 'ci' recipe
has_just_ci_recipe() {
    if [[ -f "justfile" ]] && command -v just &>/dev/null; then
        just --list 2>/dev/null | grep -q "^ci " && return 0
    fi
    return 1
}

# Check for GitHub Actions workflows
has_github_actions() {
    if [[ -d ".github/workflows" ]]; then
        local workflow_count
        workflow_count=$(find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
        [[ "$workflow_count" -gt 0 ]] && return 0
    fi
    return 1
}

# Check for GitLab CI
has_gitlab_ci() {
    [[ -f ".gitlab-ci.yml" ]] && return 0
    return 1
}

# Check for npm/pnpm
has_npm_fallback() {
    [[ -f "package.json" ]] && return 0
    return 1
}

# Detect package manager
get_package_manager() {
    if [[ -f "pnpm-lock.yaml" ]] || [[ -f "pnpm-workspace.yaml" ]]; then
        echo "pnpm"
    elif [[ -f "yarn.lock" ]]; then
        echo "yarn"
    else
        echo "npm"
    fi
}

# Detect CI system and return command
detect_ci() {
    if has_just_ci_recipe; then
        echo "justfile:just ci"
    elif has_github_actions; then
        if command -v act &>/dev/null; then
            echo "github-actions:act"
        else
            echo "github-actions:act (not installed)"
        fi
    elif has_gitlab_ci; then
        if command -v gitlab-runner &>/dev/null; then
            echo "gitlab-ci:gitlab-runner exec shell"
        else
            echo "gitlab-ci:gitlab-runner (not installed)"
        fi
    elif has_npm_fallback; then
        local pm
        pm="$(get_package_manager)"
        echo "npm-fallback:$pm run build && $pm test && $pm run lint"
    else
        echo "none:No CI system detected"
    fi
}

# Main execution
CI_INFO="$(detect_ci)"
CI_SYSTEM="${CI_INFO%%:*}"
CI_COMMAND="${CI_INFO#*:}"

# Handle detect-only mode
if $DETECT_ONLY; then
    echo -e "${CYAN}Detected CI system:${NC} $CI_SYSTEM"
    echo -e "${CYAN}Would run:${NC} $CI_COMMAND"
    exit 0
fi

# Handle dry-run mode
if $DRY_RUN; then
    echo -e "${CYAN}Detected:${NC} $CI_SYSTEM"
    echo -e "${YELLOW}Would run:${NC} $CI_COMMAND"
    exit 0
fi

# Handle no CI detected
if [[ "$CI_SYSTEM" == "none" ]]; then
    echo "No CI system detected in this project."
    exit 1
fi

# Handle missing tools
if [[ "$CI_COMMAND" == *"(not installed)"* ]]; then
    echo -e "${YELLOW}Warning:${NC} $CI_COMMAND"
    echo "Please install the required tool to run CI locally."
    exit 1
fi

# Execute CI
echo -e "${GREEN}Running CI:${NC} $CI_SYSTEM"
echo -e "${CYAN}Command:${NC} $CI_COMMAND"
echo ""

# Run the command
case "$CI_SYSTEM" in
    justfile)
        just ci
        ;;
    github-actions)
        act
        ;;
    gitlab-ci)
        gitlab-runner exec shell
        ;;
    npm-fallback)
        pm="$(get_package_manager)"
        $pm run build && $pm test && $pm run lint
        ;;
esac
