#!/bin/bash
# pre-commit.sh - Git hook to enforce branch protection and agent validation
#
# Checks:
# 1. Prevents direct commits to protected branches (main, develop)
#    Exception: sprint/ folder commits allowed on protected branches
# 2. Validates agent files when pennyfarthing-dist/agents/*.md is modified
# 3. Validates file references when pennyfarthing-dist/ files are modified (warn only)
# 4. Validates sprint YAML files when sprint/*.yaml is modified
#
# Installation:
#   End-user projects: pf setup (copies to .git/hooks/)
#   Framework/orchestrator: install-git-hooks.sh (symlinks to pennyfarthing-dist/)

set -uo pipefail

# Find project root
# Try find-root.sh via symlink resolution first, then fall back to .git location
REAL_SCRIPT="$(readlink -f "${BASH_SOURCE[0]:-$0}" 2>/dev/null || realpath "${BASH_SOURCE[0]:-$0}" 2>/dev/null || echo "${BASH_SOURCE[0]:-$0}")"
FIND_ROOT="$(dirname "$REAL_SCRIPT")/../lib/find-root.sh"
if [[ -f "$FIND_ROOT" ]]; then
    source "$FIND_ROOT"
else
    # Running as a copy in .git/hooks/ — derive PROJECT_ROOT from git dir
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
    export PROJECT_ROOT
fi

# =============================================================================
# Check 1: Branch Protection
# =============================================================================

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
PROTECTED_BRANCHES="^(main|develop)$"

if [[ $BRANCH =~ $PROTECTED_BRANCHES ]]; then
    # Special case: Allow sprint/ folder commits on protected branches
    # (orchestrator uses trunk-based on main; pennyfarthing uses gitflow on develop)
    STAGED_FILES=$(git diff --cached --name-only)
    NON_SPRINT_FILES=$(echo "$STAGED_FILES" | grep -v "^sprint/")

    # If all staged files are in sprint/, allow the commit
    if [ -z "$NON_SPRINT_FILES" ] && [ -n "$STAGED_FILES" ]; then
        # Continue to agent validation check
        :
    else
        echo ""
        echo "COMMIT BLOCKED"
        echo ""
        echo "You are trying to commit directly to: $BRANCH"
        echo "This violates the git workflow rules."
        echo ""
        echo "Protected branches: main, develop"
        echo ""
        echo "What to do:"
        echo "1. Create a feature branch:"
        echo "   git checkout -b <type>/<epic-story>-<description>"
        echo ""
        echo "2. Example:"
        echo "   git checkout -b feat/8-2-add-authentication"
        echo ""
        echo "3. Then commit your changes on the feature branch"
        echo ""
        echo "Exception: Sprint tracking files (sprint/*) can be committed directly"
        echo ""
        exit 1
    fi
fi

# =============================================================================
# Check 2: Agent File Validation
# =============================================================================

STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || true)
AGENT_FILES=$(echo "$STAGED_FILES" | grep "^pennyfarthing-dist/agents/.*\.md$" || true)

if [[ -n "$AGENT_FILES" ]]; then
    echo "Agent files staged for commit:"
    echo "$AGENT_FILES" | sed 's/^/  /'
    echo ""

    echo "Running agent schema validation..."
    echo ""

    if command -v pf &>/dev/null; then
        if ! pf validate agent; then
            echo ""
            echo "COMMIT BLOCKED - Agent validation failed"
            echo ""
            echo "Fix the validation errors above and try again."
            echo "Run 'pf validate agent' for detailed output."
            echo ""
            exit 1
        fi

        echo ""
        echo "✓ Agent validation passed"
    else
        echo "Warning: pf CLI not found — skipping agent validation."
    fi
fi

# =============================================================================
# Check 3: File Reference Validation (warn only)
# =============================================================================

DIST_FILES=$(echo "$STAGED_FILES" | grep "^pennyfarthing-dist/" || true)
SCRIPT_FILES=$(echo "$STAGED_FILES" | grep "^scripts/validate-refs" || true)

