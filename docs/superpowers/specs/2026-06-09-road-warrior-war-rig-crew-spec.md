# Plan 4 — War Rig (crewed vessel): the architectural fork, settled

**Date:** 2026-06-09
**Status:** Design — resolves the open fork in `2026-06-04-road-warrior-cwn-rig-combat-design.md` §5 Plan 4
**Author:** Architect (the Ministry of Silly Walks Official)
**Story:** 86-4 (13 pts) — recommends split into 86-4a (engine core) + 86-4b (CP economy + crises)
**Reuse mandate:** the "net-new crew-seat primitive" the story proposed **already exists** — see §2.

---

## 1. The fork (as stated)

The epic spec (`2026-06-04-…-design.md`, lines 144–146) left Plan 4's resolution path open:

> *Open architectural fork for that spec:* reuse the **ADR-077 dogfight sealed-letter infra**,
> the **`beat_selection`** confrontation path, or a **new crew-seat confrontation type**.

The story text adds: *"NET-NEW crew-seat primitive (`EncounterActor` has no seat field)."*

The requirement Plan 4 must satisfy (epic §2, §4.3): **N PCs man stations on ONE shared
vessel, each committing a concurrent verb per round, against one shared Hull** — the literal
SOUL **Guitar-Solo / wider-action** realization, with the single-seat fighter as the
degenerate solo case.

## 2. Decision

**Reuse the ADR-129 N-Seat Table Engine (`resolution_mode: table_resolution`).** Register a
new table-game kind `war_rig_crew`, bound through the existing `cwn`
`RulesetModule.deal_table()` / `.resolve_table()` seams. **Reject** both named alternatives,
and **do not** add a `seat` field to `EncounterActor`.

The "new crew-seat confrontation type" in the fork is the right *shape* — but it is **80%
already built**. The seat primitive the story says is missing on `EncounterActor` exists today
as `TableSeat` (`game/table/types.py`): `seat_id`, `party_name`, `is_pc`, `status`, and an
open `private_state: dict` that already carries kind-specific per-seat state. The sealed,
concurrent, simultaneous-resolution round loop the War Rig needs is exactly
`resolve_table()`. This is the "Don't Reinvent — Wire Up What Exists" principle applied to
the fork itself.

### 2.1 Why not ADR-077 dogfight sealed-letter infra

Fundamentally 1v1-shaped, and rearchitecting it would cost more than the table engine gives
for free:
- **Role addressing is 2-element** — `ROLE_RED` / `ROLE_BLUE` hardcoded constants.
- **Interaction table is a 2D cross-product** — N crew is exponential and hand-authored:
  8 verbs × 4 crew = 8⁴ = **4 096 cells**. ADR-077 itself (line 313) declared the 2-actor
  assumption an "explicit scope boundary."
- **Arity hard-guarded to exactly one opponent** — `encounter_lifecycle.py:1152` raises
  `SealedLetterArityError` on `len(npcs_present) != 1`.
- **No shared-resource model** — each pilot's `frame_hp` is sealed into their own
  `per_actor_state`; there is no vessel/hull concept.

Worse, it solves the *wrong* problem: the dogfight cross-product models **opposed maneuver
geometry between two adversaries**, not **cooperative concurrent station verbs on a shared
hull**.

### 2.2 Why not `beat_selection`

`beat_selection` is a single-actor resolution mode: player rolls d20 vs a static DC, opponent
outcome is narrator-fiat. It has no notion of seats, no sealed concurrent-commit round, and no
shared resource. It is the wrong shape for "N concurrent committed verbs."

### 2.3 Why not a `seat` field on `EncounterActor`

The committee measured the blast radius: ~49 production call sites across 14 files, ~200 test
fixtures re-seeded, and it pollutes the generic participant roster with vessel-domain
concepts. `TableSeat` already *is* the seat primitive, scoped to exactly the encounters that
need it. Adding `seat` to `EncounterActor` is redundant work that degrades a clean abstraction.

## 3. What the table engine gives us for free

| War Rig requirement | Table-engine native? | Mechanism |
|---|---|---|
| N players, one shared object | ✅ | each `TableSeat` = a crew member |
| Concurrent per-seat verbs | ✅ | one `TableCommit` per seat per round |
| Sealed-commit simultaneous round | ✅ | commit phase → ordered resolution → showdown check |
| Station roles (driver/gunner/wrench/spotter/road-boss) | ✅ | `seat.private_state["station"]` |
| NPC seats auto-commit | ✅ | `npc_policy.decide_npc_commit()` |
| Bound per-ruleset (cwn) | ✅ | `RulesetModule.deal_table()` / `.resolve_table()` seams |
| Dispatched per turn | ✅ | `ResolutionMode.table_resolution` → `encounter_lifecycle.instantiate_table_encounter()` → `narration_apply` table branch |
| `table_showdown` win condition | ✅ | already a `WinCondition` variant |
| **Single-seat fighter == solo rig** | ✅ | a 1-seat table; the degenerate case falls out of the same loop (epic §4.3) |

## 4. The honest gaps to build

The reuse is real but not zero. Five genuine net-new pieces, all small and localized:

- **G1 — `war_rig_crew` table game.** A new kind registered via
  `register_table_game(...)`, with the cwn module's `deal_table`/`resolve_table` seeding crew
  stations and resolving station verbs (steer / shoot / repair / scan / command).
