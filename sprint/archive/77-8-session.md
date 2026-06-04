---
story_id: "77-8"
jira_key: ""
epic: "77"
workflow: "tdd"
---
# Story 77-8: Project the quests spine to the client — emit quest_log + quest_anchors + active_stakes outbound (RELATIONSHIPS-snapshot analog)

## Story Details
- **ID:** 77-8
- **Jira Key:** (not set)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T14:16:21Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T00:00:00Z | 2026-06-04T13:23:19Z | 13h 23m |
| red | 2026-06-04T13:23:19Z | 2026-06-04T13:31:12Z | 7m 53s |
| green | 2026-06-04T13:31:12Z | 2026-06-04T13:39:19Z | 8m 7s |
| review | 2026-06-04T13:39:19Z | 2026-06-04T13:51:55Z | 12m 36s |
| red | 2026-06-04T13:51:55Z | 2026-06-04T13:57:31Z | 5m 36s |
| green | 2026-06-04T13:57:31Z | 2026-06-04T14:04:07Z | 6m 36s |
| review | 2026-06-04T14:04:07Z | 2026-06-04T14:16:21Z | 12m 14s |
| finish | 2026-06-04T14:16:21Z | - | - |

## Story Context

### Acceptance Criteria
1. **AC1 — Rich quests projection on the wire:** the client receives quest_log (title + objective + status + anchor_id per quest), quest_anchors (anchor id + owning quest + beat/location resolution), and active_stakes (string) together, in a typed payload analogous to RelationshipsPayload. Test: serialize a populated spine and assert all three fields appear with correct shape on the wire (wire-parity test, like test_wire_parity.py).

2. **AC2 — Reactive emit on change:** the projection re-broadcasts when seed-at-creation, record_quest, or set_stakes mutate the spine (mirror how relationships_emit fires). Test: mutate via each path → projection carries the new value.

3. **AC3 — Empty/seeded states are well-formed:** an unpopulated spine projects a clean empty payload (not a white-screen-inducing null soup); a single creation-seeded quest+anchor+stakes projects exactly that. Test: empty snapshot → empty-but-valid payload; seeded snapshot → one entry.

4. **AC4 — Wiring:** the projection is reachable from the live NARRATION_END / state-emit production path (not just a serializer unit test). Test: drive a turn through the handler and assert the quests projection is emitted to the socket.

5. **AC5 — Does NOT regress the legacy quests dict consumers or the wire-parity omission contract for genuinely-empty fields.** Test: existing test_wire_parity assertions still hold for empty case.

### Technical Context

**ADR-137 Server Lane Status:**
- 77-1 (seed-at-creation): DONE — `game/quest_seed.py:seed_quest_spine` (~36-89) seeds the spine at session creation
- 77-2 (record_quest/set_stakes tools): DONE — `agents/tools/record_quest.py`, `set_stakes.py` enable narrator control
- 77-3 (quest_anchors→WorldStatePatch): DONE — quest_anchors promoted to first-class; wired to orbital course (orbital/course.py:157)
- 77-4 (cleanup): DONE — legacy quest_updates lane retired, apply_world_patch quest/stakes paths removed

**The Gap:** None of these stories project the spine OUTBOUND to the client.
- Quest data is stored in game state: `quest_log` (dict[str, QuestEntry]: title/objective/status/anchor_id) at game/session.py:790; `quest_anchors` (list[str]) at :861; `active_stakes` (str) at :867
- `_shared_world_delta_to_state_delta()` (server/session_state.py:63-99) only projects location/encounter_id/party_formation/magic_state
- Legacy StateDelta.quests dict[str,str] is never populated; test_wire_parity.py:75-78 asserts omission when empty

**Pattern to Mirror:** ADR-136 RELATIONSHIPS snapshot (server/websocket_handlers/relationships_emit.py)
- Dedicated message type + payload (not piggybacked on StateDelta)
- RelationshipsMessage with RelationshipsPayload (list of RelationshipEntry)
- Invoked from websocket_session_handler.py with emit_fn=_emit_shared_world_frame (alongside location/tactical/magic emissions)
- Change-gated via signature (internal memoization, no-op on unchanged roster)

**Downstream Consumer:** 77-5 (UI panel, repos: ui, BLOCKED on this story)
- Will add QuestsPayload TS type mirroring this server shape
- Renders the quest/objective panel
- Wire shape must be clean and documented for UI integration

**OTEL Observability:**
- Per project CLAUDE.md, the projection touches quest/stakes subsystem
- Must emit/confirm watcher events so GM panel can verify projection fires (lie detector)
- Seed/tools already emit quest.* / stakes.set spans
- Determine whether projection-emit span is warranted vs. existing spans being sufficient

**Wiring Requirement (CLAUDE.md "Every Test Suite Needs a Wiring Test"):**
- Include behavioral integration test that drives a real turn through the handler
- Assert quests projection is actually emitted to socket (not just serializer unit test)

## Sm Assessment

77-8 was created today as the blocking prerequisite TEA surfaced during 77-5's RED phase. ADR-137's server lane (77-1…77-4) all landed and *store/maintain* the quest spine, but **none of them projected it outbound to the client** — the RELATIONSHIPS-snapshot analog was simply never built. 77-5 (the UI panel) is parked in `backlog`, blocked on this story; resume it once 77-8 merges and the wire shape is confirmed.

**Scope for TEA (RED phase):**
- This is a server-side projection story. Build the QUESTS projection mirroring the ADR-136 `relationships_emit.py` pattern (dedicated message/payload carrying quest_log + quest_anchors + active_stakes together) — do NOT piggyback the thin legacy `StateDelta.quests: dict[str,str]` field. The ACs (in epic-77.yaml / `pf sprint story show 77-8`) are the test rubric.
- **Mandatory wiring test:** drive a real turn through the websocket handler and assert the projection is actually emitted to the socket — not just a serializer unit test. (CLAUDE.md "Verify Wiring, Not Just Existence" / "Every Test Suite Needs a Wiring Test".)
- **OTEL:** per the project principle, confirm whether a projection-emit span is warranted (the seed/tools already emit `quest.*`/`stakes.set`) so the GM panel can verify the projection fires. If you decide existing spans suffice, say so explicitly — don't silently skip.
- **No Silent Fallbacks:** if the spine is empty, project a clean empty-but-valid payload, and preserve the `test_wire_parity` omission contract for genuinely-empty fields (AC5). No null soup, no swallowed states.

