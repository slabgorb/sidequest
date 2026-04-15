#!/usr/bin/env bash
# project-context-workflow-import.test.sh - Tests for Story <PROJECT-KEY>: Import Project Context workflow
#
# These tests verify that the generate-project-context workflow from BMAD is correctly imported
# into Pennyfarthing's stepped workflow format.
#
# AC1: Migration script successfully imports workflow from BMAD source
# AC2: Generated workflow.yaml passes Pennyfarthing stepped workflow schema
# AC3: All BMAD-style dashed variables converted to underscore style
# AC4: /workflow start project-context lists correct 3 steps
# AC5: Template file copied and variables converted
# AC6: Workflow produces valid project-context.md output when run
#
# Run with: ./project-context-workflow-import.test.sh
# Or: bash project-context-workflow-import.test.sh

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
MIGRATE_SCRIPT="$SCRIPT_DIR/migrate-bmad-workflow.mjs"
BMAD_SOURCE="${BMAD_PROJECT_CONTEXT_SOURCE:-$HOME/Projects/BMAD-METHOD/src/modules/bmm/workflows/generate-project-context}"
TARGET_DIR="$PROJECT_ROOT/pennyfarthing-dist/workflows/project-context"

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

    if [[ ! -d "$BMAD_SOURCE" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD project-context workflow source not found at: $BMAD_SOURCE"
        echo "Set BMAD_PROJECT_CONTEXT_SOURCE environment variable to point to the BMAD workflow directory"
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
# AC1: Migration script successfully imports workflow from BMAD source
# =============================================================================

test_ac1_workflow_directory_exists() {
    # This test verifies the workflow was migrated to the target directory
    # EXPECTED: FAIL until Dev runs the migration

    if [[ ! -d "$TARGET_DIR" ]]; then
        echo -e "${RED}FAIL${NC}: project-context workflow not yet migrated to $TARGET_DIR"
        return 1
    fi
    return 0
}

test_ac1_workflow_yaml_exists() {
    assert_file_exists "$TARGET_DIR/workflow.yaml" \
        "Migration should produce workflow.yaml"
}

test_ac1_workflow_yaml_has_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "name: generate-project-context" \
        "workflow.yaml should have name: generate-project-context"
}

test_ac1_workflow_yaml_has_description() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "description:" \
        "workflow.yaml should have a description"
}

test_ac1_steps_directory_exists() {
    assert_dir_exists "$TARGET_DIR/steps" \
        "Steps directory should exist"
}

# =============================================================================
# AC2: Generated workflow.yaml passes Pennyfarthing stepped workflow schema
# =============================================================================

test_ac2_workflow_yaml_has_type_stepped() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "type: stepped" \
        "workflow.yaml should have type: stepped"
}

test_ac2_schema_has_steps_config() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

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
    # project-context workflow should have an agent assignment
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    assert_contains "$content" "agent:" \
        "workflow.yaml should have an agent assignment"
}

test_ac2_has_variables() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "variables:" \
        "workflow.yaml should have variables section"
}

# =============================================================================
# AC3: All BMAD-style dashed variables converted to underscore style
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

