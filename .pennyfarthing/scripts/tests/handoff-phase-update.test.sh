#!/usr/bin/env bash
# Test: handoff-phase-update.test.sh
# Story: handoff-phase-update-bug (<PROJECT-KEY>)
#
# Tests that handoff.md contains explicit Edit tool instructions for:
# - AC1: Updating **Phase:** field to next phase
# - AC2: Updating Phase History table with end timestamp and duration
# - AC3: Adding Handoff History row with gate and status
# - AC4: prime correctly detects phase (integration)
# - AC5: All three transitions documented (TEA→Dev, Dev→Reviewer, Reviewer→SM)

set -euo pipefail

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

HANDOFF_MD="$PROJECT_ROOT/pennyfarthing-dist/agents/handoff.md"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

pass() {
    ((TESTS_PASSED++))
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    ((TESTS_FAILED++))
    echo -e "${RED}✗${NC} $1"
}

run_test() {
    ((TESTS_RUN++))
    "$@"
}

echo "=== Handoff Phase Update Tests ==="
echo "Testing: $HANDOFF_MD"
echo ""

# Verify handoff.md exists
if [[ ! -f "$HANDOFF_MD" ]]; then
    echo "ERROR: handoff.md not found at $HANDOFF_MD"
    exit 1
fi

HANDOFF_CONTENT=$(cat "$HANDOFF_MD")

# ==============================================================================
# AC1: Handoff subagent updates **Phase:** field to next phase
# ==============================================================================
echo "--- AC1: Phase field update instructions ---"

test_ac1_edit_tool_for_phase() {
    # Must contain explicit Edit tool instruction for Phase field
    if echo "$HANDOFF_CONTENT" | grep -q "Edit tool.*\*\*Phase:\*\*" || \
       echo "$HANDOFF_CONTENT" | grep -q "Edit.*old_string.*Phase" || \
       echo "$HANDOFF_CONTENT" | grep -q 'old_string:.*\*\*Phase:\*\*'; then
        pass "AC1.1: Contains Edit tool instruction for Phase field"
    else
        fail "AC1.1: Missing Edit tool instruction for Phase field"
    fi
}

test_ac1_phase_replacement_pattern() {
    # Must specify the replacement pattern: **Phase:** {old} → **Phase:** {new}
    if echo "$HANDOFF_CONTENT" | grep -q '\*\*Phase:\*\*.*CURRENT_PHASE\|NEXT_PHASE' || \
       echo "$HANDOFF_CONTENT" | grep -qE 'Phase:.*\{(CURRENT|NEXT|to|from)'; then
        pass "AC1.2: Contains Phase replacement pattern with variables"
    else
        fail "AC1.2: Missing Phase replacement pattern with variables"
    fi
}

test_ac1_session_file_target() {
    # Must specify session file as target
    if echo "$HANDOFF_CONTENT" | grep -q 'session.*file\|\.session/\|SESSION_FILE\|{STORY_ID}-session\.md'; then
        pass "AC1.3: References session file as edit target"
    else
        fail "AC1.3: Missing session file reference for edit"
    fi
}

run_test test_ac1_edit_tool_for_phase
run_test test_ac1_phase_replacement_pattern
run_test test_ac1_session_file_target

# ==============================================================================
# AC2: Phase History table updated with end timestamp and duration
# ==============================================================================
echo ""
echo "--- AC2: Phase History table update ---"

test_ac2_phase_history_instruction() {
    # Must contain instruction to update Phase History table
    if echo "$HANDOFF_CONTENT" | grep -q "Phase History" && \
       echo "$HANDOFF_CONTENT" | grep -q "Edit\|edit"; then
        pass "AC2.1: Contains Phase History update instruction"
    else
        fail "AC2.1: Missing Phase History update instruction with Edit"
    fi
}

test_ac2_end_timestamp() {
    # Must mention end timestamp or ended field
    if echo "$HANDOFF_CONTENT" | grep -qi "end.*time\|ended\|Ended\|END_TIME\|endedAt"; then
        pass "AC2.2: Contains end timestamp reference"
    else
        fail "AC2.2: Missing end timestamp reference"
    fi
}

