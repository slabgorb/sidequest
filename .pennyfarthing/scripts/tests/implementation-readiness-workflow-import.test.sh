#!/usr/bin/env bash
# implementation-readiness-workflow-import.test.sh - Tests for Story <PROJECT-KEY>
#
# These tests verify that the BMAD implementation-readiness workflow is correctly
# imported into Pennyfarthing's stepped workflow format.
#
# Source: ~/Projects/BMAD-METHOD/src/modules/bmm/workflows/3-solutioning/check-implementation-readiness/
# Target: pennyfarthing-dist/workflows/implementation-readiness/
#
# This is a STEPPED workflow with 6 step files:
# - step-01-document-discovery.md
# - step-02-prd-analysis.md
# - step-03-epic-coverage-validation.md
# - step-04-ux-alignment.md
# - step-05-epic-quality-review.md
# - step-06-final-assessment.md
#
# AC1: pennyfarthing-dist/workflows/implementation-readiness/ directory created
# AC2: workflow.yaml with correct schema (name, description, type, steps)
# AC3: All 6 step files copied with variable syntax validated
# AC4: Template file(s) copied if present
# AC5: /workflow list shows implementation-readiness as available workflow
# AC6: Workflow purpose documented (BMAD reference)
#
# Run with: ./implementation-readiness-workflow-import.test.sh
# Or: bash implementation-readiness-workflow-import.test.sh

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
BMAD_SOURCE="${BMAD_IMPL_READINESS_SOURCE:-$HOME/Projects/BMAD-METHOD/src/modules/bmm/workflows/3-solutioning/check-implementation-readiness}"
TARGET_DIR="$PROJECT_ROOT/pennyfarthing-dist/workflows/implementation-readiness"

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
        echo -e "${RED}ERROR${NC}: BMAD implementation-readiness workflow source not found at: $BMAD_SOURCE"
        echo "Set BMAD_IMPL_READINESS_SOURCE environment variable to point to the BMAD workflow directory"
        exit 1
    fi

    if [[ ! -f "$BMAD_SOURCE/workflow.md" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD implementation-readiness workflow.md not found at: $BMAD_SOURCE/workflow.md"
        exit 1
    fi

    if [[ ! -d "$BMAD_SOURCE/steps" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD implementation-readiness steps directory not found"
        exit 1
    fi

    echo -e "${GREEN}OK${NC}: Prerequisites met"
    echo ""
}

# =============================================================================
# AC1: pennyfarthing-dist/workflows/implementation-readiness/ directory created
# =============================================================================

test_ac1_workflow_directory_exists() {
    assert_dir_exists "$TARGET_DIR" \
        "implementation-readiness workflow directory should exist at $TARGET_DIR"
}

test_ac1_workflow_yaml_exists() {
    assert_file_exists "$TARGET_DIR/workflow.yaml" \
        "workflow.yaml should exist in target directory"
}

test_ac1_steps_directory_exists() {
    assert_dir_exists "$TARGET_DIR/steps" \
        "steps/ directory should exist in target"
}

test_ac1_templates_directory_exists() {
    assert_dir_exists "$TARGET_DIR/templates" \
        "templates/ directory should exist in target"
}

# =============================================================================
# AC2: workflow.yaml with correct schema (name, description, type, steps)
# =============================================================================

test_ac2_workflow_yaml_has_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "name:" \
        "workflow.yaml should have name field"
}

test_ac2_workflow_yaml_has_correct_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "implementation-readiness" \
        "workflow.yaml should have implementation-readiness in name"
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
        "workflow.yaml should have type: stepped (6 sequential steps)"
}

test_ac2_workflow_yaml_has_steps_config() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "steps:" \
        "workflow.yaml should have steps configuration"
}

test_ac2_workflow_yaml_has_steps_path() {
    # The workflow should define where step files are located
    assert_file_contains "$TARGET_DIR/workflow.yaml" "path:" \
        "workflow.yaml should have steps path defined"
}

# =============================================================================
# AC3: All 6 step files copied with variable syntax validated
# =============================================================================

test_ac3_step_01_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-01-document-discovery.md" \
        "step-01-document-discovery.md should exist"
}

test_ac3_step_02_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-02-prd-analysis.md" \
        "step-02-prd-analysis.md should exist"
}

