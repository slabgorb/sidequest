#!/bin/bash
# test-post-merge-hook.sh - Tests for story 8-1: Git Hook for PR Merge Detection
# Verifies the post-merge hook properly updates sprint YAML when PRs merge
#
# RED STATE: These tests will FAIL until Dev implements the feature

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    echo "  Expected: $2"
    echo "  Got: $3"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

echo "=== Story 8-1: Git Hook for PR Merge Detection ==="
echo ""

# ==============================================================================
# AC1: Hook installed via pf setup (or doctor --fix)
# ==============================================================================

echo "--- AC1: Hook installed via pf setup ---"
echo ""

# Test: post-merge.sh hook script exists
test_hook_script_exists() {
    local hook_file="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/post-merge.sh"

    if [[ -f "$hook_file" ]]; then
        pass "post-merge.sh hook script exists"
    else
        fail "post-merge.sh hook script exists" \
             "file at pennyfarthing-dist/scripts/hooks/post-merge.sh" \
             "file not found"
    fi
}

# Test: post-merge.sh is executable
test_hook_is_executable() {
    local hook_file="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/post-merge.sh"

    if [[ ! -f "$hook_file" ]]; then
        fail "post-merge.sh is executable" "file exists" "file not found"
        return
    fi

    if [[ -x "$hook_file" ]]; then
        pass "post-merge.sh is executable"
    else
        fail "post-merge.sh is executable" \
             "executable permission set" \
             "not executable"
    fi
}

# Test: init.ts references post-merge hook installation
test_init_installs_hook() {
    local init_file="$PROJECT_ROOT/packages/core/src/cli/commands/init.ts"

    if [[ ! -f "$init_file" ]]; then
        fail "init.ts installs post-merge hook" "file exists" "file not found"
        return
    fi

    if grep -q "post-merge\|postMerge" "$init_file" 2>/dev/null; then
        pass "init.ts references post-merge hook installation"
    else
        fail "init.ts installs post-merge hook" \
             "post-merge hook installation code in init.ts" \
             "no post-merge reference found"
    fi
}

test_hook_script_exists
test_hook_is_executable
test_init_installs_hook

echo ""

# ==============================================================================
# AC2: Detects story ID from branch name pattern (feat/X-Y-*)
# ==============================================================================

echo "--- AC2: Detects story ID from branch name pattern ---"
echo ""

# Test: extract_story_id function exists in sprint-common.sh or post-merge.sh
test_extract_function_exists() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"
    local post_merge="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/post-merge.sh"

    local found=false

    if [[ -f "$sprint_common" ]] && grep -q "extract_story_id\|parse_story_id" "$sprint_common" 2>/dev/null; then
        found=true
    fi

    if [[ -f "$post_merge" ]] && grep -q "extract_story_id\|parse_story_id" "$post_merge" 2>/dev/null; then
        found=true
    fi

    if [[ "$found" == "true" ]]; then
        pass "extract_story_id/parse_story_id function exists"
    else
        fail "story ID extraction function exists" \
             "extract_story_id or parse_story_id function" \
             "function not found in sprint-common.sh or post-merge.sh"
    fi
}

# Test: Extracts "8-1" from "feat/8-1-merge-detection"
test_extract_standard_format() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "extract from feat/8-1-merge-detection" "file exists" "sprint-common.sh not found"
        return
    fi

    # Source the file and test the function
    (
        source "$sprint_common" 2>/dev/null || true

        if type extract_story_id &>/dev/null; then
            result=$(extract_story_id "feat/8-1-merge-detection" 2>/dev/null || echo "")
            if [[ "$result" == "8-1" ]]; then
                echo "PASS"
            else
                echo "FAIL:$result"
            fi
        else
            echo "FAIL:function not found"
        fi
    ) | {
        read -r output
        if [[ "$output" == "PASS" ]]; then
            pass "extracts '8-1' from 'feat/8-1-merge-detection'"
        else
            local got="${output#FAIL:}"
            fail "extracts '8-1' from 'feat/8-1-merge-detection'" \
                 "8-1" \
                 "${got:-empty or function missing}"
        fi
    }
}