test_ac2_duration_calculation() {
    # Must mention duration or calculate-duration
    if echo "$HANDOFF_CONTENT" | grep -qi "duration\|calculate-duration"; then
        pass "AC2.3: Contains duration calculation reference"
    else
        fail "AC2.3: Missing duration calculation reference"
    fi
}

test_ac2_table_row_pattern() {
    # Must show table row format: | Phase | Started | Ended | Duration |
    if echo "$HANDOFF_CONTENT" | grep -q '|.*Phase.*|.*Started\|Ended\|Duration' || \
       echo "$HANDOFF_CONTENT" | grep -q 'table row\|table format'; then
        pass "AC2.4: Contains Phase History table row format"
    else
        fail "AC2.4: Missing Phase History table row format"
    fi
}

run_test test_ac2_phase_history_instruction
run_test test_ac2_end_timestamp
run_test test_ac2_duration_calculation
run_test test_ac2_table_row_pattern

# ==============================================================================
# AC3: Handoff History row added with gate and status
# ==============================================================================
echo ""
echo "--- AC3: Handoff History row ---"

test_ac3_handoff_history_section() {
    # Must contain Handoff History section reference
    if echo "$HANDOFF_CONTENT" | grep -q "Handoff History"; then
        pass "AC3.1: Contains Handoff History section reference"
    else
        fail "AC3.1: Missing Handoff History section reference"
    fi
}

test_ac3_gate_in_history() {
    # Must include gate type in handoff history
    if echo "$HANDOFF_CONTENT" | grep -q "gate\|Gate\|GATE_TYPE"; then
        pass "AC3.2: Contains gate reference for history"
    else
        fail "AC3.2: Missing gate reference for Handoff History"
    fi
}

test_ac3_status_in_history() {
    # Must include status (PASSED/FAILED) in handoff history
    if echo "$HANDOFF_CONTENT" | grep -q "PASSED\|status\|Status"; then
        pass "AC3.3: Contains status reference for history"
    else
        fail "AC3.3: Missing status reference for Handoff History"
    fi
}

test_ac3_explicit_edit_for_history() {
    # Must use Edit tool to add history row, not just describe it
    if echo "$HANDOFF_CONTENT" | grep -A5 "Handoff History" | grep -qi "Edit\|append\|add.*row"; then
        pass "AC3.4: Contains explicit Edit instruction for Handoff History"
    else
        fail "AC3.4: Missing explicit Edit instruction for Handoff History"
    fi
}

run_test test_ac3_handoff_history_section
run_test test_ac3_gate_in_history
run_test test_ac3_status_in_history
run_test test_ac3_explicit_edit_for_history

# ==============================================================================
# AC4: prime correctly detects current phase after handoff
# ==============================================================================
echo ""
echo "--- AC4: prime/workflow.py compatibility ---"

test_ac4_phase_field_format() {
    # Phase field must use exact format that prime/workflow.py expects
    # parse_session_header greps for: **Phase:**
    if echo "$HANDOFF_CONTENT" | grep -q '\*\*Phase:\*\*'; then
        pass "AC4.1: Uses correct **Phase:** format"
    else
        fail "AC4.1: Missing correct **Phase:** format"
    fi
}

test_ac4_phase_value_variable() {
    # Must set phase to NEXT_PHASE value, not hardcoded
    if echo "$HANDOFF_CONTENT" | grep -q 'NEXT_PHASE\|next.*phase\|toPhase\|{to}'; then
        pass "AC4.2: Uses dynamic NEXT_PHASE variable"
    else
        fail "AC4.2: Missing dynamic NEXT_PHASE variable reference"
    fi
}

run_test test_ac4_phase_field_format
run_test test_ac4_phase_value_variable

# ==============================================================================
# AC5: All three transitions documented (TEA→Dev, Dev→Reviewer, Reviewer→SM)
# ==============================================================================
echo ""
echo "--- AC5: All transitions supported ---"

