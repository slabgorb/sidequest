---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-26: ship_combat edge bars render 0/1000000 hp — fix ablative-HP/edge-pool init for ship_combat (ADR-114)

## Business Context

During the 67-8 live repro, a `ship_combat` confrontation in `space_opera`
rendered its edge bars as **`0/1000000`** instead of a sane hull readout
(`30/30` per content). For Sebastien and Jade — the playgroup's mechanics-first
players — a nonsense `0/1000000` bar is exactly the legibility failure
ADR-114's ablative-HP work was meant to kill: the player-facing surface is
supposed to *expose the math* (hull HP ablating under fire), and a bar pinned at
one million HP that never moves tells them nothing about whether the engine is
even engaged. Worse, a `0/1000000` bar is a SOUL "Illusionism" tell — the kind
of mechanically-unbacked surface this whole epic exists to eliminate. A ship
fight that *looks* like it has a million-HP hull and zero current HP reads as
broken before a single shot lands.

The fix restores correct hull-HP bounds to the player-facing confrontation
overlay for `ship_combat` (and any `hp_depletion` ship-scale confrontation), so
the bar shows the seeded hull pool (e.g. `30/30`) and ablates as the SWN attack
pipeline chews through it — the satisfying "handful of rounds" the content was
calibrated for (`rules.yaml:239-243`).

## Technical Guardrails

This is an **ablative-HP / edge-pool initialization** bug, not a UI rendering
bug per se. The root cause is in confrontation instantiation. Real anchors:

- **`sidequest/server/dispatch/encounter_lifecycle.py:1037-1040`** — the
  inert-metric synthesis for `hp_depletion` confrontations. When a cdef declares
  no dial (`win_condition: hp_depletion`, which `ship_combat` uses), the code
  synthesizes placeholder dials:
  ```python
  pm = MetricDef(name="hp", starting=0, threshold=1_000_000)
  om = MetricDef(name="hp", starting=0, threshold=1_000_000)
  ```
  The inline comment (lines 1031-1034) calls these "absurdly high threshold
  (1e6, never reached) ... belt-and-suspenders." These placeholders are NOT
  meant to be player-facing — but they are what leaks to the UI.
- **`sidequest/server/dispatch/confrontation.py:218-234`** —
  `build_confrontation_payload` serializes
  `payload["player_metric"] = encounter.player_metric.model_dump(...)` and
  `payload["opponent_metric"] = ...`. For a `ship_combat` encounter these dump
  the inert synthesized dials (`current 0`, `threshold 1_000_000`) → **this is
  the source of the `0/1000000` edge bar.**
- **`sidequest/server/dispatch/confrontation.py:244-262`** — the *correct* hull
  HP path: under `win_condition == "hp_depletion"` with a `core_resolver`,
  additive `player_hp` / `opponent_hp` keys are populated from
  `core.hp.current` / `core.hp.max`. The seeded hull HP exists here — the bug is
  that the UI's edge bar reads `player_metric`/`opponent_metric` (the inert
  dial) rather than `player_hp`/`opponent_hp` (the real pool), OR these hp keys
  aren't being populated for ship_combat (e.g. `core_resolver` is `None`, or the
  opponent actor never got a backing core). Confirm which during the failing-test
  diagnosis.
- **`sidequest/server/dispatch/encounter_lifecycle.py:103-184`** —
  `_seed_combat_hp_depletion_to_npcs`. Seeds opponent `Npc.core.hp` (via
  `hp_pool_from_hp`, `creature_core.py:47`) and `armor_class` from
  `cdef.opponent_hp` / `cdef.opponent_armor_class`. Called from line 1134 (the
  combat-category + `hp_depletion` handshake branch). For `ship_combat` the
  enemy hull is content-authored: `rules.yaml:243` `hp: 30`, `:244`
  `armor_class: 14`. Verify this seeding runs for ship_combat and that
  `find_creature_core(opponent_name)` reaches the seeded pool.
- **`sidequest/game/creature_core.py:21-61`** — `HpPool(current/max/base_max)`
  and `hp_pool_from_hp(hp)` (ADR-114 §1). The sane bound is
  `current == max == base_max == 30` for the seeded raider-frigate.
- **Content (read-only):**
  `sidequest-content/genre_packs/space_opera/rules.yaml:221-245` — the
  `ship_combat` cdef. `win_condition: hp_depletion`, `opponent_default_stats.hp:
  30`, `armor_class: 14`. **The content is correct — do not edit it.** The bug
  is engine-side: the inert dial leaks to the bar instead of the seeded hull.

**ADR reference:** ADR-114 (`docs/adr/114-ablative-hp-substrate.md`) — HP
reclaims the lethality track; partial (Part 1 live). The `HpPool` on
`CreatureCore` is the substrate; this story makes the ship-scale confrontation
*render* against it instead of the inert dial.

**What NOT to touch:**
- Do NOT change the content (`rules.yaml`) — hull 30 / AC 14 is calibrated.
- Do NOT remove the inert `1_000_000` placeholder dial wholesale — ~9 live
  metric readers depend on a non-`None` `player_metric`/`opponent_metric`
  existing (comment at lines 1031-1034). The fix is to stop the inert dial from
  being what the *bar* renders, not to delete the placeholder.
- Do NOT alter the dial-based (`dial_threshold`) confrontation path — only the
  `hp_depletion` ship-scale rendering.

## Scope Boundaries

