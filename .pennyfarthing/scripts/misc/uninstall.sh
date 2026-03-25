#!/usr/bin/env zsh
# Uninstall pennyfarthing from a project
# Usage: uninstall.sh [--force] [--all] [project-root]
#
# Options:
#   --force    Skip confirmation prompts
#   --all      Also remove project-specific files (.claude/project/, sprint/, .session/)
#   --help     Show this help message

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORCE=false
REMOVE_ALL=false
PROJECT_ROOT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --all|-a)
            REMOVE_ALL=true
            shift
            ;;
        --help|-h)
            echo "Usage: uninstall.sh [--force] [--all] [project-root]"
            echo ""
            echo "Remove pennyfarthing from a project for clean reinstall."
            echo ""
            echo "Options:"
            echo "  --force, -f    Skip confirmation prompts"
            echo "  --all, -a      Also remove project-specific files:"
            echo "                   - .claude/project/ (agent sidecars, custom docs)"
            echo "                   - .claude/persona-config.yaml"
            echo "                   - .session/ (session files)"
            echo "                   - sprint/current-sprint.yaml"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "By default, only managed files are removed:"
            echo "  - .claude/core/"
            echo "  - .claude/skills/"
            echo "  - .pennyfarthing/personas/"
            echo "  - .claude/manifest.json"
            echo "  - .claude/settings.local.json"
            echo "  - scripts/hooks/"
            echo "  - scripts/utils/"
            echo ""
            echo "ALWAYS preserved (even with --all):"
            echo "  - sprint/archive/  (completed work history)"
            echo "  - sprint/context/  (story summaries)"
            exit 0
            ;;
        *)
            PROJECT_ROOT="$1"
            shift
            ;;
    esac
done

# Determine project root
if [ -z "$PROJECT_ROOT" ]; then
    PROJECT_ROOT="$(pwd)"
fi

# Verify this looks like a pennyfarthing installation
if [ ! -f "$PROJECT_ROOT/.claude/manifest.json" ]; then
    echo -e "${RED}Error: No pennyfarthing installation found at $PROJECT_ROOT${NC}"
    echo "  (missing .claude/manifest.json)"
    exit 1
fi

echo -e "${BLUE}Pennyfarthing Uninstall${NC}"
echo "Project: $PROJECT_ROOT"
echo ""

# Read manifest for version info
VERSION=$(cat "$PROJECT_ROOT/.claude/manifest.json" 2>/dev/null | grep '"version"' | cut -d'"' -f4 || echo "unknown")
echo -e "Installed version: ${YELLOW}$VERSION${NC}"
echo ""

# Define what to remove
MANAGED_PATHS=(
    ".claude/core"
    ".claude/skills"
    ".claude/commands"
    ".claude/personas"
    ".claude/pennyfarthing"
    ".claude/manifest.json"
    ".claude/settings.local.json"
    ".claude/statusline.sh"
    ".pennyfarthing/agents"
    ".pennyfarthing/guides"
    ".pennyfarthing/personas"
    ".pennyfarthing/scripts"
    ".pennyfarthing/workflows"
    "scripts/core"
    "scripts/hooks"
    "scripts/lib"
    "scripts/misc"
)

# Project paths that can be removed with --all (but preserve archives)
PROJECT_PATHS=(
    ".claude/project"
    ".claude/persona-config.yaml"
    ".session"
)

# Paths that are ALWAYS preserved (archived work, history)
PRESERVED_PATHS=(
    "sprint/archive"
    "sprint/context"
)

# Show what will be removed
echo -e "${YELLOW}Files to remove (managed):${NC}"
for path in "${MANAGED_PATHS[@]}"; do
    full_path="$PROJECT_ROOT/$path"
    if [ -e "$full_path" ]; then
        if [ -d "$full_path" ]; then
            count=$(find "$full_path" -type f 2>/dev/null | wc -l | tr -d ' ')
            echo "  $path/ ($count files)"
        else
            echo "  $path"
        fi
    fi
done

if [ "$REMOVE_ALL" = true ]; then
    echo ""
    echo -e "${YELLOW}Files to remove (project-specific):${NC}"
    for path in "${PROJECT_PATHS[@]}"; do
        full_path="$PROJECT_ROOT/$path"
        if [ -e "$full_path" ]; then
            if [ -d "$full_path" ]; then
                count=$(find "$full_path" -type f 2>/dev/null | wc -l | tr -d ' ')
                echo "  $path/ ($count files)"
            else
                echo "  $path"
            fi
        fi
    done
    # Show sprint YAML will be removed but archives preserved
    if [ -f "$PROJECT_ROOT/sprint/current-sprint.yaml" ]; then
        echo "  sprint/current-sprint.yaml"
    fi
