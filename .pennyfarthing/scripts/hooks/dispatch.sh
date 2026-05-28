#!/usr/bin/env bash
# Plugin lifecycle hook wrapper: run the pf dispatcher for one event.
# Registered in hooks/hooks.json. $1 is the event name (PreToolUse, etc).
set -uo pipefail
exec uv run --project "${CLAUDE_PLUGIN_ROOT}/runtime" --quiet \
  pf hooks dispatch "$1"
