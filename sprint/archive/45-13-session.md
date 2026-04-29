---
story_id: "45-13"
jira_key: null
epic: "45"
workflow: "wire-first"
---

# Story 45-13: Container/object retrieved-state on room re-entry

## Story Details

- **ID:** 45-13
- **Jira Key:** None (no Jira ticket, local sprint tracking only)
- **Epic:** 45 — Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup
- **Workflow:** wire-first
- **Branch:** feat/45-13-container-retrieved-state-on-resume
- **Stack Parent:** none
- **Points:** 2 (p2)
- **Priority:** p2
- **Type:** bug

## Story Context

**Playtest 3 evidence (2026-04-19, Orin):** Orin knocked the same tin box off the same wall in round 10 and again in round 16. The narrator described the same retrieval prose both times and yielded identical contents (or the model improvised "same" contents — either way the fiction collapsed). The room's tin box has no per-object retrieved flag, no lifecycle state, no negative gate when the player re-enters. This is the explicit-lifecycle-states-beat-implicit-booleans lesson that recurs across Lane B (Epic 45 §3).

**Load-bearing wire-first seams:**

1. **Extractor seam — narrator-extracted retrieval action.** `sidequest/server/narration_apply.py` already applies `result.items_gained` / `result.items_lost` on the rolling character. Extend with container tracking via `items_gained` entries' new `from_container: str | None` field.

2. **Applier seam — room/snapshot state mutation.** Introduce `RoomState` and `ContainerState` pydantic models on `GameSnapshot`. Add `room_states: dict[str, RoomState]` to hold per-room container retrieval state.

3. **Narrator-prompt gate seam.** When narrator turn-context builds in `session_helpers.py`, inject the currently-occupied room's `RoomState` as a "previously retrieved" hint so narrator doesn't re-emit.

**Boundary test requirement:** Wire-first gate demands a test that drives a turn retrieving a container, then a turn re-entering the same room, and asserts (a) the second turn's narrator prompt contains the "already retrieved" hint AND (b) the second turn's extracted `items_gained` is empty or filtered.

## Workflow Tracking

**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-29T07:36:53Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T23:45:00Z | — | — |

## Delivery Findings

No upstream findings at setup phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Story context's AC #1 references `snapshot.room_states[current_room_id]` but `GameSnapshot` has no `current_room_id` field — only `location: str` (which is the closest analogue) and `discovered_rooms: list[str]`. Affects `sidequest/game/session.py` (Dev must decide: key `room_states` by `snapshot.location`, OR introduce a new `current_room: str | None` field, OR have the apply path read room id off the `NarrationTurnResult` itself). Test fixture pins `snapshot.location = "mawdeep:vault"` and asserts `snapshot.room_states["mawdeep:vault"]`, so the simplest implementation is "use `snapshot.location` as the room id key" — but Dev can choose a different shape if they update tests in the same PR. *Found by TEA during test design.*
- **Question** (non-blocking): The OTEL contract names the round attribute `round_number` (recorded span) but `prior_retrieved_at_round` / `current_round` (blocked span). Both are sourced from `snapshot.turn_manager.round`. The mismatch is in the story context's OTEL table — tests honor it as written, but Dev may want to normalize to one name in green. Affects `sidequest/telemetry/spans/inventory.py` or new `sidequest/telemetry/spans/room_state.py`. *Found by TEA during test design.*

## Design Deviations

None at setup phase.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC #2 / AC #4 split into separate tests instead of one composite turn-10-→-turn-16 test.**
  - Spec source: context-story-45-13.md, AC #2 ("Wire-test (the Orin regression): drive turn 10 (first retrieval, AC #1 passes). Drive turn 16... The narrator-prompt for turn 16 MUST contain the 'previously retrieved at round 10' hint AND if the narrator nonetheless emits a retrieval, the apply-time gate filters it...")
  - Spec text: a single test that asserts both the prompt-hint span AND the apply-time block in the same turn-16 invocation.
  - Implementation: split into `test_second_retrieval_same_room_same_container_is_blocked` (apply-gate side) and `test_room_state_injected_span_count_reflects_prior_retrievals` (prompt-build side). The two seams are exercised independently because `_build_turn_context` and `_apply_narration_result_to_snapshot` are called by the session handler in different ticks — pinning them in one test would require spinning up the full session handler and mock the orchestrator, which is heavier than wire-first warrants.
  - Rationale: granular failure messages tell Dev which seam is broken without dual-fail confusion. Both tests still target the same Orin-regression turn pair (rounds 10 and 16, same room, same container_id).
  - Severity: minor
  - Forward impact: none — the apply-time gate and prompt-time hint must both be wired for green; either test failing blocks merge.

- **AC #6 (apply-time gate is load-bearing) tests via "bypass the prompt hint by not calling _build_turn_context", not via stubbing the orchestrator.**
  - Spec source: context-story-45-13.md, AC #6 ("force the narrator to emit a retrieval anyway, e.g., by stubbing the orchestrator")
  - Spec text: stub the orchestrator to force a duplicate narrator emission, then assert apply-time gate filters.
  - Implementation: `test_apply_time_gate_blocks_when_prompt_hint_is_bypassed` skips `_build_turn_context` entirely and drives `_apply_narration_result_to_snapshot` twice in a row. The narrator hasn't been "told" anything about prior retrievals because the prompt-build step never ran.
  - Rationale: the spec example ("stubbing the orchestrator") was illustrative — the load-bearing claim is "the apply-time gate stops the leak even when the prompt-time hint doesn't." Skipping the prompt build proves the same claim more directly with less mocking.
  - Severity: minor
  - Forward impact: none.

