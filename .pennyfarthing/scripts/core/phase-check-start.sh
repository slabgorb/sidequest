#!/bin/bash
# DEPRECATED: Use `pf handoff phase-check <agent>` instead.
echo "DEPRECATED: phase-check-start.sh — use 'pf handoff phase-check $1' instead" >&2
exec pf handoff phase-check "$@"
