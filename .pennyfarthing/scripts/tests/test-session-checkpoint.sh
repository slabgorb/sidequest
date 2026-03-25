#!/bin/bash
# test-session-checkpoint.sh - Tests for story 8-3: Session Boundary Breadcrumbs
# Verifies that session checkpoints are written on exit and validated on start
#
# Tests the cross-session continuity feature

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

echo "=== Story 8-3: Session Boundary Breadcrumbs ==="
echo ""

# ==============================================================================
# AC1: .session/checkpoint.yaml written on exit
# ==============================================================================

echo "--- AC1: Checkpoint written on session exit ---"
echo ""

# Test: session-stop.sh exists and is executable
test_session_stop_exists() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ -f "$hook" && -x "$hook" ]]; then
        pass "session-stop.sh exists and is executable"
    else
        if [[ -f "$hook" ]]; then
            fail "session-stop.sh executable" "file is executable" "file exists but not executable"
        else
            fail "session-stop.sh exists" "file exists" "file not found"
        fi
    fi
}

# Test: session-stop.sh sources checkpoint.sh
test_session_stop_uses_checkpoint() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-stop uses checkpoint.sh" "file exists" "session-stop.sh not found"
        return
    fi

    if grep -q "checkpoint.sh" "$hook" 2>/dev/null; then
        pass "session-stop.sh sources checkpoint.sh"
    else
        fail "session-stop uses checkpoint.sh" \
             "source checkpoint.sh reference" \
             "checkpoint.sh not sourced"
    fi
}

# Test: session-stop.sh calls checkpoint_save
test_session_stop_saves_checkpoint() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-stop saves checkpoint" "file exists" "session-stop.sh not found"
        return
    fi

    if grep -q "checkpoint_save" "$hook" 2>/dev/null; then
        pass "session-stop.sh calls checkpoint_save"
    else
        fail "session-stop saves checkpoint" \
             "checkpoint_save call in session-stop.sh" \
             "checkpoint_save not found"
    fi
}

# Test: session-stop.sh captures agent info
test_session_stop_captures_agent() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-stop captures agent" "file exists" "session-stop.sh not found"
        return
    fi

    if grep -qE "agent=|\.session/agents" "$hook" 2>/dev/null; then
        pass "session-stop.sh captures agent info"
    else
        fail "session-stop captures agent" \
             "agent capture in session-stop.sh" \
             "agent capture not found"
    fi
}

# Test: session-stop.sh captures story info
test_session_stop_captures_story() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-stop captures story" "file exists" "session-stop.sh not found"
        return
    fi

    if grep -qE "story=|session\.md" "$hook" 2>/dev/null; then
        pass "session-stop.sh captures story info"
    else
        fail "session-stop captures story" \
             "story capture in session-stop.sh" \
             "story capture not found"
    fi
}

# Test: session-stop.sh captures git SHA
test_session_stop_captures_sha() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-stop captures SHA" "file exists" "session-stop.sh not found"
        return
    fi

    if grep -qE "git rev-parse|sha=|git_sha" "$hook" 2>/dev/null; then
        pass "session-stop.sh captures git SHA"
    else
        fail "session-stop captures SHA" \
             "git SHA capture in session-stop.sh" \
             "git SHA capture not found"
    fi
}

# Test: session-stop.sh captures phase info
test_session_stop_captures_phase() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-stop captures phase" "file exists" "session-stop.sh not found"
        return
    fi

    if grep -qE "phase=|Phase:" "$hook" 2>/dev/null; then
        pass "session-stop.sh captures phase info"
    else
        fail "session-stop captures phase" \
             "phase capture in session-stop.sh" \
             "phase capture not found"
    fi
}

test_session_stop_exists
test_session_stop_uses_checkpoint
test_session_stop_saves_checkpoint
test_session_stop_captures_agent
test_session_stop_captures_story
test_session_stop_captures_sha
test_session_stop_captures_phase

echo ""

# ==============================================================================
# AC2: New session validates against current git state
# ==============================================================================

echo "--- AC2: New session validates checkpoint ---"
echo ""

# Test: session-start.sh sources checkpoint.sh
test_session_start_uses_checkpoint() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start uses checkpoint.sh" "file exists" "session-start.sh not found"
        return
    fi

    if grep -q "checkpoint.sh" "$hook" 2>/dev/null; then
        pass "session-start.sh sources checkpoint.sh"
    else
        fail "session-start uses checkpoint.sh" \
             "source checkpoint.sh reference" \
             "checkpoint.sh not sourced"
    fi
}

