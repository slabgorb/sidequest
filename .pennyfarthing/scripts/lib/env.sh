#!/usr/bin/env bash
# Resolve CLAUDE_PROJECT_DIR in any context (hooks, Bash tool, subshells).
#
# Claude Code sets CLAUDE_PROJECT_DIR for hook execution but NOT for the
# Bash tool environment.  This script fills the gap by walking up from PWD
# to find .pennyfarthing/, mirroring find-root.sh's fallback strategy.
#
# Usage:
#   source .pennyfarthing/scripts/lib/env.sh   # relative (Bash tool)
#   source "$CLAUDE_PROJECT_DIR/.pennyfarthing/scripts/lib/env.sh"  # hooks (already set)
#
# After sourcing, CLAUDE_PROJECT_DIR is exported and safe to use.

if [[ -z "${CLAUDE_PROJECT_DIR:-}" ]]; then
  _d="$PWD"
  while [[ ! -d "$_d/.pennyfarthing" ]] && [[ "$_d" != "/" ]]; do
    _d="$(dirname "$_d")"
  done
  if [[ -d "$_d/.pennyfarthing" ]]; then
    # Guard against nested .pennyfarthing (e.g., inlined child repo).
    # If the found dir sits inside a parent that also has .pennyfarthing/,
    # prefer the parent (outermost project root).
    _parent="$(dirname "$_d")"
    while [[ "$_parent" != "/" ]]; do
      if [[ -d "$_parent/.pennyfarthing" ]]; then
        _d="$_parent"
      fi
      _parent="$(dirname "$_parent")"
    done
    unset _parent
    export CLAUDE_PROJECT_DIR="$_d"
  fi
  unset _d
fi
