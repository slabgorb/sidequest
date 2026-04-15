#!/usr/bin/env bash
# epics-and-stories-workflow-import.test.sh - Tests for Story <PROJECT-KEY>: Import Epics-and-Stories workflow
#
# These tests verify that the create-epics-and-stories workflow from BMAD is correctly imported
# into Pennyfarthing's stepped workflow format.
#
# AC1: Migration script runs without errors on source workflow
# AC2: Generated workflow.yaml validates against Pennyfarthing schema
# AC3: All variable syntax converted ({var-name} → {var_name})
# AC4: /workflow list shows new workflow with correct metadata
# AC5: /workflow start epics-and-stories loads step 1 correctly
# AC6: Step transitions work with menu-based gates
# AC7: Template placeholders preserved for runtime substitution
#
# Run with: ./epics-and-stories-workflow-import.test.sh
# Or: bash epics-and-stories-workflow-import.test.sh

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
BMAD_SOURCE="${BMAD_SOURCE:-$HOME/Projects/BMAD-METHOD/src/modules/bmm/workflows/3-solutioning/create-epics-and-stories}"
TARGET_DIR="$PROJECT_ROOT/pennyfarthing-dist/workflows/epics-and-stories"

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
        echo -e "${RED}ERROR${NC}: BMAD epics-and-stories workflow source not found at: $BMAD_SOURCE"
        echo "Set BMAD_SOURCE environment variable to point to the BMAD create-epics-and-stories workflow directory"
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
# AC1: Migration script runs without errors on source workflow
# =============================================================================

test_ac1_workflow_directory_exists() {
    # This test verifies the migration completed successfully
    # EXPECTED: FAIL until Dev runs the migration

    if [[ ! -d "$TARGET_DIR" ]]; then
        echo -e "${RED}FAIL${NC}: Workflow not yet migrated to $TARGET_DIR"
        return 1
    fi
    return 0
}

test_ac1_workflow_yaml_exists() {
    assert_file_exists "$TARGET_DIR/workflow.yaml" \
        "Migration should produce workflow.yaml"
}

test_ac1_workflow_yaml_has_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "name:" \
        "workflow.yaml should have name field"
}

test_ac1_workflow_yaml_has_description() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "description:" \
        "workflow.yaml should have a description"
}

test_ac1_steps_directory_exists() {
    assert_dir_exists "$TARGET_DIR/steps" \
        "Steps directory should exist"
}

test_ac1_has_four_step_files() {
    local step_count
    step_count=$(find "$TARGET_DIR/steps" -maxdepth 1 -name "step-*.md" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$step_count" -eq 4 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected 4 step files, found $step_count"
        return 1
    fi
}

# =============================================================================
# AC2: Generated workflow.yaml validates against Pennyfarthing schema
# =============================================================================

test_ac2_has_workflow_root_key() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "workflow:" \
        "workflow.yaml should have workflow: root key"
}

test_ac2_has_type_stepped() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "type: stepped" \
        "workflow.yaml should have type: stepped"
}

test_ac2_has_steps_config() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "steps:" \
        "workflow.yaml should have steps configuration"
}

test_ac2_has_steps_path() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "path:" \
        "workflow.yaml should have steps.path"
}

test_ac2_has_steps_pattern() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "pattern:" \
        "workflow.yaml should have steps.pattern"
}

test_ac2_has_agent_assignment() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "agent:" \
        "workflow.yaml should have an agent assignment"
}

test_ac2_has_triggers() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "triggers:" \
        "workflow.yaml should have triggers configuration"
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

