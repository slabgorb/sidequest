#!/usr/bin/env bash
#
# changelog-links.sh - Validate and regenerate CHANGELOG.md comparison links
#
# Parses ## [X.Y.Z] headers from CHANGELOG.md and ensures the comparison
# links section at the bottom is complete, ordered, and correct.
#
# Usage:
#   changelog-links.sh [OPTIONS]
#
# Options:
#   --validate    Check links are correct (exit 1 if not). Default mode.
#   --fix         Regenerate the links section in-place.
#   --print       Print what the links section should be (stdout).
#   --changelog   Path to CHANGELOG.md (default: auto-detect)
#   --repo-url    GitHub repo URL (default: parsed from links section)
#
# Exit codes:
#   0 - Links are valid (--validate) or fixed (--fix)
#   1 - Links are invalid (--validate) or error occurred

set -euo pipefail

# --- Defaults ---
MODE="validate"
CHANGELOG_PATH=""
REPO_URL=""

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case $1 in
        --validate)  MODE="validate"; shift ;;
        --fix)       MODE="fix"; shift ;;
        --print)     MODE="print"; shift ;;
        --changelog) CHANGELOG_PATH="$2"; shift 2 ;;
        --repo-url)  REPO_URL="$2"; shift 2 ;;
        --help|-h)
            head -17 "$0" | tail -15
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# --- Find CHANGELOG.md ---
if [[ -z "$CHANGELOG_PATH" ]]; then
    # Walk up from PWD looking for CHANGELOG.md
    _dir="$PWD"
    while [[ ! -f "$_dir/CHANGELOG.md" ]] && [[ "$_dir" != "/" ]]; do
        _dir="$(dirname "$_dir")"
    done
    if [[ -f "$_dir/CHANGELOG.md" ]]; then
        CHANGELOG_PATH="$_dir/CHANGELOG.md"
    else
        echo "ERROR: CHANGELOG.md not found" >&2
        exit 1
    fi
fi

if [[ ! -f "$CHANGELOG_PATH" ]]; then
    echo "ERROR: File not found: $CHANGELOG_PATH" >&2
    exit 1
fi

# --- Extract repo URL from existing links ---
if [[ -z "$REPO_URL" ]]; then
    REPO_URL=$(grep -oE 'https://github\.com/[^/]+/[^/]+' "$CHANGELOG_PATH" | head -1)
    if [[ -z "$REPO_URL" ]]; then
        echo "ERROR: Could not detect repo URL from CHANGELOG.md. Use --repo-url." >&2
        exit 1
    fi
fi

