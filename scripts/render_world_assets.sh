#!/usr/bin/env bash
#
# render_world_assets.sh — render a world's full image asset gate.
#
# Renders every POI landscape and every portrait for one world, uploads them
# to R2 (the canonical asset store), then rebuilds the committed
# r2_manifest.json from a live bucket scan. This is the "lift the asset gate"
# batch for a single world (e.g. story 103-9 / seaboard_of_saints).
#
# The renders run against the LOCAL MLX media daemon — `just daemon` must be
# up first (this is why it can't be a cloud routine). Each image is ~2 min;
# a full world (POIs + portraits) is roughly an hour or two.
#
# Usage:
#   scripts/render_world_assets.sh <genre> <world> [extra render flags...]
#
# Examples:
#   scripts/render_world_assets.sh mutant_wasteland seaboard_of_saints
#   scripts/render_world_assets.sh mutant_wasteland seaboard_of_saints --force
#   scripts/render_world_assets.sh space_opera perseus_cloud --no-upload   # local test, no R2
#
# Notes:
#   * Always run via this script (not bare python3): the render + R2 scripts
#     import boto3, which lives in the orchestrator uv env.
#   * Pass --no-upload to keep PNGs local (test render; skips R2 + manifest).
#   * The renderers skip assets already on R2 unless you pass --force.
#   * Does NOT lift `draft: true` — that is a deliberate, separate human step
#     after you have reviewed the rendered set.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <genre> <world> [extra render flags...]" >&2
  exit 2
fi

GENRE="$1"; WORLD="$2"; shift 2
EXTRA=("$@")   # may be empty; guarded everywhere for bash 3.2 + set -u

# --no-upload anywhere in the extra flags means a local test render; skip the
# R2 manifest rebuild (there is nothing new on the bucket to re-index).
SKIP_MANIFEST=0
if [[ ${#EXTRA[@]} -gt 0 ]]; then
  for f in "${EXTRA[@]}"; do
    [[ "$f" == "--no-upload" ]] && SKIP_MANIFEST=1
  done
fi

LOG_DIR="${HOME}/.sidequest/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="${LOG_DIR}/render-${GENRE}-${WORLD}-${STAMP}.log"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# Run a render script with the world args, appending the optional extra flags
# only when present (bash 3.2 errors on "${EXTRA[@]}" when the array is empty
# under set -u, so branch on the length).
render() {
  local script="$1"
  if [[ ${#EXTRA[@]} -gt 0 ]]; then
    uv run python "scripts/${script}" --genre "$GENRE" --world "$WORLD" "${EXTRA[@]}" 2>&1 | tee -a "$LOG"
  else
    uv run python "scripts/${script}" --genre "$GENRE" --world "$WORLD" 2>&1 | tee -a "$LOG"
  fi
}

log "=== render_world_assets: ${GENRE}/${WORLD} ==="
log "extra flags: ${EXTRA[*]:-(none)}"
log "log file: ${LOG}"

# Fail loud if the media daemon is not up — renders would otherwise hang.
if ! (cd "$ROOT/sidequest-daemon" && uv run sidequest-renderer --status) >>"$LOG" 2>&1; then
  log "ERROR: media daemon is not responding. Start it with: just daemon"
  exit 1
fi
log "daemon: ready"

log "--- [1/3] POI landscapes ---"
render generate_poi_images.py

log "--- [2/3] portraits ---"
render generate_portrait_images.py

if [[ "$SKIP_MANIFEST" -eq 0 ]]; then
  log "--- [3/3] rebuild r2_manifest.json from live bucket ---"
  uv run python scripts/r2_manifest_from_bucket.py 2>&1 | tee -a "$LOG"
else
  log "--- [3/3] skipped (--no-upload: local test render, R2 untouched) ---"
fi

log "=== done: ${GENRE}/${WORLD} ==="
log "Next (manual): review the rendered set, then lift 'draft: true' in worlds/${WORLD}/world.yaml"
