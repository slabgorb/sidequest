---
parent: context-epic-42.md
workflow: tdd
---

# Story 42-4: Combat dispatch + OTEL catalog + narrator wiring (playtest gate)

## Business Context

42-1 through 42-3 ship types. 42-4 makes them *fire*. This is the story that turns "combat encounter is a Python type" into "combat encounter plays end-to-end on the Python server with parity OTEL spans and narrator integration." Without 42-4 the other three stories are dead inventory.

42-4 also carries the **human playtest acceptance gate**: Keith completes one caverns_and_claudes combat encounter on the Python server before the story closes. This is load-bearing — the Phase 2 IOU cleanup showed that automated tests can be green while the end-to-end path is still wrong. A human turn closes the story; a passing suite does not.

Sebastien-specific value: GM-panel span parity. Every `combat.*` and `encounter.*` span name must survive the port byte-identical so existing GM-panel queries keep working. This is the external contract 42-4 enforces.

## Technical Guardrails

**Port scope:**
- `sidequest-api/crates/sidequest-server/src/dispatch/response.rs` (combat portions — `find_confrontation_def`, label/category resolution, encounter-state payload assembly)
- `sidequest-api/crates/sidequest-server/src/dispatch/tropes.rs:179-181` (encounter resolution from trope beats)
- `sidequest-api/crates/sidequest-server/src/dispatch/aside.rs` (combat portions — `strip_combat_brackets`, `in_combat` aside context)
- `sidequest-api/crates/sidequest-server/src/dispatch/state_mutations.rs:39` (XP-award combat differential)
- `sidequest-api/crates/sidequest-server/src/dispatch/telemetry.rs:92` (`in_combat` telemetry field)
- `sidequest-api/crates/sidequest-telemetry/src/lib.rs:89-266` (combat watcher event catalog)

**Target files (new):**
- `sidequest/server/dispatch/confrontation.py` — `find_confrontation_def(defs, encounter_type)`, label/category resolution, confrontation payload assembly

**Target files (modified):**
- `sidequest/server/dispatch/tropes.py` (existing — extend) — encounter resolve-from-trope
- `sidequest/server/dispatch/aside.py` (existing — extend) — `strip_combat_brackets`, `in_combat` context
- `sidequest/server/session_handler.py` — `in_combat()` helper on dispatch context; wire `TensionTracker` ownership into `_SessionData`; patch-apply resource pools
- `sidequest/agents/orchestrator.py` — `TurnContext.in_combat: bool`; `TurnContext.encounter_summary: str | None`; Valley-zone `encounter_summary` section; wire `TurnContext.pacing_hint` from session's `TensionTracker`
- `sidequest/telemetry/spans.py` — add `SPAN_COMBAT_*` and `SPAN_ENCOUNTER_*` constants

**Dependencies:**
- 42-1, 42-2, 42-3 all merged before 42-4 starts

**Translation key (dispatch-specific):**
- Rust `ctx.in_combat()` helper → Python method on dispatch context object
- Rust `watcher!("combat", StateTransition, ...)` macro → Python `tracer.start_as_current_span(...)` with explicit span name + attribute dict
- Rust `find_confrontation_def(&ctx.confrontation_defs, &enc.encounter_type)` → Python free function reading session's loaded genre pack

**Patterns to follow:**
- **Span names byte-identical to Rust.** The parity test reads Rust source directly; drift is caught in CI, not review.
- **`in_combat()` semantics match Rust exactly:** `snapshot.encounter is not None and not snapshot.encounter.resolved and snapshot.encounter.encounter_type in {"combat", ...}` — confirm the full set from Rust during story setup.
- **No silent fallbacks on confrontation-def lookup.** Unknown `encounter_type` → explicit `ConfrontationDefNotFoundError`, not a string-replace fallback.

**What NOT to touch:**
- Any Rust source
- Chase cinematography (Phase 4; skipped)
- Scenario-engine integration (Phase 5)
- Music-director mood triggering on combat events — Music director isn't ported yet

## Scope Boundaries

**In scope:**
- `in_combat()` helper on dispatch context
- `find_confrontation_def` + label/category resolution
- `ENCOUNTER_STATE` / `STATE_PATCH` message assembly for combat payload
- Encounter resolve-from-trope dispatch extension
- `strip_combat_brackets` + `in_combat` aside context
- XP-award combat differential (25 vs 10)
- Combat OTEL span catalog (`combat.tick`, `combat.ended`, `combat.player_dead`, `encounter.phase_transition`, `encounter.resolved` — confirm full list from Rust)
- Narrator prompt: `encounter_summary` Valley-zone section + `pacing_hint` Early-zone section (wiring TensionTracker from 42-3)
- Resource-pool patch application at encounter-adjacent dispatch sites + threshold lore minting
- `TensionTracker` ownership on `_SessionData` (constructed at session bind; per-turn `tick()` called from dispatch)
- Integration test: protocol-level combat walkthrough (connect → chargen → opening narration → PLAYER_ACTION triggering combat → encounter ticks → resolution)
- OTEL span-catalog parity test (every `combat.*` / `encounter.*` name from Rust appears in Python)
- **Human playtest gate:** Keith runs caverns_and_claudes on Python server, drives one combat to resolution, reaches post-combat narration

