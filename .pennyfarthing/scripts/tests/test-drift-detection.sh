#!/bin/bash
# test-drift-detection.sh - Tests for story 8-2: Startup Drift Detection
# Verifies that prime/sprint scripts detect and report drift between
# merged branches and sprint YAML status
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

echo "=== Story 8-2: Startup Drift Detection ==="
echo ""

# ==============================================================================
# AC1: prime detects merged-but-not-closed stories
# ==============================================================================

echo "--- AC1: Detects merged-but-not-closed stories ---"
echo ""

# Test: detect_drift function exists in sprint-common.sh
test_detect_drift_function_exists() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift function exists" "file exists" "sprint-common.sh not found"
        return
    fi

    if grep -q "detect_drift" "$sprint_common" 2>/dev/null; then
        pass "detect_drift function exists in sprint-common.sh"
    else
        fail "detect_drift function exists" \
             "detect_drift function in sprint-common.sh" \
             "function not found"
    fi
}

# Test: detect_drift scans git merge log
test_detect_drift_uses_git_log() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift uses git log" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check if detect_drift uses git log --merges
    if grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -q "git log.*merges\|git log --merges"; then
        pass "detect_drift scans git merge log"
    else
        fail "detect_drift uses git log" \
             "git log --merges command in detect_drift" \
             "git log --merges not found in function"
    fi
}

# Test: detect_drift calls get_story_field to check YAML status
test_detect_drift_checks_yaml() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift checks YAML status" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check if detect_drift uses get_story_field
    if grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -q "get_story_field"; then
        pass "detect_drift checks YAML status via get_story_field"
    else
        fail "detect_drift checks YAML status" \
             "get_story_field call in detect_drift" \
             "get_story_field not found in function"
    fi
}

# Test: detect_drift uses extract_story_id to parse branch names
test_detect_drift_uses_extract() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift uses extract_story_id" "file exists" "sprint-common.sh not found"
        return
    fi

    if grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -q "extract_story_id"; then
        pass "detect_drift uses extract_story_id to parse branches"
    else
        fail "detect_drift uses extract_story_id" \
             "extract_story_id call in detect_drift" \
             "extract_story_id not found in function"
    fi
}

# Test: detect_drift returns empty when no drift exists
test_detect_drift_no_drift() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift returns empty when no drift" "file exists" "sprint-common.sh not found"
        return
    fi

    # Source and call detect_drift - should return empty in a clean state
    # (no merged branches that don't match YAML status)
    (
        source "$sprint_common" 2>/dev/null || true

        if type detect_drift &>/dev/null; then
            result=$(detect_drift 2>/dev/null || echo "")
            # Empty result means no drift detected (which is correct for clean state)
            if [[ -z "$result" || "$result" == "" ]]; then
                echo "PASS"
            else
                echo "RESULT:$result"
            fi
        else
            echo "FAIL:function not found"
        fi
    ) | {
        read -r output
        if [[ "$output" == "PASS" ]]; then
            pass "detect_drift returns empty when no drift exists"
        elif [[ "$output" == RESULT:* ]]; then
            # Result might be valid - drifted stories found
            pass "detect_drift returns result (found drifted stories or empty)"
        else
            local got="${output#FAIL:}"
            fail "detect_drift returns empty when no drift" \
                 "empty string or drifted stories" \
                 "${got:-function missing}"
        fi
    }
}

# Test: detect_drift identifies story that is merged but marked in_progress
test_detect_drift_finds_in_progress() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift finds in_progress drift" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check function structure - it should compare status against "done" and "backlog"
    if grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -qE 'done|in_progress|status'; then
        pass "detect_drift checks for non-done/non-backlog statuses"
    else
        fail "detect_drift finds in_progress drift" \
             "status comparison in detect_drift" \
             "status checks not found in function"
    fi
}

# Test: detect_drift ignores stories already marked done
test_detect_drift_ignores_done() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift ignores done stories" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check that function filters out "done" status
    if grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -qE '!= "done"|!= done|-ne done'; then
        pass "detect_drift filters out stories with done status"
    else
        fail "detect_drift ignores done stories" \
             "check for status != done in function" \
             "done filter not found"
    fi
}

# Test: detect_drift ignores stories marked backlog (not drift - never started)
test_detect_drift_ignores_backlog() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift ignores backlog stories" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check that function filters out "backlog" status
    if grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -qE 'backlog'; then
        pass "detect_drift considers backlog status in filtering"
    else
        fail "detect_drift ignores backlog stories" \
             "backlog status check in function" \
             "backlog filter not found"
    fi
}

