#!/usr/bin/env bash
# DEPRECATED: Use `pf git branches` instead.
echo "DEPRECATED: create-feature-branches.sh — use 'pf git branches' instead" >&2
exec pf git branches "$@"
