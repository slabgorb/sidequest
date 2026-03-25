#!/usr/bin/env zsh
#
# generate-tandem-portraits.sh — Generate per-theme tandem cyclist branding images
#
# Processes cyclist_tandem.png source into medium (200x200) and large (300x300)
# versions for each theme's portrait directory.
#
# Usage: ./generate-tandem-portraits.sh [--source PATH] [--portraits-dir PATH]

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
# Source image lives in packages/core/src/public/images/
DIST_DIR="${SCRIPT_DIR}/../.."
# Find project root (contains packages/)
PROJECT_ROOT="${DIST_DIR}"
[[ -d "${PROJECT_ROOT}/packages" ]] || PROJECT_ROOT="${DIST_DIR}/.."
SOURCE_IMAGE="${PROJECT_ROOT}/packages/core/src/public/images/cyclist-tandem-source.png"
PORTRAITS_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE_IMAGE="$2"; shift 2 ;;
    --portraits-dir) PORTRAITS_DIR="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Auto-detect portraits directory if not provided
# Output goes to packages/cyclist/portraits/ (Cyclist UI asset, not persona portraits)
if [[ -z "$PORTRAITS_DIR" ]]; then
  PORTRAITS_DIR="${PROJECT_ROOT}/packages/cyclist/portraits"
fi

# Resolve to absolute path
PORTRAITS_DIR="${PORTRAITS_DIR:A}"

if [[ ! -f "$SOURCE_IMAGE" ]]; then
  echo "Error: Source image not found: $SOURCE_IMAGE"
  exit 1
fi

if [[ ! -d "$PORTRAITS_DIR" ]]; then
  echo "Error: Portraits directory not found: $PORTRAITS_DIR"
  exit 1
fi

# Verify ImageMagick is available
if ! command -v magick &>/dev/null; then
  echo "Error: ImageMagick (magick) not found in PATH"
  exit 1
fi

echo "Source: $SOURCE_IMAGE"
echo "Portraits: $PORTRAITS_DIR"
echo ""

generated=0
skipped=0

for theme_dir in "$PORTRAITS_DIR"/*/; do
  theme_name="$(basename "$theme_dir")"

  for size_name size_px in medium 200 large 300; do
    size_dir="${theme_dir}${size_name}"
    output="${size_dir}/cyclist-tandem.png"

    # Create size directory if it doesn't exist
    mkdir -p "$size_dir"

    # Generate resized tandem portrait
    magick "$SOURCE_IMAGE" -resize "${size_px}x${size_px}" -strip "$output"
    generated=$((generated + 1))
  done
done

echo ""
echo "Generated: $generated tandem portraits"
echo "Done."
