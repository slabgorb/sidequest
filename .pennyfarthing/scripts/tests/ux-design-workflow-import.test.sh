#!/usr/bin/env bash
# ux-design-workflow-import.test.sh - Tests for Story <PROJECT-KEY>
#
# These tests verify that the BMAD UX Design workflow is correctly
# imported into Pennyfarthing's stepped workflow format.
#
# Source: ~/Projects/BMAD-METHOD/src/modules/bmm/workflows/2-plan-workflows/create-ux-design/
# Target: pennyfarthing-dist/workflows/ux-design/
#
# This is a SINGLE-MODE STEPPED workflow with 14 step files:
# - step-01-init.md through step-14-complete.md
# - step-01b-continue.md (continuation handler)
# - ux-design-template.md (output template)
#
# AC1: pennyfarthing-dist/workflows/ux-design/ directory created
# AC2: workflow.yaml with correct schema (name, description, type: stepped, steps)
# AC3: All 14 step files copied with variable syntax validated
# AC4: Template file (ux-design-template.md) copied
# AC5: Continuation handler (step-01b-continue.md) copied
# AC6: /workflow list shows ux-design as available workflow
# AC7: Workflow can be started with /workflow start ux-design
#
# Run with: ./ux-design-workflow-import.test.sh
# Or: bash ux-design-workflow-import.test.sh

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
BMAD_SOURCE="${BMAD_UX_DESIGN_SOURCE:-$HOME/Projects/BMAD-METHOD/src/modules/bmm/workflows/2-plan-workflows/create-ux-design}"
TARGET_DIR="$PROJECT_ROOT/pennyfarthing-dist/workflows/ux-design"

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

assert_file_not_empty() {
    local filepath="$1"
    local message="${2:-File should not be empty}"

    if [[ ! -f "$filepath" ]]; then
        echo -e "${RED}FAIL${NC}: $message"
        echo "  File not found: $filepath"
        return 1
    fi

    if [[ -s "$filepath" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: $message"
        echo "  File is empty: $filepath"
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

    if [[ ! -d "$BMAD_SOURCE" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD UX Design workflow source not found at: $BMAD_SOURCE"
        echo "Set BMAD_UX_DESIGN_SOURCE environment variable to point to the BMAD workflow directory"
        exit 1
    fi

    if [[ ! -f "$BMAD_SOURCE/workflow.md" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD UX Design workflow.md not found at: $BMAD_SOURCE/workflow.md"
        exit 1
    fi

    if [[ ! -d "$BMAD_SOURCE/steps" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD UX Design steps directory not found"
        exit 1
    fi

    echo -e "${GREEN}OK${NC}: Prerequisites met"
    echo ""
}

# =============================================================================
# AC1: pennyfarthing-dist/workflows/ux-design/ directory created
# =============================================================================

test_ac1_workflow_directory_exists() {
    assert_dir_exists "$TARGET_DIR" \
        "ux-design workflow directory should exist at $TARGET_DIR"
}

test_ac1_workflow_yaml_exists() {
    assert_file_exists "$TARGET_DIR/workflow.yaml" \
        "workflow.yaml should exist in target directory"
}

test_ac1_steps_directory_exists() {
    assert_dir_exists "$TARGET_DIR/steps" \
        "steps/ directory should exist in target"
}

# =============================================================================
# AC2: workflow.yaml with correct schema (name, description, type: stepped, steps)
# =============================================================================

test_ac2_workflow_yaml_has_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "name:" \
        "workflow.yaml should have name field"
}

test_ac2_workflow_yaml_has_ux_design_name() {
    # The workflow should be named ux-design or create-ux-design
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if [[ "$content" == *"ux-design"* ]] || [[ "$content" == *"create-ux-design"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow.yaml should have ux-design in name"
        return 1
    fi
}

test_ac2_workflow_yaml_has_description() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "description:" \
        "workflow.yaml should have description field"
}

test_ac2_workflow_yaml_has_type() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "type:" \
        "workflow.yaml should have type field"
}

test_ac2_workflow_yaml_has_stepped_type() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "stepped" \
        "workflow.yaml should have type: stepped (14 sequential steps)"
}

test_ac2_workflow_yaml_has_steps_config() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "steps:" \
        "workflow.yaml should have steps configuration"
}

test_ac2_workflow_yaml_has_steps_path() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "path:" \
        "workflow.yaml should have steps path defined"
}

test_ac2_workflow_yaml_has_agent() {
    # UX Design workflow should be assigned to ux-designer agent
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if [[ "$content" == *"ux-designer"* ]] || [[ "$content" == *"agent:"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow.yaml should have agent assignment"
        return 1
    fi
}

# =============================================================================
# AC3: All 14 step files copied with variable syntax validated
# =============================================================================

test_ac3_step_01_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-01-init.md" \
        "step-01-init.md should exist"
}

test_ac3_step_02_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-02-discovery.md" \
        "step-02-discovery.md should exist"
}

test_ac3_step_03_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-03-core-experience.md" \
        "step-03-core-experience.md should exist"
}

test_ac3_step_04_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-04-emotional-response.md" \
        "step-04-emotional-response.md should exist"
}

test_ac3_step_05_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-05-inspiration.md" \
        "step-05-inspiration.md should exist"
}

test_ac3_step_06_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-06-design-system.md" \
        "step-06-design-system.md should exist"
}

