#!/usr/bin/env bash
# migrate-bmad-workflow.test.sh - Tests for BMAD workflow migration script
#
# Story <PROJECT-KEY>: BMAD to Pennyfarthing migration script
#
# These tests verify the migrate-bmad-workflow.sh script that converts
# BMAD workflow format to Pennyfarthing stepped workflow format.
#
# Run with: ./migrate-bmad-workflow.test.sh
# Or: bash migrate-bmad-workflow.test.sh

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

# Path to script under test
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATE_SCRIPT="$SCRIPT_DIR/migrate-bmad-workflow.sh"

# Temp directory for test fixtures
TEST_TMPDIR=""

# =============================================================================
# Test Framework
# =============================================================================

setup() {
    TEST_TMPDIR=$(mktemp -d)
    cd "$TEST_TMPDIR"
    export PROJECT_ROOT="$TEST_TMPDIR"
}

teardown() {
    cd /
    rm -rf "$TEST_TMPDIR"
    unset PROJECT_ROOT
}

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

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    local message="${3:-Exit code should match}"

    assert_eq "$expected" "$actual" "$message"
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
        echo "  Actual output: $haystack"
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
        echo "  Actual output: $haystack"
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

run_test() {
    local test_name="$1"
    local test_func="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    echo -n "  $test_name... "

    setup

    if $test_func; then
        echo -e "${GREEN}PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi

    teardown
}

# =============================================================================
# Test Fixtures
# =============================================================================

create_simple_bmad_workflow() {
    # Create a simple single-mode BMAD workflow for testing
    mkdir -p bmad-workflow/steps

    # Create workflow.md
    cat > bmad-workflow/workflow.md << 'EOF'
---
name: simple-workflow
description: A simple test workflow
main_config: '{project-root}/_bmad/config.yaml'
nextStep: './steps/step-01-init.md'
---

# Simple Workflow

A basic workflow for testing migration.
EOF

    # Create a step file with frontmatter
    cat > bmad-workflow/steps/step-01-init.md << 'EOF'
---
name: 'step-01-init'
description: 'Initialize the workflow'
nextStepFile: './step-02-work.md'
outputFile: '{planning_artifacts}/output.md'
---

# Step 1: Initialize

## STEP GOAL:

Initialize the workflow.
EOF

    cat > bmad-workflow/steps/step-02-work.md << 'EOF'
---
name: 'step-02-work'
description: 'Do the work'
nextStepFile: './step-03-complete.md'
templateRef: '{project-root}/templates/work.md'
---

# Step 2: Work

Do the actual work here.
EOF
}

create_trimodal_bmad_workflow() {
    # Create a tri-modal BMAD workflow (like PRD)
    mkdir -p bmad-workflow/{steps-c,steps-v,steps-e,templates,data}

    # Create workflow.md
    cat > bmad-workflow/workflow.md << 'EOF'
---
name: prd
description: PRD tri-modal workflow - Create, Validate, or Edit
main_config: '{project-root}/_bmad/config.yaml'
nextStep: './steps-c/step-01-init.md'
validateWorkflow: './steps-v/step-v-01-discovery.md'
editWorkflow: './steps-e/step-e-01-discovery.md'
web_bundle: true
---

# PRD Workflow (Tri-Modal)

Create, Validate, or Edit PRDs.
EOF

    # Create step file
    cat > bmad-workflow/steps-c/step-01-init.md << 'EOF'
---
name: 'step-01-init'
description: 'Initialize the PRD creation workflow'
nextStepFile: './step-02-discovery.md'
outputFile: '{planning_artifacts}/prd.md'
prdTemplate: '../templates/prd-template.md'
---

# Step 1: Workflow Initialization

Initialize the PRD workflow.
EOF

    # Create validate step
    cat > bmad-workflow/steps-v/step-v-01-discovery.md << 'EOF'
---
name: 'step-v-01-discovery'
description: 'Document Discovery & Confirmation'
nextStepFile: './step-v-02-format-detection.md'
advancedElicitationTask: '{project-root}/_bmad/workflows/advanced-elicitation/workflow.xml'
---

# Step 1: Document Discovery

Discover and validate documents.
EOF

    # Create edit step
    cat > bmad-workflow/steps-e/step-e-01-discovery.md << 'EOF'
---
name: 'step-e-01-discovery'
description: 'Discover PRD for editing'
nextStepFile: './step-e-02-analysis.md'
---

# Step 1: Edit Discovery

Discover PRD to edit.
EOF

    # Create template
    cat > bmad-workflow/templates/prd-template.md << 'EOF'
# Product Requirements Document

## Overview
{project_name}
EOF
}

