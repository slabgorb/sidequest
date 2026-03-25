#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow start` instead.
echo "Warning: start-workflow.sh is deprecated. Use: pf workflow start $*" >&2
exec pf workflow start "$@"