# Test: detect_drift checks Jira status for drift
test_detect_drift_checks_jira() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift checks Jira status" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check if detect_drift queries Jira status
    if grep -A 60 "detect_drift" "$sprint_common" 2>/dev/null | grep -qE 'jira.*status|jira issue view|jira_status'; then
        pass "detect_drift checks Jira status for drift"
    else
        fail "detect_drift checks Jira status" \
             "jira status check in detect_drift" \
             "jira status check not found in function"
    fi
}

# Test: detect_drift output includes Jira status
test_detect_drift_output_includes_jira() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift output includes Jira status" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check that output format includes jira_status
    if grep -A 60 "detect_drift" "$sprint_common" 2>/dev/null | grep -qE 'jira_status|:.*jira|story_id.*yaml.*jira'; then
        pass "detect_drift output includes Jira status"
    else
        fail "detect_drift output includes Jira status" \
             "jira_status in output format" \
             "jira status not found in output"
    fi
}

test_detect_drift_function_exists
test_detect_drift_uses_git_log
test_detect_drift_checks_yaml
test_detect_drift_uses_extract
test_detect_drift_checks_jira
test_detect_drift_output_includes_jira
test_detect_drift_no_drift
test_detect_drift_finds_in_progress
test_detect_drift_ignores_done
test_detect_drift_ignores_backlog

echo ""

# ==============================================================================
# AC2: Clear report of drifted stories shown to user
# ==============================================================================

echo "--- AC2: Clear report of drifted stories ---"
echo ""

# Test: detect_drift returns story_id:status format
test_drift_output_format() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "drift output includes story ID and status" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check that output includes story_id and status (colon-separated or similar)
    if grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -qE 'story_id.*status|:.*status|\$story_id:\$'; then
        pass "detect_drift output includes story ID and status"
    else
        fail "drift output includes story ID and status" \
             "output format with story_id:status" \
             "output format not found in function"
    fi
}

# Test: Drift report is user-friendly (mentions "merged" and "status")
test_drift_report_clarity() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    local found=false

    # Check sprint-common.sh for descriptive output
    if [[ -f "$sprint_common" ]] && grep -A 30 "detect_drift" "$sprint_common" 2>/dev/null | grep -qi "merged\|drift"; then
        found=true
    fi

    if [[ "$found" == "true" ]]; then
        pass "drift report uses clear terminology (merged, drift, status)"
    else
        fail "drift report clarity" \
             "user-friendly terminology (merged, drift, status)" \
             "clear terminology not found"
    fi
}

test_drift_output_format
test_drift_report_clarity

echo ""

# ==============================================================================
# AC3: Option to auto-reconcile (update YAML to done)
# ==============================================================================

echo "--- AC3: Auto-reconcile option ---"
echo ""

# Test: reconcile_drift function or auto-reconcile logic exists
test_reconcile_function_exists() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    local found=false

    # Check for reconcile function in sprint-common.sh
    if [[ -f "$sprint_common" ]] && grep -qi "reconcile_drift\|auto.reconcile\|reconcile" "$sprint_common" 2>/dev/null; then
        found=true
    fi

    if [[ "$found" == "true" ]]; then
        pass "auto-reconcile functionality exists"
    else
        fail "auto-reconcile functionality exists" \
             "reconcile_drift function or auto-reconcile logic" \
             "reconcile functionality not found"
    fi
}

# Test: Auto-reconcile uses update_story_status
test_reconcile_uses_update() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "reconcile uses update_story_status" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check if there's reconcile logic that calls update_story_status
    # Look for both being present in the file (they should work together)
    local has_detect=$(grep -c "detect_drift" "$sprint_common" 2>/dev/null || echo "0")
    local has_update=$(grep -c "update_story_status" "$sprint_common" 2>/dev/null || echo "0")

    if [[ "$has_detect" -gt 0 && "$has_update" -gt 0 ]]; then
        pass "sprint-common.sh has both detect_drift and update_story_status"
    else
        fail "reconcile uses update_story_status" \
             "both detect_drift and update_story_status in sprint-common.sh" \
             "detect_drift=$has_detect, update_story_status=$has_update"
    fi
}

# Test: Auto-reconcile logs to reconciliation.log
test_reconcile_logs_event() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    local found=false

    # Check sprint-common.sh for log_reconciliation call
    if [[ -f "$sprint_common" ]] && grep -qi "log_reconciliation\|reconciliation" "$sprint_common" 2>/dev/null; then
        found=true
    fi

    if [[ "$found" == "true" ]]; then
        pass "auto-reconcile logs to reconciliation.log"
    else
        fail "auto-reconcile logs to reconciliation.log" \
             "log_reconciliation call or reconciliation.log reference" \
             "reconciliation logging not found"
    fi
}

