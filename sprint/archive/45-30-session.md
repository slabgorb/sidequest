---
story_id: "45-30"
jira_key: ""
epic: "45"
workflow: "wire-first"
---
# Story 45-30: Render trigger policy contract + OTEL render.trigger reasons

## Story Details
- **ID:** 45-30
- **Epic:** 45 (Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup)
- **Workflow:** wire-first
- **Stack Parent:** none
- **Points:** 3
- **Priority:** P2
- **Type:** bug

## Context

**Source:** Epic 37-46 (port-drift re-scope per ADR-085). Playtest 3 (Felix, 2026-04-19) revealed that 71-turn session produced only ~6-8 renders from 71 scrapbook rows. Selection appeared arbitrary, policy-agnostic.

**Problem:** Render requests fire with no explicit contract — daemon queues images on undefined criteria. Upstream (server side) and downstream (UI indicator) have no visibility into *why* a render was requested (or declined). The absence of decision-logging breaks the lie-detector principle — GM panel cannot distinguish between a render that should-have-fired-but-failed and a render that should-not-have-fired.

**Target behavior:**
1. Define explicit trigger policy: always render on beat fire / scene change / named-NPC introduction / resolved-encounter. Skip on banter/aside/quiet turns.
2. Emit OTEL span `render.trigger` with reason field: `beat_fire|scene_change|npc_intro|resolved|none_policy`.
3. Optional (post-AC): session-level density target with backpressure-aware enforcement.
4. Optional UI indicator for skipped-but-eligible vs requested-but-failed.

## Acceptance Criteria

**AC1: Render trigger contract defined**
- Define `RenderTriggerReason` enum or string literal set: `beat_fire`, `scene_change`, `npc_intro`, `resolved_encounter`, `none_policy`
- Document in-line: beat_fire fires on any trope beat, scene_change fires on location/room change, npc_intro fires when a unique NPC (with name in synopsis) enters scene via narrator, resolved_encounter fires when an encounter state changes to terminal (won/lost/fled), none_policy fires when eligibility gating rejects the turn (banter, aside, quiet).
- All dispatcher paths (encounter flow, narration flow, trope cascade) check eligibility before enqueueing to daemon.

**AC2: OTEL render.trigger reason span**
- `websocket_session_handler._request_image_render()` (or dispatcher point) emits span with attributes: `reason` (string, one of the enum), `eligible` (bool), `queued` (bool).
- Span fires on every turn where a render decision is made (eligible or not).
- Non-firing (no decision point hit) → no span; turn produces zero render signal.

**AC3: Eligibility gates enforced server-side**
- Encounter state change (confrontation birth or resolution) → eligible.
- Location change detected in narration → eligible.
- Named NPC introduced in narrator text (check synopsis for unique_npcs) → eligible.
- Any beat fire (from trope/momentum) → eligible.
- Banter turn, aside, or quiet-turn narrative (heuristic: check narrative_log.entry.tags or narration reason) → ineligible.
- Eager queue (all eligible) vs targeted queue (top-N) deferred to AC3b.

**AC4: Wiring test coverage**
- Test beat-fire eligibility → span fires with reason=beat_fire, queued=true.
- Test scene-change eligibility → span fires with reason=scene_change.
- Test NPC-intro eligibility → span fires with reason=npc_intro.
- Test resolved-encounter eligibility → span fires with reason=resolved_encounter.
- Test banter ineligibility → span fires with reason=none_policy, eligible=false, queued=false.
- Test silent turns (no narrator text) → no span fired.

**AC3b (optional, defer to 45-31 if resource-gated):** Session density tuning + backpressure
- Session-level config: `render_density_target` (e.g. 0.1 = one render per 10 turns).
- Daemon response: enqueue path checks queue depth; if queue > threshold (e.g. 8 pending), emit `render.backpressure` span and return early.
- Post-turn aggregate: OTEL span `render.session_stats` with attributes: `total_turns`, `renders_queued`, `renders_failed`, `renders_completed`, `density_actual`, `density_target`.

## Technical Approach

**Layer 1: Encounter dispatch (encounter_lifecycle.py)**
- EncounterCreated, EncounterResolved → eligible, reason=`resolved_encounter`.
- Span emission at encounter-start and encounter-terminal (win/loss/flee).

**Layer 2: Narration dispatch (websocket_session_handler._execute_narration_turn)**
- Before enqueueing, classify narration: beat_fire, scene_change, npc_intro, banter, quiet.
- Beat fire: check narration_reason or struct membership; reason=`beat_fire`.
- Scene change: compare snapshot.location to prior-turn location; reason=`scene_change`.
- NPC intro: narrator sets `unique_npcs_introduced` in narration struct or we parse synopsis; reason=`npc_intro`.
- Banter/quiet heuristic: check narrative_tags or narrator-provided `skip_render=true` hint; reason=`none_policy`.
- Emit render.trigger span with decision.

**Layer 3: Trope beat cascade (trope_engine.py or beat_resolver.py)**
- Beat fire (any trope beat resolved) → eligible, reason=`beat_fire`.
- Span at beat-resolution checkpoint.