# Test: Extracts "15-7" from "feat/15-7-move-assets"
test_extract_double_digit() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "extract from feat/15-7-move-assets" "file exists" "sprint-common.sh not found"
        return
    fi

    (
        source "$sprint_common" 2>/dev/null || true

        if type extract_story_id &>/dev/null; then
            result=$(extract_story_id "feat/15-7-move-assets" 2>/dev/null || echo "")
            if [[ "$result" == "15-7" ]]; then
                echo "PASS"
            else
                echo "FAIL:$result"
            fi
        else
            echo "FAIL:function not found"
        fi
    ) | {
        read -r output
        if [[ "$output" == "PASS" ]]; then
            pass "extracts '15-7' from 'feat/15-7-move-assets'"
        else
            local got="${output#FAIL:}"
            fail "extracts '15-7' from 'feat/15-7-move-assets'" \
                 "15-7" \
                 "${got:-empty or function missing}"
        fi
    }
}

# Test: Returns empty for non-matching branch "fix/something"
test_extract_no_match() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "no match for fix/something" "file exists" "sprint-common.sh not found"
        return
    fi

    (
        source "$sprint_common" 2>/dev/null || true

        if type extract_story_id &>/dev/null; then
            result=$(extract_story_id "fix/something" 2>/dev/null || echo "")
            if [[ -z "$result" ]]; then
                echo "PASS"
            else
                echo "FAIL:$result"
            fi
        else
            echo "FAIL:function not found"
        fi
    ) | {
        read -r output
        if [[ "$output" == "PASS" ]]; then
            pass "returns empty for non-matching 'fix/something'"
        else
            local got="${output#FAIL:}"
            fail "returns empty for non-matching 'fix/something'" \
                 "empty string" \
                 "'$got'"
        fi
    }
}

# Test: Returns empty for invalid format "feat/invalid"
test_extract_invalid_format() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "no match for feat/invalid" "file exists" "sprint-common.sh not found"
        return
    fi

    (
        source "$sprint_common" 2>/dev/null || true

        if type extract_story_id &>/dev/null; then
            result=$(extract_story_id "feat/invalid" 2>/dev/null || echo "")
            if [[ -z "$result" ]]; then
                echo "PASS"
            else
                echo "FAIL:$result"
            fi
        else
            echo "FAIL:function not found"
        fi
    ) | {
        read -r output
        if [[ "$output" == "PASS" ]]; then
            pass "returns empty for invalid 'feat/invalid'"
        else
            local got="${output#FAIL:}"
            fail "returns empty for invalid 'feat/invalid'" \
                 "empty string" \
                 "'$got'"
        fi
    }
}

test_extract_function_exists
test_extract_standard_format
test_extract_double_digit
test_extract_no_match
test_extract_invalid_format

echo ""

# ==============================================================================
# AC3: Updates sprint YAML status to 'done' automatically
# ==============================================================================

echo "--- AC3: Updates sprint YAML status to 'done' ---"
echo ""

# Test: update_story_status function exists
test_update_function_exists() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "update_story_status function exists" "file exists" "sprint-common.sh not found"
        return
    fi

    if grep -q "update_story_status" "$sprint_common" 2>/dev/null; then
        pass "update_story_status function exists in sprint-common.sh"
    else
        fail "update_story_status function exists" \
             "update_story_status function in sprint-common.sh" \
             "function not found"
    fi
}

# Test: update_story_status uses yq to modify YAML
test_update_uses_yq() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "update_story_status uses yq" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check if update_story_status function uses yq
    if grep -A 20 "update_story_status" "$sprint_common" 2>/dev/null | grep -q "yq"; then
        pass "update_story_status uses yq for YAML modification"
    else
        fail "update_story_status uses yq" \
             "yq command in update_story_status function" \
             "yq not found in function"
    fi
}

test_update_function_exists
test_update_uses_yq

echo ""

# ==============================================================================
# AC4: Adds completed date field
# ==============================================================================

echo "--- AC4: Adds completed date field ---"
echo ""

# Test: update_story_status adds completed date
test_adds_completed_date() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "adds completed date" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check if update_story_status adds completed field
    if grep -A 30 "update_story_status" "$sprint_common" 2>/dev/null | grep -q "completed\|completion"; then
        pass "update_story_status adds completed date"
    else
        fail "update_story_status adds completed date" \
             "completed field update in function" \
             "completed/completion not found in function"
    fi
}

# Test: Date format is YYYY-MM-DD
test_date_format() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "date format YYYY-MM-DD" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check for date command with proper format
    if grep -A 30 "update_story_status" "$sprint_common" 2>/dev/null | grep -q 'date.*%Y-%m-%d\|+%Y-%m-%d'; then
        pass "uses YYYY-MM-DD date format"
    else
        fail "uses YYYY-MM-DD date format" \
             "date +%Y-%m-%d or similar" \
             "date format not found"
    fi
}

