---
id: 96
title: "Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps"
status: accepted
date: 2026-05-10
deciders: ["Keith Avery"]
supersedes: [89]
superseded-by: null
related: [55, 71, 86, 89]
tags: [game-systems, frontend-protocol, media-audio]
implementation-status: partial
implementation-pointer: docs/superpowers/plans/2026-05-10-cavern-renderer-revival.md
---

# ADR-096: Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps

## Status

Accepted (2026-05-10).

Revives ADR-089 (superseded 2026-05-02 by ADR-086) per ADR-089's own
"do not revive — write a fresh ADR" instruction. ADR-086's recipe
pipeline (portraits / POIs / illustrations) is unchanged and
unaffected; ADR-096 is a sibling decision for tactical maps
specifically.

## Context

ADR-071 (tactical ASCII grids → SVG) was the original tactical-map path.
It was implemented and shipped, then went through many rounds of fixes
without ever clearing a usability bar. Hand-authored grids produce
rectangles-with-clipped-corners, not organic caverns. The cavern
character lives only in narrative prose. ADR-089 proposed porting
maze-maker's Cellular automaton to Python and emitting pre-rendered PNG
battle maps; it was superseded by ADR-086 because a competing recipe
pipeline shipped first and the cellular path's authoring overhead
seemed unjustified.

What's changed: a Claude Design hi-fi handoff (variation A, 2026-05-10)
gave us a concrete UI target — image-as-floor with token overlays,
selection state, action panel — that requires exactly the
mechanically-grounded structure (cells, LOS, AoE anchoring, movement
validation) ADR-086's prompt-interpreted geometry can't deliver. ADR-086
is correct for portraits and POIs and stays in production. Tactical
caverns need the cellular path.

## Decision

Revive ADR-089's core idea — port maze-maker's `Cellular` to Python,
build an authoring-time tool that emits PNG + ASCII-mask sidecars per
room, ship them as committed artifacts in `sidequest-content`. Three
concrete differences from ADR-089:

1. **Authoring source-of-truth is `seed + cellular params`, not the
   mask.** Mask + PNG are derived; same input → byte-identical
   output. Authors edit numbers, not cells.
2. **Cell-stepped math is canonical.** Tokens occupy one cell;
   movement is N cells per turn; reach is Chebyshev radius
   `speed/5`; AoE is evaluated cell-by-cell against the mask. The
   PNG is the visual; the mask is the truth.
3. **Single-merge cutover, no feature flag.** The SVG floor-cell
   rendering paths in `TacticalGridRenderer.tsx` and their tests are
   deleted in the same merge that introduces the cellular path.
   `MapOverlay.tsx` (cartography view) and `DungeonMapRenderer.tsx`
   (room-graph view) are unaffected.

## Consequences

**Positive:**

- Tactical caverns finally look like caverns. Keith (the forever-GM
  primary audience) gets a tactical view with organic shapes.
- Sebastien (mechanical-first) gets cell-stepped math that's
  observable in OTEL spans (seed, density, floor_count, mask_sha).
- Alex (slow typist) is unblocked — image renders instantly from a
  static asset, no SVG-recompute lag per frame.
- ADR-071's renderer-rounds-of-fixes loop ends. The expensive part
  (visual rendering) becomes Pillow output that authors verify once
  and commit; the runtime path is `<img>` + token overlays.

**Negative:**

- ~24 cellular rooms + ~6 settlement stubs need authoring for
  `caverns_sunden`. Real authoring effort, not generated content.
- A second uv-managed Python tree appears in `sidequest-content/`.
  Mitigated: it's authoring-only; runtime never sees it.
- PNG bytes go into git history. Mitigated: 18×18 cells × 28px = 504×504
  PNG ≈ tens of kilobytes per room.
- Existing `caverns_sunden` has never had per-room tactical files;
  the ADR-071 hand-authored grids in other worlds (mawdeep,
  grimvault, horden) referenced in ADR-089's text no longer exist
  on disk. No save migration needed.

**Neutral:**

- Settlement rooms get a parallel non-tactical view. Future
  non-procedural room types (e.g., a hand-authored boss arena) slot
  in as new `room_type` values without re-architecting.

## Implementation

See `docs/superpowers/plans/2026-05-10-cavern-renderer-revival.md`.
