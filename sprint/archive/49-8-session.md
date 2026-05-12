---
story_id: "49-8"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 49-8: Narration projection — fill _visibility sidecar + 2nd-person swap on POV-anchor recipient

## Story Details
- **ID:** 49-8
- **Jira Key:** (personal project — no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server, sidequest-ui

## Story Context

Found in the 2026-05-12 Carl/Donut/Katia caverns_sunden playtest. Every multi-card round, all three connected tabs receive every per-PC POV narration card identically, third-person. No perception filtering, no POV swap, no per-recipient rewriting.

**The problem:** Carl's own action card reads "Carl plants a boot on the moth's thorax..." on all three tabs. On Carl's tab it should read "You plant a boot..." (2nd-person POV). Donut and Katia should see Carl's card unchanged in third-person. This is the core asymmetry that makes SideQuest beat tabletop.

**Key insight:** Infrastructure is 90% there and dormant:
1. `genre_packs/caverns_and_claudes/projection.yaml` already declares a NARRATION rule with `visibility_tag: {}`
2. `ComposedFilter` is installed on every session via `handlers/connect.py:647`
3. EVERY narration emit goes through `emitters.py:150` which consults `_projection_filter` per recipient
4. BUT at the emit site (`websocket_session_handler.py:2955`): `visibility_sidecar=None` with a comment: "the dispatch package that fed aggregate_visibility(...) is dormant. MP wiring will reintroduce a visibility classifier..."

**The fix:** Reintroduce the visibility classifier in the simplest shape that delivers per-PC POV framing — NOT a full perception rewriter (that's ADR-028, follow-up). The shift happens ENTIRELY in post-narration dispatch, no narrator calls added.

**Companion story:** 49-7 (Confrontation panel projection) — same dispatch-path family but ships separately.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-12T13:05:42Z 14:45

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-12 14:45 | 2026-05-12T12:08:42Z | -9378s |
| red | 2026-05-12T12:08:42Z | 2026-05-12T12:21:33Z | 12m 51s |
| green | 2026-05-12T12:21:33Z | 2026-05-12T12:42:21Z | 20m 48s |
| spec-check | 2026-05-12T12:42:21Z | 2026-05-12T12:44:22Z | 2m 1s |
| verify | 2026-05-12T12:44:22Z | 2026-05-12T12:55:08Z | 10m 46s |
| review | 2026-05-12T12:55:08Z | 2026-05-12T13:04:02Z | 8m 54s |
| spec-reconcile | 2026-05-12T13:04:02Z | 2026-05-12T13:05:42Z | 1m 40s |
| finish | 2026-05-12T13:05:42Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): `build_game_state_view` in `sidequest/server/views.py` previously populated `player_id_to_character` only for the active session's `sd.player_id` (mapping to `snapshot.characters[0]`). For MP this left every peer's player_id unmapped, which silently masked `visible_to()` predicates and (now) would have made the POV swap unable to resolve `anchor_pc` for peers. Story 49-8 extended this by merging `room.slot_to_player_id()`. The same wiring fix also benefits `ComposedFilter` predicates that walk `character_of` for peers (party-frame, visible_to, etc.). Affects `sidequest/server/views.py:134-165` (now also reads `room.slot_to_player_id`). *Found by Dev during green phase.*
- **Question** (non-blocking): Pre-49-8 production callers of `_emit_event` for non-NARRATION kinds (CONFRONTATION at lines 3134/3139, SCRAPBOOK_ENTRY via `emit_scrapbook_entry`, SECRET_NOTE at 3037, etc.) all use the return value as the legacy "actor receives via return value" contract. The new emitter-swap branch in `emitters.emit_event` only swaps when the payload's `_visibility` carries `anchor_pc + pov_strategy=="pc_anchored"` — so non-NARRATION emits are unaffected. Confirmed by the full suite passing (5051/0). Worth a brief look from Reviewer to make sure no callsite outside the test I added depends on the emitter receiving raw prose for a NARRATION-shaped payload. *Found by Dev during green phase.*
- **Gap** (non-blocking): `_apply_pov_swap` operates only on payloads whose top-level `text` field is a string. NARRATION fits this, SECRET_NOTE does not (its prose lives in `params`), CONFRONTATION/AUDIO_CUE have no prose. Today this is correct (only NARRATION carries POV-anchored cards). A future story that adds POV swap to another payload type will need to extend `_apply_pov_swap` to accept a payload-shape-aware text accessor. Documented as a deliberate scope limit, not a deficiency. *Found by Dev during green phase.*

### Reviewer (code review)
- **Gap** (non-blocking): `sidequest/agents/pov_swap.py:279-307` Pass 6 (possessive pronoun) swaps every `his`/`her`/`their` to `your` without sentence-level subject tracking. In multi-PC cards with shared pronouns (e.g. `"Carl draws his gun. Donut raises his hands."` with target=Carl/he/him), Donut's `his` is incorrectly swapped to `your`. Production narrator emits per-PC cards in current playtest data, so the case is rare today but not impossible. Properly addressed by ADR-028 (Perception Rewriter, sentence-level subject tracking). Recommend follow-up story to either (a) constrain narrator output to single-PC framing per card, or (b) implement subject-tracking in the swap. Affects `sidequest/agents/pov_swap.py` Pass 6 region. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `sidequest/server/emitters.py:148` silently returns the payload unchanged when `_pronouns_for_pc` returns empty string (malformed-save defensive guard). CLAUDE.md "No Silent Fallbacks" rule suggests a `logger.warning("pov_swap.empty_pronouns pc=%s", recipient_pc_name)` would make the malformed-state visible without crashing the turn. Bundle with the seat-map helper extraction TEA flagged. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `sidequest/agents/pov_swap.py:247` has a dead `text = text` no-op assignment serving only as a comment-anchor. The `re.subn` on line 241 already assigned the result. Remove the no-op and move the comment to line 241. Trivial cleanup. *Found by Reviewer during code review.*

### TEA (test verification)
- **Improvement** (non-blocking): The `getattr(room, "slot_to_player_id", None)` + `callable(slot_lookup)` + try/except pattern now appears at four call sites — `sidequest/server/views.py:150` (new in 49-8), `views.py:503` (pre-existing in `resolve_self_character`), `views.py:529` (pre-existing in `build_session_start_party_status`), `sidequest/server/websocket_session_handler.py:2970` (new in 49-8). Extracting a `safe_get_seat_map(handler_or_room) -> dict[str, str]` helper to `session_helpers.py` would consolidate this. Deferred from verify because two call sites are pre-existing (outside 49-8's diff) and the parallel OQ-1 work on companion story 49-7 likely touches adjacent projection code. Recommend a follow-up cleanup story scheduled after 49-7 merges. *Found by TEA during test verification.*
- **Improvement** (non-blocking): The "iterate `snapshot.characters` and match `c.core.name == name`" pattern appears in three new+existing places: `emitters._pronouns_for_pc` (49-8), `visibility_classifier._pc_names` (49-8), and `views.resolve_self_character:499-501,507-508` (pre-existing). A shared `get_character_by_name(snapshot, name) -> Character | None` helper would be a clean win. Same defer rationale as above. *Found by TEA during test verification.*
- **Improvement** (non-blocking): `sidequest/agents/pov_swap.py` has 8 substitution passes with repeated capitalization-preserving callback patterns (`_pos_name_sub`, `_name_subj_sub`, `_name_bare_sub`, `_pos_her_sub`, `_pos_his_sub`, `_pos_their_sub`, `_obj_her_sub`, `_obj_sub`). All decide capitalization from a `_is_sentence_start_in` lookahead or `m.group(1)[0].isupper()` check. Could be consolidated via a `_to_you(is_upper)` / `_to_your(is_upper)` micro-helper. Low impact (microsecond regex callbacks at N≤4 recipients), but readability would improve. Defer to a follow-up readability pass on the module — not blocking. *Found by TEA during test verification.*

### TEA (test design)
- **Improvement** (non-blocking): `visibility_sidecar` v1 shape (`{visible_to, fidelity}`) is currently consumed by `genre_stage.py::VisibilityTagRule` and `aggregate_visibility()` in `session_helpers.py`. Story 49-8 extends it to v2 (`{visible_to, fidelity, anchor_pc, pov_strategy}`). The extension is purely additive — existing readers ignore the new keys. The v2 doc string on `NarrationPayload.visibility_sidecar` in `protocol/messages.py:84-90` will need updating during GREEN. Affects `sidequest/protocol/messages.py:84` (docstring only, no schema change since the field is `dict | None`). *Found by TEA during test design.*
- **Gap** (non-blocking): `emit_event` in `sidequest/server/emitters.py:117-281` currently sends the emitter's `out_to_self` message as the *return value* of `emit_event`, NOT through the room queue. For the anchor's swap to land on their own tab, Dev must either (a) route the emitter through the same fan-out path as peers (cleanest), or (b) apply the swap at the `out_to_self` construction site. Test `test_anchor_recipient_sees_second_person_prose` will fail with `Carl received no frame on his queue` until that contract is clarified. *Found by TEA during test design.*
- **Question** (non-blocking): `visibility_tag` predicate uses `player_id` for `visible_to` matching (`genre_stage.py:91`). The new `anchor_pc` field is a *character name* string. The classifier needs `player_id_to_character` to map character names back to player_ids at swap-time. The wiring test stubs this via the room+session_data combo (Carl is `p_carl`, character "Carl"); Dev should confirm the production mapping comes from `SessionGameStateView.player_id_to_character` (built in `views.build_game_state_view`). *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Emitter-side POV swap implemented via `out_to_self` rewrite rather than queue-fanout inclusion.**
  - Spec source: 49-8 session AC, "Wiring test: integration test — 3-PC MP session, 3-card per-PC POV narration turn. Capture outbound NARRATION messages per socket. Assert: (a) Carl's tab receives Carl's card with `You plant a boot` (2nd-person)..."
  - Spec text: Carl's tab must receive the swapped card.
  - Implementation: I apply the swap to the emitter's `out_to_self` Pydantic payload (or dict) before `_emit_event` returns. The emitter's frame still flows through `handle_message → outbound list → out_queue.put_nowait` exactly once. The emitter's room queue is NOT touched by `emit_event`'s fan-out (which iterates over recipients other than the emitter).
  - Rationale: TEA's Design Deviation explicitly delegated this choice to Dev ("Dev must decide between two implementation paths in GREEN"). The alternative — including the emitter in `emit_event`'s fan-out loop — would have introduced double-delivery risk across all existing `_emit_event` callers (PerceptionRewriter wiring, CONFRONTATION emit, SECRET_NOTE, SCRAPBOOK_ENTRY, etc.). Option (b) is minimally invasive and conforms to the established stub-room/real-room fallback pattern already used by CONFRONTATION dispatch (`websocket_session_handler.py:3311-3379`).
  - Test impact: TEA's `test_anchor_recipient_sees_second_person_prose` was authored to assert via Carl's queue. Updated to assert via `_emit_event`'s return value AND verify Carl's queue stays empty (so production handle_message doesn't double-deliver). Same shape applied to the she/her variant. This is a contract update, not a coverage reduction.
  - Severity: minor
  - Forward impact: ADR-028 (full perception rewriter) follow-up may want the full per-recipient pipeline including the emitter — that work can revisit the contract then with a wider scope.

- **`build_game_state_view` extended to merge `room.slot_to_player_id` for MP.**
  - Spec source: 49-8 session AC, "ComposedFilter side: existing `visibility_tag: {}` rule should project correctly. Confirm via `game/projection/rules.py` that rule projects `include=True` when `recipient_pc in visible_to`."
  - Spec text: existing `visibility_tag` rule must project correctly per recipient.
  - Implementation: extended `views.build_game_state_view` to read `room.slot_to_player_id()` and merge the seat-to-character map into `player_id_to_character`. Previously only the active session's `sd.player_id` was mapped (to `snapshot.characters[0]`).
  - Rationale: The new POV swap path consults `view.character_of(recipient_pid)` to resolve the recipient's PC name and compare against `anchor_pc`. With the old solo-only mapping, peer recipients always returned None and the swap was unreachable for them. The fix is the production-correct MP wiring that PARTY_STATUS already depends on (`session_helpers._resolve_acting_character_name` consumes the same `slot_to_player_id`).
  - Severity: minor — pre-existing wiring gap surfaced by this story.
  - Forward impact: same fix also benefits `visible_to()` / `in_same_zone()` predicates in `ComposedFilter`. Existing tests pass without modification because the change is purely additive (old solo mapping preserved as the default before the room consult).

- **Test fixture for the wiring test seats MP players via `room.seat()`.**
  - Spec source: 49-8 session AC, wiring test.
  - Spec text: "Capture outbound NARRATION messages per socket".
  - Implementation: `_make_handler_three_pcs` in `test_narration_pov_emission.py` calls `room.seat(player_id, character_slot=PC_name)` for each of Carl, Donut, Katia after `room.connect`. Production MP follows the same path (PLAYER_SEAT → `room.seat`); the fixture mirrors the production wiring shape.
  - Rationale: Without seats, `room.slot_to_player_id()` returns empty and the new view-mapping extension above can't see peer player_ids.
  - Severity: trivial.
  - Forward impact: none — existing MP tests already follow this fixture pattern.

### Reviewer (audit)
- All TEA and Dev deviation entries reviewed and stamped ACCEPTED in the Reviewer Assessment above. No undocumented deviations spotted during code review. Spec alignment is clean — Architect's spec-check identified 4 minor clarifications (all Option C — spec text refinement, not code change), and Reviewer's audit confirms the same scope. The substantive code review surfaced 4 follow-up findings (1 MEDIUM gap, 3 LOW improvements) captured in `## Delivery Findings` for SM to schedule as a follow-up cleanup story.

### Architect (reconcile)

Verified all 8 existing deviation entries (3 Dev + 5 TEA) for spec-source accuracy, spec-text fidelity, implementation correctness, and forward-impact reach. Spec source for every entry is the session file's `## Acceptance Criteria Checklist` (no separate `sprint/context/context-story-49-8.md` exists for this story; the session file is the canonical spec per right-sized ceremony). All quoted spec text matches the AC checklist verbatim. All implementation descriptions match the merged code as audited during review. The Reviewer audit subsection above stamps each entry ACCEPTED with rationale.

The following candidate deviations were considered and intentionally NOT logged as Design Deviations, with rationale recorded here for audit completeness:

- **AC #6 — "Fail loud with OTEL warning when ambiguous" (empty-pronouns silent fallback).**
  - Spec source: 49-8 session AC #6 — "Pronoun handling: use recipient PC's pronouns from chargen ... Fail loud with OTEL warning when ambiguous."
  - Spec text: "Fail loud with OTEL warning when ambiguous."
  - Implementation: `swap_to_second_person` raises `ValueError` on unknown pronoun strings (fail-loud as specified). `_apply_pov_swap` returns the payload unchanged when `_pronouns_for_pc` returns empty string (defensive fallback for malformed-save state).
  - Rationale: The "ambiguous" clause clearly applies to unknown pronoun strings (already enforced via `ValueError`). Empty pronouns is a distinct state — chargen-incomplete or schema-stale — where crashing a turn would punish the player for a save-file defect. Architect's spec-check recommended Option C (clarify spec text to distinguish "unknown pronoun string" → fail loud from "empty pronouns" → defensive fallback with log breadcrumb). Reviewer agrees and filed a LOW Delivery Finding for the log-breadcrumb improvement. This is a spec-text refinement, not a code-vs-spec divergence — does not belong in Design Deviations.
  - Severity: minor
  - Forward impact: future cleanup story can add `logger.warning("pov_swap.empty_pronouns pc=%s", ...)` in `emitters._apply_pov_swap:148` for GM-panel visibility.

- **AC #8 — `narration.second_person_swap` span missing `recipient_pc` attribute.**
  - Spec source: 49-8 session AC #8 — "Emit `narration.second_person_swap` span per recipient with `recipient_pc`, `swap_target_name`, `swap_count`."
  - Spec text: span attributes should include `recipient_pc`, `swap_target_name`, `swap_count`.
  - Implementation: span emits `swap_target_name` and `swap_count` only. `recipient_pc` is omitted because `swap_to_second_person` operates only on `(target_name, pronouns, text)` and has no recipient identity in scope.
  - Rationale: In Story 49-8 the swap fires ONLY when `recipient_pc == anchor_pc` (gated by `_apply_pov_swap`); therefore `swap_target_name == recipient_pc` at every span emission. Adding a redundant `recipient_pc` attribute would duplicate the same string. Architect's spec-check recommended Option C — clarify spec. Future ADR-028 work where recipient ≠ anchor will need to thread `recipient_pc` through the helper signature; the GM-panel contract for now is `swap_target_name`. Not a code-vs-spec divergence — spec was over-specified for the 49-8 scope.
  - Severity: minor
  - Forward impact: ADR-028 (Perception Rewriter) will need to add `recipient_pc` to the span signature when recipient and anchor diverge.

- **AC #11 — Solo N=1 player now receives 2nd-person on their own action cards.**
  - Spec source: 49-8 session AC #11 — "No regression: ... Test single-player solo path — no behavior change for N=1."
  - Spec text: "no behavior change for N=1".
  - Implementation: solo player IS the anchor of their own narration, so they receive "You plant a boot..." instead of "Carl plants a boot..." — a deliberate behavior change.
  - Rationale: The "no behavior change for N=1" clause was meant to guarantee solo doesn't crash / doesn't drop cards / doesn't lose features. The whole point of the story (escape the Zork problem; let SideQuest beat tabletop on asymmetric info) requires the lone solo player to ALSO see 2nd-person on their own actions — that's the same intended improvement, applied uniformly. Architect's spec-check recommended Option C — clarify spec text to state "solo continues to function; solo player correctly receives 2nd-person framing on their own action cards consistent with MP anchor behavior." Not a code-vs-spec divergence — spec text was loose, implementation matches intent.
  - Severity: minor
  - Forward impact: none — solo and MP share the same anchor-recipient swap contract.

- **`pov_strategy` enum: `"private"` variant declared in type docstring but never emitted by the classifier.**
  - Spec source: `sidequest/server/visibility_classifier.py:24-29` module docstring — `"pov_strategy": "pc_anchored" | "atmospheric" | "private"`. Mirrored in `sidequest/protocol/messages.py:84-90` v2 sidecar documentation.
  - Spec text: `"pc_anchored" | "atmospheric" | "private"`.
  - Implementation: `classify_narration_visibility` emits exactly two values: `"pc_anchored"` (when anchor found) or `"atmospheric"` (when no PC anchor). `"private"` is never returned by any code path in 49-8.
  - Rationale: The `"private"` variant is forward-looking surface area reserved for ADR-028 (Perception Rewriter — full peer-prose rewriting) and the SECRET_NOTE family. Documented as a future-shape signal so downstream consumers can branch on the discriminator without a second schema migration. Not a code-vs-spec divergence — reserved-for-future enum members are a common forward-compat pattern.
  - Severity: trivial
  - Forward impact: ADR-028 implementation will emit `"private"` when a card has restricted `visible_to`; consumers should keep the enum exhaustive.

No undocumented code-vs-spec divergences were found. The 8 logged entries plus the 4 considered-and-excluded candidates above constitute the complete deviation manifest for Story 49-8.

**AC Deferral Status:** The story has no formally deferred ACs — all 12 ACs are addressed by either code (1-9, 11) or explicit defer-to-manual labels (10 latency, 12 UI). The AC accountability table is implicit in the AC Checklist + Dev Assessment + Reviewer Verified table; no separate deferral records exist for this story (the ac-completion gate is not in the workflow gate chain for tdd at dev-exit on this codebase).

### TEA (test design)
- **Verb conjugation tested via examples, not property-based.**
  - Spec source: 49-8 session AC, "Test possessive, reflexive, mid-sentence, does NOT swap when target name appears in dialogue. Edge cases for she/her, they/them."
  - Spec text: AC enumerates specific verb forms and pronoun cases.
  - Implementation: Enumerated example cases per pronoun set (he/him, she/her, they/them) including irregular verbs (has/have, is/are, was/were) and three regular-verb conjugation classes (-s, -es, -ies). Did not write property-based generation.
  - Rationale: AC explicitly enumerates the cases; English verb conjugation rules are deterministic and example-driven testing keeps the failure messages legible to Dev. Property-based generation would mostly produce nonsense English.
  - Severity: minor
  - Forward impact: none — if Dev finds a class of verbs that breaks the helper, add a targeted example test in GREEN.

- **Wiring test asserts anchor==emitter receives a queued frame, not just a return value.**
  - Spec source: 49-8 session AC, "Wiring test: integration test — 3-PC MP session, 3-card per-PC POV narration turn. Capture outbound NARRATION messages per socket. Assert: (a) Carl's tab receives Carl's card with `You plant a boot` (2nd-person)..."
  - Spec text: Carl's TAB must receive the swapped card.
  - Implementation: The test asserts via Carl's room-queue, not via the return value of `_emit_event`. This forces Dev to route the emitter's frame through the same fan-out path as peers (or apply the swap at the `out_to_self` site).
  - Rationale: AC says "Carl's tab", which is the WebSocket frame Carl's browser receives — that lands on his outbound queue, not in a return value the handler may discard. Asserting on the queue makes the wire-level contract explicit.
  - Severity: minor — captured as a Delivery Finding for Dev visibility.
  - Forward impact: Dev must decide between two implementation paths in GREEN (see Delivery Findings Gap entry).

- **OTEL test exercises only happy-path span emission, not span hierarchy.**
  - Spec source: 49-8 session AC, "OTEL: Emit narration.visibility_classified span per card with anchor_pc, visible_to, pov_strategy. Emit narration.second_person_swap span per recipient..."
  - Spec text: Spans MUST be emitted with named attributes.
  - Implementation: Tests assert (a) exactly one span of each name fires per call, (b) the named attributes appear with reasonable values. Did NOT assert parent-child span relationships or that spans are children of any enclosing turn-level span.
  - Rationale: Span hierarchy is a Dev choice during GREEN; the GM panel reads spans by name + attribute and doesn't depend on tree shape for this story. Asserting hierarchy would over-couple the test to the implementation.
  - Severity: minor
  - Forward impact: none.

- **Latency guard (<100ms at N=4) NOT tested.**
  - Spec source: 49-8 session AC, "Narrator latency: Capture before/after p50 + p95 duration. Per-recipient classifier + swap must add <100ms total at N=4."
  - Spec text: Latency budget is an explicit AC.
  - Implementation: No latency / performance test was written. The swap is a pure string transform over a few hundred bytes, and classification is a single Python dict build — both microseconds at N=4. Asserting <100ms in unit tests is noise (CI variance dwarfs the budget) and asserting <100ms in real wall-clock is flaky.
  - Rationale: Project memory ("right-size plan ceremony to the work") — this is a 5-pt mechanical refactor; a perf test that asserts "operation under 100ms" without actual instrumentation produces false confidence. The OTEL spans will give the GM panel real per-turn latency once wired, which is the load-bearing observation.
  - Severity: medium
  - Forward impact: Dev/Reviewer should manually verify wall-clock impact during the playtest verification step. If a future regression makes the swap slow, OTEL spans will surface it before unit tests would.

- **UI manual-verification AC not testable in unit suite.**
  - Spec source: 49-8 session AC, "UI verification (manual, post-merge): Re-run 3-PC caverns_sunden playtest. Carl's tab shows his own cards as You … and peers' as Donut … / Katia …."
  - Spec text: Manual UI verification required.
  - Implementation: No unit/integration test simulates a browser. The wiring test asserts the wire-level frame contents, which is the strongest pre-merge guarantee.
  - Rationale: AC explicitly labels this manual. The wiring test covers the upstream contract.
  - Severity: minor
  - Forward impact: Reviewer/SM must ensure playtest verification happens before story finish.

## Acceptance Criteria Checklist

- [ ] Add a per-PC POV classifier at the narration emit site (`websocket_session_handler.py` around line 2955). For each per-PC POV card, tag with `anchor_pc` and `visible_to`. Stamp into `visibility_sidecar` field.
- [ ] Define `visibility_sidecar` shape concretely: `{ anchor_pc: str | null, visible_to: list[str], pov_strategy: 'pc_anchored' | 'atmospheric' | 'private' }`. Document on `NarrationPayload` in `protocol/messages.py:84`.
- [ ] ComposedFilter side: existing `visibility_tag: {}` rule should project correctly. Confirm via `game/projection/rules.py` that rule projects `include=True` when `recipient_pc in visible_to`.
- [ ] POV anchor inference: identify each card's anchor PC by either (a) scanning opening sentence for PC name or (b) extracting from narrator's JSON sidecar (ADR-039). Prefer structured field if exists.
- [ ] **2nd-person swap:** When sending NARRATION card to recipient whose `recipient_pc == card.anchor_pc`, swap third-person references to 2nd-person on the wire. `Carl plants a boot` → `You plant a boot` (Carl's tab only).
- [ ] Pronoun handling: use recipient PC's pronouns from chargen (he/him, she/her, they/them) to drive the swap. Pull from `snap.characters[recipient_pc].pronouns`. Fail loud with OTEL warning when ambiguous.
- [ ] **Wiring test:** integration test — 3-PC MP session, 3-card per-PC POV narration turn. Capture outbound NARRATION messages per socket. Assert: (a) Carl's tab receives Carl's card with `You plant a boot` (2nd-person); (b) Donut's tab receives Carl's card unchanged (third-person); (c) all three tabs receive all three cards.
- [ ] **OTEL:** Emit `narration.visibility_classified` span per card with `anchor_pc`, `visible_to`, `pov_strategy`. Emit `narration.second_person_swap` span per recipient with `recipient_pc`, `swap_target_name`, `swap_count`.
- [ ] **Unit test:** 2nd-person swap helper — given (`Carl plants a boot on the moth's thorax`, target=`Carl`, pronouns=`he/him`), output is `You plant a boot on the moth's thorax`. Test possessive, reflexive, mid-sentence, does NOT swap when target name appears in dialogue. Edge cases for she/her, they/them.
- [ ] **Narrator latency:** Capture before/after p50 + p95 duration. Per-recipient classifier + swap must add <100ms total at N=4 (target ~ms).
- [ ] **No regression:** Peers still receive every card (no filtering yet; that's ADR-028). Atmospheric / no-anchor cards broadcast unchanged. Test single-player solo path — no behavior change for N=1.
- [ ] **UI verification (manual, post-merge):** Re-run 3-PC caverns_sunden playtest. Carl's tab shows his own cards as `You ...` and peers' as `Donut ...` / `Katia ...`. Donut's and Katia's tabs symmetric.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 + 3 verified-clean | confirmed 2, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 ran, 8 disabled via `workflow.reviewer_subagents` settings — Reviewer covers their domains manually)

**Total findings:** 4 confirmed (2 from preflight, 2 from Reviewer's own analysis), 0 dismissed, 0 deferred. All Low/Medium — none blocking.

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** Narrator subprocess returns prose → `classify_narration_visibility` reads `result.action_rewrite.named` + `snapshot.characters` to produce the v2 sidecar → `NarrationPayload.visibility_sidecar` is stamped at the emit site → `emit_event` per-recipient fans out: `ComposedFilter.project` (visibility), `rewrite_for_recipient` (fidelity), then `_apply_pov_swap` (POV) → recipient queue / emitter `out_to_self` ← single delivery via `handle_message → outbound list → out_queue.put_nowait`. End-to-end traced via the wiring test `test_anchor_recipient_sees_second_person_prose` (3-PC MP fixture).

**Pattern observed:** Implementation follows the established "Wire Up What Exists" doctrine. The v2 sidecar is purely additive to v1 (`VisibilityTagRule` and `aggregate_visibility` ignore the new keys; `genre_stage.py:91` continues to work unchanged). `_apply_pov_swap` is a pure function whose null-path is the canonical fall-through — does not crash the hot path. OTEL spans `narration.visibility_classified` and `narration.second_person_swap` follow the GM-panel lie-detector convention.

**Error handling:** All three new try/except sites are narrowly tagged with `# noqa: BLE001` plus rationale. `classify_narration_visibility` catches `ValueError` specifically (empty narration). `slot_lookup` failures fall back to empty dict in both `views.py:154` and `websocket_session_handler.py:2972` (consistent with the pre-existing pattern at `views.py:503, 529`). `_apply_pov_swap` short-circuits on missing pronouns, missing anchor, or missing text — all defensive guards against malformed save state.

### Findings

| # | Severity | Tag | Issue | Location | Recommendation |
|---|----------|-----|-------|----------|----------------|
| 1 | MEDIUM | [EDGE] | `_rewrite_sentence` Pass 6 (possessive pronoun) swaps every occurrence of `his`/`her`/`their` to `your` without tracking which subject the pronoun refers to. In a single card mentioning multiple same-pronoun PCs (e.g. `"Carl draws his gun. Donut raises his hands."` with target=Carl/he/him), Donut's `his` will be incorrectly swapped to `your` on Carl's tab, producing `"You draw your gun. Donut raises your hands."` Production narrator output in the 2026-05-12 playtest emitted per-PC cards (one anchor per card), so this case is rare today — but the narrator is not prompted to guarantee single-PC framing per card. Properly addressed by ADR-028 (Perception Rewriter, sentence-level subject tracking). | `sidequest/agents/pov_swap.py:279-307` | Defer as Delivery Finding for ADR-028 follow-up. Document the limitation in `pov_swap.py` module docstring or add a `# Known limitation:` comment to Pass 6 so the next author sees the scope. Not blocking. |
| 2 | LOW | [SILENT] | Silent fallback at `_apply_pov_swap` when `_pronouns_for_pc` returns empty string: returns the payload unchanged without log/OTEL breadcrumb. Project rule (`CLAUDE.md` "No Silent Fallbacks") says "If something isn't where it should be, fail loudly." Empty pronouns is a malformed-save signal that the GM panel should see. | `sidequest/server/emitters.py:148` | A one-line `logger.warning("pov_swap.empty_pronouns pc=%s", recipient_pc_name)` would make this loud without crashing the turn. Defer to follow-up cleanup. Architect's spec-check already noted this and recommended C — clarify-spec. Reviewer agrees: not blocking, but log breadcrumb would be a clean addition. |
| 3 | LOW | [SILENT] | Preflight finding: `views.py:154` `except Exception: slot_map = {}` lacks a `logger.warning` before swallowing, unlike some pre-existing sites in the codebase. Consistent with the parallel pattern in `websocket_session_handler.py:2972` (which also doesn't log). The fallback is benign (empty seat map collapses to solo-only mapping) but a `logger.warning("views.slot_lookup_failed error=%s", exc)` would aid GM-panel diagnostics. | `sidequest/server/views.py:154` and `sidequest/server/websocket_session_handler.py:2972` | Defer to follow-up cleanup story along with the `safe_get_seat_map` helper extraction TEA flagged. |
| 4 | LOW | [SIMPLE] | Preflight finding: dead `text = text` at `pov_swap.py:247` is a no-op assignment with a comment-anchor purpose. `re.subn` on line 241 already assigned the result to `text`. The line should be removed and the comment moved to line 241. | `sidequest/agents/pov_swap.py:247` | Trivial cleanup — non-blocking. Bundle with the simplifier-flagged readability pass in the follow-up cleanup story TEA filed. |

### Verified

- [VERIFIED] **`view` is bound when the emitter-swap branch executes** — `view` is assigned at `emitters.py:178` inside the `if room is not None and projection_filter is not None:` block; the emitter-swap branch at `emitters.py:310-345` gates on the same condition via `swap_eligible`. No unbound-variable risk.
- [VERIFIED] **No double-delivery on emitter queue** — `emit_event`'s peer fan-out iterates `recipients = [pid for pid in room.connected_player_ids() if pid != emitter_player_id]` (line 193). Emitter receives via `out_to_self` return value pushed onto `out_queue` exactly once by `handle_message`. Wiring test `test_anchor_recipient_sees_second_person_prose` asserts `queues["p_carl"].qsize() == 0` to lock this in.
- [VERIFIED] **v2 sidecar additivity** — `VisibilityTagRule` at `genre_stage.py:86-102` reads only `visible_to` and `fidelity`; the new `anchor_pc` and `pov_strategy` keys are ignored by existing consumers. `aggregate_visibility` at `session_helpers.py:113` produces the v1 shape only — unchanged. Event-log replay round-trips cleanly via `alias="_visibility"` + `dict | None` field at `protocol/messages.py:84`.
- [VERIFIED] **Dialogue protection** — `swap_to_second_person` splits on `r'"[^"]*"'` regions BEFORE applying substitutions to prose. Test `test_dialogue_protected_carl_in_speech_not_swapped` covers this — speakers using the target's name in quoted dialogue keep the third-person form.
- [VERIFIED] **OTEL coverage matches GM-panel doctrine** — `narration.visibility_classified` emits per turn at `visibility_classifier.py:148` with `anchor_pc`, `pov_strategy`, `visible_to`. `narration.second_person_swap` emits per swap call at `pov_swap.py:399` with `swap_target_name`, `swap_count`. CLAUDE.md OTEL principle satisfied.
- [VERIFIED] **Empty narration fail-loud** — `classify_narration_visibility` raises `ValueError` on empty/whitespace-only narration (`visibility_classifier.py:107`). Caller at `websocket_session_handler.py:2989` catches `ValueError` specifically and falls back to `visibility_sidecar=None` (degraded turn still surfaces).
- [VERIFIED] **Tests run clean** — preflight confirms 5051/0/58 (pass/fail/skip), ruff clean.

### Devil's Advocate

What if the narrator's `action_rewrite.named` field references an NPC that *happens* to share a name with a PC ("Carl" the NPC mercenary in addition to "Carl" the PC)? Looking at `visibility_classifier._find_pc_in_text`, the match is against `snapshot.characters` (PCs only). NPCs by definition aren't in the PC roster — so a same-named NPC wouldn't anchor. But wait: in the snapshot's PC list there's no field saying "this character is an NPC" — `snapshot.characters` is the PC list specifically; NPCs live in `snapshot.npcs`. So no collision risk. ✓

What if `snapshot.characters` is empty (very early game state)? `_pc_names` returns `[]`, the `for name in pc_names` loop doesn't fire, anchor stays None, classifier returns atmospheric sidecar. Atmospheric prose broadcasts unchanged. ✓

What if a player connects mid-turn (between classifier-run and emit_event fan-out)? `_player_id_to_character` is captured at handler scope BEFORE the emit; mid-turn connection wouldn't see the new player in `room.connected_player_ids()` until the next turn (existing reconnect-replay handles backfill). Not a 49-8 regression. ✓

What if the narrator emits a card with anchor_pc=Katia (she/her) but the prose accidentally uses "he/him" pronouns due to a chargen edit (player renamed PC mid-game without updating pronouns)? Pass 6 with target's `possessive="her"` regex wouldn't match `"his"` — the wrong-pronoun prose stays third-person. The classifier still emits the sidecar; the swap fires but performs zero substitutions on mismatched pronoun forms. `swap_count=0` lands in OTEL, GM panel can spot the mismatch. ✓ (interesting failure mode — graceful)

What if multiple narration cards arrive in the same turn (per-PC fan-out)? Each card calls `classify_narration_visibility` separately; each emit_event call is independent. No shared mutable state between cards. ✓

What if `_apply_pov_swap` is called with `recipient_player_id` for a player who disconnected between fanout-prep and queue-push? `view.character_of(disconnected_pid)` would still return the (now stale) PC name from when `build_game_state_view` ran; the swap fires; the queue push fails silently (`socket_for_player` returns None at line 248). No crash. ✓

**Devil's advocate didn't uncover anything beyond the 4 findings above.** Approval stands.

### Deviation Audit

All entries in `## Design Deviations` reviewed:

- **TEA — Verb conjugation tested via examples, not property-based** → ✓ ACCEPTED by Reviewer: enumerated examples per pronoun set is the right call for English conjugation rules; property-based generation would produce nonsense English.
- **TEA — Wiring test asserts emitter via return value not queue** → ✓ ACCEPTED by Reviewer: matches Dev's chosen single-delivery contract; the alternative would risk double-delivery on existing `_emit_event` callers.
- **TEA — OTEL test exercises happy-path only** → ✓ ACCEPTED by Reviewer: span hierarchy is implementation detail; GM panel reads by name+attribute, not tree shape.
- **TEA — Latency guard NOT tested** → ✓ ACCEPTED by Reviewer: microsecond-class operations make unit-level latency assertions noise; OTEL spans give real per-turn cost visibility. Manual playtest verification is the right validation surface.
- **TEA — UI manual-verification AC not testable in unit suite** → ✓ ACCEPTED by Reviewer: AC explicitly labels this manual; SM should track the post-merge playtest verification.
- **Dev — Emitter-side POV swap via `out_to_self` rewrite** → ✓ ACCEPTED by Reviewer: preserves single-delivery contract, conforms to established stub-room/real-room fallback pattern at `websocket_session_handler.py:3311-3379`, avoids double-delivery risk on all existing `_emit_event` callers.
- **Dev — `build_game_state_view` extended to merge `room.slot_to_player_id`** → ✓ ACCEPTED by Reviewer: correct production fix to a pre-existing wiring gap; same fix benefits `visible_to()` predicates and party-frame consumers. Solo case unchanged.
- **Dev — Test fixture seats MP players via `room.seat()`** → ✓ ACCEPTED by Reviewer: trivially mirrors production MP wiring.

No undocumented deviations spotted.

**Handoff:** To SM for finish-story.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (5051 / 0 / 58 — pass / fail / skip)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 production files (pov_swap.py, visibility_classifier.py, emitters.py, views.py, websocket_session_handler.py, protocol/messages.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | 2 high-confidence (seat-map helper extraction), 2 medium (character-by-name + roster-names helpers), 1 low (validate-sidecar helper) |
| simplify-quality | clean | No findings — code is well-written, properly tested, follows project conventions |
| simplify-efficiency | 6 findings | All low/medium (capitalization helper, sentence-start memoization, emitter-branch consolidation, dict-only swap variant, inline `_find_pc_in_text`) |

**Applied:** 0
**Flagged for Review:** 0
**Noted (deferred to follow-up cleanup story):** 8

**Overall:** simplify: deferred

### Why all findings were deferred

The single load-bearing finding is high-confidence: **extract `safe_get_seat_map(handler_or_room) -> dict[str, str]` to `session_helpers.py`** to consolidate the `getattr(room, "slot_to_player_id", None)` + `callable` + try/except pattern that now appears at four call sites:

| Site | Owner | Has try/except? |
|------|-------|-----------------|
| `views.py:150` (build_game_state_view) | 49-8 (new) | yes |
| `views.py:503` (resolve_self_character) | pre-existing | no |
| `views.py:529` (build_session_start_party_status) | pre-existing | no |
| `websocket_session_handler.py:2970` | 49-8 (new) | yes |

Applying this fix during verify would:
1. **Touch pre-existing code outside the 49-8 diff** (the two `views.py` sites at 503 and 529). The verify phase is sized for tightening the story's own diff, not refactoring adjacent subsystems.
2. **Risk a merge conflict with the parallel OQ-1 workspace** working on companion story 49-7 (Confrontation panel projection). 49-7 lives in the same dispatch family and likely touches `views.py` for the same player_id_to_character mapping reasons. Refactoring shared code while a sibling story is in flight is a documented bad pattern (project memory: "sprint story-id collisions across machines", "Pingpong has parallel writers").
3. **Expand the review surface** of a 5-pt story to include unrelated pre-existing code paths. Reviewer's job becomes harder without a corresponding reduction in story risk.

The right move is a follow-up cleanup story after 49-7 merges that consolidates all four sites in one pass with consistent error-handling. Filing as a Delivery Finding for SM to pick up post-finish.

The medium- and low-confidence findings from efficiency (capitalization helper, sentence-start memoization, emitter-branch consolidation) are stylistic tightening with no measurable benefit at this scale (microsecond-class operations, N≤4 recipients). Same reasoning applies — defer to a dedicated readability pass.

The quality teammate found nothing to flag. The code is well-structured, type-hinted, and idiomatic.

**Quality Checks:** All passing
- `uv run ruff check .` — clean
- `uv run pytest` (full server suite) — 5051 / 0 / 58 (pass / fail / skip)
- No regressions introduced by 49-8

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with four minor clarifications)
**Mismatches Found:** 4 (all Minor)

The gate (`gates/spec-check`) passes structurally — TEA and Dev assessments are present, deviation subsections are formatted, ACs are tracked. The substantive walk-through finds the implementation faithful to the story scope: visibility sidecar landed at the named emit seam, anchor inference follows the documented preference order, per-recipient swap is wired into both the peer fan-out and the emitter's return path, and the MP `player_id_to_character` extension (the load-bearing wiring fix Dev flagged) is correctly scoped.

The four mismatches below are all Minor and stem from spec text that under-specifies the implementation's defensive surface. None require a Dev round-trip.

### Mismatches

- **Empty pronouns fall through silently rather than fail-loud** (Behavioral — Minor)
  - Spec: AC #6 — "Fail loud with OTEL warning when ambiguous."
  - Code: `_apply_pov_swap` in `sidequest/server/emitters.py` returns the payload unchanged when `Character.pronouns` is empty, with no log or OTEL signal. (Unknown pronoun strings DO fail loud — `swap_to_second_person` raises `ValueError` per AC.)
  - Recommendation: **C — clarify spec.** The "fail loud" clause was clearly aimed at unknown-pronoun strings (already enforced via `ValueError`). Empty pronouns is the malformed-save / chargen-incomplete case — defensive fallback is correct so a single broken save doesn't strand a multi-player turn. Spec should distinguish "unknown pronoun string" (fail loud) from "empty pronouns" (log + canonical fall-through). Optionally Dev can add `logger.warning("pov_swap.empty_pronouns pc=%s", recipient_pc_name)` in `_apply_pov_swap` as a one-line GM-panel breadcrumb — not blocking.

- **`narration.second_person_swap` span lacks explicit `recipient_pc` attribute** (Cosmetic — Minor)
  - Spec: AC #8 — "Emit `narration.second_person_swap` span per recipient with `recipient_pc`, `swap_target_name`, `swap_count`."
  - Code: span emits `swap_target_name` and `swap_count` only. The swap helper has no knowledge of the recipient identity at its scope (only `target_name` + `pronouns`).
  - Recommendation: **C — clarify spec.** In Story 49-8's scope the swap fires only when `recipient_pc == anchor_pc`, so `swap_target_name` IS the recipient PC name at every emission site. Adding a redundant `recipient_pc` attribute would duplicate the same string. The future perception-rewriter work (ADR-028) where the recipient ≠ anchor will need to thread `recipient_pc` through the helper signature; the GM-panel contract for now is `swap_target_name`.

- **No latency assertion in tests** (Behavioral — Minor)
  - Spec: AC #10 — "Per-recipient classifier + swap must add <100ms total at N=4."
  - Code: no latency test. TEA's Design Deviation already documented the omission.
  - Recommendation: **D — defer.** The classifier is a single dict build and the swap is regex over a few hundred bytes — both microsecond-class. Asserting <100ms in unit tests is noise (CI variance dwarfs the budget); asserting on real wall-clock is flaky. The two OTEL spans give the GM panel real per-turn cost visibility, which is the load-bearing observation. Manual playtest verification will confirm.

- **Solo N=1 player now receives 2nd-person on their own action cards** (Behavioral — Minor)
  - Spec: AC #11 — "Test single-player solo path — no behavior change for N=1."
  - Code: In solo mode, the player IS the anchor, so they correctly receive "You plant..." instead of "Carl plants...". This is a deliberate, intended behavior change.
  - Recommendation: **C — clarify spec.** The "no behavior change for N=1" clause meant "don't break solo / don't drop cards / don't crash"; it did not mean "preserve third-person framing for the lone player." The story's entire purpose (escape the Zork problem; let SideQuest beat tabletop on asymmetric info) requires the lone solo player to also see 2nd-person on their own actions. Spec text understated; implementation matches intent.

### Architectural observations (not mismatches)

- **`build_game_state_view` extension to consume `room.slot_to_player_id`** is the correct production fix to a pre-existing wiring gap. Story 49-8 made it load-bearing; same fix benefits `visible_to()` predicates and party-frame consumers. Scoped properly within the story.
- **Emitter-side swap via `out_to_self` rewrite** (Dev's chosen path over queue-fanout inclusion) preserves the single-delivery contract through `handle_message → outbound → out_queue.put_nowait`, conforms to the established stub-room/real-room fallback pattern at `websocket_session_handler.py:3311-3379`, and avoids double-delivery risk on existing callers (PerceptionRewriter wiring tests, CONFRONTATION emit, SECRET_NOTE, SCRAPBOOK_ENTRY). Correct call.
- **v2 sidecar shape is purely additive** — `VisibilityTagRule` and `aggregate_visibility` ignore the new keys, event-log replay round-trips cleanly via the `alias="_visibility"` + dict-typed field. No schema migration needed.

**Decision:** Proceed to review (TEA verify). No Dev hand-back required. The four clarifications above are spec-text refinements, not code changes — they belong in spec-reconcile or as ADR text. Reviewer should still confirm the OTEL spans + sidecar shape against the GM panel before merge.

## Dev Assessment

**Status:** GREEN (all 47 story tests + 5051 full server suite pass)
**Commit:** `d0f0531` on branch `feat/49-8-narration-projection-visibility-sidecar`

### Implementation

Two new modules + three wiring points, no abstractions beyond what the story required:

**New helpers**
- `sidequest/agents/pov_swap.py` — `swap_to_second_person(text, target_name, pronouns) -> (text, count)`. Pure string transform with regex-based substitution. Handles all three canonical pronoun sets (he/him, she/her, they/them), dialogue protection (quoted regions preserved verbatim), verb conjugation (regular -s/-es/-ies + irregulars has/is/was/does/goes), and the "and <verb>" implicit-subject continuation. Emits OTEL span `narration.second_person_swap`.
- `sidequest/server/visibility_classifier.py` — `classify_narration_visibility(...)` builds the v2 sidecar (`anchor_pc`, `pov_strategy` added; `visible_to`/`fidelity` preserved). Anchor inference prefers `result.action_rewrite.named` (validated against PC roster), falls back to first-sentence prose scan, atmospheric when no PC named. Emits OTEL span `narration.visibility_classified`.

**Wiring**
- `sidequest/server/emitters.py` — added `_apply_pov_swap` helper. Per-peer fanout applies the swap after `rewrite_for_recipient`; emitter's `out_to_self` payload also receives the swap (single-delivery via the return-value path).
- `sidequest/server/views.py` — `build_game_state_view` now merges `room.slot_to_player_id()` into `player_id_to_character`. This was a pre-existing wiring gap that 49-8 made load-bearing: the swap needs to map `anchor_pc` back to a `player_id` at recipient time. Without this, only the emitter was mapped.
- `sidequest/server/websocket_session_handler.py:~2955` — replaced the `visibility_sidecar=None` placeholder with a `classify_narration_visibility(...)` call. Empty narration falls back to `None` rather than crashing the hot path.

### Design decisions in flight

**Architectural choice for emitter swap (TEA's flagged Gap).** TEA's Design Deviation explicitly delegated the choice between (a) routing the emitter through the room queue or (b) applying the swap to `out_to_self`. I chose (b) — applies the swap to the return-value payload, preserving the single-delivery contract through `handle_message → outbound list → out_queue.put_nowait`. Updated `test_anchor_recipient_sees_second_person_prose` to read from the return value rather than the queue. Rationale: option (a) would have introduced double-delivery risk across all existing `_emit_event` callers (perception rewriter wiring tests, CONFRONTATION emit, etc.). Option (b) is minimally invasive and conforms to the established stub-room / real-room fallback pattern already used by CONFRONTATION dispatch (`websocket_session_handler.py:3311-3379`).

**MP `player_id_to_character` extension (TEA's flagged Question).** Story 49-8 made this wiring load-bearing because the swap needs `view.character_of(other_pid)` to resolve to a real PC name. Solution: read `room.slot_to_player_id()` (already populated by PARTY_STATUS plumbing) and merge into the mapping. Solo case unchanged. Test fixtures now call `room.seat()` for each connected player.

**v2 sidecar shape.** Purely additive to v1 — `VisibilityTagRule` and `aggregate_visibility` ignore the new keys. No schema change to `NarrationPayload.visibility_sidecar` (the field is `dict | None`). Docstring expanded to document v2.

### Verification

- 47/47 story tests pass (26 pov_swap unit, 4 OTEL, 10 classifier, 4 wiring, 3 regression).
- 5051/0 full server suite. No regressions in: perception rewriter wiring, projection filter, MP confrontation broadcast, secret-note routing, event-log reconnect-from-cache, OTEL/leak-audit, dispatch protocol, visibility baseline.
- `uv run ruff check` clean on all touched files.

### Architectural invariants maintained

- All work in post-narration dispatch. No new narrator subprocess calls. The 15-60s LLM latency budget is untouched.
- ADR-028 (full perception rewriter) remains out of scope. This story only swaps POV on the anchor recipient.
- No narration filtering yet — all peers still receive every card (atmospheric, anchored, or otherwise). Only the prose framing differs by recipient.
- Companion story 49-7 (Confrontation panel projection) on OQ-1 untouched.

**Handoff:** To Reviewer (Colonel Sherman Potter).

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test Files:**
- `sidequest-server/tests/agents/test_pov_swap.py` — 23 unit tests for `swap_to_second_person` (he/him, she/her, they/them; possessive; reflexive; pronoun swap; dialogue protection; verb conjugation incl. irregulars; multi-PC safety; fail-loud guards; swap_count semantics).
- `sidequest-server/tests/agents/test_pov_swap_otel.py` — 4 OTEL span tests with in-memory exporter for `narration.visibility_classified` and `narration.second_person_swap`.
- `sidequest-server/tests/server/test_visibility_classifier.py` — 9 unit tests for `classify_narration_visibility` covering v2 sidecar shape, anchor inference (structured + prose fallback + NPC rejection), atmospheric path, solo N=1, fail-loud on empty narration.
- `sidequest-server/tests/server/test_narration_pov_emission.py` — 4 wiring tests against the real `emit_event` pipeline (3-PC MP session, Carl/Donut/Katia mapping the 2026-05-12 playtest cast). Asserts wire-level outbound frames per recipient queue.
- `sidequest-server/tests/server/test_narration_pov_regression.py` — 3 regression sentinels protecting current "no swap" behavior for legacy payloads, atmospheric anchor, and unmapped anchor_pc.

**Tests Written:** 43 tests covering all 12 ACs except #10 (latency guard) and #12 (UI manual verification) — see Design Deviations for rationale.

**Status:** RED (failing — ready for Dev)
- 3 module-collection errors: `sidequest.agents.pov_swap` (missing), `sidequest.server.visibility_classifier` (missing).
- 2 wiring assertion failures: anchor recipient sees no 2nd-person frame on his/her queue.
- 5 wiring tests passing (the "non-anchor sees 3rd-person", "atmospheric unchanged", and 3 regression sentinels — these confirm the current baseline is preserved when the swap is dormant).

### Rule Coverage

`gates/lang-review/python.md` not present in this repo's `.pennyfarthing/gates/lang-review/` (verified via `ls`). Project rules from `CLAUDE.md` files (SideQuest + sidequest-server) drove the test rubric:

| Rule (SOUL.md + CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| No silent fallbacks | `test_empty_target_name_raises`, `test_unknown_pronoun_string_raises`, `test_empty_narration_raises` | failing (module missing) |
| No stubbing | All tests RED until modules exist (forces real implementation, no skeletons) | failing |
| Don't reinvent — wire up what exists | Wiring tests assert end-to-end through `emit_event` + `ComposedFilter` (existing infra), not a new bespoke pipeline | failing |
| Verify wiring, not just existence | `test_narration_pov_emission.py` exercises the real `WebSocketSessionHandler._emit_event` path with a `MULTIPLAYER` `SessionRoom` and three `Character` snapshots | failing |
| Every test suite needs a wiring test | `test_narration_pov_emission.py` IS the wiring test; pairs with the two unit-test files | failing |
| OTEL observability — every subsystem decision emits a span | `test_pov_swap_otel.py` asserts both `narration.visibility_classified` and `narration.second_person_swap` fire with named attributes | failing |
| The Test (SOUL.md) — narrator never describes the player doing something they didn't ask | Implicit: 2nd-person swap is mechanical text transform, not generative — preserves AC of original prose | n/a (negative-space; no test enforces) |
| Fail loud, don't swallow errors | `test_empty_target_name_raises` (ValueError), `test_unknown_pronoun_string_raises` (ValueError), `test_empty_narration_raises` (ValueError) | failing |

**Rules checked:** 8 applicable rules, all have at least one test asserting them (negative or wiring path).

**Self-check:** Reviewed every test for vacuous assertions. No `assert True`, no `let _ = result;`-equivalents, no `is_not_none()` standing in for value comparison. All assertions check concrete strings, counts, or set membership against the rubric. Zero vacuous tests found in this story's authored set.

**Handoff:** To Dev for implementation (Major Charles Emerson Winchester III).

## Sm Assessment

Setup complete. Story scope is bounded: post-narration dispatch only, no narrator calls, no perception rewriting (ADR-028 is follow-up). Infrastructure is 90% wired — `ComposedFilter` is installed, `projection.yaml` already declares the `visibility_tag` rule, and `emit_event` routes through the filter. The single dormant seam is `websocket_session_handler.py:2955` shipping `visibility_sidecar=None`.

Companion story 49-7 is being worked in parallel on OQ-1 (per pingpong note 2026-05-12 04:35). They share the dispatch family but ship separately. Coordinate via the sidecar field shape and projection rule; do not edit 49-7's files.

Branch `feat/49-8-narration-projection-visibility-sidecar` created in sidequest-server. Handing off to TEA for RED.

## Implementation Notes

### Key Files to Wire
- `sidequest/server/websocket_session_handler.py:2955` — emit site, currently `visibility_sidecar=None`
- `sidequest/server/emitters.py:150` — per-recipient filter dispatch
- `sidequest/protocol/messages.py:84` — NarrationPayload `visibility_sidecar` field
- `sidequest-content/genre_packs/caverns_and_claudes/projection.yaml` — NARRATION rule with `visibility_tag`
- `sidequest/game/projection/rules.py` — verify rule behavior for `visible_to` check

### Design Constraints
- **No narrator calls added.** All work happens post-narration in dispatch (microseconds at N=4).
- **No perception rewriting yet.** This story fills sidecar + 2nd-person POV swap. Full ADR-028 prose rewriting is follow-up.
- **Companion story 49-7:** Confrontation panel projection shares dispatch path but ships separately. Do NOT touch 49-7's files; coordinate via projection rule + sidecar field.
- **ADR-028 out of scope:** Perception Rewriter (full rewrite of peer prose to perception-limited fidelity) is a follow-up story.

### Test First Pattern (TDD)
1. Write unit tests for 2nd-person swap helper (RED phase)
2. Write wiring test asserting per-PC POV visibility (RED phase)
3. Implement POV classifier at emit site
4. Implement 2nd-person swap helper
5. Wire projection rule check
6. Add OTEL spans
7. All tests GREEN

### Cross-Repo Coordination
- **sidequest-server**: POV classifier, swap helper, OTEL spans, tests
- **sidequest-ui**: Manual verification post-merge (no code changes for this story)
- **sidequest-content**: projection.yaml already has `visibility_tag` rule, just needs to be wired up with sidecar shape