# ADR-082 Phase 2: Chargen Port Decomposition

**Status:** Proposed
**Date:** 2026-04-20
**Author:** Naomi Nagata (Architect, design mode)
**Related:** `docs/adr/082-port-api-rust-to-python.md`

## Context

Phase 1 of ADR-082 is merged. All 6 genre packs load cleanly through the Python port; WebSocket handshake + session creation works end-to-end across every genre+world combo. The UI advances to `sessionPhase === "creation"` and then renders blank — because the character-creation conversation is not yet ported.

Phase 2 ports chargen. This document decomposes that work.

## Structural correction

A pre-recon sketch of this phase proposed four sub-stories including "port Claude subprocess orchestration for chargen." That sketch was wrong. **Chargen has zero Claude involvement.** It is a pure mechanical state machine driven by genre-pack `character_creation_scenes`. The narrator agent (already ported in Phase 1) does not fire until the first Playing-state turn — *after* chargen completes.

Correct shape:

- **State machine:** `BuilderPhase { InProgress | AwaitingFollowup | Confirmation }` driven by scene index.
- **Protocol surface:** a single message type, `CHARACTER_CREATION`, discriminated by a `phase` field (`scene` | `continue` | `confirmation` | `complete`).
- **Claude integration:** none. Builder accumulates `MechanicalEffects` hints across scenes, then renders a plain-text summary at `confirmation`. Claude first appears on opening narration, after Playing transition.
- **Persistence seam:** single commit point at end of `dispatch_character_creation` confirmation handler — `builder.build()` → equipment wiring → world materialization → SQLite save → `session.complete_character_creation()`.

## Decomposition: three stories in a strict DAG

No vertical slicing is possible — partial chargen cannot ship to production. But the horizontal cuts are clean and the dependencies form a DAG with no cycles.

```
2.1 (builder) → 2.2 (dispatch) → 2.3 (persistence + opening)
```

### Story 2.1 — CharacterBuilder state machine

**Scope:** Port `sidequest-api/crates/sidequest-game/src/builder.rs` (~900 LOC) and supporting types.