- **G2 — custom-beat dispatch seam (engine change).** Today `engine.py` hardcodes beat
  families (`_POT_ACTIONS`, `cheat`/`read`/`accuse`); an unknown beat hits a `ValueError`.
  Add a `custom_beat()` callback to the `TableGame` ABC so station verbs resolve through the
  kind, not the pot. **This is the one core-engine edit** — keep it minimal and
  backward-compatible (poker/auction unaffected).
- **G3 — shared Hull pool (vessel-scoped).** `RigComposurePool` **cannot** be the shared hull:
  `character_id` is required, immutable, and OTEL-attributed per character. Introduce a
  vessel-scoped hull pool that **reuses the `rig_pool.*` span vocabulary**
  (`delta` / `zero_crossing` / `crash_event`) keyed by `vessel_id` instead of `character_id`,
  stored on the table state for the `war_rig_crew` kind. Do **not** smuggle a crew-list into
  `character_id` — it breaks OTEL semantics. Fail loud on a blank vessel id.
- **G4 — crash cascade fan-out.** On Hull→0, fan 86-2's existing `resolve_crash_saves()` out
  to **each seated occupant** against their personal CWN ablative HP (the two-pool model from
  86-2, generalized from 1 occupant to N). Reuse, don't reimplement.
- **G5 — Command Points economy + Crisis table** (the SWN §4.3 crunch). CP is a per-vessel
  shared resource in the same shared-state dict; Do Your Duty / Above and Beyond / Support
  Department are commit modifiers. The d10 Crisis table is a resolution-phase branch in the
  `war_rig_crew` kind, reusing `rig_damage_tiers` / `rig_crash` content where it fits.

## 5. Recommended split (13 pts → 8 + 5)

13 pts exceeds the soft ceiling, and the gaps cleave on a natural seam: **wire the
architecture and prove it fires** (de-risking core) vs **layer the SWN command economy on
top**. Mirrors how this epic specified "Plan 1 in §6, rest scoped."

- **86-4a — War Rig table-game core (engine, ~8 pts).** G1 + G2 + G3 + G4. Register
  `war_rig_crew`; custom-beat seam; vessel-scoped Hull pool with `rig_pool.*` spans; crew
  verbs steer/shoot/repair/scan; Hull→0 crash cascade fanning crash saves to every seated
  occupant; the single-seat degenerate case covered in tests. **Mandatory OTEL wiring test**:
  a real road_warrior crewed turn through the production dispatch path fires `rig_pool.*` +
  `table.*` spans (the GM panel is the lie detector — epic §6.4 mandate). Independently
  shippable; proves the Guitar-Solo wider-action with mechanical backing.
- **86-4b — Command Points economy + Crisis table (~5 pts).** G5. CP shared resource + the
  three CP actions; d10 crisis table (continuing/acute, Deal With a Crisis). Asserts
  `command_points.*` / crisis spans fire.

## 6. Scope boundaries (do not regress 86-2)

- **Solo rig stays on 86-2's path.** 86-2 shipped solo-rig combat on the
  `RigComposurePool` / `rig_crash` two-pool path. 86-4 builds the **crewed** war_rig table
  game; the single-seat case is supported by the same engine **for completeness and testing
  only** — it does **not** replace 86-2's production solo path. Any unification of the two is
  a Plan 5 (86-5) calibration decision, logged as a deviation if attempted.
- **Minimal content in 86-4.** Ship a minimal playable `war_rig` confrontation def in
  road_warrior `rules.yaml` (`resolution_mode: table_resolution`, `table_game: war_rig_crew`,
  beats, station roles) sufficient to prove wiring. Full vessel stat blocks, mount_slots →
  CWN weapon remap, and lethality calibration belong to **86-5 (Plan 5)**.

## 7. Follow-up: ADR-129 amendment

ADR-129's stated scope is poker/auction (adversarial/free-for-all N-seat). This decision
extends the table engine to **cooperative crewed-vessel combat** (N seats acting *together* on
one shared object vs an external threat). Recommend a short ADR-129 amendment recording: the
`custom_beat` seam, the optional shared-resource/Hull-pool notion, and that
`table_resolution` now backs cooperative confrontations, not only competitive ones. (Artifact
for the Tech Writer / a follow-up; not blocking 86-4a.)

## 8. Key file references

| Concern | File |
|---|---|
| Table seats / state / commit | `sidequest-server/sidequest/game/table/types.py` |
| Round resolution loop (custom-beat seam goes here) | `sidequest-server/sidequest/game/table/engine.py` |
| Kind registry / `TableGame` ABC | `sidequest-server/sidequest/game/table/registry.py` |
| Ruleset seams (`deal_table`/`resolve_table`) | `sidequest-server/sidequest/game/ruleset/base.py:175,184` |
| `ResolutionMode.table_resolution` + validation | `sidequest-server/sidequest/genre/models/rules.py:329,502` |
| NPC auto-commit | `sidequest-server/sidequest/game/table/npc_policy.py` |
| Two-pool crash resolver (reuse for fan-out) | `sidequest-server/sidequest/game/rig_crash.py` |
| `rig_pool.*` span vocabulary (reuse for Hull) | `sidequest-server/sidequest/telemetry/spans/rig.py` |
| Per-turn table dispatch | `sidequest-server/sidequest/server/narration_apply.py` (table branch) |
| Table encounter instantiation | `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` (`instantiate_table_encounter`) |