**Audience anchor:** this is the wire half of the player-facing mechanical legibility Sebastien & Jade want (77-5 renders it). The projection shape must be clean enough for the UI to mirror into a `QuestsPayload` TS type.

**Repo:** sidequest-server only. Branch `feat/77-8-quests-spine-client-projection` on base `develop` (subrepo convention).

Routing to Amos (TEA) for the RED phase.

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Status:** RED (failing — verified via testing-runner, 100% missing-implementation failures, zero test-code defects)

**Test Files (sidequest-server):**
- `tests/protocol/test_quests_message.py` — `MessageType.QUESTS`, the `QuestLogEntry`/`QuestAnchorEntry`/`QuestsPayload` shape, the `QuestsMessage` envelope, empty-payload validity, and wire-parity round-trip (AC1, AC3, AC5).
- `tests/server/test_quests_emit.py` — `build_quests_payload` builder (seeded/empty/unowned-anchor) + the change-gated `_maybe_emit_quests` emitter (sends when populated, skips when unchanged, re-fires on stakes/quest/status change, skips empty spine) + `_quests_signature` change-gate (AC1, AC2, AC3).
- `tests/server/test_quests_emit_wiring.py` — `quests.emitted` OTEL span fires on emit, emitter imported into `websocket_session_handler` (reachable from production path), and the transient-replay invariant (QUESTS absent from `_KIND_TO_MESSAGE_CLS` and `_REPLAY_SKIP_KINDS`) (AC4, OTEL principle).

**Tests Written:** 19 tests covering 5 ACs.

**Contract handed to Dev (the missing symbols to implement, mirroring the ADR-136 RELATIONSHIPS pattern):**
1. `sidequest/protocol/enums.py` — `MessageType.QUESTS = "QUESTS"`.
2. `sidequest/protocol/models.py` — `QuestLogEntry(quest_id, title, objective, status, anchor_id|None)`, `QuestAnchorEntry(anchor_id, quest_id|None, [resolution optional])`, `QuestsPayload(quest_log=[], quest_anchors=[], active_stakes="")`. Use `extra="forbid"` like `RelationshipsPayload`; wire defaults must obey the parity-omission contract.
3. `sidequest/protocol/messages.py` — `QuestsMessage(type=QUESTS, payload: QuestsPayload, player_id="")`.
4. `sidequest/game/projection/quests.py` — `build_quests_payload(snapshot) -> QuestsPayload`. Associate each anchor to its owning quest by matching `QuestEntry.anchor_id`; unowned anchors keep `quest_id=None` (surfaced, not dropped — No Silent Fallbacks).
5. `sidequest/server/websocket_handlers/quests_emit.py` — `_quests_signature(snapshot)` + `_maybe_emit_quests(handler, *, snapshot, emit_fn)`, change-gated on a `_last_quests_sig` handler attr, skip on empty spine, emit `quests.emitted` span. Mirror `relationships_emit.py` exactly.
6. `sidequest/telemetry/spans/` — a `quests.emitted` span + `SpanRoute` (component "quests", like `relationships.emitted`) so it lights the GM panel.
7. Wire `_maybe_emit_quests` into `websocket_session_handler.py` next to `_maybe_emit_relationships` (~line 2103) via `_emit_shared_world_frame`. Keep QUESTS out of the replay structures (transient, like LOCATION_DESCRIPTION/RELATIONSHIPS).

### Rule Coverage

Applicable rules from `.pennyfarthing/gates/lang-review/python.md` (this is a pure pydantic-projection + emit feature; path/resource/deserialization rules are N/A):

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 No silent exception swallowing (≈ No Silent Fallbacks) | `test_build_payload_empty_spine_is_well_formed`, `test_build_payload_unowned_anchor_keeps_anchor_quest_id_none`, `test_emit_skipped_when_spine_empty` (empty/edge states surface explicitly, never throw or silently drop) | failing |
| #3 Type annotations at boundaries | Enforced by the typed pydantic payload contract in `test_quests_message.py` (`QuestsPayload`/`QuestLogEntry`/`QuestAnchorEntry` fully typed) | failing |
| #6 Test quality (meaningful assertions) | Self-checked: every test asserts a concrete value (==, is, in, len) — no `assert True`, no truthy-only checks, no always-None asserts | n/a (self-check) |

