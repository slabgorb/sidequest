#!/usr/bin/env zsh
# Generate skill usage reports from .session/skill-usage.log
# Usage: skill-usage-report.sh [--weekly|--all] [--output FILE]
#
# Reads JSON Lines from .session/skill-usage.log and generates:
#   - Invocation counts per skill
#   - Most/least used skills
#   - Unused skills (in registry but never invoked)
#   - Weekly breakdown (optional)
#
# Environment:
#   PROJECT_ROOT - Set by find-root.sh (required)

set -uo pipefail

# --- Configuration ---
SCRIPT_DIR="${0:A:h}"
source "${SCRIPT_DIR}/common.sh" 2>/dev/null || true

# --- Argument parsing ---
REPORT_TYPE="all"
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --weekly)
            REPORT_TYPE="weekly"
            shift
            ;;
        --all)
            REPORT_TYPE="all"
            shift
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: skill-usage-report.sh [--weekly|--all] [--output FILE]"
            echo ""
            echo "Options:"
            echo "  --weekly    Show only last 7 days of usage"
            echo "  --all       Show all-time usage (default)"
            echo "  --output    Write report to FILE instead of stdout"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# --- Find project root ---
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    dir="$PWD"
    while [[ ! -d "$dir/.pennyfarthing" ]] && [[ "$dir" != "/" ]]; do
        dir="$(dirname "$dir")"
    done
    if [[ -d "$dir/.pennyfarthing" ]]; then
        PROJECT_ROOT="$dir"
    else
        echo "Error: Could not find project root" >&2
        exit 1
    fi
fi

SESSION_DIR="$PROJECT_ROOT/.session"
LOG_FILE="$SESSION_DIR/skill-usage.log"
REGISTRY_FILE="$PROJECT_ROOT/pennyfarthing-dist/skills/skill-registry.yaml"

# --- Helper functions ---
generate_report() {
    local cutoff_date=""
    local title=""

    if [[ "$REPORT_TYPE" == "weekly" ]]; then
        # Get date 7 days ago in ISO format
        if [[ "$(uname)" == "Darwin" ]]; then
            cutoff_date=$(date -v-7d -u +"%Y-%m-%dT%H:%M:%SZ")
        else
            cutoff_date=$(date -d '7 days ago' -u +"%Y-%m-%dT%H:%M:%SZ")
        fi
        title="Skill Usage Report (Last 7 Days)"
    else
        title="Skill Usage Report (All Time)"
    fi

    echo "# $title"
    echo ""
    echo "Generated: $(date -u +"%Y-%m-%d %H:%M UTC")"
    echo ""

    # Check if log file exists
    if [[ ! -f "$LOG_FILE" ]]; then
        echo "## No Usage Data"
        echo ""
        echo "No skill usage has been logged yet."
        echo "Log file: \`$LOG_FILE\`"
        return 0
    fi

    # Filter entries if weekly
    local entries
    if [[ -n "$cutoff_date" ]]; then
        entries=$(jq -c "select(.ts >= \"$cutoff_date\")" "$LOG_FILE" 2>/dev/null || echo "")
    else
        entries=$(cat "$LOG_FILE")
    fi

    if [[ -z "$entries" ]]; then
        echo "## No Usage Data"
        echo ""
        echo "No skill invocations found for the selected period."
        return 0
    fi

    # Count invocations per skill
    echo "## Usage by Skill"
    echo ""
    echo "| Skill | Invocations |"
    echo "|-------|-------------|"

    echo "$entries" | jq -r '.skill' | sort | uniq -c | sort -rn | while read count skill; do
        echo "| $skill | $count |"
    done

    echo ""

    # Usage by agent
    echo "## Usage by Agent"
    echo ""
    echo "| Agent | Invocations |"
    echo "|-------|-------------|"

    echo "$entries" | jq -r '.agent' | sort | uniq -c | sort -rn | while read count agent; do
        echo "| $agent | $count |"
    done

    echo ""

    # Total stats
    local total_count=$(echo "$entries" | wc -l | tr -d ' ')
    local unique_skills=$(echo "$entries" | jq -r '.skill' | sort -u | wc -l | tr -d ' ')

    echo "## Summary"
    echo ""
    echo "- **Total invocations:** $total_count"
    echo "- **Unique skills used:** $unique_skills"

    # Find unused skills
    if [[ -f "$REGISTRY_FILE" ]]; then
        echo ""
        echo "## Unused Skills"
        echo ""

        # Get all skills from registry
        local registry_skills=$(yq -r '.skills | keys | .[]' "$REGISTRY_FILE" 2>/dev/null || echo "")

        # Get used skills
        local used_skills=$(echo "$entries" | jq -r '.skill' | sort -u)

        # Find unused
        local unused=""
        for skill in ${(f)registry_skills}; do
            if ! echo "$used_skills" | grep -q "^${skill}$" 2>/dev/null; then
                unused="$unused$skill\n"
            fi
        done

        if [[ -n "$unused" ]]; then
            echo "The following skills are in the registry but have not been invoked:"
            echo ""
            echo "$unused" | while read skill; do
                [[ -n "$skill" ]] && echo "- \`$skill\`"
            done
        else
            echo "All registered skills have been used!"
        fi
    fi

    return 0
}

# --- Main ---
if [[ -n "$OUTPUT_FILE" ]]; then
    generate_report > "$OUTPUT_FILE"
    echo "Report written to: $OUTPUT_FILE"
else
    generate_report
fi

exit 0