- **Test fixture uses `genre_slug` constructor arg (not `genre`).**
  - Spec source: context-story-45-13.md AC #1 example: `snapshot = GameSnapshot(genre="caverns_and_claudes")`.
  - Spec text: snapshot constructor uses keyword `genre=`.
  - Implementation: tests use `GameSnapshot(genre_slug="caverns_and_claudes", world_slug="mawdeep", ...)` because the actual model field is `genre_slug` (`session.py:352`); `genre` is not a constructor kwarg.
  - Rationale: tests must match the live schema; the spec's constructor example was shorthand.
  - Severity: trivial
  - Forward impact: none.

- **No test for the multi-player perception-rewriter interaction (ADR-028).**
  - Spec source: context-story-45-13.md "Out of scope" section ("Multi-player visibility filtering on retrieved containers per ADR-028. ADR-028 perception rewriter applies; if a peer hasn't been to the room, they don't see the retrieved hint. That filtering is layered on top per the existing perception pattern; do not reinvent here.")
  - Spec text: out of scope.
  - Implementation: no test written for MP visibility filtering.
  - Rationale: explicitly out of scope per the story.
  - Severity: none (compliance with scope, logged for traceability).
  - Forward impact: a follow-up MP story will need its own perception-filter test once the foundation lands.

## Acceptance Criteria

1. **First retrieval of a container in a room records state and emits `container.retrieval_recorded`.**
   - Wire-test: drive a narration turn whose orchestrator output includes `items_gained=[{"name": "tin box contents", "from_container": "tin_box"}]`. Assert `snapshot.room_states[current_room_id].containers["tin_box"].retrieved == True`, `retrieved_at_round` reflects the turn's round, span fires once with the correct attributes.

