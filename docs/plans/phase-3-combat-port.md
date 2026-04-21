# ADR-082 Phase 3: Combat Port Decomposition

**Status:** Proposed
**Date:** 2026-04-20
**Author:** Naomi Nagata (Architect, design mode)
**Related:** `docs/adr/082-port-api-rust-to-python.md`, `docs/plans/phase-2-chargen-port.md`

## Context

Phase 2 of ADR-082 is merged. Chargen works end-to-end on the Python server; the `Culture.chargen` IOU is closed (Story 41-11); the only open Phase 2 gate is the live playtest that Keith still owes. Phase 3 was sketched in the execution-strategy spec (`docs/superpowers/specs/2026-04-19-python-port-execution-strategy-design.md`) as *"Combat. `combat_models`, `combatant`, `engagement`, `encounter` + combat OTEL."* That sketch was wrong in three ways and needs correcting before decomposition.

## Structural correction

The pre-recon sketch of this phase proposed porting four modules. Three of those names do not describe the work:

- **`combat_models.rs` does not exist** in `sidequest-api/crates/sidequest-game/src/`. The spec named a module that was never written.
- **`engagement.rs` (18 LOC) is not combat engagement.** It is a trope-engine pure function — `engagement_multiplier(turns_since_meaningful: u32) -> f32` — that scales trope tick rate by player activity. Part of Phase 2-or-later trope porting; no combat content.
- **Combat and chase are already unified in Rust under `StructuredEncounter` (ADR-033 / Story 16-2).** The old `CombatState` and `ChaseState` structs were deleted; everything — combat, chase, standoffs, negotiations — is a `StructuredEncounter` with a string-keyed `encounter_type` and a polymorphic `EncounterMetric`. The spec's "Phase 3 combat" and "Phase 4 chase" no longer map to distinct Rust modules. They map to *flavors* of one shared type. This is the most important structural correction: the 8-phase plan's assumption that chase is a separate subsystem needs updating before Phase 4 is decomposed too.

What is actually in scope for Phase 3, sorted by LOC, after recon:

| Module | LOC | Role |
|---|---|---|
| `encounter.rs` | 724 | `StructuredEncounter` + `EncounterMetric` + `SecondaryStats` + `EncounterActor` + `EncounterPhase` + constructors |
| `tension_tracker.rs` | 803 | dual-track pacing (action + stakes); produces `PacingHint` for narrator prompt injection |
| `resource_pool.rs` | 275 | ADR-033 resource pools + `ResourcePatch` + threshold-driven lore minting |
| `combatant.rs` | 152 | `Combatant` trait (already partially ported — `Character.is_broken/edge_fraction` exist in `sidequest-server/sidequest/game/character.py`) |
| dispatch touchpoints | ~300 LOC across `response.rs`, `tropes.rs`, `aside.rs`, `state_mutations.rs`, `telemetry.rs` | confrontation-def lookup, encounter resolution, combat-in-aside strip, XP-in-combat math, combat OTEL |

`chase_depth.rs` (896 LOC) stays in Phase 4 per the spec: it is cinematic chase — camera modes, terrain modifiers, danger levels — that *consumes* a `StructuredEncounter` but does not define it. Decomposing Phase 4 chase is a separate plan; a note in the Risks section below captures that Phase 3 must land the type shape Phase 4 will build on.

## What is already ported (do not re-port)

Phase 3 does not start from zero. Epic 39 landed in Rust ahead of the port, and fragments have been ported already:

- **`EdgePool`** — `sidequest-server/sidequest/game/creature_core.py:45`. Composure axis for combat / composure-driven scenes.
- **`Combatant` interface on `Character`** — `character.py:164` (`is_broken`), `character.py:168` (`edge_fraction`). Exposed as methods, not a formal trait; the port can either leave it implicit or introduce a `Protocol` in 3.1.
- **`GameSnapshot.encounter: dict | None`** — `session.py:340`. Declared as a pass-through dict with a `P3-deferred: StructuredEncounter (ADR-033 confrontation engine)` comment. Phase 3 promotes this to a typed model.

## Decomposition: four stories in a DAG