# Test: session-start.sh calls checkpoint_restore
test_session_start_restores_checkpoint() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start restores checkpoint" "file exists" "session-start.sh not found"
        return
    fi

    if grep -q "checkpoint_restore" "$hook" 2>/dev/null; then
        pass "session-start.sh calls checkpoint_restore"
    else
        fail "session-start restores checkpoint" \
             "checkpoint_restore call in session-start.sh" \
             "checkpoint_restore not found"
    fi
}

# Test: session-start.sh compares git SHAs
test_session_start_compares_sha() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start compares SHA" "file exists" "session-start.sh not found"
        return
    fi

    if grep -qE "prev_sha.*current_sha|current_sha.*prev_sha|sha.*!=\|!=" "$hook" 2>/dev/null; then
        pass "session-start.sh compares git SHAs"
    else
        fail "session-start compares SHA" \
             "SHA comparison in session-start.sh" \
             "SHA comparison not found"
    fi
}

# Test: session-start.sh gets current git SHA
test_session_start_gets_current_sha() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start gets current SHA" "file exists" "session-start.sh not found"
        return
    fi

    if grep -q "git rev-parse" "$hook" 2>/dev/null; then
        pass "session-start.sh gets current git SHA"
    else
        fail "session-start gets current SHA" \
             "git rev-parse in session-start.sh" \
             "git rev-parse not found"
    fi
}

# Test: session-start.sh has validate_checkpoint function
test_session_start_validate_function() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start has validate function" "file exists" "session-start.sh not found"
        return
    fi

    if grep -qE "validate_checkpoint|validate.*checkpoint" "$hook" 2>/dev/null; then
        pass "session-start.sh has validate_checkpoint function"
    else
        fail "session-start has validate function" \
             "validate_checkpoint function in session-start.sh" \
             "validate_checkpoint not found"
    fi
}

test_session_start_uses_checkpoint
test_session_start_restores_checkpoint
test_session_start_compares_sha
test_session_start_gets_current_sha
test_session_start_validate_function

echo ""

# ==============================================================================
# AC3: Warns user if state changed between sessions
# ==============================================================================

echo "--- AC3: Warns user if state changed ---"
echo ""

# Test: session-start.sh logs drift warning
test_session_start_logs_drift() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start logs drift" "file exists" "session-start.sh not found"
        return
    fi

    if grep -qiE "drift|CROSS_SESSION|warning" "$hook" 2>/dev/null; then
        pass "session-start.sh logs drift warning"
    else
        fail "session-start logs drift" \
             "drift or warning in session-start.sh" \
             "drift warning not found"
    fi
}

# Test: session-start.sh writes to session-log.txt on drift
test_session_start_logs_to_session_log() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start logs to session-log" "file exists" "session-start.sh not found"
        return
    fi

    if grep -q "session-log.txt" "$hook" 2>/dev/null; then
        pass "session-start.sh writes to session-log.txt"
    else
        fail "session-start logs to session-log" \
             "session-log.txt reference in session-start.sh" \
             "session-log.txt not found"
    fi
}

# Test: session-start.sh writes to drift-log.txt
test_session_start_drift_log() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "session-start writes drift-log" "file exists" "session-start.sh not found"
        return
    fi

    if grep -q "drift-log.txt" "$hook" 2>/dev/null; then
        pass "session-start.sh writes to drift-log.txt"
    else
        fail "session-start writes drift-log" \
             "drift-log.txt reference in session-start.sh" \
             "drift-log.txt not found"
    fi
}

# Test: Warning includes story context
test_drift_warning_includes_story() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "drift warning includes story" "file exists" "session-start.sh not found"
        return
    fi

    if grep -qE "story=|prev_story|\$story" "$hook" 2>/dev/null; then
        pass "drift warning includes story context"
    else
        fail "drift warning includes story" \
             "story in drift warning" \
             "story context not found"
    fi
}

# Test: Warning includes agent context
test_drift_warning_includes_agent() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"

    if [[ ! -f "$hook" ]]; then
        fail "drift warning includes agent" "file exists" "session-start.sh not found"
        return
    fi

    if grep -qE "agent=|prev_agent|\$agent" "$hook" 2>/dev/null; then
        pass "drift warning includes agent context"
    else
        fail "drift warning includes agent" \
             "agent in drift warning" \
             "agent context not found"
    fi
}

