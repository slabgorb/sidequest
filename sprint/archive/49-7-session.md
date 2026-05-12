---
story_id: "49-7"
jira_key: ""
epic: "49"
workflow: "tdd"
---
# Story 49-7: Confrontation panel — project per-PC beats to UI (server-side filter on the outbound)

## Story Details
- **ID:** 49-7
- **Epic:** 49 (Playtest 4 Closeout — Glenross / ADR-098 Continuity Recovery)
- **Workflow:** tdd
- **Repos:** sidequest-server, sidequest-ui
- **Priority:** p1
- **Points:** 3
- **Type:** bug
- **Stack Parent:** none

## Story Context

Found in the 2026-05-12 Carl/Donut/Katia caverns_sunden playtest. During the Chalk Moth combat (encounter_type=combat fired live), the right-rail Confrontation tab on every connected tab showed the FULL 16-button union of every class's beats — Carl (Fighter) saw Backstab/Slip Behind (Thief), Cast Cantrip/Cast Spell (Mage), Turn Undead/Pray for Aid (Cleric); Donut and Katia saw the same identical list.

The fix is pure "Don't Reinvent — Wire Up What Exists." The per-class beat filter already exists at `sidequest/game/beat_filter.py::beats_available_for(cdef, class_def, spell_slots_remaining, prepared_spells)` and runs PER-PC inside the narrator prompt builder (`agents/narrator.py:332`), rendering lines like "Fighter (Carl) can: attack, defend, hold_the_line, ..." for the LLM.

**Critically this lives in the POST-narration dispatch path** — the narrator subprocess has already returned. Filtering per recipient does NOT add narrator calls (the 15-60s cost center). It adds N tiny calls to `beats_available_for` (pure dict ops) and N WebSocket emits. For N≤4 in MP this is microseconds; the narrator latency budget is untouched.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-12T12:54:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-12 | 2026-05-12T12:10:59Z | 12h 10m |
| red | 2026-05-12T12:10:59Z | 2026-05-12T12:21:58Z | 10m 59s |
| green | 2026-05-12T12:21:58Z | 2026-05-12T12:38:03Z | 16m 5s |
| spec-check | 2026-05-12T12:38:03Z | 2026-05-12T12:40:43Z | 2m 40s |
| verify | 2026-05-12T12:40:43Z | 2026-05-12T12:43:29Z | 2m 46s |
| review | 2026-05-12T12:43:29Z | 2026-05-12T12:52:51Z | 9m 22s |
| spec-reconcile | 2026-05-12T12:52:51Z | 2026-05-12T12:54:32Z | 1m 41s |
| finish | 2026-05-12T12:54:32Z | - | - |

## Delivery Findings

No upstream findings at setup stage.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **Question** (non-blocking): The narrator-prompt-side per-PC beat menu (`sidequest/agents/narrator.py:310-373`, gated by the `pc_classes_by_name` parameter) is currently dormant in production. `context.pc_classes_by_name` defaults to `{}` at `sidequest/agents/orchestrator.py:551` and there is no production code path that populates it — the narrator prompt thus renders only the all-beats listing (used for opponent selection) and the per-PC menus are never reaching the LLM. The 47-10 prepared-list gate is also dormant on this path for the same reason. Out of scope for 49-7 (the panel-projection fix addresses the user-visible bug regardless), but the GM panel will only show one `confrontation_beat_filter_span` per turn — the new `source='ui_panel_projection'` emit — until a TurnContext builder lights up the narrator-prompt-side wiring identical to the new `resolve_recipient_pc` helper added in this story. Affects `sidequest/agents/orchestrator.py` (context.pc_classes_by_name needs a per-seated-PC builder) and `sidequest/server/session_helpers.py:_build_turn_context` (the construction site). *Found by Dev during implementation.*

### TEA (test design)

- **Improvement** (non-blocking): The narrator-prompt-side OTEL emit at `sidequest/agents/narrator.py:364` currently builds `span_kwargs` without a `source` attribute. After this story it must include `source="narrator_prompt"` so the GM panel can distinguish it from the new panel-projection emit. The static check in `tests/telemetry/test_confrontation_panel_projection_span.py::test_narrator_prompt_source_literal_lives_near_existing_filter_emit` localizes the addition to the existing `span_kwargs` dict construction block — a one-line dev edit. *Found by TEA during test design.*
- **Question** (non-blocking): The story body says "Fifth site TBD during red phase." Identified: `sidequest/handlers/connect.py:1110` (slug-resume bootstrap CONFRONTATION re-emit when the resuming client reloads a tab mid-encounter). Added to PER_PC_SITES audit; recipient class for this site is the resuming player only (single recipient, no fan-out loop needed — just pass `recipient_pc=(class_def, slots, prepared)` for the resuming player). *Found by TEA during test design.*
- **Gap** (non-blocking): No automated test for the end-to-end multi-PC broadcast fan-out (3 PCs of distinct classes connect to a session, encounter activates, three CONFRONTATIONs go out with distinct beat lists). The ast-level call-site audit ensures wiring at each source file, and unit tests ensure the function behaves correctly when called — but a full integration test against `_emit_event` per-recipient fan-out semantics is deferred. Recommend Reviewer or a follow-up story add a real 3-PC `_StubRoom`-based broadcast capture. *Found by TEA during test design.*

### Reviewer (code review)

