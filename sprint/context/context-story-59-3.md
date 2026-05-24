---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-3: Repurpose confrontation_intent_validator as router-vs-engine lie-detector watcher

## Business Context

This is the **lie-detector** for Epic 59's Intent Router spine. The router (59-2)
produces a `DispatchPackage`; 59-4 will engage engines from those dispatches before
the narrator runs. Between "router said the action should engage X" and "engine X
actually engaged on the post-turn snapshot" there is a thin gap where the new
pipeline can silently fail — a dispatch never reaches its handler, a handler
crashes silently, or the engine no-ops because of upstream state corruption.
Without an observer watching for that mismatch, every regression in 59-4/5/6/7
risks landing as "convincing prose with zero mechanical backing" — the exact
SOUL-Illusionism failure mode the epic exists to defeat.

This story repurposes machinery built for the 59-1 point fix (narrator-sidecar
vs engaged-encounter mismatch) into the broader router-vs-engine mismatch watcher
the spine needs. It also retires the 59-1 self-report-reprompt path — per the
project's "one mechanism per problem" memory, the watcher replaces the reprompt
loop. Per CLAUDE.md OTEL Observability Principle, the GM panel (Sebastien's
mechanics-first surface, and Keith's dev-side lie detector) can only verify the
engine engaged if the watcher emits a per-dispatch span.

**Sebastien-facing GM-panel impact:** when (not if) the router dispatches but the
engine doesn't engage, a `dispatch_engagement.{subsystem}.mismatch` span appears
in the panel, with the dispatched subsystem and the post-turn-snapshot evidence —
provable mechanical accountability across the full dispatch vocabulary
(confrontation, magic_working, scenario_clue, and the three additive subsystems
landing in 59-7).

## Technical Guardrails

### Reuse-first inventory (per Architect pragmatic-restraint)

Every component you need exists. Do not invent.

| Component | Location | Status |
|-----------|----------|--------|
| Validator module to repurpose | `sidequest/agents/confrontation_intent_validator.py` | Live — pure function, no I/O, stateless |
| Pure-function tokenizer | `confrontation_intent_validator.py:64` `tokenize()` | Reuse if doing any string-token work; likely unused by the new path |
| Mismatch span emitter | `sidequest/telemetry/spans/confrontation_intent.py` `confrontation_unengaged_turn_span` (line ~144) | Reuse for confrontation case |
| Mismatch span emitter (intent-based) | same file, `confrontation_intent_mismatch_span` | Reuse / generalize naming if cleanly possible |
| Reprompt-failed span (to retire) | same file, `SPAN_CONFRONTATION_INTENT_MISMATCH_REPROMPT_FAILED` (line 48) | Remove span constant + context manager + route registration; remove all callers (`websocket_session_handler._execute_narration_turn` reprompt loop) |
| `DispatchPackage` (post-59-2 shape) | `sidequest/protocol/dispatch.py:183` | Read-only consumer — package.dispatch, package.per_player, package.cross_player, package.narrator_directives, package.lethality_verdicts. **No `degraded` field** (59-2 removed it). |
| `SubsystemDispatch` | `sidequest/protocol/dispatch.py:88` | Read-only — `subsystem: str` is the key |
| `run_dispatch_bank` executor | `sidequest/agents/subsystems/__init__.py:160` | Watcher does NOT run inline with the bank — it runs *post-turn* on the resulting snapshot |
| `IntentRouter.decompose` producer | `sidequest/agents/intent_router.py` (shipped by 59-2) | Read-only consumer of its output package |
| Snapshot type | `sidequest.game.snapshot.SnapshotV1` (existing) | Read fields: `snap.structured_encounter`, `snap.magic_state` (or equivalent), `snap.scenario_state` |

### Architecture — where the watcher lives

The watcher is a **pure function** with signature:

```python
def detect_dispatch_engagement_mismatch(
    package: DispatchPackage,
    post_turn_snapshot: SnapshotV1,
) -> list[DispatchMismatch]:
    """Return mismatches: dispatched-but-engine-not-engaged subsystems."""
```

(`DispatchMismatch` is a new lightweight dataclass — subsystem, dispatched_params,
expected_engagement_witness, severity. Keep it dataclass-frozen.)

**Wiring site:** post-turn, after `run_dispatch_bank` and `narration_apply` have
completed but before the broadcast goes out. The natural call site is in
`sidequest.server.websocket_session_handler._execute_narration_turn` (or its
post-turn equivalent — confirm with Dev/TEA during RED). Wherever you wire it,
it MUST consume the same package the bank consumed, and the same snapshot the
broadcast will reflect — not a separate snapshot read.

**Output:** one OTEL span per mismatch entry, NOT one per turn. A turn with two
mismatches emits two spans. Span name convention:
`dispatch_engagement.{subsystem}.mismatch` (e.g. `dispatch_engagement.confrontation.mismatch`,
`dispatch_engagement.magic_working.mismatch`, `dispatch_engagement.scenario_clue.mismatch`).
Span attributes: subsystem, dispatched_params (compact), post_turn_witness (the
field that was checked and was empty/wrong), confidence-from-dispatch.

### Engagement witnesses — what "engaged" means per subsystem

| Subsystem | Engagement witness on snapshot |
|-----------|-------------------------------|
| `confrontation` | `snap.structured_encounter is not None` AND `snap.structured_encounter.kind` matches the dispatched confrontation type |
| `magic_working` | A new magic working / spell-effect record appears on the snapshot's magic state for this turn (confirm precise field with Dev during RED — see `apply_magic_working` at `narration_apply.py:638` for what it mutates) |
| `scenario_clue` | A new fact_id advancement / clue-graph state change for this turn (confirm precise field — see `consume_clue_footnotes` at `dispatch/scenario_clue_intake.py:34`) |

If 59-7's three additive subsystems (`npc_agency`, `distinctive_detail_hint`,
`reflect_absence`) need to be watched, the watcher's vocabulary should be
**registry-driven**, not a hardcoded switch — a `dict[subsystem_name,
EngagementChecker]` so 59-7 can add three keys without re-touching the watcher
core. (Reuse pattern: `subsystems/__init__.py` already uses a registry — mirror
the shape.)

