#!/usr/bin/env zsh
# Find related archived work sessions for context

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Usage
usage() {
    cat <<EOF
Usage: $0 [OPTIONS] <search-term>

Find related archived work sessions for context.

OPTIONS:
    -e, --epic EPIC_NUM    Find all stories in this epic (e.g., 35)
    -s, --story STORY_ID   Find specific story (e.g., 35-6)
    -k, --keyword TERM     Search by keyword in archived sessions
    -l, --list             List all archived sessions
    --summaries-only       Show only context summaries, not full sessions
    -h, --help             Show this help

EXAMPLES:
    # Find all work related to epic 35
    $0 --epic 35

    # Find specific story
    $0 --story 35-6

    # Search for keyword
    $0 --keyword "topology editor"

    # List all archived work
    $0 --list

    # Show only lightweight summaries
    $0 --epic 35 --summaries-only
EOF
}

# Parse arguments
EPIC=""
STORY=""
KEYWORD=""
LIST_ALL=false
SUMMARIES_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--epic)
            EPIC="$2"
            shift 2
            ;;
        -s|--story)
            STORY="$2"
            shift 2
            ;;
        -k|--keyword)
            KEYWORD="$2"
            shift 2
            ;;
        -l|--list)
            LIST_ALL=true
            shift
            ;;
        --summaries-only)
            SUMMARIES_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Directories
ARCHIVE_DIR="$PROJECT_ROOT/sprint/archive"
CONTEXT_DIR="$PROJECT_ROOT/sprint/context"

# Ensure directories exist
mkdir -p "$ARCHIVE_DIR" "$CONTEXT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# List all archived sessions
if [ "$LIST_ALL" = true ]; then
    echo -e "${BLUE}=== Archived Work Sessions ===${NC}"
    echo ""

    if [ "$SUMMARIES_ONLY" = true ]; then
        # List summaries
        if [ -d "$CONTEXT_DIR" ]; then
            for file in "$CONTEXT_DIR"/*-summary.md; do
                [ -e "$file" ] || continue
                basename "$file"
            done
        else
            echo "No context summaries found."
        fi
    else
        # List full sessions
        for file in "$ARCHIVE_DIR"/*.md; do
            [ -e "$file" ] || continue
            basename "$file"
        done
    fi
    exit 0
fi

# Search by epic
if [ -n "$EPIC" ]; then
    echo -e "${BLUE}=== Stories in Epic $EPIC ===${NC}"
    echo ""

    if [ "$SUMMARIES_ONLY" = true ]; then
        # Search summaries
        SUMMARY_FILE="$CONTEXT_DIR/epic-$EPIC-summary.md"
        if [ -f "$SUMMARY_FILE" ]; then
            echo -e "${GREEN}Found epic summary:${NC} $SUMMARY_FILE"
            echo ""
            cat "$SUMMARY_FILE"
        else
            echo "No summary found for epic $EPIC"
            echo "Searching full archive..."
            grep -l "epic-$EPIC\|Epic $EPIC\|$EPIC-[0-9]" "$ARCHIVE_DIR"/*.md 2>/dev/null || echo "No archived work found for epic $EPIC"
        fi
    else
        # Search full sessions
        MATCHES=$(grep -l "epic-$EPIC\|Epic $EPIC\|$EPIC-[0-9]" "$ARCHIVE_DIR"/*.md 2>/dev/null || true)

        if [ -n "$MATCHES" ]; then
            echo "$MATCHES" | while read -r file; do
                echo -e "${GREEN}Found:${NC} $(basename "$file")"
                echo "  Path: $file"

                # Extract story ID and title if present
                STORY_LINE=$(grep -m 1 "Story.*$EPIC-[0-9]\|ID:.*$EPIC-[0-9]" "$file" || true)
                if [ -n "$STORY_LINE" ]; then
                    echo -e "  ${YELLOW}Story:${NC} $STORY_LINE"
                fi
                echo ""
            done
        else
            echo "No archived work found for epic $EPIC"
        fi
    fi
    exit 0
fi

# Search by story
if [ -n "$STORY" ]; then
    echo -e "${BLUE}=== Story $STORY ===${NC}"
    echo ""

    if [ "$SUMMARIES_ONLY" = true ]; then
        # Check for story summary
        STORY_SUMMARY="$CONTEXT_DIR/story-$STORY-summary.md"
        if [ -f "$STORY_SUMMARY" ]; then
            echo -e "${GREEN}Found story summary:${NC} $STORY_SUMMARY"
            echo ""
            cat "$STORY_SUMMARY"
            exit 0
        fi
    fi

    # Search full archive
    MATCHES=$(grep -l "$STORY\|story.*$STORY" "$ARCHIVE_DIR"/*.md 2>/dev/null || true)

    if [ -n "$MATCHES" ]; then
        echo "$MATCHES" | while read -r file; do
            echo -e "${GREEN}Found:${NC} $(basename "$file")"
            echo "  Path: $file"
            echo ""

            # Show first few lines of context
            echo -e "${YELLOW}Context preview:${NC}"
            head -30 "$file" | grep -v "^#\|^-\|^$" | head -10
            echo ""
        done
    else
        echo "No archived work found for story $STORY"
    fi
    exit 0
fi

# Search by keyword
if [ -n "$KEYWORD" ]; then
    echo -e "${BLUE}=== Search: '$KEYWORD' ===${NC}"
    echo ""

    SEARCH_DIR="$ARCHIVE_DIR"
    if [ "$SUMMARIES_ONLY" = true ]; then
        SEARCH_DIR="$CONTEXT_DIR"
    fi

    MATCHES=$(grep -il "$KEYWORD" "$SEARCH_DIR"/*.md 2>/dev/null || true)

    if [ -n "$MATCHES" ]; then
        echo "$MATCHES" | while read -r file; do
            echo -e "${GREEN}Found in:${NC} $(basename "$file")"
            echo "  Path: $file"
            echo ""

            # Show matching lines with context
            grep -i -C 2 "$KEYWORD" "$file" | head -20
            echo ""
            echo "---"
            echo ""
        done
    else
        echo "No matches found for '$KEYWORD'"
    fi
    exit 0
fi

# No search term provided
echo "Error: Must provide search term"
echo ""
usage
exit 1
