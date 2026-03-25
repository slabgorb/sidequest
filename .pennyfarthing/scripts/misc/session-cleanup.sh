#!/usr/bin/env zsh
# Session artifact cleanup utility for Pennyfarthing
# Cleans accumulated artifacts from .session/ directory
#
# Usage: session-cleanup.sh [OPTIONS]
#
# Options:
#   --dry-run       Show what would be cleaned without deleting
#   --aggressive    Also archive epic contexts for completed epics
#   --story ID      Clean artifacts for specific story only
#   --retention N   Days to retain artifacts (default: 1)
#
# Called by:
#   - /retro (end of sprint - deep clean)
#   - /start-epic (before starting new work)
#   - sm-finish-execution (story-specific cleanup)

set -e

# Allow globs to return empty instead of failing
setopt NULL_GLOB 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

#############################################
# Configuration
#############################################

DRY_RUN=false
AGGRESSIVE=false
STORY_ID=""
RETENTION_DAYS=1

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --aggressive)
            AGGRESSIVE=true
            shift
            ;;
        --story)
            STORY_ID="$2"
            shift 2
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Find project root
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
SESSION_DIR="$PROJECT_ROOT/.session"
ARCHIVE_DIR="$PROJECT_ROOT/sprint/archive"

if [ ! -d "$SESSION_DIR" ]; then
    info "No .session directory found - nothing to clean"
    exit 0
fi

#############################################
# Cleanup Functions
#############################################

