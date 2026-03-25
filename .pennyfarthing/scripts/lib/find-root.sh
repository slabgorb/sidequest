#!/usr/bin/env bash
# Shared utility: Find project root
#
# Resolution order:
# 1. Honor explicit PROJECT_ROOT override (from Claude Code or user)
# 2. BASH_SOURCE derivation (auto-detect caller's location)
# 3. PWD walk looking for .pennyfarthing/ (fallback)
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/../lib/find-root.sh"
#   # PROJECT_ROOT is now set

# Allow explicit override
if [[ -n "${PROJECT_ROOT:-}" ]]; then
    export PROJECT_ROOT
    return 0 2>/dev/null || exit 0
fi

# BASH_SOURCE approach: derive from caller's location
# BASH_SOURCE[1] is the script that sourced us, BASH_SOURCE[0] is this file
_caller_script="${BASH_SOURCE[1]:-}"
if [[ -n "$_caller_script" ]]; then
    _real_dir="$(cd "$(dirname "$_caller_script")" && pwd -P)"
    if [[ "$_real_dir" == */pennyfarthing-dist/scripts/* ]] || \
       [[ "$_real_dir" == */.pennyfarthing/scripts/* ]]; then
        # Extract package root from path
        _pkg="${_real_dir%/scripts/*}"
        _pkg="${_pkg%/pennyfarthing-dist}"
        _pkg="${_pkg%/.pennyfarthing}"
        if [[ "$_pkg" == */node_modules/* ]]; then
            PROJECT_ROOT="${_pkg%%/node_modules/*}"
        elif [[ -d "$_pkg/.pennyfarthing" ]]; then
            PROJECT_ROOT="$_pkg"
        elif [[ -d "$_pkg/../.pennyfarthing" ]]; then
            # Dogfooding: pennyfarthing/ inlined inside orchestrator
            PROJECT_ROOT="$(cd "$_pkg/.." && pwd -P)"
        else
            PROJECT_ROOT="$_pkg"
        fi
        unset _real_dir _pkg _caller_script
        export PROJECT_ROOT
        return 0 2>/dev/null || exit 0
    fi
    unset _real_dir
fi
unset _caller_script

# Fallback: walk up from PWD looking for .pennyfarthing/
_d="$PWD"
while [[ ! -d "$_d/.pennyfarthing" ]] && [[ "$_d" != "/" ]]; do
    _d="$(dirname "$_d")"
done

if [[ -d "$_d/.pennyfarthing" ]]; then
    PROJECT_ROOT="$_d"
else
    echo "Error: Could not find .pennyfarthing/ directory" >&2
    echo "Are you in a Pennyfarthing-enabled project?" >&2
    exit 1
fi

unset _d
export PROJECT_ROOT
