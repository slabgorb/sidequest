#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow fix-phase` instead.
echo "Warning: fix-session-phase.sh is deprecated. Use: pf workflow fix-phase $*" >&2
exec pf workflow fix-phase "$@"