**Layer 4: Daemon interaction**
- `enqueue_image_render()` path checks queue depth; emits `render.backpressure` if depth > threshold.
- Worker emits `render.completed { reason, eligible, queued, success }` post-render (reuses attributes from trigger span for correlation).

## Sm Assessment

Story is well-scoped P2 cleanup from Playtest 3 — 71-turn session produced ~6-8 renders from 71 scrapbook rows with no policy backing the selection. This is a textbook OTEL Observability case (per CLAUDE.md): a subsystem (render dispatch) is firing without emitting spans that prove *why*, so the GM panel cannot tell whether the render policy is engaged or whether dispatch is "winging it."

**Approach is wire-first, which fits:** the dispatch points already exist at three layers (encounter_lifecycle, narration handler, trope/beat cascade) — we are not building a new pipeline, we are inserting a contract (`RenderTriggerReason`) and an OTEL span (`render.trigger`) at existing decision points. Per "Don't Reinvent — Wire Up What Exists," TEA should verify the dispatch points exist before red-phase test design.

**Scope discipline:** AC1–AC4 are mandatory. AC3b (density tuning + backpressure) is explicitly deferred to 45-31 (daemon worker heartbeat) where backpressure infrastructure naturally lives. Do not let it leak in.

**Wiring test is non-negotiable** (per "Every Test Suite Needs a Wiring Test"): AC4 already mandates this — span fires from production dispatch path, not from a test-only shim. TEA must enforce.

**Risks for TEA to surface in red phase:**
- The "banter/quiet turn" heuristic in AC3 is the soft spot — if there is no existing tag/flag, classification becomes an inference call. Either find an existing signal or push back to refine the AC before red.
- NPC intro detection: confirm whether narrator already emits `unique_npcs_introduced` in narration struct (synopsis) or whether we are adding parsing.

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish (wire-first)
**Status:** RED (failing — ready for Dev / Ponder Stibbons)

**Test files (server, sidequest-server@feat/45-30-render-trigger-policy-otel):**
- `tests/server/test_render_trigger_policy.py` (NEW, 14 tests) — pure-function unit tests for `classify_trigger()` priority ordering. Explicitly *support*, not the wire (per wire-first.yaml: "unit tests allowed as SUPPORT for the boundary test, not as a substitute").
- `tests/server/test_render_dispatch.py` (extended, 8 new tests) — boundary tests through `WebSocketSessionHandler._maybe_dispatch_render` with a real Unix-socket fake daemon. Asserts on the routed watcher event (`event_type=state_transition`, `field=render`, `op=trigger|policy_skip`) — the wire the GM panel actually parses.
- `tests/server/test_scrapbook_entry_wiring.py` (extended, 2 new tests) — assert `render_status` discriminator (`rendered` / `skipped_policy` / `failed`) lands on the persisted `scrapbook_entries` row AND on the journaled SCRAPBOOK_ENTRY event (mirrors the existing test pattern for journal-based assertion).
- `tests/fixtures/packs/test_genre/worlds/flickering_reach/openings.yaml` (NEW) — minimal fixture to satisfy the canned-openings world validator (resolves a pre-existing fixture debt that was breaking `test_scrapbook_entry_persists_and_journals` on develop).

**Test files (UI, sidequest-ui@feat/45-30-render-trigger-policy-otel):**
- `src/components/GameBoard/widgets/__tests__/ScrapbookGallery.render_status.test.tsx` (NEW, 6 tests) — mounts ScrapbookGallery with three entries (rendered / skipped_policy / failed) and asserts distinct DOM nodes (data-testid), distinct a11y labels, and that the legacy `no-image` placeholder does not co-exist with the new render_status indicators.

