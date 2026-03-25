#!/usr/bin/env bash
# check.test.sh - Tests for the /check command script
#
# Story 21-1: /check command with dev-handoff integration
#
# These tests verify the check.sh script that implements quality gates.
# Tests are written in RED phase - they will fail until check.sh is implemented.
#
# Run with: ./check.test.sh
# Or: bash check.test.sh

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
CHECK_SCRIPT="$SCRIPT_DIR/check.sh"

# Temp directory for test fixtures
TEST_TMPDIR=""

# =============================================================================
# Test Framework
# =============================================================================

setup() {
    TEST_TMPDIR=$(mktemp -d)
    cd "$TEST_TMPDIR"
    # Override PROJECT_ROOT to isolate tests from parent project
    # find-root.sh skips discovery when PROJECT_ROOT is already set
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

create_node_project() {
    cat > package.json << 'EOF'
{
  "name": "test-project",
  "scripts": {
    "lint": "eslint .",
    "test": "jest"
  }
}
EOF
}

create_node_project_with_typecheck() {
    cat > package.json << 'EOF'
{
  "name": "test-project",
  "scripts": {
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "jest"
  }
}
EOF
    cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "strict": true
  }
}
EOF
}

create_justfile_project() {
    cat > justfile << 'EOF'
lint:
    eslint .

typecheck:
    tsc --noEmit

test:
    npm test
EOF
}

create_go_project() {
    mkdir -p internal
    cat > go.mod << 'EOF'
module test-project
go 1.21
EOF
}

# =============================================================================
# AC1: /check command runs lint, type check, and tests
# =============================================================================

