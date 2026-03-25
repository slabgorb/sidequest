#!/bin/bash
# DEPRECATED: Use `pf sprint story finish` instead.
set -euo pipefail
echo "DEPRECATED: finish-story.sh is deprecated. Forwarding to 'pf sprint story finish'." >&2
exec pf sprint story finish "$@"
