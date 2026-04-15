#!/usr/bin/env bash
# dev-story-workflow-import.test.sh - Tests for Story <PROJECT-KEY>: Import Dev-Story workflow
#
# These tests verify that the BMAD dev-story workflow is correctly imported
# into Pennyfarthing's workflow format.
#
# IMPORTANT: The BMAD dev-story workflow uses a different format than previous imports:
# - workflow.yaml (variable definitions)
# - instructions.xml (procedural steps)
# - checklist.md (Definition of Done)
#
# This is NOT a stepped workflow - it's a reference/BMAD-compat import.
#
# AC1: pennyfarthing-dist/workflows/dev-story/ directory created
# AC2: BMAD workflow.yaml contents converted and integrated
# AC3: instructions.xml copied with variable syntax converted
# AC4: checklist.md copied
# AC5: /workflow list shows dev-story as available workflow
# AC6: Workflow purpose documented (BMAD reference, not TDD replacement)
#
# Run with: ./dev-story-workflow-import.test.sh
# Or: bash dev-story-workflow-import.test.sh

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
BMAD_SOURCE="${BMAD_DEV_STORY_SOURCE:-$HOME/Projects/BMAD-METHOD/src/modules/bmm/workflows/4-implementation/dev-story}"
TARGET_DIR="$PROJECT_ROOT/pennyfarthing-dist/workflows/dev-story"

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
        echo -e "${RED}ERROR${NC}: BMAD dev-story workflow source not found at: $BMAD_SOURCE"
        echo "Set BMAD_DEV_STORY_SOURCE environment variable to point to the BMAD workflow directory"
        exit 1
    fi

    if [[ ! -f "$BMAD_SOURCE/workflow.yaml" ]]; then
        echo -e "${RED}ERROR${NC}: BMAD dev-story workflow.yaml not found at: $BMAD_SOURCE/workflow.yaml"
        exit 1
    fi

    echo -e "${GREEN}OK${NC}: Prerequisites met"
    echo ""
}

# =============================================================================
# AC1: pennyfarthing-dist/workflows/dev-story/ directory created
# =============================================================================

test_ac1_workflow_directory_exists() {
    # This test verifies the workflow was migrated to the target directory
    # EXPECTED: FAIL until Dev creates the directory

    assert_dir_exists "$TARGET_DIR" \
        "dev-story workflow directory should exist at $TARGET_DIR"
}

test_ac1_workflow_yaml_exists() {
    assert_file_exists "$TARGET_DIR/workflow.yaml" \
        "workflow.yaml should exist in target directory"
}

test_ac1_instructions_xml_exists() {
    assert_file_exists "$TARGET_DIR/instructions.xml" \
        "instructions.xml should exist in target directory"
}

test_ac1_checklist_md_exists() {
    assert_file_exists "$TARGET_DIR/checklist.md" \
        "checklist.md should exist in target directory"
}

# =============================================================================
# AC2: BMAD workflow.yaml contents converted and integrated
# =============================================================================

test_ac2_workflow_yaml_has_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "name:" \
        "workflow.yaml should have name field"
}

test_ac2_workflow_yaml_has_dev_story_name() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "dev-story" \
        "workflow.yaml should have dev-story in name"
}

test_ac2_workflow_yaml_has_description() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "description:" \
        "workflow.yaml should have description field"
}

test_ac2_workflow_yaml_has_type() {
    # This workflow may be type: reference or type: bmad-compat
    # or could be type: procedural - Dev can decide
    assert_file_contains "$TARGET_DIR/workflow.yaml" "type:" \
        "workflow.yaml should have type field"
}

test_ac2_workflow_yaml_has_agent() {
    # This workflow should specify dev as the primary agent
    assert_file_contains "$TARGET_DIR/workflow.yaml" "agent:" \
        "workflow.yaml should have agent field"
}

test_ac2_no_config_source_reference() {
    # The original BMAD workflow.yaml has config_source references
    # These should be converted or removed for standalone use
    assert_file_not_contains "$TARGET_DIR/workflow.yaml" "{config_source}" \
        "workflow.yaml should not have {config_source} references (should be resolved or removed)"
}

# =============================================================================
# AC3: instructions.xml copied with variable syntax converted
# =============================================================================

test_ac3_instructions_xml_exists() {
    assert_file_exists "$TARGET_DIR/instructions.xml" \
        "instructions.xml should be copied"
}

test_ac3_instructions_has_workflow_tag() {
    assert_file_contains "$TARGET_DIR/instructions.xml" "<workflow>" \
        "instructions.xml should have <workflow> root tag"
}

test_ac3_instructions_has_steps() {
    assert_file_contains "$TARGET_DIR/instructions.xml" '<step n="1"' \
        "instructions.xml should have step elements"
}

test_ac3_no_dashed_variables_project_root() {
    # Variable syntax conversion: {project-root} → {project_root}
    assert_file_not_contains "$TARGET_DIR/instructions.xml" "{project-root}" \
        "instructions.xml should not have {project-root} (should be {project_root})"
}

test_ac3_no_dashed_variables_user_skill_level() {
    assert_file_not_contains "$TARGET_DIR/instructions.xml" "{user-skill-level}" \
        "instructions.xml should not have {user-skill-level} (should be {user_skill_level})"
}

test_ac3_no_dashed_variables_communication_language() {
    assert_file_not_contains "$TARGET_DIR/instructions.xml" "{communication-language}" \
        "instructions.xml should not have {communication-language} (should be {communication_language})"
}

test_ac3_no_dashed_variables_story_path() {
    # BMAD uses {{story_path}} but if there are dashed versions they should be converted
    assert_file_not_contains "$TARGET_DIR/instructions.xml" "{story-path}" \
        "instructions.xml should not have {story-path} (should be {story_path})"
}