test_ac3_no_dashed_variables_in_steps() {
    # Check all step files for unconverted variables
    local found_dashed=0

    for stepfile in "$TARGET_DIR"/steps/*.md; do
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
        echo -e "${RED}FAIL${NC}: Found unconverted dashed variables in steps/"
        return 1
    fi
}

test_ac3_has_underscored_variables() {
    # Verify underscored variables are present (positive check)
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Should have converted variables like project_root, planning_artifacts
    assert_contains "$content" "project_root" \
        "Should have underscored variables like project_root"
}

test_ac3_preserves_non_variable_dashes() {
    # Filenames like step-01-validate-prerequisites.md should keep their dashes
    assert_file_exists "$TARGET_DIR/steps/step-01-validate-prerequisites.md" \
        "Step files should keep dashed names"
}

# =============================================================================
# AC4: /workflow list shows new workflow with correct metadata
# =============================================================================

test_ac4_workflow_name_is_correct() {
    # Verify the workflow name matches expected value
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Name should be epics-and-stories or create-epics-and-stories
    if [[ "$content" == *"name: epics-and-stories"* ]] || \
       [[ "$content" == *"name: create-epics-and-stories"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: workflow name should be 'epics-and-stories' or 'create-epics-and-stories'"
        return 1
    fi
}

test_ac4_description_mentions_epics() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Description should mention epics and/or stories
    if [[ "$content" == *"epic"* ]] || [[ "$content" == *"Epic"* ]] || \
       [[ "$content" == *"story"* ]] || [[ "$content" == *"Story"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: description should mention epics or stories"
        return 1
    fi
}

test_ac4_version_is_present() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "version:" \
        "workflow.yaml should have version field"
}

# =============================================================================
# AC5: /workflow start epics-and-stories loads step 1 correctly
# =============================================================================

test_ac5_step1_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-01-validate-prerequisites.md" \
        "Step 1 (validate-prerequisites) should exist"
}

test_ac5_step1_has_frontmatter() {
    assert_file_contains "$TARGET_DIR/steps/step-01-validate-prerequisites.md" "---" \
        "Step 1 should have YAML frontmatter"
}

test_ac5_step1_has_name() {
    assert_file_contains "$TARGET_DIR/steps/step-01-validate-prerequisites.md" "name:" \
        "Step 1 should have name in frontmatter"
}

test_ac5_step1_has_description() {
    assert_file_contains "$TARGET_DIR/steps/step-01-validate-prerequisites.md" "description:" \
        "Step 1 should have description in frontmatter"
}

test_ac5_step1_references_next_step() {
    assert_file_contains "$TARGET_DIR/steps/step-01-validate-prerequisites.md" "nextStepFile:" \
        "Step 1 should reference next step file"
}

# =============================================================================
# AC6: Step transitions work with menu-based gates
# =============================================================================

test_ac6_step2_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-02-design-epics.md" \
        "Step 2 (design-epics) should exist"
}

test_ac6_step3_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-03-create-stories.md" \
        "Step 3 (create-stories) should exist"
}

test_ac6_step4_exists() {
    assert_file_exists "$TARGET_DIR/steps/step-04-final-validation.md" \
        "Step 4 (final-validation) should exist"
}

test_ac6_steps_have_menu_markers() {
    # Check that steps have menu/gate markers for user confirmation
    local steps_with_menu=0

    for stepfile in "$TARGET_DIR"/steps/*.md; do
        if [[ -f "$stepfile" ]]; then
            # Look for menu patterns: [C], Continue, MENU, menu
            if grep -qiE '(\[C\]|Continue|MENU|menu|halt|wait)' "$stepfile" 2>/dev/null; then
                steps_with_menu=$((steps_with_menu + 1))
            fi
        fi
    done

    if [[ $steps_with_menu -gt 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected steps to have menu/gate markers"
        return 1
    fi
}

test_ac6_workflow_has_gates_config() {
    # Optional: workflow.yaml may have explicit gates configuration
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # Gates are optional for this workflow - if present, validate
    if [[ "$content" == *"gates:"* ]]; then
        assert_contains "$content" "after_steps:" \
            "If gates present, should have after_steps"
    else
        # No explicit gates - that's OK, menu-based gates are in the steps themselves
        return 0
    fi
}

# =============================================================================
# AC7: Template placeholders preserved for runtime substitution
# =============================================================================

test_ac7_templates_directory_exists() {
    assert_dir_exists "$TARGET_DIR/templates" \
        "Templates directory should exist"
}

test_ac7_epics_template_exists() {
    assert_file_exists "$TARGET_DIR/templates/epics-template.md" \
        "epics-template.md should exist"
}

test_ac7_template_has_placeholders() {
    local content
    content=$(cat "$TARGET_DIR/templates/epics-template.md" 2>/dev/null || echo "")

    # Template should have placeholder syntax like {{placeholder}}
    if [[ "$content" == *"{{"* ]] && [[ "$content" == *"}}"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Template should have {{placeholder}} syntax"
        return 1
    fi
}

test_ac7_template_has_project_name_placeholder() {
    assert_file_contains "$TARGET_DIR/templates/epics-template.md" "{{project_name}}" \
        "Template should have {{project_name}} placeholder"
}

test_ac7_template_has_epics_list_placeholder() {
    assert_file_contains "$TARGET_DIR/templates/epics-template.md" "{{epics_list}}" \
        "Template should have {{epics_list}} placeholder"
}

test_ac7_workflow_references_template() {
    local content
    content=$(cat "$TARGET_DIR/workflow.yaml" 2>/dev/null || echo "")

    # workflow.yaml may reference template - optional but good practice
    if [[ "$content" == *"template:"* ]] || [[ "$content" == *"templates/"* ]]; then
        return 0
    else
        # Template reference not required but steps should reference it
        return 0
    fi
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=============================================="
echo "Story <PROJECT-KEY>: Import Epics-and-Stories Workflow Tests"
echo "=============================================="
echo ""

check_prerequisites

echo "AC1: Migration script runs without errors on source workflow"
run_test "workflow directory exists" test_ac1_workflow_directory_exists
run_test "workflow.yaml exists" test_ac1_workflow_yaml_exists
run_test "workflow.yaml has name" test_ac1_workflow_yaml_has_name
run_test "workflow.yaml has description" test_ac1_workflow_yaml_has_description
run_test "steps/ directory exists" test_ac1_steps_directory_exists
run_test "has 4 step files" test_ac1_has_four_step_files

echo ""
echo "AC2: Generated workflow.yaml validates against Pennyfarthing schema"
run_test "has workflow: root key" test_ac2_has_workflow_root_key
run_test "has type: stepped" test_ac2_has_type_stepped
run_test "has steps config" test_ac2_has_steps_config
run_test "has steps.path" test_ac2_has_steps_path
run_test "has steps.pattern" test_ac2_has_steps_pattern
run_test "has agent assignment" test_ac2_has_agent_assignment
run_test "has triggers" test_ac2_has_triggers

echo ""
echo "AC3: Variable syntax converted ({var-name} → {var_name})"
run_test "no dashed variables in workflow.yaml" test_ac3_no_dashed_variables_in_workflow
run_test "no dashed variables in steps/" test_ac3_no_dashed_variables_in_steps
run_test "has underscored variables" test_ac3_has_underscored_variables
run_test "preserves non-variable dashes" test_ac3_preserves_non_variable_dashes

echo ""
echo "AC4: /workflow list shows new workflow with correct metadata"
run_test "workflow name is correct" test_ac4_workflow_name_is_correct
run_test "description mentions epics/stories" test_ac4_description_mentions_epics
run_test "version is present" test_ac4_version_is_present

echo ""
echo "AC5: /workflow start epics-and-stories loads step 1 correctly"
run_test "step 1 exists" test_ac5_step1_exists
run_test "step 1 has frontmatter" test_ac5_step1_has_frontmatter
run_test "step 1 has name" test_ac5_step1_has_name
run_test "step 1 has description" test_ac5_step1_has_description
run_test "step 1 references next step" test_ac5_step1_references_next_step

echo ""
echo "AC6: Step transitions work with menu-based gates"
run_test "step 2 exists" test_ac6_step2_exists
run_test "step 3 exists" test_ac6_step3_exists
run_test "step 4 exists" test_ac6_step4_exists
run_test "steps have menu/gate markers" test_ac6_steps_have_menu_markers
run_test "workflow gates config (optional)" test_ac6_workflow_has_gates_config

echo ""
echo "AC7: Template placeholders preserved for runtime substitution"
run_test "templates/ directory exists" test_ac7_templates_directory_exists
run_test "epics-template.md exists" test_ac7_epics_template_exists
run_test "template has placeholders" test_ac7_template_has_placeholders
run_test "template has {{project_name}}" test_ac7_template_has_project_name_placeholder
run_test "template has {{epics_list}}" test_ac7_template_has_epics_list_placeholder
run_test "workflow references template (optional)" test_ac7_workflow_references_template

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
