#!/usr/bin/env bash
#
# generate-skill-docs.sh - Generate SKILLS.md from skill-registry.yaml
#
# Usage: generate-skill-docs.sh [options]
#
# Options:
#   --registry <path>   Path to skill-registry.yaml
#   --output <path>     Path to write output (default: docs/SKILLS.md)
#   --dry-run           Print output instead of writing file
#   --help, -h          Show this help
#
# Examples:
#   generate-skill-docs.sh
#   generate-skill-docs.sh --dry-run
#   generate-skill-docs.sh --registry ./custom-registry.yaml

set -euo pipefail

# Self-locate: derive PROJECT_ROOT from this script's position
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Detect if we're in framework development or a consumer project
# In framework dev: scripts/misc/generate-skill-docs.sh is in pennyfarthing/pennyfarthing-dist/scripts/misc/
# In consumer: this is symlinked from .pennyfarthing/scripts/misc/
if [[ "$SCRIPT_DIR" == */pennyfarthing/pennyfarthing-dist/scripts/* ]]; then
  # Framework development context - derive from script location
  PROJECT_ROOT="${SCRIPT_DIR%/pennyfarthing-dist/scripts/*}"
  export PROJECT_ROOT
else
  # Consumer project context - use find-root.sh
  source "$SCRIPT_DIR/../lib/find-root.sh"
  # PROJECT_ROOT is now set
fi

# Default paths
REGISTRY_PATH="${PROJECT_ROOT}/pennyfarthing-dist/skills/skill-registry.yaml"
OUTPUT_PATH="${PROJECT_ROOT}/docs/SKILLS.md"
DRY_RUN=false

# Parse arguments
show_help() {
  cat <<EOF
Usage: generate-skill-docs.sh [options]

Generate SKILLS.md documentation from skill-registry.yaml.

Options:
  --registry <path>   Path to skill-registry.yaml (default: pennyfarthing-dist/skills/skill-registry.yaml)
  --output <path>     Path to write output (default: docs/SKILLS.md)
  --dry-run           Print output instead of writing file
  --help, -h          Show this help

Examples:
  generate-skill-docs.sh
  generate-skill-docs.sh --dry-run
  generate-skill-docs.sh --registry ./custom-registry.yaml --output ./SKILLS.md
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      show_help
      exit 0
      ;;
    --registry)
      REGISTRY_PATH="$2"
      shift 2
      ;;
    --output)
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Use --help for usage information" >&2
      exit 1
      ;;
  esac
done

# Check registry exists
if [[ ! -f "$REGISTRY_PATH" ]]; then
  echo "Error: Registry not found: $REGISTRY_PATH" >&2
  exit 1
fi

# Build the TypeScript module if needed
DIST_FILE="${PROJECT_ROOT}/packages/shared/dist/generate-skill-docs.js"
if [[ ! -f "$DIST_FILE" ]]; then
  echo "Building shared package..." >&2
  (cd "${PROJECT_ROOT}/packages/shared" && npm run build) >&2
fi

# Run the generator
if $DRY_RUN; then
  node "$DIST_FILE" --registry "$REGISTRY_PATH" --dry-run
else
  # Ensure output directory exists
  mkdir -p "$(dirname "$OUTPUT_PATH")"
  node "$DIST_FILE" --registry "$REGISTRY_PATH" --output "$OUTPUT_PATH"
fi