### Fail-loud discipline (project memory `feedback_no_fallbacks_hard`)

- The watcher is a **pure function**; it does not catch and swallow exceptions
  from the engagement checks. If a snapshot field is malformed, the watcher
  raises and the turn fails LOUD with the error span. **No silent skip.**
- The watcher does **not** retry, dispatch corrections, or attempt to engage
  an engine after the fact. It observes and emits. Mechanical engagement is
  the bank's job; correction (if any) belongs to a later story.
- Confidence below dispatch threshold = no dispatch = no watcher input = no
  span. That is correct silence, not a fallback.

### One mechanism per problem (project memory `feedback_one_mechanism_per_problem`)

This story REMOVES:

1. `confrontation_intent_mismatch_reprompt_failed_span` (the span constant,
   the context manager, the `SPAN_ROUTES` entry — `confrontation_intent.py:48-56` and 127-141).
2. The reprompt loop in `websocket_session_handler._execute_narration_turn`
   that calls the narrator a second time after a 59-1 mismatch.
3. Any callers of `confrontation_intent_mismatch_reprompt_failed_span`.
4. **If still present** (depends on what 59-2 left of it): the
   `_CONFRONTATION_TRIGGER_PATTERNS` keyword scanner (the deleted-2026-05-20
   regex lie-detector). It is supposed to be gone (commit `93c7659`); verify
   in RED — if any keyword-pattern code remains, remove it.

The watcher is the replacement for ALL of the above.

### Test wiring (CLAUDE.md "Every Test Suite Needs a Wiring Test")

Per CLAUDE.md "No Source-Text Wiring Tests" — do not grep production source
to assert wiring. The wiring test for this story drives a fixture turn
through the real post-turn hook with a synthetic `DispatchPackage` and an
empty-engagement snapshot, then asserts the span fired. The canonical shape
is `tests/server/test_location_description_emit.py::test_emit_sends_message_when_room_has_manifest`.

## Scope Boundaries

**In scope:**

- New pure function `detect_dispatch_engagement_mismatch(package, snapshot)`
  (location: keep within `sidequest/agents/confrontation_intent_validator.py`
  or split out — Dev/Architect call during RED; renaming the file is fine if
  the rename is mechanical).
- New OTEL spans `dispatch_engagement.{confrontation,magic_working,scenario_clue}.mismatch`
  with `SPAN_ROUTES` registration. (Architect prefers a registry-driven
  emitter so 59-7 adds entries without re-wiring; if implementation cost is
  high, three named spans is acceptable for 59-3.)
- Wire the watcher into the post-turn pipeline so it runs once per turn
  with `(consumed_package, post_turn_snapshot)`.
- Remove `confrontation_intent_mismatch_reprompt_failed_span` and its single
  reprompt-loop caller.
