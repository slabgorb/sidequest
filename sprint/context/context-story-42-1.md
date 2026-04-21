---
parent: context-epic-42.md
workflow: tdd
---

# Story 42-1: StructuredEncounter types + Combatant protocol

## Business Context

Every subsequent Phase 3 story (42-2, 42-3, 42-4) consumes `StructuredEncounter`. Without this story, the combat subsystem has no type to exchange — combat dispatch cannot ship, the narrator prompt cannot render an encounter summary, and `GameSnapshot.encounter` stays decorative. This is the foundation the rest of Epic 42 builds on.

Business value is load-bearing on the playgroup: Sebastien's mechanical-visibility feature (the GM panel) reads encounter state via OTEL spans, and those span payloads carry `encounter_type`, `metric`, `phase` fields that only exist as typed data if the model is ported. Decorative dict pass-through blocks that visibility.

## Technical Guardrails

**Port scope:**
- `sidequest-api/crates/sidequest-game/src/encounter.rs` (724 LOC)
- `sidequest-api/crates/sidequest-game/src/combatant.rs` (152 LOC) — interface side only (trait → `typing.Protocol`)

**Target files (new):**
- `sidequest/game/encounter.py` — `StructuredEncounter`, `EncounterMetric`, `SecondaryStats`, `StatValue`, `EncounterActor`, `EncounterPhase`, `MetricDirection`
- `sidequest/game/combatant.py` — `Combatant` protocol (`@runtime_checkable`)

**Target files (modified):**
- `sidequest/game/session.py:340` — `encounter: dict | None` → `encounter: StructuredEncounter | None`
- `sidequest/game/__init__.py` — export new types
- `sidequest/game/character.py` — (no code change needed; already satisfies `Combatant` structurally — add a single `isinstance(char, Combatant)` assertion somewhere to prove wiring)

**Translation key** (per execution-strategy spec §2):
- `struct` + `#[derive(Serialize, Deserialize)]` → `class(BaseModel)` with pydantic v2
- `HashMap<K, V>` → `dict[K, V]`
- `Option<T>` → `T | None`
- `#[non_exhaustive] enum` → pydantic `StrEnum` subclass with documented stability note
- `impl` methods → model methods (keep names verbatim)

**Patterns to follow:**
- Rust tests port 1:1 — every `#[test]` becomes one pytest function with the same name. No idiomatic rewrites during the port.
- `SecondaryStats.rig(rig_type)` ships in this story even though chase cinematography is deferred — the constructor is part of the type; only the *camera modes / terrain modifiers* are Phase 4 material.
- `EncounterActor.per_actor_state: dict[str, Any]` — preserve shape exactly; ADR-077 sealed-letter dispatcher (future work) reads this field, any drift breaks it silently.

**What NOT to touch:**
- `chase_depth.rs` (896 LOC) — Phase 4, skipped
- `dispatch/*` files — Phase 42-4 scope
- `tension_tracker.rs` — 42-3 scope
- `resource_pool.rs` — 42-2 scope
- `narrator.py` prompt sections — 42-4 scope

## Scope Boundaries

**In scope:**
- `StructuredEncounter` pydantic model (all 10 fields per Rust struct)
- `EncounterMetric` + `MetricDirection` (`Ascending | Descending | Bidirectional`)
- `EncounterPhase` enum + `drama_weight()` method (values verbatim from Rust: `Setup 0.70`, `Opening 0.75`, `Escalation 0.80`, `Climax 0.95`, `Resolution 0.70`)
- `StatValue { current: int, max: int }`
- `SecondaryStats { stats: dict[str, StatValue], damage_tier: str | None }` + `.rig(rig_type)` constructor + `.from_rig_stats(...)` helper
- `EncounterActor { name, role, per_actor_state }`
- Constructors: `StructuredEncounter.combat(combatants, hp)` and `StructuredEncounter.chase(escape_threshold, rig_type, goal)`
- `.resolve_from_trope(trope_id)` method — consumer lands in 42-4 dispatch, but the method is authored here
- `Combatant` `typing.Protocol` with `name`, `edge`, `max_edge`, `level`, `is_broken`, `edge_fraction`
- `GameSnapshot.encounter` type promotion
- Round-trip JSON parity test against a canned Rust-produced fixture