test_ac3_no_dashed_variables_in_steps() {
    # Check all step files in steps/ for unconverted variables
    local found_dashed=0

    for stepfile in "$TARGET_DIR"/steps/*.md; do
        if [[ -f "$stepfile" ]]; then
            # Look for dashed variables like {var-name}
            if grep -qE '\{[a-z]+-[a-z-]+\}' "$stepfile" 2>/dev/null; then
                echo "  Found dashed variable in: $(basename "$stepfile")"
                found_dashed=1
            fi
        fi
    done

    if [[ $found_dashed -eq 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found unconverted dashed variables in steps/"
        return 1
    fi
}

test_ac3_project_root_converted() {
    # Check that {project-root} is converted to {project_root}
    local found_old=0

    for file in "$TARGET_DIR"/steps/*.md "$TARGET_DIR/workflow.yaml"; do
        if [[ -f "$file" ]]; then
            if grep -q '{project-root}' "$file" 2>/dev/null; then
                found_old=1
            fi
        fi
    done

    if [[ $found_old -eq 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found unconverted {project-root} variable"
        return 1
    fi
}

test_ac3_user_skill_level_converted() {
    # Check that {user-skill-level} is converted to {user_skill_level}
    local found_old=0

    for file in "$TARGET_DIR"/steps/*.md; do
        if [[ -f "$file" ]]; then
            if grep -q '{user-skill-level}' "$file" 2>/dev/null; then
                found_old=1
            fi
        fi
    done

    if [[ $found_old -eq 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found unconverted {user-skill-level} variable"
        return 1
    fi
}

test_ac3_communication_language_converted() {
    # Check that {communication-language} is converted to {communication_language}
    local found_old=0

    for file in "$TARGET_DIR"/steps/*.md; do
        if [[ -f "$file" ]]; then
            if grep -q '{communication-language}' "$file" 2>/dev/null; then
                found_old=1
            fi
        fi
    done

    if [[ $found_old -eq 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Found unconverted {communication-language} variable"
        return 1
    fi
}

test_ac3_preserves_non_variable_dashes() {
    # Filenames like step-01-discover.md should keep their dashes
    assert_file_exists "$TARGET_DIR/steps/step-01-discover.md" \
        "Step files should keep dashed names"
}

# =============================================================================
# AC4: /workflow start project-context lists correct 3 steps
# =============================================================================

test_ac4_has_step_01_discover() {
    assert_file_exists "$TARGET_DIR/steps/step-01-discover.md" \
        "Should have step-01-discover.md"
}

test_ac4_has_step_02_generate() {
    assert_file_exists "$TARGET_DIR/steps/step-02-generate.md" \
        "Should have step-02-generate.md"
}

test_ac4_has_step_03_complete() {
    assert_file_exists "$TARGET_DIR/steps/step-03-complete.md" \
        "Should have step-03-complete.md"
}

test_ac4_step_count_is_3() {
    local step_count
    step_count=$(find "$TARGET_DIR/steps" -maxdepth 1 -name "step-*.md" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$step_count" -eq 3 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected exactly 3 steps, found $step_count"
        return 1
    fi
}

test_ac4_steps_path_correct() {
    # workflow.yaml steps.path should point to ./steps/
    assert_file_contains "$TARGET_DIR/workflow.yaml" "./steps/" \
        "Steps path should be ./steps/"
}

# =============================================================================
# AC5: Template file copied and variables converted
# =============================================================================

test_ac5_template_file_exists() {
    assert_file_exists "$TARGET_DIR/project-context-template.md" \
        "project-context-template.md should exist"
}

test_ac5_template_has_content() {
    # Template should have the Project Context header
    assert_file_contains "$TARGET_DIR/project-context-template.md" "Project Context" \
        "Template should have Project Context header"
}

test_ac5_template_variables_converted() {
    # Template variables should be converted
    local content
    content=$(cat "$TARGET_DIR/project-context-template.md" 2>/dev/null || echo "")

    # Should NOT have dashed variables
    assert_not_contains "$content" "{project-name}" \
        "Template should not have {project-name}"
}

test_ac5_template_has_sections() {
    # Template should have expected sections
    assert_file_contains "$TARGET_DIR/project-context-template.md" "Technology Stack" \
        "Template should have Technology Stack section"
}

# =============================================================================
# AC6: Workflow produces valid project-context.md output when run
# (This test validates the workflow structure can produce valid output)
# =============================================================================

test_ac6_workflow_has_output_file_variable() {
    # workflow.yaml should define output_file variable
    assert_file_contains "$TARGET_DIR/workflow.yaml" "output_file:" \
        "workflow.yaml should have output_file variable"
}

test_ac6_step_01_has_discovery_section() {
    # Step 1 should contain discovery logic
    assert_file_contains "$TARGET_DIR/steps/step-01-discover.md" "Discovery" \
        "Step 1 should have discovery content"
}

test_ac6_step_02_has_generation_section() {
    # Step 2 should contain generation logic
    assert_file_contains "$TARGET_DIR/steps/step-02-generate.md" "Generate" \
        "Step 2 should have generation content"
}

test_ac6_step_03_has_completion_section() {
    # Step 3 should contain completion logic
    assert_file_contains "$TARGET_DIR/steps/step-03-complete.md" "Complete" \
        "Step 3 should have completion content"
}

test_ac6_workflow_is_single_mode() {
    # This workflow should NOT have tri-modal structure (steps-c/v/e)
    if [[ -d "$TARGET_DIR/steps-c" ]] || [[ -d "$TARGET_DIR/steps-v" ]] || [[ -d "$TARGET_DIR/steps-e" ]]; then
        echo -e "${RED}FAIL${NC}: project-context workflow should be single-mode, not tri-modal"
        return 1
    fi
    return 0
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=============================================="
echo "Story <PROJECT-KEY>: Import Project Context Workflow Tests"
echo "=============================================="
echo ""

check_prerequisites

echo "AC1: Migration script successfully imports workflow from BMAD source"
run_test "workflow directory exists" test_ac1_workflow_directory_exists
run_test "workflow.yaml exists" test_ac1_workflow_yaml_exists
run_test "workflow.yaml has name" test_ac1_workflow_yaml_has_name
run_test "workflow.yaml has description" test_ac1_workflow_yaml_has_description
run_test "steps directory exists" test_ac1_steps_directory_exists

echo ""
echo "AC2: Generated workflow.yaml passes Pennyfarthing stepped workflow schema"
run_test "workflow.yaml has type: stepped" test_ac2_workflow_yaml_has_type_stepped
run_test "has steps configuration" test_ac2_schema_has_steps_config
run_test "has steps.path" test_ac2_has_steps_path
run_test "has steps.pattern" test_ac2_has_steps_pattern
run_test "has agent assignment" test_ac2_has_agent
run_test "has variables section" test_ac2_has_variables

echo ""
echo "AC3: All BMAD-style dashed variables converted to underscore style"
run_test "no dashed variables in workflow.yaml" test_ac3_no_dashed_variables_in_workflow
run_test "no dashed variables in steps" test_ac3_no_dashed_variables_in_steps
run_test "{project-root} converted" test_ac3_project_root_converted
run_test "{user-skill-level} converted" test_ac3_user_skill_level_converted
run_test "{communication-language} converted" test_ac3_communication_language_converted
run_test "preserves non-variable dashes in filenames" test_ac3_preserves_non_variable_dashes

echo ""
echo "AC4: /workflow start project-context lists correct 3 steps"
run_test "has step-01-discover.md" test_ac4_has_step_01_discover
run_test "has step-02-generate.md" test_ac4_has_step_02_generate
run_test "has step-03-complete.md" test_ac4_has_step_03_complete
run_test "step count is 3" test_ac4_step_count_is_3
run_test "steps path correct" test_ac4_steps_path_correct

echo ""
echo "AC5: Template file copied and variables converted"
run_test "template file exists" test_ac5_template_file_exists
run_test "template has content" test_ac5_template_has_content
run_test "template variables converted" test_ac5_template_variables_converted
run_test "template has expected sections" test_ac5_template_has_sections

echo ""
echo "AC6: Workflow produces valid project-context.md output when run"
run_test "workflow has output_file variable" test_ac6_workflow_has_output_file_variable
run_test "step 1 has discovery content" test_ac6_step_01_has_discovery_section
run_test "step 2 has generation content" test_ac6_step_02_has_generation_section
run_test "step 3 has completion content" test_ac6_step_03_has_completion_section
run_test "workflow is single-mode (not tri-modal)" test_ac6_workflow_is_single_mode

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
    echo "This is expected in RED state - Dev needs to run the migration script."
    exit 1
else
    echo -e "${GREEN}PASSED${NC} - All tests passed"
    exit 0
fi
