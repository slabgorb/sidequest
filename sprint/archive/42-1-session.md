---
story_id: "42-1"
jira_key: null
epic: "42"
workflow: "tdd"
---
# Story 42-1: Port StructuredEncounter + EncounterMetric + SecondaryStats + EncounterActor + EncounterPhase types; formalise Combatant as a Python Protocol; promote GameSnapshot.encounter from dict to typed

## Story Details
- **ID:** 42-1
- **Jira Key:** null (auto-create if needed by workflow)
- **Epic:** 42 (ADR-082 Phase 3 — Port confrontation engine to Python)
- **Workflow:** tdd
- **Stack Parent:** none (no dependencies)
- **Points:** 5
- **Priority:** p0

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-04-24T11:05:14Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-24T07:10:00Z | 2026-04-24T11:05:14Z | 3h 55m |
| red | 2026-04-24T11:05:14Z | - | - |

## Story Context

This story is the foundation for Phase 3 of the ADR-082 Python port. It ports the unified `StructuredEncounter` model from the Rust backend, enabling all downstream Phase 3 stories (resource pools, tension tracking, combat dispatch) to have a typed contract for encounter data.

**Load-bearing fact:** Sebastien's mechanical-visibility feature (GM panel) reads encounter state via OTEL spans that carry `encounter_type`, `metric`, `phase` fields. These fields only exist as typed data if the model is ported — without 42-1, decorative dict pass-through blocks that visibility.

### Context Files
- `/Users/slabgorb/Projects/oq-2/sprint/context/context-story-42-1.md` — full technical scope, ACs, and assumptions
- `/Users/slabgorb/Projects/oq-2/sprint/context/context-epic-42.md` — epic overview, phase decomposition, cross-dependencies

### Technical Scope

**Port from Rust:**
- `sidequest-api/crates/sidequest-game/src/encounter.rs` (724 LOC) → `sidequest/game/encounter.py` (new)
- `sidequest-api/crates/sidequest-game/src/combatant.rs` (152 LOC) → `sidequest/game/combatant.py` (new, `typing.Protocol`)

**Modify:**
- `sidequest/game/session.py:340` — promote `encounter: dict | None` → `encounter: StructuredEncounter | None`
- `sidequest/game/__init__.py` — export new types
- `sidequest/game/character.py` — add `isinstance(char, Combatant)` assertion to prove wiring

**Translation patterns:**
- `struct` + `#[derive(Serialize, Deserialize)]` → `class(BaseModel)` (pydantic v2)
- `HashMap<K, V>` → `dict[K, V]`
- `Option<T>` → `T | None`
- `#[non_exhaustive] enum` → `StrEnum` with stability note
- Test porting: 1:1 Rust test name mapping to pytest functions, no idiomatic rewrites during port

### Key Types
- `StructuredEncounter` (10 fields, polymorphic by `encounter_type`)
- `EncounterMetric` + `MetricDirection` (`Ascending | Descending | Bidirectional`)
- `EncounterPhase` enum with `drama_weight()` method (Setup 0.70, Opening 0.75, Escalation 0.80, Climax 0.95, Resolution 0.70)
- `StatValue { current: int, max: int }`
- `SecondaryStats` + `.rig(rig_type)` constructor for chase encounters
- `EncounterActor` with `per_actor_state: dict[str, Any]` (ADR-077 sealed-letter dispatcher depends on shape)
- `Combatant` protocol with `name`, `edge`, `max_edge`, `level`, `is_broken`, `edge_fraction`

### Key Test Gates (ACs)
1. **Round-trip JSON parity:** Rust-produced JSON fixtures (combat + chase flavors) load and re-serialize identically
2. **Constructor parity:** `StructuredEncounter.combat()` and `StructuredEncounter.chase()` produce byte-identical JSON output to Rust equivalents
3. **Combatant protocol:** `isinstance(character, Combatant)` returns `True` for `Character` and `Npc` instances
4. **GameSnapshot.encounter is typed:** Type annotation flips to `StructuredEncounter | None`; all existing tests continue to pass
5. **Unknown encounter_type fails loud:** Save file with bogus `encounter_type` raises `ValidationError` on load
6. **Extra fields ignored on GameSnapshot:** Preserve forward-compat with Rust-produced saves (keep `extra: ignore`)

## Sm Assessment

