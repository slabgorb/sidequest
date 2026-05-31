---
id: 123
title: "Mechanical-Engagement Pipeline — Confidence-Gated Topological Dispatch Bank, Precondition/Unregistered Gates, and the LethalityArbiter"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [33, 67, 113, 114, 116]
tags: [agent-system, game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-123: Mechanical-Engagement Pipeline

> **Documents a system already live in code.** The pipeline that decides *which*
> mechanical dispatches fire each turn, *in what order*, and *how 0-HP outcomes
> are adjudicated* — the confidence gate, the precondition and unregistered
> gates, the topologically-sorted dispatch bank, and the `LethalityArbiter` —
> shipped across stories 59-8, 71-16, and 71-27 (plus the 2026-04-23 decomposer
> Group C) without a governing ADR. This record closes that
> architecture-of-record gap and states what the decision *was*. It also
> **explicitly closes ADR-113's "deferred" gap**: ADR-113's 2026-05-28 amendment
> declared per-dispatch confidence scoring and threshold-gating DEFERRED / not
> implemented — but Story 71-16 then shipped them. This ADR records that landing
> and reconciles the two.

## Context

ADR-113 (Intent Router — Mechanical-Engagement Spine) established the structural
spine: a pre-narrator Haiku pass (`IntentRouter.decompose`) emits a
`DispatchPackage`, and `run_dispatch_bank` engages the matching mechanical
engines *before* the narrator runs, so the narrator narrates already-real state
rather than winging the mechanics (the SOUL Illusionism counter, ADR-002).

ADR-113 ratified that spine but left — or deferred — four behavioral questions
that the spine *cannot* answer on its own and that determine whether the engines
fire correctly:

1. **Which dispatches deserve to fire at all?** ADR-113 §Confidence gate
   specified a per-subsystem threshold (proposed 0.6, tunable in `rules.yaml`)
   below which a dispatch must degrade to a narrator hint rather than engage an
   engine — the "untaken bait" guard. ADR-113's 2026-05-28 amendment then
   recorded this as **DEFERRED / not implemented**: `run_dispatch_bank` fired
   *every* emitted dispatch unconditionally, and `SubsystemDispatch` carried no
   `confidence` field at all.

2. **In what order do they fire?** Dispatches can depend on each other (Group C
   lethality reads `npc_agency` disposition output); execution order must
   respect those dependencies deterministically.

3. **Which dispatches can never fire on this snapshot and should be removed
   before they pollute the lie-detector?** Two failure shapes were producing
   *guaranteed* false-positive `dispatch_engagement.{subsystem}.mismatch` spans
   on the post-turn watcher (ADR-113's lie-detector): (a) a `scenario_clue`
   dispatch in a world that ships no ADR-053 scenario graph (Glenross, playtest
   59-8), and (b) the router emitting a subsystem key with no registered handler
   — canonically `combat`, which is a confrontation *type* routed through the
   `confrontation` subsystem, not a subsystem key (Story 71-27).

4. **How is a 0-HP outcome adjudicated, deterministically, across genres?**
   ADR-114 (Ablative HP Substrate) made HP a first-class lethality track; 0 HP
   must produce an authoritative, genre-policy-driven verdict the narrator
   cannot soften or escalate on its own.

These four concerns compose into one ordered pipeline sitting between the intent
router and the narrator. It shipped piecemeal; this ADR is its design of record.

### The engines and consumers are not the broken part

The dispatch bank executor (`run_dispatch_bank`), the `LethalityArbiter`, and
the `DispatchPackage` protocol were all merged dormant during the 2026-04-23
LocalDM Group A/B/C work (`docs/superpowers/specs/completed/2026-04-23-local-dm-decomposer-design.md`,
cited at `sidequest/agents/lethality_arbiter.py:5`). ADR-113 woke the spine.
The work this ADR documents is the *gating and adjudication discipline* layered
onto that woken spine — wiring and behavior, not reinvention (CLAUDE.md
"Don't Reinvent").

## Decision

**A turn's mechanical actions pass through a fixed five-stage pipeline between
the intent router's `decompose` and the narrator. Each stage either removes
dispatches that must not fire, orders the survivors, fires them under a
confidence gate, or adjudicates lethality — and each stage emits a loud OTEL
span so the GM panel can audit it.**

### Pipeline stage order

```
IntentRouter.decompose(action, state_summary)        # Haiku via SDK → DispatchPackage
  → run_unregistered_subsystem_gate                  # Stage 1: drop dispatches naming a subsystem with no handler
  → run_dispatch_precondition_gate                   # Stage 2: drop structurally-inert dispatches (e.g. scenario_clue, no graph)
  → run_dispatch_bank                                # Stage 3: topo-sort by depends_on, confidence-gate per dispatch, fire engines
  → LethalityArbiter.arbitrate                        # Stage 4: synthesize 0-HP verdicts + paired must/must-not directives
  → narrator directives registration                 # Stage 5: bank + arbiter directives → narrator_directives prompt section
  → narrator turn                                     # narrates already-real state
  → dispatch_engagement_watcher                       # post-narration lie-detector (reads the GATED package)
```

Stages 1 and 2 run in the pre-narrator pass
(`execute_intent_router_pre_narrator_pass`,
`sidequest/server/intent_router_pass.py`), in that order, *before* the bank and
*before* the gated package is handed to the caller for
`turn_context.dispatch_package` (which the post-turn watcher reads). Stage 3 is
the single per-turn `run_dispatch_bank` call. Stages 4 and 5 run in the
orchestrator's narrator-prompt build (`orchestrator.py:2628-2672`).

### Stage 1 — Unregistered-subsystem gate (Story 71-27)

`run_unregistered_subsystem_gate` (`dispatch_precondition_gate.py:229`) drops
every dispatch whose `subsystem` is absent from the live bank registry
(`get_registered()`, injected by the caller so the gate stays registry-free and
testable — `intent_router_pass.py` passes `registered=set(get_registered())`).
The canonical drop is the router emitting `combat` as a subsystem (it is a
confrontation *type*, `params["type"]`, routed through `confrontation`). Such a
dispatch can never engage; registering a `combat` handler would be a stub for a
non-subsystem (CLAUDE.md "No Stubbing"). It runs **first** — before the
precondition gate, the bank, and the watcher — so the unhandlable dispatch never
pollutes the redaction path or the lie-detector. Each drop emits a loud
`intent_router.dispatch.unregistered` span (`dispatch_precondition_gate.py:243`).

### Stage 2 — Precondition gate (Story 59-8)

`run_dispatch_precondition_gate` (`dispatch_precondition_gate.py:132`) drops
dispatches that are *structurally inert* on the snapshot — they can never engage
no matter what the narrator does because a world-level precondition is unmet.
The map of predicates is `_INERT_PRECONDITIONS`
(`dispatch_precondition_gate.py:78`); the only entry today is `scenario_clue`,
inert when `snapshot.scenario_state is None`
(`_scenario_clue_precondition_unmet`, `dispatch_precondition_gate.py:72`) — the
Glenross case where no ADR-053 clue graph exists. Rather than silence the
post-turn watcher (which would blind it to *genuine* mismatches in real scenario
worlds), the gate removes the inert dispatch from the package before the bank
**and** before the watcher reads it, emitting a loud
`intent_router.dispatch.gated` span per drop (`dispatch_precondition_gate.py:145`).
In a real scenario world (`scenario_state` present) the dispatch passes through
untouched. A subsystem absent from `_INERT_PRECONDITIONS` is never gated.

Both gates preserve idempotency-key uniqueness (they only *remove* keys), so the
`DispatchPackage` validator invariant still holds, and both return the original
package unchanged (no copy) when nothing is dropped.

### Stage 3 — Topo-sorted, confidence-gated dispatch bank (Story 71-16)

`run_dispatch_bank` (`sidequest/agents/subsystems/__init__.py:214`) is the single
per-turn engine-engagement run.

- **Topological ordering by `depends_on`.** `_topo_sort`
  (`subsystems/__init__.py:188`) orders dispatches so each fires after its
  `depends_on` keys (DFS over `SubsystemDispatch.depends_on`, keyed by
  `idempotency_key`). A `depends_on` cycle raises `ValueError`
  (`subsystems/__init__.py:198`); the bank catches it, records a `__bank__`
  error, sets `error="topo_sort_failure"` on the bank span, runs zero subsystem
  dispatches, and still flows decomposer-authored `narrator_instructions`
  (`subsystems/__init__.py:248-256`).

- **Per-dispatch confidence gate.** For each dispatch the bank resolves a
  threshold via `_threshold_for` (`subsystems/__init__.py:63`): the per-subsystem
  override from the pack's `RulesConfig.dispatch_confidence_thresholds`, falling
  back to `DEFAULT_DISPATCH_CONFIDENCE_THRESHOLD = 0.6`
  (`subsystems/__init__.py:60`). If `d.confidence < threshold` the dispatch
  **degrades to a narrator hint** — a `must_narrate` `NarratorDirective`
  instructing the narrator to narrate the attempt naturally and *not* treat the
  engine as having fired — and the engine is never invoked
  (`subsystems/__init__.py:277-293`). At or above threshold the engine fires
  (`decision="engaged"`). This is ADR-113's "untaken bait" guard, now real.

- **Engine engagement.** The bank looks up the handler in `_REGISTRY`
  (populated by `_register_defaults`, `subsystems/__init__.py:162`: seven live
  handlers — `confrontation`, `magic_working`, `scenario_clue`, `reflect_absence`,
  `distinctive_detail_hint`, `npc_agency`, `movement`), filters `context` to the
  kwargs the handler actually declares (`_filter_context_for_callable`,
  `subsystems/__init__.py:85` — handlers have heterogeneous signatures, e.g.
  `run_npc_agency` requires `npc_pool` while `run_distinctive_detail` takes only
  `dispatch`), and awaits it. Per-handler exceptions are caught and recorded as
  bank errors; the bank never re-raises (`subsystems/__init__.py:312-324`), so one
  engine failing does not abort the others — the post-turn watcher catches the
  resulting dispatch-without-engagement mismatch.

The bank returns a `BankResult` (directives + `outputs_by_key` + errors). The
pre-narrator pass runs the bank exactly **once** per turn and the orchestrator
consumes the stashed `BankResult` rather than re-running it
(`intent_router_pass.py` docstring: re-running "would engage every engine a
second time").

### Stage 4 — LethalityArbiter (2026-04-23 decomposer Group C; ADR-114)

`LethalityArbiter.arbitrate` (`sidequest/agents/lethality_arbiter.py:57`) runs
**after the bank and before the narrator directives are registered**
(`orchestrator.py:2628-2646`). It is deterministic and synchronous — no LLM call.

- It reads the genre pack's `LethalityPolicy` (`genre/models/lethality.py`).
- Phase A trigger is HP-based per ADR-114: any PC core (`pc_cores_by_player`) or
  NPC core (`npc_cores_by_name`) with `hp.current == 0` fires the policy's
  `verdicts_on_zero_hp` entry (`.pc` / `.npc`)
  (`lethality_arbiter.py:70-85`). (`verdicts_on_zero_hp` was renamed from
  `verdicts_on_zero_edge` for ADR-114 — `genre/models/lethality.py:14`.)
- For each zero-HP entity it emits an authoritative `LethalityVerdict` plus a
  **paired** `must_narrate` / `must_not_narrate` `NarratorDirective` envelope
  (`_emit`, `lethality_arbiter.py:96-133`) — the narrator decides *how* to
  describe the verdict, never *whether* it fires.
- **Arbiter wins on entity conflict.** Decomposer-authored verdicts in
  `DispatchPackage.per_player[*].lethality` are merged only for entities the
  arbiter did not itself rule on; on any entity conflict the arbiter's verdict is
  authoritative and the decomposer's is dropped (`lethality_arbiter.py:86-92`).

The arbiter's directives join the bank's directives in the same high-attention
`narrator_directives` prompt section (`orchestrator.py:2656-2672`).

### Stage 5 — Narrator directives registration

The orchestrator strips directives whose visibility is
`redact_from_narrator_canonical` (MP perception firewall, ADR-105 — uniformly
covering subsystem-output directives, confidence-gate degraded hints, and
decomposer `narrator_instructions`), combines the visible bank directives with
the arbiter directives, and registers them as the `narrator_directives` section
in `AttentionZone.Recency` (`orchestrator.py:2648-2672`). A present
`dispatch_package` with a `None` `bank_result` is a wiring break and raises —
fail loud, No Silent Fallbacks (`orchestrator.py:2620-2626`).

## Invariants / Contracts

- **Topological `depends_on` ordering.** Every dispatch executes after all of its
  `depends_on` keys. Cycles fail loud (`ValueError` → recorded bank error, zero
  dispatches run, span `error="topo_sort_failure"`). Duplicate idempotency keys
  in the sorted order are de-duplicated (`seen` set, `subsystems/__init__.py:258-262`).
- **Confidence threshold + degrade-to-hint.** A dispatch engages its engine iff
  `confidence >= threshold` (per-subsystem override → `0.6` default). Below
  threshold it produces exactly one `must_narrate` hint and engages no engine.
  Both the confidence and the threshold are recorded on the subsystem span. A
  malformed threshold is not silently guessed — `dispatch_confidence_thresholds`
  must be a real mapping, and malformed values fail loud at pack load in
  `RulesConfig` validation (`subsystems/__init__.py:63-82`).
- **Gates before bank and before watcher.** Both Stage 1 and Stage 2 run in the
  pre-narrator pass before `run_dispatch_bank` *and* before the (gated) package
  is assigned to `turn_context.dispatch_package` — so the post-turn lie-detector
  never sees a dispatch that was structurally guaranteed to mismatch
  (`intent_router_pass.py`, gate-then-bank ordering). Stage 1 runs before Stage 2.
- **Arbiter wins on conflict.** On an entity the arbiter ruled on, the arbiter's
  `LethalityVerdict` is authoritative; a decomposer-authored verdict for the same
  entity is dropped. Decomposer verdicts for entities the arbiter did not touch
  pass through.
- **Single bank run per turn.** The pre-narrator pass is the sole
  `run_dispatch_bank` invocation; the orchestrator consumes the stashed
  `BankResult` and must not re-run the bank (double-engagement guard).
- **Gates preserve key uniqueness.** Both gates only remove dispatches, never add
  or rename, so the `DispatchPackage` package-level validator's
  unique-idempotency-key invariant continues to hold.

## Observability

Every stage emits an OTEL span — the GM-panel lie-detector (CLAUDE.md "The GM
panel is the lie detector"). Span definitions live in
`sidequest/telemetry/spans/intent_router.py`:

- **`intent_router.dispatch.unregistered`** (Stage 1, `:165` / `:178`) — one per
  dropped unhandlable dispatch; attributes `subsystem`, `idempotency_key`.
  Distinct from the gated span so the panel can tell "router emitted garbage"
  apart from "world has no clue graph".
- **`intent_router.dispatch.gated`** (Stage 2, `:125` / `:139`) — one per
  structurally-inert drop; attributes `subsystem`, `idempotency_key`, `reason`.
- **`intent_router.dispatch_bank`** (Stage 3 outer, `:71` / `:274`) — once per
  bank run; attributes `turn_id`, `dispatch_count` (and `error=topo_sort_failure`
  on cycle).
- **`intent_router.subsystem`** (Stage 3 per dispatch, `:82` / `:290`) — one per
  dispatch; attributes include `subsystem`, `idempotency_key`,
  `produced_directives`, `error`, and the confidence-gate trio **`confidence`,
  `threshold`, `decision`** (`engaged` | `degraded_to_hint`) added for Story
  71-16 (`:92-97`). This trio is the audit record that closes ADR-113's gap: the
  panel sees the score, the threshold, and the engage/degrade decision for every
  dispatch.
- **`intent_router.lethality_arbitrate`** (Stage 4, `:100` / `:307`) — once per
  arbiter run; attributes `turn_id`, `genre_key`, `verdict_count`.

No stage degrades silently: every drop, every below-threshold non-engagement,
every per-handler error, and every cycle is a loud span, honoring No Silent
Fallbacks.

## Consequences

**Positive**

- **ADR-113's "untaken bait" guard is real.** A weak Haiku inference no longer
  fires an engine; it reaches the narrator as a hint instead. Packs tune the
  threshold per subsystem without code changes.
- **The lie-detector stops crying wolf.** The two gates remove the only two known
  classes of *guaranteed* false-positive mismatch (no-graph `scenario_clue`,
  unregistered `combat`), so a `dispatch_engagement.*.mismatch` span now means a
  *genuine* illusionism failure worth investigating.
- **Deterministic lethality.** 0-HP outcomes are adjudicated by genre policy, not
  improvised by the narrator; the arbiter's verdict is authoritative over any
  decomposer guess.
- **Ordering is explicit and auditable.** `depends_on` topo-sort makes
  cross-subsystem data flow (e.g. lethality reading `npc_agency` output)
  deterministic and cycle-safe.

**Negative / cost**

- **Two gates plus a per-dispatch threshold lookup add pre-bank work** every turn.
  The cost is small (set membership, predicate map, dict lookup) and dwarfed by
  the Haiku call, but it is real per-turn surface.
- **`_INERT_PRECONDITIONS` is a hand-maintained map.** Each new structurally-inert
  shape needs a predicate; a missing one returns the false-positive-mismatch
  regime the gate was built to remove (visible, at least, as a watcher span).
- **Threshold tuning is unmodelled.** The `0.6` default and any per-subsystem
  overrides are playtest-calibrated; the subsystem span's confidence/threshold
  attributes are the data source for that calibration.
- **Arbiter Phase A is HP-only.** Confrontation-beat-failure and
  resource-pool-depletion triggers are not yet wired (Group E), so non-HP
  lethality paths do not fire arbiter verdicts yet.

## Alternatives considered

- **Leave confidence-gating deferred (ADR-113 status quo).** Rejected: firing
  every dispatch unconditionally forces confrontations the player never committed
  to — the exact "untaken bait" failure SOUL forbids. Story 71-16 implemented the
  gate.
- **Silence the post-turn watcher for no-graph worlds instead of gating.**
  Rejected in Story 59-8: silencing blinds the lie-detector to *genuine*
  mismatches in real scenario worlds. Removing the structurally-inert dispatch
  before the watcher (and emitting a loud gated span) is the No-Silent-Fallbacks
  answer.
- **Register a `combat` handler.** Rejected in Story 71-27: `combat` is a
  confrontation *type*, not a subsystem; a handler would be a stub for a
  non-subsystem (No Stubbing). The unregistered gate drops it loudly instead.
- **Let the narrator adjudicate 0 HP.** Rejected: that is precisely the
  improvisation ADR-114 + this arbiter exist to prevent. Determinism with a
  paired must/must-not directive envelope keeps the *what* mechanical and the
  *how* narrative.
- **Run the bank twice (pre-narrator and in the orchestrator).** Rejected as a
  double-engagement bug source (a PC would move twice, a clue consume twice). One
  run; the `BankResult` is stashed and reused.

## Reconciliation

- **ADR-113 (Intent Router — Mechanical-Engagement Spine).** ADR-113's
  2026-05-28 amendment stated, precisely: the router spine is "live end-to-end,"
  but "the §Confidence gate is **NOT implemented** — it is deferred,"
  `run_dispatch_bank` "executes **every** emitted dispatch unconditionally,"
  there is "**no per-dispatch confidence field to gate on**," and "Validation of
  the spine (the 59-8 Glenross playtest gate) is also still **backlog**."
  **This ADR records what subsequently shipped against those exact items:**
  (1) Story 71-16 added the per-dispatch confidence read and threshold gate to
  `run_dispatch_bank` (`subsystems/__init__.py:60-82`, `:268-293`) with the
  per-subsystem `rules.yaml` override (`_threshold_for`) and the
  `confidence`/`threshold`/`decision` span attributes — `SubsystemDispatch` now
  carries the `confidence` the gate reads. (2) Story 59-8 delivered the
  precondition gate that closes the Glenross no-graph false-positive, and Story
  71-27 the unregistered gate. ADR-113 is **not superseded** — its spine stands;
  this ADR documents the gating and adjudication layered onto it and marks the
  confidence-gate gap **closed (live)**.
- **ADR-114 (Ablative HP Substrate).** The arbiter is the consumer of ADR-114's
  HP track: 0 HP fires `verdicts_on_zero_hp` per genre `LethalityPolicy`. ADR-114
  is `partial` (Part 1 live); the arbiter's HP-based Phase A trigger is the live
  part, non-HP triggers (Group E) are not yet wired.
- **ADR-116 (Confrontation Invariant).** Independent but adjacent: ADR-116
  governs *who* is in a confrontation; this pipeline governs *whether and in what
  order* the `confrontation` (and other) dispatches fire and how the resulting
  0-HP states are adjudicated. The confrontation dispatch handler engaged by the
  bank is the engagement point ADR-116's membership invariant constrains.
- **ADR-033 (Genre Mechanics Engine).** The confrontation engine the
  `confrontation` dispatch routes into is ADR-033's; this pipeline decides when
  it wakes (confidence gate) and never re-fires it twice (single bank run).
- **ADR-067 (Unified Narrator Agent).** Unviolated: this pipeline is a
  *pre-narrator* and *between-bank-and-narrator* layer (Stages 1-5 all complete
  before or during prompt build); the narrator remains the single narration
  agent, now narrating already-real, already-gated, already-adjudicated state.