# Count and optionally remove files matching pattern
cleanup_pattern() {
    local pattern="$1"
    local description="$2"
    local use_mtime="${3:-true}"

    local files=()
    if [ "$use_mtime" = true ]; then
        files=($(find "$SESSION_DIR" -maxdepth 1 -name "$pattern" -mtime +${RETENTION_DAYS} 2>/dev/null || true))
    else
        files=($(find "$SESSION_DIR" -maxdepth 1 -name "$pattern" 2>/dev/null || true))
    fi

    if [ ${#files[@]} -eq 0 ]; then
        return 0
    fi

    info "Found ${#files[@]} $description"

    for f in "${files[@]}"; do
        if dry_run_check "remove $(basename "$f")"; then
            continue
        fi
        rm -f "$f"
        success "Removed $(basename "$f")"
    done
}

# Archive files matching pattern (move to sprint/archive)
archive_pattern() {
    local pattern="$1"
    local description="$2"

    local files=($(find "$SESSION_DIR" -maxdepth 1 -name "$pattern" -mtime +${RETENTION_DAYS} 2>/dev/null || true))

    if [ ${#files[@]} -eq 0 ]; then
        return 0
    fi

    info "Found ${#files[@]} $description to archive"

    for f in "${files[@]}"; do
        local basename=$(basename "$f")
        if dry_run_check "archive $basename"; then
            continue
        fi
        mv "$f" "$ARCHIVE_DIR/" 2>/dev/null || rm -f "$f"
        success "Archived $basename"
    done
}

# Story-specific cleanup (when --story is provided)
cleanup_story() {
    local story="$1"
    info "Cleaning artifacts for story: $story"

    # New normalized patterns (category-{STORY_ID}-*)
    local patterns=(
        "test-${story}-*.log"
        "test-${story}-*.md"
        "lint-${story}-*.log"
        "handoff-${story}-*.md"
        "handoff-${story}-*.json"
        "context-story-${story}.md"
        # Legacy patterns (for migration)
        "test-*-${story}*.log"
        "test-*-${story}*.md"
        "tea-*-${story}*.md"
        "*-${story}-handoff*.md"
        "*-${story}-handoff*.txt"
        "dev-${story}-*.md"
        "${story}-*.log"
        "${story}-*.txt"
        "story-${story}-context.md"
    )

    for pattern in "${patterns[@]}"; do
        local files=($(find "$SESSION_DIR" -maxdepth 1 -name "$pattern" 2>/dev/null || true))
        for f in "${files[@]}"; do
            if dry_run_check "remove $(basename "$f")"; then
                continue
            fi
            rm -f "$f"
            success "Removed $(basename "$f")"
        done
    done
}

# Rotate session-log.txt to prevent unbounded growth
rotate_session_log() {
    local log_file="$SESSION_DIR/session-log.txt"
    local max_lines=1000

    if [ ! -f "$log_file" ]; then
        return 0
    fi

    local current_lines=$(wc -l < "$log_file" | tr -d ' ')

    if [ "$current_lines" -le "$max_lines" ]; then
        info "session-log.txt has $current_lines lines (under $max_lines limit)"
        return 0
    fi

    info "session-log.txt has $current_lines lines - rotating to $max_lines"

    if dry_run_check "rotate session-log.txt from $current_lines to $max_lines lines"; then
        return 0
    fi

    tail -${max_lines} "$log_file" > "${log_file}.tmp"
    mv "${log_file}.tmp" "$log_file"
    success "Rotated session-log.txt"
}

# Archive epic contexts for completed epics
cleanup_epic_contexts() {
    local sprint_file="$PROJECT_ROOT/sprint/current-sprint.yaml"

    if [ ! -f "$sprint_file" ]; then
        return 0
    fi

    # New pattern: context-epic-{N}.md
    for f in "$SESSION_DIR"/context-epic-*.md; do
        [ -f "$f" ] || continue

        local basename=$(basename "$f")
        local epic_num=$(echo "$basename" | grep -oE '[0-9]+')

        # Check if epic is done in sprint file
        if grep -qE "epic-${epic_num}:.*status:\s*done" "$sprint_file" 2>/dev/null || \
           grep -A5 "epic-${epic_num}:" "$sprint_file" 2>/dev/null | grep -q "status: done"; then
            info "Epic $epic_num is done - archiving context"
            if dry_run_check "archive $basename"; then
                continue
            fi
            mv "$f" "$ARCHIVE_DIR/"
            success "Archived $basename"
        fi
    done

    # Legacy pattern: epic-{N}-context.md (for migration)
    for f in "$SESSION_DIR"/epic-*-context.md; do
        [ -f "$f" ] || continue

        local basename=$(basename "$f")
        local epic_num=$(echo "$basename" | grep -oE '[0-9]+')

        if grep -qE "epic-${epic_num}:.*status:\s*done" "$sprint_file" 2>/dev/null || \
           grep -A5 "epic-${epic_num}:" "$sprint_file" 2>/dev/null | grep -q "status: done"; then
            info "Epic $epic_num is done - archiving legacy context"
            if dry_run_check "archive $basename"; then
                continue
            fi
            mv "$f" "$ARCHIVE_DIR/"
            success "Archived $basename"
        fi
    done
}

#############################################
# Main Execution
#############################################

info "=== Session Cleanup ==="
info "Project: $PROJECT_ROOT"
info "Retention: ${RETENTION_DAYS} days"
[ "$DRY_RUN" = true ] && warn "DRY RUN MODE - no files will be deleted"
[ "$AGGRESSIVE" = true ] && info "Aggressive mode enabled"
echo ""

# If story-specific cleanup requested
if [ -n "$STORY_ID" ]; then
    cleanup_story "$STORY_ID"
    exit 0
fi

# 1. Clean test artifacts (new pattern: test-{STORY_ID}-{agent}-{phase}.*)
cleanup_pattern "test-*.log" "old test log files"
cleanup_pattern "test-*.md" "old test report files"

# 2. Clean lint artifacts (new pattern: lint-{STORY_ID}-{repo}.log)
cleanup_pattern "lint-*.log" "old lint log files"

# 3. Clean handoff artifacts (new pattern: handoff-{STORY_ID}-{agent}.*)
cleanup_pattern "handoff-*.md" "old handoff files"
cleanup_pattern "handoff-*.json" "old handoff JSON files"

# 4. Clean context files (new pattern: context-story-{STORY_ID}.md)
cleanup_pattern "context-story-*.md" "orphaned story context files"

# 5. Legacy patterns (for migration - will be removed in future)
cleanup_pattern "tea-*.md" "old TEA report files (legacy)"
cleanup_pattern "*-red-*.md" "old RED phase files (legacy)"
cleanup_pattern "*-green-*.md" "old GREEN phase files (legacy)"
cleanup_pattern "*-red-*.log" "old RED phase logs (legacy)"
cleanup_pattern "*-green-*.log" "old GREEN phase logs (legacy)"
cleanup_pattern "*-handoff*.md" "old handoff files (legacy)"
cleanup_pattern "*-handoff*.txt" "old handoff text files (legacy)"
cleanup_pattern "dev-*.md" "old dev report files (legacy)"
cleanup_pattern "dev-*.log" "old dev log files (legacy)"
cleanup_pattern "story-*-context.md" "orphaned story context files (legacy)"

# 6. Clean miscellaneous artifacts
cleanup_pattern "*-result.yaml" "old result YAML files"
cleanup_pattern "*-spec.md" "old spec files"
cleanup_pattern "*-research*.md" "old research files"
cleanup_pattern "*-failing-tests.json" "old failing tests JSON files"
cleanup_pattern "*-SUMMARY.md" "old summary files"
cleanup_pattern "test-summary-*.txt" "old test summary files"

# 6. Rotate session log
rotate_session_log

# 7. Clean old agent sessions (already in sm-finish-execution but ensure it runs)
if [ -d "$SESSION_DIR/agents" ]; then
    local old_agents=($(find "$SESSION_DIR/agents" -type f -mtime +${RETENTION_DAYS} 2>/dev/null || true))
    if [ ${#old_agents[@]} -gt 0 ]; then
        info "Found ${#old_agents[@]} old agent session files"
        for f in "${old_agents[@]}"; do
            if dry_run_check "remove agent session $(basename "$f")"; then
                continue
            fi
            rm -f "$f"
        done
        success "Cleaned old agent sessions"
    fi
fi

# 8. Aggressive mode: archive completed epic contexts
if [ "$AGGRESSIVE" = true ]; then
    cleanup_epic_contexts
fi

# 9. Summary
echo ""
info "=== Cleanup Complete ==="
local remaining=$(find "$SESSION_DIR" -maxdepth 1 -type f ! -name ".gitkeep" 2>/dev/null | wc -l | tr -d ' ')
info "Remaining files in .session/: $remaining"

if [ "$DRY_RUN" = true ]; then
    echo ""
    warn "This was a dry run. Run without --dry-run to actually clean files."
fi