**In scope:**
- A failing test reproducing the `0/1000000` edge-bar render for `ship_combat`.
- The corrected init/payload so the ship_combat confrontation surfaces sane hull
  HP bounds (`30/30` for the calibrated raider-frigate) on the player-facing
  overlay, ablating correctly as the SWN strike pipeline applies damage.
- An OTEL span proving the hull pool initialized with sane bounds (per the
  OTEL-on-every-subsystem principle).

**Out of scope:**
- Any content change to `ship_combat` stats (hull/AC calibration is done).
- Dial-based confrontations and personal-scale `hp_depletion` combat (unless the
  same inert-dial leak affects them — if so, note it but keep this story's fix
  scoped to ship_combat; broader fix is a follow-up).
- UI client work beyond confirming which payload field the bar reads (UI repo is
  read-only here; flag a Delivery Finding if the bar must switch from
  `player_metric` to `player_hp` on the client).
- The full ADR-114 Part 2+ rollout.

## AC Context

- **AC1 — failing repro (RED):** A test instantiates a `ship_combat`
  confrontation (via `instantiate_encounter_from_trigger` on a synthetic
  `space_opera` snapshot) and asserts the rendered confrontation payload's edge
  bar currently shows `0/1000000`. *How TEA verifies:* build the payload via
  `build_confrontation_payload(encounter, cdef, ...)`; on the unfixed code,
  `payload["opponent_metric"]` dumps `current: 0`, `threshold: 1000000`. The
  test asserts the **fixed** behavior fails initially — i.e. it asserts the bar
  reflects hull `30/30` and watches that assertion fail RED before the fix.
- **AC2 — corrected hull bounds (GREEN):** After the fix, the player-facing
  ship_combat overlay shows sane hull HP — opponent `current: 30, max: 30`
  (from `cdef.opponent_hp` via the seeded `HpPool`), not `0/1000000`. *Verify:*
  `payload["opponent_hp"] == {"current": 30, "max": 30}` is populated AND the
  field the UI bar reads no longer carries the `1_000_000` threshold for
  ship_combat. Edge cases to cover:
  - opponent actor that was router-named and never materialized → the
    `_seed_combat_hp_depletion_to_npcs` create-branch (lines 149-164) seeds a
    fresh `CreatureCore` so `find_creature_core` reaches it (hull `30`, not `0`).
  - `core_resolver` threaded into `build_confrontation_payload` so the
    `player_hp`/`opponent_hp` keys actually populate (lines 244-262) — a legacy
    call path that omits `core_resolver` would silently drop the hp keys and
    fall back to the inert dial, reproducing the bug.
  - player-side primary hull also resolves (PC ship's own hull pool), not just
    opponent.
- **AC3 — OTEL proof of init (lie-detector):** An OTEL span fires proving the
  hull pool initialized with sane bounds at ship_combat instantiation. *Reuse:*
  `_seed_combat_hp_depletion_to_npcs` already emits `npc_edge_published_span`
  (lines 175-184) carrying `current=npc.core.hp.current`, `max=npc.core.hp.max`,
  `seed_source="opponent_default_stats"`. The test drives the real handshake and
  asserts the span fired with `current == 30`, `max == 30` (NOT `0` / not
  `1_000_000`). This is the GM-panel evidence that the pool seeded correctly
  rather than the engine improvising a million-HP hull. If the existing span
  doesn't cover the player-side hull, extend coverage so both sides emit.
- **AC4 — wiring test:** Drive the full instantiation path
  (`instantiate_encounter_from_trigger` → `_seed_combat_hp_depletion_to_npcs` →
  payload build) for a `ship_combat` trigger and assert (a) the seeded
  `Npc.core.hp` is reachable via `snapshot.find_creature_core(opponent_name)`
  with `current == 30`, and (b) the OTEL seed span fired — a behavior/OTEL
  wiring test, not a source-grep (per the repo's "No Source-Text Wiring Tests"
  rule).

## Assumptions

- The `0/1000000` render originates from the inert synthesized dial at
  `encounter_lifecycle.py:1039-1040` leaking through
  `build_confrontation_payload`'s `player_metric`/`opponent_metric` dump
  (`confrontation.py:223-224`), NOT from a separate edge-pool seeded with
  `1_000_000`. (Diagnosis during RED confirms; if the source is elsewhere — e.g.
  a real `HpPool` seeded with `max=1_000_000` — log a Design Deviation and
  re-anchor the fix.)
- `ship_combat` reaches the `hp_depletion` handshake branch
  (`encounter_lifecycle.py:1127-1140`, gated on `cdef.category == "combat"` and
  `win_condition == hp_depletion`); `ship_combat`'s cdef has `category: combat`
  (`rules.yaml:226`) and `win_condition: hp_depletion` (`:230`), so it does.
- The content stats (`hp: 30`, `armor_class: 14`) are present and validated at
  load — the cdef validator requires `hp`/`armor_class`/`dexterity` under
  `opponent_default_stats` for combat `hp_depletion` confrontations
  (`_seed_combat_hp_depletion_to_npcs` docstring lines 131-135), so they're
  guaranteed at this seam.
- Story 59-23 (chassis-vs-chassis ship_combat / ADR-116 Other-seating) is
  merged — the opponent hull is seated as a real "Other" before this fix runs;
  this story fixes how that already-seated hull *renders*, not whether it's
  seated.
- If the UI bar reads `player_metric.current/threshold` rather than
  `player_hp.current/max`, the server-side fix may need the client to switch
  fields — that's a UI-repo change. Confirm during implementation and raise a
  Delivery Finding rather than editing the read-only UI from this server story.