test_ac3_step_03_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-03-epic-coverage-validation.md" \
        "step-03-epic-coverage-validation.md should exist"
}

test_ac3_step_04_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-04-ux-alignment.md" \
        "step-04-ux-alignment.md should exist"
}

test_ac3_step_05_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-05-epic-quality-review.md" \
        "step-05-epic-quality-review.md should exist"
}

test_ac3_step_06_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-06-final-assessment.md" \
        "step-06-final-assessment.md should exist"
}

test_ac3_step_01_not_empty() {
    assert_file_not_empty "$TARGET_DIR/steps/step-01-document-discovery.md" \
        "step-01-document-discovery.md should have content"
}

test_ac3_step_06_not_empty() {
    assert_file_not_empty "$TARGET_DIR/steps/step-06-final-assessment.md" \
        "step-06-final-assessment.md should have content"
}

test_ac3_step_01_has_step_goal() {
    assert_file_contains "$TARGET_DIR/steps/step-01-document-discovery.md" "STEP GOAL" \
        "step-01 should have STEP GOAL section"
}

test_ac3_step_06_has_workflow_complete() {
    assert_file_contains "$TARGET_DIR/steps/step-06-final-assessment.md" "WORKFLOW COMPLETE" \
        "step-06 should indicate workflow completion"
}

test_ac3_step_count_is_6() {
    # Count step files in the steps directory
    local step_count
    step_count=$(find "$TARGET_DIR/steps" -name "step-*.md" 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$step_count" -eq 6 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected 6 step files, found $step_count"
        return 1
    fi
}

# =============================================================================
# AC4: Template file(s) copied if present
# =============================================================================

test_ac4_template_file_exists() {
    assert_file_exists "$TARGET_DIR/templates/readiness-report-template.md" \
        "readiness-report-template.md should be copied"
}

test_ac4_template_not_empty() {
    assert_file_not_empty "$TARGET_DIR/templates/readiness-report-template.md" \
        "template file should not be empty"
}

test_ac4_template_has_title() {
    assert_file_contains "$TARGET_DIR/templates/readiness-report-template.md" "Implementation Readiness" \
        "template should have Implementation Readiness title"
}

test_ac4_template_has_date_placeholder() {
    # Template should have {{date}} placeholder
    assert_file_contains "$TARGET_DIR/templates/readiness-report-template.md" "{{date}}" \
        "template should have {{date}} placeholder"
}

# =============================================================================
# AC5: /workflow list shows implementation-readiness as available workflow
# =============================================================================

test_ac5_workflow_yaml_valid_yaml() {
    # The workflow.yaml should be parseable as YAML
    if command -v yq &> /dev/null; then
        if yq '.' "$TARGET_DIR/workflow.yaml" > /dev/null 2>&1; then
            return 0
        else
            echo -e "${RED}FAIL${NC}: workflow.yaml is not valid YAML"
            return 1
        fi
    else
        # Skip if yq not available
        echo -e "${YELLOW}SKIP${NC}: yq not available for YAML validation"
        return 0
    fi
}

test_ac5_workflow_has_triggers() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "triggers:" \
        "workflow.yaml should have triggers section for workflow listing"
}

test_ac5_workflow_triggers_has_types() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "types:" \
        "workflow.yaml triggers should have types field"
}

test_ac5_workflow_triggers_has_on_demand() {
    # This workflow should be invokable on demand
    assert_file_contains "$TARGET_DIR/workflow.yaml" "on_demand" \
        "workflow.yaml triggers should include on_demand"
}

# =============================================================================
# AC6: Workflow purpose documented (BMAD reference)
# =============================================================================