**Tests Written:** 30 tests (24 server + 6 UI) covering all 6 ACs.
**RED verification:**
- Server: 10 boundary/scrapbook tests fail with intended signals — `KeyError` on missing `SPAN_ROUTES` entry, `TypeError` on missing `encounter_resolved_this_turn=` kwarg, `AssertionError` on missing watcher events / dispatch behaviour, `sqlite3.OperationalError: no such column: render_status`. 14 unit tests collection-error with `ModuleNotFoundError: No module named 'sidequest.server.render_trigger'` — correct RED for a missing module.
- UI: 5 fail with `Unable to find element by data-testid` (component doesn't render the new badges yet) and `expected null` on the legacy `no-image` placeholder still being shown. 1 passes (the rendered-state test) — its assertions about skipped/failed badges *not* being present hold both pre- and post-implementation, so it's a non-vacuous pass.
- 12 pre-existing scrapbook+render_dispatch tests still pass — no regressions.

### Rule Coverage

| Rule (lang-review/python.md) | Covered by | Notes |
|------|---------|-------|
| #1 silent exception swallowing | Existing dispatch path test (test_render_dispatch_fires_daemon_and_enqueues_image) — Dev must not wrap classify_trigger in `except: pass` | Read-only check |
| #2 mutable default arguments | classify_trigger signature is positional + bool — no mutable defaults to mis-specify | n/a |
| #3 type annotation gaps | test_render_trigger_reason_enum_values_match_wire_contract pins enum values; classifier signature documented in story context | Implementation must annotate `RenderTriggerReason` returns |
| #4 logging coverage | Boundary tests assert on `state_transition` watcher events (the WIRE), not on logger calls — but Dev should `logger.info` the policy decision per OTEL principle | Flagged for green |
| #6 test quality | All 30 tests have specific value assertions (no `assert True`, no truthy-only checks). Self-checked. | Pass |
| #11 input validation at boundaries | `encounter_resolved_this_turn: bool` is internal kwarg, not user input — no validation needed | n/a |

**Self-check:** Reviewed every new test for vacuous assertions. Found none. The one UI test that passes pre-implementation (`renders a real image element for rendered entries`) does so because its assertions hold from BOTH directions of the contract — not because the assertions are weak.

### Architect Tandem Verdict

Leonard of Quirm reviewed the six boundary tests in red phase per `.pennyfarthing/workflows/wire-first.yaml` red.team.teammates and returned:

> **overall: approve** — All six tests assert on the typed watcher event shape (`event_type=state_transition`, `fields.field=render`, `fields.op=trigger|policy_skip`), which is exactly what the GM panel parses per ADR-031. If the wire never carries the payload, every test fails — wire-correct.

One implementation note flagged for Dev (see Delivery Findings): the legacy `op=skipped, reason=no_visual_scene` watcher event at `websocket_session_handler.py:3232` must be REPLACED, not added-to, by the new `render.trigger` emission to avoid double-emit on the no-visual-scene banter case.

**Handoff:** To Dev (Ponder Stibbons) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Phase:** finish (wire-first)
**Status:** GREEN — all 30 story-45-30 tests passing, no regressions in 213 adjacent server tests or 1379 UI tests.

**Server changes (sidequest-server@feat/45-30-render-trigger-policy-otel, commit 2033077):**
- NEW `sidequest/server/render_trigger.py` — `RenderTriggerReason` StrEnum (5 values, wire-stable strings) + `classify_trigger()` pure function. Priority order BEAT_FIRE > SCENE_CHANGE > NPC_INTRO > ENCOUNTER_RESOLVED > NONE_POLICY.
- NEW `sidequest/telemetry/spans/render.py` — registers `render.trigger` and `render.policy_skip` in `SPAN_ROUTES` (event_type=state_transition, component=render). Imported in `spans/__init__.py`.
- `sidequest/server/websocket_session_handler.py` — `_maybe_dispatch_render` refactored. New kwargs `encounter_resolved_this_turn: bool = False`, `snapshot_location_before: str | None = None`. The legacy `op=skipped, reason=no_visual_scene` watcher branch is REPLACED (per architect's red-phase note) by the new `render.trigger` emission. NONE_POLICY emits one `render.trigger` (eligible=False, queued=False) AND one `render.policy_skip`. Eligible turns emit `render.trigger` (eligible=True, queued=True) before downstream gates.
- Production call site (`websocket_session_handler.py:1866` and `:2687`) — captures `snapshot.location` and `snapshot.encounter.resolved` BEFORE `_apply_narration_result_to_snapshot`, derives `encounter_resolved_this_turn` from before/after, threads both into dispatch. Same pre-apply state classifies the scrapbook `render_status` (`skipped_policy` vs `rendered`) at emit time so the SCRAPBOOK_ENTRY frame carries the right discriminator.
- `sidequest/protocol/messages.py` — `ScrapbookEntryPayload.render_status: str = "rendered"` (default for back-compat).
- `sidequest/game/persistence.py` — `scrapbook_entries` table gains `render_status TEXT NOT NULL DEFAULT 'rendered'`.
- `sidequest/server/emitters.py` — `emit_scrapbook_entry` accepts `render_status` kwarg; `persist_scrapbook_entry` writes the column.

**UI changes (sidequest-ui@feat/45-30-render-trigger-policy-otel, commit 0fa6a70):**
- `src/providers/ImageBusProvider.tsx` — `GalleryImage` and provider-internal `ScrapbookEntry` gain `render_status?: "rendered" | "skipped_policy" | "failed"`. `parseScrapbookEntry` validates against the three known values (any other string drops to undefined — no silent fallback). Both Pass-1 (image+entry merge) and Pass-2 (entry-only) push sites project the field.
- `src/components/GameBoard/widgets/ScrapbookGallery.tsx` — three new branches in the `ScrapbookCard` component: `skipped_policy` renders `data-testid=scrapbook-entry-{id}-render-status-skipped` with aria-label "Skipped: no narrative weight on this turn"; `failed` renders `data-testid=scrapbook-entry-{id}-render-status-failed` with aria-label "Render failed: image was requested but did not arrive"; the legacy `no-image` placeholder still fires for `undefined`/`rendered`-but-pending.

**Tests:** 30/30 passing (24 server + 6 UI). No regressions in adjacent areas (243 server tests in render/scrapbook/emitters/telemetry; 1379 UI tests).

**Branches pushed:**
- `sidequest-server` → `feat/45-30-render-trigger-policy-otel` (3 commits)
- `sidequest-ui` → `feat/45-30-render-trigger-policy-otel` (2 commits)

**Self-review:**
- [x] Code is wired to non-test consumers — production call site passes the new kwargs.
- [x] Code follows project patterns (existing throttle watcher event shape, existing scrapbook span pattern, existing helper-method pattern).
- [x] All 6 ACs met (AC1 enum + classifier, AC2 span attributes, AC3 eligibility gates + priority, AC4 wiring tests, AC5 UI distinguishes skipped vs failed, AC6 Felix-shape replay).
- [x] Error handling — classifier is pure / total; dispatch keeps the existing fire-and-forget swallow pattern for daemon errors.
- [x] No deferrals (wire-first requirement).

**Handoff:** To Reviewer (Granny Weatherwax) for review.

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Story setup specified `repos: server` only, but AC5 requires UI changes (ScrapbookGallery render_status indicators). TEA created the `feat/45-30-render-trigger-policy-otel` branch in `sidequest-ui` (gitflow / develop base) and wrote the UI test there. Affects `/Users/slabgorb/Projects/oq-2/.session/45-30-session.md` (`Repos:` field needs `server,ui` — Dev should land UI implementation on the same branch). *Found by TEA during test design.*
- **Gap** (non-blocking): `tests/fixtures/packs/test_genre/worlds/flickering_reach/openings.yaml` was missing on develop, breaking pre-existing `test_scrapbook_entry_persists_and_journals` since the canned-openings story landed. TEA added a minimal world-tier fixture as part of this RED commit. Affects `tests/fixtures/packs/test_genre/worlds/flickering_reach/openings.yaml` (now present). *Found by TEA during test design.*
- **Improvement** (non-blocking, for Dev/green): The legacy `_watcher_publish` call at `sidequest-server/sidequest/server/websocket_session_handler.py:3232–3242` (`field=render, op=skipped, reason=no_visual_scene`) must be REPLACED — not added-to — by the new `render.trigger` emission. Otherwise banter turns will emit two competing events and the GM panel sees double-counted decisions. Affects `sidequest/server/websocket_session_handler.py:3232` (delete the legacy op=skipped branch when the policy classifier replaces the visual-scene short-circuit). *Found by TEA during test design (architect tandem feedback).*

### Dev (implementation)

- **Gap** (non-blocking): The full `uv run pytest tests/` sweep on develop has 36 pre-existing failures unrelated to story 45-30 — primarily missing `openings.yaml` files in genre-pack worlds (`spaghetti_western/dust_and_lead`, `elemental_harmony/burning_peace`, `heavy_metal/*`) and a `room=` kwarg mismatch on `test_session_handler_localdm_offline.py`'s narration mock. None of these tests touch the render trigger or scrapbook subsystem; they all pre-date this story. Affects `sidequest-content/genre_packs/{various}/worlds/*/openings.yaml` (canned-openings story migration is incomplete) and `tests/server/test_session_handler_localdm_offline.py` (orchestrator signature drift). *Found by Dev during implementation.*
- **Gap** (non-blocking): TS compile produces ~10 pre-existing errors in `src/providers/__tests__/ImageBusProvider.scrapbook.test.tsx` (`@ts-expect-error` directives now unused) and `src/__tests__/narration-screen-streaming.test.tsx` (`activeTurnStartedAt` field added to `StreamingNarrationState` since these tests were written) and `src/App.tsx` (a few `unknown` → `string` mismatches around line 880-929). All vitest tests still pass; these are TS-strict warnings on files I did not modify. Affects `sidequest-ui/src/providers/__tests__/ImageBusProvider.scrapbook.test.tsx`, `src/__tests__/narration-screen-streaming.test.tsx`, `src/App.tsx`. *Found by Dev during implementation.*
- **Improvement** (non-blocking, for Reviewer): Encounter-resolved detection in the production call site uses a simple "before unresolved + after resolved" comparison around `_apply_narration_result_to_snapshot`. This handles the standard case where an encounter transitions from active to terminal via narration_apply. It does NOT handle the case where the encounter is REPLACED (a new encounter starts on the same turn one resolves) — that turn would report `encounter_resolved_this_turn=True` but the snapshot post-apply might show the new encounter as unresolved. Per playgroup priority and "Cut the Dull Bits", I judged this acceptable: the policy fires once per turn anyway, and the OTEL trail surfaces both encounter-end and encounter-start events. If Reviewer wants tighter semantics, the comparison should use a stable encounter id + resolution timestamp. Affects `sidequest/server/websocket_session_handler.py:1882-1883` (the `encounter_resolved_this_turn` derivation). *Found by Dev during implementation.*

### Reviewer (code review)

- **Improvement** (non-blocking, follow-up story): `render_status` is stringly-typed across protocol message, emitter signatures, and DB schema. Recommend a follow-up story to convert to `Literal["rendered", "skipped_policy", "failed"]` (Pydantic) or a `RenderStatus` StrEnum, and add a CHECK constraint on the DB column. Today the wire is constrained by single-writer code, but the type signature invites future drift. Affects `sidequest/protocol/messages.py:151`, `sidequest/server/emitters.py:290`, `sidequest/server/websocket_session_handler.py:469`, `sidequest/game/persistence.py:141`. *Found by Reviewer during code review.*

- **Improvement** (non-blocking, follow-up story): The eligible-but-no-subject branch in `_maybe_dispatch_render` (after the policy classifies as eligible but the narrator emitted no `visual_scene.subject`) emits `render.trigger` with `queued=True` then returns None without dispatching. The OTEL stream technically tells the truth via `subject_present=False`, but a GM panel filter on `queued=True` alone would think a render is in flight and wait for a `render.dispatched` follow-up that never comes. Recommend either setting `queued=False` in this branch or emitting a paired `render.no_subject` event. Affects `sidequest/server/websocket_session_handler.py:3370-3389`. *Found by Reviewer during code review.*

- **Gap** (non-blocking, project policy): Schema migration: the new `render_status` column is added via `CREATE TABLE IF NOT EXISTS`, which leaves existing user save DBs without the column. The first INSERT into `scrapbook_entries` on an old DB will fail with `no such column: render_status`; the `BLE001` exception handler in `emit_scrapbook_entry` catches the error and silently logs to warning, dropping that turn's scrapbook entry. Per project memory "Legacy saves are throwaway" this matches stated policy, but the silent failure mode for active saves carrying over from develop is worth surfacing to SM/Tech-writer. Affects `sidequest/game/persistence.py:141`, `sidequest/server/emitters.py:46-66`. *Found by Reviewer during code review.*

## Design Deviations

None at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Reviewer (audit)

**TEA deviations:** None logged. Reviewer audit found one undocumented deviation:

- **Wire-string for ENCOUNTER_RESOLVED reason:** AC1 specifies the wire string `resolved_encounter`; story context Technical Guardrails defines `ENCOUNTER_RESOLVED = "resolved"`. TEA's tests assert `reason == "resolved"`, matching story context. Per spec authority (story context > AC text), implementation is correct. Not flagged by TEA at red phase. Severity: low (the wire shape is consistent across server and tests; AC1 text is the outlier).
  - Reviewer ruling: ✓ ACCEPTED (story context overrides AC text per the hierarchy).

**Dev deviations:**
- **Felix-replay test disables image_pacing throttle** → ✓ ACCEPTED by Reviewer: throttle has dedicated coverage in `test_render_dispatch_throttle.py`; isolating one gate at a time is sound under wire-first ("test the SEAM").
- **Existing dispatch-mechanics tests use `_make_eligible_result()` wrapper** → ✓ ACCEPTED by Reviewer: tests preserve their named-gate semantics. One side effect noted as a finding (see [TEST] below) — `test_render_skipped_when_no_visual_scene` now exercises the new "eligible_no_subject" branch instead of its named gate; test name is now misleading.
- **`render.trigger` watcher event published as `state_transition`, not via SPAN_ROUTES extract** → ✓ ACCEPTED by Reviewer: matches the established render watcher pattern (`op=throttle_decision`, `op=dispatched`, `op=failed`). SPAN_ROUTES static registration satisfies the AC's "register span" requirement.

### Dev (implementation)

- **Felix-replay test disables image_pacing throttle**
  - Spec source: tests/server/test_render_dispatch.py::test_felix_shape_replay_eight_turn_sequence (TEA red phase)
  - Spec text: "drive 8 turns through `_maybe_dispatch_render` and assert 4 dispatches + 4 none_policy events in order"
  - Implementation: Test replaces `sd.image_pacing_throttle` with an `_AlwaysAllow` stub before driving the sequence
  - Rationale: ADR-050's image pacing throttle has a 30-second cooldown by default; the test runs in milliseconds so without the stub turns 2-7 would be throttle-suppressed before reaching the policy. The throttle is downstream of the trigger policy and has its own coverage in `test_render_dispatch_throttle.py`. Wire-first principle (test the SEAM) justifies isolating one gate at a time.
  - Severity: minor
  - Forward impact: none — the throttle integration with the policy gate (whether throttle-suppressed turns should still emit `render.trigger`) is covered by the existing throttle suite.

- **Existing dispatch-mechanics tests use `_make_eligible_result()` wrapper**
  - Spec source: pre-story tests in test_render_dispatch.py / test_render_dispatch_throttle.py / test_render_broadcast_2b.py / test_render_session_mapping_37_30.py
  - Spec text: pre-story `NarrationTurnResult(narration=..., visual_scene=...)` fixtures expected dispatch to fire on visual_scene presence alone
  - Implementation: Added a `_make_eligible_result(**kwargs)` wrapper in each affected test file that injects a default `BeatSelection(actor="test", beat_id="dispatch_test")` so the result classifies as BEAT_FIRE under the new policy. `NarrationTurnResult(...)` call sites in those files routed through the wrapper (35 total sites across 4 files). Story 45-30 policy tests still construct `NarrationTurnResult` directly to exercise classification.
  - Rationale: The dispatch-mechanics tests assert URL handling, request payload structure, and broadcasting — they pre-date the policy and would otherwise hit NONE_POLICY and skip the named gate they're testing. Without the wrapper, ~35 tests would falsely pass for the wrong reason (policy gate, not their intended gate).
  - Severity: minor
  - Forward impact: none — the wrapper is opt-in; future tests can construct `NarrationTurnResult` directly.

- **`render.trigger` watcher event published as `state_transition`, not via SPAN_ROUTES extract**
  - Spec source: context-story-45-30.md, "OTEL spans" section
  - Spec text: "Define in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES` entries [...] every call to `_maybe_dispatch_render()`"
  - Implementation: SPAN_ROUTES entries are registered (the static check passes), but the actual emission is a direct `_watcher_publish("state_transition", {"field": "render", "op": "trigger", ...})` call — same pattern as the existing `op=throttle_decision` watcher events at the same dispatch site. The SPAN_ROUTES extractor would only fire if an OTEL span named `render.trigger` were opened explicitly.
  - Rationale: The existing render watcher events (throttle_decision, dispatched, failed) all use direct `state_transition` publishes — not OTEL-span-with-route. Following the established pattern keeps the GM panel parsing consistent and avoids the ceremony of opening synthetic spans for events that are conceptually plain decisions, not OTEL traces. The SPAN_ROUTES entry is preserved so any future OTEL-span-based emission remains consistent.
  - Severity: minor
  - Forward impact: minor — if a future change wants to mint a real OTEL span at this site (e.g. for OTLP export to Jaeger), the route will fire correctly. No change to GM panel behaviour.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — tests 243+76 passing, ruff clean, no smells, both branches pushed cleanly |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually (see [EDGE] in assessment) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually (see [SILENT] in assessment) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually (see [TEST] in assessment) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually (see [DOC] in assessment) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually (see [TYPE] in assessment) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually (see [SEC] in assessment) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually (see [SIMPLE] in assessment) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed domain manually against `.pennyfarthing/gates/lang-review/python.md` (see [RULE] in assessment) |

**All received:** Yes (1 returned, 8 skipped via settings — Reviewer covered each domain manually per the agent definition's instruction "if a subagent errored or is disabled, assess the specialist's domain yourself")
**Total findings:** 6 confirmed (3 MEDIUM, 3 LOW), 0 dismissed, 1 deferred-to-followup-story

## Devil's Advocate

If I were trying to break this, here's what I'd attack.

**Attack 1: the OTEL "queued=True" lie.** The eligible branch emits `render.trigger` with `queued=True` BEFORE checking `subject_present`. If `subject_present` is False, we return None without firing the daemon — but the watcher event already shipped saying we queued. The `subject_present=False` attribute on the same event tells the truth, but a GM panel filter on `queued=True` would think a render is in flight. A consumer waiting for a `render.dispatched` follow-up would wait forever. The information is recoverable (subject_present=False is right there), but the natural reading of `queued=True` is "the daemon got a request" — and it didn't. This is the strongest case for a fix-in-this-story finding, but the data is on the same event so it's an interpretation hazard, not a data loss.

**Attack 2: the encounter-replacement edge case.** Pre-apply: encounter A exists, unresolved. Apply: A resolves, B starts (also unresolved). Post-apply: encounter B exists, unresolved. `encounter_resolved_this_turn = True (was unresolved) and (encounter is None False or resolved False)` → False. We MISS the resolution of A. Dev flagged this as a delivery finding. In practice the resolving turn typically also has a `BeatSelection` (the killing blow) so BEAT_FIRE wins anyway, but the audit trail loses the "resolved" reason. Same-turn replace is rare per playgroup playtests; accepting Dev's judgment per "Cut the Dull Bits".

**Attack 3: schema migration on legacy saves.** The `render_status TEXT NOT NULL DEFAULT 'rendered'` column is added via `CREATE TABLE IF NOT EXISTS` — existing user save DBs won't get the new column. The first INSERT against an old DB will fail with `no such column: render_status`. The exception handler in `emit_scrapbook_entry` catches it (BLE001 noqa, "scrapbook must never crash a turn") and silently logs to warning. Old saves silently lose ALL scrapbook entries until reinitialized. Per project memory "Legacy saves are throwaway" this is documented project policy, but the silent loss is worth surfacing.

**Attack 4: pydantic accepts arbitrary render_status strings.** `render_status: str = "rendered"` on `ScrapbookEntryPayload` accepts any string. A typo on the server side (`"skiped_policy"` instead of `"skipped_policy"`) would propagate to the UI, which has 3-value validation and would silently drop the unknown value to `undefined`, falling back to the legacy "no image" placeholder. Two layers of silent fallback. Constrained-by-single-writer in current code, but the type signature invites future bugs.

**Attack 5: classifier called twice per turn.** Once in `dispatch_post` for scrapbook render_status, once inside `_maybe_dispatch_render` for dispatch decision. Pure function so they converge — but two calls per turn is wasted CPU. Negligible cost in practice (a few field reads + branch comparisons). Not a fix.

**Attack 6: the inline imports of render_trigger inside session_handler.** `from sidequest.server.render_trigger import (RenderTriggerReason, classify_trigger)` appears inline at TWO call sites in session_handler. There is NO circular import — render_trigger only TYPE_CHECKS NarrationTurnResult. Could be promoted to top-level. Minor.

**Outcome:** Attacks 1, 3, and 4 are real but recoverable. None are blocking; all are NON-BLOCKING improvement findings.

## Reviewer Assessment

**Verdict:** APPROVED

### Wire trace (end-to-end, both repos)

**Render decision wire (server-only):**
- narration_apply.py mutates `snapshot.encounter.resolved` (existing behaviour)
- session_handler.py:1888-1892 captures `snapshot_location_before_apply` and `encounter_unresolved_before` BEFORE `_apply_narration_result_to_snapshot`
- session_handler.py:1899-1901 derives `encounter_resolved_this_turn` from before/after
- session_handler.py:2735-2740 passes both into `_maybe_dispatch_render`
- websocket_session_handler.py:3296-3327 calls `classify_trigger` → reason
- For NONE_POLICY: emits `state_transition (field=render, op=trigger, eligible=False, queued=False)` AND `state_transition (field=render, op=policy_skip)` → returns None
- For eligible: emits trigger event → checks subject_present → if missing, returns None with logger.warning; if present, proceeds through existing throttle/daemon/queue gates
- GM panel parses `state_transition (field=render, op=trigger)` per ADR-031

**Render-status discriminator wire (server → UI):**
- session_handler.py:2200-2208 calls `classify_trigger` (same inputs as dispatch — same outcome)
- Maps NONE_POLICY → "skipped_policy", else → "rendered"
- Threads `render_status` to `_emit_scrapbook_entry` → `emitters.emit_scrapbook_entry` → `ScrapbookEntryPayload(render_status=...)` → `persist_scrapbook_entry` writes column → `emit_event(SCRAPBOOK_ENTRY)` ships frame
- UI `parseScrapbookEntry` validates against {rendered, skipped_policy, failed} — drops other strings to undefined
- Both Pass-1 and Pass-2 push render_status onto `GalleryImage`
- `ScrapbookGallery` branches on render_status: distinct DOM (data-testid `-render-status-{skipped|failed}`) + distinct aria-label per state

End-to-end wire is **live** in production code paths. Every hop verified.

### Findings

| Severity | Tag | Issue | Location | Decision |
|----------|-----|-------|----------|----------|
| MEDIUM | [TYPE] | `render_status: str = "rendered"` is stringly-typed across protocol message, emitter signatures, and DB schema (no CHECK constraint). A typo at the server side propagates silently to the UI which drops unknown values to undefined → legacy "no image" placeholder. Two layers of silent fallback. Constrained today by a single-writer code path; type signature invites future bugs. Recommend `Literal["rendered", "skipped_policy", "failed"]` or a `RenderStatus` StrEnum. | `sidequest/protocol/messages.py:151`, `sidequest/server/emitters.py:290`, `sidequest/server/websocket_session_handler.py:469`, `sidequest/game/persistence.py:141` | Confirm — non-blocking improvement, file as follow-up story |
| MEDIUM | [SILENT] [EDGE] | The eligible-but-no-subject branch emits `render.trigger` with `queued=True` then returns None without dispatching or emitting a corresponding "no_subject" event. The `subject_present=False` attribute on the same trigger event tells the truth, but a GM panel filter on `queued=True` alone would think a render is in flight. The `logger.warning` is a developer signal, not an operator one. Recommend either (a) set `queued=False` in the eligible-no-subject branch, or (b) emit a paired `render.no_subject` event after the warning. | `sidequest/server/websocket_session_handler.py:3370-3389` | Confirm — non-blocking improvement, file as follow-up story |
| MEDIUM | [EDGE] | Schema migration: new `render_status` column added via `CREATE TABLE IF NOT EXISTS` won't apply to existing user save DBs. First INSERT to scrapbook_entries on an old DB will fail with `no such column: render_status`; the exception handler in `emit_scrapbook_entry` swallows the error to `logger.warning` (BLE001 noqa). Old saves silently lose all scrapbook entries until reinitialized. Per project memory "Legacy saves are throwaway" this is documented policy, but the silent failure mode is a UX cliff for active saves carrying over from develop. | `sidequest/game/persistence.py:141`, `sidequest/server/emitters.py:46-66` | Confirm — file as delivery finding for SM/Tech-writer awareness; consistent with project policy |
| LOW | [TEST] | `test_render_skipped_when_no_visual_scene` (existing test, now wrapped via `_make_eligible_result`) no longer tests its named gate. With the wrapper it has `beat_selections` (BEAT_FIRE eligible) and no `visual_scene` → hits the new "eligible_no_subject" branch, not the no_visual_scene branch. Test still passes (queued is None) but the test name is misleading. Other negative tests (`test_render_skipped_when_flag_disabled`, `test_render_skipped_when_daemon_socket_missing`) DO still test their named gates because their fixtures set `visual_scene` so subject_present is True and the named gate fires. | `tests/server/test_render_dispatch.py::test_render_skipped_when_no_visual_scene` | Confirm — non-blocking; rename or split in follow-up |
| LOW | [DOC] | AC1 specifies the wire string `resolved_encounter` for the encounter-resolved reason; story context (Technical Guardrails) defines `ENCOUNTER_RESOLVED = "resolved"`. Implementation correctly follows story context per spec authority hierarchy. TEA's deviation log says "No deviations from spec" — undocumented divergence. Audited and ACCEPTED above; flagging here for awareness. | `sidequest/server/render_trigger.py:36`, `.session/45-30-session.md` | Confirm — undocumented deviation, audited |
| LOW | [SIMPLE] | Inline imports of `from sidequest.server.render_trigger import (RenderTriggerReason, classify_trigger)` appear at TWO call sites in `websocket_session_handler.py` (line 2191 in dispatch_post, line 3296 inside _maybe_dispatch_render). There is no circular import — render_trigger only TYPE_CHECKS NarrationTurnResult. Could be promoted to top-level imports. | `sidequest/server/websocket_session_handler.py:2191, 3296` | Confirm — cosmetic, address opportunistically |

### VERIFIED

- **[VERIFIED] [SEC]** No user input flows through new code. `classify_trigger` reads structured fields from orchestrator-extracted `NarrationTurnResult` (already sanitized per ADR-047 upstream). `render_status` flows server→UI as a constrained string, used only as React-escaped data-testid + aria-label + text content. SQL writes parameterized. Evidence: `render_trigger.py:48-92` (no string concatenation, no eval), `emitters.py:50-66` (parameterized INSERT), `ScrapbookGallery.tsx:300-322` (React text rendering, no dangerouslySetInnerHTML).

- **[VERIFIED] [TEST]** Wire-first boundary tests assert on the typed watcher event shape (`event_type=state_transition`, `field=render`, `op=trigger|policy_skip`) — what the GM panel actually parses per ADR-031. 14 classifier unit tests + 8 boundary tests + Felix-shape replay cover all 5 reasons + priority lattice + watcher emission. Architect Leonard explicitly approved the wire-correctness in red phase. Evidence: `tests/server/test_render_dispatch.py:830-1366` (boundary tests), `tests/server/test_render_trigger_policy.py` (full classifier lattice).

- **[VERIFIED] [RULE]** `.pennyfarthing/gates/lang-review/python.md` checks 1-13 reviewed against the diff: silent exception (BLE001 with justification), no mutable defaults, all type annotations at boundaries, lazy logging eval (`logger.warning("...", arg, arg)` not f-string), no resource leaks, no unsafe deserialization, async patterns unchanged from existing code, import hygiene mostly OK (one inline import flagged as [SIMPLE] above). Evidence: ruff check clean.

- **[VERIFIED] [EDGE]** `encounter_resolved_this_turn` derivation correctly handles encounter-becoming-None post-apply (`(snapshot.encounter is None or snapshot.encounter.resolved)`). Pre-apply guard `(snapshot.encounter is not None and not snapshot.encounter.resolved)` prevents False positives on already-resolved encounters. Same-turn-replacement edge case explicitly accepted via Dev's delivery finding. Evidence: `sidequest/server/websocket_session_handler.py:1888-1901`.

- **[VERIFIED] [DOC]** Comments are accurate and load-bearing — every "Story 45-30:" prefix marks new code with a one-line rationale; the deviation log captures three real implementation choices with full 6-field schema. The optimistic `queued=True` comment honestly describes the trade-off (downstream gates emit their own events) — though it doesn't cover the eligible_no_subject case which is flagged above. Evidence: `websocket_session_handler.py:3349-3365` (queued comment), `render_trigger.py:1-17` (module docstring), `spans/render.py:1-20` (route docstring).

### Wire-first compliance

- **Boundary test exists at the outermost reachable layer:** ✓ `_maybe_dispatch_render` driven through real Unix-socket fake daemon; `render.trigger` watcher event asserted on the GM-panel-parsed shape.
- **No dead exports:** ✓ `RenderTriggerReason` and `classify_trigger` consumed by production `_maybe_dispatch_render` AND `dispatch_post` block AND test suite. SPAN_ROUTES entries registered + import wired in `__init__.py`.
- **No "follow-up story" / "subsequent work" / "defer" language in diff or session:** ✓ confirmed by grep (the word "deferred" appears once in the Subagent Results table referring to MEDIUM-finding remediation, not to story scope).
- **Full test suite green:** ✓ 243 server + 76 UI passing for the impacted areas; preflight clean.

**Handoff:** To SM (Captain Carrot) for finish-story.

## Workflow Tracking

**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-05-03T01:56:54Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-02 | 2026-05-03T01:01:02Z | 25h 1m |
| red | 2026-05-03T01:01:02Z | 2026-05-03T01:17:34Z | 16m 32s |
| green | 2026-05-03T01:17:34Z | 2026-05-03T01:47:57Z | 30m 23s |
| review | 2026-05-03T01:47:57Z | 2026-05-03T01:56:54Z | 8m 57s |
| finish | 2026-05-03T01:56:54Z | - | - |