#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow status` instead.
echo "Warning: workflow-status.sh is deprecated. Use: pf workflow status $*" >&2
exec pf workflow status "$@"
