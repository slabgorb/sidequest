#!/bin/bash
# pennyfarthing-dispatcher: Git hook dispatcher for __HOOK_NAME__
# Runs all executable scripts in __HOOK_NAME__.d/ in sorted order.
# Installed by pennyfarthing — do not edit manually.

set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_NAME="__HOOK_NAME__"
D_DIR="${HOOK_DIR}/${HOOK_NAME}.d"

# If .d/ directory doesn't exist or is empty, exit successfully
if [[ ! -d "${D_DIR}" ]]; then
  exit 0
fi

# Capture stdin for hooks that receive input (e.g., pre-push)
STDIN_DATA=""
if [[ ! -t 0 ]]; then
  STDIN_DATA="$(cat /dev/stdin)"
fi

# Run each executable script in sorted order
for hook_script in $(ls "${D_DIR}/" 2>/dev/null | sort); do
  script_path="${D_DIR}/${hook_script}"

  # Skip non-executable files
  if [[ ! -x "${script_path}" ]]; then
    continue
  fi

  # Run the hook, forwarding arguments and stdin
  if [[ -n "${STDIN_DATA}" ]]; then
    echo "${STDIN_DATA}" | "${script_path}" "$@"
  else
    "${script_path}" "$@"
  fi

  exit_code=$?
  if [[ ${exit_code} -ne 0 ]]; then
    exit ${exit_code}
  fi
done

exit 0