- All-three-subsystem coverage: confrontation, magic_working, scenario_clue.
- One wiring test that drives a real router-dispatch-without-engine-engagement
  turn through the post-turn hook (not a mocked unit test).
- Unit tests for the pure function covering: dispatched + engaged (no span),
  dispatched + not-engaged (span), no-dispatch + no-engagement (no span — quiet turn),
  dispatched + wrong-engagement-kind (span — confrontation type mismatch),
  multiple mismatches in one package (multiple spans).

**Out of scope (deferred to other stories):**

- Live wiring of `IntentRouter` into the orchestrator turn pipeline — that
  is 59-4.
- Confrontation dispatch handler (`subsystems/confrontation.py`) — 59-4.
- Magic dispatch handler (`subsystems/magic_working.py`) — 59-5.
- Scenario clue dispatch handler (`subsystems/scenario_clue.py`) — 59-6.
- Three additive subsystem handlers (`npc_agency`, `distinctive_detail_hint`,
  `reflect_absence`) — 59-7. (Watcher MUST be extensible to cover them; this
  story does not have to fire spans for them.)
- Retiring `begin_confrontation` tool — 59-4.
- Removing `confrontation` from `_SDK_TOOL_OWNED_FIELDS` — 59-4.
- ADR updates — 59-2 already shipped ADR-113; 59-4 amends ADR-111.
- The pre-existing `tokenize()` / `validate()` / `ValidationResult` machinery
  in `confrontation_intent_validator.py`. The new watcher is parallel
  infrastructure; the old narrator-sidecar-mismatch path stays live until
  59-4 retires it. **Do not touch `validate()` or `tokenize()` in this story.**
  (Touching them is 59-4 scope when the sidecar path retires.)

## AC Context

> AC text reproduced verbatim from `sprint/epic-59.yaml` 59-3. Architect
> commentary inline.

### AC1: Router dispatched `confrontation:negotiation` + snapshot has no encounter → mismatch span fires (existing `confrontation_unengaged_turn_span` reused).

**Testable shape:** Build a `DispatchPackage` with one `SubsystemDispatch(subsystem="confrontation", ...)`.
Build a `SnapshotV1` where `snap.structured_encounter is None`. Call the watcher.
Assert one `dispatch_engagement.confrontation.mismatch` span emitted.

**Architect note on span name:** AC1 says "existing `confrontation_unengaged_turn_span` reused".
The 59-1 span name is `confrontation.unengaged_turn`. The watcher's new span family is
`dispatch_engagement.{subsystem}.mismatch`. **Recommended interpretation:** the AC text
predates final naming. Use the new family name `dispatch_engagement.confrontation.mismatch`
for consistency with AC4 (which introduces the family explicitly). If TEA prefers the
literal AC reading, route the new span through the existing span constant and
extend `SPAN_ROUTES` — both are acceptable. Architect lean: **new family name; retire
or alias the 59-1 span**. Flag in Design Deviations log either way.

**Edge cases:**
- Dispatched confrontation subtype `"negotiation"` but `snap.structured_encounter.kind == "negotiation"` already engaged → NO span (AC2).
- Dispatched `"negotiation"` but encounter has `kind == "duel"` → span fires (kind mismatch is still a mismatch).

### AC2: Router dispatched `confrontation:negotiation` + snapshot has matching encounter → no span (no false positive).

**Testable shape:** Same package; snapshot has `structured_encounter` with matching
type. Watcher emits zero spans. The "matching" check is on encounter kind/type,
not on identity — a re-engagement of the same encounter type still satisfies.

### AC3: Router dispatched nothing + snapshot has no encounter → no span (no false positive on quiet turns).

**Testable shape:** Empty-dispatch `DispatchPackage` (no entries in `package.dispatch`).
Snapshot has no engagement. Watcher emits zero spans. This is the "quiet walk through
town" case (SOUL Cost-Scales-with-Drama — zero compute, zero noise).

### AC4: Watcher covers `magic_working` and `scenario_clue` dispatch mismatches. NEW spans: `dispatch_engagement.{subsystem}.mismatch`.

**Testable shape:** Two more unit tests mirroring AC1, one per subsystem.
For `magic_working`: dispatched but no new magic-state record on snapshot → span.
For `scenario_clue`: dispatched but no fact-graph advancement on snapshot → span.