test_ac1_script_exists() {
    if [[ -f "$CHECK_SCRIPT" ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: check.sh script does not exist at $CHECK_SCRIPT"
        return 1
    fi
}

test_ac1_runs_lint() {
    create_node_project

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    assert_contains "$output" "Lint" "Output should include Lint section"
}

test_ac1_runs_typecheck() {
    create_node_project_with_typecheck

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    assert_contains "$output" "Type Check" "Output should include Type Check section"
}

test_ac1_runs_tests() {
    create_node_project

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    assert_contains "$output" "Tests" "Output should include Tests section"
}

# =============================================================================
# AC2: Command reports pass/fail with clear output
# =============================================================================

test_ac2_shows_pass_status() {
    create_node_project
    # Mock successful commands
    mkdir -p node_modules/.bin
    echo '#!/bin/bash' > node_modules/.bin/eslint
    echo 'exit 0' >> node_modules/.bin/eslint
    chmod +x node_modules/.bin/eslint

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    # Should show [PASS] for passing checks
    assert_contains "$output" "[PASS]" "Output should show PASS status"
}

test_ac2_shows_fail_status() {
    create_node_project
    # Mock failing lint
    mkdir -p node_modules/.bin
    echo '#!/bin/bash' > node_modules/.bin/eslint
    echo 'echo "Error: unused variable"' >> node_modules/.bin/eslint
    echo 'exit 1' >> node_modules/.bin/eslint
    chmod +x node_modules/.bin/eslint

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    # Should show [FAIL] for failing checks
    assert_contains "$output" "[FAIL]" "Output should show FAIL status"
}

test_ac2_returns_exit_code_0_on_success() {
    create_node_project
    # Mock all passing
    mkdir -p node_modules/.bin
    for cmd in eslint jest; do
        echo '#!/bin/bash' > "node_modules/.bin/$cmd"
        echo 'exit 0' >> "node_modules/.bin/$cmd"
        chmod +x "node_modules/.bin/$cmd"
    done

    "$CHECK_SCRIPT" > /dev/null 2>&1
    local exit_code=$?

    assert_exit_code "0" "$exit_code" "Should return 0 on all checks passing"
}

test_ac2_returns_nonzero_on_failure() {
    create_node_project
    # Mock failing lint
    mkdir -p node_modules/.bin
    echo '#!/bin/bash' > node_modules/.bin/eslint
    echo 'exit 1' >> node_modules/.bin/eslint
    chmod +x node_modules/.bin/eslint

    "$CHECK_SCRIPT" > /dev/null 2>&1
    local exit_code=$?

    # Should be non-zero
    if [[ "$exit_code" -ne 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Should return non-zero on check failure"
        return 1
    fi
}

test_ac2_summary_section_exists() {
    create_node_project

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    assert_contains "$output" "Summary" "Output should include Summary section"
}

# =============================================================================
# AC3: dev-handoff subagent runs /check automatically
# (This is a markdown/integration test - verified manually)
# =============================================================================

test_ac3_dev_handoff_references_check() {
    local dev_handoff="$SCRIPT_DIR/../agents/dev-handoff.md"

    if [[ ! -f "$dev_handoff" ]]; then
        echo -e "${RED}FAIL${NC}: dev-handoff.md not found"
        return 1
    fi

    local content
    content=$(cat "$dev_handoff")

    # Should reference /check or check.sh
    if [[ "$content" == *"/check"* ]] || [[ "$content" == *"check.sh"* ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: dev-handoff.md should reference /check command"
        return 1
    fi
}

# =============================================================================
# AC4: Failures block handoff to Reviewer
# (Verified by exit code - non-zero blocks handoff)
# =============================================================================

test_ac4_lint_failure_blocks() {
    create_node_project
    mkdir -p node_modules/.bin
    echo '#!/bin/bash' > node_modules/.bin/eslint
    echo 'exit 1' >> node_modules/.bin/eslint
    chmod +x node_modules/.bin/eslint

    "$CHECK_SCRIPT" > /dev/null 2>&1
    local exit_code=$?

    if [[ "$exit_code" -ne 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Lint failure should result in non-zero exit"
        return 1
    fi
}

test_ac4_test_failure_blocks() {
    create_node_project
    mkdir -p node_modules/.bin
    echo '#!/bin/bash' > node_modules/.bin/eslint
    echo 'exit 0' >> node_modules/.bin/eslint
    chmod +x node_modules/.bin/eslint

    echo '#!/bin/bash' > node_modules/.bin/jest
    echo 'exit 1' >> node_modules/.bin/jest
    chmod +x node_modules/.bin/jest

    "$CHECK_SCRIPT" > /dev/null 2>&1
    local exit_code=$?

    if [[ "$exit_code" -ne 0 ]]; then
        return 0
    else
        echo -e "${RED}FAIL${NC}: Test failure should result in non-zero exit"
        return 1
    fi
}

# =============================================================================
# AC5: --skip-check flag bypasses checks when needed
# =============================================================================

test_ac5_skip_flag_accepted() {
    create_node_project

    # Should not error on --skip-check flag
    "$CHECK_SCRIPT" --skip-check > /dev/null 2>&1
    local exit_code=$?

    assert_exit_code "0" "$exit_code" "--skip-check should always return 0"
}

test_ac5_skip_flag_shows_warning() {
    create_node_project

    local output
    output=$("$CHECK_SCRIPT" --skip-check 2>&1)

    assert_contains "$output" "skip" "Should mention skip in output"
}

test_ac5_skip_flag_does_not_run_checks() {
    create_node_project
    # Mock lint that would fail
    mkdir -p node_modules/.bin
    echo '#!/bin/bash' > node_modules/.bin/eslint
    echo 'echo "LINT_WAS_RUN"' >> node_modules/.bin/eslint
    echo 'exit 1' >> node_modules/.bin/eslint
    chmod +x node_modules/.bin/eslint

    local output
    output=$("$CHECK_SCRIPT" --skip-check 2>&1)

    assert_not_contains "$output" "LINT_WAS_RUN" "Lint should not run when --skip-check is used"
}

# =============================================================================
# AC6: Works with justfile recipes if available
# =============================================================================

test_ac6_detects_justfile() {
    create_justfile_project

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    # Should detect and use justfile
    # (Exact output depends on implementation)
    assert_contains "$output" "Lint" "Should still run lint check"
}

test_ac6_prefers_justfile_over_npm() {
    create_justfile_project
    create_node_project  # Also has package.json

    # Mock just command
    mkdir -p "$TEST_TMPDIR/bin"
    echo '#!/bin/bash' > "$TEST_TMPDIR/bin/just"
    echo 'if [[ "$1" == "--list" ]]; then' >> "$TEST_TMPDIR/bin/just"
    echo '  echo "lint (linting)"' >> "$TEST_TMPDIR/bin/just"
    echo '  echo "typecheck (type checking)"' >> "$TEST_TMPDIR/bin/just"
    echo '  echo "test (testing)"' >> "$TEST_TMPDIR/bin/just"
    echo 'else' >> "$TEST_TMPDIR/bin/just"
    echo 'echo "JUST_WAS_USED"' >> "$TEST_TMPDIR/bin/just"
    echo 'fi' >> "$TEST_TMPDIR/bin/just"
    echo 'exit 0' >> "$TEST_TMPDIR/bin/just"
    chmod +x "$TEST_TMPDIR/bin/just"

    local output
    output=$(env PATH="$TEST_TMPDIR/bin:$PATH" "$CHECK_SCRIPT" 2>&1)

    # Should use just when available
    assert_contains "$output" "(just" "Should prefer justfile recipes"
}

test_ac6_falls_back_to_npm() {
    create_node_project
    # No justfile

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    # Should work without justfile
    assert_contains "$output" "Lint" "Should fall back to npm scripts"
}

# =============================================================================
# Edge Cases
# =============================================================================

test_edge_no_lint_configured() {
    # Project with no lint
    cat > package.json << 'EOF'
{
  "name": "test-project",
  "scripts": {
    "test": "jest"
  }
}
EOF

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    # Should handle gracefully (skip or warn)
    # Not a failure condition
    if [[ "$output" == *"Lint"* ]]; then
        assert_contains "$output" "skip" "Should indicate lint was skipped"
    fi
    return 0
}

test_edge_no_tests_configured() {
    cat > package.json << 'EOF'
{
  "name": "test-project",
  "scripts": {
    "lint": "eslint ."
  }
}
EOF

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true

    # Should handle missing test command gracefully
    return 0  # Not failing is success
}

test_edge_empty_directory() {
    # Empty project directory - no package.json, no justfile

    local output
    output=$("$CHECK_SCRIPT" 2>&1) || true
    local exit_code=$?

    # Should not crash, may warn about no project detected
    return 0
}

# =============================================================================
# Run All Tests
# =============================================================================

echo ""
echo "=================================="
echo "Story 21-1: /check Command Tests"
echo "=================================="
echo ""

echo "AC1: /check command runs lint, type check, and tests"
run_test "check.sh script exists" test_ac1_script_exists
run_test "runs lint check" test_ac1_runs_lint
run_test "runs type check" test_ac1_runs_typecheck
run_test "runs tests" test_ac1_runs_tests

echo ""
echo "AC2: Command reports pass/fail with clear output"
run_test "shows PASS status" test_ac2_shows_pass_status
run_test "shows FAIL status" test_ac2_shows_fail_status
run_test "returns exit 0 on success" test_ac2_returns_exit_code_0_on_success
run_test "returns non-zero on failure" test_ac2_returns_nonzero_on_failure
run_test "includes Summary section" test_ac2_summary_section_exists

echo ""
echo "AC3: dev-handoff subagent runs /check automatically"
run_test "dev-handoff.md references /check" test_ac3_dev_handoff_references_check

echo ""
echo "AC4: Failures block handoff to Reviewer"
run_test "lint failure blocks handoff" test_ac4_lint_failure_blocks
run_test "test failure blocks handoff" test_ac4_test_failure_blocks

echo ""
echo "AC5: --skip-check flag bypasses checks when needed"
run_test "--skip-check flag accepted" test_ac5_skip_flag_accepted
run_test "--skip-check shows warning" test_ac5_skip_flag_shows_warning
run_test "--skip-check skips actual checks" test_ac5_skip_flag_does_not_run_checks

echo ""
echo "AC6: Works with justfile recipes if available"
run_test "detects justfile" test_ac6_detects_justfile
run_test "prefers justfile over npm" test_ac6_prefers_justfile_over_npm
run_test "falls back to npm scripts" test_ac6_falls_back_to_npm

echo ""
echo "Edge Cases"
run_test "handles no lint configured" test_edge_no_lint_configured
run_test "handles no tests configured" test_edge_no_tests_configured
run_test "handles empty directory" test_edge_empty_directory

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=================================="
echo "Test Summary"
echo "=================================="
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