**Out of scope:**
- Encounter tick loop / metric delta application (42-4 dispatch)
- Resource pool integration (42-2)
- Tension tracker / pacing hint (42-3)
- OTEL spans (42-4)
- Narrator prompt `encounter_summary` section (42-4)
- Chase cinematography (Phase 4 — skipped)
- Any change to Rust source

## AC Context

**AC1: `StructuredEncounter` round-trips with Rust-parity JSON.**
A JSON blob produced by `serde_json::to_string(&structured_encounter)` on the Rust side must model-validate in Python and re-serialise to the same blob (field-order tolerant; use pydantic's canonical dump). Fixture test: at least one combat-flavor and one chase-flavor encounter, each exercising `secondary_stats` and `per_actor_state`.
*Edge case:* chase encounter with `secondary_stats = None` (minimal chase construction). Must round-trip cleanly.

**AC2: Constructors produce Rust-parity output.**
`StructuredEncounter.combat(["Alice", "Bob"], hp=30)` and `StructuredEncounter.chase(escape_threshold=0.5, rig_type="motorcycle", goal=10)` each produce models byte-identical (when JSON-dumped) to the Rust equivalents called with the same arguments.
*Test verifies:* a Rust `cargo run --example encounter_fixture` output committed to `tests/fixtures/encounters/` is consumed and asserted.

**AC3: `Combatant` protocol accepts `Character` structurally.**
`isinstance(character, Combatant)` returns `True` for any `Character` instance. `npc` instances also satisfy it if `Npc` exposes `edge`/`max_edge`/`is_broken`/`edge_fraction` (currently implicit via `CreatureCore` composition — confirm during port; may require one-line `Combatant` accessor on `Npc`).
*Edge case:* `edge_fraction(max_edge=0)` returns `0.0`, not `ZeroDivisionError`. Port Rust's guard verbatim.

**AC4: `GameSnapshot.encounter` is typed.**
Type annotation changes from `dict | None` to `StructuredEncounter | None`. All tests in `tests/game/test_session*.py` that build a `GameSnapshot` with an encounter value continue to pass. Any dict-access patterns (`snapshot.encounter["key"]`) that exist in the codebase are listed in the Dev Assessment as follow-ups for 42-4 (not fixed in 42-1 — those consumers belong to dispatch scope).

**AC5: Unknown `encounter_type` fails loud on load.**
A save file with `encounter: {"encounter_type": "flibbertigibbet", ...}` raises a `ValidationError` on `GameSnapshot` load. No silent fallback, no default-to-"combat" coercion. Per CLAUDE.md "No Silent Fallbacks." Test: write a fixture with a bogus encounter_type, load it, assert the exception.

**AC6: Existing Phase 1/2 tests continue to pass.**
The `extra: ignore` on `GameSnapshot` must stay — forward-compat with Rust-produced saves that have unknown top-level fields. Do not tighten to `extra: forbid` on `GameSnapshot` as part of this story (that's a bigger cleanup, not Phase 3 scope).

## Assumptions

- **Rust fixture generation is trivially scriptable.** A `cargo run --example encounter_json_export` that prints canonical fixtures to stdout is small and low-risk. If that assumption proves wrong (e.g., the Rust side has no fixture infrastructure), fall back to hand-authored fixtures and log a Design Deviation.
- **`Npc` satisfies `Combatant` with at most one-line glue.** Python `Npc` composes `CreatureCore` which should already expose the edge accessors. If `Npc` needs significant refactoring to satisfy the protocol, that's a scope increase — log deviation and queue a follow-up, do not expand 42-1.
- **No existing `snapshot.encounter["x"]` dict-access consumers exist in Phase 2 Python code.** Quick grep during story setup: `grep -rn 'snapshot.encounter\[' sidequest-server/sidequest/`. If the list is non-empty, extend 42-1 scope to fix those, or log them as 42-4 follow-ups depending on count.
- **`chase_rig_type` string values are stable across Rust and Python.** RigType enum values (e.g., `"motorcycle"`, `"sedan"`, `"semi"`) are string-serialised; `SecondaryStats.rig()` accepts the string and does not need a Python-side enum unless the Rust side has one that exports via serde. Verify during port.
