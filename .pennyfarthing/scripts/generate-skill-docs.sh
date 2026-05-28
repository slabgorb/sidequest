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
# This is a framework build script in scripts/ - go up 1 level to find framework root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
export PROJECT_ROOT

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

# Find the compiled generator (now in core, previously in shared)
DIST_FILE="${PROJECT_ROOT}/packages/core/dist/shared/generate-skill-docs.js"
if [[ ! -f "$DIST_FILE" ]]; then
  echo "Error: generate-skill-docs.js not found at $DIST_FILE" >&2
  echo "  Build core first: pnpm --filter @pennyfarthing/core run build:tsc" >&2
  exit 1
fi

# Run the generator
if $DRY_RUN; then
  node "$DIST_FILE" --registry "$REGISTRY_PATH" --dry-run
else
  # Ensure output directory exists
  mkdir -p "$(dirname "$OUTPUT_PATH")"
  node "$DIST_FILE" --registry "$REGISTRY_PATH" --output "$OUTPUT_PATH"
fi