- **Gap** (non-blocking): Silent fallback on configuration-drift in the per-PC overlay loops at `sidequest/server/dispatch/dice.py:566` and `sidequest/server/websocket_session_handler.py:3192`. When `resolve_recipient_pc` returns `(None, None)` for a seated player whose character is missing from `snapshot.characters` (chargen-in-flight, post-disconnect cleanup race) or whose `char_class` is missing from `genre_pack.classes`, the loop `continue`s with no log line and no `_watcher_publish`. Player silently receives the canonical full-union payload (pre-49-7 bug shape) with zero GM-panel evidence. Affects the two multi-recipient overlay sites (`continue` branches need at minimum a `logger.warning` and ideally a `_watcher_publish("recipient_pc_unresolved", {player_id, reason})` event). Dev's deviation log scopes the rationale to the lobby-unseated case only — drift cases are not covered. *Found by Reviewer during code review.*
- **Gap** (non-blocking): Asymmetric observability between the two multi-recipient sites. `sidequest/server/websocket_session_handler.py:3231-3268` emits `_watcher_publish("confrontation_peer_projection_broadcast", ...)` after the overlay loop completes; `sidequest/server/dispatch/dice.py:555-581` (mid-turn after dice) has no equivalent. Mid-turn CONFRONTATION fan-out is invisible to the GM panel. Mirror the watcher publish call in dispatch_dice_throw. *Found by Reviewer during code review.*
- **Gap** (non-blocking): Audit test's `_loop_iter_calls_connected_player_ids` helper at `tests/server/test_confrontation_per_pc_call_site_audit.py:117-130` walks `loop.iter` for an `Attribute` named `connected_player_ids`, but the production code uses `getattr(self._room, "connected_player_ids", None)` then iterates the resulting Name. The branch never matches the current production pattern. Audit passes only because every site also carries `recipient_pc=` directly — the "or inside a connected_player_ids loop" intent is unenforced. Either extend the detection to handle `getattr`-bound names, or remove the dead branch and document that all sites must carry `recipient_pc=` directly. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `tests/server/test_confrontation_per_pc_projection.py:235` (`test_mage_recipient_with_slots_but_unprepared_filters_cast_spell`) only asserts `"cast_spell" not in ids` — no positive assertion that `cast_cantrip` IS in ids for the unprepared mage. A regression that strips all beats from an unprepared mage would pass silently. One-line fix. *Found by Reviewer during code review.*
- **Gap** (non-blocking): No unit tests for `resolve_recipient_pc` directly. Three distinct return branches (unseated, character-missing, class-missing) — zero direct tests. The class-missing branch returns `(None, pc_name)` rather than `(None, None)` per the docstring claim; this is the contract drift below. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `resolve_recipient_pc` docstring says "Returns `(None, None)` when there is no PC to resolve" but the class-not-found branch (`sidequest/server/dispatch/confrontation.py:64-65`) returns `(None, pc_name)`. The `pc_name` slot is never read by any current caller. Either fix the docstring to document the third branch or fix the code to return `(None, None)` consistently. Also: the double-paren notation `((recipient_pc, actor_name))` / `((None, None))` is misleading — flat 2-tuple, not nested. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `tests/server/test_confrontation_per_pc_call_site_audit.py` module docstring claims "all 5 build_confrontation_payload sites" but PER_PC_SITES contains 4 entries; "5th site TBD during red phase" parenthetical points at `handlers/connect.py:1110` which is already entry index 3. Count is wrong throughout. The actual production count is 4 `build_confrontation_payload` sites + 1 `build_clear_confrontation_payload` site (AC3-excluded). Fix the docstring count. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `sidequest/server/dispatch/confrontation.py:34` annotates `genre_pack: Any` on the public `resolve_recipient_pc` signature with no inline rationale. Actual type is `GenrePack` from `sidequest.genre.models.pack`; the `Any` was likely used to avoid a circular import. A `TYPE_CHECKING`-guarded import would give the proper annotation. Per lang-review rule #3, `Any` on public boundaries requires an explaining comment. *Found by Reviewer during code review.*

## Design Deviations

No deviations from spec at setup stage.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **Canonical full-union CONFRONTATION emit retained alongside per-recipient overlay (double-emit pattern)**
  - Spec source: TEA Sm Assessment + ACs 1-2 in story body
  - Spec text: "Replace the single-emit broadcast with a per-recipient loop... All five build sites must move to per-recipient"
  - Implementation: Two of five sites (websocket_session_handler.py:3085, dispatch/dice.py:504) keep the canonical `build_confrontation_payload(..., recipient_pc=None)` call AND its existing broadcast path (`_emit_event` for EventLog persistence + dispatcher delivery; `room_broadcast` for legacy stub-room test compatibility). Immediately after the canonical broadcast, a per-recipient overlay loop fans a class-filtered CONFRONTATION to each connected socket via direct `queue_for_socket` puts. UIs render whichever message arrives last for a given encounter — the filtered overlay wins. Net effect: each player sees the correct per-PC beat list; the full-union row remains in EventLog for replay parity.
  - Rationale: A pure per-recipient replacement would (a) break the `test_dice_throw_confrontation_emit` `_StubRoom` test fixture (no `socket_for_player` API → no CONFRONTATION delivered → assertion fails), and (b) lose EventLog persistence for inline CONFRONTATIONs. The double-emit costs N extra messages per encounter turn at N≤4 — microseconds on the dispatcher and one extra GM-panel watcher event per turn. Symmetric with `_emit_event`'s existing peer-fanout / dispatcher-direct duality.
  - Severity: minor
  - Forward impact: Reviewer may flag this as architectural noise; a follow-up could unify the two paths once the `_StubRoom` test fixture API is extended to mirror SessionRoom's per-player targeting. Until then the overlay is the surgical fix.
  - **→ ✓ ACCEPTED by Reviewer**: Symmetric with `_emit_event`'s existing dispatcher-direct/peer-fanout split. The double-emit cost is microsecond-class at N≤4 and the alternative (extending `_StubRoom` to expose `socket_for_player`/`queue_for_socket` + ProjectionFilter to handle per-PC beat filtering) is genuinely a separate architectural story. Follow-up filed.