test_ac5_tea_to_dev() {
    # Must support red → green transition (TEA → Dev)
    if echo "$HANDOFF_CONTENT" | grep -qi "red.*green\|TEA.*Dev\|tests_fail"; then
        pass "AC5.1: Supports TEA→Dev (red→green) transition"
    else
        fail "AC5.1: Missing TEA→Dev transition support"
    fi
}

test_ac5_dev_to_reviewer() {
    # Must support green → review transition (Dev → Reviewer)
    if echo "$HANDOFF_CONTENT" | grep -qi "green.*review\|Dev.*Reviewer\|tests_pass"; then
        pass "AC5.2: Supports Dev→Reviewer (green→review) transition"
    else
        fail "AC5.2: Missing Dev→Reviewer transition support"
    fi
}

test_ac5_reviewer_to_sm() {
    # Must support review → finish/approved transition (Reviewer → SM)
    if echo "$HANDOFF_CONTENT" | grep -qi "review.*finish\|review.*approved\|Reviewer.*SM\|approval"; then
        pass "AC5.3: Supports Reviewer→SM (review→finish) transition"
    else
        fail "AC5.3: Missing Reviewer→SM transition support"
    fi
}

test_ac5_generic_workflow_support() {
    # Must work with any workflow, not just TDD
    if echo "$HANDOFF_CONTENT" | grep -q 'WORKFLOW\|workflow\|--workflow'; then
        pass "AC5.4: Supports generic workflow parameter"
    else
        fail "AC5.4: Missing generic workflow support"
    fi
}

run_test test_ac5_tea_to_dev
run_test test_ac5_dev_to_reviewer
run_test test_ac5_reviewer_to_sm
run_test test_ac5_generic_workflow_support

# ==============================================================================
# Critical: Edit tool usage must be explicit, not vague
# ==============================================================================
echo ""
echo "--- Critical: Explicit Edit tool usage ---"

test_critical_edit_tool_listed() {
    # frontmatter must list Edit as available tool
    if echo "$HANDOFF_CONTENT" | head -10 | grep -q "Edit"; then
        pass "CRIT.1: Edit tool listed in frontmatter"
    else
        fail "CRIT.1: Edit tool NOT listed in frontmatter"
    fi
}

test_critical_explicit_edit_section() {
    # Must have explicit section showing Edit tool usage
    if echo "$HANDOFF_CONTENT" | grep -qE "Edit tool|use Edit|Use Edit|using Edit"; then
        pass "CRIT.2: Contains explicit 'Edit tool' instruction"
    else
        fail "CRIT.2: Missing explicit 'Edit tool' instruction - this is the bug!"
    fi
}

test_critical_old_string_new_string() {
    # Must show old_string/new_string pattern for Edit
    if echo "$HANDOFF_CONTENT" | grep -q "old_string\|new_string"; then
        pass "CRIT.3: Shows old_string/new_string Edit pattern"
    else
        fail "CRIT.3: Missing old_string/new_string Edit pattern - this is the bug!"
    fi
}

test_critical_step5_has_edit() {
    # Step 5 "Update session file" must contain Edit tool usage
    step5_section=$(echo "$HANDOFF_CONTENT" | sed -n '/5\. \*\*Update session file/,/6\. \*\*/p')
    if echo "$step5_section" | grep -qi "Edit"; then
        pass "CRIT.4: Step 5 contains Edit tool instruction"
    else
        fail "CRIT.4: Step 5 missing Edit tool instruction - this is the bug!"
    fi
}

run_test test_critical_edit_tool_listed
run_test test_critical_explicit_edit_section
run_test test_critical_old_string_new_string
run_test test_critical_step5_has_edit

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"

if [[ $TESTS_FAILED -gt 0 ]]; then
    echo ""
    echo "RESULT: RED (failing tests - ready for Dev)"
    exit 1
else
    echo ""
    echo "RESULT: GREEN (all tests passing)"
    exit 0
fi
