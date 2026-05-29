---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-18: GM-panel NPC Registry widget reads only npc_pool — merge snapshot.npcs so roster NPCs aren't a false-negative

## Business Context

The GM panel is the lie-detector (CLAUDE.md OTEL Observability Principle) — a
dev/Keith tool for verifying subsystems actually engaged. During playtest
2026-05-28 it lied by omission: the OTEL ② State "NPC Registry" widget showed "No
NPCs in registry yet" for an entire coyote_star session despite a 12-NPC authored
roster and three crew present in the cockpit narration (finding #C1, display
half). A panel that reads empty when the world is full undermines the one tool
that catches narrator confabulation. This is a small, cosmetic dashboard fix that
restores the panel's trustworthiness.

## Technical Guardrails

**Provenance — display-only follow-up to the #C1 engine fix (already merged,
sidequest-server PR #510).** Do not re-open the engine question; this is purely
the widget.

### Root cause (the two-tier model)

- `snapshot.npcs` = the authored **roster** (full `Npc` objects: disposition,
  OCEAN, belief). Presence is tracked via `Npc.last_seen_location`.
- `snapshot.npc_pool` = lightweight `NpcPoolMember` **walk-ons** the narrator
  invents on the fly.
- Roster NPCs are **deliberately not mirrored** into `npc_pool` (see
  `narration_apply._apply_npc_mentions` — an `npcs_hit` updates `last_seen_*` and
  does not append to the pool). So `npc_pool == []` with a full roster is correct
  state, not a bug.
- The widget in `sidequest-server/sidequest/server/static/dashboard.html` reads
  **only** `npc_pool`, so it shows empty for a roster-only session.

### Fix

- The widget should read/merge `snapshot.npcs` (roster) with `snapshot.npc_pool`
  (walk-ons) so the panel reflects who is actually in the world.

### Constraints

- **Cosmetic dashboard change** — per CLAUDE.md this class does NOT require new
  OTEL spans (the data already exists on the snapshot; this is a display read).
- Do not change the engine's two-tier storage model (the #C1 engine fix already
  resolved the functional half — `run_npc_agency` resolves the roster). This story
  touches the dashboard only.

## Scope Boundaries

**In scope:**
- Update the NPC Registry widget (`dashboard.html`) to display roster NPCs
  (`snapshot.npcs`) in addition to `npc_pool` walk-ons.
- Distinguish (or at least not conflate) roster vs walk-on origin in the display.

**Out of scope:**
- Any engine/storage change to `npcs` / `npc_pool` (the #C1 engine fix is done).
- The `run_npc_agency` resolution logic (already fixed).
- Broader GM-panel redesign.

## AC Context

1. **Roster shown:** the NPC Registry widget displays authored-roster NPCs
   (`snapshot.npcs`) alongside `npc_pool` walk-ons. *Verify:* load a session whose
   State Raw JSON has `npcs` populated and `npc_pool: []` → roster NPCs render.
2. **No false-negative:** a session with a populated roster and an empty
   `npc_pool` (the exact #C1 coyote_star shape) shows the roster NPCs, not "No NPCs
   in registry yet."
3. **Origin distinguished:** the widget does not conflate roster NPCs with
   narrator-invented walk-ons in its display.

### Verification Guidance (trivial workflow)
- Open the dashboard against a save with a roster + empty pool (e.g. a coyote_star
  snapshot) and confirm the roster renders; confirm a walk-on-only session still
  renders walk-ons.

### Files to Modify
- `sidequest-server/sidequest/server/static/dashboard.html` — the ② State NPC
  Registry widget data source.

## Assumptions

- The dashboard already receives `snapshot.npcs` in the State payload it renders
  (the Raw JSON shows it), so the fix is a read/merge in the widget, not a new data
  channel.
- p3 hygiene: the gotcha is documented in the sq-playtest skill, so the panel
  isn't mis-read in the meantime; this is the proper display fix, not urgent.