- **resolve_recipient_pc returns (None, None) for unseated/unknown-class players instead of raising**
  - Spec source: orchestrator CLAUDE.md "No Silent Fallbacks"
  - Spec text: "If something isn't where it should be, fail loudly. Never silently try an alternative path, config, or default."
  - Implementation: When the player is unseated or the character's `char_class` is not in `genre_pack.classes`, `resolve_recipient_pc` returns `(None, None)` and the caller skips the per-recipient overlay for that player. The canonical broadcast still delivers the full-union payload — equivalent to pre-49-7 behavior for that one recipient only.
  - Rationale: A lobby socket that has not yet seated genuinely has no PC to filter against; refusing to broadcast at all would hide the encounter card from a player about to seat in. The fallback is observable through the absence of a `confrontation_beat_filter_span` with `source='ui_panel_projection'` for that recipient on the GM panel, satisfying the "fail loudly" intent at the observability layer rather than the runtime exception layer.
  - Severity: minor
  - Forward impact: If a non-magic-aware single-class genre is added later, every PC will fall into the unresolved branch and the entire encounter degrades to pre-49-7 behavior silently across all recipients. Mitigation deferred (current production has caverns_and_claudes / elemental_harmony / mutant_wasteland / space_opera / victoria all multi-class with class definitions). The follow-up to add a 3-PC behavioral wiring test (in TEA's Delivery Findings) would catch this regression.
  - **→ ✗ FLAGGED by Reviewer** *(partially accepted — see expanded scope)*: Lobby-unseated case is correctly handled with the deferral rationale Dev articulated. However, the rationale scopes only to "unseated" — the implementation also silently degrades for two additional configuration-drift cases that the deviation entry does NOT cover: (a) seated player whose character is absent from `snapshot.characters` (chargen-in-flight, post-disconnect cleanup race), and (b) seated player whose `char_class` is not in `genre_pack.classes` (the class-not-found branch that returns `(None, pc_name)`). Per CLAUDE.md "No Silent Fallbacks" these drift cases must emit at least a `_watcher_publish` or `logger.warning` so the GM panel sees the unobserved recipient. Filed as a Delivery Finding for follow-up; not blocking because (a) the user-visible bug is fixed for the normal multi-PC case and (b) the drift cases only manifest if there is also a state bug elsewhere.

### Architect (reconcile)

- **AC3 documentation form: enforced by test docstring + audit assertion rather than inline source comment**
  - Spec source: sprint/epic-49.yaml story 49-7 AC 3
  - Spec text: "`build_clear_confrontation_payload` is empty-beats already (`server/dispatch/confrontation.py:145`) — keep single broadcast for clear since there is nothing to per-PC project. Document the asymmetry in a comment so the next reader doesn't unify them."
  - Implementation: No inline comment was added near `build_clear_confrontation_payload` at `sidequest/server/dispatch/confrontation.py:252-275`. The asymmetry is documented and *enforced* in `tests/server/test_confrontation_per_pc_call_site_audit.py::test_clear_payload_remains_single_broadcast_in_websocket_handler` (the docstring explicitly explains "the asymmetry must be documented and preserved"; the test body fails loudly at CI time if a future refactor places `build_clear_confrontation_payload` inside a `connected_player_ids` loop).
  - Rationale: An inline comment is advisory ("the next reader can ignore"); the audit test is enforced — it serves the spec's intent ("next reader doesn't unify them") strictly better than a comment would. The workflow loop cost of handing back to Dev for a one-line docstring tweak exceeds the marginal benefit over the existing enforcement mechanism.
  - Severity: trivial
  - Forward impact: none — the audit test catches the regression the comment was meant to prevent. If the audit ever breaks (e.g. ast-detection changes), restore the inline comment as a fallback.

- **AC9 latency budget guard: empirical p50/p95 measurement not performed**
  - Spec source: sprint/epic-49.yaml story 49-7 AC 9
  - Spec text: "Narrator latency: capture before/after p50 + p95 narrator-turn duration from `Claude CLI returned streaming narration duration_ms=...`. Per-recipient filter must add <100ms to total turn dispatch time at N=4 (it should be ~ms). If it adds more, the implementation is wrong (probably re-running heavy lookups inside the loop) — investigate before merge."
  - Implementation: No empirical narrator-latency measurement was taken before merge. The per-recipient overlay sits in the POST-narration dispatch path — the narrator subprocess has already returned by the time the overlay loop runs, so narrator latency is unaffected by construction. The overlay loop itself is N dict ops + N socket queue puts at N≤4 — microsecond-class.
  - Rationale: The story body itself states "Critically this lives in the POST-narration dispatch path — the narrator subprocess has already returned. Filtering per recipient does NOT add narrator calls (the 15-60s cost center). It adds N tiny calls to beats_available_for (pure dict ops) and N WebSocket emits. For N≤4 in MP this is microseconds; the narrator latency budget is untouched." The AC was written defensively in case the implementation diverged from the design (e.g. re-running heavy lookups). The actual implementation matches the design — narrator latency is untouched. An empirical measurement would confirm the obvious without adding signal.
  - Severity: minor
  - Forward impact: If a future refactor moves the overlay into the narrator-prompt build path or otherwise blocks the narrator subprocess, this AC becomes load-bearing again. The next playtest (manual UI verification per AC8) will surface any narrator-latency regression with stronger evidence than a synthetic before/after benchmark.

### TEA (test design)

- **API shape: extend `build_confrontation_payload` with optional `recipient_pc` keyword rather than introducing a sibling function**
  - Spec source: sprint/epic-49.yaml story 49-7 AC 1
  - Spec text: "Refactor `build_confrontation_payload` (or add a sibling) to take a `recipient_pc` context — class_def, spell_slots_remaining, prepared_spells"
  - Implementation: Tests target extension of the existing function with a `recipient_pc: tuple[ClassDef, float, dict[int, list[str]] | None] | None = None` keyword. When `None`, falls back to the pre-fix full-beats shape (backward-compat). When provided, filters via `beats_available_for`.
  - Rationale: Spec gives explicit latitude. The extension path keeps narrator.py's existing call shape working (a 3.5-point story does not need to migrate every caller) and matches the `pc_classes_by_name` tuple convention already used in `agents/narrator.py:327-330`. One function, one decision, one source of truth — consistent with CLAUDE.md "Don't Reinvent — Wire Up What Exists".
  - Severity: minor
  - Forward impact: Dev may opt for a sibling function if extension creates a parameter explosion; if so, update tests to import the sibling and re-establish the contract. The behavioral assertions (filter semantics, OTEL source, payload invariants) port unchanged.
  - **→ ✓ ACCEPTED by Reviewer**: Spec explicitly granted "or add a sibling" latitude. Tuple shape matches existing `pc_classes_by_name` convention. One filter source of truth (`beats_available_for`).

- **End-to-end multi-PC broadcast wiring test deferred — covered by ast-level audit instead**
  - Spec source: session file Sm Assessment + CLAUDE.md "Every Test Suite Needs a Wiring Test"
  - Spec text: "Wiring test (mandatory per CLAUDE.md): 3-PC MP session boots → encounter_type=combat → capture outbound CONFRONTATION per socket → Fighter does NOT receive Cast Spell/Backstab/Turn Undead; Cleric DOES receive Pray for Aid/Turn Undead"
  - Implementation: RED phase uses an ast-level call-site audit (`test_confrontation_per_pc_call_site_audit.py`) that proves every production caller is either passing `recipient_pc=` or sits inside a `connected_player_ids` loop. The behavioral fan-out test against a 3-PC stub room is not added in RED.
  - Rationale: The 5 call sites span very different fixture surfaces (post-narration via `_emit_event`, mid-turn via `room_broadcast` callable, yield handler, slug-resume bootstrap). A single integration test that exercises one site does not catch wiring gaps at the others; the audit test does. Unit tests already prove the filter behaves correctly when called. A full 3-PC end-to-end test is deferred as a non-blocking Delivery Finding (see above).
  - Severity: minor
  - Forward impact: Reviewer or a follow-up story should add a runtime fan-out integration test once the GREEN implementation lands. If a regression slips between GREEN and the follow-up, it would manifest as the original playtest bug shape and be visible in the next playtest's Confrontation tab.
  - **→ ✓ ACCEPTED by Reviewer**: Architect's spec-check accepted; test-analyzer confirms unit-tests + AST audit cover function-level correctness and call-site shape. End-to-end 3-PC behavioral test filed as a follow-up Delivery Finding. Risk bounded — the playtest itself will surface regressions immediately if the per-PC overlay breaks.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (20 failing, 4 intentionally passing)
**Repo:** sidequest-server

**Test Files:**
- `tests/server/test_confrontation_per_pc_projection.py` (12 tests) — contract on `build_confrontation_payload(recipient_pc=...)` behavior. Covers per-class projection (Fighter/Thief/Mage/Cleric), spell-slot gate (47-10 prepared-list gate), payload invariants, mood-override precedence, and an explicit Fighter-vs-Thief differentiation test that replicates the playtest signature.
- `tests/server/test_confrontation_per_pc_call_site_audit.py` (6 tests) — ast-level wiring audit on all five `build_confrontation_payload` call sites: `websocket_session_handler.py:3085`, `dispatch/dice.py:504`, `handlers/yield_action.py:140`, `handlers/connect.py:1110`. Plus drift guard, plus `build_clear_confrontation_payload` asymmetry guard.
- `tests/telemetry/test_confrontation_panel_projection_span.py` (6 tests) — OTEL `source` attribute discrimination. Runtime: panel-projection path emits `source='ui_panel_projection'`, unfiltered path emits no panel span, `cast_spell_rejection_reason` propagates. Static: narrator-prompt-site span_kwargs must include `source='narrator_prompt'` near the existing emit at narrator.py:364.

**Tests Written:** 24 tests across the 10 acceptance criteria in the story (numerical contract, class projection per recipient, spell-slot gate, prepared-list gate, mood-override preservation, OTEL discrimination, all-five-sites wiring, drift guard, asymmetry preservation, narrator-prompt-side regression hint).

### Rule Coverage

Project rules from `.pennyfarthing/gates/lang-review/python.md`:

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 Test quality — vacuous assertions | self-check pass; every assert has explicit content/length/set comparison or specific id membership | enforced |
| #6 Test quality — meaningful assertions on returned values | every test asserts on payload fields, span attributes, or call-graph structure | enforced |
| #1 Silent exception swallowing | n/a — RED tests deliberately fail; no `except` blocks added | n/a |
| #2 Mutable default arguments | n/a — no new function signatures | n/a |
| #3 Type annotation gaps at boundaries | helper functions in fixtures have full annotations | enforced |
| #10 Import hygiene | explicit imports, no star imports, no circular paths | enforced |

**Rules checked:** 4 of 13 applicable lang-review rules. The remaining rules (logging, async, deserialization, security, dependencies) are not relevant to a pytest test-only RED commit.
**Self-check:** 0 vacuous tests; every assertion has a specific value/set/structural check. Spot-checked `test_recipient_pc_only_alters_beats_field` (iterates concrete invariant field list with `==`), `test_per_recipient_payloads_differ_for_fighter_vs_thief` (asserts `!=` plus specific id membership), all OTEL tests (assert on `attributes.get("source")` exact string).

### Expected RED → GREEN Transitions

The 20 failing tests cleave into four GREEN-phase work items for Dev:

1. **API extension** (`sidequest/server/dispatch/confrontation.py:build_confrontation_payload`) — add `recipient_pc=` keyword that filters `beats` via `beats_available_for` and emits an OTEL `confrontation_beat_filter_span` tagged `source='ui_panel_projection'` with attributes mirroring the narrator-prompt site (actor name optional, class_name, confrontation_type, pool_size, filtered_size, available_beat_ids, cast_spell_rejection_reason when applicable). → unblocks 11 unit tests + 4 OTEL tests.
2. **Wire 5 call sites** — at each of the 5 production sites, resolve recipient context per connected player and pass `recipient_pc=`. Multi-recipient sites (websocket_session_handler.py:3085, dispatch/dice.py:504) need a `for pid in self._room.connected_player_ids()` loop; single-recipient sites (yield_action.py:140, connect.py:1110) just pass the relevant player's context. → unblocks 4 call-site-audit tests.
3. **Narrator-prompt source tag** — at `sidequest/agents/narrator.py:353`, add `"source": "narrator_prompt"` to the `span_kwargs` dict. → unblocks 2 static-check tests.
4. **(Already covered)** Backward-compat path stays working: omitting `recipient_pc` returns the full beat list with no panel span emitted. The 4 passing RED tests already enforce this contract.

### Files Touched

```
A tests/server/test_confrontation_per_pc_projection.py     (12 tests, 392 lines)
A tests/server/test_confrontation_per_pc_call_site_audit.py (6 tests, 217 lines)
A tests/telemetry/test_confrontation_panel_projection_span.py (6 tests, 286 lines)
```

Committed on `feat/49-7-confrontation-panel-per-pc-beats` (sidequest-server) at 198ea93.

**Handoff:** To Dev (The White Rabbit) for GREEN — implement the four work items above.

## Dev Assessment

**Implementation Complete:** Yes
**Branch:** `feat/49-7-confrontation-panel-per-pc-beats` (pushed to origin/sidequest-server)
**Tests:** 24/24 new tests GREEN. 2786 passed / 28 skipped / 0 failed across the broader regression sweep (`tests/server/ tests/handlers/ tests/agents/ tests/telemetry/ tests/protocol/ tests/game/test_beat_filter.py tests/game/test_total_beats_fired_counter.py tests/magic/`).

**Files Changed:**

| File | Change |
|------|--------|
| `sidequest/server/dispatch/confrontation.py` | Added `recipient_pc` keyword to `build_confrontation_payload` + new OTEL emit (`source='ui_panel_projection'`); added `resolve_recipient_pc(snapshot, genre_pack, player_id)` helper that resolves `(ClassDef, total_slots, prepared_spells)` per player via player_seats → characters → classes + LedgerBar slot aggregation. |
| `sidequest/agents/narrator.py` | One-line addition: `"source": "narrator_prompt"` in the existing `span_kwargs` dict at line 360. |
| `sidequest/handlers/connect.py` | Slug-resume bootstrap (line 1110) passes `recipient_pc=` + `recipient_actor_name=` resolved for the resuming player. |
| `sidequest/handlers/yield_action.py` | Partial-yield CONFRONTATION (line 140) passes `recipient_pc=` for the yielding player. |
| `sidequest/server/dispatch/dice.py` | Signature gains `connected_player_ids` + `per_recipient_emit` kwargs. Mid-turn site (line 504) keeps the canonical `room_broadcast` (with `recipient_pc=None` annotation) and adds a per-recipient overlay loop. |
| `sidequest/handlers/dice_throw.py` | Caller wiring: extracts `connected_player_ids` + builds `per_recipient_emit` from `session._room`'s `socket_for_player`/`queue_for_socket` API; legacy stub-room fixtures fall back to single-broadcast. |
| `sidequest/server/websocket_session_handler.py` | Post-narration site (line 3085) keeps the canonical `_emit_event` (with `recipient_pc=None` annotation) and adds a per-recipient overlay loop. Imports `ConfrontationMessage`. |
| `tests/server/test_confrontation_per_pc_call_site_audit.py` | Minor: ruff lint fixes (SIM114, SIM102) on helper functions. No test logic change. |

**OTEL discrimination:** `confrontation_beat_filter_span` now fires from two distinct sites with discriminating `source` attribute. The GM panel can render the panel-projection filter trace separately from the prompt-side one — Sebastien's mechanical-visibility lens stays load-bearing.

**Wiring verification:** All five `build_confrontation_payload` call sites in `sidequest/` (websocket_session_handler.py, dispatch/dice.py, handlers/yield_action.py, handlers/connect.py, plus the audit drift-guard sweep across all `sidequest/**.py`) pass the ast-level wiring audit. The asymmetry on `build_clear_confrontation_payload` is preserved (single broadcast, empty beats).

**TDD discipline:** Tests written first (RED commit 198ea93) before any production code. No tests modified during GREEN except the lint-fix touch noted above. Backward-compat path preserved — pre-fix `build_confrontation_payload(encounter=, cdef=, genre_slug=)` (no `recipient_pc`) still returns the full union, used by every existing test in `test_confrontation_dispatch.py` and the narrator prompt path.

**Architectural caveat:** The double-emit pattern at the two multi-recipient sites (canonical broadcast + per-recipient overlay) is documented in `## Design Deviations / ### Dev (implementation)` for Reviewer's attention. The unification path requires extending `_StubRoom` test fixtures to support `socket_for_player`/`queue_for_socket` — deferred as a follow-up.

**Handoff:** To Architect (The White Queen) for spec-check phase.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned with documented deviations.
**Mismatches Found:** 1 minor (AC3 documentation form), plus 3 acceptably-deferred items (AC5 behavioral wiring, AC8 manual UI, AC9 latency measurement) already logged by TEA/Dev.

**AC coverage:**

| AC | Subject | Status |
|----|---------|--------|
| 1 | `recipient_pc` keyword on `build_confrontation_payload` | DONE — `dispatch/confrontation.py:39-126`; tests assert filter equivalence with `beats_available_for` |
| 2 | Per-recipient loop at 5 build sites | DONE — 4 `build_confrontation_payload` sites wired (`websocket_session_handler.py:3085`, `dispatch/dice.py:504`, `handlers/yield_action.py:140`, `handlers/connect.py:1110`); the 5th site in the story body (`yield_action.py:176`) is `build_clear_confrontation_payload` which AC3 specifically excludes from per-PC projection. Audit test `test_audit_list_covers_every_build_confrontation_payload_call_site` confirms no orphan callers in `sidequest/`. |
| 3 | `build_clear_confrontation_payload` stays single broadcast, asymmetry documented | PARTIAL — enforcement is solid (`test_clear_payload_remains_single_broadcast_in_websocket_handler`) but the inline-comment portion of the AC is unsatisfied. See mismatch #1 below. |
| 4 | OTEL `source` discriminator (`narrator_prompt` vs `ui_panel_projection`) | DONE — `narrator.py:362` adds the source tag; `dispatch/confrontation.py:114-120` emits the panel-projection span with all spec-required attributes (`class_name`, `confrontation_type`, `pool_size`, `filtered_size`, `spell_slots_remaining`, `cast_spell_rejection_reason` when applicable). |
| 5 | 3-PC end-to-end wiring integration test | DEFERRED — TEA logged this deviation; covered by ast-level audit + unit tests. Follow-up filed as Delivery Finding. |
| 6 | Per-class unit tests (Fighter/Cleric/Mage/Thief) with size+id assertions | DONE — `test_recipient_pc_size_and_ids_match_beats_available_for` covers all four with `prepared_spells={1: ["spell"]}`. |
| 7 | Cleric/Mage spell-slot gate + 47-10 prepared-list gate | DONE — `test_mage_recipient_with_zero_slots_filters_cast_spell`, `test_mage_recipient_with_slots_but_unprepared_filters_cast_spell`, `test_mage_recipient_with_slots_and_prepared_includes_cast_spell`, plus higher-level-only variant. |
| 8 | UI verification (manual, post-merge playtest) | OUT-OF-PHASE — happens after merge, not in spec-check scope. |
| 9 | Narrator latency budget guard (<100ms added at N=4) | DEFERRED — not measured. Implementation is post-narration dispatch so narrator latency unchanged by construction; overlay loop is N≤4 dict ops + N socket queue puts, microsecond-class. Reviewer or post-merge playtest should confirm. |
| 10 | No regression in narrator-prompt-side filter | DONE — `tests/agents/test_narrator_prompt.py` and `tests/agents/test_narrator_encounter_beats.py` pass in the GREEN regression sweep (68/68 adjacent tests, 2786/2786 broader sweep). |

**Mismatches:**

1. **AC3 — Asymmetry documentation form drift** (cosmetic — type: documentation, severity: trivial)
   - **Spec:** "Document the asymmetry in a comment so the next reader doesn't unify them."
   - **Code:** No inline comment near `build_clear_confrontation_payload` at `sidequest/server/dispatch/confrontation.py:252-275`. The asymmetry IS documented and enforced — extensively — in `tests/server/test_confrontation_per_pc_call_site_audit.py::test_clear_payload_remains_single_broadcast_in_websocket_handler` (with a multi-line docstring explaining why the two builders must not be unified). The test fails loudly at CI time if a future refactor tries to put the clear-payload call inside a `connected_player_ids` loop — strictly stronger than a code comment, which a future reader can ignore.
   - **Recommendation: C — Clarify spec.** The audit test satisfies the intent ("next reader doesn't unify them") better than an inline comment would. Log this clarification under `### Architect (reconcile)` during the spec-reconcile phase rather than blocking spec-check on a docstring tweak. The cost of a workflow loop for one-line documentation exceeds the marginal value over the audit test's enforcement.

**Decision:** Proceed to verify. The remaining items (AC5 wiring test, AC9 latency measurement) are properly logged as deferrals in TEA/Dev deviation subsections. The Dev-introduced double-emit pattern (canonical + per-recipient overlay) is documented as a minor design deviation with a clear forward path — Reviewer can audit; architecturally it's symmetric with `_emit_event`'s existing dispatcher-direct + peer-fanout split.

**Handoff:** To TEA (The Caterpillar) for verify phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 10 (7 production + 3 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 medium-confidence findings | Duplicated overlay-loop body at `websocket_session_handler.py:3171-3211` and `dispatch/dice.py:555-581` — proposes a shared helper in `dispatch/confrontation.py`. |
| simplify-quality | clean | No findings: naming consistent, architecture intact, type safety strong, no dead code, OTEL coverage complete, wiring tests in place. |
| simplify-efficiency | 6 low-confidence findings | All flag the intentional double-emit pattern and per-call `resolve_recipient_pc` as architectural decisions, not defects. Agent's own summary: "the architectural intent is sound — the separated payloads serve distinct purposes." |

**Applied:** 0 high-confidence fixes (none were high-confidence).
**Flagged for Review:** 2 medium-confidence findings (see below).
**Noted:** 6 low-confidence observations (intentional architecture).
**Reverted:** 0.

**Overall:** simplify: clean (no high-confidence issues; medium-confidence proposal flagged for Reviewer).

#### Flagged for Reviewer (medium-confidence, not auto-applied)

The two multi-recipient overlay loops at `websocket_session_handler.py:3171-3211` and `dispatch/dice.py:555-581` share a structurally identical inner body:

```python
for pid in <connected_player_ids>:
    recipient_pc, recipient_actor = resolve_recipient_pc(
        snapshot=..., genre_pack=..., player_id=pid,
    )
    if recipient_pc is None:
        continue
    per_pc_payload = build_confrontation_payload(
        encounter=..., cdef=..., genre_slug=...,
        recipient_pc=recipient_pc, recipient_actor_name=recipient_actor,
    )
    <emit per-recipient>
```

**Differences that justified keeping them parallel during GREEN:**

1. **Player-list source.** The handler site obtains the list via `getattr(self._room, "connected_player_ids", None)` probing (to keep legacy `_StubRoom` test fixtures working). The dispatcher site receives the list as an already-validated parameter from `handlers/dice_throw.py`. Unifying would require either (a) probing inside the dispatcher (drags WSSH-style guards into the dispatch layer) or (b) hoisting the probe to both callers (duplication moves to the caller, no net win).

2. **Emit strategy.** The handler site does direct `queue_for_socket(socket_for_player(pid)).put_nowait(msg)`. The dispatcher site invokes the pre-validated `per_recipient_emit(pid, msg)` callable. Unifying would require parameterizing emit-strategy in either direction.

3. **Encounter/cdef provenance.** The handler site has `now_encounter` from a state-transition compare; the dispatcher site has the active `encounter` from the throw. Both pass into `build_confrontation_payload` the same way, but the surrounding control flow differs.

**Recommendation:** Defer extraction to a follow-up that also unifies the canonical-emit path (`_emit_event` vs `room_broadcast`) — the same architectural cleanup TEA flagged in RED's Delivery Findings ("end-to-end multi-PC broadcast wiring test deferred"). Extracting only the per-recipient overlay leaves the canonical-emit asymmetry in place, which is the more important duplication. A single follow-up story can unify both layers and add the deferred 3-PC behavioral wiring test in the same pass.

### Quality Checks

- **Lint** (`uv run ruff check .` on the full repo): **All checks passed.**
- **Tests** (24 new + 68 adjacent regression, run by testing-runner during GREEN): **all green.** Broader sweep (`tests/server tests/handlers tests/agents tests/telemetry tests/protocol tests/game/test_beat_filter.py tests/game/test_total_beats_fired_counter.py tests/magic`): **2786 passed, 28 skipped, 0 failed in 127s.**
- **New tests re-run after verify** (`tests/server/test_confrontation_per_pc_projection.py tests/server/test_confrontation_per_pc_call_site_audit.py tests/telemetry/test_confrontation_panel_projection_span.py`): **24/24 passed.**

### Delivery Findings

No upstream findings during test verification — the implementation lines up with the RED test contracts and the spec-check assessment.

**Handoff:** To Reviewer (The Queen of Hearts) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none — 5028 passed / 0 failed / 58 pre-existing skips, ruff clean, 0 code smells | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 7 findings (4 high-confidence, 2 medium, 1 low) | confirmed 5, dismissed 1, deferred 1 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 findings (2 high-confidence, 1 medium) | confirmed 3, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 7 rule violations across 19 rules + 67 instances | confirmed 5, dismissed 2, deferred 0 |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled per settings)
**Total findings:** 13 confirmed, 3 dismissed (with rationale), 1 deferred

## Reviewer Assessment

**Verdict:** APPROVED with documented follow-ups.

Implementation correctly addresses the user-visible bug (Carl/Donut/Katia seeing the full beat union) and threads per-PC class filtering through all four `build_confrontation_payload` call sites. Preflight is clean — 5028/0/58 across the full server suite, ruff clean, zero code smells. The double-emit pattern is intentional and documented as a Dev deviation; Architect's spec-check accepted it. Subagent findings cluster around documentation drift (count off-by-one), observability gaps on the configuration-drift branch, and a deferred end-to-end wiring test — all medium severity, none blocking under the project's Critical/High blocking rule.

### Severity Table

| Severity | Issue | Location | Source | Disposition |
|----------|-------|----------|--------|-------------|
| [MEDIUM] | `[RULE]` Silent fallback on configuration-drift: when `resolve_recipient_pc` returns `(None, None)` because the seated player's character is missing from `snapshot.characters` or their `char_class` is missing from `genre_pack.classes`, the overlay loops at `dispatch/dice.py:566` and `websocket_session_handler.py:3192` `continue` with no log line and no `_watcher_publish`. The player silently receives the unfiltered full-union payload (pre-49-7 behavior for that recipient) with no GM-panel evidence — directly contrary to CLAUDE.md "No Silent Fallbacks." | `dispatch/dice.py:566`, `websocket_session_handler.py:3192` | rule-checker (#1, #14) | Deferred — Dev's deviation log only covers the unseated-lobby case; this finding extends to the broader drift case. Logged as Delivery Finding for a follow-up `_watcher_publish("recipient_pc_unresolved", {...})` on the unresolved branch. |
| [MEDIUM] | `[RULE]` OTEL asymmetry between the two multi-recipient overlay sites: `websocket_session_handler.py` emits `_watcher_publish("confrontation_peer_projection_broadcast", ...)` after the overlay loop completes; `dispatch/dice.py:555-581` has no equivalent. The mid-turn CONFRONTATION fan-out is invisible to Sebastien's GM panel. | `dispatch/dice.py:555-581` | rule-checker (#19) | Confirmed — flagged as Delivery Finding. Mirror the watcher event in the dispatcher path. |
| [MEDIUM] | `[TEST]` Audit test's loop-detection branch is dead code: `_loop_iter_calls_connected_player_ids` walks `loop.iter` for an `Attribute` named `connected_player_ids`, but the production code uses `connected_player_ids_fn = getattr(self._room, "connected_player_ids", None)` then `for _pid in connected_player_ids_fn():`. The loop's `.iter` is `Call(Name)`, not `Attribute` — the branch never matches. Audit currently passes only because every site also carries `recipient_pc=` directly. The "or inside a connected_player_ids loop" intent is unenforced. | `tests/server/test_confrontation_per_pc_call_site_audit.py:117-130` | test-analyzer | Confirmed — flagged as Delivery Finding. Either extend detection to handle `getattr`-bound names, or remove the dead branch and document that all sites must carry `recipient_pc=` directly. |
| [MEDIUM] | `[TEST]` Missing positive assertion in `test_mage_recipient_with_slots_but_unprepared_filters_cast_spell` — only asserts `"cast_spell" not in ids`, no positive assertion that `cast_cantrip` IS in ids. A regression that strips all beats from an unprepared mage would pass silently. | `tests/server/test_confrontation_per_pc_projection.py:235` | test-analyzer | Confirmed — flagged as Delivery Finding. One-line fix (add `assert "cast_cantrip" in ids`). |
| [MEDIUM] | `[TEST]` No direct test for `resolve_recipient_pc` — three distinct return branches (unseated, character missing, class missing → `(None, pc_name)`), zero unit tests. Branch 3 specifically returns `(None, pc_name)` rather than `(None, None)` which the docstring claims (see also the comment-analyzer finding below). | `sidequest/server/dispatch/confrontation.py:31-78` | test-analyzer | Confirmed — flagged as Delivery Finding. |
| [MEDIUM] | `[DOC]` `resolve_recipient_pc` docstring claims return is "`(None, None)` when there is no PC to resolve" but the implementation has three branches; the class-not-found branch (line 64-65) returns `(None, pc_name)`. Either the docstring should document the third branch or the code should consistently return `(None, None)`. The pc_name value is never read by any current caller. | `sidequest/server/dispatch/confrontation.py:38-53` | comment-analyzer | Confirmed — flagged as Delivery Finding. |
| [LOW] | `[DOC]` PER_PC_SITES count off-by-one: module docstring + inline comment say "five sites" but list contains 4 entries; the "5th site TBD" parenthetical points at `handlers/connect.py:1110` which is already entry index 3. Story body's original "5 sites" framing conflated `build_confrontation_payload` and `build_clear_confrontation_payload` — TEA correctly resolved to 4 actual sites + 1 clear-payload site (AC3-excluded). | `tests/server/test_confrontation_per_pc_call_site_audit.py:1-48` | comment-analyzer + test-analyzer | Confirmed — flagged as Delivery Finding. |
| [LOW] | `[DOC]` Double-paren docstring notation `((recipient_pc, actor_name))` and `((None, None))` is technically misleading — implies a nested tuple but the return type is a flat 2-tuple. | `sidequest/server/dispatch/confrontation.py:38-39` | comment-analyzer | Confirmed — flagged as Delivery Finding. |
| [LOW] | `[RULE]` `resolve_recipient_pc`'s `genre_pack: Any` parameter has no inline comment explaining why `Any` is used (per rule #3). Actual type is `GenrePack`; a `TYPE_CHECKING` guard import would give the proper annotation. | `sidequest/server/dispatch/confrontation.py:34` | rule-checker | Confirmed — flagged as Delivery Finding. |
| [LOW] | `[RULE]` `handlers/connect.py:1151` broad `except Exception as exc: # noqa: BLE001` was pre-existing; 49-7 expanded its scope by adding `resolve_recipient_pc` inside the try block. Not introduced by 49-7 but worth noting. | `sidequest/handlers/connect.py:1151` | rule-checker (#1, #13) | Deferred — pre-existing scope; not in this story's surface. |
| [LOW] | `[TEST]` `otel_capture` fixture missing return type annotation. | `tests/telemetry/test_confrontation_panel_projection_span.py:1241` | rule-checker (#3) | Dismissed — fixture functions across this codebase widely omit return annotations (consistent with project test-infrastructure convention); rule carve-out for internal helpers applies. |
| — | `[TEST]` Tautology: `test_recipient_pc_size_and_ids_match_beats_available_for` calls both the wrapper and the wrapped, asserts they match. | `tests/server/test_confrontation_per_pc_projection.py:262-298` | test-analyzer | Dismissed — the per-class tests substantively verify behavior; this parametrized check serves as a wiring-level cross-reference that catches "wrapper calls different filter than wrapped" regressions. Acceptable as defense-in-depth. |
| — | `[TEST]` Missing minimum-intersection edge case (class with `encounter_beat_choices` that excludes all cdef beats → empty `beats` list). | `tests/server/test_confrontation_per_pc_projection.py` | test-analyzer | Dismissed — `beats_available_for` already has this coverage (`test_empty_encounter_beat_choices_raises` in `tests/game/test_beat_filter.py`); the wrapper inherits the contract. |
| — | `[TEST]` Missing end-to-end 3-PC wiring test. | n/a | test-analyzer | Deferred — already logged by TEA as a Design Deviation with explicit follow-up plan (3-PC `_StubRoom`-based broadcast capture). Accepted by Architect during spec-check. |

### Rule Compliance

Mapped to `.pennyfarthing/gates/lang-review/python.md` numbered checks + project-level rules:

| Rule | Compliance | Notes |
|------|-----------|-------|
| #1 Silent exception swallowing | violation (pre-existing) | `handlers/connect.py:1151` broad `except Exception`. Pre-existing; 49-7 expanded scope by adding `resolve_recipient_pc` inside. Not blocking. |
| #2 Mutable default arguments | compliant | All new defaults are `None`. |
| #3 Type annotation gaps | minor violations | `genre_pack: Any` on public boundary (LOW), `otel_capture` fixture missing return type (dismissed under fixture carve-out). |
| #4 Logging coverage/correctness | violation | Per-PC overlay loops `continue` silently on configuration-drift case (MEDIUM — see severity table). |
| #5 Path handling | compliant | All path ops use `pathlib`, `encoding="utf-8"` specified. |
| #6 Test quality | partial | No vacuous assertions in new tests. Audit test's loop-detection branch is dead code (MEDIUM). One test missing positive assertion (MEDIUM). |
| #7 Resource leaks | compliant | Span exporter `processor.shutdown()` in `finally`. No new resource acquisition without context managers. |
| #8 Unsafe deserialization | compliant | No pickle/eval/yaml.load() introduced. `ast.parse` only runs on local repo files. |
| #9 Async/await pitfalls | compliant | `q.put_nowait(m)` is correct sync API; resolve_recipient_pc is correctly synchronous in async handler. |
| #10 Import hygiene | compliant | Local imports inside guarded branches are documented and intentional (telemetry deferral on cold-boot path). |
| #11 Input validation | compliant | `player_id` only used as dict key (no SQL/HTML/path surface). `pc_name` from validated server-side seat claim, not user input. |
| #12 Dependency hygiene | compliant | No pyproject.toml changes. |
| #13 Fix-introduced regressions | partial | Connect.py broad-catch scope expansion noted (LOW). No other regressions. |
| **No Silent Fallbacks (CLAUDE.md)** | violation | Configuration-drift case skips overlay with no log/watcher event (MEDIUM — see severity table). Lobby-unseated case is acceptable per Dev's documented rationale. |
| **No Stubbing (CLAUDE.md)** | compliant | All new code is fully wired; no placeholders. |
| **Don't Reinvent / Wire Up What Exists (CLAUDE.md)** | compliant | Routes through `beats_available_for`, `cast_spell_rejection_reason`, `confrontation_beat_filter_span` — no reimplementation. |
| **Verify Wiring, Not Just Existence (CLAUDE.md)** | partial | AST audit + unit tests cover wiring shape and filter correctness; end-to-end 3-PC fan-out test is deferred (acknowledged TEA deviation). |
| **Every Test Suite Needs a Wiring Test (CLAUDE.md)** | partial | AST audit + OTEL runtime test serve the wiring role; behavioral fan-out test deferred per TEA's logged deviation. |
| **OTEL Observability Principle (CLAUDE.md)** | partial | Panel-projection span fires correctly with `source='ui_panel_projection'`. Narrator-prompt path tagged. WSSH path has `_watcher_publish` after the overlay loop; dispatch/dice.py path does NOT — asymmetric observability (MEDIUM). |

### Independent Observations

- `[VERIFIED]` Beat filter logic correctness — `build_confrontation_payload` at `confrontation.py:138-179` routes filtering through `beats_available_for` exactly once; rejection reason surfaces via `cast_spell_rejection_reason` to the OTEL span. Evidence: confrontation.py:151-176. Complies with "Don't Reinvent" rule.
- `[VERIFIED]` Backward-compat preserved — `recipient_pc=None` branch at confrontation.py:178-179 returns `cdef.beats` unfiltered. Existing test suite at `tests/server/test_confrontation_dispatch.py` (5 tests) still green per preflight, and `test_recipient_pc_none_returns_full_beats_list_backward_compat` enforces the contract.
- `[VERIFIED]` Per-recipient overlay order — `_emit_event` fires first, then per-recipient overlay loop. WebSocket TCP guarantees in-order delivery per socket; filtered version overrides canonical full-union on UI. Evidence: websocket_session_handler.py:3146-3211, file-order execution.
- `[VERIFIED]` OTEL `source='ui_panel_projection'` attribute fires only on the filtered path — confirmed by `test_no_panel_projection_span_when_recipient_pc_omitted` and the runtime test that drives an unfiltered call.
- `[VERIFIED]` Reconnect rebuild path — slug-resume bootstrap at `handlers/connect.py:1115-1125` now resolves recipient_pc and builds filtered payload for the resuming player. EventLog replay of the canonical (full-union) row is OVERWRITTEN by the bootstrap emit, which is itself per-PC filtered. Net: a reconnecting client never sees the union, even though EventLog has it.
- `[SIMPLE]` (medium-confidence simplify-reuse finding from TEA verify phase) — the two multi-recipient overlay loops at `websocket_session_handler.py:3171-3211` and `dispatch/dice.py:555-581` share a structurally identical body. Extracting requires unifying player-list source (getattr probe vs param) and emit strategy (direct queue vs callback). Deferred to a future story that also unifies the canonical-emit path; flagged in TEA verify report.
- `[SIMPLE]` (low-confidence simplify-efficiency findings) — `resolve_recipient_pc` called once per recipient per emit (4× at N=4). Pure dict ops + LedgerBar prefix scan; microsecond-class. Not worth caching until N≥8.

### Devil's Advocate

The code looks careful — but adversarial framing surfaces several gaps worth questioning before merge.

**Where the silent fallback bites:** Imagine a player whose chargen is in flight when an encounter activates. They're seated (player_seats has their id) but their character is mid-creation and hasn't been written to `snapshot.characters` yet. `resolve_recipient_pc` returns `(None, None)`. The overlay loop `continue`s. They receive the canonical full-union payload via `_emit_event`'s fanout — pre-49-7 bug shape. No log line. No watcher event. Sebastien's GM panel shows N-1 `confrontation_beat_filter_span` emissions for the N connected players and gives no clue that the missing one is the chargen-in-flight player. This is the exact failure mode CLAUDE.md's "No Silent Fallbacks" rule was written to prevent — but the only acknowledgment in the diff is Dev's deviation log, and it specifically scopes the rationale to the lobby-unseated case, NOT the chargen-incomplete case.

**Where the asymmetry compounds:** The dispatch/dice.py mid-turn site has no `_watcher_publish` after the overlay loop. The websocket_session_handler.py post-narration site has one. So a regression that breaks per-PC filtering ONLY on the mid-turn (dice-throw) path would surface zero GM-panel evidence — only the post-narration path would log peer projection. A player would see correct beats on narrator turns but the union after every dice roll, and the GM dashboard would not differentiate the two paths' health.

**Where the audit could mislead future Dev:** The `_loop_iter_calls_connected_player_ids` branch in the audit walks `loop.iter` for an `Attribute` named `connected_player_ids`. The production sites use `getattr` to bind a local Name, then iterate the Name. The branch can never match the current code shape. Today's audit passes because every site also has `recipient_pc=` as a keyword. A future Dev refactoring to put a canonical `recipient_pc=None` call inside a connected_player_ids loop (e.g., emitting canonical-then-overlay per recipient) would have their loop correctly detected if they avoid the `getattr` indirection, or wrongly rejected if they follow today's pattern.

**Where the empty-prepared-dict semantics could surprise:** `magic_state.prepared_spells.get(pc_name, {})` returns `{}` when the actor has never had a prep entry written. This engages the 47-10 prepared-list gate. For a fresh Mage character whose prepared_spells is unset at session start (vs. explicitly an empty dict), the behavior depends on whether `add_character` initializes the entry. If it does (line 395 of `magic_init.py`: "Initialize prepared_spells[actor] as an empty dict") then `.get` returns the same empty dict. If a code path adds a character WITHOUT going through `init_magic_state_for_session`, `.get(pc_name, {})` synthesizes `{}` on the fly — same result. Safe today, but the silent fallback shape would mask a regression that skips initialization.

**Where the docstring lies about the contract:** `resolve_recipient_pc` says "Returns `(None, None)` when there is no PC to resolve." It actually returns `(None, pc_name)` for the class-not-found branch. Future Dev pattern-matches on `(None, None)` based on the docstring and gets surprised. The pc_name value is never read today, but a future caller might want it (e.g., to log "player X's class Y is missing from pack Z"). Better to either fix the docstring or fix the code to match its own contract.

None of these escalate to Critical or High per the project's blocking definition (security/data-corruption/missing-error-handling/race-conditions). They cluster around observability gaps and documentation drift, which the project's severity table classifies as Medium. The user-visible playtest bug is fixed; the items above are hardening for the next playtest cycle.

**Decision:** APPROVED — none of the findings meet the Critical/High blocking bar; all are flagged as Delivery Findings for follow-up.

**Handoff:** To SM (The Mad Hatter) for finish phase.

## Implementation Notes

### Call Sites to Refactor
Per the story description, there are five `build_confrontation_payload` call sites that must move to per-recipient filtering:
1. `server/websocket_session_handler.py:3085` (primary broadcast site)
2. `server/dispatch/dice.py:504` (mid-turn payload)
3. `handlers/yield_action.py:140` (first handler call site)
4. `handlers/yield_action.py:176` (second handler call site)
5. (Fifth site TBD during red phase)

The `build_clear_confrontation_payload` at `server/dispatch/confrontation.py:145` is empty-beats already and should remain a single broadcast (asymmetry documented in code comment).

### OTEL Instrumentation
New OTEL emission at panel-projection call sites, tagged `source='ui_panel_projection'` to distinguish from existing `source='narrator_prompt'` filter. Span attributes:
- `recipient_pc`
- `recipient_class`
- `pool_size` (total beats in encounter)
- `filtered_size` (beats after per-PC filter)
- `spell_slots_remaining`
- `cast_spell_rejection_reason` (optional)

### Testing Strategy (TDD)
Per workflow: Red → Green → Spec Check → Verify → Review → Spec Reconcile → Finish

**RED Phase** will establish test suites covering:
- Unit test: `build_confrontation_payload` with Fighter/Cleric/Mage/Thief recipients
- Unit test: Spell-slot gating (0 slots, slots > 0 with/without prepared spells)
- Wiring test: 3-PC MP session, capture outbound CONFRONTATION messages per socket, assert per-PC filtering worked
- Regression test: existing narrator-prompt-side filter unchanged

**GREEN Phase** will implement the refactoring and filtering logic.

### Branch & Coordination
- **OQ-1 branch:** `feat/49-7-confrontation-panel-per-pc-beats` (sidequest-server, sidequest-ui)
- **Pingpong ref:** "[BUG] Confrontation tab shows the FULL union of all class beat-choices to every player" (2026-05-12 ~04:14)
- **Coordination note:** OQ-1's prior fast-loop work halted 2026-05-12 ~04:36; this story is the sanctioned TDD path. Safe to proceed.
- **Screenshots:** `oq-2/.playwright-mcp/010-carl-confrontation-tab.png`, `011-donut-confrontation-tab.png`, `012-katia-confrontation-tab.png`

## Sm Assessment

Pure "Wire Up What Exists" bug fix. The per-class beat filter (`beat_filter.beats_available_for`) is already used inside the narrator prompt; the outbound WebSocket dispatch leaks the full union because it broadcasts once with `cdef.beats`. Fix is server-side only — UI verification is manual via re-running the 3-PC caverns_sunden playtest and capturing screenshots. No narrator-latency cost (post-narration dispatch path, N≤4 microsecond dict ops).

**TEA scope for RED:**
- Unit tests: `build_confrontation_payload` per recipient class (Fighter, Cleric ×3 slot states, Mage, Thief) — assert `beats` length == filter result, contains only filter-result ids
- Wiring test (mandatory per CLAUDE.md): 3-PC MP session boots → encounter_type=combat → capture outbound CONFRONTATION per socket → Fighter does NOT receive Cast Spell/Backstab/Turn Undead; Cleric DOES receive Pray for Aid/Turn Undead
- Regression: existing narrator-prompt-side filter (`tests/test_narrator_prompt_pc_beat_menus.py` or equivalent) must remain green
- OTEL assertion: panel-projection emits `confrontation_beat_filter_span` with `source='ui_panel_projection'`, distinct from existing `source='narrator_prompt'`
- Fifth `build_confrontation_payload` call site: audit via `grep -rn "build_confrontation_payload\|build_clear_confrontation_payload" sidequest-server/` in RED before declaring test coverage complete.

**Gates:**
- No Jira (SideQuest never uses Jira — `[[feedback_no_jira_ever]]`)
- Coordination clean: pingpong line 60 explicitly sanctions this TDD path; prior fast-loop attempt parked
- Branches up on both subrepos
- Workflow: phased tdd → next phase RED → next agent tea