- **Story selection:** P0, first actionable in Epic 42 Phase 3. Sibling 42-3 already done; 42-2 in review-approved-but-backlog state (not my story to resolve). 42-1 has no `depends_on` → no stack gate.
- **Scope:** Port `encounter.rs` (724 LOC) and `combatant.rs` (152 LOC) from archived Rust repo to `sidequest-server`. Promote `GameSnapshot.encounter` from dict to typed. Six ACs already enumerated in context.
- **Workflow:** tdd (per YAML). Phased. Next phase is `red` owned by TEA.
- **Repo scope:** `sidequest-server` only. No UI/daemon/content changes.
- **Context artifacts:** epic-42 context and story-42-1 context both exist (pre-written). TEA should ingest both before authoring tests.
- **Risk notes for TEA:** (a) Rust source is at https://github.com/slabgorb/sidequest-api (read-only reference per ADR-082) — fixtures will need to be generated from that tree or from frozen Rust-produced JSON already committed. (b) AC1 requires round-trip byte-identical JSON — pydantic field ordering and `StrEnum` serialization must match Rust's serde output. (c) AC6 needs `extra: ignore` to be *preserved* on `GameSnapshot`, not added to the new types — don't cargo-cult it everywhere.
- **Jira:** YAML has `jira_key: null`. Not blocking. Workflow may auto-create.

## Delivery Findings

### TEA (test design)
- **Gap** (blocking): Story 42-1 is code-complete and PR-merged (sidequest-server commit `ada5476`, PR #17, 2026-04-20), but `sprint/epic-42.yaml` still marks it `status: backlog` with no `completed` date or `review_verdict`. Affects `sprint/epic-42.yaml` (flip 42-1 status to `done`, record completion date, run `pf sprint story finish 42-1`). 59 existing tests in `sidequest-server/tests/game/test_encounter.py` + `test_combatant.py` all pass — no RED state available, no duplicate tests authored. *Found by TEA during test design.*
- **Gap** (blocking): Story 42-2 is in the same drift state — PR #18 merged (sidequest-server commit `a4a5010`), 44 tests passing in `tests/game/test_resource_pool.py`, YAML has `review_verdict: approved` but `status: backlog` and no `completed` date. Affects `sprint/epic-42.yaml` (flip 42-2 status to `done`, record completion date, run `pf sprint story finish 42-2`). User approved option-2 bundled finish for 42-1 + 42-2. *Found by TEA during test design.*

## Design Deviations

### TEA (test design)
- **No RED phase executed — story already GREEN on main**
  - Spec source: tdd.yaml workflow, red phase
  - Spec text: "Write failing tests covering each AC"
  - Implementation: Phase skipped; 59 tests authored and merged in PR #17 (commit `ada5476`) on 2026-04-20 before this session opened. All tests pass on current HEAD.
  - Rationale: Writing duplicate tests would falsify commit history. Code and tests already landed; only tracker-state remains out of sync. Correct path is SM finish flow, not a second RED/GREEN cycle.
  - Severity: major (procedural)
  - Forward impact: SM must run `pf sprint story finish 42-1` directly from session; no TEA→Dev→Reviewer chain required for this story. Sibling 42-2 likely needs the same treatment.

## TEA Assessment

**Tests Required:** No (already written and merged)
**Reason:** Story 42-1 was implemented and merged as PR #17 (commit `ada5476`) on 2026-04-20. 59 tests exist across `tests/game/test_encounter.py` and `tests/game/test_combatant.py`, all passing on current HEAD. `sprint/epic-42.yaml` tracker status is stale — this is ADR-085 tracker hygiene, not new work.

**Test Files (existing, verified):**
- `sidequest-server/tests/game/test_encounter.py` — StructuredEncounter, EncounterMetric, SecondaryStats, StatValue, EncounterActor, EncounterPhase, MetricDirection, constructors, resolve_from_trope, GameSnapshot.encounter type promotion, AC5 validation, AC6 extra=ignore
- `sidequest-server/tests/game/test_combatant.py` — Combatant Protocol with runtime_checkable; port of combatant.rs inline tests
- `sidequest-server/tests/fixtures/encounters/*.json` — 4 hand-authored Rust-parity fixtures

**Tests Written:** 0 by me; 59 existing (verified passing)
**Status:** GREEN on main (not RED — no RED state exists for this story)

### Rule Coverage

Pre-existing tests already cover the applicable rules:

| Rule | Test(s) | Status |
|------|---------|--------|
| No Silent Fallbacks (CLAUDE.md) | `test_unknown_encounter_type_raises_on_load` (AC5) | passing |
| Validated constructors | `test_edge_fraction_zero_max_returns_zero` (AC3 guard) | passing |
| Forward-compat on GameSnapshot | `test_snapshot_extra_fields_ignored` (AC6) | passing |
| Round-trip JSON parity | `test_round_trip_combat_fixture`, `test_round_trip_chase_fixture` (AC1) | passing |

**Rules checked:** Rule coverage on existing suite appears adequate for story scope; a full lang-review audit against `gates/lang-review/python.md` was not performed by TEA in this session (the audit lane is for new test authorship, which did not occur).
**Self-check:** No vacuous tests authored (no tests authored).

**Handoff:** Back to SM (Captain Carrot) — run finish flow. Do NOT hand off to Dev; there is no GREEN phase to run when the code is already merged.