```
            ┌──→ 3.2 (resource_pool) ──┐
3.1 (types) ┤                          ├──→ 3.4 (dispatch + OTEL + narrator wiring)
            └──→ 3.3 (tension_tracker) ─┘
```

3.2 and 3.3 are independent of each other and can run in parallel once 3.1 lands. 3.4 depends on all three. No vertical slicing — partial combat cannot ship to production (a half-typed encounter dict is worse than the current full pass-through).

### Story 3.1 — StructuredEncounter types + Combatant protocol

**Scope:** Port `sidequest-game/src/encounter.rs` (724 LOC) and formalise the `Combatant` interface.

**Includes:**
- `StructuredEncounter` model (pydantic `BaseModel`) — `encounter_type`, `metric`, `beat`, `structured_phase`, `secondary_stats`, `actors`, `outcome`, `resolved`, `mood_override`, `narrator_hints`
- `EncounterMetric` + `MetricDirection` (`Ascending | Descending | Bidirectional`)
- `EncounterPhase` enum + `drama_weight()` method
- `StatValue` + `SecondaryStats` (string-keyed `dict[str, StatValue]`) + `damage_tier`
- `EncounterActor` with `per_actor_state: dict[str, Any]` for ADR-077 `SealedLetterLookup`
- Constructors: `StructuredEncounter.combat(combatants, hp)` and `StructuredEncounter.chase(escape_threshold, rig_type, goal)` — chase is included here because the type is unified, even though chase cinematography is Phase 4
- `resolve_from_trope(trope_id)` method (consumer: dispatch `tropes.rs`)
- `Combatant` `typing.Protocol` — `name`, `edge`, `max_edge`, `level`, `is_broken`, `edge_fraction`. Opt-in for NPC + future Enemy; Character already satisfies structurally.
- Replace `GameSnapshot.encounter: dict | None` with `StructuredEncounter | None` (breaking the Phase 1 IOU)

**Acceptance criteria:**
- Save-file compatibility: an existing `.db` with an encounter JSON in the Rust shape round-trips through the Python type with no field drift (`extra: ignore` on `GameSnapshot` allows unknown fields; `StructuredEncounter` itself uses `extra: forbid`)
- `StructuredEncounter.combat(...)` and `StructuredEncounter.chase(...)` produce JSON output byte-identical to `serde_json::to_string(&rust_equivalent)` on identical inputs (Rust-parity fixture test)
- `Combatant.edge_fraction(max_edge=0) == 0.0` — division-by-zero guard preserved
- `SecondaryStats.rig(rig_type)` produces the Rust-parity `hp/speed/armor` map shape (chase-flavor; needed for 3.1 even though chase cinematography is Phase 4)

**Test strategy:**
- Unit: model validation, constructor parity, `resolve_from_trope`, `edge_fraction` boundary
- Round-trip: load a canned Rust-produced encounter JSON, model-validate, re-serialise, compare
- **Wiring check:** `GameSnapshot.encounter` now annotated as `StructuredEncounter | None`; grep for `snapshot.encounter["` dict-access patterns that will break and list them as follow-ups for 3.4

**Phase 1 IOUs promoted:**
- `GameSnapshot.encounter` (`session.py:340`) — dict → typed

---

### Story 3.2 — Resource pools (ADR-033)

**Scope:** Port `sidequest-game/src/resource_pool.rs` (275 LOC).

**Includes:**
- `ResourceThreshold` (tier label + trigger point + lore beat template)
- `ResourcePool` (current/max, decay curve, thresholds, last-tier-crossed state)
- `ResourcePatchOp` enum (`Spend | Restore | SetMax | Invalidate`)
- `ResourcePatch` + `ResourcePatchResult` (applied delta + fired thresholds)
- `ResourcePatchError` (typed enum → exception subclasses)
- `mint_threshold_lore(thresholds, store, turn)` — threshold crossings mint `LoreEntry` into the session `LoreStore`. `LoreStore` is already ported (Slice F); this function is the consumer edge.

**Acceptance criteria:**
- Threshold crossings fire exactly once per crossing (not repeatedly while the pool hovers at the threshold)
- Patch application is atomic — a failed patch leaves the pool unchanged (no partial apply)
- `mint_threshold_lore` produces `LoreEntry` rows with the same `category`/`keywords`/`text` shape as the Rust version (fixture comparison)