test_ac3_step_07_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-07-defining-experience.md" \
        "step-07-defining-experience.md should exist"
}

test_ac3_step_08_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-08-visual-foundation.md" \
        "step-08-visual-foundation.md should exist"
}

test_ac3_step_09_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-09-design-directions.md" \
        "step-09-design-directions.md should exist"
}

test_ac3_step_10_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-10-user-journeys.md" \
        "step-10-user-journeys.md should exist"
}

test_ac3_step_11_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-11-component-strategy.md" \
        "step-11-component-strategy.md should exist"
}

test_ac3_step_12_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-12-ux-patterns.md" \
        "step-12-ux-patterns.md should exist"
}

test_ac3_step_13_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-13-responsive-accessibility.md" \
        "step-13-responsive-accessibility.md should exist"
}

test_ac3_step_14_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-14-complete.md" \
        "step-14-complete.md should exist"
}

test_ac3_step_01_not_empty() {
    assert_file_not_empty "$TARGET_DIR/steps/step-01-init.md" \
        "step-01-init.md should have content"
}

test_ac3_step_14_not_empty() {
    assert_file_not_empty "$TARGET_DIR/steps/step-14-complete.md" \
        "step-14-complete.md should have content"
}

test_ac3_step_count_is_14() {
    # Count step files in the steps directory (excluding step-01b-continue.md)
    local step_count
    step_count=$(find "$TARGET_DIR/steps" -name "step-[0-9]*.md" ! -name "step-*b-*.md" 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$step_count" -eq 14 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected 14 step files, found $step_count"
        return 1
    fi
}

test_ac3_no_dashed_variables() {
    # Check that BMAD-style dashed variables {var-name} have been converted
    # to Pennyfarthing underscore style {var_name}
    local dashed_vars
    dashed_vars=$(grep -r '\{[a-zA-Z0-9_]*-[a-zA-Z0-9_-]*\}' "$TARGET_DIR/steps/" 2>/dev/null || echo "")

    if [[ -z "$dashed_vars" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found BMAD-style dashed variables that should be converted to underscores"
        echo "  Found: ${dashed_vars:0:100}..."
        return 1
    fi
}

# =============================================================================
# AC4: Template file (ux-design-template.md) copied
# =============================================================================

test_ac4_template_file_exists() {
    assert_file_exists "$TARGET_DIR/ux-design-template.md" \
        "ux-design-template.md should be copied"
}

test_ac4_template_not_empty() {
    assert_file_not_empty "$TARGET_DIR/ux-design-template.md" \
        "template file should not be empty"
}

test_ac4_template_has_ux_content() {
    # Template should have UX-related content
    local content
    content=$(cat "$TARGET_DIR/ux-design-template.md" 2>/dev/null || echo "")

    if [[ "$content" == *"UX"* ]] || [[ "$content" == *"design"* ]] || \
       [[ "$content" == *"Design"* ]] || [[ "$content" == *"user"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: template should have UX/design content"
        return 1
    fi
}

# =============================================================================
# AC5: Continuation handler (step-01b-continue.md) copied
# =============================================================================

test_ac5_continuation_handler_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-01b-continue.md" \
        "step-01b-continue.md should be copied"
}

test_ac5_continuation_handler_not_empty() {
    assert_file_not_empty "$TARGET_DIR/steps/step-01b-continue.md" \
        "continuation handler should have content"
}

test_ac5_continuation_handler_has_continue_logic() {
    # Should have content about resuming/continuing
    local content
    content=$(cat "$TARGET_DIR/steps/step-01b-continue.md" 2>/dev/null || echo "")

    if [[ "$content" == *"continu"* ]] || [[ "$content" == *"resum"* ]] || \
       [[ "$content" == *"existing"* ]] || [[ "$content" == *"previous"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: continuation handler should have resume/continue logic"
        return 1
    fi
}

# =============================================================================
# AC6: /workflow list shows ux-design as available workflow
# =============================================================================

test_ac6_workflow_yaml_valid_yaml() {
    if command -v yq &> /dev/null; then
        if yq '.' "$TARGET_DIR/workflow.yaml" > /dev/null 2>&1; then
            return 0
        else
            echo -e "${RED}FAIL${NC}: workflow.yaml is not valid YAML"
            return 1
        fi
    else
        echo -e "${YELLOW}SKIP${NC}: yq not available for YAML validation"
        return 0
    fi
}

test_ac6_workflow_has_triggers() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "triggers:" \
        "workflow.yaml should have triggers section for workflow listing"
}

test_ac6_workflow_triggers_has_types() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "types:" \
        "workflow.yaml triggers should have types field"
}

test_ac6_workflow_triggers_has_ux_design() {
    # Triggers should include ux-design for discoverability
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if [[ "$content" == *"ux-design"* ]] || [[ "$content" == *"ux_design"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow.yaml triggers should include ux-design"
        return 1
    fi
}

# =============================================================================
# AC7: Workflow can be started with /workflow start ux-design
# =============================================================================

test_ac7_workflow_has_version() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "version:" \
        "workflow.yaml should have version field"
}

test_ac7_workflow_has_variables() {
    # Workflow should define variables for step files
    assert_file_contains "$TARGET_DIR/workflow.yaml" "variables:" \
        "workflow.yaml should have variables section"
}

test_ac7_first_step_is_init() {
    # First step should be step-01-init.md for proper startup
    assert_file_exists "$TARGET_DIR/steps/step-01-init.md" \
        "first step (step-01-init.md) should exist for workflow start"
}

test_ac7_last_step_is_complete() {
    # Last step should be step-14-complete.md
    assert_file_exists "$TARGET_DIR/steps/step-14-complete.md" \
        "last step (step-14-complete.md) should exist"
}

test_ac7_steps_pattern_matches() {
    # workflow.yaml should have pattern that matches step files
    assert_file_contains "$TARGET_DIR/workflow.yaml" "step-*.md" \
        "workflow.yaml should have pattern: step-*.md"
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=============================================="
echo "Story <PROJECT-KEY>: Import UX Design Workflow Tests"
echo "=============================================="
echo ""

check_prerequisites

echo "AC1: pennyfarthing-dist/workflows/ux-design/ directory created"
run_test "workflow directory exists" test_ac1_workflow_directory_exists
run_test "workflow.yaml exists" test_ac1_workflow_yaml_exists
run_test "steps/ directory exists" test_ac1_steps_directory_exists

echo ""
echo "AC2: workflow.yaml with correct schema (name, description, type: stepped, steps)"
run_test "workflow.yaml has name field" test_ac2_workflow_yaml_has_name
run_test "workflow.yaml has ux-design name" test_ac2_workflow_yaml_has_ux_design_name
run_test "workflow.yaml has description" test_ac2_workflow_yaml_has_description
run_test "workflow.yaml has type field" test_ac2_workflow_yaml_has_type
run_test "workflow.yaml has stepped type" test_ac2_workflow_yaml_has_stepped_type
run_test "workflow.yaml has steps config" test_ac2_workflow_yaml_has_steps_config
run_test "workflow.yaml has steps path" test_ac2_workflow_yaml_has_steps_path
run_test "workflow.yaml has agent assignment" test_ac2_workflow_yaml_has_agent

echo ""
echo "AC3: All 14 step files copied with variable syntax validated"
run_test "step-01-init.md exists" test_ac3_step_01_exists
run_test "step-02-discovery.md exists" test_ac3_step_02_exists
run_test "step-03-core-experience.md exists" test_ac3_step_03_exists
run_test "step-04-emotional-response.md exists" test_ac3_step_04_exists
run_test "step-05-inspiration.md exists" test_ac3_step_05_exists
run_test "step-06-design-system.md exists" test_ac3_step_06_exists
run_test "step-07-defining-experience.md exists" test_ac3_step_07_exists
run_test "step-08-visual-foundation.md exists" test_ac3_step_08_exists
run_test "step-09-design-directions.md exists" test_ac3_step_09_exists
run_test "step-10-user-journeys.md exists" test_ac3_step_10_exists
run_test "step-11-component-strategy.md exists" test_ac3_step_11_exists
run_test "step-12-ux-patterns.md exists" test_ac3_step_12_exists
run_test "step-13-responsive-accessibility.md exists" test_ac3_step_13_exists
run_test "step-14-complete.md exists" test_ac3_step_14_exists
run_test "step-01 has content" test_ac3_step_01_not_empty
run_test "step-14 has content" test_ac3_step_14_not_empty
run_test "exactly 14 step files present" test_ac3_step_count_is_14
run_test "no dashed variables (converted to underscores)" test_ac3_no_dashed_variables

echo ""
echo "AC4: Template file (ux-design-template.md) copied"
run_test "ux-design-template.md exists" test_ac4_template_file_exists
run_test "template file has content" test_ac4_template_not_empty
run_test "template has UX content" test_ac4_template_has_ux_content

echo ""
echo "AC5: Continuation handler (step-01b-continue.md) copied"
run_test "step-01b-continue.md exists" test_ac5_continuation_handler_exists
run_test "continuation handler has content" test_ac5_continuation_handler_not_empty
run_test "continuation handler has continue logic" test_ac5_continuation_handler_has_continue_logic

echo ""
echo "AC6: /workflow list shows ux-design as available workflow"
run_test "workflow.yaml is valid YAML" test_ac6_workflow_yaml_valid_yaml
run_test "workflow.yaml has triggers section" test_ac6_workflow_has_triggers
run_test "triggers has types field" test_ac6_workflow_triggers_has_types
run_test "triggers includes ux-design" test_ac6_workflow_triggers_has_ux_design

echo ""
echo "AC7: Workflow can be started with /workflow start ux-design"
run_test "workflow.yaml has version" test_ac7_workflow_has_version
run_test "workflow.yaml has variables" test_ac7_workflow_has_variables
run_test "first step is step-01-init.md" test_ac7_first_step_is_init
run_test "last step is step-14-complete.md" test_ac7_last_step_is_complete
run_test "steps pattern matches step-*.md" test_ac7_steps_pattern_matches

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
    echo "This is expected in RED state - Dev needs to import the workflow."
    exit 1
else
    echo -e "${GREEN}PASSED${NC} - All tests passed"
    exit 0
fi