**Rules checked:** 3 of 3 applicable lang-review rules have coverage (the rest — #2 mutable defaults, #5 path, #7 resource, #8 deserialization — are not applicable to this feature surface).
**Self-check:** 0 vacuous tests found.

**Handoff:** To Dev (Naomi Nagata) for GREEN implementation.

### TEA Rework — Round 1 (post-Reviewer REJECT)

The Reviewer confirmed 3 HIGH findings (2 signature correctness bugs + 1 AC4 wiring-test weakness). I added failing/guarding tests that pin them down:

**New failing tests (must go GREEN by Dev's fix):**
- `test_quests_emit.py::test_signature_changes_with_objective_update` — objective-only change must alter the signature (objective was omitted). FAILS now.
- `test_quests_emit.py::test_signature_no_collision_on_free_text_delimiters` — two distinct spines (`status="active:done"`/`anchor="x"` vs `status="active"`/`anchor="done:x"`) must not collide. FAILS now (`:`-join collision).
- `test_quests_emit.py::test_emit_refires_when_only_objective_changes` — end-to-end: an objective edit must re-broadcast. FAILS now (emitter skips).

**New hardening guards (PASS now — prevent regression, satisfy AC4 properly):**
- `test_quests_emit_wiring.py::test_emitter_is_called_from_narration_turn` — **reflection call-graph check** over `WebSocketSessionHandler._execute_narration_turn.__code__` (recursing nested code objects) proving `_maybe_emit_quests` is actually *called*, not just imported. This closes the AC4 gap the Reviewer flagged. NOTE: the codebase has **no full-turn handler harness** for transient shared-world-frame emits — even `test_location_description_emit.py` and `test_tactical_grid_runtime_wiring.py` invoke the emitter directly with a fixture, and the RELATIONSHIPS sibling's wiring test does the same. So a literal "drive a full turn" test is not the established pattern; the reflection call-graph check is the strongest refactor-stable, reflection-based (not source-grep) wiring assertion available here, and it genuinely fails if the call site is deleted.
- `test_quests_emit_wiring.py::test_quests_message_is_in_game_message_union` — positive routability (QuestsMessage ∈ GameMessage union).
- `test_quests_emit_wiring.py::test_emit_fires_on_first_call_for_fresh_handler` — reconnect first-emit.

**Recommended fix for Dev (resolves both signature HIGHs at once):** derive `_quests_signature` from `build_quests_payload(snapshot).model_dump_json()` instead of delimiter-joining free text — this includes `objective` and eliminates delimiter ambiguity in one move. The medium/low items (setattr-before-emit ordering, `getattr`/`isinstance` guard for dict-valued quest_log, empty-skip debug log, justification comment) are optional-but-recommended while in the file; the objective-firewall is a doc-only item (see Reviewer Delivery Finding).

**Status:** RED (rework) — verified via testing-runner: 3 bug-targeting tests fail on their own assertions, guards + 14 pre-existing tests pass, no test-code defects.
**Handoff:** To Dev (Naomi Nagata) for the fix (GREEN).

## Delivery Findings

No upstream findings.

### TEA (test design)
- No upstream findings during test design. The blocking dependency that spawned this story (the missing client projection) is the story's own subject; nothing further surfaced. The design choices left to Dev (whether `QuestAnchorEntry` carries a resolved beat/location string in v1, and the exact span-constant module placement) are noted in the contract above, not findings.
- (Rework round 1) No new upstream findings. The Reviewer's HIGH findings were correctness defects in this story's own code (now covered by failing tests), not upstream gaps.

### Dev (implementation)
- No upstream findings during implementation. The contract TEA handed down matched the codebase exactly; the RELATIONSHIPS sibling gave a 1:1 template for every layer (payload, message, union, builder, change-gated emitter, span route, handler wiring). No surprises, no spec conflicts.
- **Improvement** (non-blocking): The `setattr(sig)`-before-`emit_fn` ordering bug the Reviewer flagged also lives in the `relationships_emit` sibling (same systemic pattern). I fixed it in this story's `quests_emit.py`; the sibling is out of scope here. Affects `sidequest/server/websocket_handlers/relationships_emit.py` (move the sig commit after `emit_fn` succeeds, mirroring the 77-8 fix). *Found by Dev during rework round 1 — corroborates the Reviewer's own Delivery Finding above.*

### Reviewer (code review)
- **Improvement** (non-blocking): The `objective` field is projected verbatim to all clients with no content firewall, unlike the RELATIONSHIPS claims-only filter. A quest objective is player-facing by design (it is the panel's purpose), so no runtime filter is warranted — but the player-facing contract is undocumented. Affects `sidequest/game/projection/quests.py` and ADR-137 (document that quest `objective`/`active_stakes` are definitionally player-visible; if any genre ever needs GM-secret quest notes, that would require a separate `gm_note` field stripped at projection, analogous to `claims_to_party()`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The `setattr(sig)`-before-`emit_fn` ordering that risks a stale-client-on-broadcast-failure is shared with the `relationships_emit` sibling — a systemic pattern worth fixing in both, not just here. Affects `sidequest/server/websocket_handlers/relationships_emit.py` (same ordering). *Found by Reviewer during code review.*

#### Reviewer (code review — round 2, post-rework)
- **Improvement** (non-blocking): `relationships_emit.py` still commits its signature *before* `emit_fn` — `quests_emit.py` now does it correctly (after). Worth porting the 77-8 ordering fix to the sibling. Affects `sidequest/server/websocket_handlers/relationships_emit.py:81` (move `setattr(_SIG_ATTR)` after `emit_fn`). *Found by Reviewer (corroborates Dev + silent-failure-hunter).*
- **Improvement** (non-blocking): `_quests_signature` is now production-dead — `_maybe_emit_quests` inlines `payload.model_dump_json()`; only the unit signature tests call the helper. Consolidate to a single source of truth (either have the emitter call `_quests_signature`, accepting one extra build, or drop the helper and assert the signature via the emitter). Affects `sidequest/server/websocket_handlers/quests_emit.py:29`. *Found by Reviewer + silent-failure-hunter.*
- **Improvement** (non-blocking): The change signature derives from `quest_log.items()` in dict-insertion order; a future `WorldStatePatch` that replaces `quest_log` with identical content in a different key order would spuriously re-broadcast (benign over-fire — never a missed update). Zero-cost hardening: iterate `sorted(quest_log.items())` in `build_quests_payload`. No live trigger today (`apply_world_patch` forbids `/quest_log`). Affects `sidequest/game/projection/quests.py:43`. *Found by Reviewer (edge-hunter).*
- **Improvement** (non-blocking): `objective`/`active_stakes` projected with no perception firewall is **safe** (global spine, no per-player secrets — security confirmed) but the player-facing contract is undocumented. Add a one-line comment on `QuestLogEntry`/`QuestsPayload` noting no filter is applied and that any future GM-secret field must NOT be projected here (contrast `claims_to_party`). Affects `sidequest/protocol/models.py` + ADR-137. *Found by Reviewer (security).*
- **Gap** (non-blocking): Test coverage gaps for a follow-up — duplicate-`anchor_id` (first-writer-wins) projection behavior, and a `GameMessage.model_validate()` discriminated-union round-trip parse for `QuestsMessage` (membership is tested; parse-back is not). Affects `tests/server/test_quests_emit.py`, `tests/protocol/test_quests_message.py`. *Found by Reviewer (test-analyzer).*

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 20/20 new GREEN; 19/19 regression guards (wire-parity, span-routing-completeness, relationships-emit) still GREEN.
**Branch:** `feat/77-8-quests-spine-client-projection` (pushed to origin).

**Files Changed (sidequest-server):**
- `sidequest/protocol/enums.py` — `MessageType.QUESTS`.
- `sidequest/protocol/models.py` — `QuestLogEntry`, `QuestAnchorEntry`, `QuestsPayload` (`extra="forbid"`, empty-but-valid defaults), mirroring `RelationshipsPayload`.
- `sidequest/protocol/messages.py` — `QuestsMessage` (type=QUESTS, payload, broadcast `player_id=""`); added to the `GameMessage` discriminated union; imported `QuestsPayload`.
- `sidequest/protocol/__init__.py` — exported `QuestsMessage`, `QuestsPayload`, `QuestLogEntry`, `QuestAnchorEntry`.
- `sidequest/game/projection/quests.py` (new) — `build_quests_payload(snapshot)`: projects the stored spine, associates anchors to owning quests via `QuestEntry.anchor_id`, keeps unowned anchors with `quest_id=None`. Empty spine → clean empty payload.
- `sidequest/server/websocket_handlers/quests_emit.py` (new) — `_quests_signature` + change-gated `_maybe_emit_quests` (skips empty spine + unchanged signature), mirrors `relationships_emit.py`. Emits the `quests.emitted` span.
- `sidequest/telemetry/spans/quests.py` (new) + `spans/__init__.py` — `SPAN_QUESTS_EMITTED = "quests.emitted"`, routed (`component="quests"`, event_type `state_transition`) so it lights the GM panel.
- `sidequest/server/websocket_session_handler.py` — imported and called `_maybe_emit_quests` in the NARRATION_END shared-world-frame path, immediately after `_maybe_emit_relationships`, via `_emit_shared_world_frame` (transient broadcast, never event-sourced).

**AC coverage:** AC1 (rich payload on the wire) ✓ · AC2 (reactive on stakes/quest/status change, change-gated) ✓ · AC3 (empty/seeded well-formed, no null soup) ✓ · AC4 (wired into production emit path + transient-replay invariant + `quests.emitted` span) ✓ · AC5 (wire-parity + relationships regression guards pass) ✓.

**OTEL decision:** Added a dedicated `quests.emitted` routed span (not relying on the existing `quest.*`/`stakes.set` mutation spans) — those prove the spine *changed*, this proves the engine *projected it to the player*, which is the new subsystem this story introduces. The GM panel can now distinguish "spine mutated" from "spine reached the client."

**Note for Reviewer / 77-5:** `QuestAnchorEntry.resolution` ships as an always-`None` optional in v1 (the bare `quest_anchors: list[str]` carries no beat/location; resolving would couple the projection to `orbital/course.py`). Per TEA's logged deviation, this is intentional latitude from AC1's "where present." 77-5's TS mirror should treat it as optional. Not a stub — it's a populated-when-available field with a documented v1 absence.

**Handoff:** To Reviewer (Chrisjen Avasarala) for code review.

### Dev Assessment — Rework Round 1 (post-Reviewer REJECT)

**Implementation Complete:** Yes
**Files Changed (sidequest-server):**
- `sidequest/server/websocket_handlers/quests_emit.py` — `_quests_signature` now derives from `build_quests_payload(snapshot).model_dump_json()` (was a hand-joined free-text string). Emitter builds the payload once, derives the sig from it, and commits the sig *after* `emit_fn` succeeds.

**The convergent fix (TEA's recommendation, applied):** Deriving the change signature from the projected payload's JSON resolves both Reviewer signature HIGHs at once:
- **HIGH #1 (objective omitted from signature → AC2 violation):** `objective` is in the payload, so it's now in the signature; an objective-only `record_quest` update re-broadcasts.
- **HIGH #2 (free-text delimiter collision):** JSON-escapes field contents, so narrator text containing `:`/`,`/`|`/`#` can never collapse two distinct spines onto one signature.

**HIGH #3 (AC4 wiring test):** Addressed in TEA's RED rework, not Dev's — TEA added `test_emitter_is_called_from_narration_turn` (reflection call-graph over `_execute_narration_turn.__code__`, recursing nested code objects) which proves `_maybe_emit_quests` is *called*, not just imported, and fails if the call site is deleted. Per the server CLAUDE.md "No Source-Text Wiring Tests" rule, this reflection-based call-graph assertion is the sanctioned wiring proof for a transient shared-world-frame emit (the codebase has no full-turn harness for these; the LOCATION_DESCRIPTION and RELATIONSHIPS siblings invoke the emitter directly with a fixture too). The production call site in `websocket_session_handler.py` is unchanged and intact.

**Plus (MEDIUM, flagged-fix-while-in-file):** moved the `setattr(sig)` commit after the `emit_fn` broadcast so a failed send retries next turn rather than skipping a never-delivered frame.

**Tests:** 26/26 story+wiring+protocol GREEN (the 3 prior RED — `test_signature_changes_with_objective_update`, `test_signature_no_collision_on_free_text_delimiters`, `test_emit_refires_when_only_objective_changes` — now pass); 17/17 wire-parity + relationships-sibling regression guards still GREEN. `ruff check` + `pyright` clean on both changed files.
**Branch:** `feat/77-8-quests-spine-client-projection` (pushed — commit `b15099e`).

**Out of scope (surfaced, not done):** the same `setattr`-before-`emit` ordering bug in the `relationships_emit` sibling — logged in Delivery Findings for a follow-up.

**Handoff:** To Reviewer (Chrisjen Avasarala) for re-review.

## Subagent Results — Round 1 (REJECTED, superseded)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (tests GREEN 20/20, lint clean, 0 smells) | 0 blocking; 1 mechanical observation (objective absent from change signature) | observation → confirmed (corroborates [TYPE/HIGH] below) |
| 2 | reviewer-edge-hunter | Yes | findings | 6 | confirmed 2 high + 1 medium, deferred 3 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 0 blocking, dismissed 0, deferred 3 (all medium/low, sibling-parity) |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 2 (1 high objective-test, 1 high AC4-wiring), deferred 3 |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 2 | confirmed 1 high (objective-signature, corroborates), deferred 1 medium (objective firewall) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled)
**Total findings:** 3 confirmed HIGH (blocking), 4 confirmed medium/low (non-blocking), 6 deferred to rework

**Cross-corroboration:** The objective-omitted-from-signature defect was independently flagged HIGH by **three** specialists (edge-hunter, test-analyzer, security) and noted mechanically by preflight. That is not noise — it is a confirmed correctness bug.

## Prior Review — Round 1 (REJECTED, superseded by the Reviewer Assessment below)

**Verdict:** REJECTED

The implementation is structurally clean and faithfully mirrors the ADR-136 RELATIONSHIPS sibling at every layer — protocol models, discriminated-union membership, the projection builder, the routed `quests.emitted` span, and the handler wiring are all correct, and 20/20 tests are green. But the change-gate signature has a confirmed correctness defect that defeats AC2, and the AC4 wiring test does not test what AC4 requires. Both are squarely in scope and cheaply fixable.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | `_quests_signature` omits `entry.objective`. An objective-only `record_quest` update (title/status/anchor unchanged) produces an identical signature → the emitter skips → the client shows a **stale objective forever** until another field changes. Directly violates AC2 ("re-broadcasts when record_quest mutates the spine"); `objective` *is* in the wire payload. Confirmed HIGH by edge-hunter, test-analyzer, security; noted by preflight. | `sidequest/server/websocket_handlers/quests_emit.py:36` | Include `objective` in the change detection. **Recommended:** derive the signature from the structured payload (`build_quests_payload(snapshot).model_dump_json()`) so it tracks exactly what goes on the wire — this fixes the next finding too. |
| [HIGH] | The signature is hand-joined from **free-text** fields with `:` / `,` / `\|` / `#` delimiters. Narrator-authored content containing a delimiter (e.g. `status="complete: betrayed"`, or an `anchor_id`/`title` with a comma) ambiguates the segment boundaries, so two distinct spines can produce the same signature → a genuine spine change is suppressed and never reaches the client. (RELATIONSHIPS is immune because it only joins integers; this code joins LLM free text.) Confirmed HIGH by edge-hunter. | `sidequest/server/websocket_handlers/quests_emit.py:36-37` | Stop delimiter-joining free text. Hash/compare a structured representation (`model_dump_json()` of the projected payload, or per-field `repr`) — the same fix as above resolves both. |
| [HIGH] | AC4 requires "drive a turn through the handler and assert the projection is emitted to the socket." The wiring test only proves `_maybe_emit_quests` is **imported** into the handler module (reflection check) and separately calls the emitter **directly** (span test). Neither drives the production NARRATION_END path, so neither would catch a deleted/dead call site — exactly the failure mode this whole story exists to prevent. Confirmed HIGH by test-analyzer. | `tests/server/test_quests_emit_wiring.py:76` | Add a fixture-driven behavior test that fires the shared-world-frame path through the real handler and asserts a `QUESTS` message reaches the outbound/socket (canonical shape: `tests/server/test_location_description_emit.py`). |
| [MEDIUM] | `setattr(handler, _SIG_ATTR, sig)` commits **before** `emit_fn(...)`. If the broadcast raises, the sig is advanced but nothing was delivered → next turn skips, client stuck stale. Shared with the `relationships_emit` sibling (systemic), but present in new code. | `quests_emit.py:87` | Set the sig *after* `emit_fn` succeeds (or clear on failure). |
| [MEDIUM] | `build_quests_payload` does attribute access (`entry.title`, …) on `quest_log` values whose container is typed `Any`. A dict-valued entry from a post-load raw mutation raises `AttributeError` rather than projecting gracefully. | `quests.py:41` | `isinstance`-guard or `getattr` the entry fields. |
| [MEDIUM] | `objective` is projected verbatim with no content firewall analogous to the RELATIONSHIPS claims-only filter. **My judgment:** a quest objective is *definitionally* player-facing (it is "what am I doing" — the panel's entire purpose), unlike NPC beliefs which carry secrets, so no runtime filter is needed — but the intent is undocumented. Non-blocking; see Delivery Findings. | `quests.py` / `models.py` | Document the player-facing contract (projection module + ADR-137). No code change if intent confirmed. |
| [LOW] | Duplicate `anchor_id` values are not deduped in the projection. | `quests.py:58` | Dedup before building anchor entries (optional). |
| [LOW] | Empty-spine skip has no debug log / skip-span; a 77-1 seed regression would leave a blank panel with no telemetry. | `quests_emit.py:41` | Add a `logger.debug` on the empty-skip path. |
| [LOW] | `getattr(...) or {}` guards lack the inline justification comment the `relationships_emit` sibling carries. | `quests.py:37` | Add the one-line justification comment. |

**Data flow traced:** `record_quest`/`set_stakes`/seed → `GameSnapshot.{quest_log,quest_anchors,active_stakes}` → `_maybe_emit_quests` (NARRATION_END) → `build_quests_payload` → `QuestsMessage` → `_emit_shared_world_frame` broadcast → client. The pipeline is correctly wired end-to-end; the defect is solely in the change-gate's *detection* of objective/free-text mutations (it under-fires), not in the payload content (which is correct when it does fire).

**Pattern observed:** Faithful RELATIONSHIPS mirror (`quests_emit.py` ≅ `relationships_emit.py`, `QuestsPayload` ≅ `RelationshipsPayload`). Good. The one place the mirror is unsafe is the signature: the sibling hashes integers, this code hashes free text — the pattern was copied without accounting for the field-type difference.

**The fix is small and convergent:** replacing the hand-rolled signature with `build_quests_payload(snapshot).model_dump_json()` resolves both HIGH signature findings at once and makes the change-gate track the wire payload exactly. Plus a handler-path wiring test for AC4. Testable findings → back to TEA for RED rework (objective-change test, delimiter-collision test, handler-path wiring test), then Dev.

**Handoff:** Back to TEA (Amos) for rework — RED phase.

## Subagent Results

Round 2 (re-review of the rework commit `b15099e`). Enabled subagents re-run on the full feature diff with focus on the change-signature rework.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (tests GREEN 43/43, ruff clean, pyright clean, 0 smells) | 0 blocking; 1 observation (payload built every non-empty turn — conscious tradeoff) | observation noted, accepted (tiny spine, correct) |
| 2 | reviewer-edge-hunter | Yes | findings | 3 | confirmed both prior HIGH **closed**; 1 medium + 2 low non-blocking (quest_log order, span-before-emit, resolution-mutation) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | 0 blocking; 1 low (empty-skip telemetry), 1 low (`_quests_signature` prod-dead), 1 medium **out-of-scope** (relationships sibling sig-order) |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | 0 blocking; 2 medium (AC4 not full-turn, dup-anchor untested), 3 low/medium coverage gaps — all non-blocking |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 3 | 0 blocking; objective-no-firewall confirmed **SAFE** (undocumented), 2 low (getattr guards, status default); sig confirmed never logged/wired |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled)
**Total findings:** 0 confirmed HIGH/CRITICAL (the 3 prior HIGH are RESOLVED), 0 blocking, ~11 MEDIUM/LOW non-blocking (documentation, test-strengthening, quality nits, 1 out-of-scope sibling)

**Cross-corroboration:** Both prior HIGH signature defects are independently confirmed **closed** by edge-hunter (field enumeration + JSON-escaping verification) and preflight (the 3 target tests pass). No specialist raised a new HIGH.

## Reviewer Assessment

**Verdict:** APPROVED

The rework is the convergent fix I asked for in Round 1 and it lands cleanly. `_quests_signature` now derives from `build_quests_payload(snapshot).model_dump_json()`, which (a) folds `objective` into change detection and (b) JSON-escapes every field so narrator free text can no longer collapse two distinct spines onto one signature. The emitter builds the payload once and commits the signature only after `emit_fn` succeeds. **43/43 tests green, ruff + pyright clean.** All three Round-1 HIGH blockers are resolved; everything the specialists surfaced this round is MEDIUM/LOW and non-blocking.

**Round-1 HIGH findings — disposition:**
1. **[EDGE][SEC] objective omitted from signature → AC2 violation** → **RESOLVED.** `model_dump_json()` of the projected payload includes `objective` (field-enumeration-confirmed by edge-hunter); `test_signature_changes_with_objective_update` and the end-to-end `test_emit_refires_when_only_objective_changes` both pass.
2. **[EDGE] free-text delimiter collision** → **RESOLVED.** JSON encoding structurally escapes `:`/`,`/`|`/`#`/`"`/`\n`; edge-hunter verified collision is now impossible; `test_signature_no_collision_on_free_text_delimiters` passes.
3. **[TEST] AC4 wiring test didn't catch a deleted call site** → **RESOLVED.** `test_emitter_is_called_from_narration_turn` introspects `_execute_narration_turn.__code__` (recursing nested code objects) and fails if the call site is removed — the sanctioned reflection exception per CLAUDE.md "No Source-Text Wiring Tests." I independently verified the production call site: `websocket_session_handler.py:2118`, an unconditional `_maybe_emit_quests(self, snapshot=snapshot, emit_fn=_emit_shared_world_frame)` inside `_execute_narration_turn` (def :726), beside `_maybe_emit_relationships` (:2106).

**Five+ observations (this round):**
- [VERIFIED] Both prior signature HIGHs closed — evidence: `quests_emit.py:38` returns `build_quests_payload(snapshot).model_dump_json()`; all five `QuestLogEntry` fields appear in the JSON (edge-hunter field enumeration); collision test green.
- [VERIFIED] Production wiring intact — evidence: `websocket_session_handler.py:2118` unconditional call inside `_execute_narration_turn`; `quests.emitted` span test green; replay invariant (QUESTS ∉ `_KIND_TO_MESSAGE_CLS`/`_REPLAY_SKIP_KINDS`) green.
- [VERIFIED] Emit-ordering retry correct — evidence: `quests_emit.py:93-94` `emit_fn` then `setattr`; edge-hunter confirmed no double-emit (sig guard at :67) and no infinite retry (exceptions propagate, not swallowed).
- [VERIFIED] No missed-broadcast risk — evidence: any wire-field change changes the JSON → sig changes → re-fires. The only ordering nuance (quest_log dict order) can produce a *spurious extra* identical frame, never a *suppressed* change. Benign.
- [SEC] objective-no-firewall is **safe but undocumented** — `quest_log`/`quest_anchors`/`active_stakes` are global `GameSnapshot` fields with no per-player secret analogous to `Npc.belief_state`; broadcasting unfiltered is correct. Add a one-line contract comment (non-blocking, Delivery Finding).
- [SILENT] `_quests_signature` is now production-dead (emitter inlines the JSON) but still consumed by the unit signature tests; the inline prod path is independently covered by the end-to-end `test_emit_*` behavior tests, so no divergence can hide. LOW maintainability (Delivery Finding).
- [EDGE] `build_quests_payload` iterates `quest_log.items()` in dict order; a future `WorldStatePatch`-driven reorder of identical content would spuriously re-broadcast. No live trigger today (`apply_world_patch` forbids `/quest_log`); zero-cost future hardening = `sorted(quest_log.items())`. LOW (Delivery Finding).
- [TEST] AC4 guard is a code-object reference check, not a literal full-turn drive — but no transient-emit sibling (location_description/relationships/tactical) has a full-turn harness; all use direct fixture invocation, which 77-8 also does (six `test_emit_*` behavior tests). Accept TEA's logged deviation. MEDIUM, non-blocking.
- [TEST] duplicate-`anchor_id` (first-writer-wins) and `GameMessage` round-trip parse are untested coverage gaps; union *membership* is tested. MEDIUM/LOW, non-blocking (Delivery Findings).

**Dispatch tag coverage:** [EDGE] quest_log order / span-before-emit / resolution-mutation — all LOW/MEDIUM non-blocking. [SILENT] empty-skip telemetry + prod-dead `_quests_signature` — LOW. [TEST] AC4-full-turn / dup-anchor / round-trip-parse — MEDIUM/LOW non-blocking. [SEC] objective-firewall safe-but-undocumented — non-blocking; sig never logged/wired (clean). [DOC] reviewer-comment-analyzer **disabled** — I spot-checked docstrings myself: the module/function docstrings are accurate and describe the new JSON-signature behavior. [TYPE] reviewer-type-design **disabled** — payload is fully-typed pydantic with `extra="forbid"`; `snapshot: Any` is the established sibling convention (guarded by getattr). [SIMPLE] reviewer-simplifier **disabled** — one minor redundancy (`_quests_signature` vs inline), tracked as a Delivery Finding, not worth a block. [RULE] reviewer-rule-checker **disabled** — I ran the lang-review checklist myself; see Rule Compliance below.

### Rule Compliance

Lang-review checklist (`.pennyfarthing/gates/lang-review/python.md`) applied to the two changed files (`quests_emit.py`, `quests.py`) — pure pydantic projection + emit; path/resource/deserialization rules N/A:

- **#1 Silent exception swallowing** — COMPLIANT. No `try/except`, no bare except, no `suppress()` in either file. The empty-spine early-return is a documented intentional no-op (mirrors `relationships_emit`), not a swallowed error.
- **#2 Mutable default arguments** — COMPLIANT. No mutable defaults; `getattr(..., {})/[]/("")` produce fresh literals per call, not shared defaults.
- **#3 Type annotations at boundaries** — COMPLIANT. `_quests_signature(snapshot: Any) -> str`, `_maybe_emit_quests(handler, *, snapshot, emit_fn) -> None`, `build_quests_payload(snapshot: Any) -> QuestsPayload` all annotated. `Any` on `snapshot` matches the sibling convention (duck-typed snapshot); acceptable. NOTE (LOW): no inline comment justifying `Any`/getattr — security + I both flagged this as a doc nicety.
- **#4 Logging coverage AND correctness** — COMPLIANT. `logger.info("quests.emitted quests=%d anchors=%d", ...)` uses lazy `%s`-style args, logs counts only (no PII/secrets — security confirmed the sig/free-text is never logged). Happy-path info log is appropriate; no error path exists in the emit (exceptions propagate).
- **#6 Test quality** — COMPLIANT. The 3 rework tests assert concrete inequality/equality with explanatory messages; no `assert True`, no truthy-only checks. Coverage gaps (dup-anchor, round-trip parse) are *missing* tests, not vacuous ones — non-blocking.
- **#2/#5/#7/#8 (mutable class vars / path / resource / deserialization)** — N/A to this feature surface.

**Data flow traced:** narrator `record_quest`/`set_stakes` (pydantic-bounded args) → `GameSnapshot.{quest_log,quest_anchors,active_stakes}` → `_execute_narration_turn` → `_maybe_emit_quests` → `build_quests_payload` → `model_dump_json()` (sig + payload) → `QuestsMessage` → `_emit_shared_world_frame` broadcast (`player_id=""`) → all clients. Safe: global spine, no per-player secrets, JSON-encoded free text (XSS is the client renderer's boundary).

**Pattern observed:** Faithful RELATIONSHIPS mirror, now *safer* than the sibling on two axes — the signature tracks the wire payload exactly (sibling hashes a hand-rolled tuple) and the sig commits post-broadcast (sibling commits pre-broadcast). The rework turned the Round-1 weakness (copied integer-hash pattern onto free text) into a strength.

### Devil's Advocate

Let me try to break this. **Missed broadcast (the dangerous class):** could a real spine change ever be suppressed? The signature is `model_dump_json()` of the projected payload — every wire field feeds it, so any field mutation changes the string and re-fires. The only way to under-fire is two *different* logical spines producing *identical* JSON; since the JSON is injective over distinct (field-value, key-order) tuples and every quest carries a required non-default `quest_id`, two distinct spines cannot serialize identically. Under-fire is impossible. **Over-fire:** dict insertion-order churn re-broadcasts identical data — wasteful but harmless (client re-renders the same panel). **Broadcast failure mid-turn:** `emit_fn` raises → sig uncommitted → retry next turn; edge-hunter confirmed no double-delivery and no infinite loop. The one cosmetic wart is the OTEL span firing *before* `emit_fn`, so a failed delivery + retry shows two `quests.emitted` spans — a GM-panel could misread that as two changes. That is an observability nuance on a rare failure path, not a player-facing bug; LOW. **Malicious/garbage narrator content:** `objective`/`status`/`active_stakes` are LLM free text, length-bounded at the args schema (500/1024), JSON-escaped on serialization; no server-side injection surface — the client owns render-escaping, the standard JSON-API boundary. **Confused future developer:** the real trap is someone adding a GM-secret field to `QuestEntry` and not realizing the whole entry broadcasts to every seat — which is exactly why security and I want the player-facing contract documented (non-blocking follow-up). **Stressed state:** a structurally malformed snapshot (missing the three fields entirely) is silently treated as empty by the getattr guards; in production `GameSnapshot` guarantees the fields via `default_factory`, so this only bites a malformed test double — but it is undocumented. **Test theater:** the AC4 guard proves *reference*, not *invocation on a live path* — but the actual call site is unconditional (I read it), and the six fixture-driven `test_emit_*` tests prove the emitter's real behavior. None of these rise above LOW/MEDIUM. The code does what it claims; the holes are documentation and test-strengthening, not broken behavior. Verdict stands: APPROVED.

**Handoff:** To SM (Camina Drummer) for finish-story.

## Design Deviations

### TEA (test design)
- **Anchor beat/location resolution deferred as optional, not asserted in v1.**
  - Spec source: context-story-77-8.md, AC1 ("quest_anchors (anchor id + owning quest + beat/location resolution where present)")
  - Spec text: "beat/location resolution where present"
  - Implementation: Tests assert `anchor_id` + owning `quest_id` association, and treat any beat/location `resolution` as an optional field (not asserted populated). The snapshot's `quest_anchors` is a bare `list[str]` of body ids; resolving them to a beat/location requires the orbital course lookup (`orbital/course.py`), which I did not force into the v1 wire contract.
  - Rationale: The AC's "where present" gives explicit latitude; forcing orbital coupling into the projection would over-specify the implementation during RED. Dev may add a populated `resolution` if cheap; the contract permits but does not require it.
  - Severity: minor
  - Forward impact: 77-5 (UI) should treat anchor resolution as optional in its `QuestsPayload` TS mirror.
- **Empty-spine behavior: emitter SKIPS rather than emitting an empty payload.**
  - Spec source: context-story-77-8.md, AC3 ("an unpopulated spine projects a clean empty payload")
  - Spec text: "unpopulated spine → clean empty-but-valid payload"
  - Implementation: The *builder* (`build_quests_payload`) returns a clean empty-but-valid payload on an empty spine (AC3 honored at the builder). The *emitter* (`_maybe_emit_quests`) SKIPS broadcasting a wholly-empty spine, mirroring `relationships_emit`'s "no NPCs → nothing" and preserving the wire-parity omission contract (AC5).
  - Rationale: Reconciles AC3 (builder robustness) with AC5 (omission contract) and the established RELATIONSHIPS sibling pattern + Cost-Scales-with-Drama. The 77-1 seed populates the spine at session start, so the skip only covers the brief pre-seed window.
  - Severity: minor
  - Forward impact: none — UI tab is data-gated and appears once the seed lands.

### Dev (implementation)
- No deviations from spec. The implementation matched the TEA test contract exactly, mirroring the RELATIONSHIPS sibling at every layer. The two design choices (optional anchor `resolution`; emitter skips an empty spine) are TEA's already-logged deviations above — I implemented them as the tests specified, not as new departures.

### Dev (implementation — rework round 1)
- **Adopted TEA's recommended convergent signature fix verbatim.** `_quests_signature` now returns `build_quests_payload(snapshot).model_dump_json()` instead of a hand-joined free-text string. Resolves both Reviewer signature HIGHs (objective inclusion + delimiter-collision) in one move. Not a deviation — this is exactly the fix TEA's rework contract recommended.
- **Emitter builds the payload once (efficiency refinement, beyond the failing tests).**
  - Spec source: TEA rework contract (session file, "Recommended fix for Dev")
  - Spec text: "derive `_quests_signature` from `build_quests_payload(snapshot).model_dump_json()`"
  - Implementation: `_quests_signature` does exactly that for standalone callers/tests; inside `_maybe_emit_quests` I build the payload once and compute `sig = payload.model_dump_json()` inline rather than calling `_quests_signature(snapshot)` (which would build a second time). Functionally identical signature.
  - Rationale: avoid double-building the payload per turn; the tested helper still exists and returns the same value.
  - Severity: minor
  - Forward impact: none — `_quests_signature` semantics unchanged; tests call it directly and pass.
- **Fixed the MEDIUM broadcast-ordering finding (beyond the 3 failing tests).**
  - Spec source: Reviewer Assessment, [MEDIUM] `quests_emit.py:87`
  - Spec text: "Set the sig *after* `emit_fn` succeeds (or clear on failure)."
  - Implementation: moved `setattr(handler, _SIG_ATTR, sig)` to *after* `emit_fn(msg, "QUESTS")`. A raising broadcast now leaves the sig unchanged so the next turn retries instead of skipping a never-delivered frame.
  - Rationale: addressing the flagged correctness finding while in the file avoids a second round-trip; no failing test required it, so logging as a deviation per "never assume simplification/scope-change is acceptable."
  - Severity: minor
  - Forward impact: the `relationships_emit` sibling carries the same ordering bug (Reviewer Delivery Finding) — left untouched here (out of this story's scope); see Delivery Findings.

### TEA (test design — rework round 1)
- **AC4 wiring proven via reflection call-graph rather than a full-turn handler test.**
  - Spec source: context-story-77-8.md, AC4 ("drive a turn through the handler and assert the quests projection is emitted to the socket")
  - Spec text: "drive a turn through the handler and assert the quests projection is emitted to the socket"
  - Implementation: The wiring is proven by introspecting `WebSocketSessionHandler._execute_narration_turn.__code__` (recursing nested code objects) and asserting `_maybe_emit_quests` is referenced/called — plus the OTEL span and direct-emit behavior tests. No test drives a full NARRATION_END turn end-to-end.
  - Rationale: The codebase has no full-turn harness for transient shared-world-frame emits; the canonical `test_location_description_emit.py`, `test_tactical_grid_runtime_wiring.py`, and the RELATIONSHIPS sibling all invoke the emitter directly with a fixture. The reflection call-graph check is the strongest refactor-stable, reflection-based (allowed per "No Source-Text Wiring Tests") assertion available, and it fails if the call site is deleted — which is the actual regression AC4 guards against.
  - Severity: minor
  - Forward impact: none — if a full-turn integration harness is later built, this can be upgraded to a literal turn-drive test.

### Reviewer (audit)
- **TEA deviation 1 (optional anchor `resolution`, not asserted in v1)** → ✓ ACCEPTED by Reviewer: AC1's "where present" gives explicit latitude; deferring orbital-course coupling is reasonable v1 scope and 77-5 was told to treat it as optional. Sound.
- **TEA deviation 2 (emitter SKIPS an empty spine rather than broadcasting an empty payload)** → ✓ ACCEPTED by Reviewer: consistent with the RELATIONSHIPS sibling and the wire-parity omission contract (AC5); the builder still returns a clean empty-but-valid payload satisfying AC3's builder-robustness requirement. The only residual concern (no telemetry on the skip path) is logged as a [LOW] finding, not a deviation reversal.
- **Dev "no deviations"** → ✓ ACCEPTED by Reviewer: confirmed — the implementation tracks TEA's contract; no undocumented departures found.
- **Undocumented deviation spotted by Reviewer:** The change-gate signature silently under-fires on `objective`-only and delimiter-bearing free-text mutations (see the two [HIGH] findings). This was not a *logged* deviation — it is an unintended correctness defect, captured in the Reviewer Assessment severity table and routed to rework, not stamped here.

### Reviewer (audit — round 2, post-rework)
- **Dev rework: adopted TEA's convergent signature fix verbatim** → ✓ ACCEPTED: this is the exact fix the Round-1 assessment recommended; edge-hunter confirmed it closes both HIGHs. Not a departure.
- **Dev rework: emitter builds the payload once (inline `payload.model_dump_json()` instead of calling `_quests_signature`)** → ✓ ACCEPTED: functionally identical signature, avoids a double build. Side effect — `_quests_signature` is now production-dead (only tests call it). I confirmed the inline prod path is independently covered by the end-to-end `test_emit_*` behavior tests, so no divergence can hide. Reasonable; consolidation tracked as a non-blocking Delivery Finding (LOW).
- **Dev rework: moved `setattr(sig)` after `emit_fn` (MEDIUM ordering fix)** → ✓ ACCEPTED: directly implements the Round-1 [MEDIUM] recommendation; edge-hunter confirmed correct retry semantics (no double-emit, no infinite loop). This makes `quests_emit` *safer* than the `relationships_emit` sibling, which still commits the sig pre-broadcast (out-of-scope sibling fix logged in Delivery Findings).
- **TEA rework: AC4 proven via reflection call-graph over `_execute_narration_turn.__code__` rather than a full-turn drive** → ✓ ACCEPTED: this is the sanctioned reflection exception (CLAUDE.md "No Source-Text Wiring Tests"), it genuinely fails on a deleted call site (the Round-1 HIGH's exact regression), and no transient-emit sibling in the codebase has a full-turn harness — all use direct fixture invocation, which 77-8 also does via six `test_emit_*` tests. The residual "code-object reference is not a literal full-turn behavior proof" gap is theoretical (the real call site is unconditional, verified at `websocket_session_handler.py:2118`) and is recorded as a non-blocking [TEST/MEDIUM] Delivery Finding for if a full-turn harness is ever built. Sound v1 scope.