test_ac3_has_all_10_steps() {
    # The BMAD dev-story workflow has 10 steps
    local content
    content=$(cat "$TARGET_DIR/instructions.xml" 2>/dev/null || echo "")

    local step_count=0
    for i in 1 2 3 4 5 6 7 8 9 10; do
        if [[ "$content" == *"<step n=\"$i\""* ]]; then
            step_count=$((step_count + 1))
        fi
    done

    if [[ $step_count -eq 10 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Expected 10 steps, found $step_count"
        return 1
    fi
}

# =============================================================================
# AC4: checklist.md copied
# =============================================================================

test_ac4_checklist_md_exists() {
    assert_file_exists "$TARGET_DIR/checklist.md" \
        "checklist.md should be copied"
}

test_ac4_checklist_has_title() {
    assert_file_contains "$TARGET_DIR/checklist.md" "Definition of Done" \
        "checklist.md should have Definition of Done title"
}

test_ac4_checklist_has_implementation_section() {
    assert_file_contains "$TARGET_DIR/checklist.md" "Implementation Completion" \
        "checklist.md should have Implementation Completion section"
}

test_ac4_checklist_has_testing_section() {
    assert_file_contains "$TARGET_DIR/checklist.md" "Testing" \
        "checklist.md should have Testing section"
}

test_ac4_checklist_has_checkbox_items() {
    # The checklist should have checkbox items like "- [ ]"
    assert_file_contains "$TARGET_DIR/checklist.md" "- [ ]" \
        "checklist.md should have checkbox items"
}

# =============================================================================
# AC5: /workflow list shows dev-story as available workflow
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
    # For /workflow list to show the workflow, it should have triggers
    assert_file_contains "$TARGET_DIR/workflow.yaml" "triggers:" \
        "workflow.yaml should have triggers section for workflow listing"
}

test_ac5_workflow_triggers_has_types() {
    assert_file_contains "$TARGET_DIR/workflow.yaml" "types:" \
        "workflow.yaml triggers should have types field"
}

# =============================================================================
# AC6: Workflow purpose documented (BMAD reference, not TDD replacement)
# =============================================================================

test_ac6_workflow_description_mentions_bmad() {
    # The description should clarify this is BMAD-related
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
    # This workflow should NOT be a default workflow (TDD is the default)
    assert_file_not_contains "$TARGET_DIR/workflow.yaml" "default: true" \
        "dev-story should not be default workflow (TDD is default)"
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

test_ac6_description_mentions_story_or_implementation() {
    # Description should mention story implementation
    assert_file_contains "$TARGET_DIR/workflow.yaml" "story" \
        "workflow.yaml description should mention story implementation"
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=============================================="
echo "Story <PROJECT-KEY>: Import Dev-Story Workflow Tests"
echo "=============================================="
echo ""

check_prerequisites

echo "AC1: pennyfarthing-dist/workflows/dev-story/ directory created"
run_test "workflow directory exists" test_ac1_workflow_directory_exists
run_test "workflow.yaml exists" test_ac1_workflow_yaml_exists
run_test "instructions.xml exists" test_ac1_instructions_xml_exists
run_test "checklist.md exists" test_ac1_checklist_md_exists

echo ""
echo "AC2: BMAD workflow.yaml contents converted and integrated"
run_test "workflow.yaml has name field" test_ac2_workflow_yaml_has_name
run_test "workflow.yaml has dev-story name" test_ac2_workflow_yaml_has_dev_story_name
run_test "workflow.yaml has description" test_ac2_workflow_yaml_has_description
run_test "workflow.yaml has type field" test_ac2_workflow_yaml_has_type
run_test "workflow.yaml has agent field" test_ac2_workflow_yaml_has_agent
run_test "no {config_source} references" test_ac2_no_config_source_reference

echo ""
echo "AC3: instructions.xml copied with variable syntax converted"
run_test "instructions.xml exists" test_ac3_instructions_xml_exists
run_test "instructions.xml has <workflow> tag" test_ac3_instructions_has_workflow_tag
run_test "instructions.xml has step elements" test_ac3_instructions_has_steps
run_test "no {project-root} dashed variable" test_ac3_no_dashed_variables_project_root
run_test "no {user-skill-level} dashed variable" test_ac3_no_dashed_variables_user_skill_level
run_test "no {communication-language} dashed variable" test_ac3_no_dashed_variables_communication_language
run_test "no {story-path} dashed variable" test_ac3_no_dashed_variables_story_path
run_test "has all 10 steps" test_ac3_has_all_10_steps

echo ""
echo "AC4: checklist.md copied"
run_test "checklist.md exists" test_ac4_checklist_md_exists
run_test "checklist has Definition of Done title" test_ac4_checklist_has_title
run_test "checklist has Implementation section" test_ac4_checklist_has_implementation_section
run_test "checklist has Testing section" test_ac4_checklist_has_testing_section
run_test "checklist has checkbox items" test_ac4_checklist_has_checkbox_items

echo ""
echo "AC5: /workflow list shows dev-story as available workflow"
run_test "workflow.yaml is valid YAML" test_ac5_workflow_yaml_valid_yaml
run_test "workflow.yaml has triggers section" test_ac5_workflow_has_triggers
run_test "triggers has types field" test_ac5_workflow_triggers_has_types

echo ""
echo "AC6: Workflow purpose documented (BMAD reference, not TDD replacement)"
run_test "description mentions BMAD origin" test_ac6_workflow_description_mentions_bmad
run_test "workflow is not default" test_ac6_workflow_not_default
run_test "workflow.yaml has comment header" test_ac6_workflow_has_comment_header
run_test "description mentions story implementation" test_ac6_description_mentions_story_or_implementation

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