test_ac6_workflow_description_mentions_bmad() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Should mention BMAD, reference, or compatibility
    if [[ "$content" == *"BMAD"* ]] || [[ "$content" == *"bmad"* ]] || \
       [[ "$content" == *"reference"* ]] || [[ "$content" == *"compat"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow.yaml should document BMAD origin/purpose"
        return 1
    fi
}

test_ac6_workflow_not_default() {
    # This workflow should NOT be a default workflow
    assert_file_not_contains "$TARGET_DIR/workflow.yaml" "default: true" \
        "implementation-readiness should not be default workflow"
}

test_ac6_workflow_has_comment_header() {
    # Should have a comment header explaining the workflow
    local first_line
    first_line=$(head -1 "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if [[ "$first_line" == "#"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow.yaml should have comment header explaining purpose"
        return 1
    fi
}

test_ac6_description_mentions_readiness_or_validation() {
    # Description should mention readiness check or validation
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if [[ "$content" == *"readiness"* ]] || [[ "$content" == *"validation"* ]] || \
       [[ "$content" == *"validate"* ]] || [[ "$content" == *"assessment"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow.yaml description should mention readiness/validation purpose"
        return 1
    fi
}

test_ac6_description_mentions_prd_or_architecture() {
    # Description should mention what it validates (PRD, Architecture, Epics)
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    if [[ "$content" == *"PRD"* ]] || [[ "$content" == *"Architecture"* ]] || \
       [[ "$content" == *"Epic"* ]] || [[ "$content" == *"implementation"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow.yaml description should mention PRD/Architecture/Epics"
        return 1
    fi
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=============================================="
echo "Story <PROJECT-KEY>: Import Implementation-Readiness Workflow Tests"
echo "=============================================="
echo ""

check_prerequisites

echo "AC1: pennyfarthing-dist/workflows/implementation-readiness/ directory created"
run_test "workflow directory exists" test_ac1_workflow_directory_exists
run_test "workflow.yaml exists" test_ac1_workflow_yaml_exists
run_test "steps/ directory exists" test_ac1_steps_directory_exists
run_test "templates/ directory exists" test_ac1_templates_directory_exists

echo ""
echo "AC2: workflow.yaml with correct schema (name, description, type, steps)"
run_test "workflow.yaml has name field" test_ac2_workflow_yaml_has_name
run_test "workflow.yaml has correct name" test_ac2_workflow_yaml_has_correct_name
run_test "workflow.yaml has description" test_ac2_workflow_yaml_has_description
run_test "workflow.yaml has type field" test_ac2_workflow_yaml_has_type
run_test "workflow.yaml has stepped type" test_ac2_workflow_yaml_has_stepped_type
run_test "workflow.yaml has steps config" test_ac2_workflow_yaml_has_steps_config
run_test "workflow.yaml has steps path" test_ac2_workflow_yaml_has_steps_path

echo ""
echo "AC3: All 6 step files copied with variable syntax validated"
run_test "step-01-document-discovery.md exists" test_ac3_step_01_exists
run_test "step-02-prd-analysis.md exists" test_ac3_step_02_exists
run_test "step-03-epic-coverage-validation.md exists" test_ac3_step_03_exists
run_test "step-04-ux-alignment.md exists" test_ac3_step_04_exists
run_test "step-05-epic-quality-review.md exists" test_ac3_step_05_exists
run_test "step-06-final-assessment.md exists" test_ac3_step_06_exists
run_test "step-01 has content" test_ac3_step_01_not_empty
run_test "step-06 has content" test_ac3_step_06_not_empty
run_test "step-01 has STEP GOAL section" test_ac3_step_01_has_step_goal
run_test "step-06 has WORKFLOW COMPLETE marker" test_ac3_step_06_has_workflow_complete
run_test "exactly 6 step files present" test_ac3_step_count_is_6

echo ""
echo "AC4: Template file(s) copied if present"
run_test "readiness-report-template.md exists" test_ac4_template_file_exists
run_test "template file has content" test_ac4_template_not_empty
run_test "template has correct title" test_ac4_template_has_title
run_test "template has date placeholder" test_ac4_template_has_date_placeholder

echo ""
echo "AC5: /workflow list shows implementation-readiness as available workflow"
run_test "workflow.yaml is valid YAML" test_ac5_workflow_yaml_valid_yaml
run_test "workflow.yaml has triggers section" test_ac5_workflow_has_triggers
run_test "triggers has types field" test_ac5_workflow_triggers_has_types
run_test "triggers includes on_demand" test_ac5_workflow_triggers_has_on_demand

echo ""
echo "AC6: Workflow purpose documented (BMAD reference)"
run_test "description mentions BMAD origin" test_ac6_workflow_description_mentions_bmad
run_test "workflow is not default" test_ac6_workflow_not_default
run_test "workflow.yaml has comment header" test_ac6_workflow_has_comment_header
run_test "description mentions readiness/validation" test_ac6_description_mentions_readiness_or_validation
run_test "description mentions PRD/Architecture/Epics" test_ac6_description_mentions_prd_or_architecture

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
