#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow list` instead.
echo "Warning: list-workflows.sh is deprecated. Use: pf workflow list" >&2
exec pf workflow list "$@"