**Test strategy:**
- Unit: patch-op semantics, threshold-crossing edge cases (exact-hit, overshoot, reversal)
- Integration: pool → lore-store round-trip with real `LoreStore`

**Phase 1 IOUs promoted:**
- `GameSnapshot.resources` is currently P4-deferred (`session.py:313`). Opinion: Phase 3 is the right moment to land it *as a typed list* — resource pools are orthogonal to encounter types (a pool can exist outside an encounter) and deferring the typed shape to Phase 4 creates another dict-pass-through cleanup round. **Recommend:** promote `resources` in 3.2, not Phase 4.

**Wiring check:** 3.2's non-test consumer is 3.4 (combat dispatch uses pool patches for HP/fuel/shields). 3.2 can land ahead of 3.4 only if 3.4 is queued immediately behind it.

---

### Story 3.3 — TensionTracker + PacingHint narrator injection

**Scope:** Port `sidequest-game/src/tension_tracker.rs` (803 LOC).

**Includes:**
- `RoundResult`, `DamageEvent` (per-turn combat digest)
- `PacingHint` + `DeliveryMode` + `DramaThresholds` (re-export from `sidequest-genre`)
- `CombatEvent` / `DetailedCombatEvent` enums + `classify_round(round, killed)` + `classify_combat_outcome(...)`
- `TurnClassification` enum
- `TensionTracker` state machine (action-tension + stakes-tension + history)
- Narrator-prompt section: currently Rust injects `PacingHint` text into the narrator's Early zone; Phase 3 wires the same into the Python orchestrator as a new `TurnContext.pacing_hint: str | None` field + Valley-zone `pacing_hint` section (or Early, TBD in implementation — match Rust)

**Acceptance criteria:**
- `TensionTracker.tick(round_result)` produces the same `PacingHint` as the Rust equivalent on identical fixture inputs (12+ cases covering all combinations of action/stakes tension)
- `classify_round` classifications match Rust verbatim on the full fixture suite
- `DramaThresholds` pulled from genre pack — not re-declared in Python (single source of truth)

**Test strategy:**
- Unit: classification tables (`classify_round`, `classify_combat_outcome`)
- Fixture: Rust `cargo run --bin tension_tracker_fixture_gen` output → Python fixture, assert parity
- Wiring test: orchestrator registers `pacing_hint` section only when `TurnContext.pacing_hint is not None`

**Phase 1 IOUs promoted:**
- None directly, but note that `DramaThresholds` from `sidequest-genre` must already be ported by 3.3 start. Confirm in Phase 2 audit.

---

### Story 3.4 — Combat dispatch + OTEL catalog + narrator wiring

**Scope:** Port the combat-sensitive dispatch touchpoints in `sidequest-api/crates/sidequest-server/src/` plus the combat OTEL span catalog.

**Includes:**
- `dispatch/state_mutations.rs:39` — XP-award differential by `ctx.in_combat()` (25 vs 10). Port the `in_combat()` helper on the Python dispatch context.
- `dispatch/response.rs` — `find_confrontation_def(defs, encounter_type)` + label/category resolution; confrontation payload assembly for `STATE_PATCH` / `ENCOUNTER_STATE` messages
- `dispatch/tropes.rs:179-181` — encounter resolution from trope beats (`encounter.resolve_from_trope(ts.trope_definition_id())`)
- `dispatch/aside.rs:7,46,95` — `strip_combat_brackets` helper + `in_combat` aside context + narrator pre-aside sanitisation
- `dispatch/telemetry.rs:92` — `in_combat: ctx.in_combat()` in watcher-event fields
- OTEL span catalog: `combat.*` span names from `sidequest-telemetry/src/lib.rs:89-266` — `watcher!("combat", StateTransition, ...)` events: `combat_tick`, `combat_ended`, `player_dead`, etc. Port to `sidequest-server/sidequest/telemetry/spans.py` preserving Rust names byte-for-byte (GM-panel contract; see Risks)
- Narrator wiring: `TurnContext.in_combat: bool` + `TurnContext.encounter_summary: str | None` + Valley-zone section that renders the encounter state for the narrator
- Resource-pool wiring: patch application → lore-store threshold mint
- `end_to_end` playtest script: drive a caverns_and_claudes combat through PLAYER_ACTION messages, assert encounter state progresses, resolves, and OTEL spans fire