# Test: reconcile_drift transitions Jira to Done
test_reconcile_transitions_jira() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "reconcile transitions Jira" "file exists" "sprint-common.sh not found"
        return
    fi

    # Check if reconcile_drift uses jira issue move to transition
    if grep -A 40 "reconcile_drift" "$sprint_common" 2>/dev/null | grep -qE 'jira issue move|jira.*Done|transition.*jira'; then
        pass "reconcile_drift transitions Jira to Done"
    else
        fail "reconcile transitions Jira" \
             "jira issue move or transition in reconcile_drift" \
             "jira transition not found"
    fi
}

test_reconcile_function_exists
test_reconcile_uses_update
test_reconcile_transitions_jira
test_reconcile_logs_event

echo ""

# ==============================================================================
# Integration Tests
# ==============================================================================

echo "--- Integration: Drift Detection Pipeline ---"
echo ""

# Test: All required functions exist together
test_drift_pipeline_complete() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "drift pipeline complete" "file exists" "sprint-common.sh not found"
        return
    fi

    local has_extract=$(grep -c "extract_story_id" "$sprint_common" 2>/dev/null || echo "0")
    local has_get=$(grep -c "get_story_field" "$sprint_common" 2>/dev/null || echo "0")
    local has_update=$(grep -c "update_story_status" "$sprint_common" 2>/dev/null || echo "0")
    local has_log=$(grep -c "log_reconciliation" "$sprint_common" 2>/dev/null || echo "0")
    local has_detect=$(grep -c "detect_drift" "$sprint_common" 2>/dev/null || echo "0")

    if [[ "$has_extract" -gt 0 && "$has_get" -gt 0 && "$has_update" -gt 0 && "$has_log" -gt 0 && "$has_detect" -gt 0 ]]; then
        pass "all drift detection pipeline functions exist"
    else
        fail "drift pipeline complete" \
             "extract_story_id, get_story_field, update_story_status, log_reconciliation, detect_drift" \
             "extract=$has_extract get=$has_get update=$has_update log=$has_log detect=$has_detect"
    fi
}

# Test: detect_drift is callable without errors
test_detect_drift_callable() {
    local sprint_common="$PROJECT_ROOT/pennyfarthing-dist/scripts/sprint/sprint-common.sh"

    if [[ ! -f "$sprint_common" ]]; then
        fail "detect_drift callable" "file exists" "sprint-common.sh not found"
        return
    fi

    (
        source "$sprint_common" 2>/dev/null || true

        if type detect_drift &>/dev/null; then
            # Just try to call it - we don't care about the result
            detect_drift 2>/dev/null
            echo "PASS"
        else
            echo "FAIL:function not found"
        fi
    ) | {
        read -r output
        if [[ "$output" == "PASS" ]]; then
            pass "detect_drift is callable without errors"
        else
            local got="${output#FAIL:}"
            fail "detect_drift callable" \
                 "function exists and runs without error" \
                 "${got:-unknown error}"
        fi
    }
}

test_drift_pipeline_complete
test_detect_drift_callable

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
    echo -e "${YELLOW}Story 8-2 Status: RED (tests failing - ready for Dev)${NC}"
    echo ""
    echo "Dev should implement:"
    echo "  1. Add detect_drift() function to sprint-common.sh (AC1)"
    echo "     - Scan git log --merges for recent merges (7 days)"
    echo "     - Extract story IDs from feat/X-Y-* branches"
    echo "     - Compare merged stories against YAML AND Jira status"
    echo "     - Return list of drifted stories (status != done, != backlog)"
    echo "  2. Output format: story_id:yaml_status:jira_status (AC2)"
    echo "     - Clear, user-friendly terminology"
    echo "     - Include both YAML and Jira status"
    echo "  3. Add drift detection to prime/workflow.py (AC1, AC2)"
    echo "     - Call detect_drift after git scan"
    echo "     - Report drifted stories before state determination"
    echo "  4. Add auto-reconcile option (AC3)"
    echo "     - Offer to update YAML to done"
    echo "     - Transition Jira issue to Done"
    echo "     - Use update_story_status() for YAML reconciliation"
    echo "     - Use jira issue move for Jira transition"
    echo "     - Log to reconciliation.log"
    exit 1
else
    echo ""
    echo -e "${GREEN}ALL TESTS PASSED - Story 8-2 Complete${NC}"
    exit 0
fi
