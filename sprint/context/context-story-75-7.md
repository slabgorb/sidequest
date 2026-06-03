---
parent: context-epic-75.md
workflow: tdd
---
# Story 75-7 Context — Universal retrieval: OTEL `retrieval.universal` instrumentation + GM-panel surface (ADR-118)

## Business Context

The universal-retrieval layer (75-4/75-5/75-6) now decides, every turn, *which*
NPCs/locations/factions the narrator gets to see — a floor of scene-present
entities plus a budgeted semantic fill, instead of the old full-`npc_pool` blob.
That is a load-bearing mechanical decision, and per CLAUDE.md's **OTEL
Observability Principle the GM panel is the lie detector**: a retrieval layer
that the GM panel cannot see is indistinguishable from the narrator improvising
grounding it never actually retrieved. Claude is excellent at writing convincing
prose about an NPC "stepping out of the shadows" whether or not that NPC's card
was ever selected by the fill — the only way Keith can tell the engine from the
improv is to watch the retrieval decision land on the dashboard.

The span itself was born in 75-5 (`SPAN_UNIVERSAL_RETRIEVAL = "retrieval.universal"`,
`game/retrieval_orchestration.py:55`) and fires live every turn
(`websocket_session_handler.py:2500`). **But it only reaches Jaeger/OTLP — not
the GM dashboard.** The GM panel subscribes to the **WatcherHub** event stream
(`telemetry/watcher_hub.py`), not the raw OTEL span pipeline, and
`retrieve_turn_context` never calls `publish_event`. So today the retrieval
decision is observable to an operator running a Jaeger UI and invisible on the
GM panel Keith actually uses during play. 75-7 closes that gap: it makes the
existing `retrieval.universal` decision surface on the GM panel the same way its
siblings (`lore_retrieval`, `accretion.entity_sync`) already do.