test_adds_completed_date
test_date_format

echo ""

# ==============================================================================
# AC5: Logs reconciliation to .session/
# ==============================================================================

echo "--- AC5: Logs reconciliation to .session/ ---"
echo ""

# Test: log_reconciliation function exists
test_log_function_exists() {
    local post_merge="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/post-merge.sh"
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    local found=false

    if [[ -f "$post_merge" ]] && grep -q "log_reconciliation\|write_log\|append_log" "$post_merge" 2>/dev/null; then
        found=true
    fi

    if [[ -f "$sprint_common" ]] && grep -q "log_reconciliation\|write_log\|append_log" "$sprint_common" 2>/dev/null; then
        found=true
    fi

    if [[ "$found" == "true" ]]; then
        pass "reconciliation logging function exists"
    else
        fail "reconciliation logging function exists" \
             "log_reconciliation or similar function" \
             "logging function not found"
    fi
}

# Test: Logs to .session/ directory
test_logs_to_session_dir() {
    local post_merge="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/post-merge.sh"

    if [[ ! -f "$post_merge" ]]; then
        fail "logs to .session/" "file exists" "post-merge.sh not found"
        return
    fi

    if grep -q "\.session/\|SESSION_DIR" "$post_merge" 2>/dev/null; then
        pass "hook references .session/ directory for logging"
    else
        fail "logs to .session/" \
             ".session/ path or SESSION_DIR variable" \
             "no .session reference found"
    fi
}

test_log_function_exists
test_logs_to_session_dir

echo ""

# ==============================================================================
# AC6: Works for merges that happen outside Claude workflow
# ==============================================================================

echo "--- AC6: Works outside Claude workflow (git hook) ---"
echo ""

# Test: Hook can be installed as .git/hooks/post-merge
test_git_hook_installable() {
    local hook_file="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/post-merge.sh"

    if [[ ! -f "$hook_file" ]]; then
        fail "hook installable as git hook" "file exists" "post-merge.sh not found"
        return
    fi

    # Check if script has proper shebang
    if head -1 "$hook_file" 2>/dev/null | grep -q "^#!/bin/\(bash\|sh\)"; then
        pass "hook has proper shebang for git hook installation"
    else
        fail "hook has proper shebang" \
             "#!/bin/bash or #!/bin/sh" \
             "$(head -1 "$hook_file" 2>/dev/null || echo 'no content')"
    fi
}

# Test: Hook does not require Claude session (no CLAUDE_* env vars required)
test_no_claude_dependency() {
    local hook_file="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/post-merge.sh"

    if [[ ! -f "$hook_file" ]]; then
        fail "no Claude dependency" "file exists" "post-merge.sh not found"
        return
    fi

    # Check that hook doesn't require CLAUDE_* environment variables
    if grep -q 'CLAUDE_.*:-\|CLAUDE_.*:?\|: "\${CLAUDE_' "$hook_file" 2>/dev/null; then
        fail "no Claude dependency" \
             "no required CLAUDE_* env vars" \
             "found required CLAUDE_* environment variable"
    else
        pass "hook does not require CLAUDE_* environment variables"
    fi
}

test_git_hook_installable
test_no_claude_dependency

echo ""

# ==============================================================================
# Summary
# ==============================================================================

echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"

if [[ $TESTS_FAILED -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}Story 8-1 Status: RED (tests failing - ready for Dev)${NC}"
    echo ""
    echo "Dev should implement:"
    echo "  1. Create pennyfarthing-dist/scripts/hooks/post-merge.sh (AC1, AC6)"
    echo "     - Executable, with proper shebang"
    echo "     - Does not require Claude session"
    echo "  2. Add extract_story_id() to sprint-common.sh (AC2)"
    echo "     - Parse feat/X-Y-* pattern"
    echo "     - Return empty for non-matching"
    echo "  3. Add update_story_status() to sprint-common.sh (AC3, AC4)"
    echo "     - Use yq to update status to 'done'"
    echo "     - Add completed date in YYYY-MM-DD format"
    echo "  4. Add log_reconciliation() for .session/ logging (AC5)"
    echo "  5. Update init.ts to install git hook (AC1)"
    exit 1
else
    echo ""
    echo -e "${GREEN}ALL TESTS PASSED - Story 8-1 Complete${NC}"
    exit 0
fi