else
    echo ""
    echo -e "${GREEN}Files preserved (project-specific):${NC}"
    for path in "${PROJECT_PATHS[@]}"; do
        full_path="$PROJECT_ROOT/$path"
        if [ -e "$full_path" ]; then
            echo "  $path"
        fi
    done
    if [ -d "$PROJECT_ROOT/sprint" ]; then
        echo "  sprint/"
    fi
    echo ""
    echo "  Use --all to also remove project-specific files"
fi

# Always show preserved paths
echo ""
echo -e "${GREEN}Files ALWAYS preserved (archived work):${NC}"
for path in "${PRESERVED_PATHS[@]}"; do
    full_path="$PROJECT_ROOT/$path"
    if [ -e "$full_path" ]; then
        if [ -d "$full_path" ]; then
            count=$(find "$full_path" -type f 2>/dev/null | wc -l | tr -d ' ')
            echo "  $path/ ($count files)"
        else
            echo "  $path"
        fi
    fi
done

echo ""

# Confirm unless --force
if [ "$FORCE" != true ]; then
    read -p "Proceed with uninstall? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

echo ""
echo -e "${BLUE}Removing files...${NC}"

# Remove managed paths
for path in "${MANAGED_PATHS[@]}"; do
    full_path="$PROJECT_ROOT/$path"
    if [ -e "$full_path" ]; then
        rm -rf "$full_path"
        echo -e "  ${RED}✗${NC} $path"
    fi
done

# Remove project paths if --all (but preserve archives)
if [ "$REMOVE_ALL" = true ]; then
    for path in "${PROJECT_PATHS[@]}"; do
        full_path="$PROJECT_ROOT/$path"
        if [ -e "$full_path" ]; then
            rm -rf "$full_path"
            echo -e "  ${RED}✗${NC} $path"
        fi
    done

    # Remove sprint YAML but preserve archive and context
    if [ -f "$PROJECT_ROOT/sprint/current-sprint.yaml" ]; then
        rm -f "$PROJECT_ROOT/sprint/current-sprint.yaml"
        echo -e "  ${RED}✗${NC} sprint/current-sprint.yaml"
    fi
    if [ -f "$PROJECT_ROOT/sprint/.gitkeep" ]; then
        rm -f "$PROJECT_ROOT/sprint/.gitkeep"
    fi

    echo ""
    echo -e "${GREEN}Preserved:${NC}"
    for path in "${PRESERVED_PATHS[@]}"; do
        full_path="$PROJECT_ROOT/$path"
        if [ -e "$full_path" ]; then
            echo -e "  ${GREEN}✓${NC} $path"
        fi
    done
fi

# Clean up empty directories
if [ -d "$PROJECT_ROOT/.claude" ]; then
    # Remove .claude if empty or only has empty subdirs
    find "$PROJECT_ROOT/.claude" -type d -empty -delete 2>/dev/null || true

    # Check if .claude is now empty
    if [ -d "$PROJECT_ROOT/.claude" ] && [ -z "$(ls -A "$PROJECT_ROOT/.claude")" ]; then
        rmdir "$PROJECT_ROOT/.claude"
        echo -e "  ${RED}✗${NC} .claude/ (empty)"
    fi
fi

if [ -d "$PROJECT_ROOT/scripts" ]; then
    # Remove scripts if empty
    find "$PROJECT_ROOT/scripts" -type d -empty -delete 2>/dev/null || true

    if [ -d "$PROJECT_ROOT/scripts" ] && [ -z "$(ls -A "$PROJECT_ROOT/scripts")" ]; then
        rmdir "$PROJECT_ROOT/scripts"
        echo -e "  ${RED}✗${NC} scripts/ (empty)"
    fi
fi

# Remove symlinks in .claude/ if they exist
for link in agents subagents commands guides; do
    link_path="$PROJECT_ROOT/.claude/$link"
    if [ -L "$link_path" ]; then
        rm "$link_path"
        echo -e "  ${RED}✗${NC} .claude/$link (symlink)"
    fi
done

echo ""
echo -e "${GREEN}Pennyfarthing uninstalled successfully.${NC}"
echo ""
echo "To reinstall:"
echo "  pf setup"
