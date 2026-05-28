#!/usr/bin/env bash
# SessionStart plugin hook wrapper.
# 1. Launch the Frame server detached so it outlives this session.
#    `nohup … & disown` is the ONLY spawn pattern that survives Claude Code's
#    hook process-group kill on macOS (spike Q4); plain backgrounding and
#    `setsid` get killed.
# 2. Run the SessionStart dispatcher (session setup, OTEL wiring, agent context).
set -uo pipefail

nohup uv run --project "${CLAUDE_PLUGIN_ROOT}/runtime" --quiet \
  pf frame start --background >/dev/null 2>&1 &
disown

exec uv run --project "${CLAUDE_PLUGIN_ROOT}/runtime" --quiet \
  pf hooks dispatch SessionStart