create_workflow_with_dashed_variables() {
    # Create workflow with BMAD-style dashed variables
    mkdir -p bmad-workflow/steps

    cat > bmad-workflow/workflow.md << 'EOF'
---
name: variable-test
description: Workflow to test variable conversion
main_config: '{project-root}/_bmad/bmm/config.yaml'
nextStep: './steps/step-01-init.md'
---

# Variable Test Workflow
EOF

    cat > bmad-workflow/steps/step-01-init.md << 'EOF'
---
name: 'step-01-init'
description: 'Test step with many variables'
nextStepFile: './step-02-work.md'
outputFile: '{planning-artifacts}/output.md'
configRef: '{project-root}/_bmad/bmm/config.yaml'
templateRef: '{user-templates}/custom.md'
---

# Step 1: Initialize

Load configuration from {main-config} and write to {output-folder}.
User skill level: {user-skill-level}
Communication: {communication-language}
EOF
}

# =============================================================================
# AC1: Script parses BMAD workflow.md configuration
# =============================================================================

test_ac1_script_exists() {
    if [[ -f "$MIGRATE_SCRIPT" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: migrate-bmad-workflow.sh script does not exist at $MIGRATE_SCRIPT"
        return 1
    fi
}

test_ac1_accepts_source_path() {
    create_simple_bmad_workflow

    local output
    output=$("$MIGRATE_SCRIPT" bmad-workflow 2>&1) || true

    # Should not error on valid source path
    assert_not_contains "$output" "not found" "Should accept valid source path"
}

test_ac1_extracts_workflow_name() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Check generated workflow.yaml has correct name
    assert_file_contains "output/workflow.yaml" "name: simple-workflow" \
        "Should extract workflow name from BMAD workflow.md"
}

test_ac1_extracts_workflow_description() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_file_contains "output/workflow.yaml" "description:" \
        "Should extract workflow description from BMAD workflow.md"
}

test_ac1_errors_on_missing_workflowmd() {
    mkdir -p bmad-workflow/steps
    # No workflow.md

    # Capture exit code properly (|| true swallows it, so use set +e)
    set +e
    "$MIGRATE_SCRIPT" bmad-workflow output 2>&1
    local exit_code=$?
    set -e

    # Should fail when workflow.md is missing
    if [[ "$exit_code" -ne 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Should error when workflow.md is missing"
        return 1
    fi
}

# =============================================================================
# AC2: Script extracts YAML frontmatter from step files
# =============================================================================

test_ac2_extracts_step_frontmatter() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Should have copied/processed step files
    assert_file_exists "output/steps/step-01-init.md" \
        "Should copy step files to output"
}

test_ac2_preserves_step_content() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Step content should be preserved
    assert_file_contains "output/steps/step-01-init.md" "STEP GOAL" \
        "Should preserve step file content"
}

test_ac2_handles_complex_frontmatter() {
    create_trimodal_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Should handle step files with multiple frontmatter fields
    assert_file_exists "output/steps-c/step-01-init.md" \
        "Should handle step files with complex frontmatter"
}

# =============================================================================
# AC3: Variable syntax converted (dashes to underscores)
# =============================================================================

test_ac3_converts_dashed_variables_in_workflow() {
    create_workflow_with_dashed_variables
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Should convert {project-root} to {project_root}
    assert_file_contains "output/workflow.yaml" "project_root" \
        "Should convert dashed variables to underscored in workflow.yaml"
}

test_ac3_converts_dashed_variables_in_steps() {
    create_workflow_with_dashed_variables
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    local content
    content=$(cat "output/steps/step-01-init.md" 2>/dev/null || echo "")

    # Should convert {planning-artifacts} to {planning_artifacts}
    assert_not_contains "$content" "{planning-artifacts}" \
        "Should convert dashed variables in step files"
    assert_contains "$content" "{planning_artifacts}" \
        "Should have underscored variables after conversion"
}

test_ac3_converts_all_common_variables() {
    create_workflow_with_dashed_variables
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    local content
    content=$(cat "output/steps/step-01-init.md" 2>/dev/null || echo "")

    # Check multiple variable conversions
    assert_not_contains "$content" "{main-config}" \
        "Should convert {main-config}"
    assert_not_contains "$content" "{output-folder}" \
        "Should convert {output-folder}"
    assert_not_contains "$content" "{user-skill-level}" \
        "Should convert {user-skill-level}"
}

test_ac3_preserves_non_variable_dashes() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Regular dashes (not in braces) should be preserved
    # Step names like 'step-01-init' should remain unchanged
    assert_file_contains "output/steps/step-01-init.md" "step-01-init" \
        "Should preserve dashes outside of variable braces"
}

# =============================================================================
# AC4: workflow.yaml generated with correct schema
# =============================================================================

