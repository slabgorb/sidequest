#!/usr/bin/env bash
# DEPRECATED: Use `pf git status` instead.
echo "DEPRECATED: git-status-all.sh — use 'pf git status' instead" >&2
exec pf git status "$@"