# --- Extract version headers in document order (top = newest) ---
# Matches: ## [X.Y.Z] or ## [Unreleased]
# Captures just the version string
VERSIONS=()
while IFS= read -r line; do
    # Extract version from ## [version] headers
    if [[ "$line" =~ ^##[[:space:]]+\[([^]]+)\] ]]; then
        VERSIONS+=("${BASH_REMATCH[1]}")
    fi
done < "$CHANGELOG_PATH"

if [[ ${#VERSIONS[@]} -lt 2 ]]; then
    echo "ERROR: Found fewer than 2 version headers in CHANGELOG.md" >&2
    exit 1
fi

# --- Generate correct links ---
# Links are in same order as headers (newest first).
# Each version compares against the next (older) version.
# The oldest version links to its release tag.
# [Unreleased] compares against the newest release.
generate_links() {
    local i
    for ((i = 0; i < ${#VERSIONS[@]}; i++)); do
        local ver="${VERSIONS[$i]}"
        if [[ "$ver" == "Unreleased" ]]; then
            # Unreleased compares against the next version (newest release)
            if [[ $((i + 1)) -lt ${#VERSIONS[@]} ]]; then
                local next="${VERSIONS[$((i + 1))]}"
                echo "[Unreleased]: ${REPO_URL}/compare/v${next}...HEAD"
            fi
        elif [[ $((i + 1)) -lt ${#VERSIONS[@]} ]]; then
            local next="${VERSIONS[$((i + 1))]}"
            if [[ "$next" == "Unreleased" ]]; then
                # This shouldn't happen in a well-formed changelog
                continue
            fi
            echo "[${ver}]: ${REPO_URL}/compare/v${next}...v${ver}"
        else
            # Oldest version - link to release tag
            echo "[${ver}]: ${REPO_URL}/releases/tag/v${ver}"
        fi
    done
}

EXPECTED_LINKS=$(generate_links)

# --- Extract current links section ---
# Links section starts after the last version content, identified by
# lines matching the [version]: URL pattern at the end of the file.
# We find the first link line and take everything from there to EOF.
FIRST_LINK_LINE=$(grep -n '^\[' "$CHANGELOG_PATH" | grep -E '^\d+:\[.+\]: https://' | head -1 | cut -d: -f1)

if [[ -z "$FIRST_LINK_LINE" ]]; then
    CURRENT_LINKS=""
else
    CURRENT_LINKS=$(tail -n +"$FIRST_LINK_LINE" "$CHANGELOG_PATH" | sed '/^$/d')
fi

# --- Act based on mode ---
case "$MODE" in
    print)
        echo "$EXPECTED_LINKS"
        ;;
    validate)
        if [[ "$CURRENT_LINKS" == "$EXPECTED_LINKS" ]]; then
            echo "PASS: CHANGELOG.md comparison links are correct (${#VERSIONS[@]} versions)"
            exit 0
        else
            echo "FAIL: CHANGELOG.md comparison links are incorrect"
            echo ""
            echo "--- Expected (${#VERSIONS[@]} links) ---"
            echo "$EXPECTED_LINKS" | head -5
            echo "..."
            echo ""
            echo "--- Actual ---"
            echo "$CURRENT_LINKS" | head -5
            echo "..."
            echo ""

            # Count specific issues
            EXPECTED_COUNT=$(echo "$EXPECTED_LINKS" | wc -l | tr -d ' ')
            ACTUAL_COUNT=$(echo "$CURRENT_LINKS" | wc -l | tr -d ' ')
            if [[ "$EXPECTED_COUNT" != "$ACTUAL_COUNT" ]]; then
                echo "Link count mismatch: expected $EXPECTED_COUNT, got $ACTUAL_COUNT"
            fi

            # Check for missing versions
            for ver in "${VERSIONS[@]}"; do
                if [[ "$ver" == "Unreleased" ]]; then
                    if ! echo "$CURRENT_LINKS" | grep -q '^\[Unreleased\]:'; then
                        echo "  Missing: [Unreleased] link"
                    fi
                else
                    if ! echo "$CURRENT_LINKS" | grep -q "^\[${ver}\]:"; then
                        echo "  Missing: [${ver}] link"
                    fi
                fi
            done

            echo ""
            echo "Run with --fix to regenerate links."
            exit 1
        fi
        ;;
    fix)
        # Remove existing links section and append correct one
        if [[ -n "$FIRST_LINK_LINE" ]]; then
            # Keep everything before the links section
            BEFORE_LINKS_LINE=$((FIRST_LINK_LINE - 1))
            head -n "$BEFORE_LINKS_LINE" "$CHANGELOG_PATH" > "${CHANGELOG_PATH}.tmp"
        else
            # No links section exists - use entire file
            cp "$CHANGELOG_PATH" "${CHANGELOG_PATH}.tmp"
        fi

        # Strip trailing blank lines from content
        while [[ -s "${CHANGELOG_PATH}.tmp" ]] && [[ "$(tail -c 1 "${CHANGELOG_PATH}.tmp" | xxd -p)" == "0a" ]]; do
            # Check if last line is empty
            LAST_LINE=$(tail -1 "${CHANGELOG_PATH}.tmp")
            if [[ -z "$LAST_LINE" ]]; then
                # Remove last empty line using head
                LINE_COUNT=$(wc -l < "${CHANGELOG_PATH}.tmp" | tr -d ' ')
                head -n $((LINE_COUNT - 1)) "${CHANGELOG_PATH}.tmp" > "${CHANGELOG_PATH}.tmp2"
                mv "${CHANGELOG_PATH}.tmp2" "${CHANGELOG_PATH}.tmp"
            else
                break
            fi
        done

        # Append links section with blank line separator
        {
            echo ""
            echo "$EXPECTED_LINKS"
        } >> "${CHANGELOG_PATH}.tmp"

        mv "${CHANGELOG_PATH}.tmp" "$CHANGELOG_PATH"
        echo "Fixed: Regenerated ${#VERSIONS[@]} comparison links in CHANGELOG.md"
        ;;
esac
