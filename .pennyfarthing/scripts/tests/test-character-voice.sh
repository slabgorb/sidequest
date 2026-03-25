#!/usr/bin/env bash
# Test: agent-session.sh respects character_voice preference
#
# This test verifies that when character_voice=false in preferences.yaml,
# the persona output is suppressed.
#
# Usage: ./test-character-voice.sh
# Exit codes: 0 = pass, 1 = fail

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=== Testing character_voice preference ==="
echo "Project root: $PROJECT_ROOT"

# Create temp directory for test
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

# Setup test project structure
mkdir -p "$TEST_DIR/.pennyfarthing/personas/themes"
mkdir -p "$TEST_DIR/.claude/pennyfarthing"
mkdir -p "$TEST_DIR/scripts"

# Copy core scripts (including agent-session.sh)
mkdir -p "$TEST_DIR/scripts/core"
mkdir -p "$TEST_DIR/scripts/lib"
cp "$PROJECT_ROOT/scripts/core/agent-session.sh" "$TEST_DIR/scripts/core/"
cp "$PROJECT_ROOT/scripts/lib/find-root.sh" "$TEST_DIR/scripts/lib/"

# Create minimal theme file
cat > "$TEST_DIR/.pennyfarthing/personas/themes/test-theme.yaml" << 'EOF'
name: test-theme
description: Test theme

agents:
  sm:
    character: Test Character
    style: Test style
    role: Test role
EOF

# Create persona config
cat > "$TEST_DIR/.claude/persona-config.yaml" << 'EOF'
theme: test-theme
EOF

# Test 1: Without preferences file (default behavior - should show persona)
echo ""
echo "Test 1: Without preferences file (should show persona)..."
cd "$TEST_DIR"
OUTPUT=$("$TEST_DIR/scripts/core/agent-session.sh" start sm test-session 2>&1 || true)

if echo "$OUTPUT" | grep -q "Character:"; then
  echo -e "${GREEN}PASS${NC}: Persona shown when no preferences file"
else
  echo -e "${RED}FAIL${NC}: Persona NOT shown when no preferences file"
  echo "Output was: $OUTPUT"
  exit 1
fi

# Test 2: With character_voice=true (should show persona)
echo ""
echo "Test 2: character_voice=true (should show persona)..."
cat > "$TEST_DIR/.claude/pennyfarthing/preferences.yaml" << 'EOF'
character_voice: true
explain_decisions: true
auto_commit: false
EOF

OUTPUT=$("$TEST_DIR/scripts/core/agent-session.sh" start sm test-session-2 2>&1 || true)

if echo "$OUTPUT" | grep -q "Character:"; then
  echo -e "${GREEN}PASS${NC}: Persona shown when character_voice=true"
else
  echo -e "${RED}FAIL${NC}: Persona NOT shown when character_voice=true"
  echo "Output was: $OUTPUT"
  exit 1
fi

# Test 3: With character_voice=false (should suppress persona)
echo ""
echo "Test 3: character_voice=false (should suppress persona)..."
cat > "$TEST_DIR/.claude/pennyfarthing/preferences.yaml" << 'EOF'
character_voice: false
explain_decisions: true
auto_commit: false
EOF

OUTPUT=$("$TEST_DIR/scripts/core/agent-session.sh" start sm test-session-3 2>&1 || true)

if echo "$OUTPUT" | grep -q "<persona"; then
  echo -e "${RED}FAIL${NC}: Persona shown when character_voice=false (should be suppressed)"
  echo "Output was: $OUTPUT"
  exit 1
else
  echo -e "${GREEN}PASS${NC}: Persona suppressed when character_voice=false"
fi

echo ""
echo -e "${GREEN}=== All character_voice tests passed ===${NC}"
exit 0