**Engagement witness ambiguity:** the precise snapshot field for "magic engaged"
and "clue advanced" is not 100% pinned from outside the engine. Dev/TEA should
during RED:
1. Read `apply_magic_working` (`narration_apply.py:638`) to identify what it mutates.
2. Read `consume_clue_footnotes` (`dispatch/scenario_clue_intake.py:34`) similarly.
3. Pick the field that the engine sets and use it as the witness.

If the engine writes a state delta rather than a flag, the witness check is
"the snapshot field changed shape in a way that proves the engine fired" —
e.g. a new entry in a list whose length the watcher can compare against an
empty baseline.

If the witness is ambiguous, **stop and flag a Design Deviation** before
committing — do not guess the witness. (Wrong witness = false-positive spam in
the GM panel, which makes the lie detector itself a liar.)

### AC5: Wiring test — drive a synthetic router-dispatched-not-engaged turn through the real watcher hook (not a unit-test mock); assert span emission.

**Testable shape:** Construct a real turn pipeline fixture (mirrors
`tests/server/test_location_description_emit.py` shape):

1. Synthetic genre pack + snapshot fixture.
2. Construct a `DispatchPackage` synthetically (skip the live IntentRouter —
   59-2's tests already cover decompose; this AC tests *the watcher's wiring*,
   not the router's).
3. Drive the real post-turn hook — the function the orchestrator calls.
4. Assert the OTEL span fired (via the OTEL test exporter, not source-grep).

**Anti-pattern guard:** Do NOT use `read_text()` + regex on
`websocket_session_handler.py` to "prove" the watcher is called. Drive the
real call site.

### AC6: The 59-1-shipped `confrontation_intent_mismatch_reprompt_failed_span` self-report-reprompt flow is REMOVED (replaced by the watcher; "one mechanism" rule).

**Testable shape:**

1. The span constant `SPAN_CONFRONTATION_INTENT_MISMATCH_REPROMPT_FAILED`
   no longer exists in `sidequest/telemetry/spans/confrontation_intent.py`.
2. The context manager `confrontation_intent_mismatch_reprompt_failed_span`
   no longer exists.
3. The `SPAN_ROUTES` entry for that span name no longer exists.
4. No caller imports the removed symbol (verify via the test suite still
   passing after removal, not via grep-on-source).
5. The reprompt loop in `_execute_narration_turn` is removed: after a 59-1
   `validate()` mismatch fires its span, the turn proceeds (no second narrator
   call). The watcher catches downstream engagement failures instead.

**Architect note:** The 59-1 validator path (`validate()` returning a
`ValidationResult` on narrator-sidecar mismatch) is OUT OF SCOPE here. Only the
**reprompt response** to that mismatch is being retired. The validator itself
stays live and emits `confrontation.intent_mismatch` until 59-4 retires the
whole sidecar path. **Do not remove `validate()` or its span — just the reprompt loop.**

## Assumptions

1. **59-2 has shipped** the `IntentRouter` class and the post-degraded
   `DispatchPackage` shape. Confirmed: 59-2 status is `done`, archive session
   present. If the actual code shape disagrees with what the 59-2 session
   describes, log as Design Deviation and re-plan with Architect/SM.
2. **The post-turn pipeline has a natural wiring site** — i.e. there is a
   point after `run_dispatch_bank` + `narration_apply` and before the
   broadcast where both `package` and `snapshot` are in scope. If no such
   site exists today, that is itself a finding — log a Design Deviation;
   creating one is acceptable scope creep within this story (the watcher
   is useless without a call site).
3. **The OTEL test exporter / capture harness used in
   `tests/server/test_location_description_emit.py` is reusable.** If not,
   adopt whatever the rest of `tests/server/` uses for span assertions.
4. **Snapshot engagement-witness fields exist and are stable.** Mid-story
   discovery that magic_state or scenario_state is reshaped breaks AC4 —
   log as Design Deviation and pin the witness via Dev/Architect consult.
5. **The watcher is invoked from the same orchestrator code path that
   consumed the package.** Two separate read sites (one for the bank, one
   for the watcher) is a correctness bug waiting — keep the package and
   snapshot in one frame and pass both to the watcher.

If any of these proves wrong during RED or green, log under
`## Design Deviations` per `deviation-format.md` and notify SM (Captain
Carrot) immediately — wrong assumptions are the #1 source of scope creep.

---

**Architect:** Leonard of Quirm
**Date:** 2026-05-24
**Parent epic context:** `sprint/context/context-epic-59.md`
**Spec under PR:** none (the 59-3 scope is fully captured in epic context + this story context)
