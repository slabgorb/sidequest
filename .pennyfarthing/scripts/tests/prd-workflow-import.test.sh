#!/usr/bin/env bash
# prd-workflow-import.test.sh - Tests for Story <PROJECT-KEY>: Import PRD workflow (all 3 modes)
#
# These tests verify that the PRD workflow from BMAD is correctly imported into Pennyfarthing's
# stepped workflow format with all three modes (create, validate, edit) working correctly.
#
# AC1: Migration script successfully converts PRD workflow from BMAD format
# AC2: Generated workflow.yaml validates against Pennyfarthing schema
# AC3: All variable syntax converted ({var-name} → {var_name})
# AC4-AC6: Each mode executes correctly
# AC7: Gates pause at correct steps (2, 8, 12)
# AC8: Templates and data directories copied and accessible
#
# Run with: ./prd-workflow-import.test.sh
# Or: bash prd-workflow-import.test.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATE_SCRIPT="$SCRIPT_DIR/migrate-bmad-workflow.sh"
BMAD_PRD_SOURCE="${BMAD_PRD_SOURCE:-$HOME/Projects/BMAD-METHOD/src/modules/bmm/workflows/2-plan-workflows/prd}"
TARGET_DIR="$PROJECT_ROOT/pennyfarthing-dist/workflows/prd"

# =============================================================================
# Test Framework
# =============================================================================

