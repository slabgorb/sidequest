#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow phase-check` instead.
echo "Warning: phase-owner.sh is deprecated. Use: pf workflow phase-check $*" >&2
exec pf workflow phase-check "$@"