**Includes:**
- `CharacterBuilder` struct + `BuilderPhase` enum
- `SceneResult`, `AccumulatedChoices`
- Scene-walking operations: `apply_choice`, `apply_freeform`, `apply_auto_advance`, `go_back`, `go_to_scene`
- Stat generators: `roll_3d6_strict`, `point_buy`, and whatever other strategies the Rust source supports (recon didn't enumerate them; Dev to confirm during port)
- HP formula evaluator (supports `hp_formula` override on RulesConfig)
- `EdgeConfig` resolution (story 39-3 territory)
- `build(name)` finalizer → produces `Character`

**Acceptance criteria:**
- Builder can walk every scene flow in every pack's `rules.yaml.character_creation_scenes` without error
- Stat rolls are deterministic under test (seedable RNG)
- `MechanicalEffects` accumulation is correctly replayed after `go_back` (no stale hints from reverted scenes)
- `build(name)` produces a `Character` with stats, abilities, pronouns, and accumulated hints

**Test strategy:**
- Pure unit tests — no WebSocket, no protocol, no dispatch. Feed the builder synthetic `CharCreationScene[]`, drive it with canned choices, assert on the output.
- At least one integration test per pack that walks a real scene flow to completion.

**Pass-through fields that become load-bearing here:**
Phase 1 accepted `MechanicalEffects.reputation_bonus` as pass-through. Phase 2.1 needs to **either** wire it into builder hints **or** remove it from the content and the model. Don't leave it as decoration — the IOU comes due.

**Wiring check:** Builder must have a non-test consumer by the end of 2.2 (dispatch calls it). 2.1 can land first with `TODO: wired by 2.2` only if 2.2 is queued immediately behind it. No orphan code.

---

### Story 2.2 — dispatch_character_creation + protocol

**Scope:** Port the handler at `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs:1394–2350` (~950 LOC) plus the confirmation rendering helper `chargen_summary.rs` (~266 LOC).

**Includes:**
- `CHARACTER_CREATION` message type on the Python side (should extend `sidequest.protocol.messages` — the existing protocol port)
- Dispatch branches:
  - `phase: "scene"` + `choice: "<numeric index>" | "<label>"` (case-insensitive label matching)
  - `phase: "scene"` + `choice: "<freeform text>"` when `allows_freeform: true`
  - `phase: "continue"` (display-only scene acknowledged)
  - `phase: "confirmation"` (player commits)
  - `action: "back"` (navigate to prior scene)
  - `action: "edit"` + `target_step: N` (jump from review to scene N)
- Error paths: invalid choice index, choice label miss, freeform when not allowed, can't go back from first scene, edit target out of range
- Confirmation summary rendering: name resolution, equipment resolution from `InventoryConfig.starting_equipment`, pronoun/stat/mutation rollup
- OTEL spans: `character_creation` state-transition events (phase, action, name_resolved, character_built); `archetype_resolution` with provenance tier

**Acceptance criteria:**
- UI can walk a full chargen flow end-to-end for at least two packs (one simple, one with freeform hooks — pulp_noir and caverns_and_claudes good candidates)
- Invalid inputs produce structured error messages, never exceptions through the WebSocket
- `go_back` through a scene with side-effects correctly reverts accumulated state (regression test: pick a class, go back, pick a different class, ensure first class's hints are gone)
- OTEL spans match the Rust telemetry names so existing GM-panel queries continue to work

**Test strategy:**
- Protocol-level integration tests: send `CHARACTER_CREATION` frames, assert on server responses.
- Mock the builder (already isolated and tested in 2.1) where useful, but also have at least one end-to-end test with real builder + real genre pack.
- **No live LLM calls.** There are no LLM calls in chargen, so this is automatic — but explicitly fail the PR if a test depends on `claude -p`.

**Pass-through fields that become load-bearing here:**
- `InventoryConfig.starting_equipment`, `InventoryConfig.starting_gold` — if these were pass-through in Phase 1, tighten the models now.
- `RulesConfig.character_creation_scenes` — tighten the model to structured scenes, not dict pass-through.
- `Culture.chargen` — if the Rust chargen consumes it (recon said it's in the pass-through list; confirm during port), wire it; else delete.

---

### Story 2.3 — Persistence, world seeding, opening turn bootstrap

**Scope:** Port the confirmation-handler tail at `connect.rs:1892–2350` — everything after `builder.build()`.

**Includes:**
- World materialization from genre pack history (`lines 1892–2072`)
- Room-graph initialization (`lines 2026–2069`)
- Scenario binding (`lines 1948–2023`) — strongly coupled to chargen, ported alongside world materialization
- Character → SQLite save pipeline (`line 2174+`)
- NPC registry reset (`line 2136`, ~5 LOC but critical for session hygiene — fresh character, no prior NPC baggage)
- Lore seeding from chargen (`seed_lore_from_char_creation`, `line 2199`) — extracts `NarrativeHook` and `LoreAnchor` from builder scenes to populate `LoreStore` for prompt injection
- Opening turn bootstrap (`lines 2260–2350`): `opening_seed` + `opening_directive` injection into first narrator prompt; initial `PARTY_STATUS` message to UI
- Transition: `session.complete_character_creation()` → Playing state → first narrator turn fires

**Acceptance criteria:**
- After confirmation, a character save appears in `~/.sidequest/saves/<genre>_<world>.db` with the correct stats/equipment/location
- Reconnect with the same `player_name` lands directly in Playing state (skips chargen)
- First narrator turn fires with the correct `opening_directive` from the pack
- NPC registry starts empty for a fresh character
- Lore store is seeded with the character's narrative hooks before narration begins

**Test strategy:**
- Integration test: drive full chargen via protocol, assert save file shape in SQLite, reconnect, assert Playing state on second connect.
- Unit test world materialization in isolation — feed it canned pack history, assert world snapshot shape.
- Mock the narrator at the opening-turn boundary (narrator correctness is not this story's burden — the port of that happened in Phase 1).

**Wiring check:** Story 2.3 is the story that makes chargen *actually work for players*. Its acceptance criteria must include at least one end-to-end human playtest (Keith clicks through chargen for one pack and reaches the opening narration) before the story closes. Code can pass all automated tests and still be broken at the integration seam — the e2e path must be verified by hand.

---

## Risks and watch-outs

**Deferred pass-through fields in Phase 1.** Phase 1 accepted a large surface of pass-through fields to unblock loading. Phase 2 is the first moment several of those become load-bearing. For each, 2.1 or 2.2 must choose: wire it, or delete it from YAML + model. Leaving them as permanent decoration violates SOUL.md ("Strictness surfaces drift") and accumulates tech debt that Phase 3 will pay for.

**Mid-chargen disconnect is not gracefully resumable.** The Rust source doesn't persist builder state across disconnect — player restarts chargen from scene 1 on reconnect. This is an acceptable MVP simplification (chargen is ~5 min, not 3 hours) and the port should preserve it. If a future story wants mid-chargen resume, it's additive, not retro.

**OTEL span names are an external contract.** The GM panel queries spans by name. If the port renames them (Rust snake_case → Python… also snake_case, but naming drift is easy), Sebastien's mechanical visibility breaks. Span name parity must be in the 2.2 acceptance criteria, not an afterthought.

**Protocol changes bleed to the UI.** `CHARACTER_CREATION` already flows from the UI into the Rust server; the Python port must accept the same payload shape. If the ports diverge (even by field naming), the UI breaks silently. Verify payload parity against the Rust handler line-by-line during 2.2; don't trust "it worked before."

## Total estimate

- 2.1: 3–4 days
- 2.2: 2–3 days
- 2.3: 3–4 days (world materialization + scenario binding + persistence + opening turn)

Range: **8–11 days of Dev time** for Phase 2 complete. Add TEA + Reviewer rounds per story. No parallelism — the DAG is strict. Phase 2 is sequential work.

## Appendix: Phase 1 pass-through audit — which IOUs come due

Phase 1 accepted a large pass-through surface under `extra: forbid`-softened models. Audit against chargen consumption:

**Already structured — NOT pass-through (load-bearing for Phase 2, already typed):**

- `CharCreationScene`, `CharCreationChoice`, `MechanicalEffects` — chargen domain types, strict models, no compat shims
- `RulesConfig`: `stat_generation`, `point_buy_budget`, `ability_score_names`, `class_hp_bases`, `edge_config`, `default_class/race/location`, `hp_formula`, `race_label`, `class_label` — all typed
- `InventoryConfig.starting_equipment`, `InventoryConfig.starting_gold`, `InventoryConfig.item_catalog` — typed `dict[str, list[str]]` and `dict[str, int]`
- `OpeningHook` — typed at pack + world level
- Both pack and world `char_creation: list[CharCreationScene]` — typed entrypoint

**Wire during Phase 2 (IOUs come due):**

| Field | Location | Wire in | How |
|---|---|---|---|
| `MechanicalEffects.reputation_bonus` | `character.py:66` | Story 2.1 | Accumulate into builder state alongside other hints; no model change needed, just consumption |
| `Culture.chargen` | `culture.py:52` | Story 2.2 | Dispatch filters offered cultures by `.chargen` flag; lore-only cultures must not appear in chargen selection |

**Stays pass-through (Phase 3+, not chargen-load-bearing):**

- `RulesConfig.{standoff_rules, reputation_factions, reputation_effects, luck_rules}` — spaghetti_western post-chargen gameplay systems
- `ProgressionConfig.synergies`, `Affinity.sub_paths` — elemental_harmony emergent effects (advancement-time, not chargen-time)
- `Legend.{id, culture, period, details, notable_figures, related_tropes}` — narrator context (narrator wiring, not chargen)
- `TropeEscalation.roles` — multiplayer role targeting
- `Prompts.{ritual, debt_collection, session_opener_template}`, `BeatVocabulary.{event_flavor, decision_framings, chase_modes}` — narrator prompt flavor
- `CurrencyConfig.{abbreviation, description, secondary}`, `InventoryPhilosophy.notes` — authored flavor, zero-consumer
- `ItemEvolution`, `WealthTier.description`, `LevelBonuses` dict-form, `AffinityUnlocks` tier-name flexibility — compat shims for cross-pack shape drift; harmless, stay

Phase 2 adds **zero new pass-throughs**. By the end of 2.2, two existing pass-throughs are promoted to consumed. The remainder are chargen-irrelevant and belong to subsystem-scoped wiring stories (combat wiring, narrator wiring, progression wiring) — each its own epic, sequenced by Keith.