if [[ -n "$DIST_FILES" || -n "$SCRIPT_FILES" ]]; then
    VALIDATE_REFS="$PROJECT_ROOT/scripts/validate-refs.js"

    if [[ -f "$VALIDATE_REFS" ]] && command -v node &>/dev/null; then
        echo "Running file reference validation..."
        if ! node "$VALIDATE_REFS" 2>&1; then
            echo ""
            echo "WARNING: File reference issues detected (see above)"
            echo "CI will fail on these — fix before pushing."
            echo ""
        else
            echo "✓ File reference validation passed"
            echo ""
        fi
    fi
fi

# =============================================================================
# Check 4: Sprint YAML Validation
# =============================================================================

SPRINT_YAML_FILES=$(git diff --cached --name-only -- 'sprint/*.yaml' 'sprint/archive/*.yaml' 2>/dev/null \
    | grep -v 'sprint-template\.yaml$' \
    | grep -v 'sprint/completed\.yaml$' \
    | grep -v 'sprint/context/archived/' \
    | grep -v 'sprints\.yaml$' \
    | grep -v 'sprint/demos/' || true)

if [[ -n "$SPRINT_YAML_FILES" ]]; then
    echo "Sprint YAML files staged for commit:"
    echo "$SPRINT_YAML_FILES" | sed 's/^/  /'
    echo ""

    # Find python3
    PYTHON=""
    if command -v python3 &>/dev/null; then
        PYTHON="python3"
    elif command -v python &>/dev/null; then
        PYTHON="python"
    fi

    if [[ -z "$PYTHON" ]]; then
        echo "Warning: Python not found, skipping sprint YAML validation."
    else
        echo "Running sprint YAML validation..."

        # Set PYTHONPATH to include pennyfarthing source (src/ layout)
        PYTHONPATH_ORIG="${PYTHONPATH:-}"
        if [[ -d "$PROJECT_ROOT/pennyfarthing/pennyfarthing-dist/src" ]]; then
            export PYTHONPATH="$PROJECT_ROOT/pennyfarthing/pennyfarthing-dist/src${PYTHONPATH_ORIG:+:$PYTHONPATH_ORIG}"
        elif [[ -d "$PROJECT_ROOT/.pennyfarthing/src" ]]; then
            export PYTHONPATH="$PROJECT_ROOT/.pennyfarthing/src${PYTHONPATH_ORIG:+:$PYTHONPATH_ORIG}"
        fi

        VALIDATION_FAILED=0
        while IFS= read -r yaml_file; do
            FULL_PATH="$PROJECT_ROOT/$yaml_file"
            if [[ ! -f "$FULL_PATH" ]]; then
                echo "  Warning: $yaml_file not found (deleted?), skipping"
                continue
            fi
            if ! $PYTHON -c "
import sys
from pathlib import Path
from pf.sprint.validate_cmd import validate_sprint_yaml
result = validate_sprint_yaml(Path(sys.argv[1]))
if result.errors:
    for e in result.errors:
        line = f' (line {e.line})' if e.line else ''
        print(f'  ERROR [{e.category}]{line}: {e.message}', file=sys.stderr)
if result.format_issues:
    for f in result.format_issues:
        print(f'  FORMAT: {f.message}', file=sys.stderr)
sys.exit(0 if result.valid else 1)
" "$FULL_PATH"; then
                VALIDATION_FAILED=1
            fi
        done <<< "$SPRINT_YAML_FILES"

        # Restore PYTHONPATH
        if [[ -n "$PYTHONPATH_ORIG" ]]; then
            export PYTHONPATH="$PYTHONPATH_ORIG"
        else
            unset PYTHONPATH
        fi

        if [[ $VALIDATION_FAILED -eq 1 ]]; then
            echo ""
            echo "COMMIT BLOCKED - Sprint YAML validation failed"
            echo ""
            echo "Fix: Review errors above, then run:"
            echo "  python3 -m pf.sprint.validate_cmd --fix <file>"
            echo ""
            exit 1
        fi

        echo "✓ Sprint YAML validation passed"
        echo ""
    fi
fi

exit 0
