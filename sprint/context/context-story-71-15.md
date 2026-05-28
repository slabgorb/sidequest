---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-15: ADR-055 — wire per-transition trope-tick + item resource depletion on room-graph movement

## Business Context

ADR-055 (Room Graph Navigation) made two promises that never reached the code: a
trope tick on each room transition, and resource depletion (the canonical "torch
burn") as the party moves through a dungeon. The data model shipped — `RoomDef`,
`discovered_rooms`, `NavigationMode`, and a populated `uses_remaining` on items —
but the *behaviors* that consume that data on movement were never wired.

Why it matters for the playgroup: room-graph dungeon crawl (e.g. `beneath_sunden`,
ADR-106) is meant to create pressure *through traversal* — the Keeper's awareness
escalates as you go deeper, the torch burns down, the dungeon becomes a clock. With
neither mechanic firing, movement is consequence-free: you can wander a megadungeon
indefinitely with no escalation and no attrition. That guts the tension model the
mechanics-first players (Sebastien, Jade) came for, and it makes the dungeon a
diorama instead of a living, ablating space (SOUL: "Living World", "Cut the Dull
Bits" — traversal should *do something* or be cut).

## Technical Guardrails

**Provenance — do NOT re-investigate the diagnosis.** Surfaced by the ADR-accuracy
audit (Architect, 2026-05-28), verified against HEAD. ADR-055's own "Implementation
status § Dark" section already lists these two gaps; the audit confirmed them in
code. This is documentation-confirmed drift, not a stale-save artifact. ADR-055 now
carries a 2026-05-28 amendment recording the current state.

### Root cause / current state (file:line pinned)

1. **Per-transition trope tick — UNWIRED.** `grep tick_on_room_transition` returns
   zero hits across the tree. The trope tick machinery exists
   (`sidequest/game/trope_tick.py:81` `tick_tropes`, using
   `passive_progression.rate_per_turn` at `:214`), but nothing calls a tick on a
   room transition. The transition seam where it belongs is
   `sidequest/game/room_movement.py:59` `process_room_entry` (idempotent — it
   records the visited room, so it is the natural once-per-transition hook).
2. **Item resource depletion — UNWIRED.** `uses_remaining` is *written* and never
   decremented: seeded from `catalog_item.resource_ticks` at
   `sidequest/server/dispatch/chargen_loadout.py:66`, and set to `None` at several
   other sites (`narration_apply.py:2038`, `builder.py:1906`, `:1979`). No code
   path decrements it on movement or use. The torch never burns.

### Fix direction (surgical — do not over-build)

- Wire a **once-per-transition** trope tick into `process_room_entry` (room-graph
  mode only), reusing the existing `tick_tropes` / `rate_per_turn` machinery. Do
  NOT invent a parallel progression system. Guard against double-ticking against
  the existing per-interaction tick (see Constraints).
- Wire **resource depletion** for items carrying a finite `uses_remaining` so they
  decrement on the ADR-055 trigger (per-transition for movement-consumed resources
  like light sources). Follow ADR-055's stated depletion model; if the trigger is
  ambiguous for a given item class, scope to movement-consumed items and log a
  Design Deviation rather than guessing a broader model.
- Emit OTEL on both decisions (CLAUDE.md Observability mandate) — the GM panel must
  see "trope ticked on transition" and "item X depleted, N→N-1".

### Constraints

- **Room-graph mode only.** These mechanics fire under `NavigationMode` room-graph
  traversal, NOT region-mode cartography. Do not change region-mode behavior.
- **No double-tick.** The per-interaction trope tick (`tick_tropes` on the turn
  loop) must not be doubled by the new per-transition tick. Establish a clear,
  tested rule for which fires when (e.g. transition-tick is the room-graph
  equivalent of the per-turn tick, not additive to it).
- **Idempotency.** `process_room_entry` already records visited rooms; re-entering a
  known room must not re-tick/re-deplete unless ADR-055 intends re-entry to cost.
  Pin the intended rule and test it.
- **No silent fallbacks (CLAUDE.md).** If depletion can't resolve an item's trigger
  class, fail loud / log — do not silently skip.
- **Wiring required (CLAUDE.md).** Prove the tick and depletion fire end-to-end
  through the production movement path (fixture-driven behavior + OTEL-span
  assertions), not just unit calls. No source-text grep wiring tests.

## Scope Boundaries

**In scope:**
- Server: per-transition trope tick wired into `process_room_entry` (room-graph
  mode), reusing `tick_tropes` machinery.
- Server: `uses_remaining` decrement for movement-consumed items on the ADR-055
  trigger, with depletion → exhausted handling.
- Server: OTEL spans for both (transition-tick result; resource-depletion delta).
- Tests: behavior + wiring + no-double-tick + idempotent-re-entry guard.

**Out of scope:**
- Region-mode cartography behavior and the `MAP_UPDATE` emission (the ADR-055
  "MAP_UPDATE deleted" claim was already corrected in its 2026-05-28 amendment —
  the wire name is reused for the region-mode `CartographyMapMessage`; do NOT touch
  it here).
- New item categories, new trope schema, or a redesign of `process_room_entry`.
- ADR-106 megadungeon materializer wiring (that landed; not this story).
- Backfilling depletion onto existing live saves.

## AC Context

1. **Per-transition trope tick (room-graph mode):** On a room transition via
   `process_room_entry`, progressing tropes advance once by their
   `passive_progression.rate_per_turn` (reusing `tick_tropes`), in room-graph mode
   only. A transition emits a trope-tick OTEL span carrying the matched/advanced
   tropes.
2. **No double-tick:** The new per-transition tick does not compound the existing
   per-interaction `tick_tropes`. The which-fires-when rule is explicit and tested.
3. **Idempotent re-entry:** Re-entering an already-`discovered` room does not
   re-tick/re-deplete unless ADR-055 specifies a re-entry cost (pin the rule; test
   both directions).
4. **Item resource depletion:** Items carrying a finite `uses_remaining`
   (seeded from `resource_ticks`) decrement on the ADR-055 movement trigger; at
   zero, the item is marked exhausted (define the exhausted state; do not delete the
   item silently).
5. **OTEL observability (CLAUDE.md):** Both decisions emit spans — a trope-tick span
   on transition and a resource-depletion span (`item`, `before`, `after`). On a
   skip (region mode / no progressing tropes / no depletable items) emit nothing or
   an explicit skip reason; never a silent partial.

### Test Guidance (TEA red phase)

- **Fixture-driven behavior test:** build a room-graph genre pack + snapshot with a
  progressing trope and a torch (`uses_remaining` from `resource_ticks`); drive a
  transition through the real `process_room_entry` seam; assert trope advanced once
  and torch decremented once, with both spans fired. Canonical shape:
  `tests/server/test_location_description_emit.py`.
- **No-double-tick test:** a single room-graph turn that both transitions and runs
  the interaction loop advances the trope by exactly one tick's worth.
- **Idempotent re-entry test:** re-entering a discovered room does not re-tick /
  re-deplete (or does, per the pinned rule).
- **Region-mode regression:** region-mode traversal still does NOT fire these.

### Files to Modify
- `sidequest/game/room_movement.py` — `process_room_entry` transition hook.
- `sidequest/game/trope_tick.py` — reuse `tick_tropes`; possibly a transition-mode entry.
- Item depletion: the use/movement path that owns `uses_remaining`
  (`sidequest/server/narration_apply.py` and/or `room_movement.py`).
- `sidequest/telemetry/` span definitions — add transition-tick + depletion spans.

## Assumptions

- ADR-055's intended model is a once-per-transition tick equivalent to the per-turn
  tick, not additive. If ADR-055 is ambiguous, the Architect's reading (equivalent,
  not additive) governs; deviations get logged.
- `resource_ticks` on catalog items is the authored source of finite uses; this
  story consumes it, it does not redefine the schema.
- Depletion trigger for non-movement-consumed items (e.g. charges spent by an
  ability) is OUT of scope; only movement-consumed depletion (torch model) is in.
