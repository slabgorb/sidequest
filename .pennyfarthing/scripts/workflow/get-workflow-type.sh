#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow type` instead.
echo "Warning: get-workflow-type.sh is deprecated. Use: pf workflow type $*" >&2
exec pf workflow type "$@"