**Acceptance criteria:**
- OTEL span names are byte-identical to Rust — `combat.tick`, `combat.ended`, `combat.player_dead`, `encounter.phase_transition`, `encounter.resolved`. GM-panel queries must not break.
- A full combat encounter (engage → tick → climax → resolve) completes end-to-end on the Python server with the same message-sequence shape the UI currently receives from Rust
- `ctx.in_combat()` returns `True` iff `snapshot.encounter is not None and not snapshot.encounter.resolved and snapshot.encounter.encounter_type in {"combat", "skirmish", ...}` (exact set mirrors Rust)
- Confrontation-def lookup: an encounter with `encounter_type = "duel"` resolves against the pack's `confrontation_defs` list and produces the correct label + category
- Keith plays through one combat scene on the Python server end-to-end before this story closes

**Test strategy:**
- Unit: `in_combat()` helper, `find_confrontation_def` variants, `strip_combat_brackets` parity
- Integration: protocol-level combat walkthrough test (PLAYER_ACTION → orchestrator → encounter update → STATE_PATCH → broadcast)
- OTEL: span-catalog parity test (every `combat.*` name from Rust appears in Python span registry)
- **No live LLM calls.** Mock the narrator; combat dispatch is mechanical, not narrative

**Phase 1/2 IOUs promoted:**
- `GameSnapshot.encounter` — transitions from typed-but-not-wired (3.1) to actively-dispatched (3.4)

**Wiring check:** 3.4 closes the loop. After 3.4 merges, `ctx.in_combat()` has real consumers (XP math, aside context, telemetry, narrator prompt). No dead code.

---

## Risks and watch-outs

**Phase 4 chase decomposition is coupled to 3.1.** `StructuredEncounter.chase(...)` constructor + `SecondaryStats.rig(...)` ship in 3.1 because the type is unified. Phase 4 (`chase_depth.rs` — 896 LOC) layers camera modes, terrain, and cinematography *on top of* the already-typed encounter. If 3.1 misses a chase-flavor field (e.g., the per-actor `per_actor_state` for `SealedLetterLookup`), Phase 4 will be blocked until the type is amended. Recon the chase-specific fields before 3.1 closes, not after.