assert_eq() {
    local expected="$1"
    local actual="$2"
    local message="${3:-Values should be equal}"

    if [[ "$expected" == "$actual" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Expected: $expected"
        echo "  Actual:   $actual"
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-Output should contain expected text}"

    if [[ "$haystack" == *"$needle"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Expected to contain: $needle"
        echo "  Actual output: ${haystack:0:200}..."
        return 1
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-Output should not contain text}"

    if [[ "$haystack" != *"$needle"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Should not contain: $needle"
        return 1
    fi
}

assert_file_exists() {
    local filepath="$1"
    local message="${2:-File should exist}"

    if [[ -f "$filepath" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  File not found: $filepath"
        return 1
    fi
}

assert_dir_exists() {
    local dirpath="$1"
    local message="${2:-Directory should exist}"

    if [[ -d "$dirpath" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Directory not found: $dirpath"
        return 1
    fi
}

assert_file_contains() {
    local filepath="$1"
    local needle="$2"
    local message="${3:-File should contain text}"

    if [[ ! -f "$filepath" ]]; then
        echo -e "${RED}FAIL${NC}: $message"
        echo "  File not found: $filepath"
        return 1
    fi

    local content
    content=$(cat "$filepath")

    if [[ "$content" == *"$needle"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Expected file to contain: $needle"
        echo "  File: $filepath"
        return 1
    fi
}

assert_file_not_contains() {
    local filepath="$1"
    local needle="$2"
    local message="${3:-File should not contain text}"

    if [[ ! -f "$filepath" ]]; then
        echo -e "${RED}FAIL${NC}: $message"
        echo "  File not found: $filepath"
        return 1
    fi

    local content
    content=$(cat "$filepath")

    if [[ "$content" != *"$needle"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Should not contain: $needle"
        echo "  File: $filepath"
        return 1
    fi
}

assert_file_count() {
    local dirpath="$1"
    local pattern="$2"
    local expected_count="$3"
    local message="${4:-File count should match}"

    if [[ ! -d "$dirpath" ]]; then
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Directory not found: $dirpath"
        return 1
    fi

    local actual_count
    actual_count=$(find "$dirpath" -maxdepth 1 -name "$pattern" -type f | wc -l | tr -d ' ')

    if [[ "$actual_count" -eq "$expected_count" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  Expected: $expected_count files matching $pattern"
        echo "  Actual:   $actual_count files"
        return 1
    fi
}

run_test() {
    local test_name="$1"
    local test_func="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    echo -n "  $test_name... "

    if $test_func; then
        echo -e "${GREEN}PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# =============================================================================
# Prerequisites Check
# =============================================================================

check_prerequisites() {
    echo "Checking prerequisites..."

    if [[ ! -d "$BMAD_PRD_SOURCE" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD PRD workflow source not found at: $BMAD_PRD_SOURCE"
        echo "Set BMAD_PRD_SOURCE environment variable to point to the BMAD PRD workflow directory"
        exit 1
    fi

    if [[ ! -f "$MIGRATE_SCRIPT" ]]; then
        echo -e "${RED}ERROR${NC}: Migration script not found at: $MIGRATE_SCRIPT"
        exit 1
    fi

    echo -e "${GREEN}OK${NC}: Prerequisites met"
    echo ""
}

# =============================================================================
# AC1: Migration script successfully converts PRD workflow from BMAD format
# =============================================================================

test_ac1_migration_completes() {
    # This test verifies the migration script runs without error on PRD source
    # EXPECTED: FAIL until Dev runs the migration

    if [[ ! -d "$TARGET_DIR" ]]; then
        echo -e "${RED}FAIL${NC}: PRD workflow not yet migrated to $TARGET_DIR"
        return 1
    fi

    assert_file_exists "$TARGET_DIR/workflow.yaml" \
        "Migration should produce workflow.yaml"
}

test_ac1_workflow_yaml_has_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "name: prd" \
        "workflow.yaml should have name: prd"
}

test_ac1_workflow_yaml_has_description() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "description:" \
        "workflow.yaml should have a description"
}

test_ac1_workflow_yaml_has_type_stepped() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "type: stepped" \
        "workflow.yaml should have type: stepped"
}

# =============================================================================
# AC2: Generated workflow.yaml validates against Pennyfarthing schema
# =============================================================================

test_ac2_schema_validation_passes() {
    # This test verifies the generated workflow.yaml passes schema validation
    # We'll use the workflow-schema.test.ts validation or a simple structure check

    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Check for required stepped workflow fields
    assert_contains "$content" "workflow:" "Should have workflow root key" && \
    assert_contains "$content" "type: stepped" "Should have type: stepped" && \
    assert_contains "$content" "steps:" "Should have steps configuration"
}

test_ac2_has_steps_path() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "path:" \
        "workflow.yaml should have steps.path"
}

test_ac2_has_steps_pattern() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "pattern:" \
        "workflow.yaml should have steps.pattern"
}

test_ac2_has_agent() {
    # PRD workflow should have an agent assignment
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    assert_contains "$content" "agent:" \
        "workflow.yaml should have an agent assignment"
}

# =============================================================================
# AC3: All variable syntax converted ({var-name} → {var_name})
# =============================================================================

test_ac3_no_dashed_variables_in_workflow() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Check that common BMAD dashed variables are converted
    assert_not_contains "$content" "{project-root}" \
        "Should not have {project-root}" && \
    assert_not_contains "$content" "{planning-artifacts}" \
        "Should not have {planning-artifacts}" && \
    assert_not_contains "$content" "{output-folder}" \
        "Should not have {output-folder}"
}

test_ac3_no_dashed_variables_in_create_steps() {
    # Check all step files in steps-c/ for unconverted variables
    local found_dashed=0

    for stepfile in "$TARGET_DIR"/steps-c/*.md; do
        if [[ -f "$stepfile" ]]; then
            if grep -qE '\{[a-z]+-[a-z-]+\}' "$stepfile" 2>/dev/null; then
                echo "  Found dashed variable in: $(basename "$stepfile")"
                found_dashed=1
            fi
        fi
    done

    if [[ $found_dashed -eq 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found unconverted dashed variables in steps-c/"
        return 1
    fi
}

test_ac3_no_dashed_variables_in_validate_steps() {
    local found_dashed=0

    for stepfile in "$TARGET_DIR"/steps-v/*.md; do
        if [[ -f "$stepfile" ]]; then
            if grep -qE '\{[a-z]+-[a-z-]+\}' "$stepfile" 2>/dev/null; then
                echo "  Found dashed variable in: $(basename "$stepfile")"
                found_dashed=1
            fi
        fi
    done

    if [[ $found_dashed -eq 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found unconverted dashed variables in steps-v/"
        return 1
    fi
}

test_ac3_no_dashed_variables_in_edit_steps() {
    local found_dashed=0

    for stepfile in "$TARGET_DIR"/steps-e/*.md; do
        if [[ -f "$stepfile" ]]; then
            if grep -qE '\{[a-z]+-[a-z-]+\}' "$stepfile" 2>/dev/null; then
                echo "  Found dashed variable in: $(basename "$stepfile")"
                found_dashed=1
            fi
        fi
    done

    if [[ $found_dashed -eq 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found unconverted dashed variables in steps-e/"
        return 1
    fi
}

test_ac3_preserves_non_variable_dashes() {
    # Filenames like step-01-init.md should keep their dashes
    assert_file_exists "$TARGET_DIR/steps-c/step-01-init.md" \
        "Step files should keep dashed names"
}

# =============================================================================
# AC4: Create mode (steps-c/) executes correctly
# =============================================================================

test_ac4_steps_c_directory_exists() {
    assert_dir_exists "$TARGET_DIR/steps-c" \
        "Create mode steps directory (steps-c/) should exist"
}

test_ac4_steps_c_has_correct_count() {
    # BMAD PRD has 13 create steps (including step-01b)
    local step_count
    step_count=$(find "$TARGET_DIR/steps-c" -maxdepth 1 -name "step-*.md" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$step_count" -ge 12 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected at least 12 create steps, found $step_count"
        return 1
    fi
}

test_ac4_steps_c_has_init_step() {
    assert_file_exists "$TARGET_DIR/steps-c/step-01-init.md" \
        "Create mode should have step-01-init.md"
}

test_ac4_steps_c_has_complete_step() {
    assert_file_exists "$TARGET_DIR/steps-c/step-12-complete.md" \
        "Create mode should have step-12-complete.md"
}

test_ac4_workflow_references_create_mode() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    assert_contains "$content" "create:" \
        "workflow.yaml modes should reference create"
}

# =============================================================================
# AC5: Validate mode (steps-v/) executes correctly
# =============================================================================

test_ac5_steps_v_directory_exists() {
    assert_dir_exists "$TARGET_DIR/steps-v" \
        "Validate mode steps directory (steps-v/) should exist"
}

test_ac5_steps_v_has_files() {
    local step_count
    step_count=$(find "$TARGET_DIR/steps-v" -maxdepth 1 -name "step-*.md" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$step_count" -gt 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected validate steps, found $step_count"
        return 1
    fi
}

test_ac5_steps_v_has_discovery_step() {
    assert_file_exists "$TARGET_DIR/steps-v/step-v-01-discovery.md" \
        "Validate mode should have step-v-01-discovery.md"
}

test_ac5_workflow_references_validate_mode() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    assert_contains "$content" "validate:" \
        "workflow.yaml modes should reference validate"
}

# =============================================================================
# AC6: Edit mode (steps-e/) executes correctly
# =============================================================================

test_ac6_steps_e_directory_exists() {
    assert_dir_exists "$TARGET_DIR/steps-e" \
        "Edit mode steps directory (steps-e/) should exist"
}

test_ac6_steps_e_has_files() {
    local step_count
    step_count=$(find "$TARGET_DIR/steps-e" -maxdepth 1 -name "step-*.md" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$step_count" -gt 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected edit steps, found $step_count"
        return 1
    fi
}

test_ac6_steps_e_has_discovery_step() {
    assert_file_exists "$TARGET_DIR/steps-e/step-e-01-discovery.md" \
        "Edit mode should have step-e-01-discovery.md"
}

test_ac6_workflow_references_edit_mode() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    assert_contains "$content" "edit:" \
        "workflow.yaml modes should reference edit"
}

# =============================================================================
# AC7: Gates pause for user approval at steps 2, 8, 12
# =============================================================================

test_ac7_workflow_has_gates_config() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "gates:" \
        "workflow.yaml should have gates configuration"
}

test_ac7_gates_has_after_steps() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "after_steps:" \
        "gates should have after_steps array"
}

test_ac7_gates_include_discovery() {
    # Gate after step 2 (discovery)
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Look for 2 in after_steps array
    if echo "$content" | grep -A5 "after_steps:" | grep -q "2"; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Gates should include step 2 (discovery)"
        return 1
    fi
}

test_ac7_gates_include_scoping() {
    # Gate after step 8 (scoping)
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if echo "$content" | grep -A10 "after_steps:" | grep -q "8"; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Gates should include step 8 (scoping)"
        return 1
    fi
}

test_ac7_gates_include_completion() {
    # Gate after step 12 (completion)
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if echo "$content" | grep -A15 "after_steps:" | grep -q "12"; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Gates should include step 12 (completion)"
        return 1
    fi
}

# =============================================================================
# AC8: Templates and data directories copied and accessible
# =============================================================================

test_ac8_templates_directory_exists() {
    assert_dir_exists "$TARGET_DIR/templates" \
        "Templates directory should exist"
}

test_ac8_data_directory_exists() {
    assert_dir_exists "$TARGET_DIR/data" \
        "Data directory should exist"
}

test_ac8_prd_template_exists() {
    # Check for a PRD template file
    local template_count
    template_count=$(find "$TARGET_DIR/templates" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$template_count" -gt 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected at least one template file in templates/"
        return 1
    fi
}

test_ac8_workflow_references_template() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    assert_contains "$content" "template:" \
        "workflow.yaml should reference template"
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=============================================="
echo "Story <PROJECT-KEY>: Import PRD Workflow Tests"
echo "=============================================="
echo ""

check_prerequisites

echo "AC1: Migration script converts PRD workflow from BMAD format"
run_test "migration completes (workflow dir exists)" test_ac1_migration_completes
run_test "workflow.yaml has name: prd" test_ac1_workflow_yaml_has_name
run_test "workflow.yaml has description" test_ac1_workflow_yaml_has_description
run_test "workflow.yaml has type: stepped" test_ac1_workflow_yaml_has_type_stepped

echo ""
echo "AC2: Generated workflow.yaml validates against schema"
run_test "schema validation passes" test_ac2_schema_validation_passes
run_test "has steps.path" test_ac2_has_steps_path
run_test "has steps.pattern" test_ac2_has_steps_pattern
run_test "has agent assignment" test_ac2_has_agent

echo ""
echo "AC3: Variable syntax converted"
run_test "no dashed variables in workflow.yaml" test_ac3_no_dashed_variables_in_workflow
run_test "no dashed variables in steps-c/" test_ac3_no_dashed_variables_in_create_steps
run_test "no dashed variables in steps-v/" test_ac3_no_dashed_variables_in_validate_steps
run_test "no dashed variables in steps-e/" test_ac3_no_dashed_variables_in_edit_steps
run_test "preserves non-variable dashes in filenames" test_ac3_preserves_non_variable_dashes

echo ""
echo "AC4: Create mode (steps-c/) executes correctly"
run_test "steps-c/ directory exists" test_ac4_steps_c_directory_exists
run_test "steps-c/ has correct step count" test_ac4_steps_c_has_correct_count
run_test "steps-c/ has init step" test_ac4_steps_c_has_init_step
run_test "steps-c/ has complete step" test_ac4_steps_c_has_complete_step
run_test "workflow references create mode" test_ac4_workflow_references_create_mode

echo ""
echo "AC5: Validate mode (steps-v/) executes correctly"
run_test "steps-v/ directory exists" test_ac5_steps_v_directory_exists
run_test "steps-v/ has files" test_ac5_steps_v_has_files
run_test "steps-v/ has discovery step" test_ac5_steps_v_has_discovery_step
run_test "workflow references validate mode" test_ac5_workflow_references_validate_mode

echo ""
echo "AC6: Edit mode (steps-e/) executes correctly"
run_test "steps-e/ directory exists" test_ac6_steps_e_directory_exists
run_test "steps-e/ has files" test_ac6_steps_e_has_files
run_test "steps-e/ has discovery step" test_ac6_steps_e_has_discovery_step
run_test "workflow references edit mode" test_ac6_workflow_references_edit_mode

echo ""
echo "AC7: Gates pause at steps 2, 8, 12"
run_test "workflow has gates config" test_ac7_workflow_has_gates_config
run_test "gates has after_steps" test_ac7_gates_has_after_steps
run_test "gates include step 2 (discovery)" test_ac7_gates_include_discovery
run_test "gates include step 8 (scoping)" test_ac7_gates_include_scoping
run_test "gates include step 12 (completion)" test_ac7_gates_include_completion

echo ""
echo "AC8: Templates and data directories accessible"
run_test "templates/ directory exists" test_ac8_templates_directory_exists
run_test "data/ directory exists" test_ac8_data_directory_exists
run_test "PRD template exists" test_ac8_prd_template_exists
run_test "workflow references template" test_ac8_workflow_references_template

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo -e "Tests run:    $TESTS_RUN"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "${RED}FAILED${NC} - $TESTS_FAILED test(s) failed"
    echo ""
    echo "This is expected in RED state - Dev needs to implement the migration."
    exit 1
else
    echo -e "${GREEN}PASSED${NC} - All tests passed"
    exit 0
fi