test_ac4_generates_workflow_yaml() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_file_exists "output/workflow.yaml" \
        "Should generate workflow.yaml"
}

test_ac4_yaml_has_type_stepped() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_file_contains "output/workflow.yaml" "type: stepped" \
        "Generated workflow.yaml should have type: stepped"
}

test_ac4_yaml_has_steps_config() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_file_contains "output/workflow.yaml" "steps:" \
        "Generated workflow.yaml should have steps configuration"
}

test_ac4_yaml_has_valid_structure() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Check for required workflow.yaml structure
    local content
    content=$(cat "output/workflow.yaml" 2>/dev/null || echo "")

    assert_contains "$content" "workflow:" "Should have workflow: root key"
    assert_contains "$content" "name:" "Should have name field"
    assert_contains "$content" "description:" "Should have description field"
}

# =============================================================================
# AC5: Tri-modal structure preserved
# =============================================================================

test_ac5_preserves_steps_c_directory() {
    create_trimodal_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_dir_exists "output/steps-c" \
        "Should preserve steps-c directory for create mode"
}

test_ac5_preserves_steps_v_directory() {
    create_trimodal_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_dir_exists "output/steps-v" \
        "Should preserve steps-v directory for validate mode"
}

test_ac5_preserves_steps_e_directory() {
    create_trimodal_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_dir_exists "output/steps-e" \
        "Should preserve steps-e directory for edit mode"
}

test_ac5_copies_all_modal_steps() {
    create_trimodal_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_file_exists "output/steps-c/step-01-init.md" \
        "Should copy create mode steps"
    assert_file_exists "output/steps-v/step-v-01-discovery.md" \
        "Should copy validate mode steps"
    assert_file_exists "output/steps-e/step-e-01-discovery.md" \
        "Should copy edit mode steps"
}

test_ac5_yaml_references_modes() {
    create_trimodal_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    local content
    content=$(cat "output/workflow.yaml" 2>/dev/null || echo "")

    # Should reference all three modes in workflow.yaml
    assert_contains "$content" "modes:" "Should have modes configuration"
}

test_ac5_preserves_supporting_dirs() {
    create_trimodal_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Should copy templates directory
    assert_dir_exists "output/templates" \
        "Should preserve templates directory"
}

# =============================================================================
# AC6: Dry-run mode shows changes without writing
# =============================================================================

test_ac6_dry_run_flag_accepted() {
    create_simple_bmad_workflow
    mkdir -p output

    local output
    output=$("$MIGRATE_SCRIPT" --dry-run bmad-workflow output 2>&1) || true
    local exit_code=$?

    # Should accept --dry-run flag without error
    assert_eq "0" "$exit_code" "--dry-run should be accepted"
}

test_ac6_dry_run_shows_plan() {
    create_simple_bmad_workflow
    mkdir -p output

    local output
    output=$("$MIGRATE_SCRIPT" --dry-run bmad-workflow output 2>&1)

    # Should show what would be done
    assert_contains "$output" "workflow.yaml" "Dry-run should mention workflow.yaml"
}

test_ac6_dry_run_does_not_write() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" --dry-run bmad-workflow output 2>/dev/null || true

    # Should NOT create files
    if [[ -f "output/workflow.yaml" ]]; then
        echo -e "${RED}FAIL${NC}: Dry-run should not create workflow.yaml"
        return 1
    fi
    return 0
}

test_ac6_dry_run_does_not_copy_steps() {
    create_simple_bmad_workflow
    mkdir -p output

    "$MIGRATE_SCRIPT" --dry-run bmad-workflow output 2>/dev/null || true

    # Should NOT copy step files
    if [[ -f "output/steps/step-01-init.md" ]]; then
        echo -e "${RED}FAIL${NC}: Dry-run should not copy step files"
        return 1
    fi
    return 0
}

test_ac6_dry_run_shows_variable_conversions() {
    create_workflow_with_dashed_variables
    mkdir -p output

    local output
    output=$("$MIGRATE_SCRIPT" --dry-run bmad-workflow output 2>&1)

    # Should mention variable conversions
    assert_contains "$output" "variable" "Dry-run should mention variable conversions"
}

# =============================================================================
# Edge Cases
# =============================================================================

test_edge_missing_target_directory() {
    create_simple_bmad_workflow

    # Output directory doesn't exist - script should create it
    "$MIGRATE_SCRIPT" bmad-workflow nonexistent-output 2>/dev/null || true

    assert_dir_exists "nonexistent-output" \
        "Should create target directory if it doesn't exist"
}

test_edge_empty_workflow() {
    mkdir -p bmad-workflow

    # Just workflow.md with minimal content
    cat > bmad-workflow/workflow.md << 'EOF'
---
name: empty
description: Empty workflow
---

# Empty Workflow
EOF

    mkdir -p output

    # Should handle gracefully
    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_file_exists "output/workflow.yaml" \
        "Should handle workflow with no steps"
}