**OTEL span names are an external contract.** `combat.tick`, `combat.ended`, `combat.player_dead`, and the encounter-phase transitions are read by the GM panel (Sebastien's mechanical visibility). Name drift between Rust and Python silently breaks the lie-detector. The Phase 2 chargen port enforced span-name parity via a test that reads Rust source; repeat that test for `combat.*` in 3.4.

**The Rust `Combatant` trait vs Python `Protocol`.** Rust's trait is explicit; Python's structural typing is implicit. A class that *happens to have* `is_broken` and `edge_fraction` will satisfy the protocol, which is good for ducks but bad for discoverability. Ship the `Protocol` + an explicit `@runtime_checkable` decorator so `isinstance(x, Combatant)` works where it is useful. A wiring test should assert `isinstance(character, Combatant) and isinstance(npc, Combatant)`.

**`TensionTracker` fixture suite is expensive to generate.** The classification tables are large (12+ variants × 5+ states). Recommend generating the fixtures from Rust once via a `cargo run --example tension_fixture_export` and committing the JSON in the Python test suite. Do not hand-transcribe — drift will happen.

**Epic 39 edge/composure is Rust-ahead.** Rust has production edge-pool code that exceeds what's on Python. Phase 3 ports the *types* and the *combat-adjacent* accessors (`is_broken`, `edge_fraction`), but advancement-time edge math (Epic 39 territory) is Phase 6. If Phase 3 accidentally depends on Phase 6 math, the port blocks. Verify the encounter tick does not call advancement-level edge functions before 3.1 closes.

**Save-file compatibility is load-bearing.** `GameSnapshot.encounter` is currently `dict | None` and accepts any shape Rust produces. Promoting to typed means saves with unknown encounter types fail model validation. Two options: (a) add `extra: ignore` on `StructuredEncounter`, accept forward-compat; (b) fail loud on unknown `encounter_type` values (per CLAUDE.md "No Silent Fallbacks"). **Recommend (b)** — an unknown encounter_type is a genre-pack typo and silent-forgiving turns it into a debugging black hole.

**Resource pools vs encounter secondary_stats.** Both track HP-like quantities. `SecondaryStats.stats["hp"]` is on `StructuredEncounter`; `ResourcePool.current` is on a standalone pool. They are NOT aliases — the former is encounter-scoped (lives with the encounter, dies on resolution), the latter is session-persistent (survives encounter end). Clarity in the port: name them distinctly, document the scope, resist "unifying" them.

## Total estimate

- 3.1: 3–4 days (724 LOC + round-trip tests + Combatant Protocol + GameSnapshot.encounter promotion)
- 3.2: 2 days (275 LOC + lore-store wiring)
- 3.3: 4–5 days (803 LOC + fixture-parity suite + narrator prompt wiring)
- 3.4: 4–6 days (dispatch touchpoints + OTEL catalog + end-to-end integration + playtest gate)

Range: **13–17 days of Dev time** for Phase 3 complete. 3.2 and 3.3 can run in parallel after 3.1, collapsing calendar time by up to 4 days if two devs are available. Serial estimate without parallelism: ~15 days.

Add TEA + Reviewer rounds per story. 3.4 carries a human-playtest acceptance gate (Keith completes one combat scene on Python) that is not automatable.

## Appendix A: Phase 1/2 pass-through audit — which IOUs come due

**Promoted to typed in Phase 3:**

| Field | Location | Promoted in | How |
|---|---|---|---|
| `GameSnapshot.encounter` | `session.py:340` | Story 3.1 | `dict \| None` → `StructuredEncounter \| None`; update all `snapshot.encounter["k"]` consumers |
| `GameSnapshot.resources` | `session.py:313` (P4-deferred) | Story 3.2 (recommend) | `list` → `list[ResourcePool]`; pulling forward from Phase 4 to avoid a second cleanup pass |

**Stays pass-through into Phase 4+:**

- `campaign_maturity` / `world_history` (`session.py:306`) — Phase 3 does not touch world materialization beyond what Story 2.3 Slice F seeded
- `discovered_rooms` (`session.py:312`) — room-graph navigation, not encounter-adjacent
- `genie_wishes` (`session.py:307`) — consequence engine, Phase 5 scenario work
- `axis_values` (`session.py:308`) — tone system, standalone port
- `achievement_tracker` (`session.py:309`) — Phase 6 material
- `Npc` deferred fields (OCEAN, BeliefState, ResolutionTier, `session.py:74`) — P5 scenario system; combat touches NPCs via the `Combatant` protocol, not via OCEAN state

## Appendix B: What Phase 3 does NOT include

Explicit non-goals so scope does not creep:

- **Chase cinematography** (`chase_depth.rs`, 896 LOC) — Phase 4
- **Scenario engine** (belief_state, gossip, clue_activation, accusation, faction_agenda) — Phase 5
- **Advancement trees / affinity tiers** — Phase 6 (Epic 39 Rust material)
- **CLIs** (encountergen, loadoutgen, namegen, promptpreview, validate) — Phase 7
- **Sealed-letter turn flow** — ADR-077 land already; the Python port honours `per_actor_state` shape in 3.1 but does not port the lookup dispatcher
- **Narrator combat narration polish** — prompt tuning is narrator work, not port work; any prompt drift discovered during 3.4 integration is logged as a Phase 3-adjacent sprint item, not scope creep into this phase

## Recommendation

Start with 3.1 (types) as a single focused story. It unblocks both 3.2 and 3.3, surfaces the Rust-Python type drift early, and lands the most visible Phase 1 IOU (`GameSnapshot.encounter`). After 3.1 merges, queue 3.2 and 3.3 in parallel; 3.4 lands last and carries the playtest gate.
