#!/usr/bin/env bash
# DEPRECATED: Use `pf workflow resume` instead.
echo "Warning: resume-workflow.sh is deprecated. Use: pf workflow resume $*" >&2
exec pf workflow resume "$@"
