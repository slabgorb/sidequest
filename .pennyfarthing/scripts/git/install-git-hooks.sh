#!/usr/bin/env bash
# DEPRECATED: Use `pf git install-hooks` instead.
echo "DEPRECATED: install-git-hooks.sh — use 'pf git install-hooks' instead" >&2
exec pf git install-hooks "$@"