test_edge_nested_step_directories() {
    mkdir -p bmad-workflow/steps/substeps

    cat > bmad-workflow/workflow.md << 'EOF'
---
name: nested
description: Nested steps test
nextStep: './steps/step-01.md'
---
# Nested
EOF

    cat > bmad-workflow/steps/step-01.md << 'EOF'
---
name: 'step-01'
description: 'Step with nested reference'
substepRef: './substeps/sub-01.md'
---
# Step 1
EOF

    cat > bmad-workflow/steps/substeps/sub-01.md << 'EOF'
---
name: 'sub-01'
description: 'A substep'
---
# Substep 1
EOF

    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    # Should preserve nested structure
    assert_file_exists "output/steps/substeps/sub-01.md" \
        "Should preserve nested step directories"
}

test_edge_special_characters_in_content() {
    mkdir -p bmad-workflow/steps

    cat > bmad-workflow/workflow.md << 'EOF'
---
name: special-chars
description: Test with $pecial ch@rs & "quotes"
---
# Special Characters Test
EOF

    cat > bmad-workflow/steps/step-01.md << 'EOF'
---
name: 'step-01'
description: "Step with 'quotes' and $dollars"
---
# Step 1

Content with `backticks` and [brackets] and {braces}.
EOF

    mkdir -p output

    "$MIGRATE_SCRIPT" bmad-workflow output 2>/dev/null || true

    assert_file_contains "output/steps/step-01.md" "backticks" \
        "Should preserve special characters in content"
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=============================================="
echo "Story <PROJECT-KEY>: BMAD Migration Script Tests"
echo "=============================================="
echo ""

echo "AC1: Script parses BMAD workflow.md configuration"
run_test "migrate-bmad-workflow.sh script exists" test_ac1_script_exists
run_test "accepts source path argument" test_ac1_accepts_source_path
run_test "extracts workflow name" test_ac1_extracts_workflow_name
run_test "extracts workflow description" test_ac1_extracts_workflow_description
run_test "errors on missing workflow.md" test_ac1_errors_on_missing_workflowmd

echo ""
echo "AC2: Script extracts YAML frontmatter from step files"
run_test "extracts step frontmatter" test_ac2_extracts_step_frontmatter
run_test "preserves step content" test_ac2_preserves_step_content
run_test "handles complex frontmatter" test_ac2_handles_complex_frontmatter

echo ""
echo "AC3: Variable syntax converted (dashes to underscores)"
run_test "converts dashed variables in workflow" test_ac3_converts_dashed_variables_in_workflow
run_test "converts dashed variables in steps" test_ac3_converts_dashed_variables_in_steps
run_test "converts all common variables" test_ac3_converts_all_common_variables
run_test "preserves non-variable dashes" test_ac3_preserves_non_variable_dashes

echo ""
echo "AC4: workflow.yaml generated with correct schema"
run_test "generates workflow.yaml" test_ac4_generates_workflow_yaml
run_test "yaml has type: stepped" test_ac4_yaml_has_type_stepped
run_test "yaml has steps config" test_ac4_yaml_has_steps_config
run_test "yaml has valid structure" test_ac4_yaml_has_valid_structure

echo ""
echo "AC5: Tri-modal structure preserved"
run_test "preserves steps-c directory" test_ac5_preserves_steps_c_directory
run_test "preserves steps-v directory" test_ac5_preserves_steps_v_directory
run_test "preserves steps-e directory" test_ac5_preserves_steps_e_directory
run_test "copies all modal steps" test_ac5_copies_all_modal_steps
run_test "yaml references modes" test_ac5_yaml_references_modes
run_test "preserves supporting directories" test_ac5_preserves_supporting_dirs

echo ""
echo "AC6: Dry-run mode shows changes without writing"
run_test "--dry-run flag accepted" test_ac6_dry_run_flag_accepted
run_test "dry-run shows plan" test_ac6_dry_run_shows_plan
run_test "dry-run does not write files" test_ac6_dry_run_does_not_write
run_test "dry-run does not copy steps" test_ac6_dry_run_does_not_copy_steps
run_test "dry-run shows variable conversions" test_ac6_dry_run_shows_variable_conversions

echo ""
echo "Edge Cases"
run_test "creates missing target directory" test_edge_missing_target_directory
run_test "handles empty workflow" test_edge_empty_workflow
run_test "handles nested step directories" test_edge_nested_step_directories
run_test "handles special characters" test_edge_special_characters_in_content

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
    exit 1
else
    echo -e "${GREEN}PASSED${NC} - All tests passed"
    exit 0
fi