**Whom it serves:** Keith / the dev. This is a backend observability surface so
the *engine builder* can verify the retrieval layer is engaging real grounding,
not winging it. It is **not** a player-facing surface — players never see the GM
panel — and it is **not** a reason to put a playgroup member's name on backend
observability. (Sebastien and Jade want the *math behind mechanical resolution*
in the **player UI**; the GM panel, OTEL spans, and watcher telemetry are
Keith/dev tools and serve none of them. If you find yourself writing
"Sebastien's lie-detector" about this span, you've made the wrong association.)

## Technical Guardrails

The canonical, code-level spec lives in the **session file**
(`.session/75-7-session.md`, higher spec authority than this document). The
design of record is **ADR-118 §D5 (OTEL observability)** — quoted verbatim
below. These are the constraints test design must enforce, grounded in the live
code the scout read (2026-06-02):

- **Repo / language:** `sidequest-server` (Python). Base branch: `develop`.
  Apply the `python.md` lang-review checklist.

- **The span name and attribute contract are FROZEN by ADR-118 §D5 and already
  shipped — do not redefine them.** §D5 specifies *"A new `retrieval.universal`
  span emits, mirroring the existing `lore.*` attribute discipline"* with:
  `retrieval.budget_total`, `retrieval.outcome`, `retrieval.floor_count`,
  `retrieval.floor_token_cost`, `retrieval.fill_candidate_count`,
  `retrieval.fill_selected_count`, `retrieval.fill_token_cost`,
  `retrieval.npc_count`, `retrieval.location_count`, `retrieval.faction_count`,
  `retrieval.rejected_below_similarity`, `retrieval.dimension_mismatch_count`,
  and the failure outcomes *"query embed failed, daemon unavailable, budget
  exhausted before fill, no relevant entities — each a distinct `outcome` value,
  never a silent skip."* **75-5 already implements every one of these** in
  `retrieve_turn_context` (`game/retrieval_orchestration.py:209-220`), with the
  outcome enum `{"success","budget_exhausted","query_failed","no_candidates"}`
  (`retrieval_orchestration.py:67-70`). 75-7 does **not** re-emit or re-define
  the span; it makes that already-firing decision *reach the GM panel*.

- **Scout finding — the actual gap is the WatcherHub bridge, NOT the span (this
  reshapes the whole story; SOUL *Don't Reinvent*):** there are two distinct
  observability paths in this codebase. (1) **OTEL spans**
  (`tracer.start_as_current_span`) flow to OTLP exporters (Jaeger). (2) **GM-panel
  events** flow through `watcher_hub.publish_event(...)`
  (`telemetry/watcher_hub.py:534`) → WebSocket `/ws/watcher` → the React
  `Dashboard/` tabs. The bridge between them is **one-way and opt-in**: when
  `SIDEQUEST_WATCHER_AS_SPANS=1`, `publish_event` *also* mints a synthetic OTEL
  span (`watcher_hub.py:497,581`). There is **no reverse bridge** — a raw OTEL
  span never becomes a GM-panel watcher event. Therefore the `retrieval.universal`
  span fires into Jaeger every turn but **emits no `publish_event`**, so the GM
  panel shows nothing. The fix is to add the watcher `publish_event` half, **not**
  to touch the span. Confirm with `grep -n publish_event game/retrieval_orchestration.py`
  → no hits today.

- **Reuse the exact sibling pattern — dual emission (SOUL *Don't Reinvent*):** the
  gold-standard sibling is **75-6's `entity_sync.sync_for_turn`**
  (`server/dispatch/entity_sync.py:39-91`): it fires `accretion.entity_sync` as an
  OTEL span (`:68`) **and** calls `publish_event("state_transition", {...},
  component="retrieval")` (`:78`) carrying the same counts. `lore_embed.retrieve_for_turn`
  (`server/dispatch/lore_embed.py:38`) and `run_worker` (`:79`) do the same with
  `component="lore"`. 75-7 must add the identical second half for universal
  retrieval: a `publish_event` carrying the ADR-118 §D5 attributes (outcome,
  floor/fill counts, per-type counts, budget) so the same numbers the span holds
  reach the dashboard. Match `component="retrieval"` (the component 75-6 already
  established for this subsystem) so the GM panel groups universal-retrieval and
  entity-sync under one Subsystems-tab label.

- **The emission seam is the dispatch wrapper, not the pure orchestrator (mirror
  the lore split):** the pure `retrieve_turn_context` lives in the *game* tier
  (`game/retrieval_orchestration.py`) and must stay watcher-free for the same
  import-hygiene reason `watcher_hub` itself documents — game/genre code should not
  pull the server stack in at import. The watcher emission belongs in the *server*
  dispatch layer. Today the call site is `_retrieve_entities_for_turn`
  (`websocket_session_handler.py:2986-3001`), which is the typed sibling of
  `_retrieve_lore_for_turn` (`:2980`) and already imports nothing watcher-bound.
  Preferred shape (mirroring lore's decomposition): a
  `server/dispatch/universal_retrieval.py` `retrieve_for_turn(handler, sd, action)`
  sibling of `lore_embed.retrieve_for_turn` that calls `retrieve_turn_context`,
  then maps the returned `RetrievedEntities` fields to a `publish_event`. The
  call at `websocket_session_handler.py:2500` (`entity_retrieval =
  await self._retrieve_entities_for_turn(sd, action)`) is the live per-turn path —
  the span fires inside it today; the watcher event must fire from the same path.

- **Map `RetrievedEntities` → watcher fields losslessly (the D5 contract):** the
  result dataclass already carries every D5 attribute as a typed field — `outcome`,
  `budget_total`, `floor_count`, `floor_token_cost`, `fill_candidate_count`,
  `fill_selected_count`, `fill_token_cost`, `rejected_below_similarity`,
  `dimension_mismatch_count`, and per-type counts derivable from
  `len(retrieved_npcs or [])` etc. (`retrieval_orchestration.py:73-97`). The
  watcher event's `fields` must carry these so the dashboard sees the same numbers
  Jaeger does. Use `field`/`op` keys consistent with the sibling events
  (`{"field": "universal_retrieval", "op": "<outcome>", ...counts...,
  "turn_number": <interaction>}`) so the existing Subsystems/Timeline rendering
  picks them up without a UI schema change.

- **Failure isolation — retrieval failure must NOT cost the player their
  narration (ADR-006; mirror lore + 75-6):** `retrieve_turn_context` is documented
  *"NEVER raises"* and already records a failure `outcome` for every degraded path
  (`retrieval_orchestration.py:176`, `:246`, `:254`). 75-7's watcher emission must
  inherit the identical discipline: it publishes the failure `outcome` as a watcher
  event (with `severity="warning"`/`"error"` per the failure class — mirror
  `lore_embed.py:67` `severity="error"`), and the emission wrapper itself must be
  wrapped so a `publish_event` exception (or an unexpected raise) is logged and
  swallowed — **observing the turn must never crash the turn.** A test MUST assert
  that a forced failure in the retrieval/emit path does not propagate out of the
  per-turn entry, and that a failure `outcome` is surfaced (not a silent drop).

- **No Silent Fallbacks (SOUL / ADR-118 §D5):** §D5 is explicit — each failure
  path is *"a distinct `outcome` value, never a silent skip."* The watcher event
  must carry the real `outcome` string from `RetrievedEntities.outcome`
  (`query_failed` / `budget_exhausted` / `no_candidates` / `success`) — never
  coerce a failure to `success`, never publish a generic "retrieval ran" with no
  outcome, never swallow a failure into an empty event. A test MUST assert the
  `query_failed` and `no_candidates` outcomes each reach the watcher event with
  their distinct value.

- **Zero-byte-leak / clean-skip semantics (mirror 75-5 + 75-6):** the orchestrator
  already returns `None` per type when nothing was retrieved (zero-byte-leak into
  the prompt, `retrieval_orchestration.py:80-88`). The watcher emission has the
  analogous obligation: a turn where retrieval did real work emits its counts; the
  per-type counts in the event must reflect *actual* selections (0 is a legitimate
  value, e.g. `no_candidates` → all per-type counts 0 with `outcome="no_candidates"`).
  Do not fabricate non-zero counts and do not suppress the event on an empty fill —
  the GM needs to see "retrieval ran and found nothing" distinctly from "retrieval
  never fired." A test MUST assert the empty-fill turn still publishes an event with
  zeroed counts and the correct outcome.

- **GM-panel surface wiring — the span/event must actually REACH the dashboard
  (CLAUDE.md "Every Test Suite Needs a Wiring Test"):** the deliverable is not "an
  event object got constructed" — it is "the universal-retrieval decision is visible
  on the GM panel." The watcher path is: `publish_event` → `watcher_hub.publish` →
  `_broadcast` → subscribed `/ws/watcher` sockets (`watcher_hub.py:114-189`), with a
  2000-event replay buffer for dashboard reconnects (`:97`, `:191`). The UI consumes
  it via the `WatcherEvent` contract (`sidequest-ui/src/types/watcher.ts:22-29`),
  rendered in the `Dashboard/` Subsystems/Timeline tabs grouped by `component`. The
  wiring test MUST drive a real turn through `_retrieve_entities_for_turn` (the
  production path at `:2500`) and assert a `retrieval`-component watcher event was
  published — i.e. subscribe a fake `_Sendable` to `watcher_hub`, run the turn, and
  assert the event landed on the subscriber (or assert the buffer/published count
  grew with the right `component`/`field`). **Do NOT grep production source as a
  wiring assertion** (CLAUDE.md "No Source-Text Wiring Tests"): drive the flow and
  assert the published event, OTEL-span-assertion or fixture-driven-behavior style.

- **Event type stays within the existing `WatcherEventType` union (no UI schema
  churn):** the UI's `WatcherEventType` union (`watcher.ts:6-17`) is closed —
  `state_transition` is the member the siblings use for subsystem decisions
  (`entity_sync.py:55,79` and `lore_embed.py:65,79` both publish
  `"state_transition"`). 75-7 should publish `"state_transition"` with
  `component="retrieval"` and a `field` discriminator, NOT invent a new
  `event_type` that the UI union doesn't know (that would require a coordinated
  `sidequest-ui` change and is out of scope per Scope Boundaries). If the GM panel
  needs a dedicated visual treatment, that is a UI follow-up, not a backend AC.

- **Meaningful assertions only (TEA self-check):** assert the *watcher event's
  `component`, `field`, `op`/`outcome`, and the count field VALUES* against the
  scenario's expected floor/fill/per-type numbers — never `assert event is not None`
  where the outcome string or count is the contract. No `assert True`, no
  `is None` on an always-None value, no source-text grep.

## Scope Boundaries

**In scope:**
- A GM-panel watcher emission for universal retrieval — a `publish_event`
  (`"state_transition"`, `component="retrieval"`, `field="universal_retrieval"`)
  carrying the ADR-118 §D5 attribute set mapped from `RetrievedEntities`
  (outcome, budget_total, floor/fill counts, per-type counts,
  rejected_below_similarity, dimension_mismatch_count, turn_number).
- The server-tier dispatch seam for that emission — preferably a
  `server/dispatch/universal_retrieval.py` `retrieve_for_turn(handler, sd, action)`
  sibling of `lore_embed.retrieve_for_turn`, called from
  `_retrieve_entities_for_turn` (`websocket_session_handler.py:2986`) so the
  watcher event fires on the live per-turn path (`:2500`) alongside the existing
  span.
- Failure-path emission parity: degraded outcomes (`query_failed`,
  `budget_exhausted`, `no_candidates`) reach the GM panel with their distinct
  outcome value and appropriate severity; the emission is wrapped so it cannot
  crash the turn.
- Unit tests for the field mapping (each outcome + count combination), failure
  isolation, clean-skip/zeroed-count emission, and the production-reachable
  **wiring test** (a real turn → a `retrieval`-component watcher event lands on a
  subscriber).

**Out of scope (do not let tests demand these):**
- **The `retrieval.universal` span itself + its attributes/outcome enum** — that
  is **75-5** (merged): `SPAN_UNIVERSAL_RETRIEVAL`, every `span.set_attribute`,
  and the outcome taxonomy already exist in `game/retrieval_orchestration.py`. 75-7
  consumes the returned `RetrievedEntities`; it does not re-emit or redefine the
  span.
- **The floor+fill retrieval logic, budget seam, sanitization, dimension-mismatch
  requeue, Valley injection** — that is **75-5** (merged). 75-7 observes the
  decision; it does not run or alter the retrieval pass.
- **The `accretion.entity_sync` span / card-sync watcher event** — that is **75-6**
  (merged). 75-7 mirrors its dual-emission *pattern* for the retrieval span; it does
  not touch the entity-sync emitter.
- **`EntityCard` / projectors / `EntityStore` / cosine query** — that is **75-4**
  (merged).
- **New UI components / a dedicated dashboard tab / a new `WatcherEventType`
  member** — out of scope. 75-7 publishes within the existing
  `state_transition`/`component` contract the `Dashboard/` Subsystems & Timeline
  tabs already render. Any bespoke retrieval visualization is a UI follow-up, not
  this backend story.
- **Per-turn *total* budget unification (lore + entities under one ceiling)** —
  75-5's context flagged this as a "75-7 follow-up," but it is a *budget-seam*
  change, not an *instrumentation* change. The story title scopes 75-7 to
  instrumentation + GM-panel surface. Treat budget unification as deferred (name it
  a Delivery Finding if the team wants it folded in; do not let tests demand it).
- **End-to-end action→floor+fill→Valley→narrator integration** — that is **75-8**.
  75-7's wiring test proves the *watcher event* reaches the panel; the full
  retrieval-to-narration e2e is 75-8.
- **NPC-pool ratification gate (75-9) and player-NPC reference signal (75-10)** —
  downstream stories; 75-7 does not anticipate them.

## AC Context

The story YAML carries no explicit AC list; the authoritative spec is the session
file (`.session/75-7-session.md`). These ACs are derived from **ADR-118 §D5** and
the story title ("instrumentation + GM-panel surface"). Each expands into what
must be true, edge cases, and how a test verifies it:

1. **The `retrieval.universal` span attribute contract is intact and unchanged.**
   *Must be true:* the span still fires every turn with the full §D5 attribute set
   (75-5's contract). *Edge:* 75-7's added emission must not perturb the span (no
   double-span, no attribute drop). *Test:* drive a turn, assert the
   `retrieval.universal` span fired with its outcome + counts (regression guard
   that 75-7 didn't disturb 75-5).

2. **Universal retrieval emits a GM-panel watcher event (the core new behavior).**
   *Must be true:* every turn that runs retrieval publishes a watcher event with
   `component="retrieval"`, `field="universal_retrieval"`, the `outcome`, and the
   ADR-118 §D5 counts. *Edge:* counts must match the span's values for the same
   turn. *Test:* run `retrieve_for_turn` on a fixture with known floor/fill, assert
   the published event's field values equal the expected counts and outcome.

3. **Per-type and floor/fill counts reach the panel losslessly.**
   *Must be true:* `floor_count`, `floor_token_cost`, `fill_candidate_count`,
   `fill_selected_count`, `fill_token_cost`, `npc_count`, `location_count`,
   `faction_count`, `rejected_below_similarity`, `dimension_mismatch_count`,
   `budget_total` all appear in the event. *Edge:* per-type counts sum to
   `fill_selected_count`. *Test:* assert each field present with the expected
   value; assert the per-type sum invariant.

4. **Each failure outcome reaches the panel distinctly (No Silent Fallbacks /
   §D5).** *Must be true:* `query_failed`, `budget_exhausted`, `no_candidates`,
   `success` each surface as the event's outcome — never coerced. *Edge:* a daemon
   embed failure → `query_failed` with severity warning/error. *Test:* force each
   degraded path; assert the published outcome string equals the distinct value and
   severity is non-`info` for failures.

5. **Empty/clean-skip turns publish a zeroed event, not a suppressed one.**
   *Must be true:* a turn that retrieves nothing (`no_candidates`) still publishes
   an event with zeroed per-type counts and the correct outcome, so the GM can
   distinguish "ran, found nothing" from "never fired." *Test:* fixture with an
   empty store / below-threshold candidates → assert the event published with all
   per-type counts 0 and `outcome="no_candidates"`.

6. **Failure isolation — the emission cannot crash the turn (ADR-006).**
   *Must be true:* a raise inside retrieval or inside the emit step is logged and
   swallowed; the turn proceeds. *Test:* force an exception in the emit path; assert
   `_retrieve_entities_for_turn` returns and does not raise out of the per-turn
   entry (and a failure event/log is recorded).

7. **Wiring test (mandatory; CLAUDE.md doctrine) — the event reaches the GM
   panel through the production path.** *Must be true:* driving a real turn via
   `_retrieve_entities_for_turn` (`websocket_session_handler.py:2500`) results in a
   `retrieval`-component watcher event delivered to a `watcher_hub` subscriber.
   *Test:* subscribe a fake `_Sendable` to `watcher_hub`, run the turn through the
   handler method, assert the subscriber received an event with the right
   `component`/`field`/`outcome`. **Behavior-driven, not source-grep** (CLAUDE.md
   "No Source-Text Wiring Tests").

**Negative / paranoia cases beyond the AC minimum:**
- Daemon unavailable mid-session → `query_failed` event each turn, no crash, no
  span/event divergence.
- Floor exhausts the entire budget → `budget_exhausted` event with
  `fill_selected_count=0`, floor counts non-zero.
- A dimension-mismatch requeue happened → `dimension_mismatch_count > 0` reaches
  the event (proves the guard metric, not just the rejection metric, surfaces).
- Two turns in a row → two distinct events with monotonically advancing
  `turn_number`; the replay buffer (`watcher_hub.py:97`) holds both for a dashboard
  reconnect.
- `publish_event` raises (serialize failure / dead loop) → swallowed; turn
  unaffected; loud log emitted (mirror `watcher_hub.py:158`).

## Assumptions

- **75-1, 75-2, 75-4, 75-5, 75-6 are merged** (waterfall, ADR-118 §Composition).
  75-7 may assume: the `retrieval.universal` span fires live with the full §D5
  attribute set (`retrieval_orchestration.py:178-220`), `retrieve_turn_context` is
  wired into the per-turn path (`websocket_session_handler.py:2500`), and the
  entity store is kept fresh by 75-6's `sync_for_turn`. **Verified by scout
  (2026-06-02):** the span and the wiring both exist; the watcher emission does not.
- **The WatcherHub is the GM-panel transport, OTEL spans are not.** The GM
  dashboard subscribes to `/ws/watcher` → `watcher_hub` events
  (`telemetry/watcher_hub.py`); raw OTEL spans go only to OTLP/Jaeger. The
  watcher→span bridge is one-way and opt-in (`SIDEQUEST_WATCHER_AS_SPANS=1`); there
  is no span→watcher reverse bridge. If this proves false (e.g. a `WatcherSpanProcessor`
  reverse path lands), log a deviation — but the scout read confirms it
  (`watcher_hub.py:42-59,497-582`).
- **`component="retrieval"` is the established subsystem label.** 75-6 already
  publishes entity-sync events under `component="retrieval"`
  (`entity_sync.py:62,90`); reusing it groups universal-retrieval and entity-sync
  under one Subsystems-tab label rather than fragmenting the subsystem across two.
- **The existing `state_transition` `WatcherEventType` + the `component`/`field`
  rendering carries this event with no UI change.** The `Dashboard/` Subsystems and
  Timeline tabs render `state_transition` events grouped by `component`
  (`watcher.ts:22-29`). If a bespoke retrieval panel is wanted, that is a separate
  UI story; this backend story stays inside the existing contract.
- **The 75-5-deferred "per-turn total budget unification" is NOT this story.** It is
  a budget-seam change misfiled into 75-7 by 75-5's context note. 75-7 is
  instrumentation + GM-panel surfacing per its title; budget unification is deferred
  (flag as a Delivery Finding if desired).
- **`RetrievedEntities` exposes every value the watcher event needs.** The frozen
  dataclass (`retrieval_orchestration.py:73-97`) carries all §D5 attributes as typed
  fields; per-type counts derive from the `retrieved_*` lists. No new return-shape
  change is required in 75-5's code.

---
_Authored by the Architect during SETUP-phase story definition, 2026-06-02. The
session file (`.session/75-7-session.md`) was created by `sm-setup` as a stub
(setup phase, no Implementation Contract yet) and remains the higher-authority
spec once populated; this document is the scout-grounded test-strategy lens the
context gate (`pf validate context-story 75-7`) requires. Sources: ADR-118 (§D5
OTEL observability — the exact span name `retrieval.universal` and full attribute
contract; §Composition waterfall), epic-75 context (scout audit of the lore-only
RAG and the universal-layer vision), sibling 75-5 context (the span emitter,
already shipped) and 75-6 context (the dual-emission gold-standard pattern), and a
live read (2026-06-02) of `game/retrieval_orchestration.py` (span + outcome enum),
`server/dispatch/entity_sync.py` and `server/dispatch/lore_embed.py` (the
span+`publish_event` dual pattern), `telemetry/watcher_hub.py` (the GM-panel
transport and the one-way span bridge), `server/websocket_session_handler.py:2500,2986`
(the live retrieval seam), `server/dashboard.py` + `sidequest-ui/src/types/watcher.ts`
(the GM-panel surface and closed event-type union). **Load-bearing scout finding
that reshapes scope:** the `retrieval.universal` span already fires (75-5); the real
75-7 gap is that it never reaches the GM panel because `retrieve_turn_context`
emits no WatcherHub `publish_event` — 75-7 adds the watcher-emission half, mirroring
the lore + entity-sync siblings, not the span._