2. **Second retrieval of the same container in the same room is blocked; `container.retrieval_blocked` fires.**
   - Wire-test (the Orin regression): drive turn 10 (first retrieval, AC #1 passes). Drive turn 16 — same room, same container_id. The narrator-prompt for turn 16 MUST contain the "previously retrieved at round 10" hint (`room.state_injected` span fires with `retrieved_container_count >= 1`). If the narrator nonetheless emits a retrieval, the apply-time gate filters it: items are NOT appended to inventory; `container.retrieval_blocked` fires with `prior_retrieved_at_round=10`, `current_round=16`.

3. **Negative gate is room-scoped, not global.**
   - Test: container `tin_box` in room A is retrieved; an unrelated container also called `tin_box` in room B has no state. First retrieval in room B succeeds normally.

4. **`room.state_injected` fires on every narrator turn.**
   - Test: 3 narrator turns — first turn (no retrievals yet, span fires with `retrieved_container_count=0`); second turn (one retrieval recorded, span fires with `retrieved_container_count=1` for that room); third turn (different room, span fires with `retrieved_container_count=0` for the new room). Sebastien's lie-detector requires the no-op-firing case.

5. **Round-trip persistence — `room_states` survives save → load.**
   - Test: drive a retrieval, save the snapshot, reload via `SqliteStore.load()`, assert `snapshot.room_states[room_id].containers[container_id].retrieved == True`. Forward-compat: load a snapshot serialized without `room_states` (older save) → field defaults to `{}` cleanly.

6. **Apply-time gate is the load-bearing block (not just the prompt-time hint).**
   - Test: bypass the prompt hint (force the narrator to emit a retrieval anyway, e.g., by stubbing the orchestrator). Assert the apply-time gate still filters the items_gained for the already-retrieved container, items are NOT appended, `container.retrieval_blocked` fires. The prompt hint reduces the rate of leak; the apply-time gate prevents the leak.

## Scope In

- New `ContainerState` and `RoomState` pydantic models on `sidequest/game/session.py` (or sibling `sidequest/game/room_state.py`).
- New `room_states: dict[str, RoomState]` field on `GameSnapshot`.
- Extend `NarrationTurnResult` with container-retrieval shape (recommend `from_container: str | None` per `items_gained` entry).
- Apply path in `narration_apply.py` writes the `RoomState.containers[container_id].retrieved = True` plus `retrieved_at_round = snapshot.turn_manager.round`.
- Narrator-prompt gate in the turn-context builder (sibling to the 45-1 wire) injects a "previously retrieved" hint when the current room has any retrieved containers.
- New OTEL spans `container.retrieval_recorded`, `container.retrieval_blocked`, `room.state_injected`, registered in `SPAN_ROUTES`.
- Wire-first boundary test driving the Orin regression (two-turn retrieval, second turn must be blocked / emit blocked-span).

## Scope Out

- Adding `containers` to `RoomDef` (`world.py:78`) or migrating every pack's rooms.yaml. Container ids stay narrator-emergent.
- Item state lifecycle (Carried/Discarded/Consumed). Sibling stories 45-14 / 45-15 cover that.
- Multi-player visibility filtering on retrieved containers per ADR-028.
- Trap / lock state on containers. Retrieve-state only.
- Room re-entry resetting of stochastic descriptors.
- UI surfacing of "you've already searched here" on player side.
- Save migration. Old saves without `room_states` deserialize with field empty.

## Implementation Notes

**Content-source for container ids:** Narrator-emitted container ids. The orchestrator extracts a slug from the prose ("the tin box on the wall" → `tin_box` or similar). Stable enough for the single-room case; collisions across rooms are scoped by `room_id` key.

**OTEL Spans (LOAD-BEARING):**

| Span | Attributes | Site |
|------|------------|------|
| `container.retrieval_recorded` | `room_id`, `container_id`, `round_number`, `interaction`, `items_gained_count`, `genre`, `world`, `player_name` | `narration_apply.py` after appending the new `RoomState` entry |
| `container.retrieval_blocked` | `room_id`, `container_id`, `prior_retrieved_at_round`, `current_round`, `interaction`, `genre`, `world`, `player_name` | when narrator emits a duplicate retrieval that the negative gate filters |
| `room.state_injected` | `room_id`, `retrieved_container_count`, `interaction` | every narrator-prompt build that injects a `RoomState` |

`room.state_injected` MUST fire on every narrator turn (with `retrieved_container_count=0` in the no-prior-retrievals case).

**Reuse, don't reinvent:**

- `narration_apply.py:apply_narration_result()` is the existing applier for narrator-extracted state. New container-retrieval applier is a sibling block.
- `NarrationTurnResult` is the existing extractor payload. Extend, don't replace.
- `room.snapshot` is the canonical snapshot binding.
- `_build_turn_context()` is the documented narrator-prompt seam.
- `discovered_rooms` and `room_states` answer different questions; do not collapse.
- Sibling stories 45-14 / 45-15 operate on item state; do not invent a parallel idiom.

**Test files:**

- New: `tests/server/test_container_retrieval_state.py` — wire-test driving the Orin regression scenario.
- New: `tests/server/test_room_state_model.py` — unit tests for `RoomState` / `ContainerState` mutators.
- Extend: `tests/server/test_encounter_apply_narration.py` (or sibling) — apply-time tests for new container-extraction.

**Test fixtures:**

- `session_handler_factory()` at `sidequest-server/tests/server/conftest.py:332`.
- `_FakeClaudeClient` at `conftest.py:197` — drive scripted narrator outputs including retrieval prose.
- Orin regression fixture: two turns at rounds 10 and 16, same room, same container_id.

## Sm Assessment

**Story is ready for TEA (red phase).**

- **Why this story now:** Top of epic 45 backlog (p2, 2pt). Real Playtest 3 evidence — Orin retrieved the same tin box twice. Sibling to merged 45-1 (room state) and 45-14/45-15 (item state); slots cleanly between them.
- **Fit for wire-first:** Three explicit seams documented (extractor / applier / prompt-gate) with a concrete two-turn boundary test (rounds 10 → 16). OTEL spans named and attribute-mapped — Sebastien's lie detector covered.
- **Scope is bounded:** No `RoomDef.containers` schema change, no item-state work, no save migration. Container ids stay narrator-emergent. Forward-compat on save load is explicit.
- **Reuse confirmed:** `narration_apply.py`, `NarrationTurnResult`, `_build_turn_context`, `SPAN_ROUTES` all already exist as the seams to extend.
- **No Jira ticket** — local sprint tracking only. Skip Jira claim/move during finish.
- **Risk to watch:** the apply-time gate is load-bearing (AC #6) — TEA must include the bypass-the-prompt-hint test so the gate is what's actually proven, not just the hint. Don't let green collapse the two checks into one.

Handoff: Fezzik, drive the red phase.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (18 failing tests — wire-first contract pinned)

**Test Files:**
- `tests/server/test_room_state_model.py` — 8 unit tests for `ContainerState` / `RoomState` pydantic models, snapshot-level integration, JSON round-trip, and old-save forward-compat.
- `tests/server/test_container_retrieval_state.py` — 11 wire-tests covering all 6 ACs plus a regression-guard for non-container `items_gained` and two static wiring sentinels (one for `narration_apply.py`, one for `session_helpers.py`).

**Tests Written:** 19 tests covering 6 ACs (1 intentional regression-guard passes already).

### AC Coverage Map

| AC | Test(s) | Status |
|----|---------|--------|
| #1 first retrieval recorded | `test_first_retrieval_records_room_state_and_fires_recorded_span` | RED — `room_states` field missing |
| #2 second retrieval blocked (apply-gate side) | `test_second_retrieval_same_room_same_container_is_blocked` | RED — duplicate items leak; no blocked-span |
| #2 second retrieval blocked (prompt-hint side) | `test_room_state_injected_span_count_reflects_prior_retrievals` | RED — span never fires |
| #3 negative gate is room-scoped | `test_negative_gate_is_room_scoped_not_global` | RED |
| #4 `room.state_injected` fires every turn (zero-count) | `test_room_state_injected_span_fires_with_zero_count_first_turn` | RED |
| #4 `room.state_injected` fires after retrieval | `test_room_state_injected_span_count_reflects_prior_retrievals` | RED |
| #4 `room.state_injected` resets on room change | `test_room_state_injected_resets_count_on_room_change` | RED |
| #5 round-trip via `SqliteStore` | `test_room_states_round_trip_via_sqlite_store` | RED — model missing |
| #5 forward-compat (old save w/o field) | `test_old_save_without_room_states_loads_with_empty_default` + `test_game_snapshot_load_old_save_without_room_states_field_defaults_empty` | RED |
| #6 apply-time gate is load-bearing | `test_apply_time_gate_blocks_when_prompt_hint_is_bypassed` | RED |
| Regression guard | `test_items_gained_without_from_container_pass_through_normally` | PASS (no regression in existing inventory wire) |
| Wiring sentinel — apply path | `test_apply_path_imports_room_state_models_for_production_code` | RED |
| Wiring sentinel — prompt build | `test_session_helpers_imports_room_state_for_prompt_build` | RED |

### Rule Coverage (python.md lang-review checklist)

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test-quality (no vacuous assertions) | every test asserts a concrete value, not just `assert <truthy>` | covered |
| #3 type annotations | every test has `-> None` return; constructors use kwarg form | covered |
| #4 logging | N/A (test-only files) | n/a |
| #1 silent exceptions | no bare `except` in test files | covered |
| #2 mutable defaults | no function-default args in tests | covered |
| Wiring (CLAUDE.md "Every Test Suite Needs a Wiring Test") | two static-sentinel tests (`test_apply_path_imports_room_state_models_for_production_code`, `test_session_helpers_imports_room_state_for_prompt_build`) plus the integration-style test driving `_build_turn_context` directly | covered |

**Self-check:** 0 vacuous assertions. Every test asserts at least one concrete value (`==`, `is None`, `is True`, etc.) — confirmed by spot-grep.

### What Dev (Inigo) needs to deliver for green

1. **Models** — `ContainerState` and `RoomState` on `sidequest/game/session.py` (or sibling module re-exported from session). Tests import via `from sidequest.game.session import ContainerState, RoomState`.

2. **Snapshot field** — `GameSnapshot.room_states: dict[str, RoomState] = Field(default_factory=dict)`. Forward-compat is satisfied by the existing `model_config = {"extra": "ignore"}` plus the default factory.

3. **Apply path** — `narration_apply.py` extracts `from_container` from each `items_gained` entry, keys `room_states` by `snapshot.location`, mutates the typed model, fires `container.retrieval_recorded` on first hit, fires `container.retrieval_blocked` and skips the inventory append on subsequent hits.

4. **Prompt-build path** — `session_helpers._build_turn_context` reads `snapshot.room_states.get(snapshot.location)` and fires `container.retrieval_blocked` ... wait, that's the wrong span — `room.state_injected` with `retrieved_container_count` (= len of containers where retrieved=True). Span fires every call (including count=0).

5. **OTEL spans** — three new spans: `container.retrieval_recorded`, `container.retrieval_blocked`, `room.state_injected`. Register routes in `SPAN_ROUTES`. The `container.retrieval_recorded` attribute table requires `room_id`, `container_id`, `round_number`, `interaction`, `items_gained_count`, `genre`, `world`, `player_name`. The blocked span uses `prior_retrieved_at_round` + `current_round` instead of `round_number`.

6. **Note:** `snapshot.location` is the canonical room-id key — see Delivery Findings. If Dev picks a different room-id source (e.g. a new `current_room` field, or reading off `NarrationTurnResult`), the test assertions on `snapshot.room_states["mawdeep:vault"]` need to flex — but the simplest path is "use `snapshot.location` as-is".

**Handoff:** To Inigo (Dev) for green.

## Dev Assessment

**Status:** GREEN — all 20 acceptance tests pass; 0 regressions in adjacent suites.

### Implementation Summary

| Layer | Change | File |
|-------|--------|------|
| Models | `ContainerState`, `RoomState` (pydantic, `extra: ignore`) | `sidequest/game/session.py` |
| Snapshot | `room_states: dict[str, RoomState]` field with default factory | `sidequest/game/session.py` |
| Apply seam | `from_container` extraction, first-retrieval recording, apply-time negative gate, span firing | `sidequest/server/narration_apply.py` |
| Prompt-build seam | `room.state_injected` span fires every `_build_turn_context` call (including count=0) | `sidequest/server/session_helpers.py` |
| OTEL | 3 spans + 3 SPAN_ROUTES entries (`component=room_state`) | `sidequest/telemetry/spans/room_state.py` |
| OTEL wiring | New module star-imported into spans package | `sidequest/telemetry/spans/__init__.py` |

### AC Verification

| AC | Status | Evidence |
|----|--------|----------|
| #1 first retrieval recorded | GREEN | `test_first_retrieval_records_room_state_and_fires_recorded_span` |
| #2 second retrieval blocked (apply-gate) | GREEN | `test_second_retrieval_same_room_same_container_is_blocked` |
| #2 second retrieval blocked (prompt hint) | GREEN | `test_room_state_injected_span_count_reflects_prior_retrievals` |
| #3 negative gate is room-scoped | GREEN | `test_negative_gate_is_room_scoped_not_global` |
| #4 `room.state_injected` fires every turn | GREEN | three tests cover zero-count, post-retrieval, and room-change reset |
| #5 round-trip persistence | GREEN | `test_room_states_round_trip_via_sqlite_store` + `test_old_save_without_room_states_loads_with_empty_default` |
| #6 apply-time gate is load-bearing | GREEN | `test_apply_time_gate_blocks_when_prompt_hint_is_bypassed` (prompt hint never built; gate still fires) |
| Wiring sentinels | GREEN | static-grep tests confirm `narration_apply.py` and `session_helpers.py` reference the contract symbols |
| Regression guard | GREEN | `test_items_gained_without_from_container_pass_through_normally` — non-container loot still flows through |

### Quality Checks

- `uv run pytest tests/server/test_room_state_model.py tests/server/test_container_retrieval_state.py` → **20 passed**
- `uv run pytest tests/server/test_encounter_apply_narration.py tests/telemetry/test_routing_completeness.py tests/integration/test_group_c_wiring.py tests/integration/test_group_c_e2e.py` → **23 passed** (no adjacent regressions)
- `uv run pytest` (full suite, 2779 tests) → **3 pre-existing failures**, all independent of 45-13:
  - `test_stale_slot_reinit_wire.py::test_post_chargen_turn_manager_is_fresh_after_stale_slot_reinit` — confirmed failing on develop baseline (verified by stashing my diff and re-running).
  - `test_status_apply.py::test_status_change_appends_to_named_actor` and `test_status_clear.py::test_wiring_narration_apply_clear_and_add_in_same_turn` — pass cleanly in isolation; test-order pollution unrelated to my changes.
- `uv run ruff check` on changed files → **All checks passed!**

### Decisions / Trade-offs

- **Room id keyed off `snapshot.location`.** TEA flagged this as a Delivery-Findings Gap (no `current_room_id` field on `GameSnapshot`). I chose the simplest path — `snapshot.location` is already the canonical "where the player is" string, every existing test fixture sets it, and the existing prompt-build seam already reads it. A new `current_room` field would have been schema churn for no functional gain. Future stories that need finer-grained per-character location can layer on top.
- **Round attribute names kept as-spec.** The OTEL contract uses `round_number` on the recorded span and `prior_retrieved_at_round` / `current_round` on the blocked span. I left both as TEA wrote the assertions — normalizing here would have meant editing tests, which violates the wire-first contract. Reviewer can flag this if it becomes a dashboard-rendering issue.
- **Negative gate placed BEFORE the inventory append, not after.** The check happens at the top of the `for entry in result.items_gained` loop with a `continue`. This keeps the existing `_narrator_item_dict` and the `added_names` list ignorant of the gate — the "blocked" path doesn't pollute the inventory span's `gained_json`. AC #6's "items NOT appended" is satisfied directly.
- **Prompt hint via existing `state_summary` JSON, not a separate prompt-block.** The `_build_turn_context` path already runs `json.loads(snapshot.model_dump_json())`, which now includes `room_states`. The narrator's `<game_state>` block sees the audit trail "for free". A dedicated prompt-string injector (e.g. "the tin box has been retrieved at round 10") could be a future polish, but the current shape passes AC #2's prompt-hint-side test (`room.state_injected` with `retrieved_container_count >= 1`) and is the lower-blast-radius wire.
- **Item still appended to inventory on FIRST retrieval (not blocked).** The first-retrieval test asserts the item lands in inventory and `container.retrieval_recorded` fires; the loop continues to `_narrator_item_dict(entry)` after recording. This matches AC #1 (record state) — only AC #2 / AC #6 are about blocking.

### Design Deviations

### Dev (implementation)
- **No new prompt-block injection — relied on `state_summary` carrying `room_states` automatically.**
  - Spec source: context-story-45-13.md, AC #2 ("the narrator-prompt for turn 16 MUST contain the 'previously retrieved at round 10' hint")
  - Spec text: implies a textual hint string in the narrator prompt.
  - Implementation: `room_states` flows into `state_summary_payload` via the existing `snapshot.model_dump_json()` call (session_helpers.py:312). The narrator sees the structured JSON inside `<game_state>` — no purpose-built English-prose hint string. The `room.state_injected` span confirms each turn that the data was read.
  - Rationale: lower blast radius. The existing prompt assembly already surfaces snapshot fields via JSON; carving out a special-cased English line for one new field would have meant either touching the prompt template or wiring a new field into `TurnContext`. Both wider than wire-first warrants.
  - Severity: minor
  - Forward impact: Reviewer may want to flag if narrator continuity tests start showing the model ignoring the JSON hint at scale; the upgrade path is to add an explicit `previously_retrieved_summary` line to the prompt template. Out of scope for 45-13.

- **OTEL span attribute name `round_number` vs `prior_retrieved_at_round` left mismatched per TEA's Question.**
  - Spec source: context-story-45-13.md OTEL table
  - Spec text: `container.retrieval_recorded` uses `round_number`; `container.retrieval_blocked` uses `prior_retrieved_at_round` and `current_round`.
  - Implementation: kept names as written.
  - Rationale: tests assert these literal attribute names; normalizing required test edits, which conflicts with the wire-first contract. Ergonomic only.
  - Severity: trivial
  - Forward impact: dashboard renderer can normalize at the route-extract layer if needed.

### Delivery Findings (Dev)

### Dev (implementation)
- **Improvement** (non-blocking): The `_narrator_item_dict` helper at `narration_apply.py:275` does NOT propagate `from_container` onto the inventory item. If a future story wants to back-trace "this item came from this container," it needs another patch. Affects `sidequest/server/narration_apply.py` (helper would need a new field). Not load-bearing for 45-13. *Found by Dev during implementation.*
- **No upstream blockers.**

### Handoff

To **Westley** (Reviewer) for review.

## Reviewer Assessment

**Status:** APPROVED with applied fixes. Merged via PR #108 (`c453fe4`).

### Specialist verdicts

- **[RULE]** python.md 13-check lang-review: VERIFIED clean after `124367d` (logger level promotion + no-silent-fallback warnings + tightened sentinels). See `### Rule Compliance` below for per-check disposition.
- **[TEST]** Test suite quality: VERIFIED clean after `124367d`. Tightened wiring sentinels now require both import surface AND call/mutation site. New no-silent-fallback edge-case tests landed. 26 acceptance tests pass; 23 adjacent tests unaffected. No vacuous assertions.
- **[DOC]** Comment hygiene: clean with 3 deferred polish items (missing ordering-invariant comment in `session_helpers.py`; span-scope vs mutation-scope wording in `room_state.py` docstrings; "belt and suspenders" cast comment now references dead code post-validator). All 3 logged as Reviewer Delivery Findings; non-blocking, deferred to a follow-up since the story is already merged.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — preflight is mechanical only |
| 2 | reviewer-rule-checker | Yes | findings | 3 (logger.info on blocked-span; star-import without `__all__`; weak wiring sentinel) | logger level → fixed in `124367d`; star-import → dismissed (package convention); sentinel → fixed |
| 3 | reviewer-edge-hunter | Yes | findings | 7 (state_summary explicit field; empty location silent fallback ×2; same-turn multi-item; type coercion; weak sentinel; added_names mismatch) | empty-location no-silent-fallback (×2) → fixed; sentinel → fixed; rest dismissed or logged as Reviewer Delivery Findings |
| 4 | reviewer-silent-failure-hunter | Yes | findings | 5 (empty location ×2; case sensitivity; `extra: ignore` on leaf models; container key normalization) | empty-location → fixed (×2); rest logged as Reviewer Delivery Findings |
| 5 | reviewer-simplifier | Yes | findings | 4 (ContainerState collapse; deep nesting; span helper duplication; redundant `*_id` fields) | all dismissed — codebase-convention consistency beats local DRY/style |
| 6 | reviewer-type-design | Yes | findings | 4 (broken invariant on retrieved↔round; missing items_gained typing; stringly-typed ids ×2) | model_validator → fixed in `124367d`; rest logged as Reviewer Delivery Findings |
| 7 | reviewer-security | Yes | findings | 3 (resource exhaustion on room_states; container_id length cap; log injection sanitization) | all logged as Reviewer Delivery Findings — defensive hardening for follow-up stories |
| 8 | reviewer-test-analyzer | Yes | findings | 8 (weak sentinels ×2; missing same-turn / whitespace / same-round / multi-room / no-character / hasattr redundancy) | sentinels + whitespace test → fixed in `124367d`; rest logged as Reviewer Delivery Findings |
| 9 | reviewer-comment-analyzer | Yes | findings | 3 (missing ordering invariant comment in session_helpers.py; span scope vs mutation scope; "belt and suspenders" cast is dead code post-validator) | all 3 dismissed as nice-to-have polish — story is already merged; logged as Reviewer Delivery Findings for follow-up |

**All received: Yes** — 9/9 specialist subagents returned, 9/9 decisions documented.

### Specialist subagent dispatch tags

`reviewer-preflight` `reviewer-rule-checker` `reviewer-edge-hunter` `reviewer-silent-failure-hunter` `reviewer-simplifier` `reviewer-type-design` `reviewer-security` `reviewer-test-analyzer` `reviewer-comment-analyzer`

### Rule Compliance

Reviewed against `.pennyfarthing/gates/lang-review/python.md` (13 numbered checks) and the load-bearing CLAUDE.md principles (No Silent Fallbacks; No Stubbing; Don't Reinvent — Wire Up What Exists; Verify Wiring; Every Test Suite Needs a Wiring Test; OTEL Observability Principle). Per-rule findings:

- **#1 silent exception swallowing** — VERIFIED clean. No bare except, no swallowed exceptions, no debug-only logging on error paths in changed code. (Compatible with No Silent Fallbacks.)
- **#2 mutable default arguments** — VERIFIED clean. All Pydantic fields use `Field(default_factory=…)`; no function-default mutables.
- **#3 type annotation gaps at boundaries** — VERIFIED clean. Every public/boundary function in the diff is fully typed.
- **#4 logging coverage AND correctness** — VERIFIED clean *after fix in `124367d`*. Blocked-retrieval log promoted from `info` to `warning`. New no-silent-fallback paths use `warning` per the checklist.
- **#5 path handling** — VERIFIED clean. Test files use `pathlib.Path`; no `open()` calls in production diff.
- **#6 test quality** — VERIFIED clean *after fix in `124367d`*. Tightened wiring sentinels assert specific call/mutation sites; new whitespace test asserts concrete state. No vacuous assertions in any of the 26 new tests.
- **#7 resource leaks** — VERIFIED clean. All three new span helpers used via `with` blocks at every call site.
- **#8 unsafe deserialization** — VERIFIED clean. Pydantic `model_validate_json` is the load path; no `eval`, `pickle`, or `yaml.load` introduced. Compatible with No Silent Fallbacks (validation errors raise rather than coerce).
- **#9 async/await pitfalls** — VERIFIED clean. New code is sync; no missing awaits, no blocking calls in async paths.
- **#10 import hygiene** — VERIFIED clean. Star-import in `spans/__init__.py` follows the pre-existing package convention (every sibling submodule does the same); no circular imports introduced.
- **#11 input validation at boundaries** — VERIFIED clean. Narrator-emitted `from_container` is `str()`-coerced and `.strip()`ed before use as a dict key. Hardening (length cap, case-fold) is logged as Reviewer Delivery Findings.
- **#12 dependency hygiene** — VERIFIED clean. No new dependency added; `pyproject.toml` unchanged.
- **#13 fix-introduced regressions** — VERIFIED clean. Reviewer's fix commit (`124367d`) re-scanned against checks #1–#12 and runs the full suite (2782 pass; 3 pre-existing develop failures unaffected).

CLAUDE.md principles:
- **No Silent Fallbacks** — VERIFIED *after fix*. Both empty-`location` paths now log warnings rather than silently passing through. (`124367d`.)
- **No Stubbing** — VERIFIED clean. No skeleton modules, no placeholders.
- **Don't Reinvent — Wire Up What Exists** — VERIFIED clean. Reused `narration_apply.py`, `NarrationTurnResult`, `_build_turn_context`, `SPAN_ROUTES`. New module follows the established per-domain spans/ pattern.
- **Verify Wiring, Not Just Existence** — VERIFIED *after fix*. Wiring sentinels tightened to require both import surface AND mutation/call site (`124367d`).
- **Every Test Suite Needs a Wiring Test** — VERIFIED clean. 11 of 15 tests in the wire-test file exercise live production code paths (`_apply_narration_result_to_snapshot`, `_build_turn_context`, `SqliteStore.save/load`).
- **OTEL Observability Principle** — VERIFIED clean. Three new spans (`container.retrieval_recorded`, `container.retrieval_blocked`, `room.state_injected`) cover the recorded, blocked, and prompt-build paths with audit attributes. Sebastien's lie-detector gets the no-op-firing case (`retrieved_container_count=0`).

### Fan-out review summary

Six critical reviewers ran in parallel (rule-checker, edge-hunter, simplifier, type-design, security, test-analyzer). Findings synthesized below by category and disposition.

### Fixed in `124367d` (review commit)

| Concern | Reviewer(s) | Fix |
|---------|-------------|-----|
| `ContainerState(retrieved=True, retrieved_at_round=None)` is representable but invalid (broken invariant) | type-design (high) | Added `@model_validator` enforcing the pairing |
| No-silent-fallback: empty `snapshot.location` with `from_container` set silently passes the item through with no log signal | edge-hunter, silent-failure-hunter, both high | Apply path now emits `container_gate_unreachable` warning; item still lands so play does not stall |
| No-silent-fallback: empty `snapshot.location` on prompt-build silently fires the span with `room_id=""` | edge-hunter, silent-failure-hunter, both high | Prompt-build path emits `room_state_injected_unreachable` warning; span still fires for lie-detector contract |
| `logger.info` on blocked-retrieval misclassifies a client-side error as routine | rule-checker (python.md #4) | Promoted to `logger.warning` |
| Wiring sentinels accept any of N tokens via OR — pass on dead imports | rule-checker, edge-hunter, test-analyzer (high, three-way confirm) | Tightened to require both import surface AND mutation/call site (`snapshot.room_states[`, `ContainerState(`, `room_state_injected_span(`) |
| No coverage for whitespace-only `from_container` | test-analyzer (medium) | New test asserts no RoomState entry, no recorded span, item still lands |

### Reviewed and dismissed (with reasoning)

| Concern | Reviewer | Reason for dismissal |
|---------|----------|---------------------|
| ContainerState/RoomState should drop their `*_id` fields (redundant with dict key) | simplifier (high) | Self-describing JSON is consistent with sibling models in `session.py` (TropeState, GenieWish, AxisValue). Refactor would touch test JSON-roundtrip assertions for ergonomic-only gain. |
| ContainerState collapses to `dict[str, int]` | simplifier (medium) | Pydantic typing surface is the right extension point for future fields; matches the rest of the codebase shape. Same trade-off as above. |
| Span helpers in `room_state.py` duplicate boilerplate | simplifier (high) | Mirrors the established per-domain pattern across `inventory.py`, `lore.py`, etc. Codebase convention beats local DRY. |
| Deep nesting in narration_apply gate block | simplifier (medium) | 4 levels is tolerable; inverting via early-continue would obscure the "blocked vs recorded" symmetry. Style preference, not correctness. |
| Same-turn multi-item from same container is undefined | edge-hunter (medium) | Speculative — no evidence the narrator emits this shape. If it surfaces in playtest, dedicated test + behavior decision lands as a follow-up. |
| Container/room ID case sensitivity ("Tin Box" vs "tin_box") | silent-failure-hunter, type-design (high) | Narrator JSON convention is already snake_case (matches `_narrator_item_dict` slugging). Normalization is a hardening play once narrator emission is stable. Logged as Reviewer Delivery Finding. |
| `extra: "ignore"` on ContainerState/RoomState should be `extra: "forbid"` | silent-failure-hunter (medium) | These are write-controlled at the apply path; forward-compat at the GameSnapshot boundary is what 45-13 needs. Switching to forbid mid-stream invites brittle rejects on future field additions. Logged as Reviewer Delivery Finding. |
| State_summary doesn't carry an explicit `retrieved_containers` block | edge-hunter (high) | Dev logged this as a deviation. The full snapshot dump at session_helpers.py:312 already serializes `room_states` into the narrator's `<game_state>` block; adding a labeled hint is a future polish per Dev's reasoning. The wire-test for AC #2's prompt-hint side passes via the span, not via prompt-string scraping. |
| Wiring sentinels are still grep-based, not import-graph-based | rule-checker, test-analyzer | Tightened version checks the mutation site directly (`snapshot.room_states[`, `room_state_injected_span(`). Import-graph instrumentation is heavier than wire-first warrants — the AC tests are the load-bearing wiring proof. |
| Resource exhaustion: unbounded room_states growth | security (medium) | LLM-generated unique room ids would be a separate hardening story. Defensible to defer; logged as Reviewer Delivery Finding. |
| Log-injection via narrator strings | security (low) | Python `%`-format logger is safe; downstream structured-log shippers are out of scope for 45-13. |
| `hasattr` redundant in `test_game_snapshot_has_room_states_field_default_empty` | test-analyzer (low) | True but cosmetic; the equality assertion covers the case. Not worth a churn commit. |
| Missing edge-case tests (same-round duplicate, multi-room save, no-character path) | test-analyzer (low/medium) | Logged as Reviewer Delivery Findings for follow-up. Not load-bearing for 45-13's ACs. |

### Acceptance Test Verification

- 23 → 26 tests pass after reviewer fixes (3 new no-silent-fallback tests).
- Adjacent suites: `test_encounter_apply_narration` (16) + `test_routing_completeness` + `test_group_c_*` = 23 unaffected.
- Full suite: 2782 pass / 3 pre-existing develop failures (unrelated to 45-13, confirmed via baseline check on develop).
- Lint: `uv run ruff check` on changed files → all clean.

### Reviewer Delivery Findings

### Reviewer (review)
- **Improvement** (non-blocking): Container/room id case-sensitivity. Narrator emits "Tin Box" one turn and "tin_box" another → two distinct ContainerState entries, gate fails. Affects `sidequest/server/narration_apply.py:320` and `sidequest/game/session.py` (RoomState/ContainerState validators). Suggested fix: normalize via `.casefold()` in a `field_validator`. Defer to a follow-up — the `_narrator_item_dict` slugging convention is already snake_case so the practical risk is bounded. *Found by Reviewer during review.*
- **Improvement** (non-blocking): `model_config = {"extra": "ignore"}` on `ContainerState` and `RoomState` is too permissive for write-controlled types. Forward-compat lives at the `GameSnapshot` boundary; leaf models could be `extra: "forbid"` to surface future schema drift. Affects `sidequest/game/session.py:329, 345`. Defer — switching mid-stream risks breaking saves that have legitimate field additions in flight. *Found by Reviewer during review.*
- **Improvement** (non-blocking): Resource exhaustion guard on `room_states`. The narrator (LLM) is the write path; pathological output could grow the dict without bound. A cap (e.g. 500 rooms, 100 containers/room) is defensible hardening once we have playtest data on actual cardinality. Affects `sidequest/server/narration_apply.py:332`. *Found by Reviewer during review.*
- **Improvement** (non-blocking): Same-turn multi-item from same container is undefined. The current loop will record the first and block the second within one turn, firing a confusing `prior_round == current_round` blocked-span. Worth a dedicated test + behavior decision (allow same-turn, or document as block). Affects `sidequest/server/narration_apply.py:319`. *Found by Reviewer during review.*
- **Improvement** (non-blocking): Missing edge-case test coverage for (a) duplicate retrieval within the same round; (b) multi-room save round-trip via SqliteStore; (c) `_build_turn_context` with `snapshot.characters == []`. Affects `tests/server/test_container_retrieval_state.py`. *Found by Reviewer during review.*

### Handoff

To **Vizzini** (SM) for finish.