**Out of scope:**
- Multiplayer encounter coordination — Phase 3 is single-player
- Encounter-during-chargen (not supported in Rust either)
- Mid-encounter save/load robustness beyond what persistence already handles
- Any UI changes — `STATE_PATCH` shape is stable from Rust, UI already consumes it

## AC Context

**AC1: `in_combat()` helper semantics match Rust.**
Fixture: build `TurnContext` with (a) no encounter, (b) resolved combat, (c) active combat, (d) active chase, (e) active negotiation. Assert `in_combat()` returns True only for case (c), matching Rust. Confirm the exact `encounter_type` set from Rust during story setup.

**AC2: `find_confrontation_def` parity.**
Given a loaded genre pack with confrontation defs, `find_confrontation_def(defs, "duel")` returns the correct def. Unknown type raises `ConfrontationDefNotFoundError` with the unknown string in the message. No silent fallback to `encounter_type.replace('_', ' ')` — that's a Rust convenience bug we're not porting.
*(Note: Rust's `.unwrap_or_else(|| enc.encounter_type.replace('_', ' '))` is a fallback label. Port it, but log a WARN-level OTEL event so the drift is visible. Fail-loud is for model validation; narrator label fallback is cosmetic.)*

**AC3: OTEL span names byte-identical to Rust.**
The parity test greps Rust source for `watcher!("combat", ...` and `watcher!("encounter", ...` calls, extracts span names, and asserts every name appears in Python's `SPAN_*` constants. If a name appears in Rust and not Python, the test fails with a list. A name in Python and not Rust is also a failure (forward-only drift is still drift).

**AC4: XP differential.**
A PLAYER_ACTION during active combat awards 25 XP; the same action outside combat awards 10 XP. Matches Rust `state_mutations.rs:39`. Test with mocked orchestrator response so this is a pure dispatch check.

**AC5: Encounter resolve-from-trope wiring.**
When a trope beat fires that resolves an active encounter (per Rust `dispatch/tropes.rs:179`), the dispatch code calls `encounter.resolve_from_trope(trope_id)`, marks the encounter resolved, and emits the encounter resolution message. Integration test using a canned trope beat + active encounter.

**AC6: `pacing_hint` narrator injection wiring.**
`TensionTracker` on `_SessionData` ticks per turn. Produced `PacingHint` serialises into `TurnContext.pacing_hint`. Orchestrator registers the Early-zone section. Turn without tension tracker (Phase 1/2 narrative-only scene) → `pacing_hint is None` → no section. Turn with active combat → section registered with correct text.

**AC7: Integration walkthrough ends with resolution.**
Protocol-level test: connect to `caverns_and_claudes/grimvault` → walk chargen → opening narration → send a PLAYER_ACTION that the mocked narrator returns with `encounter.engage` patch → multiple turns with metric deltas → final turn with `resolve` patch → assert `snapshot.encounter.resolved is True` and resolution OTEL span fired.

**AC8: Human playtest gate.**
Keith runs `just server-dev`, connects via the UI, plays through one combat encounter in caverns_and_claudes, and reaches post-combat narration. Story does not close until this gate passes. Dev Assessment records the playtest date and a one-line observation ("combat felt correct" or a bug list).

## Assumptions

- **42-1, 42-2, 42-3 merge before 42-4 starts.** DAG enforcement is manual — SM will not start 42-4 while any prerequisite is open.
- **The UI's combat overlay already consumes Rust's `ENCOUNTER_STATE` / `STATE_PATCH` shape.** Python produces the same shape byte-identical; no UI changes needed. Verify during story setup by diffing a captured UI message log against the Python-produced messages.
- **`confrontation_defs` are loaded on the genre pack object at session bind.** Phase 2 chargen wiring should have ensured this; if not, add to the bind sequence.
- **Mocked narrator responses can drive the integration test without coupling to real narration.** Phase 2 tests already do this pattern (see `tests/server/conftest.py::canned_claude_response`). Reuse.
- **The human playtest runs on OQ-2.** Per Keith's memory: build verification on OQ-2, not OQ-1. Playtest gate runs on the same machine Keith uses for live play.
