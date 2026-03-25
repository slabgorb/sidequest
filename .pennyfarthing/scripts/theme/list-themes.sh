#!/usr/bin/env bash
# list-themes.sh - List all available persona themes
#
# Thin wrapper: discovery logic lives in pf.common.themes
#
# Usage: list-themes.sh [--current-only]

set -euo pipefail

if [[ "${1:-}" == "--current-only" ]]; then
    pf theme show --current-only
else
    pf theme list
fi