test_session_start_logs_drift
test_session_start_logs_to_session_log
test_session_start_drift_log
test_drift_warning_includes_story
test_drift_warning_includes_agent

echo ""

# ==============================================================================
# Integration Tests
# ==============================================================================

echo "--- Integration: Session Checkpoint Flow ---"
echo ""

# Test: checkpoint.sh functions are available
test_checkpoint_functions_exist() {
    local checkpoint="$PROJECT_ROOT/pennyfarthing-dist/scripts/lib/checkpoint.sh"

    if [[ ! -f "$checkpoint" ]]; then
        fail "checkpoint functions exist" "file exists" "checkpoint.sh not found"
        return
    fi

    local has_save=$(grep -c "checkpoint_save" "$checkpoint" 2>/dev/null || echo "0")
    local has_restore=$(grep -c "checkpoint_restore" "$checkpoint" 2>/dev/null || echo "0")

    if [[ "$has_save" -gt 0 && "$has_restore" -gt 0 ]]; then
        pass "checkpoint.sh has checkpoint_save and checkpoint_restore"
    else
        fail "checkpoint functions exist" \
             "checkpoint_save and checkpoint_restore" \
             "save=$has_save restore=$has_restore"
    fi
}

# Test: Both hooks use find-root.sh for PROJECT_ROOT
test_hooks_use_find_root() {
    local start_hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-start.sh"
    local stop_hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    local start_ok=false
    local stop_ok=false

    if [[ -f "$start_hook" ]] && grep -q "find-root.sh" "$start_hook" 2>/dev/null; then
        start_ok=true
    fi

    if [[ -f "$stop_hook" ]] && grep -q "find-root.sh" "$stop_hook" 2>/dev/null; then
        stop_ok=true
    fi

    if [[ "$start_ok" == "true" && "$stop_ok" == "true" ]]; then
        pass "both hooks use find-root.sh for PROJECT_ROOT"
    else
        fail "hooks use find-root.sh" \
             "find-root.sh in both hooks" \
             "start=$start_ok stop=$stop_ok"
    fi
}

# Test: session-stop.sh saves with "session_state" label
test_session_state_label() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "uses session_state label" "file exists" "session-stop.sh not found"
        return
    fi

    if grep -q '"session_state"' "$hook" 2>/dev/null; then
        pass "session-stop.sh saves with session_state label"
    else
        fail "uses session_state label" \
             "checkpoint_save \"session_state\"" \
             "session_state label not found"
    fi
}

# Test: Checkpoint data format is key=value;key=value
test_checkpoint_data_format() {
    local hook="$PROJECT_ROOT/pennyfarthing-dist/scripts/hooks/session-stop.sh"

    if [[ ! -f "$hook" ]]; then
        fail "checkpoint data format" "file exists" "session-stop.sh not found"
        return
    fi

    # Check for semicolon-separated key=value pairs
    if grep -qE 'agent=.*story=.*phase=.*sha=|;.*;.*;' "$hook" 2>/dev/null; then
        pass "checkpoint uses key=value;key=value format"
    else
        fail "checkpoint data format" \
             "key=value;key=value format" \
             "format not found"
    fi
}

test_checkpoint_functions_exist
test_hooks_use_find_root
test_session_state_label
test_checkpoint_data_format

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
    echo -e "${YELLOW}Story 8-3 Status: RED (tests failing - ready for Dev)${NC}"
    echo ""
    echo "Dev should implement:"
    echo "  1. Create session-stop.sh hook (AC1)"
    echo "     - Source checkpoint.sh"
    echo "     - Capture agent, story, phase, git SHA"
    echo "     - Call checkpoint_save with session_state label"
    echo "  2. Update session-start.sh validation (AC2)"
    echo "     - Source checkpoint.sh"
    echo "     - Call checkpoint_restore for session_state"
    echo "     - Compare previous SHA with current git HEAD"
    echo "  3. Add drift warnings (AC3)"
    echo "     - Log to session-log.txt on SHA mismatch"
    echo "     - Write to drift-log.txt for easy scanning"
    echo "     - Include story and agent context in warning"
    exit 1
else
    echo ""
    echo -e "${GREEN}ALL TESTS PASSED - Story 8-3 Complete${NC}"
    exit 0
fi
