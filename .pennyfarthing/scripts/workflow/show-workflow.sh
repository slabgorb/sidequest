#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow show` instead.
echo "Warning: show-workflow.sh is deprecated. Use: pf workflow show $*" >&2
exec pf workflow show "$@"
